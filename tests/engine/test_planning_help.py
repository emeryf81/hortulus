"""Seeds to buy, what follows a crop, expected harvests."""

from __future__ import annotations

from datetime import date, timedelta

from custom_components.garden_manager.engine import planning
from custom_components.garden_manager.engine.models import PlantingStatus, SeedPacket, SowMethod
from custom_components.garden_manager.engine.region import season_anchors
from custom_components.garden_manager.engine.schedule import planting_timeline


def _timelines(garden, db, season, today):
    anchors = season_anchors(garden.settings.region, season)
    out = {}
    for p in garden.plantings:
        bed = garden.bed(p.bed_id)
        out[p.id] = planting_timeline(p, db.get(p.plant_id), anchors, garden.zone(bed.zone_id) if bed else None, today)
    return out


def test_seed_needs_count_plants_with_a_margin_against_the_stock(garden, db, make_planting):
    garden.layout_season = 2026
    carrots = make_planting("carrot", "bed_1", 2026, id="c", method=SowMethod.DIRECT_SOW, count=40)
    lettuce = make_planting("lettuce", "bed_1", 2026, id="l", method=SowMethod.INDOOR_SOW, count=10)
    bought = make_planting("tomato", "gh_bed", 2026, id="t", method=SowMethod.TRANSPLANT, count=4)
    done = make_planting("radish", "bed_1", 2026, id="r", count=20, status=PlantingStatus.SOWN)
    garden.plantings = [carrots, lettuce, bought, done]
    garden.seed_stock = [SeedPacket("s1", "carrot", year=2025, quantity=500, unit="seeds")]
    needs = {n.plant_id: n for n in planning.seed_needs(garden, db, 2026)}
    assert set(needs) == {"carrot", "lettuce"}  # bought plants and sown crops need no seed
    assert needs["carrot"].seeds == 80 and needs["carrot"].status == "ok"
    assert needs["lettuce"].seeds == 13 and needs["lettuce"].status == "none"
    assert needs["carrot"].to_buy == 0 and needs["lettuce"].to_buy == 13
    items = planning.seed_todo_items(list(needs.values()), db, 2026, "nl")
    assert [i["plant_id"] for i in items] == ["lettuce"]
    # the summary names only the crop (a new quantity must not add a second item); the amount is in the description
    assert items[0]["summary"] == "Zaad: Sla" and "13 zaden" in items[0]["description"]


def test_successions_follow_early_crops_without_repeating_the_family(garden, db, make_planting):
    garden.layout_season = 2026
    radish = make_planting("radish", "bed_1", 2026, id="r", width_cm=100, length_cm=30)
    garden.plantings = [radish]
    today = date(2026, 4, 1)
    tl = _timelines(garden, db, 2026, today)
    beds = planning.successions(garden, db, 2026, tl, today=today, first_frost=date(2026, 10, 25), lang="nl")
    assert beds and beds[0].bed_id == "bed_1" and beds[0].leaving == ["radish"]
    radish_family = db.get("radish").family
    assert beds[0].options and all(db.get(o["plant_id"]).family != radish_family for o in beds[0].options)


def test_harvest_forecast_spreads_the_yield_over_the_harvest_weeks(garden, db, make_planting):
    garden.layout_season = 2026
    lettuce = make_planting("lettuce", "bed_1", 2026, id="l", width_cm=100, length_cm=100)
    garden.plantings = [lettuce]
    tl = _timelines(garden, db, 2026, date(2026, 3, 1))
    fc = planning.harvest_forecast(garden, db, 2026, tl)
    total = sum(w["kg"] for w in fc["weeks"])
    assert abs(total - db.get("lettuce").yield_kg_m2) < 0.1
    assert all(date.fromisoformat(w["week"]).weekday() == 0 for w in fc["weeks"])


def test_season_report_compares_harvest_with_expectation(garden, db, make_planting):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from custom_components.garden_manager.engine.models import HarvestEntry, JournalEntry

    garden.layout_season = 2026
    lettuce = make_planting("lettuce", "bed_1", 2026, id="l", width_cm=100, length_cm=100)
    beans = make_planting("bush_bean", "bed_1", 2026, id="b", status=PlantingStatus.FAILED, notes="slakken")
    garden.plantings = [lettuce, beans]
    garden.harvest_log = [HarvestEntry("h1", date(2026, 6, 10), "lettuce", 9.0, planting_id="l")]
    tz = ZoneInfo("Europe/Brussels")
    garden.journal = [JournalEntry("j1", datetime(2026, 6, 1, 9, tzinfo=tz), "bladluis op de bonen", kind="problem")]
    report = planning.season_report(garden, db, 2026)
    crops = {c["plant_id"]: c for c in report["crops"]}
    assert crops["lettuce"]["kg"] == 9.0 and crops["lettuce"]["verdict"] in ("above", "as_expected")
    assert crops["bush_bean"]["verdict"] == "failed" and report["failed"][0]["notes"] == "slakken"
    assert report["problems"][0]["text"] == "bladluis op de bonen" and report["totals"]["failed"] == 1


def test_own_years_blend_the_yield_and_move_the_harvest_start(garden, db, make_planting):
    from custom_components.garden_manager.engine.models import HarvestEntry
    from custom_components.garden_manager.engine.records import learned_details, learned_harvest_days, learned_yields

    garden.layout_season = 2026
    book = db.get("lettuce").yield_kg_m2
    # last year: 1 m² of lettuce sown on 1 April, first harvest after 50 days, 6 kg in all
    old = make_planting("lettuce", "bed_1", 2025, id="old", width_cm=100, length_cm=100,
                        sown_on=date(2025, 4, 1), harvest_started_on=date(2025, 5, 21))  # fmt: skip
    new = make_planting("lettuce", "bed_1", 2026, id="l", width_cm=100, length_cm=100, sow_date=date(2026, 4, 1))
    garden.plantings = [old, new]
    garden.harvest_log = [HarvestEntry("h", date(2025, 6, 1), "lettuce", 6.0, planting_id="old")]
    assert learned_yields(garden) == {"lettuce": 6.0}
    assert learned_yields(garden, db) == {"lettuce": round((6.0 + book) / 2, 2)}  # the book counts as one season
    assert learned_harvest_days(garden) == {"lettuce": 50}
    assert learned_details(garden)["lettuce"] == {"kg_m2": 6.0, "seasons": 1, "first_harvest_days": 50}

    tl = _timelines(garden, db, 2026, date(2026, 3, 1))
    fc = planning.harvest_forecast(garden, db, 2026, tl)
    first = min(date.fromisoformat(w["week"]) for w in fc["weeks"] if w["by_plant"].get("lettuce"))
    assert first <= date(2026, 5, 21) <= first + timedelta(days=6)  # the week of sowing + 50 days
    assert "lettuce" in fc["learned"] and fc["learned_detail"]["lettuce"]["seasons"] == 1

    garden.settings.own_yields = False
    assert learned_yields(garden, db) == {} and learned_harvest_days(garden) == {}
