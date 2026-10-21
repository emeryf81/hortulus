"""Phase-2 agronomy: ET0, GDD/phenology, water balance, fertiliser, disease, irrigation safety."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.garden_manager.engine.analysis import analyze
from custom_components.garden_manager.engine.fertilizer import (
    bed_fertilizer_plan,
    feed_dose,
    nutrient_balance,
)
from custom_components.garden_manager.engine.irrigation import plan_irrigation
from custom_components.garden_manager.engine.models import (
    ClimateDay,
    ForecastPoint,
    IrrigationAction,
    Planting,
    PlantingStatus,
    RiskLevel,
    SoilType,
    WaterBalance,
    WeatherSnapshot,
)
from custom_components.garden_manager.engine.phenology import phenology, stage_kc
from custom_components.garden_manager.engine.region import season_anchors
from custom_components.garden_manager.engine.schedule import planting_timeline
from custom_components.garden_manager.engine.watering import (
    IrrigationRecommendation,
    total_available_water,
    update_water_balance,
)
from custom_components.garden_manager.engine.weather import (
    FrostAssessment,
    accumulate_gdd,
    assess_disease,
    daily_outlook,
    et0_hargreaves,
    et0_penman_monteith,
    gdd_for_day,
)

TZ = ZoneInfo("Europe/Amsterdam")


# --------------------------------------------------------------------------- #
# ET0
# --------------------------------------------------------------------------- #
def test_penman_monteith_matches_fao56_example_18():
    """Brussels, 6 July: FAO-56 gives ET0 = 3.9 mm/day."""
    et0 = et0_penman_monteith(
        12.3, 21.5, 50.8, date(2026, 7, 6), rh_min=63, rh_max=84, wind_kmh_10m=10.0,
        sunshine_fraction=9.25 / 16.1, elevation_m=100,
    )  # fmt: skip
    assert et0 == pytest.approx(3.9, abs=0.1)


def test_penman_monteith_needs_humidity_and_wind():
    assert et0_penman_monteith(12.0, 22.0, 52.0, date(2026, 7, 6)) is None


def test_daily_outlook_falls_back_to_hargreaves_without_humidity():
    now = datetime(2026, 7, 6, 0, 0, tzinfo=TZ)
    hourly = [
        ForecastPoint(at=now + timedelta(hours=h), temperature=12 + 10 * (1 - abs(h - 14) / 14), precipitation=0.0)
        for h in range(48)
    ]
    out = daily_outlook(WeatherSnapshot(available=True, hourly=hourly), now, TZ, 52.0)
    assert out[0].et0_method == "hargreaves"
    assert out[0].et0_mm == pytest.approx(et0_hargreaves(out[0].tmin, out[0].tmax, 52.0, out[0].day), abs=0.01)

    for p in hourly:
        p.humidity, p.wind_speed, p.cloud_coverage = 70.0, 12.0, 30.0
    out = daily_outlook(WeatherSnapshot(available=True, hourly=hourly), now, TZ, 52.0)
    assert out[0].et0_method == "penman_monteith"
    assert 2.0 < out[0].et0_mm < 7.0


# --------------------------------------------------------------------------- #
# GDD and phenology
# --------------------------------------------------------------------------- #
def test_gdd_modified_average_clamps_to_base_and_cap():
    assert gdd_for_day(5.0, 15.0, 10.0) == pytest.approx(2.5)  # min raised to base
    assert gdd_for_day(20.0, 40.0, 10.0) == pytest.approx(15.0)  # max capped at 30
    assert gdd_for_day(2.0, 8.0, 10.0) == 0.0


def test_gdd_accumulates_only_logged_days_in_range():
    log = [ClimateDay(date(2026, 5, d), 10.0, 20.0) for d in range(1, 11)] + [ClimateDay(date(2026, 5, 11))]
    gdd, counted = accumulate_gdd(log, date(2026, 5, 3), date(2026, 5, 11), base=10.0)
    assert counted == 8
    assert gdd == pytest.approx(8 * 5.0)


def _courgette_timeline(db, garden):
    plant = db.get("courgette")
    planting = Planting("pc", "courgette", "bed_1", 2026, status=PlantingStatus.TRANSPLANTED)
    planting.transplanted_on = date(2026, 5, 20)
    anchors = season_anchors(garden.settings.region, 2026)
    tl = planting_timeline(planting, plant, anchors, garden.zone("outdoor"), date(2026, 6, 10))
    return plant, tl


def test_warm_weather_brings_harvest_forward(db, garden):
    plant, tl = _courgette_timeline(db, garden)
    today = tl.in_ground + timedelta(days=20)
    days = [tl.in_ground + timedelta(days=i) for i in range(21)]
    warm = [ClimateDay(d, 16.0, 30.0) for d in days]
    cold = [ClimateDay(d, 8.0, 17.0) for d in days]
    hot = phenology("pc", plant, tl, today, warm)
    chilly = phenology("pc", plant, tl, today, cold)
    assert hot.gdd > chilly.gdd
    assert hot.harvest_estimate < chilly.harvest_estimate
    # Never more than three weeks away from the calendar estimate.
    assert abs((chilly.harvest_estimate - tl.harvest_start).days) <= 21
    assert hot.stage in ("vegetative", "flowering", "ripening", "harvest")


def test_phenology_without_climate_log_keeps_calendar(db, garden):
    plant, tl = _courgette_timeline(db, garden)
    info = phenology("pc", plant, tl, tl.in_ground + timedelta(days=10), [])
    assert info.harvest_estimate is None
    assert info.stage in {"establishing", "vegetative"}


def test_stage_kc_follows_fao_curve(db, garden):
    plant, tl = _courgette_timeline(db, garden)
    kc_ini, kc_mid, kc_end = plant.kc
    total = (tl.harvest_end - tl.in_ground).days
    assert stage_kc(plant, tl, tl.in_ground) == kc_ini
    assert stage_kc(plant, tl, tl.in_ground + timedelta(days=round(total * 0.6))) == kc_mid
    assert stage_kc(plant, tl, tl.harvest_end) == pytest.approx(kc_end, abs=0.01)
    assert stage_kc(plant, tl, tl.in_ground - timedelta(days=1)) == 0.0


# --------------------------------------------------------------------------- #
# Water balance
# --------------------------------------------------------------------------- #
def test_water_balance_bucket():
    taw = total_available_water(SoilType.LOAM, 300)
    assert taw == pytest.approx(48.0)
    d = update_water_balance(10.0, et0_mm=4.0, kc=1.0, rain_mm=0.0, irrigation_mm=0.0, taw_mm=taw)
    assert d == 14.0
    # Rain refills (80 % effective), never above field capacity.
    assert update_water_balance(d, et0_mm=1.0, kc=1.0, rain_mm=30.0, irrigation_mm=0.0, taw_mm=taw) == 0.0
    # Greenhouse: no rain, reduced ET.
    assert (
        update_water_balance(0.0, et0_mm=4.0, kc=1.0, rain_mm=30.0, irrigation_mm=0.0, taw_mm=taw, enclosed=True) == 2.8
    )
    assert update_water_balance(47.0, et0_mm=5.0, kc=1.2, rain_mm=0, irrigation_mm=0, taw_mm=taw) == taw


def test_bucket_drives_irrigation_without_sensor(garden, db, make_planting):
    garden.beds[0].sensors.soil_moisture = None
    garden.plantings = [
        make_planting("lettuce", "bed_1", 2026, status=PlantingStatus.SOWN, width_cm=200, length_cm=100)
    ]
    now = datetime(2026, 6, 10, 8, 0, tzinfo=TZ)
    garden.water_balance["bed_1"] = WaterBalance(date(2026, 6, 9), 30.0)
    result = analyze(garden, db, WeatherSnapshot(), {}, now=now, tz=TZ)
    rec = result.beds["bed_1"].irrigation
    assert rec.action is IrrigationAction.WATER
    assert "water_balance_depleted" in rec.reasons
    assert result.beds["bed_1"].taw_mm is not None


def test_moisture_sensor_calibrates_the_bucket_and_learns_how_fast_a_bed_dries(garden, db, make_planting):
    from custom_components.garden_manager.engine.waterbalance import advance_water_balance, sensor_depletion

    garden.plantings = [
        make_planting("lettuce", "bed_1", 2026, status=PlantingStatus.SOWN, width_cm=200, length_cm=100)
    ]
    day0 = date(2026, 6, 10)
    timelines = analyze(garden, db, WeatherSnapshot(), {}, now=datetime(2026, 6, 10, 8, tzinfo=TZ), tz=TZ).timelines
    garden.water_balance["bed_1"] = WaterBalance(day0, 5.0)

    def advance(today: date, moisture: float | None) -> WaterBalance:
        advance_water_balance(garden, db, timelines, today, latitude=51.0, tz=TZ, moisture={"bed_1": moisture})
        return garden.water_balance["bed_1"]

    wb = advance(day0, 40.0)  # first reading sets the bucket
    assert wb.calibrated_on == day0 and wb.depletion_mm == wb.calibrated_mm and wb.et_factor == 1.0
    first = wb.calibrated_mm
    wb_again = advance(day0, 10.0)  # once a day only
    assert wb_again.calibrated_mm == first

    garden.climate_log = [ClimateDay(day0 + timedelta(days=i), tmin=14.0, tmax=28.0, rain_mm=0.0) for i in range(4)]
    taw = total_available_water(garden.beds[0].soil, db.get("lettuce").root_depth_cm * 10)
    start = wb.calibrated_mm
    wb = advance(day0 + timedelta(days=4), 18.0)  # four hot, dry days: the sensor fell faster than modelled
    measured = sensor_depletion(18.0, taw, garden.beds[0], [db.get("lettuce").water_needs])
    assert wb.depletion_mm == measured and measured > start
    assert wb.et_factor > 1.0 and wb.model_et_mm == 0.0

    # rain in between: nothing is learned from that stretch
    factor = wb.et_factor
    garden.climate_log += [ClimateDay(day0 + timedelta(days=i), tmin=14.0, tmax=24.0, rain_mm=12.0) for i in (4, 5)]
    wb = advance(day0 + timedelta(days=6), 35.0)
    assert wb.et_factor == factor

    # rain logged on a day without temperatures stops learning too
    garden.climate_log += [ClimateDay(day0 + timedelta(days=6), tmin=None, tmax=None, rain_mm=15.0)]
    garden.climate_log += [ClimateDay(day0 + timedelta(days=i), tmin=14.0, tmax=28.0, rain_mm=0.0) for i in (7, 8, 9)]
    wb = advance(day0 + timedelta(days=10), 15.0)
    assert wb.et_factor == factor


def test_greenhouse_bed_learns_nothing_when_the_sensor_matches_the_model(garden, db, make_planting):
    """The model's lower ET under glass is part of the baseline, not something to learn again."""
    from custom_components.garden_manager.engine.waterbalance import advance_water_balance
    from custom_components.garden_manager.engine.watering import ENCLOSED_ET_FACTOR
    from custom_components.garden_manager.engine.weather import et0_hargreaves

    garden.plantings = [
        make_planting("lettuce", "gh_bed", 2026, status=PlantingStatus.SOWN, width_cm=200, length_cm=100)
    ]
    day0 = date(2026, 6, 10)
    timelines = analyze(garden, db, WeatherSnapshot(), {}, now=datetime(2026, 6, 10, 8, tzinfo=TZ), tz=TZ).timelines
    garden.water_balance["gh_bed"] = WaterBalance(day0, 5.0, calibrated_on=day0 - timedelta(days=1), calibrated_mm=5.0)
    garden.climate_log = [ClimateDay(day0, tmin=14.0, tmax=28.0, rain_mm=0.0)]
    advance_water_balance(garden, db, timelines, day0 + timedelta(days=1), latitude=51.0, tz=TZ)
    wb = garden.water_balance["gh_bed"]
    modelled = wb.depletion_mm - 5.0  # what the bucket booked for that day
    assert wb.model_et_mm == pytest.approx(modelled, abs=0.15)
    assert wb.model_et_mm < et0_hargreaves(14.0, 28.0, 51.0, day0) * 1.0 * ENCLOSED_ET_FACTOR + 0.1


