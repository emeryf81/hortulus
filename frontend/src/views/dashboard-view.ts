import type { GardenApi } from "../api";
import "../components/quick-harvest";
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { FamilyInfo, Plant, Snapshot, Task } from "../types";
import { addDays, familyColor, formatDate, plantName, sortTasks, localeOf } from "../util/garden";
import { tileColor } from "../components/plant-image";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import { renderTaskRow, taskPlantResolver, taskRowStyles, type TaskCtx } from "../components/task-ui";
import "../components/info";

const RISK_CHIP: Record<string, string> = { none: "ok", low: "cold", moderate: "warn", high: "bad", unknown: "" };
const ALERT_ICON: Record<string, string> = {
  frost: "mdi:snowflake-alert",
  heat: "mdi:thermometer-alert",
  dry: "mdi:water-alert",
  sensor_stale: "mdi:access-point-network-off",
  forecast: "mdi:weather-cloudy-alert",
  disease: "mdi:mushroom-outline",
  nutrients: "mdi:flask-outline",
};

@customElement("hl-dashboard-view")
export class DashboardView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) plants: Map<string, Plant> = new Map();
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @property({ attribute: false }) api?: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ type: Boolean }) admin = true;
  @state() private starting = false;
  @state() private starterSize: "small" | "medium" | "large" = "medium";
  @state() private starterGreenhouse = false;

  static styles = [
    shared,
    taskRowStyles,
    css`
      .welcome { padding: 24px 28px; }
      .welcome .choices { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--hl-s4); margin-top: var(--hl-s3); }
      .welcome .choice { border: 1px solid var(--hl-border); border-radius: 16px; padding: 16px; display: grid; gap: 8px; align-content: start; background: var(--hl-surface-2); }
      .welcome .choice h3 { margin: 0; font-family: var(--hl-font-serif); }
      .pests { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
      .pests li { display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start; }
      .hero { position: relative; overflow: hidden; border-radius: 22px; margin-bottom: var(--hl-s5); padding: 28px 32px 24px;
        color: var(--hl-hero-ink); background: var(--season, var(--hl-grad-spring)); box-shadow: var(--hl-shadow-2), var(--hl-highlight);
        isolation: isolate; }
      .hero::before { content: ""; position: absolute; inset: 0; z-index: -1; opacity: 0.55;
        background: radial-gradient(600px 220px at 85% 10%, rgba(255, 255, 255, 0.7), transparent 70%),
          radial-gradient(400px 200px at 0% 120%, rgba(255, 255, 255, 0.35), transparent 70%); }
      .hero::before { opacity: var(--hl-hero-glow, 0.55); }
      .hero .wall { position: absolute; top: 16px; right: 16px; background: color-mix(in srgb, var(--hl-surface) 55%, transparent); }
      .hero .art { position: absolute; right: 18px; top: -6px; height: 150%; opacity: 0.9; z-index: -1; pointer-events: none; }
      .hero .eyebrow { color: color-mix(in srgb, var(--hl-hero-ink) 70%, transparent); }
      .hero h1 { font-size: clamp(28px, 3.4vw, 42px); color: var(--hl-hero-ink); margin: 6px 0 2px; }
      .hero .lede { font-family: var(--hl-font-serif); font-style: italic; font-size: 16px; color: color-mix(in srgb, var(--hl-hero-ink) 78%, transparent); max-width: 560px; }
      .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 20px; max-width: 760px; }
      .stat { padding: 12px 14px; border-radius: 14px; background: color-mix(in srgb, var(--hl-surface) 62%, transparent);
        backdrop-filter: blur(6px); border: 1px solid color-mix(in srgb, #fff 45%, transparent); box-shadow: var(--hl-shadow-1); }
      .stat { border-color: var(--hl-stat-edge, color-mix(in srgb, #fff 45%, transparent)); }
      .stat .v { font-family: var(--hl-font-serif); font-size: 26px; font-weight: 700; line-height: 1.05; font-variant-numeric: tabular-nums; }
      .stat .v small { font-family: var(--hl-font); font-size: 12px; font-weight: 600; margin-left: 2px; opacity: 0.7; }
      .stat .l { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.72; margin-top: 4px; }
      .stat.alert-frost .v { color: var(--hl-info); }
      @media (max-width: 720px) { .hero { padding: 22px 20px; } .stats { grid-template-columns: repeat(2, 1fr); } .hero .art { opacity: 0.35; } }
      .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--hl-s4); }
      .span-8 { grid-column: span 8; }
      .span-4 { grid-column: span 4; }
      .span-12 { grid-column: span 12; }
      @media (max-width: 1100px) { .span-8, .span-4 { grid-column: span 12; } }
      .alerts { display: flex; flex-direction: column; gap: var(--hl-s2); margin-bottom: var(--hl-s4); }
      .alert { position: relative; display: flex; gap: var(--hl-s3); align-items: center; padding: 14px 18px 14px 22px; border-radius: 14px;
        border: 1px solid var(--hl-border); background: var(--hl-surface); box-shadow: var(--hl-shadow-1); overflow: hidden; }
      .alert::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--accent, var(--hl-text-muted)); }
      .alert > ha-icon { flex: none; width: 36px; height: 36px; display: grid; place-items: center; border-radius: 50%;
        background: color-mix(in srgb, var(--accent, var(--hl-text-muted)) 14%, transparent); color: var(--accent, var(--hl-text)); }
      .alert.critical { --accent: var(--hl-danger); }
      .alert.warning { --accent: var(--hl-warning); }
      .alert.frost { --accent: var(--hl-info); }
      .alert.critical { background: var(--hl-tomato-100); border-color: color-mix(in srgb, var(--hl-danger) 35%, transparent); }
      .alert.warning { background: var(--hl-sun-100); border-color: color-mix(in srgb, var(--hl-warning) 35%, transparent); }
      .alert.frost { background: var(--hl-frost-100); border-color: color-mix(in srgb, var(--hl-info) 35%, transparent); }
      .alert ha-icon { --mdc-icon-size: 20px; }
      .beds { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--hl-s3); }
      .bed { border: 1px solid var(--hl-border); border-radius: var(--hl-r-md); padding: var(--hl-s3); background: var(--hl-surface-2); display: flex; flex-direction: column; gap: var(--hl-s2); }
      .gauge { height: 8px; border-radius: 4px; background: var(--hl-surface-3); position: relative; overflow: hidden; }
      .gauge .target { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--hl-leaf-500) 30%, transparent); }
      .gauge .value { position: absolute; top: -2px; bottom: -2px; width: 3px; background: var(--hl-text); border-radius: 2px; }
      .avatars { display: flex; flex-wrap: wrap; gap: 4px; }
      .avatar { border: 0; cursor: pointer; padding: 0; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; color: #fff; font-size: 10px; font-weight: 700; }
      .days { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--hl-s2); }
      .day { text-align: center; padding: 12px 8px; border-radius: 14px; border: 1px solid color-mix(in srgb, var(--hl-border) 70%, transparent);
        background: linear-gradient(180deg, var(--hl-frost-100) 0%, var(--hl-surface) 100%); }
      .day:first-child { background: linear-gradient(180deg, var(--hl-sun-100) 0%, var(--hl-surface) 100%); }
      .day .temp { font-family: var(--hl-font-serif); font-size: 24px; font-weight: 700; margin: 2px 0; }
      .alert.warning { background: color-mix(in srgb, var(--hl-sun-100) 65%, var(--hl-surface)); }
      .alert.critical { background: color-mix(in srgb, var(--hl-tomato-100) 65%, var(--hl-surface)); }
      .alert.frost { background: color-mix(in srgb, var(--hl-frost-100) 65%, var(--hl-surface)); }
      .big { font-size: var(--hl-fs-3xl); font-weight: 700; line-height: 1; }
      .kv { display: flex; justify-content: space-between; gap: var(--hl-s2); font-size: var(--hl-fs-sm); }
    `,
  ];

  private emit(name: string, detail: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  private get ctx(): TaskCtx {
    return {
      t: this.t,
      lang: this.lang,
      today: this.snapshot.analysis?.today ?? "",
      onOpen: (task: Task) => this.emit("open-task", task),
      onComplete: (task: Task) => this.emit("complete-task", task),
      onPostpone: (task: Task, days: number) => this.emit("postpone-task", { task, days }),
      plantOf: taskPlantResolver(this.snapshot, this.plants, this.families),
    };
  }

  /** A valve or the pump stayed open: say so, with a button to close it. */
  private renderStuck(): TemplateResult | typeof nothing {
    const stuck = this.snapshot.irrigation_status?.stuck ?? [];
    const leak = this.snapshot.irrigation_status?.leak;
    if (!stuck.length && !leak) return nothing;
    return html`<section class="alerts" aria-label=${this.t("valve.stuck_title")}>
      ${leak ? html`<div class="alert critical" role="alert"><ha-icon icon="mdi:water-alert"></ha-icon>
        <div><b>${this.t("valve.leak", { liters: leak.liters, minutes: leak.minutes })}</b>
        <div class="small">${this.t("valve.leak_hint", { entity: leak.entity_id })}</div></div></div>` : nothing}
      ${stuck.map((v) => html`<div class="alert critical" role="alert">
      <ha-icon icon="mdi:valve-open"></ha-icon>
      <div><b>${this.t("valve.stuck", { what: v.what === "pump" ? this.t("valve.pump") : v.what, entity: v.entity_id })}</b>
        <div class="small">${this.t("valve.stuck_since", { time: new Date(v.since).toLocaleTimeString(this.lang === "nl" ? "nl-NL" : localeOf(this.lang), { hour: "2-digit", minute: "2-digit" }) })}</div></div>
      <span class="spacer"></span>
      ${this.admin ? html`<button class="btn small danger" @click=${() => this.emit("close-valve", v.entity_id)}>${this.t("valve.close")}</button>` : nothing}
    </div>`)}</section>`;
  }

  /** Season of the year for the hero colour (hemisphere aware). */
  private seasonOf(day: string): "spring" | "summer" | "autumn" | "winter" {
    let m = Number(day.slice(5, 7)) - 1;
    if (this.snapshot.settings.region?.hemisphere === "south") m = (m + 6) % 12;
    return m < 2 || m === 11 ? "winter" : m < 5 ? "spring" : m < 8 ? "summer" : "autumn";
  }

  private greeting(): string {
    const h = new Date().getHours();
    return this.t(h < 12 ? "dash.greeting_morning" : h < 18 ? "dash.greeting_afternoon" : "dash.greeting_evening");
  }

  /** First visit, empty garden: a ready-made starter garden, draw your own, or let the planner fill it. */
  private renderWelcome(): TemplateResult {
    const start = async () => {
      if (!this.api) return;
      this.starting = true;
      try {
        await this.api.starterGarden(this.starterSize, this.starterGreenhouse);
      } catch (err) {
        const message = this.t("common.error", { message: (err as Error).message });
        this.dispatchEvent(new CustomEvent("hl-toast", { detail: { message }, bubbles: true, composed: true }));
      } finally {
        this.starting = false;
      }
    };
    return html`<section class="card welcome" aria-labelledby="welcome-h">
      <h2 id="welcome-h">${this.t("welcome.title")}</h2>
      <p>${this.t("welcome.intro")}</p>
      <div class="choices">
        <div class="choice">
          <h3>${this.t("welcome.starter")}</h3>
          <p class="small">${this.t("welcome.starter_text")}</p>
          <label class="field">${this.t("welcome.size")}<select @change=${(e: Event) => (this.starterSize = (e.target as HTMLSelectElement).value as "small" | "medium" | "large")}>
            ${(["small", "medium", "large"] as const).map((s) => html`<option value=${s} ?selected=${s === this.starterSize}>${this.t(`welcome.size.${s}`)}</option>`)}</select></label>
          <label class="field check"><input type="checkbox" .checked=${this.starterGreenhouse} @change=${(e: Event) => (this.starterGreenhouse = (e.target as HTMLInputElement).checked)} />${this.t("welcome.greenhouse")}</label>
          <button class="btn primary" ?disabled=${this.starting || !this.api} @click=${start}>${this.t("welcome.starter_go")}</button>
        </div>
        <div class="choice">
          <h3>${this.t("welcome.draw")}</h3>
          <p class="small">${this.t("welcome.draw_text")}</p>
          <button class="btn" @click=${() => this.emit("navigate", "layout")}>${this.t("welcome.draw_go")}</button>
        </div>
        <div class="choice">
          <h3>${this.t("welcome.handbook")}</h3>
          <p class="small">${this.t("welcome.handbook_text")}</p>
          <button class="btn ghost" @click=${() => this.emit("navigate", "handbook")}>${this.t("welcome.handbook_go")}</button>
        </div>
      </div>
    </section>`;
  }

  render(): TemplateResult {
    const snap = this.snapshot;
    const a = snap.analysis;
    if (!a) return html`<p class="empty">${this.t("common.loading")}</p>`;
    const today = a.today;
    const due = sortTasks(snap.tasks.filter((t) => t.status === "open" && t.due <= today));
    const upcoming = sortTasks(snap.tasks.filter((t) => t.status === "open" && t.due > today && t.due <= addDays(today, 7)));
    const minutes = due.reduce((s, t) => s + t.estimated_minutes, 0);
    const greenhouses = snap.zones.filter((z) => z.type !== "outdoor");
    return html`
      <section class="hero" style=${`--season: var(--hl-grad-${this.seasonOf(today)})`}>
        ${botanical(this.seasonOf(today))}
        <div class="eyebrow">${formatDate(today, this.lang, { weekday: "long", day: "numeric", month: "long" })} · ${this.t("common.season", { year: a.season })}</div>
        <h1>${this.greeting()}</h1>
        <p class="lede">${(this.snapshot.settings.slogans !== false && a.slogan) || this.t(`dash.lede.${this.seasonOf(today)}`)}</p>
        <button class="btn small ghost wall" @click=${() => this.emit("navigate", "wall")}><ha-icon icon="mdi:tablet-dashboard"></ha-icon>${this.t("wall.open")}</button>
        <div class="stats">
          <div class="stat"><div class="v">${due.length}</div><div class="l">${this.t("dash.stat_tasks")}</div></div>
          <div class="stat"><div class="v">${minutes}<small>min</small></div><div class="l">${this.t("dash.stat_work")}</div></div>
          <div class="stat ${a.frost.level === "high" || a.frost.level === "moderate" ? "alert-frost" : ""}"><div class="v">${this.t(`risk.${a.frost.level}`)}</div><div class="l">${this.t("dash.frost_risk")}</div></div>
          <div class="stat"><div class="v">${Math.round(a.gdd.season_total)}</div><div class="l">${this.t("dash.stat_gdd")}</div></div>
        </div>
      </section>

      ${this.renderStuck()}
      ${a.alerts.length ? html`<section class="alerts" aria-label="Alerts">
        ${a.alerts.map((al) => html`<div class="alert ${al.kind === "frost" ? "frost" : al.severity}" role=${al.severity === "critical" ? "alert" : "status"}>
          <ha-icon icon=${ALERT_ICON[al.kind] ?? "mdi:information-outline"}></ha-icon>
          <div><b>${this.t(al.message_key, al.params)}</b>
            ${Array.isArray(al.params.plants) && al.params.plants.length ? html`<div class="small">${(al.params.plants as string[]).join(", ")}</div>` : nothing}</div>
        </div>`)}
      </section>` : nothing}

      ${!snap.beds.length && this.admin ? this.renderWelcome() : nothing}
      <div class="grid">
        <section class="card span-8" aria-labelledby="today-h">
          <header><h2 id="today-h">${this.t("dash.today_tasks")}</h2><span class="spacer"></span>
            ${due.length ? html`<span class="small muted">${this.t("dash.total_time", { minutes })}</span>` : nothing}</header>
          ${due.length ? html`<ul class="tasks">${due.slice(0, 10).map((task) => renderTaskRow(task, this.ctx))}</ul>` : html`<p class="empty">${this.t("dash.no_tasks")}</p>`}
          ${due.length > 10 ? html`<button class="btn small ghost" @click=${() => this.emit("navigate", "calendar")}>${this.t("dash.show_all", { n: due.length })}</button>` : nothing}
        </section>

        ${this.api && this.admin ? html`<section class="card span-12" aria-labelledby="quick-h">
          <header><h2 id="quick-h">${this.t("quick.title")}</h2><span class="spacer"></span><span class="small muted">${this.t("quick.hint")}</span></header>
          <hl-quick-harvest .snapshot=${snap} .api=${this.api} .t=${this.t} .plants=${this.plants} .families=${this.families} lang=${this.lang}></hl-quick-harvest>
        </section>` : nothing}
        ${a.pests?.length ? html`<section class="card span-12" aria-labelledby="pests-h">
          <header><h2 id="pests-h">${this.t("pests.title")}</h2><span class="spacer"></span><span class="small muted">${this.t("pests.hint")}</span></header>
          <ul class="pests">${a.pests.map((w) => html`<li>
            <span class="chip ${w.status === "active" ? "warn" : "info"}">${this.t(`pests.status.${w.status}`)}</span>
            <div><b>${w.label.charAt(0).toUpperCase() + w.label.slice(1)}</b> · <span class="small">${w.plants.join(", ")}</span>
              <div class="xs muted">${w.status === "soon" && w.start ? this.t("pests.from", { date: formatDate(w.start, this.lang) }) : w.end ? this.t("pests.until", { date: formatDate(w.end, this.lang) }) : ""}${w.source === "gdd" && w.gdd != null ? ` · ${this.t("pests.gdd", { gdd: Math.round(w.gdd), gen: w.generation })}` : w.source === "weather" ? ` · ${this.t("pests.weather")}` : ""}</div>
              <div class="small">${w.advice}</div></div>
          </li>`)}</ul>
        </section>` : nothing}
        <section class="card span-4" aria-labelledby="weather-h">
          <header><h2 id="weather-h">${this.t("dash.weather")}</h2></header>
          ${a.weather_available ? html`
            <div class="days">${a.outlook.slice(0, 3).map((o) => html`
              <div class="day">
                <div class="small muted">${o.day === today ? this.t("common.today") : formatDate(o.day, this.lang, { weekday: "short" })}</div>
                <div class="temp">${o.tmax != null ? Math.round(o.tmax) : "–"}° <span class="muted small">${o.tmin != null ? Math.round(o.tmin) : "–"}°</span></div>
                <div class="xs muted">💧 ${o.rain_mm} mm${o.et0_mm != null ? html` · ET₀ ${o.et0_mm}` : nothing}</div>
              </div>`)}</div>
            <div class="divider"></div>
            <div class="kv"><span>${this.t("dash.frost_risk")}</span><span class="chip ${RISK_CHIP[a.frost.level]}">${this.t(`risk.${a.frost.level}`)}</span></div>
            ${a.frost.plant_level_min_c != null ? html`<div class="kv"><span></span><span class="muted">${this.t("dash.min_temp", { temp: a.frost.plant_level_min_c })}${a.frost.min_at ? ` · ${new Date(a.frost.min_at).toLocaleString(this.lang === "nl" ? "nl-NL" : localeOf(this.lang), { weekday: "short", hour: "2-digit", minute: "2-digit" })}` : ""}</span></div>` : nothing}
          ` : html`<p class="small muted">${this.t("dash.forecast_missing")}</p>`}
          <div class="divider"></div>
          ${a.et0_today != null ? html`<div class="kv"><span>ET₀ ${this.t("common.today").toLowerCase()} <hl-info term="et0" .t=${this.t}></hl-info></span>
            <span><b>${a.et0_today.toFixed(1)} mm</b> <span class="muted xs">${a.et0_method === "penman_monteith" ? "Penman-Monteith" : a.et0_method === "hargreaves" ? "Hargreaves" : ""}</span></span></div>` : nothing}
          ${a.gdd_today != null ? html`<div class="kv"><span>${this.t("dash.gdd_today")}</span><span><b>${a.gdd_today.toFixed(1)}</b></span></div>` : nothing}
          <div class="kv"><span>${this.t("dash.gdd")} <hl-info term="gdd" .t=${this.t}></hl-info></span><span><b>${Math.round(a.gdd.season_total)}</b> <span class="muted xs">${this.t("dash.gdd_since", { date: formatDate(a.gdd.since, this.lang) })}</span></span></div>
        </section>

        <section class="card span-8" aria-labelledby="beds-h">
          <header><h2 id="beds-h">${this.t("dash.beds")}</h2></header>
          <div class="beds">${snap.beds.map((bed) => this.renderBed(bed.id))}</div>
        </section>

        ${this.renderWaterClimate()}

        <section class="card span-4" aria-labelledby="up-h">
          ${greenhouses.map((z) => {
            const gh = a.zones[z.id]?.greenhouse;
            return html`<header><h2>${z.name}</h2><span class="spacer"></span>
                <span class="chip ${gh?.action === "none" || !gh ? "ok" : gh.action === "shade" || gh.action === "heat" ? "bad" : "warn"}">${this.t(`gh.${gh?.action ?? "none"}`)}</span></header>
              ${a.zones[z.id]?.air_temperature != null ? html`<div class="big">${a.zones[z.id].air_temperature?.toFixed(1)}°</div>` : html`<p class="small muted">${this.t("dash.no_sensor")}</p>`}
              ${gh?.limit_max_c != null && gh.limiting_plants.length ? html`<p class="small muted">${this.t("dash.limits", { min: gh.limit_min_c, max: gh.limit_max_c })} (${gh.limiting_plants.join(", ")})</p>` : nothing}
              ${gh?.forecast_max_c != null ? html`<p class="xs muted">↑ ${gh.forecast_max_c}° · ↓ ${gh.forecast_min_c ?? "–"}°</p>` : nothing}
              <div class="divider"></div>`;
          })}
          <header><h2 id="up-h">${this.t("dash.coming_up")}</h2></header>
          ${upcoming.length ? html`<ul class="tasks">${upcoming.slice(0, 8).map((task) => renderTaskRow(task, this.ctx))}</ul>` : html`<p class="small muted">–</p>`}
        </section>
      </div>
    `;
  }

  private renderWaterClimate(): TemplateResult {
    const snap = this.snapshot;
    const a = snap.analysis!;
    const status = snap.irrigation_status;
    const cfg = snap.settings.irrigation;
    const valves = snap.beds.filter((b) => b.irrigation_entity).length;
    const zones = snap.zones.filter((z) => a.zones[z.id]?.disease && a.zones[z.id].disease!.level !== "unknown");
    const needWater = snap.beds.filter((b) => a.beds[b.id]?.irrigation.action === "water");
    const bedName = (id: string | null) => snap.beds.find((b) => b.id === id)?.name ?? "";
    return html`<section class="card span-4" aria-labelledby="wc-h">
      <header><h2 id="wc-h">${this.t("dash.water_climate")}</h2></header>
      <div class="kv"><span>${this.t("dash.irrigation_mode")}</span><span class="chip">${this.t(`settings.irrigation_mode.${cfg?.mode ?? "advise"}`)}</span></div>
      ${status?.running ? html`<div class="kv"><span class="chip ok"><ha-icon icon="mdi:sprinkler"></ha-icon>${this.t("dash.watering_now", { bed: bedName(status.bed_id) })}</span>
        <button class="btn small danger" @click=${() => this.emit("irrigation", "stop")}>${this.t("dash.stop")}</button></div>` : nothing}
      ${status?.waiting_for_sun ? html`<div class="kv"><span class="chip warn"><ha-icon icon="mdi:solar-power-variant"></ha-icon>${this.t("dash.waiting_for_sun")}</span>
        ${status.waiting_for_sun.battery != null && status.waiting_for_sun.battery_full != null
          ? html`<span class="xs muted">${this.t("dash.waiting_battery", { pct: Math.round(status.waiting_for_sun.battery), full: status.waiting_for_sun.battery_full })}</span>` : nothing}</div>` : nothing}
      ${status?.waiting_for_rain && status.waiting_for_rain === a.today ? html`<div class="kv"><span class="chip warn"><ha-icon icon="mdi:barrel-outline"></ha-icon>${this.t("dash.waiting_for_rain")}</span></div>` : nothing}
      ${status?.last_error ? html`<p class="xs" style="color:var(--hl-danger)">⚠ ${status.last_error}</p>` : nothing}
      <div class="kv"><span>${this.t("dash.beds_need_water")}</span><b>${needWater.length ? needWater.map((b) => b.name).join(", ") : "–"}</b></div>
      ${valves && this.admin && !status?.running ? html`<button class="btn small" @click=${() => this.emit("irrigation", "run")}>
        <ha-icon icon="mdi:sprinkler"></ha-icon>${this.t("dash.water_now")}</button>
        <p class="xs muted">${this.t("dash.safety_note")} <hl-info term="frost_lockout" .t=${this.t}></hl-info></p>` : nothing}
      ${zones.length ? html`<div class="divider"></div>
        <div class="kv"><span><b>${this.t("dash.disease_risk")}</b> <hl-info term="leaf_wetness" .t=${this.t}></hl-info></span></div>
        ${zones.map((z) => {
          const d = a.zones[z.id].disease!;
          return html`<div class="kv"><span>${z.name}</span><span class="chip ${RISK_CHIP[d.level]}">${this.t(`risk.${d.level}`)}${d.wet_hours ? ` · ${Math.round(d.wet_hours)} h` : ""}</span></div>`;
        })}` : nothing}
    </section>`;
  }

  private renderBed(bedId: string): TemplateResult {
    const snap = this.snapshot;
    const bed = snap.beds.find((b) => b.id === bedId)!;
    const ba = snap.analysis?.beds[bedId];
    const irr = ba?.irrigation;
    const status = ba?.moisture_status ?? "unknown";
    const soilT = ba?.sensors?.soil_temperature?.value;
    const active = (ba?.active_plantings ?? []).map((id) => snap.plantings.find((p) => p.id === id)).filter(Boolean);
    const chip = status === "optimal" ? "ok" : status === "dry" ? "bad" : status === "unknown" ? "" : status === "wet" ? "cold" : "warn";
    const pct = (v: number) => Math.max(0, Math.min(100, v));
    return html`
      <article class="bed" aria-label=${bed.name}>
        <div class="row"><h3>${bed.name}</h3><span class="spacer"></span><span class="chip ${chip}">${this.t(`moisture.${status}`)}</span></div>
        ${irr?.moisture != null ? html`
          <div class="gauge" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow=${Math.round(irr.moisture)} aria-label=${this.t("settings.sensor.soil_moisture")}>
            ${irr.target_low != null && irr.target_high != null ? html`<div class="target" style=${`left:${pct(irr.target_low)}%;width:${pct(irr.target_high) - pct(irr.target_low)}%`}></div>` : nothing}
            <div class="value" style=${`left:${pct(irr.moisture)}%`}></div>
          </div>
          <div class="kv"><span>💧 ${Math.round(irr.moisture)}%</span>${soilT != null ? html`<span>🌡 ${soilT.toFixed(1)} °C</span>` : nothing}</div>` : html`<p class="xs muted">${this.t("dash.no_sensor")}</p>`}
        ${soilT == null && ba?.soil_temp_estimate != null ? html`<div class="kv xs muted"><span>${this.t("dash.soil_estimate")}</span><span>≈ ${ba.soil_temp_estimate.toFixed(1)} °C</span></div>` : nothing}
        ${ba?.dry_in_days != null ? html`<div class="kv xs"><span>${this.t("dash.dry_forecast")}</span>
          <span class="chip ${ba.dry_in_days <= 1 ? "warn" : ""}">${ba.dry_in_days === 0 ? this.t("dash.dry_today") : this.t("dash.dry_in", { n: ba.dry_in_days })}</span></div>` : nothing}
        ${irr ? html`<p class="small"><ha-icon icon="mdi:watering-can-outline" style="--mdc-icon-size:16px"></ha-icon>
          ${this.t(`irrigation.${irr.action}`, { mm: irr.amount_mm, liters: Math.round(irr.liters) })}${irr.duration_min ? ` · ${Math.round(irr.duration_min)} min` : ""}</p>` : nothing}
        ${ba?.nutrients?.index != null ? html`<div class="kv"><span>${this.t("dash.nutrients")} <hl-info term="nutrient_index" .t=${this.t}></hl-info></span>
          <span class="chip ${ba.nutrients.status === "balanced" ? "ok" : "warn"}">${ba.nutrients.index}/100</span></div>` : nothing}
        ${ba?.depletion_mm != null && ba.taw_mm ? html`<div class="kv xs muted"><span>${this.t("dash.water_balance")} <hl-info term="water_balance" .t=${this.t}></hl-info></span>
          <span>${Math.round(ba.depletion_mm)} / ${Math.round(ba.taw_mm)} mm</span></div>` : nothing}
        ${ba?.et_factor != null && Math.abs(ba.et_factor - 1) >= 0.05 ? html`<div class="kv xs muted"><span>${this.t("dash.drying")}</span>
          <span>${this.t(ba.et_factor > 1 ? "dash.drying_fast" : "dash.drying_slow", { pct: Math.round(Math.abs(ba.et_factor - 1) * 100) })}</span></div>` : nothing}
        <div class="avatars" role="group" aria-label=${this.t("dash.active_crops", { n: active.length })}>
          ${active.map((p) => {
            const plant = this.plants.get(p!.plant_id);
            const name = plantName(plant, this.lang);
            const color = plant?.color || familyColor(this.families, plant?.family);
            return html`<button class="avatar" title=${name} style=${`background:${tileColor(color)}`}
              @click=${() => plant && this.emit("open-plant", plant.id)}>${plant ? glyphIcon(glyphFor(plant), color, 22) : name.slice(0, 2)}</button>`;
          })}
        </div>
      </article>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-dashboard-view": DashboardView;
  }
}

/** Hand-drawn botanical line art for the hero, one sprig per season. */
function botanical(season: string): TemplateResult {
  const ink = "color-mix(in srgb, var(--hl-hero-ink) 32%, transparent)";
  const fill = { spring: "#7fb069", summer: "#e8a33d", autumn: "#c8742f", winter: "#7d9bb8" }[season] ?? "#7fb069";
  return html`<svg class="art" viewBox="0 0 260 220" aria-hidden="true">
    <g fill="none" stroke=${ink} stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M150 220 C150 170 146 120 160 70 C168 42 182 22 200 8" />
      <path d="M152 170 C128 160 112 140 108 116 C132 118 150 136 152 170 Z" fill=${fill} fill-opacity="0.28" />
      <path d="M156 128 C182 122 200 104 206 80 C182 82 162 98 156 128 Z" fill=${fill} fill-opacity="0.28" />
      <path d="M160 92 C140 82 130 64 130 44 C150 50 162 68 160 92 Z" fill=${fill} fill-opacity="0.22" />
      <path d="M182 40 C198 40 212 30 220 16 C204 14 190 24 182 40 Z" fill=${fill} fill-opacity="0.22" />
      <path d="M152 170 L130 132 M156 128 L190 96 M160 92 L142 60" stroke-width="1" />
      <circle cx="214" cy="54" r="7" fill=${fill} fill-opacity="0.5" />
      <circle cx="226" cy="70" r="4.5" fill=${fill} fill-opacity="0.4" />
      <path d="M60 220 C64 190 58 166 70 140 M70 140 C58 128 52 112 56 96 C68 104 74 120 70 140 Z" fill=${fill} fill-opacity="0.16" />
    </g>
  </svg>`;
}
