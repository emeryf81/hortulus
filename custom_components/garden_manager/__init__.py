"""Hortulus - vegetable garden planning and care for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .actions import ACTION_EVENT
from .const import DOMAIN, PLATFORMS
from .controllers import ClimateController, IrrigationController
from .coordinator import GardenCoordinator
from .engine.i18n import normalize_lang
from .engine.plantdb import PlantDatabase, load_builtin_json
from .gardens import loaded, storage_key
from .notifications import GardenNotifier
from .options import apply_options
from .panel import async_register_panel, async_unregister_panel
from .printing import async_register_print_view
from .seed import build_initial_data
from .services import async_setup_services
from .storage import GardenRepository
from .voice import async_setup_intents
from .websocket_api import async_notify_reloaded, async_setup_websocket, clear_diagnosis_cache

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class GardenRuntime:
    repo: GardenRepository
    coordinator: GardenCoordinator
    notifier: GardenNotifier
    irrigation: IrrigationController
    climate: ClimateController


type GardenConfigEntry = ConfigEntry[GardenRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services and websocket commands once (HA best practice)."""
    async_setup_services(hass)
    async_setup_websocket(hass)
    async_setup_intents(hass)
    async_register_print_view(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GardenConfigEntry) -> bool:
    builtin = await hass.async_add_executor_job(load_builtin_json)
    repo = GardenRepository(hass, builtin, storage_key(entry))
    if await repo.async_load():
        _LOGGER.info("Creating initial Hortulus garden from setup answers")
        repo.data = build_initial_data(
            {**entry.data, **entry.options},
            latitude=hass.config.latitude,
            time_zone=hass.config.time_zone,
            language=normalize_lang(hass.config.language),
            today=dt_util.now().date(),
            db=PlantDatabase(builtin),
        )
        await repo.async_flush()

    repo.adopt_seasons()
    coordinator = GardenCoordinator(hass, entry, repo)
    notifier = GardenNotifier(hass, repo)
    irrigation = IrrigationController(hass, coordinator)
    climate = ClimateController(hass, coordinator)
    entry.runtime_data = GardenRuntime(repo, coordinator, notifier, irrigation, climate)
    entry.async_on_unload(coordinator.async_add_post_compute_hook(notifier.async_process))
    entry.async_on_unload(coordinator.async_add_listener(climate.async_apply))
    entry.async_on_unload(irrigation.async_stop_on_unload)
    irrigation.notifier = notifier
    notifier.actions.runtime = entry.runtime_data
    entry.async_on_unload(hass.bus.async_listen(ACTION_EVENT, notifier.actions.handle))
    entry.async_on_unload(async_track_time_interval(hass, irrigation.async_watch, timedelta(minutes=1)))

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass)

    @callback
    def _midnight(now: datetime) -> None:
        """New day: expire yesterday's sensor tasks, roll windows forward."""
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(async_track_time_change(hass, _midnight, hour=0, minute=5, second=0))
    _schedule_digest(hass, entry)
    _schedule_reminders(hass, entry)
    _schedule_irrigation(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    async_notify_reloaded(hass, entry.entry_id, entry.runtime_data)
    return True


def _schedule_digest(hass: HomeAssistant, entry: GardenConfigEntry) -> None:
    """Daily digest at the configured time; follows changes made in the panel."""
    runtime = entry.runtime_data
    unsub: CALLBACK_TYPE | None = None
    scheduled_for: str | None = None

    async def _digest(now: datetime) -> None:
        if runtime.coordinator.data is not None:
            await runtime.notifier.async_send_digest(runtime.coordinator.data)

    @callback
    def _reschedule(reason: str = "settings") -> None:
        nonlocal unsub, scheduled_for
        if reason != "settings":
            return
        wanted = runtime.repo.data.settings.notifications.digest_time
        if wanted == scheduled_for:
            return
        if unsub:
            unsub()
        hh, _, mm = wanted.partition(":")
        try:
            hour, minute = int(hh), int(mm or 0)
        except ValueError:
            hour, minute = 7, 30
        unsub = async_track_time_change(hass, _digest, hour=hour, minute=minute, second=0)
        scheduled_for = wanted

    @callback
    def _cancel() -> None:
        if unsub:
            unsub()

    _reschedule()
    entry.async_on_unload(runtime.repo.async_add_listener(_reschedule))
    entry.async_on_unload(_cancel)


def _schedule_reminders(hass: HomeAssistant, entry: GardenConfigEntry) -> None:
    """Overdue reminder and weekly look-ahead; checked every quarter of an hour.

    Times come from the settings (editable in the panel), de-duplication from
    the notifier's day keys, so a restart never sends them twice.
    """
    runtime = entry.runtime_data

    async def _tick(now: datetime) -> None:
        analysis = runtime.coordinator.data
        if analysis is None:
            return
        cfg = runtime.repo.data.settings.notifications
        hhmm = now.strftime("%H:%M")
        if _passed(hhmm, cfg.overdue_time):
            await runtime.notifier.async_send_overdue(analysis)
        if now.weekday() == cfg.weekly_plan_weekday and _passed(hhmm, cfg.weekly_plan_time):
            await runtime.notifier.async_send_weekly(analysis)
        from .calendar_mirror import async_mirror_tasks  # (imports the calendar platform)

        await async_mirror_tasks(hass, runtime, now.date())  # new tasks reach the other calendar within 15 min

    entry.async_on_unload(async_track_time_change(hass, _tick, minute=[0, 15, 30, 45], second=0))


def _passed(now_hhmm: str, wanted: str) -> bool:
    """True from the configured time until midnight (the day key prevents repeats)."""
    return len(wanted) >= 4 and now_hhmm >= wanted.zfill(5)


def _schedule_irrigation(hass: HomeAssistant, entry: GardenConfigEntry) -> None:
    """Automatic watering at the configured start time (mode ``auto`` only)."""
    runtime = entry.runtime_data
    unsub: CALLBACK_TYPE | None = None
    scheduled_for: str | None = None

    async def _run(now: datetime) -> None:
        await runtime.irrigation.async_start_scheduled(now)  # (waits for solar surplus when asked to)

    @callback
    def _reschedule(reason: str = "settings") -> None:
        nonlocal unsub, scheduled_for
        if reason != "settings":
            return
        wanted = runtime.repo.data.settings.irrigation.start_time
        if wanted == scheduled_for:
            return
        if unsub:
            unsub()
        hh, _, mm = wanted.partition(":")
        try:
            hour, minute = int(hh), int(mm or 0)
        except ValueError:
            hour, minute = 6, 0
        unsub = async_track_time_change(hass, _run, hour=hour, minute=minute, second=0)
        scheduled_for = wanted

    @callback
    def _cancel() -> None:
        if unsub:
            unsub()

    _reschedule()
    entry.async_on_unload(runtime.repo.async_add_listener(_reschedule))
    entry.async_on_unload(_cancel)


async def _async_update_listener(hass: HomeAssistant, entry: GardenConfigEntry) -> None:
    """Options flow saved: copy into the store and reload."""
    apply_options(entry.runtime_data.repo, dict(entry.options))
    await entry.runtime_data.repo.async_flush()
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: GardenConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        clear_diagnosis_cache(entry.runtime_data)
        # stop a watering run first: its clean-up writes the tasks, and must not land after the flush
        await entry.runtime_data.irrigation.async_stop()
        await entry.runtime_data.repo.async_flush()
        if not [e for e in loaded(hass) if e.entry_id != entry.entry_id]:
            async_unregister_panel(hass)  # the panel stays while another garden is loaded
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: GardenConfigEntry) -> None:
    """Remove stored garden data, keeping one backup copy for recovery."""
    key = storage_key(entry)
    store: Store[dict] = Store(hass, 1, key)
    raw = await store.async_load()
    if raw is not None:
        await Store[dict](hass, 1, f"{key}.backup").async_save(raw)
    await store.async_remove()