def test_water_given_on_a_day_without_temperatures_still_counts(garden, db, make_planting):
    """No weather that day: no drying is known, but the watering is booked."""
    from custom_components.garden_manager.engine.models import IrrigationEvent
    from custom_components.garden_manager.engine.waterbalance import advance_water_balance

    garden.plantings = [make_planting("lettuce", "bed_1", 2026, status=PlantingStatus.SOWN)]
    day0 = date(2026, 6, 10)
    timelines = analyze(garden, db, WeatherSnapshot(), {}, now=datetime(2026, 6, 10, 8, tzinfo=TZ), tz=TZ).timelines
    garden.water_balance["bed_1"] = WaterBalance(day0, 20.0)
    garden.climate_log = []
    garden.irrigation_log = [IrrigationEvent("bed_1", datetime(2026, 6, 10, 9, tzinfo=TZ), 15.0, 30.0, source="manual")]
    advance_water_balance(garden, db, timelines, day0 + timedelta(days=1), latitude=51.0, tz=TZ)
    assert garden.water_balance["bed_1"].depletion_mm == pytest.approx(5.0, abs=0.2)


# --------------------------------------------------------------------------- #
# Fertiliser
# --------------------------------------------------------------------------- #
def test_fertilizer_plan_scales_with_demand_and_area(db):
    heavy = bed_fertilizer_plan(2.0, [db.get("tomato")])
    beans = bed_fertilizer_plan(2.0, [db.get("bush_bean")])
    assert heavy.compost_kg == 10.0 and heavy.base_fertilizer_g == 160
    assert beans.compost_kg == 1.0 and beans.base_fertilizer_g == 0
    assert bed_fertilizer_plan(1.0, [db.get("kale")]).lime_check


