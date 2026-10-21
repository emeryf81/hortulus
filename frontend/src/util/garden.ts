// Small pure helpers shared by the views (no Lit imports - unit testable).
import type { FamilyInfo, GardenLayout, Plant, Planting, Snapshot, Task, TaskType, Window } from "../types";

export const FAMILY_FALLBACK = "#7d7d7d";

export function familyColor(families: Record<string, FamilyInfo>, family: string | undefined): string {
  return (family && families[family]?.color) || FAMILY_FALLBACK;
}

/** Two-letter label drawn inside plantings so colour is never the only cue. */
export function plantMonogram(name: string): string {
  const clean = name.replace(/[^\p{L}\s]/gu, "").trim();
  const parts = clean.split(/\s+/);
  if (parts.length > 1) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (clean.slice(0, 2) || "?").replace(/^./, (c) => c.toUpperCase());
}

/** Family name in the UI language, falling back to English (catalog data has en/nl only). */
export function familyName(families: Record<string, FamilyInfo>, family: string, lang: string): string | undefined {
  const info = families[family] as (FamilyInfo & Record<string, string | undefined>) | undefined;
  return info?.[lang] ?? info?.en;
}

/** BCP-47 locale for Intl date/number formatting: Belgian for nl/fr, German for de, British English otherwise. */
export function localeOf(lang: string | null | undefined): string {
  const base = (lang ?? "en").toLowerCase().split(/[-_]/)[0];
  return base === "nl" ? "nl-BE" : base === "fr" ? "fr-BE" : base === "de" ? "de-DE" : "en-GB";
}

export function plantName(plant: Plant | undefined, lang: string): string {
  if (!plant) return "?";
  return plant.names[lang] || plant.names.en || plant.id;
}

export const TASK_ICONS: Record<TaskType, string> = {
  sow_indoor: "mdi:seed-outline",
  sow_direct: "mdi:seed",
  harden_off: "mdi:weather-partly-cloudy",
  transplant: "mdi:shovel",
  thin: "mdi:content-cut",
  stake: "mdi:pillar",
  prune: "mdi:scissors-cutting",
  pinch: "mdi:hand-back-left-outline",
  earth_up: "mdi:terrain",
  feed: "mdi:bottle-tonic-plus-outline",
  water: "mdi:watering-can",
  weed: "mdi:sprout-outline",
  pest_check: "mdi:bug-outline",
  harvest: "mdi:basket-outline",
  ventilate: "mdi:window-open-variant",
  shade: "mdi:sun-angle-outline",
  frost_protect: "mdi:snowflake-alert",
  soil_prep: "mdi:shovel",
  compost: "mdi:recycle",
  green_manure: "mdi:grass",
  mulch: "mdi:layers-outline",
  clean_greenhouse: "mdi:spray-bottle",
  winter_prep: "mdi:snowflake-variant",
  plan_season: "mdi:clipboard-text-outline",
  tool_care: "mdi:hammer-wrench",
  soil_test: "mdi:test-tube",
  cut_back: "mdi:content-cut",
  divide: "mdi:call-split",
  protect: "mdi:shield-sun-outline",
  clean: "mdi:broom",
  tie_in: "mdi:link-variant",
  thin_fruit: "mdi:fruit-cherries",
  pollinate: "mdi:bee-flower",
  check: "mdi:clipboard-check-outline",
  make_feed: "mdi:flask-outline",
  custom: "mdi:checkbox-marked-circle-outline",
};

export const TASK_COLORS: Partial<Record<TaskType, string>> = {
  sow_indoor: "var(--hl-leaf-500)",
  sow_direct: "var(--hl-leaf-500)",
  transplant: "var(--hl-leaf-700)",
  harvest: "var(--hl-sun-500)",
  water: "var(--hl-water-500)",
  frost_protect: "var(--hl-frost-500)",
  ventilate: "var(--hl-frost-500)",
  shade: "var(--hl-sun-500)",
  weed: "var(--hl-soil-500)",
  pest_check: "var(--hl-tomato-500)",
  soil_prep: "var(--hl-soil-500)",
  compost: "var(--hl-soil-700)",
  green_manure: "var(--hl-leaf-600)",
  mulch: "var(--hl-soil-500)",
  clean_greenhouse: "var(--hl-frost-500)",
  winter_prep: "var(--hl-frost-500)",
  plan_season: "var(--hl-leaf-700)",
  protect: "var(--hl-sun-500)",
  clean: "var(--hl-soil-500)",
  tie_in: "var(--hl-leaf-600)",
  thin_fruit: "var(--hl-tomato-500)",
  pollinate: "var(--hl-sun-500)",
  make_feed: "var(--hl-soil-700)",
};

