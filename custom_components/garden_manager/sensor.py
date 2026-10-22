"""Derived sensors: moisture status, irrigation, frost risk, GDD, tasks."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfLength, UnitOfMass, UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GardenConfigEntry
from .coordinator import GardenCoordinator
from .engine import climate
from .engine.adaptive import heater_budget_left, iso_week
from .engine.models import (
    GardenBed,
    GreenhouseAction,
    MoistureStatus,
    RiskLevel,
    Zone,
)
from .engine.records import harvest_summary, water_stats
from .engine.region import resolve_profile
from .engine.serde import to_dict
from .engine.tasks import tasks_due
from .entity import BedEntity, GardenEntity, ZoneEntity, async_setup_dynamic

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: GardenConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            FrostRiskSensor(coordinator),
            GrowingDegreeDaysSensor(coordinator),
            TasksDueTodaySensor(coordinator),
            NextTaskSensor(coordinator),
            Et0TodaySensor(coordinator),
            GddTodaySensor(coordinator),
            HarvestSeasonSensor(coordinator),
            WaterWeekSensor(coordinator),
            RainWaterSensor(coordinator),
            ClimateSensor(coordinator, "rain_7_days"),
            ClimateSensor(coordinator, "mean_temperature_7_days"),
            ClimateSensor(coordinator, "sunshine_7_days"),
            ClimateSensor(coordinator, "frost_nights_season"),
            PumpEnergySensor(coordinator),
            HeaterEnergySensor(coordinator),
        ]
    )
    async_setup_dynamic(
        entry,
        async_add_entities,
        bed_factory=lambda c, bed: [
            MoistureStatusSensor(c, bed),
            IrrigationRecommendationSensor(c, bed),
            CompanionScoreSensor(c, bed),
            NutrientBalanceSensor(c, bed),
            SoilWaterDepletionSensor(c, bed),
        ],
        zone_factory=_zone_sensors,
    )


def _zone_sensors(coordinator: GardenCoordinator, zone: Zone) -> list[SensorEntity]:
    sensors: list[SensorEntity] = [DiseaseRiskSensor(coordinator, zone), ZoneGddSensor(coordinator, zone)]
    if zone.is_enclosed:
        sensors.append(GreenhouseAdviceSensor(coordinator, zone))
    return sensors


# --------------------------------------------------------------------------- #
# Garden-wide
# --------------------------------------------------------------------------- #
class FrostRiskSensor(GardenEntity, SensorEntity):
    """``sensor.hortulus_frost_risk_next_48h``"""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [r.value for r in RiskLevel]
    _attr_icon = "mdi:snowflake-alert"

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "frost_risk_next_48h")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.frost.level.value if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        f = self.coordinator.data.frost
        return {
            "min_temperature": f.min_temp_c,
            "plant_level_min_temperature": f.plant_level_min_c,
            "min_at": f.min_at.isoformat() if f.min_at else None,
            "first_below_zero_at": f.first_below_zero_at.isoformat() if f.first_below_zero_at else None,
            "hours_below_zero": f.hours_below_zero,
            "source": f.source,
            "zones": {zid: z.frost.level.value for zid, z in self.coordinator.data.zones.items()},
        }


class GrowingDegreeDaysSensor(GardenEntity, SensorEntity):
    """Season accumulated growing degree days (base 10 °C by default)."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "°C·d"
    _attr_icon = "mdi:thermometer-plus"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "growing_degree_days")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.gdd.season_total if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        g = self.coordinator.data.gdd
        return {"base_temperature": g.base_c, "since": g.since.isoformat(), "days_counted": g.days_counted}


class TasksDueTodaySensor(GardenEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_native_unit_of_measurement = "tasks"

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "tasks_due_today")

    def _due(self) -> list:
        data = self.coordinator.data
        return tasks_due(self.coordinator.repo.data.tasks, data.today) if data else []

    @property
    def native_value(self) -> int:
        return len(self._due())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        due = self._due()
        return {
            "estimated_minutes": sum(t.estimated_minutes for t in due),
            "overdue": sum(1 for t in due if self.coordinator.data and t.due < self.coordinator.data.today),
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "type": t.type.value,
                    "priority": t.priority.value,
                    "due": t.due.isoformat(),
                }
                for t in due[:25]
            ],
        }


