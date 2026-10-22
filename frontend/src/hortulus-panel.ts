/**
 * Hortulus panel - entry point registered by the integration as
 * <hortulus-panel> (see custom_components/garden_manager/panel.py).
 *
 * Why Lit: Home Assistant's own frontend is built with Lit web components,
 * so the panel shares the runtime model (the `hass` property is pushed on every
 * state change), theming via CSS custom properties, `ha-icon`, and a small
 * bundle (~55 kB gzipped incl. Lit) without a second framework runtime.
 */
import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { keyed } from "lit/directives/keyed.js";
import { customElement, property, state } from "lit/decorators.js";
import { GardenApi } from "./api";
import { emblem } from "./brand";
import { makeTranslator, normalizeLang, type Translate } from "./i18n";
import { shared, themes, tokens } from "./styles/tokens";
import type { FamilyInfo, HomeAssistant, Plant, Snapshot, Task } from "./types";
import "./views/weather-view";
import { gicon } from "./components/garden-icons";
import "./views/wall-view";
import { celebrate } from "./util/celebrate";
import { appearanceChoice, setAppearanceChoice, setThemeChoice, themeAttribute, themeChoice, THEMES, APPEARANCES, type Appearance, type ThemeChoice } from "./util/theme";
import { paletteFor } from "./styles/palettes";
import "./views/dashboard-view";
import "./views/planner-view";
import "./views/library-view";
import "./views/calendar-view";
import "./views/settings-view";
import "./views/handbook-view";
import "./views/print-view";
import "./views/advice-view";
import "./views/journal-view";
import "./views/cooking-view";
import "./views/garden-viewer";
import "./views/analysis-view";
import "./views/crops-view";
import { setPersons } from "./util/people";
import { setSupplies } from "./util/tools";
import "./components/task-ui";
import { setGlossary } from "./components/info";
import "./components/modal";
import "./components/plant-detail";
import { familyColor, plantName, familyName } from "./util/garden";

type Tab = "wall" | "view" | "dashboard" | "layout" | "planner" | "crops" | "library" | "calendar" | "weather" | "journal" | "cooking" | "advice" | "analysis" | "handbook" | "print" | "settings";
const TABS: { id: Tab; icon: string }[] = [
  { id: "view", icon: "garden" }, // a visitor's look at the plan (website), never in Home Assistant's menu
  { id: "dashboard", icon: "home" },
  { id: "planner", icon: "planner" },
  { id: "layout", icon: "layout" },
  { id: "crops", icon: "crops" },
  { id: "calendar", icon: "calendar" },
  { id: "weather", icon: "weather" },
  { id: "journal", icon: "journal" },
  { id: "cooking", icon: "cooking" },
  { id: "library", icon: "library" },
  { id: "advice", icon: "advice" },
  { id: "handbook", icon: "handbook" },
  { id: "analysis", icon: "analysis" },
  { id: "print", icon: "print" },
  { id: "settings", icon: "settings" },
  { id: "wall", icon: "wall" }, // the wall screen: no menu, reached from Today
];
/** The menu: seven places, the related tabs of a place in a row underneath. */
type Group = "view" | "today" | "garden" | "calendar" | "weather" | "journal" | "kitchen" | "knowledge" | "manage";
const GROUPS: { id: Group; icon: string; tabs: Tab[] }[] = [
  { id: "view", icon: "garden", tabs: ["view"] },
  { id: "today", icon: "home", tabs: ["dashboard"] },
  { id: "garden", icon: "garden", tabs: ["planner", "layout", "crops"] },
  { id: "calendar", icon: "calendar", tabs: ["calendar"] },
  { id: "weather", icon: "weather", tabs: ["weather"] },
  { id: "journal", icon: "journal", tabs: ["journal"] },
  { id: "kitchen", icon: "cooking", tabs: ["cooking"] },
  { id: "knowledge", icon: "knowledge", tabs: ["library", "advice", "handbook"] },
  { id: "manage", icon: "manage", tabs: ["analysis", "print", "settings"] },
];
const groupOf = (tab: Tab): (typeof GROUPS)[number] => GROUPS.find((g) => g.tabs.includes(tab)) ?? GROUPS[0];

