/**
 * Wall screen (kiosk): one calm, large screen for a tablet in the kitchen or
 * the shed. It is a grid of blocks - the time, the weather, today's garden
 * tasks with big tick-boxes, the beds' moisture and, in Dutch, much more: the
 * rain radar, the agenda, a weather saying, a recipe tip, an organic gardening
 * fact ... The gardener picks the blocks, drags them in order and sets their
 * width; everything fits on one screen. No menus; it dims at night.
 *
 * The layout is kept in the garden's settings (wall/layout), so every screen
 * shows the same wall. Arranging it is Dutch only for now: in other languages
 * the wall keeps its default blocks.
 */
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import { shared } from "../styles/tokens";
import type { FamilyInfo, HomeAssistant, Plant, Snapshot, Task, WallBlock, WallData } from "../types";
import { celebrateAt } from "../util/celebrate";
import { familyColor, formatDate, sortTasks, localeOf } from "../util/garden";
import { weatherGlyph } from "./weather-view";

/** The default wall, also the only wall outside Dutch (same as wall.py DEFAULT_LAYOUT). */
const DEFAULT_LAYOUT: WallBlock[] = [
  { id: "clock", w: 2 }, { id: "weather_now", w: 2 }, { id: "tasks", w: 2 }, { id: "forecast", w: 2 }, { id: "moisture", w: 2 },
];

/** The blocks' names and what they show (Dutch: arranging the wall is Dutch only for now). */
const NL: Record<string, { name: string; about: string }> = {
  clock: { name: "Klok en datum", about: "De tijd, de datum en de naam van je tuin" },
  weather_now: { name: "Weer nu", about: "Temperatuur en weertype van dit moment" },
  forecast: { name: "Weersverwachting", about: "De komende dagen: hoogste en laagste temperatuur en regen" },
  radar: { name: "Buienradar", about: "De regenradar van Nederland en België" },
  tasks: { name: "Taken van vandaag", about: "Met grote vinkjes om af te vinken" },
  agenda: { name: "Agenda", about: "De taken van de komende zeven dagen, per dag" },
  moisture: { name: "Bodemvocht", about: "Hoe vochtig elk bed is (bedden met een vochtsensor)" },
  watering: { name: "Bewatering", about: "Of er nu water gegeven wordt, of waarom niet" },
  harvest_ready: { name: "Oogstklaar", about: "Wat je nu kunt oogsten" },
  sow_week: { name: "Zaaien en planten", about: "Wat deze week gezaaid of uitgeplant mag worden" },
  pests: { name: "Plagen", about: "Welke plagen nu of binnenkort actief zijn, met een biologische tip" },
  garden: { name: "Je tuin", about: "Bedden, teelten in de grond en de oogst van dit jaar" },
  sun: { name: "Zon", about: "Zonsopgang en zonsondergang" },
  saying: { name: "Weerspreuk", about: "Een oude weerspreuk voor deze maand" },
  fact: { name: "Weetje", about: "Elke dag een weetje over biologisch tuinieren" },
  eco_month: { name: "Biologische tip van de maand", about: "Wat je deze maand voor bodem en biodiversiteit kunt doen" },
  recipe: { name: "Recepttip", about: "Een recept met wat je tuin nu geeft" },
  slogan: { name: "Tuinspreuk", about: "Een wisselende tuinspreuk" },
};
const SOW_TYPES = new Set(["sow_indoor", "sow_direct", "transplant", "harden_off"]);

