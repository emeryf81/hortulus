// Mirrors custom_components/garden_manager/engine/models.py (serde.to_dict output).
// Keep both sides in sync - the websocket API sends these shapes verbatim.

export type ISODate = string; // "2026-04-20"
export type ISODateTime = string;

export type ZoneType = "outdoor" | "greenhouse" | "cold_frame" | "orchard" | "fruit" | "herbs" | "flowers" | "garden" | "containers" | "food_forest";
export type BedKind = "in_ground" | "raised" | "container";
export type SoilType = "sandy" | "loam" | "clay" | "silt" | "peat" | "chalk" | "potting_mix";
export type Wind = "sheltered" | "moderate" | "exposed";
export type LayoutMode = "single" | "block" | "row";
export type SowMethod = "indoor_sow" | "direct_sow" | "transplant";
export type PlantingStatus =
  | "planned" | "sown_indoors" | "sown" | "transplanted" | "harvesting" | "finished" | "failed";
export type TaskType =
  | "sow_indoor" | "sow_direct" | "harden_off" | "transplant" | "thin" | "stake" | "prune" | "pinch"
  | "earth_up" | "feed" | "water" | "weed" | "pest_check" | "harvest" | "ventilate" | "shade"
  | "frost_protect" | "soil_prep" | "compost" | "green_manure" | "mulch" | "clean_greenhouse"
  | "winter_prep" | "plan_season" | "tool_care" | "soil_test" | "cut_back" | "divide"
  | "protect" | "clean" | "tie_in" | "thin_fruit" | "pollinate" | "check" | "make_feed" | "custom";
export type TaskStatus = "open" | "done" | "skipped";
export type Priority = "low" | "normal" | "high" | "urgent";
export type RiskLevel = "none" | "low" | "moderate" | "high" | "unknown";
export type MoistureStatus = "dry" | "slightly_dry" | "optimal" | "wet" | "unknown";
export type Level = "low" | "medium" | "high";

export interface SensorMapping {
  soil_moisture: string | null;
  soil_temperature: string | null;
  air_temperature: string | null;
  air_humidity: string | null;
  light: string | null;
  rain: string | null;
  par?: string | null;
  ec?: string | null;
  npk_n?: string | null;
  npk_p?: string | null;
  npk_k?: string | null;
  leaf_wetness?: string | null;
  wind_speed?: string | null;
  wind_gust?: string | null;
  radiation?: string | null;
}

export interface Microclimate {
  shade_pct: number;
  wind: Wind;
  heated: boolean;
  min_heating_temp_c: number | null;
  night_offset_c: number | null;
  solar_gain_c: number | null;
  wall_heat?: boolean;
  thermal_mass?: boolean;
}

export interface Zone {
  id: string;
  name: string;
  type: ZoneType;
  x_cm: number;
  y_cm: number;
  width_cm: number;
  length_cm: number;
  microclimate: Microclimate;
  sensors: SensorMapping;
  vent_entity: string | null;
  shade_entity?: string | null;
  climate_control?: "off" | "advise" | "auto";
  shading_mode?: "auto" | "on" | "off";
  /** Frost heating (2.1): switched in climate_control "auto". */
  heater_entity?: string | null;
  heater_power_w?: number;
  heater_budget_kwh_week?: number | null;
  heater_kwh?: Record<string, number>;
}

export type FeatureType =
  | "path" | "compost" | "water_butt" | "shed" | "tree" | "hedge" | "trellis"
  | "terrace" | "lawn" | "flowerbed" | "fence" | "pond"
  | "house" | "driveway" | "street" | "parking" | "play" | "beehive"
  | "stone_path" | "wood_path" | "stepping_stones" | "bark_path" | "decking" | "wall" | "carport" | "shrub" | "pool" | "seating"
  | "other";

export interface Feature {
  id: string;
  name: string;
  type: FeatureType;
  x_cm: number;
  y_cm: number;
  width_cm: number;
  length_cm: number;
  notes: string;
}

export interface Bed {
  id: string;
  name: string;
  zone_id: string;
  kind: BedKind;
  x_cm: number;
  y_cm: number;
  width_cm: number;
  length_cm: number;
  orientation_deg: number;
  soil: SoilType;
  shade_pct: number | null;
  sensors: SensorMapping;
  irrigation_entity: string | null;
  irrigation_flow_lpm: number | null;
  measured_flow_lpm?: number | null;
  valve_max_min?: number | null;
  /** Learned from the moisture sensor after runs (2.1). */
  water_factor?: number;
  water_factor_runs?: number;
  notes: string;
  soil_tests?: SoilTest[];
}

