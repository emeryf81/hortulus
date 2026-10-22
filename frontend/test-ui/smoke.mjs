// Click through the real panel in a browser (dev harness + engine-generated data):
// every tab renders without errors, popups open and close, links between tabs work.
//
//   python frontend/dev/make_snapshot.py nl && python frontend/dev/make_snapshot.py en
//   npm run test:ui            (PW_CHROMIUM=/path/to/chromium to use a local browser)
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { chromium } from "playwright";

const ROOT = normalize(join(fileURLToPath(new URL(".", import.meta.url)), "..", ".."));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml" };

const server = createServer(async (req, res) => {
  const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (path !== ROOT && !path.startsWith(ROOT.endsWith(sep) ? ROOT : ROOT + sep)) return res.writeHead(403).end();
  try {
    const body = await readFile(path);
    res.writeHead(200, { "content-type": TYPES[extname(path)] ?? "application/octet-stream" }).end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}/frontend/dev/index.html`;

const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
// Wikipedia photos are optional and unreachable in CI.
await page.route(/wikipedia|wikimedia/, (route) => route.abort());

const results = [];
async function step(name, fn) {
  const before = errors.length;
  try {
    await fn();
    assert.deepEqual(errors.slice(before), [], "page errors");
    results.push(["ok", name]);
  } catch (err) {
    results.push(["FAIL", name, err.message.split("\n")[0]]);
  }
}
const open = async (tab, lang = "nl") => {
  await page.goto(`${base}?tab=${tab}&lang=${lang}`);
  await page.locator("hortulus-panel").waitFor();
  // the tab's view has rendered (not just "loading")
  await page.waitForFunction(() => {
    const deep = (node) => [...(node.shadowRoot ? node.shadowRoot.childNodes : []), ...node.childNodes]
      .map((n) => (n.nodeType === 3 ? n.textContent : n.nodeType === 1 && !["STYLE", "SCRIPT"].includes(n.tagName) ? deep(n) : "")).join(" ");
    const view = document.querySelector("hortulus-panel")?.shadowRoot?.querySelector("main")?.firstElementChild;
    return !!view && view.tagName !== "P" && deep(view).trim().length > 20;
  });
};
const modal = () => page.locator("hl-modal");
// the popup's <dialog> lives in the top layer, the hl-modal host itself has no size
const modalOpen = () => page.locator("hl-modal dialog[open]").first().waitFor();
const modalTitle = () => modal().first().evaluate((m) => m.shadowRoot.querySelector("h2")?.textContent ?? "");

const TABS = ["dashboard", "layout", "planner", "crops", "library", "calendar", "weather", "journal", "cooking", "advice", "analysis", "handbook", "print", "settings"];
for (const lang of ["nl", "en"]) {
  for (const tab of TABS) {
    await step(`${lang}: ${tab} renders`, async () => {
      await open(tab, lang);
      const text = await page.locator("hortulus-panel").evaluate((el) => {
        // text of the tab, shadow roots included
        const deep = (node) => [...(node.shadowRoot ? node.shadowRoot.childNodes : []), ...node.childNodes]
          .map((n) => (n.nodeType === 3 ? n.textContent : n.nodeType === 1 && !["STYLE", "SCRIPT"].includes(n.tagName) ? deep(n) : "")).join(" ");
        return deep(el.shadowRoot.querySelector("main") ?? el);
      });
      assert.ok(text.trim().length > 20, "tab is empty");
    });
  }
}

await step("plants: popup, arrow keys, neighbour, close", async () => {
  await open("library");
  await page.locator("hl-library-view button.pcard").first().click();
  await modalOpen();
  const first = await modalTitle();
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction((was) => {
    const title = document.querySelector("hortulus-panel")?.shadowRoot?.querySelector("hl-library-view")
      ?.shadowRoot?.querySelector("hl-modal")?.shadowRoot?.querySelector("h2")?.textContent;
    return !!title && title !== was;
  }, first);
  await page.keyboard.press("Escape");
  await modal().first().waitFor({ state: "detached" });
});

await step("planner: crop popup and why-here", async () => {
  await open("planner");
  const label = page.locator("hl-garden-canvas text", { hasText: /Stamboon|Wortel|Sla/ }).first();
  await label.waitFor();
  const details = page.locator("hl-planner-view .step-tip button", { hasText: "Details" });
  const clickLabel = async () => {
    const box = await label.boundingBox(); // measured right before clicking: the plan may still be fitting itself
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  };
  for (let i = 0; i < 5 && !(await details.isVisible()); i++) {
    await clickLabel(); // one click picks the crop
    await details.waitFor({ timeout: 3000 }).catch(() => {});
  }
  await details.waitFor();
  await page.waitForTimeout(600); // well past a double click: clicking the selected crop again still opens it
  await clickLabel(); // a second click opens it
  await modalOpen();
  await page.locator("hl-modal button", { hasText: "Waarom (niet) hier?" }).click();
  await page.locator("hl-planner-view .why").waitFor();
});

await step("planner: five steps, each step edits only its own kind", async () => {
  await open("layout");
  const steps = page.locator("hl-planner-view nav.stepper button.step");
  assert.equal(await steps.count(), 5);
  await steps.nth(0).click(); // terrain
  const layers = () => page.locator("hl-garden-canvas").evaluate((c) => ({
    kind: c.editKind,
    editable: c.shadowRoot.querySelectorAll("g.editable").length,
    locked: c.shadowRoot.querySelectorAll("g.locked").length,
  }));
  let l = await layers();
  assert.equal(l.kind, "feature");
  assert.ok(l.editable > 0 && l.locked > 0, JSON.stringify(l)); // elements pickable, zones and beds locked
  // an element picked on the terrain moves with the arrow keys
  const el = page.locator("hl-garden-canvas g.editable").first();
  const b0 = await el.boundingBox();
  await page.mouse.click(b0.x + b0.width / 2, b0.y + b0.height / 2);
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction((x0) => {
    const g = document.querySelector("hortulus-panel").shadowRoot.querySelector("hl-planner-view").shadowRoot
      .querySelector("hl-garden-canvas").shadowRoot.querySelector("g.editable");
    return g && g.getBoundingClientRect().x > x0;
  }, b0.x);
  await steps.nth(1).click();
  assert.equal((await layers()).kind, "zone");
  await steps.nth(2).click();
  assert.equal((await layers()).kind, "bed");
  await steps.nth(4).click(); // annuals: on to the planner tab
  await page.waitForFunction(() => document.querySelector("hortulus-panel").shadowRoot.querySelector("hl-planner-view")?.getAttribute("mode") === "plant");
  l = await layers();
  assert.equal(l.kind, "planting");
  // the "more" menu stays on the row of the other action buttons
  const tops = await page.locator("hl-planner-view").evaluate((v) => {
    const r = v.shadowRoot;
    return [r.querySelector(".toolbar details.more").getBoundingClientRect().top, r.querySelector(".toolbar .actions .btn").getBoundingClientRect().top];
  });
  assert.ok(Math.abs(tops[0] - tops[1]) < 12, `more menu on its own line: ${tops}`);
  // back from the planner tab to the terrain: lands on the terrain step, not on the beds
  await steps.nth(0).click();
  await page.waitForFunction(() => document.querySelector("hortulus-panel").shadowRoot.querySelector("hl-planner-view")?.getAttribute("mode") !== "plant");
  await page.waitForFunction(() => document.querySelector("hortulus-panel").shadowRoot.querySelector("hl-planner-view")?.shadowRoot.querySelector("hl-garden-canvas")?.editKind === "feature");
});

await step("year transition: keep everything, or tick per element, zone and perennial", async () => {
  await open("planner");
  await page.locator("hl-planner-view .toolbar button", { hasText: "Jaarovergang" }).click();
  const yt = page.locator("hl-year-transition");
  await yt.locator("text=Alles meenemen").waitFor();
  assert.equal(await yt.locator("input[name=keep]").first().isChecked(), true);
  assert.equal(await yt.locator("label.item").count(), 0); // no tick lists while keeping everything
  await yt.locator("text=Zelf kiezen").click();
  await yt.locator("label.item").first().waitFor();
  const toggle = yt.locator("button", { hasText: "Niets aanvinken" }).first();
  await toggle.click();
  await yt.locator("button", { hasText: "Alles aanvinken" }).first().waitFor();
});

await step("crops: bulk edit bar and show on map", async () => {
  await open("crops");
  const boxes = page.locator("hl-crops-view tbody input[type=checkbox]");
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  await page.locator("hl-crops-view .bulk").waitFor();
  const date = await page.locator("hl-crops-view hl-date-input").first().evaluate((el) => el.shadowRoot.querySelector("input").placeholder);
  assert.equal(date, "dd-mm-jjjj");
  await page.locator("hl-crops-view button.map").first().click();
  await page.locator("hl-planner-view").waitFor();
  await modalOpen();
});

await step("analysis: badge, repairs, compare", async () => {
  await open("analysis");
  const badge = await page.locator("hortulus-panel").evaluate((el) => el.shadowRoot.querySelector("nav a .badge")?.textContent ?? "");
  assert.match(badge, /^\d+$/);
  await page.locator("button[role=tab]", { hasText: "Vergelijken" }).click();
  await page.locator("hl-plan-compare").waitFor();
});

await step("plant popup from the dashboard", async () => {
  await open("dashboard");
  const avatar = page.locator("hl-dashboard-view button.avatar").first();
  await avatar.scrollIntoViewIfNeeded();
  await avatar.click();
  await page.locator("hortulus-panel hl-plant-detail").waitFor();
});

await step("journal: date field works inside a form", async () => {
  await open("journal");
  await page.locator("hl-journal-view button[role=tab]", { hasText: "Oogst" }).click();
  const value = await page.locator("hl-journal-view hl-date-input[name=day]").first().evaluate((el) => {
    const form = el.closest("form");
    return form ? form.elements.namedItem("day").value : "no form";
  });
  assert.match(value, /^\d{4}-\d{2}-\d{2}$/);
});

await step("crops: sowing plan, seeds, succession, harvest", async () => {
  await open("crops");
  for (const label of ["Zaaiplan", "Zaden", "Opvolgteelt", "Oogstverwachting"]) {
    await page.locator("hl-crops-view .views button", { hasText: label }).click();
    await page.locator("hl-crops-planning section.card").first().waitFor();
  }
});

await step("journal: watering per bed and season report", async () => {
  await open("journal");
  await page.locator("hl-journal-view button[role=tab]", { hasText: "Water" }).click();
  await page.locator("hl-water-chart svg").first().waitFor();
  await page.locator("hl-journal-view button[role=tab]", { hasText: "Seizoensrapport" }).click();
  await page.locator("hl-season-report .tiles").waitFor();
});

await step("journal: kitchen, harvest value and an expense", async () => {
  await open("journal");
  await page.locator("hl-journal-view button[role=tab]", { hasText: "Keuken" }).click();
  const kitchen = page.locator("hl-kitchen-economy");
  await kitchen.locator(".money").waitFor();
  await kitchen.locator("input[name=amount]").fill("12.50");
  await kitchen.locator("form button[type=submit]").click();
  const sent = await page.evaluate(() => window.__calls.find((c) => c.type.endsWith("/records/expense/save")));
  assert.equal(sent?.expense?.amount, 12.5);
});

await step("cooking: a dish from the garden, another side, kept, on the list, printed", async () => {
  await page.evaluate(() => localStorage.clear());
  await open("cooking");
  const view = page.locator("hl-cooking-view");
  const chapters = await view.locator(".chapter:not(.menus) h3.chapter-title").allInnerTexts();
  assert.ok(chapters[0].startsWith("Soepen") && chapters.some((c) => c.startsWith("Desserten")), `chapters: ${chapters}`);
  await view.locator(".chapter:not(.menus)", { hasText: "Hoofdgerechten" }).locator("button.recipe").first().click();
  await modalOpen();
  await view.locator("hl-modal select#side").selectOption("bulgur");
  await page.waitForFunction(() => window.__calls.some((c) => c.type.endsWith("/cooking/render") && c.spec.side === "bulgur"));
  await view.locator("hl-modal button", { hasText: "Bewaar in mijn kookboek" }).click();
  await page.waitForFunction(() => window.__calls.some((c) => c.type.endsWith("/cooking/book/save")));
  await view.locator("hl-modal button", { hasText: "Op boodschappenlijst" }).click();
  await page.keyboard.press("Escape");
  await view.locator("button[role=tab]", { hasText: "Boodschappenlijst" }).click();
  await view.locator("table tr").first().waitFor();
  assert.ok((await view.locator("table tr").count()) > 2, "shopping list is empty");
  await view.locator("button:has(ha-icon[icon=\"mdi:file-pdf-box\"])").first().click();
  await page.waitForFunction(() => window.__calls.some((c) => c.type.endsWith("/cooking/pdf") && c.kind === "shopping"));
});

await step("cooking: complete menus and the preserving chapter", async () => {
  await page.evaluate(() => localStorage.clear());
  await open("cooking");
  const view = page.locator("hl-cooking-view");
  const menu = view.locator("section.menus article.menu").first();
  await menu.waitFor();
  assert.equal(await menu.locator(".menu-courses li").count(), 3, "a menu has three courses");
  const chapters = await view.locator(".chapter:not(.menus) h3.chapter-title").allInnerTexts();
  assert.ok(chapters.some((c) => c.startsWith("Bewaren")), `chapters: ${chapters}`);
  await menu.locator("button.linklike").first().click();
  await modalOpen();
  await page.keyboard.press("Escape");
  await menu.locator("button", { hasText: "Alles op de boodschappenlijst" }).click();
  await view.locator("button[role=tab]", { hasText: "Boodschappenlijst" }).click();
  await view.locator(".basket-item").first().waitFor();
  assert.equal(await view.locator(".basket-item").count(), 3, "the three dishes of the menu are on the list");
});

await step("cooking: the cook's own version (ingredients and steps by hand)", async () => {
  await open("cooking");
  const view = page.locator("hl-cooking-view");
  await view.locator("button[role=tab]", { hasText: "Mijn kookboek" }).click();
  await view.locator("button.recipe").first().click();
  await modalOpen();
  await view.locator("hl-modal button", { hasText: "Aanpassen" }).click();
  const before = await view.locator("hl-modal .ed-ingr").count();
  await view.locator("hl-modal .ed-ingr").first().locator("button").click();
  await view.locator("hl-modal button", { hasText: "Ingrediënt toevoegen" }).click();
  await view.locator("hl-modal .ed-ingr").last().locator("input[type=text]").fill("Gerookte paprika");
  await view.locator("hl-modal button", { hasText: "Stap toevoegen" }).click();
  await view.locator("hl-modal .ed-step textarea").last().fill("Bestrooi met gerookte paprika.");
  await view.locator("hl-modal button", { hasText: "Mijn versie bewaren" }).click();
  await page.waitForFunction(() => window.__calls.some((c) => c.type.endsWith("/cooking/book/update") && c.changes.steps?.includes("Bestrooi met gerookte paprika.")));
  const sent = await page.evaluate(() => window.__calls.filter((c) => c.type.endsWith("/cooking/book/update")).pop().changes.ingredients);
  assert.equal(sent.length, before, "one ingredient removed, one added");
  assert.ok(sent.some((i) => i.name === "Gerookte paprika"), "the new ingredient was not sent");
  await view.locator("hl-modal .chip", { hasText: "Eigen versie" }).waitFor();
  assert.ok(await view.locator("hl-modal ol.steps li", { hasText: "gerookte paprika" }).count(), "own step not shown");
  await page.keyboard.press("Escape");
});

await step("weather: climate history, periods against last year, every temperature sensor", async () => {
  await open("weather");
  const history = page.locator("hl-climate-history");
  await history.locator(".tiles").first().waitFor();
  assert.ok((await history.locator(".tile").count()) >= 20, "period tiles missing");
  assert.equal(await history.locator("table tbody tr", { hasText: "sensor.greenhouse_temp" }).count(), 1);
  await history.locator("button[role=tab]", { hasText: "1 jaar" }).click();
  await page.waitForFunction(() => document.querySelector("hortulus-panel")?.shadowRoot?.querySelector("hl-weather-view")
    ?.shadowRoot?.querySelector("hl-climate-history")?.shadowRoot?.querySelector("button[aria-selected=true]")?.textContent?.includes("1 jaar"));
  assert.ok(await page.evaluate(() => window.__calls.some((c) => c.type.endsWith("/climate/stats"))));
});

await step("colour theme and light/dark go on as inline colours (also Safari / iPhone)", async () => {
  await open("settings");
  const view = page.locator("hl-settings-view");
  await view.locator("button.theme-opt", { hasText: "Aarde" }).click();
  const prop = (name) => page.locator("hortulus-panel").evaluate((el, n) => el.style.getPropertyValue(n), name);
  assert.equal((await prop("--hl-primary")).trim(), "#8a4f2a", "earth palette not applied");
  await view.locator("button.btn[role=radio]", { hasText: /^Donker$/ }).click();
  assert.equal((await prop("--hl-bg")).trim(), "#17120e", "dark earth palette not applied");
  await view.locator("button.btn[role=radio]", { hasText: /^Automatisch$/ }).click();
  await view.locator("button.theme-opt", { hasText: "Klassiek groen" }).click();
  assert.equal(await prop("--hl-primary"), "", "classic should leave the base palette");
});

await step("dashboard: pest calendar card", async () => {
  await open("dashboard");
  const n = await page.locator("hl-dashboard-view").evaluate((el) => el.shadowRoot.querySelectorAll(".pests li").length);
  assert.ok(n > 0, "no pest warnings shown");
});

await step("menu: eight places, the garden's tabs underneath", async () => {
  await open("crops");
  const top = await page.locator("hortulus-panel").evaluate((el) => el.shadowRoot.querySelectorAll("nav.top a").length);
  assert.equal(top, 8);
  await page.locator("hortulus-panel nav.sub a", { hasText: "Tuinplan" }).click();
  await page.locator("hl-planner-view").waitFor();
  await page.locator("hortulus-panel nav.top a", { hasText: "Weer" }).click();
  await page.locator("hl-weather-view .day").first().waitFor();
  const days = await page.locator("hl-weather-view .day").count();
  assert.ok(days >= 7, `only ${days} days`);
});

await step("crops timeline: a bar per crop, bed by bed", async () => {
  await open("crops");
  await page.locator("hl-crops-view .views button", { hasText: "Tijdlijn" }).click();
  await page.locator("hl-crop-gantt .bar").first().waitFor();
  assert.ok((await page.locator("hl-crop-gantt .bar").count()) > 5);
});

await step("settings: drop-downs list only entities that fit", async () => {
  await open("settings");
  const view = page.locator("hl-settings-view");
  const opts = async (id) => view.locator(`select#${id} option`).evaluateAll((os) => os.map((o) => o.value).filter(Boolean));
  assert.deepEqual(await opts("w"), ["weather.home"]);
  assert.deepEqual(await opts("tts"), ["tts.google_nl"]);
  const pump = await opts("pump");
  assert.ok(pump.includes("valve.bed_1") && !pump.includes("light.porch") && !pump.some((x) => x.startsWith("sensor.")), pump.join());
  assert.ok((await view.locator("fieldset.picks input[type=checkbox]").count()) >= 2, "notify / speaker tick-boxes");
});

