import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { glyphFor, glyphIcon } from "../planner/plant-glyphs";
import { shared } from "../styles/tokens";
import type { FamilyInfo, Plant, RecordsOverview, Snapshot, Task } from "../types";
import { TASK_COLORS, TASK_ICONS, addDays, daysBetween, familyColor, formatDate, parseDate, plantName, sortTasks, toIso, localeOf } from "../util/garden";
import { renderTaskRow, taskPlantResolver, taskRowStyles, type TaskCtx } from "../components/task-ui";

type Mode = "month" | "week" | "list" | "timeline" | "year";

@customElement("hl-calendar-view")
export class CalendarView extends LitElement {
  @property({ attribute: false }) snapshot!: Snapshot;
  @property({ attribute: false }) t!: Translate;
  @property() lang = "en";
  @property({ attribute: false }) plants: Map<string, Plant> = new Map();
  @property({ attribute: false }) families: Record<string, FamilyInfo> = {};
  @state() private mode: Mode = "month";
  @state() private cursor = "";
  @state() private showDone = false;
  @state() private bedFilter = "";
  @property({ attribute: false }) api?: GardenApi;
  @state() private year: RecordsOverview["year"] = null;

  private async loadYear(): Promise<void> {
    try {
      this.year = (await this.api?.records())?.year ?? null;
    } catch {
      this.year = null;
    }
  }

  private renderYear(): TemplateResult {
    const y = this.year;
    if (!y) return html`<p class="empty">${this.t("common.loading")}</p>`;
    const months = Array.from({ length: 12 }, (_, i) => new Date(2026, i, 1).toLocaleDateString(localeOf(this.lang), { month: "short" }));
    const now = new Date().getMonth();
    const order = ["harvest", "plant", "sow", "sow_indoor", "grow"];
    const bedName = this.snapshot.beds.find((b) => b.id === this.bedFilter)?.name ?? "";
    const rows = y.rows
      .filter((r) => !this.bedFilter || r.beds.includes(bedName))
      .sort((a, b) => plantName(this.plants.get(a.plant_id), this.lang).localeCompare(plantName(this.plants.get(b.plant_id), this.lang), this.lang));
    return html`<div class="card year-wrap"><table class="year">
      <thead><tr><th></th>${months.map((m, i) => html`<th class=${i === now ? "now" : ""}>${m}</th>`)}</tr></thead>
      <tbody>
        ${rows.map((r) => {
          const plant = this.plants.get(r.plant_id);
          return html`<tr><th scope="row"><button class="crop linklike" title=${this.t("lib.open_plant")} @click=${() => this.emit("open-plant", r.plant_id)}>${plant ? glyphIcon(glyphFor(plant), plant.color || familyColor(this.families, plant.family), 20) : nothing}
            ${plantName(plant, this.lang)}</button><span class="xs muted">${r.beds.join(", ")}</span></th>
            ${months.map((_, i) => {
              const acts = r.months[String(i + 1)] ?? [];
              const act = order.find((a) => acts.includes(a));
              return html`<td class=${`${act ?? ""} ${i === now ? "now" : ""}`} title=${acts.map((a) => this.t(`cal.act.${a}`)).join(", ")}>
                ${act && act !== "grow" ? this.t(`cal.act_short.${act}`) : ""}</td>`;
            })}</tr>`;
        })}
        <tr class="tasks-row"><th scope="row">${this.t("cal.tasks_per_month")}</th>${y.tasks.map((n, i) => html`<td class=${i === now ? "now" : ""}>${n || ""}
          ${y.minutes[i] ? html`<span class="xs muted"> · ${this.t("cal.hours", { n: Math.max(1, Math.round(y.minutes[i] / 60)) })}</span>` : nothing}</td>`)}</tr>
      </tbody></table>
      <div class="legend year-legend">${order.map((a) => html`<span><i class=${`sw ${a}`}></i> ${this.t(`cal.act.${a}`)}</span>`)}</div>
    </div>`;
  }

