"""Config flow: region -> weather -> beds/zones + sensors -> notifications -> summary."""

from __future__ import annotations

import re
from typing import Any
import uuid

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    AREA_CONTAINER,
    AREA_GREENHOUSE,
    AREA_OUTDOOR,
    BRAND,
    CONF_AIR_TEMP,
    CONF_AREA_NAME,
    CONF_AREA_TYPE,
    CONF_AREAS,
    CONF_DIGEST_TIME,
    CONF_FIRST_FROST,
    CONF_FLOW_LPM,
    CONF_HARDINESS_ZONE,
    CONF_HEMISPHERE,
    CONF_HUMIDITY,
    CONF_IMPORT_EXAMPLE,
    CONF_IRRIGATION,
    CONF_LAST_FROST,
    CONF_LENGTH_M,
    CONF_LIGHT,
    CONF_MOISTURE,
    CONF_NOTIFY_SERVICES,
    CONF_OUTDOOR_TEMP,
    CONF_PERSISTENT,
    CONF_PRESET,
    CONF_RAIN_SENSOR,
    CONF_REGION,
    CONF_REGION_MODE,
    CONF_SHADE,
    CONF_SOIL,
    CONF_SOIL_TEMP,
    CONF_TTS_ENTITY,
    CONF_TTS_PLAYERS,
    CONF_WEATHER_ENTITY,
    CONF_WIDTH_M,
    CONF_WIND,
    DOMAIN,
)
from .engine.models import GardenSettings, SoilType, WindExposure
from .engine.region import PRESETS, USDA_FROST_DATES, resolve_profile
from .gardens import CONF_STORAGE_KEY
from .options import settings_to_options
from .seed import region_from_conf

MMDD = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
USDA_ZONES = [f"{n}{s}" for n in range(1, 14) for s in ("a", "b")]


def _select(
    options: list[str], key: str | None, *, multiple: bool = False, custom: bool = False
) -> selector.SelectSelector:
    config = selector.SelectSelectorConfig(
        options=options,
        mode=selector.SelectSelectorMode.DROPDOWN,
        multiple=multiple,
        custom_value=custom,
    )
    if key:
        config["translation_key"] = key
    return selector.SelectSelector(config)


def _entity(
    domain: str | list[str], device_class: str | list[str] | None = None, multiple: bool = False
) -> selector.EntitySelector:
    config: selector.EntitySelectorConfig = {"domain": domain, "multiple": multiple}
    if device_class:
        config["device_class"] = device_class
    return selector.EntitySelector(config)


def _number(minimum: float, maximum: float, step: float, unit: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum, max=maximum, step=step, unit_of_measurement=unit, mode=selector.NumberSelectorMode.BOX
        )
    )


def region_schema(mode: str, defaults: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(CONF_HEMISPHERE, default=defaults.get(CONF_HEMISPHERE, "north")): _select(
            ["north", "south"], "hemisphere"
        )
    }
    if mode == "preset":
        fields[vol.Required(CONF_PRESET, default=defaults.get(CONF_PRESET) or "nl_be")] = _select(
            sorted(PRESETS), "preset"
        )
    elif mode == "usda":
        fields[vol.Required(CONF_HARDINESS_ZONE, default=defaults.get(CONF_HARDINESS_ZONE) or "8a")] = _select(
            USDA_ZONES, None
        )
    else:
        fields[vol.Required(CONF_LAST_FROST, default=defaults.get(CONF_LAST_FROST) or "04-20")] = str
        fields[vol.Required(CONF_FIRST_FROST, default=defaults.get(CONF_FIRST_FROST) or "10-25")] = str
    return vol.Schema(fields)


