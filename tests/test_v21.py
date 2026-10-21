# ruff: noqa: F811  (the garden fixture is imported from test_phase2)
"""2.1 in Home Assistant: battery as a start signal, rain water first with pump energy,
frost heating with a budget, and learning how much water a bed takes up."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest

from custom_components.garden_manager import controllers
from custom_components.garden_manager.engine.adaptive import iso_week
from custom_components.garden_manager.engine.records import water_stats

from .test_init import _result
from .test_phase2 import garden  # noqa: F401


@pytest.fixture
def fast(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, bool]]:
    """No real waiting, and switches that report their new state at once."""
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    switched: list[tuple[str, bool]] = []

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        switched.append((entity_id, on))
        hass.states.async_set(entity_id, "on" if on else "off")

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(controllers, "_switch", fake_switch)
    return switched


async def test_a_full_home_battery_starts_the_waiting_run(hass: HomeAssistant, garden) -> None:
    entry, _ = garden
    irrigation = entry.runtime_data.irrigation
    irr = entry.runtime_data.repo.data.settings.irrigation
    irr.mode = "auto"
    irr.surplus_entity = "sensor.solar_surplus"
    irr.surplus_min_w = 800
    irr.battery_entity = "sensor.battery_soc"
    irr.battery_full_pct = 95
    morning = dt_util.now().replace(hour=7, minute=0, second=0, microsecond=0)
    hass.states.async_set("sensor.solar_surplus", "100", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.battery_soc", "80", {"unit_of_measurement": "%"})
    assert irrigation.solar_ready(morning) == (False, 100)
    await irrigation.async_start_scheduled(morning)
    assert irrigation.waiting_for_sun["battery"] == 80 and irrigation.waiting_for_sun["battery_full"] == 95
    hass.states.async_set("sensor.battery_soc", "96", {"unit_of_measurement": "%"})
    assert irrigation.solar_ready(morning)[0]  # full battery: the surplus would go to the grid anyway
    # a battery alone (no surplus sensor) also works, and still never waits past the latest time
    irr.surplus_entity = None
    hass.states.async_set("sensor.battery_soc", "50", {"unit_of_measurement": "%"})
    assert irrigation.solar_ready(morning) == (False, None)
    assert irrigation.solar_ready(morning.replace(hour=12))[0]


async def test_rain_water_first_books_source_and_pump_energy(hass: HomeAssistant, garden, fast) -> None:
    entry, _ = garden
    data = entry.runtime_data.repo.data
    irrigation = entry.runtime_data.irrigation
    irr = data.settings.irrigation
    irr.pump_entity = "switch.pump"
    irr.butt_pump_entity = "switch.butt_pump"
    irr.pump_power_w = 900
    irr.butt_pump_power_w = 300
    data.settings.water.butt_level_entity = "sensor.butt_level"
    bed = data.beds[0]
    hass.states.async_set("sensor.butt_level", "70", {"unit_of_measurement": "%"})

    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=4), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    event = data.irrigation_log[-1]
    assert event.water == "rain" and ("switch.butt_pump", True) in fast and ("switch.pump", True) not in fast
    assert event.kwh == pytest.approx(event.minutes / 60 * 0.3, abs=0.002)

    fast.clear()
    hass.states.async_set("sensor.butt_level", "5", {"unit_of_measurement": "%"})
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=4), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert data.irrigation_log[-1].water == "mains" and ("switch.pump", True) in fast

    stats = water_stats(data, dt_util.now().date())
    assert stats.irrigated_rain_l > 0 and stats.irrigated_mains_l > 0 and stats.pump_kwh > 0
    assert hass.states.get("sensor.hortulus_pump_energy_this_year") is not None

    # no mains fallback: nothing runs, the run waits for rain (once a day it says so)
    fast.clear()
    irr.butt_fallback = False
    runs = len(data.irrigation_log)
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=4), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(data.irrigation_log) == runs and not any(on for _, on in fast)
    assert irrigation.waiting_for_rain == dt_util.now().date().isoformat()


async def test_frost_heater_switches_and_books_its_energy(hass: HomeAssistant, garden, fast, freezer) -> None:
    entry, _ = garden
    runtime = entry.runtime_data
    zone = next(z for z in runtime.repo.data.zones if z.is_enclosed)
    zone.climate_control = "auto"
    zone.heater_entity = "switch.heater"
    zone.heater_power_w = 1000
    zone.microclimate.min_heating_temp_c = 5
    hass.states.async_set("switch.heater", "off")
    hass.states.async_set("sensor.greenhouse_temp", "2.0", {"unit_of_measurement": "°C", "device_class": "temperature"})
    await runtime.coordinator.async_recompute()
    await hass.async_block_till_done()
    assert ("switch.heater", True) in fast

    freezer.tick(timedelta(hours=2))
    runtime.climate.async_apply()  # still cold: two hours of 1 kW booked
    await hass.async_block_till_done()
    week = iso_week(dt_util.now().date())
    assert zone.heater_kwh[week] == pytest.approx(2.0, abs=0.01)

    zone.heater_budget_kwh_week = 2.0  # the budget is used up: off, however cold
    runtime.climate.async_apply()
    await hass.async_block_till_done()
    assert fast[-1] == ("switch.heater", False)

    # switched off in the extras: the heater is left alone (energy is still booked while it runs)
    runtime.repo.data.settings.frost_heating = False
    fast.clear()
    hass.states.async_set(
        "sensor.greenhouse_temp", "-4.0", {"unit_of_measurement": "°C", "device_class": "temperature"}
    )
    runtime.climate.async_apply()
    await hass.async_block_till_done()
    assert fast == []


async def test_heating_through_sunday_night_books_each_part_in_its_own_week(
    hass: HomeAssistant, garden, freezer
) -> None:
    entry, _ = garden
    runtime = entry.runtime_data
    zone = next(z for z in runtime.repo.data.zones if z.is_enclosed)
    zone.heater_entity = "switch.heater"
    zone.heater_power_w = 1000
    zone.climate_control = "manual"  # only the energy is booked, nothing is switched
    freezer.move_to(dt_util.as_local(dt_util.now()).replace(year=2026, month=10, day=25, hour=23, minute=0))  # Sunday
    hass.states.async_set("switch.heater", "on")
    runtime.climate._heater(zone, 1.0)  # on: counted from now
    freezer.tick(timedelta(hours=2))  # Monday 01:00
    runtime.climate._heater(zone, 1.0)
    assert zone.heater_kwh[iso_week(date(2026, 10, 25))] == pytest.approx(1.0, abs=0.01)
    assert zone.heater_kwh[iso_week(date(2026, 10, 26))] == pytest.approx(1.0, abs=0.01)


async def test_a_stale_planner_draft_keeps_what_hortulus_measured(hass: HomeAssistant, garden) -> None:
    from custom_components.garden_manager.engine.serde import to_dict
    from custom_components.garden_manager.operations import op_save_plan

    entry, _ = garden
    runtime = entry.runtime_data
    data = runtime.repo.data
    zones = [to_dict(z) for z in data.zones]  # the draft is taken now ...
    beds = [to_dict(b) for b in data.beds]
    plantings = [to_dict(p) for p in data.plantings]
    zone = next(z for z in data.zones if z.is_enclosed)
    zone.heater_kwh = {"2026-W22": 1.5}  # ... and Hortulus measures and learns meanwhile
    data.beds[0].water_factor, data.beds[0].water_factor_runs, data.beds[0].measured_flow_lpm = 1.3, 4, 3.2
    op_save_plan(hass, runtime, base_revision=None, zones=zones, beds=beds, plantings=plantings)
    zone = next(z for z in data.zones if z.is_enclosed)
    assert zone.heater_kwh == {"2026-W22": 1.5}
    assert (data.beds[0].water_factor, data.beds[0].water_factor_runs, data.beds[0].measured_flow_lpm) == (1.3, 4, 3.2)


async def test_a_bed_learns_how_much_water_soaks_in(hass: HomeAssistant, garden, fast, freezer) -> None:
    entry, _ = garden
    data = entry.runtime_data.repo.data
    irrigation = entry.runtime_data.irrigation
    bed = data.beds[0]
    assert bed.sensors.soil_moisture == "sensor.soil_moisture_bed_1"
    for _ in range(2):
        hass.states.async_set("sensor.soil_moisture_bed_1", "20", {"unit_of_measurement": "%"})
        assert irrigation.async_start(
            irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=10), source="service"
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert irrigation._soak_checks
        hass.states.async_set("sensor.soil_moisture_bed_1", "22", {"unit_of_measurement": "%"})  # +2 of the expected +5
        freezer.tick(timedelta(minutes=91))
        irrigation.async_watch(dt_util.now())
    assert bed.water_factor_runs == 2 and bed.water_factor > 1.0

    # the balance is credited with what soaked in, not with what ran off
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=10), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    last = data.irrigation_log[-1]
    assert last.mm < last.liters / bed.area_m2


async def test_what_a_bed_learned_can_be_forgotten(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _ = garden
    bed = entry.runtime_data.repo.data.beds[0]
    bed.water_factor, bed.water_factor_runs = 1.4, 3
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "garden_manager/bed/reset_water_factor", "bed_id": bed.id})
    msg = await _result(client)
    assert msg["success"], msg
    assert bed.water_factor == 1.0 and bed.water_factor_runs == 0
    await client.send_json({"id": 2, "type": "garden_manager/bed/reset_water_factor", "bed_id": "nope"})
    assert not (await _result(client))["success"]


async def test_photo_diagnosis_through_an_ai_task(hass: HomeAssistant, garden, hass_ws_client) -> None:
    from homeassistant.core import ServiceCall, SupportsResponse

    entry, _ = garden
    data = entry.runtime_data.repo.data
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "garden_manager/photo/diagnose", "photo": "abc123"})
    msg = await _result(client)
    assert not msg["success"] and msg["error"]["code"] == "ai_unavailable"

    asked: list[dict] = []

    async def generate(call: ServiceCall) -> dict:
        asked.append(dict(call.data))
        return {"conversation_id": "x", "data": {"problem_id": "late_blight", "confidence": 80, "explanation": "spots"}}

    hass.services.async_register("ai_task", "generate_data", generate, supports_response=SupportsResponse.ONLY)
    data.settings.ai_task_entity = "ai_task.garden_eye"
    planting = next(p for p in data.plantings)
    await client.send_json(
        {"id": 2, "type": "garden_manager/photo/diagnose", "photo": "abc123", "planting_id": planting.id}
    )
    msg = await _result(client)
    assert msg["success"], msg
    assert msg["result"]["problem_id"] == "late_blight" and msg["result"]["confidence"] == 80
    call = asked[-1]
    assert call["entity_id"] == "ai_task.garden_eye"
    assert call["attachments"][0]["media_content_id"] == "media-source://image_upload/abc123"
    assert "problem_id" in call["structure"]

    await client.send_json({"id": 3, "type": "garden_manager/photo/diagnose", "photo": "../../etc"})
    assert not (await _result(client))["success"]  # only an upload id
    data.settings.ai_diagnosis = False
    await client.send_json({"id": 4, "type": "garden_manager/photo/diagnose", "photo": "abc123"})
    assert (await _result(client))["error"]["code"] == "disabled"


async def test_only_an_administrator_can_send_photos_to_the_ai(
    hass: HomeAssistant, garden, hass_ws_client, hass_read_only_access_token
) -> None:
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json({"id": 1, "type": "garden_manager/photo/diagnose", "photo": "abc123"})
    msg = await _result(client)
    assert not msg["success"] and msg["error"]["code"] == "unauthorized"


async def test_tasks_are_copied_once_into_another_calendar(hass: HomeAssistant, garden) -> None:
    from homeassistant.core import ServiceCall

    from custom_components.garden_manager.calendar_mirror import async_mirror_tasks

    entry, _ = garden
    runtime = entry.runtime_data
    data = runtime.repo.data
    created: list[dict] = []

    async def create_event(call: ServiceCall) -> None:
        created.append(dict(call.data))

    hass.services.async_register("calendar", "create_event", create_event)
    assert await async_mirror_tasks(hass, runtime) == 0  # no calendar chosen
    hass.states.async_set("calendar.family", "unavailable")
    data.settings.mirror_calendar = "calendar.family"
    data.settings.mirror_days = 14
    today = dt_util.now().date()
    assert await async_mirror_tasks(hass, runtime, today) == 0  # unavailable: nothing marked as copied
    assert not [k for k in data.notified if k.startswith("mirror:")]
    hass.states.async_set("calendar.family", "off")
    expected = [t for t in data.tasks if t.is_open and today <= t.due < today + timedelta(days=14)]
    assert expected, "the example garden has tasks in the coming two weeks"
    added = await async_mirror_tasks(hass, runtime, today)
    assert added == min(len(expected), 50) == len(created)
    assert all(c["entity_id"] == "calendar.family" and "start_date" in c for c in created)
    assert await async_mirror_tasks(hass, runtime, today) == 0  # each task once
    data.settings.calendar_mirror = False
    expected[0].due = today + timedelta(days=1) if expected[0].due != today + timedelta(days=1) else today
    assert await async_mirror_tasks(hass, runtime, today) == 0  # switched off
