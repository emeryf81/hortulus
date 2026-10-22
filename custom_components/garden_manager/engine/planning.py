"""Planning help on top of the plan: seeds to buy, what follows a crop, expected harvests.

* :func:`seed_needs` - how many seeds the plan of a season needs per crop
  (plant count x a germination margin) against the seed stock.
* :func:`successions` - per bed: when it becomes free this season and which
  crops still fit after that (same rules as autofill: window, frost before the
  harvest, zone type) without repeating the family that just grew there.
* :func:`harvest_forecast` - kg per week for the season, from the bed area,
  the crop's yield (your own learned yield when there is one) and the harvest
  window of each crop.

Pure module: no Home Assistant imports.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
import math
from typing import Any

from .autoplan import feasibility
from .geometry import plant_count
from .models import GardenData, PlantingStatus, SowMethod, present_in
from .plantdb import PlantDatabase
from .records import learned_details, learned_harvest_days, learned_yields, seed_report
from .schedule import PlantingTimeline
from .seasons import layout_for

# Seeds per plant that end up as a plant: more for direct sowing (birds, slugs,
# thinning), fewer when raised indoors.
SEED_MARGIN = {SowMethod.DIRECT_SOW: 2.0, SowMethod.INDOOR_SOW: 1.3}


# --------------------------------------------------------------------------- #
# Seeds
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class SeedNeed:
    plant_id: str
    plants: int = 0
    seeds: int = 0
    plantings: list[str] = field(default_factory=list)
    stock: list[dict[str, Any]] = field(default_factory=list)  # usable packets
    status: str = "none"  # ok | check | short | none
    to_buy: int = 0  # seeds still missing (counted seed packets only)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "plants": self.plants,
            "seeds": self.seeds,
            "plantings": self.plantings,
            "stock": self.stock,
            "status": self.status,
            "to_buy": self.to_buy,
        }


def seed_needs(data: GardenData, db: PlantDatabase, season: int) -> list[SeedNeed]:
    """Seeds the season's plan still needs, per crop, with what is in stock."""
    needs: dict[str, SeedNeed] = {}
    for p in data.plantings:
        plant = db.get(p.plant_id)
        if plant is None or plant.perennial or p.season != season:
            continue
        if p.method is SowMethod.TRANSPLANT or p.status is not PlantingStatus.PLANNED:
            continue
        n = plant_count(p, plant)
        need = needs.setdefault(p.plant_id, SeedNeed(p.plant_id))
        need.plants += n
        need.seeds += math.ceil(n * SEED_MARGIN.get(p.method, 1.5))
        need.plantings.append(p.id)
    usable = {"ok", "use_soon", "unknown"}
    for packet in seed_report(data, db, season)["packets"]:
        need = needs.get(packet["plant_id"])
        if need is not None and packet["status"] in usable:
            need.stock.append(packet)
    for need in needs.values():
        seeds = sum(s["quantity"] for s in need.stock if s.get("unit") == "seeds")
        other = [s for s in need.stock if s.get("unit") != "seeds" and s["quantity"] > 0]
        if seeds >= need.seeds:
            need.status = "ok"
        elif other:
            need.status = "check"  # packets or grams: probably enough, Hortulus cannot count them
        elif seeds:
            need.status = "short"
        else:
            need.status = "none"
        need.to_buy = max(0, need.seeds - seeds) if need.status in ("short", "none") else 0
    order = {"none": 0, "short": 1, "check": 2, "ok": 3}
    return sorted(needs.values(), key=lambda n: (order[n.status], n.plant_id))


def seed_todo_items(needs: list[SeedNeed], db: PlantDatabase, season: int, lang: str) -> list[dict[str, str]]:
    """Shopping items (summary + description) for the crops that still lack seed."""
    from .i18n import t

    items = []
    for need in needs:
        if need.status not in ("short", "none"):
            continue
        plant = db.get(need.plant_id)
        name = plant.name(lang) if plant else need.plant_id
        # the summary names only the crop, so a changed quantity does not add a second item
        description = t("seeds.todo_description", lang, season=season, plants=need.plants)
        if need.to_buy:
            description = f"{t('seeds.todo_amount', lang, seeds=need.to_buy)} {description}"
        items.append(
            {
                "plant_id": need.plant_id,
                "summary": t("seeds.todo_item_any", lang, plant=name),
                "description": description,
            }
        )
    return items


# --------------------------------------------------------------------------- #
# What can follow a crop
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class BedSuccession:
    bed_id: str
    free_from: date
    leaving: list[str]  # plant ids that end there
    options: list[dict[str, Any]]  # {"plant_id", "harvest_by"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "bed_id": self.bed_id,
            "free_from": self.free_from.isoformat(),
            "leaving": self.leaving,
            "options": self.options,
        }