export interface Planting {
  id: string;
  plant_id: string;
  bed_id: string;
  season: number;
  layout: LayoutMode;
  x_cm: number;
  y_cm: number;
  width_cm: number;
  length_cm: number;
  count: number | null;
  method: SowMethod;
  status: PlantingStatus;
  sow_date: ISODate | null;
  transplant_date: ISODate | null;
  sown_on: ISODate | null;
  transplanted_on: ISODate | null;
  harvest_started_on: ISODate | null;
  finished_on: ISODate | null;
  succession_group: string | null;
  succession_index: number;
  notes: string;
  /** Perennials: first season it is no longer in the ground (explicit removal). */
  /** Last season this planting is in the plan (carried over at the year-end transition); null = only its own season. */
  last_season?: number | null;
  removed_season?: number | null;
}

export interface TaskNote { at: ISODateTime; text: string; author: string | null }

export interface Task {
  id: string;
  type: TaskType;
  title: string;
  due: ISODate;
  key: string | null;
  title_key: string | null;
  title_params: Record<string, unknown>;
  description: string;
  window_start: ISODate | null;
  window_end: ISODate | null;
  priority: Priority;
  estimated_minutes: number;
  status: TaskStatus;
  source: "generated" | "sensor" | "weather" | "user";
  planting_id: string | null;
  bed_id: string | null;
  zone_id: string | null;
  recurrence: { interval_days: number; until: ISODate | null } | null;
  depends_on: string[];
  completed_at: ISODateTime | null;
  notes: TaskNote[];
  photos: string[];
  assignee?: string | null;
  postponed_count: number;
  original_due: ISODate | null;
  user_modified: boolean;
}

export interface Window { start_week: number; end_week: number; anchor: "last_frost" | "first_frost" }

export interface CompanionLink {
  plant: string;
  relation: "friend" | "enemy" | "neutral";
  reason: Record<string, string>;
  strength: number;
}

export interface CareRule {
  task: TaskType;
  start_day: number;
  interval_days: number | null;
  end_day: number | null;
  anchor: "planting" | "sow" | "transplant" | "harvest_start" | "last_frost" | "first_frost";
  minutes: number;
  notes: Record<string, string>;
}

export interface Plant {
  id: string;
  names: Record<string, string>;
  scientific_name: string;
  family: string;
  variety: string | null;
  habit: string;
  perennial: boolean;
  spacing_cm: number;
  row_spacing_cm: number;
  sowing_depth_cm: number;
  germination_days: [number, number];
  min_soil_temp_c: number;
  optimal_soil_temp_c: number;
  max_soil_temp_c: number | null;
  days_to_maturity: [number, number];
  maturity_from: "sow" | "transplant";
  harvest_duration_days: number;
  harvestable: boolean;
  continuous_harvest: boolean;
  harvest_interval_days: number | null;
  transplant_age_days: [number, number];
  sowing: { indoor_sow: Window[]; direct_sow: Window[]; transplant: Window[] };
  greenhouse: {
    suitability: "yes" | "no" | "conditional";
    min_night_c: number;
    max_day_c: number;
    season_extension_weeks: number;
    notes: Record<string, string>;
  };
  frost_tolerance: "tender" | "half_hardy" | "hardy" | "very_hardy";
  min_temp_c: number;
  max_temp_c: number;
  companions: CompanionLink[];
  rotation_years: number;
  pests: string[];
  diseases: string[];
  water_needs: Level;
  nutrient_needs: Level;
  feeding_interval_days: number | null;
  care: CareRule[];
  pruning_notes: Record<string, string>;
  thinning: boolean;
  succession_interval_days: number | null;
  gdd_base_c: number;
  gdd_to_maturity: number | null;
  tags: string[];
  category?: "vegetable" | "herb" | "flower" | "fruit";
  kc?: [number, number, number];
  npk?: [number, number, number];
  height_cm?: number;
  root_depth_cm?: number;
  plants_per_person?: number;
  yield_kg_m2?: number;
  deters?: string[];
  trap_for?: string[];
  allelopathic?: boolean;
  shade_tolerant?: boolean;
  harvest_windows?: Window[];
  years_to_bearing?: number;
  emoji?: string;
  icon?: string;
  color?: string;
  tips?: Record<string, string[]>;
  pollination?: "self" | "insects" | "wind" | "partner" | "none";
  source: "builtin" | "custom" | "override";
}

export interface FamilyInfo { en: string; nl: string; color: string }

export interface PairFinding {
  a: string;
  b: string;
  kind: "friend" | "enemy" | "overlap" | "same_family" | "pest_synergy" | "allelopathy" | "competition" | "shading";
  severity: "info" | "warning" | "error";
  score: number;
  distance_cm: number;
  key: string;
  params: Record<string, unknown>;
}

export interface RotationFinding {
  planting: string;
  bed_id: string;
  family: string;
  conflicting_season: number;
  years_required: number;
  severity: "warning" | "error";
  key: string;
  params: Record<string, unknown>;
  alternatives?: string[];
}

