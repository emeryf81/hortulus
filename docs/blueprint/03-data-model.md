<!-- Generated from the sources by a script: code excerpts below are verbatim. -->
[↑ Blueprint contents](../BLUEPRINT.md) · [4. Backend (Python) →](04-backend-python.md)

## 3. Data Model

All models are dataclasses in [`engine/models.py`](../../custom_components/garden_manager/engine/models.py)
serialised by [`engine/serde.py`](../../custom_components/garden_manager/engine/serde.py)
(unknown keys ignored, missing keys defaulted, enums/dates as ISO strings). The frontend
mirrors them in [`frontend/src/types.ts`](../../frontend/src/types.ts).

Conventions: lengths in **cm**, temperatures **°C**, rain **mm**; canvas origin top‑left;
planting coordinates relative to their bed; calendar dates local, timestamps tz‑aware; a
*season* is named after the year its spring falls in (southern hemisphere: July → June).

### 3.1 Layout: `Zone`, `GardenBed`, sensor mapping

```python
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
```

Zone types: `outdoor`, `greenhouse`, `cold_frame` (the two *enclosed* types have their own
climate and sensors), `orchard`, `fruit`, `herbs`, `flowers`, `garden` (ornamental),
`containers` (planters & pots) and `food_forest` (seven layers, see `engine/eco.py`).
Beds in the non‑enclosed types use the outdoor sensors. Bed kinds: `in_ground`, `raised`,
`container` (potting mix). Besides the sensor and shade fields shown above, a bed holds the
valve data the controller needs: `irrigation_entity`, `irrigation_flow_lpm` (entered),
`measured_flow_lpm` (learned from the water meter; `flow_lpm` prefers the entered value) and
`valve_max_min` (the valve's own safety timer: longer runs are split into openings that stay inside it).

Non‑growing **elements** are `Feature`s (`id`, `name`, `type`, position, size, notes) with 29
types, grouped in the planner as buildings & paving (house, carport, shed, driveway, parking,
street, terrace, decking, wall), paths (gravel `path`, stone, wood, bark, stepping stones),
green (lawn, flowerbed, hedge, shrub, tree, pond) and outdoor living (seating, pool, play,
fence, trellis, compost, water butt, beehive, other). `engine/coverage.py` (mirrored by
`frontend/src/planner/coverage.ts`) decides what covers what: solid elements and growing zones
take their area away from a ground cover underneath (lawn, terrace, border …) in the map, the
print and the m² shown; a tree or shrub takes nothing.

**Plans per season.** The garden plan (zones, beds, elements – no plants) is stored per
season. The plan of `layout_season` lives in `GardenData.zones/beds/features` and is the garden
as it is now (entities, tasks and irrigation work with it); other seasons are
`GardenLayout`s in `GardenData.layouts` (`{season: layout}`). Plans set aside with *start a new
plan* are `ArchivedPlan`s (layout + the plantings it held). Nothing carries into a new
year by itself: a `Planting` belongs to its own `season` and to the seasons it was moved into
at the year‑end transition (`last_season`), see 4.16.

### 3.2 `Plant`

Sowing windows are **weeks relative to a frost anchor**, which makes one database work on
both hemispheres and in every climate.

```python
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
```

The built‑in database (`data/plants.json`, ≈ 600 kB, generated by `scripts/build_plantdb.py`
from compact profile rows plus `scripts/plantdb_extra.py`) holds **232 crops** –
vegetables, herbs, fruit (trees, soft, cane and vine fruit), companion flowers and green
manures – with `names`, `tips` and companion `reason`s in **EN, NL and FR**, Kc per stage,
N‑P‑K demand, height, root depth, yield and plants per person, pollination, harvest windows,
icon/colour/emoji and 178 companion relations. Relations are stored once and made symmetric at load
(*enemy wins* when two sources disagree), with a family‑level fallback. User data layers on top:
`custom_plants` (full `Plant`s, `source: "custom"`) and `plant_overrides` (a sparse patch per
built‑in plant, deep‑merged, `source: "override"`; language dictionaries add up per language and
extra sowing windows are kept).

A database entry (excerpt of `data/plants.json`):

```json
  {
   "habit": "bush",
   "category": "fruit",
   "perennial": true,
   "spacing_cm": 25,
   "row_spacing_cm": 25,
   "sowing_depth_cm": 0.5,
   "germination_days": [
    10,
    21
   ],
   "min_soil_temp_c": 12,
   "optimal_soil_temp_c": 20,
   "days_to_maturity": [
    90,
    120
   ],
   "maturity_from": "sow",
   "harvest_duration_days": 150,
   "continuous_harvest": true,
   "harvest_interval_days": 4,
   "transplant_age_days": [
    56,
    84
   ],
   "sowing": {
    "indoor_sow": [
    …
```

### 3.3 `Planting`

```python
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
```

### 3.4 `Task`

```python
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
```

### 3.5 Runtime snapshots: `WeatherSnapshot`, `SensorSnapshot`

```python
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
```

### 3.6 Root document, versioning & migrations

```python
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
```

The document is persisted with `homeassistant.helpers.storage.Store` at
`(version=1, minor_version=8)`. Minor versions are additive; HA calls our migration on load,
and the plan importer reuses the same chain for files exported by older releases. Each step is
a pure `dict → dict` function in `engine/migrations.py`:

| Minor | Introduced | Change |
|---|---|---|
| 1.2 | 1.0 | `plantings[].succession_group/succession_index`; `beds[].shape` replaced by `kind` |
| 1.3 | 1.0 | `tasks[].photos`; `tasks[].notes` become objects; `settings.notifications` block |
| 1.4 | 1.0 | `climate_log`, `notified` (GDD, notification de‑duplication) |
| 1.5 | 1.1 | `features`, `water_balance`, `irrigation_log`, `settings.irrigation/resources` |
| 1.6 | 1.4 | plans per season (`layout_season`, `layouts`) and explicit carry‑over (`plantings[].last_season`); the date‑dependent part (which year the plan is, which perennials stay) runs in `seasons.adopt` after loading |
| 1.7 | 1.4 | `archived_plans` (plans set aside) |
| 1.8 | 1.8 | `sensor_log`, `climate_months`, `frost_years` (climate history and statistics); the new optional `ClimateDay` fields are defaulted by `serde` |

Records added later (harvest log, journal, seed stock, water log, expenses, cookbook,
`cooking_prefs`, economy settings, soil tests …) are new optional keys: `serde` defaults missing
keys, so they need no step.

```python
def _v1_2_to_1_3(doc: Doc) -> Doc:
    for task in doc.get("tasks", []):
        task.setdefault("photos", [])
        notes = task.get("notes", [])
        if notes and isinstance(notes[0], str):
            stamp = task.get("updated_at") or task.get("created_at") or "1970-01-01T00:00:00+00:00"
            task["notes"] = [{"at": stamp, "text": text, "author": None} for text in notes]
    settings = doc.setdefault("settings", {})
    legacy = settings.pop("notify_service", None)
    notifications = settings.setdefault("notifications", {})
    if legacy and not notifications.get("notify_services"):
        notifications["notify_services"] = [legacy]
    return doc


def migrate(doc: Doc, major: int, minor: int) -> Doc:
    """Bring ``doc`` from ``major.minor`` to the current version."""
    if major > STORAGE_VERSION:
        raise MigrationError(f"Data version {major}.{minor} is newer than supported")
    out = copy.deepcopy(doc)
    current = max(minor, 1)
    while current < STORAGE_MINOR_VERSION:
        out = MIGRATIONS[current](out)
        current += 1
    return out
```

```python
class GardenStore(Store[dict[str, Any]]):
    """Store with Hortulus migrations."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        _LOGGER.info(
            "Migrating Hortulus data from %s.%s to %s.%s",
            old_major_version,
            old_minor_version,
            STORAGE_VERSION,
            STORAGE_MINOR_VERSION,
        )
        return migrate(old_data, old_major_version, old_minor_version)
```

The *revision* counter guards the plan for optimistic concurrency (the planner sends
`base_revision`); task edits do not bump it, so ticking off a chore never invalidates an
open editor.

### 3.7 Settings, records and cooking data

All in `GardenData` next to the plan (see `engine/models.py`):

| Dataclass | Holds |
|---|---|
| `GardenSettings` | `region` (`RegionProfile`: hemisphere, preset/custom/USDA mode, frost dates, `frost_free`, latitude, time zone), `weather_entity`, `outdoor_sensors`, `language`, `notifications` (persistent, notify services, TTS, digest/overdue/weekly times), `irrigation` (mode, pump, start time, max runtime, frost lockout, rain skip, pump lead, `surplus_entity`, `surplus_min_w` (500), `surplus_latest` ("11:00")), `resources` (household, hours, water, compost, goals, wanted/excluded, autofill preferences), `water` (meter, butt level + capacity, leak alerts), `economy` (currency, water price, own prices per crop), `assignment`, `person_notify`, `open_meteo`, `elevation_m`, `maintenance_tasks`, `eco_tips`, `weather_aware_scheduling`, the extras (2.0, all `True` by default: `slogans`, `soil_estimate`, `water_forecast`, `sensor_health`, `season_summary`, `local_frost_suggest`, `station_import`, `solar_irrigation`, `climate_card`), `sensor_stale_minutes`, `companion_radius_cm`, `root_zone_depth_mm`, `max_irrigation_mm`, `gdd_base_c`, `snap_cm` |
| Task data | `Task`, `TaskNote`, `Recurrence`; `RotationRecord` (manual + implied (bed, season, family) records) |
| Climate & water | `ClimateDay` (one outdoor day: temperature, humidity, wind, gusts, radiation, sunshine, rain, sources), `SensorDay` (daily min / max / mean per temperature sensor), `ClimateMonth` (a month kept for good per series), `FrostYear` (measured frost dates per year), `WaterBalance` per bed (depletion, `et_factor` learned from the moisture sensor, calibration), `IrrigationEvent` (run log), `WaterReading` (meter m³, butt %) |
| Records | `HarvestEntry`, `JournalEntry` (text, photos, links to bed/crop/plant), `SeedPacket`, `SoilTest` (per bed), `Expense` |
| Cooking | `CookbookRecipe` (a small *spec* + title, favourite, `shared`, note, dates cooked, optional own `ingredients` / `steps`), `cooking_prefs` (what the cook has at home, uses up, likes, side, servings) |
| Plans | `GardenLayout`, `ArchivedPlan`, `layout_season` |

Photos are stored as references to Home Assistant's `image_upload` store (the dependency in
the manifest), never as bytes in the garden document.