@customElement("hl-wall-view")
export class WallView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) api?: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property({ attribute: false }) plants = new Map<string, Plant>();
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property() lang = "en";
  @property({ type: Boolean }) admin = false;
  @state() private now = new Date();
  @state() private data: WallData | null = null;
  @state() private editing = false;
  @state() private draft: WallBlock[] | null = null;
  @state() private dragIndex: number | null = null;
  @state() private radarTick = Date.now();
  @state() private radarFailed = false;
  @state() private saveError = "";
  private timer?: number;
  private dataTimer?: number;

  static styles = [
    shared,
    css`
      :host { display: flex; flex-direction: column; height: 100vh; padding: 22px 28px; box-sizing: border-box; color: var(--hl-text); overflow: hidden;
        background: radial-gradient(900px 500px at 0% 0%, color-mix(in srgb, var(--hl-leaf-100) 80%, transparent), transparent 70%), var(--hl-bg); }
      :host([night]) { filter: brightness(0.78) saturate(0.85); }
      :host([editing]) { overflow: auto; height: auto; min-height: 100vh; padding-top: 60px; }
      .bar { position: fixed; top: 10px; right: 12px; display: flex; gap: 6px; z-index: 3; }
      .bar .btn { opacity: 0.4; }
      .bar .btn:hover, .bar .btn:focus-visible, :host([editing]) .bar .btn { opacity: 1; }
      .alerts { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
      .alert { padding: 12px 18px; border-radius: 16px; font-size: 18px; font-weight: 600;
        background: color-mix(in srgb, var(--hl-danger) 14%, var(--hl-surface)); color: var(--hl-danger); }
      .alert.frost { background: var(--hl-frost-100); color: var(--hl-info); }
      .grid { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-auto-rows: minmax(0, 1fr);
        grid-auto-flow: row dense; gap: 18px; }
      :host([editing]) .grid { grid-auto-rows: minmax(220px, auto); }
      @media (max-width: 760px) {
        :host { height: auto; min-height: 100vh; overflow: auto; padding: 16px; }
        .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-auto-rows: auto; }
      }
      .block { position: relative; min-height: 0; overflow: hidden; display: flex; flex-direction: column; container-type: size;
        background: var(--hl-surface); border-radius: 22px; padding: 18px 22px; box-shadow: var(--hl-shadow-2), var(--hl-highlight); }
      :host([dense]) .grid { gap: 10px; }
      :host([dense]) .block { padding: 10px 14px; border-radius: 16px; }
      :host([editing]) .block { container-type: normal; }
      .block.plain { background: none; box-shadow: none; padding: 4px; }
      .block h2 { font-size: clamp(13px, min(11cqh, 6cqw), 26px); margin: 0 0 min(10px, 3cqh); line-height: 1.15; }
      .block .body { min-height: 0; overflow: hidden; flex: 1; }
      .w1 { grid-column: span 1; } .w2 { grid-column: span 2; } .w3 { grid-column: span 3; } .w4 { grid-column: span 4; }
      @media (max-width: 760px) { .w3, .w4 { grid-column: span 2; } .block { container-type: normal; } }
      .editing .block { outline: 2px dashed var(--hl-border-strong, var(--hl-border)); cursor: grab; min-height: 200px; }
      .editing .block.dragging { opacity: 0.4; }
      .tools { display: flex; gap: 4px; flex-wrap: wrap; margin: -6px -8px 8px; padding-bottom: 6px; border-bottom: 1px solid var(--hl-border); }
      .tools .name { font-weight: 700; margin-right: auto; align-self: center; font-size: 15px; }
      .tools button { min-width: 36px; }
      .add { margin-top: 16px; background: var(--hl-surface); border-radius: 22px; padding: 18px 22px; box-shadow: var(--hl-shadow-2); }
      .add ul { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; list-style: none; margin: 10px 0 0; padding: 0; }
      .add li button { width: 100%; text-align: left; padding: 10px 14px; border-radius: 14px; border: 1px solid var(--hl-border); background: var(--hl-surface-2); cursor: pointer; color: inherit; font: inherit; }
      .add li button:hover { border-color: var(--hl-primary); }
      .add li b { display: block; }
      /* everything below scales with its own block (container query units), so the wall fits one screen */
      .clock { font-family: var(--hl-font-serif); font-size: clamp(28px, min(46cqh, 24cqw), 128px); font-weight: 700; line-height: 0.95; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
      .date { font-family: var(--hl-font-serif); font-style: italic; font-size: clamp(12px, min(12cqh, 5cqw), 28px); color: var(--hl-text-muted); margin-top: 4px; }
      .now { display: flex; align-items: center; gap: min(16px, 4cqw); height: 100%; }
      .now svg { width: clamp(36px, min(70cqh, 30cqw), 96px); height: auto; flex: none; }
      .now .t { font-family: var(--hl-font-serif); font-size: clamp(24px, min(42cqh, 20cqw), 80px); font-weight: 700; line-height: 1; }
      .now .c { font-size: clamp(12px, min(12cqh, 5cqw), 20px); color: var(--hl-text-muted); }
      ul.list { list-style: none; margin: 0; padding: 0; }
      ul.list li { display: flex; align-items: center; gap: 12px; padding: clamp(2px, 2.5cqh, 8px) 0; border-top: 1px solid color-mix(in srgb, var(--hl-border) 60%, transparent); font-size: clamp(12px, min(8cqh, 4cqw), 20px); }
      ul.list li:first-child { border-top: 0; }
      .tick { width: clamp(26px, 14cqh, 44px); height: clamp(26px, 14cqh, 44px); border-radius: 50%; border: 2.5px solid var(--hl-primary); background: none; cursor: pointer; flex: none; }
      .tick:hover { background: var(--hl-leaf-100); }
      li small { display: block; font-size: 0.7em; color: var(--hl-text-muted); }
      .late small { color: var(--hl-danger); }
      .days { display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: min(10px, 2cqw); height: 100%; }
      .day { text-align: center; padding: clamp(4px, 3cqh, 10px); border-radius: 14px; background: var(--hl-surface-2); font-size: clamp(11px, 7cqh, 14px); }
      .day b { display: block; font-family: var(--hl-font-serif); font-size: clamp(14px, min(14cqh, 6cqw), 26px); }
      .beds { display: flex; flex-direction: column; gap: clamp(4px, 3cqh, 10px); }
      .bed { display: grid; grid-template-columns: 1fr 2fr 48px; gap: 10px; align-items: center; font-size: clamp(12px, min(8cqh, 4cqw), 17px); }
      .gauge { height: clamp(6px, 4cqh, 12px); border-radius: 6px; background: var(--hl-surface-3); overflow: hidden; }
      .gauge span { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #d98e57, #9cc58a, #4a90c8); }
      .radar { width: 100%; height: 100%; object-fit: contain; border-radius: 12px; background: var(--hl-surface-2); }
      .quote { font-family: var(--hl-font-serif); font-style: italic; font-size: clamp(13px, min(13cqh, 5.5cqw), 30px); line-height: 1.3; margin: 0; }
      .text { font-size: clamp(12px, min(9cqh, 4.2cqw), 21px); line-height: 1.4; margin: 0; }
      .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 8px; }
      .stat b { display: block; font-family: var(--hl-font-serif); font-size: clamp(16px, min(20cqh, 9cqw), 40px); line-height: 1.05; }
      .stat span { color: var(--hl-text-muted); font-size: clamp(11px, 7cqh, 14px); }
      .agenda h3 { font-size: clamp(11px, 6cqh, 15px); margin: 6px 0 0; color: var(--hl-text-muted); text-transform: capitalize; }
      .agenda h3:first-child { margin-top: 0; }
      .empty { font-size: clamp(12px, min(8cqh, 4cqw), 19px); color: var(--hl-text-muted); margin: 0; }
      .note { font-size: clamp(10px, 6cqh, 12px); color: var(--hl-text-muted); margin-top: 4px; }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this.timer = window.setInterval(() => (this.now = new Date()), 20_000);
    this.dataTimer = window.setInterval(() => {
      this.radarTick = Date.now();
      this.radarFailed = false;
      void this.load();
    }, 10 * 60_000);
    void this.load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.timer);
    window.clearInterval(this.dataTimer);
  }

  protected updated(): void {
    const h = this.now.getHours();
    this.toggleAttribute("night", !this.editing && (h >= 22 || h < 6));
    this.toggleAttribute("editing", this.editing);
    const rows = Math.ceil(this.layout.reduce((s, b) => s + b.w, 0) / 4);
    this.toggleAttribute("dense", rows >= 4);
  }

  private get dutch(): boolean {
    return this.lang === "nl";
  }

  private async load(): Promise<void> {
    if (!this.api) return;
    try {
      this.data = await this.api.wallData();
    } catch {
      // the wall keeps showing what it has (the snapshot blocks work without it)
    }
  }

  /** The blocks to show: the garden's own wall in Dutch, the default elsewhere. */
  private get layout(): WallBlock[] {
    if (this.draft) return this.draft;
    if (!this.dutch) return DEFAULT_LAYOUT;
    return this.data?.layout ?? this.snapshot.settings.wall_layout ?? DEFAULT_LAYOUT;
  }

  private emit(name: string, detail?: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  // -- arranging -------------------------------------------------------------- //
  private startEditing(): void {
    this.draft = this.layout.map((b) => ({ ...b }));
    this.editing = true;
    this.saveError = "";
  }

  private async finishEditing(save: boolean): Promise<void> {
    if (save && this.draft && this.api) {
      try {
        const { layout } = await this.api.saveWallLayout(this.draft);
        if (this.data) this.data = { ...this.data, layout: layout ?? DEFAULT_LAYOUT, custom: layout != null };
      } catch (err) {
        this.saveError = (err as Error).message ?? String(err);
        return;
      }
    }
    this.editing = false;
    this.draft = null;
  }

  private async resetLayout(): Promise<void> {
    if (!this.api) return;
    try {
      await this.api.saveWallLayout(null);
      if (this.data) this.data = { ...this.data, layout: DEFAULT_LAYOUT, custom: false };
      this.draft = DEFAULT_LAYOUT.map((b) => ({ ...b }));
    } catch (err) {
      this.saveError = (err as Error).message ?? String(err);
    }
  }

  private change(fn: (blocks: WallBlock[]) => void): void {
    const blocks = (this.draft ?? []).map((b) => ({ ...b }));
    fn(blocks);
    this.draft = blocks;
  }

  private move(index: number, to: number): void {
    this.change((blocks) => {
      if (to < 0 || to >= blocks.length) return;
      const [b] = blocks.splice(index, 1);
      blocks.splice(to, 0, b);
    });
  }

  private onDrop(e: DragEvent, target: number): void {
    e.preventDefault();
    const from = this.dragIndex;
    this.dragIndex = null;
    if (from == null || from === target) return;
    this.move(from, target);
  }

  // -- blocks ----------------------------------------------------------------- //
  private plantIcon(task: Task): TemplateResult | typeof nothing {
    const planting = task.planting_id ? this.snapshot.plantings.find((p) => p.id === task.planting_id) : undefined;
    const plant = planting ? this.plants.get(planting.plant_id) : undefined;
    return plant ? glyphIcon(glyphFor(plant), plant.color || familyColor(this.families, plant.family), 30) : nothing;
  }

  private heading(id: string): string {
    if (this.dutch) return NL[id]?.name ?? id;
    return { tasks: this.t("dash.today_tasks"), forecast: this.t("dash.weather"), moisture: this.t("settings.sensor.soil_moisture") }[id] ?? "";
  }

  private renderBlock(id: string): TemplateResult | typeof nothing {
    const a = this.snapshot.analysis;
    const today = a?.today ?? "";
    const loc = localeOf(this.lang);
    switch (id) {
      case "clock":
        return html`<div class="clock">${this.now.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" })}</div>
          <div class="date">${this.now.toLocaleDateString(loc, { weekday: "long", day: "numeric", month: "long" })} · ${this.snapshot.gardens?.find((g) => g.entry_id === this.snapshot.entry_id)?.title ?? "Hortulus"}</div>`;
      case "weather_now": {
        const wid = this.snapshot.settings.weather_entity;
        const w = wid ? this.hass.states[wid] : undefined;
        if (w) {
          return html`<div class="now">${weatherGlyph(w.state, 88, this.now.getHours() >= 21 || this.now.getHours() < 6)}
            <div><div class="t">${w.attributes.temperature != null ? Math.round(Number(w.attributes.temperature)) : "–"}°</div>
              <div class="c">${this.t(`weather.cond.${w.state}`)}</div></div></div>`;
        }
        const o = a?.outlook?.find((x) => x.day === today);
        return o ? html`<div class="now"><div><div class="t">${o.tmax != null ? Math.round(o.tmax) : "–"}°</div>
          <div class="c">${o.tmin != null ? `${Math.round(o.tmin)}° · ` : ""}${o.rain_mm} mm</div></div></div>` : html`<p class="empty">–</p>`;
      }
      case "forecast":
        return a?.outlook?.length ? html`<div class="days">${a.outlook.slice(0, 5).map((o) => html`<div class="day">
            <span class="small muted">${o.day === today ? this.t("common.today") : formatDate(o.day, this.lang, { weekday: "short" })}</span>
            <b>${o.tmax != null ? Math.round(o.tmax) : "–"}° <span class="muted" style="font-size:0.7em">${o.tmin != null ? Math.round(o.tmin) : "–"}°</span></b>
            <span class="small" style="color:var(--hl-water-ink, var(--hl-water-500))">${o.rain_mm} mm</span></div>`)}</div>` : html`<p class="empty">–</p>`;
      case "radar": {
        const r = this.radarSrc();
        if (!r) return html`<p class="empty">Geen regenradar voor deze plek.</p>`;
        return this.radarFailed ? html`<p class="empty">De regenradar laadt niet.</p>`
          : html`<img class="radar" src=${r.src} alt=${NL.radar.name} @error=${() => (this.radarFailed = true)} />`;
      }
      case "tasks": {
        const tasks = sortTasks(this.snapshot.tasks.filter((x) => x.status === "open" && x.due <= today)).slice(0, 8);
        return tasks.length ? html`<ul class="list">${tasks.map((task) => html`<li class=${task.due < today ? "late" : ""}>
            <button class="tick" aria-label=${this.t("task.complete")} ?disabled=${this.editing}
              @click=${(e: Event) => { celebrateAt(e.currentTarget as Element); this.emit("complete-task", task); }}></button>
            ${this.plantIcon(task)}
            <span>${task.title}<small>${task.due < today ? this.t("wall.late", { date: formatDate(task.due, this.lang) }) : `${task.estimated_minutes} min`}</small></span>
          </li>`)}</ul>` : html`<p class="empty">${this.t("dash.no_tasks")}</p>`;
      }
      case "agenda": {
        const until = this.addDays(today, 7);
        const tasks = sortTasks(this.snapshot.tasks.filter((x) => x.status === "open" && x.due > today && x.due <= until));
        if (!tasks.length) return html`<p class="empty">Niets gepland voor de komende week.</p>`;
        const days = [...new Set(tasks.map((x) => x.due))].slice(0, 5);
        return html`<div class="agenda">${days.map((d) => html`<h3>${formatDate(d, this.lang, { weekday: "long", day: "numeric", month: "short" })}</h3>
          <ul class="list">${tasks.filter((x) => x.due === d).slice(0, 3).map((x) => html`<li>${this.plantIcon(x)}<span>${x.title}</span></li>`)}</ul>`)}</div>`;
      }
      case "moisture": {
        const beds = this.snapshot.beds.filter((b) => a?.beds[b.id]?.irrigation?.moisture != null);
        return beds.length ? html`<div class="beds">${beds.map((b) => {
          const m = a!.beds[b.id].irrigation.moisture ?? 0;
          return html`<div class="bed"><span>${b.name}</span><span class="gauge"><span style=${`width:${Math.max(4, Math.min(100, m))}%`}></span></span><b>${Math.round(m)}%</b></div>`;
        })}</div>` : html`<p class="empty">${this.dutch ? "Geen bedden met een vochtsensor." : "–"}</p>`;
      }
      case "watering": {
        const st = this.snapshot.irrigation_status;
        if (st?.running) return html`<p class="text">💧 ${this.t("wall.watering", { bed: this.snapshot.beds.find((b) => b.id === st.bed_id)?.name ?? "" })}</p>`;
        if (st?.waiting_for_rain) return html`<p class="text">🌧 ${this.t("dash.waiting_for_rain")}</p>`;
        return html`<p class="empty">Er wordt nu geen water gegeven.</p>`;
      }
      case "harvest_ready": {
        const ready = this.data?.ready ?? [];
        return ready.length ? html`<ul class="list">${ready.slice(0, 6).map((r) => html`<li><span>🧺 ${r.name}${r.until ? html`<small>tot ${formatDate(r.until, this.lang)}</small>` : nothing}</span></li>`)}</ul>`
          : html`<p class="empty">Nu nog niets oogstklaar.</p>`;
      }
      case "sow_week": {
        const until = this.addDays(today, 7);
        const tasks = sortTasks(this.snapshot.tasks.filter((x) => x.status === "open" && SOW_TYPES.has(x.type) && x.due <= until)).slice(0, 6);
        return tasks.length ? html`<ul class="list">${tasks.map((x) => html`<li>${this.plantIcon(x)}<span>${x.title}<small>${x.due <= today ? this.t("common.today") : formatDate(x.due, this.lang, { weekday: "long" })}</small></span></li>`)}</ul>`
          : html`<p class="empty">Deze week niets te zaaien of uit te planten.</p>`;
      }
      case "pests": {
        const pests = a?.pests ?? [];
        return pests.length ? html`<ul class="list">${pests.slice(0, 3).map((w) => html`<li><span><b>${w.label.charAt(0).toUpperCase() + w.label.slice(1)}</b>
            <span class="chip ${w.status === "active" ? "warn" : "info"}">${this.t(`pests.status.${w.status}`)}</span><small>${w.advice}</small></span></li>`)}</ul>`
          : html`<p class="empty">Geen plagen in aantocht.</p>`;
      }
      case "garden": {
        const season = a?.season ?? new Date().getFullYear();
        const active = new Set(Object.values(a?.beds ?? {}).flatMap((b) => b.active_plantings));
        const crops = new Set(this.snapshot.plantings.filter((p) => active.has(p.id)).map((p) => p.plant_id));
        const kg = (this.snapshot.harvest_log ?? []).filter((h) => h.day.startsWith(String(season))).reduce((s, h) => s + (h.kg || 0), 0);
        return html`<div class="stats">
          <div class="stat"><b>${this.snapshot.beds.length}</b><span>bedden</span></div>
          <div class="stat"><b>${active.size}</b><span>teelten in de grond</span></div>
          <div class="stat"><b>${crops.size}</b><span>soorten</span></div>
          <div class="stat"><b>${kg.toLocaleString(loc, { maximumFractionDigits: 1 })}</b><span>kg geoogst in ${season}</span></div>
        </div>`;
      }
      case "sun": {
        const sun = this.hass.states?.["sun.sun"];
        const rise = sun?.attributes.next_rising as string | undefined;
        const set = sun?.attributes.next_setting as string | undefined;
        if (!rise || !set) return html`<p class="empty">Geen zongegevens.</p>`;
        const fmt = (iso: string) => new Date(iso).toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" });
        return html`<div class="stats"><div class="stat"><b>${fmt(rise)}</b><span>☀️ op</span></div><div class="stat"><b>${fmt(set)}</b><span>🌙 onder</span></div></div>`;
      }
      case "saying":
        return this.data?.saying ? html`<p class="quote">“${this.data.saying}”</p><p class="note">Volksweerspreuk</p>` : html`<p class="empty">–</p>`;
      case "fact":
        return this.data?.fact ? html`<p class="text">🌱 ${this.data.fact}</p>` : html`<p class="empty">–</p>`;
      case "eco_month":
        return this.data?.eco_month?.text ? html`<p class="text"><b>${this.data.eco_month.title}</b><br />${this.data.eco_month.text}</p>` : html`<p class="empty">–</p>`;
      case "recipe": {
        const r = this.data?.recipe;
        return r ? html`<p class="quote" style="font-style:normal">🍲 ${r.title}</p>
            <p class="text">${[r.produce.length ? `Met ${r.produce.join(", ").toLowerCase()} uit je tuin` : "", r.course, r.minutes ? `${r.minutes} min` : ""].filter(Boolean).join(" · ")}</p>
            <p class="note">Het volledige recept staat bij Koken.</p>`
          : html`<p class="empty">Een recepttip volgt zodra er iets oogstklaar is.</p>`;
      }
      case "slogan":
        return a?.slogan ? html`<p class="quote">${a.slogan}</p>` : html`<p class="empty">–</p>`;
      default:
        return nothing;
    }
  }

  private addDays(iso: string, n: number): string {
    const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
    d.setDate(d.getDate() + n);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  /** A radar camera in Home Assistant (e.g. Buienradar), else Buienradar's public map for NL / BE. */
  private radarSrc(): { src: string } | null {
    const camera = Object.keys(this.hass.states ?? {}).find((id) => id.startsWith("camera.") && /buienradar|radar|regen|rain/i.test(id));
    if (camera) {
      const token = this.hass.states[camera].attributes.access_token as string | undefined;
      return { src: `/api/camera_proxy/${camera}?token=${token ?? ""}&t=${this.radarTick}` };
    }
    const country = (this.hass.config?.country ?? "NL").toUpperCase();
    if (country !== "NL" && country !== "BE") return null;
    return { src: `https://api.buienradar.nl/image/1.0/RadarMap${country}?w=500&h=512&t=${this.radarTick}` };
  }

  private renderTools(b: WallBlock, i: number, count: number): TemplateResult {
    return html`<div class="tools">
      <span class="name">${NL[b.id]?.name ?? b.id}</span>
      <button class="btn small ghost" aria-label="Naar voren" title="Naar voren" ?disabled=${i === 0} @click=${() => this.move(i, i - 1)}>◀</button>
      <button class="btn small ghost" aria-label="Naar achteren" title="Naar achteren" ?disabled=${i === count - 1} @click=${() => this.move(i, i + 1)}>▶</button>
      <button class="btn small ghost" aria-label="Smaller" title="Smaller" ?disabled=${b.w <= 1} @click=${() => this.change((bs) => (bs[i].w = Math.max(1, bs[i].w - 1)))}>−</button>
      <button class="btn small ghost" aria-label="Breder" title="Breder" ?disabled=${b.w >= 4} @click=${() => this.change((bs) => (bs[i].w = Math.min(4, bs[i].w + 1)))}>+</button>
      <button class="btn small ghost" aria-label="Verwijderen" title="Verwijderen" @click=${() => this.change((bs) => bs.splice(i, 1))}>✕</button>
    </div>`;
  }

  private renderAdd(): TemplateResult {
    const shown = new Set(this.layout.map((b) => b.id));
    const hidden = Object.keys(NL).filter((id) => !shown.has(id));
    const width = (id: string) => this.data?.blocks?.[id] ?? 2;
    return html`<section class="add" aria-labelledby="wall-add">
      <h2 id="wall-add">Blok toevoegen</h2>
      <p class="small muted">Sleep de blokken om de volgorde te kiezen, of gebruik ◀ ▶. Met − en + maak je een blok smaller of breder. Alles past op één scherm.</p>
      ${hidden.length ? html`<ul>${hidden.map((id) => html`<li><button @click=${() => this.change((bs) => bs.push({ id, w: width(id) }))}>
          <b>+ ${NL[id].name}</b><span class="small muted">${NL[id].about}</span></button></li>`)}</ul>` : html`<p class="small muted">Alle blokken staan op je wandscherm.</p>`}
      ${this.saveError ? html`<p class="small" role="alert" style="color:var(--hl-danger)">${this.saveError}</p>` : nothing}
    </section>`;
  }

  render(): TemplateResult {
    const a = this.snapshot.analysis;
    const st = this.snapshot.irrigation_status;
    const blocks = this.layout;
    const canArrange = this.dutch && this.admin && !!this.api;
    return html`
      <div class="bar">
        ${canArrange && !this.editing ? html`<button class="btn small ghost" @click=${() => this.startEditing()}>Aanpassen</button>` : nothing}
        ${this.editing ? html`
          <button class="btn small ghost" @click=${() => this.resetLayout()}>Standaard</button>
          <button class="btn small ghost" @click=${() => this.finishEditing(false)}>Annuleren</button>
          <button class="btn small primary" @click=${() => this.finishEditing(true)}>Klaar</button>` : nothing}
        ${!this.editing ? html`<button class="btn small ghost exit" @click=${() => this.emit("navigate", "dashboard")}>${this.t("wall.exit")}</button>` : nothing}
      </div>
      ${st?.leak || st?.stuck?.length || (a && (a.frost.level === "high" || a.frost.level === "moderate")) ? html`<div class="alerts">
        ${st?.leak ? html`<div class="alert">${this.t("valve.leak", { liters: st.leak.liters, minutes: st.leak.minutes })}</div>` : nothing}
        ${(st?.stuck ?? []).map((v) => html`<div class="alert">${this.t("valve.stuck", { what: v.what === "pump" ? this.t("valve.pump") : v.what, entity: v.entity_id })}</div>`)}
        ${a && (a.frost.level === "high" || a.frost.level === "moderate") ? html`<div class="alert frost">${this.t("dash.frost_risk")}: ${this.t(`risk.${a.frost.level}`)}</div>` : nothing}
      </div>` : nothing}
      <div class="grid ${this.editing ? "editing" : ""}">
        ${blocks.map((b, i) => {
          const plain = b.id === "clock" || b.id === "weather_now";
          const title = plain ? "" : this.heading(b.id);
          return html`<section class="block w${b.w} ${plain && !this.editing ? "plain" : ""} ${this.dragIndex === i ? "dragging" : ""}"
              aria-label=${title || (NL[b.id]?.name ?? b.id)}
              draggable=${this.editing ? "true" : "false"}
              @dragstart=${(e: DragEvent) => { if (!this.editing) return; this.dragIndex = i; e.dataTransfer?.setData("text/plain", b.id); }}
              @dragend=${() => (this.dragIndex = null)}
              @dragover=${(e: DragEvent) => { if (this.editing) e.preventDefault(); }}
              @drop=${(e: DragEvent) => this.onDrop(e, i)}>
            ${this.editing ? this.renderTools(b, i, blocks.length) : nothing}
            ${title && !this.editing ? html`<h2>${title}</h2>` : nothing}
            <div class="body">${this.renderBlock(b.id)}</div>
          </section>`;
        })}
      </div>
      ${this.editing ? this.renderAdd() : nothing}`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-wall-view": WallView;
  }
}