def validate_region(mode: str, user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if mode == "custom":
        for key in (CONF_LAST_FROST, CONF_FIRST_FROST):
            if not MMDD.match(str(user_input.get(key, "")).strip()):
                errors[key] = "invalid_frost_date"
    if mode == "usda":
        digits = "".join(c for c in user_input.get(CONF_HARDINESS_ZONE, "") if c.isdigit())
        if digits not in USDA_FROST_DATES:
            errors[CONF_HARDINESS_ZONE] = "invalid_zone"
    return errors


WEATHER_FIELDS = {
    vol.Optional(CONF_WEATHER_ENTITY): _entity("weather"),
    vol.Optional(CONF_OUTDOOR_TEMP): _entity("sensor", "temperature"),
    vol.Optional(CONF_RAIN_SENSOR): _entity(["sensor", "binary_sensor"]),
}


def notification_schema(defaults: dict[str, Any], notify_services: list[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_PERSISTENT, default=defaults.get(CONF_PERSISTENT, True)): bool,
            vol.Optional(CONF_NOTIFY_SERVICES, default=defaults.get(CONF_NOTIFY_SERVICES, [])): _select(
                notify_services, None, multiple=True, custom=True
            ),
            vol.Optional(CONF_TTS_ENTITY, description={"suggested_value": defaults.get(CONF_TTS_ENTITY)}): _entity(
                "tts"
            ),
            vol.Optional(CONF_TTS_PLAYERS, default=defaults.get(CONF_TTS_PLAYERS, [])): _entity(
                "media_player", multiple=True
            ),
            vol.Required(CONF_DIGEST_TIME, default=defaults.get(CONF_DIGEST_TIME, "07:30")): selector.TimeSelector(),
        }
    )


def _nonce() -> dict[str, str]:
    """A value that changes with every save: Home Assistant only applies options that differ
    from the previous ones, and the panel may have changed the store in between."""
    return {"save_id": uuid.uuid4().hex}


class GardenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guided setup."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {CONF_AREAS: []}
        self._region_mode = "preset"
        self._area: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> GardenOptionsFlow:
        return GardenOptionsFlow()

    # -- 1. region ------------------------------------------------------- #
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._region_mode = user_input[CONF_REGION_MODE]
            return await self.async_step_region()
        default_mode = (
            "preset" if (self.hass.config.country or "").upper() in ("NL", "BE", "GB", "DE", "FR") else "usda"
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION_MODE, default=default_mode): _select(
                        ["preset", "usda", "custom"], "region_mode"
                    )
                }
            ),
        )

    async def async_step_region(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_region(self._region_mode, user_input)
            if not errors:
                self._data[CONF_REGION] = {CONF_REGION_MODE: self._region_mode, **user_input}
                return await self.async_step_weather()
        hemisphere = "south" if (self.hass.config.latitude or 0) < 0 else "north"
        return self.async_show_form(
            step_id="region",
            data_schema=region_schema(self._region_mode, {CONF_HEMISPHERE: hemisphere, **(user_input or {})}),
            errors=errors,
        )

    # -- 2. weather ------------------------------------------------------ #
    async def async_step_weather(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_area()
        suggested = "weather.home" if self.hass.states.get("weather.home") else None
        schema = vol.Schema(WEATHER_FIELDS)
        if suggested:
            schema = self.add_suggested_values_to_schema(schema, {CONF_WEATHER_ENTITY: suggested})
        return self.async_show_form(step_id="weather", data_schema=schema)

    # -- 3. beds / zones ------------------------------------------------- #
    async def async_step_area(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            names = {a[CONF_AREA_NAME].casefold() for a in self._data[CONF_AREAS]}
            if user_input[CONF_AREA_NAME].casefold() in names:
                errors[CONF_AREA_NAME] = "duplicate_name"
            elif not (0.1 <= user_input[CONF_WIDTH_M] <= 100 and 0.1 <= user_input[CONF_LENGTH_M] <= 100):
                errors["base"] = "invalid_dimensions"
            else:
                self._area = dict(user_input)
                return await self.async_step_area_sensors()
        index = len(self._data[CONF_AREAS]) + 1
        is_first = index == 1
        defaults = {
            CONF_AREA_NAME: f"Bed {index}" if is_first or index > 2 else "Greenhouse Zone A",
            CONF_AREA_TYPE: AREA_OUTDOOR if is_first else AREA_GREENHOUSE,
            CONF_WIDTH_M: 2.0 if is_first else 3.0,
            CONF_LENGTH_M: 1.0 if is_first else 2.0,
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_AREA_NAME, default=defaults[CONF_AREA_NAME]): str,
                vol.Required(CONF_AREA_TYPE, default=defaults[CONF_AREA_TYPE]): _select(
                    [AREA_OUTDOOR, AREA_GREENHOUSE, AREA_CONTAINER], "area_type"
                ),
                vol.Required(CONF_WIDTH_M, default=defaults[CONF_WIDTH_M]): _number(0.1, 100, 0.1, "m"),
                vol.Required(CONF_LENGTH_M, default=defaults[CONF_LENGTH_M]): _number(0.1, 100, 0.1, "m"),
                vol.Required(CONF_SOIL, default="loam"): _select([s.value for s in SoilType], "soil"),
                vol.Required(CONF_SHADE, default=0): _number(0, 100, 5, "%"),
                vol.Required(CONF_WIND, default="moderate"): _select([w.value for w in WindExposure], "wind"),
            }
        )
        return self.async_show_form(
            step_id="area",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={"count": str(index - 1)},
        )

    async def async_step_area_sensors(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_AREAS].append(
                {**self._area, **{k: v for k, v in user_input.items() if v not in (None, "")}}
            )
            return await self.async_step_area_menu()
        enclosed = self._area.get(CONF_AREA_TYPE) == AREA_GREENHOUSE
        fields: dict[Any, Any] = {
            vol.Optional(CONF_MOISTURE): _entity("sensor", "moisture"),
            vol.Optional(CONF_SOIL_TEMP): _entity("sensor", "temperature"),
        }
        if enclosed:
            fields[vol.Optional(CONF_AIR_TEMP)] = _entity("sensor", "temperature")
            fields[vol.Optional(CONF_HUMIDITY)] = _entity("sensor", "humidity")
            fields[vol.Optional(CONF_LIGHT)] = _entity("sensor", "illuminance")
        fields[vol.Optional(CONF_IRRIGATION)] = _entity([Platform.SWITCH, Platform.VALVE])
        fields[vol.Optional(CONF_FLOW_LPM)] = _number(0.1, 200, 0.1, "L/min")
        return self.async_show_form(
            step_id="area_sensors",
            data_schema=vol.Schema(fields),
            description_placeholders={"name": self._area.get(CONF_AREA_NAME, "")},
        )

    async def async_step_area_menu(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="area_menu",
            menu_options=["area", "notifications"],
            description_placeholders={"areas": ", ".join(a[CONF_AREA_NAME] for a in self._data[CONF_AREAS])},
        )

    # -- 4. notifications ------------------------------------------------ #
    async def async_step_notifications(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data["notifications"] = user_input
            return await self.async_step_summary()
        services = sorted(
            f"notify.{name}"
            for name in self.hass.services.async_services_for_domain("notify")
            if name not in ("send_message", "persistent_notification")
        )
        return self.async_show_form(step_id="notifications", data_schema=notification_schema({}, services))

    # -- 5. summary ------------------------------------------------------ #
    async def async_step_summary(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_IMPORT_EXAMPLE] = user_input[CONF_IMPORT_EXAMPLE]
            others = self._async_current_entries(include_ignore=False)
            if others:
                # a second (third ...) garden: its own storage, a title to tell them apart
                self._data[CONF_STORAGE_KEY] = f"{DOMAIN}.garden_{uuid.uuid4().hex[:8]}"
                taken = {(e.title or "").casefold() for e in others}
                n = 2
                while f"{BRAND} {n}".casefold() in taken:
                    n += 1
                return self.async_create_entry(title=f"{BRAND} {n}", data=self._data)
            return self.async_create_entry(title=BRAND, data=self._data)
        region = resolve_profile(region_from_conf(self._data[CONF_REGION], None, None))
        areas = "\n".join(
            f"- **{a[CONF_AREA_NAME]}** ({a[CONF_AREA_TYPE]}, {a[CONF_WIDTH_M]} x {a[CONF_LENGTH_M]} m"
            + (
                ", " + ", ".join(k for k in (CONF_MOISTURE, CONF_SOIL_TEMP, CONF_AIR_TEMP) if a.get(k))
                if any(a.get(k) for k in (CONF_MOISTURE, CONF_SOIL_TEMP, CONF_AIR_TEMP))
                else ""
            )
            + ")"
            for a in self._data[CONF_AREAS]
        )
        return self.async_show_form(
            step_id="summary",
            data_schema=vol.Schema({vol.Required(CONF_IMPORT_EXAMPLE, default=True): bool}),
            description_placeholders={
                "hemisphere": region.hemisphere.value,
                "last_frost": region.last_frost,
                "first_frost": region.first_frost,
                "weather": self._data.get(CONF_WEATHER_ENTITY) or "-",
                "areas": areas or "-",
            },
        )


class GardenOptionsFlow(OptionsFlow):
    """Change region, weather, notifications and advanced tuning.

    Beds, zones and sensor mappings are edited in the Hortulus panel
    (Settings tab), which offers a visual layout and live validation.
    """

    def __init__(self) -> None:
        self._mode: str | None = None

    def _current(self) -> dict[str, Any]:
        runtime = getattr(self.config_entry, "runtime_data", None)
        settings = runtime.repo.data.settings if runtime is not None else GardenSettings()
        return settings_to_options(settings)

    def _save(self, key: str, value: Any) -> ConfigFlowResult:
        # Only the section just edited: the store (also edited from the panel) is the source
        # of truth, so stale sections from earlier option edits must not be re-applied.
        return self.async_create_entry(data={key: value, **_nonce()})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["region_mode", "weather", "notifications", "advanced"]
        )

    async def async_step_region_mode(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._current()[CONF_REGION]
        if user_input is not None:
            self._mode = user_input[CONF_REGION_MODE]
            return await self.async_step_region()
        return self.async_show_form(
            step_id="region_mode",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION_MODE, default=current["region_mode"]): _select(
                        ["preset", "usda", "custom"], "region_mode"
                    )
                }
            ),
        )

    async def async_step_region(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        mode = self._mode or "preset"
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_region(mode, user_input)
            if not errors:
                return self._save(CONF_REGION, {CONF_REGION_MODE: mode, **user_input})
        return self.async_show_form(
            step_id="region", data_schema=region_schema(mode, user_input or self._current()[CONF_REGION]), errors=errors
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            data: dict[str, Any] = {}
            for key in (CONF_WEATHER_ENTITY, CONF_OUTDOOR_TEMP, CONF_RAIN_SENSOR):
                data[key] = user_input.get(key)
            return self.async_create_entry(data={**data, **_nonce()})
        current = self._current()
        return self.async_show_form(
            step_id="weather",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(WEATHER_FIELDS), current),
        )

    async def async_step_notifications(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._current()["notifications"]
        if user_input is not None:
            return self._save("notifications", {**current, **user_input})
        services = sorted(f"notify.{name}" for name in self.hass.services.async_services_for_domain("notify"))
        schema = notification_schema(current, services).extend(
            {
                vol.Required("frost_alerts", default=current["frost_alerts"]): bool,
                vol.Required("heat_alerts", default=current["heat_alerts"]): bool,
                vol.Required("tts_frost_announcement", default=current["tts_frost_announcement"]): bool,
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._current()["advanced"]
        if user_input is not None:
            return self._save("advanced", user_input)
        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required("language", default=current["language"]): _select(
                        ["auto", "en", "nl", "fr", "de"], "language"
                    ),
                    vol.Required("companion_radius_cm", default=current["companion_radius_cm"]): _number(
                        10, 300, 5, "cm"
                    ),
                    vol.Required("sensor_stale_minutes", default=current["sensor_stale_minutes"]): _number(
                        15, 2880, 15, "min"
                    ),
                    vol.Required("root_zone_depth_mm", default=current["root_zone_depth_mm"]): _number(
                        50, 600, 10, "mm"
                    ),
                    vol.Required("max_irrigation_mm", default=current["max_irrigation_mm"]): _number(2, 60, 1, "mm"),
                }
            ),
        )
