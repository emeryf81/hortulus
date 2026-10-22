"""Websocket API consumed by the Hortulus panel.

All commands live under ``garden_manager/``.  Reads are available to every
authenticated user; layout, plant database and settings writes require an
admin.  Task actions are allowed for everyone - family members tick off
chores too.
"""

from __future__ import annotations

from dataclasses import astuple
from datetime import date
import json
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.util import dt as dt_util, yaml as yaml_util
import voluptuous as vol

from .const import DOMAIN
from .engine import climate, cooking, diagnose, handbook, planning, seasons, syslog
from .engine.advisor import advise, harvest_coverage
from .engine.autoplan import AutoplanOptions, autoplan
from .engine.compatibility import check_bed, check_rotation, rotation_history, suggest_companions
from .engine.i18n import t
from .engine.kitchen import economics, kitchen_report
from .engine.models import GardenBed, GardenResources, Planting
from .engine.planio import PlanImportError, export_plan
from .engine.plantdb import FAMILIES
from .engine.printout import PrintOptions
from .engine.qa import answer as qa_answer, options as qa_options
from .engine.records import harvest_by_year, harvest_summary, learned_yields, seed_report, water_stats, year_overview
from .engine.region import resolve_profile, season_anchors, season_bounds, season_for_date
from .engine.schedule import plant_windows, planting_timeline, season_timeline
from .engine.serde import from_dict, to_dict
from .engine.succession import expand_succession
from .engine.supplies import catalog as supplies_catalog, shopping_list
from .gardens import listing, pick
from .operations import (
    RevisionConflict,
    op_activate_plan,
    op_add_task,
    op_apply_autoplan,
    op_complete_task,
    op_cookbook_delete,
    op_cookbook_save,
    op_cookbook_update,
    op_cooking_prefs,
    op_delete_layout,
    op_delete_plan,
    op_delete_plant,
    op_delete_record,
    op_delete_soil_test,
    op_delete_task,
    op_fix_issue,
    op_import_plan,
    op_log_harvest,
    op_new_plan,
    op_postpone_task,
    op_reset_water_factor,
    op_save_expense,
    op_save_journal,
    op_save_plan,
    op_save_plant,
    op_save_seed,
    op_save_settings,
    op_save_soil_test,
    op_starter_garden,
    op_undo,
    op_update_planting,
    op_update_plantings,
    op_update_task,
    op_year_transition,
)
from .printing import async_render_svg
from .storage import current_user

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from . import GardenRuntime

DONE_TASK_WINDOW_DAYS = 60


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    for command in (
        ws_subscribe,
        ws_plants,
        ws_plant_save,
        ws_plant_delete,
        ws_plant_windows,
        ws_plan_save,
        ws_plan_check,
        ws_plan_succession,
        ws_plan_export,
        ws_plan_import,
        ws_task_add,
        ws_task_action,
        ws_settings_save,
        ws_bed_reset_water_factor,
        ws_autofill,
        ws_autofill_apply,
        ws_print_render,
        ws_handbook_index,
        ws_handbook_chapter,
        ws_handbook_search,
        ws_irrigation_plan,
        ws_irrigation_run,
        ws_irrigation_stop,
        ws_advice,
        ws_qa_options,
        ws_qa_ask,
        ws_supplies,
        ws_records_overview,
        ws_harvest_add,
        ws_record_delete,
        ws_expense_save,
        ws_starter_garden,
        ws_journal_save,
        ws_seed_save,
        ws_soil_save,
        ws_soil_delete,
        ws_syslog_list,
        ws_syslog_entry,
        ws_syslog_undo,
        ws_layout_delete,
        ws_year_preview,
        ws_year_apply,
        ws_plan_new,
        ws_plan_activate,
        ws_plan_delete,
        ws_analysis,
        ws_analysis_explain,
        ws_plantings_season,
        ws_planting_update,
        ws_plantings_update_many,
        ws_analysis_fix,
        ws_plan_compare,
        ws_still_possible,
        ws_irrigation_test,
        ws_irrigation_close,
        ws_planning,
        ws_seeds_to_todo,
        ws_season_report,
        ws_climate_stats,
        ws_climate_import_csv,
        ws_climate_apply_local_frost,
        ws_photo_diagnose,
        ws_cooking_suggest,
        ws_cooking_render,
        ws_cookbook_save,
        ws_cookbook_update,
        ws_cookbook_delete,
        ws_cooking_prefs,
        ws_cooking_pdf,
        ws_cooking_send,
        ws_cooking_to_todo,
    ):
        websocket_api.async_register_command(hass, command)


def _runtime(hass: HomeAssistant, msg: dict[str, Any] | None = None) -> GardenRuntime | None:
    """The garden the panel asked for (``garden_id``, a config entry id), else the first."""
    return pick(hass, (msg or {}).get("garden_id"))


def _require_runtime(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> GardenRuntime | None:
    runtime = _runtime(hass, msg)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Hortulus is not set up")
    # Attribute whatever this command changes to the user in the system log.
    current_user.set(connection.user.name if connection.user else None)
    return runtime


# (runtime id) -> ((revision, day, region, plant database), summary): the check only reruns
# when the plan, the day, the region or the plant data changed, not on every snapshot push.
_DIAGNOSIS_CACHE: dict[int, tuple[tuple[Any, ...], dict[str, int] | None]] = {}


def clear_diagnosis_cache(runtime: GardenRuntime) -> None:
    """Forget the cached check of a runtime that is being unloaded."""
    _DIAGNOSIS_CACHE.pop(id(runtime), None)


def _diagnosis_summary(runtime: GardenRuntime) -> dict[str, int] | None:
    """Issue counts for the badge on the Analysis tab (re-checked when the plan changes)."""
    data = runtime.repo.data
    today = dt_util.now().date()
    key = (data.revision, data.layout_season, today, astuple(data.settings.region), id(runtime.repo.db))
    cached = _DIAGNOSIS_CACHE.get(id(runtime))
    if cached is not None and cached[0] == key:
        return cached[1]
    try:
        issues = diagnose.check_garden(
            data, runtime.repo.db, today=today, current_season=season_for_date(data.settings.region, today)
        )
    except Exception:  # a broken check must never break the panel
        _LOGGER.exception("Garden check failed")
        return None
    summary = diagnose.summary(issues)
    _DIAGNOSIS_CACHE[id(runtime)] = (key, summary)
    return summary


def _latitude(configured: float | None, hass: HomeAssistant) -> float:
    """The region's latitude; Home Assistant's home only when none is set (0.0 is the equator)."""
    return configured if configured is not None else hass.config.latitude


def build_snapshot(runtime: GardenRuntime) -> dict[str, Any]:
    """Everything the panel renders, in one JSON document."""
    data = runtime.repo.data
    coordinator = runtime.coordinator
    cutoff = dt_util.now().date().toordinal() - DONE_TASK_WINDOW_DAYS
    tasks = [t for t in data.tasks if t.is_open or t.due.toordinal() >= cutoff]
    weather = coordinator.weather
    return {
        "revision": data.revision,
        "lang": coordinator.lang,
        "settings": to_dict(data.settings),
        "zones": [to_dict(z) for z in data.zones],
        "beds": [to_dict(b) for b in data.beds],
        "plantings": [to_dict(p) for p in data.plantings],
        "tasks": [to_dict(t) for t in tasks],
        "rotation_history": [to_dict(r) for r in data.rotation_history],
        "features": [to_dict(f) for f in data.features],
        "layout_season": data.layout_season,
        "layouts": {k: to_dict(v) for k, v in data.layouts.items()},
        "archived_plans": [
            {
                "id": p.id,
                "name": p.name,
                "season": p.season,
                "archived_at": p.archived_at.isoformat() if p.archived_at else None,
                "zones": len(p.zones),
                "beds": len(p.beds),
                "features": len(p.features),
                "plantings": len(p.plantings),
            }
            for p in data.archived_plans
        ],
        "diagnosis": _diagnosis_summary(runtime),
        "transition_due": seasons.pending_transition(
            data, coordinator.data.season if coordinator.data else data.layout_season or 0
        ),
        "irrigation_log": [to_dict(e) for e in data.irrigation_log[-300:]],
        "harvest_log": [to_dict(e) for e in data.harvest_log[-300:]],
        "journal": [to_dict(e) for e in data.journal[-200:]],
        "seed_stock": [to_dict(e) for e in data.seed_stock],
        "archived_seasons": sorted(int(k) for k in runtime.repo.archive if k.isdigit()),
        "irrigation_status": {
            "running": runtime.irrigation.running,
            "bed_id": runtime.irrigation.status.bed_id,
            "ends_at": runtime.irrigation.status.ends_at.isoformat() if runtime.irrigation.status.ends_at else None,
            "last_error": runtime.irrigation.status.last_error,
            "stuck": [
                {"entity_id": e, "since": since.isoformat(), "what": runtime.irrigation.valve_entities().get(e, e)}
                for e, since in runtime.irrigation.stuck.items()
            ],
            "leak": runtime.irrigation.leak,
            "waiting_for_sun": getattr(runtime.irrigation, "waiting_for_sun", None),
            "waiting_for_rain": getattr(runtime.irrigation, "waiting_for_rain", None),
        },
        "entry_id": coordinator.config_entry.entry_id,
        "gardens": listing(coordinator.hass),
        "analysis": coordinator.data.to_dict() if coordinator.data else None,
        "weather": {
            "available": weather.available,
            "temperature": weather.temperature,
            "condition": weather.condition,
            "fetched_at": weather.fetched_at.isoformat() if weather.fetched_at else None,
            "daily": [to_dict(p) for p in weather.daily[:7]],
            "hourly": [to_dict(p) for p in weather.hourly[:48]],
            "error": weather.error,
        },
    }


# --------------------------------------------------------------------------- #
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe", vol.Optional("garden_id"): str})
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Push a full snapshot now and after every coordinator update."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    current: dict[str, Any] = {"runtime": runtime, "unsub": None}

    @callback
    def push() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], build_snapshot(current["runtime"])))

    @callback
    def attach(new: GardenRuntime) -> None:
        if current["unsub"] is not None:
            current["unsub"]()
        current["runtime"] = new
        current["unsub"] = new.coordinator.async_add_listener(push)

    @callback
    def reloaded(new: GardenRuntime) -> None:
        """The garden was set up again (options saved, reload): follow it, not the old runtime."""
        attach(new)
        push()

    attach(runtime)
    subscribers = hass.data.setdefault(SUBSCRIBERS, {}).setdefault(runtime.coordinator.config_entry.entry_id, set())
    subscribers.add(reloaded)

    @callback
    def unsubscribe() -> None:
        subscribers.discard(reloaded)
        if current["unsub"] is not None:
            current["unsub"]()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    push()