class NextTaskSensor(GardenEntity, SensorEntity):
    _attr_icon = "mdi:shovel"

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "next_task")

    @property
    def native_value(self) -> str | None:
        open_tasks = sorted(
            (t for t in self.coordinator.repo.data.tasks if t.is_open),
            key=lambda t: (t.due, -t.priority.rank),
        )
        return open_tasks[0].title[:255] if open_tasks else None


# --------------------------------------------------------------------------- #
# Per bed
# --------------------------------------------------------------------------- #
class MoistureStatusSensor(BedEntity, SensorEntity):
    """``garden.bed_moisture_status`` -> ``sensor.<bed>_moisture_status``"""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [s.value for s in MoistureStatus]
    _attr_icon = "mdi:water-percent"

    def __init__(self, coordinator: GardenCoordinator, bed: GardenBed) -> None:
        super().__init__(coordinator, bed, "moisture_status")

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return None
        return data.beds[self.bed_id].moisture_status.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return {}
        rec = data.beds[self.bed_id].irrigation
        sensors = data.beds[self.bed_id].sensors
        return {
            "moisture": rec.moisture,
            "target_low": rec.band.target_low if rec.band else None,
            "target_high": rec.band.target_high if rec.band else None,
            "water_need": rec.water_need.value if rec.water_need else None,
            "soil_temperature": sensors.value(sensors.soil_temperature),
            "moisture_entity": sensors.soil_moisture.entity_id if sensors.soil_moisture else None,
        }


class IrrigationRecommendationSensor(BedEntity, SensorEntity):
    """``garden.irrigation_recommendation`` in mm (attributes carry litres/minutes)."""

    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_icon = "mdi:watering-can"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: GardenCoordinator, bed: GardenBed) -> None:
        super().__init__(coordinator, bed, "irrigation_recommendation")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return None
        return data.beds[self.bed_id].irrigation.amount_mm

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return {}
        attrs = data.beds[self.bed_id].irrigation.to_dict()
        bed = self.bed
        attrs["irrigation_entity"] = bed.irrigation_entity if bed else None
        return attrs


class CompanionScoreSensor(BedEntity, SensorEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:handshake-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: GardenCoordinator, bed: GardenBed) -> None:
        super().__init__(coordinator, bed, "companion_score")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return None
        return round(data.beds[self.bed_id].compatibility.score)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return {}
        ba = data.beds[self.bed_id]
        return {
            "conflicts": [p.to_dict() for p in ba.compatibility.conflicts],
            "rotation_conflicts": [r.to_dict() for r in ba.rotation],
        }


