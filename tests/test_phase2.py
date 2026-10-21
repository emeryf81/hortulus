"""HA layer for planting services, irrigation safety, shading, autofill, print and handbook."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.garden_manager import controllers, operations
from custom_components.garden_manager.const import DOMAIN
from custom_components.garden_manager.engine.serde import to_dict

from .conftest import load_fixture
from .test_init import ENTRY_DATA, _result

ENTRY = {
    **ENTRY_DATA,
    "areas": [
        {**ENTRY_DATA["areas"][0], "irrigation": "switch.valve_bed_1", "flow_lpm": 4.0},
        {**ENTRY_DATA["areas"][1], "irrigation": "valve.greenhouse_drip", "flow_lpm": 2.0},
    ],
}


@pytest.fixture
async def garden(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> tuple[MockConfigEntry, list[tuple[str, str]]]:
    """Warm late-May day; valves, pump and shade screen record their calls."""
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    freezer.move_to("2026-05-25T08:00:00+00:00")
    for entity_id, state in load_fixture("sensors.json").items():
        hass.states.async_set(entity_id, state["state"], state["attributes"])
    hass.states.async_set("sensor.outdoor_temp", "64", {"unit_of_measurement": "°F"})
    hass.states.async_set("switch.pump", "off")

    async def get_forecasts(call: ServiceCall) -> dict[str, Any]:
        return {"weather.home": {"forecast": []}}

    hass.services.async_register("weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY)
    calls: list[tuple[str, str]] = []

    def recorder(domain: str):
        async def handler(call: ServiceCall) -> None:
            for entity_id in (
                call.data["entity_id"] if isinstance(call.data["entity_id"], list) else [call.data["entity_id"]]
            ):
                calls.append((f"{domain}.{call.service}", entity_id))

        return handler

    for domain, services in (
        ("switch", ("turn_on", "turn_off")),
        ("valve", ("open_valve", "close_valve")),
        ("cover", ("open_cover", "close_cover")),
    ):
        for service in services:
            hass.services.async_register(domain, service, recorder(domain))

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY, title="Hortulus")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


async def test_new_entities_exist(hass: HomeAssistant, garden) -> None:
    for entity_id in (
        "sensor.hortulus_reference_evapotranspiration_today",
        "sensor.hortulus_degree_days_today",
        "sensor.bed_1_nutrient_balance",
        "sensor.greenhouse_zone_a_disease_risk",
        "binary_sensor.greenhouse_zone_a_frost_risk_48h",
        "binary_sensor.hortulus_irrigation_frost_lockout",
        "binary_sensor.hortulus_irrigation_running",
        "number.hortulus_irrigation_max_runtime",
        "select.hortulus_irrigation_mode",
        "select.greenhouse_zone_a_shading",
        "switch.hortulus_automatic_irrigation",
        "button.hortulus_water_now",
    ):
        assert hass.states.get(entity_id) is not None, entity_id
    assert hass.states.get("select.hortulus_irrigation_mode").state == "advise"


async def test_planting_services(hass: HomeAssistant, garden) -> None:
    entry, _ = garden
    repo = entry.runtime_data.repo
    added = await hass.services.async_call(
        DOMAIN,
        "add_planting",
        {"plant_id": "dill", "bed": "Bed 1", "season": 2026},
        blocking=True,
        return_response=True,
    )
    pid = added["planting_id"]
    planting = repo.data.planting(pid)
    assert planting.bed_id == repo.data.beds[0].id and planting.width_cm == 200
    await hass.async_block_till_done()
    assert any(t.planting_id == pid for t in repo.data.tasks)

    updated = await hass.services.async_call(
        DOMAIN, "update_planting", {"planting_id": pid, "x_cm": 20, "status": "sown", "sown_on": "2026-05-20"},
        blocking=True, return_response=True,
    )  # fmt: skip
    assert updated["planting"]["x_cm"] == 20 and repo.data.planting(pid).sown_on.isoformat() == "2026-05-20"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "add_planting", {"plant_id": "dragonfruit", "bed": "Bed 1"}, blocking=True
        )
    await hass.services.async_call(DOMAIN, "remove_planting", {"planting_id": pid}, blocking=True)
    assert repo.data.planting(pid) is None


async def test_irrigation_dry_run_and_run_with_pump_interlock(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, calls = garden
    repo = entry.runtime_data.repo
    repo.data.settings.irrigation.pump_entity = "switch.pump"
    repo.data.settings.irrigation.max_runtime_min = 2
    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    switched: list[tuple[str, bool]] = []

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        # The switch domain belongs to Hortulus' own platform in this test,
        # so record at the controller boundary instead of mocking services.
        switched.append((entity_id, on))
        hass.states.async_set(entity_id, "on" if on else "off")  # the valve reports open: the pump may start

    monkeypatch.setattr(controllers, "_switch", fake_switch)

    dry = await hass.services.async_call(
        DOMAIN, "run_irrigation_plan", {"dry_run": True, "amount_mm": 10}, blocking=True, return_response=True
    )
    assert dry["started"] is False and len(dry["runs"]) == 2
    assert all(run["minutes"] <= 2 for run in dry["runs"]) and any(run["capped"] for run in dry["runs"])
    assert calls == []

    run = await hass.services.async_call(
        DOMAIN, "run_irrigation_plan", {"beds": ["Bed 1"], "amount_mm": 1}, blocking=True, return_response=True
    )
    assert run["started"] is True
    await hass.async_block_till_done(wait_background_tasks=True)
    # valve open -> pump on -> pump off -> valve closed, and nothing left on.
    assert switched[:4] == [
        ("switch.valve_bed_1", True),
        ("switch.pump", True),
        ("switch.pump", False),
        ("switch.valve_bed_1", False),
    ]
    assert switched[-1] == ("switch.pump", False)  # final safety sweep
    assert 0.5 * 60 in sleeps  # 1 mm x 2 m² = 2 L at 4 L/min = 0.5 min
    event = repo.data.irrigation_log[-1]
    assert event.source == "service" and event.liters == 2.0
    assert not entry.runtime_data.irrigation.running


async def test_frost_lockout_blocks_outdoor_valves(hass: HomeAssistant, garden) -> None:
    entry, _ = garden
    hass.states.async_set("sensor.outdoor_temp", "33", {"unit_of_measurement": "°F"})  # 0.6 °C
    await hass.async_block_till_done()
    response = await hass.services.async_call(
        DOMAIN, "run_irrigation_plan", {"dry_run": True, "amount_mm": 5}, blocking=True, return_response=True
    )
    bed1 = entry.runtime_data.repo.data.beds[0].id
    assert response["lockout"] is True
    assert response["skipped"][bed1]["key"] == "irrigation.skip.frost"
    assert "Frost" in response["skipped_reasons"][bed1]
    assert [r["entity_id"] for r in response["runs"]] == ["valve.greenhouse_drip"]
    await entry.runtime_data.coordinator.async_recompute()
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.hortulus_irrigation_frost_lockout").state == "on"


async def test_irrigation_entities_change_settings(hass: HomeAssistant, garden) -> None:
    entry, _ = garden
    await hass.services.async_call(
        "number", "set_value", {"entity_id": "number.hortulus_irrigation_max_runtime", "value": 12}, blocking=True
    )
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.hortulus_automatic_irrigation"}, blocking=True
    )
    settings = entry.runtime_data.repo.data.settings.irrigation
    assert settings.max_runtime_min == 12 and settings.mode == "auto"
    await hass.async_block_till_done()
    assert hass.states.get("select.hortulus_irrigation_mode").state == "auto"


async def test_shading_mode_drives_the_shade_cover(hass: HomeAssistant, garden) -> None:
    entry, calls = garden
    zone = next(z for z in entry.runtime_data.repo.data.zones if z.is_enclosed)
    zone.shade_entity = "cover.greenhouse_shade"
    await hass.services.async_call(
        DOMAIN, "set_shading_mode", {"zone": zone.name, "mode": "on"}, blocking=True, return_response=True
    )
    await hass.async_block_till_done()
    assert ("cover.close_cover", "cover.greenhouse_shade") in calls  # a shade cover deploys by closing
    await hass.services.async_call(
        "select", "select_option", {"entity_id": "select.greenhouse_zone_a_shading", "option": "off"}, blocking=True
    )
    await hass.async_block_till_done()
    assert calls[-1] == ("cover.open_cover", "cover.greenhouse_shade")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "set_shading_mode", {"zone": "Garden", "mode": "on"}, blocking=True)


async def test_autofill_service(hass: HomeAssistant, garden) -> None:
    entry, _ = garden
    repo = entry.runtime_data.repo
    before = sorted(p.id for p in repo.data.plantings)
    proposal = await hass.services.async_call(
        DOMAIN, "autofill_plan",
        {"season": 2027, "household_size": 3, "goals": ["fresh", "herbs"], "wanted": ["tomato"], "replace": True},
        blocking=True, return_response=True,
    )  # fmt: skip
    assert proposal["plantings"] and proposal["summary"]["yield_kg"] > 0
    assert sorted(p.id for p in repo.data.plantings) == before  # a proposal stores nothing
    applied = await hass.services.async_call(
        DOMAIN, "autofill_plan", {"season": 2027, "replace": True, "apply": True, "wanted": ["tomato"]},
        blocking=True, return_response=True,
    )  # fmt: skip
    assert applied["applied"]
    season_2027 = {p.id for p in repo.data.plantings if p.season == 2027}
    assert season_2027 == {p["id"] for p in applied["plantings"]}  # replaced, not stacked


async def test_export_pdf_and_http_view(
    hass: HomeAssistant, garden, hass_client, hass_client_no_auth, tmp_path: Path
) -> None:
    hass.config.config_dir = str(tmp_path)
    result = await hass.services.async_call(
        DOMAIN, "export_pdf", {"document": "garden", "page": "remarkable", "color_mode": "eink"},
        blocking=True, return_response=True,
    )  # fmt: skip
    content = await hass.async_add_executor_job(Path(result["path"]).read_bytes)
    assert content.startswith(b"%PDF") and result["url"].startswith("/api/garden_manager/exports/")
    assert "/www/" not in result["path"]  # never in the public folder

    client = await hass_client()
    exported = await client.get(f"/api/garden_manager/exports/{result['filename']}")
    assert exported.status == 200 and (await exported.read()).startswith(b"%PDF")
    assert (await client.get("/api/garden_manager/exports/..%2Fsecrets.yaml")).status in (400, 404)
    anon = await hass_client_no_auth()
    assert (await anon.get(f"/api/garden_manager/exports/{result['filename']}")).status == 401
    resp = await client.get("/api/garden_manager/print?document=beds&page=a4&landscape=1")
    assert resp.status == 200 and resp.headers["Content-Type"] == "application/pdf"
    assert (await resp.read()).startswith(b"%PDF")
    bad = await client.get("/api/garden_manager/print?document=poster")
    assert bad.status == 400


async def test_season_book_reads_journal_photos_from_image_uploads(hass: HomeAssistant, garden, tmp_path: Path) -> None:
    """The book takes photos from HA's image uploads (``image/<id>/original``), upright and scaled down."""
    from io import BytesIO

    from homeassistant.util import dt as dt_util
    from PIL import Image as PILImage

    from custom_components.garden_manager.engine.models import JournalEntry
    from custom_components.garden_manager.printing import photo_loader

    entry, _calls = garden
    hass.config.config_dir = str(tmp_path)
    photo_id = "0123456789abcdef0123456789abcdef"
    folder = tmp_path / "image" / photo_id
    folder.mkdir(parents=True)
    buf = BytesIO()
    PILImage.new("RGB", (3000, 2000), "orange").save(buf, "PNG")  # not a JPEG, too large: converted
    (folder / "original").write_bytes(buf.getvalue())
    (tmp_path / "secret.jpg").write_bytes(b"x")

    load = photo_loader(tmp_path)
    img = await hass.async_add_executor_job(load, photo_id, False)
    assert img is not None and (img.width, img.height) == (1600, 1067) and img.components == 3
    gray = await hass.async_add_executor_job(load, f"/api/image/serve/{photo_id}/512x512", True)
    assert gray is not None and gray.components == 1
    assert await hass.async_add_executor_job(load, "/local/../secret.jpg", False) is None
    assert await hass.async_add_executor_job(load, "https://example.com/a.jpg", False) is None

    repo = entry.runtime_data.repo
    repo.data.journal.append(JournalEntry("j1", dt_util.now(), "Eerste oogst", [photo_id], "milestone"))
    result = await hass.services.async_call(
        DOMAIN, "export_pdf", {"document": "book", "page": "a5"}, blocking=True, return_response=True
    )
    content = await hass.async_add_executor_job(Path(result["path"]).read_bytes)
    assert content.startswith(b"%PDF") and b"/DCTDecode" in content
    assert result["filename"].startswith("hortulus-book-")