SUBSCRIBERS = f"{DOMAIN}_subscribers"


@callback
def async_notify_reloaded(hass: HomeAssistant, entry_id: str, runtime: GardenRuntime) -> None:
    """Open panel and card subscriptions move to the garden's new runtime."""
    for reloaded in list(hass.data.get(SUBSCRIBERS, {}).get(entry_id, ())):
        reloaded(runtime)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/plants", vol.Optional("garden_id"): str})
@callback
def ws_plants(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    db = runtime.repo.db
    connection.send_result(
        msg["id"],
        {
            "plants": db.as_dicts(),
            "families": FAMILIES,
            "overrides": runtime.repo.data.plant_overrides,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plants/save",
        vol.Optional("garden_id"): str,
        vol.Required("plant"): dict,
        vol.Optional("mode", default="custom"): vol.In(["custom", "override"]),
    }
)
@websocket_api.require_admin
@callback
def ws_plant_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        plant = op_save_plant(runtime, msg["plant"], msg["mode"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "invalid_plant", str(err))
        return
    connection.send_result(msg["id"], {"plant": to_dict(plant)})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/plants/delete", vol.Optional("garden_id"): str, vol.Required("plant_id"): str}
)
@websocket_api.require_admin
@callback
def ws_plant_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        op_delete_plant(runtime, msg["plant_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "plant_in_use", str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plants/windows",
        vol.Optional("garden_id"): str,
        vol.Required("plant_id"): str,
        vol.Optional("zone_id"): vol.Any(str, None),
        vol.Optional("season"): vol.Any(int, None),
    }
)
@callback
def ws_plant_windows(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Absolute sowing windows of a plant (library + planner tooltips)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    db = runtime.repo.db
    plant = db.get(msg["plant_id"])
    if plant is None:
        connection.send_error(msg["id"], "unknown_plant", msg["plant_id"])
        return
    region = data.settings.region
    season = msg.get("season") or season_for_date(region, dt_util.now().date())
    anchors = season_anchors(region, season)
    windows = plant_windows(plant, anchors, data.zone(msg.get("zone_id")))
    connection.send_result(
        msg["id"],
        {
            "season": season,
            "windows": windows.to_dict(),
            "companions": [{"plant_id": pid, "strength": s} for pid, s in suggest_companions(plant.id, db)],
            "enemies": db.enemies_of(plant.id),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/save",
        vol.Optional("garden_id"): str,
        vol.Optional("base_revision"): vol.Any(int, None),
        vol.Required("zones"): list,
        vol.Required("beds"): list,
        vol.Required("plantings"): list,
        vol.Optional("features"): list,
        vol.Optional("season"): vol.Any(int, None),
    }
)
@websocket_api.require_admin
@callback
def ws_plan_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        revision = op_save_plan(
            hass,
            runtime,
            base_revision=msg.get("base_revision"),
            zones=msg["zones"],
            beds=msg["beds"],
            plantings=msg["plantings"],
            features=msg.get("features"),
            season=msg.get("season"),
        )
    except RevisionConflict as err:
        _log_error(hass, msg, "revision_conflict", err)
        connection.send_error(msg["id"], "revision_conflict", str(err))
        return
    except HomeAssistantError as err:
        _log_error(hass, msg, "invalid_plan", err)
        connection.send_error(msg["id"], "invalid_plan", str(err))
        return
    connection.send_result(msg["id"], {"revision": revision})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/check",
        vol.Optional("garden_id"): str,
        vol.Required("bed"): dict,
        vol.Required("plantings"): list,
    }
)
@callback
def ws_plan_check(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Live feedback for a *draft* bed while dragging (nothing is saved)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    db = runtime.repo.db
    lang = runtime.coordinator.lang
    try:
        bed = from_dict(GardenBed, msg["bed"])
        plantings = [from_dict(Planting, p) for p in msg["plantings"]]
    except (TypeError, ValueError, KeyError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    today = dt_util.now().date()
    zone = data.zone(bed.zone_id)
    timelines = {}
    planned = {}
    for p in plantings:
        plant = db.get(p.plant_id)
        if plant is not None:
            anchors = season_anchors(data.settings.region, p.season)
            timelines[p.id] = planting_timeline(p, plant, anchors, zone, today)
            planned[p.id] = planting_timeline(p, plant, anchors, zone, None).occupancy
    report = check_bed(
        bed,
        plantings,
        db,
        timelines={k: v.occupancy for k, v in timelines.items()},
        planned=planned,
        radius_cm=data.settings.companion_radius_cm,
        lang=lang,
        hemisphere=resolve_profile(data.settings.region).hemisphere,
    )
    others = [p for p in data.plantings if p.id not in {d.id for d in plantings}]
    history = rotation_history(data.rotation_history, others, db)
    rotation = [f.to_dict() for p in plantings for f in check_rotation(p, bed, history, db, lang=lang)]
    connection.send_result(
        msg["id"],
        {
            **report.to_dict(),
            "rotation": rotation,
            "timelines": {k: v.to_dict() for k, v in timelines.items()},
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/succession",
        vol.Optional("garden_id"): str,
        vol.Required("planting"): dict,
        vol.Required("count"): vol.All(int, vol.Range(min=1, max=20)),
        vol.Optional("interval_days"): vol.Any(None, vol.All(int, vol.Range(min=1, max=120))),
        vol.Optional("placement", default="split"): vol.In(["split", "stack"]),
    }
)
@callback
def ws_plan_succession(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    try:
        base = from_dict(Planting, msg["planting"])
    except (TypeError, ValueError, KeyError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    plant = runtime.repo.db.get(base.plant_id)
    bed = data.bed(base.bed_id)
    if plant is None:
        connection.send_error(msg["id"], "unknown_plant", base.plant_id)
        return
    zone = data.zone(bed.zone_id) if bed else None
    plantings, dropped = expand_succession(
        base,
        plant,
        season_anchors(data.settings.region, base.season),
        zone,
        count=msg["count"],
        interval_days=msg.get("interval_days"),
        placement=msg["placement"],
    )
    connection.send_result(msg["id"], {"plantings": [to_dict(p) for p in plantings], "dropped": dropped})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/export",
        vol.Optional("garden_id"): str,
        vol.Optional("format", default="json"): vol.In(["json", "yaml"]),
        vol.Optional("include_tasks", default=False): bool,
    }
)
@callback
def ws_plan_export(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    doc = export_plan(runtime.repo.data, now=dt_util.now(), include_tasks=msg["include_tasks"])
    stamp = date.today().isoformat()
    if msg["format"] == "yaml":
        content = yaml_util.dump(doc)
        filename = f"hortulus-plan-{stamp}.yaml"
    else:
        content = json.dumps(doc, indent=2, ensure_ascii=False)
        filename = f"hortulus-plan-{stamp}.json"
    connection.send_result(msg["id"], {"filename": filename, "content": content})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/import",
        vol.Optional("garden_id"): str,
        vol.Required("content"): str,
        vol.Optional("mode", default="merge"): vol.In(["merge", "replace"]),
    }
)
@websocket_api.require_admin
@callback
def ws_plan_import(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    text = msg["content"].strip()
    try:
        doc = json.loads(text) if text.startswith("{") else yaml_util.parse_yaml(text)
        if not isinstance(doc, dict):
            raise PlanImportError("Plan must be a mapping")
        counts = op_import_plan(hass, runtime, doc, msg["mode"])
    except (PlanImportError, ValueError, HomeAssistantError) as err:
        connection.send_error(msg["id"], "invalid_plan", str(err))
        return
    connection.send_result(msg["id"], {"counts": counts, "revision": runtime.repo.data.revision})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/tasks/add",
        vol.Optional("garden_id"): str,
        vol.Required("title"): str,
        vol.Optional("due"): vol.Any(str, None),
        vol.Optional("task_type", default="custom"): str,
        vol.Optional("description", default=""): str,
        vol.Optional("priority", default="normal"): vol.In(["low", "normal", "high", "urgent"]),
        vol.Optional("estimated_minutes"): vol.Any(int, None),
        vol.Optional("bed_id"): vol.Any(str, None),
        vol.Optional("planting_id"): vol.Any(str, None),
        vol.Optional("recurrence_days"): vol.Any(int, None),
        vol.Optional("until"): vol.Any(str, None),
    }
)
@callback
def ws_task_add(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        task_id = op_add_task(
            runtime,
            title=msg["title"],
            due=date.fromisoformat(msg["due"]) if msg.get("due") else None,
            task_type=msg["task_type"],
            description=msg["description"],
            priority=msg["priority"],
            minutes=msg.get("estimated_minutes"),
            bed=msg.get("bed_id"),
            planting_id=msg.get("planting_id"),
            recurrence_days=msg.get("recurrence_days"),
            until=date.fromisoformat(msg["until"]) if msg.get("until") else None,
        )
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_task", str(err))
        return
    connection.send_result(msg["id"], {"task_id": task_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/tasks/action",
        vol.Optional("garden_id"): str,
        vol.Required("task_id"): str,
        vol.Required("action"): vol.In(["complete", "skip", "postpone", "update", "delete", "reopen"]),
        vol.Optional("note"): vol.Any(str, None),
        vol.Optional("photos"): [str],
        vol.Optional("days"): vol.Any(int, None),
        vol.Optional("to"): vol.Any(str, None),
        vol.Optional("cascade", default=True): bool,
        vol.Optional("changes"): dict,
    }
)
@callback
def ws_task_action(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    task_id, action = msg["task_id"], msg["action"]
    result: dict[str, Any] = {}
    try:
        if action in ("complete", "skip"):
            res = op_complete_task(
                hass,
                runtime,
                task_id,
                note=msg.get("note"),
                photos=msg.get("photos", []),
                skipped=action == "skip",
                user_id=connection.user.id,
            )
            result = {"next_task_id": res.next_task.id if res.next_task else None}
        elif action == "postpone":
            res_p = op_postpone_task(
                runtime,
                task_id,
                days=msg.get("days"),
                to=date.fromisoformat(msg["to"]) if msg.get("to") else None,
                reason=msg.get("note"),
                cascade=msg["cascade"],
            )
            result = {"shifted": [t.id for t in res_p.shifted], "warnings": res_p.warnings}
        elif action == "delete":
            op_delete_task(runtime, task_id)
        else:
            changes = dict(msg.get("changes") or {})
            if action == "reopen":
                changes["reopen"] = True
            if msg.get("note"):
                changes["note"] = msg["note"]
            if "photos" in msg:
                changes["photos"] = msg["photos"]
            op_update_task(runtime, task_id, changes)
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], "task_error", str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/settings/save", vol.Optional("garden_id"): str, vol.Required("settings"): dict}
)
@websocket_api.require_admin
@callback
def ws_settings_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        settings = op_save_settings(runtime, msg["settings"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "invalid_settings", str(err))
        return
    connection.send_result(msg["id"], {"settings": to_dict(settings)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/bed/reset_water_factor",
        vol.Optional("garden_id"): str,
        vol.Required("bed_id"): str,
    }
)
@websocket_api.require_admin
@callback
def ws_bed_reset_water_factor(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        op_reset_water_factor(runtime, msg["bed_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "unknown_bed", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


# --------------------------------------------------------------------------- #
# Autofill
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/autofill",
        vol.Optional("garden_id"): str,
        vol.Optional("season"): int,
        vol.Optional("bed_ids"): [str],
        vol.Optional("replace", default=False): bool,
        vol.Optional("resources"): dict,
        vol.Optional("max_crops", default=16): vol.All(int, vol.Range(min=1, max=60)),
        vol.Optional("remember", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_autofill(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Propose a plan; nothing is stored except (optionally) the resources."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    resources = data.settings.resources
    if msg.get("resources"):
        try:
            resources = from_dict(GardenResources, {**to_dict(resources), **msg["resources"]})
        except (TypeError, ValueError, KeyError) as err:
            connection.send_error(msg["id"], "invalid_format", str(err))
            return
        if msg["remember"] and connection.user.is_admin:
            op_save_settings(runtime, {"resources": to_dict(resources)})
    today = dt_util.now().date()
    season = msg.get("season") or season_for_date(data.settings.region, today)
    opts = AutoplanOptions(
        season=season,
        bed_ids=msg.get("bed_ids"),
        replace=msg["replace"],
        max_crops=msg["max_crops"],
        lang=runtime.coordinator.lang,
    )
    result = await hass.async_add_executor_job(
        lambda: autoplan(data, runtime.repo.db, opts, today=today, resources=resources)
    )
    connection.send_result(msg["id"], {**result.to_dict(), "season": season, "revision": data.revision})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/autofill/apply",
        vol.Optional("garden_id"): str,
        vol.Optional("base_revision"): vol.Any(int, None),
        vol.Required("plantings"): list,
        vol.Optional("replace_beds", default=[]): [str],
        vol.Optional("plan_from"): vol.Any(int, None),
    }
)
@websocket_api.require_admin
@callback
def ws_autofill_apply(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        revision = op_apply_autoplan(
            runtime,
            base_revision=msg.get("base_revision"),
            plantings=msg["plantings"],
            replace_beds=msg["replace_beds"],
            plan_from=msg.get("plan_from"),
        )
    except RevisionConflict as err:
        _log_error(hass, msg, "revision_conflict", err)
        connection.send_error(msg["id"], "revision_conflict", str(err))
        return
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "invalid_plan", str(err))
        return
    connection.send_result(msg["id"], {"revision": revision})


# --------------------------------------------------------------------------- #
# Print preview (the PDF itself comes from the authenticated HTTP view)
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/print/render", vol.Optional("garden_id"): str, vol.Required("options"): dict}
)
@websocket_api.async_response
async def ws_print_render(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    try:
        opts = PrintOptions.from_dict({"lang": runtime.coordinator.lang, **msg["options"]})
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    pages = await async_render_svg(hass, runtime, opts)
    connection.send_result(msg["id"], {"pages": pages})


# --------------------------------------------------------------------------- #
# Handbook
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/handbook/index", vol.Optional("garden_id"): str, vol.Optional("lang"): str}
)
@websocket_api.async_response
async def ws_handbook_index(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    runtime = _runtime(hass, msg)
    lang = msg.get("lang") or (runtime.coordinator.lang if runtime else "en")
    chapters = await hass.async_add_executor_job(handbook.chapters, lang)
    glossary = await hass.async_add_executor_job(handbook.glossary, lang)
    connection.send_result(msg["id"], {"chapters": [c.meta() for c in chapters], "glossary": glossary})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/handbook/chapter",
        vol.Optional("garden_id"): str,
        vol.Required("chapter_id"): str,
        vol.Optional("lang"): str,
    }
)
@websocket_api.async_response
async def ws_handbook_chapter(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    runtime = _runtime(hass, msg)
    lang = msg.get("lang") or (runtime.coordinator.lang if runtime else "en")
    chapter = await hass.async_add_executor_job(handbook.chapter, msg["chapter_id"], lang)
    if chapter is None:
        connection.send_error(msg["id"], "not_found", f"no chapter {msg['chapter_id']}")
        return
    connection.send_result(msg["id"], {**chapter.meta(), "body": chapter.body})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/handbook/search",
        vol.Optional("garden_id"): str,
        vol.Required("query"): str,
        vol.Optional("lang"): str,
    }
)
@websocket_api.async_response
async def ws_handbook_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    runtime = _runtime(hass, msg)
    lang = msg.get("lang") or (runtime.coordinator.lang if runtime else "en")
    hits = await hass.async_add_executor_job(handbook.search, msg["query"], lang)
    connection.send_result(msg["id"], {"results": hits})


# --------------------------------------------------------------------------- #
# Irrigation
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/irrigation/plan", vol.Optional("garden_id"): str})
@callback
def ws_irrigation_plan(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    plan = runtime.irrigation.build_plan(force=True)
    lang = runtime.coordinator.lang
    connection.send_result(
        msg["id"],
        {
            **plan.to_dict(),
            "reasons": {k: t(key, lang, **params) for k, (key, params) in plan.skipped.items()},
            "running": runtime.irrigation.running,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/irrigation/run",
        vol.Optional("garden_id"): str,
        vol.Optional("bed_ids"): [str],
        vol.Optional("amount_mm"): vol.Coerce(float),
    }
)
@websocket_api.require_admin
@callback
def ws_irrigation_run(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    bed_ids = set(msg["bed_ids"]) if msg.get("bed_ids") else None
    plan = runtime.irrigation.build_plan(force=True, bed_ids=bed_ids, override_mm=msg.get("amount_mm"))
    started = runtime.irrigation.async_start(plan, source="manual")
    connection.send_result(msg["id"], {"started": started, **plan.to_dict()})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/irrigation/stop", vol.Optional("garden_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_irrigation_stop(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    await runtime.irrigation.async_stop()
    connection.send_result(msg["id"])


# --------------------------------------------------------------------------- #
# Advice, Q&A and supplies
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/advice", vol.Optional("garden_id"): str})
@websocket_api.async_response
async def ws_advice(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Suggestions for the current plan plus the month-by-month harvest coverage."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None or runtime.coordinator.data is None:
        if runtime is not None:
            connection.send_error(msg["id"], "not_ready", "Analysis not ready yet")
        return
    data, db, analysis, lang = runtime.repo.data, runtime.repo.db, runtime.coordinator.data, runtime.coordinator.lang

    def build() -> dict[str, Any]:
        return {
            "suggestions": [s.to_dict() for s in advise(data, db, analysis, lang)],
            "coverage": harvest_coverage(data, db, analysis).to_dict(),
        }

    connection.send_result(msg["id"], await hass.async_add_executor_job(build))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/qa/options", vol.Optional("garden_id"): str})
@callback
def ws_qa_options(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    season = season_for_date(data.settings.region, dt_util.now().date())
    connection.send_result(msg["id"], qa_options(data, runtime.repo.db, season, runtime.coordinator.lang))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/qa/ask",
        vol.Optional("garden_id"): str,
        vol.Required("subject"): str,
        vol.Required("problem"): str,
        vol.Optional("target"): vol.Any(str, None),
    }
)
@callback
def ws_qa_ask(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    analysis = runtime.coordinator.data
    if analysis is None:
        connection.send_error(msg["id"], "not_ready", "Analysis not ready yet")
        return
    try:
        result = qa_answer(msg["subject"], msg["problem"], msg.get("target"), runtime.repo.data, runtime.repo.db,
                           analysis, runtime.coordinator.lang)  # fmt: skip
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], result.to_dict())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/supplies", vol.Optional("garden_id"): str})
@callback
def ws_supplies(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Tool catalogue, tools per task type and the season's shopping list."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    lang = runtime.coordinator.lang
    analysis = runtime.coordinator.data
    items = shopping_list(runtime.repo.data, runtime.repo.db, analysis, lang) if analysis else []
    connection.send_result(msg["id"], {**supplies_catalog(lang), "shopping": [i.to_dict() for i in items]})


# --------------------------------------------------------------------------- #
# Records: harvest, diary, seeds, soil tests, water, year overview
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/records/overview", vol.Optional("garden_id"): str})
@callback
def ws_records_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data, db, analysis = runtime.repo.data, runtime.repo.db, runtime.coordinator.data
    today = analysis.today if analysis else dt_util.now().date()
    season = analysis.season if analysis else today.year
    connection.send_result(
        msg["id"],
        {
            "season": season,
            "harvest_season": {k: v.to_dict() for k, v in harvest_summary(data, season).items()},
            "harvest_all": {k: v.to_dict() for k, v in harvest_summary(data).items()},
            "harvest_years": harvest_by_year(data),
            "learned_yields": learned_yields(data),
            "seeds": seed_report(data, db, season),
            "water": water_stats(data, today).to_dict(),
            "year": year_overview(data, db, analysis) if analysis else None,
            "kitchen": kitchen_report(data, db, analysis.timelines, today, runtime.coordinator.lang)
            if analysis
            else None,
            "economics": economics(data, db, season, runtime.coordinator.lang),
            "expenses": [
                to_dict(e) for e in sorted(data.expenses, key=lambda e: e.day, reverse=True) if e.season == season
            ],
        },
    )


def _log_error(hass: HomeAssistant | None, msg: dict[str, Any], code: str, err: BaseException) -> None:
    """Keep failed panel actions in the system log for the analysis view."""
    runtime = _runtime(hass, msg) if hass is not None else None
    if runtime is None:
        return
    context = {
        k: v for k, v in msg.items() if k not in ("id", "type") and isinstance(v, (str, int, float, bool, type(None)))
    }
    runtime.repo.record_error(str(msg.get("type", "")).split("/", 1)[-1], code, str(err) or type(err).__name__, context)


def _ws_op(connection: websocket_api.ActiveConnection, msg: dict[str, Any], fn: Any) -> None:
    """Run an operation and translate validation errors into websocket errors (and log them)."""
    hass = getattr(connection, "hass", None)
    try:
        result = fn()
    except ServiceValidationError as err:
        _log_error(hass, msg, err.translation_key or "invalid_format", err)
        connection.send_error(msg["id"], err.translation_key or "invalid_format", str(err))
        return
    except Exception as err:
        _log_error(hass, msg, "unexpected", err)
        raise
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/harvest/add",
        vol.Optional("garden_id"): str,
        vol.Optional("planting_id"): vol.Any(str, None),
        vol.Optional("plant_id"): vol.Any(str, None),
        vol.Optional("kg"): vol.Coerce(float),
        vol.Optional("count"): vol.Any(vol.Coerce(int), None),
        vol.Optional("quality"): vol.Any(vol.Coerce(int), None),
        vol.Optional("day"): str,
        vol.Optional("note"): str,
    }
)
@callback
def ws_harvest_add(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        raw = {k: v for k, v in msg.items() if k not in ("id", "type")}
        _ws_op(connection, msg, lambda: {"harvest": to_dict(op_log_harvest(runtime, raw))})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/delete",
        vol.Optional("garden_id"): str,
        vol.Required("kind"): vol.In(["harvest", "journal", "seed", "expense"]),
        vol.Required("record_id"): str,
    }
)
@callback
def ws_record_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_delete_record(runtime, msg["kind"], msg["record_id"]) or {})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/garden/starter",
        vol.Optional("garden_id"): str,
        vol.Optional("size", default="medium"): vol.In(["small", "medium", "large"]),
        vol.Optional("greenhouse", default=False): bool,
    }
)
@websocket_api.require_admin
@callback
def ws_starter_garden(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_starter_garden(runtime, msg["size"], msg["greenhouse"]))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/expense/save",
        vol.Optional("garden_id"): str,
        vol.Required("expense"): dict,
    }
)
@callback
def ws_expense_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"expense": to_dict(op_save_expense(runtime, msg["expense"]))})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/journal/save",
        vol.Optional("garden_id"): str,
        vol.Required("entry"): dict,
    }
)
@callback
def ws_journal_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        raw = {
            **msg["entry"],
            "author": msg["entry"].get("author") or (connection.user.name if connection.user else None),
        }
        _ws_op(connection, msg, lambda: {"entry": to_dict(op_save_journal(runtime, raw))})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/records/seeds/save", vol.Optional("garden_id"): str, vol.Required("packet"): dict}
)
@callback
def ws_seed_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"packet": to_dict(op_save_seed(runtime, msg["packet"]))})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/soil/save",
        vol.Optional("garden_id"): str,
        vol.Required("bed_id"): str,
        vol.Required("test"): dict,
    }
)
@callback
def ws_soil_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"test": to_dict(op_save_soil_test(runtime, msg["bed_id"], msg["test"]))})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/records/soil/delete",
        vol.Optional("garden_id"): str,
        vol.Required("bed_id"): str,
        vol.Required("date"): str,
    }
)
@callback
def ws_soil_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(
            connection, msg, lambda: op_delete_soil_test(runtime, msg["bed_id"], date.fromisoformat(msg["date"])) or {}
        )


