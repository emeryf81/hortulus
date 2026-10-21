"""Hortulus domain model.

Everything in :mod:`custom_components.garden_manager.engine` is *pure Python*:
no Home Assistant imports, no I/O.  That keeps the horticultural logic fast to
unit-test and lets the same rules run inside the coordinator, the services and
the websocket API.

Conventions
-----------
* Lengths are centimetres, temperatures degrees Celsius, rain millimetres.
* Canvas coordinates: origin top-left, x to the east, y to the south (cm).
* Planting coordinates are *relative to their bed*.
* Calendar dates are local (``date``), timestamps are tz-aware (``datetime``).
* A *season* is identified by the year in which its spring (last frost) falls,
  so on the southern hemisphere season 2026 runs from July 2026 to June 2027.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Hemisphere(StrEnum):
    NORTH = "north"
    SOUTH = "south"


class ZoneType(StrEnum):
    OUTDOOR = "outdoor"  # vegetable garden (moestuin)
    GREENHOUSE = "greenhouse"
    COLD_FRAME = "cold_frame"
    ORCHARD = "orchard"  # fruit trees
    FRUIT = "fruit"  # soft fruit: berries, currants, canes, grapes
    HERBS = "herbs"  # herb garden
    FLOWERS = "flowers"  # flower / pollinator border
    GARDEN = "garden"  # ornamental garden: shrubs, borders, lawn edges
    CONTAINERS = "containers"  # planters, pots, balcony and terrace boxes
    FOOD_FOREST = "food_forest"  # forest garden: trees, shrubs, herbs, ground cover and climbers in layers


# What each zone type is meant to hold (used by the planner palette and autofill).
ZONE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "outdoor": ("vegetable", "herb", "flower"),
    "greenhouse": ("vegetable", "herb", "fruit"),
    "cold_frame": ("vegetable", "herb"),
    "orchard": ("fruit",),
    "fruit": ("fruit",),
    "herbs": ("herb", "flower"),
    "flowers": ("flower", "herb"),
    "garden": ("flower", "herb", "fruit"),
    "containers": ("vegetable", "herb", "flower", "fruit"),
    "food_forest": ("fruit", "herb", "flower", "vegetable"),
}


class BedKind(StrEnum):
    IN_GROUND = "in_ground"
    RAISED = "raised"
    CONTAINER = "container"


class SoilType(StrEnum):
    SANDY = "sandy"
    LOAM = "loam"
    CLAY = "clay"
    SILT = "silt"
    PEAT = "peat"
    CHALK = "chalk"
    POTTING_MIX = "potting_mix"


class WindExposure(StrEnum):
    SHELTERED = "sheltered"
    MODERATE = "moderate"
    EXPOSED = "exposed"


class GrowthHabit(StrEnum):
    BUSH = "bush"
    VINE = "vine"
    CLIMBING = "climbing"
    UPRIGHT = "upright"
    ROSETTE = "rosette"
    ROOT = "root"
    BULB = "bulb"


class Suitability(StrEnum):
    YES = "yes"
    NO = "no"
    CONDITIONAL = "conditional"


class FrostTolerance(StrEnum):
    TENDER = "tender"  # damaged at/just above 0 °C
    HALF_HARDY = "half_hardy"  # light frost OK (to about -2 °C)
    HARDY = "hardy"  # to about -7 °C
    VERY_HARDY = "very_hardy"  # below -10 °C


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Relation(StrEnum):
    FRIEND = "friend"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class SowMethod(StrEnum):
    INDOOR_SOW = "indoor_sow"  # sow in trays, transplant later
    DIRECT_SOW = "direct_sow"  # sow in place
    TRANSPLANT = "transplant"  # bought seedling / sets / cloves


class PlantingStatus(StrEnum):
    PLANNED = "planned"
    SOWN_INDOORS = "sown_indoors"
    SOWN = "sown"
    TRANSPLANTED = "transplanted"
    HARVESTING = "harvesting"
    FINISHED = "finished"
    FAILED = "failed"


class LayoutMode(StrEnum):
    SINGLE = "single"
    BLOCK = "block"
    ROW = "row"


class TaskType(StrEnum):
    SOW_INDOOR = "sow_indoor"
    SOW_DIRECT = "sow_direct"
    HARDEN_OFF = "harden_off"
    TRANSPLANT = "transplant"
    THIN = "thin"
    STAKE = "stake"
    PRUNE = "prune"
    PINCH = "pinch"
    EARTH_UP = "earth_up"
    FEED = "feed"
    WATER = "water"
    WEED = "weed"
    PEST_CHECK = "pest_check"
    HARVEST = "harvest"
    VENTILATE = "ventilate"
    SHADE = "shade"
    FROST_PROTECT = "frost_protect"
    # Seasonal garden work (not tied to a single crop)
    SOIL_PREP = "soil_prep"
    COMPOST = "compost"
    GREEN_MANURE = "green_manure"
    MULCH = "mulch"
    CLEAN_GREENHOUSE = "clean_greenhouse"
    WINTER_PREP = "winter_prep"
    PLAN_SEASON = "plan_season"
    TOOL_CARE = "tool_care"
    SOIL_TEST = "soil_test"
    CUT_BACK = "cut_back"
    DIVIDE = "divide"
    PROTECT = "protect"  # fleece, mesh, nets, shade cloth, storm fixing
    CLEAN = "clean"  # windows, pots, trays, water butts, gutters
    TIE_IN = "tie_in"  # climbers, canes, espaliers
    THIN_FRUIT = "thin_fruit"
    POLLINATE = "pollinate"
    CHECK = "check"  # inspections: stores, vents, irrigation, stakes
    MAKE_FEED = "make_feed"  # nettle / comfrey tea, compost tea, bokashi
    CUSTOM = "custom"


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    SKIPPED = "skipped"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def rank(self) -> int:
        return _PRIORITY_RANK[self]


_PRIORITY_RANK = {
    TaskPriority.LOW: 0,
    TaskPriority.NORMAL: 1,
    TaskPriority.HIGH: 2,
    TaskPriority.URGENT: 3,
}


class TaskSource(StrEnum):
    GENERATED = "generated"  # derived from the plan + plant database
    SENSOR = "sensor"  # derived from live sensor readings
    WEATHER = "weather"  # derived from the forecast
    USER = "user"  # created by a person or an automation


class RiskLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class MoistureStatus(StrEnum):
    DRY = "dry"
    SLIGHTLY_DRY = "slightly_dry"
    OPTIMAL = "optimal"
    WET = "wet"
    UNKNOWN = "unknown"


class IrrigationAction(StrEnum):
    NONE = "none"
    WATER = "water"
    SKIP_RAIN_EXPECTED = "skip_rain_expected"
    CHECK_MANUALLY = "check_manually"


class DiseaseRisk(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class PlantCategory(StrEnum):
    VEGETABLE = "vegetable"
    HERB = "herb"
    FLOWER = "flower"
    FRUIT = "fruit"


class FeatureType(StrEnum):
    PATH = "path"
    COMPOST = "compost"
    WATER_BUTT = "water_butt"
    SHED = "shed"
    TREE = "tree"
    HEDGE = "hedge"
    TRELLIS = "trellis"
    TERRACE = "terrace"
    LAWN = "lawn"
    FLOWERBED = "flowerbed"
    FENCE = "fence"
    POND = "pond"
    HOUSE = "house"
    DRIVEWAY = "driveway"
    STREET = "street"
    PARKING = "parking"
    PLAY = "play"
    BEEHIVE = "beehive"
    STONE_PATH = "stone_path"
    WOOD_PATH = "wood_path"
    STEPPING_STONES = "stepping_stones"
    BARK_PATH = "bark_path"
    DECKING = "decking"
    WALL = "wall"
    CARPORT = "carport"
    SHRUB = "shrub"
    POOL = "pool"
    SEATING = "seating"
    OTHER = "other"


class GreenhouseAction(StrEnum):
    NONE = "none"
    VENTILATE = "ventilate"
    SHADE = "shade"
    CLOSE_UP = "close_up"
    HEAT = "heat"


WindowAnchor = Literal["last_frost", "first_frost"]
# "last_frost"/"first_frost" anchor yearly care of established perennials
# (prune in winter, net before ripening ...) to the season, not the planting.
CareAnchor = Literal["planting", "sow", "transplant", "harvest_start", "last_frost", "first_frost"]


# --------------------------------------------------------------------------- #
# Plant database
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class Window:
    """A sowing/planting window in *weeks* relative to a frost anchor.

    ``start_week=-8, end_week=-6, anchor="last_frost"`` means "between 8 and 6
    weeks before the average last spring frost".  Anchoring on frost dates makes
    the database hemisphere- and climate-independent.
    """

    start_week: int
    end_week: int
    anchor: WindowAnchor = "last_frost"


@dataclass(slots=True)
class SowingCalendar:
    indoor_sow: list[Window] = field(default_factory=list)
    direct_sow: list[Window] = field(default_factory=list)
    transplant: list[Window] = field(default_factory=list)


@dataclass(slots=True)
class GreenhouseProfile:
    suitability: Suitability = Suitability.NO
    min_night_c: float = 5.0
    max_day_c: float = 30.0
    # How many weeks earlier sowing/transplanting may start under glass.
    season_extension_weeks: int = 0
    notes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class CompanionLink:
    plant: str
    relation: Relation
    reason: dict[str, str] = field(default_factory=dict)
    strength: int = 2  # 1 = folklore / weak … 3 = well documented


@dataclass(slots=True)
class CareRule:
    """Data-driven care task, e.g. "prune side shoots weekly from day 14"."""

    task: TaskType
    start_day: int = 0
    interval_days: int | None = None
    end_day: int | None = None
    anchor: CareAnchor = "planting"
    minutes: int = 10
    notes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Plant:
    id: str
    names: dict[str, str]
    scientific_name: str
    family: str
    variety: str | None = None
    habit: GrowthHabit = GrowthHabit.BUSH
    perennial: bool = False
    spacing_cm: float = 30.0
    row_spacing_cm: float = 30.0
    sowing_depth_cm: float = 1.0
    germination_days: list[int] = field(default_factory=lambda: [7, 14])
    min_soil_temp_c: float = 7.0
    optimal_soil_temp_c: float = 18.0
    max_soil_temp_c: float | None = None
    days_to_maturity: list[int] = field(default_factory=lambda: [60, 80])
    maturity_from: Literal["sow", "transplant"] = "sow"
    harvest_duration_days: int = 14
    # False for companion flowers / green manures: no harvest tasks.
    harvestable: bool = True
    continuous_harvest: bool = False
    harvest_interval_days: int | None = None
    transplant_age_days: list[int] = field(default_factory=lambda: [35, 49])
    sowing: SowingCalendar = field(default_factory=SowingCalendar)
    greenhouse: GreenhouseProfile = field(default_factory=GreenhouseProfile)
    frost_tolerance: FrostTolerance = FrostTolerance.HALF_HARDY
    min_temp_c: float = 0.0
    max_temp_c: float = 32.0
    companions: list[CompanionLink] = field(default_factory=list)
    rotation_years: int = 3
    pests: list[str] = field(default_factory=list)
    diseases: list[str] = field(default_factory=list)
    water_needs: Level = Level.MEDIUM
    nutrient_needs: Level = Level.MEDIUM
    feeding_interval_days: int | None = None
    care: list[CareRule] = field(default_factory=list)
    pruning_notes: dict[str, str] = field(default_factory=dict)
    thinning: bool = False
    succession_interval_days: int | None = None
    gdd_base_c: float = 10.0
    gdd_to_maturity: int | None = None
    tags: list[str] = field(default_factory=list)
    category: PlantCategory = PlantCategory.VEGETABLE
    # FAO-56 crop coefficients: initial, mid-season, late season.
    kc: list[float] = field(default_factory=lambda: [0.5, 1.0, 0.8])
    # Relative nitrogen / phosphorus / potassium demand (0 = none ... 3 = high).
    npk: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    height_cm: int = 50
    root_depth_cm: int = 30
    plants_per_person: float = 2.0
    yield_kg_m2: float = 2.0
    # Pests this plant deters (scent, root exudates) or lures away (trap crop).
    deters: list[str] = field(default_factory=list)
    trap_for: list[str] = field(default_factory=list)
    allelopathic: bool = False
    shade_tolerant: bool = False
    # Perennials: harvest each year in these windows once bearing.
    harvest_windows: list[Window] = field(default_factory=list)
    years_to_bearing: int = 0
    emoji: str = ""
    icon: str = ""  # vector glyph drawn on the planner map (see frontend plant-glyphs)
    color: str = ""  # glyph colour (the crop's own colour, not the family colour)
    # Short ecological growing tips and home remedies (per language).
    tips: dict[str, list[str]] = field(default_factory=dict)
    pollination: Literal["self", "insects", "wind", "partner", "none"] = "self"
    source: Literal["builtin", "custom", "override"] = "builtin"

    def name(self, lang: str = "en") -> str:
        return self.names.get(lang) or self.names.get("en") or self.id


# --------------------------------------------------------------------------- #
# Garden layout
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class SensorMapping:
    """Entity ids feeding a bed or zone.  ``None`` means "not available"."""

    soil_moisture: str | None = None
    soil_temperature: str | None = None
    air_temperature: str | None = None
    air_humidity: str | None = None
    light: str | None = None
    rain: str | None = None
    # Advanced probes (all optional)
    par: str | None = None  # PAR/PPFD in µmol/m²/s
    ec: str | None = None  # electrical conductivity in mS/cm
    npk_n: str | None = None  # mg/kg
    npk_p: str | None = None
    npk_k: str | None = None
    leaf_wetness: str | None = None  # binary or %
    # Outdoor weather station (optional): wind, gusts and global radiation
    wind_speed: str | None = None  # km/h, m/s, mph or kn
    wind_gust: str | None = None
    radiation: str | None = None  # W/m² (solar / global radiation)

    def merged_with(self, fallback: SensorMapping) -> SensorMapping:
        """Bed sensors fall back to the sensors of their zone."""
        return SensorMapping(**{k: getattr(self, k) or getattr(fallback, k) for k in SENSOR_KEYS})

    def entity_ids(self) -> list[str]:
        return [e for e in (getattr(self, k) for k in SENSOR_KEYS) if e]


SENSOR_KEYS = (
    "soil_moisture",
    "soil_temperature",
    "air_temperature",
    "air_humidity",
    "light",
    "rain",
    "par",
    "ec",
    "npk_n",
    "npk_p",
    "npk_k",
    "leaf_wetness",
    "wind_speed",
    "wind_gust",
    "radiation",
)


@dataclass(slots=True)
class Microclimate:
    shade_pct: int = 0
    wind: WindExposure = WindExposure.MODERATE
    heated: bool = False
    # Against a sun-facing wall (re-radiates heat at night).
    wall_heat: bool = False
    # Water barrels / stone floor in an enclosure buffer night temperatures.
    thermal_mass: bool = False
    min_heating_temp_c: float | None = None
    # Night-time buffering of an enclosure versus outside (°C).  ``None`` means
    # "use the default for the zone type" (greenhouse +3, cold frame +2).
    night_offset_c: float | None = None
    # Extra daytime warming in full sun (°C).  ``None`` = default for type.
    solar_gain_c: float | None = None


@dataclass(slots=True)
class Zone:
    id: str
    name: str
    type: ZoneType = ZoneType.OUTDOOR
    x_cm: float = 0
    y_cm: float = 0
    width_cm: float = 400
    length_cm: float = 300
    microclimate: Microclimate = field(default_factory=Microclimate)
    sensors: SensorMapping = field(default_factory=SensorMapping)
    vent_entity: str | None = None
    shade_entity: str | None = None
    # off = ignore, advise = tasks only, auto = drive vent/shade entities
    climate_control: Literal["off", "advise", "auto"] = "advise"
    # Shade screen override for enclosed zones: auto follows the advice.
    shading_mode: Literal["auto", "on", "off"] = "auto"
    # Frost protection for an enclosure (climate_control "auto"): a heater switched on below
    # ``microclimate.min_heating_temp_c`` (default 3 °C) and off 1.5 °C above it, within an
    # optional weekly energy budget.
    heater_entity: str | None = None
    heater_power_w: float = 0.0
    heater_budget_kwh_week: float | None = None
    heater_kwh: dict[str, float] = field(default_factory=dict)  # ISO week ("2026-W43") -> kWh used

    @property
    def is_enclosed(self) -> bool:
        return self.type in (ZoneType.GREENHOUSE, ZoneType.COLD_FRAME)


@dataclass(slots=True)
class SoilTest:
    """A soil analysis of one bed (lab report or home test kit)."""

    date: date
    ph: float | None = None
    organic_matter_pct: float | None = None
    # Lab values in mg per 100 g dry soil (or kit classes mapped to them).
    n_mg: float | None = None
    p_mg: float | None = None
    k_mg: float | None = None
    mg_mg: float | None = None
    lime_status: Literal["low", "ok", "high"] | None = None
    notes: str = ""


@dataclass(slots=True)
class GardenBed:
    id: str
    name: str
    zone_id: str
    kind: BedKind = BedKind.RAISED
    x_cm: float = 0
    y_cm: float = 0
    width_cm: float = 200
    length_cm: float = 100
    # Compass bearing of the rows (0 = rows run north-south).
    orientation_deg: int = 0
    soil: SoilType = SoilType.LOAM
    shade_pct: int | None = None  # overrides zone microclimate when set
    sensors: SensorMapping = field(default_factory=SensorMapping)
    irrigation_entity: str | None = None
    irrigation_flow_lpm: float | None = None
    # Learned from the water meter during watering runs (used when no flow is entered).
    measured_flow_lpm: float | None = None
    # The valve's own safety timer (it closes by itself after this many minutes):
    # longer runs are split so the valve never shuts mid-run.
    valve_max_min: float | None = None
    notes: str = ""
    soil_tests: list[SoilTest] = field(default_factory=list)
    # Learned by watching the soil moisture sensor after each run (GardenSettings.adaptive_irrigation):
    # > 1 when the soil takes up less than the water balance expects (sand, run-off), < 1 when more.
    water_factor: float = 1.0
    water_factor_runs: int = 0

    @property
    def flow_lpm(self) -> float | None:
        """Flow through the bed's valve: what was entered, else what the meter measured."""
        for value in (self.irrigation_flow_lpm, self.measured_flow_lpm):
            if value and value > 0:
                return value
        return None

    @property
    def latest_soil_test(self) -> SoilTest | None:
        return max(self.soil_tests, key=lambda s: s.date, default=None)

    @property
    def area_m2(self) -> float:
        return (self.width_cm * self.length_cm) / 10_000