  static styles = [
    shared,
    taskRowStyles,
    css`
      .bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--hl-s2); margin-bottom: var(--hl-s3); }
      .bar h2 { min-width: 200px; text-transform: capitalize; }
      .year-wrap { overflow-x: auto; padding: var(--hl-s3); }
      table.year { border-collapse: separate; border-spacing: 2px; width: 100%; min-width: 720px; font-size: var(--hl-fs-sm); }
      table.year th { text-align: left; font-weight: 600; padding: 4px 6px; white-space: nowrap; }
      table.year thead th { text-align: center; color: var(--hl-text-muted); text-transform: capitalize; }
      table.year th[scope="row"] { display: flex; flex-direction: column; gap: 0; }
      table.year .crop { display: inline-flex; gap: 6px; align-items: center; }
      .linklike { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: pointer; text-align: left; }
      .linklike:hover { text-decoration: underline; }
      table.year td { height: 30px; border-radius: 6px; background: var(--hl-surface-2); text-align: center; font-size: 11px; font-weight: 700; color: #fff; }
      table.year td.now, table.year th.now { outline: 2px solid var(--hl-focus); outline-offset: -2px; }
      table.year td.grow, .sw.grow { background: color-mix(in srgb, var(--hl-leaf-500) 25%, var(--hl-surface-2)); color: var(--hl-text); }
      table.year td.sow_indoor, .sw.sow_indoor { background: var(--hl-leaf-300); color: var(--hl-text); }
      table.year td.sow, .sw.sow { background: var(--hl-leaf-500); }
      table.year td.plant, .sw.plant { background: var(--hl-leaf-700); }
      table.year td.harvest, .sw.harvest { background: var(--hl-sun-500); color: #3a2a00; }
      table.year .tasks-row td { background: transparent; color: var(--hl-text); font-weight: 600; }
      .year-legend { display: flex; flex-wrap: wrap; gap: var(--hl-s3); margin-top: var(--hl-s2); font-size: var(--hl-fs-sm); }
      .year-legend .sw { display: inline-block; width: 14px; height: 10px; border-radius: 3px; vertical-align: middle; }
      .month { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 1px; background: var(--hl-border); border: 1px solid var(--hl-border); border-radius: var(--hl-r-lg); overflow: hidden; }
      .dow { background: var(--hl-surface-2); padding: 6px; font-size: var(--hl-fs-xs); font-weight: 600; color: var(--hl-text-muted); text-transform: uppercase; text-align: center; }
      .cell { background: var(--hl-surface); min-height: 108px; padding: 4px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
      .cell.other { background: var(--hl-surface-2); }
      .cell.other .num { font-weight: 400; }
      .cell.today { box-shadow: inset 0 0 0 2px var(--hl-primary); }
      .num { font-size: var(--hl-fs-xs); font-weight: 600; color: var(--hl-text-muted); padding: 2px 4px; }
      .ev { display: flex; align-items: center; gap: 4px; border: 0; border-left: 3px solid; background: var(--hl-surface-2); border-radius: 4px;
        padding: 2px 4px; font-size: 11px; text-align: left; cursor: pointer; color: var(--hl-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; --mdc-icon-size: 12px; }
      .ev:hover { background: var(--hl-surface-3); }
      .ev.done { opacity: 0.55; text-decoration: line-through; }
      .ev.overdue { background: var(--hl-tomato-100); }
      .more { font-size: 11px; color: var(--hl-text-muted); border: 0; background: transparent; cursor: pointer; text-align: left; padding: 0 4px; }
      .week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: var(--hl-s2); }
      .week .col { background: var(--hl-surface); border: 1px solid var(--hl-border); border-radius: var(--hl-r-md); padding: var(--hl-s2); min-height: 260px; display: flex; flex-direction: column; gap: 4px; }
      .week .col.today { border-color: var(--hl-primary); }
      .week .ev { white-space: normal; }
      @media (max-width: 900px) {
        .week { grid-template-columns: 1fr; }
        .cell { min-height: 64px; }
        .ev span { display: none; }
      }
      .group h3 { margin: var(--hl-s3) 0 var(--hl-s1); font-size: var(--hl-fs-md); }
      .gantt { background: var(--hl-surface); border: 1px solid var(--hl-border); border-radius: var(--hl-r-lg); overflow-x: auto; }
      .gantt-inner { min-width: 860px; position: relative; padding-bottom: var(--hl-s2); }
      .g-row { display: grid; grid-template-columns: 220px 1fr; align-items: center; min-height: 26px; border-bottom: 1px solid var(--hl-border); }
      .g-row.head { position: sticky; top: 0; background: var(--hl-surface-2); z-index: 1; font-size: var(--hl-fs-xs); color: var(--hl-text-muted); font-weight: 600; }
      .g-row.bed { background: var(--hl-surface-2); font-weight: 700; font-size: var(--hl-fs-sm); }
      .g-label { padding: 2px var(--hl-s2); font-size: var(--hl-fs-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; gap: 6px; align-items: center; }
      .g-track { position: relative; height: 26px; }
      .g-bar { position: absolute; top: 6px; height: 14px; border-radius: 4px; }
      .g-bar.sow { top: 10px; height: 6px; opacity: 0.6; }
      .g-mark { position: absolute; top: 4px; width: 10px; height: 10px; transform: translateX(-5px) rotate(45deg); background: var(--hl-text); border: 2px solid var(--hl-surface); }
      .g-month { position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--hl-border); padding-left: 4px; }
      .g-line { position: absolute; top: 0; bottom: 0; width: 0; border-left: 2px dashed var(--hl-frost-500); pointer-events: none; }
      .g-line.today { border-left: 2px solid var(--hl-tomato-500); }
      .g-task { position: absolute; top: 3px; transform: translateX(-10px); border: 0; background: transparent; cursor: pointer; --mdc-icon-size: 18px; padding: 0; }
      .g-legend { display: flex; gap: var(--hl-s3); flex-wrap: wrap; font-size: var(--hl-fs-xs); color: var(--hl-text-muted); padding: var(--hl-s2); }
      .g-legend span { display: inline-flex; gap: 4px; align-items: center; }
      .g-legend i { display: inline-block; width: 18px; height: 8px; border-radius: 3px; }
    `,
  ];

