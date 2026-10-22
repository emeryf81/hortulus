/**
 * Weather tab: the weather now, the next 24 hours, the coming days, what it
 * means for the garden (frost, heat, rain, dry spells) and a rain radar map.
 *
 * Forecasts come live from Home Assistant (``weather/subscribe_forecast`` on the
 * garden's weather entity); the radar is a camera entity when there is one
 * (e.g. the Buienradar integration), else Buienradar's public map for NL / BE.
 */
import { LitElement, css, html, nothing, svg, type PropertyValues, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Translate } from "../i18n";
import { localeOf } from "../util/garden";
import { shared } from "../styles/tokens";
import type { GardenApi } from "../api";
import "../components/climate-history";
import type { HomeAssistant, Snapshot } from "../types";

interface Fc {
  datetime: string;
  condition?: string;
  temperature?: number;
  templow?: number;
  precipitation?: number;
  precipitation_probability?: number;
  wind_speed?: number;
  wind_bearing?: number;
  humidity?: number;
  is_daytime?: boolean;
}

const RADAR_REFRESH_MS = 5 * 60_000;

/** Hand-drawn weather glyphs in one consistent style (no icon font needed). */
export function weatherGlyph(condition: string | undefined, size = 40, night = false): TemplateResult {
  const c = condition ?? "cloudy";
  const sun = svg`<g><circle cx="22" cy="20" r="8" fill="#F2B544"/>
    ${[0, 45, 90, 135, 180, 225, 270, 315].map((a) => svg`<line x1=${22 + Math.cos((a * Math.PI) / 180) * 11.5} y1=${20 + Math.sin((a * Math.PI) / 180) * 11.5}
      x2=${22 + Math.cos((a * Math.PI) / 180) * 15} y2=${20 + Math.sin((a * Math.PI) / 180) * 15} stroke="#F2B544" stroke-width="2.2" stroke-linecap="round"/>`)}</g>`;
  const moon = svg`<path d="M26 8a11 11 0 1 0 10 15 9 9 0 0 1-10-15z" fill="#C9D6E8"/>`;
  const cloud = (fill = "#E3E9EF", dy = 0) => svg`<path transform="translate(0 ${dy})" d="M14 38h22a8 8 0 0 0 0-16 11 11 0 0 0-21-2 7 7 0 0 0-1 18z" fill=${fill} stroke="#AEB9C4" stroke-width="1.2"/>`;
  const drops = (n: number) => svg`${Array.from({ length: n }, (_, i) => svg`<line x1=${17 + i * 7} y1="41" x2=${15 + i * 7} y2="47" stroke="#4A90C8" stroke-width="2.2" stroke-linecap="round"/>`)}`;
  const flakes = svg`${[17, 25, 33].map((x) => svg`<circle cx=${x} cy="44" r="1.8" fill="#9DB7D1"/>`)}`;
  const bolt = svg`<path d="M26 36l-5 8h4l-2 7 7-10h-4l3-5z" fill="#F2B544"/>`;
  const fog = svg`${[30, 36, 42].map((y) => svg`<line x1="10" y1=${y} x2="40" y2=${y} stroke="#AEB9C4" stroke-width="2.4" stroke-linecap="round"/>`)}`;
  const wind = svg`<path d="M8 22h22a4 4 0 1 0-4-4M8 30h28a4 4 0 1 1-4 4M8 38h16" fill="none" stroke="#8FA3B5" stroke-width="2.4" stroke-linecap="round"/>`;
  let body: TemplateResult;
  switch (c) {
    case "sunny": body = sun; break;
    case "clear-night": body = moon; break;
    case "partlycloudy": body = svg`${night ? moon : sun}${cloud("#EEF2F6", 4)}`; break;
    case "rainy": body = svg`${cloud()}${drops(3)}`; break;
    case "pouring": body = svg`${cloud("#CBD5DF")}${drops(4)}`; break;
    case "snowy": case "snowy-rainy": case "hail": body = svg`${cloud()}${flakes}`; break;
    case "lightning": case "lightning-rainy": body = svg`${cloud("#CBD5DF")}${bolt}`; break;
    case "fog": body = svg`${cloud("#EEF2F6", -6)}${fog}`; break;
    case "windy": case "windy-variant": body = wind; break;
    default: body = cloud();
  }
  return html`<svg width=${size} height=${size} viewBox="0 0 50 50" aria-hidden="true">${body}</svg>`;
}