@dataclass(slots=True)
class Planting:
    id: str
    plant_id: str
    bed_id: str
    season: int
    layout: LayoutMode = LayoutMode.SINGLE
    x_cm: float = 0
    y_cm: float = 0
    width_cm: float = 30
    length_cm: float = 30
    count: int | None = None  # ``None`` = derive from spacing
    method: SowMethod = SowMethod.DIRECT_SOW
    status: PlantingStatus = PlantingStatus.PLANNED
    # User overrides for the planned dates (otherwise the scheduler decides).
    sow_date: date | None = None
    transplant_date: date | None = None
    # What actually happened.
    sown_on: date | None = None
    transplanted_on: date | None = None
    harvest_started_on: date | None = None
    finished_on: date | None = None
    succession_group: str | None = None
    succession_index: int = 0
    notes: str = ""
    # Nothing carries into the next year by itself: the year-end transition
    # extends ``last_season`` explicitly for perennials and overwintering crops
    # (None = only its own season).
    last_season: int | None = None
    # Removed from the plan "from this season on" (history kept).
    removed_season: int | None = None


def present_in(planting: Planting, perennial: bool, season: int) -> bool:
    """Is this planting part of ``season``?

    A planting belongs to its own season and to every later season it was
    explicitly carried over into at a year-end transition (``last_season``) -
    perennials included: an apple tree stays in the plan because the gardener
    moved it into the new year, not by itself.  ``perennial`` is kept for
    callers that still pass it.
    """
    del perennial
    if season < planting.season:
        return False
    if planting.removed_season is not None and season >= planting.removed_season:
        return False
    return season <= (planting.last_season if planting.last_season is not None else planting.season)