async def test_websocket_print_handbook_autofill(hass: HomeAssistant, garden, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/print/render", "options": {"document": "tasks", "page": "remarkable"}}
    )
    pages = (await _result(client))["result"]["pages"]
    assert pages and pages[0].startswith("<svg")

    await client.send_json_auto_id({"type": f"{DOMAIN}/handbook/index", "lang": "nl"})
    index = (await _result(client))["result"]
    assert len(index["chapters"]) >= 15 and index["glossary"]["et0"]["chapter"] == "watering"
    await client.send_json_auto_id({"type": f"{DOMAIN}/handbook/chapter", "chapter_id": "greenhouse", "lang": "nl"})
    chapter = (await _result(client))["result"]
    assert chapter["title"] == "De serre" and "kuisen" in chapter["body"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/handbook/search", "query": "phytophthora", "lang": "nl"})
    assert (await _result(client))["result"]["results"]

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plan/autofill", "season": 2027, "resources": {"household_size": 4}, "replace": True}
    )
    proposal = (await _result(client))["result"]
    assert proposal["plantings"] and proposal["season"] == 2027
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/plan/autofill/apply",
            "base_revision": proposal["revision"],
            "plantings": proposal["plantings"],
            "replace_beds": proposal["beds"],
        }
    )
    assert (await _result(client))["success"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/irrigation/plan"})
    plan = (await _result(client))["result"]
    assert "runs" in plan and "reasons" in plan


async def test_websocket_advice_qa_supplies(hass: HomeAssistant, garden, hass_ws_client) -> None:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/advice"})
    advice = (await _result(client))["result"]
    assert "suggestions" in advice and len(advice["coverage"]["months"]) == 12

    await client.send_json_auto_id({"type": f"{DOMAIN}/qa/options"})
    opts = (await _result(client))["result"]
    assert "plant" in opts["subjects"] and opts["targets"]["plant"]
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/qa/ask", "subject": "plant", "problem": "pests", "target": "tomato"}
    )
    ans = (await _result(client))["result"]
    assert ans["title"] and ans["remedies"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/qa/ask", "subject": "plant", "problem": "nonsense"})
    assert not (await _result(client))["success"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/supplies"})
    supplies = (await _result(client))["result"]
    assert supplies["tools"]["secateurs"] and "prune" in supplies["task_tools"] and "shopping" in supplies


async def test_overdue_reminder_and_weekly_plan(hass: HomeAssistant, garden) -> None:
    entry, _calls = garden
    runtime = entry.runtime_data
    analysis = runtime.coordinator.data
    from datetime import timedelta

    from custom_components.garden_manager.engine.models import Task, TaskType

    runtime.repo.data.tasks.append(
        Task(
            id="late",
            title="Sow carrots",
            type=TaskType.SOW_DIRECT,
            due=analysis.today - timedelta(days=5),
            window_end=analysis.today - timedelta(days=1),
        )
    )
    await runtime.notifier.async_send_overdue(analysis)
    await runtime.notifier.async_send_weekly(analysis)
    await hass.async_block_till_done()
    notes = hass.data.get("persistent_notification") or {}
    ids = set(notes) if isinstance(notes, dict) else set()
    assert f"{DOMAIN}_overdue" in ids and f"{DOMAIN}_weekly" in ids
    # Once per day only
    assert f"overdue:{analysis.today.isoformat()}" in runtime.repo.data.notified


async def test_records_services_and_websocket(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    planting = repo.data.plantings[0]
    res = await hass.services.async_call(
        DOMAIN,
        "log_harvest",
        {"planting_id": planting.id, "kg": 1.25, "quality": 4},
        blocking=True,
        return_response=True,
    )
    assert res["harvest"]["kg"] == 1.25 and repo.data.harvest_log[0].plant_id == planting.plant_id
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "log_harvest", {"plant_id": "tomato"}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "add_journal_entry", {"text": "First flowers", "bed": "Bed 1"}, blocking=True
    )
    assert repo.data.journal[0].bed_id == repo.data.beds[0].id
    await hass.services.async_call(
        DOMAIN, "save_soil_test", {"bed": "Bed 1", "date": "2026-03-01", "ph": 6.1, "organic_matter_pct": 2.5},
        blocking=True,
    )  # fmt: skip
    assert repo.data.beds[0].latest_soil_test.ph == 6.1
    task = repo.data.tasks[0]
    await hass.services.async_call(
        DOMAIN, "assign_task", {"task_id": task.id, "assignee": "person.emery"}, blocking=True
    )
    assert repo.data.task(task.id).assignee == "person.emery"

    client = await hass_ws_client(hass)
    # A planner draft opened before the soil test neither conflicts nor drops it.
    revision = repo.data.revision
    stale_beds = [{**to_dict(b), "soil_tests": []} for b in repo.data.beds]
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/plan/save",
            "base_revision": revision,
            "zones": [to_dict(z) for z in repo.data.zones],
            "beds": stale_beds,
            # ... nor undoes the first harvest recorded since it was opened
            "plantings": [
                {**to_dict(p), "harvest_started_on": None, "status": "transplanted"}
                if p.id == planting.id
                else to_dict(p)
                for p in repo.data.plantings
            ],
        }
    )
    assert (await _result(client))["success"]
    assert repo.data.beds[0].latest_soil_test.ph == 6.1
    kept = repo.data.planting(planting.id)
    assert kept.harvest_started_on is not None and kept.status == "harvesting"
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/records/seeds/save", "packet": {"plant_id": "carrot", "year": 2025}}
    )
    packet = (await _result(client))["result"]["packet"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/records/overview"})
    overview = (await _result(client))["result"]
    assert overview["harvest_all"][planting.plant_id]["kg"] == 1.25
    assert overview["seeds"]["packets"][0]["plant_id"] == "carrot", overview["seeds"]
    assert len(overview["year"]["tasks"]) == 12  # the example plan is for next season, rows may be empty
    await client.send_json_auto_id({"type": f"{DOMAIN}/records/delete", "kind": "seed", "record_id": packet["id"]})
    assert (await _result(client))["success"] and not repo.data.seed_stock
    await client.send_json_auto_id({"type": f"{DOMAIN}/records/journal/save", "entry": {"text": ""}})
    assert not (await _result(client))["success"]
    state = hass.states.get("sensor.hortulus_harvest_this_season")
    assert state is None or float(state.state) >= 0


async def test_voice_answers_and_sentence_install(hass: HomeAssistant, garden, tmp_path: Path) -> None:
    from custom_components.garden_manager.voice import answer

    entry, _calls = garden
    runtime = entry.runtime_data
    for intent_type in ("HortulusTasksToday", "HortulusHarvest", "HortulusGreenhouse", "HortulusWater", "HortulusFrost",
                        "HortulusOverdue"):  # fmt: skip
        assert answer(runtime, intent_type, "nl")
    hass.config.config_dir = str(tmp_path)
    res = await hass.services.async_call(DOMAIN, "install_voice_sentences", {}, blocking=True, return_response=True)
    assert len(res["written"]) == 3 and (tmp_path / "custom_sentences/nl/hortulus.yaml").exists()
    again = await hass.services.async_call(DOMAIN, "install_voice_sentences", {}, blocking=True, return_response=True)
    assert again["written"] == []  # never overwrite without asking


async def test_system_log_records_and_undoes_actions(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    client = await hass_ws_client(hass)
    removed = repo.data.plantings[0]
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/plan/save",
            "base_revision": repo.data.revision,
            "zones": [to_dict(z) for z in repo.data.zones],
            "beds": [to_dict(b) for b in repo.data.beds],
            "plantings": [to_dict(p) for p in repo.data.plantings[1:]],
        }
    )
    assert (await _result(client))["success"]
    assert repo.data.planting(removed.id) is None

    await client.send_json_auto_id({"type": f"{DOMAIN}/syslog/list", "include_system": False})
    page = (await _result(client))["result"]
    latest = page["entries"][0]
    assert latest["source"] == "user" and latest["reason"] == "plan" and latest["user"]
    assert {"col": "plantings", "op": "remove"}.items() <= latest["summary"][0].items()
    assert latest["summary"][0]["plant_id"] == removed.plant_id

    await client.send_json_auto_id({"type": f"{DOMAIN}/syslog/undo", "entry_id": latest["id"]})
    res = (await _result(client))["result"]
    assert res["ok"] and res["undone_by"]
    assert repo.data.planting(removed.id) is not None

    # The undo is logged too and can itself be undone (redo).
    await client.send_json_auto_id({"type": f"{DOMAIN}/syslog/list", "include_system": False})
    entries = (await _result(client))["result"]["entries"]
    assert entries[0]["undo_of"] == latest["id"] and entries[1]["undone_by"] == entries[0]["id"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/syslog/undo", "entry_id": entries[0]["id"]})
    assert (await _result(client))["result"]["ok"]
    assert repo.data.planting(removed.id) is None

    await client.send_json_auto_id({"type": f"{DOMAIN}/syslog/undo", "entry_id": "log_nope"})
    assert not (await _result(client))["success"]


async def test_garden_plan_per_season_and_year_transition(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    data = repo.data
    assert data.layout_season == 2026  # adopted on first load
    client = await hass_ws_client(hass)

    # Design next year's plan without touching the live garden.
    zones = [to_dict(z) for z in data.zones]
    beds = [to_dict(b) for b in data.beds]
    beds[0]["name"] = "Moestuin 2027"
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plan/save", "season": 2027, "base_revision": data.revision, "zones": zones, "beds": beds,
         "plantings": [to_dict(p) for p in data.plantings], "features": []}
    )  # fmt: skip
    assert (await _result(client))["success"]
    assert data.beds[0].name != "Moestuin 2027" and data.layouts["2027"].beds[0].name == "Moestuin 2027"

    await client.send_json_auto_id({"type": f"{DOMAIN}/year/preview", "from_season": 2026})
    pre = (await _result(client))["result"]
    assert pre["to_season"] == 2027 and pre["target_exists"] and pre["is_live"]

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/year/apply", "from_season": 2026, "layout": "keep", "planting_ids": []}
    )
    res = (await _result(client))["result"]
    assert res["activated"] and res["season"] == 2027
    assert repo.data.layout_season == 2027 and repo.data.beds[0].name == "Moestuin 2027"
    assert "2026" in repo.data.layouts

    # The archived plan of a closed year cannot be deleted while plantings use it; the live one never.
    await client.send_json_auto_id({"type": f"{DOMAIN}/layout/delete", "season": 2027})
    assert not (await _result(client))["success"]


