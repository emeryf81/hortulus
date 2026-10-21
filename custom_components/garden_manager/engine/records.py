"""Garden records: harvest log, seed stock, water use and the year overview.

* Harvest: totals per crop and season, and **learned yields** (kg/m²) from
  your own harvests - the auto-planner and the advice use them instead of the
  generic database value once there is enough data.
* Seed stock: how long seed keeps per family, which packets are getting old,
  and which crops in the plan still need seed.
* Water: daily meter and water-butt readings -> use per week, rain water
  available, and the share of rain water.
* Year overview: per crop and month what happens (sow indoors, sow, plant
  out, harvest) - the calendar's year view and the "year" printout.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from .models import GardenData, Plant, PlantingStatus, SeedPacket, SowMethod, WaterReading, present_in
from .plantdb import PlantDatabase
from .region import season_for_date

if TYPE_CHECKING:
    from .analysis import GardenAnalysis

# --------------------------------------------------------------------------- #
# Harvest
# --------------------------------------------------------------------------- #
MIN_LEARN_AREA_M2 = 0.1


@dataclass(slots=True)
class CropHarvest:
    plant_id: str
    kg: float = 0.0
    count: int = 0
    entries: int = 0
    first: date | None = None
    last: date | None = None
    area_m2: float = 0.0  # planted area of the plantings with harvests

    @property
    def kg_m2(self) -> float | None:
        return round(self.kg / self.area_m2, 2) if self.area_m2 >= MIN_LEARN_AREA_M2 and self.kg > 0 else None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["first"] = self.first.isoformat() if self.first else None
        d["last"] = self.last.isoformat() if self.last else None
        d["kg_m2"] = self.kg_m2
        return d


def harvest_summary(data: GardenData, season: int | None = None) -> dict[str, CropHarvest]:
    """Totals per crop (optionally one season; hemisphere aware like the rest of the plan)."""
    out: dict[str, CropHarvest] = {}
    areas: dict[str, set[str]] = defaultdict(set)
    region = data.settings.region
    for e in data.harvest_log:
        if season is not None and season_for_date(region, e.day) != season:
            continue
        crop = out.setdefault(e.plant_id, CropHarvest(e.plant_id))
        crop.kg += e.kg
        crop.count += e.count or 0
        crop.entries += 1
        crop.first = min(crop.first or e.day, e.day)
        crop.last = max(crop.last or e.day, e.day)
        if e.planting_id:
            areas[e.plant_id].add(e.planting_id)
    for pid, ids in areas.items():
        out[pid].area_m2 = sum(p.width_cm * p.length_cm / 10_000 for p in data.plantings if p.id in ids)
    for crop in out.values():
        crop.kg = round(crop.kg, 2)
        crop.area_m2 = round(crop.area_m2, 2)
    return out


def harvest_by_year(data: GardenData) -> dict[str, dict[str, float]]:
    """kg per crop per season, for the harvest-over-the-years chart."""
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    region = data.settings.region
    for e in data.harvest_log:
        if e.kg:
            out[e.plant_id][str(season_for_date(region, e.day))] += e.kg
    return {pid: {season: round(kg, 2) for season, kg in sorted(years.items())} for pid, years in out.items()}


def learned_yields(data: GardenData) -> dict[str, float]:
    """kg/m² per crop from your own harvests (average over seasons with data)."""
    per_season: dict[str, list[float]] = defaultdict(list)
    seasons = {season_for_date(data.settings.region, e.day) for e in data.harvest_log}
    for season in seasons:
        for pid, crop in harvest_summary(data, season).items():
            if crop.kg_m2 is not None:
                per_season[pid].append(crop.kg_m2)
    return {pid: round(sum(v) / len(v), 2) for pid, v in per_season.items()}


# --------------------------------------------------------------------------- #
# Seed stock
# --------------------------------------------------------------------------- #
# Years seed stays reliably viable when stored cool and dry.
VIABILITY_BY_FAMILY = {
    "Amaryllidaceae": 2, "Apiaceae": 3, "Asteraceae": 4, "Brassicaceae": 5, "Cucurbitaceae": 6,
    "Fabaceae": 3, "Solanaceae": 5, "Amaranthaceae": 4, "Lamiaceae": 3, "Poaceae": 2,
}  # fmt: skip
VIABILITY_BY_PLANT = {"parsnip": 1, "onion": 2, "leek": 3, "chives": 2, "sweet_corn": 2, "spinach": 3, "lettuce": 4}
DEFAULT_VIABILITY = 3


def viability_years(plant: Plant | None, plant_id: str) -> int:
    if plant_id in VIABILITY_BY_PLANT:
        return VIABILITY_BY_PLANT[plant_id]
    if plant is not None:
        return VIABILITY_BY_FAMILY.get(plant.family, DEFAULT_VIABILITY)
    return DEFAULT_VIABILITY


@dataclass(slots=True)
class SeedStatus:
    packet: SeedPacket
    use_by: int | None
    status: str  # ok | use_soon | expired | unknown | empty
    needed: bool  # a crop in this season's plan uses it

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self.packet), "use_by": self.use_by, "status": self.status, "needed": self.needed}


def seed_report(data: GardenData, db: PlantDatabase, season: int) -> dict[str, Any]:
    """Status per packet + crops in the plan that have no usable seed."""
    planned = {
        p.plant_id
        for p in data.plantings
        if p.season == season
        and p.status is PlantingStatus.PLANNED
        and p.method is not SowMethod.TRANSPLANT
        and not (db.get(p.plant_id) or _NoPlant).perennial
    }
    packets: list[SeedStatus] = []
    usable: set[str] = set()
    for packet in data.seed_stock:
        plant = db.get(packet.plant_id)
        use_by = packet.year + viability_years(plant, packet.plant_id) if packet.year else None
        if packet.quantity <= 0:
            status = "empty"
        elif use_by is None:
            status = "unknown"
        elif season > use_by:
            status = "expired"
        elif season == use_by:
            status = "use_soon"
        else:
            status = "ok"
        if status in ("ok", "use_soon", "unknown"):
            usable.add(packet.plant_id)
        packets.append(SeedStatus(packet, use_by, status, packet.plant_id in planned))
    packets.sort(key=lambda s: (not s.needed, s.status != "expired", s.packet.plant_id))
    return {"packets": [s.to_dict() for s in packets], "missing": sorted(planned - usable), "season": season}


class _NoPlant:
    perennial = False


# --------------------------------------------------------------------------- #
# Water
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class WaterStats:
    week_l: float | None = None  # mains water used in the last 7 days
    season_l: float | None = None  # since 1 January
    rain_available_l: float | None = None  # in the butts now
    butt_pct: float | None = None
    per_day: list[dict[str, Any]] = field(default_factory=list)  # last 14 days
    # Watering this year by source, and the pump energy (2.1)
    irrigated_rain_l: float = 0.0
    irrigated_mains_l: float = 0.0
    pump_kwh: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def book_irrigation(data: GardenData, day: date, liters: float, water: str, kwh: float) -> None:
    """Add one run to the year's watering totals (by source) and pump energy."""
    year = data.irrigation_years.setdefault(str(day.year), {"rain_l": 0.0, "mains_l": 0.0, "kwh": 0.0})
    key = "rain_l" if water == "rain" else "mains_l"
    year[key] = round(year.get(key, 0.0) + max(liters, 0.0), 1)
    year["kwh"] = round(year.get("kwh", 0.0) + max(kwh, 0.0), 3)