@dataclass(slots=True)
class Feature:
    """Non-growing garden element: path, compost bin, water butt, shed, tree ..."""

    id: str
    name: str
    type: FeatureType = FeatureType.PATH
    x_cm: float = 0
    y_cm: float = 0
    width_cm: float = 60
    length_cm: float = 200
    notes: str = ""


@dataclass(slots=True)
class ArchivedPlan:
    """A garden plan set aside ("not active"): its layout and the crops it held, restorable."""

    id: str
    name: str
    season: int
    archived_at: datetime | None = None
    zones: list[Zone] = field(default_factory=list)
    beds: list[GardenBed] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    plantings: list[Planting] = field(default_factory=list)


@dataclass(slots=True)
class GardenLayout:
    """The garden plan of one season: zones, beds and elements - no plants."""

    zones: list[Zone] = field(default_factory=list)
    beds: list[GardenBed] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    saved_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class TaskNote:
    at: datetime
    text: str
    author: str | None = None


@dataclass(slots=True)
class Recurrence:
    interval_days: int
    until: date | None = None


@dataclass(slots=True)
class Task:
    id: str
    type: TaskType
    title: str
    due: date
    # Stable key for generated tasks so regeneration is idempotent.
    key: str | None = None
    title_key: str | None = None
    title_params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    window_start: date | None = None
    window_end: date | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_minutes: int = 10
    status: TaskStatus = TaskStatus.OPEN
    source: TaskSource = TaskSource.USER
    planting_id: str | None = None
    bed_id: str | None = None
    zone_id: str | None = None
    recurrence: Recurrence | None = None
    depends_on: list[str] = field(default_factory=list)
    completed_at: datetime | None = None
    notes: list[TaskNote] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    postponed_count: int = 0
    original_due: date | None = None
    user_modified: bool = False
    text_modified: bool = False  # the cook rewrote the title or description: recalculation leaves them
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Household member doing it: a person.* entity id (or None = anyone).
    assignee: str | None = None

    @property
    def is_open(self) -> bool:
        return self.status is TaskStatus.OPEN


