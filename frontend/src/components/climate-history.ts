/**
 * Climate history and statistics (Weather tab): what the weather really did here.
 *
 * A daily chart (temperature range, mean and rain) for 30 days, 90 days or a year,
 * the last week / month / season compared with the same period last year, all-time
 * records, every measured temperature sensor (greenhouse air, soil ...), a monthly
 * table and the measured frost dates against the regional preset.  Data comes from
 * ``climate/stats``: own samples, the recorder's history and Open-Meteo's observed
 * weather for days nobody measured.
 */
import { LitElement, css, html, nothing, svg, type PropertyValues, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { ClimateDayRow, ClimatePeriod, ClimateSensorStats, ClimateStats } from "../types";
import { localeOf } from "../util/garden";

type Range = 30 | 90 | 365;
const REFRESH_MS = 10 * 60_000;

@customElement("hl-climate-history")
export class ClimateHistory extends LitElement {
  @property({ attribute: false }) api?: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  /** Bumped by the parent when the garden changed (new day, new sensors). */
  @property({ type: Number }) revision = 0;
  /** May change settings (apply the measured frost dates, import a station CSV). */
  @property({ type: Boolean }) admin = false;
  @state() private importMsg = "";
  @state() private frostMsg = "";
  @state() private busy = false;
  @state() private stats: ClimateStats | null = null;
  @state() private range: Range = 30;
  @state() private failed = false;
  private loadedAt = 0;
  private timer?: number;

  static styles = [
    shared,
    css`
      :host { display: block; }
      .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--hl-s4); }
      .s12 { grid-column: span 12; } .s8 { grid-column: span 8; } .s6 { grid-column: span 6; } .s4 { grid-column: span 4; }
      @media (max-width: 1100px) { .s8, .s6, .s4 { grid-column: span 12; } }
      header.bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; }
      .chips { display: flex; gap: 6px; }
      .chart svg { width: 100%; height: auto; display: block; }
      .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
      .tile { border-radius: 14px; background: var(--hl-surface-2); padding: 10px 12px; }
      .tile .v { font-family: var(--hl-font-serif); font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
      .tile .l { font-size: var(--hl-fs-xs); color: var(--hl-text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
      .tile .d { font-size: var(--hl-fs-xs); font-variant-numeric: tabular-nums; }
      .up { color: var(--hl-danger-ink, #9a2e1c); } .down { color: var(--hl-water-ink, #2a5f86); }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); font-variant-numeric: tabular-nums; }
      th, td { text-align: right; padding: 5px 6px; border-top: 1px solid color-mix(in srgb, var(--hl-border) 60%, transparent); white-space: nowrap; }
      th:first-child, td:first-child { text-align: left; }
      th { font-weight: 600; color: var(--hl-text-muted); font-size: var(--hl-fs-xs); border-top: 0; }
      .scroll { overflow-x: auto; }
      .spark { width: 110px; height: 26px; vertical-align: middle; }
      .note { font-size: var(--hl-fs-xs); color: var(--hl-text-muted); }
      .kind { font-size: 11px; color: var(--hl-text-muted); display: block; }
      .uses li { margin: 2px 0; }
      .summary p { margin: 2px 0; }
      .suggest { border-radius: 12px; padding: 10px 12px; background: color-mix(in srgb, var(--hl-info) 10%, var(--hl-surface)); margin-top: 8px; }
      input[type="file"] { max-width: 100%; }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this.timer = window.setInterval(() => void this.load(), REFRESH_MS);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.timer);
  }

  protected willUpdate(changed: PropertyValues): void {
    if ((changed.has("api") || changed.has("revision")) && this.api && Date.now() - this.loadedAt > 60_000) void this.load();
  }

  private async load(): Promise<void> {
    if (!this.api) return;
    this.loadedAt = Date.now();
    try {
      this.stats = await this.api.climateStats(400);
      this.failed = false;
    } catch {
      this.failed = true;
    }
  }

  // -- formatting ------------------------------------------------------- //
  private n(v: number | null | undefined, digits = 1, unit = ""): string {
    if (v == null) return "–";
    return `${v.toLocaleString(localeOf(this.lang), { maximumFractionDigits: digits, minimumFractionDigits: 0 })}${unit}`;
  }

  private date(iso: string | null | undefined, month = false): string {
    if (!iso) return "–";
    const [year, monthNumber, day = 1] = iso.split("-").map(Number);
    const d = new Date(year, monthNumber - 1, day); // a local calendar date: no shift west of UTC
    return d.toLocaleDateString(localeOf(this.lang), month || iso.length === 7 ? { month: "short", year: "numeric" } : { day: "numeric", month: "short" });
  }

  private delta(now: number | null | undefined, before: number | null | undefined, unit: string, digits = 1): TemplateResult | typeof nothing {
    if (now == null || before == null) return nothing;
    const d = now - before;
    if (Math.abs(d) < 10 ** -digits / 2) return html`<span class="d">${this.t("climate.same_as_last_year")}</span>`;
    return html`<span class="d ${d > 0 ? "up" : "down"}">${d > 0 ? "+" : "−"}${this.n(Math.abs(d), digits)}${unit} ${this.t("climate.vs_last_year")}</span>`;
  }

  // -- chart -------------------------------------------------------------- //
  private renderChart(rows: ClimateDayRow[]): TemplateResult {
    const days = rows.filter((r) => r.lo != null && r.hi != null);
    if (days.length < 2) return html`<p class="small muted">${this.t("climate.too_few")}</p>`;
    const W = 900, H = 270, L = 36, R = 12, T = 12, RAIN_H = 46;
    const lo = Math.floor(Math.min(0, ...days.map((d) => d.lo as number)) / 5) * 5;
    const hi = Math.ceil(Math.max(...days.map((d) => d.hi as number)) / 5) * 5;
    const t0 = new Date(rows[0].d).getTime(), t1 = new Date(rows[rows.length - 1].d).getTime();
    const x = (iso: string) => L + ((new Date(iso).getTime() - t0) / Math.max(1, t1 - t0)) * (W - L - R);
    const y = (v: number) => T + (1 - (v - lo) / Math.max(1, hi - lo)) * (H - 20 - RAIN_H - 16 - T);
    const band = `${days.map((d, i) => `${i ? "L" : "M"}${x(d.d).toFixed(1)},${y(d.hi as number).toFixed(1)}`).join(" ")} `
      + `${[...days].reverse().map((d) => `L${x(d.d).toFixed(1)},${y(d.lo as number).toFixed(1)}`).join(" ")} Z`;
    const means = days.filter((d) => d.m != null);
    const mean = means.map((d, i) => `${i ? "L" : "M"}${x(d.d).toFixed(1)},${y(d.m as number).toFixed(1)}`).join(" ");
    const maxRain = Math.max(5, ...rows.map((r) => r.r ?? 0));
    const bw = Math.max(1, ((W - L - R) / rows.length) * 0.7);
    const rainBase = H - 20 - RAIN_H; // rain bars between the temperatures and the date labels
    const ticks: number[] = [];
    for (let v = lo; v <= hi; v += hi - lo > 30 ? 10 : 5) ticks.push(v);
    const labels = rows.filter((r, i) => (this.range === 30 ? i % 5 === 0 : r.d.endsWith("-01")));
    return html`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label=${this.t("climate.chart")}>
      ${ticks.map((v) => svg`<line x1=${L} x2=${W - R} y1=${y(v)} y2=${y(v)} stroke=${v === 0 ? "#6aa9de" : "var(--hl-border)"} stroke-width=${v === 0 ? 1.4 : 0.6} stroke-dasharray=${v === 0 ? "4 3" : ""}/>
        <text x=${L - 6} y=${y(v) + 4} text-anchor="end" font-size="11" fill="var(--hl-text-muted)">${v}°</text>`)}
      <path d=${band} fill="#f2b544" fill-opacity="0.28" stroke="none"/>
      ${mean ? svg`<path d=${mean} fill="none" stroke="#e08a2e" stroke-width="2" stroke-linejoin="round"/>` : nothing}
      ${rows.map((r) => (r.r ?? 0) > 0 ? svg`<rect x=${x(r.d) - bw / 2} width=${bw} y=${rainBase + RAIN_H - ((r.r ?? 0) / maxRain) * RAIN_H} height=${((r.r ?? 0) / maxRain) * RAIN_H}
        fill="#4a90c8" fill-opacity="0.7" rx="1"/>` : nothing)}
      ${rows.map((r) => svg`<rect x=${x(r.d) - (W - L - R) / rows.length / 2} y=${T} width=${(W - L - R) / rows.length} height=${H - T - 18} fill="transparent">
        <title>${this.date(r.d)}: ${this.n(r.lo)}° – ${this.n(r.hi)}°${r.r != null ? ` · ${this.n(r.r)} mm` : ""}${r.s != null ? ` · ☀ ${this.n(r.s)} h` : ""}${r.w != null ? ` · ${this.n(r.w, 0)} km/h` : ""}${r.src && r.src !== "sensor" ? ` · ${this.t(`climate.src.${r.src.split("+").pop()}`)}` : ""}</title></rect>`)}
      ${labels.map((r) => svg`<text x=${x(r.d)} y=${H - 4} text-anchor="middle" font-size="11" fill="var(--hl-text-muted)">${this.date(r.d, this.range !== 30)}</text>`)}
      <text x=${L} y=${rainBase - 2} font-size="10" fill="#4a90c8">${this.t("climate.rain")} (max ${this.n(maxRain, 0)} mm)</text>
    </svg>`;
  }

  // -- periods ------------------------------------------------------------ //
  private tiles(p: ClimatePeriod, before?: ClimatePeriod): TemplateResult {
    const tile = (label: string, value: string, d: TemplateResult | typeof nothing = nothing, sub = "") =>
      html`<div class="tile"><div class="l">${label}</div><div class="v">${value}</div>${sub ? html`<div class="d">${sub}</div>` : nothing}${d}</div>`;
    return html`<div class="tiles">
      ${tile(this.t("climate.mean"), this.n(p.tmean, 1, "°"), this.delta(p.tmean, before?.tmean, "°"))}
      ${tile(this.t("climate.lowest"), this.n(p.tmin, 1, "°"), nothing, this.date(p.tmin_day))}
      ${tile(this.t("climate.highest"), this.n(p.tmax, 1, "°"), nothing, this.date(p.tmax_day))}
      ${tile(this.t("climate.rain"), this.n(p.rain_mm, 0, " mm"), this.delta(p.rain_mm, before?.rain_mm, " mm", 0), this.t("climate.rain_days", { n: p.rain_days }))}
      ${tile(this.t("climate.frost_nights"), String(p.frost_nights ?? "–"), this.delta(p.frost_nights, before?.frost_nights, "", 0))}
      ${tile(this.t("climate.hot_days"), String(p.hot_days ?? "–"), this.delta(p.hot_days, before?.hot_days, "", 0), p.very_hot_days ? this.t("climate.very_hot", { n: p.very_hot_days }) : "")}
      ${tile(this.t("climate.sun"), this.n(p.sun_h, 0, " h"), this.delta(p.sun_h, before?.sun_h, " h", 0))}
      ${tile(this.t("climate.gust"), this.n(p.gust_max, 0, " km/h"), nothing, this.date(p.gust_day))}
      ${tile(this.t("climate.gdd"), this.n(p.gdd, 0), this.delta(p.gdd, before?.gdd, "", 0))}
      ${tile(this.t("climate.et0"), this.n(p.et0_mm, 0, " mm"), nothing, p.balance_mm != null ? this.t("climate.balance", { mm: this.n(p.balance_mm, 0) }) : "")}
    </div>`;
  }

  private renderPeriods(s: ClimateStats): TemplateResult {
    const p = s.periods;
    return html`<div class="stack" style="gap:14px">
      <div><h3>${this.t("climate.last_7")}</h3>${this.tiles(p.d7, p.d7_last_year?.days ? p.d7_last_year : undefined)}</div>
      <div><h3>${this.t("climate.last_30")}</h3>${this.tiles(p.d30, p.d30_last_year.days ? p.d30_last_year : undefined)}</div>
      <div><h3>${this.t("climate.season", { since: this.date(s.season_start) })}</h3>${this.tiles(p.season, p.season_last_year.days ? p.season_last_year : undefined)}</div>
    </div>`;
  }

  // -- sensors ------------------------------------------------------------ //
  private spark(rows: NonNullable<ClimateSensorStats["series"]>): TemplateResult | typeof nothing {
    const pts = rows.slice(-30).filter((r) => r.lo != null && r.hi != null);
    if (pts.length < 2) return nothing;
    const lo = Math.min(...pts.map((r) => r.lo as number)), hi = Math.max(...pts.map((r) => r.hi as number));
    const x = (i: number) => (i / (pts.length - 1)) * 108 + 1;
    const y = (v: number) => 24 - ((v - lo) / Math.max(1, hi - lo)) * 22;
    const top = pts.map((r, i) => `${i ? "L" : "M"}${x(i)},${y(r.hi as number)}`).join(" ");
    const bottom = [...pts].reverse().map((r, i) => `L${x(pts.length - 1 - i)},${y(r.lo as number)}`).join(" ");
    return html`<svg class="spark" viewBox="0 0 110 26" aria-hidden="true"><path d="${top} ${bottom} Z" fill="#f2b544" fill-opacity="0.35" stroke="#e08a2e" stroke-width="0.8"/></svg>`;
  }

  private renderSensors(s: ClimateStats): TemplateResult {
    if (!s.sensors.length) return html`<p class="small muted">${this.t("climate.no_sensors")}</p>`;
    return html`<div class="scroll" tabindex="0" role="region" aria-label=${this.t("climate.table")}><table>
      <thead><tr><th>${this.t("climate.sensor")}</th><th>${this.t("climate.now")}</th><th>${this.t("climate.today")}</th>
        <th>${this.t("climate.mean_7")}</th><th>${this.t("climate.range_30")}</th><th>${this.t("climate.record_low")}</th>
        <th>${this.t("climate.record_high")}</th><th>${this.t("climate.days")}</th><th></th></tr></thead>
      <tbody>${s.sensors.map((x) => html`<tr>
        <td>${x.label === "outdoor" ? this.t("climate.outdoor") : x.label}<span class="kind">${this.t(`climate.kind.${x.kind}`)} · ${x.entity_id}</span></td>
        <td>${this.n(x.now, 1, "°")}</td>
        <td>${x.today ? `${this.n(x.today.tmin, 1)}° – ${this.n(x.today.tmax, 1)}°` : "–"}</td>
        <td>${this.n(x.d7?.tmean, 1, "°")}</td>
        <td>${x.d30 ? `${this.n(x.d30.tmin, 1)}° – ${this.n(x.d30.tmax, 1)}°` : "–"}</td>
        <td>${x.record_low ? html`${this.n(x.record_low.t, 1, "°")}<span class="kind">${this.date(x.record_low.when)}</span>` : "–"}</td>
        <td>${x.record_high ? html`${this.n(x.record_high.t, 1, "°")}<span class="kind">${this.date(x.record_high.when)}</span>` : "–"}</td>
        <td>${x.days}</td>
        <td>${this.spark(x.series ?? [])}</td>
      </tr>`)}</tbody></table></div>`;
  }

  // -- months, records, frost -------------------------------------------- //
  private renderMonths(s: ClimateStats): TemplateResult {
    if (!s.months.length) return html`<p class="small muted">${this.t("climate.too_few")}</p>`;
    const byMonth = new Map(s.months.map((m) => [m.month, m]));
    const ago = (m: string) => `${Number(m.slice(0, 4)) - 1}${m.slice(4)}`;
    return html`<div class="scroll" tabindex="0" role="region" aria-label=${this.t("climate.table")}><table>
      <thead><tr><th>${this.t("climate.month")}</th><th>${this.t("climate.mean")}</th><th>${this.t("climate.lowest")}</th><th>${this.t("climate.highest")}</th>
        <th>${this.t("climate.rain")}</th><th>${this.t("climate.frost_nights")}</th><th>${this.t("climate.hot_days")}</th><th>${this.t("climate.sun")}</th><th>${this.t("climate.gust")}</th></tr></thead>
      <tbody>${s.months.slice(0, 13).map((m) => {
        const before = byMonth.get(ago(m.month));
        return html`<tr><td>${this.date(m.month, true)}<span class="kind">${this.t("climate.days_logged", { n: m.days })}</span></td>
          <td>${this.n(m.tmean, 1, "°")}${before ? html`<span class="kind">${this.delta(m.tmean, before.tmean, "°")}</span>` : nothing}</td>
          <td>${this.n(m.tmin, 1, "°")}</td><td>${this.n(m.tmax, 1, "°")}</td>
          <td>${this.n(m.rain_mm, 0, " mm")}${before ? html`<span class="kind">${this.delta(m.rain_mm, before.rain_mm, " mm", 0)}</span>` : nothing}</td>
          <td>${m.frost_days}</td><td>${m.hot_days}</td><td>${this.n(m.sun_h, 0, " h")}</td><td>${this.n(m.wind_max, 0)}</td></tr>`;
      })}</tbody></table></div>`;
  }

  private renderRecords(s: ClimateStats): TemplateResult {
    const r = s.records;
    const row = (key: "tmin" | "tmax" | "wettest" | "gust_max", unit: string, digits = 1) =>
      r[key] ? html`<tr><td>${this.t(`climate.record.${key}`)}</td><td>${this.n(r[key]!.value, digits, unit)}</td><td>${this.date(r[key]!.when)}</td></tr>` : nothing;
    return html`<table><tbody>${row("tmin", "°")}${row("tmax", "°")}${row("wettest", " mm", 0)}${row("gust_max", " km/h", 0)}</tbody></table>
      <p class="note" style="margin-top:8px">${this.t("climate.coverage", { days: s.coverage.days, since: this.date(s.coverage.first_day), months: s.coverage.months_kept })}</p>
      <p class="note">${Object.entries(s.coverage.sources).map(([k, v]) => `${this.t(`climate.src.${k}`)}: ${v}`).join(" · ")}</p>`;
  }

  /** The season and last month in words, against last year (settings.season_summary). */
  private renderSummary(s: ClimateStats): TemplateResult | typeof nothing {
    const sum = s.summary;
    if (!sum || (!sum.season.length && !sum.month.length)) return nothing;
    const month = new Date(`${sum.month_start}T12:00:00`).toLocaleDateString(localeOf(this.lang), { month: "long", year: "numeric" });
    return html`<section class="card s12 summary"><header><h2>${this.t("climate.summary_title")}</h2></header>
      <div class="grid">
        ${sum.season.length ? html`<div class="s6"><h3>${this.t("climate.summary_season")}</h3>${sum.season.map((l) => html`<p class="small">${l}</p>`)}</div>` : nothing}
        ${sum.month.length ? html`<div class="s6"><h3>${month}</h3>${sum.month.map((l) => html`<p class="small">${l}</p>`)}</div>` : nothing}
      </div></section>`;
  }

  private async applyFrost(): Promise<void> {
    if (!this.api || this.busy) return;
    this.busy = true;
    this.frostMsg = "";
    try {
      await this.api.applyLocalFrost();
      await this.load();
    } catch (err) {
      this.frostMsg = `${this.t("climate.frost_apply_failed")} ${(err as { message?: string }).message ?? ""}`;
    } finally {
      this.busy = false;
    }
  }

  /** A weather station's export (Netatmo, Ecowitt, Davis ...) into the history (settings.station_import). */
  private async importCsv(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !this.api) return;
    this.busy = true;
    this.importMsg = "";
    try {
      const r = await this.api.importStationCsv(await file.text());
      this.importMsg = r.days
        ? this.t("climate.import_done", { days: r.days, first: this.date(r.first), last: this.date(r.last), columns: Object.keys(r.columns).join(", ") })
        : this.t("climate.import_empty");
      await this.load();
    } catch (err) {
      this.importMsg = `${this.t("climate.import_failed")} ${(err as { message?: string }).message ?? ""}`;
    } finally {
      this.busy = false;
      input.value = "";
    }
  }

  private renderImport(s: ClimateStats): TemplateResult | typeof nothing {
    if (!this.admin || s.station_import === false) return nothing;
    return html`<h3 style="margin-top:14px">${this.t("climate.import_title")}</h3>
      <p class="note">${this.t("climate.import_hint")}</p>
      <input type="file" accept=".csv,text/csv,text/plain" ?disabled=${this.busy} aria-label=${this.t("climate.import_title")} @change=${(e: Event) => void this.importCsv(e)} />
      ${this.importMsg ? html`<p class="small" role="status">${this.importMsg}</p>` : nothing}`;
  }

  private renderFrost(s: ClimateStats): TemplateResult {
    const years = Object.entries(s.frost.years).reverse();
    const local = s.frost.local;
    const diff = (d: number | undefined) => (d == null ? "" : d === 0 ? this.t("climate.frost_same") : this.t(d < 0 ? "climate.frost_earlier" : "climate.frost_later", { n: Math.abs(d) }));
    return html`
      ${local ? html`<div class="stack" style="gap:6px">
        ${local.last_spring ? html`<p class="small">${this.t("climate.frost_local_spring", { date: this.date(`2000-${local.last_spring}`), preset: this.date(`2000-${s.frost.preset_last}`), diff: diff(local.spring_diff_days), years: local.years_spring })}</p>` : nothing}
        ${local.first_autumn ? html`<p class="small">${this.t("climate.frost_local_autumn", { date: this.date(`2000-${local.first_autumn}`), preset: this.date(`2000-${s.frost.preset_first}`), diff: diff(local.autumn_diff_days), years: local.years_autumn })}</p>` : nothing}
        <p class="note">${this.t("climate.frost_hint")}</p></div>` : html`<p class="small muted">${this.t("climate.frost_none", { preset: this.date(`2000-${s.frost.preset_last ?? "04-15"}`) })}</p>`}
      ${years.length ? html`<table style="margin-top:8px"><thead><tr><th>${this.t("climate.year")}</th><th>${this.t("climate.last_spring")}</th><th>${this.t("climate.first_autumn")}</th></tr></thead>
        <tbody>${years.map(([y, f]) => html`<tr><td>${y}</td><td>${this.date(f.last_spring)}${f.spring_complete ? "" : " *"}</td><td>${this.date(f.first_autumn)}${f.autumn_complete ? "" : " *"}</td></tr>`)}</tbody></table>
        <p class="note">* ${this.t("climate.incomplete")}</p>` : nothing}
      ${s.local_frost_suggestion ? html`<div class="suggest">
        <p class="small">${this.t("climate.frost_suggest", { last: this.date(`2000-${s.local_frost_suggestion.last_frost}`), first: this.date(`2000-${s.local_frost_suggestion.first_frost}`), years: s.local_frost_suggestion.years })}</p>
        ${this.admin ? html`<button class="btn small" ?disabled=${this.busy} @click=${() => void this.applyFrost()}>${this.t("climate.frost_apply")}</button>` : nothing}
      </div>` : nothing}
      ${this.frostMsg ? html`<p class="small" role="alert">${this.frostMsg}</p>` : nothing}`;
  }

  render(): TemplateResult {
    if (this.failed && !this.stats) return html`<section class="card"><h2>${this.t("climate.title")}</h2><p class="small muted">${this.t("climate.failed")}</p></section>`;
    const s = this.stats;
    if (!s) return html`<section class="card"><h2>${this.t("climate.title")}</h2><p class="small muted">${this.t("common.loading")}</p></section>`;
    const [ty, tm, td] = s.today.split("-").map(Number);
    const cutoff = new Date(Date.UTC(ty, tm - 1, td - this.range + 1)).toISOString().slice(0, 10);
    const rows = s.series.filter((r) => r.d >= cutoff); // ISO days compare as text: no daylight-saving shift
    return html`<div class="grid" style="margin-top:var(--hl-s4)">
      <section class="card s12 chart">
        <header class="bar"><h2>${this.t("climate.title")}</h2>
          <div class="chips" role="tablist">${([30, 90, 365] as Range[]).map((r) => html`<button class="chip" role="tab" aria-selected=${String(this.range === r)}
            @click=${() => (this.range = r)}>${this.t(`climate.range.${r}`)}</button>`)}</div></header>
        ${this.renderChart(rows)}
        <p class="note">${this.t("climate.legend")}</p>
      </section>
      ${this.renderSummary(s)}
      <section class="card s8"><header><h2>${this.t("climate.periods")}</h2></header>${this.renderPeriods(s)}</section>
      <section class="card s4"><header><h2>${this.t("climate.records")}</h2></header>${this.renderRecords(s)}
        <h3 style="margin-top:14px">${this.t("climate.uses_title")}</h3>
        <ul class="small uses">${["gdd", "water", "disease", "tasks", "frost"].map((k) => html`<li>${this.t(`climate.uses.${k}`)}</li>`)}</ul>
        ${this.renderImport(s)}</section>
      <section class="card s12"><header><h2>${this.t("climate.sensors")}</h2></header>${this.renderSensors(s)}</section>
      <section class="card s8"><header><h2>${this.t("climate.months")}</h2></header>${this.renderMonths(s)}</section>
      <section class="card s4"><header><h2>${this.t("climate.frost_title")}</h2></header>${this.renderFrost(s)}</section>
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-climate-history": ClimateHistory;
  }
}
