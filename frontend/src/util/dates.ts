// Day-month-year dates in the panel's language, independent of the browser's locale.

/** ``2026-04-13`` -> ``13-04-2026`` (nl) / ``13.04.2026`` (de) / ``13/04/2026`` (en). */
export function displayDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return y && m && d ? [d, m, y].join(lang === "nl" ? "-" : lang === "de" ? "." : "/") : iso;
}

/** Day-month-year (any separator, 2- or 4-digit year) or ISO -> ISO; ``undefined`` when unreadable. */
export function parseDate(text: string): string | null | undefined {
  const s = text.trim();
  if (!s) return null;
  let y: number, m: number, d: number;
  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(s);
  const dmy = /^(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{2}|\d{4})$/.exec(s);
  if (iso) [y, m, d] = [Number(iso[1]), Number(iso[2]), Number(iso[3])];
  else if (dmy) [d, m, y] = [Number(dmy[1]), Number(dmy[2]), Number(dmy[3].length === 2 ? `20${dmy[3]}` : dmy[3])];
  else return undefined;
  const date = new Date(Date.UTC(y, m - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return undefined;
  return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}