export interface CompatibilityReport {
  score: number;
  pairs: PairFinding[];
  rotation: RotationFinding[];
  out_of_bounds: string[];
  placement?: { planting: string; severity: string; key: string; params: Record<string, unknown> }[];
  timelines?: Record<string, Timeline>;
  suggestions?: Record<string, string[]>;
}

export interface Timeline {
  method: SowMethod;
  sow_window: { start: ISODate; end: ISODate } | null;
  sow_date: ISODate | null;
  transplant_window: { start: ISODate; end: ISODate } | null;
  transplant_date: ISODate | null;
  harden_off_date: ISODate | null;
  in_ground: ISODate;
  harvest_start: ISODate;
  harvest_end: ISODate;
  late: boolean;
}

export interface Irrigation {
  bed_id: string;
  action: "none" | "water" | "skip_rain_expected" | "check_manually";
  status: MoistureStatus;
  amount_mm: number;
  liters: number;
  duration_min: number | null;
  moisture: number | null;
  target_low: number | null;
  target_high: number | null;
  water_need: Level | null;
  etc_24h_mm: number | null;
  rain_24h_mm: number;
  rain_48h_mm: number;
  confidence: "high" | "medium" | "low";
  priority: Priority;
  reasons: string[];
}

export interface Reading { entity_id: string; value: number | null; last_updated: ISODateTime | null; stale: boolean }

export interface Frost {
  level: RiskLevel;
  min_temp_c: number | null;
  plant_level_min_c: number | null;
  min_at: ISODateTime | null;
  first_below_zero_at: ISODateTime | null;
  hours_below_zero: number;
  source: string;
}

export interface Alert {
  key: string;
  kind: "frost" | "heat" | "dry" | "sensor_stale" | "forecast" | "disease" | "nutrients";
  severity: "info" | "warning" | "critical";
  message_key: string;
  params: Record<string, unknown>;
  zone_id: string | null;
  bed_id: string | null;
}

export interface Analysis {
  computed_at: ISODateTime;
  today: ISODate;
  season: number;
  anchors: { last_frost: ISODate; first_frost: ISODate; frost_free: boolean };
  frost: Frost;
  beds: Record<
    string,
    {
      sensors: Record<string, Reading | null>;
      moisture_status: MoistureStatus;
      irrigation: Irrigation;
      active_plantings: string[];
      compatibility: CompatibilityReport;
      rotation: RotationFinding[];
      kc?: number;
      nutrients?: NutrientBalance;
      taw_mm?: number | null;
      depletion_mm?: number | null;
      et_factor?: number;
      dry_in_days?: number | null;
      dry_on?: ISODate | null;
      soil_temp_estimate?: number | null;
    }
  >;
  zones: Record<
    string,
    {
      frost: Frost;
      greenhouse: {
        action: "none" | "ventilate" | "shade" | "close_up" | "heat";
        inside_now_c: number | null;
        forecast_max_c: number | null;
        forecast_min_c: number | null;
        limit_max_c: number | null;
        limit_min_c: number | null;
        limiting_plants: string[];
        reasons: string[];
      } | null;
      air_temperature: number | null;
      humidity?: number | null;
      disease?: DiseaseRisk;
      gdd_season?: number | null;
    }
  >;
  timelines: Record<string, Timeline>;
  advice: Record<string, { action: string; status: string; reasons: { key: string; params: Record<string, unknown> }[] }>;
  outlook: { day: ISODate; tmin: number | null; tmax: number | null; rain_mm: number; et0_mm: number | null; et0_method?: string | null }[];
  gdd: { season_total: number; base_c: number; days_counted: number; since: ISODate };
  alerts: Alert[];
  weather_available: boolean;
  phenology?: Record<string, Phenology>;
  et0_today?: number | null;
  et0_method?: string | null;
  gdd_today?: number | null;
  pests?: PestWarning[];
  slogan?: string;
  local_frost?: { last_frost: string; first_frost: string; years: number } | null;
}

export interface PestWarning {
  pest: string;
  status: "active" | "soon";
  action: "net" | "check" | "collect" | "trap";
  source: "gdd" | "calendar" | "weather";
  start: ISODate | null;
  end: ISODate | null;
  generation: number;
  gdd: number | null;
  plantings: string[];
  beds: string[];
  plants: string[];
  label: string;
  advice: string;
}

export interface NutrientBalance {
  index: number | null;
  status: "unknown" | "deficient" | "balanced" | "excess";
  deficits: string[];
  excess: string[];
  source: "npk" | "ec" | "none";
}

export interface DiseaseRisk {
  level: RiskLevel;
  wet_hours: number;
  hutton_period: boolean;
  humidity_now: number | null;
  leaf_wet_now: boolean | null;
  reasons: string[];
}

