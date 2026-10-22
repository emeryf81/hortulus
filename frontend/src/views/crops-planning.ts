// Planning views in the Crops tab:
//  - weeks:   what to sow inside / outside, plant out and start harvesting, week by week,
//             with "Done" that fills in the real date;
//  - seeds:   seeds the plan still needs against the seed stock;
//  - follow:  beds that empty out this season and what can follow there;
//  - harvest: expected kg per week.
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import { shared } from "../styles/tokens";
import type { FamilyInfo, Plant, Planting, PlantingStatus, Snapshot } from "../types";
import { addDays, familyColor, formatDate, plantName } from "../util/garden";
import type { CropRow } from "./crops-view";

export type PlanningView = "weeks" | "seeds" | "follow" | "harvest";

interface PlanningResult {
  season: number;
  seeds: { plant_id: string; plants: number; seeds: number; plantings: string[]; stock: { quantity: number; unit: string; variety: string; year: number | null }[]; status: "ok" | "check" | "short" | "none"; to_buy: number }[];
  successions: { bed_id: string; free_from: string; leaving: string[]; options: { plant_id: string; harvest_by: string; days: number }[] }[];
  harvest: {
    weeks: { week: string; kg: number; by_plant: Record<string, number> }[]; totals: Record<string, number>; learned: string[];
    learned_detail?: Record<string, { kg_m2: number | null; seasons: number; first_harvest_days: number | null }>;
  };
}

type Action = "sow_indoor" | "sow_direct" | "transplant" | "harvest";
interface WeekItem { row: CropRow; action: Action; date: string; done: boolean }

/** Monday of the week ``iso`` falls in. */
function monday(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return addDays(iso, -((d.getDay() + 6) % 7));
}

