"""Regions/seasons, watering, migrations and plant database integrity."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.garden_manager.engine.migrations import (
    STORAGE_MINOR_VERSION,
    MigrationError,
    migrate,
)
from custom_components.garden_manager.engine.models import (
    GardenBed,
    GardenData,
    Hemisphere,
    IrrigationAction,
    Level,
    MoistureStatus,
    RegionProfile,
    SoilType,
    Zone,
    ZoneType,
)
from custom_components.garden_manager.engine.planio import PlanImportError, export_plan, import_plan
from custom_components.garden_manager.engine.region import (
    parse_mmdd,
    resolve_profile,
    season_anchors,
    season_for_date,
)
from custom_components.garden_manager.engine.serde import from_dict, to_dict
from custom_components.garden_manager.engine.succession import expand_succession
from custom_components.garden_manager.engine.watering import recommend_irrigation
from custom_components.garden_manager.engine.weather import DailyOutlook, et0_hargreaves


# --------------------------------------------------------------------------- #
# Region
# --------------------------------------------------------------------------- #
def test_leap_day_frost_date_resolves_in_common_years():
    assert parse_mmdd(2028, "02-29") == date(2028, 2, 29)
    assert parse_mmdd(2026, "02-29") == date(2026, 2, 28)


def test_southern_hemisphere_season_spans_new_year():
    south = RegionProfile(hemisphere=Hemisphere.SOUTH, mode="custom", last_frost="09-15", first_frost="05-15")
    anchors = season_anchors(south, 2026)
    assert anchors.last_frost == date(2026, 9, 15)
    assert anchors.first_frost == date(2027, 5, 15)
    assert season_for_date(south, date(2027, 2, 1)) == 2026
    assert season_for_date(south, date(2026, 8, 1)) == 2026


def test_usda_zone_shifts_six_months_on_southern_hemisphere():
    north = resolve_profile(RegionProfile(mode="usda", hardiness_zone="6b"))
    south = resolve_profile(RegionProfile(mode="usda", hardiness_zone="6b", hemisphere=Hemisphere.SOUTH))
    assert (north.last_frost, north.first_frost) == ("04-21", "10-21")
    assert (south.last_frost, south.first_frost) == ("10-21", "04-21")


def test_frost_free_zone():
    profile = resolve_profile(RegionProfile(mode="usda", hardiness_zone="11a"))
    assert profile.frost_free
    assert season_anchors(profile, 2026).frost_free


# --------------------------------------------------------------------------- #
# Watering
# --------------------------------------------------------------------------- #
BED = GardenBed("b", "Bed 1", "z", width_cm=200, length_cm=100, soil=SoilType.LOAM, irrigation_flow_lpm=4.0)
OUTDOOR = Zone("z", "Garden")
GREENHOUSE = Zone("g", "GH", ZoneType.GREENHOUSE)
DRY_DAY = [DailyOutlook(date(2026, 6, 1), 12, 26, 0.0, 4.5), DailyOutlook(date(2026, 6, 2), 13, 27, 0.0, 4.8)]
RAIN_DAY = [DailyOutlook(date(2026, 6, 1), 12, 18, 15.0, 2.5), DailyOutlook(date(2026, 6, 2), 11, 17, 6.0, 2.4)]


def test_dry_bed_gets_water_in_mm_litres_and_minutes():
    rec = recommend_irrigation(BED, OUTDOOR, 22.0, [Level.HIGH, Level.MEDIUM], DRY_DAY)
    assert rec.status is MoistureStatus.DRY and rec.action is IrrigationAction.WATER
    # deficit (46.5 - 22)% of 200 mm = 49 mm, capped at 20 mm per session
    assert rec.amount_mm == 20.0
    assert rec.liters == 40.0  # 20 mm x 2 m²
    assert rec.duration_min == 10.0  # 40 L / 4 L/min
    assert rec.priority.value == "high"


def test_rain_forecast_skips_watering_outdoors_but_not_in_greenhouse():
    rec = recommend_irrigation(BED, OUTDOOR, 29.0, [Level.MEDIUM], RAIN_DAY)
    assert rec.status is MoistureStatus.SLIGHTLY_DRY
    assert rec.action is IrrigationAction.SKIP_RAIN_EXPECTED
    inside = recommend_irrigation(BED, GREENHOUSE, 29.0, [Level.MEDIUM], RAIN_DAY)
    assert inside.action is IrrigationAction.WATER and inside.rain_24h_mm == 0


def test_sandy_soil_shifts_thresholds():
    sandy = GardenBed("s", "Sandy", "z", soil=SoilType.SANDY)
    assert recommend_irrigation(sandy, OUTDOOR, 26.0, [Level.MEDIUM], DRY_DAY).status is MoistureStatus.OPTIMAL
    assert recommend_irrigation(BED, OUTDOOR, 26.0, [Level.MEDIUM], DRY_DAY).status is MoistureStatus.SLIGHTLY_DRY


def test_missing_sensor_uses_water_balance():
    rec = recommend_irrigation(BED, OUTDOOR, None, [Level.HIGH], DRY_DAY)
    assert rec.action is IrrigationAction.CHECK_MANUALLY and rec.confidence == "low"
    assert recommend_irrigation(BED, OUTDOOR, None, [Level.HIGH], RAIN_DAY).action is IrrigationAction.NONE


def test_empty_bed_needs_no_water():
    assert recommend_irrigation(BED, OUTDOOR, 10.0, [], DRY_DAY).action is IrrigationAction.NONE


def test_et0_is_plausible_and_works_on_both_hemispheres():
    summer_nl = et0_hargreaves(12, 26, 52.0, date(2026, 6, 21))
    winter_nl = et0_hargreaves(0, 6, 52.0, date(2026, 12, 21))
    summer_south = et0_hargreaves(12, 26, -37.8, date(2026, 12, 21))
    assert 4.0 < summer_nl < 6.5 and winter_nl < 1.0 and 4.0 < summer_south < 7.0
    assert et0_hargreaves(5, 10, 78.0, date(2026, 12, 21)) == 0.0  # polar night


# --------------------------------------------------------------------------- #
# Migrations & import/export
# --------------------------------------------------------------------------- #
def test_migrates_legacy_document():
    legacy = {
        "settings": {"notify_service": "notify.mobile_app_phone"},
        "beds": [{"id": "b1", "name": "Pot", "zone_id": "z", "shape": "circle"}],
        "plantings": [{"id": "p1", "plant_id": "basil", "bed_id": "b1", "season": 2025}],
        "tasks": [
            {
                "id": "t1",
                "type": "water",
                "title": "Water",
                "due": "2025-06-01",
                "notes": ["done quickly"],
                "created_at": "2025-06-01T08:00:00+02:00",
            }
        ],
    }
    doc = migrate(legacy, 1, 1)
    assert doc["beds"][0]["kind"] == "container" and "shape" not in doc["beds"][0]
    assert doc["plantings"][0]["succession_index"] == 0
    assert doc["tasks"][0]["notes"][0]["text"] == "done quickly"
    assert doc["settings"]["notifications"]["notify_services"] == ["notify.mobile_app_phone"]
    assert doc["climate_log"] == [] and doc["notified"] == {}
    data = from_dict(GardenData, doc)  # and it loads
    assert data.tasks[0].notes[0].text == "done quickly"
    assert doc["layout_season"] is None and doc["layouts"] == {}
    assert doc["plantings"][0]["last_season"] is None
    assert doc["archived_plans"] == []
    assert doc["sensor_log"] == [] and doc["climate_months"] == [] and doc["frost_years"] == {}
    assert STORAGE_MINOR_VERSION == 8


def test_future_major_version_is_rejected():
    with pytest.raises(MigrationError):
        migrate({}, 2, 1)


def test_export_import_roundtrip(garden, make_planting):
    from datetime import datetime

    garden.plantings = [make_planting("carrot")]
    doc = export_plan(garden, now=datetime(2026, 1, 1))
    fresh = GardenData()
    counts = import_plan(fresh, doc, "replace")
    assert counts["beds"] == 2 and to_dict(fresh.plantings) == to_dict(garden.plantings)
    doc["beds"][0]["zone_id"] = "nope"
    with pytest.raises(PlanImportError):
        import_plan(GardenData(), doc, "replace")


def test_export_import_brings_the_whole_garden_map(garden):
    """Paths, sheds, trees and the per-season plans come along, not only zones and beds."""
    from datetime import datetime
    import json

    from custom_components.garden_manager.engine.models import Feature, FeatureType, GardenLayout

    garden.features = [
        Feature("ft_path", "Pad", FeatureType.PATH, 0, 300, 1210, 60),
        Feature("ft_shed", "Schuur", FeatureType.SHED, -300, 0, 200, 150),
    ]
    garden.layouts = {
        "2025": GardenLayout(zones=list(garden.zones), beds=list(garden.beds), features=garden.features[:1])
    }
    garden.layout_season = 2026
    doc = json.loads(json.dumps(export_plan(garden, now=datetime(2026, 1, 1))))  # through a real file

    fresh = GardenData()
    counts = import_plan(fresh, doc, "replace")
    assert counts["features"] == 2 and counts["layouts"] == 1
    assert [(f.id, f.type, f.x_cm, f.y_cm, f.width_cm, f.length_cm) for f in fresh.features] == [
        ("ft_path", FeatureType.PATH, 0, 300, 1210, 60),
        ("ft_shed", FeatureType.SHED, -300, 0, 200, 150),
    ]
    assert [f.id for f in fresh.layouts["2025"].features] == ["ft_path"] and fresh.layout_season == 2026

    # merge keeps elements that are not in the file; an old file without elements touches none
    fresh.features.append(Feature("ft_tree", "Appel", FeatureType.TREE, 500, 500, 300, 300))
    import_plan(fresh, doc, "merge")
    assert {f.id for f in fresh.features} == {"ft_path", "ft_shed", "ft_tree"}
    doc.pop("features")
    import_plan(fresh, doc, "merge")
    assert len(fresh.features) == 3

    # merging a season both gardens have keeps the stored items; the active season stays
    fresh.layouts["2025"].features.append(Feature("ft_pond", "Vijver", FeatureType.POND, 0, 0, 100, 100))
    fresh.layout_season = 2027
    import_plan(fresh, doc, "merge")
    assert {f.id for f in fresh.layouts["2025"].features} == {"ft_path", "ft_pond"}
    assert fresh.layout_season == 2027


def test_import_without_soil_tests_keeps_stored_ones(garden):
    from datetime import date, datetime

    from custom_components.garden_manager.engine.models import SoilTest

    doc = export_plan(garden, now=datetime(2026, 1, 1))
    for bed in doc["beds"]:
        bed.pop("soil_tests", None)  # an older or hand-written plan file
    garden.beds[0].soil_tests = [SoilTest(date(2026, 3, 1), ph=6.2)]
    import_plan(garden, doc, "replace")
    assert garden.beds[0].soil_tests[0].ph == 6.2
    doc["beds"][0]["soil_tests"] = []  # an explicit empty list does replace them
    import_plan(garden, doc, "replace")
    assert garden.beds[0].soil_tests == []


def test_succession_splits_bed_and_stays_in_window(garden, db, make_planting):
    base = make_planting("lettuce", width_cm=150, length_cm=30, sow_date=date(2026, 7, 1))
    anchors = season_anchors(garden.settings.region, 2026)
    series, dropped = expand_succession(base, db.get("lettuce"), anchors, garden.zone("outdoor"), count=4)
    # lettuce spring window ends LF + 10 w = 6 July; autumn window ends FF-6w = mid Sept
    assert [p.sow_date for p in series][:2] == [date(2026, 7, 1), date(2026, 7, 22)]
    assert all(p.width_cm == 37.5 for p in series)
    assert len({p.succession_group for p in series}) == 1
    assert len(series) + dropped == 4


# --------------------------------------------------------------------------- #
# Plant database integrity
# --------------------------------------------------------------------------- #
def test_starter_database_integrity(db):
    plants = db.all()
    assert len(plants) >= 130
    categories = {p.category.value for p in plants}
    assert categories == {"vegetable", "herb", "fruit", "flower"}
    assert sum(1 for p in plants if p.category.value == "herb") >= 50
    ids = {p.id for p in plants}
    for plant in plants:
        assert plant.names.get("en") and plant.names.get("nl"), plant.id
        assert plant.spacing_cm > 0 and plant.row_spacing_cm > 0
        assert plant.days_to_maturity[0] <= plant.days_to_maturity[1]
        assert plant.sowing.indoor_sow or plant.sowing.direct_sow or plant.sowing.transplant, plant.id
        if plant.sowing.indoor_sow:
            assert plant.sowing.transplant, f"{plant.id}: indoor sowing needs a transplant window"
        for link in plant.companions:
            assert link.plant in ids, f"{plant.id} -> unknown companion {link.plant}"
            assert link.reason.get("en") and link.reason.get("nl")


def test_overrides_and_search(db):
    from custom_components.garden_manager.engine.plantdb import PlantDatabase, load_builtin_json

    custom_db = PlantDatabase(
        load_builtin_json(), overrides={"tomato": {"spacing_cm": 60, "names": {"nl": "Trostomaat"}}}
    )
    tomato = custom_db.get("tomato")
    assert tomato.spacing_cm == 60 and tomato.names == {"en": "Tomato", "nl": "Trostomaat", "fr": "Tomate"}
    assert tomato.source == "override"
    assert {p.id for p in db.search("tomaat")} == {"tomato", "cherry_tomato", "beefsteak_tomato"}
    assert {"pea", "bush_bean", "broad_bean", "runner_bean"} <= {p.id for p in db.search(family="Fabaceae")}
    assert [p.id for p in db.search("bieslook")] == ["chives", "garlic_chives"]


def test_import_takes_old_seasons_and_tasks_along(garden, make_planting):
    """A crop in last year's plan whose bed is gone now, and the tasks of the file, both come back."""
    import dataclasses
    from datetime import date, datetime
    import json

    from custom_components.garden_manager.engine.models import GardenLayout, Task, TaskType

    old_bed = dataclasses.replace(garden.beds[0], id="bed_old", name="Old bed")
    garden.layouts = {"2025": GardenLayout(zones=list(garden.zones), beds=[old_bed])}
    garden.layout_season = 2026
    garden.plantings = [make_planting("carrot", "bed_old", 2025)]
    garden.tasks = [Task(id="t1", title="Weed", type=TaskType.WEED, due=date(2026, 5, 1))]
    doc = json.loads(json.dumps(export_plan(garden, include_tasks=True, now=datetime(2026, 1, 1))))
    fresh = GardenData()
    counts = import_plan(fresh, doc, "replace")
    assert counts["plantings"] == 1 and counts["tasks"] == 1 and [t.id for t in fresh.tasks] == ["t1"]
