"""Write operations shared by services and the websocket API.

Keeping them in one place guarantees an automation calling
``garden_manager.complete_task`` and a click in the panel behave identically.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
import math
from typing import TYPE_CHECKING, Any
import uuid

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_TASK_COMPLETED, SIGNAL_LAYOUT_CHANGED
from .engine import cooking, seasons
from .engine.models import (
    CookbookRecipe,
    Expense,
    Feature,
    GardenBed,
    GardenSettings,
    HarvestEntry,
    IrrigationEvent,
    JournalEntry,
    Plant,
    Planting,
    PlantingStatus,
    SeedPacket,
    SoilTest,
    Task,
    TaskNote,
    TaskPriority,
    TaskStatus,
    TaskType,
    Zone,
    present_in,
)
from .engine.plantdb import validate_plant_dict
from .engine.region import season_for_date
from .engine.serde import from_dict, to_dict
from .engine.tasks import (
    CompletionResult,
    PostponeResult,
    complete_task,
    make_user_task,
    postpone_task,
)

if TYPE_CHECKING:
    from . import GardenRuntime


class RevisionConflict(HomeAssistantError):
    """The plan was changed elsewhere since the client loaded it."""


def _err(key: str, **placeholders: Any) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={k: str(v) for k, v in placeholders.items()},
    )


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
def resolve_bed(runtime: GardenRuntime, ref: str | None) -> GardenBed | None:
    """Accept a bed id or (case-insensitive) bed name - handy in YAML."""
    if not ref:
        return None
    data = runtime.repo.data
    bed = data.bed(ref) or next((b for b in data.beds if b.name.casefold() == ref.casefold()), None)
    if bed is None:
        raise _err("unknown_bed", bed=ref)
    return bed


@callback
def op_add_task(
    runtime: GardenRuntime,
    *,
    title: str,
    due: date | None = None,
    task_type: str = "custom",
    description: str = "",
    priority: str = "normal",
    minutes: int | None = None,
    bed: str | None = None,
    planting_id: str | None = None,
    recurrence_days: int | None = None,
    until: date | None = None,
) -> str:
    data = runtime.repo.data
    bed_obj = resolve_bed(runtime, bed)
    if planting_id and data.planting(planting_id) is None:
        raise _err("unknown_planting", planting=planting_id)
    task = make_user_task(
        title=title,
        due=due or dt_util.now().date(),
        now=dt_util.now(),
        task_type=TaskType(task_type),
        description=description,
        priority=TaskPriority(priority),
        minutes=minutes,
        bed_id=bed_obj.id if bed_obj else None,
        zone_id=bed_obj.zone_id if bed_obj else None,
        planting_id=planting_id,
        recurrence_days=recurrence_days,
        until=until,
    )
    data.tasks.append(task)
    runtime.repo.async_changed("tasks")
    return task.id


@callback
def op_complete_task(
    hass: HomeAssistant,
    runtime: GardenRuntime,
    task_id: str,
    *,
    note: str | None = None,
    photos: Sequence[str] = (),
    skipped: bool = False,
    user_id: str | None = None,
) -> CompletionResult:
    data = runtime.repo.data
    existing = data.task(task_id)
    was_open = existing is not None and existing.is_open
    try:
        result = complete_task(
            data,
            task_id,
            now=dt_util.now(),
            today=dt_util.now().date(),
            note=note,
            photos=photos,
            author=user_id,
            skipped=skipped,
            lang=runtime.coordinator.lang,
        )
    except KeyError as err:
        raise _err("unknown_task", task=task_id) from err
    task = result.task
    if not was_open:
        return result  # already done (a second dashboard, a retried automation): nothing to book twice
    bed = data.bed(task.bed_id) if task.bed_id else None
    if task.type is TaskType.WATER and not skipped and bed is not None and bed.area_m2 > 0:
        # A ticked-off watering task feeds the bed's water balance.
        liters = float(task.title_params.get("liters") or 0)
        if liters > 0:
            data.irrigation_log.append(
                IrrigationEvent(bed.id, dt_util.now(), round(liters / bed.area_m2, 1), liters, source="task")
            )
    runtime.repo.async_changed("plan" if result.planting_changed else "tasks")
    hass.bus.async_fire(
        EVENT_TASK_COMPLETED,
        {
            "task_id": result.task.id,
            "type": result.task.type.value,
            "title": result.task.title,
            "skipped": skipped,
            "planting_id": result.task.planting_id,
            "bed_id": result.task.bed_id,
            "next_task_id": result.next_task.id if result.next_task else None,
        },
    )
    return result


@callback
def op_postpone_task(
    runtime: GardenRuntime,
    task_id: str,
    *,
    days: int | None = None,
    to: date | None = None,
    reason: str | None = None,
    cascade: bool = True,
) -> PostponeResult:
    try:
        result = postpone_task(
            runtime.repo.data, task_id, now=dt_util.now(), days=days, to=to, reason=reason, cascade=cascade
        )
    except KeyError as err:
        raise _err("unknown_task", task=task_id) from err
    runtime.repo.async_changed("tasks")
    return result


@callback
def op_update_task(runtime: GardenRuntime, task_id: str, changes: Mapping[str, Any]) -> None:
    task = runtime.repo.data.task(task_id)
    if task is None:
        raise _err("unknown_task", task=task_id)
    try:  # convert everything first: a refused change leaves the task as it was
        priority = TaskPriority(changes["priority"]) if "priority" in changes else None
        minutes = int(changes["estimated_minutes"]) if "estimated_minutes" in changes else None
    except (TypeError, ValueError) as err:
        raise _err("invalid_task") from err
    if "title" in changes:
        task.title = str(changes["title"])
        task.title_key = None
        task.text_modified = True
    if "description" in changes:
        task.description = str(changes["description"])
        task.text_modified = True
    if priority is not None:
        task.priority = priority
    if minutes is not None:
        task.estimated_minutes = minutes
    if changes.get("note"):
        task.notes.append(TaskNote(dt_util.now(), str(changes["note"])))
    if "photos" in changes:
        task.photos = [str(p) for p in changes["photos"]]
    if "assignee" in changes:
        task.assignee = str(changes["assignee"]) or None if changes["assignee"] else None
    if changes.get("reopen"):
        task.status = TaskStatus.OPEN
        task.completed_at = None
    task.user_modified = True
    task.updated_at = dt_util.now()
    runtime.repo.async_changed("tasks")


@callback
def op_delete_task(runtime: GardenRuntime, task_id: str) -> None:
    data = runtime.repo.data
    task = data.task(task_id)
    if task is None:
        raise _err("unknown_task", task=task_id)
    if task.key and task.source.value != "user":
        # Generated tasks would be re-created; mark skipped instead.
        task.status = TaskStatus.SKIPPED
        task.completed_at = dt_util.now()
    else:
        data.tasks.remove(task)
    runtime.repo.async_changed("tasks")


# --------------------------------------------------------------------------- #
# Plan
# --------------------------------------------------------------------------- #
def _sized(*sizes: Any) -> bool:
    """Real, positive and finite sizes (a NaN or an infinity never passes)."""
    return all(isinstance(v, (int, float)) and math.isfinite(v) and 0 < v <= 1_000_000 for v in sizes)


def validate_layout(
    zones: list[Zone],
    beds: list[GardenBed],
    plantings: list[Planting],
    known_plants: set[str],
    other_beds: set[str] = frozenset(),  # type: ignore[assignment]
) -> None:
    """Check one season's plan; plantings may also sit on beds of other seasons' plans."""
    zone_ids = {z.id for z in zones}
    bed_ids = set()
    for bed in beds:
        if bed.zone_id not in zone_ids:
            raise _err("invalid_plan", reason=f"bed {bed.name} has unknown zone")
        if not _sized(bed.width_cm, bed.length_cm):
            raise _err("invalid_plan", reason=f"bed {bed.name} has no size")
        bed_ids.add(bed.id)
    for planting in plantings:
        if planting.bed_id not in bed_ids and planting.bed_id not in other_beds:
            raise _err("invalid_plan", reason=f"planting {planting.id} has unknown bed")
        if planting.plant_id not in known_plants:
            raise _err("invalid_plan", reason=f"unknown plant {planting.plant_id}")
    if len({z.id for z in zones}) != len(zones) or len(bed_ids) != len(beds):
        raise _err("invalid_plan", reason="duplicate ids")


def _live_layout_snapshot(data: Any) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    return [(z.id, z.name, z.type) for z in data.zones], [(b.id, b.name) for b in data.beds]


def _sync_devices(hass: HomeAssistant, runtime: GardenRuntime, before: tuple[list, list]) -> None:
    """After the live garden changed: drop devices of removed zones/beds, rebuild entities."""
    data = runtime.repo.data
    old_zones, old_beds = before
    removed = ({z[0] for z in old_zones} - {z.id for z in data.zones}) | (
        {b[0] for b in old_beds} - {b.id for b in data.beds}
    )
    if removed:
        _remove_devices(hass, runtime, removed)
    if (old_zones, old_beds) != _live_layout_snapshot(data):
        async_dispatcher_send(hass, SIGNAL_LAYOUT_CHANGED)


_BEFORE_HARVEST = frozenset((
    PlantingStatus.PLANNED, PlantingStatus.SOWN_INDOORS, PlantingStatus.SOWN, PlantingStatus.TRANSPLANTED,
))  # fmt: skip


@callback
def op_save_plan(
    hass: HomeAssistant,
    runtime: GardenRuntime,
    *,
    base_revision: int | None,
    zones: list[dict[str, Any]],
    beds: list[dict[str, Any]],
    plantings: list[dict[str, Any]],
    features: list[dict[str, Any]] | None = None,
    season: int | None = None,
) -> int:
    """Save the garden plan of ``season`` (default: the live garden) and all plantings."""
    repo = runtime.repo
    data = repo.data
    if base_revision is not None and base_revision != data.revision:
        raise RevisionConflict(f"revision {base_revision} != {data.revision}")
    try:
        new_zones = [from_dict(Zone, z) for z in zones]
        new_beds = [from_dict(GardenBed, b) for b in beds]
        new_plantings = [from_dict(Planting, p) for p in plantings]
        new_features = [from_dict(Feature, f) for f in features] if features is not None else None
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_plan", reason=str(err)) from err
    if season is None:
        season = data.layout_season if data.layout_season is not None else 0
    current = seasons.layout_for(data, season)
    other_beds = seasons.all_bed_ids(data) - {b.id for b in (current.beds if current else [])}
    validate_layout(new_zones, new_beds, new_plantings, {p.id for p in repo.db.all()}, other_beds)

    # Soil tests are edited through their own commands; a planner draft that
    # was opened earlier must not drop the ones added since.
    old_tests = {b.id: b.soil_tests for b in (current.beds if current else [])}
    for bed in new_beds:
        if bed.id in old_tests:
            bed.soil_tests = old_tests[bed.id]
    # What Hortulus measured and learned itself is kept from the server, never from a draft:
    # the flow from the meter, the water factor, and the heater energy.
    old_beds = {b.id: b for b in (current.beds if current else [])}
    for bed in new_beds:
        if (old := old_beds.get(bed.id)) is not None:
            bed.measured_flow_lpm = old.measured_flow_lpm
            bed.water_factor, bed.water_factor_runs = old.water_factor, old.water_factor_runs
    old_zones = {z.id: z for z in (current.zones if current else [])}
    for zone in new_zones:
        if (old_zone := old_zones.get(zone.id)) is not None:
            zone.heater_kwh = old_zone.heater_kwh
    # Likewise the lifecycle that harvests record (first harvest, "harvesting"): a draft opened
    # before the first harvest must not undo it.
    old_plantings = {p.id: p for p in data.plantings}
    for p in new_plantings:
        was = old_plantings.get(p.id)
        if was is not None and was.harvest_started_on is not None and p.harvest_started_on is None:
            p.harvest_started_on = was.harvest_started_on
            if was.status in (PlantingStatus.HARVESTING, PlantingStatus.FINISHED) and p.status in _BEFORE_HARVEST:
                p.status = was.status  # never back to before the harvest, nor reopen a finished crop
    before = _live_layout_snapshot(data)
    features_now = new_features if new_features is not None else (current.features if current else [])
    live = seasons.store_layout(data, season, new_zones, new_beds, features_now, now=dt_util.now())
    data.plantings = new_plantings
    repo.async_changed("plan")
    if live:
        _sync_devices(hass, runtime, before)
    return data.revision


@callback
def op_delete_layout(runtime: GardenRuntime, season: int) -> None:
    """Remove a stored plan of another season (the live garden stays)."""
    data = runtime.repo.data
    if season == data.layout_season:
        raise _err("invalid_plan", reason="the current garden plan cannot be deleted")
    in_use = {b.id for b in (seasons.layout_for(data, season) or seasons.GardenLayout()).beds}
    live_beds = seasons.all_bed_ids(data) - in_use
    if any(
        p.bed_id in in_use and p.bed_id not in live_beds and seasons.present_in(p, False, season)
        for p in data.plantings
    ):
        raise _err("invalid_plan", reason="plantings still use this plan")
    if seasons.delete_layout(data, season):
        runtime.repo.async_changed("plan")


@callback
def op_year_transition(
    hass: HomeAssistant,
    runtime: GardenRuntime,
    from_season: int,
    *,
    layout: str = "copy",
    zone_ids: list[str] | None = None,
    feature_ids: list[str] | None = None,
    planting_ids: list[str] = (),  # type: ignore[assignment]
    activate: bool = True,
) -> dict[str, Any]:
    """Explicit year-end transition: carry the chosen plan and crops into next year."""
    data = runtime.repo.data
    if data.layout_season is not None and from_season + 1 <= data.layout_season:
        raise _err("invalid_plan", reason=f"{from_season} is already closed")
    before = _live_layout_snapshot(data)
    result = seasons.apply(
        data,
        from_season,
        layout="keep" if layout == "keep" else "copy",
        zone_ids=zone_ids,
        feature_ids=feature_ids,
        planting_ids=planting_ids,
        activate=activate,
        now=dt_util.now(),
    )
    runtime.repo.async_changed("plan")
    if result.activated:
        _sync_devices(hass, runtime, before)
    return {
        "season": result.to_season,
        "carried": result.carried,
        "skipped": result.skipped,
        "activated": result.activated,
        "revision": data.revision,
    }


def _remove_devices(hass: HomeAssistant, runtime: GardenRuntime, ids: set[str]) -> None:
    registry = dr.async_get(hass)
    entry_id = runtime.coordinator.config_entry.entry_id
    for item_id in ids:
        device = registry.async_get_device(identifiers={(DOMAIN, f"{entry_id}_{item_id}")})
        if device:
            registry.async_remove_device(device.id)


# --------------------------------------------------------------------------- #
# Plants & settings
# --------------------------------------------------------------------------- #
@callback
def op_import_plan(hass: HomeAssistant, runtime: GardenRuntime, doc: Mapping[str, Any], mode: str) -> dict[str, int]:
    """Import a plan and keep devices/entities in sync (like ``op_save_plan``).

    Raises ``PlanImportError`` on invalid input; the caller turns it into a user error.
    """
    from .engine.planio import import_plan

    repo = runtime.repo
    old_zones = [(z.id, z.name, z.type) for z in repo.data.zones]
    old_beds = [(b.id, b.name) for b in repo.data.beds]
    counts = import_plan(repo.data, dict(doc), mode)
    repo.async_changed("import", bump_revision=False)
    removed = ({z[0] for z in old_zones} - {z.id for z in repo.data.zones}) | (
        {b[0] for b in old_beds} - {b.id for b in repo.data.beds}
    )
    if removed:
        _remove_devices(hass, runtime, removed)
    if old_zones != [(z.id, z.name, z.type) for z in repo.data.zones] or old_beds != [
        (b.id, b.name) for b in repo.data.beds
    ]:
        async_dispatcher_send(hass, SIGNAL_LAYOUT_CHANGED)
    return dict(counts)


def op_save_plant(runtime: GardenRuntime, raw: Mapping[str, Any], mode: str) -> Plant:
    repo = runtime.repo
    if mode == "override":
        plant_id = str(raw.get("id", ""))
        base = repo.db.get(plant_id)
        if base is None or base.source == "custom":
            raise _err("unknown_plant", plant=plant_id)
        # an edit adds to the earlier customisations of this plant (resetting is a separate action)
        patch = dict(repo.data.plant_overrides.get(plant_id, {}))
        for key, value in raw.items():
            if key in ("id", "source"):
                continue
            # names (and other per-language texts) are edited one language at a time
            patch[key] = (
                {**patch[key], **value} if isinstance(value, dict) and isinstance(patch.get(key), dict) else value
            )
        validate_plant_dict({**to_dict(base), **patch})
        repo.data.plant_overrides[plant_id] = patch
    else:
        try:
            plant = validate_plant_dict(raw)
        except ValueError as err:
            raise _err("invalid_plant", reason=str(err)) from err
        builtin = repo.db.get(plant.id)
        if builtin is not None and builtin.source != "custom":
            raise _err("invalid_plant", reason=f"id {plant.id} is used by the built-in database")
        repo.data.custom_plants = [p for p in repo.data.custom_plants if p.id != plant.id] + [plant]
    repo.async_changed("plants")
    result = repo.db.get(str(raw["id"]))
    assert result is not None
    return result


@callback
def op_delete_plant(runtime: GardenRuntime, plant_id: str) -> None:
    repo = runtime.repo
    if plant_id in repo.data.plant_overrides:
        del repo.data.plant_overrides[plant_id]  # reset to built-in
    else:
        if any(p.plant_id == plant_id for p in repo.data.plantings) or any(
            p.plant_id == plant_id for plan in repo.data.archived_plans for p in plan.plantings
        ):
            raise _err("plant_in_use", plant=plant_id)
        repo.data.custom_plants = [p for p in repo.data.custom_plants if p.id != plant_id]
    repo.async_changed("plants")


def _deep_merge(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@callback
def _validate_settings(settings: GardenSettings) -> None:
    """What the engine relies on: real frost dates, real clock times, finite numbers."""
    import dataclasses
    import re

    from .engine.region import season_anchors

    region = settings.region
    for name in ("last_frost", "first_frost"):
        value = getattr(region, name)
        if not re.fullmatch(r"\d{2}-\d{2}", str(value)):
            raise ValueError(f"{name} must be MM-DD")
        month, day = (int(x) for x in str(value).split("-"))
        if not 1 <= month <= 12 or not 1 <= day <= (29 if month == 2 else 30 if month in (4, 6, 9, 11) else 31):
            raise ValueError(f"{name} {value} is not a date")
    season_anchors(region, 2024)  # a leap year and an ordinary one both resolve
    season_anchors(region, 2025)

    def walk(obj: Any, path: str) -> None:
        if dataclasses.is_dataclass(obj):
            for f in dataclasses.fields(obj):
                walk(getattr(obj, f.name), f"{path}.{f.name}" if path else f.name)
        elif isinstance(obj, float) and not math.isfinite(obj):
            raise ValueError(f"{path} must be a finite number")
        elif isinstance(obj, str) and path.endswith("_time") and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", obj):
            raise ValueError(f"{path} must be HH:MM")

    walk(settings, "")
    irr = settings.irrigation
    for name in ("battery_full_pct", "butt_min_pct"):
        if not 0 <= getattr(irr, name) <= 100:
            raise ValueError(f"irrigation.{name} must be 0-100")
    for name in ("pump_power_w", "butt_pump_power_w"):
        if getattr(irr, name) < 0:
            raise ValueError(f"irrigation.{name} must not be negative")
    if not 1 <= settings.mirror_days <= 31:
        raise ValueError("mirror_days must be 1-31")


@callback
def op_reset_water_factor(runtime: GardenRuntime, bed_id: str) -> None:
    """Forget what adaptive irrigation learned for a bed (after re-digging it, a new sensor ...)."""
    bed = runtime.repo.data.bed(bed_id)
    if bed is None:
        raise _err("unknown_bed", bed=bed_id)
    bed.water_factor, bed.water_factor_runs = 1.0, 0
    runtime.repo.async_changed("plan", bump_revision=False)


def op_save_settings(runtime: GardenRuntime, patch: Mapping[str, Any]) -> GardenSettings:
    repo = runtime.repo
    merged = _deep_merge(to_dict(repo.data.settings), patch)
    # Mappings are edited key by key; an empty value removes the key.
    for key in ("assignment", "person_notify"):
        if isinstance(merged.get(key), dict):
            merged[key] = {k: v for k, v in merged[key].items() if v}
    prices = (merged.get("economy") or {}).get("prices")
    try:
        if isinstance(prices, dict):  # an empty price restores the default
            converted = {k: float(v) for k, v in prices.items() if v not in (None, "", 0)}
            if not all(math.isfinite(v) and v > 0 for v in converted.values()):
                raise ValueError("prices must be positive numbers")
            merged["economy"]["prices"] = converted
        candidate = from_dict(GardenSettings, merged)
        _validate_settings(candidate)
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_settings", reason=str(err)) from err
    repo.data.settings = candidate
    repo.async_changed("settings")
    return repo.data.settings


# --------------------------------------------------------------------------- #
# Plantings (services: add / update / remove) and autofill
# --------------------------------------------------------------------------- #
PLANTING_FIELDS = {
    "plant_id", "bed_id", "season", "layout", "x_cm", "y_cm", "width_cm", "length_cm", "count", "method",
    "status", "sow_date", "transplant_date", "sown_on", "transplanted_on", "harvest_started_on", "finished_on",
    "notes",
}  # fmt: skip


def _check_planting(runtime: GardenRuntime, planting: Planting) -> None:
    """A planting must sit on a bed of its own season's plan (or, without one, of any plan)."""
    repo = runtime.repo
    layout = seasons.layout_for(repo.data, planting.season)
    beds = {b.id for b in layout.beds} if layout is not None else seasons.all_bed_ids(repo.data)
    if planting.bed_id not in beds:
        raise _err("unknown_bed", bed=planting.bed_id)
    if repo.db.get(planting.plant_id) is None:
        raise _err("unknown_plant", plant=planting.plant_id)
    if not _sized(planting.width_cm, planting.length_cm) or not all(
        isinstance(v, (int, float)) and math.isfinite(v) for v in (planting.x_cm, planting.y_cm)
    ):
        raise _err("invalid_plan", reason="planting has no size")