# --------------------------------------------------------------------------- #
# Settings, history and the stored root document
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class RegionProfile:
    hemisphere: Hemisphere = Hemisphere.NORTH
    mode: Literal["usda", "preset", "custom"] = "preset"
    hardiness_zone: str | None = None
    preset: str | None = "nl_be"
    last_frost: str = "04-20"  # MM-DD, average last spring frost
    first_frost: str = "10-25"  # MM-DD, average first autumn frost
    frost_free: bool = False
    latitude: float | None = None
    time_zone: str | None = None


@dataclass(slots=True)
class NotificationSettings:
    persistent: bool = True
    notify_services: list[str] = field(default_factory=list)
    tts_entity: str | None = None
    tts_media_players: list[str] = field(default_factory=list)
    digest_time: str = "07:30"
    frost_alerts: bool = True
    heat_alerts: bool = True
    tts_frost_announcement: bool = False
    # Reminders for tasks left undone (evening nudge) and a weekly look-ahead.
    overdue_reminders: bool = True
    overdue_time: str = "18:30"
    overdue_after_days: int = 1
    weekly_plan: bool = True
    weekly_plan_weekday: int = 6  # 0 = Monday ... 6 = Sunday
    weekly_plan_time: str = "19:00"


@dataclass(slots=True)
class IrrigationSettings:
    """Hardware actuation for watering, with safety limits."""

    mode: Literal["off", "advise", "auto"] = "advise"
    pump_entity: str | None = None
    start_time: str = "06:00"
    max_runtime_min: float = 30.0
    # Outdoor valves are locked when the plant-level minimum in the next
    # 12 h - or the current outdoor temperature - is at or below this value.
    frost_lockout_c: float = 2.0
    rain_skip_mm: float = 3.0
    pump_lead_s: float = 3.0
    # Solar-aware runs (GardenSettings.solar_irrigation): a scheduled run waits until this power
    # sensor reports at least ``surplus_min_w`` W of surplus (export), but never past ``surplus_latest``.
    surplus_entity: str | None = None
    surplus_min_w: float = 500.0
    surplus_latest: str = "11:00"
    # ... or as soon as the home battery is (nearly) full: the surplus then goes to the grid anyway.
    battery_entity: str | None = None  # state of charge in %
    battery_full_pct: float = 95.0
    # Rain water first: a pump that draws from the butt(s) while they hold more than ``butt_min_pct``;
    # below that the mains pump (or plain mains pressure) takes over, unless ``butt_fallback`` is off -
    # then the run waits for rain.
    butt_pump_entity: str | None = None
    butt_min_pct: float = 10.0
    butt_fallback: bool = True
    # Electric power of the pumps, for the energy per run (kWh) - 0 = not counted.
    pump_power_w: float = 0.0
    butt_pump_power_w: float = 0.0