def record_water(data: GardenData, day: date, meter_m3: float | None, butt_pct: float | None) -> bool:
    """Store today's reading (one per day, latest wins). Returns True when stored."""
    if meter_m3 is None and butt_pct is None:
        return False
    existing = next((r for r in data.water_log if r.day == day), None)
    if existing:
        existing.meter_m3, existing.butt_pct = meter_m3, butt_pct
    else:
        data.water_log.append(WaterReading(day, meter_m3, butt_pct))
        data.water_log.sort(key=lambda r: r.day)
        del data.water_log[:-400]  # about a year of history
    return True


def water_stats(data: GardenData, today: date) -> WaterStats:
    stats = WaterStats()
    log = [r for r in data.water_log if r.meter_m3 is not None]

    def reading_on_or_before(day: date) -> WaterReading | None:
        return next((r for r in reversed(log) if r.day <= day), None)

    latest = reading_on_or_before(today)
    if latest is not None:
        week = reading_on_or_before(today - timedelta(days=7))
        year = next((r for r in log if r.day.year == today.year), None)
        if week is not None and latest.meter_m3 is not None and week.meter_m3 is not None:
            stats.week_l = round(max(latest.meter_m3 - week.meter_m3, 0) * 1000)
        if year is not None and latest.meter_m3 is not None and year.meter_m3 is not None:
            stats.season_l = round(max(latest.meter_m3 - year.meter_m3, 0) * 1000)
        prev = None
        for r in log:
            if r.day < today - timedelta(days=14):
                prev = r
                continue
            if prev is not None and prev.meter_m3 is not None and r.meter_m3 is not None:
                stats.per_day.append(
                    {"day": r.day.isoformat(), "liters": round(max(r.meter_m3 - prev.meter_m3, 0) * 1000)}
                )
            prev = r
    year_stats = data.irrigation_years.get(str(today.year), {})
    stats.irrigated_rain_l = round(year_stats.get("rain_l", 0.0), 1)
    stats.irrigated_mains_l = round(year_stats.get("mains_l", 0.0), 1)
    stats.pump_kwh = round(year_stats.get("kwh", 0.0), 2)
    butt = next((r for r in reversed(data.water_log) if r.butt_pct is not None), None)
    if butt is not None:
        stats.butt_pct = butt.butt_pct
        cap = data.settings.water.butt_capacity_l
        if cap:
            stats.rain_available_l = round(cap * (butt.butt_pct or 0) / 100)
    return stats