await step("shared view: only the tabs the owner shows", async () => {
  await page.goto(`${base}?tab=journal&lang=nl&tabs=dashboard,planner,layout,crops,library,handbook`);
  await page.locator("hl-dashboard-view").waitFor(); // a tab that is not shown falls back to Today
  const places = await page.locator("hortulus-panel").evaluate((el) => [...el.shadowRoot.querySelectorAll("nav.side a, nav.bottom a, nav a")].map((a) => a.textContent.trim()));
  assert.ok(!places.some((t) => /Logboek|Kalender|Weer|Beheer/.test(t)), places.join("|"));
  assert.ok(places.some((t) => /Tuin/.test(t)), places.join("|"));
  // without Today in the list, a tab that is not shown falls back to the first one that is
  await page.goto(`${base}?tab=journal&lang=nl&tabs=planner,crops`);
  await page.locator("hl-planner-view").waitFor();
  // an empty list shows no part of the garden, not even Today
  await page.goto(`${base}?tab=dashboard&lang=nl&tabs=`);
  await page.locator("hortulus-panel main .empty").waitFor();
  assert.equal(await page.locator("hl-dashboard-view").count(), 0);
});

await step("visitor without account: only the plan, clickable, with a year choice", async () => {
  await page.goto(`${base}?lang=nl&tabs=view`);
  const viewer = page.locator("hl-garden-viewer");
  await viewer.locator("hl-garden-canvas").waitFor();
  assert.equal(await page.locator("hortulus-panel").evaluate((el) => el.shadowRoot.querySelectorAll("nav a").length), 0);
  assert.ok((await viewer.locator("select option").count()) >= 1, "no year to choose");
  const box = await viewer.locator("hl-garden-canvas").boundingBox();
  await page.mouse.click(box.x + 260, box.y + 340);
  await viewer.locator("aside h3").waitFor();
});

await step("wall screen: clock and big tick-boxes, back to Today", async () => {
  await page.goto(`${base}?tab=wall&lang=nl`);
  await page.locator("hl-wall-view .clock").waitFor();
  assert.ok((await page.locator("hl-wall-view .tick").count()) > 0, "no tasks on the wall");
  await page.locator("hl-wall-view .exit").click();
  await page.locator("hl-dashboard-view").waitFor();
});

await step("crops on a phone: one card per crop", async () => {
  await page.setViewportSize({ width: 400, height: 860 });
  await open("crops");
  await page.locator("hl-crops-view .crop-card").first().waitFor();
  await page.setViewportSize({ width: 1400, height: 1000 });
});

await browser.close();
server.close();
for (const r of results) console.log(r.join("  "));
const failed = results.filter((r) => r[0] === "FAIL");
console.log(`\n${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