  protected willUpdate(): void {
    // Start on the garden's "today" (server time zone), not the browser's.
    if (!this.cursor) this.cursor = this.today;
  }

  private emit(name: string, detail: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  private get today(): string {
    return this.snapshot.analysis?.today ?? toIso(new Date());
  }

  private get tasks(): Task[] {
    return this.snapshot.tasks.filter(
      (t) => (this.showDone || t.status === "open") && t.status !== "skipped" && (!this.bedFilter || t.bed_id === this.bedFilter),
    );
  }

  private byDay(): Map<string, Task[]> {
    const map = new Map<string, Task[]>();
    for (const task of sortTasks(this.tasks)) {
      // Overdue open tasks are shown on today so nothing gets lost in the past.
      const day = task.status === "open" && task.due < this.today ? this.today : task.due;
      map.set(day, [...(map.get(day) ?? []), task]);
    }
    return map;
  }

  private move(dir: -1 | 1): void {
    const d = parseDate(this.cursor);
    if (this.mode === "timeline") d.setFullYear(d.getFullYear() + dir);
    else if (this.mode === "month") d.setMonth(d.getMonth() + dir, 1);
    else d.setDate(d.getDate() + dir * (this.mode === "week" ? 7 : 30));
    this.cursor = toIso(d);
  }

  private weekStart(iso: string): string {
    const d = parseDate(iso);
    const offset = (d.getDay() + 6) % 7; // Monday first (ISO 8601)
    return addDays(iso, -offset);
  }

  private renderEvent(task: Task): TemplateResult {
    const overdue = task.status === "open" && task.due < this.today;
    return html`<button class="ev ${task.status !== "open" ? "done" : ""} ${overdue ? "overdue" : ""}" style=${`border-left-color:${TASK_COLORS[task.type] ?? "var(--hl-soil-500)"}`}
      title=${task.title} @click=${() => this.emit("open-task", task)}>
      <ha-icon icon=${TASK_ICONS[task.type]}></ha-icon><span>${task.title}</span></button>`;
  }

  private renderMonth(): TemplateResult {
    const first = parseDate(this.cursor);
    first.setDate(1);
    const start = this.weekStart(toIso(first));
    const month = first.getMonth();
    const days = Array.from({ length: 42 }, (_, i) => addDays(start, i));
    const map = this.byDay();
    const dows = Array.from({ length: 7 }, (_, i) => formatDate(addDays(start, i), this.lang, { weekday: "short" }));
    return html`<div class="month" role="list" aria-label=${formatDate(toIso(first), this.lang, { month: "long", year: "numeric" })}>
      ${dows.map((d) => html`<div class="dow" aria-hidden="true">${d}</div>`)}
      ${days.map((day) => {
        const list = map.get(day) ?? [];
        return html`<div class="cell ${parseDate(day).getMonth() !== month ? "other" : ""} ${day === this.today ? "today" : ""}" role="listitem" aria-label=${formatDate(day, this.lang, { day: "numeric", month: "long" })}>
          <span class="num">${parseDate(day).getDate()}</span>
          ${list.slice(0, 4).map((task) => this.renderEvent(task))}
          ${list.length > 4 ? html`<button class="more" @click=${() => { this.cursor = day; this.mode = "week"; }}>+${list.length - 4}</button>` : nothing}
        </div>`;
      })}
    </div>`;
  }

  private renderWeek(): TemplateResult {
    const start = this.weekStart(this.cursor);
    const map = this.byDay();
    return html`<div class="week">
      ${Array.from({ length: 7 }, (_, i) => addDays(start, i)).map((day) => html`
        <div class="col ${day === this.today ? "today" : ""}">
          <b class="small">${formatDate(day, this.lang, { weekday: "long", day: "numeric", month: "short" })}</b>
          ${(map.get(day) ?? []).map((task) => this.renderEvent(task))}
        </div>`)}
    </div>`;
  }

  private renderList(): TemplateResult {
    const ctx: TaskCtx = {
      t: this.t, lang: this.lang, today: this.today,
      onOpen: (task) => this.emit("open-task", task),
      onComplete: (task) => this.emit("complete-task", task),
      onPostpone: (task, days) => this.emit("postpone-task", { task, days }),
      plantOf: taskPlantResolver(this.snapshot, this.plants, this.families),
    };
    const map = this.byDay();
    const days = [...map.keys()].filter((d) => d >= this.cursor).sort().slice(0, 30);
    if (!days.length) return html`<p class="empty">–</p>`;
    return html`${days.map((day) => html`<div class="group">
      <h3>${day === this.today ? this.t("common.today") : formatDate(day, this.lang, { weekday: "long", day: "numeric", month: "long" })}</h3>
      <ul class="tasks">${map.get(day)!.map((task) => renderTaskRow(task, ctx))}</ul></div>`)}`;
  }

  /** Season Gantt: every planting per bed, plus the seasonal garden work. */
  private renderTimeline(): TemplateResult {
    const a = this.snapshot.analysis;
    if (!a) return html`<p class="empty">–</p>`;
    const season = Number(this.cursor.slice(0, 4)) || a.season;
    const south = this.snapshot.settings.region.hemisphere === "south";
    const start = south ? `${season}-07-01` : `${season}-01-01`;
    const end = south ? `${season + 1}-06-30` : `${season}-12-31`;
    const total = daysBetween(start, end) + 1;
    const x = (iso: string | null | undefined) => (iso ? Math.max(0, Math.min(100, (daysBetween(start, iso) / total) * 100)) : null);
    const bar = (from: string | null | undefined, to: string | null | undefined, cls: string, style: string, title: string) => {
      const x1 = x(from);
      const x2 = x(to);
      if (x1 === null || x2 === null || x2 <= 0 || x1 >= 100) return nothing;
      return html`<div class="g-bar ${cls}" title=${title} style=${`left:${x1}%;width:${Math.max(x2 - x1, 0.6)}%;${style}`}></div>`;
    };
    const months = Array.from({ length: 12 }, (_, i) => {
      const d = parseDate(start);
      d.setMonth(d.getMonth() + i, 1);
      return toIso(d);
    });
    const plantings = this.snapshot.plantings.filter((p) => p.season === season && a.timelines[p.id] && (!this.bedFilter || p.bed_id === this.bedFilter));
    const beds = this.snapshot.beds.filter((b) => plantings.some((p) => p.bed_id === b.id));
    const garden = this.snapshot.tasks.filter((t) => t.key?.startsWith("m:") && t.due >= start && t.due <= end && (this.showDone || t.status === "open"));
    const lines = html`
      ${!a.anchors.frost_free && x(a.anchors.last_frost) !== null ? html`<div class="g-line" style=${`left:${x(a.anchors.last_frost)}%`} title=${this.t("cal.last_frost")}></div>` : nothing}
      ${!a.anchors.frost_free && x(a.anchors.first_frost) !== null ? html`<div class="g-line" style=${`left:${x(a.anchors.first_frost)}%`} title=${this.t("cal.first_frost")}></div>` : nothing}
      ${this.today >= start && this.today <= end ? html`<div class="g-line today" style=${`left:${x(this.today)}%`} title=${this.t("common.today")}></div>` : nothing}`;
    return html`<div class="gantt"><div class="gantt-inner" role="table" aria-label=${this.t("cal.timeline")}>
      <div class="g-row head" role="row"><div class="g-label">${this.t("common.season", { year: season })}</div>
        <div class="g-track">${months.map((m) => html`<span class="g-month" style=${`left:${x(m)}%`}>${formatDate(m, this.lang, { month: "short" })}</span>`)}</div></div>
      ${garden.length ? html`<div class="g-row" role="row"><div class="g-label"><ha-icon icon="mdi:calendar-sync-outline"></ha-icon>${this.t("cal.garden_work")}</div>
        <div class="g-track">${lines}${garden.map((t) => html`<button class="g-task" style=${`left:${x(t.due)}%;color:${TASK_COLORS[t.type] ?? "var(--hl-soil-500)"}`}
          title=${`${formatDate(t.due, this.lang)} · ${t.title}`} @click=${() => this.emit("open-task", t)}><ha-icon icon=${TASK_ICONS[t.type]}></ha-icon></button>`)}</div></div>` : nothing}
      ${beds.map((bed) => html`
        <div class="g-row bed" role="row"><div class="g-label">${bed.name}</div><div class="g-track">${lines}</div></div>
        ${plantings.filter((p) => p.bed_id === bed.id).sort((p, q) => (a.timelines[p.id].in_ground < a.timelines[q.id].in_ground ? -1 : 1)).map((p) => {
          const tl = a.timelines[p.id];
          const plant = this.plants.get(p.plant_id);
          const color = familyColor(this.families, plant?.family);
          const name = plantName(plant, this.lang);
          const ph = a.phenology?.[p.id];
          return html`<div class="g-row" role="row">
            <div class="g-label"><span class="family-dot" style=${`background:${color};width:10px;height:10px`}></span>${name}
              ${ph && ph.stage !== "not_planted" && ph.stage !== "finished" ? html`<span class="xs muted">· ${this.t(`stage.${ph.stage}`)}</span>` : nothing}</div>
            <div class="g-track">${lines}
              ${tl.sow_date && tl.sow_date < tl.in_ground ? bar(tl.sow_date, tl.in_ground, "sow", `background:${color}`, `${this.t("lib.indoor_sow")}: ${formatDate(tl.sow_date, this.lang)}`) : nothing}
              ${bar(tl.in_ground, tl.harvest_start, "", `background:color-mix(in srgb, ${color} 35%, transparent);border:1px solid ${color}`, `${formatDate(tl.in_ground, this.lang)} – ${formatDate(tl.harvest_start, this.lang)}`)}
              ${bar(tl.harvest_start, tl.harvest_end, "", `background:${color}`, `${this.t("lib.harvest")}: ${formatDate(tl.harvest_start, this.lang)} – ${formatDate(tl.harvest_end, this.lang)}`)}
              ${ph?.harvest_estimate && x(ph.harvest_estimate) !== null ? html`<span class="g-mark" style=${`left:${x(ph.harvest_estimate)}%`}
                title=${this.t("cal.harvest_estimate", { date: formatDate(ph.harvest_estimate, this.lang) })}></span>` : nothing}
            </div></div>`;
        })}`)}
      ${!beds.length ? html`<p class="empty">${this.t("cal.no_plantings")}</p>` : nothing}
      <div class="g-legend">
        <span><i style="background:var(--hl-leaf-300);height:4px"></i>${this.t("lib.indoor_sow")}</span>
        <span><i style="background:color-mix(in srgb, var(--hl-leaf-500) 35%, transparent);border:1px solid var(--hl-leaf-500)"></i>${this.t("cal.growing")}</span>
        <span><i style="background:var(--hl-leaf-600)"></i>${this.t("lib.harvest")}</span>
        <span><i style="width:10px;height:10px;transform:rotate(45deg);background:var(--hl-text)"></i>${this.t("cal.harvest_estimate_short")}</span>
        <span><i style="border-left:2px dashed var(--hl-frost-500);width:2px;height:12px;border-radius:0"></i>${this.t("cal.frost_dates")}</span>
      </div>
    </div></div>`;
  }

  render(): TemplateResult {
    const title =
      this.mode === "timeline" || this.mode === "year"
        ? this.t("common.season", { year: this.mode === "year" ? (this.year?.season ?? Number(this.cursor.slice(0, 4))) : Number(this.cursor.slice(0, 4)) })
        : this.mode === "month"
        ? formatDate(this.cursor, this.lang, { month: "long", year: "numeric" })
        : `${formatDate(this.weekStart(this.cursor), this.lang)} – ${formatDate(addDays(this.weekStart(this.cursor), 6), this.lang)}`;
    return html`
      <div class="bar">
        <button class="icon-btn" aria-label=${this.t("cal.prev")} @click=${() => this.move(-1)}><ha-icon icon="mdi:chevron-left"></ha-icon></button>
        <button class="btn small" @click=${() => (this.cursor = this.today)}>${this.t("common.today")}</button>
        <button class="icon-btn" aria-label=${this.t("cal.next")} @click=${() => this.move(1)}><ha-icon icon="mdi:chevron-right"></ha-icon></button>
        <h2 aria-live="polite">${title}</h2>
        <span class="spacer"></span>
        <div class="row" role="group">
          ${(["month", "week", "list", "timeline", "year"] as Mode[]).map((m) => html`<button class="chip" aria-pressed=${String(this.mode === m)}
            @click=${() => { this.mode = m; if (m === "year") void this.loadYear(); }}>${this.t(`cal.${m}`)}</button>`)}
        </div>
        <label class="row small"><span class="visually-hidden">${this.t("task.bed")}</span>
          <select style="width:auto" @change=${(e: Event) => (this.bedFilter = (e.target as HTMLSelectElement).value)}>
            ${[{ id: "", name: this.t("cal.all_beds") }, ...this.snapshot.beds].map((b) => html`<option value=${b.id} ?selected=${b.id === this.bedFilter}>${b.name}</option>`)}
          </select>
        </label>
        <label class="row small"><input type="checkbox" .checked=${this.showDone} @change=${(e: Event) => (this.showDone = (e.target as HTMLInputElement).checked)} />${this.t("cal.show_done")}</label>
        <button class="btn primary small" @click=${() => this.emit("new-task", null)}><ha-icon icon="mdi:plus"></ha-icon>${this.t("cal.add_task")}</button>
      </div>
      ${this.mode === "month" ? this.renderMonth() : this.mode === "week" ? this.renderWeek() : this.mode === "timeline" ? this.renderTimeline()
        : this.mode === "year" ? this.renderYear() : this.renderList()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-calendar-view": CalendarView;
  }
}
