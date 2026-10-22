<!-- Generated from the sources by a script: code excerpts below are verbatim. -->
[← 4. Backend (Python)](04-backend-python.md) · [↑ Blueprint contents](../BLUEPRINT.md) · [6. Services, Entities, and Events →](06-services-entities-and-events.md)

## 5. Frontend (TypeScript)

Lit 3 + TypeScript, bundled by esbuild (`frontend/build.mjs`) into two ES modules in
`custom_components/garden_manager/frontend/`, both committed so HACS users need no Node.js (CI fails when
the committed bundles are out of date): the panel, served from
`/garden_manager_static/hortulus-panel.js?v=<sha256>`, and the Lovelace card `hortulus-card.js`, which the
integration adds to every dashboard by itself (no resource to register). `src/types.ts` mirrors
`engine/models.py` and the snapshot; `src/api.ts` wraps the websocket commands and adds the current
`garden_id` to each.

### 5.1 Root panel – subscription

```ts
private async connect(retried = false): Promise<void> {
  if (this.api && !this.api.gardenId && !retried) {
    try {
      this.api.gardenId = localStorage.getItem("hortulus.garden") ?? "";
    } catch {
      /* private mode */
    }
  }
  try {
    await this.loadPlants();
    void this.loadGlossary();
    this.unsubscribe = await this.api!.subscribe((snap) => {
      this.snapshot = snap;
      this.applyTheme();
      const lang = normalizeLang(snap.lang);
      if (lang !== this.uiLang) {
        this.uiLang = lang;
        this.t = makeTranslator(lang);
        void this.loadGlossary();
      }
      if (this.openTask) this.openTask = snap.tasks.find((t) => t.id === this.openTask!.id) ?? null;
    });
  } catch (err) {
    const notLoaded = (err as { code?: string }).code === "not_loaded";
    if (notLoaded && this.api?.gardenId && !retried) {
      // the remembered garden was removed: forget it and show the first garden instead
      this.api.gardenId = "";
      try {
        localStorage.removeItem("hortulus.garden");
      } catch {
        /* private mode */
      }
      await this.connect(true);
      return;
    }
    this.error = notLoaded ? this.t("common.not_loaded") : String((err as Error).message ?? err);
  }
}
```

### 5.2 Planner – palette drag & drop with live companion feedback

```ts
private onPalettePointerDown(ev: PointerEvent, plant: Plant): void {
  if (!this.admin || (ev.pointerType === "mouse" && ev.button !== 0)) return;
  (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
  this.paletteDrag = { plant, pointerId: ev.pointerId, bedId: null, rect: null };
  this.ghostReport = null;
  this.ghostSeq++;
}

private onPalettePointerMove(ev: PointerEvent): void {
  const drag = this.paletteDrag;
  if (!drag || drag.pointerId !== ev.pointerId) return;
  const pt = this.canvas.clientToCanvas(ev.clientX, ev.clientY);
  if (!pt) {
    this.paletteDrag = { ...drag, bedId: null, rect: null };
    return;
  }
  const bed = bedAt(this.draft.beds, pt.x, pt.y);
  if (!bed) {
    const size = { w: drag.plant.spacing_cm, h: drag.plant.spacing_cm };
    this.paletteDrag = { ...drag, bedId: null, rect: { x: pt.x - size.w / 2, y: pt.y - size.h / 2, ...size } };
    return;
  }
  const size = defaultFootprint(drag.plant, this.layoutMode, bed);
  const step = this.snapOn ? this.snapshot.settings.snap_cm : 1;
  let local = { x: snap(pt.x - bed.x_cm - size.w / 2, step), y: snap(pt.y - bed.y_cm - size.h / 2, step), ...size };
  if (this.layoutMode === "row") local = bed.width_cm >= bed.length_cm ? { ...local, x: 0 } : { ...local, y: 0 };
  local = clampInto(local, { x: 0, y: 0, w: bed.width_cm, h: bed.length_cm });
  this.paletteDrag = { ...drag, bedId: bed.id, rect: { ...local, x: local.x + bed.x_cm, y: local.y + bed.y_cm } };
  // Live companion feedback while hovering - throttled.
  const now = performance.now();
  if (now - this.ghostCheckAt > 220) {
    this.ghostCheckAt = now;
    const ghost = this.newPlanting(drag.plant, bed, local);
    ghost.id = "__ghost__";
    const seq = ++this.ghostSeq;
    this.api.checkBed(bed, [...this.bedPlantings(bed.id), ghost]).then((r) => {
      // a later check (another bed, a new drag) supersedes this one
      if (seq === this.ghostSeq && this.paletteDrag?.bedId === bed.id) this.ghostReport = r;
    }).catch(() => undefined);
  }
}

private onPalettePointerUp(ev: PointerEvent): void {
  const drag = this.paletteDrag;
  if (!drag || drag.pointerId !== ev.pointerId) return;
  this.paletteDrag = null;
  this.ghostReport = null;
  this.ghostSeq++;
  if (!drag.bedId || !drag.rect) {
    if (drag.rect) this.announce(this.t("planner.no_bed_here"));
    return;
  }
  const doc = clone(this.draft);
  const bed = doc.beds.find((b) => b.id === drag.bedId)!;
  const planting = this.newPlanting(drag.plant, bed, { ...drag.rect, x: drag.rect.x - bed.x_cm, y: drag.rect.y - bed.y_cm });
  doc.plantings.push(planting);
  this.selection = { kind: "planting", id: planting.id };
  this.commit(doc, this.t("planner.placed", { plant: plantName(drag.plant, this.lang), bed: bed.name }), [bed.id]);
  this.dropWarning = null;
  void this.checkDrop(planting);
}
```

