"""Hardware actuation: irrigation valves + pump, greenhouse vents and shading.

Safety first - every rule from ``engine/irrigation.py`` is re-checked right
before a run, and the controller adds the runtime guarantees:

* **One run at a time** (``asyncio.Lock``); a second request is refused.
* **Pump interlock** - valve open → wait → pump on … pump off → wait →
  valve closed.  The pump never runs against closed valves.
* **Max runtime** - clamped again here, independent of the plan.
* **Always clean up** - a ``finally`` block closes every valve that was
  touched and switches the pump off, also on errors and on cancellation
  (``stop`` service, Home Assistant shutdown).
* Every run is written to ``irrigation_log`` (feeds the water balance) and
  fired as ``garden_manager_irrigation_run``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import logging
import math
from typing import TYPE_CHECKING, Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import EVENT_IRRIGATION_RUN
from .engine.adaptive import (
    SOAK_MINUTES,
    book_heater,
    choose_water,
    expected_rise,
    heater_wanted,
    learn_water_factor,
    pump_kwh,
    water_factor,
)
from .engine.irrigation import IrrigationPlan, plan_irrigation
from .engine.models import GreenhouseAction, IrrigationEvent
from .engine.records import book_irrigation
from .engine.waterbalance import trim_irrigation_log

if TYPE_CHECKING:
    from .coordinator import GardenCoordinator

_LOGGER = logging.getLogger(__name__)

VALVE_SETTLE_S = 1.0
# How long a valve may take to report its new state.
STATE_TIMEOUT_S = 5.0
# A valve open this much longer than the longest allowed run (without Hortulus
# watering) is reported as stuck.
STUCK_MARGIN_MIN = 10
TEST_MAX_S = 60
# Watering is held in steps so a valve that shuts by itself is noticed.
HOLD_STEP_S = 30.0
LOST_VALVE_S = 60.0  # a pumped valve that reports nothing for this long ends the run
# The valve's own timer is left this much room before Hortulus re-opens it.
TIMER_MARGIN_MIN = 1.0
# A pause between closing and re-opening a valve with its own timer.
REOPEN_PAUSE_S = 3.0
# Flow is learned from runs of at least this long (meters update in steps).
LEARN_MIN_MINUTES = 3.0
# Leak: this much water within LEAK_WINDOW_MIN while every valve is closed.
LEAK_LITERS = 5.0
LEAK_WINDOW_MIN = 15

# Only settled states count; "opening" / "closing" are still on their way.
_OPEN = {"on", "open"}
_CLOSED = {"off", "closed"}


def _is_open(state: str | None) -> bool | None:
    """``True``/``False`` for a settled valve/switch state, ``None`` when moving, unknown or unavailable."""
    if state in _OPEN:
        return True
    if state in _CLOSED:
        return False
    return None


def _on_service(entity_id: str, on: bool) -> tuple[str, str]:
    domain = entity_id.split(".", 1)[0]
    if domain == "valve":
        return "valve", "open_valve" if on else "close_valve"
    if domain == "cover":
        return "cover", "open_cover" if on else "close_cover"
    if domain in ("switch", "input_boolean", "fan", "light"):
        return domain, "turn_on" if on else "turn_off"
    return "homeassistant", "turn_on" if on else "turn_off"


async def _switch(hass: HomeAssistant, entity_id: str, on: bool) -> None:
    domain, service = _on_service(entity_id, on)
    await hass.services.async_call(domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=True)


def _chunks(minutes: float, valve_max_min: float | None) -> list[float]:
    """Split a run so each opening stays inside the valve's own timer."""
    if not valve_max_min or valve_max_min <= 0:
        return [minutes]
    # a short timer keeps a quarter of its length as margin (1 min -> 45 s openings)
    step = valve_max_min - min(TIMER_MARGIN_MIN, valve_max_min / 4)
    out = []
    left = minutes
    while left > 1e-6:
        out.append(min(step, left))
        left -= step
    return out


@dataclass(slots=True)
class RunStatus:
    running: bool = False
    bed_id: str | None = None
    started_at: datetime | None = None
    ends_at: datetime | None = None
    last_plan: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None


