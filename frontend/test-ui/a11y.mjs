// Accessibility check (WCAG 2.1 AA, axe-core) of every tab of the real panel in the dev harness,
// in Dutch and English, light and dark.  Fails on serious and critical findings.
//
//   python frontend/dev/make_snapshot.py nl && python frontend/dev/make_snapshot.py en
//   npm run test:a11y          (PW_CHROMIUM=/path/to/chromium to use a local browser)
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = normalize(join(fileURLToPath(new URL(".", import.meta.url)), "..", ".."));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml" };
const AXE = await readFile(createRequire(import.meta.url).resolve("axe-core/axe.min.js"), "utf8");
const TABS = ["dashboard", "planner", "layout", "crops", "calendar", "weather", "analysis", "journal", "cooking", "advice", "library", "handbook", "print", "settings"];
const FAIL_ON = new Set(["serious", "critical"]);

const server = createServer(async (req, res) => {
  const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (path !== ROOT && !path.startsWith(ROOT.endsWith(sep) ? ROOT : ROOT + sep)) return res.writeHead(403).end();
  try {
    res.writeHead(200, { "content-type": TYPES[extname(path)] ?? "application/octet-stream" }).end(await readFile(path));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}/frontend/dev/index.html`;

const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
await page.route(/wikipedia|wikimedia/, (route) => route.abort());

const findings = new Map(); // rule|target -> finding
for (const [lang, dark] of [["nl", false], ["en", true]]) {
  for (const tab of TABS) {
    await page.goto(`${base}?tab=${tab}&lang=${lang}${dark ? "&dark=1" : ""}`);
    await page.locator("hortulus-panel").waitFor();
    await page.waitForTimeout(700);
    await page.addScriptTag({ content: AXE });
    const result = await page.evaluate(async () =>
      // eslint-disable-next-line no-undef
      axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] }, resultTypes: ["violations"] }));
    for (const v of result.violations) {
      for (const node of v.nodes) {
        const key = `${v.id}|${node.target.join(" > ")}`;
        if (!findings.has(key)) findings.set(key, { tab, lang, dark, id: v.id, impact: node.impact ?? v.impact, help: v.help, target: node.target.join(" > "), html: node.html.slice(0, 160), summary: (node.failureSummary ?? "").split("\n").slice(0, 3).join(" ") });
      }
    }
  }
}
await browser.close();
server.close();

const all = [...findings.values()];
const blocking = all.filter((f) => FAIL_ON.has(f.impact));
for (const f of all) {
  console.log(`${FAIL_ON.has(f.impact) ? "FAIL" : "warn"} [${f.impact}] ${f.id} · ${f.tab} (${f.lang}${f.dark ? ", dark" : ""}) · ${f.help}\n     ${f.target}\n     ${f.html}\n     ${f.summary}`);
}
console.log(`\n${all.length} findings, ${blocking.length} serious or critical`);
process.exit(blocking.length ? 1 : 0);