@dataclass(slots=True)
class GardenResources:
    """What the gardener has - remembered for the auto-planner."""

    household_size: int = 2
    hours_per_week: float = 3.0
    water_liters_per_week: float | None = None  # None = unlimited (mains)
    compost_kg: float | None = None
    irrigation: bool = False
    goals: list[str] = field(default_factory=lambda: ["fresh", "herbs"])
    wanted: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    # Auto-planner preferences
    # strict = only the wanted crops; balanced = wanted + goals; free = wider choice.
    freedom: Literal["strict", "balanced", "free"] = "balanced"
    respect_companions: bool = True  # never put bad neighbours together
    add_pollinators: bool = True  # add a few bee & hoverfly flowers
    year_round: bool = False  # add winter & storage crops for harvests in every month
    allow_perennials: bool = True  # may propose crops that stay for years
    match_zone_type: bool = True  # orchard -> fruit, herb garden -> herbs ...


@dataclass(slots=True)
class WaterSettings:
    """Garden water: a (sub)meter on the garden tap and the rain water butts."""

    meter_entity: str | None = None  # total m³ (or L) - a water meter / flow sensor
    butt_level_entity: str | None = None  # % full of the rain water butt(s)
    butt_capacity_l: float = 0.0  # total volume of all butts
    # Water counted while every Hortulus valve is closed -> a notification.
    leak_alerts: bool = True


