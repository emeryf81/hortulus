// Lovelace card: today's garden tasks (and overdue ones), tick them off from any dashboard.
//
//   type: custom:hortulus-tasks-card
//   title: Garden today        # optional
//   days: 0                    # 0 = today + overdue, 7 = the coming week
//   assignee: me               # optional: me | person.xyz | unassigned
//   max: 8                     # optional: maximum rows
//   garden: Volkstuin          # optional: which garden (title or entry id) when you have more than one
//   water: true                # optional: watering today, a running run, a stuck valve or leak (with Close)
//   climate: true              # optional: the last 7 days against last year (also Settings → Extras → climate card)
//   slogan: true               # optional: a changing garden saying (also Settings → Extras → slogans)
import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, Task } from "../types";
import { TASK_ICONS } from "../util/garden";
import { cardTasks } from "./card-tasks";

const DOMAIN = "garden_manager";

export interface CardConfig {
  type: string;
  title?: string;
  days?: number;
  assignee?: string;
  max?: number;
  water?: boolean;
  climate?: boolean;
  slogan?: boolean;
  garden?: string;
}

interface ClimateLite {
  periods: Record<string, { days?: number; tmean?: number; rain_mm?: number | null; sun_h?: number | null; frost_nights?: number }>;
  series: { d: string; lo: number | null; hi: number | null }[];
}

const STRINGS = {
  en: { week: "7 days: {t} °C", vs: "{d} °C vs last year", rain: "{mm} mm rain", sun: "{h} h sun", water: "Watered today: {l} L", running: "Watering {bed} until {time}", stuck: "{what} is still open", leak: "Water meter counts while every valve is closed: {l} L", close: "Close", title: "Garden today", none: "Nothing to do - enjoy the garden.", overdue: "overdue", more: "+{n} more", open: "Open Hortulus", min: "min", error: "Hortulus is not available", failed: "Could not complete the task - try again or open Hortulus." },
  fr: { week: "7 jours : {t} °C", vs: "{d} °C par rapport à l'an dernier", rain: "{mm} mm de pluie", sun: "{h} h de soleil", water: "Arrosé aujourd'hui : {l} L", running: "Arrosage de {bed} jusqu'à {time}", stuck: "{what} est toujours ouvert", leak: "Le compteur d'eau tourne alors que toutes les vannes sont fermées : {l} L", close: "Fermer", title: "Potager aujourd'hui", none: "Rien à faire - profitez du jardin.", overdue: "en retard", more: "+{n} de plus", open: "Ouvrir Hortulus", min: "min", error: "Hortulus n'est pas disponible", failed: "La tâche n'a pas pu être terminée - réessayez ou ouvrez Hortulus." },
  nl: { week: "7 dagen: {t} °C", vs: "{d} °C t.o.v. vorig jaar", rain: "{mm} mm regen", sun: "{h} u zon", water: "Vandaag water gegeven: {l} L", running: "{bed} krijgt water tot {time}", stuck: "{what} staat nog open", leak: "Watermeter telt terwijl alle kranen dicht zijn: {l} L", close: "Sluiten", title: "Tuin vandaag", none: "Niets te doen - geniet van de tuin.", overdue: "achterstallig", more: "+{n} meer", open: "Open Hortulus", min: "min", error: "Hortulus is niet beschikbaar", failed: "Taak afronden lukte niet - probeer opnieuw of open Hortulus." },
};

interface SnapshotLite {
  tasks: Task[];
  settings?: { climate_card?: boolean; slogans?: boolean };
  analysis?: { slogan?: string };
  beds?: { id: string; name: string }[];
  irrigation_log?: { bed_id: string; at: string; liters: number }[];
  irrigation_status?: {
    running: boolean; bed_id: string | null; ends_at: string | null;
    stuck?: { entity_id: string; what: string }[];
    leak?: { liters: number } | null;
  };
}