# --------------------------------------------------------------------------- #
# Year overview
# --------------------------------------------------------------------------- #
ACTIVITIES = ("sow_indoor", "sow", "plant", "grow", "harvest")


def year_overview(data: GardenData, db: PlantDatabase, analysis: GardenAnalysis) -> dict[str, Any]:
    """Per crop of the season: month (1-12) -> activities, plus task counts per month."""
    return year_matrix(data, db, analysis.timelines, analysis.season)


def year_matrix(data: GardenData, db: PlantDatabase, timelines: Mapping[str, Any], season: int) -> dict[str, Any]:
    region = data.settings.region
    rows: dict[str, dict[str, Any]] = {}
    for p in data.plantings:
        plant = db.get(p.plant_id)
        tl = timelines.get(p.id)
        if plant is None or tl is None or not present_in(p, plant.perennial, season):
            continue
        row = rows.setdefault(
            plant.id, {"plant_id": plant.id, "months": {str(m): [] for m in range(1, 13)}, "beds": []}
        )
        bed = data.bed(p.bed_id)
        if bed and bed.name not in row["beds"]:
            row["beds"].append(bed.name)

        def mark(start: date | None, end: date | None, what: str, row: dict[str, Any] = row) -> None:
            if start is None or end is None:
                return
            day = date(start.year, start.month, 1)
            while day <= end:
                if season_for_date(region, day) == season and what not in row["months"][str(day.month)]:
                    row["months"][str(day.month)].append(what)
                day = date(day.year + (day.month == 12), day.month % 12 + 1, 1)

        if tl.sow_date and tl.method is SowMethod.INDOOR_SOW:
            mark(tl.sow_date, tl.sow_date, "sow_indoor")
        elif tl.sow_date:
            mark(tl.sow_date, tl.sow_date, "sow")
        if tl.transplant_date:
            mark(tl.transplant_date, tl.transplant_date, "plant")
        mark(tl.in_ground, tl.harvest_start - timedelta(days=1), "grow")
        if plant.harvestable and tl.bearing:
            mark(tl.harvest_start, tl.harvest_end, "harvest")
    tasks = [0] * 12
    minutes = [0] * 12
    for task in data.tasks:
        if season_for_date(region, task.due) == season:
            tasks[task.due.month - 1] += 1
            minutes[task.due.month - 1] += task.estimated_minutes
    return {
        "season": season,
        "rows": sorted(rows.values(), key=lambda r: r["plant_id"]),
        "tasks": tasks,
        "minutes": minutes,
    }