export interface Phenology {
  planting_id: string;
  stage: "not_planted" | "establishing" | "vegetative" | "flowering" | "ripening" | "harvest" | "finished";
  progress: number;
  kc: number;
  gdd: number | null;
  gdd_target: number | null;
  harvest_estimate: ISODate | null;
  heat_stress_days: number;
  cold_stress_days: number;
  heat_stress_logged?: number;
  cold_stress_logged?: number;
  dull_days?: number | null;
  weather_delay_days?: number;
  delay_causes?: { heat?: number; dull?: number; cold?: number };
  gdd_source?: "outdoor" | "zone_sensor" | "outdoor_buffered";
}

/** A summary of a run of days (``climate.summarize``). */
export interface ClimatePeriod {
  days: number;
  days_with_temp?: number;
  tmean?: number;
  tmin?: number;
  tmin_day?: ISODate;
  tmax?: number;
  tmax_day?: ISODate;
  frost_nights?: number;
  hot_days?: number;
  very_hot_days?: number;
  gdd?: number;
  rain_mm: number | null;
  rain_days: number;
  wettest?: number;
  wettest_day?: ISODate;
  sun_h: number | null;
  rs_mj: number | null;
  gust_max?: number;
  gust_day?: ISODate;
  et0_mm: number | null;
  balance_mm?: number;
  rh_mean: number | null;
}

export interface ClimateDayRow {
  d: ISODate;
  lo: number | null;
  hi: number | null;
  m: number | null;
  r: number | null;
  s: number | null;
  w: number | null;
  rh: number | null;
  et0: number | null;
  src: string;
}

export interface ClimateMonthRow {
  month: string;
  days: number;
  tmin: number | null;
  tmax: number | null;
  tmean: number | null;
  rain_mm: number | null;
  frost_days: number;
  hot_days: number;
  sun_h: number | null;
  wind_max: number | null;
}

export interface ClimateSensorStats {
  entity_id: string;
  label: string;
  kind: "outdoor" | "zone_air" | "bed_air" | "soil";
  now: number | null;
  days: number;
  first_day?: ISODate;
  today?: { tmin: number | null; tmax: number | null; tmean: number | null };
  d7?: { tmin: number | null; tmax: number | null; tmean: number | null };
  d30?: { tmin: number | null; tmax: number | null; tmean: number | null };
  record_low?: { t: number | null; when: string } | null;
  record_high?: { t: number | null; when: string } | null;
  series?: { d: ISODate; lo: number | null; hi: number | null; m: number | null }[];
  months?: ClimateMonthRow[];
}

export interface ClimateStats {
  today: ISODate;
  season_start: ISODate;
  periods: Record<"d7" | "d30" | "season" | "season_last_year" | "d7_last_year" | "d30_last_year" | "d365", ClimatePeriod>;
  records: Partial<Record<"tmin" | "tmax" | "wettest" | "gust_max", { value: number; when: string }>>;
  series: ClimateDayRow[];
  months: ClimateMonthRow[];
  frost: {
    years: Record<string, { last_spring: ISODate | null; first_autumn: ISODate | null; spring_complete: boolean; autumn_complete: boolean }>;
    local: { years_spring: number; years_autumn: number; last_spring?: string; first_autumn?: string; spring_diff_days?: number; autumn_diff_days?: number } | null;
    preset_last: string | null;
    preset_first: string | null;
  };
  sensors: ClimateSensorStats[];
  coverage: { days: number; first_day: ISODate | null; sources: Record<string, number>; months_kept: number };
  /** The season and last month in sentences (settings.season_summary). */
  summary?: { season: string[]; month: string[]; month_start: ISODate };
  /** Measured frost dates worth using instead of the region's (settings.local_frost_suggest). */
  local_frost_suggestion?: { last_frost: string; first_frost: string; spring_diff_days: number | null; autumn_diff_days: number | null; years: number } | null;
  station_import?: boolean;
}

export interface IrrigationSettings {
  mode: "off" | "advise" | "auto";
  pump_entity: string | null;
  start_time: string;
  max_runtime_min: number;
  frost_lockout_c: number;
  rain_skip_mm: number;
  pump_lead_s: number;
  surplus_entity?: string | null;
  surplus_min_w?: number;
  surplus_latest?: string;
  battery_entity?: string | null;
  battery_full_pct?: number;
  butt_pump_entity?: string | null;
  butt_min_pct?: number;
  butt_fallback?: boolean;
  pump_power_w?: number;
  butt_pump_power_w?: number;
}

export interface Resources {
  household_size: number;
  hours_per_week: number;
  water_liters_per_week: number | null;
  compost_kg: number | null;
  irrigation: boolean;
  goals: string[];
  wanted: string[];
  excluded: string[];
  freedom?: "strict" | "balanced" | "free";
  respect_companions?: boolean;
  add_pollinators?: boolean;
  year_round?: boolean;
  allow_perennials?: boolean;
  match_zone_type?: boolean;
}

