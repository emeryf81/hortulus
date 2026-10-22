// "Cooking" tab: a seasonal cookbook from what the garden gives right now.
// Ideas (recipes for the ready produce, with what is in the fridge, meat or
// fish and a side of choice), the cook's own cookbook (favourites, shared
// recipes) and one shopping list for the dishes picked.  Every dish gets a
// picture (the crops on a plate); recipes, the cookbook and the shopping list
// export to PDF, print, go to a phone (HA) or the cook's mailbox (website).
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { GardenApi } from "../api";
import type { Translate } from "../i18n";
import { shared } from "../styles/tokens";
import type { CookingMenu, CookingOverview, CookingPrefs, CookingProduce, CustomIngredient, HomeAssistant, Recipe, RecipeSpec, RecipeTarget } from "../types";
import { formatDate } from "../util/garden";
import { glyphIcon, GLYPHS } from "../planner/plant-glyphs";
import { dishDataUrl, dishJpeg } from "../components/dish-picture";
import "../components/modal";

type Section = "ideas" | "book" | "shopping";
type BookFilter = "all" | "favorite" | "shared";
type Course = "soup" | "starter" | "main" | "dessert" | "preserve";
const COURSES: Course[] = ["soup", "starter", "main", "dessert", "preserve"];

interface WebHooks {
  mailSelf?: (subject: string, text: string) => Promise<{ ok: boolean; to?: string; error?: string }>;
}

const KIND_GLYPH: Record<string, string> = {
  leafy: "leafy", brassica: "cabbage", root: "root", allium: "onion", fruiting: "tomato", squash: "pumpkin",
  legume: "bean", potato: "potato", corn: "corn", asparagus: "asparagus", herb: "herb", fruit: "berry",
};
const PROTEIN_GROUPS = ["meat", "fish", "veg_protein"] as const;
const UNITS = ["g", "ml", "pc", "tbsp", "clove", "slice", "cube", "can"] as const;
const SOURCES = ["garden", "pantry", "shop"] as const;
/** What the backend accepts in a recipe of the cook's own. */
const MAX_INGREDIENTS = 40;
const MAX_STEPS = 30;
const SHOP_ORDER = ["meat", "fish", "veg_protein", "dairy", "side", "pantry", "other"];

/** The cook's own version of a recipe while it is being edited. */
interface Draft {
  ingredients: CustomIngredient[];
  steps: string[];
}
const EMPTY_PREFS: CookingPrefs = { pantry: [], use: [], proteins: [], side: "", servings: 2 };

const specOf = (r: Recipe): RecipeSpec => ({ ...r.spec, extras: [...r.spec.extras], produce: [...r.spec.produce] });
const web = (): WebHooks | undefined => (window as unknown as { hortulusWeb?: WebHooks }).hortulusWeb;

@customElement("hl-cooking-view")
export class CookingView extends LitElement {
  @property({ attribute: false }) api!: GardenApi;
  @property({ attribute: false }) t!: Translate;
  @property({ attribute: false }) hass?: HomeAssistant;
  @property() lang = "en";
  /** A visitor's read-only view (website): only the recipes the owner shares. */
  @property({ type: Boolean }) readonly = false;
  /** On the website: recipes can be shared with whoever may see the garden. */
  @property({ type: Boolean }) web = false;
  @property() gardenKey = "";

  @state() private section: Section = "ideas";
  @state() private data: CookingOverview | null = null;
  @state() private prefs: CookingPrefs = { ...EMPTY_PREFS };
  @state() private produce: string[] = [];
  @state() private open: Recipe | null = null;
  @state() private openList: Recipe[] = [];
  @state() private basket: RecipeSpec[] = [];
  @state() private basketRecipes: Recipe[] = [];
  @state() private busy = "";
  @state() private msg = "";
  @state() private error = "";
  @state() private bookFilter: BookFilter = "all";
  @state() private bookSearch = "";
  @state() private bookCourse: Course | "" = "";
  @state() private todoEntity = "";
  @state() private notifyService = "";
  @state() private showPantry = false;
  @state() private draft: Draft | null = null;
  /** Side, meat and fridge choices: open on a wide screen, folded on a phone. */
  @state() private moreOpen = !window.matchMedia?.("(max-width: 900px)").matches;
  private refreshTimer?: number;
  private loadedFor = "";

