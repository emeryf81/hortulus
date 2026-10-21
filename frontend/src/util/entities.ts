/**
 * Which Home Assistant entities can serve a setting: a valve or switch for a
 * bed, a moisture sensor for the soil, a TTS engine for announcements ...
 * Settings show only these in their drop-downs.
 */

export type EntityKind =
  | "soil_moisture" | "soil_temperature" | "air_temperature" | "air_humidity" | "light" | "rain" | "par" | "ec"
  | "npk_n" | "npk_p" | "npk_k" | "leaf_wetness" | "wind_speed" | "wind_gust" | "radiation"
  | "weather" | "irrigation" | "pump" | "tts" | "media_player" | "vent" | "shade" | "meter" | "butt" | "power"
  | "battery" | "heater" | "calendar" | "ai_task";

export interface EntityLike {
  entity_id: string;
  state?: string;
  attributes: Record<string, unknown>;
}

const DOOR_LIKE = new Set(["garage", "door", "gate"]);
const NPK_UNITS = ["mg/kg", "mg/l", "ppm"];
const NPK_WORDS: Record<"npk_n" | "npk_p" | "npk_k", string[]> = {
  npk_n: ["nitrogen", "stikstof", "azote", "_n_", "_n "],
  npk_p: ["phosph", "fosfor", "fosfaat", "_p_", "_p "],
  npk_k: ["potass", "kalium", "_k_", "_k "],
};
const SOIL_WORDS = ["soil", "bodem", "grond", "ground", "sol_", " sol", "probe"];

function unit(s: EntityLike): string {
  return String(s.attributes.unit_of_measurement ?? "").toLowerCase().replace("μ", "µ");
}

function cls(s: EntityLike): string {
  return String(s.attributes.device_class ?? "");
}

function named(s: EntityLike, words: string[]): boolean {
  const text = `${s.entity_id} ${String(s.attributes.friendly_name ?? "")} `.toLowerCase();
  return words.some((w) => text.includes(w));
}

/** True when this entity can be used for this kind of setting. */
export function entityFits(kind: EntityKind, s: EntityLike): boolean {
  const domain = s.entity_id.split(".")[0];
  const sensor = domain === "sensor";
  const u = unit(s);
  const dc = cls(s);
  switch (kind) {
    case "weather":
      return domain === "weather";
    case "irrigation": // a smart plug (outlet) drives a pump, not a bed
      return domain === "valve" || domain === "input_boolean" || (domain === "switch" && dc !== "outlet");
    case "pump":
      return domain === "valve" || domain === "input_boolean" || domain === "switch";
    case "tts":
      return domain === "tts";
    case "media_player":
      return domain === "media_player";
    case "vent":
      return (domain === "cover" && !DOOR_LIKE.has(dc)) || domain === "fan" || domain === "switch";
    case "shade":
      return (domain === "cover" && !DOOR_LIKE.has(dc) && dc !== "window") || domain === "switch";
    case "meter":
      return (sensor && (dc === "water" || ["l", "m³", "gal", "ft³"].includes(u))) || domain === "input_number";
    case "butt":
      return (sensor && (["volume_storage", "water", "volume", "distance"].includes(dc) || ["%", "l", "m³", "cm", "mm", "m"].includes(u)))
        || domain === "input_number";
    case "power": // solar surplus / grid export, in W or kW
      return (sensor && (dc === "power" || ["w", "kw"].includes(u))) || domain === "input_number";
    case "battery": // a home battery's state of charge
      return (sensor && (dc === "battery" || (u === "%" && named(s, ["soc", "batter", "accu", "charge"])))) || domain === "input_number";
    case "heater": // a heater on a smart plug, or a climate entity
      return domain === "switch" || domain === "input_boolean" || domain === "climate";
    case "calendar":
      return domain === "calendar" && !s.entity_id.startsWith("calendar.hortulus");
    case "ai_task":
      return domain === "ai_task";
    case "soil_moisture":
      return sensor && (dc === "moisture" || (dc === "humidity" && named(s, ["soil", "bodem", "sol", "plant"])));
    case "soil_temperature": // a soil probe says so in its name
      return sensor && (dc === "temperature" || u === "°c" || u === "°f") && named(s, SOIL_WORDS);
    case "air_temperature":
      return sensor && (dc === "temperature" || u === "°c" || u === "°f") && !named(s, SOIL_WORDS);
    case "air_humidity":
      return sensor && dc === "humidity";
    case "light":
      return sensor && (dc === "illuminance" || u === "lx");
    case "rain":
      return (sensor && (dc === "precipitation" || dc === "precipitation_intensity" || (["mm", "mm/h", "in", "in/h"].includes(u) && named(s, ["rain", "regen", "pluie", "precip"]))))
        || (domain === "binary_sensor" && (dc === "moisture" || named(s, ["rain", "regen", "pluie"])));
    case "par":
      return sensor && (u.includes("µmol") || named(s, ["_par", " par", "ppfd"]));
    case "ec":
      return sensor && (dc === "conductivity" || u === "µs/cm" || u === "ms/cm");
    case "npk_n":
    case "npk_p":
    case "npk_k": // the unit alone cannot tell nitrogen from phosphorus: the name must
      return sensor && NPK_UNITS.includes(u) && named(s, NPK_WORDS[kind]);
    case "wind_speed":
    case "wind_gust": // gusts say so in their name
      return sensor && (dc === "wind_speed" || ["km/h", "m/s", "mph", "kn", "ft/s"].includes(u))
        && (kind === "wind_gust" ? named(s, ["gust", "stoot", "rafale"]) : !named(s, ["gust", "stoot", "rafale"]));
    case "radiation":
      return sensor && (dc === "irradiance" || u === "w/m²" || u === "w/m2");
    case "leaf_wetness":
      return (domain === "binary_sensor" && dc === "moisture") || (sensor && named(s, ["leaf", "blad", "feuille", "wetness"]));
  }
}

/** The entities that fit, sorted by their friendly name. */
export function fittingEntities(kind: EntityKind, states: Record<string, EntityLike> | undefined): EntityLike[] {
  return Object.values(states ?? {})
    .filter((s) => entityFits(kind, s))
    .sort((a, b) => entityLabel(a).localeCompare(entityLabel(b)));
}

export function entityLabel(s: EntityLike): string {
  const name = s.attributes.friendly_name ? String(s.attributes.friendly_name) : "";
  return name ? `${name} (${s.entity_id})` : s.entity_id;
}