export interface IrrigationRun { bed_id: string; entity_id: string; minutes: number; mm: number; liters: number; capped: boolean }

export interface IrrigationPlan {
  runs: IrrigationRun[];
  skipped: Record<string, { key: string; params: Record<string, unknown> }>;
  reasons?: Record<string, string>;
  lockout: boolean;
  lockout_temp: number | null;
  total_minutes: number;
  running?: boolean;
}

export interface AutofillResult {
  plantings: Planting[];
  placements: { plant_id: string; bed_id: string; count: number; area_m2: number; reason: string; yield_kg: number;
    minutes_week: number; water_l_week: number; sowings: number }[];
  skipped: { plant_id: string; reason: string; beds?: Record<string, Reason[]> }[];
  /** The season had no plan: the proposal was made on this year's plan (copied when applied). */
  plan_from?: number | null;
  warnings: { key: string; params: Record<string, unknown> }[];
  beds: string[];
  summary: { crops: number; plantings: number; yield_kg: number; minutes_week: number; water_l_week: number; compost_kg: number; fertilizer_g: number };
  season: number;
  revision: number;
}

export interface HandbookChapterMeta { id: string; order: number; title: string; summary: string; sections: string[] }
export interface GlossaryEntry { term: string; text: string; chapter: string }

export interface PrintOptions {
  document: "garden" | "zone" | "beds" | "tasks" | "season" | "year" | "blank" | "plants" | "book";
  page: "a4" | "a3" | "a5" | "letter" | "remarkable";
  landscape: boolean;
  color_mode: "color" | "eink" | "grayscale";
  season?: number | null;
  zone_id?: string | null;
  bed_ids?: string[] | null;
  days: number;
  notes: boolean;
  grid: boolean;
  labels: boolean;
  title?: string | null;
}

export interface Settings {
  region: {
    hemisphere: "north" | "south";
    mode: "usda" | "preset" | "custom";
    hardiness_zone: string | null;
    preset: string | null;
    last_frost: string;
    first_frost: string;
    frost_free: boolean;
    latitude: number | null;
    time_zone: string | null;
  };
  weather_entity: string | null;
  outdoor_sensors: SensorMapping;
  language: string | null;
  notifications: {
    persistent: boolean;
    notify_services: string[];
    tts_entity: string | null;
    tts_media_players: string[];
    digest_time: string;
    frost_alerts: boolean;
    heat_alerts: boolean;
    tts_frost_announcement: boolean;
    overdue_reminders?: boolean;
    overdue_time?: string;
    overdue_after_days?: number;
    weekly_plan?: boolean;
    weekly_plan_weekday?: number;
    weekly_plan_time?: string;
  };
  weather_aware_scheduling?: boolean;
  economy?: { currency: string; water_price_m3: number; prices: Record<string, number> };
  water?: { meter_entity: string | null; butt_level_entity: string | null; butt_capacity_l: number; leak_alerts?: boolean };
  assignment?: Record<string, string>;
  person_notify?: Record<string, string>;
  sensor_stale_minutes: number;
  companion_radius_cm: number;
  root_zone_depth_mm: number;
  max_irrigation_mm: number;
  gdd_base_c: number;
  snap_cm: number;
  irrigation?: IrrigationSettings;
  resources?: Resources;
  open_meteo?: boolean;
  elevation_m?: number | null;
  maintenance_tasks?: boolean;
  eco_tips?: boolean;
  slogans?: boolean;
  soil_estimate?: boolean;
  season_summary?: boolean;
  local_frost_suggest?: boolean;
  water_forecast?: boolean;
  sensor_health?: boolean;
  station_import?: boolean;
  solar_irrigation?: boolean;
  climate_card?: boolean;
  frost_heating?: boolean;
  adaptive_irrigation?: boolean;
  own_yields?: boolean;
  ai_diagnosis?: boolean;
  calendar_mirror?: boolean;
  ai_task_entity?: string | null;
  mirror_calendar?: string | null;
  mirror_days?: number;
  wall_layout?: WallBlock[] | null;
}

export interface ForecastPoint {
  at: ISODateTime;
  temperature: number | null;
  templow: number | null;
  precipitation: number | null;
  precipitation_probability: number | null;
  condition: string | null;
  humidity?: number | null;
  wind_speed?: number | null;
  cloud_coverage?: number | null;
}