### 5.3 Canvas – move / resize with snapping (pointer capture)

```ts
private onPointerMove(ev: PointerEvent): void {
  const d = this.drag;
  if (!d || d.pointerId !== ev.pointerId) return;
  if (Math.hypot(ev.clientX - d.clientX, ev.clientY - d.clientY) > 3) d.moved = true;
  if (d.mode === "pan") {
    this.tx = d.startTx + (ev.clientX - d.clientX);
    this.ty = d.startTy + (ev.clientY - d.clientY);
    return;
  }
  const pt = this.clientToCanvas(ev.clientX, ev.clientY);
  if (d.mode === "draw") {
    if (!pt) return;
    const step = this.snapOn ? this.snapStep : 1;
    const x2 = snap(pt.x, step);
    const y2 = snap(pt.y, step);
    this.drawRect = { x: Math.min(d.startX, x2), y: Math.min(d.startY, y2), w: Math.abs(x2 - d.startX), h: Math.abs(y2 - d.startY) };
    return;
  }
  if (!pt || !d.kind || !d.id) return;
  const dx = pt.x - d.startX;
  const dy = pt.y - d.startY;
  const step = this.snapOn ? this.snapStep : 1;
  let rect: Rect;
  if (d.mode === "move") {
    rect = { ...d.origin, x: d.origin.x + dx, y: d.origin.y + dy };
    if (d.kind === "planting") {
      // snap relative to the bed so rows line up with bed edges
      const bed = this.beds.find((b) => b.id === this.plantings.find((p) => p.id === d.id)?.bed_id);
      if (bed) {
        rect.x = bed.x_cm + snap(rect.x - bed.x_cm, step);
        rect.y = bed.y_cm + snap(rect.y - bed.y_cm, step);
      }
    } else {
      rect.x = snap(rect.x, step);
      rect.y = snap(rect.y, step);
    }
  } else {
    rect = { ...d.origin, w: Math.max(step, snap(d.origin.w + dx, step)), h: Math.max(step, snap(d.origin.h + dy, step)) };
    if (d.kind === "planting") {
      const bed = this.beds.find((b) => b.id === this.plantings.find((p) => p.id === d.id)?.bed_id);
      if (bed) rect = clampInto(rect, bedRect(bed));
    }
  }
  this.preview = { kind: d.kind, id: d.id, rect };
}
```

### 5.4 Undo/redo & autosave with revision guard

