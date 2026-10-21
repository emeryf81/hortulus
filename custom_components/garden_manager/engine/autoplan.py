"""Autofill: propose a season plan from the available area and resources.

The planner is deliberately greedy and explainable - every choice can be
traced to one of these rules:

1. **What** - crops come from the gardener's ``wanted`` list first, then from
   the goals (fresh, storage, herbs, pollinators, winter, perennials, easy),
   ordered by a popularity prior.  ``excluded`` crops never appear.
2. **How much** - ``plants_per_person x household`` plants at a time, using
   the crop's own spacing.  Quick crops are split into three successive
   sowings so the harvest is spread instead of all at once.
3. **Where** - each crop goes to the bed with the best score: rotation (a
   family returning too soon is excluded), zone fit (tender, long-season
   crops into the greenhouse; never a greenhouse-unsuitable crop under
   glass), companions already placed in that bed, shade tolerance and
   container suitability.
4. **Layout** - inside a bed, crops are packed in strips with the tallest on
   the side away from the sun (north in the northern hemisphere) so they
   do not shade the rest.
5. **Budgets** - placements stop when the weekly time, peak-week water or
   compost budget would be exceeded; skipped crops are reported.

The result is a *proposal*; nothing is stored until the gardener applies it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
import math
from typing import Any

from .compatibility import check_rotation, rotation_history
from .fertilizer import bed_fertilizer_plan
from .models import (
    ZONE_CATEGORIES,
    BedKind,
    FrostTolerance,
    GardenBed,
    GardenData,
    GardenResources,
    Hemisphere,
    LayoutMode,
    Plant,
    PlantCategory,
    Planting,
    Relation,
    Suitability,
    TaskType,
    Zone,
    present_in,
)
from .plantdb import PlantDatabase
from .records import learned_yields
from .region import resolve_profile, season_anchors
from .schedule import default_method, planting_timeline
from .seasons import layout_for, plan_seasons
from .succession import expand_succession
from .tasks import new_id

# Typical peak-summer reference ET (mm/day) and effective rain for NW Europe;
# used for the *budget* only - daily watering always uses the live forecast.
PEAK_ET0_MM = 4.0
EFFECTIVE_RAIN_MM = 1.6
MINUTES_PER_M2_WEEK = 6.0  # weeding, checking, tidying
HAND_WATERING_L_PER_MIN = 8.0
SUCCESSION_SOWINGS = 3
MARGIN_CM = 5.0
MIN_SHRINK = 0.4  # a crop is never squeezed below 40 % of its wanted area
MIN_SHRINK_WANTED = 0.1
FILL_FACTOR = 0.85  # strips never pack perfectly

# Popularity prior: what most kitchen gardens grow, best first.
POPULAR = (
    "tomato", "lettuce", "courgette", "bush_bean", "carrot", "cucumber", "potato", "onion", "radish",
    "beetroot", "spinach", "pea", "kale", "leek", "chard", "runner_bean", "cherry_tomato", "garlic",
    "pepper", "strawberry", "squash", "broccoli", "cabbage", "spring_onion", "rocket", "pumpkin",
    "celeriac", "parsnip", "cauliflower", "corn_salad", "basil", "parsley", "chives", "thyme", "dill",
    "coriander", "mint", "rosemary", "oregano", "sage", "marigold", "nasturtium", "calendula", "borage",
)  # fmt: skip

# Flowers added for bees and hoverflies when insect-pollinated crops are planned.
POLLINATOR_FLOWERS = ("borage", "calendula", "phacelia", "sweet_alyssum")
GOALS = ("fresh", "storage", "herbs", "pollinators", "winter", "perennials", "easy")


@dataclass(slots=True)
class AutoplanOptions:
    season: int
    bed_ids: list[str] | None = None  # None = every bed without crops this season
    replace: bool = False  # re-plan the selected beds (existing crops are ignored)
    max_crops: int = 16
    lang: str = "en"


@dataclass(slots=True)
class CropDemand:
    plant: Plant
    count: int
    area_cm2: float
    priority: float
    reason: str  # wanted | goal:<name>


@dataclass(slots=True)
class _Item:
    demand: CropDemand
    width: float
    depth: float
    x: float = 0.0
    y: float = 0.0
    orig_area: float = 0.0

    def __post_init__(self) -> None:
        if not self.orig_area:
            self.orig_area = self.width * self.depth


@dataclass(slots=True)
class Placement:
    planting: Planting
    plant_id: str
    bed_id: str
    count: int
    area_m2: float
    reason: str
    yield_kg: float
    minutes_week: float
    water_l_week: float
    sowings: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "bed_id": self.bed_id,
            "count": self.count,
            "area_m2": round(self.area_m2, 2),
            "reason": self.reason,
            "yield_kg": round(self.yield_kg, 1),
            "minutes_week": round(self.minutes_week),
            "water_l_week": round(self.water_l_week),
            "sowings": self.sowings,
        }


@dataclass(slots=True)
class AutoplanResult:
    plantings: list[Planting] = field(default_factory=list)
    placements: list[Placement] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)  # {plant_id, reason, beds: {bed_id: reasons}}
    plan_from: int | None = None  # the season's plan did not exist: proposal made on this year's plan
    warnings: list[dict[str, Any]] = field(default_factory=list)  # {key, params}
    beds: list[str] = field(default_factory=list)
    compost_kg: float = 0.0
    fertilizer_g: float = 0.0

    @property
    def yield_kg(self) -> float:
        return round(sum(p.yield_kg for p in self.placements), 1)

    @property
    def minutes_week(self) -> float:
        return round(sum(p.minutes_week for p in self.placements))

    @property
    def water_l_week(self) -> float:
        return round(sum(p.water_l_week for p in self.placements))

    def to_dict(self) -> dict[str, Any]:
        from .serde import to_dict

        return {
            "plantings": [to_dict(p) for p in self.plantings],
            "placements": [p.to_dict() for p in self.placements],
            "skipped": self.skipped,
            "plan_from": self.plan_from,
            "warnings": self.warnings,
            "beds": self.beds,
            "summary": {
                "crops": len({p.plant_id for p in self.placements}),
                "plantings": len(self.plantings),
                "yield_kg": self.yield_kg,
                "minutes_week": self.minutes_week,
                "water_l_week": self.water_l_week,
                "compost_kg": round(self.compost_kg, 1),
                "fertilizer_g": round(self.fertilizer_g),
            },
        }


# --------------------------------------------------------------------------- #
# 1. What and how much
# --------------------------------------------------------------------------- #
def _goal_match(plant: Plant, goal: str) -> bool:
    tags = set(plant.tags)
    if goal == "fresh":
        return plant.category is PlantCategory.VEGETABLE and bool(tags & {"quick", "leafy", "fruiting", "succession"})
    if goal == "storage":
        return "storage" in tags
    if goal == "herbs":
        return plant.category is PlantCategory.HERB
    if goal == "pollinators":
        return bool(tags & {"pollinators", "flower"}) and plant.category in (PlantCategory.FLOWER, PlantCategory.HERB)
    if goal == "winter":
        return "winter" in tags
    if goal == "perennials":
        return plant.perennial and plant.category in (PlantCategory.VEGETABLE, PlantCategory.FRUIT)
    if goal == "easy":
        return plant.category is PlantCategory.VEGETABLE and not plant.care and "fruiting" not in tags
    return False


def crop_demand(db: PlantDatabase, resources: GardenResources, max_crops: int) -> list[CropDemand]:
    """Ordered list of crops with plant counts for the household."""
    popular = {pid: i for i, pid in enumerate(POPULAR)}
    excluded = set(resources.excluded)
    chosen: dict[str, CropDemand] = {}
    household = max(resources.household_size, 1)

    def add(plant: Plant, priority: float, reason: str) -> None:
        if plant.id in excluded or plant.id in chosen:
            return
        if "green_manure" in plant.tags:
            return
        per_person = plant.plants_per_person
        count = max(1, math.ceil(per_person * household)) if per_person > 0 else 1
        if plant.category is PlantCategory.HERB or plant.perennial:
            count = max(1, min(count, 2 + household // 3))  # herbs scale weakly
        area = count * plant.spacing_cm * max(plant.row_spacing_cm, plant.spacing_cm)
        chosen[plant.id] = CropDemand(plant, count, area, priority, reason)

    for i, pid in enumerate(resources.wanted):
        plant = db.get(pid)
        if plant is not None:
            add(plant, 1000.0 - i, "wanted")
    if resources.freedom == "strict":
        return sorted(chosen.values(), key=lambda d: -d.priority)
    if not resources.allow_perennials:
        excluded |= {p.id for p in db.all() if p.perennial and p.id not in resources.wanted}
    if resources.freedom == "free":
        max_crops += 6
    goals = [g for g in resources.goals if g in GOALS] or ["fresh"]
    if resources.year_round:
        goals += [g for g in ("winter", "storage") if g not in goals]
    families: dict[str, int] = {}
    for g_idx, goal in enumerate(goals):
        candidates = [p for p in db.all() if _goal_match(p, goal)]
        candidates.sort(key=lambda p: (popular.get(p.id, 999), p.id))
        quota = max(2, round(max_crops * (0.6 if g_idx == 0 else 0.4 / max(len(goals) - 1, 1))))
        taken = 0
        for plant in candidates:
            if taken >= quota or len(chosen) >= max_crops:
                break
            if plant.id in popular or goal not in ("fresh", "herbs"):
                # Keep families varied so a rotation stays possible.
                if families.get(plant.family, 0) >= 3 and plant.category is PlantCategory.VEGETABLE:
                    continue
                before = len(chosen)
                add(plant, 500.0 - g_idx * 100 - popular.get(plant.id, 99), f"goal:{goal}")
                if len(chosen) > before:
                    families[plant.family] = families.get(plant.family, 0) + 1
                    taken += 1
    result = sorted(chosen.values(), key=lambda d: -d.priority)[: max(max_crops, len(resources.wanted))]
    if resources.add_pollinators and any(d.plant.pollination in ("insects", "partner") for d in result):
        have = {d.plant.id for d in result}
        if not any("pollinators" in d.plant.tags and d.plant.category is PlantCategory.FLOWER for d in result):
            for pid in POLLINATOR_FLOWERS[:2]:
                plant = db.get(pid)
                if plant is not None and pid not in have and pid not in excluded:
                    count = 3 + household // 2
                    area = count * plant.spacing_cm * max(plant.row_spacing_cm, plant.spacing_cm)
                    result.append(CropDemand(plant, count, area, 100.0, "pollinators"))
    return result


def scale_to_capacity(demands: list[CropDemand], beds: Sequence[GardenBed]) -> float:
    """Shrink the wish list proportionally when it exceeds the bed area.

    Wanted crops keep a larger share (square-root scaling).  Returns the
    factor applied to the other crops (1.0 = everything fits).
    """
    capacity = FILL_FACTOR * sum(max(b.width_cm - 2 * MARGIN_CM, 0) * max(b.length_cm - 2 * MARGIN_CM, 0) for b in beds)
    total = sum(d.area_cm2 for d in demands)
    if total <= capacity or total <= 0:
        return 1.0
    wanted = sum(d.area_cm2 for d in demands if d.reason == "wanted")
    rest = total - wanted
    factor = capacity / total
    wanted_factor = min(1.0, factor**0.5)
    if rest > 0:
        factor = max(min((capacity - wanted * wanted_factor) / rest, 1.0), 0.05)
    for d in demands:
        f = wanted_factor if d.reason == "wanted" else factor
        min_area = d.plant.spacing_cm * max(d.plant.row_spacing_cm, d.plant.spacing_cm)
        new_area = max(d.area_cm2 * f, min_area)
        d.count = max(1, round(d.count * new_area / d.area_cm2))
        d.area_cm2 = new_area
    return factor


# --------------------------------------------------------------------------- #
# 2. Where
# --------------------------------------------------------------------------- #
def _prefers_glass(plant: Plant) -> bool:
    return plant.greenhouse.suitability is Suitability.YES and (
        (plant.frost_tolerance is FrostTolerance.TENDER and plant.min_temp_c >= 8) or "greenhouse" in plant.tags
    )


def feasibility(
    plant: Plant, bed: GardenBed, zone: Zone | None, data: GardenData, season: int, today: date, match_zone: bool = True
) -> list[dict[str, Any]]:
    """Why ``plant`` cannot go into ``bed`` this season (empty list = it can).

    Each reason is ``{"code": ..., "params": {...}}`` so the UI and the
    analysis view can explain it in plain words.
    """
    reasons: list[dict[str, Any]] = []
    enclosed = bool(zone and zone.is_enclosed)
    if match_zone and zone is not None:
        allowed = ZONE_CATEGORIES.get(zone.type.value)
        if allowed and plant.category.value not in allowed:
            reasons.append({"code": "zone_type", "params": {"zone": zone.name, "zone_type": zone.type.value,
                                                            "category": plant.category.value, "allowed": list(allowed)}})  # fmt: skip
    if enclosed and plant.greenhouse.suitability is Suitability.NO:
        reasons.append({"code": "not_under_glass", "params": {"zone": zone.name if zone else ""}})
    anchors = season_anchors(data.settings.region, season)
    probe = Planting("probe", plant.id, bed.id, season, method=default_method(plant))
    tl = planting_timeline(probe, plant, anchors, zone, today)
    if tl.late:
        window = tl.sow_window or tl.transplant_window
        reasons.append(
            {"code": "too_late", "params": {"season": season, "until": window.end.isoformat() if window else None}}
        )
    elif not enclosed and not anchors.frost_free and plant.frost_tolerance is FrostTolerance.TENDER:
        # A tender crop must give a harvest before the first autumn frost.
        if tl.harvest_start > anchors.first_frost - timedelta(days=14):
            reasons.append({"code": "frost_before_harvest", "params": {
                "harvest": tl.harvest_start.isoformat(), "frost": anchors.first_frost.isoformat()}})  # fmt: skip
    return reasons


def _feasible(
    plant: Plant, bed: GardenBed, zone: Zone | None, data: GardenData, season: int, today: date, match_zone: bool = True
) -> bool:
    return not feasibility(plant, bed, zone, data, season, today, match_zone)


def _bed_score(
    demand: CropDemand,
    bed: GardenBed,
    zone: Zone | None,
    placed: Sequence[CropDemand],
    db: PlantDatabase,
    history: list[Any],
    season: int,
    respect: bool = True,
    why: list[dict[str, Any]] | None = None,
) -> float | None:
    plant = demand.plant
    enclosed = bool(zone and zone.is_enclosed)
    score = 0.0
    if _prefers_glass(plant):
        score += 40 if enclosed else -10
    elif enclosed:
        score -= 25  # keep greenhouse space for crops that need it
    probe = Planting("probe", plant.id, bed.id, season)
    for finding in check_rotation(probe, bed, history, db):
        if finding.severity == "error":
            if why is not None:
                why.append({"code": "rotation", "params": {"family": finding.family, "season": finding.conflicting_season,
                                                           "years": finding.years_required}})  # fmt: skip
            return None
        score -= 20
    for other in placed:
        rel = db.relation(plant.id, other.plant.id)
        if rel.relation is Relation.ENEMY and respect:
            if rel.strength >= 2:
                if why is not None:
                    why.append({"code": "bad_neighbour", "params": {"plant_id": other.plant.id}})
                return None
            score -= 15
        elif rel.relation is Relation.FRIEND:
            score += 6 * rel.strength
        if other.plant.family == plant.family:
            score -= 2  # monoculture beds spread pests
    shade = bed.shade_pct if bed.shade_pct is not None else (zone.microclimate.shade_pct if zone else 0)
    if shade >= 30:
        score += 5 if plant.shade_tolerant else -15
    if bed.kind is BedKind.CONTAINER:
        score += 10 if "container" in plant.tags or plant.category is PlantCategory.HERB else -20
    if plant.perennial and bed.kind is not BedKind.CONTAINER:
        score -= 3  # perennials block a bed for years; prefer an edge bed
    return score


# --------------------------------------------------------------------------- #
# 3. Layout (shelf packing, tall crops away from the sun)
# --------------------------------------------------------------------------- #
def _item_for(demand: CropDemand, bed: GardenBed) -> _Item:
    plant = demand.plant
    row = max(plant.row_spacing_cm, plant.spacing_cm)
    usable_w = max(
        bed.width_cm - 2 * MARGIN_CM, 1.0
    )  # a bed with no room left never divides by zero (packing refuses it)
    depth = row
    width = demand.area_cm2 / depth
    if width > usable_w:
        width = usable_w
        depth = math.ceil(demand.area_cm2 / width / row) * row
    width = max(width, plant.spacing_cm)
    return _Item(demand, round(width), round(depth))


def _pack(items: list[_Item], bed: GardenBed, hemisphere: Hemisphere) -> bool:
    """Shelf-pack items into the bed; returns False if they do not fit."""
    usable_w = bed.width_cm - 2 * MARGIN_CM
    usable_l = bed.length_cm - 2 * MARGIN_CM
    order = sorted(items, key=lambda i: (-i.demand.plant.height_cm, -i.depth))
    y, shelf_depth, x = 0.0, 0.0, 0.0
    for item in order:
        if item.width > usable_w:
            return False
        if x + item.width > usable_w + 0.1:
            y += shelf_depth
            x, shelf_depth = 0.0, 0.0
        item.x, item.y = x, y
        x += item.width
        shelf_depth = max(shelf_depth, item.depth)
    if y + shelf_depth > usable_l + 0.1:
        return False
    for item in order:
        item.x += MARGIN_CM
        if hemisphere is Hemisphere.NORTH:
            item.y += MARGIN_CM  # canvas y grows south: tall crops at the north edge
        else:
            item.y = bed.length_cm - MARGIN_CM - item.y - item.depth
    return True


def _row(plant: Plant) -> float:
    return max(plant.row_spacing_cm, plant.spacing_cm)


def _set_size(item: _Item, width: float, depth: float) -> None:
    plant = item.demand.plant
    item.width, item.depth = round(width), round(depth)
    item.demand.count = max(1, int(item.width // plant.spacing_cm) * max(1, int(item.depth // _row(plant))))
    item.demand.area_cm2 = item.width * item.depth


def _shrink(item: _Item, bed: GardenBed, others: list[_Item], hemisphere: Hemisphere) -> bool:
    """Make an item fit by trimming it - and if needed its neighbours.

    Nothing is squeezed below ``MIN_SHRINK`` of its wanted area (a handful of
    carrots is not worth a strip): then the crop is reported as skipped.
    """
    row = _row(item.demand.plant)
    # A crop the gardener asked for is better small than missing.
    floor = item.orig_area * (MIN_SHRINK_WANTED if item.demand.reason == "wanted" else MIN_SHRINK)
    original = [(o, o.width, o.depth) for o in others]

    def try_self() -> bool:
        depth = item.depth
        while depth >= row:
            width = min(item.width, item.orig_area / depth) if depth < item.depth else item.width
            while width * depth >= floor and width >= item.demand.plant.spacing_cm:
                probe = _Item(item.demand, round(width), round(depth), orig_area=item.orig_area)
                if _pack([*others, probe], bed, hemisphere):
                    _set_size(item, probe.width, probe.depth)
                    return True
                width *= 0.8
            depth -= row
        return False

    if try_self():
        return True
    # Make room: take one row off the deepest neighbour that can spare it.
    for _ in range(8):
        spare = [o for o in others if o.demand.reason != "wanted" and o.depth >= 2 * _row(o.demand.plant) - 0.1]
        spare = [o for o in spare if (o.depth - _row(o.demand.plant)) * o.width >= o.orig_area * MIN_SHRINK]
        if not spare:
            break
        victim = max(spare, key=lambda o: o.depth)
        _set_size(victim, victim.width, victim.depth - _row(victim.demand.plant))
        if try_self():
            return True
    for o, width, depth in original:  # nothing gained: restore the neighbours
        _set_size(o, width, depth)
    return False


# --------------------------------------------------------------------------- #
# 4. Budgets
# --------------------------------------------------------------------------- #
def weekly_minutes(plant: Plant, area_m2: float, count: int, hand_watering_l: float) -> float:
    care = sum(rule.minutes * 7 / rule.interval_days for rule in plant.care if rule.interval_days)
    care += sum(rule.minutes / 8 for rule in plant.care if not rule.interval_days)  # one-off, spread
    if plant.feeding_interval_days and not any(r.task is TaskType.FEED for r in plant.care):
        care += 10 * 7 / plant.feeding_interval_days
    harvest = 10.0 if plant.continuous_harvest else 3.0
    return (
        MINUTES_PER_M2_WEEK * area_m2
        + care * min(1.0, 0.3 + count / 10)
        + harvest
        + hand_watering_l / HAND_WATERING_L_PER_MIN
    )


def peak_water_l_week(plant: Plant, area_m2: float, enclosed: bool) -> float:
    kc_mid = (plant.kc + [1.0, 1.0])[1]
    daily = PEAK_ET0_MM * kc_mid * 0.7 if enclosed else max(PEAK_ET0_MM * kc_mid - EFFECTIVE_RAIN_MM, 0.0)
    return daily * 7 * area_m2


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main_reason(why_by_bed: dict[str, list[dict[str, Any]]]) -> str:
    """The reason that blocks a crop in most beds (``no_suitable_bed`` when there are none)."""
    counts: dict[str, int] = {}
    for reasons in why_by_bed.values():
        for code in {r["code"] for r in reasons}:
            counts[code] = counts.get(code, 0) + 1
    if not counts:
        return "no_suitable_bed"
    return max(counts, key=lambda c: (counts[c], c))


def autoplan(
    data: GardenData,
    db: PlantDatabase,
    options: AutoplanOptions,
    *,
    today: date,
    resources: GardenResources | None = None,
    id_factory: Callable[[], str] = new_id,
) -> AutoplanResult:
    resources = resources or data.settings.resources
    season = options.season
    hemisphere = resolve_profile(data.settings.region).hemisphere
    result = AutoplanResult()

    # The garden plan of the season being filled (not necessarily today's garden).
    layout = layout_for(data, season)
    if layout is None:
        # No plan for that year yet: propose on the most recent earlier plan;
        # applying the proposal copies that plan into the year.
        earlier = sorted(s for s in plan_seasons(data) if s < season)
        if not earlier:
            result.warnings.append({"key": "autoplan.no_plan", "params": {"season": season}})
            return result
        result.plan_from = earlier[-1]
        layout = layout_for(data, earlier[-1])
        result.warnings.append({"key": "autoplan.plan_from", "params": {"season": season, "from": earlier[-1]}})
    assert layout is not None
    all_beds = list(layout.beds)
    zones = {z.id: z for z in layout.zones}
    occupied = {p.bed_id for p in data.plantings if present_in(p, False, season)}
    if options.bed_ids is not None:
        beds = [b for b in all_beds if b.id in options.bed_ids]
        if not options.replace:
            for bed in beds:
                if bed.id in occupied:
                    result.warnings.append({"key": "autoplan.bed_not_empty", "params": {"bed": bed.name}})
            beds = [b for b in beds if b.id not in occupied]
    elif options.replace:
        beds = list(all_beds)
    else:
        beds = [b for b in all_beds if b.id not in occupied]
    result.beds = [b.id for b in beds]
    if not beds:
        result.warnings.append({"key": "autoplan.no_beds", "params": {}})
        return result

    history = list(rotation_history(data.rotation_history, data.plantings, db))
    learned = learned_yields(data, db)  # your own kg/m² weigh in against the database average
    demands = crop_demand(db, resources, options.max_crops)
    scale_to_capacity(demands, beds)
    assigned: dict[str, list[_Item]] = {b.id: [] for b in beds}
    budget_min = resources.hours_per_week * 60 if resources.hours_per_week else None
    budget_water = resources.water_liters_per_week
    budget_compost = resources.compost_kg
    used_min = used_water = 0.0

    for demand in demands:
        plant = demand.plant
        ranked: list[tuple[float, GardenBed]] = []
        why_by_bed: dict[str, list[dict[str, Any]]] = {}
        for bed in beds:
            zone = zones.get(bed.zone_id)
            reasons = feasibility(plant, bed, zone, data, season, today, resources.match_zone_type)
            if reasons:
                why_by_bed[bed.id] = reasons
                continue
            why: list[dict[str, Any]] = []
            score = _bed_score(
                demand,
                bed,
                zone,
                [i.demand for i in assigned[bed.id]],
                db,
                history,
                season,
                resources.respect_companions,
                why,
            )
            if score is not None:
                ranked.append((score, bed))
            else:
                why_by_bed[bed.id] = why
        if not ranked:
            result.skipped.append({"plant_id": plant.id, "reason": main_reason(why_by_bed), "beds": why_by_bed})
            continue
        ranked.sort(key=lambda r: -r[0])
        placed_in: GardenBed | None = None
        for _score, bed in ranked:
            item = _item_for(demand, bed)
            if _pack([*assigned[bed.id], item], bed, hemisphere) or (
                demand.reason != "wanted" and _shrink(item, bed, assigned[bed.id], hemisphere)
            ):
                placed_in = bed
                break
            if demand.reason == "wanted" and _shrink(item, bed, assigned[bed.id], hemisphere):
                placed_in = bed
                break
        if placed_in is None:
            result.skipped.append({"plant_id": plant.id, "reason": "no_space"})
            continue
        zone = zones.get(placed_in.zone_id)
        enclosed = bool(zone and zone.is_enclosed)
        area_m2 = item.width * item.depth / 10_000
        water = peak_water_l_week(plant, area_m2, enclosed)
        hand = 0.0 if resources.irrigation and placed_in.irrigation_entity else water
        minutes = weekly_minutes(plant, area_m2, demand.count, hand)
        if budget_min is not None and used_min + minutes > budget_min and demand.reason != "wanted":
            result.skipped.append({"plant_id": plant.id, "reason": "time_budget"})
            continue
        if budget_water is not None and used_water + water > budget_water and demand.reason != "wanted":
            result.skipped.append({"plant_id": plant.id, "reason": "water_budget"})
            continue
        used_min += minutes
        used_water += water
        assigned[placed_in.id].append(item)

    # Final layout + plantings
    for bed in beds:
        items = assigned[bed.id]
        if not items:
            continue
        _pack(items, bed, hemisphere)
        zone = zones.get(bed.zone_id)
        enclosed = bool(zone and zone.is_enclosed)
        plants_here = [i.demand.plant for i in items]
        fert = bed_fertilizer_plan(bed.area_m2, plants_here, options.lang, bed.latest_soil_test)
        result.compost_kg += fert.compost_kg
        result.fertilizer_g += fert.base_fertilizer_g
        for item in items:
            plant, demand = item.demand.plant, item.demand
            row = max(plant.row_spacing_cm, plant.spacing_cm)
            layout = (
                LayoutMode.SINGLE
                if demand.count == 1
                else LayoutMode.ROW
                if item.depth <= row * 1.5
                else LayoutMode.BLOCK
            )
            base = Planting(
                id=id_factory(), plant_id=plant.id, bed_id=bed.id, season=season, layout=layout,
                x_cm=round(item.x), y_cm=round(item.y), width_cm=round(item.width), length_cm=round(item.depth),
                method=default_method(plant),
                notes="autofill",
            )  # fmt: skip
            sowings = 1
            plantings = [base]
            if (
                "succession" in plant.tags
                and plant.succession_interval_days
                and item.width >= plant.spacing_cm * SUCCESSION_SOWINGS * 2
            ):
                anchors = season_anchors(data.settings.region, season)
                expanded, _dropped = expand_succession(
                    base, plant, anchors, zone, count=SUCCESSION_SOWINGS, placement="split", id_factory=id_factory
                )
                if expanded:
                    plantings = expanded
                    for p in plantings:
                        p.notes = "autofill"
                    sowings = len(plantings)
            result.plantings.extend(plantings)
            area_m2 = item.width * item.depth / 10_000
            water = peak_water_l_week(plant, area_m2, enclosed)
            hand = 0.0 if resources.irrigation and bed.irrigation_entity else water
            result.placements.append(
                Placement(
                    planting=base, plant_id=plant.id, bed_id=bed.id, count=demand.count, area_m2=area_m2,
                    reason=demand.reason, yield_kg=learned.get(plant.id, plant.yield_kg_m2) * area_m2 if plant.harvestable else 0.0,
                    minutes_week=weekly_minutes(plant, area_m2, demand.count, hand), water_l_week=water,
                    sowings=sowings,
                )
            )  # fmt: skip

    if budget_compost is not None and result.compost_kg > budget_compost:
        result.warnings.append(
            {"key": "autoplan.compost_short", "params": {"need": round(result.compost_kg), "have": budget_compost}}
        )
    if budget_min is not None and result.minutes_week > budget_min:
        result.warnings.append(
            {"key": "autoplan.time_over", "params": {"need": result.minutes_week, "have": round(budget_min)}}
        )
    wanted_missing = [s["plant_id"] for s in result.skipped if s["plant_id"] in resources.wanted]
    if wanted_missing:
        result.warnings.append({"key": "autoplan.wanted_missing", "params": {"plants": wanted_missing}})
    if not resources.irrigation and result.water_l_week > 150:
        result.warnings.append({"key": "autoplan.consider_irrigation", "params": {"liters": result.water_l_week}})
    return result


class _NoPlant:
    perennial = False
