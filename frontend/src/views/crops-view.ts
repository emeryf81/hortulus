// "Crops" tab: every crop of a season in one list - adjust every date, the status,
// the count and notes directly, without dragging anything on the map.
import "../components/crop-gantt";
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { FamilyInfo, Plant, Planting, PlantingStatus, Snapshot, SowMethod, Timeline } from "../types";
import { familyColor, formatDate, plantName } from "../util/garden";
import "../components/plant-image";
import "../components/modal";
import "../components/date-input";
import "../components/quick-note";
import "./crops-planning";
import type { PlanningView } from "./crops-planning";

export interface CropRow { planting: Planting; bed: string | null; zone: string | null; timeline: Timeline | null }

const STATUSES: PlantingStatus[] = ["planned", "sown_indoors", "sown", "transplanted", "harvesting", "finished", "failed"];
const METHODS: SowMethod[] = ["indoor_sow", "direct_sow", "transplant"];
const METHOD_LABEL: Record<SowMethod, string> = { indoor_sow: "lib.indoor_sow", direct_sow: "lib.direct_sow", transplant: "lib.transplant" };
/** Editable date fields: planned (empty = computed) and what actually happened. */
const DATE_FIELDS = ["sow_date", "sown_on", "transplant_date", "transplanted_on", "harvest_started_on", "finished_on"] as const;
type DateField = (typeof DATE_FIELDS)[number];