```ts
// Snapshot-based undo/redo. A "commit" happens once per finished gesture
// (drop, resize end, form change), never during pointer moves.

export class History<T> {
  private past: T[] = [];
  private future: T[] = [];

  constructor(private present: T, private readonly limit = 100) {}

  get current(): T {
    return this.present;
  }

  get canUndo(): boolean {
    return this.past.length > 0;
  }

  get canRedo(): boolean {
    return this.future.length > 0;
  }

  /** Record a new state; clears the redo stack. */
  commit(next: T): T {
    this.past.push(this.present);
    if (this.past.length > this.limit) this.past.shift();
    this.present = next;
    this.future = [];
    return next;
  }

  undo(): T {
    const prev = this.past.pop();
    if (prev === undefined) return this.present;
    this.future.push(this.present);
    this.present = prev;
    return prev;
  }

  redo(): T {
    const next = this.future.pop();
    if (next === undefined) return this.present;
    this.past.push(this.present);
    this.present = next;
    return next;
  }

  /** Replace everything (e.g. after a server reload). */
  reset(state: T): void {
    this.past = [];
    this.future = [];
    this.present = state;
  }
}
```

```ts
private scheduleSave(): void {
  window.clearTimeout(this.saveTimer);
  this.saveTimer = window.setTimeout(() => this.save(), 1200);
}

private saving = false;

private async save(): Promise<void> {
  if (this.saveState !== "dirty") return;
  // one request at a time: an edit made meanwhile is saved right after, on the new revision
  if (this.saving) return;
  const doc = this.draft;
  const garden = this.draftGarden;
  this.saving = true;
  this.saveState = "saving";
  try {
    const res = await this.api.savePlan(doc, this.baseRevision, this.season, garden || undefined);
    if (garden !== this.draftGarden) return; // another garden is shown meanwhile
    this.baseRevision = res.revision;
    this.saveState = this.draft === doc ? "saved" : "dirty";
  } catch (err) {
    if (garden !== this.draftGarden) {
      void this.saveDetached(doc, this.baseRevision, this.season, garden);
      return;
    }
    const code = (err as { code?: string }).code;
    if (code === "revision_conflict") {
      this.saveState = "saved";
      this.history = null;
      this.syncFromSnapshot();
      this.toast(this.t("common.conflict"));
    } else {
      this.saveState = "error";
      this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
    }
  } finally {
    this.saving = false;
    // also after an early return: an edit made meanwhile (in this or another garden) still goes out
    if (this.saveState === "dirty") void this.save();
  }
}

/** Edits of a garden no longer shown: saved to that garden, retried a few times, never lost silently. */
private async saveDetached(doc: PlanDoc, revision: number | null, season: number, garden: string, attempt = 1): Promise<void> {
  try {
    await this.api.savePlan(doc, revision, season, garden || undefined);
  } catch (err) {
    if ((err as { code?: string }).code !== "revision_conflict" && attempt < 3) {
      await new Promise((r) => window.setTimeout(r, 1500 * attempt));
      return this.saveDetached(doc, revision, season, garden, attempt + 1);
    }
    this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
  }
}

/** Switch the season shown: finish saving first, then load that season's garden plan. */
private async setSeason(season: number): Promise<void> {
  window.clearTimeout(this.saveTimer);
  if (this.saveState === "dirty") await this.save();
  if (this.saveState !== "saved") {
    // Saving failed or conflicted: stay on this season rather than drop the edits.
    this.toast(this.t("layout.save_first"));
    this.requestUpdate();
    return;
  }
  this.seasonChosen = true;
  this.season = season;
  this.dispatchEvent(new CustomEvent("season-changed", { detail: season, bubbles: true, composed: true }));
  this.selection = null;
  this.multi = [];
  this.focusZone = "";
  this.syncFromSnapshot(true);
  if (!this.plantStep && !this.draft.zones.length) this.step = this.draft.features.length ? "zones" : "site";
  requestAnimationFrame(() => this.canvas?.fit());
}

/** Start this season's garden plan as a copy of another season's (or empty). */
private startLayout(from: number | null): void {
  const src = from == null ? null : layoutOf(this.snapshot, from);
  const doc: PlanDoc = { ...clone(this.draft), zones: clone(src?.zones ?? []), beds: clone(src?.beds ?? []), features: clone(src?.features ?? []) };
  this.commit(doc, this.t("layout.started", { season: this.season }));
  this.step = doc.zones.length ? "beds" : "site";
  requestAnimationFrame(() => this.canvas?.fit());
}
```

