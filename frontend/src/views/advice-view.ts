// "Advice" tab: ask a question in a sentence of dropdowns, see the garden's
// suggestions (placement, pollination, neighbours, year-round harvest, ecology),
// the month-by-month harvest coverage and the season's shopping list.
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { AdviceResult, Plant, PlanDoc, Planting, QaAnswer, QaOptions, Snapshot, Suggestion, Supplies } from "../types";
import { familyColor, plantName, presentIn, uid, localeOf } from "../util/garden";
import { defaultFootprint, findFreeSpot } from "../planner/geometry";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import { defaultMethod } from "./planner-view";
import "../components/plant-image";
import { chapterArt } from "../components/chapter-art";
import "../components/info";

/** Problems phrased as "I have a problem with ..." (the rest are questions). */
const PROBLEM_KINDS = new Set(["growth", "yellow_leaves", "wilting", "no_fruit", "bolting", "pests", "disease", "too_hot", "too_cold", "soil", "slugs", "frost"]);
const SEVERITY_ICON: Record<string, string> = { warning: "mdi:alert-outline", tip: "mdi:lightbulb-on-outline", info: "mdi:information-outline" };
const KIND_ICON: Record<string, string> = {
  pollination: "mdi:bee-flower", neighbours: "mdi:handshake-outline", placement: "mdi:white-balance-sunny",
  year_round: "mdi:calendar-sync-outline", soil: "mdi:shovel", eco: "mdi:leaf-circle-outline", growth: "mdi:sprout",
  greenhouse: "mdi:greenhouse",
};

