import { en } from "./en";
import { nl } from "./nl";
import { fr } from "./fr";
import { de } from "./de";

const CATALOGS: Record<string, Record<string, string>> = { en, nl, fr, de };

export type Translate = (key: string, params?: Record<string, unknown>) => string;

export type Lang = "en" | "nl" | "fr" | "de";

export const normalizeLang = (lang?: string | null): Lang => {
  const base = (lang ?? "en").toLowerCase().split(/[-_]/)[0];
  return base === "nl" ? "nl" : base === "fr" ? "fr" : base === "de" ? "de" : "en";
};

/** Build a translator. Unknown keys fall back to English, then to the key. */
export function makeTranslator(lang: string): Translate {
  const catalog = CATALOGS[normalizeLang(lang)];
  return (key, params = {}) => {
    const template = catalog[key] ?? en[key] ?? key;
    return template.replace(/\{(\w+)\}/g, (_m, name: string) => {
      const value = params[name];
      if (value === undefined || value === null) return `{${name}}`;
      if (key.startsWith("alert.") && name === "level") return catalog[`risk.${value}`] ?? String(value);
      if (key.startsWith("alert.") && name === "when") return catalog[String(value)] ?? String(value);
      return Array.isArray(value) ? value.join(", ") : String(value);
    });
  };
}

/** Humanise tags like "red_spider_mite" when no translation exists. */
export const humanize = (tag: string): string => tag.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export const PEST_NL: Record<string, string> = {
  aphids: "bladluis", whitefly: "witte vlieg", red_spider_mite: "spint", thrips: "trips", slugs: "slakken",
  cabbage_white: "koolwitje", cabbage_root_fly: "koolvlieg", flea_beetle: "aardvlo", carrot_fly: "wortelvlieg",
  onion_fly: "uienvlieg", leek_moth: "preimot", pea_moth: "erwtenbladroller", birds: "vogels", pigeons: "duiven",
  black_bean_aphid: "zwarte bonenluis", bean_weevil: "bonenkever", leaf_miner: "bladmineerder",
  late_blight: "phytophthora", early_blight: "alternaria (vroeg)", blossom_end_rot: "neusrot", botrytis: "grauwe schimmel",
  powdery_mildew: "echte meeldauw", downy_mildew: "valse meeldauw", cucumber_mosaic_virus: "komkommermozaïekvirus",
  clubroot: "knolvoet", white_rot: "witrot", rust: "roest", alternaria: "alternaria", leaf_spot: "bladvlekken",
  root_rot: "wortelrot", anthracnose: "vlekkenziekte", halo_blight: "vetvlekkenziekte", chocolate_spot: "chocoladevlekken",
  damping_off: "kiemplantenziekte", ants: "mieren", asparagus_beetle: "aspergekever", canker: "kanker", celery_fly: "selderijvlieg",
  colorado_beetle: "coloradokever", nematodes: "aaltjes", scab: "schurft", smut: "builenbrand", verticillium_wilt: "verwelkingsziekte",
  wireworm: "ritnaald",
};

export const PEST_FR: Record<string, string> = {
  aphids: "pucerons", whitefly: "aleurodes", red_spider_mite: "acariens (araignée rouge)", thrips: "thrips", slugs: "limaces",
  cabbage_white: "piéride du chou", cabbage_root_fly: "mouche du chou", flea_beetle: "altises", carrot_fly: "mouche de la carotte",
  onion_fly: "mouche de l'oignon", leek_moth: "teigne du poireau", pea_moth: "tordeuse du pois", birds: "oiseaux", pigeons: "pigeons",
  black_bean_aphid: "puceron noir de la fève", bean_weevil: "bruche du haricot", leaf_miner: "mineuse",
  late_blight: "mildiou (phytophthora)", early_blight: "alternariose (précoce)", blossom_end_rot: "nécrose apicale", botrytis: "pourriture grise",
  powdery_mildew: "oïdium", downy_mildew: "mildiou", cucumber_mosaic_virus: "virus de la mosaïque du concombre",
  clubroot: "hernie du chou", white_rot: "pourriture blanche", rust: "rouille", alternaria: "alternariose", leaf_spot: "taches foliaires",
  root_rot: "pourriture des racines", anthracnose: "anthracnose", halo_blight: "graisse du haricot", chocolate_spot: "taches chocolat",
  damping_off: "fonte des semis", ants: "fourmis", asparagus_beetle: "criocère de l'asperge", canker: "chancre", celery_fly: "mouche du céleri",
  colorado_beetle: "doryphore", nematodes: "nématodes", scab: "gale", smut: "charbon", verticillium_wilt: "verticilliose",
  wireworm: "taupin (ver fil de fer)",
};

export const PEST_DE: Record<string, string> = {
  aphids: "Blattläuse", whitefly: "Weiße Fliege", red_spider_mite: "Spinnmilben (Rote Spinne)", thrips: "Thripse", slugs: "Schnecken",
  cabbage_white: "Kohlweißling", cabbage_root_fly: "Kohlfliege", flea_beetle: "Erdflöhe", carrot_fly: "Möhrenfliege",
  onion_fly: "Zwiebelfliege", leek_moth: "Lauchmotte", pea_moth: "Erbsenwickler", birds: "Vögel", pigeons: "Tauben",
  black_bean_aphid: "Schwarze Bohnenlaus", bean_weevil: "Bohnenkäfer", leaf_miner: "Minierfliege",
  late_blight: "Kraut- und Braunfäule", early_blight: "Dürrfleckenkrankheit (früh)", blossom_end_rot: "Blütenendfäule", botrytis: "Grauschimmel",
  powdery_mildew: "Echter Mehltau", downy_mildew: "Falscher Mehltau", cucumber_mosaic_virus: "Gurkenmosaikvirus",
  clubroot: "Kohlhernie", white_rot: "Mehlkrankheit", rust: "Rost", alternaria: "Alternaria", leaf_spot: "Blattflecken",
  root_rot: "Wurzelfäule", anthracnose: "Brennfleckenkrankheit", halo_blight: "Fettfleckenkrankheit", chocolate_spot: "Schokoladenfleckenkrankheit",
  damping_off: "Umfallkrankheit", ants: "Ameisen", asparagus_beetle: "Spargelhähnchen", canker: "Krebs", celery_fly: "Selleriefliege",
  colorado_beetle: "Kartoffelkäfer", nematodes: "Nematoden", scab: "Schorf", smut: "Brand", verticillium_wilt: "Verticillium-Welke",
  wireworm: "Drahtwurm",
};

const PEST_BY_LANG: Partial<Record<Lang, Record<string, string>>> = { nl: PEST_NL, fr: PEST_FR, de: PEST_DE };

export const tagLabel = (tag: string, lang: string): string => PEST_BY_LANG[normalizeLang(lang)]?.[tag] ?? humanize(tag);