@callback
def op_add_planting(runtime: GardenRuntime, raw: Mapping[str, Any]) -> Planting:
    from .engine.tasks import new_id

    repo = runtime.repo
    bed = resolve_bed(runtime, str(raw.get("bed_id") or raw.get("bed") or ""))
    if bed is None:
        raise _err("unknown_bed", bed=raw.get("bed_id") or raw.get("bed"))
    plant = repo.db.get(str(raw.get("plant_id", "")))
    if plant is None:
        raise _err("unknown_plant", plant=raw.get("plant_id"))
    fields = {k: v for k, v in raw.items() if k in PLANTING_FIELDS}
    fields["bed_id"] = bed.id
    fields.setdefault("season", dt_util.now().year)
    # Default footprint: one row across the bed at the crop's row spacing.
    fields.setdefault("width_cm", bed.width_cm)
    fields.setdefault("length_cm", max(plant.row_spacing_cm, plant.spacing_cm))
    fields.setdefault("layout", "row")
    try:
        planting = from_dict(Planting, {"id": new_id(), **_jsonable(fields)})
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_plan", reason=str(err)) from err
    _check_planting(runtime, planting)
    repo.data.plantings.append(planting)
    repo.async_changed("plan")
    return planting


@callback
def op_update_planting(runtime: GardenRuntime, planting_id: str, changes: Mapping[str, Any]) -> Planting:
    repo = runtime.repo
    current = repo.data.planting(planting_id)
    if current is None:
        raise _err("unknown_planting", planting=planting_id)
    patch = {k: v for k, v in changes.items() if k in PLANTING_FIELDS}
    if "bed" in changes and "bed_id" not in patch:
        bed = resolve_bed(runtime, str(changes["bed"]))
        if bed is None:
            raise _err("unknown_bed", bed=changes["bed"])
        patch["bed_id"] = bed.id
    try:
        updated = from_dict(Planting, {**to_dict(current), **_jsonable(patch)})
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_plan", reason=str(err)) from err
    _check_planting(runtime, updated)
    repo.data.plantings = [updated if p.id == planting_id else p for p in repo.data.plantings]
    repo.async_changed("plan")
    return updated


