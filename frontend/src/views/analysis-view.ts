// "Analysis" tab: explain errors and unexpected things yourself.
//  - Check: inconsistencies in the plan (crops off their plan, a year without a plan,
//    a missed year-end transition, crops planned too late ...), each with the why.
//  - Why not here?: pick a plant and a season, see per bed why it fits or not.
//  - Errors: refused or failed actions, as logged by Hortulus.
//  - System log: every change, undoable.
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { AnalysisIssue, AnalysisResult, ExplainResult, FamilyInfo, Plant, Snapshot } from "../types";
import { download, familyColor, plantName, localeOf } from "../util/garden";
import { explainReason } from "../util/reasons";
import "../components/plant-image";
import "./journal-view";
import "../components/plan-compare";

type Section = "check" | "why" | "compare" | "errors" | "log";
const SEVERITY_ICON = { error: "mdi:alert-octagon-outline", warning: "mdi:alert-outline", info: "mdi:information-outline" } as const;

@customElement("hl-analysis-view")
export class AnalysisView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) plants: Plant[] = [];
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ type: Boolean }) admin = true;
  @property() section: Section = "check";

  @state() private result: AnalysisResult | null = null;
  @state() private loading = false;
  @state() private plantId = "";
  @state() private season = 0;
  @state() private matchZone = true;
  @state() private explained: ExplainResult | null = null;
  @state() private fixing = "";
  private plantMap = new Map<string, Plant>();
  private reloadTimer?: number;

  static styles = [
    shared,
    css`
      :host { display: block; }
      .tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: var(--hl-s3); }
      .issue { display: grid; grid-template-columns: 28px 1fr; gap: 4px 10px; padding: 10px 12px; border-radius: var(--hl-r-md);
        border: 1px solid var(--hl-border); background: var(--hl-surface); }
      .issue.error { border-left: 4px solid var(--hl-tomato-500); }
      .issue.warning { border-left: 4px solid var(--hl-sun-500); }
      .issue.info { border-left: 4px solid var(--hl-frost-500); }
      .issue .why { font-size: var(--hl-fs-sm); color: var(--hl-text-muted); }
      .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: var(--hl-s2); }
      .tile { padding: 10px; border-radius: var(--hl-r-md); background: var(--hl-surface-2); }
      .tile b { display: block; font-size: var(--hl-fs-xl); }
      .bed { display: grid; grid-template-columns: 26px 1fr; gap: 2px 10px; padding: 8px 10px; border-bottom: 1px solid var(--hl-border); }
      .bed.ok ha-icon { color: var(--hl-leaf-600); }
      .bed.no ha-icon { color: var(--hl-tomato-500); }
      .bed ul { margin: 2px 0 0; padding-left: 1.1em; font-size: var(--hl-fs-sm); }
      .pick { display: flex; flex-wrap: wrap; gap: var(--hl-s2); align-items: end; }
      .pick hl-plant-image { width: 64px; height: 64px; }
      .err { padding: 8px 10px; border-bottom: 1px solid var(--hl-border); }
      .err code { font-size: var(--hl-fs-xs); }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this.reloadTimer);
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("plants")) this.plantMap = new Map(this.plants.map((p) => [p.id, p]));
    if (changed.has("snapshot") && changed.get("snapshot") !== undefined) {
      window.clearTimeout(this.reloadTimer);
      this.reloadTimer = window.setTimeout(() => void this.load(), 800);
    }
    if (!this.season && this.snapshot) this.season = this.snapshot.layout_season ?? this.snapshot.analysis?.season ?? new Date().getFullYear();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      this.result = await this.api.analysis();
    } catch {
      /* older backend */
    } finally {
      this.loading = false;
    }
  }

  private async explain(): Promise<void> {
    if (!this.plantId) return;
    try {
      this.explained = await this.api.explain(this.plantId, this.season, this.matchZone);
    } catch (err) {
      this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message: (err as Error).message }, bubbles: true, composed: true }));
    }
  }

  /** One click: let Hortulus repair what the check found (logged, so it can be undone). */
  private async fix(i: AnalysisIssue, key: string): Promise<void> {
    this.fixing = key;
    try {
      await this.api.fixIssue(i);
      this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message: this.t("analysis.fixed") }, bubbles: true, composed: true }));
      await this.load();
    } catch (err) {
      this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message: this.t("common.error", { message: (err as Error).message }) }, bubbles: true, composed: true }));
    } finally {
      this.fixing = "";
    }
  }

  /** Everything needed to report a problem, in one file: check, errors, recent log. */
  private async exportDiagnosis(): Promise<void> {
    let log: unknown = null;
    try {
      log = (await this.api.syslog({ limit: 200, include_system: true })).entries;
    } catch {
      /* keep the rest */
    }
    const snap = this.snapshot;
    const doc = {
      exported_at: new Date().toISOString(),
      lang: this.lang,
      panel: { user_agent: navigator.userAgent, url_path: location.pathname },
      garden: {
        revision: snap.revision,
        layout_season: snap.layout_season ?? null,
        plan_seasons: Object.keys(snap.layouts ?? {}),
        archived_plans: snap.archived_plans ?? [],
        zones: snap.zones.length,
        beds: snap.beds.length,
        plantings: snap.plantings.length,
        transition_due: snap.transition_due ?? null,
        diagnosis: snap.diagnosis ?? null,
      },
      analysis: this.result,
      system_log: log,
    };
    const day = (snap.analysis?.today ?? new Date().toISOString().slice(0, 10));
    download(`hortulus-diagnose-${day}.json`, JSON.stringify(doc, null, 2), "application/json");
  }

  private showIssue(i: AnalysisIssue): void {
    const id = i.refs.planting?.[0];
    const season = Number(i.params.season ?? this.snapshot.layout_season);
    if (id) this.dispatchEvent(new CustomEvent("focus-planting", { detail: { planting_id: id, season }, bubbles: true, composed: true }));
  }

  private go(tab: string): void {
    this.dispatchEvent(new CustomEvent("navigate", { detail: tab, bubbles: true, composed: true }));
  }

  render(): TemplateResult {
    const sections: [Section, string][] = [["check", "mdi:stethoscope"], ["why", "mdi:help-circle-outline"], ["compare", "mdi:compare-horizontal"],
      ["errors", "mdi:alert-circle-outline"], ["log", "mdi:history"]];
    const nErr = this.result?.errors.length ?? 0;
    return html`
      <div class="tabs" role="tablist">
        ${sections.map(([id, icon]) => html`<button class="chip" role="tab" aria-selected=${String(this.section === id)}
          @click=${() => (this.section = id)}><ha-icon icon=${icon}></ha-icon>${this.t(`analysis.${id}`)}${id === "errors" && nErr ? html` <span class="chip bad">${nErr}</span>` : nothing}</button>`)}
      </div>
      ${this.section === "check" ? this.renderCheck() : this.section === "why" ? this.renderWhy() : this.section === "errors" ? this.renderErrors()
        : this.section === "compare" ? html`<section class="card stack"><h2><ha-icon icon="mdi:compare-horizontal"></ha-icon> ${this.t("compare.title")}</h2>
            <p class="small muted">${this.t("compare.intro")}</p>
            <hl-plan-compare .snapshot=${this.snapshot} .api=${this.api} .t=${this.t} lang=${this.lang} .plants=${this.plantMap} .families=${this.families}></hl-plan-compare></section>`
        : html`<hl-journal-view systemOnly .snapshot=${this.snapshot} .plants=${this.plants} .families=${this.families} .api=${this.api}
            .t=${this.t} lang=${this.lang} ?admin=${this.admin}></hl-journal-view>`}`;
  }

  // -- check ------------------------------------------------------------------ //
  private issueText(i: AnalysisIssue): string {
    return this.t(`analysis.issue.${i.code}`, i.params);
  }

  private renderCheck(): TemplateResult {
    const r = this.result;
    if (!r) return html`<p class="muted">${this.t("common.loading")}</p>`;
    const action = (i: AnalysisIssue): TemplateResult | typeof nothing => {
      const key = `${i.code}:${JSON.stringify(i.refs)}`;
      const fix = i.fixable && this.admin ? html`<button class="btn small primary" ?disabled=${this.fixing === key} @click=${() => this.fix(i, key)}>
        <ha-icon icon="mdi:auto-fix"></ha-icon>${this.t(`analysis.fix.${i.code}`)}</button>` : nothing;
      const show = i.refs.planting?.length === 1 || (i.refs.planting?.length && i.code === "plantings_overlap")
        ? html`<button class="btn small ghost" @click=${() => this.showIssue(i)}>🗺 ${this.t("crops.show_on_map")}</button>` : nothing;
      return html`${fix}${show}${this.navAction(i)}`;
    };
    return this.renderCheckBody(r, action);
  }

  private navAction(i: AnalysisIssue): TemplateResult | typeof nothing {
    {
      if (i.code === "transition_due") return html`<button class="btn small" @click=${() => this.dispatchEvent(new CustomEvent("year-transition", { bubbles: true, composed: true }))}>${this.t("advice.apply_transition")}</button>`;
      if (i.code === "season_without_plan" || i.code.startsWith("bed_") || i.code === "zone_without_beds") return html`<button class="btn small" @click=${() => this.go("layout")}>${this.t("layout.edit")}</button>`;
      if (i.code.startsWith("planting") || i.code === "plantings_overlap") return html`<button class="btn small" @click=${() => this.go("planner")}>${this.t("analysis.to_planner")}</button>`;
      return nothing;
    }
  }

  private renderCheckBody(r: AnalysisResult, action: (i: AnalysisIssue) => TemplateResult | typeof nothing): TemplateResult {
    return html`<section class="card stack" aria-labelledby="chk">
      <h2 id="chk"><ha-icon icon="mdi:stethoscope"></ha-icon> ${this.t("analysis.check_title")}
        <button class="btn small ghost" ?disabled=${this.loading} @click=${() => this.load()}><ha-icon icon="mdi:refresh"></ha-icon>${this.t("analysis.recheck")}</button>
        <button class="btn small ghost" @click=${() => this.exportDiagnosis()}><ha-icon icon="mdi:download"></ha-icon>${this.t("analysis.export")}</button></h2>
      <p class="small muted">${this.t("analysis.check_intro")}</p>
      <div class="tiles">${Object.entries(r.counts).map(([k, v]) => html`<div class="tile">${this.t(`analysis.count.${k}`)}<b>${v}</b></div>`)}</div>
      ${r.issues.length ? html`<div class="stack" style="gap:8px">${r.issues.map((i) => html`<div class="issue ${i.severity}">
        <ha-icon icon=${SEVERITY_ICON[i.severity]}></ha-icon>
        <div><b>${this.issueText(i)}</b><div class="why">${this.t(`analysis.issue.${i.code}.why`, i.params)}</div>
          <div class="row wrap" style="margin-top:6px">${action(i)}</div></div>
      </div>`)}</div>` : html`<div class="finding info"><ha-icon icon="mdi:check-circle-outline"></ha-icon><span>${this.t("analysis.all_good")}</span></div>`}
    </section>`;
  }

  // -- why not? ------------------------------------------------------------------ //
  private renderWhy(): TemplateResult {
    const list = [...this.plants].sort((a, b) => plantName(a, this.lang).localeCompare(plantName(b, this.lang)));
    const plant = this.plantMap.get(this.plantId);
    const seasons = [this.season - 1, this.season, this.season + 1];
    const ex = this.explained;
    return html`<section class="card stack" aria-labelledby="why">
      <h2 id="why"><ha-icon icon="mdi:help-circle-outline"></ha-icon> ${this.t("analysis.why_title")}</h2>
      <p class="small muted">${this.t("analysis.why_intro")}</p>
      <div class="pick">
        ${plant ? html`<hl-plant-image .plant=${plant} color=${familyColor(this.families, plant.family)} lang=${this.lang} size="thumb"></hl-plant-image>` : nothing}
        <label class="field">${this.t("lib.plant")}
          <select @change=${(e: Event) => { this.plantId = (e.target as HTMLSelectElement).value; this.explained = null; void this.explain(); }}>
            <option value="">–</option>${list.map((p) => html`<option value=${p.id} ?selected=${p.id === this.plantId}>${plantName(p, this.lang)}</option>`)}
          </select></label>
        <label class="field">${this.t("planner.season")}
          <select @change=${(e: Event) => { this.season = Number((e.target as HTMLSelectElement).value); void this.explain(); }}>
            ${seasons.map((s) => html`<option value=${s} ?selected=${s === this.season}>${this.t("common.season", { year: s })}</option>`)}
          </select></label>
        <label class="row small"><input type="checkbox" .checked=${this.matchZone}
          @change=${(e: Event) => { this.matchZone = (e.target as HTMLInputElement).checked; void this.explain(); }} />${this.t("autofill.pref.match_zone_type")}</label>
      </div>
      ${!ex ? nothing : !ex.has_plan ? html`<div class="finding warning"><ha-icon icon="mdi:floor-plan"></ha-icon><span>${this.t("layout.none_title", { season: ex.season })}</span></div>`
        : !ex.beds.length ? html`<p class="small muted">${this.t("analysis.no_beds")}</p>`
        : html`<div>${ex.beds.map((b) => html`<div class="bed ${b.ok ? "ok" : "no"}">
            <ha-icon icon=${b.ok ? "mdi:check-circle-outline" : "mdi:close-circle-outline"}></ha-icon>
            <div><b>${b.bed}</b> <span class="xs muted">${b.zone} · ${this.t("analysis.free", { m2: b.free_m2 })}</span>
              ${b.ok && !b.warnings.length ? html`<div class="small">${this.t("analysis.fits")}</div>` : nothing}
              ${b.reasons.length || b.warnings.length ? html`<ul>
                ${b.reasons.map((r) => html`<li>${explainReason(r, this.t, this.lang, this.plantMap)}</li>`)}
                ${b.warnings.map((r) => html`<li class="muted">${this.t("analysis.warning")}: ${explainReason(r, this.t, this.lang, this.plantMap)}</li>`)}
              </ul>` : nothing}
            </div></div>`)}</div>`}
    </section>`;
  }

  // -- errors ------------------------------------------------------------------ //
  private renderErrors(): TemplateResult {
    const errors = this.result?.errors ?? [];
    const time = (iso: string) => new Date(iso).toLocaleString(this.lang === "nl" ? "nl-NL" : localeOf(this.lang),
      { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    return html`<section class="card stack" aria-labelledby="errs">
      <h2 id="errs"><ha-icon icon="mdi:alert-circle-outline"></ha-icon> ${this.t("analysis.errors_title")}</h2>
      <p class="small muted">${this.t("analysis.errors_intro")}</p>
      ${errors.length ? html`<div>${errors.map((e) => html`<div class="err">
        <b>${this.t(`analysis.error.${e.summary[0]?.key ?? "unexpected"}`)}</b> <span class="xs muted">${time(e.at)} · ${e.user ?? ""} · <code>${e.reason}</code></span>
        <div class="small">${e.summary[0]?.name ?? ""}</div>
      </div>`)}</div>` : html`<div class="finding info"><ha-icon icon="mdi:check-circle-outline"></ha-icon><span>${this.t("analysis.no_errors")}</span></div>`}
    </section>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-analysis-view": AnalysisView;
  }
}
