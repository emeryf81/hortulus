"""Build the first garden document from the config-flow answers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import uuid

from .const import (
    AREA_CONTAINER,
    AREA_GREENHOUSE,
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
)
from .engine.models import (
    BedKind,
    Feature,
    FeatureType,
    GardenBed,
    GardenData,
    Hemisphere,
    LayoutMode,
    Microclimate,
    NotificationSettings,
    Planting,
    RegionProfile,
    SensorMapping,
    SoilType,
    SowMethod,
    WindExposure,
    Zone,
    ZoneType,
)
from .engine.plantdb import PlantDatabase
from .engine.region import season_anchors, season_for_date
from .engine.succession import expand_succession

GAP_CM = 50
MARGIN_CM = 50


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def region_from_conf(conf: dict[str, Any], latitude: float | None, time_zone: str | None) -> RegionProfile:
    return RegionProfile(
        hemisphere=Hemisphere(conf.get(CONF_HEMISPHERE, "north")),
        mode=conf.get(CONF_REGION_MODE, "preset"),
        hardiness_zone=conf.get(CONF_HARDINESS_ZONE),
        preset=conf.get(CONF_PRESET),
        last_frost=conf.get(CONF_LAST_FROST) or "04-20",
        first_frost=conf.get(CONF_FIRST_FROST) or "10-25",
        latitude=latitude,
        time_zone=time_zone,
    )


def notifications_from_conf(conf: dict[str, Any]) -> NotificationSettings:
    return NotificationSettings(
        persistent=conf.get(CONF_PERSISTENT, True),
        notify_services=list(conf.get(CONF_NOTIFY_SERVICES) or []),
        tts_entity=conf.get(CONF_TTS_ENTITY) or None,
        tts_media_players=list(conf.get(CONF_TTS_PLAYERS) or []),
        digest_time=(conf.get(CONF_DIGEST_TIME) or "07:30")[:5],
    )


def build_initial_data(
    entry_data: dict[str, Any],
    *,
    latitude: float | None,
    time_zone: str | None,
    language: str,
    today: date,
    db: PlantDatabase | None = None,
) -> GardenData:
    data = GardenData()
    settings = data.settings
    settings.region = region_from_conf(entry_data.get(CONF_REGION, {}), latitude, time_zone)
    settings.weather_entity = entry_data.get(CONF_WEATHER_ENTITY)
    settings.outdoor_sensors = SensorMapping(
        air_temperature=entry_data.get(CONF_OUTDOOR_TEMP) or None,
        rain=entry_data.get(CONF_RAIN_SENSOR) or None,
    )
    settings.notifications = notifications_from_conf(entry_data.get("notifications", {}))

    areas: list[dict[str, Any]] = list(entry_data.get(CONF_AREAS, []))
    outdoor_areas = [a for a in areas if a.get(CONF_AREA_TYPE) != AREA_GREENHOUSE]
    greenhouse_areas = [a for a in areas if a.get(CONF_AREA_TYPE) == AREA_GREENHOUSE]

    cursor_x = 0.0
    if outdoor_areas or not areas:
        outdoor = Zone(id="zone_outdoor", name="Tuin" if language == "nl" else "Garden", type=ZoneType.OUTDOOR)
        data.zones.append(outdoor)
        x = MARGIN_CM
        tallest = 0.0
        for area in outdoor_areas:
            width = float(area.get(CONF_WIDTH_M, 2)) * 100
            length = float(area.get(CONF_LENGTH_M, 1)) * 100
            data.beds.append(
                GardenBed(
                    id=_id("bed"),
                    name=area[CONF_AREA_NAME],
                    zone_id=outdoor.id,
                    kind=BedKind.CONTAINER if area.get(CONF_AREA_TYPE) == AREA_CONTAINER else BedKind.RAISED,
                    x_cm=x,
                    y_cm=MARGIN_CM,
                    width_cm=width,
                    length_cm=length,
                    soil=SoilType(
                        area.get(CONF_SOIL, "potting_mix" if area.get(CONF_AREA_TYPE) == AREA_CONTAINER else "loam")
                    ),
                    shade_pct=int(area.get(CONF_SHADE, 0)) or None,
                    sensors=_sensors(area),
                    irrigation_entity=area.get(CONF_IRRIGATION) or None,
                    irrigation_flow_lpm=area.get(CONF_FLOW_LPM) or None,
                )
            )
            outdoor.microclimate.wind = WindExposure(area.get(CONF_WIND, outdoor.microclimate.wind.value))
            x += width + GAP_CM
            tallest = max(tallest, length)
        outdoor.width_cm = max(400.0, x - GAP_CM + MARGIN_CM)
        outdoor.length_cm = max(300.0, tallest + 2 * MARGIN_CM)
        cursor_x = outdoor.width_cm + 100

    for area in greenhouse_areas:
        width = float(area.get(CONF_WIDTH_M, 3)) * 100
        length = float(area.get(CONF_LENGTH_M, 2)) * 100
        zone = Zone(
            id=_id("zone"),
            name=area[CONF_AREA_NAME],
            type=ZoneType.GREENHOUSE,
            x_cm=cursor_x,
            y_cm=0,
            width_cm=width,
            length_cm=length,
            microclimate=Microclimate(shade_pct=int(area.get(CONF_SHADE, 0))),
            sensors=SensorMapping(
                air_temperature=area.get(CONF_AIR_TEMP) or None,
                air_humidity=area.get(CONF_HUMIDITY) or None,
                light=area.get(CONF_LIGHT) or None,
            ),
        )
        data.zones.append(zone)
        # A border along the long side with a 60 cm path, the typical layout.
        path = 60 if length >= 180 else 0
        # Inset scales down for tiny greenhouses so the bed never gets a size <= 0.
        inset = min(20.0, width * 0.1, length * 0.1)
        data.beds.append(
            GardenBed(
                id=_id("bed"),
                # Distinct from the zone name so devices/entities are unambiguous.
                name=f"{area[CONF_AREA_NAME]} bed",
                zone_id=zone.id,
                kind=BedKind.IN_GROUND,
                x_cm=cursor_x + inset,
                y_cm=inset,
                width_cm=max(width - 2 * inset, 10.0),
                length_cm=max(length - 2 * inset - path, 10.0),
                soil=SoilType(area.get(CONF_SOIL, "loam")),
                sensors=SensorMapping(
                    soil_moisture=area.get(CONF_MOISTURE) or None,
                    soil_temperature=area.get(CONF_SOIL_TEMP) or None,
                ),
                irrigation_entity=area.get(CONF_IRRIGATION) or None,
                irrigation_flow_lpm=area.get(CONF_FLOW_LPM) or None,
            )
        )
        cursor_x += width + 100

    if entry_data.get(CONF_IMPORT_EXAMPLE) and db is not None:
        add_example_plan(data, db, today)
    return data


def _sensors(area: dict[str, Any]) -> SensorMapping:
    return SensorMapping(
        soil_moisture=area.get(CONF_MOISTURE) or None,
        soil_temperature=area.get(CONF_SOIL_TEMP) or None,
        air_temperature=area.get(CONF_AIR_TEMP) or None,
        air_humidity=area.get(CONF_HUMIDITY) or None,
        light=area.get(CONF_LIGHT) or None,
    )


def add_example_plan(data: GardenData, db: PlantDatabase, today: date) -> None:
    """A small, companion-friendly starter plan for the upcoming season."""
    region = data.settings.region
    season = season_for_date(region, today)
    anchors = season_anchors(region, season)
    if today > anchors.last_frost + timedelta(days=30):
        season += 1
        anchors = season_anchors(region, season)

    def planting(
        plant_id: str, bed: GardenBed, x: float, y: float, w: float, h: float, layout: LayoutMode, method: SowMethod
    ) -> Planting:
        return Planting(
            id=_id("pl"),
            plant_id=plant_id,
            bed_id=bed.id,
            season=season,
            layout=layout,
            x_cm=round(min(x, bed.width_cm - w), 1),
            y_cm=round(min(y, bed.length_cm - h), 1),
            width_cm=min(w, bed.width_cm),
            length_cm=min(h, bed.length_cm),
            method=method,
        )

    for bed in data.beds:
        zone = data.zone(bed.zone_id)
        if zone and zone.type is ZoneType.GREENHOUSE and bed.width_cm >= 120:
            data.plantings += [
                planting("tomato", bed, 0, 0, min(200, bed.width_cm - 50), 50, LayoutMode.ROW, SowMethod.INDOOR_SOW),
                planting("basil", bed, 0, 60, 50, 50, LayoutMode.BLOCK, SowMethod.INDOOR_SOW),
                planting("marigold", bed, 60, 60, 50, 50, LayoutMode.BLOCK, SowMethod.INDOOR_SOW),
            ]
        elif zone and zone.type is ZoneType.OUTDOOR and bed.kind is not BedKind.CONTAINER and bed.width_cm >= 150:
            data.plantings += [
                planting("carrot", bed, 0, 0, bed.width_cm, 25, LayoutMode.ROW, SowMethod.DIRECT_SOW),
                planting("onion", bed, 0, 30, bed.width_cm, 25, LayoutMode.ROW, SowMethod.TRANSPLANT),
            ]
            if bed.length_cm >= 90 and (lettuce := db.get("lettuce")) is not None:
                base = planting(
                    "lettuce", bed, 0, 60, min(bed.width_cm, 150), 30, LayoutMode.BLOCK, SowMethod.DIRECT_SOW
                )
                series, _ = expand_succession(base, lettuce, anchors, zone, count=3)
                data.plantings += series


STARTER_SIZES: dict[str, tuple[int, float, float]] = {
    # size -> (raised beds, long side m, short side m); the rows run along the long side
    "small": (2, 2.4, 1.2),
    "medium": (3, 3.0, 1.2),
    "large": (4, 3.6, 1.2),
}


def starter_garden(
    size: str, *, greenhouse: bool, language: str, today: date, db: PlantDatabase, base: GardenData
) -> GardenData:
    """A ready-made beginner's garden: raised beds, a herb pot, optionally a greenhouse, and a first plan.

    Built in a fresh document with the settings (region, weather ...) of ``base``;
    the caller copies the zones, beds, features and plantings over.
    """
    beds, width, length = STARTER_SIZES.get(size, STARTER_SIZES["medium"])
    names = {
        "nl": ("Bak", "Kruidenpot", "Serre"),
        "fr": ("Carré", "Pot d'aromates", "Serre"),
        "de": ("Beet", "Kräutertopf", "Gewächshaus"),
    }.get(language, ("Bed", "Herb pot", "Greenhouse"))
    areas: list[dict[str, Any]] = [
        {CONF_AREA_NAME: f"{names[0]} {i + 1}", CONF_AREA_TYPE: "outdoor", CONF_WIDTH_M: width, CONF_LENGTH_M: length}
        for i in range(beds)
    ]
    areas.append({CONF_AREA_NAME: names[1], CONF_AREA_TYPE: AREA_CONTAINER, CONF_WIDTH_M: 0.6, CONF_LENGTH_M: 0.6})
    if greenhouse:
        areas.append({CONF_AREA_NAME: names[2], CONF_AREA_TYPE: AREA_GREENHOUSE, CONF_WIDTH_M: 3.0, CONF_LENGTH_M: 2.0})
    data = build_initial_data(
        {CONF_AREAS: areas, CONF_IMPORT_EXAMPLE: True},
        latitude=None,
        time_zone=None,
        language=language,
        today=today,
        db=db,
    )
    data.settings = base.settings  # keep the gardener's region, weather and notifications
    data.plantings.clear()
    add_example_plan(data, db, today)
    outdoor = next((z for z in data.zones if z.type is ZoneType.OUTDOOR), None)
    if outdoor is not None:
        labels = {
            "nl": ("Pad", "Regenton", "Compost"),
            "fr": ("Allée", "Récupérateur d'eau", "Compost"),
            "de": ("Weg", "Regentonne", "Kompost"),
        }.get(language, ("Path", "Water butt", "Compost"))
        data.features = [
            Feature(
                _id("ft"),
                labels[0],
                FeatureType.PATH,
                x_cm=0,
                y_cm=outdoor.length_cm,
                width_cm=outdoor.width_cm,
                length_cm=60,
            ),
            Feature(_id("ft"), labels[1], FeatureType.WATER_BUTT, x_cm=-80, y_cm=0, width_cm=60, length_cm=60),
            Feature(_id("ft"), labels[2], FeatureType.COMPOST, x_cm=-120, y_cm=100, width_cm=100, length_cm=100),
        ]
    return data
