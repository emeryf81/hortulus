"""The 2.1 run-time rules: water factor, water source and frost heating."""

from __future__ import annotations

from datetime import date, timedelta

from custom_components.garden_manager.engine import adaptive
from custom_components.garden_manager.engine.models import (
    GardenBed,
    GardenSettings,
    IrrigationSettings,
    Microclimate,
    Zone,
    ZoneType,
)


def _bed() -> GardenBed:
    return GardenBed(id="b", name="Bed", zone_id="z", width_cm=200, length_cm=100)


def test_a_bed_that_soaks_up_less_than_expected_gets_more_water():
    bed = _bed()
    settings = GardenSettings()
    expected = adaptive.expected_rise(10, 200)  # 10 mm in a 20 cm root zone = 5 %-points
    assert expected == 5.0
    assert adaptive.learn_water_factor(bed, expected, 2.5)  # only half of it showed up
    assert adaptive.water_factor(settings, bed) == 1.0  # one observation is not enough yet
    assert adaptive.learn_water_factor(bed, expected, 2.5)
    assert 1.0 < adaptive.water_factor(settings, bed) <= adaptive.FACTOR_MAX
    settings.adaptive_irrigation = False
    assert adaptive.water_factor(settings, bed) == 1.0


def test_tiny_rises_and_dry_readings_are_handled():
    bed = _bed()
    assert not adaptive.learn_water_factor(bed, 1.0, 0.0)  # too little water to tell
    assert bed.water_factor_runs == 0
    assert adaptive.learn_water_factor(bed, 5.0, 0.0)  # nothing arrived at all: capped, not infinite
    assert bed.water_factor <= adaptive.FACTOR_MAX
    for _ in range(20):
        adaptive.learn_water_factor(bed, 5.0, 50.0)  # a sensor that jumps far too much
    assert bed.water_factor >= adaptive.FACTOR_MIN


def test_rain_water_first_then_mains_or_wait():
    cfg = IrrigationSettings(pump_entity="switch.mains", butt_pump_entity="switch.butt", butt_min_pct=10,
                             pump_power_w=800, butt_pump_power_w=300)  # fmt: skip
    assert adaptive.choose_water(cfg, 60).water == "rain"
    assert adaptive.choose_water(cfg, 60).pump == "switch.butt"
    assert adaptive.choose_water(cfg, None).water == "rain"  # no level sensor: trust the butt pump
    low = adaptive.choose_water(cfg, 8)
    assert (low.water, low.pump, low.power_w) == ("mains", "switch.mains", 800)
    cfg.butt_fallback = False
    assert adaptive.choose_water(cfg, 8).water is None
    plain = adaptive.choose_water(IrrigationSettings(), 50)
    assert (plain.water, plain.pump) == ("mains", None)
    assert adaptive.pump_kwh(30, 600) == 0.3


def test_heater_hysteresis_and_weekly_budget():
    zone = Zone(id="z", name="Kas", type=ZoneType.GREENHOUSE, microclimate=Microclimate(min_heating_temp_c=4),
                heater_entity="switch.heater", heater_power_w=2000, heater_budget_kwh_week=3)  # fmt: skip
    day = date(2026, 1, 12)
    assert adaptive.heater_wanted(zone, 3.0, False, day) is True
    assert adaptive.heater_wanted(zone, 4.5, True, day) is True  # inside the band: stays on
    assert adaptive.heater_wanted(zone, 4.5, False, day) is False  # ... and stays off
    assert adaptive.heater_wanted(zone, 5.5, True, day) is False
    assert adaptive.heater_wanted(zone, None, True, day) is None  # no reading: leave it alone
    assert adaptive.book_heater(zone, day, 1.0) == 2.0
    assert adaptive.heater_budget_left(zone, day) == 1.0
    adaptive.book_heater(zone, day, 0.5)
    assert adaptive.heater_wanted(zone, -3.0, True, day) is False  # budget used up: off, however cold
    assert adaptive.heater_wanted(zone, -3.0, False, date(2026, 1, 19)) is True  # a new week
    for week in range(20):
        adaptive.book_heater(zone, date(2026, 3, 2) + timedelta(weeks=week), 0.1)
    assert len(zone.heater_kwh) <= adaptive.KEEP_WEEKS