@callback
def op_update_plantings(runtime: GardenRuntime, planting_ids: list[str], changes: Mapping[str, Any]) -> list[Planting]:
    """The same change for several crops at once (one entry in the system log)."""
    repo = runtime.repo
    # status, dates, method, count, notes - never where, what or which year
    fixed = ("bed_id", "x_cm", "y_cm", "season", "plant_id")
    patch = {k: v for k, v in changes.items() if k in PLANTING_FIELDS and k not in fixed}
    if not patch:
        raise _err("invalid_plan", reason="nothing to change")
    by_id = {p.id: p for p in repo.data.plantings}
    updated: dict[str, Planting] = {}
    for pid in planting_ids:
        current = by_id.get(pid)
        if current is None:
            raise _err("unknown_planting", planting=pid)
        try:
            new = from_dict(Planting, {**to_dict(current), **_jsonable(patch)})
        except (TypeError, ValueError, KeyError) as err:
            raise _err("invalid_plan", reason=str(err)) from err
        _check_planting(runtime, new)
        updated[pid] = new
    repo.data.plantings = [updated.get(p.id, p) for p in repo.data.plantings]
    repo.async_changed("plan")
    return list(updated.values())


@callback
def op_fix_issue(
    hass: HomeAssistant, runtime: GardenRuntime, code: str, params: Mapping[str, Any], refs: Mapping[str, list[str]]
) -> dict[str, Any]:
    """Repair a problem the analysis found (logged, so it can be undone)."""
    from .engine import diagnose
    from .engine.region import season_for_date

    data = runtime.repo.data
    before = _live_layout_snapshot(data)
    try:
        done = diagnose.fix_issue(
            data, code, params, refs, current_season=season_for_date(data.settings.region, dt_util.now().date())
        )
    except ValueError as err:
        raise _err("invalid_plan", reason=str(err)) from err
    runtime.repo.async_changed("plan")
    _sync_devices(hass, runtime, before)
    return {**done, "revision": data.revision}