// -- dates (all local, ISO yyyy-mm-dd) --------------------------------------
export const parseDate = (iso: string): Date => {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d, 12); // noon: immune to DST shifts
};

export const toIso = (date: Date): string =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export const addDays = (iso: string, days: number): string => {
  const d = parseDate(iso);
  d.setDate(d.getDate() + days);
  return toIso(d);
};

export const daysBetween = (a: string, b: string): number =>
  Math.round((parseDate(b).getTime() - parseDate(a).getTime()) / 86_400_000);

export function formatDate(iso: string | null | undefined, lang: string, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }): string {
  if (!iso) return "–";
  return parseDate(iso).toLocaleDateString(lang === "nl" ? "nl-NL" : localeOf(lang), opts);
}

/** Absolute date range of a relative window (weeks around a frost anchor). */
export function windowDates(win: Window, anchors: { last_frost: string; first_frost: string }): [string, string] {
  const base = win.anchor === "first_frost" ? anchors.first_frost : anchors.last_frost;
  const start = addDays(base, win.start_week * 7);
  const end = addDays(base, win.end_week * 7 + 6);
  return start <= end ? [start, end] : [end, start];
}

export function isActiveOn(planting: Planting, tl: { in_ground: string; harvest_end: string } | undefined, day: string): boolean {
  if (!tl) return true;
  if (planting.status === "failed" || planting.status === "finished") return false;
  return tl.in_ground <= day && day <= tl.harvest_end;
}

export function sortTasks(tasks: Task[]): Task[] {
  const rank = { urgent: 3, high: 2, normal: 1, low: 0 } as const;
  return [...tasks].sort((a, b) => (a.due === b.due ? rank[b.priority] - rank[a.priority] : a.due < b.due ? -1 : 1));
}

export function uid(prefix: string): string {
  const rnd = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2) + Date.now().toString(16);
  return `${prefix}_${rnd.replace(/-/g, "").slice(0, 10)}`;
}

export function download(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Perennials stay in the ground from their planting season until removed explicitly. */
/**
 * Is a planting part of ``season``?  Its own season plus every later season it was
 * explicitly carried into at a year-end transition (``last_season``) - perennials
 * included; nothing carries over by itself.  ``perennial`` is kept for callers.
 */
export function presentIn(p: Planting, _perennial: boolean, season: number): boolean {
  if (season < p.season) return false;
  if (p.removed_season != null && season >= p.removed_season) return false;
  return season <= (p.last_season ?? p.season);
}

/** The garden plan of a season: the live one, a stored one, or null when that year has none yet. */
export function layoutOf(snap: Snapshot, season: number): GardenLayout | null {
  if (snap.layout_season == null || season === snap.layout_season) {
    return { zones: snap.zones, beds: snap.beds, features: snap.features ?? [] };
  }
  return snap.layouts?.[String(season)] ?? null;
}

/** Which plant categories belong in a zone type (palette filter, autofill). */
export const ZONE_CATEGORIES: Record<string, string[]> = {
  outdoor: ["vegetable", "herb", "flower"],
  greenhouse: ["vegetable", "herb", "fruit"],
  cold_frame: ["vegetable", "herb"],
  orchard: ["fruit"],
  food_forest: ["fruit", "herb", "flower", "vegetable"],
  fruit: ["fruit"],
  herbs: ["herb", "flower"],
  flowers: ["flower", "herb"],
  garden: ["flower", "herb", "fruit"],
  containers: ["vegetable", "herb", "flower", "fruit"],
};