@customElement("hl-weather-view")
export class WeatherView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) api?: GardenApi;
  /** A visitor of a shared garden (website): the forecast, not the garden's own history. */
  @property({ type: Boolean }) viewer = false;
  /** A visitor of a shared garden on the website may see the climate history (the owner's choice). */
  @property({ type: Boolean }) viewerClimate = false;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @state() private daily: Fc[] = [];
  @state() private hourly: Fc[] = [];
  @state() private radarTick = Date.now();
  @state() private radarFailed = false;
  private unsubs: Promise<() => Promise<void>>[] = [];
  private subscribedTo = "";
  private generation = 0;
  private timer?: number;

  static styles = [
    shared,
    css`
      :host { display: block; }
      .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--hl-s4); }
      .s12 { grid-column: span 12; } .s7 { grid-column: span 7; } .s5 { grid-column: span 5; }
      @media (max-width: 1100px) { .s7, .s5 { grid-column: span 12; } }
      .now { position: relative; overflow: hidden; border-radius: 22px; padding: 26px 30px; color: var(--hl-hero-ink);
        background: var(--sky, var(--hl-grad-winter)); box-shadow: var(--hl-shadow-2), var(--hl-highlight); display: flex; flex-wrap: wrap; gap: 24px; align-items: center; }
      .now .temp { font-family: var(--hl-font-serif); font-size: 64px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
      .now .cond { font-family: var(--hl-font-serif); font-size: 22px; font-style: italic; }
      .now .facts { display: grid; grid-template-columns: repeat(2, auto); gap: 4px 18px; font-size: var(--hl-fs-sm); margin-left: auto; }
      .now .facts b { font-variant-numeric: tabular-nums; }
      .hint { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 12px; background: var(--hl-surface-2); font-size: var(--hl-fs-sm); }
      .hint.frost { background: var(--hl-frost-100); } .hint.heat { background: var(--hl-sun-100); } .hint.wet { background: color-mix(in srgb, var(--hl-water-500) 12%, var(--hl-surface)); }
      .hint.dry { background: var(--hl-soil-100); }
      .hint b { display: block; }
      .hours svg { width: 100%; height: auto; display: block; }
      .days { display: flex; flex-direction: column; }
      .day { display: grid; grid-template-columns: 92px 44px 70px 1fr 64px; align-items: center; gap: 10px; padding: 8px 4px; border-top: 1px solid color-mix(in srgb, var(--hl-border) 60%, transparent); }
      .day:first-child { border-top: 0; }
      .day .name { font-weight: 600; }
      .day .name small { display: block; font-weight: 400; color: var(--hl-text-muted); font-size: 11px; }
      .range { position: relative; height: 8px; border-radius: 4px; background: var(--hl-surface-2); }
      .range span { position: absolute; top: 0; bottom: 0; border-radius: 4px; background: linear-gradient(90deg, #6aa9de, #9cc58a, #f2b544, #e07a2e); }
      .tmin, .tmax { font-variant-numeric: tabular-nums; font-size: var(--hl-fs-sm); }
      .tmin { color: var(--hl-text-muted); text-align: right; }
      .rain { font-size: 12px; color: var(--hl-water-ink, var(--hl-water-500)); font-variant-numeric: tabular-nums; }
      .tags { display: flex; gap: 4px; flex-wrap: wrap; }
      .radar img { width: 100%; border-radius: 14px; display: block; background: var(--hl-surface-2); min-height: 200px; }
      .muted-note { font-size: var(--hl-fs-xs); color: var(--hl-text-muted); }
      @media (max-width: 600px) { .day { grid-template-columns: 70px 36px 54px 1fr; } .day .tags { display: none; } .now .temp { font-size: 48px; } }
    `,
  ];

  private get entityId(): string | null {
    return this.snapshot.settings.weather_entity ?? null;
  }

  protected willUpdate(changed: PropertyValues): void {
    if (!(changed.has("snapshot") || changed.has("hass")) || !this.hass) return;
    const entityId = this.entityId;
    if (entityId && entityId !== this.subscribedTo) this.subscribe(entityId);
    else if (!entityId && this.subscribedTo) {
      this.unsubscribe();
      this.subscribedTo = "";
    }
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.timer = window.setInterval(() => {
      this.radarTick = Date.now();
      this.radarFailed = false; // try the radar again after a failed load
    }, RADAR_REFRESH_MS);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearInterval(this.timer);
    this.unsubscribe();
    this.subscribedTo = "";
  }

  private unsubscribe(): void {
    this.generation++; // a late message from a replaced subscription is ignored
    this.daily = []; // no forecast of the previous entity until the new one arrives
    this.hourly = [];
    for (const u of this.unsubs) void u.then((off) => off()).catch(() => undefined);
    this.unsubs = [];
  }

  private subscribe(entityId: string): void {
    this.unsubscribe();
    this.subscribedTo = entityId;
    const generation = this.generation;
    for (const type of ["daily", "hourly"] as const) {
      const sub = this.hass.connection.subscribeMessage<{ forecast: Fc[] | null }>((msg) => {
        if (generation !== this.generation) return;
        if (type === "daily") this.daily = msg.forecast ?? [];
        else this.hourly = msg.forecast ?? [];
      }, { type: "weather/subscribe_forecast", entity_id: entityId, forecast_type: type });
      sub.catch(() => undefined); // not every weather entity offers both
      this.unsubs.push(sub);
    }
  }

  private cond(c: string | undefined): string {
    return this.t(`weather.cond.${c ?? "unknown"}`);
  }

  private fmtDay(iso: string, opts: Intl.DateTimeFormatOptions): string {
    // a daily forecast at UTC midnight means that calendar day, not the evening before west of UTC
    const m = /^(\d{4})-(\d{2})-(\d{2})T00:00:00(?:\.0+)?(?:Z|\+00:00)$/.exec(iso);
    const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12) : new Date(iso);
    return d.toLocaleDateString(localeOf(this.lang), opts);
  }

  private sky(c: string | undefined): string {
    if (c === "sunny" || c === "partlycloudy") return "var(--hl-grad-summer)";
    if (c === "rainy" || c === "pouring" || c === "lightning-rainy" || c === "lightning") return "var(--hl-grad-winter)";
    if (c === "snowy" || c === "snowy-rainy" || c === "hail" || c === "fog") return "var(--hl-grad-winter)";
    if (c === "clear-night") return "var(--hl-grad-winter)";
    return "var(--hl-grad-spring)";
  }

  // -- the garden view on the forecast ----------------------------------- //
  private hints(): { cls: string; title: string; text: string }[] {
    const out: { cls: string; title: string; text: string }[] = [];
    const days = this.daily.slice(0, 7);
    const lockout = this.snapshot.settings.irrigation?.frost_lockout_c ?? 2;
    const rainSkip = this.snapshot.settings.irrigation?.rain_skip_mm ?? 3;
    const frost = days.filter((d) => d.templow != null && d.templow <= lockout);
    if (frost.length) {
      const coldest = frost.reduce((a, b) => ((a.templow ?? 99) <= (b.templow ?? 99) ? a : b));
      out.push({ cls: "frost", title: this.t(frost.length === 1 ? "weather.hint.frost_title_one" : "weather.hint.frost_title", { n: frost.length }),
        text: this.t("weather.hint.frost", { day: this.fmtDay(coldest.datetime, { weekday: "long" }), t: Math.round(coldest.templow ?? 0) }) });
    }
    const heat = days.filter((d) => (d.temperature ?? 0) >= 28);
    if (heat.length) {
      const hottest = heat.reduce((a, b) => ((a.temperature ?? 0) >= (b.temperature ?? 0) ? a : b));
      out.push({ cls: "heat", title: this.t(heat.length === 1 ? "weather.hint.heat_title_one" : "weather.hint.heat_title", { n: heat.length }),
        text: this.t("weather.hint.heat", { day: this.fmtDay(hottest.datetime, { weekday: "long" }), t: Math.round(hottest.temperature ?? 0) }) });
    }
    const rain3 = days.slice(0, 3).reduce((a, d) => a + (d.precipitation ?? 0), 0);
    if (rain3 >= rainSkip) {
      out.push({ cls: "wet", title: this.t("weather.hint.rain_title", { mm: Math.round(rain3) }), text: this.t("weather.hint.rain") });
    } else if (days.length >= 5 && days.slice(0, 5).every((d) => (d.precipitation ?? 0) < 1)) {
      out.push({ cls: "dry", title: this.t("weather.hint.dry_title"), text: this.t("weather.hint.dry") });
    }
    const thirsty = Object.values(this.snapshot.analysis?.beds ?? {}).filter((b) => b.irrigation?.action === "water").length;
    if (thirsty) out.push({ cls: "dry", title: this.t(thirsty === 1 ? "weather.hint.beds_title_one" : "weather.hint.beds_title", { n: thirsty }), text: this.t("weather.hint.beds") });
    return out;
  }

  // -- next 24 hours: temperature line over rain bars --------------------- //
  private renderHours(): TemplateResult {
    const hrs = this.hourly.slice(0, 24);
    if (hrs.length < 2) return html`<p class="small muted">${this.t("weather.no_hourly")}</p>`;
    const W = 720, H = 190, L = 14, R = 14, T = 34, B = 34;
    const temps = hrs.map((h) => h.temperature ?? 0);
    const lo = Math.floor(Math.min(...temps)) - 1, hi = Math.ceil(Math.max(...temps)) + 1;
    const x = (i: number) => L + (i / (hrs.length - 1)) * (W - L - R);
    const y = (t: number) => T + (1 - (t - lo) / Math.max(1, hi - lo)) * (H - T - B - 26);
    const line = temps.map((t, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(t).toFixed(1)}`).join(" ");
    const area = `${line} L${x(hrs.length - 1)},${H - B} L${x(0)},${H - B} Z`;
    const maxRain = Math.max(2, ...hrs.map((h) => h.precipitation ?? 0));
    const bw = (W - L - R) / hrs.length * 0.6;
    return html`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label=${this.t("weather.hours")}>
      <defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2b544" stop-opacity="0.35"/><stop offset="1" stop-color="#f2b544" stop-opacity="0"/></linearGradient></defs>
      ${hrs.map((h, i) => (h.precipitation ?? 0) > 0 ? svg`<rect x=${x(i) - bw / 2} width=${bw} y=${H - B - ((h.precipitation ?? 0) / maxRain) * 40} height=${((h.precipitation ?? 0) / maxRain) * 40}
        rx="2" fill="#4a90c8" fill-opacity="0.55"><title>${h.precipitation} mm</title></rect>` : nothing)}
      <path d=${area} fill="url(#tg)"/>
      <path d=${line} fill="none" stroke="#e08a2e" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
      ${hrs.map((h, i) => (i % 3 === 0 ? svg`
        <circle cx=${x(i)} cy=${y(h.temperature ?? 0)} r="3" fill="#e08a2e"/>
        <text x=${x(i)} y=${y(h.temperature ?? 0) - 9} text-anchor="middle" font-size="12" font-weight="600" fill="currentColor">${Math.round(h.temperature ?? 0)}°</text>
        <text x=${x(i)} y=${H - 10} text-anchor="middle" font-size="11" fill="var(--hl-text-muted)">${new Date(h.datetime).toLocaleTimeString(localeOf(this.lang), { hour: "2-digit" })}</text>` : nothing))}
    </svg>`;
  }

  // -- coming days ---------------------------------------------------------- //
  private renderDays(): TemplateResult {
    const days = this.daily.slice(0, 10);
    if (!days.length) return html`<p class="small muted">${this.t("weather.no_daily")}</p>`;
    const lows = days.map((d) => d.templow ?? d.temperature ?? 0), highs = days.map((d) => d.temperature ?? 0);
    const lo = Math.min(...lows), hi = Math.max(...highs);
    const pct = (v: number) => ((v - lo) / Math.max(1, hi - lo)) * 100;
    const lockout = this.snapshot.settings.irrigation?.frost_lockout_c ?? 2;
    return html`<div class="days">${days.map((d, i) => {
      const low = d.templow ?? d.temperature ?? 0, high = d.temperature ?? 0;
      return html`<div class="day">
        <span class="name">${i === 0 ? this.t("common.today") : this.fmtDay(d.datetime, { weekday: "long" })}<small>${this.fmtDay(d.datetime, { day: "numeric", month: "short" })}</small></span>
        <span title=${this.cond(d.condition)}>${weatherGlyph(d.condition, 36)}</span>
        <span class="rain">${d.precipitation ? `${d.precipitation} mm` : ""}${d.precipitation_probability != null ? html`<br />${d.precipitation_probability}%` : nothing}</span>
        <span style="display:grid;grid-template-columns:32px 1fr 32px;gap:8px;align-items:center">
          <span class="tmin">${Math.round(low)}°</span>
          <span class="range"><span style="left:${pct(low)}%;right:${100 - pct(high)}%"></span></span>
          <span class="tmax">${Math.round(high)}°</span></span>
        <span class="tags">
          ${low <= lockout ? html`<span class="chip cold">${this.t("weather.tag.frost")}</span>` : nothing}
          ${high >= 28 ? html`<span class="chip warn">${this.t("weather.tag.heat")}</span>` : nothing}
        </span>
      </div>`;
    })}</div>`;
  }

  // -- rain radar ----------------------------------------------------------- //
  private radarSrc(): { src: string; source: string; link: string } | null {
    const camera = Object.keys(this.hass.states).find((id) => id.startsWith("camera.") && /buienradar|radar|regen|rain/i.test(id));
    if (camera) {
      const token = this.hass.states[camera].attributes.access_token as string | undefined;
      return { src: `/api/camera_proxy/${camera}?token=${token ?? ""}&t=${this.radarTick}`, source: camera, link: "" };
    }
    const country = (this.hass.config?.country ?? (this.lang === "nl" ? "NL" : "")).toUpperCase();
    if (country !== "NL" && country !== "BE") return null;
    return {
      src: `https://api.buienradar.nl/image/1.0/RadarMap${country}?w=500&h=512&t=${this.radarTick}`,
      source: "Buienradar",
      link: country === "BE" ? "https://www.buienradar.be" : "https://www.buienradar.nl",
    };
  }

  private renderRadar(): TemplateResult {
    const r = this.radarSrc();
    if (!r) return html`<p class="small muted">${this.t("weather.radar_none")}</p>`;
    return html`<div class="radar">
      ${this.radarFailed ? html`<p class="small muted">${this.t("weather.radar_failed")}</p>` : html`<img src=${r.src} alt=${this.t("weather.radar")} loading="lazy"
        @error=${() => (this.radarFailed = true)} @load=${() => (this.radarFailed = false)} />`}
      <p class="muted-note" style="margin-top:6px">${this.t("weather.radar_source", { source: r.source })}
        ${r.link ? html` · <a href=${r.link} target="_blank" rel="noopener">${r.link.replace("https://www.", "")}</a>` : nothing}</p>
    </div>`;
  }

  render(): TemplateResult {
    const id = this.entityId;
    if (!id || !this.hass.states[id]) {
      return html`<section class="card"><h2>${this.t("weather.title")}</h2><p class="small muted" style="margin-top:8px">${this.t("weather.no_entity")}</p></section>
        ${this.renderClimate()}`;
    }
    const st = this.hass.states[id];
    const a = st.attributes as Record<string, number | string | undefined>;
    const night = this.hourly[0]?.is_daytime === false || st.state === "clear-night";
    const hints = this.hints();
    return html`
      <section class="now" style=${`--sky:${this.sky(st.state)}`}>
        ${weatherGlyph(st.state, 92, night)}
        <div>
          <div class="eyebrow">${this.t("weather.now")} · ${String(a.friendly_name ?? id)}</div>
          <div class="temp">${a.temperature != null ? Math.round(Number(a.temperature)) : "–"}°</div>
          <div class="cond">${this.cond(st.state)}</div>
        </div>
        <div class="facts">
          ${a.humidity != null ? html`<span>${this.t("weather.humidity")}</span><b>${Math.round(Number(a.humidity))} %</b>` : nothing}
          ${a.wind_speed != null ? html`<span>${this.t("weather.wind")}</span><b>${Math.round(Number(a.wind_speed))} ${a.wind_speed_unit ?? "km/h"}</b>` : nothing}
          ${a.pressure != null ? html`<span>${this.t("weather.pressure")}</span><b>${Math.round(Number(a.pressure))} ${a.pressure_unit ?? "hPa"}</b>` : nothing}
          ${this.daily[0]?.precipitation != null ? html`<span>${this.t("weather.rain_today")}</span><b>${this.daily[0].precipitation} mm</b>` : nothing}
        </div>
      </section>
      <div class="grid" style="margin-top:var(--hl-s4)">
        <section class="card s7"><header><h2>${this.t("weather.hours")}</h2></header>
          <div class="hours">${this.renderHours()}</div></section>
        <section class="card s5"><header><h2>${this.t("weather.garden")}</h2></header>
          <div class="stack" style="gap:8px">${hints.length ? hints.map((h) => html`<div class="hint ${h.cls}"><span><b>${h.title}</b>${h.text}</span></div>`)
            : html`<p class="small muted">${this.t("weather.hint.none")}</p>`}</div></section>
        <section class="card s7"><header><h2>${this.t("weather.days")}</h2></header>${this.renderDays()}</section>
        <section class="card s5"><header><h2>${this.t("weather.radar")}</h2></header>${this.renderRadar()}</section>
      </div>
      ${this.renderClimate()}`;
  }

  private renderClimate(): TemplateResult | typeof nothing {
    if (!this.api || (this.viewer && !this.viewerClimate)) return nothing;
    return html`<hl-climate-history .api=${this.api} .t=${this.t} .lang=${this.lang} .revision=${this.snapshot.revision}
      .admin=${!this.viewer && (this.hass?.user?.is_admin ?? true)}></hl-climate-history>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-weather-view": WeatherView;
  }
}