@callback
def op_remove_planting(runtime: GardenRuntime, planting_id: str) -> None:
    repo = runtime.repo
    if repo.data.planting(planting_id) is None:
        raise _err("unknown_planting", planting=planting_id)
    repo.data.plantings = [p for p in repo.data.plantings if p.id != planting_id]
    repo.async_changed("plan")


@callback
def op_apply_autoplan(
    runtime: GardenRuntime,
    *,
    base_revision: int | None,
    plantings: list[dict[str, Any]],
    replace_beds: list[str],
    plan_from: int | None = None,
) -> int:
    """Store an autofill proposal; ``replace_beds`` drops that season's crops first.

    When the proposal was made on another year's plan (``plan_from``) because
    its own season had none, that plan is copied into the season first.
    """
    repo = runtime.repo
    if base_revision is not None and base_revision != repo.data.revision:
        raise RevisionConflict(f"revision {base_revision} != {repo.data.revision}")
    try:
        new = [from_dict(Planting, p) for p in plantings]
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_plan", reason=str(err)) from err
    if plan_from is not None:
        for season in {p.season for p in new}:
            seasons.copy_plan(repo.data, plan_from, season, now=dt_util.now())
    for planting in new:
        _check_planting(runtime, planting)
    new_seasons = {p.season for p in new}
    keep = [p for p in repo.data.plantings if not (p.bed_id in replace_beds and p.season in new_seasons)]
    repo.data.plantings = keep + new
    repo.async_changed("plan")
    return repo.data.revision