export interface Snapshot {
  revision: number;
  lang: string;
  settings: Settings;
  zones: Zone[];
  beds: Bed[];
  plantings: Planting[];
  tasks: Task[];
  features?: Feature[];
  /** Families grown per bed and season before Hortulus knew the plantings (crop rotation). */
  rotation_history?: { bed_id: string; season: number; family: string; plant_id?: string | null; source?: string }[];
  /** Season of the live garden plan (zones/beds/features above). */
  layout_season?: number | null;
  /** Garden plans of other seasons (archived years, next year's draft). */
  layouts?: Record<string, GardenLayout>;
  /** Season still waiting for its year-end transition, if the calendar moved on. */
  transition_due?: number | null;
  /** Plans set aside with "start a new plan". */
  archived_plans?: ArchivedPlanSummary[];
  /** Number of problems the garden check finds right now (badge on the Analysis tab). */
  diagnosis?: { error: number; warning: number; info: number } | null;
  harvest_log?: HarvestEntry[];
  journal?: JournalEntry[];
  /** This garden's config entry, and every garden in this Home Assistant. */
  entry_id?: string;
  gardens?: { entry_id: string; title: string }[];
  seed_stock?: SeedPacket[];
  irrigation_log?: { bed_id: string; at: ISODateTime; mm: number; liters: number; minutes: number; source: string }[];
  irrigation_status?: {
    running: boolean; bed_id: string | null; ends_at: ISODateTime | null; last_error: string | null;
    /** Valves or the pump open far longer than any run could last. */
    stuck?: { entity_id: string; since: ISODateTime; what: string }[];
    leak?: { entity_id: string; since: ISODateTime; liters: number; minutes: number } | null;
    /** A scheduled run waits for solar surplus (settings.solar_irrigation). */
    waiting_for_sun?: { since: ISODateTime; watts: number | null; needed: number; latest: string; battery?: number | null; battery_full?: number | null } | null;
    /** ISO date a run was held back because the rain water butt was empty (no mains fallback). */
    waiting_for_rain?: string | null;
  };
  analysis: Analysis | null;
  weather: {
    available: boolean;
    temperature: number | null;
    condition: string | null;
    fetched_at: ISODateTime | null;
    daily: ForecastPoint[];
    hourly: ForecastPoint[];
    error: string | null;
  };
  archived_seasons?: number[];
}

export interface PlanDoc { zones: Zone[]; beds: Bed[]; plantings: Planting[]; features: Feature[] }

export interface ArchivedPlanSummary {
  id: string; name: string; season: number; archived_at: ISODateTime | null;
  zones: number; beds: number; features: number; plantings: number;
}

/** A machine-readable reason with parameters, explained in the UI (``reason.<code>``). */
export interface Reason { code: string; params: Record<string, unknown> }

export interface AnalysisIssue { code: string; severity: "error" | "warning" | "info"; params: Record<string, unknown>; refs: Record<string, string[]>; fixable?: boolean }

export interface ValveTest {
  entity_id: string; seconds: number; before: string | null; ok: boolean;
  opened: boolean | null; open_state: string | null; closed: boolean; closed_state: string | null; pump: string | null;
}

export interface PlanRef { season?: number | null; plan_id?: string | null }

export interface DiffPart<T = { id: string; name: string }> { added: T[]; removed: T[]; changed: (T & { was?: string; what: string[] })[] }

export interface CropDiff { id: string; plant_id: string; name: string; bed: string; was_bed?: string }

export interface PlanComparison {
  a: string; b: string; identical: boolean;
  zones: DiffPart; beds: DiffPart; features: DiffPart; plantings: DiffPart<CropDiff>;
}

export interface AnalysisResult {
  season: number;
  layout_season: number | null;
  issues: AnalysisIssue[];
  errors: SyslogEntry[];
  counts: Record<string, number>;
}

export interface BedVerdict { bed_id: string; bed: string; zone: string; ok: boolean; reasons: Reason[]; warnings: Reason[]; free_m2: number }

export interface ExplainResult { plant_id: string; season: number; has_plan: boolean; beds: BedVerdict[] }

export interface GardenLayout { zones: Zone[]; beds: Bed[]; features: Feature[]; saved_at?: ISODateTime | null }

export interface CarryCandidate { planting_id: string; plant_id: string; bed_id: string; reason: "perennial" | "overwinter"; selected: boolean }

export interface TransitionPreview {
  from_season: number;
  to_season: number;
  zones: Zone[];
  features: Feature[];
  beds: Bed[];
  target_exists: boolean;
  is_live: boolean;
  candidates: CarryCandidate[];
}

export interface TransitionResult { season: number; carried: string[]; skipped: string[]; activated: boolean; revision: number }

// Minimal subset of the Home Assistant frontend `hass` object we use.
export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  services: Record<string, Record<string, unknown>>;
  language: string;
  locale?: { language: string };
  themes?: { darkMode?: boolean };
  user?: { id: string; is_admin: boolean; name: string };
  config?: { country?: string | null; latitude?: number; longitude?: number };
  connection: {
    sendMessagePromise<T>(msg: Record<string, unknown>): Promise<T>;
    subscribeMessage<T>(cb: (msg: T) => void, msg: Record<string, unknown>): Promise<() => Promise<void>>;
  };
  fetchWithAuth(path: string, init?: RequestInit): Promise<Response>;
  callService(domain: string, service: string, data?: Record<string, unknown>): Promise<unknown>;
}