@customElement("hortulus-tasks-card")
export class HortulusTasksCard extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @state() private config: CardConfig = { type: "custom:hortulus-tasks-card" };
  @state() private tasks: Task[] | null = null;
  @state() private snap: SnapshotLite | null = null;
  @state() private error = false;
  @state() private failed = false;
  @state() private busy = new Set<string>();
  @state() private climate: ClimateLite | null = null;
  private climateAt = 0;
  private unsub?: Promise<() => Promise<void>>;

  static getStubConfig(): CardConfig {
    return { type: "custom:hortulus-tasks-card", days: 0 };
  }

  setConfig(config: CardConfig): void {
    if (!config) throw new Error("Invalid configuration");
    const gardenChanged = (config.garden ?? "") !== (this.config.garden ?? "");
    this.config = { days: 0, max: 8, ...config };
    if (gardenChanged) {
      // the climate line belongs to the garden: fetch it again for the new one
      this.climate = null;
      this.climateAt = 0;
    }
    if (gardenChanged && this.unsub) {
      // another garden: drop the old subscription and follow the new one
      void this.unsub.then((off) => off()).catch(() => undefined);
      this.unsub = undefined;
      this.snap = null;
      this.tasks = null;
      if (this.hass && this.isConnected) this.subscribe();
    }
  }

  getCardSize(): number {
    return 1 + Math.min(this.tasks?.length ?? 3, this.config.max ?? 8);
  }

  private get s() {
    const base = (this.hass?.locale?.language ?? this.hass?.language ?? "en").toLowerCase().slice(0, 2);
    const lang = base === "nl" || base === "fr" ? base : "en";
    return { ...STRINGS[lang], lang };
  }

  connectedCallback(): void {
    super.connectedCallback();
    if (this.hass && !this.unsub) this.subscribe();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    void this.unsub?.then((off) => off()).catch(() => undefined);
    this.unsub = undefined;
  }

  protected updated(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass && !this.unsub && this.isConnected) this.subscribe();
    if (changed.has("snap")) void this.loadClimate();
  }

  private subscribe(): void {
    this.unsub = this.hass!.connection.subscribeMessage<SnapshotLite>((snap) => {
      this.tasks = snap.tasks;
      this.snap = snap;
      this.error = false;
    }, { type: `${DOMAIN}/subscribe`, ...(this.config.garden ? { garden_id: this.config.garden } : {}) });
    this.unsub.catch(() => {
      this.error = true;
      this.unsub = undefined;
    });
  }

  private assigneeFilter(): string | null {
    const a = this.config.assignee;
    if (!a) return null;
    if (a === "unassigned") return "";
    if (a === "me") {
      const uid = this.hass?.user?.id;
      const me = Object.values(this.hass?.states ?? {}).find((s) => s.entity_id.startsWith("person.") && s.attributes.user_id === uid);
      return me?.entity_id ?? null;
    }
    return a;
  }

  private async complete(task: Task): Promise<void> {
    this.busy = new Set(this.busy).add(task.id);
    try {
      await this.hass!.connection.sendMessagePromise({ type: `${DOMAIN}/tasks/action`, task_id: task.id, action: "complete", ...(this.config.garden ? { garden_id: this.config.garden } : {}) });
      this.failed = false;
    } catch {
      this.failed = true;
    } finally {
      const next = new Set(this.busy);
      next.delete(task.id);
      this.busy = next;
    }
  }

  private async closeValve(entityId: string): Promise<void> {
    try {
      await this.hass!.connection.sendMessagePromise({ type: `${DOMAIN}/irrigation/close`, entity_id: entityId, ...(this.config.garden ? { garden_id: this.config.garden } : {}) });
    } catch {
      this.failed = true;
    }
  }

  private get showClimate(): boolean {
    return this.config.climate !== false && this.snap?.settings?.climate_card !== false;
  }

  /** The climate of the last days, fetched at most once an hour. */
  private async loadClimate(): Promise<void> {
    if (!this.hass || !this.showClimate || Date.now() - this.climateAt < 3_600_000) return;
    this.climateAt = Date.now();
    try {
      this.climate = await this.hass.connection.sendMessagePromise<ClimateLite>({
        type: `${DOMAIN}/climate/stats`, days: 14, ...(this.config.garden ? { garden_id: this.config.garden } : {}),
      });
    } catch {
      this.climate = null;
    }
  }

  /** The last 7 days against the same days last year, with a little temperature band. */
  private renderClimate(): TemplateResult | typeof nothing {
    const c = this.climate;
    const d7 = c?.periods?.d7;
    if (!this.showClimate || !c || !d7?.days || d7.tmean == null) return nothing;
    const s = this.s;
    const last = c.periods.d7_last_year;
    const diff = last?.days && last.tmean != null ? d7.tmean - last.tmean : null;
    const parts = [s.week.replace("{t}", d7.tmean.toFixed(1))];
    if (diff != null) parts.push(s.vs.replace("{d}", `${diff > 0 ? "+" : diff < 0 ? "−" : "±"}${Math.abs(diff).toFixed(1)}`));
    if (d7.rain_mm != null) parts.push(s.rain.replace("{mm}", String(Math.round(d7.rain_mm))));
    if (d7.sun_h != null) parts.push(s.sun.replace("{h}", String(Math.round(d7.sun_h))));
    const rows = (c.series ?? []).filter((r) => r.lo != null && r.hi != null).slice(-14);
    const lo = Math.min(...rows.map((r) => r.lo as number)), hi = Math.max(...rows.map((r) => r.hi as number));
    const span = Math.max(1, hi - lo);
    const y = (v: number) => 22 - ((v - lo) / span) * 20;
    const step = rows.length > 1 ? 100 / (rows.length - 1) : 0;
    const band = rows.length > 1
      ? html`<svg viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
          <polygon points=${[...rows.map((r, i) => `${i * step},${y(r.hi as number)}`), ...rows.map((r, i) => `${i * step},${y(r.lo as number)}`).reverse()].join(" ")}></polygon>
        </svg>`
      : nothing;
    return html`<div class="climate"><ha-icon icon="mdi:thermometer"></ha-icon><span>${parts.join(" · ")}</span>${band}</div>`;
  }

  /** Watering today, a run in progress, a valve left open, a leak. */
  private renderWater(today: string): TemplateResult | typeof nothing {
    if (this.config.water === false || !this.snap) return nothing;
    const s = this.s;
    const st = this.snap.irrigation_status;
    const liters = (this.snap.irrigation_log ?? [])
      .filter((e) => new Date(e.at).toLocaleDateString("sv-SE") === today) // the browser's calendar day, like `today`
      .reduce((a, e) => a + e.liters, 0);
    const bed = (id: string | null) => this.snap?.beds?.find((b) => b.id === id)?.name ?? "";
    const time = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString(({ nl: "nl-BE", fr: "fr-BE" } as Record<string, string>)[s.lang] ?? "en-GB", { hour: "2-digit", minute: "2-digit" }) : "");
    const rows: TemplateResult[] = [];
    if (st?.leak) rows.push(html`<div class="w bad"><ha-icon icon="mdi:water-alert"></ha-icon><span>${s.leak.replace("{l}", String(st.leak.liters))}</span></div>`);
    for (const v of st?.stuck ?? []) {
      rows.push(html`<div class="w bad"><ha-icon icon="mdi:valve-open"></ha-icon><span>${s.stuck.replace("{what}", v.what)}</span>
        ${this.hass?.user?.is_admin ? html`<button class="pill" @click=${() => this.closeValve(v.entity_id)}>${s.close}</button>` : nothing}</div>`);
    }
    if (st?.running) rows.push(html`<div class="w on"><ha-icon icon="mdi:sprinkler-variant"></ha-icon><span>${s.running.replace("{bed}", bed(st.bed_id)).replace("{time}", time(st.ends_at))}</span></div>`);
    else if (liters > 0) rows.push(html`<div class="w"><ha-icon icon="mdi:water-outline"></ha-icon><span>${s.water.replace("{l}", String(Math.round(liters)))}</span></div>`);
    return rows.length ? html`<div class="water">${rows}</div>` : nothing;
  }

  /** Today's garden saying (empty when switched off in the card or in Settings → Extras). */
  private get saying(): string {
    if (this.config.slogan === false || this.snap?.settings?.slogans === false) return "";
    return this.snap?.analysis?.slogan ?? "";
  }

  private open(): void {
    history.pushState(null, "", "/hortulus");
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  render(): TemplateResult {
    const s = this.s;
    const today = new Date().toLocaleDateString("sv-SE");
    const header = html`<div class="head"><h2>${this.config.title ?? s.title}</h2>
      <button class="link" @click=${() => this.open()} aria-label=${s.open}><ha-icon icon="mdi:sprout"></ha-icon></button></div>`;
    if (this.error) return html`<ha-card>${header}<p class="empty">${s.error}</p></ha-card>`;
    if (!this.tasks) return html`<ha-card>${header}<p class="empty">…</p></ha-card>`;
    const { shown, hidden } = cardTasks(this.tasks, today, this.config.days ?? 0, this.assigneeFilter(), this.config.max ?? 8);
    return html`<ha-card>
      ${header}
      ${this.renderClimate()}
      ${this.renderWater(today)}
      ${shown.length === 0 ? html`<p class="empty">${this.saying || s.none}</p>` : html`<ul>
        ${shown.map((t) => html`<li class=${t.due < today ? "late" : ""}>
          <button class="check" role="checkbox" aria-checked="false" aria-label=${t.title} ?disabled=${this.busy.has(t.id)} @click=${() => this.complete(t)}>
            <ha-icon icon=${this.busy.has(t.id) ? "mdi:progress-check" : "mdi:checkbox-blank-circle-outline"}></ha-icon></button>
          <ha-icon class="type" icon=${TASK_ICONS[t.type] ?? "mdi:sprout"}></ha-icon>
          <span class="text"><span class="title">${t.title}</span>
            <span class="meta">${t.due < today ? html`<b>${s.overdue}</b> · ` : t.due > today ? html`${new Date(`${t.due}T12:00`).toLocaleDateString(({ nl: "nl-BE", fr: "fr-BE" } as Record<string, string>)[s.lang] ?? "en-GB", { weekday: "short" })} · ` : nothing}${t.estimated_minutes} ${s.min}</span></span>
        </li>`)}
      </ul>`}
      ${this.failed ? html`<p class="failed" role="alert">${s.failed}</p>` : nothing}
      ${hidden ? html`<p class="more"><button class="link" @click=${() => this.open()}>${s.more.replace("{n}", String(hidden))}</button></p>` : nothing}
      ${shown.length && this.saying ? html`<p class="saying">🌱 ${this.saying}</p>` : nothing}
    </ha-card>`;
  }

  static styles = css`
    ha-card { padding: 12px 16px 8px; }
    .head { display: flex; align-items: center; justify-content: space-between; }
    h2 { margin: 0 0 4px; font-size: 1.15rem; font-weight: 500; }
    ul { list-style: none; margin: 0; padding: 0; }
    li { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid var(--divider-color, #e0e0e0); }
    li:first-child { border-top: 0; }
    .check, .link { background: none; border: 0; padding: 4px; cursor: pointer; color: var(--primary-color); border-radius: 50%; min-width: 36px; min-height: 36px; }
    .check:focus-visible, .link:focus-visible { outline: 2px solid var(--primary-color); }
    .type { color: var(--secondary-text-color); --mdc-icon-size: 20px; }
    .text { display: flex; flex-direction: column; min-width: 0; }
    .title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .meta { font-size: 0.8rem; color: var(--secondary-text-color); }
    li.late .meta b { color: var(--error-color, #c62828); font-weight: 600; }
    .empty { color: var(--secondary-text-color); margin: 8px 0; }
    .failed { color: var(--error-color, #c62828); font-size: 0.9rem; margin: 4px 0; }
    .more { margin: 4px 0 0; text-align: right; }
    .more .link { border-radius: 4px; font-size: 0.9rem; }
    .water { display: flex; flex-direction: column; gap: 6px; margin: 4px 0 8px; }
    .w { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 10px; font-size: 0.9rem;
      background: color-mix(in srgb, var(--info-color, #039be5) 10%, transparent); --mdc-icon-size: 20px; }
    .w.on { background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent); }
    .w.bad { background: color-mix(in srgb, var(--error-color, #c62828) 12%, transparent); color: var(--error-color, #c62828); }
    .w span { flex: 1; }
    .climate { display: flex; align-items: center; gap: 8px; margin: 2px 0 8px; font-size: 0.9rem; color: var(--secondary-text-color); --mdc-icon-size: 18px; }
    .climate span { flex: 1; }
    .climate svg { width: 70px; height: 22px; flex: none; }
    .climate polygon { fill: color-mix(in srgb, var(--warning-color, #ef6c00) 45%, transparent); stroke: none; }
    .saying { margin: 6px 0 2px; font-size: 0.85rem; font-style: italic; color: var(--secondary-text-color); }
    .pill { border: 1px solid currentColor; background: none; color: inherit; border-radius: 999px; padding: 2px 12px; cursor: pointer; font: inherit; }
  `;
}

declare global {
  interface Window { customCards?: { type: string; name: string; description: string; preview?: boolean }[] }
  interface HTMLElementTagNameMap { "hortulus-tasks-card": HortulusTasksCard }
}

window.customCards = window.customCards ?? [];
if (!window.customCards.some((c) => c.type === "hortulus-tasks-card")) {
  window.customCards.push({ type: "hortulus-tasks-card", name: "Hortulus – garden tasks", description: "Today's garden tasks with a tick-box, watering and valve alerts.", preview: true });
}
