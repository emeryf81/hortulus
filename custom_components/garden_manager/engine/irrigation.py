"""Irrigation plan: which valves to open, for how long - and when not to.

The plan is pure; ``irrigation_controller.py`` executes it against Home
Assistant.  Safety rules (all of them also apply to a manual run):

* **Frost lockout** - outdoor valves stay shut when the plant-level minimum in
  the next 12 hours, or the current outdoor temperature, is at or below
  ``frost_lockout_c``: water in a drip line or on leaves freezes.  Enclosed
  zones are only locked when their own air temperature is that low.
* **Rain skip** - outdoor beds are skipped when at least ``rain_skip_mm`` of
  rain is forecast for the next 24 hours.
* **Max runtime** - no valve runs longer than ``max_runtime_min``.
* **One valve at a time** - runs are sequential so the pump keeps pressure;
  the controller adds a pump interlock (pump on before / off after valves).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .adaptive import water_factor
from .models import GardenData, IrrigationAction
from .watering import IrrigationRecommendation
from .weather import NEAR_HOURS, FrostAssessment

LOCKOUT_WINDOW_H = NEAR_HOURS  # hours ahead a forecast frost locks the valves


@dataclass(slots=True)
class IrrigationRun:
    bed_id: str
    entity_id: str
    minutes: float
    mm: float
    liters: float
    capped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "bed_id": self.bed_id,
            "entity_id": self.entity_id,
            "minutes": self.minutes,
            "mm": self.mm,
            "liters": self.liters,
            "capped": self.capped,
        }


@dataclass(slots=True)
class IrrigationPlan:
    runs: list[IrrigationRun] = field(default_factory=list)
    # bed id -> (i18n key, params)
    skipped: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)
    lockout: bool = False  # outdoor frost lockout active
    lockout_temp: float | None = None

    @property
    def total_minutes(self) -> float:
        return round(sum(r.minutes for r in self.runs), 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [r.to_dict() for r in self.runs],
            "skipped": {k: {"key": key, "params": params} for k, (key, params) in self.skipped.items()},
            "lockout": self.lockout,
            "lockout_temp": self.lockout_temp,
            "total_minutes": self.total_minutes,
        }


def frost_lockout(
    frost: FrostAssessment | None, outdoor_temp: float | None, limit: float, now: datetime
) -> tuple[bool, float | None]:
    """(locked, temperature that triggered it)."""
    if outdoor_temp is not None and outdoor_temp <= limit:
        return True, outdoor_temp
    if frost is not None and frost.near_min_c is not None and frost.near_min_c <= limit:
        return True, frost.near_min_c  # freezing within the lockout window (a colder night later does not hide it)
    if frost is None or frost.plant_level_min_c is None or frost.plant_level_min_c > limit:
        return False, None
    if frost.min_at is None or frost.min_at <= now + timedelta(hours=LOCKOUT_WINDOW_H):
        return True, frost.plant_level_min_c
    return False, None


def plan_irrigation(
    data: GardenData,
    recommendations: Mapping[str, IrrigationRecommendation],
    *,
    now: datetime,
    frost_by_zone: Mapping[str, FrostAssessment],
    outdoor_frost: FrostAssessment | None,
    outdoor_temp: float | None,
    zone_air: Mapping[str, float | None] | None = None,
    force: bool = False,
    bed_ids: set[str] | None = None,
    override_mm: float | None = None,
    only_if_needed: bool = False,
) -> IrrigationPlan:
    """Build today's run list.

    ``force`` (a manual run) ignores the mode switch and the "no water needed"
    check - never the safety rules.  ``only_if_needed`` keeps that check for a
    forced run (an automation that picks the moment, not the amount).
    ``override_mm`` waters a fixed depth.
    """
    cfg = data.settings.irrigation
    plan = IrrigationPlan()
    locked, lock_temp = frost_lockout(outdoor_frost, outdoor_temp, cfg.frost_lockout_c, now)
    plan.lockout, plan.lockout_temp = locked, lock_temp
    zone_air = zone_air or {}

    for bed in data.beds:
        if bed_ids is not None and bed.id not in bed_ids:
            continue
        rec = recommendations.get(bed.id)
        zone = data.zone(bed.zone_id)
        enclosed = bool(zone and zone.is_enclosed)
        if cfg.mode != "auto" and not force:
            plan.skipped[bed.id] = ("irrigation.skip.disabled", {})
            continue
        if not bed.irrigation_entity:
            plan.skipped[bed.id] = ("irrigation.skip.no_valve", {})
            continue
        flow = bed.flow_lpm
        if flow is None:
            plan.skipped[bed.id] = ("irrigation.skip.no_flow", {})
            continue
        # -- safety ------------------------------------------------------- #
        if enclosed:
            air = zone_air.get(bed.zone_id)
            if air is not None and air <= cfg.frost_lockout_c:
                plan.skipped[bed.id] = ("irrigation.skip.frost", {"temp": air, "limit": cfg.frost_lockout_c})
                continue
        else:
            z_locked, z_temp = frost_lockout(frost_by_zone.get(bed.zone_id), outdoor_temp, cfg.frost_lockout_c, now)
            if locked or z_locked:
                temp = z_temp if z_locked else lock_temp
                plan.skipped[bed.id] = ("irrigation.skip.frost", {"temp": temp, "limit": cfg.frost_lockout_c})
                continue
            rain = rec.rain_24h_mm if rec else 0.0
            if rain >= cfg.rain_skip_mm:
                plan.skipped[bed.id] = ("irrigation.skip.rain", {"mm": rain, "limit": cfg.rain_skip_mm})
                continue
        # -- amount ------------------------------------------------------- #
        if override_mm is not None:
            mm = override_mm
        elif rec is not None and rec.action is IrrigationAction.WATER and rec.amount_mm > 0:
            mm = rec.amount_mm
        elif force and not only_if_needed and rec is not None and rec.etc_24h_mm:
            mm = rec.etc_24h_mm  # manual run without need: replace one day of ET
        else:
            plan.skipped[bed.id] = ("irrigation.skip.not_needed", {})
            continue
        if override_mm is None:
            mm *= water_factor(data.settings, bed)  # what this bed really takes up (learned)
        liters = round(mm * bed.area_m2, 1)
        minutes = liters / flow
        capped = minutes > cfg.max_runtime_min
        minutes = round(min(minutes, cfg.max_runtime_min), 1)
        if capped:
            liters = round(minutes * flow, 1)
            mm = round(liters / bed.area_m2, 1) if bed.area_m2 else mm
        plan.runs.append(IrrigationRun(bed.id, bed.irrigation_entity, minutes, round(mm, 1), liters, capped))
    return plan