@customElement("hl-advice-view")
export class AdviceView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) plants: Plant[] = [];
  @property({ attribute: false }) families: Record<string, { en: string; nl: string; color: string }> = {};
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ type: Boolean }) admin = true;

  @state() private mode: "question" | "problem" = "question";
  @state() private options: QaOptions | null = null;
  @state() private subject = "plant";
  @state() private target = "";
  @state() private problem = "what_to_do";
  @state() private answer: QaAnswer | null = null;
  @state() private busy = false;
  @state() private advice: AdviceResult | null = null;
  @state() private supplies: Supplies | null = null;
  @state() private dismissed = new Set<string>();

  static styles = [
    shared,
    css`
      .pic[role="button"] { cursor: pointer; }
      :host { display: block; }
      .grid { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: var(--hl-s4); align-items: start; }
      @media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }
      .ask { background: linear-gradient(135deg, var(--hl-leaf-100), var(--hl-surface)); }
      .sentence { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: var(--hl-fs-lg); line-height: 2.2; }
      .sentence select { width: auto; max-width: 100%; font-size: var(--hl-fs-md); font-weight: 600; border-radius: var(--hl-r-pill); padding: 4px 12px; }
      .segmented { display: inline-flex; background: var(--hl-surface-2); border-radius: var(--hl-r-pill); padding: 3px; border: 1px solid var(--hl-border); }
      .segmented button { border: 0; background: transparent; padding: 2px 14px; border-radius: var(--hl-r-pill); cursor: pointer;
        font: inherit; font-weight: 600; color: var(--hl-text-muted); line-height: 1.8; }
      .segmented button[aria-pressed="true"] { background: var(--hl-leaf-600); color: #fff; box-shadow: var(--hl-shadow-1); }
      .answer h3 { display: flex; gap: 8px; align-items: center; }
      .section { display: grid; grid-template-columns: 28px 1fr; gap: 4px 8px; margin-top: var(--hl-s3); }
      .section ha-icon { color: var(--hl-leaf-600); }
      .section h4 { margin: 0; }
      .section ul { margin: 4px 0 0; padding-left: 18px; grid-column: 2; }
      .section li { margin-bottom: 3px; }
      .section.status ha-icon { color: var(--hl-water-500); }
      .section.causes ha-icon { color: var(--hl-sun-500); }
      .section.remedies ha-icon { color: var(--hl-soil-500); }
      .chips { display: flex; flex-wrap: wrap; gap: 6px; }
      .plant-chip { display: inline-flex; gap: 6px; align-items: center; padding: 2px 10px 2px 4px; border-radius: var(--hl-r-pill);
        background: var(--hl-surface-2); border: 1px solid var(--hl-border); font-size: var(--hl-fs-sm); }
      .sugg .pic { width: 44px; height: 44px; border-radius: 50%; overflow: hidden; display: block; position: relative; }
      .sugg .pic .badge { position: absolute; right: -2px; bottom: -2px; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
        background: var(--hl-surface); box-shadow: 0 0 0 2px var(--hl-surface); --mdc-icon-size: 14px; }
      .sugg .pic svg.chapter-art { display: block; }
      .answer .hero { display: block; margin-bottom: var(--hl-s3); border-radius: var(--hl-r-md); overflow: hidden; }
      .sugg { display: grid; grid-template-columns: 44px 1fr; gap: 4px 10px; padding: 10px 12px; border-radius: var(--hl-r-md);
        border: 1px solid var(--hl-border); background: var(--hl-surface); }
      .sugg.warning { border-left: 4px solid var(--hl-tomato-500); }
      .sugg.tip { border-left: 4px solid var(--hl-leaf-500); }
      .sugg.info { border-left: 4px solid var(--hl-frost-500); }
      .sugg .icon { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; background: var(--hl-surface-2); }
      .sugg b { display: block; }
      .sugg .row { grid-column: 2; }
      .months { display: grid; grid-template-columns: repeat(12, 1fr); gap: 4px; }
      .month { border-radius: var(--hl-r-sm); padding: 6px 2px; text-align: center; font-size: 11px; background: var(--hl-leaf-100); }
      .month b { display: block; font-size: 16px; }
      .month.gap { background: var(--hl-tomato-100); color: var(--hl-danger-ink, #8a2a1f); }
      .month.now { outline: 2px solid var(--hl-focus); }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); }
      td, th { padding: 4px 6px; border-bottom: 1px solid var(--hl-border); text-align: left; }
      td.num { text-align: right; white-space: nowrap; }
      .cat { font-weight: 700; padding-top: 10px; color: var(--hl-text-muted); text-transform: uppercase; font-size: 11px; letter-spacing: 0.04em; }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [options, advice, supplies] = await Promise.all([this.api.qaOptions(), this.api.advice(), this.api.supplies()]);
      this.options = options;
      this.advice = advice;
      this.supplies = supplies;
      const planted = options.targets.plant.find((p) => p.planted);
      this.target = planted?.id ?? options.targets.plant[0]?.id ?? "";
    } catch (err) {
      this.toast((err as Error).message ?? String(err));
    }
  }

  private toast(message: string): void {
    this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message }, bubbles: true, composed: true }));
  }

  private openChapter(chapter: string): void {
    this.dispatchEvent(new CustomEvent("open-handbook", { detail: { chapter }, bubbles: true, composed: true }));
  }

  private problems(): string[] {
    const all = this.options?.subjects[this.subject] ?? [];
    const list = all.filter((p) => (this.mode === "problem") === PROBLEM_KINDS.has(p));
    return list.length ? list : all;
  }

  private setSubject(subject: string): void {
    this.subject = subject;
    const targets = this.options?.targets[subject] ?? [];
    this.target = targets.find((t) => t.planted)?.id ?? targets[0]?.id ?? "";
    if (!this.problems().includes(this.problem)) this.problem = this.problems()[0] ?? "";
    this.answer = null;
  }

  private setMode(mode: "question" | "problem"): void {
    this.mode = mode;
    if (!this.problems().includes(this.problem)) this.problem = this.problems()[0] ?? "";
    this.answer = null;
  }

  private async ask(): Promise<void> {
    this.busy = true;
    try {
      this.answer = await this.api.qaAsk(this.subject, this.problem, this.target || null);
    } catch (err) {
      this.toast((err as Error).message ?? String(err));
    } finally {
      this.busy = false;
    }
  }

  /** Apply "add this plant to that bed" in the first free spot. */
  private async apply(s: Suggestion): Promise<void> {
    const a = s.action;
    if (!a) return;
    if (a.type === "add_planting" && a.plant_id && a.bed_id) {
      const plant = this.plants.find((p) => p.id === a.plant_id);
      const snap = this.snapshot;
      const bed = snap.beds.find((b) => b.id === a.bed_id);
      if (!plant || !bed) return;
      const season = snap.analysis?.season ?? new Date().getFullYear();
      const size = defaultFootprint(plant, "block", bed);
      // Perennials from earlier seasons (trees, bushes) still occupy their spot.
      const taken = snap.plantings
        .filter((p) => p.bed_id === bed.id && presentIn(p, !!this.plants.find((x) => x.id === p.plant_id)?.perennial, season))
        .map((p) => ({ x: p.x_cm, y: p.y_cm, w: p.width_cm, h: p.length_cm }));
      const spot = findFreeSpot(bed, size, taken, snap.settings.snap_cm);
      if (!spot) {
        this.toast(this.t("advice.no_space", { bed: bed.name }));
        return;
      }
      const planting: Planting = {
        id: uid("pl"), plant_id: plant.id, bed_id: bed.id, season, layout: "block", x_cm: spot.x, y_cm: spot.y, width_cm: size.w,
        length_cm: size.h, count: null, method: defaultMethod(plant), status: "planned", sow_date: null, transplant_date: null, sown_on: null,
        transplanted_on: null, harvest_started_on: null, finished_on: null, succession_group: null, succession_index: 0, notes: "advice",
      };
      const doc: PlanDoc = { zones: snap.zones, beds: snap.beds, plantings: [...snap.plantings, planting], features: snap.features ?? [] };
      try {
        await this.api.savePlan(doc, snap.revision);
        this.dismissed = new Set([...this.dismissed, s.id]);
        this.toast(this.t("planner.placed", { plant: plantName(plant, this.lang), bed: bed.name }));
      } catch (err) {
        this.toast((err as Error).message ?? String(err));
      }
    } else if (a.type === "year_transition") {
      this.dispatchEvent(new CustomEvent("year-transition", { detail: a.from_season, bubbles: true, composed: true }));
    } else {
      this.dispatchEvent(new CustomEvent("navigate", { detail: a.type === "draw" ? "layout" : "planner", bubbles: true, composed: true }));
    }
  }

  /** Picture of a suggestion: its first plant, else the handbook chapter it points to, else its kind icon. */
  private suggestionPicture(s: Suggestion): TemplateResult {
    const icon = html`<ha-icon icon=${KIND_ICON[s.kind] ?? SEVERITY_ICON[s.severity]}></ha-icon>`;
    const plant = s.plants.map((id) => this.plants.find((x) => x.id === id)).find(Boolean);
    const title = this.t(`advice.kind.${s.kind}`);
    if (plant) {
      return html`<span class="pic" title=${`${title} · ${this.t("lib.open_plant")}`} role="button" tabindex="0"
        @click=${() => this.dispatchEvent(new CustomEvent("open-plant", { detail: plant.id, bubbles: true, composed: true }))}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key !== "Enter" && e.key !== " ") return;
          e.preventDefault();
          this.dispatchEvent(new CustomEvent("open-plant", { detail: plant.id, bubbles: true, composed: true }));
        }}><hl-plant-image .plant=${plant} color=${familyColor(this.families, plant.family)}
        lang=${this.lang} size="thumb"></hl-plant-image><span class="badge">${icon}</span></span>`;
    }
    if (s.handbook) return html`<span class="pic" title=${title}>${chapterArt(s.handbook, 44)}<span class="badge">${icon}</span></span>`;
    return html`<span class="icon" title=${title}>${icon}</span>`;
  }

  /** Header picture of an answer: the plant asked about, or the chapter behind the advice. */
  private answerPicture(a: QaAnswer): TemplateResult | typeof nothing {
    const plant = a.subject === "plant" ? this.plants.find((x) => x.id === a.target) : undefined;
    if (plant) {
      return html`<hl-plant-image class="hero" .plant=${plant} color=${familyColor(this.families, plant.family)} lang=${this.lang}
        size="hero" credit></hl-plant-image>`;
    }
    return a.handbook ? html`<span class="hero">${chapterArt(a.handbook, 120)}</span>` : nothing;
  }

  private plantChip(id: string): TemplateResult {
    const p = this.plants.find((x) => x.id === id);
    if (!p) return html``;
    return html`<span class="plant-chip">${glyphIcon(glyphFor(p), p.color || familyColor(this.families, p.family), 20)}${plantName(p, this.lang)}</span>`;
  }

  render(): TemplateResult {
    if (!this.options) return html`<p class="empty">${this.t("common.loading")}</p>`;
    return html`<div class="grid">
      <div class="stack">${this.renderAsk()}${this.answer ? this.renderAnswer(this.answer) : nothing}${this.renderSuggestions()}</div>
      <div class="stack">${this.renderCoverage()}${this.renderShopping()}</div>
    </div>`;
  }

  private renderAsk(): TemplateResult {
    const o = this.options!;
    const targets = o.targets[this.subject] ?? [];
    const planted = targets.filter((x) => x.planted);
    const other = targets.filter((x) => !x.planted);
    return html`<section class="card ask stack" aria-labelledby="ask-h">
      <h2 id="ask-h"><ha-icon icon="mdi:chat-question-outline"></ha-icon> ${this.t("advice.ask_title")}</h2>
      <div class="sentence">
        <span>${this.t("advice.i_have")}</span>
        <span class="modes segmented" role="group">
          <button aria-pressed=${String(this.mode === "question")} @click=${() => this.setMode("question")}>${this.t("advice.mode.question")}</button>
          <button aria-pressed=${String(this.mode === "problem")} @click=${() => this.setMode("problem")}>${this.t("advice.mode.problem")}</button>
        </span>
        <span>${this.t("advice.about")}</span>
        <select aria-label=${this.t("advice.subject")} @change=${(e: Event) => this.setSubject((e.target as HTMLSelectElement).value)}>
          ${Object.keys(o.subjects).map((s) => html`<option value=${s} ?selected=${s === this.subject}>${this.t(`advice.subject.${s}`)}</option>`)}
        </select>
        ${targets.length ? html`<select aria-label=${this.t("advice.target")} @change=${(e: Event) => { this.target = (e.target as HTMLSelectElement).value; this.answer = null; }}>
          ${planted.length ? html`<optgroup label=${this.t("advice.in_garden")}>${planted.map((x) => html`<option value=${x.id} ?selected=${x.id === this.target}>${x.name}</option>`)}</optgroup>` : nothing}
          ${(planted.length ? html`<optgroup label=${this.t("advice.all_plants")}>${other.map((x) => html`<option value=${x.id} ?selected=${x.id === this.target}>${x.name === "*" ? this.t("advice.whole_garden") : this.subject === "tools" ? this.t(`type.${x.id}`) : x.name}</option>`)}</optgroup>`
            : other.map((x) => html`<option value=${x.id} ?selected=${x.id === this.target}>${x.name === "*" ? this.t("advice.whole_garden") : this.subject === "tools" ? this.t(`type.${x.id}`) : x.name}</option>`))}
        </select>` : nothing}
        <span>:</span>
        <select aria-label=${this.t("advice.problem")} @change=${(e: Event) => { this.problem = (e.target as HTMLSelectElement).value; this.answer = null; }}>
          ${this.problems().map((p) => html`<option value=${p} ?selected=${p === this.problem}>${this.t(`advice.q.${p}`)}</option>`)}
        </select>
        <button class="btn primary" ?disabled=${this.busy} @click=${() => this.ask()}><ha-icon icon="mdi:send"></ha-icon>${this.t("advice.ask")}</button>
      </div>
    </section>`;
  }

  private renderAnswer(a: QaAnswer): TemplateResult {
    const sec = (cls: string, icon: string, title: string, items: string[]) => (items.length
      ? html`<div class="section ${cls}"><ha-icon icon=${icon}></ha-icon><h4>${title}</h4><ul>${items.map((i) => html`<li>${i}</li>`)}</ul></div>`
      : nothing);
    return html`<section class="card answer" aria-live="polite">
      ${this.answerPicture(a)}
      <h3><ha-icon icon="mdi:message-reply-text-outline"></ha-icon>${a.title} – ${this.t(`advice.q.${a.problem}`)}</h3>
      ${sec("status", "mdi:pulse", this.t("advice.sec.status"), a.status)}
      ${sec("facts", "mdi:information-outline", this.t("advice.sec.facts"), a.facts)}
      ${sec("causes", "mdi:help-circle-outline", this.t("advice.sec.causes"), a.causes)}
      ${sec("actions", "mdi:checkbox-marked-circle-outline", this.t("advice.sec.actions"), a.actions)}
      ${sec("remedies", "mdi:leaf", this.t("advice.sec.remedies"), a.remedies)}
      ${sec("prevention", "mdi:shield-check-outline", this.t("advice.sec.prevention"), a.prevention)}
      ${a.tasks.length ? html`<div class="section"><ha-icon icon="mdi:format-list-checks"></ha-icon><h4>${this.t("advice.sec.tasks")}</h4>
        <ul>${a.tasks.map((x) => html`<li>${x.title} <span class="xs muted">(${x.due})</span></li>`)}</ul></div>` : nothing}
      ${a.plants.length > 1 || a.subject !== "plant" ? html`<div class="chips" style="margin-top:12px">${a.plants.map((p) => this.plantChip(p))}</div>` : nothing}
      ${a.handbook ? html`<div class="row" style="margin-top:12px"><button class="btn small ghost" @click=${() => this.openChapter(a.handbook!)}>
        <ha-icon icon="mdi:book-open-page-variant-outline"></ha-icon>${this.t("advice.read_more")}</button></div>` : nothing}
    </section>`;
  }

  private renderSuggestions(): TemplateResult {
    const list = (this.advice?.suggestions ?? []).filter((s) => !this.dismissed.has(s.id));
    return html`<section class="card stack" aria-labelledby="sugg-h">
      <h2 id="sugg-h"><ha-icon icon="mdi:lightbulb-group-outline"></ha-icon> ${this.t("advice.suggestions")} <span class="chip">${list.length}</span></h2>
      <p class="small muted">${this.t("advice.suggestions_intro")}</p>
      ${list.length ? list.map((s) => html`<article class="sugg ${s.severity}">
        ${this.suggestionPicture(s)}
        <div><b>${s.title}</b><span class="small">${s.text}</span></div>
        ${s.plants.length ? html`<div class="row chips">${s.plants.slice(0, 5).map((p) => this.plantChip(p))}</div>` : nothing}
        <div class="row wrap">
          ${s.action && this.admin ? html`<button class="btn small primary" @click=${() => this.apply(s)}>
            ${this.t(s.action.type === "add_planting" ? "advice.apply_add" : s.action.type === "year_transition" ? "advice.apply_transition" : "advice.apply_open")}</button>` : nothing}
          ${s.handbook ? html`<button class="btn small ghost" @click=${() => this.openChapter(s.handbook!)}>${this.t("advice.read_more")}</button>` : nothing}
          <button class="btn small ghost" @click=${() => (this.dismissed = new Set([...this.dismissed, s.id]))}>${this.t("advice.dismiss")}</button>
        </div></article>`)
        : html`<p class="small">${this.t("advice.none")}</p>`}
    </section>`;
  }

  private renderCoverage(): TemplateResult {
    const cov = this.advice?.coverage;
    if (!cov) return html``;
    const now = new Date().getMonth();
    const month = (i: number) => new Date(2026, i, 1).toLocaleDateString(localeOf(this.lang), { month: "short" });
    return html`<section class="card stack" aria-labelledby="cov-h">
      <h2 id="cov-h"><ha-icon icon="mdi:calendar-sync-outline"></ha-icon> ${this.t("advice.coverage")}</h2>
      <div class="months" role="list">
        ${cov.months.map((ids, i) => html`<div role="listitem" class="month ${ids.length ? "" : "gap"} ${i === now ? "now" : ""}"
          title=${ids.map((id) => plantName(this.plants.find((p) => p.id === id), this.lang)).join(", ") || this.t("advice.nothing")}>
          ${month(i)}<b>${ids.length}</b></div>`)}
      </div>
      <p class="xs muted">${cov.gaps.length ? this.t("advice.coverage_gaps") : this.t("advice.coverage_full")}</p>
    </section>`;
  }

  private renderShopping(): TemplateResult {
    const s = this.supplies;
    if (!s) return html``;
    let last = "";
    return html`<section class="card stack" aria-labelledby="shop-h">
      <h2 id="shop-h"><ha-icon icon="mdi:cart-outline"></ha-icon> ${this.t("advice.shopping")}</h2>
      <p class="small muted">${this.t("advice.shopping_intro")}</p>
      ${s.shopping.length ? html`<table>
        ${s.shopping.map((i) => {
          const head = i.category !== last ? html`<tr><td class="cat" colspan="3">${this.t(`advice.cat.${i.category}`)}</td></tr>` : nothing;
          last = i.category;
          return html`${head}<tr><td>${i.emoji} ${i.name}</td><td class="num">${i.quantity} ${i.unit}</td><td class="xs muted">${i.reason}</td></tr>`;
        })}
      </table>` : html`<p class="small">${this.t("advice.nothing_to_buy")}</p>`}
      <details><summary class="small"><b>${this.t("advice.tools_per_task")}</b></summary>
        <table>${Object.entries(s.task_tools).filter(([, tools]) => tools.length).map(([type, tools]) => html`<tr>
          <td>${this.t(`type.${type}`)}</td><td class="small">${tools.map((x) => `${s.tools[x]?.emoji ?? ""} ${s.tools[x]?.name ?? x}`).join(", ")}</td></tr>`)}</table>
      </details>
      <button class="btn small ghost" @click=${() => this.openChapter("tools")}><ha-icon icon="mdi:book-open-page-variant-outline"></ha-icon>${this.t("advice.read_tools")}</button>
    </section>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-advice-view": AdviceView;
  }
}
