// "Journal" tab: garden diary with photos, harvest log with learned yields,
// seed stock with viability, and garden water use.
import "../components/harvest-years";
import "../components/kitchen-economy";
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { photoUrl, type GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { FamilyInfo, JournalEntry, Plant, Planting, RecordsOverview, SeedPacket, Snapshot, SyslogEntry, SyslogSummary } from "../types";
import { familyColor, formatDate, plantName, presentIn, localeOf } from "../util/garden";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import "../components/date-input";
import "../components/water-chart";
import "../components/season-report";

type Section = "diary" | "harvest" | "kitchen" | "seeds" | "water" | "report" | "system";
const SYSLOG_PAGE = 50;
const SYSLOG_SHOWN_LINES = 6;
const OP_ICON: Record<string, string> = { add: "mdi:plus-circle-outline", remove: "mdi:minus-circle-outline", change: "mdi:pencil-outline" };
const KINDS = ["note", "observation", "problem", "milestone"] as const;
const KIND_ICON: Record<string, string> = {
  note: "mdi:note-text-outline", observation: "mdi:eye-outline", problem: "mdi:alert-circle-outline", milestone: "mdi:flag-checkered",
};
const SEED_CHIP: Record<string, string> = { ok: "ok", use_soon: "warn", expired: "bad", empty: "", unknown: "" };

@customElement("hl-journal-view")
export class JournalView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) plants: Plant[] = [];
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ type: Boolean }) admin = true;
  @property() section: Section = "diary";
  /** Show only the system log (used by the Analysis tab). */
  @property({ type: Boolean }) systemOnly = false;

  @state() private waterBed = "";
  @state() private waterDays = 14;
  @state() private overview: RecordsOverview | null = null;
  @state() private filter = "";
  @state() private draftPhotos: string[] = [];
  @state() private busy = false;
  @state() private syslog: SyslogEntry[] = [];
  @state() private syslogMore = false;
  @state() private syslogSystem = true;

  static styles = [
    shared,
    css`
      .plant-icon { border: 0; background: none; padding: 0; cursor: pointer; display: inline-grid; vertical-align: middle; }
      :host { display: block; }
      .tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: var(--hl-s3); }
      .grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: var(--hl-s4); align-items: start; }
      @media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }
      form.stack textarea { min-height: 80px; }
      .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--hl-s2) var(--hl-s3); }
      .form-grid .full { grid-column: 1 / -1; }
      .timeline { display: flex; flex-direction: column; gap: var(--hl-s3); }
      .month { font-weight: 700; color: var(--hl-text-muted); text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; margin-top: 6px; }
      .entry { display: grid; grid-template-columns: 36px 1fr; gap: 4px 10px; padding: 10px 12px; border-radius: var(--hl-r-md);
        border: 1px solid var(--hl-border); background: var(--hl-surface); }
      .entry.problem { border-left: 4px solid var(--hl-tomato-500); }
      .entry.milestone { border-left: 4px solid var(--hl-sun-500); }
      .entry .icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; background: var(--hl-surface-2); }
      .entry .meta { font-size: var(--hl-fs-xs); color: var(--hl-text-muted); }
      .photos { display: flex; gap: 6px; flex-wrap: wrap; grid-column: 2; }
      .photos img { width: 96px; height: 96px; object-fit: cover; border-radius: var(--hl-r-sm); border: 1px solid var(--hl-border); }
      .crop { display: grid; grid-template-columns: 28px 1fr auto; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--hl-border); }
      .bar { height: 8px; border-radius: 4px; background: var(--hl-sun-500); margin-top: 3px; }
      .total { font-size: var(--hl-fs-2xl); font-weight: 800; }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); }
      td, th { padding: 5px 6px; border-bottom: 1px solid var(--hl-border); text-align: left; }
      td.num, th.num { text-align: right; white-space: nowrap; }
      .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--hl-s3); }
      .tile { padding: 12px; border-radius: var(--hl-r-md); background: var(--hl-surface-2); }
      .tile b { display: block; font-size: var(--hl-fs-2xl); }
      .days { display: flex; align-items: flex-end; gap: 3px; height: 90px; }
      .days div { flex: 1; background: var(--hl-water-500); border-radius: 3px 3px 0 0; min-height: 2px; }
      .stars button { border: 0; background: none; cursor: pointer; font-size: 20px; color: var(--hl-text-muted); padding: 0 1px; }
      .stars button[aria-pressed="true"] { color: var(--hl-sun-500); }
      .log { display: grid; grid-template-columns: 36px 1fr auto; gap: 4px 10px; padding: 10px 12px; border-radius: var(--hl-r-md);
        border: 1px solid var(--hl-border); background: var(--hl-surface); align-items: start; }
      .log.undone { opacity: 0.6; }
      .log.error { border-left: 4px solid var(--hl-tomato-500); }
      .log.system .icon { color: var(--hl-text-muted); }
      .log .icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; background: var(--hl-surface-2); }
      .log ul { margin: 4px 0 0; padding: 0; list-style: none; font-size: var(--hl-fs-sm); }
      .log li { display: flex; gap: 6px; align-items: center; }
      .log li ha-icon { --mdc-icon-size: 16px; color: var(--hl-text-muted); flex: none; }
      .log .meta { font-size: var(--hl-fs-xs); color: var(--hl-text-muted); }
      @media (max-width: 600px) { .log { grid-template-columns: 1fr; } .log .icon { display: none; } }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private reloadTimer?: number;

  protected updated(changed: Map<string, unknown>): void {
    // Every pushed snapshot can change the overview (harvests, seeds, water readings from
    // any client): reload it, debounced so a burst of pushes costs one request.
    if (!changed.has("snapshot") || !this.snapshot || changed.get("snapshot") === undefined) return;
    window.clearTimeout(this.reloadTimer);
    this.reloadTimer = window.setTimeout(() => void this.load(), 800);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.reloadTimer);
  }

  private async load(): Promise<void> {
    try {
      this.overview = await this.api.records();
    } catch {
      /* older backend */
    }
    if (this.section === "system" || this.systemOnly) await this.loadSyslog();
  }

  private async loadSyslog(more = false): Promise<void> {
    try {
      const before = more ? this.syslog[this.syslog.length - 1]?.id ?? null : null;
      // A refresh keeps as many entries as are already on screen.
      const limit = more ? SYSLOG_PAGE : Math.max(SYSLOG_PAGE, this.syslog.length);
      const page = await this.api.syslog({ limit, before, include_system: this.syslogSystem });
      this.syslog = more ? [...this.syslog, ...page.entries] : page.entries;
      this.syslogMore = page.more;
    } catch {
      /* older backend */
    }
  }

  private toast(message: string): void {
    this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message }, bubbles: true, composed: true }));
  }

  private async guard(fn: () => Promise<unknown>, ok?: string): Promise<boolean> {
    this.busy = true;
    try {
      await fn();
      if (ok) this.toast(ok);
      return true;
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
      return false;
    } finally {
      this.busy = false;
    }
  }

  private plant(id: string | null | undefined): Plant | undefined {
    return this.plants.find((p) => p.id === id);
  }

  private icon(id: string | null | undefined, size = 24): TemplateResult {
    const p = this.plant(id);
    return p ? html`<button class="plant-icon" title=${this.t("lib.open_plant")} aria-label=${plantName(p, this.lang)}
      @click=${() => this.dispatchEvent(new CustomEvent("open-plant", { detail: p.id, bubbles: true, composed: true }))}>${glyphIcon(glyphFor(p), p.color || familyColor(this.families, p.family), size)}</button>` : html``;
  }

  private get season(): number {
    return this.snapshot.analysis?.season ?? new Date().getFullYear();
  }

  private get presentPlantings(): Planting[] {
    return this.snapshot.plantings.filter((p) => presentIn(p, !!this.plant(p.plant_id)?.perennial, this.season));
  }

  private plantingLabel(p: Planting): string {
    const bed = this.snapshot.beds.find((b) => b.id === p.bed_id);
    return `${plantName(this.plant(p.plant_id), this.lang)} · ${bed?.name ?? ""}`;
  }

  render(): TemplateResult {
    if (this.systemOnly) return this.renderSystem();
    const sections: [Section, string][] = [["diary", "mdi:notebook-outline"], ["harvest", "mdi:basket-outline"], ["kitchen", "mdi:silverware-fork-knife"], ["seeds", "mdi:seed-outline"], ["water", "mdi:water-outline"], ["report", "mdi:file-chart-outline"], ["system", "mdi:history"]];
    return html`
      <div class="tabs" role="tablist">
        ${sections.map(([id, icon]) => html`<button class="chip" role="tab" aria-selected=${String(this.section === id)} aria-pressed=${String(this.section === id)}
          @click=${() => this.openSection(id)}><ha-icon icon=${icon}></ha-icon>${this.t(`journal.${id}`)}</button>`)}
      </div>
      ${this.section === "diary" ? this.renderDiary() : this.section === "harvest" ? this.renderHarvest() : this.section === "seeds" ? this.renderSeeds()
        : this.section === "water" ? this.renderWater()
        : this.section === "kitchen" ? html`<hl-kitchen-economy .overview=${this.overview} .api=${this.api} .t=${this.t} lang=${this.lang}
            today=${this.snapshot.analysis?.today ?? ""} ?admin=${this.admin} @changed=${() => this.load()}></hl-kitchen-economy>`
        : this.section === "report" ? html`<section class="card stack"><h2><ha-icon icon="mdi:file-chart-outline"></ha-icon> ${this.t("journal.report")}</h2>
            <hl-season-report .snapshot=${this.snapshot} .api=${this.api} .t=${this.t} lang=${this.lang}
              .plants=${new Map(this.plants.map((x) => [x.id, x]))} .families=${this.families}></hl-season-report></section>`
        : this.renderSystem()}
    `;
  }

  private openSection(id: Section): void {
    this.section = id;
    if (id === "system") void this.loadSyslog();
  }

  // -- diary ------------------------------------------------------------------ //
  private async addPhoto(ev: Event): Promise<void> {
    const files = [...((ev.target as HTMLInputElement).files ?? [])];
    for (const file of files) {
      await this.guard(async () => {
        this.draftPhotos = [...this.draftPhotos, await this.api.uploadPhoto(file)];
      });
    }
    (ev.target as HTMLInputElement).value = "";
  }

  private async saveEntry(ev: Event): Promise<void> {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const val = (n: string) => (form.elements.namedItem(n) as HTMLInputElement | HTMLSelectElement).value;
    const link = val("link");
    const entry: Partial<JournalEntry> = {
      text: val("text"),
      kind: val("kind") as JournalEntry["kind"],
      photos: this.draftPhotos,
      planting_id: link.startsWith("p:") ? link.slice(2) : null,
      bed_id: link.startsWith("b:") ? link.slice(2) : null,
    };
    if (await this.guard(() => this.api.saveJournal(entry), this.t("journal.saved"))) {
      form.reset();
      this.draftPhotos = [];
    }
  }

  private renderDiary(): TemplateResult {
    const all = [...(this.snapshot.journal ?? [])].sort((a, b) => (a.at < b.at ? 1 : -1));
    const list = all.filter((e) => !this.filter || e.bed_id === this.filter || e.plant_id === this.filter);
    let lastMonth = "";
    return html`<div class="grid">
      <section class="card stack" aria-labelledby="new-entry">
        <h2 id="new-entry"><ha-icon icon="mdi:notebook-edit-outline"></ha-icon> ${this.t("journal.new")}</h2>
        <form class="stack" @submit=${this.saveEntry}>
          <label class="field">${this.t("journal.text")}<textarea name="text" placeholder=${this.t("journal.placeholder")}></textarea></label>
          <div class="form-grid">
            <label class="field">${this.t("journal.kind")}<select name="kind">${KINDS.map((k) => html`<option value=${k}>${this.t(`journal.kind.${k}`)}</option>`)}</select></label>
            <label class="field">${this.t("journal.link")}<select name="link"><option value="">${this.t("journal.whole_garden")}</option>
              <optgroup label=${this.t("journal.beds")}>${this.snapshot.beds.map((b) => html`<option value=${`b:${b.id}`}>${b.name}</option>`)}</optgroup>
              <optgroup label=${this.t("journal.crops")}>${this.presentPlantings.map((p) => html`<option value=${`p:${p.id}`}>${this.plantingLabel(p)}</option>`)}</optgroup>
            </select></label>
          </div>
          <label class="btn small ghost" style="align-self:flex-start"><ha-icon icon="mdi:camera-plus-outline"></ha-icon>${this.t("journal.add_photo")}
            <input type="file" accept="image/*" capture="environment" multiple hidden @change=${this.addPhoto} /></label>
          ${this.draftPhotos.length ? html`<div class="photos" style="grid-column:auto">${this.draftPhotos.map((id) => html`<img src=${photoUrl(id)} alt="" />`)}</div>` : nothing}
          <div class="row"><button class="btn primary" type="submit" ?disabled=${this.busy || !this.admin}>${this.t("journal.save")}</button></div>
        </form>
      </section>
      <section class="card stack" aria-labelledby="diary-h">
        <div class="row wrap"><h2 id="diary-h"><ha-icon icon="mdi:timeline-text-outline"></ha-icon> ${this.t("journal.diary")}</h2><span class="spacer"></span>
          <select aria-label=${this.t("journal.filter")} @change=${(e: Event) => (this.filter = (e.target as HTMLSelectElement).value)}>
            <option value="">${this.t("journal.all")}</option>
            ${this.snapshot.beds.map((b) => html`<option value=${b.id}>${b.name}</option>`)}
            ${[...new Set(all.map((e) => e.plant_id).filter(Boolean))].map((id) => html`<option value=${id!}>${plantName(this.plant(id), this.lang)}</option>`)}
          </select></div>
        ${list.length ? html`<div class="timeline">${list.map((e) => {
          const month = formatDate(e.at, this.lang, { month: "long", year: "numeric" });
          const head = month !== lastMonth ? html`<div class="month">${month}</div>` : nothing;
          lastMonth = month;
          const bed = this.snapshot.beds.find((b) => b.id === e.bed_id);
          return html`${head}<article class="entry ${e.kind}">
            <span class="icon">${e.plant_id ? this.icon(e.plant_id, 26) : html`<ha-icon icon=${KIND_ICON[e.kind]}></ha-icon>`}</span>
            <div><div class="meta">${formatDate(e.at, this.lang, { weekday: "short", day: "numeric", month: "short" })}
              · ${this.t(`journal.kind.${e.kind}`)}${e.plant_id ? ` · ${plantName(this.plant(e.plant_id), this.lang)}` : ""}${bed ? ` · ${bed.name}` : ""}${e.author ? ` · ${e.author}` : ""}</div>
              <div>${e.text}</div></div>
            ${e.photos.length ? html`<div class="photos">${e.photos.map((id) => html`<a href=${photoUrl(id, "original")} target="_blank" rel="noopener"><img src=${photoUrl(id)} alt="" loading="lazy" /></a>`)}</div>` : nothing}
            ${this.admin ? html`<div style="grid-column:2"><button class="btn small ghost" @click=${() => this.guard(() => this.api.deleteRecord("journal", e.id))}>${this.t("common.delete")}</button></div>` : nothing}
          </article>`;
        })}</div>` : html`<p class="small muted">${this.t("journal.empty")}</p>`}
      </section>
    </div>`;
  }

  // -- harvest ---------------------------------------------------------------- //
  @state() private quality = 0;

  private async saveHarvest(ev: Event): Promise<void> {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const val = (n: string) => (form.elements.namedItem(n) as HTMLInputElement | HTMLSelectElement).value;
    const what = val("what");
    const ok = await this.guard(() => this.api.logHarvest({
      planting_id: what.startsWith("p:") ? what.slice(2) : null,
      plant_id: what.startsWith("x:") ? what.slice(2) : null,
      kg: Number(val("kg")) || 0,
      count: val("count") ? Number(val("count")) : null,
      quality: this.quality || null,
      day: val("day") || undefined,
      note: val("note"),
    }), this.t("journal.harvest_saved"));
    if (ok) {
      form.reset();
      this.quality = 0;
      void this.load();
    }
  }

  private renderHarvest(): TemplateResult {
    const o = this.overview;
    const season = Object.values(o?.harvest_season ?? {}).sort((a, b) => b.kg - a.kg);
    const total = season.reduce((s, c) => s + c.kg, 0);
    const max = Math.max(...season.map((c) => c.kg), 0.001);
    const recent = [...(this.snapshot.harvest_log ?? [])].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, 25);
    const harvestable = this.presentPlantings.filter((p) => this.plant(p.plant_id)?.harvestable !== false);
    return html`<div class="grid">
      <section class="card stack" aria-labelledby="h-new">
        <h2 id="h-new"><ha-icon icon="mdi:basket-plus-outline"></ha-icon> ${this.t("journal.log_harvest")}</h2>
        <form class="stack" @submit=${this.saveHarvest}>
          <label class="field">${this.t("journal.what")}<select name="what" required>
            <optgroup label=${this.t("journal.crops")}>${harvestable.map((p) => html`<option value=${`p:${p.id}`}>${this.plantingLabel(p)}</option>`)}</optgroup>
            <optgroup label=${this.t("advice.all_plants")}>${[...this.plants].sort((a, b) => plantName(a, this.lang).localeCompare(plantName(b, this.lang)))
              .map((p) => html`<option value=${`x:${p.id}`}>${plantName(p, this.lang)}</option>`)}</optgroup>
          </select></label>
          <div class="form-grid">
            <label class="field">${this.t("journal.kg")}<input name="kg" type="number" min="0" step="0.05" inputmode="decimal" /></label>
            <label class="field">${this.t("journal.count")}<input name="count" type="number" min="0" step="1" inputmode="numeric" /></label>
            <label class="field">${this.t("journal.day")}<hl-date-input name="day" .value=${this.snapshot.analysis?.today ?? ""} lang=${this.lang} pickLabel=${this.t("crops.pick_date")}></hl-date-input></label>
            <div class="field">${this.t("journal.quality")}<span class="stars" role="group">${[1, 2, 3, 4, 5].map((n) => html`<button type="button" aria-label=${String(n)}
              aria-pressed=${String(this.quality >= n)} @click=${() => (this.quality = this.quality === n ? 0 : n)}>★</button>`)}</span></div>
            <label class="field full">${this.t("task.notes")}<input name="note" /></label>
          </div>
          <div class="row"><button class="btn primary" type="submit" ?disabled=${this.busy || !this.admin}>${this.t("journal.save")}</button></div>
        </form>
        <p class="xs muted">${this.t("journal.learn_hint")}</p>
      </section>
      <section class="card stack" aria-labelledby="h-season">
        <h2 id="h-season"><ha-icon icon="mdi:chart-bar"></ha-icon> ${this.t("journal.harvest_season", { season: o?.season ?? this.season })}</h2>
        <div class="row"><span class="total">${total.toFixed(1)} kg</span><span class="small muted">${this.t("journal.crops_n", { n: season.length })}</span></div>
        ${season.map((c) => {
          const learned = o?.learned_yields[c.plant_id];
          const db = this.plant(c.plant_id)?.yield_kg_m2;
          return html`<div class="crop">${this.icon(c.plant_id, 26)}
            <div><b>${plantName(this.plant(c.plant_id), this.lang)}</b>
              <div class="bar" style=${`width:${Math.max((c.kg / max) * 100, 2)}%`}></div>
              ${learned != null ? html`<span class="xs muted">${this.t("journal.yield", { kg: learned, db: db ?? "–" })}</span>` : nothing}</div>
            <span class="num"><b>${c.kg.toFixed(1)} kg</b>${c.count ? html`<br /><span class="xs muted">${c.count} ×</span>` : nothing}</span></div>`;
        })}
        ${recent.length ? html`<h3>${this.t("journal.recent")}</h3><table>
          <tr><th>${this.t("journal.day")}</th><th>${this.t("lib.plant")}</th><th class="num">kg</th><th class="num">#</th><th></th></tr>
          ${recent.map((e) => html`<tr><td>${formatDate(e.day, this.lang)}</td><td>${plantName(this.plant(e.plant_id), this.lang)}${e.quality ? ` ${"★".repeat(e.quality)}` : ""}</td>
            <td class="num">${e.kg ? e.kg.toFixed(2) : "–"}</td><td class="num">${e.count ?? "–"}</td>
            <td class="num">${this.admin ? html`<button class="icon-btn" aria-label=${this.t("common.delete")} @click=${() => this.guard(() => this.api.deleteRecord("harvest", e.id)).then(() => this.load())}>
              <ha-icon icon="mdi:delete-outline"></ha-icon></button>` : nothing}</td></tr>`)}
        </table>` : html`<p class="small muted">${this.t("journal.no_harvest")}</p>`}
      </section>
      <section class="card stack" style="grid-column: 1 / -1" aria-labelledby="h-years">
        <h2 id="h-years"><ha-icon icon="mdi:chart-timeline-variant"></ha-icon> ${this.t("harvest.years_title")}</h2>
        <hl-harvest-years .years=${o?.harvest_years ?? {}} .plants=${new Map(this.plants.map((p) => [p.id, p]))} .families=${this.families}
          .t=${this.t} lang=${this.lang}></hl-harvest-years>
      </section>
    </div>`;
  }

  // -- seeds ----------------------------------------------------------------- //
  private async saveSeed(ev: Event): Promise<void> {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const val = (n: string) => (form.elements.namedItem(n) as HTMLInputElement | HTMLSelectElement).value;
    const packet: Partial<SeedPacket> = {
      plant_id: val("plant"), variety: val("variety"), year: val("year") ? Number(val("year")) : null,
      quantity: Number(val("quantity") || 1), unit: val("unit") as SeedPacket["unit"], source: val("source"),
    };
    if (await this.guard(() => this.api.saveSeed(packet), this.t("journal.seed_saved"))) {
      form.reset();
      void this.load();
    }
  }

  private renderSeeds(): TemplateResult {
    const report = this.overview?.seeds;
    const sorted = [...this.plants].sort((a, b) => plantName(a, this.lang).localeCompare(plantName(b, this.lang)));
    return html`<div class="grid">
      <section class="card stack" aria-labelledby="s-new">
        <h2 id="s-new"><ha-icon icon="mdi:seed-plus-outline"></ha-icon> ${this.t("journal.add_seed")}</h2>
        <form class="stack" @submit=${this.saveSeed}>
          <label class="field">${this.t("lib.plant")}<select name="plant" required>${sorted.map((p) => html`<option value=${p.id}>${plantName(p, this.lang)}</option>`)}</select></label>
          <div class="form-grid">
            <label class="field">${this.t("journal.variety")}<input name="variety" /></label>
            <label class="field">${this.t("journal.year")}<input name="year" type="number" min="1990" max="2100" .value=${String(this.season)} /></label>
            <label class="field">${this.t("journal.quantity")}<input name="quantity" type="number" min="0" step="0.5" value="1" /></label>
            <label class="field">${this.t("journal.unit")}<select name="unit">${(["packet", "seeds", "g"] as const).map((u) => html`<option value=${u}>${this.t(`journal.unit.${u}`)}</option>`)}</select></label>
            <label class="field full">${this.t("journal.source")}<input name="source" placeholder=${this.t("journal.source_hint")} /></label>
          </div>
          <div class="row"><button class="btn primary" type="submit" ?disabled=${this.busy || !this.admin}>${this.t("journal.save")}</button></div>
        </form>
        ${report?.missing.length ? html`<div class="finding warning"><ha-icon icon="mdi:cart-outline"></ha-icon><span>${this.t("journal.seed_missing")}:
          ${report.missing.map((id) => plantName(this.plant(id), this.lang)).join(", ")}</span></div>` : nothing}
        <p class="xs muted">${this.t("journal.seed_hint")}</p>
      </section>
      <section class="card stack" aria-labelledby="s-box">
        <h2 id="s-box"><ha-icon icon="mdi:archive-outline"></ha-icon> ${this.t("journal.seed_box")} <span class="chip">${report?.packets.length ?? 0}</span></h2>
        ${report?.packets.length ? html`<table>
          <tr><th>${this.t("lib.plant")}</th><th>${this.t("journal.variety")}</th><th class="num">${this.t("journal.year")}</th><th class="num">${this.t("journal.quantity")}</th><th>${this.t("journal.status")}</th><th></th></tr>
          ${report.packets.map((p) => html`<tr>
            <td>${this.icon(p.plant_id, 18)} ${plantName(this.plant(p.plant_id), this.lang)}${p.needed ? html` <span class="chip ok" title=${this.t("journal.needed")}>✓</span>` : nothing}</td>
            <td>${p.variety || "–"}</td><td class="num">${p.year ?? "–"}</td><td class="num">${p.quantity} ${this.t(`journal.unit.${p.unit}`)}</td>
            <td><span class="chip ${SEED_CHIP[p.status]}">${this.t(`journal.seed.${p.status}`, { year: p.use_by ?? "" })}</span></td>
            <td class="num">${this.admin ? html`<button class="icon-btn" aria-label=${this.t("common.delete")} @click=${() => this.guard(() => this.api.deleteRecord("seed", p.id)).then(() => this.load())}>
              <ha-icon icon="mdi:delete-outline"></ha-icon></button>` : nothing}</td></tr>`)}
        </table>` : html`<p class="small muted">${this.t("journal.no_seeds")}</p>`}
      </section>
    </div>`;
  }

  // -- water ----------------------------------------------------------------- //
  private renderWater(): TemplateResult {
    const w = this.overview?.water;
    const cfg = this.snapshot.settings.water;
    const configured = !!(cfg?.meter_entity || cfg?.butt_level_entity);
    const max = Math.max(...(w?.per_day ?? []).map((d) => d.liters), 1);
    return html`<section class="card stack" aria-labelledby="w-h">
      <h2 id="w-h"><ha-icon icon="mdi:water-outline"></ha-icon> ${this.t("journal.water")}</h2>
      ${configured ? nothing : html`<div class="finding info"><ha-icon icon="mdi:information-outline"></ha-icon><span>${this.t("journal.water_setup")}</span></div>`}
      <div class="tiles">
        <div class="tile">${this.t("journal.water_week")}<b>${w?.week_l != null ? `${w.week_l} L` : "–"}</b></div>
        <div class="tile">${this.t("journal.water_season")}<b>${w?.season_l != null ? `${w.season_l} L` : "–"}</b></div>
        <div class="tile">${this.t("journal.rain_available")}<b>${w?.rain_available_l != null ? `${w.rain_available_l} L` : w?.butt_pct != null ? `${w.butt_pct}%` : "–"}</b></div>
        ${w?.irrigated_rain_l ? html`<div class="tile">${this.t("journal.from_rain")}<b>${w.irrigated_rain_l} L</b></div>` : nothing}
        ${w?.irrigated_mains_l ? html`<div class="tile">${this.t("journal.from_mains")}<b>${w.irrigated_mains_l} L</b></div>` : nothing}
        ${w?.pump_kwh ? html`<div class="tile">${this.t("journal.pump_energy")}<b>${w.pump_kwh.toFixed(2)} kWh</b></div>` : nothing}
      </div>
      ${w?.per_day.length ? html`<h3>${this.t("journal.per_day")}</h3><div class="days" role="img" aria-label=${this.t("journal.per_day")}>
        ${w.per_day.map((d) => html`<div title=${`${d.day}: ${d.liters} L`} style=${`height:${(d.liters / max) * 100}%`}></div>`)}</div>` : nothing}
      <p class="xs muted">${this.t("journal.water_hint")}</p>
    </section>
    ${this.renderBedWater()}`;
  }

  /** Per bed: moisture, water given and rain over the last two weeks. */
  private renderBedWater(): TemplateResult | typeof nothing {
    const beds = this.snapshot.beds.filter((b) => b.irrigation_entity || b.sensors?.soil_moisture);
    if (!beds.length) return nothing;
    const bed = beds.find((b) => b.id === this.waterBed) ?? beds[0];
    return html`<section class="card stack" aria-labelledby="wb-h">
      <h2 id="wb-h"><ha-icon icon="mdi:chart-bell-curve"></ha-icon> ${this.t("water.per_bed")}</h2>
      <div class="row wrap">
        <select style="width:auto" aria-label=${this.t("task.bed")} @change=${(e: Event) => (this.waterBed = (e.target as HTMLSelectElement).value)}>
          ${beds.map((b) => html`<option value=${b.id} ?selected=${b.id === bed.id}>${b.name}</option>`)}</select>
        ${[7, 14, 30].map((n) => html`<button class="chip" aria-pressed=${String(this.waterDays === n)} @click=${() => (this.waterDays = n)}>${this.t("water.days", { n })}</button>`)}
      </div>
      <hl-water-chart .bed=${bed} .snapshot=${this.snapshot} .api=${this.api} .t=${this.t} lang=${this.lang} days=${this.waterDays}></hl-water-chart>
      <p class="xs muted">${this.t("water.chart_hint")}</p>
    </section>`;
  }

  // -- system log --------------------------------------------------------------- //
  private async undo(entry: SyslogEntry): Promise<void> {
    if (!confirm(this.t("syslog.confirm", { what: this.entryTitle(entry) }))) return;
    this.busy = true;
    try {
      let res = await this.api.undo(entry.id);
      if (!res.ok && res.conflicts.length && !res.problems.length
        && confirm(this.t("syslog.conflict", { n: res.conflicts.length }))) {
        res = await this.api.undo(entry.id, true);
      }
      if (res.ok) this.toast(this.t("syslog.undone"));
      else if (res.problems.length) this.toast(this.t("syslog.blocked"));
      await this.loadSyslog();
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
    } finally {
      this.busy = false;
    }
  }

  private summaryText(s: SyslogSummary): string {
    let what: string;
    if (s.col === "settings") what = s.key ?? "";
    else if (s.plant_id && (s.col === "plantings" || !s.name)) what = plantName(this.plant(s.plant_id), this.lang) || s.plant_id;
    else what = s.name ?? "";
    const extra = [s.bed, s.col === "plantings" && s.season ? this.t("common.season", { year: s.season }) : null].filter(Boolean).join(", ");
    return `${this.t(`syslog.col.${s.col}`)}: ${what}${extra ? ` (${extra})` : ""}`;
  }

  private entryTitle(e: SyslogEntry): string {
    if (e.source === "error") return `${this.t("syslog.error")}: ${e.summary[0]?.name ?? ""}`;
    if (e.undo_of) return this.t("syslog.reason.undo");
    const first = e.summary[0];
    const ops = new Set(e.summary.map((s) => s.op));
    const verb = ops.size === 1 ? this.t(`syslog.op.${first.op}`) : this.t("syslog.op.mixed");
    return e.summary.length === 1 ? `${verb} – ${this.summaryText(first)}` : this.t("syslog.n_changes", { verb, n: e.count });
  }

  private renderSystem(): TemplateResult {
    const time = (iso: string) => new Date(iso).toLocaleString(this.lang === "nl" ? "nl-NL" : localeOf(this.lang),
      { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
    return html`<section class="card stack" aria-labelledby="sys-h">
      <h2 id="sys-h"><ha-icon icon="mdi:history"></ha-icon> ${this.t("journal.system")}</h2>
      <p class="small muted">${this.t("syslog.intro")}</p>
      <label class="row small"><input type="checkbox" .checked=${this.syslogSystem}
        @change=${(e: Event) => { this.syslogSystem = (e.target as HTMLInputElement).checked; void this.loadSyslog(); }} />${this.t("syslog.show_system")}</label>
      ${this.syslog.length ? nothing : html`<p class="small muted">${this.t("syslog.empty")}</p>`}
      <div class="stack" style="gap:8px" role="list">
        ${this.syslog.map((e) => html`<article role="listitem" class="log ${e.source} ${e.undone_by ? "undone" : ""}">
          <div class="icon"><ha-icon icon=${e.source === "error" ? "mdi:alert-circle-outline" : e.undo_of ? "mdi:undo-variant" : e.source === "system" ? "mdi:robot-outline" : "mdi:account-edit-outline"}></ha-icon></div>
          <div>
            <strong>${this.entryTitle(e)}</strong>
            <div class="meta">${time(e.at)} · ${e.source === "system" ? this.t("syslog.by_system") : e.user ?? this.t("syslog.by_unknown")}
              · ${e.source === "error" ? e.reason : this.t(`syslog.reason.${e.reason}`)}${e.undone_by ? html` · <span class="chip warn">${this.t("syslog.is_undone")}</span>` : nothing}</div>
            ${e.summary.length > 1 ? html`<ul>
              ${e.summary.slice(0, SYSLOG_SHOWN_LINES).map((s) => html`<li><ha-icon icon=${OP_ICON[s.op]}></ha-icon>${this.summaryText(s)}</li>`)}
              ${e.summary.length > SYSLOG_SHOWN_LINES ? html`<li class="muted">${this.t("syslog.and_more", { n: e.summary.length - SYSLOG_SHOWN_LINES })}</li>` : nothing}
            </ul>` : nothing}
          </div>
          ${this.admin && !e.undone_by && e.source !== "error" && e.count > 0 ? html`<button class="btn small ghost" ?disabled=${this.busy} @click=${() => this.undo(e)}
            aria-label=${`${this.t("syslog.undo")}: ${this.entryTitle(e)}`}><ha-icon icon="mdi:undo"></ha-icon>${this.t("syslog.undo")}</button>` : html`<span></span>`}
        </article>`)}
      </div>
      ${this.syslogMore ? html`<div class="row"><button class="btn small" @click=${() => this.loadSyslog(true)}>${this.t("syslog.more")}</button></div>` : nothing}
    </section>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-journal-view": JournalView;
  }
}
