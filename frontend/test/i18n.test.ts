import { test } from "node:test";
import assert from "node:assert/strict";
import { en } from "../src/i18n/en";
import { nl } from "../src/i18n/nl";
import { makeTranslator, normalizeLang } from "../src/i18n";

test("Dutch catalog covers every English key", () => {
  const missing = Object.keys(en).filter((k) => !(k in nl));
  assert.deepEqual(missing, []);
});

test("placeholders are identical in both languages", () => {
  const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
  for (const key of Object.keys(en)) assert.equal(ph(nl[key]), ph(en[key]), key);
});

test("translator interpolates and localises alert params", () => {
  const t = makeTranslator("nl-NL");
  assert.equal(normalizeLang("nl-BE"), "nl");
  assert.equal(t("alert.frost", { level: "high", temp: -2, when: "when.tonight" }), "Vorstrisico hoog: -2 °C verwacht vannacht");
  assert.equal(makeTranslator("es")("nav.planner"), "Planner");
  assert.equal(t("missing.key"), "missing.key");
});
