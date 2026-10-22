"""Build a realistic websocket snapshot from the real engine for the dev harness.

Usage (from the repository root, with the test requirements installed)::

    python frontend/dev/make_snapshot.py en frontend/dev/data-en.json
    python frontend/dev/make_snapshot.py nl frontend/dev/data-nl.json

The garden is the example garden from the brief (Bed 1, Greenhouse Zone A) plus a few
extra beds, frozen on 20 May 2026 with realistic sensor readings and a rainy forecast,
so every panel view has something to show (alerts, overdue tasks, a companion conflict).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.garden_manager.engine import climate, diagnose, handbook, planning, seasons  # noqa: E402
from custom_components.garden_manager.engine.advisor import advise, harvest_coverage  # noqa: E402
from custom_components.garden_manager.engine.analysis import analyze  # noqa: E402
from custom_components.garden_manager.engine.autoplan import AutoplanOptions, autoplan  # noqa: E402
from custom_components.garden_manager.engine.irrigation import plan_irrigation  # noqa: E402
from custom_components.garden_manager.engine.kitchen import economics, kitchen_report  # noqa: E402
from custom_components.garden_manager.engine.models import (  # noqa: E402
    Feature,
    FeatureType,
    GardenBed,
    GardenResources,
    HarvestEntry,
    IrrigationEvent,
    JournalEntry,
    LayoutMode,
    Planting,
    PlantingStatus,
    SeedPacket,
    SensorReading,
    SoilTest,
    SowMethod,
    WaterReading,
    WeatherSnapshot,
    Zone,
    ZoneType,
)
from custom_components.garden_manager.engine.plantdb import (  # noqa: E402
    FAMILIES,
    PlantDatabase,
    load_builtin_json,
)
from custom_components.garden_manager.engine.printout import PrintContext, PrintOptions, render_svg  # noqa: E402
from custom_components.garden_manager.engine.qa import answer as qa_answer, options as qa_options  # noqa: E402
from custom_components.garden_manager.engine.records import (  # noqa: E402
    harvest_by_year,
    harvest_summary,
    learned_yields,
    seed_report,
    water_stats,
    year_overview,
)
from custom_components.garden_manager.engine.region import season_anchors  # noqa: E402
from custom_components.garden_manager.engine.schedule import season_timeline  # noqa: E402
from custom_components.garden_manager.engine.serde import to_dict  # noqa: E402
from custom_components.garden_manager.engine.supplies import catalog, shopping_list  # noqa: E402
from custom_components.garden_manager.engine.tasks import generate_specs, merge_tasks  # noqa: E402
from custom_components.garden_manager.engine.weather import parse_forecast  # noqa: E402
from custom_components.garden_manager.seed import build_initial_data  # noqa: E402

TZ = ZoneInfo("Europe/Amsterdam")
NOW = datetime(2026, 5, 20, 8, 30, tzinfo=TZ)
ENTRY = {
    "region": {"region_mode": "preset", "hemisphere": "north", "preset": "nl_be"},
    "weather_entity": "weather.home",
    "areas": [
        {
            "name": "Bed 1",
            "type": "outdoor",
            "width_m": 2.0,
            "length_m": 1.0,
            "soil": "loam",
            "soil_moisture": "sensor.soil_moisture_bed_1",
            "soil_temperature": "sensor.soil_temp_bed_1",
        },
        {"name": "Bed 2", "type": "outdoor", "width_m": 2.4, "length_m": 1.2, "soil": "sandy"},
        {"name": "Herb pot", "type": "container", "width_m": 0.6, "length_m": 0.6},
        {
            "name": "Greenhouse Zone A",
            "type": "greenhouse",
            "width_m": 3.0,
            "length_m": 2.0,
            "air_temperature": "sensor.greenhouse_temp",
        },
    ],
    "import_example_plan": True,
}
PROGRESS = {
    "tomato": (PlantingStatus.TRANSPLANTED, date(2026, 2, 1), date(2026, 4, 28)),
    "basil": (PlantingStatus.TRANSPLANTED, date(2026, 2, 1), date(2026, 4, 28)),
    "marigold": (PlantingStatus.TRANSPLANTED, date(2026, 2, 1), date(2026, 4, 28)),
    "onion": (PlantingStatus.TRANSPLANTED, None, date(2026, 4, 2)),
    "carrot": (PlantingStatus.SOWN, date(2026, 4, 12), None),
}


def build(lang: str) -> dict:
    def pick(en: str, nl: str, fr: str) -> str:
        return {"en": en, "nl": nl, "fr": fr}[lang]

    db = PlantDatabase(load_builtin_json())
    data = build_initial_data(
        ENTRY, latitude=52.1, time_zone="Europe/Amsterdam", language=lang, today=NOW.date(), db=db
    )
    greenhouse_bed = next(b for b in data.beds if b.name == "Greenhouse Zone A bed")
    bed2 = next(b for b in data.beds if b.name == "Bed 2")
    data.plantings += [
        # kale right next to the tomatoes: a companion conflict to look at
        Planting("pl_kale", "kale", greenhouse_bed.id, 2026, LayoutMode.SINGLE, x_cm=210, y_cm=0,
                 width_cm=45, length_cm=45, method=SowMethod.INDOOR_SOW),
        Planting("pl_beans", "bush_bean", bed2.id, 2026, LayoutMode.ROW, x_cm=0, y_cm=10, width_cm=240, length_cm=45),
        Planting("pl_courgette", "courgette", bed2.id, 2026, LayoutMode.SINGLE, x_cm=60, y_cm=60, width_cm=90,
                 length_cm=60, method=SowMethod.INDOOR_SOW, status=PlantingStatus.TRANSPLANTED,
                 transplanted_on=NOW.date() - timedelta(days=5)),
    ]  # fmt: skip
    for planting in data.plantings:
        if planting.plant_id in PROGRESS:
            planting.status, planting.sown_on, planting.transplanted_on = PROGRESS[planting.plant_id]
        elif planting.plant_id == "lettuce" and planting.succession_index == 0:
            planting.status, planting.sown_on = PlantingStatus.SOWN, date(2026, 4, 1)
    data.features = [
        Feature(
            "ft_path",
            pick("Path", "Pad", "Allée"),
            FeatureType.PATH,
            x_cm=-20,
            y_cm=-90,
            width_cm=900,
            length_cm=60,
        ),
        Feature(
            "ft_butt",
            pick("Water butt", "Regenton", "Récupérateur d'eau"),
            FeatureType.WATER_BUTT,
            x_cm=-110,
            y_cm=0,
            width_cm=60,
            length_cm=60,
        ),
        Feature("ft_compost", "Compost", FeatureType.COMPOST, x_cm=-140, y_cm=120, width_cm=100, length_cm=100),
    ]
    # Orchard + soft fruit below the vegetable garden: perennials planted in earlier years.
    bottom = max(z.y_cm + z.length_cm for z in data.zones) + 120
    orchard = Zone(
        "zone_orchard",
        pick("Orchard", "Boomgaard", "Verger"),
        ZoneType.ORCHARD,
        x_cm=-20,
        y_cm=bottom,
        width_cm=900,
        length_cm=600,
    )
    fruit = Zone(
        "zone_fruit",
        pick("Fruit corner", "Fruithoek", "Coin à fruits"),
        ZoneType.FRUIT,
        x_cm=920,
        y_cm=bottom,
        width_cm=500,
        length_cm=300,
    )
    data.zones += [orchard, fruit]
    obed = GardenBed(
        "bed_orchard",
        orchard.name,
        orchard.id,
        x_cm=orchard.x_cm,
        y_cm=orchard.y_cm,
        width_cm=orchard.width_cm,
        length_cm=orchard.length_cm,
    )
    fbed = GardenBed(
        "bed_fruit",
        fruit.name,
        fruit.id,
        x_cm=fruit.x_cm,
        y_cm=fruit.y_cm,
        width_cm=fruit.width_cm,
        length_cm=fruit.length_cm,
    )
    data.beds += [obed, fbed]
    trees = [("apple", 2022, 0, 0), ("pear", 2023, 400, 0), ("sweet_cherry", 2025, 0, 300), ("plum", 2024, 400, 300)]
    for pid, season, x, y in trees:
        data.plantings.append(
            Planting(
                f"pl_{pid}",
                pid,
                obed.id,
                season,
                LayoutMode.SINGLE,
                x_cm=x + 50,
                y_cm=y,
                width_cm=300,
                length_cm=300,
                method=SowMethod.TRANSPLANT,
                status=PlantingStatus.TRANSPLANTED,
            )
        )
    data.plantings += [
        Planting("pl_alpine", "alpine_strawberry", obed.id, 2025, LayoutMode.ROW, x_cm=780, y_cm=0, width_cm=60, length_cm=600,
                 method=SowMethod.TRANSPLANT, status=PlantingStatus.TRANSPLANTED),
        Planting("pl_rasp", "raspberry_summer", fbed.id, 2024, LayoutMode.ROW, x_cm=0, y_cm=20, width_cm=500, length_cm=60,
                 method=SowMethod.TRANSPLANT, status=PlantingStatus.TRANSPLANTED),
        Planting("pl_redcurrant", "redcurrant", fbed.id, 2024, LayoutMode.BLOCK, x_cm=0, y_cm=130, width_cm=300, length_cm=150,
                 method=SowMethod.TRANSPLANT, status=PlantingStatus.TRANSPLANTED),
        Planting("pl_blueberry", "blueberry", fbed.id, 2025, LayoutMode.BLOCK, x_cm=320, y_cm=130, width_cm=160, length_cm=150,
                 method=SowMethod.TRANSPLANT, status=PlantingStatus.TRANSPLANTED),
    ]  # fmt: skip
    data.features += [
        Feature("ft_lawn", pick("Lawn", "Gazon", "Pelouse"), FeatureType.LAWN, x_cm=1080, y_cm=-90, width_cm=340, length_cm=420),
        Feature("ft_terrace", pick("Terrace", "Terras", "Terrasse"), FeatureType.TERRACE, x_cm=920, y_cm=bottom + 330,
                width_cm=500, length_cm=270),
        Feature("ft_fence", pick("Fence", "Omheining", "Clôture"), FeatureType.FENCE, x_cm=-160, y_cm=bottom + 620,
                width_cm=1580, length_cm=10),
    ]  # fmt: skip
    data.settings.resources = GardenResources(
        household_size=3, hours_per_week=4, goals=["fresh", "herbs", "storage"], wanted=["tomato"]
    )
    data.settings.irrigation.pump_entity = "switch.garden_pump"
    bed1 = next(b for b in data.beds if b.name == "Bed 1")
    bed1.irrigation_entity, bed1.irrigation_flow_lpm = "switch.valve_bed_1", 4.0
    data.irrigation_log = [IrrigationEvent(bed1.id, NOW - timedelta(days=1, hours=2), 6.0, 12.0, 3.0, "auto")]
    data.revision = 7
    # Records: last year's harvests (learned yields), diary, seed box, water meter, soil test.
    data.harvest_log = [
        HarvestEntry("h1", date(2025, 7, 20), "lettuce", 1.4, None, next(p.id for p in data.plantings if p.plant_id == "lettuce"), bed1.id, 4),
        HarvestEntry("h2", date(2025, 8, 12), "tomato", 3.2, 28, next((p.id for p in data.plantings if p.plant_id == "tomato"), None), None, 5),
        HarvestEntry("h3", date(2025, 9, 2), "tomato", 4.1, 35, next((p.id for p in data.plantings if p.plant_id == "tomato"), None), None, 4),
        HarvestEntry("h0a", date(2023, 8, 10), "tomato", 5.6, 41, None, None, 4),
        HarvestEntry("h0b", date(2024, 8, 14), "tomato", 9.2, 70, None, None, 5),
        HarvestEntry("h0c", date(2024, 7, 2), "lettuce", 2.1, None, None, bed1.id, 4),
        HarvestEntry("h0d", date(2023, 6, 20), "lettuce", 1.2, None, None, bed1.id, 3),
        HarvestEntry("h0e", date(2024, 9, 1), "courgette", 6.4, 9, None, None, 4),
        HarvestEntry("h4", date(2026, 5, 12), "radish", 0.6, 40, None, bed1.id, 4),
        HarvestEntry("h5", date(2026, 5, 18), "lettuce", 0.8, 3, None, bed1.id, 5),
    ]  # fmt: skip
    data.journal = [
        JournalEntry("j1", NOW - timedelta(days=6), pick("First flowers on the tomatoes.", "Eerste bloemen aan de tomaten.", "Premières fleurs sur les tomates."), kind="milestone",
                     plant_id="tomato", zone_id=data.zones[1].id),
        JournalEntry("j2", NOW - timedelta(days=2), pick("Aphids on the broad beans - hosed them off.", "Bladluis op de tuinbonen - met water afgespoten.", "Pucerons sur les fèves - rincés au jet d'eau."),
                     kind="problem", bed_id=bed1.id),
        JournalEntry("j3", NOW - timedelta(hours=20), pick("Courgette settled well after planting out.", "Courgette goed aangeslagen na het uitplanten.", "Les courgettes ont bien repris après la plantation."),
                     kind="observation", planting_id="pl_courgette", bed_id=bed2.id, plant_id="courgette"),
    ]  # fmt: skip
    data.seed_stock = [
        SeedPacket("s1", "carrot", "Nantaise 2", 2024, 1, "packet", "Vreeken"),
        SeedPacket("s2", "lettuce", "Lollo rossa", 2021, 1, "packet"),
        SeedPacket("s3", "bush_bean", "Purple Teepee", 2025, 120, "seeds", "swap"),
        SeedPacket("s4", "parsnip", "Tender and True", 2024, 1, "packet"),
    ]
    data.water_log = [
        WaterReading(NOW.date() - timedelta(days=d), round(142.0 - d * 0.055, 3), max(20.0, 80.0 - d * 4))
        for d in range(13, -1, -1)
    ]
    data.settings.water.meter_entity, data.settings.water.butt_level_entity = (
        "sensor.garden_water",
        "sensor.rain_butt_level",
    )
    data.settings.water.butt_capacity_l = 500
    bed1.soil_tests = [SoilTest(date(2026, 2, 20), ph=6.1, organic_matter_pct=2.4, p_mg=38, k_mg=12, lime_status="ok")]
    _climate_history(data)

    raw = json.loads((ROOT / "tests/fixtures/forecast_hourly_rain.json").read_text())["weather.home"]["forecast"]
    hourly = parse_forecast(raw)
    shift = NOW - hourly[0].at
    for point in hourly:
        point.at += shift
    weather = WeatherSnapshot(available=True, fetched_at=NOW, temperature=14.0, condition="partlycloudy", hourly=hourly)
    readings = {
        "sensor.soil_moisture_bed_1": SensorReading("sensor.soil_moisture_bed_1", 21.0, NOW),
        "sensor.soil_temp_bed_1": SensorReading("sensor.soil_temp_bed_1", 13.4, NOW),
        "sensor.greenhouse_temp": SensorReading("sensor.greenhouse_temp", 29.5, NOW),
    }
    seasons.adopt(data, NOW.year, db)
    analysis = analyze(data, db, weather, readings, now=NOW, tz=TZ, latitude=52.1, lang=lang)
    data.tasks = merge_tasks(
        [], generate_specs(analysis.task_context(data, db)), today=analysis.today, now=NOW, lang=lang
    ).tasks
    for task in data.tasks[:6:2]:
        task.assignee = "person.emery"
    snapshot = {
        "revision": data.revision,
        "lang": lang,
        "settings": to_dict(data.settings),
        "zones": [to_dict(z) for z in data.zones],
        "beds": [to_dict(b) for b in data.beds],
        "plantings": [to_dict(p) for p in data.plantings],
        "tasks": [to_dict(t) for t in data.tasks],
        "rotation_history": [],
        "features": [to_dict(f) for f in data.features],
        "layout_season": data.layout_season,
        "layouts": {k: to_dict(v) for k, v in data.layouts.items()},
        "transition_due": None,
        "irrigation_log": [to_dict(e) for e in data.irrigation_log],
        "harvest_log": [to_dict(e) for e in data.harvest_log],
        "journal": [to_dict(e) for e in data.journal],
        "seed_stock": [to_dict(e) for e in data.seed_stock],
        "irrigation_status": {"running": False, "bed_id": None, "ends_at": None, "last_error": None},
        "analysis": analysis.to_dict(),
        "weather": {
            "available": True,
            "temperature": 14.0,
            "condition": "partlycloudy",
            "fetched_at": NOW.isoformat(),
            "daily": [],
            "hourly": [to_dict(p) for p in hourly[:48]],
            "error": None,
        },
    }
    # Canned answers for the other websocket commands, produced by the real engine.
    chapters = handbook.chapters(lang)
    ctx = PrintContext(data, db, analysis.timelines, analysis.today, "Hortulus")
    proposal = autoplan(data, db, AutoplanOptions(season=2027, replace=True, lang=lang), today=analysis.today)
    irrigation = plan_irrigation(
        data, {k: b.irrigation for k, b in analysis.beds.items()}, now=NOW,
        frost_by_zone={k: z.frost for k, z in analysis.zones.items()}, outdoor_frost=analysis.frost, outdoor_temp=14.0, force=True,
    )  # fmt: skip
    crop_rows = []
    for p in data.plantings:
        if not seasons.present_in(p, False, NOW.year):
            continue
        plant = db.get(p.plant_id)
        bed = data.bed(p.bed_id)
        zone = data.zone(bed.zone_id) if bed else None
        tl = (
            season_timeline(
                p,
                plant,
                NOW.year,
                lambda y: season_anchors(data.settings.region, y),
                zone,
                NOW.date(),
                date(NOW.year, 1, 1),
                date(NOW.year, 12, 31),
            ).to_dict()
            if plant
            else None
        )
        crop_rows.append(
            {
                "planting": to_dict(p),
                "bed": bed.name if bed else None,
                "zone": zone.name if zone else None,
                "timeline": tl,
            }
        )
    issues = diagnose.check_garden(data, db, today=NOW.date(), current_season=NOW.year, lang=lang)
    snapshot["diagnosis"] = diagnose.summary(issues)
    here = diagnose.plan_view(data, season=NOW.year)
    other = diagnose.plan_view(data, season=NOW.year - 1) or here
    plan_tl = {
        p.id: season_timeline(
            p, db.get(p.plant_id), NOW.year, lambda y: season_anchors(data.settings.region, y),
            data.zone(data.bed(p.bed_id).zone_id) if data.bed(p.bed_id) else None, NOW.date(),
            date(NOW.year, 1, 1), date(NOW.year, 12, 31),
        )
        for p in data.plantings
        if db.get(p.plant_id) and seasons.present_in(p, False, NOW.year)
    }  # fmt: skip
    extras = {
        "report": planning.season_report(data, db, NOW.year, today=NOW.date()),
        "planning": {
            "season": NOW.year,
            "seeds": [n.to_dict() for n in planning.seed_needs(data, db, NOW.year)],
            "successions": [
                b.to_dict()
                for b in planning.successions(
                    data,
                    db,
                    NOW.year,
                    plan_tl,
                    today=NOW.date(),
                    first_frost=season_anchors(data.settings.region, NOW.year).first_frost,
                    lang=lang,
                )
            ],
            "harvest": planning.harvest_forecast(data, db, NOW.year, plan_tl),
        },
        "compare": diagnose.compare_plans(other, here, db, lang),
        "still_possible": {
            "season": NOW.year,
            "plants": diagnose.still_possible(data, db, NOW.year, today=NOW.date()),
        },
        "crop_rows": crop_rows,
        "analysis": {
            "season": NOW.year,
            "layout_season": data.layout_season,
            "issues": [i.to_dict() for i in issues],
            "errors": [],
            "counts": {
                "zones": len(data.zones),
                "beds": len(data.beds),
                "features": len(data.features),
                "plantings": len(data.plantings),
                "plans": 1,
                "archived_plans": 0,
                "log_entries": 0,
            },
        },
        "explain": {
            "plant_id": "tomato",
            "season": NOW.year,
            "has_plan": True,
            "beds": [
                v.to_dict() for v in diagnose.explain_plant(db.get("tomato"), data, db, NOW.year, today=NOW.date())
            ],
        },
        "year_preview": seasons.preview(data, db, NOW.year, season_end=date(NOW.year, 12, 31)).to_dict(),
        "handbook_index": {"chapters": [c.meta() for c in chapters], "glossary": handbook.glossary(lang)},
        "handbook_chapters": {c.id: {**c.meta(), "body": c.body} for c in chapters},
        "print_pages": render_svg(
            ctx, PrintOptions(document="garden", page="remarkable", color_mode="eink", lang=lang)
        ),
        "autofill": {**proposal.to_dict(), "season": 2027, "revision": data.revision},
        "irrigation_plan": {**irrigation.to_dict(), "reasons": {}, "running": False},
        "advice": {
            "suggestions": [x.to_dict() for x in advise(data, db, analysis, lang)],
            "coverage": harvest_coverage(data, db, analysis).to_dict(),
        },
        "qa_options": qa_options(data, db, 2026, lang),
        "qa_answers": {
            f"{subj}/{prob}/{tgt}": qa_answer(subj, prob, tgt, data, db, analysis, lang).to_dict()
            for subj, prob, tgt in (
                ("plant", "what_to_do", "tomato"),
                ("plant", "pests", "tomato"),
                ("plant", "disease", "tomato"),
                ("plant", "pruning", "apple"),
                ("plant", "no_fruit", "apple"),
                ("plant", "when_sow", "carrot"),
                ("greenhouse", "too_hot", data.zones[1].id),
                ("garden", "year_round", ""),
            )
        },
        "records": {
            "season": analysis.season,
            "harvest_season": {k: v.to_dict() for k, v in harvest_summary(data, analysis.season).items()},
            "harvest_all": {k: v.to_dict() for k, v in harvest_summary(data).items()},
            "harvest_years": harvest_by_year(data),
            "learned_yields": learned_yields(data),
            "seeds": seed_report(data, db, analysis.season),
            "water": water_stats(data, analysis.today).to_dict(),
            "year": year_overview(data, db, analysis),
            "kitchen": kitchen_report(data, db, analysis.timelines, analysis.today, lang),
            "economics": economics(data, db, analysis.season, lang),
            "expenses": [],
        },
        "supplies": {**catalog(lang), "shopping": [i.to_dict() for i in shopping_list(data, db, analysis, lang)]},
        "cooking": _cooking(data, db, analysis, lang),
        "wall": _wall(data, db, analysis, lang),
        "climate": _climate_stats(data, readings),
    }
    return {
        "snapshot": snapshot,
        "plants": {"plants": db.as_dicts(), "families": FAMILIES, "overrides": {}},
        "extras": extras,
    }


def _climate_history(data) -> None:
    """Two years of believable weather (deterministic), a greenhouse and a soil sensor."""
    import math

    from custom_components.garden_manager.engine.models import ClimateDay, Hemisphere, SensorDay

    data.settings.outdoor_sensors.air_temperature = "sensor.outdoor_temp"
    log, sensors = [], []
    start = NOW.date() - timedelta(days=760)
    for i in range(760):
        day = start + timedelta(days=i)
        season = math.cos((day.timetuple().tm_yday - 200) / 365 * 2 * math.pi)  # 1 in July, -1 in January
        wobble = math.sin(i * 1.7) * 2.5 + math.sin(i * 0.31) * 3.0
        tmin = round(5.5 + 6.5 * season + wobble - 1.5, 1)
        tmax = round(14.0 + 9.0 * season + wobble + math.sin(i * 2.3) * 2, 1)
        rain = round(max(0.0, math.sin(i * 0.9) * 9 + math.sin(i * 0.23) * 4 - 3), 1)
        sun = round(max(0.0, 4.5 + 3.5 * season - rain / 3 + math.sin(i * 1.1)), 1)
        source = "sensor" if i > 700 else ("history" if i % 5 else "model")
        log.append(ClimateDay(day, tmin, tmax, rain, tmean=round((tmin + tmax) / 2, 1), rh_mean=round(78 - 10 * season + rain), sun_h=sun,
                              gust_max=round(25 + abs(math.sin(i * 0.7)) * 45), hours=24.0 if source == "sensor" else 0.0, source=source,
                              rain_src="gauge" if source == "sensor" else source))  # fmt: skip
        if i > 760 - 120:
            sensors.append(
                SensorDay(
                    "sensor.greenhouse_temp",
                    day,
                    round(tmin + 3, 1),
                    round(tmax + 9, 1),
                    round((tmin + tmax) / 2 + 5, 1),
                    140,
                )
            )
            sensors.append(
                SensorDay(
                    "sensor.soil_temp_bed_1",
                    day,
                    round((tmin + tmax) / 2 - 1.5, 1),
                    round((tmin + tmax) / 2 + 1.5, 1),
                    round((tmin + tmax) / 2, 1),
                    140,
                )
            )
            sensors.append(SensorDay("sensor.outdoor_temp", day, tmin, tmax, round((tmin + tmax) / 2, 1), 140))
    data.climate_log, data.sensor_log = log, sensors
    climate.update_frost_years(data, Hemisphere.NORTH, NOW.date())


def _climate_stats(data, readings) -> dict:
    anchors = season_anchors(data.settings.region, NOW.year)
    sensors = {
        e: {**meta, "now": readings[e].value if e in readings else 12.5}
        for e, meta in climate.temperature_sensors(data).items()
    }
    return climate.climate_stats(
        data,
        NOW.date(),
        latitude=52.1,
        preset_last=anchors.last_frost,
        preset_first=anchors.first_frost,
        sensors=sensors,
    )


def _wall(data, db, analysis, lang: str) -> dict:
    """What wall/data returns: the default layout and today's reading blocks (Dutch)."""
    from custom_components.garden_manager.engine import eco, wall

    day = date(2026, 8, 12)
    c = _cooking(data, db, analysis, "nl")
    title, text = eco.month_tip(day.month, "nl")
    return {
        "layout": wall.default_layout(), "custom": False, "user_id": "u", "can_arrange": True,
        "blocks": dict(wall.BLOCKS),
        "saying": wall.saying(day), "fact": wall.fact(day), "eco_month": {"title": title, "text": text},
        "recipe": wall.recipe_tip(c["recipes"], day),
        "ready": [{"name": p["name"], "until": p.get("until")} for p in c["ready"]],
    }  # fmt: skip