# --------------------------------------------------------------------------- #
# Per greenhouse zone
# --------------------------------------------------------------------------- #
class GreenhouseAdviceSensor(ZoneEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [a.value for a in GreenhouseAction]
    _attr_icon = "mdi:greenhouse"

    def __init__(self, coordinator: GardenCoordinator, zone: Zone) -> None:
        super().__init__(coordinator, zone, "greenhouse_advice")

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self.zone_id not in data.zones or data.zones[self.zone_id].greenhouse is None:
            return None
        return data.zones[self.zone_id].greenhouse.action.value  # type: ignore[union-attr]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.zone_id not in data.zones:
            return {}
        za = data.zones[self.zone_id]
        attrs = to_dict(za.greenhouse) if za.greenhouse else {}
        attrs["frost_risk"] = za.frost.level.value
        attrs["air_temperature"] = za.air_temperature
        attrs["temperature_unit"] = UnitOfTemperature.CELSIUS
        return attrs


# --------------------------------------------------------------------------- #
# Agronomy (phase 2)
# --------------------------------------------------------------------------- #
class Et0TodaySensor(GardenEntity, SensorEntity):
    """Reference evapotranspiration for today (FAO-56 PM, Hargreaves fallback)."""

    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:weather-sunny-alert"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "et0_today")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.et0_today if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or not data.outlook:
            return {}
        today = data.outlook[0]
        return {
            "method": data.et0_method,
            "tmin": today.tmin,
            "tmax": today.tmax,
            "rh_min": today.rh_min,
            "rh_max": today.rh_max,
            "wind_kmh": today.wind_kmh,
            "cloud_fraction": today.cloud_fraction,
            "rain_mm": today.rain_mm,
            "forecast": [{"day": o.day.isoformat(), "et0": o.et0_mm, "rain": o.rain_mm} for o in data.outlook],
        }


class HarvestSeasonSensor(GardenEntity, SensorEntity):
    """Kilograms harvested this season (from the harvest log)."""

    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:basket-outline"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "harvest_season")

    def _season(self) -> int:
        data = self.coordinator.data
        return data.season if data else dt_util.now().year

    @property
    def native_value(self) -> float:
        return round(sum(c.kg for c in harvest_summary(self.coordinator.repo.data, self._season()).values()), 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        crops = harvest_summary(self.coordinator.repo.data, self._season())
        return {
            "season": self._season(),
            "per_crop_kg": {k: v.kg for k, v in sorted(crops.items(), key=lambda kv: -kv[1].kg)},
        }


class WaterWeekSensor(GardenEntity, SensorEntity):
    """Mains water used in the garden over the last 7 days (needs a water meter)."""

    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "water_week")

    @property
    def native_value(self) -> float | None:
        return water_stats(self.coordinator.repo.data, dt_util.now().date()).week_l


class RainWaterSensor(GardenEntity, SensorEntity):
    """Rain water left in the butts (level sensor x capacity)."""

    _attr_device_class = SensorDeviceClass.VOLUME_STORAGE
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:barrel-outline"

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "rain_water")

    @property
    def native_value(self) -> float | None:
        return water_stats(self.coordinator.repo.data, dt_util.now().date()).rain_available_l