  static styles = [
    shared,
    css`
      :host { display: block; }
      .tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: var(--hl-s3); }
      .layout { display: grid; grid-template-columns: minmax(260px, 340px) minmax(0, 1fr); gap: var(--hl-s4); align-items: start; }
      @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
      .pick { display: flex; flex-wrap: wrap; gap: 6px; }
      .pick button { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px 4px 6px; border-radius: 999px;
        border: 1px solid var(--hl-border); background: var(--hl-surface); color: var(--hl-text); font: inherit; font-size: var(--hl-fs-sm); cursor: pointer; }
      .pick button[aria-pressed="true"] { background: var(--hl-leaf-100, #e3f1dc); border-color: var(--hl-leaf-500, #4f8a34); font-weight: 600; }
      .pick button.text { padding-left: 10px; }
      .pick .until { font-size: 10px; color: var(--hl-text-muted); }
      h3 { margin: var(--hl-s3) 0 6px; font-size: var(--hl-fs-sm); text-transform: uppercase; letter-spacing: .04em; color: var(--hl-text-muted); }
      h3:first-child { margin-top: 0; }
      .servings { display: inline-flex; align-items: center; gap: 8px; }
      .servings b { min-width: 2ch; text-align: center; font-size: var(--hl-fs-lg); }
      .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: var(--hl-s3); }
      .recipe { display: flex; flex-direction: column; border: 1px solid var(--hl-border); border-radius: var(--hl-r-lg); overflow: hidden;
        background: var(--hl-surface); cursor: pointer; text-align: left; padding: 0; font: inherit; color: inherit; transition: transform .15s, box-shadow .15s; }
      .recipe:hover, .recipe:focus-visible { transform: translateY(-2px); box-shadow: var(--hl-shadow-md, 0 6px 18px rgba(0,0,0,.12)); }
      .recipe img { width: 100%; aspect-ratio: 1 / 0.78; object-fit: cover; display: block; background: #b88a5c; }
      .recipe .body { padding: 10px 12px 12px; display: flex; flex-direction: column; gap: 4px; }
      .recipe .title { font-weight: 700; line-height: 1.25; }
      .recipe .sub { color: var(--hl-text-muted); font-size: var(--hl-fs-sm); }
      .recipe .meta { display: flex; gap: 6px; flex-wrap: wrap; font-size: var(--hl-fs-xs); color: var(--hl-text-muted); align-items: center; }
      .share { height: 6px; border-radius: 3px; background: var(--hl-surface-2); overflow: hidden; margin-top: 2px; }
      .share i { display: block; height: 100%; background: var(--hl-leaf-500, #4f8a34); }
      .star { color: var(--hl-sun-500, #e9a92b); }
      .detail { display: grid; grid-template-columns: minmax(0, 300px) minmax(0, 1fr); gap: var(--hl-s4); }
      @media (max-width: 760px) { .detail { grid-template-columns: 1fr; } }
      .detail img.big { width: 100%; border-radius: var(--hl-r-lg); display: block; }
      .ingr { list-style: none; padding: 0; margin: 0; }
      .ingr li { display: grid; grid-template-columns: 22px 1fr auto; gap: 6px; align-items: center; padding: 4px 0; border-bottom: 1px dashed var(--hl-border); }
      .ingr li .q { color: var(--hl-text-muted); font-size: var(--hl-fs-sm); white-space: nowrap; }
      .ingr .src { font-size: 10px; text-transform: uppercase; letter-spacing: .04em; }
      .ingr .src.garden { color: var(--hl-leaf-600, #3f7a2a); font-weight: 700; }
      ol.steps { padding-left: 0; list-style: none; counter-reset: s; margin: 0; }
      ol.steps li { counter-increment: s; position: relative; padding: 0 0 10px 34px; line-height: 1.45; }
      ol.steps li::before { content: counter(s); position: absolute; left: 0; top: 0; width: 24px; height: 24px; border-radius: 50%;
        background: var(--hl-leaf-600, #2f6b4f); color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
      .switch { display: grid; grid-template-columns: auto 1fr; gap: 6px 10px; align-items: center; margin: var(--hl-s2) 0; }
      .switch select { min-width: 0; }
      .actions { display: flex; flex-wrap: wrap; gap: 6px; }
      .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
      .toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: var(--hl-s3); }
      .toolbar input[type=search] { flex: 1; min-width: 160px; }
      table { width: 100%; border-collapse: collapse; font-size: var(--hl-fs-sm); }
      td, th { padding: 6px; border-bottom: 1px solid var(--hl-border); text-align: left; }
      td.num { text-align: right; white-space: nowrap; }
      .menu-grid { grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
      .menu { display: flex; flex-direction: column; gap: 6px; }
      .menu .actions { margin-top: auto; }
      .menu h4 { margin: 0; font-family: var(--hl-font-display, inherit); }
      .menu-courses { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
      .menu-courses li { display: flex; flex-direction: column; }
      .linklike { background: none; border: 0; padding: 0; font: inherit; color: var(--hl-primary-hover, inherit); text-align: left; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
      .basket-item { display: grid; grid-template-columns: 56px 1fr auto; gap: 10px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--hl-border); }
      .basket-item img { width: 56px; height: 56px; border-radius: 10px; object-fit: cover; }
      .note { width: 100%; min-height: 60px; }
      .layout > * { min-width: 0; }
      .more { white-space: normal; text-align: left; justify-content: flex-start; height: auto; }
      aside select, aside label { max-width: 100%; min-width: 0; }
      @media (min-width: 901px) { .more { display: none; } }
      @media (max-width: 600px) {
        .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
        .recipe .body { padding: 8px 9px 10px; }
        .recipe .title { font-size: var(--hl-fs-sm); }
      }
      .ed-ingr { display: grid; grid-template-columns: minmax(0, 1fr) 72px 84px 92px auto; gap: 6px; align-items: center; }
      .ed-ingr input, .ed-ingr select { min-width: 0; width: 100%; }
      .ed-step { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 6px; align-items: start; }
      .ed-step .num { width: 24px; height: 24px; border-radius: 50%; background: var(--hl-leaf-600, #2f6b4f); color: #fff;
        display: grid; place-items: center; font-size: 12px; font-weight: 700; margin-top: 4px; }
      .ed-step textarea { width: 100%; min-height: 54px; resize: vertical; font: inherit; }
      .ed-step .tools { display: flex; flex-direction: column; gap: 0; }
      .ed-step .tools .icon-btn { width: 28px; height: 28px; min-width: 28px; }
      .ed-step textarea { min-height: 84px; }
      @media (max-width: 600px) {
        .ed-ingr { grid-template-columns: 64px minmax(0, 1fr) minmax(0, 1fr) auto; }
        .ed-ingr input[type=text] { grid-column: 1 / 4; grid-row: 1; }
        .ed-ingr .icon-btn { grid-column: 4; grid-row: 1; }
      }
      .chapter + .chapter { margin-top: var(--hl-s5); }
      .chapter-title { font-family: var(--hl-font-serif); font-size: var(--hl-fs-xl); text-transform: none; letter-spacing: 0; color: var(--hl-text);
        margin: 0 0 var(--hl-s3); display: flex; align-items: baseline; gap: 8px; border-bottom: 1px solid var(--hl-border); padding-bottom: 6px; }
      .banner { padding: 10px 12px; border-radius: var(--hl-r-md); background: var(--hl-surface-2); margin-bottom: var(--hl-s3); }
      .banner.err { background: var(--hl-tomato-100, #fde3dd); }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    if (this.readonly) this.section = "book";
    try {
      this.basket = JSON.parse(localStorage.getItem(this.basketKey) || "[]") as RecipeSpec[];
    } catch {
      this.basket = [];
    }
  }

  protected updated(changed: Map<string, unknown>): void {
    const key = `${this.gardenKey}|${this.lang}`;
    if ((changed.has("api") || changed.has("gardenKey") || changed.has("lang")) && this.api && key !== this.loadedFor) {
      this.loadedFor = key;
      void this.load(true);
    }
  }

  private get basketKey(): string {
    return `hortulus-cook-basket-${this.gardenKey || "default"}`;
  }

  /** Bumped at every change of the basket: a reload that started before it must not put old recipes back. */
  private basketGen = 0;

  private storeBasket(): void {
    this.basketGen++;
    try {
      localStorage.setItem(this.basketKey, JSON.stringify(this.basket));
    } catch {
      /* private mode: the list lives as long as the page */
    }
  }

  private loadSeq = 0;

  private async load(first = false): Promise<void> {
    const seq = ++this.loadSeq;
    this.busy = "load";
    this.error = "";
    try {
      const data = first
        ? await this.api.cookingSuggest({ lang: this.lang })
        : await this.api.cookingSuggest({ prefs: this.prefs, produce: this.produce, lang: this.lang });
      if (seq !== this.loadSeq) return; // a newer request is under way: its answer counts
      this.data = data;
      if (first) {
        this.prefs = { ...EMPTY_PREFS, ...(data.prefs ?? data.used_prefs) };
        this.produce = data.produce.map((p) => p.plant_id);
      }
      if (this.basket.length) void this.loadBasket();
    } catch (err) {
      this.error = (err as Error).message || String(err);
    } finally {
      if (seq === this.loadSeq) this.busy = "";
    }
  }

  /** Ask again shortly after the cook stops clicking. */
  private refresh(): void {
    window.clearTimeout(this.refreshTimer);
    this.refreshTimer = window.setTimeout(() => void this.load(), 280);
  }

  /** What the cook has at home right now: "always in the house" and "use up from the fridge". */
  private get home(): string[] {
    return [...this.prefs.pantry, ...this.prefs.use];
  }

  private toggle(list: "pantry" | "use" | "proteins", id: string): void {
    const cur = this.prefs[list];
    this.prefs = { ...this.prefs, [list]: cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id] };
    this.refresh();
  }

  private toggleProduce(id: string): void {
    this.produce = this.produce.includes(id) ? this.produce.filter((x) => x !== id) : [...this.produce, id];
    this.refresh();
  }

  private flash(msg: string): void {
    this.msg = msg;
    window.setTimeout(() => {
      if (this.msg === msg) this.msg = "";
    }, 4000);
  }

  private async savePrefs(): Promise<void> {
    try {
      const { prefs } = await this.api.cookingPrefs(this.prefs);
      if (this.data) this.data = { ...this.data, prefs };
      this.flash(this.t("cook.prefs_saved"));
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  // -- a recipe ------------------------------------------------------------- //
  private openRecipe(r: Recipe, list: Recipe[]): void {
    this.open = r;
    this.openList = list;
  }

  private async changeSpec(change: Partial<RecipeSpec>): Promise<void> {
    if (!this.open) return;
    const spec = { ...specOf(this.open), ...change };
    try {
      const { recipe } = await this.api.cookingRender(spec, this.lang, this.home);
      const saved = this.data?.book.find((b) => b.id === recipe.id);
      this.open = saved ?? recipe;
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  private isSaved(r: Recipe): Recipe | undefined {
    return this.data?.book.find((b) => b.id === r.id);
  }

  private async save(r: Recipe, extra: { favorite?: boolean; shared?: boolean; ingredients?: CustomIngredient[]; steps?: string[] } = {}): Promise<void> {
    try {
      const { book, id } = await this.api.cookbookSave({ spec: specOf(r), ...extra }, this.lang, this.home);
      if (this.data) this.data = { ...this.data, book };
      const fresh = book.find((b) => b.id === id);
      if (fresh) this.basketRecipes = this.basketRecipes.map((b) => (b.id === id ? fresh : b));
      if (this.open?.id === id) this.open = book.find((b) => b.id === id) ?? this.open;
      this.flash(this.t("cook.saved"));
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  private async updateRecipe(r: Recipe, changes: Record<string, unknown>): Promise<void> {
    if (!this.isSaved(r)) {
      await this.save(r, changes as { favorite?: boolean; shared?: boolean; ingredients?: CustomIngredient[]; steps?: string[] });
      return;
    }
    try {
      const { book } = await this.api.cookbookUpdate(r.id, changes, this.lang, this.home);
      if (this.data) this.data = { ...this.data, book };
      const fresh = book.find((b) => b.id === r.id);
      if (this.open?.id === r.id) this.open = fresh ?? this.open;
      if (fresh) this.basketRecipes = this.basketRecipes.map((b) => (b.id === r.id ? fresh : b)); // the list follows an edit
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  private async removeRecipe(r: Recipe): Promise<void> {
    if (!confirm(this.t("cook.delete_confirm", { title: r.title }))) return;
    try {
      const { book } = await this.api.cookbookDelete(r.id, this.lang, this.home);
      if (this.data) this.data = { ...this.data, book };
      if (this.open?.id === r.id) this.open = null;
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  // -- shopping basket ----------------------------------------------------- //
  private inBasket(r: Recipe): boolean {
    return this.basket.some((s) => JSON.stringify(s) === JSON.stringify(r.spec));
  }

  private toggleBasket(r: Recipe): void {
    if (this.inBasket(r)) {
      this.basket = this.basket.filter((s) => JSON.stringify(s) !== JSON.stringify(r.spec));
      this.basketRecipes = this.basketRecipes.filter((b) => b.id !== r.id);
    } else {
      this.basket = [...this.basket, specOf(r)];
      this.basketRecipes = [...this.basketRecipes, r];
      this.flash(this.t("cook.added_to_list", { title: r.title }));
    }
    this.storeBasket();
  }

  private async loadBasket(): Promise<void> {
    const gen = this.basketGen;
    const out: Recipe[] = [];
    for (const spec of this.basket) {
      try {
        const { recipe } = await this.api.cookingRender(spec, this.lang, this.home);
        out.push(this.data?.book.find((b) => b.id === recipe.id) ?? recipe); // the cook's own version when saved
      } catch {
        /* a crop that is no longer known: drop it */
      }
    }
    if (gen === this.basketGen) this.basketRecipes = out;
  }

  private shoppingRows(): { buy: { name: string; label: string; group: string; qty: number; unit: string }[]; garden: { name: string; qty: number }[] } {
    const buy = new Map<string, { name: string; label: string; group: string; qty: number; unit: string }>();
    const garden = new Map<string, { name: string; qty: number }>();
    for (const r of this.basketRecipes) {
      for (const i of r.ingredients) {
        if (i.source === "shop") {
          const key = `${i.id}|${i.unit}`;
          const row = buy.get(key) ?? { name: i.name, label: "", group: i.group, qty: 0, unit: i.unit };
          row.qty += i.qty;
          buy.set(key, row);
        } else if (i.source === "garden") {
          const row = garden.get(i.id) ?? { name: i.name, qty: 0 };
          row.qty += i.qty;
          garden.set(i.id, row);
        }
      }
    }
    const order = SHOP_ORDER;
    const rank = (g: string): number => (order.includes(g) ? order.indexOf(g) : order.length);
    const unit = (u: string): string => (u === "pc" || u === "cube" ? "" : this.t(`cook.unit.${u}`));
    const rows = [...buy.values()]
      .map((r) => ({ ...r, label: `${Math.round(r.qty * 10) / 10} ${unit(r.unit)}`.trim() }))
      .sort((a, b) => rank(a.group) - rank(b.group) || a.name.localeCompare(b.name));
    return { buy: rows, garden: [...garden.values()].sort((a, b) => a.name.localeCompare(b.name)) };
  }

  // -- export ---------------------------------------------------------------- //
  private target(recipes: Recipe[]): RecipeTarget {
    const ids = recipes.filter((r) => this.isSaved(r)).map((r) => r.id);
    const specs = recipes.filter((r) => !this.isSaved(r)).map((r) => specOf(r));
    return { ...(ids.length ? { ids } : {}), ...(specs.length ? { specs } : {}), pantry: this.home };
  }

  // -- the cook's own version ---------------------------------------------- //
  private startEdit(r: Recipe): void {
    this.draft = {
      ingredients: r.ingredients.filter((i) => i.source !== "basic").map((i) => ({
        id: i.id, name: i.name, qty: i.qty, unit: i.unit, source: i.source as CustomIngredient["source"], group: i.group,
        ...(i.plant_id ? { plant_id: i.plant_id } : {}), ...(i.kind ? { kind: i.kind } : {}), ...(i.color ? { color: i.color } : {}),
      })),
      steps: [...r.steps],
    };
  }

  private editIngredient(n: number, change: Partial<CustomIngredient>): void {
    if (!this.draft) return;
    const ingredients = this.draft.ingredients.map((x, i) => {
      if (i !== n) return x;
      const next = { ...x, ...change };
      if ("name" in change && change.name !== x.name) delete next.id; // a renamed row is a new ingredient: the server names it
      return next;
    });
    this.draft = { ...this.draft, ingredients };
  }

  private editSteps(steps: string[]): void {
    if (this.draft) this.draft = { ...this.draft, steps };
  }

  private moveStep(n: number, by: number): void {
    if (!this.draft) return;
    const steps = [...this.draft.steps];
    const to = n + by;
    if (to < 0 || to >= steps.length) return;
    [steps[n], steps[to]] = [steps[to], steps[n]];
    this.editSteps(steps);
  }

  private async saveDraft(r: Recipe): Promise<void> {
    if (!this.draft) return;
    const ingredients = this.draft.ingredients.filter((i) => i.name.trim()).map((i) => ({ ...i, name: i.name.trim() }));
    const steps = this.draft.steps.map((x) => x.trim()).filter(Boolean);
    if (!ingredients.length || !steps.length) {
      this.error = this.t("cook.edit_need_both");
      return;
    }
    this.error = ""; // a message from an earlier try must not hide this save
    await this.updateRecipe(r, { ingredients, steps });
    if (!this.error) {
      this.draft = null;
      this.flash(this.t("cook.edit_saved"));
    }
  }

  private async resetCustom(r: Recipe): Promise<void> {
    if (!confirm(this.t("cook.edit_reset_confirm"))) return;
    await this.updateRecipe(r, { ingredients: [], steps: [] });
    this.draft = null;
  }

  private async pdf(kind: "recipe" | "book" | "shopping", recipes: Recipe[], print = false): Promise<void> {
    if (!recipes.length) return;
    this.busy = "pdf";
    // a popup must open in the click itself; it gets the PDF once it is made
    const win = print ? window.open("", "_blank") : null;
    try {
      const images: Record<string, string> = {};
      if (kind !== "shopping") {
        for (const r of recipes.slice(0, 40)) {
          const jpg = await dishJpeg(r.picture, r.id);
          if (jpg) images[r.id] = jpg;
        }
      }
      const res = await this.api.cookingPdf(kind, this.target(recipes), images, this.lang, kind === "book" ? this.t("cook.book_title") : undefined);
      const bytes = Uint8Array.from(atob(res.pdf), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
      if (win) {
        win.location.href = url;
      } else {
        const a = document.createElement("a");
        a.href = url;
        a.download = res.filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      win?.close();
      this.error = (err as Error).message;
    } finally {
      this.busy = "";
    }
  }

  private async send(what: "recipe" | "shopping", recipes: Recipe[]): Promise<void> {
    if (!recipes.length) return;
    this.busy = "send";
    try {
      const hooks = web();
      if (hooks?.mailSelf) {
        const { title, text } = await this.api.cookingSend(what, this.target(recipes), { dryRun: true, lang: this.lang });
        const res = await hooks.mailSelf(title, text);
        if (res.ok) this.flash(this.t("cook.mailed", { to: res.to ?? "" }));
        else this.error = res.error || this.t("cook.mail_failed");
      } else {
        await this.api.cookingSend(what, this.target(recipes), { service: this.notifyService || undefined, lang: this.lang });
        this.flash(this.t("cook.sent"));
      }
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.busy = "";
    }
  }

  private async toTodo(): Promise<void> {
    if (!this.todoEntity || !this.basketRecipes.length) return;
    this.busy = "todo";
    try {
      const res = await this.api.cookingToTodo(this.todoEntity, this.target(this.basketRecipes), this.lang);
      this.flash(this.t("cook.todo_added", { n: res.added, skipped: res.skipped }));
    } catch (err) {
      this.error = (err as Error).message;
    } finally {
      this.busy = "";
    }
  }

  private get todoLists(): string[] {
    return Object.keys(this.hass?.states ?? {}).filter((e) => e.startsWith("todo.")).sort();
  }

  private get notifyServices(): string[] {
    const notify = (this.hass?.services as Record<string, Record<string, unknown>> | undefined)?.notify ?? {};
    return Object.keys(notify).filter((s) => s !== "send_message" && s !== "persistent_notification").sort();
  }

  // -- render ---------------------------------------------------------------- //
  private produceIcon(p: { icon?: string; kind: string; color?: string }, size = 22): TemplateResult {
    const icon = p.icon && GLYPHS[p.icon] ? p.icon : KIND_GLYPH[p.kind] ?? "leafy";
    return glyphIcon(icon, p.color || "#4f8a34", size);
  }

  render(): TemplateResult {
    const book = this.data?.book ?? [];
    return html`
      ${this.readonly ? nothing : html`<div class="tabs" role="tablist">
        ${(["ideas", "book", "shopping"] as Section[]).map((s) => html`<button class="btn small ${this.section === s ? "primary" : "ghost"}" role="tab"
          aria-selected=${this.section === s} @click=${() => (this.section = s)}>${this.t(`cook.section.${s}`)}${s === "book" && book.length
            ? html` <span class="chip">${book.length}</span>` : s === "shopping" && this.basket.length ? html` <span class="chip">${this.basket.length}</span>` : nothing}</button>`)}
      </div>`}
      ${this.error ? html`<div class="banner err" role="alert">${this.error} <button class="btn small ghost" @click=${() => (this.error = "")}>${this.t("common.close")}</button></div>` : nothing}
      ${this.msg ? html`<div class="banner" role="status">${this.msg}</div>` : nothing}
      ${!this.data && this.busy ? html`<div class="card"><div class="skeleton" style="height:160px"></div></div>`
        : this.section === "ideas" ? this.renderIdeas() : this.section === "book" ? this.renderBook() : this.renderShopping()}
      ${this.open ? this.renderDetail(this.open) : nothing}
    `;
  }

  private renderIdeas(): TemplateResult {
    const d = this.data;
    if (!d) return html``;
    const ready = new Set(d.ready.map((p) => p.plant_id));
    const extra = this.produce.filter((id) => !ready.has(id)).map((id) => d.catalog.edible.find((e) => e.plant_id === id)).filter(Boolean) as CookingProduce[];
    return html`<div class="layout">
      <aside class="card stack">
        <h3>${this.t("cook.from_garden")}</h3>
        ${d.ready.length ? nothing : html`<p class="small muted">${this.t("cook.nothing_ready")}</p>`}
        <div class="pick">
          ${[...d.ready, ...extra].map((p) => html`<button aria-pressed=${this.produce.includes(p.plant_id)} @click=${() => this.toggleProduce(p.plant_id)}
            title=${p.until ? this.t("cook.until", { date: formatDate(p.until, this.lang) }) : ""}>${this.produceIcon(p)}${p.name}</button>`)}
        </div>
        <label class="small">${this.t("cook.add_produce")}
          <select @change=${(e: Event) => { const v = (e.target as HTMLSelectElement).value; (e.target as HTMLSelectElement).value = ""; if (v && !this.produce.includes(v)) this.toggleProduce(v); }}>
            <option value="">${this.t("cook.add_produce_hint")}</option>
            ${d.catalog.edible.filter((e) => !this.produce.includes(e.plant_id)).map((e) => html`<option value=${e.plant_id}>${e.name}</option>`)}
          </select>
        </label>

        <button class="btn small ghost more" aria-expanded=${this.moreOpen} @click=${() => (this.moreOpen = !this.moreOpen)}>
          ${this.moreOpen ? "▾" : "▸"} ${this.t("cook.more_choices", { n: this.prefs.servings })}</button>
        ${this.moreOpen ? this.renderChoices() : nothing}
      </aside>
      <section>
        <div class="toolbar">
          <span class="muted small">${this.busy === "load" ? this.t("cook.cooking_up") : this.t("cook.n_ideas", { n: d.recipes.length })}</span>
          <span class="spacer"></span>
          <button class="btn small ghost" ?disabled=${!d.recipes.length || !!this.busy} @click=${() => this.pdf("book", d.recipes)}>
            <ha-icon icon="mdi:book-open-variant"></ha-icon>${this.t("cook.pdf_ideas")}</button>
        </div>
        ${d.menus?.length ? this.renderMenus(d.menus) : nothing}
        ${d.recipes.length ? this.renderChapters(d.recipes)
          : html`<div class="card empty">${this.produce.length ? this.t("cook.no_ideas") : this.t("cook.pick_produce")}</div>`}
      </section>
    </div>`;
  }

  private renderChoices(): TemplateResult {
    const d = this.data!;
    return html`
        <h3>${this.t("cook.servings")}</h3>
        <div class="servings">
          <button class="icon-btn" aria-label="-" ?disabled=${this.prefs.servings <= 1} @click=${() => { this.prefs = { ...this.prefs, servings: this.prefs.servings - 1 }; this.refresh(); }}>−</button>
          <b>${this.prefs.servings}</b>
          <button class="icon-btn" aria-label="+" ?disabled=${this.prefs.servings >= 12} @click=${() => { this.prefs = { ...this.prefs, servings: this.prefs.servings + 1 }; this.refresh(); }}>+</button>
          <span class="small muted">${this.t("cook.persons")}</span>
        </div>

        <h3>${this.t("cook.side")}</h3>
        <div class="pick">
          ${[{ id: "", name: this.t("cook.side_auto") }, ...d.catalog.sides, { id: "none", name: this.t("cook.side_none") }].map((s) => html`<button class="text"
            aria-pressed=${this.prefs.side === s.id} @click=${() => { this.prefs = { ...this.prefs, side: s.id }; this.refresh(); }}>${s.name}</button>`)}
        </div>

        <h3>${this.t("cook.protein")}</h3>
        <p class="xs muted" style="margin:0">${this.t("cook.protein_hint")}</p>
        ${PROTEIN_GROUPS.map((g) => html`<div class="pick">${d.catalog.proteins.filter((p) => p.group === g).map((p) => html`<button class="text"
          aria-pressed=${this.prefs.proteins.includes(p.id)} @click=${() => this.toggle("proteins", p.id)}>${p.name}</button>`)}</div>`)}

        <h3>${this.t("cook.fridge")}</h3>
        <p class="xs muted" style="margin:0">${this.t("cook.fridge_hint")}</p>
        <div class="pick">${d.catalog.pantry.filter((p) => p.fridge !== false).map((p) => html`<button class="text" aria-pressed=${this.prefs.use.includes(p.id)}
          @click=${() => this.toggle("use", p.id)}>${p.name}</button>`)}</div>

        <button class="btn small ghost" aria-expanded=${this.showPantry} @click=${() => (this.showPantry = !this.showPantry)}>${this.t("cook.in_house")} (${this.prefs.pantry.length})</button>
        ${this.showPantry ? html`<p class="xs muted" style="margin:0">${this.t("cook.in_house_hint")}</p>
          <div class="pick">${[...d.catalog.sides, ...d.catalog.pantry].map((p) => html`<button class="text" aria-pressed=${this.prefs.pantry.includes(p.id)}
            @click=${() => this.toggle("pantry", p.id)}>${p.name}</button>`)}</div>` : nothing}
        <button class="btn small" @click=${() => this.savePrefs()}>${this.t("cook.save_prefs")}</button>
    `;
  }

  /** Complete menus: a soup or starter, a main course and a dessert that belong together. */
  private renderMenus(menus: CookingMenu[]): TemplateResult {
    return html`<section class="chapter menus" aria-label=${this.t("cook.menus")}>
      <h3 class="chapter-title">${this.t("cook.menus")} <span class="xs muted">${menus.length}</span></h3>
      <p class="xs muted" style="margin:0 0 var(--hl-s2)">${this.t("cook.menus_hint")}</p>
      <div class="grid menu-grid">${menus.map((m) => this.renderMenu(m))}</div></section>`;
  }

  private renderMenu(m: CookingMenu): TemplateResult {
    const recipes = m.courses.map((c) => c.recipe);
    const onList = recipes.every((r) => this.inBasket(r));
    return html`<article class="card menu" aria-label=${m.title}>
      <h4>${m.title}</h4>
      <span class="xs muted">${this.t("cook.minutes", { n: m.minutes })} · ${this.t("cook.n_persons", { n: m.servings })}</span>
      <ol class="menu-courses">${m.courses.map((c) => html`<li>
        <span class="xs muted">${this.t(`cook.course.${c.course}`)}</span>
        <button class="linklike" @click=${() => this.openRecipe(c.recipe, recipes)}>${c.recipe.title}</button></li>`)}</ol>
      <div class="actions">
        <button class="btn small ${onList ? "ghost" : ""}" @click=${() => this.menuToList(recipes, onList)}>
          ${onList ? this.t("cook.menu_off_list") : this.t("cook.menu_to_list")}</button>
        ${this.readonly ? nothing : html`<button class="btn small ghost" @click=${() => this.menuToBook(recipes)}>${this.t("cook.menu_to_book")}</button>`}
      </div></article>`;
  }

  /** All the dishes of a menu on the shopping list at once (or all off it). */
  private menuToList(recipes: Recipe[], off: boolean): void {
    for (const r of recipes) if (this.inBasket(r) === off) this.toggleBasket(r);
  }

  private async menuToBook(recipes: Recipe[]): Promise<void> {
    for (const r of recipes) if (!this.isSaved(r)) await this.save(r);
  }

  /** Recipes under their chapter headings: soups, starters, main courses, desserts, preserving. */
  private renderChapters(list: Recipe[]): TemplateResult {
    const ordered = COURSES.flatMap((c) => list.filter((r) => (r.course ?? "main") === c));
    return html`${COURSES.map((c) => {
      const rows = ordered.filter((r) => (r.course ?? "main") === c);
      return rows.length ? html`<section class="chapter" aria-label=${this.t(`cook.course.${c}`)}>
        <h3 class="chapter-title">${this.t(`cook.course.${c}`)} <span class="xs muted">${rows.length}</span></h3>
        <div class="grid">${rows.map((r) => this.renderCard(r, ordered))}</div></section>` : nothing;
    })}`;
  }

  private renderCard(r: Recipe, list: Recipe[]): TemplateResult {
    const saved = this.isSaved(r);
    return html`<button class="recipe" @click=${() => this.openRecipe(r, list)} aria-label=${r.title}>
      <img src=${dishDataUrl(r.picture, r.id)} alt="" loading="lazy" />
      <span class="body">
        <span class="title">${saved?.favorite ? html`<span class="star" aria-label=${this.t("cook.favorite")}>★</span> ` : nothing}${r.title}</span>
        ${r.subtitle ? html`<span class="sub">${r.subtitle}</span>` : nothing}
        <span class="meta"><span>⏱ ${this.t("cook.minutes", { n: r.minutes })}</span><span>· ${r.technique_name}</span>
          ${saved?.shared ? html`<span class="chip ok">${this.t("cook.shared")}</span>` : nothing}
          ${this.inBasket(r) ? html`<span class="chip">🛒</span>` : nothing}</span>
        <span class="xs muted">${this.t("cook.garden_share", { n: Math.round(r.garden_share * 100) })}</span>
        <span class="share"><i style=${`width:${Math.round(r.garden_share * 100)}%`}></i></span>
      </span>
    </button>`;
  }

  private renderDetail(r: Recipe): TemplateResult {
    const d = this.data;
    const saved = this.isSaved(r);
    const list = this.openList;
    const i = list.findIndex((x) => x.id === r.id);
    const ro = this.readonly;
    return html`<hl-modal heading=${r.title} subheading=${[r.subtitle, r.technique_name].filter(Boolean).join(" · ")} size="wide"
      nav ?has-prev=${i > 0} ?has-next=${i >= 0 && i < list.length - 1}
      closeLabel=${this.t("common.close")} prevLabel=${this.t("common.previous")} nextLabel=${this.t("common.next")}
      @prev=${() => { this.draft = null; this.open = list[i - 1]; }} @next=${() => { this.draft = null; this.open = list[i + 1]; }}
      @closed=${(e: Event) => { e.stopPropagation(); this.open = null; this.draft = null; }}>
      <div class="detail">
        <div class="stack">
          <img class="big" src=${dishDataUrl(r.picture, r.id)} alt=${this.t("cook.picture_alt", { title: r.title })} />
          <div class="meta small muted">⏱ ${this.t("cook.minutes", { n: r.minutes })} · ${this.t("cook.n_persons", { n: r.servings })} · ${r.tag_names.join(" · ")}</div>
          ${r.custom ? html`<p class="small"><span class="chip ok">${this.t("cook.custom")}</span> <span class="muted">${this.t("cook.custom_hint")}</span></p>
            ${ro || this.draft ? nothing : html`<button class="btn small ghost" @click=${() => this.resetCustom(r)}>↺ ${this.t("cook.edit_reset")}</button>`}` : nothing}
          ${ro || !d || r.custom || this.draft ? nothing : html`<div class="switch">
            <label for="side">${this.t("cook.side")}</label>
            <select id="side" @change=${(e: Event) => this.changeSpec({ side: (e.target as HTMLSelectElement).value })}>
              <option value="" ?selected=${!r.spec.side}>${this.t("cook.side_none")}</option>
              ${d.catalog.sides.map((s) => html`<option value=${s.id} ?selected=${r.spec.side === s.id}>${s.name}</option>`)}
            </select>
            <label for="protein">${this.t("cook.protein_one")}</label>
            <select id="protein" @change=${(e: Event) => this.changeSpec({ protein: (e.target as HTMLSelectElement).value })}>
              <option value="" ?selected=${!r.spec.protein}>${this.t("cook.veggie")}</option>
              ${PROTEIN_GROUPS.map((g) => html`<optgroup label=${this.t(`cook.group.${g}`)}>${d.catalog.proteins.filter((p) => p.group === g)
                .map((p) => html`<option value=${p.id} ?selected=${r.spec.protein === p.id}>${p.name}</option>`)}</optgroup>`)}
            </select>
            <label>${this.t("cook.servings")}</label>
            <span class="servings">
              <button class="icon-btn" aria-label="-" ?disabled=${r.servings <= 1} @click=${() => this.changeSpec({ servings: r.servings - 1 })}>−</button>
              <b>${r.servings}</b>
              <button class="icon-btn" aria-label="+" ?disabled=${r.servings >= 12} @click=${() => this.changeSpec({ servings: r.servings + 1 })}>+</button>
            </span>
          </div>`}
          ${saved?.cooked?.length ? html`<p class="xs muted">${this.t("cook.cooked_on", { dates: saved.cooked.slice(-3).map((c) => formatDate(c, this.lang)).join(", ") })}</p>` : nothing}
        </div>
        ${this.draft ? this.renderEditor(this.draft) : html`<div class="stack">
          <h3>${this.t("cook.ingredients")}</h3>
          <ul class="ingr">
            ${r.ingredients.filter((x) => x.source !== "basic").map((x) => html`<li>
              ${x.source === "garden" ? this.produceIcon({ icon: r.picture.produce.find((p) => p.plant_id === x.id)?.icon, kind: x.kind ?? "leafy", color: x.color }, 20)
                : html`<span class="dot" style="background:var(--hl-border)"></span>`}
              <span>${x.name} <span class="src ${x.source}">${this.t(`cook.src.${x.source}`)}</span></span>
              <span class="q">${x.label}</span></li>`)}
          </ul>
          <p class="xs muted">${this.t("cook.basics")}: ${r.ingredients.filter((x) => x.source === "basic").map((x) => x.name).join(", ")}</p>
          <h3>${this.t("cook.method")}</h3>
          <ol class="steps">${r.steps.map((s) => html`<li>${s}</li>`)}</ol>
          ${saved && !ro ? html`<label class="small">${this.t("cook.note")}
            <textarea class="note" .value=${saved.note ?? ""} @change=${(e: Event) => this.updateRecipe(r, { note: (e.target as HTMLTextAreaElement).value })}></textarea></label>`
            : saved?.note ? html`<p class="small"><b>${this.t("cook.note")}:</b> ${saved.note}</p>` : nothing}
        </div>`}
      </div>
      <div slot="actions" class="actions">
        ${this.draft ? html`
          <button class="btn small primary" @click=${() => this.saveDraft(r)}><ha-icon icon="mdi:content-save-outline"></ha-icon>${this.t("cook.edit_save")}</button>
          <button class="btn small ghost" @click=${() => (this.draft = null)}>${this.t("common.cancel")}</button>` : ro ? nothing : html`
          <button class="btn small ghost" @click=${() => this.startEdit(r)}><ha-icon icon="mdi:pencil-outline"></ha-icon>${this.t("cook.edit")}</button>`}
        ${ro || this.draft ? nothing : html`
          <button class="btn small ${saved ? "ghost" : "primary"}" @click=${() => (saved ? this.removeRecipe(r) : this.save(r))}>
            <ha-icon icon=${saved ? "mdi:bookmark-remove-outline" : "mdi:bookmark-plus-outline"}></ha-icon>${saved ? this.t("cook.unsave") : this.t("cook.save")}</button>
          <button class="btn small ghost" aria-pressed=${!!saved?.favorite} @click=${() => this.updateRecipe(r, { favorite: !saved?.favorite })}>
            ${saved?.favorite ? "★" : "☆"} ${this.t("cook.favorite")}</button>
          ${this.web ? html`<button class="btn small ghost" aria-pressed=${!!saved?.shared} title=${this.t("cook.share_hint")}
            @click=${() => this.updateRecipe(r, { shared: !saved?.shared })}><ha-icon icon=${saved?.shared ? "mdi:eye" : "mdi:eye-off-outline"}></ha-icon>${saved?.shared ? this.t("cook.shared") : this.t("cook.share")}</button>` : nothing}
          ${saved ? html`<button class="btn small ghost" @click=${() => this.updateRecipe(r, { cooked: true })}>🍽 ${this.t("cook.cooked")}</button>` : nothing}
          <button class="btn small ghost" @click=${() => this.toggleBasket(r)}>🛒 ${this.inBasket(r) ? this.t("cook.off_list") : this.t("cook.on_list")}</button>`}
        ${this.draft ? nothing : html`<button class="btn small ghost" ?disabled=${!!this.busy} @click=${() => this.pdf("recipe", [r])}><ha-icon icon="mdi:file-pdf-box"></ha-icon>PDF</button>
        <button class="btn small ghost" ?disabled=${!!this.busy} @click=${() => this.pdf("recipe", [r], true)}><ha-icon icon="mdi:printer-outline"></ha-icon>${this.t("cook.print")}</button>`}
        ${ro || this.draft ? nothing : html`<button class="btn small ghost" ?disabled=${!!this.busy} @click=${() => this.send("recipe", [r])}>
          <ha-icon icon=${web()?.mailSelf ? "mdi:email-outline" : "mdi:cellphone-message"}></ha-icon>${web()?.mailSelf ? this.t("cook.mail_me") : this.t("cook.to_phone")}</button>`}
      </div>
    </hl-modal>`;
  }

  private renderEditor(draft: Draft): TemplateResult {
    const blank: CustomIngredient = { name: "", qty: 0, unit: "g", source: "shop" };
    return html`<div class="stack editor">
      <p class="xs muted" style="margin:0">${this.t("cook.edit_hint")}</p>
      <h3>${this.t("cook.ingredients")}</h3>
      ${draft.ingredients.map((x, n) => html`<div class="ed-ingr">
        <input type="text" aria-label=${this.t("cook.edit_name")} placeholder=${this.t("cook.edit_name")} .value=${x.name} maxlength="80"
          @input=${(e: Event) => this.editIngredient(n, { name: (e.target as HTMLInputElement).value })} />
        <input type="number" min="0" step="any" aria-label=${this.t("cook.edit_qty")} .value=${x.qty ? String(x.qty) : ""}
          @input=${(e: Event) => this.editIngredient(n, { qty: Number((e.target as HTMLInputElement).value) || 0 })} />
        <select aria-label=${this.t("cook.edit_unit")} @change=${(e: Event) => this.editIngredient(n, { unit: (e.target as HTMLSelectElement).value })}>
          ${UNITS.map((u) => html`<option value=${u} ?selected=${x.unit === u}>${this.t(`cook.unit.${u}`)}</option>`)}
        </select>
        <select aria-label=${this.t("cook.edit_source")} @change=${(e: Event) => this.editIngredient(n, { source: (e.target as HTMLSelectElement).value as CustomIngredient["source"] })}>
          ${SOURCES.map((src) => html`<option value=${src} ?selected=${x.source === src}>${this.t(`cook.src.${src}`)}</option>`)}
        </select>
        <button class="icon-btn" aria-label=${this.t("cook.edit_remove")} title=${this.t("cook.edit_remove")}
          @click=${() => this.draft && (this.draft = { ...this.draft, ingredients: this.draft.ingredients.filter((_, i) => i !== n) })}>✕</button>
      </div>`)}
      <button class="btn small ghost" ?disabled=${draft.ingredients.length >= MAX_INGREDIENTS} @click=${() => this.draft && (this.draft = { ...this.draft, ingredients: [...this.draft.ingredients, { ...blank }] })}>
        + ${this.t("cook.edit_add_ingredient")}</button>
      <h3>${this.t("cook.method")}</h3>
      ${draft.steps.map((step, n) => html`<div class="ed-step">
        <span class="num">${n + 1}</span>
        <textarea aria-label=${this.t("cook.edit_step", { n: n + 1 })} .value=${step} maxlength="600"
          @input=${(e: Event) => this.editSteps(draft.steps.map((x, i) => (i === n ? (e.target as HTMLTextAreaElement).value : x)))}></textarea>
        <span class="tools">
          <button class="icon-btn" aria-label=${this.t("cook.edit_up")} ?disabled=${n === 0} @click=${() => this.moveStep(n, -1)}>↑</button>
          <button class="icon-btn" aria-label=${this.t("cook.edit_down")} ?disabled=${n === draft.steps.length - 1} @click=${() => this.moveStep(n, 1)}>↓</button>
          <button class="icon-btn" aria-label=${this.t("cook.edit_remove")} @click=${() => this.editSteps(draft.steps.filter((_, i) => i !== n))}>✕</button>
        </span>
      </div>`)}
      <button class="btn small ghost" ?disabled=${draft.steps.length >= MAX_STEPS} @click=${() => this.editSteps([...draft.steps, ""])}>+ ${this.t("cook.edit_add_step")}</button>
    </div>`;
  }

  private renderBook(): TemplateResult {
    const all = this.data?.book ?? [];
    const q = this.bookSearch.trim().toLowerCase();
    const list = all.filter((r) => (this.bookFilter === "favorite" ? r.favorite : this.bookFilter === "shared" ? r.shared : true))
      .filter((r) => !this.bookCourse || (r.course ?? "main") === this.bookCourse)
      .filter((r) => !q || `${r.title} ${r.subtitle} ${r.ingredients.map((i) => i.name).join(" ")}`.toLowerCase().includes(q));
    return html`
      ${this.readonly ? html`<p class="muted">${this.t("cook.visitor_intro")}</p>` : nothing}
      <div class="toolbar">
        <input type="search" placeholder=${this.t("cook.search")} aria-label=${this.t("cook.search")} .value=${this.bookSearch}
          @input=${(e: Event) => (this.bookSearch = (e.target as HTMLInputElement).value)} />
        ${this.readonly ? nothing : (["all", "favorite", "shared"] as BookFilter[]).filter((f) => f !== "shared" || this.web)
          .map((f) => html`<button class="btn small ${this.bookFilter === f ? "primary" : "ghost"}" @click=${() => (this.bookFilter = f)}>${this.t(`cook.filter.${f}`)}</button>`)}
        <button class="btn small ghost" ?disabled=${!list.length || !!this.busy} @click=${() => this.pdf("book", list)}>
          <ha-icon icon="mdi:book-open-variant"></ha-icon>${this.t("cook.pdf_book")}</button>
      </div>
      <div class="toolbar chapters" role="group" aria-label=${this.t("cook.chapters")}>
        ${(["", ...COURSES] as (Course | "")[]).filter((c) => !c || all.some((r) => (r.course ?? "main") === c)).map((c) => html`<button
          class="btn small ${this.bookCourse === c ? "primary" : "ghost"}" aria-pressed=${this.bookCourse === c}
          @click=${() => (this.bookCourse = c)}>${c ? this.t(`cook.course.${c}`) : this.t("cook.course.all")}</button>`)}
      </div>
      ${list.length ? this.renderChapters(list)
        : html`<div class="card empty">${this.readonly ? this.t("cook.visitor_empty") : all.length ? this.t("cook.book_none_found") : this.t("cook.book_empty")}</div>`}`;
  }

  private renderShopping(): TemplateResult {
    const rows = this.shoppingRows();
    const recipes = this.basketRecipes;
    const hooks = web();
    return html`<div class="layout">
      <section class="card stack">
        <h3>${this.t("cook.dishes")}</h3>
        ${recipes.length ? recipes.map((r) => html`<div class="basket-item">
          <img src=${dishDataUrl(r.picture, r.id)} alt="" />
          <span><b>${r.title}</b><br /><span class="xs muted">${this.t("cook.n_persons", { n: r.servings })}</span></span>
          <button class="icon-btn" aria-label=${this.t("cook.off_list")} @click=${() => this.toggleBasket(r)}>✕</button></div>`)
          : html`<p class="muted">${this.t("cook.list_empty")}</p>`}
        ${recipes.length ? html`<button class="btn small ghost" @click=${() => { this.basket = []; this.basketRecipes = []; this.storeBasket(); }}>${this.t("cook.clear_list")}</button>` : nothing}
      </section>
      <section class="card stack">
        <h3>${this.t("cook.to_buy")}</h3>
        ${rows.buy.length ? html`<table><tbody>${rows.buy.map((r) => html`<tr><td><input type="checkbox" aria-label=${r.name} /></td><td>${r.name}</td><td class="num">${r.label}</td></tr>`)}</tbody></table>`
          : html`<p class="muted small">${recipes.length ? this.t("cook.nothing_to_buy") : this.t("cook.list_empty")}</p>`}
        ${rows.garden.length ? html`<h3>${this.t("cook.from_garden_list")}</h3>
          <p class="small muted">${rows.garden.map((g) => `${g.name} (${Math.round(g.qty)} g)`).join(" · ")}</p>` : nothing}
        <div class="actions">
          <button class="btn small primary" ?disabled=${!recipes.length || !!this.busy} @click=${() => this.pdf("shopping", recipes, true)}>
            <ha-icon icon="mdi:printer-outline"></ha-icon>${this.t("cook.print_list")}</button>
          <button class="btn small ghost" ?disabled=${!recipes.length || !!this.busy} @click=${() => this.pdf("shopping", recipes)}>
            <ha-icon icon="mdi:file-pdf-box"></ha-icon>PDF</button>
          <button class="btn small ghost" ?disabled=${!recipes.length || !!this.busy} @click=${() => this.pdf("book", recipes)}>
            <ha-icon icon="mdi:book-open-variant"></ha-icon>${this.t("cook.pdf_with_recipes")}</button>
          <button class="btn small ghost" ?disabled=${!recipes.length || !!this.busy} @click=${() => this.send("shopping", recipes)}>
            <ha-icon icon=${hooks?.mailSelf ? "mdi:email-outline" : "mdi:cellphone-message"}></ha-icon>${hooks?.mailSelf ? this.t("cook.mail_me") : this.t("cook.to_phone")}</button>
        </div>
        ${!hooks?.mailSelf && this.notifyServices.length ? html`<label class="small">${this.t("cook.notify_via")}
          <select @change=${(e: Event) => (this.notifyService = (e.target as HTMLSelectElement).value)}>
            <option value="">${this.t("cook.notify_default")}</option>
            ${this.notifyServices.map((s) => html`<option value=${`notify.${s}`} ?selected=${this.notifyService === `notify.${s}`}>${s}</option>`)}
          </select></label>` : nothing}
        ${!hooks?.mailSelf && this.todoLists.length ? html`<div class="row wrap">
          <select aria-label=${this.t("cook.todo_list")} @change=${(e: Event) => (this.todoEntity = (e.target as HTMLSelectElement).value)}>
            <option value="">${this.t("cook.todo_list")}</option>
            ${this.todoLists.map((e) => html`<option value=${e} ?selected=${this.todoEntity === e}>${String(this.hass?.states[e]?.attributes?.friendly_name ?? e)}</option>`)}
          </select>
          <button class="btn small ghost" ?disabled=${!this.todoEntity || !recipes.length || !!this.busy} @click=${() => this.toTodo()}>${this.t("cook.to_todo")}</button>
        </div>` : nothing}
      </section>
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-cooking-view": CookingView;
  }
}