// -- advice, Q&A and supplies (phase 3) ---------------------------------- //
export interface Suggestion {
  id: string;
  kind: string;
  severity: "warning" | "tip" | "info";
  title: string;
  text: string;
  plants: string[];
  zone_id: string | null;
  bed_id: string | null;
  planting_id: string | null;
  action: { type: string; plant_id?: string; bed_id?: string; planting_id?: string; feature?: string; from_season?: number } | null;
  handbook: string | null;
}
export interface AdviceResult { suggestions: Suggestion[]; coverage: { months: string[][]; gaps: number[] } }
export interface QaTarget { id: string; name: string; planted?: boolean; category?: string }
export interface QaOptions { subjects: Record<string, string[]>; targets: Record<string, QaTarget[]> }
export interface QaAnswer {
  subject: string;
  problem: string;
  target: string | null;
  title: string;
  status: string[];
  facts: string[];
  causes: string[];
  actions: string[];
  remedies: string[];
  prevention: string[];
  tasks: { id: string; title: string; due: string }[];
  plants: string[];
  handbook: string | null;
}
export interface ShoppingItem { id: string; name: string; emoji: string; quantity: number; unit: string; reason: string; category: string }
export interface Supplies {
  tools: Record<string, { name: string; emoji: string; kind: string }>;
  task_tools: Record<string, string[]>;
  shopping: ShoppingItem[];
}

// -- records (harvest, diary, seeds, soil, water) ------------------------- //
export interface HarvestEntry { id: string; day: ISODate; plant_id: string; kg: number; count: number | null; planting_id: string | null; bed_id: string | null; quality: number | null; note: string }
export interface JournalEntry {
  id: string; at: ISODateTime; text: string; photos: string[]; kind: "note" | "observation" | "problem" | "milestone";
  planting_id: string | null; bed_id: string | null; zone_id: string | null; plant_id: string | null; author: string | null;
}
/** What the AI task saw on a photo (2.1). */
export interface PhotoDiagnosis {
  problem_id: string; kind: "pest" | "disease" | "healthy" | "other"; name: string; confidence: number;
  explanation: string; remedy: string; known: boolean;
}
export interface SeedPacket { id: string; plant_id: string; variety: string; year: number | null; quantity: number; unit: "packet" | "seeds" | "g"; source: string; notes: string }
export interface SeedStatus extends SeedPacket { use_by: number | null; status: "ok" | "use_soon" | "expired" | "unknown" | "empty"; needed: boolean }
export interface SoilTest { date: ISODate; ph: number | null; organic_matter_pct: number | null; n_mg: number | null; p_mg: number | null; k_mg: number | null; mg_mg: number | null; lime_status: string | null; notes: string }
export interface CropHarvest { plant_id: string; kg: number; count: number; entries: number; first: ISODate | null; last: ISODate | null; area_m2: number; kg_m2: number | null }
export interface YearRow { plant_id: string; months: Record<string, string[]>; beds: string[] }
export interface RecordsOverview {
  season: number;
  harvest_season: Record<string, CropHarvest>;
  harvest_all: Record<string, CropHarvest>;
  harvest_years?: Record<string, Record<string, number>>;
  learned_yields: Record<string, number>;
  seeds: { packets: SeedStatus[]; missing: string[]; season: number };
  water: {
    week_l: number | null; season_l: number | null; rain_available_l: number | null; butt_pct: number | null; per_day: { day: string; liters: number }[];
    irrigated_rain_l?: number; irrigated_mains_l?: number; pump_kwh?: number;
  };
  year: { season: number; rows: YearRow[]; tasks: number[]; minutes: number[] } | null;
  kitchen?: KitchenReport | null;
  economics?: Economics;
  expenses?: Expense[];
}

export interface KitchenReport {
  ready: { planting_id: string; plant_id: string; name: string; bed: string; until: ISODate; group: string; keep: string }[];
  surplus: { plant_id: string; name: string; kg_week: number; need_week: number; group: string; ideas: string }[];
  picked_week_kg: number;
  people: number;
}

export interface Economics {
  season: number;
  currency: string;
  harvest_value: number;
  harvest_kg: number;
  crops: { plant_id: string; name: string; kg: number; price: number; value: number }[];
  expenses: Record<string, number>;
  water_m3: number | null;
  water_cost: number;
  total_cost: number;
  balance: number;
}

export interface Expense {
  id: string;
  day: ISODate;
  season: number;
  category: string;
  amount: number;
  note: string;
}