def test_feed_dose_for_fruiting_crop(db):
    dose = feed_dose(db.get("tomato"), 6, 1.2)
    assert dose.liquid_liters == 9.0
    assert dose.concentrate_ml == 90


def test_nutrient_balance_index(db):
    crops = [db.get("tomato")]
    assert nutrient_balance(crops).status == "unknown"
    ok = nutrient_balance(crops, n=40, p=30, k=200)
    assert ok.index == 100 and ok.status == "balanced"
    low = nutrient_balance(crops, n=5, p=30, k=200)
    assert low.status == "deficient" and "n" in low.deficits and low.index < 80
    salty = nutrient_balance(crops, ec=4.5)
    assert salty.source == "ec" and salty.status == "excess"


# --------------------------------------------------------------------------- #
# Disease risk
# --------------------------------------------------------------------------- #
def _humid_weather(now: datetime, humidity: float, tmin: float) -> WeatherSnapshot:
    hourly = [
        ForecastPoint(at=now + timedelta(hours=h), temperature=tmin + 6 * ((h % 24) > 9), humidity=humidity)
        for h in range(48)
    ]
    return WeatherSnapshot(available=True, hourly=hourly)


def test_hutton_period_is_high_blight_risk():
    now = datetime(2026, 7, 10, 0, 0, tzinfo=TZ)
    risk = assess_disease(_humid_weather(now, 95, 12), now, TZ)
    assert risk.hutton_period and risk.level == "high"
    dry = assess_disease(_humid_weather(now, 60, 12), now, TZ)
    assert dry.level == "none"