@customElement("hl-crops-planning")
export class CropsPlanning extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property({ attribute: false }) plants = new Map<string, Plant>();
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property({ attribute: false }) rows: CropRow[] = [];
  @property() lang = "en";
  @property({ type: Number }) season = 0;
  @property() view: PlanningView = "weeks";
  @property({ type: Boolean }) admin = true;
  @state() private result: PlanningResult | null = null;
  @state() private weeksAhead = 8;
  private loadedFor = 0;
  @state() private error = "";
  @state() private todoList = "";
  @state() private todoBusy = false;
  @state() private todoMsg = "";

  static styles = [
    shared,
    css`
      :host { display: block; }
      .week { margin-bottom: var(--hl-s3); }
      .week h3 { margin: 0 0 6px; font-size: var(--hl-fs-md); }
      .item { display: flex; gap: 8px; align-items: center; padding: 6px 8px; border-radius: var(--hl-r-md); background: var(--hl-surface); border: 1px solid var(--hl-border); margin-bottom: 4px; }
      .item.done { opacity: 0.55; }
      .item .grow { flex: 1; min-width: 0; }
      .act { font-size: var(--hl-fs-xs); padding: 1px 8px; border-radius: 10px; background: var(--hl-surface-2); white-space: nowrap; }
      .act.sow_indoor { background: var(--hl-leaf-100); }
      .act.sow_direct { background: var(--hl-sun-100); }
      .act.transplant { background: var(--hl-frost-100, #e3f0fb); }
      .act.harvest { background: var(--hl-tomato-100, #fde3dc); }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); }
      th, td { text-align: left; padding: 6px; border-bottom: 1px solid var(--hl-border); }
      .bars { display: flex; align-items: flex-end; gap: 3px; height: 160px; padding-top: 10px; }
      .bars .b { flex: 1; background: var(--hl-leaf-500); border-radius: 3px 3px 0 0; min-height: 1px; position: relative; }
      .bars .b.now { background: var(--hl-sun-500); }
      .axis { display: flex; gap: 3px; font-size: 9px; color: var(--hl-text-muted); }
      .axis span { flex: 1; text-align: center; overflow: hidden; }
      .bed { border: 1px solid var(--hl-border); border-radius: var(--hl-r-md); padding: var(--hl-s2) var(--hl-s3); margin-bottom: var(--hl-s2); }
      .opts { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
      .opts .chip, .plant { display: inline-flex; align-items: center; gap: 4px; }
      .plant-btn { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
    `,
  ];

  protected willUpdate(): void {
    // one request per season serves the seeds, succession and harvest views
    if (this.view !== "weeks" && this.api && this.season !== this.loadedFor) {
      const season = this.season;
      this.loadedFor = season;
      this.result = null;
      this.error = "";
      this.api.planning(season).then((r) => {
        if (season === this.season) this.result = r as PlanningResult;
      }).catch((err) => {
        if (season !== this.season) return;
        this.loadedFor = 0; // a later update may retry
        this.error = (err as Error).message ?? String(err);
      });
    }
  }

  private plant(id: string): TemplateResult {
    const p = this.plants.get(id);
    return html`<button class="plant-btn" title=${this.t("lib.open_plant")}
      @click=${() => this.dispatchEvent(new CustomEvent("open-plant", { detail: id, bubbles: true, composed: true }))}>
      ${p ? glyphIcon(glyphFor(p), p.color || familyColor(this.families, p.family), 20) : nothing}<span>${plantName(p, this.lang) || id}</span></button>`;
  }

  render(): TemplateResult {
    if (this.view === "weeks") return this.renderWeeks();
    if (this.error) return html`<p class="small">${this.t("common.error", { message: this.error })}</p>`;
    if (!this.result) return html`<p class="muted">${this.t("common.loading")}</p>`;
    if (this.view === "seeds") return this.renderSeeds(this.result);
    if (this.view === "follow") return this.renderFollow(this.result);
    return this.renderHarvest(this.result);
  }

  // -- weeks ------------------------------------------------------------------ //
  private items(): WeekItem[] {
    const out: WeekItem[] = [];
    const rank: Record<string, number> = { planned: 0, sown_indoors: 1, sown: 2, transplanted: 3, harvesting: 4, finished: 5, failed: 5 };
    for (const row of this.rows) {
      const p = row.planting;
      const tl = row.timeline;
      if (!tl || p.status === "failed" || p.status === "finished") continue;
      const r = rank[p.status] ?? 0;
      // a perennial carried into this year was sown/planted in an earlier one
      const established = p.season < this.season;
      const sow = p.sow_date ?? tl.sow_date;
      if (!established && p.method === "indoor_sow" && sow) out.push({ row, action: "sow_indoor", date: sow, done: !!p.sown_on || r >= 1 });
      if (!established && p.method === "direct_sow" && sow) out.push({ row, action: "sow_direct", date: sow, done: !!p.sown_on || r >= 2 });
      const tp = p.transplant_date ?? tl.transplant_date;
      if (!established && p.method !== "direct_sow" && tp) out.push({ row, action: "transplant", date: tp, done: !!p.transplanted_on || r >= 3 });
      if (tl.harvest_start) out.push({ row, action: "harvest", date: tl.harvest_start, done: !!p.harvest_started_on || r >= 4 });
    }
    return out;
  }

  private async done(item: WeekItem): Promise<void> {
    const today = this.snapshot.analysis?.today ?? new Date().toISOString().slice(0, 10);
    const changes: Partial<Planting> = item.action === "sow_indoor" ? { sown_on: today, status: "sown_indoors" as PlantingStatus }
      : item.action === "sow_direct" ? { sown_on: today, status: "sown" as PlantingStatus }
      : item.action === "transplant" ? { transplanted_on: today, status: "transplanted" as PlantingStatus }
      : { harvest_started_on: today, status: "harvesting" as PlantingStatus };
    try {
      await this.api.updatePlanting(item.row.planting.id, changes);
      this.dispatchEvent(new CustomEvent("crops-changed", { bubbles: true, composed: true }));
    } catch (err) {
      this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message: this.t("common.error", { message: (err as Error).message }) }, bubbles: true, composed: true }));
    }
  }

  private renderWeeks(): TemplateResult {
    const today = this.snapshot.analysis?.today ?? new Date().toISOString().slice(0, 10);
    const first = monday(today);
    const last = addDays(first, this.weeksAhead * 7);
    const items = this.items();
    const overdue = items.filter((i) => !i.done && i.date < first);
    const byWeek = new Map<string, WeekItem[]>();
    for (const i of items) {
      if (i.date < first || i.date >= last) continue;
      const w = monday(i.date);
      byWeek.set(w, [...(byWeek.get(w) ?? []), i]);
    }
    const weeks = Array.from({ length: this.weeksAhead }, (_, k) => addDays(first, k * 7));
    const line = (i: WeekItem) => html`<div class="item ${i.done ? "done" : ""}">
      <span class="act ${i.action}">${this.t(`plan.act.${i.action}`)}</span>
      <span class="grow">${this.plant(i.row.planting.plant_id)} <span class="xs muted">· ${i.row.bed ?? "–"} · ${formatDate(i.date, this.lang, { weekday: "short", day: "numeric", month: "short" })}</span></span>
      ${i.done ? html`<span class="xs">✓</span>` : this.admin ? html`<button class="btn small" @click=${() => this.done(i)}>${this.t("plan.done")}</button>` : nothing}
    </div>`;
    return html`<section class="card stack">
      <div class="row wrap"><h2 style="margin:0">${this.t("plan.weeks_title")}</h2><span class="spacer"></span>
        ${[4, 8, 12].map((n) => html`<button class="chip" aria-pressed=${String(this.weeksAhead === n)} @click=${() => (this.weeksAhead = n)}>${this.t("plan.n_weeks", { n })}</button>`)}</div>
      <p class="small muted">${this.t("plan.weeks_intro")}</p>
      ${overdue.length ? html`<div class="week"><h3 class="bad-text">${this.t("plan.overdue", { n: overdue.length })}</h3>${overdue.map(line)}</div>` : nothing}
      ${weeks.map((w) => {
        const list = (byWeek.get(w) ?? []).sort((a, b) => a.date.localeCompare(b.date));
        return html`<div class="week"><h3>${this.t("plan.week_of", { date: formatDate(w, this.lang, { day: "numeric", month: "long" }) })}${w === first ? ` · ${this.t("common.today")}` : ""}</h3>
          ${list.length ? list.map(line) : html`<p class="xs muted">–</p>`}</div>`;
      })}
    </section>`;
  }

  // -- seeds ------------------------------------------------------------------ //
  private renderSeeds(r: PlanningResult): TemplateResult {
    const label = (s: PlanningResult["seeds"][number]) => s.stock.map((x) => `${x.quantity} ${this.t(`journal.unit.${x.unit}`)}${x.year ? ` (${x.year})` : ""}`).join(", ");
    return html`<section class="card stack">
      <h2 style="margin:0">${this.t("plan.seeds_title", { season: r.season })}</h2>
      <p class="small muted">${this.t("plan.seeds_intro")}</p>
      ${r.seeds.length ? html`<table>
        <thead><tr><th>${this.t("lib.plant")}</th><th>${this.t("plan.plants")}</th><th>${this.t("plan.seeds")}</th><th>${this.t("plan.in_stock")}</th><th>${this.t("plan.to_buy")}</th><th></th></tr></thead>
        <tbody>${r.seeds.map((s) => html`<tr>
          <td>${this.plant(s.plant_id)}</td><td>${s.plants}</td><td>~${s.seeds}</td><td class="small">${label(s) || "–"}</td>
          <td>${s.status === "short" || s.status === "none" ? (s.to_buy ? `~${s.to_buy}` : "✓") : "–"}</td>
          <td><span class="chip ${s.status === "ok" ? "ok" : s.status === "check" ? "" : "bad"}">${this.t(`plan.seed.${s.status}`)}</span></td>
        </tr>`)}</tbody></table>
        <p class="xs muted">${this.t("plan.seeds_hint")}</p>
        ${this.renderTodo(r)}` : html`<p class="muted">${this.t("plan.seeds_none")}</p>`}
    </section>`;
  }

  /** Send the seeds still missing to a Home Assistant to-do list (a shopping list). */
  private renderTodo(r: PlanningResult): TemplateResult | typeof nothing {
    const missing = r.seeds.filter((s) => s.status === "short" || s.status === "none").length;
    if (!missing) return nothing;
    const lists = this.api.todoLists();
    if (!lists.length) return html`<p class="xs muted">${this.t("plan.todo_none")}</p>`;
    let saved = this.todoList;
    if (!saved) {
      try {
        saved = localStorage.getItem("hortulus.seed_todo") ?? "";
      } catch {
        /* private mode */
      }
    }
    const list = lists.some((l) => l.entity_id === saved) ? saved : lists.find((l) => l.entity_id.includes("shopping"))?.entity_id ?? lists[0].entity_id;
    const send = async () => {
      this.todoBusy = true;
      this.todoMsg = "";
      try {
        localStorage.setItem("hortulus.seed_todo", list);
      } catch {
        /* private mode */
      }
      try {
        const res = await this.api.seedsToTodo(r.season, list);
        this.todoMsg = this.t("plan.todo_done", { added: res.added, skipped: res.skipped });
      } catch (err) {
        this.todoMsg = (err as Error).message;
      } finally {
        this.todoBusy = false;
      }
    };
    return html`<div class="row wrap" style="align-items:end">
      <label class="field">${this.t("plan.todo_list")}
        <select @change=${(e: Event) => (this.todoList = (e.target as HTMLSelectElement).value)}>
          ${lists.map((l) => html`<option value=${l.entity_id} ?selected=${l.entity_id === list}>${l.name}</option>`)}</select></label>
      <button class="btn small" ?disabled=${this.todoBusy} @click=${send}><ha-icon icon="mdi:cart-plus"></ha-icon>${this.t("plan.todo_send", { n: missing })}</button>
      ${this.todoMsg ? html`<span class="small muted" role="status">${this.todoMsg}</span>` : nothing}
    </div>`;
  }

  // -- what follows ------------------------------------------------------------ //
  private renderFollow(r: PlanningResult): TemplateResult {
    const beds = new Map<string, string>();
    for (const layout of [{ beds: this.snapshot.beds }, ...Object.values(this.snapshot.layouts ?? {})]) for (const b of layout.beds) beds.set(b.id, b.name);
    return html`<section class="card stack">
      <h2 style="margin:0">${this.t("plan.follow_title")}</h2>
      <p class="small muted">${this.t("plan.follow_intro")}</p>
      ${r.successions.length ? r.successions.map((b) => html`<div class="bed">
        <b>${beds.get(b.bed_id) ?? b.bed_id}</b> <span class="small muted">· ${this.t("plan.free_from", { date: formatDate(b.free_from, this.lang, { day: "numeric", month: "long" }) })}
          · ${this.t("plan.after", { plants: b.leaving.map((id) => plantName(this.plants.get(id), this.lang)).join(", ") })}</span>
        <div class="opts">${b.options.length ? b.options.map((o) => html`<span class="chip">${this.plant(o.plant_id)}
          <span class="xs muted">${this.t("plan.ready_by", { date: formatDate(o.harvest_by, this.lang, { day: "numeric", month: "short" }) })}</span></span>`)
          : html`<span class="small muted">${this.t("plan.follow_nothing")}</span>`}</div>
      </div>`) : html`<p class="muted">${this.t("plan.follow_none")}</p>`}
    </section>`;
  }

  // -- harvest ------------------------------------------------------------------ //
  private renderHarvest(r: PlanningResult): TemplateResult {
    // no empty weeks before the first or after the last harvest
    const all = r.harvest.weeks;
    const firstIdx = all.findIndex((w) => w.kg >= 0.05);
    const lastIdx = all.length - 1 - [...all].reverse().findIndex((w) => w.kg >= 0.05);
    const weeks = firstIdx < 0 ? [] : all.slice(firstIdx, lastIdx + 1);
    const max = Math.max(0.1, ...weeks.map((w) => w.kg));
    const now = monday(this.snapshot.analysis?.today ?? new Date().toISOString().slice(0, 10));
    const total = Object.values(r.harvest.totals).reduce((a, b) => a + b, 0);
    return html`<section class="card stack">
      <h2 style="margin:0">${this.t("plan.harvest_title", { season: r.season })}</h2>
      <p class="small muted">${this.t("plan.harvest_intro", { kg: Math.round(total) })}</p>
      ${weeks.length ? html`
        <div class="bars" role="img" aria-label=${this.t("plan.harvest_title", { season: r.season })}>
          ${weeks.map((w) => html`<div class="b ${w.week === now ? "now" : ""}" style=${`height:${(w.kg / max) * 100}%`}
            title=${`${formatDate(w.week, this.lang, { day: "numeric", month: "short" })}: ${w.kg} kg – ${Object.entries(w.by_plant).sort((a, b) => b[1] - a[1]).slice(0, 4)
              .map(([id, kg]) => `${plantName(this.plants.get(id), this.lang)} ${kg}`).join(", ")}`}></div>`)}
        </div>
        <div class="axis">${weeks.map((w, i) => html`<span>${i % 4 === 0 ? formatDate(w.week, this.lang, { day: "numeric", month: "numeric" }) : ""}</span>`)}</div>
        <table><thead><tr><th>${this.t("lib.plant")}</th><th>kg</th><th></th></tr></thead>
          <tbody>${Object.entries(r.harvest.totals).map(([id, kg]) => html`<tr><td>${this.plant(id)}</td><td>${kg}</td>
            <td class="xs muted">${r.harvest.learned.includes(id) ? this.learnedNote(r.harvest.learned_detail?.[id]) : this.t("plan.book_yield")}</td></tr>`)}</tbody></table>`
        : html`<p class="muted">${this.t("plan.harvest_none")}</p>`}
    </section>`;
  }

  /** "your yield · 2 seasons · first harvest after 64 days" */
  private learnedNote(d?: { kg_m2: number | null; seasons: number; first_harvest_days: number | null }): string {
    const parts = [this.t("plan.learned")];
    if (d?.seasons) parts.push(this.t("plan.learned_seasons", { n: d.seasons }));
    if (d?.first_harvest_days) parts.push(this.t("plan.learned_days", { days: d.first_harvest_days }));
    return parts.join(" · ");
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-crops-planning": CropsPlanning;
  }
}