@dataclass(slots=True)
class EconomySettings:
    """Shop prices and costs for the harvest-versus-cost overview."""

    currency: str = "€"
    water_price_m3: float = 5.0  # mains water incl. levies
    prices: dict[str, float] = field(default_factory=dict)  # plant id -> price per kg (overrides the defaults)


@dataclass(slots=True)
class Expense:
    """Money spent on the garden (seeds, plants, compost, tools ...)."""

    id: str
    day: date
    season: int
    category: Literal["seeds", "plants", "soil", "fertilizer", "tools", "water", "protection", "other"] = "other"
    amount: float = 0.0
    note: str = ""


@dataclass(slots=True)
class CookbookRecipe:
    """A recipe kept in the garden's own cookbook (rendered from its spec in any language)."""

    id: str
    spec: dict[str, Any] = field(default_factory=dict)
    title: str = ""  # the cook's own name for it ("" = the generated title)
    favorite: bool = False
    shared: bool = False  # visible to whoever may look at the garden (web)
    note: str = ""
    added: date | None = None
    cooked: list[date] = field(default_factory=list)
    # the cook's own version: an ingredient list and/or method that replace the generated ones
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GardenSettings:
    region: RegionProfile = field(default_factory=RegionProfile)
    weather_entity: str | None = None
    outdoor_sensors: SensorMapping = field(default_factory=SensorMapping)
    language: str | None = None  # None = follow Home Assistant
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    sensor_stale_minutes: int = 360
    companion_radius_cm: float = 60.0
    root_zone_depth_mm: float = 200.0
    max_irrigation_mm: float = 20.0
    gdd_base_c: float = 10.0
    snap_cm: int = 10
    irrigation: IrrigationSettings = field(default_factory=IrrigationSettings)
    resources: GardenResources = field(default_factory=GardenResources)
    water: WaterSettings = field(default_factory=WaterSettings)
    # Default assignee per task type ("*" = every type): person.* entity ids.
    assignment: dict[str, str] = field(default_factory=dict)
    # person.* -> notify service, for reminders addressed to that person.
    person_notify: dict[str, str] = field(default_factory=dict)
    # Optional extra forecast source (no API key, opt-in, needs internet).
    open_meteo: bool = False
    elevation_m: float | None = None
    # Seasonal maintenance tasks (soil prep, greenhouse cleaning, winter rest ...)
    maintenance_tasks: bool = True
    # Ecological gardening & permaculture: organic tips, eco calendar, food-forest advice (recommended).
    eco_tips: bool = True
    # Move weather-sensitive jobs (sowing, planting out, spraying ...) off rainy, frosty or hot days.
    weather_aware_scheduling: bool = True
    economy: EconomySettings = field(default_factory=EconomySettings)
    # -- Extras (2.0), each on by default and each can be switched off ------------------- #
    slogans: bool = True  # a changing garden saying in the digest, reports and the panel
    soil_estimate: bool = True  # soil temperature from the logged air when no soil sensor is mapped
    season_summary: bool = True  # monthly weather summary against last year (notification + report)
    local_frost_suggest: bool = True  # offer the measured frost dates once a few years are logged
    water_forecast: bool = True  # "this bed is dry in N days" from the forecast
    sensor_health: bool = True  # tell when a mapped sensor has gone silent for days
    station_import: bool = True  # import a weather station's CSV export into the climate history
    solar_irrigation: bool = True  # wait for solar surplus before a scheduled run (needs a surplus sensor)
    climate_card: bool = True  # the dashboard card shows the climate against last year
    # -- Extras (2.1) ---------------------------------------------------------------------- #
    frost_heating: bool = True  # switch an enclosure's heater against frost (needs a heater entity)
    adaptive_irrigation: bool = True  # learn per bed how much water really soaks in (needs a moisture sensor)
    own_yields: bool = True  # yield and harvest-start expectations learn from the garden's own years
    ai_diagnosis: bool = True  # "what is wrong with this plant?" from a photo (needs an AI task entity)
    calendar_mirror: bool = True  # copy the coming tasks into another calendar (needs a calendar entity)
    ai_task_entity: str | None = None  # ai_task.* entity; None = Home Assistant's preferred one
    mirror_calendar: str | None = None  # calendar.* entity that receives the tasks
    mirror_days: int = 7