def successions(
    data: GardenData,
    db: PlantDatabase,
    season: int,
    timelines: Mapping[str, PlantingTimeline],
    *,
    today: date,
    first_frost: date,
    limit: int = 6,
    lang: str = "en",
) -> list[BedSuccession]:
    """Beds that empty out before the frost, with crops that still fit afterwards."""
    layout = layout_for(data, season)
    if layout is None:
        return []
    zones = {z.id: z for z in layout.zones}
    out: list[BedSuccession] = []
    for bed in layout.beds:
        here = [p for p in data.plantings if p.bed_id == bed.id and present_in(p, False, season)]
        annual = [p for p in here if (pl := db.get(p.plant_id)) is not None and not pl.perennial]
        if not annual or len(annual) != len(here):
            continue  # empty beds are autofill's job; beds with perennials stay occupied
        ends = [timelines[p.id].occupancy.end for p in annual if p.id in timelines]
        if not ends:
            continue
        free_from = max(*ends, today)
        if free_from >= first_frost - timedelta(days=21):
            continue
        families = {pl.family for p in annual if (pl := db.get(p.plant_id))}
        options = []
        for plant in sorted(db.all(), key=lambda pl: pl.name(lang).casefold()):
            if plant.perennial or plant.family in families or not plant.harvestable:
                continue
            if feasibility(plant, bed, zones.get(bed.zone_id), data, season, free_from, True):
                continue
            ready = free_from + timedelta(days=plant.days_to_maturity[0])
            options.append({"plant_id": plant.id, "harvest_by": ready.isoformat(), "days": plant.days_to_maturity[0]})
        options.sort(key=lambda o: o["days"])
        out.append(BedSuccession(bed.id, free_from, sorted({p.plant_id for p in annual}), options[:limit]))
    out.sort(key=lambda b: b.free_from)
    return out


# --------------------------------------------------------------------------- #
# Expected harvests
# --------------------------------------------------------------------------- #
MAX_SHIFT_DAYS = 30


def harvest_forecast(
    data: GardenData,
    db: PlantDatabase,
    season: int,
    timelines: Mapping[str, PlantingTimeline],
) -> dict[str, Any]:
    """Expected kg per week (Monday) for the season, per crop.

    Your own years count: yields blend in the kg/m² you harvested, and the harvest start moves to
    when your first harvests really came (days after sowing or planting out), at most a month.
    """
    learned = learned_yields(data, db)
    own_days = learned_harvest_days(data)
    weeks: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    totals: dict[str, float] = defaultdict(float)
    for p in data.plantings:
        plant = db.get(p.plant_id)
        tl = timelines.get(p.id)
        if plant is None or tl is None or not plant.harvestable or not present_in(p, False, season):
            continue
        if p.status in (PlantingStatus.FAILED, PlantingStatus.FINISHED) or not tl.bearing:
            continue
        kg = p.width_cm * p.length_cm / 10_000 * (learned.get(p.plant_id) or plant.yield_kg_m2 or 0.0)
        start, end = tl.harvest_start, max(tl.harvest_end, tl.harvest_start)
        # the same start as the learned days (planting out before sowing), planned dates as a fallback
        sown = p.transplanted_on or p.transplant_date or tl.transplant_date or p.sown_on or p.sow_date or tl.sow_date
        if p.plant_id in own_days and sown is not None and p.harvest_started_on is None:
            shift = (sown + timedelta(days=own_days[p.plant_id])) - start
            shift = max(timedelta(days=-MAX_SHIFT_DAYS), min(timedelta(days=MAX_SHIFT_DAYS), shift))
            start, end = start + shift, end + shift
        days = (end - start).days + 1
        per_day = kg / days
        for i in range(days):
            day = start + timedelta(days=i)
            if day.year != season and day.year != season + 1:
                continue
            weeks[day - timedelta(days=day.weekday())][p.plant_id] += per_day
        totals[p.plant_id] += kg
    rows = [
        {
            "week": w.isoformat(),
            "kg": round(sum(v.values()), 2),
            "by_plant": {k: round(x, 2) for k, x in v.items() if x >= 0.01},
        }
        for w, v in sorted(weeks.items())
    ]
    return {
        "season": season,
        "weeks": rows,
        "totals": {k: round(v, 1) for k, v in sorted(totals.items(), key=lambda kv: -kv[1])},
        "learned": sorted(k for k in totals if k in learned or k in own_days),
        "learned_detail": {k: v for k, v in learned_details(data).items() if k in totals},
    }