### 5.5 Keyboard shortcuts (accessible drag‑and‑drop alternative)

```ts
private onKeyDown(ev: KeyboardEvent): void {
  const target = ev.composedPath()[0] as HTMLElement;
  if (["INPUT", "SELECT", "TEXTAREA"].includes(target?.tagName)) return;
  const mod = ev.ctrlKey || ev.metaKey;
  const step = (this.snapOn ? this.snapshot.settings.snap_cm : 1) * (ev.shiftKey ? 10 : 1);
  const key = ev.key;
  const handled = (): void => { ev.preventDefault(); ev.stopPropagation(); };
  if (mod && key.toLowerCase() === "z" && !ev.shiftKey) { this.undo(); return handled(); }
  if ((mod && key.toLowerCase() === "y") || (mod && ev.shiftKey && key.toLowerCase() === "z")) { this.redo(); return handled(); }
  if (mod && key.toLowerCase() === "d") { this.duplicateSelected(); return handled(); }
  if (mod) return;
  const arrows: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  if (arrows[key] && this.selection) { this.nudge(...arrows[key], ev.altKey); return handled(); }
  switch (key) {
    case "Delete":
    case "Backspace": this.removeSelected(); return handled();
    case "Enter": if (this.selection && this.findItem(this.selection)) this.popupOpen = true; return handled();
    case "Escape": this.selection = null; this.multi = []; this.paletteDrag = null; this.dialog = null; return handled();
    case "g": this.snapOn = !this.snapOn; return handled();
    case "c": this.showCompanions = !this.showCompanions; return handled();
    case "m": this.showMoisture = !this.showMoisture; return handled();
    case "t": this.showTemperature = !this.showTemperature; return handled();
    case "+": case "=": this.canvas.zoom(1.2); return handled();
    case "-": this.canvas.zoom(1 / 1.2); return handled();
    case "0": this.canvas.fit(); return handled();
    case "?": this.dialog = "shortcuts"; return handled();
    case "]": case "[": this.cycleSelection(key === "]" ? 1 : -1); return handled();
    default:
  }
}
```

### 5.6 Plant library – sowing calendar for *your* frost dates

```ts
export function renderPlantCalendar(plant: Plant, snapshot: Snapshot, lang: string, t: Translate): TemplateResult {
  const anchors = snapshot.analysis?.anchors ?? { last_frost: `${new Date().getFullYear()}-04-20`, first_frost: `${new Date().getFullYear()}-10-25` };
  const lf = anchors.last_frost;
  const start = snapshot.settings.region.hemisphere === "south" ? `${lf.slice(0, 4)}-07-01` : `${lf.slice(0, 4)}-01-01`;
  const pos = (iso: string) => Math.max(0, Math.min(100, (daysBetween(start, iso) / 365) * 100));
  const bars: TemplateResult[] = [];
  const add = (wins: Window[], top: number, color: string) => {
    for (const w of wins) {
      const [a, b] = windowDates(w, anchors);
      bars.push(html`<div class="b" style=${`left:${pos(a)}%;width:${Math.max(pos(b) - pos(a), 1)}%;top:${top}px;background:${color}`}></div>`);
    }
  };
  add(plant.sowing.indoor_sow, 2, "var(--hl-leaf-300)");
  add(plant.sowing.direct_sow, 8, "var(--hl-leaf-500)");
  add(plant.sowing.transplant, 14, "var(--hl-leaf-700)");
  const ground = [...plant.sowing.direct_sow, ...plant.sowing.transplant][0];
  if (ground && plant.harvestable) {
    const [a, b] = windowDates(ground, anchors);
    const offset = plant.maturity_from === "transplant" && !plant.sowing.transplant.length ? plant.germination_days[1] + 14 : 0;
    bars.push(html`<div class="b" style=${`left:${pos(addDays(a, plant.days_to_maturity[0] + offset))}%;width:${Math.max(
      pos(addDays(b, plant.days_to_maturity[1] + offset + plant.harvest_duration_days)) - pos(addDays(a, plant.days_to_maturity[0] + offset)), 1)}%;top:20px;background:var(--hl-sun-500)`}></div>`);
  }
  const months = Array.from({ length: 12 }, (_, i) => formatDate(addDays(start, Math.round(i * 30.5 + 10)), lang, { month: "narrow" }));
  return html`<div class="cal" role="img" aria-label=${t("lib.calendar")}>${months.map((m) => html`<div class="m">${m}</div>`)}${bars}</div>`;
}

import "./photo-timeline";
```