@customElement("hortulus-panel")
export class HortulusPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean, reflect: true }) narrow = false;
  @property({ attribute: false }) route?: { prefix: string; path: string };
  @property({ attribute: false }) panel?: unknown;

  @state() private snapshot: Snapshot | null = null;
  @state() private lastInGroup: Partial<Record<Group, Tab>> = {};
  @state() private plants: Plant[] = [];
  @state() private families: Record<string, FamilyInfo> = {};
  @state() private tab: Tab = "dashboard";

  /**
   * The tabs this panel may show: `panel.config.tabs` (the website's read-only view of a
   * garden someone shares) or all of them (Home Assistant).
   */
  /** The website passes extra settings here (`tabs`, `viewer`, `web`); Home Assistant none. */
  private get panelConfig(): { tabs?: string[]; viewer?: unknown; web?: boolean } {
    return (this.panel as { config?: { tabs?: string[]; viewer?: unknown; web?: boolean } } | undefined)?.config ?? {};
  }

  private get allowedTabs(): Set<Tab> | null {
    const tabs = (this.panel as { config?: { tabs?: string[] } } | undefined)?.config?.tabs;
    // no list: everything (Home Assistant); a list, even an empty one, restricts
    return Array.isArray(tabs) ? new Set(tabs as Tab[]) : null;
  }

  /** Where a tab that may not be shown leads: Today, else the first allowed tab. */
  private get fallbackTab(): Tab {
    if (this.tabAllowed("dashboard")) return "dashboard";
    return TABS.find((t) => this.tabAllowed(t.id))?.id ?? "dashboard";
  }

  private tabAllowed(tab: Tab): boolean {
    const allowed = this.allowedTabs;
    return allowed ? allowed.has(tab) : tab !== "view";
  }

  /** The menu as this panel shows it: places without an allowed tab are left out. */
  private get groups(): { id: Group; icon: string; tabs: Tab[] }[] {
    return GROUPS.map((g) => ({ ...g, tabs: g.tabs.filter((t) => this.tabAllowed(t)) })).filter((g) => g.tabs.length);
  }

  private groupOf(tab: Tab): { id: Group; icon: string; tabs: Tab[] } {
    return this.groups.find((g) => g.tabs.includes(tab)) ?? this.groups[0] ?? groupOf(tab);
  }
  @state() private toastMsg = "";
  @state() private openTask: Task | null = null;
  @state() private creatingTask = false;
  @state() private error = "";
  @state() private chapter = "";
  @state() private plannerSeason: number | null = null;
  @state() private transitionRequest = 0;
  @state() private popupPlant: Plant | null = null;
  @state() private plannerFocus: { id: string; season: number; n: number } | null = null;
  @state() private cropsFocus: { id: string; season: number; n: number } | null = null;

  private api?: GardenApi;
  private unsubscribe?: () => Promise<void>;
  private toastTimer?: number;
  private t: Translate = makeTranslator("en");
  private uiLang = "en";

  static styles = [
    tokens,
    themes,
    shared,
    css`
      :host { display: block; min-height: 100vh; background:
        radial-gradient(1200px 520px at 12% -8%, color-mix(in srgb, var(--hl-leaf-100) 70%, transparent), transparent 70%),
        radial-gradient(900px 420px at 100% 0%, color-mix(in srgb, var(--hl-sun-100) 55%, transparent), transparent 70%),
        var(--hl-bg); background-attachment: fixed; }
      .appbar { position: sticky; top: 0; z-index: 4; display: flex; align-items: center; gap: var(--hl-s3);
        padding: 0 var(--hl-s5); height: 60px; background: color-mix(in srgb, var(--hl-surface) 78%, transparent);
        backdrop-filter: saturate(1.6) blur(14px); -webkit-backdrop-filter: saturate(1.6) blur(14px);
        border-bottom: 1px solid color-mix(in srgb, var(--hl-border) 70%, transparent);
        box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset, 0 6px 20px -12px rgba(46, 33, 24, 0.25); }
      .brand { display: flex; align-items: center; gap: 10px; flex: none; }
      .brand > span { font-family: var(--hl-font-serif); font-weight: 700; font-size: 21px; letter-spacing: -0.01em; }
      .brand small { font-weight: 400; color: var(--hl-text-muted); font-size: var(--hl-fs-xs); line-height: 1.25; max-width: 150px;
        padding-left: 10px; border-left: 1px solid var(--hl-border); }
      .brand svg { filter: drop-shadow(0 2px 4px rgba(31, 61, 28, 0.25)); }
      nav { display: flex; gap: 2px; margin-left: var(--hl-s4); overflow-x: auto; padding: 4px; scrollbar-width: none;
        mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 32px), transparent); }
      nav::-webkit-scrollbar { display: none; }
      nav a { position: relative; display: inline-flex; align-items: center; gap: 6px; padding: 0 14px; height: 38px; border-radius: var(--hl-r-pill);
        color: var(--hl-text-muted); text-decoration: none; font-weight: 500; white-space: nowrap; --mdc-icon-size: 18px;
        transition: background var(--hl-dur) var(--hl-ease), color var(--hl-dur) var(--hl-ease), box-shadow var(--hl-dur) var(--hl-ease); }
      nav a:hover { background: color-mix(in srgb, var(--hl-surface-2) 80%, transparent); color: var(--hl-text); }
      nav a[aria-current="page"] { background: var(--hl-surface); color: var(--hl-primary); font-weight: 600;
        box-shadow: var(--hl-shadow-2), inset 0 0 0 1px color-mix(in srgb, var(--hl-leaf-300) 60%, transparent); }
      nav.top a[aria-current="page"]::after { content: ""; position: absolute; left: 50%; bottom: 4px; width: 16px; height: 2px; margin-left: -8px;
        border-radius: 2px; background: var(--hl-accent); }
      .view { animation: hl-rise var(--hl-dur-slow) var(--hl-ease) both; }
      .burst { position: fixed; z-index: 30; width: 0; height: 0; pointer-events: none; }
      .burst span { position: absolute; left: -5px; top: -4px; width: 10px; height: 7px; border-radius: 10px 0; background: var(--c);
        animation: hl-leaf 900ms cubic-bezier(0.2, 0.7, 0.3, 1) both; }
      @keyframes hl-leaf {
        0% { transform: translate(0, 0) rotate(0) scale(0.4); opacity: 0; }
        15% { opacity: 1; }
        100% { transform: translate(var(--dx), calc(var(--dy) + 40px)) rotate(var(--rot)) scale(1); opacity: 0; }
      }
      :host([narrow]) .bottom-nav a[aria-current="page"] { box-shadow: none; background: var(--hl-leaf-100); border-radius: 14px; }
      :host([narrow]) .bottom-nav { backdrop-filter: saturate(1.6) blur(14px); background: color-mix(in srgb, var(--hl-surface) 86%, transparent); }
      nav.sub { display: inline-flex; gap: 2px; padding: 4px; margin: 0 0 var(--hl-s4); border-radius: 999px; overflow-x: auto; max-width: 100%;
        background: color-mix(in srgb, var(--hl-surface-2) 85%, transparent); border: 1px solid color-mix(in srgb, var(--hl-border) 70%, transparent);
        scrollbar-width: none; }
      nav.sub a { display: inline-flex; align-items: center; gap: 6px; padding: 0 16px; height: 34px; border-radius: 999px; white-space: nowrap;
        color: var(--hl-text-muted); text-decoration: none; font-weight: 500; font-size: var(--hl-fs-sm); --mdc-icon-size: 17px;
        transition: background var(--hl-dur) var(--hl-ease), color var(--hl-dur) var(--hl-ease); }
      nav.sub a:hover { color: var(--hl-text); }
      nav.sub a[aria-current="page"] { background: var(--hl-surface); color: var(--hl-primary); font-weight: 600; box-shadow: var(--hl-shadow-1); }
      nav.sub a .badge { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; font-size: 11px; font-weight: 700; color: #fff;
        display: inline-grid; place-items: center; line-height: 1; }
      nav.sub a .badge.bad { background: var(--hl-danger); }
      nav.sub a .badge.warn { background: var(--hl-warning); }
      select.garden { width: auto; min-height: 34px; padding: 4px 30px 4px 12px; border-radius: 999px; font-weight: 600; flex: none;
        background-color: var(--hl-leaf-50); border-color: var(--hl-leaf-300); }
      nav a:focus-visible { outline: 2px solid var(--hl-focus); outline-offset: 2px; }
      nav a .badge { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; font-size: 11px; font-weight: 700; color: #fff;
        display: inline-grid; place-items: center; line-height: 1; }
      nav a .badge.bad { background: var(--hl-danger); }
      nav a .badge.warn { background: var(--hl-warning); }
      main { padding: var(--hl-s4); max-width: 1680px; margin: 0 auto; }
      .bottom-nav { display: none; }
      :host([narrow]) nav.top { display: none; }
      :host([narrow]) .bottom-nav { display: flex; position: fixed; bottom: 0; left: 0; right: 0; z-index: 4; background: var(--hl-surface);
        border-top: 1px solid var(--hl-border); justify-content: space-around; padding: 4px 0 calc(4px + env(safe-area-inset-bottom)); }
      :host([narrow]) .bottom-nav a { flex-direction: column; height: auto; padding: 4px 2px; font-size: 10.5px; gap: 2px; margin: 0;
        flex: 1 1 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      :host([narrow]) main { padding: var(--hl-s3) var(--hl-s3) 88px; }
      .toast { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); z-index: 20; background: var(--hl-soil-900); color: #fff;
        padding: 10px 18px; border-radius: var(--hl-r-pill); box-shadow: var(--hl-shadow-3); font-size: var(--hl-fs-sm); max-width: calc(100vw - 32px); }
      :host([narrow]) .toast { bottom: 84px; }
      .error { margin: var(--hl-s6) auto; max-width: 560px; text-align: center; }
    `,
  ];

  /** Colour theme chosen in this browser (night forces the dark palette). */
  private applyTheme = (): void => {
    const today = this.snapshot?.analysis?.today ?? new Date().toISOString().slice(0, 10);
    const { theme, dark } = themeAttribute(themeChoice(), today, this.snapshot?.settings.region?.hemisphere === "south", appearanceChoice());
    const isDark = dark ?? Boolean(this.hass?.themes?.darkMode);
    this.setAttribute("theme", theme);
    this.toggleAttribute("dark", isDark);
    // the palette goes on as inline custom properties: they always win and every
    // browser (also Safari on iPhone / the HA app) re-renders them straight away
    const palette = paletteFor(theme, isDark);
    for (const prop of this.paletteProps) if (!(prop in palette)) this.style.removeProperty(prop);
    for (const [prop, value] of Object.entries(palette)) this.style.setProperty(prop, value);
    this.paletteProps = Object.keys(palette);
  };
  private paletteProps: string[] = [];
  private lookLoaded = false;
  private lookSaving = false;

  /** The colour choice follows the Home Assistant user to every device (phone, tablet, PC). */
  private async loadLook(): Promise<void> {
    if (this.lookLoaded || !this.hass?.connection || this.panelConfig.web) return;
    this.lookLoaded = true;
    const before = { theme: themeChoice(), appearance: appearanceChoice() };
    let changedMeanwhile = false;
    try {
      const res = await this.hass.connection.sendMessagePromise<{ value?: { theme?: string; appearance?: string } | null }>({
        type: "frontend/get_user_data", key: "hortulus_look" });
      const v = res?.value;
      changedMeanwhile = themeChoice() !== before.theme || appearanceChoice() !== before.appearance;
      this.lookSaving = true;
      // a choice made while the request ran wins over the saved one
      const theme = themeChoice() === before.theme ? v?.theme : undefined;
      const look = appearanceChoice() === before.appearance ? v?.appearance : undefined;
      if (theme && THEMES.includes(theme as ThemeChoice) && theme !== themeChoice()) setThemeChoice(theme as ThemeChoice);
      if (look && APPEARANCES.includes(look as Appearance) && look !== appearanceChoice()) setAppearanceChoice(look as Appearance);
    } catch {
      /* older Home Assistant or no user data: the choice stays on this device */
    } finally {
      this.lookSaving = false;
    }
    // a choice made while the request ran only went to this device with the old other half: send the pair
    if (changedMeanwhile) this.saveLook();
  }

  /** Writes go one after the other, each carrying the choices of the moment it is sent, so the last word is the latest. */
  private lookChain: Promise<unknown> = Promise.resolve();

  private saveLook = (): void => {
    if (this.lookSaving || !this.hass?.connection || this.panelConfig.web) return;
    const connection = this.hass.connection;
    this.lookChain = this.lookChain.then(() =>
      connection
        .sendMessagePromise({ type: "frontend/set_user_data", key: "hortulus_look", value: { theme: themeChoice(), appearance: appearanceChoice() } })
        .catch(() => undefined),
    );
  };

  // ---------------------------------------------------------------------- //
  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass) {
      const lang = normalizeLang(this.snapshot?.lang ?? this.hass.locale?.language ?? this.hass.language);
      if (lang !== this.uiLang) {
        this.uiLang = lang;
        this.t = makeTranslator(lang);
      }
      this.applyTheme();
      void this.loadLook();
      setPersons(this.hass);
      if (!this.api) {
        this.api = new GardenApi(this.hass);
        void this.connect();
      } else {
        this.api.setHass(this.hass);
      }
    }
    if (changed.has("route") && this.route) {
      const [seg, sub] = this.route.path.replace(/^\//, "").split("/") as [Tab, string | undefined];
      this.tab = TABS.some((t) => t.id === seg) && this.tabAllowed(seg) ? seg : this.fallbackTab;
      if (this.tab === "handbook") this.chapter = sub ?? "";
    } else if (changed.has("panel") && !this.tabAllowed(this.tab)) {
      this.tab = this.fallbackTab; // the allowed tabs changed under the open one
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("hortulus-theme-changed", this.applyTheme);
    window.removeEventListener("hortulus-theme-changed", this.saveLook);
    void this.unsubscribe?.();
    this.unsubscribe = undefined;
    this.api = undefined;
  }

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("hortulus-theme-changed", this.applyTheme);
    window.addEventListener("hortulus-theme-changed", this.saveLook);
    if (this.hass && !this.api) {
      this.api = new GardenApi(this.hass);
      void this.connect();
    }
  }

  /** Show another garden: remember it, subscribe to it, load its plants. */
  private async switchGarden(id: string): Promise<void> {
    if (!this.api || id === (this.snapshot?.entry_id ?? "")) return;
    try {
      localStorage.setItem("hortulus.garden", id);
    } catch {
      /* private mode */
    }
    await this.unsubscribe?.();
    this.unsubscribe = undefined;
    this.api.gardenId = id;
    this.snapshot = null;
    await this.connect();
  }

  private async connect(retried = false): Promise<void> {
    if (this.api && !this.api.gardenId && !retried) {
      try {
        this.api.gardenId = localStorage.getItem("hortulus.garden") ?? "";
      } catch {
        /* private mode */
      }
    }
    try {
      await this.loadPlants();
      void this.loadGlossary();
      this.unsubscribe = await this.api!.subscribe((snap) => {
        this.snapshot = snap;
        this.applyTheme();
        const lang = normalizeLang(snap.lang);
        if (lang !== this.uiLang) {
          this.uiLang = lang;
          this.t = makeTranslator(lang);
          void this.loadGlossary();
        }
        if (this.openTask) this.openTask = snap.tasks.find((t) => t.id === this.openTask!.id) ?? null;
      });
    } catch (err) {
      const notLoaded = (err as { code?: string }).code === "not_loaded";
      if (notLoaded && this.api?.gardenId && !retried) {
        // the remembered garden was removed: forget it and show the first garden instead
        this.api.gardenId = "";
        try {
          localStorage.removeItem("hortulus.garden");
        } catch {
          /* private mode */
        }
        await this.connect(true);
        return;
      }
      this.error = notLoaded ? this.t("common.not_loaded") : String((err as Error).message ?? err);
    }
  }

  private async loadGlossary(): Promise<void> {
    try {
      setGlossary((await this.api!.handbookIndex(this.uiLang)).glossary);
      setSupplies(await this.api!.supplies());
    } catch {
      /* older backend - tooltips stay empty */
    }
  }

  private openHandbook(chapter = ""): void {
    if (!this.tabAllowed("handbook")) return;
    this.chapter = chapter;
    const base = `/${this.route?.prefix?.replace(/^\//, "") || "hortulus"}/handbook${chapter ? `/${chapter}` : ""}`;
    history.pushState(null, "", base);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    this.tab = "handbook";
  }

  private async loadPlants(): Promise<void> {
    const res = await this.api!.plants();
    this.plants = res.plants;
    this.families = res.families;
  }

  private navigate(tab: Tab, ev?: Event): void {
    if (!this.tabAllowed(tab)) tab = this.fallbackTab;
    ev?.preventDefault();
    const path = `/${this.route?.prefix?.replace(/^\//, "") || "hortulus"}/${tab === "dashboard" ? "" : tab}`.replace(/\/$/, "");
    history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    this.tab = tab;
    this.lastInGroup = { ...this.lastInGroup, [this.groupOf(tab).id]: tab };
  }

  private openPlant(id: string): void {
    this.popupPlant = this.plants.find((p) => p.id === id) ?? null;
  }

  /** Show one crop in the planner (selected, popup open). */
  private focusPlanting(detail: { planting_id: string; season: number }): void {
    this.popupPlant = null;
    this.plannerSeason = detail.season;
    this.plannerFocus = { id: detail.planting_id, season: detail.season, n: (this.plannerFocus?.n ?? 0) + 1 };
    this.navigate("planner");
  }

  /** Show one crop in the crops list. */
  private focusCrop(detail: { planting_id: string; season: number }): void {
    this.popupPlant = null;
    this.plannerSeason = detail.season;
    this.cropsFocus = { id: detail.planting_id, season: detail.season, n: (this.cropsFocus?.n ?? 0) + 1 };
    this.navigate("crops");
  }

  private renderPlantPopup(): TemplateResult | typeof nothing {
    const p = this.popupPlant;
    if (!p || !this.snapshot) return nothing;
    return html`<hl-modal heading=${plantName(p, this.uiLang)} accent=${familyColor(this.families, p.family)} closeLabel=${this.t("common.close")}
      @closed=${() => (this.popupPlant = null)}
      @select-plant=${(e: CustomEvent<Plant>) => { this.popupPlant = e.detail; void this.updateComplete.then(() => this.renderRoot.querySelector("hl-modal")?.toTop()); }}
      @focus-planting=${(e: CustomEvent<{ planting_id: string; season: number }>) => this.focusPlanting(e.detail)}>
      <span slot="subheading" class="small muted"><i>${p.scientific_name}</i> · ${familyName(this.families, p.family, this.uiLang) ?? p.family}</span>
      <hl-plant-detail .plant=${p} .plants=${this.plants} .families=${this.families} .snapshot=${this.snapshot} .t=${this.t} lang=${this.uiLang}></hl-plant-detail>
    </hl-modal>`;
  }

  private toast(message: string): void {
    this.toastMsg = message;
    window.clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => (this.toastMsg = ""), 4500);
  }

  private async completeTask(task: Task): Promise<void> {
    try {
      await this.api!.taskAction(task.id, "complete");
      this.toast(this.t("task.completed", { title: task.title }));
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message }));
    }
  }

  private async irrigation(action: "run" | "stop"): Promise<void> {
    try {
      if (action === "stop") {
        await this.api!.irrigationStop();
        this.toast(this.t("dash.irrigation_stopped"));
        return;
      }
      const res = await this.api!.irrigationRun();
      const skipped = Object.values(res.reasons ?? {});
      this.toast(res.started ? this.t("dash.irrigation_started", { min: Math.round(res.total_minutes) }) : skipped[0] ?? this.t("dash.irrigation_nothing"));
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message }));
    }
  }

  private async closeValve(entityId: string): Promise<void> {
    try {
      const res = await this.api!.irrigationClose(entityId);
      this.toast(res.state === "off" || res.state === "closed" ? this.t("valve.closed") : this.t("valve.still_open", { state: res.state ?? "?" }));
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message }));
    }
  }

  private async postponeTask(task: Task, days: number): Promise<void> {
    try {
      await this.api!.taskAction(task.id, "postpone", { days });
      this.toast(this.t("task.postponed", { title: task.title, n: days }));
    } catch (err) {
      this.toast(this.t("common.error", { message: (err as Error).message }));
    }
  }

  // ---------------------------------------------------------------------- //
  private renderTab(): TemplateResult {
    const snap = this.snapshot!;
    const admin = this.hass.user?.is_admin ?? true;
    const plantMap = new Map(this.plants.map((p) => [p.id, p]));
    // a shared view that allows no tab at all shows nothing of the garden
    if (!this.tabAllowed(this.tab)) return html`<div class="card empty">${this.t("nav.nothing_shared")}</div>`;
    switch (this.tab) {
      case "layout":
        return html`<hl-planner-view mode="layout" .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin} .narrow=${this.narrow} .initialSeason=${this.plannerSeason}
          .transitionRequest=${this.transitionRequest}></hl-planner-view>`;
      case "crops":
        return html`<hl-crops-view .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin} .initialSeason=${this.plannerSeason} .focusPlanting=${this.cropsFocus}></hl-crops-view>`;
      case "analysis":
        return html`<hl-analysis-view .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin}></hl-analysis-view>`;
      case "planner":
        return html`<hl-planner-view mode="plant" .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin} .narrow=${this.narrow} .initialSeason=${this.plannerSeason}
          .focusPlanting=${this.plannerFocus}></hl-planner-view>`;
      case "library":
        return html`<hl-library-view .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin} @plants-changed=${() => this.loadPlants()}></hl-library-view>`;
      case "weather":
        return html`<hl-weather-view .snapshot=${snap} .hass=${this.hass} .api=${this.api} .viewer=${!!this.panelConfig.viewer}
          .viewerClimate=${!!(this.panelConfig.viewer as { climate?: boolean } | undefined)?.climate} .t=${this.t} .lang=${this.uiLang}></hl-weather-view>`;
      case "calendar":
        return html`<hl-calendar-view .snapshot=${snap} .api=${this.api!} .t=${this.t} .lang=${this.uiLang} .plants=${plantMap} .families=${this.families}></hl-calendar-view>`;
      case "journal":
        return html`<hl-journal-view .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin} .web=${!!this.panelConfig.web}></hl-journal-view>`;
      case "view":
        return html`<hl-garden-viewer .snapshot=${snap} .plants=${this.plants} .families=${this.families} .t=${this.t} .lang=${this.uiLang}></hl-garden-viewer>`;
      case "cooking":
        return html`<hl-cooking-view .api=${this.api!} .t=${this.t} .hass=${this.hass} .lang=${this.uiLang} .gardenKey=${this.api?.gardenId ?? ""}
          .readonly=${!!this.panelConfig.viewer} .web=${!!this.panelConfig.web}></hl-cooking-view>`;
      case "advice":
        return html`<hl-advice-view .snapshot=${snap} .plants=${this.plants} .families=${this.families} .api=${this.api!} .t=${this.t}
          .lang=${this.uiLang} .admin=${admin}></hl-advice-view>`;
      case "handbook":
        return html`<hl-handbook-view .api=${this.api!} .t=${this.t} .lang=${this.uiLang} .chapterId=${this.chapter} .narrow=${this.narrow}></hl-handbook-view>`;
      case "print":
        return html`<hl-print-view .snapshot=${snap} .api=${this.api!} .t=${this.t} .lang=${this.uiLang} .narrow=${this.narrow} .admin=${admin}></hl-print-view>`;
      case "settings":
        return html`<hl-settings-view .snapshot=${snap} .plants=${this.plants} .hass=${this.hass} .api=${this.api!} .t=${this.t} .lang=${this.uiLang} .admin=${admin}></hl-settings-view>`;
      default:
        return html`<hl-dashboard-view .snapshot=${snap} .api=${this.api} .plants=${plantMap} .families=${this.families} .t=${this.t} .lang=${this.uiLang} .admin=${admin}></hl-dashboard-view>`;
    }
  }

  /** Problems the garden check finds right now (re-checked on every change). */
  private renderBadge(): TemplateResult | typeof nothing {
    const d = this.snapshot?.diagnosis;
    const n = d ? d.error + d.warning : 0;
    if (!d || !n) return nothing;
    return html`<span class="badge ${d.error ? "bad" : "warn"}" title=${this.t("analysis.badge", { errors: d.error, warnings: d.warning })}>${n}</span>`;
  }

  /** Open a place: the tab you used last there, else its first tab. */
  private openGroup(group: { id: Group; tabs: Tab[] }, e: Event): void {
    const last = this.lastInGroup[group.id];
    this.navigate(last && group.tabs.includes(last) ? last : group.tabs[0], e);
  }

  /** The tabs of the current place, as a row under the app bar. */
  private renderSubnav(): TemplateResult | typeof nothing {
    const group = this.groupOf(this.tab);
    if (group.tabs.length < 2) return nothing;
    return html`<nav class="sub" aria-label=${this.t(`nav.group.${group.id}`)}>
      ${group.tabs.map((id) => {
        const tab = TABS.find((x) => x.id === id)!;
        return html`<a href="#" aria-current=${id === this.tab ? "page" : "false"} @click=${(e: Event) => this.navigate(id, e)}>
          ${gicon(tab.icon, 17)}${this.t(`nav.${id}`)}${id === "analysis" ? this.renderBadge() : nothing}</a>`;
      })}
    </nav>`;
  }

  private renderNav(cls: string): TemplateResult | typeof nothing {
    if (this.groups.length < 2) return nothing; // one place only (a visitor's plan): no menu
    const current = this.groupOf(this.tab).id;
    return html`<nav class=${cls} aria-label="Hortulus">
      ${this.groups.map((g) => html`<a href="#" aria-current=${g.id === current ? "page" : "false"} @click=${(e: Event) => this.openGroup(g, e)}>
        ${gicon(g.icon, 19)}${this.t(g.tabs.length > 1 ? `nav.group.${g.id}` : `nav.${g.tabs[0]}`)}${g.tabs.includes("analysis") ? this.renderBadge() : nothing}</a>`)}
    </nav>`;
  }

  /** First load: a calm skeleton instead of a bare "Loading". */
  private renderLoading(): TemplateResult {
    return html`<div class="loading" aria-busy="true" aria-label=${this.t("common.loading")}>
      <div class="skeleton" style="width:220px;height:14px"></div>
      <div class="skeleton" style="width:320px;height:34px;margin-top:10px"></div>
      <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:24px">
        <div class="skeleton" style="height:320px;border-radius:16px"></div><div class="skeleton" style="height:320px;border-radius:16px"></div>
      </div></div>`;
  }

  render(): TemplateResult {
    if (this.tab === "wall" && this.snapshot && this.api) {
      return html`<hl-wall-view .snapshot=${this.snapshot} .hass=${this.hass} .api=${this.api} .t=${this.t} lang=${this.uiLang}
          ?admin=${this.hass.user?.is_admin ?? true}
          .plants=${new Map(this.plants.map((p) => [p.id, p]))} .families=${this.families}
          @navigate=${(e: CustomEvent<Tab>) => this.navigate(e.detail)}
          @complete-task=${(e: CustomEvent<Task>) => this.completeTask(e.detail)}
          @hl-celebrate=${(e: CustomEvent<{ x: number; y: number }>) => celebrate(this.renderRoot as ShadowRoot, e.detail.x, e.detail.y)}></hl-wall-view>
        ${this.toastMsg ? html`<div class="toast" role="status" aria-live="polite">${this.toastMsg}</div>` : nothing}`;
    }
    return html`
      <header class="appbar">
        ${this.narrow ? html`<button class="icon-btn" aria-label="Menu" @click=${() => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }))}>
          <ha-icon icon="mdi:menu"></ha-icon></button>` : nothing}
        <div class="brand">${emblem(30)}<span>Hortulus</span>${this.narrow || (this.snapshot?.gardens?.length ?? 0) > 1 ? nothing : html`<small>${this.t("app.tagline")}</small>`}</div>
        ${(this.snapshot?.gardens?.length ?? 0) > 1 ? html`<select class="garden" aria-label=${this.t("app.garden")}
            @change=${(e: Event) => this.switchGarden((e.target as HTMLSelectElement).value)}>
          ${this.snapshot!.gardens!.map((g) => html`<option value=${g.entry_id} ?selected=${g.entry_id === this.snapshot!.entry_id}>${g.title}</option>`)}
        </select>` : nothing}
        ${this.renderNav("top")}
        ${this.narrow && this.tabAllowed("settings") ? html`<span style="flex:1"></span>
          <button class="icon-btn" aria-label=${this.t("nav.settings")} aria-pressed=${String(this.tab === "settings")} @click=${() => this.navigate("settings")}>
            <ha-icon icon="mdi:cog-outline"></ha-icon></button>` : nothing}
      </header>
      <main @open-task=${(e: CustomEvent<Task>) => (this.openTask = e.detail)}
        @complete-task=${(e: CustomEvent<Task>) => this.completeTask(e.detail)}
        @hl-celebrate=${(e: CustomEvent<{ x: number; y: number }>) => celebrate(this.renderRoot as ShadowRoot, e.detail.x, e.detail.y)}
        @postpone-task=${(e: CustomEvent<{ task: Task; days: number }>) => this.postponeTask(e.detail.task, e.detail.days)}
        @irrigation=${(e: CustomEvent<"run" | "stop">) => this.irrigation(e.detail)}
        @close-valve=${(e: CustomEvent<string>) => this.closeValve(e.detail)}
        @new-task=${() => (this.creatingTask = true)}
        @navigate=${(e: CustomEvent<Tab>) => this.navigate(e.detail)}
        @season-changed=${(e: CustomEvent<number>) => (this.plannerSeason = e.detail)}
        @year-transition=${() => { this.navigate("layout"); this.transitionRequest += 1; }}
        @open-handbook=${(e: CustomEvent<{ chapter?: string }>) => this.openHandbook(e.detail?.chapter ?? "")}
        @open-plant=${(e: CustomEvent<string>) => this.openPlant(e.detail)}
        @focus-planting=${(e: CustomEvent<{ planting_id: string; season: number }>) => this.focusPlanting(e.detail)}
        @focus-crop=${(e: CustomEvent<{ planting_id: string; season: number }>) => this.focusCrop(e.detail)}
        @hl-toast=${(e: CustomEvent<{ message: string }>) => this.toast(e.detail.message)}>
        ${this.error ? html`<div class="card error">${emblem(56)}<p>${this.error}</p></div>`
          : this.snapshot ? html`${this.renderSubnav()}${keyed(this.tab, html`<div class="view">${this.renderTab()}</div>`)}` : this.renderLoading()}
      </main>
      ${this.renderNav("bottom-nav")}
      ${this.snapshot && (this.openTask || this.creatingTask) ? html`<hl-task-dialog .task=${this.openTask} .create=${this.creatingTask} .snapshot=${this.snapshot}
        @open-handbook=${(e: CustomEvent<{ chapter?: string }>) => this.openHandbook(e.detail?.chapter ?? "")}
        .beds=${this.snapshot.beds} .api=${this.api!} .t=${this.t} .lang=${this.uiLang} .today=${this.snapshot.analysis?.today ?? ""}
        @hl-toast=${(e: CustomEvent<{ message: string }>) => this.toast(e.detail.message)}
        @closed=${() => { this.openTask = null; this.creatingTask = false; }}></hl-task-dialog>` : nothing}
      ${this.renderPlantPopup()}
      ${this.toastMsg ? html`<div class="toast" role="status" aria-live="polite">${this.toastMsg}</div>` : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hortulus-panel": HortulusPanel;
  }
}