class PumpEnergySensor(GardenEntity, SensorEntity):
    """Energy the watering pumps used this year (needs the pump power in the settings)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "pump_energy_year")

    @property
    def native_value(self) -> float | None:
        return water_stats(self.coordinator.repo.data, dt_util.now().date()).pump_kwh

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = water_stats(self.coordinator.repo.data, dt_util.now().date())
        return {"rain_water_liters": stats.irrigated_rain_l, "mains_water_liters": stats.irrigated_mains_l}


class HeaterEnergySensor(GardenEntity, SensorEntity):
    """Energy the frost heaters of the enclosures used this (ISO) week."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "heater_energy_week")

    @property
    def native_value(self) -> float:
        week = iso_week(dt_util.now().date())
        return round(sum(z.heater_kwh.get(week, 0.0) for z in self.coordinator.repo.data.zones), 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = dt_util.now().date()
        week = iso_week(today)
        return {
            z.name: {"kwh": z.heater_kwh.get(week, 0.0), "budget_left_kwh": heater_budget_left(z, today)}
            for z in self.coordinator.repo.data.zones
            if z.heater_entity
        }


class ClimateSensor(GardenEntity, SensorEntity):
    """What the weather did lately (from the climate history), compared with a year ago."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    SPECS: dict[str, tuple[str | None, str, str]] = {
        # key: (unit, icon, value in climate.summarize)
        "rain_7_days": (UnitOfLength.MILLIMETERS, "mdi:weather-rainy", "rain_mm"),
        "mean_temperature_7_days": (UnitOfTemperature.CELSIUS, "mdi:thermometer", "tmean"),
        "sunshine_7_days": ("h", "mdi:weather-sunny", "sun_h"),
        "frost_nights_season": (None, "mdi:snowflake-thermometer", "frost_nights"),
    }

    def __init__(self, coordinator: GardenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        unit, self._attr_icon, self._field = self.SPECS[key]
        self._attr_native_unit_of_measurement = unit
        if key == "mean_temperature_7_days":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        if key == "frost_nights_season":
            self._attr_state_class = SensorStateClass.TOTAL
            self._attr_suggested_display_precision = 0

    def _summaries(self) -> tuple[dict[str, Any], dict[str, Any]]:
        data = self.coordinator.repo.data
        region = data.settings.region
        latitude = region.latitude or self.hass.config.latitude
        today = dt_util.now().date()
        year_ago = today - timedelta(days=365)
        if self._key == "frost_nights_season":
            hemisphere = resolve_profile(region).hemisphere
            now = climate.season_so_far(data, today, hemisphere)
            before = climate.season_so_far(data, year_ago, hemisphere)
        else:
            now, before = climate.period(data, today, 7), climate.period(data, year_ago, 7)
        return climate.summarize(now, latitude), climate.summarize(before, latitude)

    @property
    def native_value(self) -> float | None:
        now, _before = self._summaries()
        return now.get(self._field) if now.get("days") else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        now, before = self._summaries()
        return {
            "days_logged": now.get("days", 0),
            "last_year": before.get(self._field),
            "lowest": now.get("tmin"),
            "highest": now.get("tmax"),
            "rain_mm": now.get("rain_mm"),
            "sunshine_h": now.get("sun_h"),
            "gust_max_kmh": now.get("gust_max"),
            "et0_mm": now.get("et0_mm"),
            "water_balance_mm": now.get("balance_mm"),
        }


class GddTodaySensor(GardenEntity, SensorEntity):
    _attr_native_unit_of_measurement = "°C·d"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: GardenCoordinator) -> None:
        super().__init__(coordinator, "gdd_today")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.gdd_today if self.coordinator.data else None


class NutrientBalanceSensor(BedEntity, SensorEntity):
    """0-100 index from NPK / EC probes against the crops' needs."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flask-outline"

    def __init__(self, coordinator: GardenCoordinator, bed: GardenBed) -> None:
        super().__init__(coordinator, bed, "nutrient_balance")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return None
        return data.beds[self.bed_id].nutrients.index

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return {}
        return data.beds[self.bed_id].nutrients.to_dict()


class SoilWaterDepletionSensor(BedEntity, SensorEntity):
    """Root-zone water deficit from the daily water balance (mm below field capacity)."""

    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-minus"
    _attr_suggested_display_precision = 1
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: GardenCoordinator, bed: GardenBed) -> None:
        super().__init__(coordinator, bed, "water_deficit")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return None
        return data.beds[self.bed_id].depletion_mm

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.bed_id not in data.beds:
            return {}
        ba = data.beds[self.bed_id]
        return {"available_water_mm": ba.taw_mm, "crop_coefficient": round(ba.kc, 2)}


class DiseaseRiskSensor(ZoneEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["none", "low", "moderate", "high", "unknown"]
    _attr_icon = "mdi:mushroom-outline"

    def __init__(self, coordinator: GardenCoordinator, zone: Zone) -> None:
        super().__init__(coordinator, zone, "disease_risk")

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self.zone_id not in data.zones:
            return None
        return data.zones[self.zone_id].disease.level

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self.zone_id not in data.zones:
            return {}
        d = data.zones[self.zone_id].disease
        return {
            "wet_hours_48h": d.wet_hours,
            "hutton_period": d.hutton_period,
            "humidity": d.humidity_now,
            "leaf_wet": d.leaf_wet_now,
            "reasons": d.reasons,
        }


class ZoneGddSensor(ZoneEntity, SensorEntity):
    """Season degree days for the zone (greenhouses run warmer)."""

    _attr_native_unit_of_measurement = "°C·d"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:thermometer-plus"
    _attr_suggested_display_precision = 0
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: GardenCoordinator, zone: Zone) -> None:
        super().__init__(coordinator, zone, "gdd_season")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self.zone_id not in data.zones:
            return None
        return data.zones[self.zone_id].gdd_season