@dataclass(slots=True)
class RotationRecord:
    bed_id: str
    season: int
    family: str
    plant_id: str | None = None
    source: Literal["planting", "manual"] = "manual"


@dataclass(slots=True)
class ClimateDay:
    """One local day of outdoor weather, as measured here or filled in afterwards.

    Own samples (a sensor, otherwise the weather entity) are folded in through the day;
    ``hours`` is how much of the day they cover.  Days the garden was not watched are
    filled from the recorder history of the same sensors (``source`` "history") or from
    Open-Meteo's observed weather ("model"); see :mod:`.climate`.
    """

    day: date
    tmin: float | None = None
    tmax: float | None = None
    rain_mm: float | None = None
    tmean: float | None = None
    t_n: int = 0  # samples behind tmean
    rh_min: float | None = None  # relative humidity %
    rh_max: float | None = None
    rh_mean: float | None = None
    rh_n: int = 0
    wind_mean: float | None = None  # km/h at 10 m
    wind_max: float | None = None
    gust_max: float | None = None
    w_n: int = 0
    rs_mj: float | None = None  # global (shortwave) radiation, MJ/m²
    sun_h: float | None = None  # sunshine hours (>= 120 W/m²)
    et0_mm: float | None = None  # reference evaporation given by the source (Open-Meteo)
    hours: float = 0.0  # hours of the day covered by own samples
    source: str = ""  # sensor | history | model, "+"-joined when mixed
    rain_src: str = ""  # gauge | forecast | history | model


@dataclass(slots=True)
class SensorDay:
    """Daily statistics of one measured temperature (outdoor, greenhouse air, soil ...)."""

    entity_id: str
    day: date
    tmin: float | None = None
    tmax: float | None = None
    tmean: float | None = None
    n: int = 0
    source: str = "sensor"  # sensor | history


@dataclass(slots=True)
class ClimateMonth:
    """A month of a series kept for good once its days leave the daily logs.

    ``series`` is ``"outdoor"`` or a sensor's entity id.
    """

    series: str
    month: str  # YYYY-MM
    days: int = 0
    tmin: float | None = None  # lowest
    tmax: float | None = None  # highest
    tmean: float | None = None  # mean of the daily means
    rain_mm: float = 0.0
    frost_days: int = 0  # minimum below 0 °C
    hot_days: int = 0  # maximum >= 25 °C
    sun_h: float = 0.0
    wind_max: float | None = None
    t_days: int = 0  # days with a temperature (the mean's weight; days of only rain do not count)


@dataclass(slots=True)
class FrostYear:
    """Measured frost dates of one year (outdoor): the local truth behind the regional preset."""

    last_spring: date | None = None
    first_autumn: date | None = None
    spring_complete: bool = False  # the whole frost season was logged
    autumn_complete: bool = False


@dataclass(slots=True)
class WaterBalance:
    """Root-zone depletion bucket per bed (used when no moisture sensor).

    With a moisture sensor the bucket is set from the reading once a day and
    the bed learns ``et_factor``: how much faster (or slower) it really dries
    out than the model predicts.  That keeps the bucket honest for the days
    the sensor is off or flat.
    """

    day: date | None = None
    depletion_mm: float = 0.0
    et_factor: float = 1.0
    calibrated_on: date | None = None  # last day the bucket was set from the sensor
    calibrated_mm: float | None = None  # sensor depletion on that day
    model_et_mm: float = 0.0  # modelled crop ET since then (factor 1), dry days only
    wet_since: bool = False  # rain or irrigation since the calibration: no learning


@dataclass(slots=True)
class IrrigationEvent:
    bed_id: str
    at: datetime
    mm: float
    liters: float = 0.0
    minutes: float = 0.0
    source: Literal["auto", "manual", "service", "task"] = "manual"
    water: Literal["mains", "rain"] = "mains"  # where the water came from
    kwh: float = 0.0  # pump energy (when the pump power is set)


@dataclass(slots=True)
class HarvestEntry:
    """What came out of the garden: weight and/or count, per planting."""

    id: str
    day: date
    plant_id: str
    kg: float = 0.0
    count: int | None = None
    planting_id: str | None = None
    bed_id: str | None = None
    quality: int | None = None  # 1 (poor) .. 5 (excellent)
    note: str = ""


@dataclass(slots=True)
class JournalEntry:
    """Garden diary: a note and/or photos, linked to a planting, bed or zone."""

    id: str
    at: datetime
    text: str = ""
    photos: list[str] = field(default_factory=list)
    kind: Literal["note", "observation", "problem", "milestone"] = "note"
    planting_id: str | None = None
    bed_id: str | None = None
    zone_id: str | None = None
    plant_id: str | None = None
    author: str | None = None


@dataclass(slots=True)
class SeedPacket:
    """Seed stock: one packet / jar of a variety."""

    id: str
    plant_id: str
    variety: str = ""
    year: int | None = None  # harvest / packing year ("use by" is derived from it)
    quantity: float = 1.0
    unit: Literal["packet", "seeds", "g"] = "packet"
    source: str = ""  # shop, swap, own harvest
    notes: str = ""


@dataclass(slots=True)
class WaterReading:
    """Daily snapshot of the water meter and the rain water butts."""

    day: date
    meter_m3: float | None = None
    butt_pct: float | None = None