def test_two_humid_days_with_a_gap_are_no_hutton_period():
    now = datetime(2026, 7, 10, 0, 0, tzinfo=TZ)
    hourly = [
        ForecastPoint(at=now + timedelta(days=d, hours=h), temperature=14, humidity=95)
        for d in (0, 2)  # the forecast lacks the 11th
        for h in range(24)
    ]
    risk = assess_disease(WeatherSnapshot(available=True, hourly=hourly), now, TZ, horizon_hours=72)
    assert not risk.hutton_period


def test_humid_greenhouse_raises_risk():
    now = datetime(2026, 7, 10, 0, 0, tzinfo=TZ)
    risk = assess_disease(WeatherSnapshot(), now, TZ, humidity_now=93, enclosed=True)
    assert risk.level == "moderate"
    assert assess_disease(WeatherSnapshot(), now, TZ).level == "unknown"


# --------------------------------------------------------------------------- #
# Irrigation safety
# --------------------------------------------------------------------------- #
def _rec(bed_id: str, mm: float = 10.0, rain: float = 0.0) -> IrrigationRecommendation:
    return IrrigationRecommendation(bed_id, action=IrrigationAction.WATER, amount_mm=mm, rain_24h_mm=rain)


@pytest.fixture
def irrigated(garden):
    garden.settings.irrigation.mode = "auto"
    for bed in garden.beds:
        bed.irrigation_entity = f"switch.valve_{bed.id}"
        bed.irrigation_flow_lpm = 4.0
    return garden


def test_frost_lockout_blocks_outdoor_valves(irrigated):
    now = datetime(2026, 4, 10, 5, 0, tzinfo=TZ)
    frost = FrostAssessment(RiskLevel.MODERATE, 2.5, 1.0, now + timedelta(hours=2))
    plan = plan_irrigation(
        irrigated, {"bed_1": _rec("bed_1"), "gh_bed": _rec("gh_bed")}, now=now,
        frost_by_zone={"outdoor": frost}, outdoor_frost=frost, outdoor_temp=4.0, zone_air={"gh_a": 9.0},
    )  # fmt: skip
    assert plan.lockout
    assert plan.skipped["bed_1"][0] == "irrigation.skip.frost"
    # The heated greenhouse is not locked by outdoor frost.
    assert [r.bed_id for r in plan.runs] == ["gh_bed"]