### 5.7 Task calendar – overdue tasks surface on today

```ts
private byDay(): Map<string, Task[]> {
  const map = new Map<string, Task[]>();
  for (const task of sortTasks(this.tasks)) {
    // Overdue open tasks are shown on today so nothing gets lost in the past.
    const day = task.status === "open" && task.due < this.today ? this.today : task.due;
    map.set(day, [...(map.get(day) ?? []), task]);
  }
  return map;
}
```

### 5.8 Design tokens (excerpt)

```ts
export const tokens = css`
  :host {
    /* -- brand palette ------------------------------------------------ */
    --hl-leaf-900: #1f3d1c;
    --hl-leaf-700: #2f5d2a;
    --hl-leaf-600: #3b7334;
    --hl-leaf-500: #4c8c3f;
    --hl-leaf-300: #9cc58a;
    --hl-leaf-100: #e4f0dc;
    --hl-leaf-50: #f3f8ef;
    --hl-soil-900: #2e2118;
    --hl-soil-700: #5a3f2b;
    --hl-soil-500: #8b6446;
    --hl-soil-300: #c4a587;
    --hl-soil-100: #efe4d6;
    --hl-sun-500: #e8a33d;
    --hl-sun-100: #fbefd9;
    --hl-tomato-600: #a8331f;
    --hl-tomato-500: #c8432f;
    --hl-tomato-100: #f8e1dc;
    --hl-frost-600: #2f6690;
    --hl-frost-500: #5b8db8;
    --hl-frost-100: #e1ecf5;
    --hl-water-500: #3a7ca5;
    --hl-water-ink: #2a5f86; /* text in water blue (AA on every light surface) */

    /* -- semantic (light) --------------------------------------------- */
    --hl-bg: #faf7f0;
    --hl-surface: #ffffff;
    --hl-surface-2: #f3efe6;
    --hl-surface-3: #e9e3d6;
    --hl-text: #22281f;
    --hl-text-muted: #5e6658;
    --hl-border: #e2dccd;
    --hl-primary: var(--hl-leaf-600);
    --hl-primary-hover: var(--hl-leaf-700);
    --hl-on-primary: #ffffff;
    --hl-accent: var(--hl-sun-500);
    --hl-danger: var(--hl-tomato-500);
    --hl-warning: #b26b00;
    --hl-info: var(--hl-frost-600);
    --hl-success: var(--hl-leaf-600);
    --hl-focus: #2f7dd1;
    --hl-canvas-bg: #f6f1e4;
    --hl-grid-line: rgba(90, 63, 43, 0.12);
    --hl-grid-line-strong: rgba(90, 63, 43, 0.25);
    --hl-bed-fill: #8b6446;
    --hl-bed-fill-raised: #7a5539;
    --hl-container-fill: #a07b5a;
    --hl-zone-outdoor: rgba(76, 140, 63, 0.08);
    --hl-zone-greenhouse: rgba(91, 141, 184, 0.12);
    /* … typography, spacing, radii, shadows, family colours … */
  }`;
```

### 5.9 Menu, views and components

Eight *places* (Today, Garden, Calendar, Weather, Journal, Cooking, Knowledge, Manage; the website adds a ninth, the read‑only view) with the related tabs of a place in a row underneath (a place reopens on the tab last
used; URLs of the tabs never changed):