@dataclass(slots=True)
class GardenData:
    """Root document persisted with ``homeassistant.helpers.storage.Store``."""

    revision: int = 0
    settings: GardenSettings = field(default_factory=GardenSettings)
    zones: list[Zone] = field(default_factory=list)
    beds: list[GardenBed] = field(default_factory=list)
    plantings: list[Planting] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    custom_plants: list[Plant] = field(default_factory=list)
    plant_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    rotation_history: list[RotationRecord] = field(default_factory=list)
    climate_log: list[ClimateDay] = field(default_factory=list)
    # Daily min/max/mean of every measured temperature, months kept for good, frost dates.
    sensor_log: list[SensorDay] = field(default_factory=list)
    climate_months: list[ClimateMonth] = field(default_factory=list)
    frost_years: dict[str, FrostYear] = field(default_factory=dict)
    # Dedupe keys of notifications already sent -> ISO date sent.
    notified: dict[str, str] = field(default_factory=dict)
    features: list[Feature] = field(default_factory=list)
    water_balance: dict[str, WaterBalance] = field(default_factory=dict)
    irrigation_log: list[IrrigationEvent] = field(default_factory=list)
    harvest_log: list[HarvestEntry] = field(default_factory=list)
    journal: list[JournalEntry] = field(default_factory=list)
    seed_stock: list[SeedPacket] = field(default_factory=list)
    water_log: list[WaterReading] = field(default_factory=list)
    expenses: list[Expense] = field(default_factory=list)
    # Garden plans per season.  ``zones``/``beds``/``features`` above are the
    # plan of ``layout_season`` - the garden as it is now; ``layouts`` holds the
    # plans of other seasons (archived years, next year's draft).  A new year
    # only gets a plan through the explicit year-end transition (or by
    # designing it); None = not yet adopted (set on first load).
    layout_season: int | None = None
    layouts: dict[str, GardenLayout] = field(default_factory=dict)
    # Plans set aside with "start a new plan"; one can be made active again.
    archived_plans: list[ArchivedPlan] = field(default_factory=list)
    # The kitchen: saved recipes and what the cook usually has in the house.
    cookbook: list[CookbookRecipe] = field(default_factory=list)
    cooking_prefs: dict[str, Any] = field(default_factory=dict)
    # Watering per year (the irrigation log keeps only 60 days): "2026" -> rain_l / mains_l / kwh
    irrigation_years: dict[str, dict[str, float]] = field(default_factory=dict)

    # -- lookups ---------------------------------------------------------- #
    def zone(self, zone_id: str | None) -> Zone | None:
        return next((z for z in self.zones if z.id == zone_id), None)

    def bed(self, bed_id: str | None) -> GardenBed | None:
        return next((b for b in self.beds if b.id == bed_id), None)

    def planting(self, planting_id: str | None) -> Planting | None:
        return next((p for p in self.plantings if p.id == planting_id), None)

    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def zone_of_bed(self, bed: GardenBed) -> Zone | None:
        return self.zone(bed.zone_id)

    def bed_sensors(self, bed: GardenBed) -> SensorMapping:
        zone = self.zone_of_bed(bed)
        merged = bed.sensors.merged_with(zone.sensors) if zone else bed.sensors
        if zone is None or not zone.is_enclosed:
            merged = merged.merged_with(self.settings.outdoor_sensors)
        return merged


# --------------------------------------------------------------------------- #
# Runtime snapshots (not persisted)
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class ForecastPoint:
    at: datetime
    temperature: float | None = None
    templow: float | None = None
    precipitation: float | None = None
    precipitation_probability: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None  # km/h, HA default for metric
    cloud_coverage: float | None = None
    condition: str | None = None
    dew_point: float | None = None
    # Daily sums from Open-Meteo (optional): MJ/m²/day
    shortwave_radiation: float | None = None


@dataclass(slots=True)
class WeatherSnapshot:
    available: bool = False
    fetched_at: datetime | None = None
    temperature: float | None = None
    humidity: float | None = None
    condition: str | None = None
    hourly: list[ForecastPoint] = field(default_factory=list)
    daily: list[ForecastPoint] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class SensorReading:
    entity_id: str
    value: float | None
    last_updated: datetime | None = None
    stale: bool = False

    @property
    def usable(self) -> float | None:
        return None if self.stale else self.value


@dataclass(slots=True)
class SensorSnapshot:
    """Resolved sensor values for a bed (zone fallbacks already applied)."""

    soil_moisture: SensorReading | None = None
    soil_temperature: SensorReading | None = None
    air_temperature: SensorReading | None = None
    air_humidity: SensorReading | None = None
    light: SensorReading | None = None
    rain: SensorReading | None = None
    par: SensorReading | None = None
    ec: SensorReading | None = None
    npk_n: SensorReading | None = None
    npk_p: SensorReading | None = None
    npk_k: SensorReading | None = None
    leaf_wetness: SensorReading | None = None
    wind_speed: SensorReading | None = None
    wind_gust: SensorReading | None = None
    radiation: SensorReading | None = None

    @staticmethod
    def value(reading: SensorReading | None) -> float | None:
        return reading.usable if reading else None