class IrrigationController:
    def __init__(self, hass: HomeAssistant, coordinator: GardenCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self.status = RunStatus()
        self.notifier: Any = None  # set by __init__ (GardenNotifier)
        # entity_id -> since when it is open while Hortulus is not watering
        self._open_since: dict[str, datetime] = {}
        self.stuck: dict[str, datetime] = {}
        self._reported: set[str] = set()
        # water meter readings (time, litres) while nothing waters, and the leak being reported
        self._meter_window: list[tuple[datetime, float]] = []
        self._quiet_since: datetime | None = None
        self.leak: dict[str, Any] | None = None
        self._partial_s = 0.0  # seconds held by an opening that was interrupted
        self.waiting_for_sun: dict[str, Any] | None = None  # a scheduled run waiting for solar surplus
        self._scheduled_on: date | None = None  # the day the scheduled run last fired
        # runs whose soil moisture is read again after a while (adaptive irrigation)
        self._soak_checks: list[dict[str, Any]] = []
        self.waiting_for_rain: str | None = None  # ISO date a run was held back: the butt was empty

    @property
    def running(self) -> bool:
        # A run that is scheduled but has not taken the lock yet counts as running,
        # otherwise two quick requests would water the beds twice.
        return self._lock.locked() or (self._task is not None and not self._task.done())

    def build_plan(
        self,
        *,
        force: bool = False,
        bed_ids: set[str] | None = None,
        override_mm: float | None = None,
        only_if_needed: bool = False,
    ) -> IrrigationPlan:
        analysis = self.coordinator.data
        data = self.coordinator.repo.data
        recs = {k: b.irrigation for k, b in analysis.beds.items()} if analysis else {}
        outdoor_temp = None
        if data.settings.outdoor_sensors.air_temperature:
            state = self.hass.states.get(data.settings.outdoor_sensors.air_temperature)
            outdoor_temp = _float(state.state) if state else None
        if outdoor_temp is None:
            outdoor_temp = self.coordinator.weather.temperature
        return plan_irrigation(
            data,
            recs,
            now=dt_util.now(),
            frost_by_zone={k: z.frost for k, z in analysis.zones.items()} if analysis else {},
            outdoor_frost=analysis.frost if analysis else None,
            outdoor_temp=outdoor_temp,
            zone_air={k: z.air_temperature for k, z in analysis.zones.items()} if analysis else {},
            force=force,
            bed_ids=bed_ids,
            override_mm=override_mm,
            only_if_needed=only_if_needed,
        )

    @callback
    def async_start(self, plan: IrrigationPlan, *, source: str = "auto") -> bool:
        """Run ``plan`` in the background; False when a run is already active."""
        if self.running or not plan.runs:
            return False
        self._task = self.hass.async_create_background_task(self._run(plan, source), "hortulus_irrigation")
        return True

    @callback
    def async_stop_on_unload(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()  # the run's finally block closes everything

    async def async_stop(self) -> None:
        self._set_waiting(None)  # Stop also ends a run that is still waiting for the sun
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self, plan: IrrigationPlan, source: str) -> None:
        settings = self.coordinator.repo.data.settings.irrigation
        touched: set[str] = set()
        pumps: set[str] = set()  # every pump this run switched (mains and/or rain water)
        async with self._lock:
            self.status = RunStatus(running=True, last_plan=plan.to_dict())
            try:
                for run in plan.runs:
                    minutes = min(run.minutes, settings.max_runtime_min)
                    if minutes <= 0:
                        continue
                    water = choose_water(settings, self.butt_pct())  # per bed: the butt can run dry
                    if water.water is None:
                        self._hold_for_rain(run.bed_id)
                        continue
                    pump = water.pump
                    if pump:
                        pumps.add(pump)
                    moisture_before = self._moisture(run.bed_id)
                    self.status.bed_id = run.bed_id
                    self.status.started_at = dt_util.now()
                    self.status.ends_at = dt_util.now() + timedelta(minutes=minutes)
                    self.coordinator.async_update_listeners()
                    bed = self.coordinator.repo.data.bed(run.bed_id)
                    chunks = _chunks(minutes, bed.valve_max_min if bed else None)
                    meter_start = self.meter_liters()
                    ran_s = 0.0
                    self._partial_s = 0.0
                    try:
                        for n, chunk in enumerate(chunks):
                            if n:
                                await asyncio.sleep(REOPEN_PAUSE_S)
                            held, closed_early = await self._open_for(run.entity_id, pump, chunk * 60, touched)
                            ran_s += held
                            if held == 0 and not closed_early:
                                break  # the valve never opened (reported by _open_for)
                            if closed_early:
                                self._problem(run.entity_id, "valve_closed_early", self._state(run.entity_id),
                                              bed_id=run.bed_id, minutes=round(ran_s / 60, 1))  # fmt: skip
                                break
                    finally:
                        # an interrupted run books the time that really passed
                        ran_s += self._partial_s
                        self.hass.async_create_background_task(
                            self._verify_closed(run.entity_id, run.bed_id), "hortulus_verify_valve"
                        )
                        ran_min = min(ran_s / 60, minutes)
                        event = self._log(run.bed_id, ran_min, run, source, meter_start, water=water.water,
                                          kwh=pump_kwh(ran_min, water.power_w))  # fmt: skip
                        self._plan_soak_check(event, moisture_before)
            except asyncio.CancelledError:
                _LOGGER.info("Irrigation run cancelled")
                raise
            except HomeAssistantError as err:
                _LOGGER.error("Irrigation run aborted: %s", err)
                self.status.last_error = str(err)
            finally:
                # Belt and braces: everything off, whatever happened - the pumps first,
                # so they never push against valves that are already shut.
                for pump in pumps:
                    try:
                        await _switch(self.hass, pump, False)
                    except HomeAssistantError:
                        _LOGGER.exception("Could not stop pump %s", pump)
                for entity_id in touched:
                    try:
                        await _switch(self.hass, entity_id, False)
                    except HomeAssistantError:
                        _LOGGER.exception("Could not close %s", entity_id)
                self.status.running = False
                self.status.bed_id = None
                self.status.ends_at = None
                self.coordinator.repo.async_changed("tasks", source="system")

    async def _open_for(
        self, entity_id: str, pump: str | None, seconds: float, touched: set[str]
    ) -> tuple[float, bool]:
        """Open a valve (then the pump), hold, close in the safe order.

        Returns the seconds it was held and whether the valve shut by itself
        (it reported open, then closed while Hortulus still wanted water).
        """
        touched.add(entity_id)
        seen_open = False
        pump_on = False
        started = dt_util.now()
        held = 0.0
        last_open = 0.0  # held seconds at the last sample that saw the valve open
        closed_early = False
        done = False
        lost_s = 0.0  # seconds the valve has reported nothing at all
        try:
            await _switch(self.hass, entity_id, True)
            # the pump only ever runs against a valve that reported open; without a pump a valve that
            # plainly stays closed ends the run too (one that reports nothing is trusted)
            state = await self._wait_for(entity_id, True)
            if _is_open(state) is not True and (pump or _is_open(state) is False):
                self._problem(entity_id, "valve_did_not_open", state)
                done = True
                return 0.0, False
            seen_open = _is_open(state) is True
            if pump:
                await asyncio.sleep(VALVE_SETTLE_S)
                pump_on = True  # set before the call: a pump that starts and then raises is stopped too
                await _switch(self.hass, pump, True)
            started = dt_util.now()
            while held < seconds:
                step = min(HOLD_STEP_S, seconds - held)
                await asyncio.sleep(step)
                held += step
                is_open = _is_open(self._state(entity_id))
                if is_open is None and pump:
                    lost_s += step
                    if lost_s >= LOST_VALVE_S:  # no way to tell the pump still has an open outlet
                        self._problem(entity_id, "valve_lost", self._state(entity_id))
                        closed_early = True
                        held = last_open
                        break
                else:
                    lost_s = 0.0
                if is_open is True:
                    seen_open = True
                    last_open = held
                elif seen_open and is_open is False:
                    # shut by itself (also at the last sample): book only the time it was seen open
                    closed_early = True
                    held = last_open
                    break
            done = True
        finally:
            if not done:
                self._partial_s = (
                    min(seconds, (dt_util.now() - started).total_seconds()) if pump_on or not pump else 0.0
                )
            if pump_on:
                await _switch(self.hass, pump, False)
                await asyncio.sleep(self.coordinator.repo.data.settings.irrigation.pump_lead_s)
            await _switch(self.hass, entity_id, False)
            touched.discard(entity_id)
        return held, closed_early

    # ------------------------------------------------------------------ #
    # The water meter: measured flow and leaks
    # ------------------------------------------------------------------ #
    def meter_liters(self) -> float | None:
        """The garden water meter in litres (meters report m³ or L)."""
        entity_id = self.coordinator.repo.data.settings.water.meter_entity
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        from .coordinator import volume_liters

        return volume_liters(value, state.attributes.get("unit_of_measurement"))

    def _learn_flow(self, bed: Any, minutes: float, liters: float) -> None:
        if minutes < LEARN_MIN_MINUTES or liters <= 0:
            return
        measured = liters / minutes
        old = bed.measured_flow_lpm
        bed.measured_flow_lpm = round(measured if not old else old * 0.7 + measured * 0.3, 2)

    @callback
    def _watch_meter(self, now: datetime, any_open: bool) -> bool:
        """Water counted while every valve is closed (and nothing runs) -> a leak notification."""
        water = self.coordinator.repo.data.settings.water
        liters = self.meter_liters() if water.meter_entity and water.leak_alerts else None
        if liters is None or self.running or any_open:
            self._meter_window.clear()
            self._quiet_since = None
            return False
        self._quiet_since = self._quiet_since or now
        window = timedelta(minutes=LEAK_WINDOW_MIN)
        self._meter_window.append((now, liters))
        self._meter_window = [(t, v) for t, v in self._meter_window if now - t <= window]
        if now - self._quiet_since < window or len(self._meter_window) < 2:
            return False  # a run just ended: the meter may still be catching up
        used = liters - self._meter_window[0][1]
        if used >= LEAK_LITERS and self.leak is None:
            minutes = round((now - self._meter_window[0][0]).total_seconds() / 60)
            self.leak = {"entity_id": water.meter_entity, "since": self._meter_window[0][0].isoformat(),
                         "liters": round(used, 1), "minutes": minutes}  # fmt: skip
            self._problem(water.meter_entity, "water_leak", None, liters=round(used, 1), minutes=minutes)  # type: ignore[arg-type]
            return True
        if used < 0.5 and self.leak is not None:
            self.leak = None
            self._reported.discard(water.meter_entity)  # type: ignore[arg-type]
            return True
        return False

    # ------------------------------------------------------------------ #
    # Checking the hardware
    # ------------------------------------------------------------------ #
    def valve_entities(self) -> dict[str, str]:
        """Every valve/pump Hortulus drives -> what it is (bed name or ``pump``)."""
        data = self.coordinator.repo.data
        out = {b.irrigation_entity: b.name for b in data.beds if b.irrigation_entity}
        for pump in (data.settings.irrigation.pump_entity, data.settings.irrigation.butt_pump_entity):
            if pump:
                out[pump] = "pump"
        return out

    # ------------------------------------------------------------------ #
    # Rain water and soil moisture
    # ------------------------------------------------------------------ #
    def butt_pct(self) -> float | None:
        """How full the rain water butt is now (%), None without a (working) level sensor."""
        return _float(self._state(self.coordinator.repo.data.settings.water.butt_level_entity or ""))

    def _moisture(self, bed_id: str) -> float | None:
        bed = self.coordinator.repo.data.bed(bed_id)
        entity_id = bed.sensors.soil_moisture if bed else None
        return _float(self._state(entity_id)) if entity_id else None

    def _hold_for_rain(self, bed_id: str) -> None:
        """The butt is empty and mains water is not allowed: skip, and say so once a day."""
        today = dt_util.now().date().isoformat()
        _LOGGER.info("Irrigation of %s held back: the rain water butt is empty", bed_id)
        if self.waiting_for_rain == today:
            return
        self.waiting_for_rain = today
        self.coordinator.async_update_listeners()
        if self.notifier is not None:
            from .engine.i18n import t

            lang = self.coordinator.lang
            self.hass.async_create_task(
                self.notifier.async_send(
                    t("notify.butt_empty_title", lang),
                    t("notify.butt_empty", lang, pct=self.butt_pct()),
                    notification_id="hortulus_butt_empty",
                    tts=False,
                )
            )

    def _plan_soak_check(self, event: IrrigationEvent | None, before: float | None) -> None:
        """Read the bed's moisture again in a while: how much of the water really soaked in?"""
        settings = self.coordinator.repo.data.settings
        if event is None or before is None or not settings.adaptive_irrigation or event.mm <= 0:
            return
        bed = self.coordinator.repo.data.bed(event.bed_id)
        if bed is None or not bed.area_m2:
            return
        delivered_mm = event.liters / bed.area_m2 if event.liters else event.mm
        self._soak_checks = [c for c in self._soak_checks if c["bed_id"] != event.bed_id]
        self._soak_checks.append({
            "bed_id": event.bed_id, "before": before, "mm": delivered_mm,
            "due": event.at + timedelta(minutes=SOAK_MINUTES), "rain": self._rain_24h(event.bed_id),
        })  # fmt: skip

    def _rain_24h(self, bed_id: str) -> float:
        analysis = self.coordinator.data
        bed = analysis.beds.get(bed_id) if analysis else None
        rec = bed.irrigation if bed else None
        return float(rec.rain_24h_mm or 0.0) if rec else 0.0

    def _check_soak(self, now: datetime) -> bool:
        """Due checks: learn the bed's water factor (skipped when it rained in between)."""
        due = [c for c in self._soak_checks if c["due"] <= now]
        if not due:
            return False
        self._soak_checks = [c for c in self._soak_checks if c["due"] > now]
        data = self.coordinator.repo.data
        learned = False
        for check in due:
            bed = data.bed(check["bed_id"])
            after = self._moisture(check["bed_id"])
            if bed is None or after is None or self._rain_24h(check["bed_id"]) - check["rain"] > 0.5:
                continue
            expected = expected_rise(check["mm"], data.settings.root_zone_depth_mm)
            if learn_water_factor(bed, expected, after - check["before"]):
                learned = True
                _LOGGER.debug("Water factor of %s now %s (%s runs)", bed.name, bed.water_factor, bed.water_factor_runs)
        if learned:
            self.coordinator.repo.async_schedule_save()
        return learned

    def _state(self, entity_id: str) -> str | None:
        state = self.hass.states.get(entity_id)
        return state.state if state else None

    async def _wait_for(self, entity_id: str, want_open: bool) -> str | None:
        """Wait until the entity reports the wanted state; returns the last state seen."""
        for _ in range(max(1, int(STATE_TIMEOUT_S / 0.25))):
            state = self._state(entity_id)
            if _is_open(state) is want_open:
                return state
            await asyncio.sleep(0.25)
        return self._state(entity_id)

    async def _verify_closed(self, entity_id: str, bed_id: str | None) -> None:
        state = await self._wait_for(entity_id, False)
        if _is_open(state) is not False:  # still open, stuck closing, or not reporting
            self._problem(entity_id, "valve_not_closed", state, bed_id=bed_id)

    def _problem(
        self, entity_id: str, code: str, state: str | None, *, bed_id: str | None = None, **params: Any
    ) -> None:
        """Log a hardware problem and notify (once per valve until it is fine again)."""
        what = self.valve_entities().get(entity_id, entity_id)
        message = f"{entity_id} ({what}): {code}, state {state!r}"
        _LOGGER.warning("Irrigation hardware: %s", message)
        self.coordinator.repo.record_error(
            "irrigation", code, message, {"entity_id": entity_id, "bed_id": bed_id, "state": state}
        )
        if entity_id in self._reported:
            return
        self._reported.add(entity_id)
        if self.notifier is not None:
            from .engine.i18n import t

            lang = self.coordinator.lang
            data = None
            if code in ("valve_stuck", "valve_not_closed") and getattr(self.notifier, "actions", None):
                data = {
                    "tag": f"hortulus_valve_{entity_id}",
                    "actions": self.notifier.actions.for_valve(entity_id, lang),
                }
            self.hass.async_create_task(
                self.notifier.async_send(
                    t("notify.valve_title", lang),
                    t(f"notify.{code}", lang, entity=entity_id, what=what, **params),
                    notification_id=f"hortulus_valve_{entity_id}",
                    tts=False,
                    data=data,
                )
            )

    async def async_test(self, entity_id: str, *, seconds: float = 5, with_pump: bool = True) -> dict[str, Any]:
        """Open a valve briefly (with the pump, in the safe order) and check it reports open and closed."""
        if self.running:
            raise HomeAssistantError("irrigation is running")
        seconds = max(1.0, min(float(seconds), TEST_MAX_S))
        irr = self.coordinator.repo.data.settings.irrigation
        if entity_id in (irr.pump_entity, irr.butt_pump_entity):
            # a pump must never run on its own against closed valves: test it through a bed valve
            raise HomeAssistantError("the pump is tested together with a bed valve")
        pump = choose_water(irr, self.butt_pct()).pump if with_pump else None
        result: dict[str, Any] = {"entity_id": entity_id, "seconds": seconds, "before": self._state(entity_id)}
        # a task of its own, like a watering run: Stop (and Close) can end it, pump first
        task = self.hass.async_create_background_task(
            self._test(entity_id, seconds, pump, result), "hortulus_valve_test"
        )
        self._task = task
        try:
            await task
        except asyncio.CancelledError:
            me = asyncio.current_task()
            if not task.cancelled() or (me is not None and me.cancelling()):
                raise  # not stopped by Stop/Close, but this call itself was cancelled
            result["stopped"] = True
            result.setdefault("closed_state", self._state(entity_id))
            result["closed"] = _is_open(result["closed_state"]) is False
        ok = bool(result.get("opened")) and result["closed"]
        result["ok"] = ok
        if result.get("stopped"):
            pass  # stopped on purpose: nothing to report
        elif not result.get("opened"):
            self._problem(entity_id, "valve_did_not_open", result.get("open_state"))
        elif not result["closed"]:
            self._problem(entity_id, "valve_not_closed", result["closed_state"])
        return result

    async def _test(self, entity_id: str, seconds: float, pump: str | None, result: dict[str, Any]) -> None:
        async with self._lock:
            try:
                await _switch(self.hass, entity_id, True)
                result["open_state"] = await self._wait_for(entity_id, True)
                result["opened"] = _is_open(result["open_state"])
                if result["opened"]:
                    # the pump only ever runs against a valve that reported open
                    if pump:
                        await asyncio.sleep(VALVE_SETTLE_S)
                        await _switch(self.hass, pump, True)
                    await asyncio.sleep(seconds)
                else:
                    pump = None
            finally:
                try:
                    if pump:
                        await _switch(self.hass, pump, False)
                        await asyncio.sleep(self.coordinator.repo.data.settings.irrigation.pump_lead_s)
                finally:
                    await _switch(self.hass, entity_id, False)
            result["closed_state"] = await self._wait_for(entity_id, False)
            result["closed"] = _is_open(result["closed_state"]) is False
            result["pump"] = pump

    async def async_close(self, entity_id: str) -> str | None:
        """Close a valve that stayed open (button in the panel)."""
        if self.running:
            # stop the run first: it switches the pump off before closing its valve
            await self.async_stop()
        await _switch(self.hass, entity_id, False)
        state = await self._wait_for(entity_id, False)
        if _is_open(state) is False:  # only a valve that reports closed is cleared
            self.stuck.pop(entity_id, None)
            self._open_since.pop(entity_id, None)
            self._reported.discard(entity_id)
        return state

    def solar_ready(self, now: datetime) -> tuple[bool, float | None]:
        """May a scheduled run start now? Waits for solar surplus (settings.solar_irrigation)
        until ``surplus_latest``; without a surplus sensor, or with a sensor that reports nothing
        usable, it never waits.  ``(ready, surplus in W)``."""
        settings = self.coordinator.repo.data.settings
        irr = settings.irrigation
        if not settings.solar_irrigation or not (irr.surplus_entity or irr.battery_entity):
            return True, None
        battery = _float(self._state(irr.battery_entity)) if irr.battery_entity else None
        if battery is not None and battery >= irr.battery_full_pct:
            return True, None  # the home battery is full: the surplus goes to the grid anyway
        if not irr.surplus_entity:
            return self._past_latest(now), None
        state = self.hass.states.get(irr.surplus_entity)
        try:
            watts = float(state.state) if state is not None else None
        except (TypeError, ValueError):
            watts = None
        if watts is None or not math.isfinite(watts):
            return True, None
        unit = str(state.attributes.get("unit_of_measurement", "")).lower() if state is not None else ""
        if unit == "kw":  # some inverters (SolarEdge ...) report kW
            watts *= 1000
        return watts >= irr.surplus_min_w or self._past_latest(now), round(watts)

    def _past_latest(self, now: datetime) -> bool:
        hh, _, mm = self.coordinator.repo.data.settings.irrigation.surplus_latest.partition(":")
        try:
            latest = now.replace(hour=int(hh), minute=int(mm or 0), second=0, microsecond=0)
        except ValueError:
            latest = now.replace(hour=11, minute=0, second=0, microsecond=0)
        return now >= latest

    def _set_waiting(self, value: dict[str, Any] | None) -> None:
        """Change the solar wait and tell the panel and the card at once."""
        if value != self.waiting_for_sun:
            self.waiting_for_sun = value
            self.coordinator.async_update_listeners()

    async def async_start_scheduled(self, now: datetime) -> None:
        """The automatic run at the start time - or, waiting for the sun, as soon as there is surplus."""
        self._scheduled_on = now.date()
        if self.coordinator.repo.data.settings.irrigation.mode != "auto" or self.running:
            self._set_waiting(None)
            return
        ready, watts = self.solar_ready(now)
        if not ready:
            irr = self.coordinator.repo.data.settings.irrigation
            self._set_waiting({"since": now.isoformat(), "watts": watts, "needed": irr.surplus_min_w,
                               "latest": irr.surplus_latest, "battery": self._battery(),
                               "battery_full": irr.battery_full_pct if irr.battery_entity else None})  # fmt: skip
            _LOGGER.debug("Automatic irrigation waits for solar surplus: %s W", watts)
            return
        self._set_waiting(None)
        await self.coordinator.async_recompute()
        plan = self.build_plan()
        if plan.runs:
            self.async_start(plan, source="auto")
        else:
            _LOGGER.debug("Automatic irrigation: nothing to do (%s)", plan.skipped)

    def _missed_solar_wait(self, now: datetime) -> bool:
        """After a restart between the start time and the latest time, today's run that was
        waiting for the sun is picked up again - once, and only when no automatic run went yet."""
        settings = self.coordinator.repo.data.settings
        irr = settings.irrigation
        if (self._scheduled_on == now.date() or irr.mode != "auto" or not settings.solar_irrigation
                or not (irr.surplus_entity or irr.battery_entity) or self.running):  # fmt: skip
            return False
        hhmm = now.strftime("%H:%M")
        if not (irr.start_time.zfill(5) <= hhmm < irr.surplus_latest.zfill(5)):
            return False
        today = now.date()
        return not any(
            e.source == "auto" and dt_util.as_local(e.at).date() == today
            for e in self.coordinator.repo.data.irrigation_log
        )

    @callback
    def async_watch(self, now: datetime | None = None) -> None:
        """Every minute: a valve or pump open long after any run could last is reported."""
        now = now or dt_util.now()
        if self._missed_solar_wait(now):
            self.hass.async_create_task(self.async_start_scheduled(now))
        elif self.waiting_for_sun is not None and not self.running:
            ready, watts = self.solar_ready(now)
            if ready:
                self.hass.async_create_task(self.async_start_scheduled(now))
            elif watts != self.waiting_for_sun.get("watts") or self._battery() != self.waiting_for_sun.get("battery"):
                self._set_waiting({**self.waiting_for_sun, "watts": watts, "battery": self._battery()})
        self._check_soak(now)
        limit = timedelta(minutes=self.coordinator.repo.data.settings.irrigation.max_runtime_min + STUCK_MARGIN_MIN)
        changed = False
        any_open = False
        for entity_id in self.valve_entities():
            is_open = _is_open(self._state(entity_id))
            any_open = any_open or is_open is not False
            if self.running or is_open is None:
                # watering, moving, or not reporting: keep what we know until it settles
                continue
            if is_open is False:
                if entity_id in self.stuck:
                    changed = True
                self._open_since.pop(entity_id, None)
                self.stuck.pop(entity_id, None)
                self._reported.discard(entity_id)
                continue
            since = self._open_since.setdefault(entity_id, now)
            if now - since >= limit and entity_id not in self.stuck:
                self.stuck[entity_id] = since
                changed = True
                self._problem(entity_id, "valve_stuck", self._state(entity_id))
        changed = self._watch_meter(now, any_open) or changed
        if changed:
            self.coordinator.async_update_listeners()

    def _battery(self) -> float | None:
        irr = self.coordinator.repo.data.settings.irrigation
        return _float(self._state(irr.battery_entity)) if irr.battery_entity else None

    def _log(
        self,
        bed_id: str,
        minutes: float,
        run: Any,
        source: str,
        meter_start: float | None = None,
        *,
        water: str | None = "mains",
        kwh: float = 0.0,
    ) -> IrrigationEvent | None:
        data = self.coordinator.repo.data
        bed = data.bed(bed_id)
        if bed is None or minutes <= 0:
            return None
        meter_end = self.meter_liters() if meter_start is not None else None
        measured = meter_end - meter_start if meter_end is not None and meter_start is not None else None
        if measured is not None and measured > 0:
            liters = round(measured, 1)  # what really went through
            self._learn_flow(bed, minutes, measured)
        else:
            liters = round(minutes * (bed.flow_lpm or 0), 1)
        # the water balance is credited with what the bed takes up (learned factor), not what ran off
        mm = round(liters / bed.area_m2 / water_factor(data.settings, bed), 1) if bed.area_m2 else 0.0
        now = dt_util.now()
        event = IrrigationEvent(bed_id, now, mm, liters, round(minutes, 1), source, water or "mains", kwh)  # type: ignore[arg-type]
        data.irrigation_log.append(event)
        book_irrigation(data, now.date(), liters, event.water, kwh)
        trim_irrigation_log(data, now)
        self.hass.bus.async_fire(
            EVENT_IRRIGATION_RUN,
            {
                "bed_id": bed_id,
                "bed": bed.name,
                "minutes": round(minutes, 1),
                "liters": liters,
                "mm": mm,
                "source": source,
                "water": event.water,
                "kwh": kwh,
            },
        )
        return event


class ClimateController:
    """Drives vent and shade entities of enclosed zones in ``auto`` mode.

    Acts only when the wanted state changes (no flapping, no fighting with a
    manual override).  The shade select (``auto`` / ``on`` / ``off``) wins
    over the advice.
    """

    def __init__(self, hass: HomeAssistant, coordinator: GardenCoordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._last: dict[str, bool] = {}
        self._heat_booked: dict[str, datetime] = {}  # zone id -> heater energy booked up to

    @callback
    def async_apply(self, *_: Any) -> None:
        analysis = self.coordinator.data
        if analysis is None:
            return
        for zone in self.coordinator.repo.data.zones:
            if not zone.is_enclosed:
                continue
            za = analysis.zones.get(zone.id)
            if zone.heater_entity:
                self._heater(zone, za.air_temperature if za else None)
            advice = za.greenhouse if za else None
            action = advice.action if advice else GreenhouseAction.NONE
            if zone.shade_entity:
                if zone.shading_mode == "on":
                    wanted: bool | None = True
                elif zone.shading_mode == "off":
                    wanted = False
                elif zone.climate_control == "auto":
                    wanted = action is GreenhouseAction.SHADE
                else:
                    wanted = None
                self._set(f"shade:{zone.id}", zone.shade_entity, wanted, shade=True)
            if zone.vent_entity and zone.climate_control == "auto":
                vent = action in (GreenhouseAction.VENTILATE, GreenhouseAction.SHADE)
                if action in (GreenhouseAction.CLOSE_UP, GreenhouseAction.HEAT):
                    vent = False
                humid = (
                    za is not None
                    and za.humidity is not None
                    and za.humidity >= 90
                    and za.air_temperature is not None
                    and za.air_temperature > 12
                )
                self._set(f"vent:{zone.id}", zone.vent_entity, vent or humid, shade=False)

    def _heater(self, zone: Any, air_c: float | None) -> None:
        """Frost heating: book the energy of the time it was on, then switch it on or off."""
        now = dt_util.now()
        state = self.hass.states.get(zone.heater_entity)
        is_on = _is_open(state.state) if state else None
        if state is not None and zone.heater_entity.startswith("climate.") and state.state not in ("unavailable", "unknown"):
            is_on = state.state != "off"  # a climate entity: heat / auto / ... is on
        since = self._heat_booked.get(zone.id)
        if is_on and since is not None and book_heater(zone, now.date(), (now - since).total_seconds() / 3600):
            self.coordinator.repo.async_schedule_save()
        if is_on:
            self._heat_booked[zone.id] = now
        else:
            self._heat_booked.pop(zone.id, None)
        if not self.coordinator.repo.data.settings.frost_heating or zone.climate_control != "auto":
            return
        wanted = heater_wanted(zone, air_c, bool(is_on), now.date())
        if wanted is not None and wanted != is_on:
            self._last.pop(f"heat:{zone.id}:{zone.heater_entity}", None)  # follow the real state
            self._set(f"heat:{zone.id}", zone.heater_entity, wanted, shade=False)
            if wanted:
                self._heat_booked[zone.id] = now  # its energy counts from now on
            else:
                self._heat_booked.pop(zone.id, None)

    def _set(self, key: str, entity_id: str, wanted: bool | None, *, shade: bool) -> None:
        key = f"{key}:{entity_id}"  # another entity mapped to the zone is switched afresh
        if wanted is None or self._last.get(key) == wanted:
            return
        self._last[key] = wanted
        # A shade *cover* is deployed by closing it; switches are simply on.
        on = (not wanted) if shade and entity_id.startswith("cover.") else wanted
        self.hass.async_create_task(self._safe_switch(key, entity_id, on, wanted))

    async def _safe_switch(self, key: str, entity_id: str, on: bool, wanted: bool) -> None:
        try:
            await _switch(self.hass, entity_id, on)
        except HomeAssistantError as err:
            _LOGGER.warning("Could not switch %s: %s", entity_id, err)
            # not done: forget it, so the next update (every few minutes) tries again
            if self._last.get(key) == wanted:
                self._last.pop(key, None)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