| Place | Tabs (`src/views/`) |
|---|---|
| Today | `dashboard-view` (plus the wall screen `wall-view`, `/hortulus/wall`: a calm kiosk view with big tick‑boxes) |
| Garden | `planner-view` in two modes – *Garden plan* (`layout`: site, growing zones, beds) and *Planner* (`plant`: perennials, annuals) – and `crops-view` (+ `crops-planning`: sowing plan, seeds, succession, harvest forecast, timeline) |
| Calendar | `calendar-view` (month, year view, task dialog) |
| Weather | `weather-view` (now, 24 h chart, ten days, what it means for the garden, rain radar) with `climate-history` (daily chart for 30 / 90 / 365 days, periods against last year, records, every temperature sensor, months, measured frost dates) |
| Journal | `journal-view` sections: diary (photos per bed or crop), harvest (incl. harvest over the years), kitchen (ready to pick, surplus, cost and harvest), seeds, water, season report, system log (every change, with undo) |
| Kitchen | `cooking-view` (ideas, menus, own cookbook, shopping list, PDFs) |
| Knowledge | `library-view`, `advice-view`, `handbook-view` |
| Manage | `analysis-view` (check, why not?, errors, compare), `print-view`, `settings-view` |
| (website only) | `garden-viewer`: read‑only look at the plan, click for details, pick the year |

The planner works in five steps – site, growing zones, beds, perennials, annuals – and each item can only be
selected, moved and edited in its own step (the rest is dimmed and locked); a click selects, a second click
(or *Details*, or Enter) opens the details popup. Shared building blocks live in `src/components/`:
`hl-modal` (one popup everywhere: header, close, backdrop, Escape, arrow keys between neighbours),
`hl-plant-detail`, `hl-task-dialog` + task rows with swipe actions, `hl-year-transition`, `hl-plan-compare`,
`hl-season-report`, `hl-crop-gantt`, `hl-harvest-years`, `hl-quick-harvest`, `hl-quick-note`,
`hl-photo-timeline`, `hl-water-chart`, `hl-kitchen-economy`, `hl-dish-picture` and illustrations
(`chapter-art`, `garden-icons`, `plant-glyphs`). Visibility of tabs is decided by `panel.config.tabs`
(2.2). Entity pickers in the settings list only the entities that fit (`util/entities.ts`: valve, pump,
sensors, weather, TTS, speakers, notify services, vent, shade, water meter).

**Lovelace card** (`src/card/`, `custom:hortulus-tasks-card`): today's and overdue tasks with a tick box,
`days`, `assignee`, `max`, `water` and `garden` options, watering today, a run in progress, a valve left open
(with *Close*) and leaks; it reads the same snapshot subscription.

**Theme.** `styles/tokens.ts` holds the design tokens (5.8); `styles/palettes.ts` the four colour themes
(classic green, earth, night, follows the season) and `util/theme.ts` the choice plus *Light / dark /
automatic*. Themes and the dark palette are applied as inline colours on the panel element (no
`:host([theme])` rules, no `:host-context`: both fail in Safari / the iOS app); the choice is kept per
browser and, inside Home Assistant, in the user's data (`frontend/set_user_data`, key `hortulus_look`) so it
follows the user to every device. All motion is off with *reduce motion*.

**Pictures.** Every plant and handbook chapter has an illustration built from the plant glyph stickers (works
offline); on top, the browser may show a Wikipedia photo looked up by scientific name (CC BY, CC BY‑SA, CC0 or
public domain only, credited and linked, cached 30 days, switchable per browser).

**Planner internals worth knowing.** Saves go to the garden and season they were made for, one request at a
time, with the revision guard (5.4); `coverage.ts` mirrors `engine/coverage.py` so the map, the m² and the
print agree; companion and rotation feedback while dragging comes from `plan/check`; the crop timeline
(drag a planned crop sideways to move its sowing and planting out) and the *Why (not) here?* popup call the
planning and analysis commands.

Screens (English and Dutch, light and dark):

| | |
|---|---|
| ![Dashboard](../images/en/dashboard.png) | ![Planner](../images/en/planner.png) |
| ![Plant card](../images/en/library-plant.png) | ![Crop popup](../images/en/planner-crop.png) |
| ![Timeline](../images/en/calendar-timeline.png) | ![Settings](../images/en/settings.png) |

---

---

[← 4. Backend (Python)](04-backend-python.md) · [↑ Blueprint contents](../BLUEPRINT.md) · [6. Services, Entities, and Events →](06-services-entities-and-events.md)
