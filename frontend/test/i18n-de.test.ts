import { test } from "node:test";
import assert from "node:assert/strict";
import { en } from "../src/i18n/en";
import { de } from "../src/i18n/de";
import { makeTranslator, normalizeLang, tagLabel } from "../src/i18n";
import { familyName, localeOf } from "../src/util/garden";
import { displayDate, parseDate } from "../src/util/dates";

const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");

test("German catalog has exactly the English keys", () => {
  assert.deepEqual(Object.keys(en).filter((k) => !(k in de)), []);
  assert.deepEqual(Object.keys(de).filter((k) => !(k in en)), []);
});

test("German placeholders match English", () => {
  for (const key of Object.keys(en)) assert.equal(ph(de[key]), ph(en[key]), key);
});

test("German translator, tags, locale and dates", () => {
  assert.equal(normalizeLang("de-AT"), "de");
  assert.equal(normalizeLang("de_CH"), "de");
  assert.equal(normalizeLang("DE"), "de");
  const t = makeTranslator("de-DE");
  assert.equal(t("alert.frost", { level: "high", temp: -2, when: "when.tonight" }), "Frostrisiko hoch: -2 °C erwartet heute Nacht");
  assert.equal(tagLabel("aphids", "de"), "Blattläuse");
  assert.equal(tagLabel("aphids", "fr"), "pucerons");
  assert.equal(localeOf("de"), "de-DE");
  assert.equal(localeOf("fr"), "fr-BE");
  const fams = { solanaceae: { en: "Nightshades", nl: "Nachtschadefamilie", de: "Nachtschattengewächse", color: "#f00" } };
  assert.equal(familyName(fams, "solanaceae", "de"), "Nachtschattengewächse");
  assert.equal(familyName(fams, "unknown", "de"), undefined);
  assert.equal(displayDate("2026-04-13", "de"), "13.04.2026");
  assert.equal(parseDate("13.04.2026"), "2026-04-13");
});