# --------------------------------------------------------------------------- #
# System log
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/syslog/list",
        vol.Optional("garden_id"): str,
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=syslog.MAX_ENTRIES)),
        vol.Optional("before"): vol.Any(str, None),
        vol.Optional("include_system", default=True): bool,
    }
)
@callback
def ws_syslog_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Newest first; page with ``before`` = id of the last entry received."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    entries = list(reversed(runtime.repo.syslog))
    if msg.get("before"):
        ids = [e["id"] for e in entries]
        entries = entries[ids.index(msg["before"]) + 1 :] if msg["before"] in ids else []
    if not msg["include_system"]:
        entries = [e for e in entries if e.get("source") != "system"]
    page = entries[: msg["limit"]]
    connection.send_result(
        msg["id"],
        {
            "entries": [syslog.public(e) for e in page],
            "more": len(entries) > len(page),
            "total": len(runtime.repo.syslog),
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/syslog/entry", vol.Optional("garden_id"): str, vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@callback
def ws_syslog_entry(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """One entry including the before/after of every changed item."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    entry = runtime.repo.syslog_entry(msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "unknown_log_entry", msg["entry_id"])
        return
    connection.send_result(msg["id"], {"entry": entry})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/syslog/undo",
        vol.Optional("garden_id"): str,
        vol.Required("entry_id"): str,
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.require_admin
@callback
def ws_syslog_undo(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_undo(hass, runtime, msg["entry_id"], force=msg["force"]))


# --------------------------------------------------------------------------- #
# Garden plans per season & the year-end transition
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/layout/delete", vol.Optional("garden_id"): str, vol.Required("season"): int}
)
@websocket_api.require_admin
@callback
def ws_layout_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_delete_layout(runtime, msg["season"]) or {})


def _occupancy(runtime: GardenRuntime) -> dict[str, Any]:
    """Planned occupancy of every planting (to spot crops that overwinter)."""
    data = runtime.repo.data
    db = runtime.repo.db
    zones = {z.id: z for z in data.zones}
    beds = {b.id: b for b in data.beds}
    for layout in data.layouts.values():
        zones.update({z.id: z for z in layout.zones if z.id not in zones})
        beds.update({b.id: b for b in layout.beds if b.id not in beds})
    out = {}
    for p in data.plantings:
        plant = db.get(p.plant_id)
        bed = beds.get(p.bed_id)
        if plant is None:
            continue
        zone = zones.get(bed.zone_id) if bed else None
        anchors = season_anchors(data.settings.region, p.season)
        out[p.id] = planting_timeline(p, plant, anchors, zone, None).occupancy
    return out


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/year/preview", vol.Optional("garden_id"): str, vol.Optional("from_season"): int}
)
@callback
def ws_year_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """What the year-end transition would carry into next year (nothing is changed)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    today = dt_util.now().date()
    from_season = msg.get("from_season") or data.layout_season or season_for_date(data.settings.region, today)
    _start, end = season_bounds(data.settings.region, from_season)
    result = seasons.preview(data, runtime.repo.db, from_season, season_end=end, timelines=_occupancy(runtime))
    connection.send_result(msg["id"], result.to_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/year/apply",
        vol.Optional("garden_id"): str,
        vol.Required("from_season"): int,
        vol.Optional("layout", default="copy"): vol.In(["copy", "keep"]),
        vol.Optional("zone_ids"): vol.Any([str], None),
        vol.Optional("feature_ids"): vol.Any([str], None),
        vol.Optional("planting_ids", default=[]): [str],
        vol.Optional("activate", default=True): bool,
    }
)
@websocket_api.require_admin
@callback
def ws_year_apply(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(
            connection,
            msg,
            lambda: op_year_transition(
                hass,
                runtime,
                msg["from_season"],
                layout=msg["layout"],
                zone_ids=msg.get("zone_ids"),
                feature_ids=msg.get("feature_ids"),
                planting_ids=msg["planting_ids"],
                activate=msg["activate"],
            ),
        )


# --------------------------------------------------------------------------- #
# Several plans per season
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/new",
        vol.Optional("garden_id"): str,
        vol.Required("season"): int,
        vol.Optional("start", default="empty"): vol.In(["empty", "zones", "zones_beds"]),
        vol.Optional("old_name"): vol.Any(str, None),
    }
)
@websocket_api.require_admin
@callback
def ws_plan_new(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(
            connection,
            msg,
            lambda: op_new_plan(hass, runtime, msg["season"], start=msg["start"], old_name=msg.get("old_name")),
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/activate",
        vol.Optional("garden_id"): str,
        vol.Required("plan_id"): str,
        vol.Optional("old_name"): vol.Any(str, None),
    }
)
@websocket_api.require_admin
@callback
def ws_plan_activate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_activate_plan(hass, runtime, msg["plan_id"], old_name=msg.get("old_name")))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/plan/delete", vol.Optional("garden_id"): str, vol.Required("plan_id"): str}
)
@websocket_api.require_admin
@callback
def ws_plan_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_delete_plan(runtime, msg["plan_id"]) or {})


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/analysis", vol.Optional("garden_id"): str})
@callback
def ws_analysis(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Consistency check of the plan plus the most recent errors."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    today = dt_util.now().date()
    current = season_for_date(data.settings.region, today)
    issues = diagnose.check_garden(
        data, runtime.repo.db, today=today, current_season=current, lang=runtime.coordinator.lang
    )
    errors = [syslog.public(e) for e in reversed(runtime.repo.syslog) if e.get("source") == "error"][:50]
    connection.send_result(
        msg["id"],
        {
            "season": current,
            "layout_season": data.layout_season,
            "issues": [i.to_dict() for i in issues],
            "errors": errors,
            "counts": {
                "zones": len(data.zones),
                "beds": len(data.beds),
                "features": len(data.features),
                "plantings": len(data.plantings),
                "plans": len(seasons.plan_seasons(data)),
                "archived_plans": len(data.archived_plans),
                "log_entries": len(runtime.repo.syslog),
            },
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/analysis/explain",
        vol.Optional("garden_id"): str,
        vol.Required("plant_id"): str,
        vol.Optional("season"): vol.Any(int, None),
        vol.Optional("match_zone", default=True): bool,
    }
)
@callback
def ws_analysis_explain(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Why can (or can't) a plant go into each bed of a season's plan?"""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    db = runtime.repo.db
    plant = db.get(msg["plant_id"])
    if plant is None:
        connection.send_error(msg["id"], "unknown_plant", msg["plant_id"])
        return
    data = runtime.repo.data
    today = dt_util.now().date()
    season = msg.get("season") or data.layout_season or season_for_date(data.settings.region, today)
    verdicts = diagnose.explain_plant(
        plant, data, db, season, today=today, match_zone=msg["match_zone"], lang=runtime.coordinator.lang
    )
    connection.send_result(
        msg["id"],
        {
            "plant_id": plant.id,
            "season": season,
            "has_plan": seasons.has_layout(data, season),
            "beds": [v.to_dict() for v in verdicts],
        },
    )


# --------------------------------------------------------------------------- #
# Crops of a season (list view with all dates, no dragging)
# --------------------------------------------------------------------------- #
def _crop_timeline(data: Any, p: Planting, plant: Any, season: int, zone: Any, today: Any) -> Any:
    """A crop's timeline as it matters for ``season`` (perennials carried over re-anchor on that year)."""
    region = data.settings.region
    start, end = season_bounds(region, season)
    return season_timeline(p, plant, season, lambda s: season_anchors(region, s), zone, today, start, end)


def _season_rows(runtime: GardenRuntime, season: int) -> list[dict[str, Any]]:
    data = runtime.repo.data
    db = runtime.repo.db
    layout = seasons.layout_for(data, season)
    # a crop whose year has no plan (or whose bed is gone) still shows the bed it knew
    beds = {b.id: b for b in data.beds}
    zones = {z.id: z for z in data.zones}
    if layout is not None:
        beds |= {b.id: b for b in layout.beds}
        zones |= {z.id: z for z in layout.zones}
    today = dt_util.now().date()
    rows = []
    for p in data.plantings:
        if not seasons.present_in(p, False, season):
            continue
        plant = db.get(p.plant_id)
        bed = beds.get(p.bed_id)
        timeline = None
        if plant is not None:
            zone = zones.get(bed.zone_id) if bed else None
            timeline = _crop_timeline(data, p, plant, season, zone, today).to_dict()
        rows.append(
            {
                "planting": to_dict(p),
                "bed": bed.name if bed else None,
                "zone": zones[bed.zone_id].name if bed and bed.zone_id in zones else None,
                "timeline": timeline,
            }
        )
    return rows


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/plantings/season", vol.Optional("garden_id"): str, vol.Required("season"): int}
)
@callback
def ws_plantings_season(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Every crop of a season with its bed and computed dates."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        connection.send_result(msg["id"], {"season": msg["season"], "rows": _season_rows(runtime, msg["season"])})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/planting/update",
        vol.Optional("garden_id"): str,
        vol.Required("planting_id"): str,
        vol.Required("changes"): dict,
    }
)
@websocket_api.require_admin
@callback
def ws_planting_update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Change dates, status, count or notes of one crop (no geometry needed)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return

    def run() -> dict[str, Any]:
        updated = op_update_planting(runtime, msg["planting_id"], msg["changes"])
        row = next((r for r in _season_rows(runtime, updated.season) if r["planting"]["id"] == updated.id), None)
        return {"planting": to_dict(updated), "row": row, "revision": runtime.repo.data.revision}

    _ws_op(connection, msg, run)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plantings/update_many",
        vol.Optional("garden_id"): str,
        vol.Required("planting_ids"): [str],
        vol.Required("changes"): dict,
    }
)
@websocket_api.require_admin
@callback
def ws_plantings_update_many(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The same change (status, a date ...) for several crops at once."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(
            connection,
            msg,
            lambda: {
                "updated": len(op_update_plantings(runtime, msg["planting_ids"], msg["changes"])),
                "revision": runtime.repo.data.revision,
            },
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/analysis/fix",
        vol.Optional("garden_id"): str,
        vol.Required("code"): str,
        vol.Optional("params", default={}): dict,
        vol.Optional("refs", default={}): dict,
    }
)
@websocket_api.require_admin
@callback
def ws_analysis_fix(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Repair a problem the garden check reported."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: op_fix_issue(hass, runtime, msg["code"], msg["params"], msg["refs"]))


_PLAN_REF = vol.Schema({vol.Optional("season"): vol.Any(int, None), vol.Optional("plan_id"): vol.Any(str, None)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/plan/compare",
        vol.Optional("garden_id"): str,
        vol.Required("a"): _PLAN_REF,
        vol.Required("b"): _PLAN_REF,
    }
)
@callback
def ws_plan_compare(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Differences between two plans (a season's or one that was set aside)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    views = [
        diagnose.plan_view(data, season=ref.get("season"), plan_id=ref.get("plan_id")) for ref in (msg["a"], msg["b"])
    ]
    if views[0] is None or views[1] is None:
        connection.send_error(msg["id"], "unknown_record", "plan not found")
        return
    connection.send_result(
        msg["id"], diagnose.compare_plans(views[0], views[1], runtime.repo.db, runtime.coordinator.lang)
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/analysis/still_possible",
        vol.Optional("garden_id"): str,
        vol.Required("season"): int,
    }
)
@callback
def ws_still_possible(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Plants that can still be sown or planted in a season, and where."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        today = dt_util.now().date()
        rows = diagnose.still_possible(
            runtime.repo.data, runtime.repo.db, msg["season"], today=today, lang=runtime.coordinator.lang
        )
        connection.send_result(msg["id"], {"season": msg["season"], "plants": rows})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/irrigation/test",
        vol.Optional("garden_id"): str,
        vol.Required("entity_id"): str,
        vol.Optional("seconds", default=5): vol.All(vol.Coerce(float), vol.Range(min=1, max=60)),
        vol.Optional("with_pump", default=True): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_irrigation_test(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Open a valve for a few seconds and check it reports open and closed again."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    valves = runtime.irrigation.valve_entities()
    if msg["entity_id"] not in valves or valves[msg["entity_id"]] == "pump":
        connection.send_error(msg["id"], "unknown_entity", msg["entity_id"])
        return
    try:
        result = await runtime.irrigation.async_test(
            msg["entity_id"], seconds=msg["seconds"], with_pump=msg["with_pump"]
        )
    except HomeAssistantError as err:
        _log_error(hass, msg, "irrigation_test", err)
        connection.send_error(msg["id"], "irrigation_test", str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/irrigation/close", vol.Optional("garden_id"): str, vol.Required("entity_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_irrigation_close(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Close a valve (or stop the pump) that stayed open."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    if msg["entity_id"] not in runtime.irrigation.valve_entities():
        connection.send_error(msg["id"], "unknown_entity", msg["entity_id"])
        return
    try:
        state = await runtime.irrigation.async_close(msg["entity_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "irrigation_close", str(err))
        return
    runtime.coordinator.async_update_listeners()
    connection.send_result(msg["id"], {"state": state})


def _season_timelines(runtime: GardenRuntime, season: int) -> dict[str, Any]:
    """Timeline of every crop present in ``season`` (zone of that season's plan)."""
    data = runtime.repo.data
    db = runtime.repo.db
    layout = seasons.layout_for(data, season)
    beds = {b.id: b for b in data.beds} | ({b.id: b for b in layout.beds} if layout else {})
    zones = {z.id: z for z in data.zones} | ({z.id: z for z in layout.zones} if layout else {})
    today = dt_util.now().date()
    out = {}
    for p in data.plantings:
        plant = db.get(p.plant_id)
        if plant is None or not seasons.present_in(p, False, season):
            continue
        bed = beds.get(p.bed_id)
        zone = zones.get(bed.zone_id) if bed else None
        out[p.id] = _crop_timeline(data, p, plant, season, zone, today)
    return out


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/planning", vol.Optional("garden_id"): str, vol.Required("season"): int}
)
@websocket_api.async_response
async def ws_planning(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Seeds to buy, what can follow a crop, and the expected harvest per week."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    db = runtime.repo.db
    season = msg["season"]
    lang = runtime.coordinator.lang
    today = dt_util.now().date()

    def build() -> dict[str, Any]:
        # successions try every plant on every bed that frees up: keep it off the event loop
        timelines = _season_timelines(runtime, season)
        anchors = season_anchors(data.settings.region, season)
        return {
            "season": season,
            "seeds": [n.to_dict() for n in planning.seed_needs(data, db, season)],
            "successions": [
                b.to_dict()
                for b in planning.successions(
                    data, db, season, timelines, today=today, first_frost=anchors.first_frost, lang=lang
                )
            ],
            "harvest": planning.harvest_forecast(data, db, season, timelines),
        }

    connection.send_result(msg["id"], await hass.async_add_executor_job(build))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/seeds/to_todo",
        vol.Optional("garden_id"): str,
        vol.Required("season"): int,
        vol.Required("entity_id"): str,
    }
)
@websocket_api.async_response
async def ws_seeds_to_todo(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Put the seeds the plan still lacks on a Home Assistant to-do list (skipping items already on it)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    entity_id = msg["entity_id"]
    if not entity_id.startswith("todo.") or hass.states.get(entity_id) is None:
        connection.send_error(msg["id"], "invalid_format", f"{entity_id} is not a to-do list")
        return
    if not connection.user.permissions.check_entity(entity_id, POLICY_CONTROL):
        raise Unauthorized(context=connection.context(msg), entity_id=entity_id)  # the user's own rights apply
    needs = planning.seed_needs(runtime.repo.data, runtime.repo.db, msg["season"])
    items = planning.seed_todo_items(needs, runtime.repo.db, msg["season"], runtime.coordinator.lang)
    try:
        current = await hass.services.async_call(
            "todo", "get_items", {"status": ["needs_action"]}, target={"entity_id": entity_id},
            blocking=True, return_response=True, context=connection.context(msg),
        )  # fmt: skip
        open_items = {i.get("summary") for i in (current or {}).get(entity_id, {}).get("items", [])}
        added = 0
        for item in items:
            if item["summary"] in open_items:
                continue
            await hass.services.async_call(
                "todo", "add_item", {"item": item["summary"], "description": item["description"]},
                target={"entity_id": entity_id}, blocking=True, context=connection.context(msg),
            )  # fmt: skip
            added += 1
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], "home_assistant_error", str(err))
        return
    connection.send_result(msg["id"], {"added": added, "skipped": len(items) - added, "items": items})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/report/season", vol.Optional("garden_id"): str, vol.Required("season"): int}
)
@callback
def ws_season_report(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """End of season report: grown, harvested, lost, and what the journal said."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        connection.send_result(
            msg["id"],
            planning.season_report(
                runtime.repo.data_for_season(msg["season"]),
                runtime.repo.db,
                msg["season"],
                today=dt_util.now().date(),
                lang=runtime.coordinator.lang,
                latitude=_latitude(runtime.repo.data.settings.region.latitude, hass),
            ),
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/climate/stats",
        vol.Optional("garden_id"): str,
        vol.Optional("days", default=400): vol.All(int, vol.Range(min=7, max=climate.KEEP_DAYS)),
    }
)
@callback
def ws_climate_stats(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Climate history and statistics: what the weather did, per period, month and sensor."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    coordinator = runtime.coordinator
    today = dt_util.now().date()
    region = data.settings.region
    anchors = season_anchors(region, season_for_date(region, today))
    readings = coordinator.read_sensors()
    sensors = {
        entity_id: {**meta, "now": readings[entity_id].usable if entity_id in readings else None}
        for entity_id, meta in climate.temperature_sensors(data).items()
    }
    latitude = _latitude(region.latitude, hass)
    elevation = data.settings.elevation_m or 0.0
    hemisphere = resolve_profile(region).hemisphere
    stats = climate.climate_stats(
        data,
        today,
        latitude=latitude,
        elevation_m=elevation,
        hemisphere=hemisphere,
        preset_last=anchors.last_frost,
        preset_first=anchors.first_frost,
        sensors=sensors,
        days=msg["days"],
    )
    lang = runtime.coordinator.lang
    settings = data.settings
    if settings.season_summary:  # the season and last month in words, against last year
        month_start, month_end = climate.last_month(today)
        stats["summary"] = {
            "season": climate.summary_lines(
                climate.compare_with_last_year(
                    data, climate._season_start(today, hemisphere), today, latitude=latitude, elevation_m=elevation
                ),
                lang,
            ),
            "month": climate.summary_lines(
                climate.compare_with_last_year(data, month_start, month_end, latitude=latitude, elevation_m=elevation),
                lang,
            ),
            "month_start": month_start.isoformat(),
        }
    if settings.local_frost_suggest:
        stats["local_frost_suggestion"] = climate.local_frost_suggestion(
            data, today, anchors.last_frost, anchors.first_frost
        )
    stats["station_import"] = settings.station_import
    connection.send_result(msg["id"], stats)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/climate/import_csv",
        vol.Optional("garden_id"): str,
        vol.Required("text"): vol.All(str, vol.Length(max=20_000_000)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_climate_import_csv(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """A weather station's CSV export into the climate history (settings.station_import)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    if not data.settings.station_import:
        connection.send_error(msg["id"], "disabled", "station import is switched off")
        return
    now = dt_util.now()
    try:
        # a big export takes a moment: parse it off the event loop, merge it on the loop
        parsed = await hass.async_add_executor_job(climate.parse_station_csv, msg["text"], now.tzinfo)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_csv", str(err))
        return
    records = parsed["records"]
    changed = climate.merge_history(data, records, "history", now.date())
    if changed:
        climate.update_frost_years(data, resolve_profile(data.settings.region).hemisphere, now.date())
        runtime.repo.async_changed("climate")
    days = [r["day"] for r in records]
    connection.send_result(
        msg["id"],
        {"days": len(days), "first": min(days) if days else None, "last": max(days) if days else None,
         "rows": parsed["rows"], "columns": parsed["columns"], "changed": changed},
    )  # fmt: skip


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/photo/diagnose",
        vol.Optional("garden_id"): str,
        vol.Required("photo"): vol.All(str, vol.Match(r"^[A-Za-z0-9_-]{1,64}$")),
        vol.Optional("planting_id"): str,
        vol.Optional("bed_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_photo_diagnose(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """What is wrong with this plant? A photo (image_upload id) to an AI task entity (settings.ai_diagnosis)."""
    from .engine import photo_diagnosis as pd

    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    if not data.settings.ai_diagnosis:
        connection.send_error(msg["id"], "disabled", "photo diagnosis is switched off")
        return
    if not hass.services.has_service("ai_task", "generate_data"):
        connection.send_error(msg["id"], "ai_unavailable", "no AI task is set up in Home Assistant")
        return
    lang = runtime.coordinator.lang
    planting = data.planting(msg.get("planting_id"))
    bed_id = msg.get("bed_id") or (planting.bed_id if planting else None)
    plant_ids = (
        [planting.plant_id] if planting else [p.plant_id for p in data.plantings if bed_id and p.bed_id == bed_id]
    )
    db = runtime.repo.db
    crops = [plant.name("en") for pid in dict.fromkeys(plant_ids) if (plant := db.get(pid)) is not None]
    options = pd.candidates(db, plant_ids, lang)
    call: dict[str, Any] = {
        "task_name": "Hortulus photo diagnosis",
        "instructions": pd.instructions(crops, options, lang),
        "structure": pd.structure(),
        "attachments": [
            {"media_content_id": f"media-source://image_upload/{msg['photo']}", "media_content_type": "image/jpeg"}
        ],
    }
    if data.settings.ai_task_entity:
        call["entity_id"] = data.settings.ai_task_entity
    try:
        response = await hass.services.async_call("ai_task", "generate_data", call, blocking=True, return_response=True)
    except (HomeAssistantError, vol.Invalid) as err:
        connection.send_error(msg["id"], "ai_failed", str(err))
        return
    answer = (response or {}).get("data") if isinstance(response, dict) else None
    connection.send_result(msg["id"], pd.interpret(answer, options, lang))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/climate/apply_local_frost", vol.Optional("garden_id"): str}
)
@websocket_api.require_admin
@callback
def ws_climate_apply_local_frost(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Use the garden's measured frost dates instead of the region's (asked, never automatic)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    data = runtime.repo.data
    today = dt_util.now().date()
    region = data.settings.region
    anchors = season_anchors(region, season_for_date(region, today))
    suggestion = climate.local_frost_suggestion(data, today, anchors.last_frost, anchors.first_frost)
    if suggestion is None:
        connection.send_error(msg["id"], "no_suggestion", "not enough measured frost years yet")
        return
    resolved = resolve_profile(region)
    region.mode = "custom"
    region.hemisphere = resolved.hemisphere
    region.last_frost, region.first_frost = suggestion["last_frost"], suggestion["first_frost"]
    runtime.repo.async_changed("settings")
    connection.send_result(msg["id"], {"settings": to_dict(data.settings)})


# --------------------------------------------------------------------------- #
# Kitchen: seasonal recipes from what the garden gives, the cookbook
# --------------------------------------------------------------------------- #
def _cooking_lang(runtime: GardenRuntime, msg: dict[str, Any]) -> str:
    return str(msg.get("lang") or runtime.coordinator.lang)


def _book_entry(entry: Any, db: Any, lang: str, garden_herbs: list[str], pantry: list[str]) -> dict[str, Any] | None:
    recipe = cooking.render(entry.spec, db, lang, garden_herbs, pantry)
    if recipe is None:
        return None
    if entry.title:
        recipe["title"], recipe["subtitle"] = entry.title, ""
    recipe = cooking.apply_custom(recipe, entry.ingredients, entry.steps, lang)
    recipe["id"] = entry.id  # the entry, also when its spec was made under older rules
    return {
        **recipe,
        "saved": True,
        "favorite": entry.favorite,
        "shared": entry.shared,
        "note": entry.note,
        "added": entry.added.isoformat() if entry.added else None,
        "cooked": [d.isoformat() for d in entry.cooked],
    }


PRINT_MAX = 200  # recipes in one PDF, mail or to-do export
POLICY_CONTROL = "control"  # Home Assistant's permission policy (the website's runtime has no homeassistant.auth)


def _in_house(runtime: GardenRuntime, msg: dict[str, Any] | None = None) -> list[str]:
    """What the cook has at home: the list sent along (unsaved choices) or the saved "always in the
    house" and "use up from the fridge" lists."""
    if msg is not None and "pantry" in msg:
        return cooking.str_ids(msg["pantry"])[:80]
    prefs = cooking.Prefs.from_dict(runtime.repo.data.cooking_prefs or {})
    return [*prefs.pantry, *prefs.use]


def _cookbook(runtime: GardenRuntime, lang: str, pantry: list[str] | None = None) -> list[dict[str, Any]]:
    data, db = runtime.repo.data, runtime.repo.db
    pantry = _in_house(runtime) if pantry is None else pantry
    out = [_book_entry(e, db, lang, [], pantry) for e in data.cookbook]
    rows = [r for r in out if r is not None]
    rows.sort(key=lambda r: (not r["favorite"], r["added"] or ""), reverse=False)
    return rows


def _ready_produce(runtime: GardenRuntime, lang: str) -> list[dict[str, Any]]:
    data, db, analysis = runtime.repo.data, runtime.repo.db, runtime.coordinator.data
    if analysis is None:
        return []
    report = kitchen_report(data, db, analysis.timelines, analysis.today, lang)
    produce = cooking.ready_produce(report.get("ready", []), db)
    for p in produce:
        plant = db.get(p["plant_id"])
        p["name"] = plant.name(lang) if plant else p["plant_id"]
        p["icon"], p["color"], p["emoji"] = (plant.icon, plant.color, plant.emoji) if plant else ("", "", "")
    return produce


def _specs_or_ids(runtime: GardenRuntime, msg: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    """The recipes a command is about: saved ones by id and/or unsaved specs."""
    data, db = runtime.repo.data, runtime.repo.db
    pantry = _in_house(runtime, msg)
    out: list[dict[str, Any]] = []
    for rid in msg.get("ids") or []:
        entry = next((r for r in data.cookbook if r.id == rid), None)
        row = _book_entry(entry, db, lang, [], pantry) if entry else None
        if row is not None:
            out.append(row)
    for spec in msg.get("specs") or []:
        recipe = cooking.render(spec, db, lang, [], pantry) if isinstance(spec, dict) else None
        if recipe is not None and all(r["id"] != recipe["id"] for r in out):
            out.append(recipe)
    if len(out) > PRINT_MAX:  # never cut a cookbook off silently
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="too_many_recipes",
            translation_placeholders={"max": str(PRINT_MAX)},
        )
    return out


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/suggest",
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Optional("prefs"): dict,
        vol.Optional("produce"): [str],  # garden produce to cook with (default: what is ready now)
        vol.Optional("limit", default=12): vol.All(int, vol.Range(min=1, max=24)),
    }
)
@callback
def ws_cooking_suggest(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """What is ready, recipes for it, the cookbook and the choices the cook can make."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    lang = _cooking_lang(runtime, msg)
    db = runtime.repo.db
    saved = runtime.repo.data.cooking_prefs or {}
    prefs = cooking.Prefs.from_dict(msg.get("prefs", saved))
    ready = _ready_produce(runtime, lang)
    if "produce" in msg:
        known = {p["plant_id"]: p for p in ready}
        chosen = []
        for pid in msg["produce"]:
            plant = db.get(pid)
            kind = cooking.produce_kind(plant)
            if plant is None or kind is None:
                continue
            chosen.append(known.get(pid) or {"plant_id": pid, "kind": kind, "until": None, "beds": [], "name": plant.name(lang),
                                             "icon": plant.icon, "color": plant.color, "emoji": plant.emoji})  # fmt: skip
    else:
        chosen = ready
    edible = sorted(
        ({"plant_id": p.id, "name": p.name(lang), "kind": k, "icon": p.icon, "color": p.color, "emoji": p.emoji}
         for p in db.all() if (k := cooking.produce_kind(p)) is not None),
        key=lambda x: x["name"].lower(),
    )  # fmt: skip
    connection.send_result(
        msg["id"],
        {
            "ready": ready,
            "produce": chosen,
            "recipes": cooking.suggest(chosen, db, prefs, lang, msg["limit"]),
            "menus": cooking.menus(chosen, db, prefs, lang, 4, dt_util.now().date()),
            "prefs": saved or None,
            "used_prefs": {
                "pantry": prefs.pantry,
                "use": prefs.use,
                "proteins": prefs.proteins,
                "side": prefs.side,
                "servings": prefs.servings,
            },
            "catalog": {**cooking.catalog(lang), "edible": edible},
            "book": _cookbook(runtime, lang, [*prefs.pantry, *prefs.use]),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/render",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("spec"): dict,
    }
)
@callback
def ws_cooking_render(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """A recipe again after the cook changed its side, meat, extras or servings."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    recipe = cooking.render(msg["spec"], runtime.repo.db, _cooking_lang(runtime, msg), [], _in_house(runtime, msg))
    if recipe is None:
        connection.send_error(msg["id"], "invalid_recipe", "This recipe cannot be made")
        return
    entry = next((r for r in runtime.repo.data.cookbook if r.id == recipe["id"]), None)
    connection.send_result(msg["id"], {"recipe": recipe, "saved": entry is not None})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/book/save",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("recipe"): dict,
    }
)
@callback
def ws_cookbook_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"id": op_cookbook_save(runtime, msg["recipe"]).id,
                                         "book": _cookbook(runtime, _cooking_lang(runtime, msg), _in_house(runtime, msg))})  # fmt: skip


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/book/update",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("recipe_id"): str,
        vol.Required("changes"): dict,
    }
)
@callback
def ws_cookbook_update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"id": op_cookbook_update(runtime, msg["recipe_id"], msg["changes"]).id,
                                         "book": _cookbook(runtime, _cooking_lang(runtime, msg), _in_house(runtime, msg))})  # fmt: skip


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/book/delete",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("recipe_id"): str,
    }
)
@callback
def ws_cookbook_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:

        def run() -> dict[str, Any]:
            op_cookbook_delete(runtime, msg["recipe_id"])
            return {"book": _cookbook(runtime, _cooking_lang(runtime, msg), _in_house(runtime, msg))}

        _ws_op(connection, msg, run)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/cooking/prefs", vol.Optional("garden_id"): str, vol.Required("prefs"): dict}
)
@callback
def ws_cooking_prefs(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    runtime = _require_runtime(hass, connection, msg)
    if runtime is not None:
        _ws_op(connection, msg, lambda: {"prefs": op_cooking_prefs(runtime, msg["prefs"])})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/pdf",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("kind"): vol.In(["recipe", "book", "shopping"]),
        vol.Optional("ids"): [str],
        vol.Optional("specs"): [dict],
        vol.Optional("images"): {str: str},  # recipe id -> base64 JPEG of the dish picture
        vol.Optional("title"): str,
    }
)
@websocket_api.async_response
async def ws_cooking_pdf(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """A recipe, a cookbook or a shopping list as PDF (base64; the panel saves or prints it)."""
    import base64
    import binascii

    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    lang = _cooking_lang(runtime, msg)
    recipes = _specs_or_ids(runtime, msg, lang)
    if not recipes:
        connection.send_error(msg["id"], "invalid_recipe", "No recipe to print")
        return
    images: dict[str, bytes] = {}
    for rid, b64 in list((msg.get("images") or {}).items())[:PRINT_MAX]:
        try:
            images[rid] = base64.b64decode(b64.split(",")[-1], validate=False)
        except (binascii.Error, ValueError):
            continue
    title = (msg.get("title") or "").strip()[:80] or None
    pdf = await hass.async_add_executor_job(
        lambda: cooking.recipes_pdf(recipes, lang, msg["kind"], images, dt_util.now().date(), title)
    )
    stem = {"recipe": recipes[0]["title"], "book": title or "kookboek", "shopping": "boodschappen"}[msg["kind"]]
    safe = "".join(c if c.isalnum() else "-" for c in str(stem).lower()).strip("-")[:60] or "hortulus"
    connection.send_result(
        msg["id"], {"pdf": base64.b64encode(pdf).decode(), "filename": f"hortulus-{safe}.pdf", "bytes": len(pdf)}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/send",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("what"): vol.In(["recipe", "shopping"]),
        vol.Optional("ids"): [str],
        vol.Optional("specs"): [dict],
        vol.Optional("service"): str,  # notify.mobile_app_x (default: the garden's notification settings)
        vol.Optional("dry_run", default=False): bool,  # only the text (the website mails it itself)
    }
)
@websocket_api.async_response
async def ws_cooking_send(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Send a recipe or the shopping list to a phone (Home Assistant notification)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    lang = _cooking_lang(runtime, msg)
    recipes = _specs_or_ids(runtime, msg, lang)
    if not recipes:
        connection.send_error(msg["id"], "invalid_recipe", "Nothing to send")
        return
    if msg["what"] == "shopping":
        text = cooking.shopping_text(recipes, lang)
        title = cooking.label("shopping", lang)
    else:
        text, title = cooking.recipe_text(recipes[0], lang), str(recipes[0]["title"])
    if msg["dry_run"]:
        connection.send_result(msg["id"], {"sent": False, "title": title, "text": text})
        return
    service = msg.get("service") or ""
    try:
        if service:
            domain, _, name = service.partition(".")
            if domain != "notify" or not hass.services.has_service(domain, name):
                connection.send_error(msg["id"], "invalid_format", f"{service} is not a notify service")
                return
            await hass.services.async_call(domain, name, {"title": title, "message": text}, blocking=True)
        else:
            await runtime.notifier.async_send(title, text, notification_id=f"{DOMAIN}_cooking_{msg['what']}")
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "home_assistant_error", str(err))
        return
    connection.send_result(msg["id"], {"sent": True, "title": title, "text": text})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cooking/to_todo",
        vol.Optional("pantry"): [str],  # what the cook has at home (unsaved choices)
        vol.Optional("garden_id"): str,
        vol.Optional("lang"): str,
        vol.Required("entity_id"): str,
        vol.Optional("ids"): [str],
        vol.Optional("specs"): [dict],
    }
)
@websocket_api.async_response
async def ws_cooking_to_todo(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Put the shopping list on a Home Assistant to-do list (items already on it are skipped)."""
    runtime = _require_runtime(hass, connection, msg)
    if runtime is None:
        return
    entity_id = msg["entity_id"]
    if not entity_id.startswith("todo.") or hass.states.get(entity_id) is None:
        connection.send_error(msg["id"], "invalid_format", f"{entity_id} is not a to-do list")
        return
    if not connection.user.permissions.check_entity(entity_id, POLICY_CONTROL):
        raise Unauthorized(context=connection.context(msg), entity_id=entity_id)  # the user's own rights apply
    lang = _cooking_lang(runtime, msg)
    rows = cooking.shopping_list(_specs_or_ids(runtime, msg, lang), lang)["buy"]
    try:
        current = await hass.services.async_call(
            "todo", "get_items", {"status": ["needs_action"]}, target={"entity_id": entity_id},
            blocking=True, return_response=True, context=connection.context(msg),
        )  # fmt: skip
        open_items = {str(i.get("summary", "")).lower() for i in (current or {}).get(entity_id, {}).get("items", [])}
        added = 0
        for row in rows:
            if str(row["name"]).lower() in open_items:
                continue
            await hass.services.async_call(
                "todo", "add_item", {"item": row["name"], "description": row["label"]},
                target={"entity_id": entity_id}, blocking=True, context=connection.context(msg),
            )  # fmt: skip
            added += 1
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], "home_assistant_error", str(err))
        return
    connection.send_result(msg["id"], {"added": added, "skipped": len(rows) - added})