def _cooking(data, db, analysis, lang: str) -> dict:
    """What the Cooking tab shows: the garden's ready produce (plus a late-summer basket) as recipes."""
    from custom_components.garden_manager.engine import cooking

    report = kitchen_report(data, db, analysis.timelines, analysis.today, lang)
    extra = [
        {"plant_id": p, "until": None} for p in ("tomato", "courgette", "kale", "carrot", "basil", "pumpkin", "apple")
    ]
    produce = cooking.ready_produce([*report.get("ready", []), *extra], db)
    for p in produce:
        plant = db.get(p["plant_id"])
        p.update(name=plant.name(lang), icon=plant.icon, color=plant.color, emoji=plant.emoji)
    prefs = cooking.Prefs.from_dict({"proteins": ["chicken", "salmon"], "use": ["feta"], "servings": 4})
    recipes = cooking.suggest(produce, db, prefs, lang, 12)
    menus = cooking.menus(produce, db, prefs, lang, 4, date(2026, 8, 12))
    edible = sorted(
        ({"plant_id": p.id, "name": p.name(lang), "kind": k, "icon": p.icon, "color": p.color} for p in db.all()
         if (k := cooking.produce_kind(p)) is not None),
        key=lambda x: x["name"].lower(),
    )  # fmt: skip
    book = [
        {
            **recipes[1],
            "saved": True,
            "favorite": True,
            "shared": False,
            "note": "",
            "added": "2026-08-01",
            "cooked": [],
        }
    ]
    return {
        "ready": produce, "produce": produce, "recipes": recipes, "menus": menus, "prefs": None,
        "used_prefs": {"pantry": [], "use": prefs.use, "proteins": prefs.proteins, "side": "", "servings": prefs.servings},
        "catalog": {**cooking.catalog(lang), "edible": edible}, "book": book,
    }  # fmt: skip


if __name__ == "__main__":
    language = sys.argv[1] if len(sys.argv) > 1 else "en"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / f"data-{language}.json"
    target.write_text(json.dumps(build(language)), encoding="utf-8")
    print(f"wrote {target}")