@callback
def op_set_shading_mode(runtime: GardenRuntime, zone_ref: str, mode: str) -> Zone:
    repo = runtime.repo
    zone = repo.data.zone(zone_ref) or next(
        (z for z in repo.data.zones if z.name.casefold() == zone_ref.casefold()), None
    )
    if zone is None:
        raise _err("unknown_zone", zone=zone_ref)
    if not zone.is_enclosed:
        raise _err("not_enclosed", zone=zone.name)
    zone.shading_mode = mode  # type: ignore[assignment]
    repo.async_changed("settings", bump_revision=False)
    return zone


def _jsonable(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v.isoformat() if isinstance(v, date) else v for k, v in fields.items()}


# --------------------------------------------------------------------------- #
# Records: harvest log, garden diary, seed stock, soil tests
# --------------------------------------------------------------------------- #
def _new_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@callback
def resolve_plant_id(runtime: GardenRuntime, ref: str | None) -> str:
    """A plant id, or a plant name in any language (case-insensitive) - for NFC tags and YAML."""
    db = runtime.repo.db
    text = str(ref or "").strip()
    if db.get(text) is not None:
        return text
    folded = text.casefold()
    for plant in db.all():
        if any(name.casefold() == folded for name in plant.names.values()):
            return plant.id
    raise _err("unknown_plant", plant=text or "-")