async def test_new_plan_analysis_and_autofill_on_next_years_plan(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    client = await hass_ws_client(hass)

    # A 2027 plan with a brand-new bed: autofill must be able to place crops there.
    data = repo.data
    zones = [to_dict(z) for z in data.zones]
    beds = [*(to_dict(b) for b in data.beds),
            {"id": "bed_new", "name": "Nieuw bed", "zone_id": data.beds[0].zone_id, "x_cm": data.beds[0].x_cm,
             "y_cm": data.beds[0].y_cm + 200, "width_cm": 120, "length_cm": 300}]  # fmt: skip
    zone = next(z for z in zones if z["id"] == data.beds[0].zone_id)
    zone["length_cm"] = max(zone["length_cm"], 900)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plan/save", "season": 2027, "base_revision": data.revision, "zones": zones, "beds": beds,
         "plantings": [to_dict(p) for p in data.plantings], "features": []}
    )  # fmt: skip
    assert (await _result(client))["success"]
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/plan/autofill",
            "season": 2027,
            "bed_ids": ["bed_new"],
            "replace": True,
            "resources": {"hours_per_week": 20},
        }
    )
    proposal = (await _result(client))["result"]
    assert proposal["plantings"] and {p["bed_id"] for p in proposal["plantings"]} == {"bed_new"}
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plan/autofill/apply", "plantings": proposal["plantings"], "replace_beds": ["bed_new"]}
    )
    applied = await _result(client)
    assert applied["success"], applied  # used to fail with "unknown bed": only today's beds were accepted

    # Why can't a tomato go into this year's beds in late May? (it can - or the reasons say why)
    await client.send_json_auto_id({"type": f"{DOMAIN}/analysis/explain", "plant_id": "tomato", "season": 2027})
    explained = (await _result(client))["result"]
    assert explained["has_plan"] and any(b["bed_id"] == "bed_new" for b in explained["beds"])

    # Start over in 2026 with the same zones; the old plan is kept and can come back.
    planted = {p.id for p in repo.data.plantings if p.season == 2026}
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plan/new", "season": 2026, "start": "zones", "old_name": "Eerste plan"}
    )
    res = (await _result(client))["result"]
    assert repo.data.beds == [] and repo.data.archived_plans[0].name == "Eerste plan"
    await client.send_json_auto_id({"type": f"{DOMAIN}/plan/activate", "plan_id": res["archived"]})
    assert (await _result(client))["success"]
    assert repo.data.beds and {p.id for p in repo.data.plantings if p.season == 2026} >= planted

    # Refused actions end up in the error log the analysis view shows.
    await client.send_json_auto_id({"type": f"{DOMAIN}/plan/activate", "plan_id": "nope"})
    assert not (await _result(client))["success"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/analysis"})
    analysis = (await _result(client))["result"]
    assert analysis["errors"] and analysis["errors"][0]["source"] == "error"
    assert analysis["counts"]["archived_plans"] == 1


async def test_crops_list_and_date_edits_without_the_planner(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    client = await hass_ws_client(hass)
    planting = repo.data.plantings[0]

    await client.send_json_auto_id({"type": f"{DOMAIN}/plantings/season", "season": planting.season})
    rows = (await _result(client))["result"]["rows"]
    row = next(r for r in rows if r["planting"]["id"] == planting.id)
    assert row["bed"] and "timeline" in row

    before = (planting.x_cm, planting.y_cm, planting.bed_id)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/planting/update",
            "planting_id": planting.id,
            "changes": {"sown_on": "2026-04-02", "count": 7},
        }
    )
    res = await _result(client)
    assert res["success"], res
    assert res["result"]["row"]["planting"]["sown_on"] == "2026-04-02"
    updated = next(p for p in repo.data.plantings if p.id == planting.id)
    assert updated.count == 7 and (updated.x_cm, updated.y_cm, updated.bed_id) == before  # nothing moved

    await client.send_json_auto_id({"type": f"{DOMAIN}/planting/update", "planting_id": "nope", "changes": {}})
    assert not (await _result(client))["success"]