# --------------------------------------------------------------------------- #
# End of season report
# --------------------------------------------------------------------------- #
def season_report(
    data: GardenData,
    db: PlantDatabase,
    season: int,
    *,
    today: date | None = None,
    lang: str = "en",
    latitude: float | None = None,
) -> dict[str, Any]:
    """What was grown, harvested and lost in a season, and what the journal said about it."""
    from .records import harvest_summary
    from .region import season_bounds, season_for_date

    region = data.settings.region
    running = today is not None and today <= season_bounds(region, season)[1]
    harvests = harvest_summary(data, season)
    crops: dict[str, dict[str, Any]] = {}
    failed = []
    for p in data.plantings:
        if not present_in(p, False, season) or db.get(p.plant_id) is None:
            continue
        plant = db.get(p.plant_id)
        c = crops.setdefault(
            p.plant_id,
            {"plant_id": p.plant_id, "plantings": 0, "area_m2": 0.0, "failed": 0, "expected_kg": 0.0},
        )
        c["plantings"] += 1
        area = p.width_cm * p.length_cm / 10_000
        c["area_m2"] += area
        if p.status is PlantingStatus.FAILED:
            c["failed"] += 1
            failed.append({"planting_id": p.id, "plant_id": p.plant_id, "bed_id": p.bed_id, "notes": p.notes})
        elif plant.harvestable and not (plant.perennial and p.season + (plant.years_to_bearing or 0) > season):
            c["expected_kg"] += area * (plant.yield_kg_m2 or 0.0)  # young fruit trees do not crop yet
    for pid, h in harvests.items():
        c = crops.setdefault(pid, {"plant_id": pid, "plantings": 0, "area_m2": 0.0, "failed": 0, "expected_kg": 0.0})
        c["kg"] = h.kg
        c["kg_m2"] = h.kg_m2
        c["first"] = h.first.isoformat() if h.first else None
        c["last"] = h.last.isoformat() if h.last else None
    for c in crops.values():
        c["area_m2"] = round(c["area_m2"], 2)
        c["expected_kg"] = round(c["expected_kg"], 1)
        plant = db.get(c["plant_id"])
        c["book_kg_m2"] = plant.yield_kg_m2 if plant else None
        kg, exp = c.get("kg", 0.0), c["expected_kg"]
        c["verdict"] = (
            "failed" if c["failed"] and c["failed"] == c["plantings"]
            else "growing" if running and not kg
            else "no_record" if not kg and exp
            else "above" if exp and kg >= exp * 1.2
            else "below" if exp and kg < exp * 0.6
            else "as_expected" if exp
            else "ok"
        )  # fmt: skip
    journal = [e for e in data.journal if season_for_date(region, e.at.date()) == season]
    water = [e for e in data.irrigation_log if season_for_date(region, e.at.date()) == season]
    weather: list[str] = []
    if data.settings.season_summary:  # the season's weather against the same dates a year before
        from .climate import compare_with_last_year, summary_lines

        start, end = season_bounds(region, season)
        end = min(end, today) if today else end
        if start <= end:
            weather = summary_lines(
                compare_with_last_year(data, start, end, latitude=latitude or region.latitude or 50.85,
                                       elevation_m=data.settings.elevation_m or 0.0),
                lang,
            )  # fmt: skip
    saying = ""
    if data.settings.slogans:
        from .slogans import slogan

        saying = slogan(lang, day=today or date.today(), topics=("harvest", "garden", "veg"), salt=f"report{season}",
                        south=region.hemisphere.value == "south", season=False)  # fmt: skip
    return {
        "season": season,
        "running": running,
        "weather": weather,
        "slogan": saying,
        "crops": sorted(crops.values(), key=lambda c: (-c.get("kg", 0.0), c["plant_id"])),
        "failed": failed,
        "problems": [
            {
                "at": e.at.isoformat(),
                "text": e.text,
                "planting_id": e.planting_id,
                "bed_id": e.bed_id,
                "plant_id": e.plant_id,
            }
            for e in journal
            if e.kind == "problem"
        ],
        "milestones": [{"at": e.at.isoformat(), "text": e.text} for e in journal if e.kind == "milestone"],
        "totals": {
            "crops": len(crops),
            "plantings": sum(c["plantings"] for c in crops.values()),
            "kg": round(sum(c.get("kg", 0.0) for c in crops.values()), 1),
            "expected_kg": round(sum(c["expected_kg"] for c in crops.values()), 1),
            "failed": len(failed),
            "water_l": round(sum(e.liters for e in water)),
            "water_runs": len(water),
            "journal": len(journal),
        },
    }