def _harvest_planting(runtime: GardenRuntime, plant_id: str, bed_id: str | None, day: date) -> Planting | None:
    """The one crop of this plant in the garden on ``day`` (optionally in ``bed_id``), if it is unambiguous."""
    from .engine.region import season_for_date

    data = runtime.repo.data
    season = season_for_date(data.settings.region, day)
    plant = runtime.repo.db.get(plant_id)
    live = [
        p for p in data.plantings
        if p.plant_id == plant_id and present_in(p, bool(plant and plant.perennial), season)
        and p.status not in (PlantingStatus.FAILED, PlantingStatus.FINISHED) and (bed_id is None or p.bed_id == bed_id)
    ]  # fmt: skip
    return live[0] if len(live) == 1 else None


def op_log_harvest(runtime: GardenRuntime, raw: Mapping[str, Any]) -> HarvestEntry:
    """Record a harvest.  ``planting`` (id) or ``plant`` (id or name) identifies the crop."""
    data = runtime.repo.data
    planting = data.planting(raw.get("planting_id")) if raw.get("planting_id") else None
    if raw.get("planting_id") and planting is None:
        raise _err("unknown_planting", planting=raw["planting_id"])
    bed = resolve_bed(runtime, raw["bed"]) if raw.get("bed") else None
    plant_id = planting.plant_id if planting else resolve_plant_id(runtime, raw.get("plant_id") or raw.get("plant"))
    raw_day = raw.get("day") or dt_util.now().date()
    harvest_day = raw_day if isinstance(raw_day, date) else date.fromisoformat(str(raw_day))
    if planting is None:
        planting = _harvest_planting(runtime, plant_id, bed.id if bed else raw.get("bed_id"), harvest_day)
    kg = float(raw.get("kg") or 0)
    count = int(raw["count"]) if raw.get("count") not in (None, "") else None
    if not math.isfinite(kg) or kg < 0 or kg > 100000 or (count is not None and count < 0) or (kg == 0 and not count):
        raise _err("invalid_harvest")
    day = raw.get("day") or dt_util.now().date()
    entry = HarvestEntry(
        id=_new_id("hv"), day=day if isinstance(day, date) else date.fromisoformat(str(day)), plant_id=plant_id,
        kg=round(kg, 3), count=count, planting_id=planting.id if planting else None,
        bed_id=planting.bed_id if planting else (bed.id if bed else raw.get("bed_id")),
        quality=int(raw["quality"]) if raw.get("quality") else None, note=str(raw.get("note") or ""),
    )  # fmt: skip
    data.harvest_log.append(entry)
    if planting is not None and planting.harvest_started_on is None:
        planting.harvest_started_on = entry.day
        if planting.status in (PlantingStatus.PLANNED, PlantingStatus.SOWN, PlantingStatus.TRANSPLANTED):
            planting.status = PlantingStatus.HARVESTING
    runtime.repo.async_changed("records")
    return entry


@callback
def op_delete_record(runtime: GardenRuntime, kind: str, record_id: str) -> None:
    data = runtime.repo.data
    lists = {"harvest": data.harvest_log, "journal": data.journal, "seed": data.seed_stock, "expense": data.expenses}
    items = lists.get(kind)
    if items is None:
        raise _err("invalid_record", kind=kind)
    before = len(items)
    items[:] = [i for i in items if i.id != record_id]
    if len(items) == before:
        raise _err("unknown_record", record=record_id)
    runtime.repo.async_changed("records")


@callback
def op_starter_garden(runtime: GardenRuntime, size: str, greenhouse: bool) -> dict[str, int]:
    """Lay out a beginner's garden with a first plan - only in a garden that has no beds yet."""
    from .seed import starter_garden

    data = runtime.repo.data
    if data.beds or data.plantings:
        raise _err("garden_not_empty")
    built = starter_garden(
        size, greenhouse=greenhouse, language=runtime.coordinator.lang, today=dt_util.now().date(),
        db=runtime.repo.db, base=data,
    )  # fmt: skip
    data.zones, data.beds, data.features, data.plantings = built.zones, built.beds, built.features, built.plantings
    runtime.repo.async_changed("plan")
    return {"beds": len(data.beds), "plantings": len(data.plantings)}


EXPENSE_CATEGORIES = ("seeds", "plants", "soil", "fertilizer", "tools", "water", "protection", "other")


@callback
def op_save_expense(runtime: GardenRuntime, raw: Mapping[str, Any]) -> Expense:
    """Add or update an expense (amount in the garden's currency)."""
    data = runtime.repo.data
    try:
        amount = round(float(raw.get("amount") or 0), 2)
    except (TypeError, ValueError) as err:
        raise _err("invalid_expense") from err
    category = str(raw.get("category") or "other")
    if not math.isfinite(amount) or amount <= 0 or category not in EXPENSE_CATEGORIES:
        raise _err("invalid_expense")
    raw_day = raw.get("day") or dt_util.now().date()
    day = raw_day if isinstance(raw_day, date) else date.fromisoformat(str(raw_day))
    season = int(raw.get("season") or season_for_date(data.settings.region, day))
    existing = next((e for e in data.expenses if e.id == raw.get("id")), None) if raw.get("id") else None
    if existing is None:
        existing = Expense(id=_new_id("ex"), day=day, season=season)
        data.expenses.append(existing)
    existing.day, existing.season, existing.category = day, season, category  # type: ignore[assignment]
    existing.amount, existing.note = amount, str(raw.get("note") or "")[:200]
    runtime.repo.async_changed("records")
    return existing


@callback
def op_save_journal(runtime: GardenRuntime, raw: Mapping[str, Any]) -> JournalEntry:
    data = runtime.repo.data
    existing = next((j for j in data.journal if j.id == raw.get("id")), None) if raw.get("id") else None
    planting = data.planting(raw.get("planting_id")) if raw.get("planting_id") else None
    if not str(raw.get("text") or "").strip() and not raw.get("photos"):
        raise _err("invalid_journal")
    fields = {
        "text": str(raw.get("text") or ""),
        "photos": [str(p) for p in raw.get("photos") or []],
        "kind": raw.get("kind") or "note",
        "planting_id": planting.id if planting else None,
        "bed_id": raw.get("bed_id") or (planting.bed_id if planting else None),
        "zone_id": raw.get("zone_id"),
        "plant_id": raw.get("plant_id") or (planting.plant_id if planting else None),
    }
    if fields["kind"] not in ("note", "observation", "problem", "milestone"):
        raise _err("invalid_journal")
    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        entry = existing
    else:
        entry = JournalEntry(id=_new_id("jn"), at=dt_util.now(), author=raw.get("author"), **fields)
        data.journal.append(entry)
    runtime.repo.async_changed("records")
    return entry


