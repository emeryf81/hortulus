"""Learning and choosing at run time (2.1): how much water a bed really takes up, where the water
comes from, and when an enclosure's heater runs.

Pure functions - the controllers read the sensors and switch the hardware; the rules live here so
they are tested without Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from .models import GardenBed, GardenSettings, IrrigationSettings, Zone

# -- How much water soaks in --------------------------------------------------------------- #
FACTOR_MIN = 0.5
FACTOR_MAX = 2.0
LEARN_RATE = 0.3  # each observation moves the factor 30 % of the way
MIN_EXPECTED_RISE = 2.0  # %-points: smaller rises drown in sensor noise
MIN_RUNS = 2  # the factor is used from the second observation on
SOAK_MINUTES = 90  # wait this long after a run before reading the moisture sensor


def expected_rise(mm: float, root_zone_depth_mm: float) -> float:
    """Volumetric moisture rise (%-points) the water balance expects from ``mm`` of water."""
    if root_zone_depth_mm <= 0:
        return 0.0
    return mm / root_zone_depth_mm * 100


def learn_water_factor(bed: GardenBed, expected: float, observed: float) -> bool:
    """Fold one observation into ``bed.water_factor``; False when it was not usable.

    ratio = expected / observed: a bed that rises less than expected (water runs off or drains
    away) needs more water next time.
    """
    if expected < MIN_EXPECTED_RISE:
        return False
    ratio = FACTOR_MAX if observed <= 0.2 else expected / observed
    ratio = max(FACTOR_MIN, min(FACTOR_MAX, ratio))
    old = bed.water_factor if bed.water_factor_runs else 1.0
    bed.water_factor = round(max(FACTOR_MIN, min(FACTOR_MAX, old + LEARN_RATE * (ratio - old))), 2)
    bed.water_factor_runs += 1
    return True


def water_factor(settings: GardenSettings, bed: GardenBed) -> float:
    """The factor applied to planned water, 1.0 until it has been learned (or when switched off)."""
    if not settings.adaptive_irrigation or bed.water_factor_runs < MIN_RUNS:
        return 1.0
    return max(FACTOR_MIN, min(FACTOR_MAX, bed.water_factor or 1.0))


# -- Where the water comes from ------------------------------------------------------------ #
@dataclass(slots=True)
class WaterSource:
    water: Literal["rain", "mains"] | None  # None = wait (butt empty, no fallback)
    pump: str | None
    power_w: float = 0.0


def choose_water(cfg: IrrigationSettings, butt_pct: float | None) -> WaterSource:
    """Rain water while the butt holds enough, then mains (or wait, without fallback).

    ``butt_pct`` None means there is no level sensor (or it reports nothing): the butt pump is used
    and its own dry-run protection is trusted.
    """
    if cfg.butt_pump_entity:
        if butt_pct is None or butt_pct > cfg.butt_min_pct:
            return WaterSource("rain", cfg.butt_pump_entity, cfg.butt_pump_power_w)
        if not cfg.butt_fallback:
            return WaterSource(None, None)
    return WaterSource("mains", cfg.pump_entity, cfg.pump_power_w if cfg.pump_entity else 0.0)


def pump_kwh(minutes: float, power_w: float) -> float:
    return round(max(minutes, 0.0) / 60 * max(power_w, 0.0) / 1000, 3)


# -- Frost heating ------------------------------------------------------------------------- #
HEATER_DEFAULT_C = 3.0
HEATER_HYSTERESIS_C = 1.5
KEEP_WEEKS = 8


def iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def heater_target(zone: Zone) -> float:
    value = zone.microclimate.min_heating_temp_c
    return HEATER_DEFAULT_C if value is None else float(value)


def heater_budget_left(zone: Zone, day: date) -> float | None:
    """kWh left this week, None without a budget."""
    if zone.heater_budget_kwh_week is None:
        return None
    return round(zone.heater_budget_kwh_week - zone.heater_kwh.get(iso_week(day), 0.0), 3)


def heater_wanted(zone: Zone, air_c: float | None, is_on: bool, day: date) -> bool | None:
    """On below the target, off 1.5 °C above it (hysteresis); None = leave it alone (no reading).

    An exhausted weekly budget always means off.
    """
    left = heater_budget_left(zone, day)
    if left is not None and left <= 0:
        return False
    if air_c is None:
        return None
    target = heater_target(zone)
    if air_c < target:
        return True
    if air_c >= target + HEATER_HYSTERESIS_C:
        return False
    return is_on  # in the band: keep what it does


def book_heater(zone: Zone, day: date, hours: float) -> float:
    """Add ``hours`` of heating at the heater's power to this week's energy; returns the kWh added."""
    if hours <= 0 or zone.heater_power_w <= 0:
        return 0.0
    kwh = round(hours * zone.heater_power_w / 1000, 4)
    week = iso_week(day)
    zone.heater_kwh[week] = round(zone.heater_kwh.get(week, 0.0) + kwh, 3)
    for old in sorted(zone.heater_kwh)[:-KEEP_WEEKS]:
        zone.heater_kwh.pop(old, None)
    return kwh