The climate history (4.22) lives in four collections of `GardenData`: `climate_log`
(`ClimateDay`, outdoor, 800 days), `sensor_log` (`SensorDay`, 400 days), `climate_months`
(`ClimateMonth`, kept for good; `series` is `"outdoor"` or an entity id) and `frost_years`
(`FrostYear` by year):

```python
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
```

### 3.8 Stored documents per garden

Each garden (config entry) owns up to four `Store` keys; the first garden keeps the original
keys, later ones get `garden_manager.garden_<8 hex>` (kept in the entry's data as `storage_key`).

| Key | Content | Notes |
|---|---|---|
| `garden_manager.garden` | the `GardenData` document | schema 1.8, debounced save (5 s), done tasks pruned after 400 days |
| `garden_manager.garden.syslog` | the system log (last 500 entries, diffs with `before`/`after`) | version 1 store of its own, so the garden document needs no migration for it |
| `garden_manager.garden.archive` | plantings and plans of seasons older than the last three | see 4.16 |
| `garden_manager.garden.corrupt` / `.backup` | a document that failed to load (kept, a fresh garden starts) / a copy kept when the entry is removed | recovery only |

`serde` is deliberately forgiving on read: unknown keys are ignored, missing keys defaulted, and
an empty JSON object that came back as an empty list (a PHP `json_decode` round trip) loads
as `{}`. Numeric input from the panel is validated in `operations.py` (NaN and infinity are refused
for sizes, positions and weights; `null` for a required field is refused).

---

---

[↑ Blueprint contents](../BLUEPRINT.md) · [4. Backend (Python) →](04-backend-python.md)