@customElement("hl-crops-view")
export class CropsView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) plants: Plant[] = [];
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ type: Boolean }) admin = true;
  @property({ type: Number }) initialSeason: number | null = null;
  /** Show this crop (from the planner): highlight its row and open it. */
  @property({ attribute: false }) focusPlanting: { id: string; season: number; n: number } | null = null;
  @state() private picked = new Set<string>();
  @state() private bulkStatus: PlantingStatus | "" = "";
  @state() private bulkField: DateField | "" = "";
  @state() private bulkDate: string | null = null;
  @state() private highlight = "";
  @state() private view: "list" | "timeline" | PlanningView = "list";
  @state() private compact = false;
  private media?: MediaQueryList;
  private onMedia = () => (this.compact = !!this.media?.matches);

  @state() private season = 0;
  @state() private rows: CropRow[] = [];
  @state() private filter = "";
  @state() private group: "bed" | "plant" | "date" = "bed";
  @state() private open: CropRow | null = null;
  @state() private saving = new Set<string>();
  private plantMap = new Map<string, Plant>();
  private reloadTimer?: number;

  static styles = [
    shared,
    css`
      :host { display: block; }
      .top { display: flex; flex-wrap: wrap; gap: var(--hl-s2); align-items: center; margin-bottom: var(--hl-s3); }
      .top input[type="search"] { flex: 1; min-width: 180px; }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); }
      th { text-align: left; font-weight: 600; color: var(--hl-text-muted); padding: 6px; border-bottom: 2px solid var(--hl-border); white-space: nowrap; }
      td { padding: 4px 6px; border-bottom: 1px solid var(--hl-border); vertical-align: middle; }
      tr.group td { background: var(--hl-surface-2); font-weight: 700; padding-top: 10px; }
      td.plant { display: flex; gap: 8px; align-items: center; min-width: 160px; }
      td.plant button { all: unset; cursor: pointer; font-weight: 600; }
      td.plant button:hover { text-decoration: underline; }
      td hl-date-input { width: 136px; }
      td input[type="number"] { width: 64px; min-height: 30px; }
      td select { min-height: 30px; padding: 2px 4px; font-size: var(--hl-fs-sm); width: auto; }
      .computed { font-size: 10px; color: var(--hl-text-muted); display: block; }
      .late { color: var(--hl-warning); }
      .wrap { overflow-x: auto; }
      tr.saving { opacity: 0.6; }
      .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--hl-s2) var(--hl-s3); }
      .full { grid-column: 1 / -1; }
      .kv { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: var(--hl-fs-sm); }
      tr.hl td { background: var(--hl-sun-100); }
      td.plant button.map { font-weight: 400; opacity: 0.7; }
      td.plant button.map:hover { opacity: 1; text-decoration: none; }
      .bulk { display: flex; flex-wrap: wrap; gap: var(--hl-s2) var(--hl-s3); align-items: center; padding: var(--hl-s2) var(--hl-s3); margin-bottom: var(--hl-s2);
        position: sticky; top: 0; z-index: 2; border: 1px solid var(--hl-primary); }
      .bulk label { display: inline-flex; gap: 6px; align-items: center; }
      .views { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: var(--hl-s3); }
      .cards { display: flex; flex-direction: column; gap: var(--hl-s2); }
      .crop-card { background: var(--hl-surface); border: 1px solid var(--hl-border); border-radius: var(--hl-r-lg); padding: var(--hl-s2) var(--hl-s3); display: flex; flex-direction: column; gap: 6px; }
      .crop-card.hl { background: var(--hl-sun-100); }
      .crop-card .name { all: unset; cursor: pointer; font-weight: 600; }
      .crop-card hl-date-input { max-width: none; }
      .bulk select { width: auto; min-height: 30px; }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this.media = window.matchMedia("(max-width: 760px)");
    this.media.addEventListener("change", this.onMedia);
    this.onMedia();
    if (!this.season) this.season = this.initialSeason ?? this.snapshot?.layout_season ?? this.snapshot?.analysis?.season ?? new Date().getFullYear();
    void this.load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.media?.removeEventListener("change", this.onMedia);
    window.clearTimeout(this.reloadTimer);
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("plants")) this.plantMap = new Map(this.plants.map((p) => [p.id, p]));
    if (changed.has("focusPlanting") && this.focusPlanting) void this.showFocus(this.focusPlanting);
    // a selection belongs to the season it was made in
    if (changed.has("season") && changed.get("season") && this.picked.size) this.picked = new Set();
    if (changed.has("snapshot") && changed.get("snapshot") !== undefined && !this.saving.size) {
      window.clearTimeout(this.reloadTimer);
      this.reloadTimer = window.setTimeout(() => void this.load(), 600);
    }
  }

  private async showFocus(focus: { id: string; season: number }): Promise<void> {
    if (focus.season !== this.season) {
      this.season = focus.season;
      await this.load();
    } else if (!this.rows.length) {
      await this.load();
    }
    const row = this.rows.find((r) => r.planting.id === focus.id);
    if (!row) return;
    this.filter = "";
    this.highlight = focus.id;
    this.open = row;
    await this.updateComplete;
    this.renderRoot.querySelector(`[data-id="${focus.id}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  private emit(name: string, detail: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  private togglePick(id: string, on: boolean): void {
    const next = new Set(this.picked);
    on ? next.add(id) : next.delete(id);
    this.picked = next;
  }

  /** The same status and/or date for every ticked crop. */
  private async applyBulk(): Promise<void> {
    const changes: Partial<Planting> = {};
    if (this.bulkStatus) changes.status = this.bulkStatus;
    if (this.bulkField) (changes as Record<string, unknown>)[this.bulkField] = this.bulkDate;
    if (!Object.keys(changes).length || !this.picked.size) return;
    try {
      const res = await this.api.updatePlantings([...this.picked], changes);
      this.toast(this.t("crops.bulk_done", { n: res.updated }));
      this.picked = new Set();
      await this.load();
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
    }
  }

  private renderBulk(): TemplateResult | typeof nothing {
    if (!this.admin || !this.picked.size) return nothing;
    return html`<div class="bulk card" role="region" aria-label=${this.t("crops.bulk")}>
      <b>${this.t("crops.bulk_n", { n: this.picked.size })}</b>
      <label class="small">${this.t("crops.status")}
        <select @change=${(e: Event) => (this.bulkStatus = (e.target as HTMLSelectElement).value as PlantingStatus | "")}>
          <option value="">–</option>${STATUSES.map((st) => html`<option value=${st} ?selected=${this.bulkStatus === st}>${this.t(`status.${st}`)}</option>`)}
        </select></label>
      <label class="small">${this.t("crops.bulk_date")}
        <select @change=${(e: Event) => (this.bulkField = (e.target as HTMLSelectElement).value as DateField | "")}>
          <option value="">–</option>${DATE_FIELDS.map((f) => html`<option value=${f} ?selected=${this.bulkField === f}>${this.t(`crops.field.${f}`)}</option>`)}
        </select></label>
      ${this.bulkField ? html`<hl-date-input .value=${this.bulkDate ?? ""} lang=${this.lang} label=${this.t(`crops.field.${this.bulkField}`)}
        pickLabel=${this.t("crops.pick_date")} @date-change=${(e: CustomEvent<string | null>) => (this.bulkDate = e.detail)}></hl-date-input>
        <button class="chip" @click=${() => (this.bulkDate = this.snapshot.analysis?.today ?? new Date().toISOString().slice(0, 10))}>${this.t("common.today")}</button>` : nothing}
      <span class="spacer"></span>
      <button class="btn primary small" ?disabled=${!this.bulkStatus && !this.bulkField} @click=${() => this.applyBulk()}>${this.t("crops.bulk_apply")}</button>
      <button class="btn ghost small" @click=${() => (this.picked = new Set())}>${this.t("common.cancel")}</button>
    </div>`;
  }

  private async load(): Promise<void> {
    try {
      this.rows = (await this.api.plantingsSeason(this.season)).rows;
      if (this.open) this.open = this.rows.find((r) => r.planting.id === this.open!.planting.id) ?? null;
    } catch {
      /* older backend */
    }
  }

  private toast(message: string): void {
    this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message }, bubbles: true, composed: true }));
  }

  private async saveRow(row: CropRow, changes: Partial<Planting>): Promise<void> {
    const id = row.planting.id;
    this.saving = new Set([...this.saving, id]);
    try {
      const res = await this.api.updatePlanting(id, changes);
      if (res.row) {
        this.rows = this.rows.map((r) => (r.planting.id === id ? res.row! : r));
        if (this.open?.planting.id === id) this.open = res.row;
      }
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message ?? String(err) }));
      await this.load();
    } finally {
      const next = new Set(this.saving);
      next.delete(id);
      this.saving = next;
    }
  }

  /** The date the plan uses when a field is left empty. */
  private computed(row: CropRow, field: DateField): string | null {
    const tl = row.timeline;
    if (!tl) return null;
    if (field === "sow_date") return tl.sow_date;
    if (field === "transplant_date") return tl.transplant_date;
    if (field === "harvest_started_on") return tl.harvest_start;
    if (field === "finished_on") return tl.harvest_end;
    return null;
  }

  private dateInput(row: CropRow, field: DateField): TemplateResult {
    const value = (row.planting[field] as string | null | undefined) ?? "";
    const computed = this.computed(row, field);
    return html`<hl-date-input .value=${value} lang=${this.lang} ?disabled=${!this.admin} label=${this.t(`crops.field.${field}`)} pickLabel=${this.t("crops.pick_date")}
      @date-change=${(e: CustomEvent<string | null>) => this.saveRow(row, { [field]: e.detail } as Partial<Planting>)}></hl-date-input>
      ${!value && computed ? html`<span class="computed">${this.t("crops.computed")}: ${formatDate(computed, this.lang)}</span>` : nothing}`;
  }

  private icon(row: CropRow, size: "thumb" = "thumb"): TemplateResult | typeof nothing {
    const plant = this.plantMap.get(row.planting.plant_id);
    return plant ? html`<hl-plant-image .plant=${plant} color=${familyColor(this.families, plant.family)} lang=${this.lang} size=${size}
      style="width:32px;height:32px"></hl-plant-image>` : nothing;
  }

  private visibleRows(): CropRow[] {
    const q = this.filter.trim().toLowerCase();
    const rows = this.rows.filter((r) => !q || [plantName(this.plantMap.get(r.planting.plant_id), this.lang), r.bed ?? "", r.zone ?? ""]
      .some((s) => s.toLowerCase().includes(q)));
    const key = (r: CropRow) => this.group === "bed" ? `${r.zone ?? ""} ${r.bed ?? ""}` : this.group === "plant"
      ? plantName(this.plantMap.get(r.planting.plant_id), this.lang) : (r.timeline?.in_ground ?? "");
    return rows.sort((a, b) => key(a).localeCompare(key(b)) || plantName(this.plantMap.get(a.planting.plant_id), this.lang)
      .localeCompare(plantName(this.plantMap.get(b.planting.plant_id), this.lang)));
  }

  render(): TemplateResult {
    const views: ["list" | "timeline" | PlanningView, string][] = [["list", "mdi:table"], ["timeline", "mdi:chart-gantt"], ["weeks", "mdi:calendar-week"], ["seeds", "mdi:seed-outline"],
      ["follow", "mdi:swap-horizontal"], ["harvest", "mdi:basket-outline"]];
    return html`
      <div class="views" role="tablist">${views.map(([id, icon]) => html`<button class="chip" role="tab" aria-selected=${String(this.view === id)}
        @click=${() => (this.view = id)}><ha-icon icon=${icon}></ha-icon>${this.t(`crops.view.${id}`)}</button>`)}</div>
      ${this.view === "list" ? this.renderList() : this.view === "timeline" ? html`${this.renderSeasonPick()}
        <section class="card"><hl-crop-gantt .rows=${this.rows} .plants=${this.plantMap} .families=${this.families} .t=${this.t} lang=${this.lang}
          season=${this.season} today=${this.snapshot.analysis?.today ?? ""} ?south=${this.snapshot.settings.region?.hemisphere === "south"} ?admin=${this.admin}
          @move-planting=${(e: CustomEvent<{ row: CropRow; changes: Partial<Planting> }>) => this.saveRow(e.detail.row, e.detail.changes)}></hl-crop-gantt></section>` : html`${this.renderSeasonPick()}
        <hl-crops-planning .snapshot=${this.snapshot} .api=${this.api} .t=${this.t} lang=${this.lang} .plants=${this.plantMap} .families=${this.families}
          .rows=${this.rows} season=${this.season} view=${this.view} ?admin=${this.admin} @crops-changed=${() => this.load()}></hl-crops-planning>`}
      ${this.open ? this.renderDetail(this.open) : nothing}`;
  }

  private renderSeasonPick(): TemplateResult {
    const seasons = [this.season - 1, this.season, this.season + 1];
    return html`<select style="width:auto;margin-bottom:var(--hl-s2)" aria-label=${this.t("planner.season")} @change=${(e: Event) => { this.season = Number((e.target as HTMLSelectElement).value); void this.load();
      this.dispatchEvent(new CustomEvent("season-changed", { detail: this.season, bubbles: true, composed: true })); }}>
      ${seasons.map((s) => html`<option value=${s} ?selected=${s === this.season}>${this.t("common.season", { year: s })}</option>`)}
    </select>`;
  }

  /** On a phone: one card per crop instead of the wide table. */
  private renderCards(rows: CropRow[]): TemplateResult {
    return html`<div class="cards">${rows.map((r) => {
      const p = r.planting;
      const tl = r.timeline;
      // the next real date to fill in, from the status as well as the dates already known
      const rank = ({ planned: 0, sown_indoors: 1, sown: 2, transplanted: 3, harvesting: 4 } as Record<string, number>)[p.status] ?? 5;
      const next = !p.sown_on && rank < 1 && p.method !== "transplant" ? ["sown_on"] : !p.transplanted_on && rank < 3 && p.method !== "direct_sow"
        ? ["transplanted_on"] : !p.harvest_started_on && rank < 4 ? ["harvest_started_on"] : ["finished_on"];
      return html`<article class="crop-card ${this.highlight === p.id ? "hl" : ""}" data-id=${p.id}>
        <div class="row" style="gap:8px">${this.icon(r)}
          <button class="name" @click=${() => (this.open = r)}>${plantName(this.plantMap.get(p.plant_id), this.lang) || p.plant_id}</button>
          <span class="spacer"></span><span class="chip">${this.t(`status.${p.status}`)}</span></div>
        <div class="xs muted">${r.zone ?? ""} · ${r.bed ?? this.t("crops.no_bed")}${tl?.late ? ` · ⚠ ${this.t("crops.late")}` : ""}</div>
        <label class="field">${this.t(`crops.field.${next[0]}`)}${this.dateInput(r, next[0] as DateField)}</label>
        <div class="row wrap" style="gap:6px">
          <button class="btn small ghost" @click=${() => (this.open = r)}>${this.t("crops.all_dates")}</button>
          ${r.bed ? html`<button class="btn small ghost" @click=${() => this.emit("focus-planting", { planting_id: p.id, season: this.season })}>🗺 ${this.t("crops.show_on_map")}</button>` : nothing}
        </div>
      </article>`;
    })}</div>`;
  }

  private renderList(): TemplateResult {
    const seasons = [this.season - 1, this.season, this.season + 1];
    const rows = this.visibleRows();
    let lastGroup = "";
    return html`
      <div class="top">
        <select style="width:auto" aria-label=${this.t("planner.season")} @change=${(e: Event) => { this.season = Number((e.target as HTMLSelectElement).value); void this.load();
          this.dispatchEvent(new CustomEvent("season-changed", { detail: this.season, bubbles: true, composed: true })); }}>
          ${seasons.map((s) => html`<option value=${s} ?selected=${s === this.season}>${this.t("common.season", { year: s })}</option>`)}
        </select>
        <input type="search" placeholder=${this.t("crops.search")} .value=${this.filter} @input=${(e: Event) => (this.filter = (e.target as HTMLInputElement).value)} />
        <span class="small">${this.t("crops.group")}:</span>
        ${(["bed", "plant", "date"] as const).map((g) => html`<button class="chip" aria-pressed=${String(this.group === g)} @click=${() => (this.group = g)}>${this.t(`crops.group.${g}`)}</button>`)}
        <span class="small muted">${this.t("planner.count", { n: rows.length })}</span>
      </div>
      <p class="small muted">${this.t("crops.intro")}</p>
      ${this.renderBulk()}
      ${rows.length && this.compact ? this.renderCards(rows) : rows.length ? html`<div class="card wrap"><table>
        <thead><tr>${this.admin ? html`<th><input type="checkbox" aria-label=${this.t("crops.pick_all")} .checked=${rows.length > 0 && rows.every((r) => this.picked.has(r.planting.id))}
          @change=${(e: Event) => (this.picked = (e.target as HTMLInputElement).checked ? new Set(rows.map((r) => r.planting.id)) : new Set())} /></th>` : nothing}<th>${this.t("lib.plant")}</th><th>${this.t("task.bed")}</th><th>${this.t("crops.method")}</th><th>${this.t("crops.status")}</th>
          ${DATE_FIELDS.map((f) => html`<th>${this.t(`crops.field.${f}`)}</th>`)}<th>#</th></tr></thead>
        <tbody>${rows.map((r) => {
          const g = this.group === "bed" ? `${r.zone ?? "?"} · ${r.bed ?? this.t("crops.no_bed")}` : "";
          const header = g && g !== lastGroup ? html`<tr class="group"><td colspan=${6 + DATE_FIELDS.length}>${g}</td></tr>` : nothing;
          lastGroup = g || lastGroup;
          const p = r.planting;
          return html`${header}<tr data-id=${p.id} class="${this.saving.has(p.id) ? "saving" : ""} ${this.highlight === p.id ? "hl" : ""}">
            ${this.admin ? html`<td><input type="checkbox" aria-label=${plantName(this.plantMap.get(p.plant_id), this.lang)} .checked=${this.picked.has(p.id)}
              @change=${(e: Event) => this.togglePick(p.id, (e.target as HTMLInputElement).checked)} /></td>` : nothing}
            <td class="plant">${this.icon(r)}<button @click=${() => (this.open = r)}>${plantName(this.plantMap.get(p.plant_id), this.lang) || p.plant_id}</button>
              ${r.bed ? html`<button class="map" title=${this.t("crops.show_on_map")} aria-label=${this.t("crops.show_on_map")}
                @click=${() => this.emit("focus-planting", { planting_id: p.id, season: this.season })}>🗺</button>` : nothing}
              ${r.timeline?.late ? html`<ha-icon class="late" icon="mdi:clock-alert-outline" title=${this.t("crops.late")}></ha-icon>` : nothing}</td>
            <td>${r.bed ?? html`<span class="late">${this.t("crops.no_bed")}</span>`}</td>
            <td><select ?disabled=${!this.admin} aria-label=${`${this.t("crops.method")} · ${plantName(this.plantMap.get(p.plant_id), this.lang) || p.plant_id}`} @change=${(e: Event) => this.saveRow(r, { method: (e.target as HTMLSelectElement).value as SowMethod })}>
              ${METHODS.map((m) => html`<option value=${m} ?selected=${p.method === m}>${this.t(METHOD_LABEL[m])}</option>`)}</select></td>
            <td><select ?disabled=${!this.admin} aria-label=${`${this.t("crops.status")} · ${plantName(this.plantMap.get(p.plant_id), this.lang) || p.plant_id}`} @change=${(e: Event) => this.saveRow(r, { status: (e.target as HTMLSelectElement).value as PlantingStatus })}>
              ${STATUSES.map((s) => html`<option value=${s} ?selected=${p.status === s}>${this.t(`status.${s}`)}</option>`)}</select></td>
            ${DATE_FIELDS.map((f) => html`<td>${this.dateInput(r, f)}</td>`)}
            <td><input type="number" min="0" .value=${p.count == null ? "" : String(p.count)} placeholder="auto" ?disabled=${!this.admin}
              @change=${(e: Event) => this.saveRow(r, { count: (e.target as HTMLInputElement).value === "" ? null : Number((e.target as HTMLInputElement).value) })} /></td>
          </tr>`;
        })}</tbody></table></div>` : html`<p class="muted">${this.t("crops.none", { season: this.season })}</p>`}`;
  }

  /** Popup with everything about one crop. */
  private renderDetail(r: CropRow): TemplateResult {
    const p = r.planting;
    const plant = this.plantMap.get(p.plant_id);
    const tl = r.timeline;
    const list = this.visibleRows();
    const i = list.findIndex((x) => x.planting.id === p.id);
    const line = (label: string, a?: string | null, b?: string | null) => (a ? html`<span>${label}</span><span>${formatDate(a, this.lang)}${b ? ` – ${formatDate(b, this.lang)}` : ""}</span>` : nothing);
    return html`<hl-modal heading=${plantName(plant, this.lang)} subheading=${`${r.zone ?? ""} · ${r.bed ?? ""} · ${this.t("common.season", { year: p.season })}`}
      accent=${plant ? familyColor(this.families, plant.family) : ""} nav ?has-prev=${i > 0} ?has-next=${i >= 0 && i < list.length - 1}
      closeLabel=${this.t("common.close")} prevLabel=${this.t("common.previous")} nextLabel=${this.t("common.next")}
      @prev=${() => (this.open = list[i - 1])} @next=${() => (this.open = list[i + 1])} @closed=${() => (this.open = null)}>
      ${plant ? html`<hl-plant-image .plant=${plant} color=${familyColor(this.families, plant.family)} lang=${this.lang} size="card" credit></hl-plant-image>` : nothing}
      ${tl ? html`<div class="kv">
        ${line(this.t("crops.window.sow"), tl.sow_window?.start, tl.sow_window?.end)}
        ${line(this.t("crops.window.transplant"), tl.transplant_window?.start, tl.transplant_window?.end)}
        ${line(this.t("crops.in_ground"), tl.in_ground)}
        ${line(this.t("crops.harvest"), tl.harvest_start, tl.harvest_end)}
      </div>${tl.late ? html`<div class="finding warning"><ha-icon icon="mdi:clock-alert-outline"></ha-icon><span>${this.t("crops.late")}</span></div>` : nothing}` : nothing}
      <div class="form-grid">
        <label class="field">${this.t("crops.method")}<select ?disabled=${!this.admin} @change=${(e: Event) => this.saveRow(r, { method: (e.target as HTMLSelectElement).value as SowMethod })}>
          ${METHODS.map((m) => html`<option value=${m} ?selected=${p.method === m}>${this.t(METHOD_LABEL[m])}</option>`)}</select></label>
        <label class="field">${this.t("crops.status")}<select ?disabled=${!this.admin} @change=${(e: Event) => this.saveRow(r, { status: (e.target as HTMLSelectElement).value as PlantingStatus })}>
          ${STATUSES.map((st) => html`<option value=${st} ?selected=${p.status === st}>${this.t(`status.${st}`)}</option>`)}</select></label>
        ${DATE_FIELDS.map((f) => html`<label class="field">${this.t(`crops.field.${f}`)}${this.dateInput(r, f)}</label>`)}
        <label class="field">${this.t("crops.count")}<input type="number" min="0" .value=${p.count == null ? "" : String(p.count)} placeholder="auto" ?disabled=${!this.admin}
          @change=${(e: Event) => this.saveRow(r, { count: (e.target as HTMLInputElement).value === "" ? null : Number((e.target as HTMLInputElement).value) })} /></label>
        <label class="field full">${this.t("crops.notes")}<textarea .value=${p.notes ?? ""} ?disabled=${!this.admin}
          @change=${(e: Event) => this.saveRow(r, { notes: (e.target as HTMLTextAreaElement).value })}></textarea></label>
      </div>
      <details><summary class="small">${this.t("note.title")}</summary>
        <hl-quick-note .snapshot=${this.snapshot} .api=${this.api} .t=${this.t} lang=${this.lang} plantingId=${p.id} ?admin=${this.admin}></hl-quick-note></details>
      <p class="xs muted">${this.t("crops.detail_hint")}</p>
      <div slot="actions" class="row wrap">
        ${r.bed ? html`<button class="btn small" @click=${() => this.emit("focus-planting", { planting_id: p.id, season: p.season })}>🗺 ${this.t("crops.show_on_map")}</button>` : nothing}
        <button class="btn small ghost" @click=${() => this.emit("open-plant", p.plant_id)}>${this.t("planner.plant_info")}</button>
      </div>
    </hl-modal>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-crops-view": CropsView;
  }
}