@callback
def op_save_seed(runtime: GardenRuntime, raw: Mapping[str, Any]) -> SeedPacket:
    data = runtime.repo.data
    if runtime.repo.db.get(str(raw.get("plant_id") or "")) is None:
        raise _err("unknown_plant", plant=raw.get("plant_id") or "-")
    try:
        packet = from_dict(
            SeedPacket, {"id": raw.get("id") or _new_id("sd"), **{k: v for k, v in raw.items() if k != "id"}}
        )
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_seed", reason=str(err)) from err
    if packet.quantity < 0 or (packet.year is not None and not 1990 <= packet.year <= 2100):
        raise _err("invalid_seed", reason="quantity / year")
    data.seed_stock = [s for s in data.seed_stock if s.id != packet.id] + [packet]
    runtime.repo.async_changed("records")
    return packet


@callback
def op_save_soil_test(runtime: GardenRuntime, bed_ref: str, raw: Mapping[str, Any]) -> SoilTest:
    bed = resolve_bed(runtime, bed_ref)
    if bed is None:
        raise _err("unknown_bed", bed=bed_ref)
    try:
        test = from_dict(SoilTest, dict(raw))
    except (TypeError, ValueError, KeyError) as err:
        raise _err("invalid_soil_test", reason=str(err)) from err
    if test.ph is not None and not 3.0 <= test.ph <= 10.0:
        raise _err("invalid_soil_test", reason="pH 3-10")
    if not isinstance(test.date, date):
        raise _err("invalid_soil_test", reason="date")
    # build and sort aside: a failure leaves the bed as it was
    bed.soil_tests = sorted([s for s in bed.soil_tests if s.date != test.date] + [test], key=lambda s: s.date)
    # Soil tests are records, not layout: an open planner must not get a conflict.
    runtime.repo.async_changed("plan", bump_revision=False)
    return test


@callback
def op_delete_soil_test(runtime: GardenRuntime, bed_ref: str, day: date) -> None:
    bed = resolve_bed(runtime, bed_ref)
    if bed is None:
        raise _err("unknown_bed", bed=bed_ref)
    bed.soil_tests = [s for s in bed.soil_tests if s.date != day]
    runtime.repo.async_changed("plan", bump_revision=False)


@callback
def op_assign_task(runtime: GardenRuntime, task_id: str, assignee: str | None) -> Task:
    task = runtime.repo.data.task(task_id)
    if task is None:
        raise _err("unknown_task", task=task_id)
    task.assignee = assignee or None
    task.user_modified = True
    task.updated_at = dt_util.now()
    runtime.repo.async_changed("tasks")
    return task


# --------------------------------------------------------------------------- #
# System log
# --------------------------------------------------------------------------- #
@callback
def op_undo(hass: HomeAssistant, runtime: GardenRuntime, entry_id: str, *, force: bool = False) -> dict[str, Any]:
    """Revert one system-log entry; keeps devices in sync like ``op_save_plan``.

    Returns ``{"ok", "conflicts", "problems", "entry"}``: with conflicts (items
    changed again since) nothing happens unless ``force``; broken references
    (e.g. a planting whose bed was deleted later) always block.
    """
    repo = runtime.repo
    old_zones = [(z.id, z.name, z.type) for z in repo.data.zones]
    old_beds = [(b.id, b.name) for b in repo.data.beds]
    try:
        result = repo.async_undo(entry_id, force=force)
    except KeyError as err:
        raise _err("unknown_log_entry", entry=entry_id) from err
    applied = result.ok or (force and not result.problems)
    if applied:
        removed = ({z[0] for z in old_zones} - {z.id for z in repo.data.zones}) | (
            {b[0] for b in old_beds} - {b.id for b in repo.data.beds}
        )
        if removed:
            _remove_devices(hass, runtime, removed)
        if old_zones != [(z.id, z.name, z.type) for z in repo.data.zones] or old_beds != [
            (b.id, b.name) for b in repo.data.beds
        ]:
            async_dispatcher_send(hass, SIGNAL_LAYOUT_CHANGED)
    entry = repo.syslog_entry(entry_id)
    return {
        "ok": applied,
        "conflicts": result.conflicts,
        "problems": result.problems,
        "undone_by": entry.get("undone_by") if entry else None,
        "revision": repo.data.revision,
    }


# --------------------------------------------------------------------------- #
# Several plans per season: start anew, set aside, reactivate
# --------------------------------------------------------------------------- #
def _plan_name(data: Any, season: int, name: str | None) -> str:
    if name and name.strip():
        return name.strip()[:80]
    n = sum(1 for p in data.archived_plans if p.season == season) + 1
    return f"{season} – {n}"


@callback
def op_new_plan(
    hass: HomeAssistant,
    runtime: GardenRuntime,
    season: int,
    *,
    start: str = "empty",
    old_name: str | None = None,
) -> dict[str, Any]:
    """Set the plan of ``season`` aside (restorable) and start a fresh one."""
    data = runtime.repo.data
    if start not in ("empty", "zones", "zones_beds"):
        raise _err("invalid_plan", reason=f"unknown start {start}")
    before = _live_layout_snapshot(data)
    plan = seasons.start_new_plan(
        data,
        season,
        start=start,  # type: ignore[arg-type]
        old_name=_plan_name(data, season, old_name),
        plan_id=f"plan_{uuid.uuid4().hex[:10]}",
        now=dt_util.now(),
    )
    runtime.repo.async_changed("plan")
    if season == data.layout_season:
        _sync_devices(hass, runtime, before)
    return {"archived": plan.id, "name": plan.name, "plantings": len(plan.plantings), "revision": data.revision}