// -- system log ------------------------------------------------------------- //
export type SyslogOp = "add" | "remove" | "change";

export interface SyslogSummary {
  col: string;
  op: SyslogOp;
  key?: string;
  name?: string | null;
  plant_id?: string | null;
  bed?: string | null;
  season?: number | null;
  status?: string | null;
}

export interface SyslogEntry {
  id: string;
  at: string;
  reason: string;
  source: "user" | "system" | "error";
  user: string | null;
  undo_of: string | null;
  undone_by: string | null;
  summary: SyslogSummary[];
  count: number;
}

export interface SyslogPage {
  entries: SyslogEntry[];
  more: boolean;
  total: number;
}

export interface UndoResult {
  ok: boolean;
  conflicts: { col: string; key: string; op: SyslogOp }[];
  problems: string[];
  undone_by: string | null;
  revision: number;
}

// -- kitchen ------------------------------------------------------------------ //
export interface RecipeSpec {
  technique: string;
  produce: string[];
  side: string;
  protein: string;
  extras: string[];
  servings: number;
}

export interface RecipeIngredient {
  id: string;
  plant_id?: string;
  name: string;
  qty: number;
  unit: string;
  label: string;
  group: string;
  kind?: string;
  source: "garden" | "pantry" | "shop" | "basic";
  color?: string;
  extra?: boolean;
}

/** An ingredient the cook typed (their own version of a recipe). */
export interface CustomIngredient {
  id?: string;
  name: string;
  qty: number;
  unit: string;
  source: "garden" | "pantry" | "shop";
  group?: string;
  plant_id?: string;
  kind?: string;
  color?: string;
}

/** The recipes a command is about: saved ones by id, unsaved ones by spec; what is at home. */
export interface RecipeTarget {
  ids?: string[];
  specs?: RecipeSpec[];
  pantry?: string[];
}

export interface Recipe {
  id: string;
  spec: RecipeSpec;
  title: string;
  subtitle: string;
  technique: string;
  technique_name: string;
  /** The cookbook chapter: soup, starter, main, dessert or preserving. */
  course?: "soup" | "starter" | "main" | "dessert" | "preserve";
  course_name?: string;
  minutes: number;
  servings: number;
  ingredients: RecipeIngredient[];
  steps: string[];
  shopping: { id: string; name: string; qty: number; unit: string; label: string; group: string }[];
  tags: string[];
  tag_names: string[];
  garden_share: number;
  picture: {
    produce: { plant_id: string; kind: string; color: string; icon?: string; emoji?: string }[];
    side: string;
    protein: string;
    extras: string[];
    technique: string;
  };
  /** The cook's own ingredient list and/or method (cookbook). */
  custom?: boolean;
  // in the cookbook
  saved?: boolean;
  favorite?: boolean;
  shared?: boolean;
  note?: string;
  added?: string | null;
  cooked?: string[];
}

export interface CookingPrefs {
  pantry: string[];
  use: string[];
  proteins: string[];
  side: string;
  servings: number;
}

export interface CookingProduce {
  plant_id: string;
  name: string;
  kind: string;
  until?: string | null;
  beds?: string[];
  icon?: string;
  color?: string;
  emoji?: string;
}

export interface CookingCatalog {
  sides: { id: string; name: string }[];
  proteins: { id: string; name: string; group: string }[];
  /** `fridge: false`: a cupboard item (baking powder ...), not offered as "use up from the fridge". */
  pantry: { id: string; name: string; group: string; fridge?: boolean }[];
  techniques: { id: string; name: string; course?: string }[];
  edible: CookingProduce[];
}

/** A starter (or soup), a main course and a dessert that belong together. */
export interface CookingMenu {
  id: string;
  /** A themed menu ("provence", "flemish_spring" ...); empty for one built around a main course. */
  theme: string;
  title: string;
  courses: { course: "soup" | "starter" | "main" | "dessert"; recipe: Recipe }[];
  minutes: number;
  servings: number;
}

export interface CookingOverview {
  ready: CookingProduce[];
  produce: CookingProduce[];
  recipes: Recipe[];
  menus?: CookingMenu[];
  prefs: CookingPrefs | null;
  used_prefs: CookingPrefs;
  catalog: CookingCatalog;
  book: Recipe[];
}

/** One block of the wall screen: which one and how many of the 4 columns it spans. */
export interface WallBlock { id: string; w: number }

/** What the wall screen needs beyond the snapshot (wall/data). The texts are Dutch. */
export interface WallData {
  layout: WallBlock[];
  custom: boolean;
  blocks: Record<string, number>;
  saying: string;
  fact: string;
  eco_month: { title: string; text: string };
  recipe: { title: string; minutes: number | null; produce: string[]; course: string | null } | null;
  ready: { name: string; until: string | null }[];
}