async def test_bulk_update_fix_compare_and_still_possible(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    client = await hass_ws_client(hass)
    ids = [p.id for p in repo.data.plantings[:2]]
    log_before = len(repo.syslog)

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plantings/update_many", "planting_ids": ids, "changes": {"notes": "samen"}}
    )
    res = await _result(client)
    assert res["success"] and res["result"]["updated"] == 2
    assert all(p.notes == "samen" for p in repo.data.plantings if p.id in ids)
    assert len(repo.syslog) == log_before + 1  # one entry, one undo

    seasons_before = {p.id: p.season for p in repo.data.plantings if p.id in ids}
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/plantings/update_many", "planting_ids": ids, "changes": {"season": 1999, "notes": "x"}}
    )
    assert (await _result(client))["success"]
    assert {p.id: p.season for p in repo.data.plantings if p.id in ids} == seasons_before  # never moves a crop's year

    season = repo.data.layout_season
    await client.send_json_auto_id({"type": f"{DOMAIN}/plan/compare", "a": {"season": season}, "b": {"season": season}})
    assert (await _result(client))["result"]["identical"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/plan/compare", "a": {"plan_id": "x"}, "b": {"season": season}})
    assert not (await _result(client))["success"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/analysis/still_possible", "season": season})
    assert "plants" in (await _result(client))["result"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/analysis/fix", "code": "zone_without_beds"})
    assert not (await _result(client))["success"]
    from custom_components.garden_manager.websocket_api import build_snapshot

    assert set(build_snapshot(entry.runtime_data)["diagnosis"]) == {"error", "warning", "info"}

    # the cached garden check follows a region change made in place, and is dropped on unload
    from custom_components.garden_manager import websocket_api as ws

    runtime = entry.runtime_data
    key = ws._DIAGNOSIS_CACHE[id(runtime)][0]
    runtime.repo.data.settings.region.last_frost = "05-15"
    build_snapshot(runtime)
    assert ws._DIAGNOSIS_CACHE[id(runtime)][0] != key
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert id(runtime) not in ws._DIAGNOSIS_CACHE


def test_a_valve_can_drive_the_pump_or_a_bed() -> None:
    """A tap behind a ``valve`` entity (e.g. valve.tuinkraan_watervalve_one) works as pump or bed valve."""
    assert controllers._on_service("valve.tuinkraan_watervalve_one", True) == ("valve", "open_valve")
    assert controllers._on_service("valve.tuinkraan_watervalve_one", False) == ("valve", "close_valve")
    assert controllers._on_service("input_boolean.pomp", True) == ("input_boolean", "turn_on")


async def test_valve_test_reports_open_and_closed_with_the_pump_in_order(
    hass: HomeAssistant, garden, hass_ws_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    repo.data.settings.irrigation.pump_entity = "switch.pump"
    order: list[tuple[str, bool]] = []

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        order.append((entity_id, on))
        hass_.states.async_set(entity_id, "on" if on else "off")

    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(controllers, "_switch", fake_switch)
    valve = next(b.irrigation_entity for b in repo.data.beds if b.irrigation_entity)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/irrigation/test", "entity_id": valve, "seconds": 1})
    res = await _result(client)
    assert res["success"], res
    assert res["result"]["ok"] and res["result"]["opened"] and res["result"]["closed"]
    assert order == [(valve, True), ("switch.pump", True), ("switch.pump", False), (valve, False)]

    await client.send_json_auto_id({"type": f"{DOMAIN}/irrigation/test", "entity_id": "switch.kettle"})
    assert not (await _result(client))["success"]  # only valves Hortulus drives


async def test_a_valve_that_does_not_respond_or_stays_open_is_reported(
    hass: HomeAssistant, garden, hass_ws_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    from custom_components.garden_manager.websocket_api import build_snapshot

    entry, _calls = garden
    runtime = entry.runtime_data
    monkeypatch.setattr(controllers, "STATE_TIMEOUT_S", 0.5)
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)

    async def dead_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        return None

    monkeypatch.setattr(controllers, "_switch", dead_switch)
    valve = next(b.irrigation_entity for b in runtime.repo.data.beds if b.irrigation_entity)
    hass.states.async_set(valve, "off")
    result = await runtime.irrigation.async_test(valve, seconds=1, with_pump=False)
    assert not result["ok"] and result["opened"] is False
    assert any(
        e.get("source") == "error" and e["summary"][0]["key"] == "valve_did_not_open" for e in runtime.repo.syslog
    )

    # left open by hand / stuck: reported once it is open far longer than any run
    hass.states.async_set(valve, "open")
    now = dt_util.now()
    runtime.irrigation.async_watch(now)
    assert not runtime.irrigation.stuck
    runtime.irrigation.async_watch(now + timedelta(minutes=runtime.repo.data.settings.irrigation.max_runtime_min + 11))
    assert valve in runtime.irrigation.stuck
    assert build_snapshot(runtime)["irrigation_status"]["stuck"][0]["entity_id"] == valve

    async def working_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        hass_.states.async_set(entity_id, "on" if on else "off")

    monkeypatch.setattr(controllers, "_switch", working_switch)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/irrigation/close", "entity_id": valve})
    res = await _result(client)
    assert res["success"] and res["result"]["state"] == "off"
    assert not runtime.irrigation.stuck


async def test_planning_overview(hass: HomeAssistant, garden, hass_ws_client) -> None:
    entry, _calls = garden
    client = await hass_ws_client(hass)
    season = entry.runtime_data.repo.data.layout_season
    await client.send_json_auto_id({"type": f"{DOMAIN}/planning", "season": season})
    res = await _result(client)
    assert res["success"], res
    assert {"seeds", "successions", "harvest"} <= set(res["result"])
    assert all(w["kg"] >= 0 for w in res["result"]["harvest"]["weeks"])


async def test_valve_test_never_runs_the_pump_against_a_closed_valve(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    entry, _calls = garden
    runtime = entry.runtime_data
    runtime.repo.data.settings.irrigation.pump_entity = "switch.pump"
    monkeypatch.setattr(controllers, "STATE_TIMEOUT_S", 0.5)
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    order: list[tuple[str, bool]] = []

    async def stuck_closed(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        order.append((entity_id, on))
        if entity_id == "switch.pump":
            hass_.states.async_set(entity_id, "on" if on else "off")

    monkeypatch.setattr(controllers, "_switch", stuck_closed)
    valve = next(b.irrigation_entity for b in runtime.repo.data.beds if b.irrigation_entity)
    hass.states.async_set(valve, "off")
    result = await runtime.irrigation.async_test(valve, seconds=1)
    assert not result["ok"] and ("switch.pump", True) not in order and order[-1] == (valve, False)

    # a stuck valve that stops reporting is not taken for closed
    hass.states.async_set(valve, "open")
    now = dt_util.now()
    runtime.irrigation.async_watch(now)
    runtime.irrigation.async_watch(now + timedelta(minutes=runtime.repo.data.settings.irrigation.max_runtime_min + 11))
    assert valve in runtime.irrigation.stuck
    hass.states.async_set(valve, "unavailable")
    runtime.irrigation.async_watch(now + timedelta(minutes=60))
    assert valve in runtime.irrigation.stuck
    hass.states.async_set(valve, "closing")
    assert await runtime.irrigation.async_close(valve) == "closing" and valve in runtime.irrigation.stuck


async def test_pump_is_never_tested_alone_and_close_stops_a_run(
    hass: HomeAssistant, garden, hass_ws_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _calls = garden
    runtime = entry.runtime_data
    runtime.repo.data.settings.irrigation.pump_entity = "switch.pump"
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/irrigation/test", "entity_id": "switch.pump"})
    assert not (await _result(client))["success"]
    with pytest.raises(Exception, match="bed valve"):
        await runtime.irrigation.async_test("switch.pump")

    stopped: list[bool] = []

    async def fake_stop() -> None:
        stopped.append(True)

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        hass_.states.async_set(entity_id, "on" if on else "off")

    monkeypatch.setattr(runtime.irrigation, "async_stop", fake_stop)
    monkeypatch.setattr(controllers, "_switch", fake_switch)
    monkeypatch.setattr(type(runtime.irrigation), "running", property(lambda self: not stopped))
    valve = next(b.irrigation_entity for b in runtime.repo.data.beds if b.irrigation_entity)
    assert await runtime.irrigation.async_close(valve) == "off" and stopped == [True]


async def test_missing_seed_goes_to_a_todo_list_once(hass: HomeAssistant, garden, hass_ws_client) -> None:
    """Seeds the plan lacks land on a HA to-do list; items already on it are not added twice."""
    from homeassistant.core import SupportsResponse

    from custom_components.garden_manager.engine.models import PlantingStatus, SowMethod

    entry, _calls = garden
    repo = entry.runtime_data.repo
    season = repo.data.plantings[0].season
    for p in repo.data.plantings:
        p.status, p.method = PlantingStatus.PLANNED, SowMethod.DIRECT_SOW
    repo.data.seed_stock = []
    items: list[str] = []
    hass.states.async_set("todo.shopping_list", "0")

    async def get_items(call: ServiceCall):
        return {"todo.shopping_list": {"items": [{"summary": s} for s in items]}}

    async def add_item(call: ServiceCall) -> None:
        items.append(call.data["item"])

    hass.services.async_register("todo", "get_items", get_items, supports_response=SupportsResponse.ONLY)
    hass.services.async_register("todo", "add_item", add_item)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/seeds/to_todo", "season": season, "entity_id": "todo.shopping_list"}
    )
    first = (await _result(client))["result"]
    assert first["added"] > 0 and first["skipped"] == 0 and len(items) == first["added"]
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/seeds/to_todo", "season": season, "entity_id": "todo.shopping_list"}
    )
    second = (await _result(client))["result"]
    assert second["added"] == 0 and second["skipped"] == first["added"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/seeds/to_todo", "season": season, "entity_id": "light.kitchen"})
    assert not (await _result(client))["success"]


async def test_runs_split_for_the_valve_timer_and_learn_the_flow_from_the_meter(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valve with its own 10-minute timer gets 9 + 9 + 7 minutes; the meter tells the real flow."""
    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.irrigation.max_runtime_min = 60
    repo.data.settings.water.meter_entity = "sensor.garden_water"
    hass.states.async_set("sensor.garden_water", "1.000", {"unit_of_measurement": "m³"})
    bed = next(b for b in repo.data.beds if b.irrigation_entity == "switch.valve_bed_1")
    bed.valve_max_min = 10
    meter = {"l": 1000.0}
    real_sleep = asyncio.sleep

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        opened.append((entity_id, on))
        hass.states.async_set(entity_id, "on" if on else "off")

    async def fake_sleep(seconds: float) -> None:
        if hass.states.get("switch.valve_bed_1").state == "on":
            meter["l"] += seconds / 60 * 12.0  # really 12 L/min, not the 4 entered
            hass.states.async_set("sensor.garden_water", f"{meter['l'] / 1000:.4f}", {"unit_of_measurement": "m³"})
        await real_sleep(0)

    opened: list[tuple[str, bool]] = []
    monkeypatch.setattr(controllers, "_switch", fake_switch)
    monkeypatch.setattr(controllers.asyncio, "sleep", fake_sleep)
    plan = irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=50)  # 100 L at 4 L/min = 25 min
    assert plan.runs[0].minutes == 25
    assert irrigation.async_start(plan, source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert [on for e, on in opened if e == "switch.valve_bed_1"] == [True, False, True, False, True, False]
    event = repo.data.irrigation_log[-1]
    assert event.minutes == 25 and event.liters == pytest.approx(300, abs=1)  # measured, not 100 L
    assert bed.measured_flow_lpm == pytest.approx(12, abs=0.1)
    bed.irrigation_flow_lpm = None
    assert bed.flow_lpm == pytest.approx(12, abs=0.1)  # used when no flow is entered


async def test_a_valve_that_shuts_by_itself_ends_the_run_and_is_reported(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.irrigation.max_runtime_min = 60
    bed = next(b for b in repo.data.beds if b.irrigation_entity == "switch.valve_bed_1")
    held = {"s": 0.0}
    real_sleep = asyncio.sleep

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        hass.states.async_set(entity_id, "on" if on else "off")

    async def fake_sleep(seconds: float) -> None:
        held["s"] += seconds
        if held["s"] >= 120:  # the valve's own timer shuts it after two minutes
            hass.states.async_set("switch.valve_bed_1", "off")
        await real_sleep(0)

    monkeypatch.setattr(controllers, "_switch", fake_switch)
    monkeypatch.setattr(controllers.asyncio, "sleep", fake_sleep)
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=20), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert repo.data.irrigation_log[-1].minutes == 1.5  # last seen open at 90 s, closed at the 120 s check
    assert any(e["summary"][0]["key"] == "valve_closed_early" for e in repo.syslog if e["source"] == "error")


async def test_water_counted_with_every_valve_closed_is_a_leak(hass: HomeAssistant, garden) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.water.meter_entity = "sensor.garden_water"
    for entity_id in irrigation.valve_entities():
        hass.states.async_set(entity_id, "off" if entity_id.startswith("switch.") else "closed")
    start = dt_util.now()
    for minute in range(0, 17):
        hass.states.async_set("sensor.garden_water", str(500 + minute * 0.5), {"unit_of_measurement": "L"})
        irrigation.async_watch(start + timedelta(minutes=minute))
    assert irrigation.leak is not None and irrigation.leak["liters"] >= 5
    for minute in range(17, 40):  # the tap is closed again: no more water counted
        irrigation.async_watch(start + timedelta(minutes=minute))
    assert irrigation.leak is None
    repo.data.settings.water.leak_alerts = False
    for minute in range(40, 60):
        hass.states.async_set("sensor.garden_water", str(600 + minute), {"unit_of_measurement": "L"})
        irrigation.async_watch(start + timedelta(minutes=minute))
    assert irrigation.leak is None


async def test_phone_notification_buttons_complete_postpone_and_close(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The digest carries Done / Tomorrow; pressing them on the phone changes the tasks; a stuck valve gets Close."""
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    from custom_components.garden_manager.engine.models import Task, TaskStatus, TaskType

    entry, _calls = garden
    runtime = entry.runtime_data
    repo = runtime.repo
    today = dt_util.now().date()
    sent: list[dict[str, Any]] = []

    async def phone(call: ServiceCall) -> None:
        sent.append(dict(call.data))

    hass.services.async_register("notify", "mobile_app_phone", phone)
    repo.data.settings.notifications.notify_services = ["notify.mobile_app_phone"]
    repo.data.tasks = [Task("only", TaskType.WEED, "Wieden", today)]
    await runtime.notifier.async_send_digest(runtime.coordinator.data)
    await hass.async_block_till_done()
    actions = sent[-1]["data"]["actions"]
    assert [a["title"] for a in actions][:2] == ["Done", "Tomorrow"] or [a["title"] for a in actions][:2] == [
        "Gedaan",
        "Morgen",
    ]
    hass.bus.async_fire("mobile_app_notification_action", {"action": actions[1]["action"]})  # tomorrow
    await hass.async_block_till_done()
    assert repo.data.task("only").due == today + timedelta(days=1)

    repo.data.notified.clear()
    await runtime.notifier.async_send_overdue(runtime.coordinator.data)  # nothing overdue: no buttons needed
    repo.data.tasks.append(Task("two", TaskType.MULCH, "Mulchen", today))
    done = runtime.notifier.actions.for_tasks([repo.data.task("two")], "en")[0]
    hass.bus.async_fire("mobile_app_notification_action", {"action": done["action"]})
    await hass.async_block_till_done()
    assert repo.data.task("two").status is TaskStatus.DONE
    # a used button does nothing the second time, a foreign action is ignored
    hass.bus.async_fire("mobile_app_notification_action", {"action": done["action"]})
    hass.bus.async_fire("mobile_app_notification_action", {"action": "OTHER_APP_THING"})
    await hass.async_block_till_done()

    valve = "valve.greenhouse_drip"
    closed: list[str] = []

    async def fake_close(entity_id: str) -> str:
        closed.append(entity_id)
        return "closed"

    monkeypatch.setattr(runtime.irrigation, "async_close", fake_close)
    close = runtime.notifier.actions.for_valve(valve, "nl")[0]
    assert close["title"] == "Kraan dicht"
    hass.bus.async_fire("mobile_app_notification_action", {"action": close["action"]})
    await hass.async_block_till_done()
    assert closed == [valve]

    # "Water now" carries this garden's token and waters only the beds that asked for it (also in advise mode)
    bed = next(b for b in repo.data.beds if b.irrigation_entity)
    started: list[set[str]] = []
    monkeypatch.setattr(runtime.notifier.actions, "thirsty_beds", lambda: {bed.id})
    real_build = runtime.irrigation.build_plan

    def build(**kw):
        assert kw.get("force") is True  # the press is the go-ahead, also in advise mode
        started.append(kw.get("bed_ids"))
        return real_build(**kw)

    monkeypatch.setattr(runtime.irrigation, "build_plan", build)
    monkeypatch.setattr(runtime.irrigation, "async_start", lambda plan, source="auto": True)
    water = next(a for a in runtime.notifier.actions.for_tasks([], "en") if a["action"].startswith("HORTULUS_WATER_"))
    hass.bus.async_fire("mobile_app_notification_action", {"action": "HORTULUS_WATER_deadbeef"})  # another garden's
    await hass.async_block_till_done()
    assert started == []
    hass.bus.async_fire("mobile_app_notification_action", {"action": water["action"]})
    await hass.async_block_till_done()
    assert started == [{bed.id}]


async def test_harvest_by_plant_name_finds_the_crop(hass: HomeAssistant, garden) -> None:
    """``log_harvest`` with a plant name (as an NFC tag would send) books it on the one crop in the garden."""
    entry, _calls = garden
    repo = entry.runtime_data.repo
    crop = next(p for p in repo.data.plantings if p.plant_id == "tomato")
    others = [p for p in repo.data.plantings if p.plant_id == "tomato" and p is not crop]
    for p in others:
        repo.data.plantings.remove(p)
    crop.season = 2026  # the example plan is for next year; the harvest is today (May 2026)
    result = await hass.services.async_call(
        DOMAIN, "log_harvest", {"plant": "TOMAAT", "kg": 0.8}, blocking=True, return_response=True
    )
    assert result["harvest"]["plant_id"] == "tomato" and result["harvest"]["planting_id"] == crop.id
    assert crop.harvest_started_on is not None
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "log_harvest", {"plant": "Mandragora", "kg": 1}, blocking=True)


async def test_two_gardens_side_by_side(hass: HomeAssistant, garden, hass_ws_client) -> None:
    """A second garden has its own data; the panel picks it with ``garden_id``, services with ``garden``."""
    entry, _calls = garden
    second = MockConfigEntry(domain=DOMAIN, data={**ENTRY, "storage_key": f"{DOMAIN}.garden_two"}, title="Volkstuin")
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    first_repo, second_repo = entry.runtime_data.repo, second.runtime_data.repo
    assert first_repo is not second_repo and second_repo.key == f"{DOMAIN}.garden_two"

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/subscribe", "garden_id": second.entry_id})
    assert (await client.receive_json())["success"]
    snap = (await client.receive_json())["event"]
    assert snap["entry_id"] == second.entry_id
    assert {g["title"] for g in snap["gardens"]} == {"Hortulus", "Volkstuin"}

    before = len(first_repo.data.harvest_log)
    await hass.services.async_call(
        DOMAIN, "log_harvest", {"plant_id": "tomato", "kg": 1, "garden": "volkstuin"}, blocking=True
    )
    assert len(second_repo.data.harvest_log) == 1 and len(first_repo.data.harvest_log) == before
    await hass.services.async_call(DOMAIN, "log_harvest", {"plant_id": "tomato", "kg": 1}, blocking=True)
    assert len(first_repo.data.harvest_log) == before + 1  # no garden named: the first one

    # unloading one garden keeps the panel for the other
    assert await hass.config_entries.async_unload(second.entry_id)
    from homeassistant.components.frontend import DATA_PANELS

    assert "hortulus" in hass.data.get(DATA_PANELS, {})


async def test_the_pump_waits_for_a_valve_that_reports_open(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valve that never reports open gets no pump and no water booked; it is reported."""
    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.irrigation.pump_entity = "switch.pump"
    switched: list[tuple[str, bool]] = []
    real_sleep = asyncio.sleep

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        switched.append((entity_id, on))  # the valve never changes state

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(controllers, "_switch", fake_switch)
    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    hass.states.async_set("switch.valve_bed_1", "off")
    bed = next(b for b in repo.data.beds if b.irrigation_entity == "switch.valve_bed_1")
    before = len(repo.data.irrigation_log)
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=5), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert ("switch.pump", True) not in switched
    assert len(repo.data.irrigation_log) == before
    assert any(e["summary"][0]["key"] == "valve_did_not_open" for e in repo.syslog if e["source"] == "error")


def test_valve_timer_chunks_and_jpeg_guard() -> None:
    from custom_components.garden_manager.controllers import _chunks
    from custom_components.garden_manager.engine.pdf import jpeg_info

    assert _chunks(25, 10) == [9, 9, 7]
    assert _chunks(3, 1) == [0.75, 0.75, 0.75, 0.75]  # a one-minute timer still splits
    assert _chunks(5, None) == [5]
    assert jpeg_info(b"\xff\xd8\xff\xe0\x00\x00" + b"\x00" * 20) is None  # a zero-length segment


async def test_archive_write_failure_never_loses_a_season(hass: HomeAssistant, garden) -> None:
    """Home Assistant's store logs a failed write instead of raising: the garden keeps the season."""
    from unittest.mock import AsyncMock, patch

    from custom_components.garden_manager.engine.models import Planting, PlantingStatus

    entry, _ = garden
    repo = entry.runtime_data.repo
    old = Planting(id="old_tomato", plant_id="tomato", bed_id=repo.data.beds[0].id, season=2020)
    old.status = PlantingStatus.FINISHED
    repo.data.plantings.append(old)

    with patch.object(repo.archive_store, "async_save", AsyncMock()):  # the write "succeeds" but nothing lands
        assert await repo.async_archive_old(2026) is False
    assert repo.data.planting("old_tomato") is not None

    # the real write: still in the garden until the archive has been read back
    assert await repo.async_archive_old(2026) is False
    assert repo.data.planting("old_tomato") is not None

    await repo._async_load_archive()  # what the next start-up does
    assert await repo.async_archive_old(2026) is True
    assert repo.data.planting("old_tomato") is None
    assert any(p.id == "old_tomato" for p in repo.data_for_season(2020).plantings)


async def test_money_must_be_a_real_number(hass: HomeAssistant, garden) -> None:

    entry, _ = garden
    runtime = entry.runtime_data
    for amount in ("nan", "inf", "-3", 0):
        with pytest.raises(ServiceValidationError):
            operations.op_save_expense(runtime, {"amount": amount, "category": "seeds"})
    assert runtime.repo.data.expenses == []
    with pytest.raises(ServiceValidationError):
        operations.op_save_settings(runtime, {"economy": {"prices": {"tomato": "nan"}}})
    operations.op_save_settings(runtime, {"economy": {"prices": {"tomato": "4.5", "carrot": ""}}})
    assert runtime.repo.data.settings.economy.prices == {"tomato": 4.5}
    assert operations.op_save_expense(runtime, {"amount": "12.5", "category": "seeds"}).amount == 12.5


async def test_cooking_suggest_save_print_and_shop(hass: HomeAssistant, garden, hass_ws_client) -> None:
    """Recipes from the garden; the cookbook keeps them; PDF and to-do list work."""
    import base64

    from homeassistant.core import SupportsResponse

    entry, _calls = garden
    repo = entry.runtime_data.repo
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/suggest", "produce": ["kale", "carrot", "leek"], "prefs": {"proteins": ["pork"]}}
    )
    res = (await _result(client))["result"]
    assert res["recipes"] and res["catalog"]["sides"] and res["book"] == []
    assert all(len(m["courses"]) == 3 and m["title"] for m in res["menus"])
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/cooking/suggest",
            "produce": ["tomato", "courgette", "basil", "strawberry", "carrot"],
            "limit": 6,
        }
    )
    summer = (await _result(client))["result"]
    assert summer["menus"] and all(
        r["spec"]["produce"] for m in summer["menus"] for c in m["courses"] for r in [c["recipe"]]
    )
    assert any(r["course"] == "preserve" for r in summer["recipes"])
    assert any(not p["fridge"] for p in summer["catalog"]["pantry"]) and any(
        p["fridge"] for p in summer["catalog"]["pantry"]
    )
    assert any(p["plant_id"] == "kale" for p in res["catalog"]["edible"])
    recipe = res["recipes"][0]
    assert {i["plant_id"] for i in recipe["ingredients"] if i["source"] == "garden"} <= {"kale", "carrot", "leek"}

    spec = {**recipe["spec"], "side": "bulgur"}
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/render", "spec": spec})
    changed = (await _result(client))["result"]
    assert changed["saved"] is False and any(i["id"] == "bulgur" for i in changed["recipe"]["ingredients"])

    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/book/save", "recipe": {"spec": spec, "favorite": True}})
    saved = (await _result(client))["result"]
    assert saved["id"] == changed["recipe"]["id"] and saved["book"][0]["favorite"] is True
    assert len(repo.data.cookbook) == 1
    # malformed lists are refused or cleaned, never an unknown_error
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/render", "spec": {**spec, "produce": 1}})
    assert (await _result(client))["error"]["code"] == "invalid_recipe"
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/book/save", "recipe": {"spec": {**spec, "produce": 1}}})
    assert (await _result(client))["error"]["code"] == "invalid_recipe"
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/book/save", "recipe": {"spec": {**spec, "extras": [{}, *spec.get("extras", [])]}}}
    )
    assert (await _result(client))["success"] and len(repo.data.cookbook) == 1
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/cooking/book/update",
            "recipe_id": saved["id"],
            "changes": {"shared": True, "title": "Ons recept"},
        }
    )
    book = (await _result(client))["result"]["book"]
    assert book[0]["shared"] is True and book[0]["title"] == "Ons recept"
    # the cook's own version: ingredients and steps by hand, back to the generated with []
    own = {"ingredients": [{"name": "Boerenkool", "qty": 400, "unit": "g", "source": "garden", "plant_id": "kale"},
                           {"name": "Gerookte paprika", "qty": 1, "unit": "tbsp", "source": "shop"}],
           "steps": ["Alles in de pan.", "  ", "Proeven."]}  # fmt: skip
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/book/update", "recipe_id": saved["id"], "changes": own})
    mine = (await _result(client))["result"]["book"][0]
    assert mine["custom"] is True and mine["steps"] == ["Alles in de pan.", "Proeven."] and mine["id"] == saved["id"]
    assert [i["name"] for i in mine["shopping"]] == ["Gerookte paprika"]
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/cooking/book/update",
            "recipe_id": saved["id"],
            "changes": {"title": "Kapot", "ingredients": [{"name": ""}]},
        }
    )
    assert (await _result(client))["error"]["code"] == "invalid_recipe"
    assert repo.data.cookbook[0].title == "Ons recept"  # a refused change changes nothing
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/book/update", "recipe_id": saved["id"], "changes": {"steps": "Alles in de pan."}}
    )
    assert (await _result(client))["error"]["code"] == "invalid_recipe"  # a wrong shape is no reset
    other = {**spec, "servings": 7}  # another dish: a refused save adds no entry
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/book/save", "recipe": {"spec": other, "ingredients": [{"name": " "}]}}
    )
    assert (await _result(client))["error"]["code"] == "invalid_recipe" and len(repo.data.cookbook) == 1
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/book/update", "recipe_id": saved["id"], "changes": {"ingredients": [], "steps": []}}
    )
    assert (await _result(client))["result"]["book"][0]["custom"] is False
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/book/update", "recipe_id": saved["id"], "changes": {}, "pantry": ["bulgur"]}
    )
    kept = (await _result(client))["result"]["book"][0]  # the answer follows the unsaved "at home" choices
    assert next(i for i in kept["ingredients"] if i["id"] == "bulgur")["source"] == "pantry"
    # what the cook has at home (sent along) is not bought
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/render", "spec": spec, "pantry": ["bulgur"]})
    home = (await _result(client))["result"]["recipe"]
    assert next(i for i in home["ingredients"] if i["id"] == "bulgur")["source"] == "pantry"

    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/pdf", "kind": "book", "ids": [saved["id"]]})
    pdf = (await _result(client))["result"]
    assert base64.b64decode(pdf["pdf"]).startswith(b"%PDF") and pdf["filename"].endswith(".pdf")

    items: list[str] = []
    hass.states.async_set("todo.shopping_list", "0")

    async def get_items(call: ServiceCall):
        return {"todo.shopping_list": {"items": [{"summary": s} for s in items]}}

    async def add_item(call: ServiceCall) -> None:
        items.append(call.data["item"])

    hass.services.async_register("todo", "get_items", get_items, supports_response=SupportsResponse.ONLY)
    hass.services.async_register("todo", "add_item", add_item)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/to_todo", "entity_id": "todo.shopping_list", "ids": [saved["id"]]}
    )
    first = (await _result(client))["result"]
    assert first["added"] == len(items) > 0
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/to_todo", "entity_id": "todo.shopping_list", "ids": [saved["id"]]}
    )
    assert (await _result(client))["result"]["added"] == 0

    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/send", "what": "shopping", "ids": [saved["id"]]})
    assert "bulgur" in (await _result(client))["result"]["text"]

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/cooking/prefs", "prefs": {"pantry": ["rice", "nope"], "servings": 3}}
    )
    assert (await _result(client))["result"]["prefs"]["pantry"] == ["rice"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/book/delete", "recipe_id": saved["id"]})
    assert (await _result(client))["result"]["book"] == []
    await client.send_json_auto_id({"type": f"{DOMAIN}/cooking/book/delete", "recipe_id": saved["id"]})
    assert not (await _result(client))["success"]


async def test_stop_ends_a_valve_test_pump_first(hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop (or Close) during a valve test: the pump goes off before the valve shuts."""
    from custom_components.garden_manager import controllers

    entry, _calls = garden
    runtime = entry.runtime_data
    runtime.repo.data.settings.irrigation.pump_entity = "switch.pump"
    real_sleep = asyncio.sleep
    holding = asyncio.Event()

    async def sleep(seconds: float) -> None:
        if seconds >= 60:  # the test holds the valve open: wait until stopped
            holding.set()
            await asyncio.Event().wait()
        await real_sleep(0)

    monkeypatch.setattr(controllers.asyncio, "sleep", sleep)
    order: list[tuple[str, bool]] = []

    async def switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        order.append((entity_id, on))
        hass_.states.async_set(entity_id, "on" if on else "off")

    monkeypatch.setattr(controllers, "_switch", switch)
    valve = next(b.irrigation_entity for b in runtime.repo.data.beds if b.irrigation_entity)
    hass.states.async_set(valve, "off")
    test = hass.async_create_task(runtime.irrigation.async_test(valve, seconds=60))
    await holding.wait()
    assert runtime.irrigation.running and ("switch.pump", True) in order
    await runtime.irrigation.async_stop()
    result = await test
    assert result["stopped"] and not runtime.irrigation.running
    assert order.index(("switch.pump", False)) < order.index((valve, False))


async def test_a_second_customisation_keeps_the_first(hass: HomeAssistant, garden, hass_ws_client) -> None:
    """Change spacing, later only the name: the spacing stays customised."""
    entry, _calls = garden
    client = await hass_ws_client(hass)
    for patch in ({"spacing_cm": 7}, {"names": {"en": "Mighty carrot"}}, {"names": {"fr": "Carotte royale"}}):
        await client.send_json_auto_id(
            {"type": f"{DOMAIN}/plants/save", "mode": "override", "plant": {"id": "carrot", **patch}}
        )
        assert (await _result(client))["success"]
    assert entry.runtime_data.repo.data.plant_overrides["carrot"]["spacing_cm"] == 7
    names = entry.runtime_data.repo.data.plant_overrides["carrot"]["names"]
    assert names["en"] == "Mighty carrot" and names["fr"] == "Carotte royale"
    assert entry.runtime_data.repo.db.get("carrot").spacing_cm == 7


async def test_a_stale_draft_does_not_reopen_a_finished_crop(hass: HomeAssistant, garden, hass_ws_client) -> None:
    from datetime import date

    from custom_components.garden_manager.engine.models import PlantingStatus

    entry, _calls = garden
    repo = entry.runtime_data.repo
    planting = repo.data.plantings[0]
    stale = [to_dict(p) for p in repo.data.plantings]
    planting.harvest_started_on, planting.status = date(2026, 5, 1), PlantingStatus.FINISHED
    stale[0] = {**stale[0], "status": "transplanted", "harvest_started_on": None}
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/plan/save",
            "base_revision": repo.data.revision,
            "zones": [to_dict(z) for z in repo.data.zones],
            "beds": [to_dict(b) for b in repo.data.beds],
            "plantings": stale,
        }
    )
    assert (await _result(client))["success"]
    assert repo.data.planting(planting.id).status == "finished"


async def test_a_watering_task_ticked_twice_books_its_water_once(hass: HomeAssistant, garden) -> None:
    from datetime import date

    from custom_components.garden_manager.engine.models import Task, TaskType
    from custom_components.garden_manager.operations import op_complete_task

    entry, _calls = garden
    runtime = entry.runtime_data
    bed = next(b for b in runtime.repo.data.beds if b.area_m2 > 0)
    runtime.repo.data.tasks.append(
        Task(
            id="t_water",
            title="Water",
            type=TaskType.WATER,
            due=date(2026, 5, 25),
            bed_id=bed.id,
            title_params={"liters": 10},
        )
    )
    before = len(runtime.repo.data.irrigation_log)
    op_complete_task(hass, runtime, "t_water")
    op_complete_task(hass, runtime, "t_water")  # a second dashboard, a retried automation
    assert len(runtime.repo.data.irrigation_log) == before + 1


async def test_a_failed_vent_command_is_tried_again(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.garden_manager import controllers

    entry, _calls = garden
    climate = entry.runtime_data.climate
    tries: list[bool] = []

    async def flaky(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        tries.append(on)
        if len(tries) == 1:
            raise HomeAssistantError("device unavailable")

    monkeypatch.setattr(controllers, "_switch", flaky)
    climate._set("vent:z", "cover.vent", True, shade=False)
    await hass.async_block_till_done()
    climate._set("vent:z", "cover.vent", True, shade=False)  # the next update: tried again
    await hass.async_block_till_done()
    climate._set("vent:z", "cover.vent", True, shade=False)  # now done: not sent a third time
    await hass.async_block_till_done()
    assert tries == [True, True]


# --------------------------------------------------------------------------- #
# Whole-repository review findings (valves, to-do exports, import, input checks)
# --------------------------------------------------------------------------- #
async def test_a_valve_that_stays_closed_gets_no_water_booked_even_without_a_pump(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.irrigation.pump_entity = ""
    real_sleep = asyncio.sleep

    async def stuck_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        hass.states.async_set(entity_id, "off")  # accepts the command, stays closed

    async def fast_sleep(seconds: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(controllers, "_switch", stuck_switch)
    monkeypatch.setattr(controllers, "STATE_TIMEOUT_S", 0.2)
    monkeypatch.setattr(controllers.asyncio, "sleep", fast_sleep)
    bed = next(b for b in repo.data.beds if b.irrigation_entity == "switch.valve_bed_1")
    before = len(repo.data.irrigation_log)
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=5), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(repo.data.irrigation_log) == before
    assert any(e["summary"][0]["key"] == "valve_did_not_open" for e in repo.syslog if e["source"] == "error")


async def test_a_valve_that_goes_silent_stops_the_pump(
    hass: HomeAssistant, garden, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry, _calls = garden
    repo = entry.runtime_data.repo
    irrigation = entry.runtime_data.irrigation
    repo.data.settings.irrigation.pump_entity = "switch.pump"
    repo.data.settings.irrigation.max_runtime_min = 60
    held = {"s": 0.0}
    real_sleep = asyncio.sleep

    async def fake_switch(hass_: HomeAssistant, entity_id: str, on: bool) -> None:
        hass.states.async_set(entity_id, "on" if on else "off")

    async def fake_sleep(seconds: float) -> None:
        held["s"] += seconds
        if held["s"] >= 40:  # the valve reported open, then drops off the network
            hass.states.async_set("switch.valve_bed_1", "unavailable")
        await real_sleep(0)

    monkeypatch.setattr(controllers, "_switch", fake_switch)
    monkeypatch.setattr(controllers.asyncio, "sleep", fake_sleep)
    bed = next(b for b in repo.data.beds if b.irrigation_entity == "switch.valve_bed_1")
    assert irrigation.async_start(irrigation.build_plan(force=True, bed_ids={bed.id}, override_mm=20), source="service")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("switch.pump").state == "off"  # not left running against a valve nobody can see
    assert held["s"] < 300  # ended after about a minute of silence, not after the whole run
    assert any(e["summary"][0]["key"] == "valve_lost" for e in repo.syslog if e["source"] == "error")


async def test_to_do_exports_follow_the_users_own_rights(
    hass: HomeAssistant, garden, hass_ws_client, hass_read_only_access_token
) -> None:
    hass.states.async_set("todo.shopping", "0")
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/cooking/to_todo",
            "entity_id": "todo.shopping",
            "specs": [{"technique": "soup", "produce": ["carrot"]}],
        }
    )
    res = await client.receive_json()
    assert not res["success"] and res["error"]["code"] == "unauthorized"
    await client.send_json_auto_id({"type": f"{DOMAIN}/seeds/to_todo", "entity_id": "todo.shopping", "season": 2026})
    assert (await client.receive_json())["error"]["code"] == "unauthorized"


async def test_input_checks_refuse_what_would_break_the_garden(hass: HomeAssistant, garden) -> None:
    from homeassistant.exceptions import ServiceValidationError

    entry, _calls = garden
    runtime = entry.runtime_data
    data = runtime.repo.data
    # a task change that is refused changes nothing
    task = next(iter(data.tasks))
    title = task.title
    with pytest.raises(ServiceValidationError):
        operations.op_update_task(runtime, task.id, {"title": "Changed", "priority": "nonsense"})
    assert task.title == title
    # rewriting the text of a generated task keeps it through the next recalculation
    operations.op_update_task(runtime, task.id, {"title": "Mijn titel"})
    assert task.text_modified and task.title == "Mijn titel"
    # NaN and infinity never get in
    planting = data.plantings[0]
    for bad in ("NaN", "Infinity", -5):
        with pytest.raises(ServiceValidationError):
            operations.op_update_planting(runtime, planting.id, {"width_cm": bad})
    with pytest.raises(ServiceValidationError):
        operations.op_log_harvest(runtime, {"plant": planting.plant_id, "kg": "NaN"})
    with pytest.raises(ServiceValidationError):
        operations.op_log_harvest(runtime, {"plant": planting.plant_id, "kg": "Infinity"})
    # recipes of the cook's own: too long is refused, not cut off
    with pytest.raises(ServiceValidationError):
        operations._cookbook_changes({"steps": ["x"] * 31})
    with pytest.raises(ServiceValidationError):
        operations._cookbook_changes({"ingredients": [{"name": "a"}] * 41})
    assert len(operations._cookbook_changes({"steps": ["x"] * 30})["steps"]) == 30


async def test_a_plant_a_set_aside_plan_needs_cannot_be_deleted(hass: HomeAssistant, garden) -> None:
    from dataclasses import replace

    from homeassistant.exceptions import ServiceValidationError

    from custom_components.garden_manager.engine.models import ArchivedPlan
    from custom_components.garden_manager.engine.serde import to_dict

    entry, _calls = garden
    runtime = entry.runtime_data
    data = runtime.repo.data
    raw = {**to_dict(runtime.repo.db.get("tomato")), "id": "my_tomato", "source": "custom"}
    operations.op_save_plant(runtime, raw, "custom")
    planting = replace(data.plantings[0], id="pz", plant_id="my_tomato")
    data.archived_plans.append(ArchivedPlan(id="ap9", name="Old", season=2024, plantings=[planting]))
    with pytest.raises(ServiceValidationError):
        operations.op_delete_plant(runtime, "my_tomato")  # only a plan set aside still needs it
    data.archived_plans.clear()
    operations.op_delete_plant(runtime, "my_tomato")
    assert runtime.repo.db.get("my_tomato") is None


async def test_text_the_cook_rewrote_survives_recalculation(hass: HomeAssistant, garden) -> None:
    entry, _calls = garden
    runtime = entry.runtime_data
    task = next(t for t in runtime.repo.data.tasks if t.title_key)
    operations.op_update_task(runtime, task.id, {"title": "Mijn titel", "description": "Mijn tekst"})
    await runtime.coordinator.async_refresh()
    await hass.async_block_till_done()
    same = runtime.repo.data.task(task.id)
    assert same is not None and same.title == "Mijn titel" and same.description == "Mijn tekst"


async def test_digest_carries_a_changing_saying_unless_switched_off(hass: HomeAssistant, garden) -> None:
    from homeassistant.util import dt as dt_util

    from custom_components.garden_manager.engine.models import Task, TaskType

    entry, _calls = garden
    runtime = entry.runtime_data
    repo = runtime.repo
    sent: list[dict[str, Any]] = []

    async def phone(call: ServiceCall) -> None:
        sent.append(dict(call.data))

    hass.services.async_register("notify", "mobile_app_phone", phone)
    repo.data.settings.notifications.notify_services = ["notify.mobile_app_phone"]
    repo.data.tasks = [Task("only", TaskType.WEED, "Wieden", dt_util.now().date())]
    await runtime.notifier.async_send_digest(runtime.coordinator.data)
    await hass.async_block_till_done()
    assert "🌱" in sent[-1]["message"]

    repo.data.notified.clear()
    repo.data.settings.slogans = False
    await runtime.notifier.async_send_digest(runtime.coordinator.data)
    await hass.async_block_till_done()
    assert "🌱" not in sent[-1]["message"]