@callback
def op_activate_plan(
    hass: HomeAssistant, runtime: GardenRuntime, plan_id: str, *, old_name: str | None = None
) -> dict[str, Any]:
    """Make a plan that was set aside active again; the current one is set aside."""
    data = runtime.repo.data
    plan = next((p for p in data.archived_plans if p.id == plan_id), None)
    if plan is None:
        raise _err("unknown_record", record=plan_id)
    before = _live_layout_snapshot(data)
    replaced = seasons.activate_plan(
        data,
        plan_id,
        old_name=_plan_name(data, plan.season, old_name),
        new_id=f"plan_{uuid.uuid4().hex[:10]}",
        now=dt_util.now(),
    )
    runtime.repo.async_changed("plan")
    if plan.season == data.layout_season:
        _sync_devices(hass, runtime, before)
    return {"season": plan.season, "archived": replaced.id, "revision": data.revision}


@callback
def op_delete_plan(runtime: GardenRuntime, plan_id: str) -> None:
    if not seasons.delete_plan(runtime.repo.data, plan_id):
        raise _err("unknown_record", record=plan_id)
    runtime.repo.async_changed("plan")


# --------------------------------------------------------------------------- #
# Cookbook
# --------------------------------------------------------------------------- #
COOKBOOK_MAX = 500


def _clean_spec(raw: Mapping[str, Any]) -> dict[str, Any]:

    tech = str(raw.get("technique") or "")
    produce = cooking.str_ids(raw.get("produce"))[:6]
    if tech not in cooking.TECHNIQUE or not produce:
        raise _err("invalid_recipe")
    side = str(raw.get("side") or "")
    protein = str(raw.get("protein") or "")
    return {
        "technique": tech,
        "produce": produce,
        "side": side if side in cooking.SIDES else "",
        "protein": protein if protein in cooking.PROTEINS else "",
        "extras": cooking.fitting_extras(tech, cooking.str_ids(raw.get("extras")), cooking.pan_meat(protein), produce),
        "servings": cooking.servings_of(raw.get("servings")),
    }


@callback
def op_cookbook_save(runtime: GardenRuntime, raw: Mapping[str, Any]) -> CookbookRecipe:
    """Keep a recipe in the cookbook (the same dish twice stays one entry)."""

    data = runtime.repo.data
    spec = _clean_spec(raw.get("spec") or {})
    changes = _cookbook_changes(raw)  # a refused request changes nothing
    rid = cooking.spec_id(spec)
    entry = next((r for r in data.cookbook if r.id == rid), None)
    if entry is None:
        if len(data.cookbook) >= COOKBOOK_MAX:
            raise _err("cookbook_full", max=COOKBOOK_MAX)
        entry = CookbookRecipe(id=rid, spec=spec, added=dt_util.now().date())
        data.cookbook.append(entry)
    _apply_cookbook_fields(entry, changes)
    runtime.repo.async_changed("records")
    return entry


def _cookbook_changes(raw: Mapping[str, Any]) -> dict[str, Any]:
    """The requested cookbook fields, cleaned and checked (raises before anything changes)."""
    out: dict[str, Any] = {}
    if "title" in raw:
        out["title"] = str(raw.get("title") or "").strip()[:120]
    if "note" in raw:
        out["note"] = str(raw.get("note") or "")[:1000]
    if "favorite" in raw:
        out["favorite"] = bool(raw.get("favorite"))
    if "shared" in raw:
        out["shared"] = bool(raw.get("shared"))
    if raw.get("cooked"):
        out["cooked"] = True
    if "ingredients" in raw:  # [] goes back to the generated list
        items = raw.get("ingredients")
        if not isinstance(items, list):
            raise _err("invalid_recipe")
        if len(items) > cooking.MAX_INGREDIENTS:
            raise _err("recipe_too_long", ingredients=cooking.MAX_INGREDIENTS, steps=cooking.MAX_STEPS)
        rows = [row for n, x in enumerate(items) if (row := cooking.custom_ingredient(x, n)) is not None]
        if items and not rows:
            raise _err("invalid_recipe")
        out["ingredients"] = rows
    if "steps" in raw:  # [] goes back to the generated method
        steps = raw.get("steps")
        if not isinstance(steps, list):
            raise _err("invalid_recipe")
        if len(steps) > cooking.MAX_STEPS:
            raise _err("recipe_too_long", ingredients=cooking.MAX_INGREDIENTS, steps=cooking.MAX_STEPS)
        out["steps"] = [s for x in steps if isinstance(x, str) and (s := x.strip()[:600])]
    return out


def _apply_cookbook_fields(entry: CookbookRecipe, changes: Mapping[str, Any]) -> None:
    for key in ("title", "note", "favorite", "shared", "ingredients", "steps"):
        if key in changes:
            setattr(entry, key, changes[key])
    if changes.get("cooked"):
        entry.cooked = [*entry.cooked, dt_util.now().date()][-50:]


@callback
def op_cookbook_update(runtime: GardenRuntime, recipe_id: str, raw: Mapping[str, Any]) -> CookbookRecipe:
    entry = next((r for r in runtime.repo.data.cookbook if r.id == recipe_id), None)
    if entry is None:
        raise _err("unknown_recipe", recipe=recipe_id)
    _apply_cookbook_fields(entry, _cookbook_changes(raw))
    runtime.repo.async_changed("records")
    return entry


@callback
def op_cookbook_delete(runtime: GardenRuntime, recipe_id: str) -> None:
    data = runtime.repo.data
    before = len(data.cookbook)
    data.cookbook = [r for r in data.cookbook if r.id != recipe_id]
    if len(data.cookbook) == before:
        raise _err("unknown_recipe", recipe=recipe_id)
    runtime.repo.async_changed("records")


@callback
def op_cooking_prefs(runtime: GardenRuntime, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Remember what the cook usually has in the house, likes, and for how many."""
    from dataclasses import asdict

    prefs = asdict(cooking.Prefs.from_dict(raw))
    runtime.repo.data.cooking_prefs = prefs
    runtime.repo.async_changed("records")
    return prefs