def test_frost_lockout_also_applies_to_manual_runs(irrigated):
    now = datetime(2026, 4, 10, 5, 0, tzinfo=TZ)
    plan = plan_irrigation(
        irrigated, {"bed_1": _rec("bed_1")}, now=now, frost_by_zone={}, outdoor_frost=None,
        outdoor_temp=0.5, force=True, bed_ids={"bed_1"}, override_mm=5.0,
    )  # fmt: skip
    assert not plan.runs and plan.skipped["bed_1"][0] == "irrigation.skip.frost"


def test_only_if_needed_keeps_the_need_check_for_a_forced_run(irrigated):
    """A blueprint picks the moment; when the bed turned out not to need water, nothing runs."""
    now = datetime(2026, 7, 10, 5, 0, tzinfo=TZ)
    no_need = IrrigationRecommendation("bed_1", action=IrrigationAction.NONE, etc_24h_mm=3.0)
    kw = {
        "now": now,
        "frost_by_zone": {},
        "outdoor_frost": None,
        "outdoor_temp": 18.0,
        "force": True,
        "bed_ids": {"bed_1"},
    }
    assert plan_irrigation(irrigated, {"bed_1": no_need}, **kw).runs  # a manual run replaces a day of ET
    plan = plan_irrigation(irrigated, {"bed_1": no_need}, only_if_needed=True, **kw)
    assert not plan.runs and plan.skipped["bed_1"][0] == "irrigation.skip.not_needed"
    irrigated.settings.irrigation.mode = "advise"  # the mode switch is still ignored: the automation decides when
    assert plan_irrigation(irrigated, {"bed_1": _rec("bed_1")}, only_if_needed=True, **kw).runs


def test_far_away_frost_does_not_lock(irrigated):
    now = datetime(2026, 4, 10, 5, 0, tzinfo=TZ)
    frost = FrostAssessment(RiskLevel.MODERATE, 2.5, 1.0, now + timedelta(hours=30))
    plan = plan_irrigation(
        irrigated, {"bed_1": _rec("bed_1")}, now=now, frost_by_zone={"outdoor": frost},
        outdoor_frost=frost, outdoor_temp=8.0,
    )  # fmt: skip
    assert not plan.lockout and plan.runs


def test_rain_skip_and_max_runtime(irrigated):
    now = datetime(2026, 7, 10, 5, 0, tzinfo=TZ)
    irrigated.settings.irrigation.max_runtime_min = 3.0
    plan = plan_irrigation(
        irrigated, {"bed_1": _rec("bed_1", rain=5.0), "gh_bed": _rec("gh_bed", mm=20.0)}, now=now,
        frost_by_zone={}, outdoor_frost=None, outdoor_temp=18.0,
    )  # fmt: skip
    assert plan.skipped["bed_1"][0] == "irrigation.skip.rain"
    (run,) = plan.runs
    assert run.minutes == 3.0 and run.capped and run.liters == 12.0


def test_advise_mode_never_opens_valves(irrigated):
    irrigated.settings.irrigation.mode = "advise"
    now = datetime(2026, 7, 10, 5, 0, tzinfo=TZ)
    plan = plan_irrigation(
        irrigated, {"bed_1": _rec("bed_1")}, now=now, frost_by_zone={}, outdoor_frost=None, outdoor_temp=18.0
    )
    assert not plan.runs and plan.skipped["bed_1"][0] == "irrigation.skip.disabled"


def test_a_learned_water_factor_scales_the_planned_water(irrigated):
    now = datetime(2026, 7, 10, 5, 0, tzinfo=TZ)
    kw = {"now": now, "frost_by_zone": {}, "outdoor_frost": None, "outdoor_temp": 18.0}
    base = plan_irrigation(irrigated, {"bed_1": _rec("bed_1", mm=6.0)}, **kw).runs[0]
    bed = irrigated.bed("bed_1")
    bed.water_factor, bed.water_factor_runs = 1.5, 3
    more = plan_irrigation(irrigated, {"bed_1": _rec("bed_1", mm=6.0)}, **kw).runs[0]
    assert more.mm == pytest.approx(base.mm * 1.5, abs=0.1)
    fixed = plan_irrigation(irrigated, {"bed_1": _rec("bed_1")}, force=True, bed_ids={"bed_1"}, override_mm=5.0, **kw)
    assert fixed.runs[0].mm == 5.0  # a fixed amount stays what was asked
    irrigated.settings.adaptive_irrigation = False
    assert plan_irrigation(irrigated, {"bed_1": _rec("bed_1", mm=6.0)}, **kw).runs[0].mm == base.mm
