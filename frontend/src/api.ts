// Thin, typed wrapper around the garden_manager websocket commands.
import type {
  ClimateStats,
  CookingOverview,
  CookingPrefs,
  Recipe,
  RecipeSpec,
  CustomIngredient,
  RecipeTarget,
  Expense,
  AdviceResult,
  HarvestEntry,
  JournalEntry,
  RecordsOverview,
  SeedPacket,
  SoilTest,
  QaAnswer,
  QaOptions,
  Supplies,
  AutofillResult,
  CompatibilityReport,
  GlossaryEntry,
  HandbookChapterMeta,
  IrrigationPlan,
  PrintOptions,
  Resources,
  FamilyInfo,
  HomeAssistant,
  Plant,
  PlanDoc,
  Planting,
  Bed,
  Settings,
  Snapshot,
  SyslogPage,
  AnalysisIssue,
  AnalysisResult,
  PlanComparison,
  PlanRef,
  ValveTest,
  ExplainResult,
  TransitionPreview,
  TransitionResult,
  UndoResult,
  PhotoDiagnosis,
} from "./types";
import type { CropRow } from "./views/crops-view";

const D = "garden_manager";

export class GardenApi {
  /** The garden (config entry) this panel shows; "" = the first one. */
  gardenId = "";

  constructor(private hass: HomeAssistant) {}

  setHass(hass: HomeAssistant): void {
    this.hass = hass;
  }

  private call<T>(type: string, payload: Record<string, unknown> = {}): Promise<T> {
    const garden = this.gardenId ? { garden_id: this.gardenId } : {};
    return this.hass.connection.sendMessagePromise<T>({ type: `${D}/${type}`, ...garden, ...payload });
  }

  subscribe(cb: (snapshot: Snapshot) => void): Promise<() => Promise<void>> {
    return this.hass.connection.subscribeMessage<Snapshot>(cb, { type: `${D}/subscribe`, ...(this.gardenId ? { garden_id: this.gardenId } : {}) });
  }

  plants(): Promise<{ plants: Plant[]; families: Record<string, FamilyInfo>; overrides: Record<string, unknown> }> {
    return this.call("plants");
  }

  savePlant(plant: Partial<Plant> & { id: string }, mode: "custom" | "override"): Promise<{ plant: Plant }> {
    return this.call("plants/save", { plant, mode });
  }

  deletePlant(plantId: string): Promise<void> {
    return this.call("plants/delete", { plant_id: plantId });
  }

  plantWindows(plantId: string, zoneId?: string | null, season?: number) {
    return this.call<{
      season: number;
      windows: Record<"indoor_sow" | "direct_sow" | "transplant", { start: string; end: string }[]> & {
        extension_weeks: number;
        greenhouse_ok: boolean;
      };
      companions: { plant_id: string; strength: number }[];
      enemies: string[];
    }>("plants/windows", { plant_id: plantId, zone_id: zoneId ?? null, season: season ?? null });
  }

  /** ``gardenId``: the garden the draft was made for (a pending save must not land in another one). */
  savePlan(doc: PlanDoc, baseRevision: number | null, season?: number, gardenId?: string): Promise<{ revision: number }> {
    return this.call("plan/save", {
      ...doc, base_revision: baseRevision, ...(season != null ? { season } : {}), ...(gardenId ? { garden_id: gardenId } : {}),
    });
  }

  yearPreview(fromSeason?: number): Promise<TransitionPreview> {
    return this.call("year/preview", fromSeason != null ? { from_season: fromSeason } : {});
  }

  yearApply(opts: {
    from_season: number; layout: "copy" | "keep"; zone_ids?: string[] | null; feature_ids?: string[] | null;
    planting_ids: string[]; activate: boolean;
  }): Promise<TransitionResult> {
    return this.call("year/apply", opts);
  }

  deleteLayout(season: number): Promise<void> {
    return this.call("layout/delete", { season });
  }

  syslog(opts: { limit?: number; before?: string | null; include_system?: boolean } = {}): Promise<SyslogPage> {
    return this.call("syslog/list", opts);
  }

  undo(entryId: string, force = false): Promise<UndoResult> {
    return this.call("syslog/undo", { entry_id: entryId, force });
  }

  checkBed(bed: Bed, plantings: Planting[]): Promise<CompatibilityReport> {
    return this.call("plan/check", { bed, plantings });
  }

  succession(planting: Planting, count: number, intervalDays: number | null, placement: "split" | "stack") {
    return this.call<{ plantings: Planting[]; dropped: number }>("plan/succession", {
      planting,
      count,
      interval_days: intervalDays,
      placement,
    });
  }

  exportPlan(format: "json" | "yaml", includeTasks = false): Promise<{ filename: string; content: string }> {
    return this.call("plan/export", { format, include_tasks: includeTasks });
  }

  importPlan(content: string, mode: "merge" | "replace") {
    return this.call<{ counts: Record<string, number>; revision: number }>("plan/import", { content, mode });
  }

  addTask(task: {
    title: string;
    due?: string | null;
    task_type?: string;
    description?: string;
    priority?: string;
    estimated_minutes?: number | null;
    bed_id?: string | null;
    recurrence_days?: number | null;
  }): Promise<{ task_id: string }> {
    return this.call("tasks/add", task);
  }

  taskAction(
    taskId: string,
    action: "complete" | "skip" | "postpone" | "update" | "delete" | "reopen",
    extra: { note?: string; photos?: string[]; days?: number; to?: string; cascade?: boolean; changes?: Record<string, unknown> } = {},
  ): Promise<{ next_task_id?: string | null; shifted?: string[]; warnings?: string[] }> {
    return this.call("tasks/action", { task_id: taskId, action, ...extra });
  }

  resetWaterFactor(bedId: string): Promise<{ ok: boolean }> {
    return this.call("bed/reset_water_factor", { bed_id: bedId });
  }

  saveSettings(settings: Partial<Settings> | Record<string, unknown>): Promise<{ settings: Settings }> {
    return this.call("settings/save", { settings });
  }

  // -- autofill ----------------------------------------------------------- //
  autofill(opts: { season?: number; bed_ids?: string[]; replace?: boolean; resources?: Partial<Resources>; max_crops?: number }): Promise<AutofillResult> {
    return this.call("plan/autofill", opts);
  }

  autofillApply(plantings: Planting[], replaceBeds: string[], baseRevision: number | null, planFrom?: number | null): Promise<{ revision: number }> {
    return this.call("plan/autofill/apply", { plantings, replace_beds: replaceBeds, base_revision: baseRevision, ...(planFrom != null ? { plan_from: planFrom } : {}) });
  }

  newPlan(season: number, start: "empty" | "zones" | "zones_beds", oldName?: string): Promise<{ archived: string; name: string; plantings: number; revision: number }> {
    return this.call("plan/new", { season, start, ...(oldName ? { old_name: oldName } : {}) });
  }

  activatePlan(planId: string, oldName?: string): Promise<{ season: number; archived: string; revision: number }> {
    return this.call("plan/activate", { plan_id: planId, ...(oldName ? { old_name: oldName } : {}) });
  }

  deletePlan(planId: string): Promise<void> {
    return this.call("plan/delete", { plan_id: planId });
  }

  plantingsSeason(season: number): Promise<{ season: number; rows: CropRow[] }> {
    return this.call("plantings/season", { season });
  }

  updatePlanting(plantingId: string, changes: Partial<Planting>): Promise<{ planting: Planting; row: CropRow | null; revision: number }> {
    return this.call("planting/update", { planting_id: plantingId, changes });
  }

  updatePlantings(plantingIds: string[], changes: Partial<Planting>): Promise<{ updated: number; revision: number }> {
    return this.call("plantings/update_many", { planting_ids: plantingIds, changes });
  }

  fixIssue(issue: AnalysisIssue): Promise<Record<string, unknown>> {
    return this.call("analysis/fix", { code: issue.code, params: issue.params, refs: issue.refs });
  }

  comparePlans(a: PlanRef, b: PlanRef): Promise<PlanComparison> {
    return this.call("plan/compare", { a, b });
  }

  /** What the weather did: series, periods compared with last year, months, frost dates, every temperature sensor. */
  climateStats(days = 400): Promise<ClimateStats> {
    return this.call("climate/stats", { days });
  }

  importStationCsv(text: string): Promise<{ days: number; first: string | null; last: string | null; rows: number; columns: Record<string, string>; changed: boolean }> {
    return this.call("climate/import_csv", { text });
  }

  applyLocalFrost(): Promise<{ settings: unknown }> {
    return this.call("climate/apply_local_frost");
  }

  seasonReport(season: number): Promise<unknown> {
    return this.call("report/season", { season });
  }

  /** Seeds to buy, what can follow a crop, expected harvest per week. */
  planning(season: number): Promise<unknown> {
    return this.call("planning", { season });
  }

  stillPossible(season: number): Promise<{ season: number; plants: { plant_id: string; beds: string[] }[] }> {
    return this.call("analysis/still_possible", { season });
  }

  analysis(): Promise<AnalysisResult> {
    return this.call("analysis");
  }

  explain(plantId: string, season?: number, matchZone = true): Promise<ExplainResult> {
    return this.call("analysis/explain", { plant_id: plantId, season: season ?? null, match_zone: matchZone });
  }

  // -- seeds to a to-do list ------------------------------------------------ //
  /** Home Assistant to-do lists (Hortulus' own week list left out). */
  todoLists(): { entity_id: string; name: string }[] {
    return Object.values(this.hass.states)
      .filter((s) => s.entity_id.startsWith("todo.") && !s.entity_id.startsWith("todo.hortulus"))
      .map((s) => ({ entity_id: s.entity_id, name: String(s.attributes.friendly_name ?? s.entity_id) }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  seedsToTodo(season: number, entityId: string): Promise<{ added: number; skipped: number }> {
    return this.call("seeds/to_todo", { season, entity_id: entityId });
  }

  // -- print --------------------------------------------------------------- //
  printPreview(options: Partial<PrintOptions>): Promise<{ pages: string[] }> {
    return this.call("print/render", { options });
  }

  /** Download the PDF through the authenticated HTTP view. */
  async printPdf(options: Partial<PrintOptions>): Promise<{ blob: Blob; filename: string }> {
    const query = new URLSearchParams();
    if (this.gardenId) query.set("garden_id", this.gardenId);
    for (const [key, value] of Object.entries(options)) {
      if (value === null || value === undefined || value === "") continue;
      query.set(key, Array.isArray(value) ? value.join(",") : String(value));
    }
    const resp = await this.hass.fetchWithAuth(`/api/${D}/print?${query.toString()}`);
    if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
    const disposition = resp.headers.get("Content-Disposition") ?? "";
    const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "hortulus.pdf";
    return { blob: await resp.blob(), filename };
  }

  exportPdfToConfig(options: Partial<PrintOptions>): Promise<unknown> {
    return this.hass.callService(D, "export_pdf", { ...(options as Record<string, unknown>), ...(this.gardenId ? { garden: this.gardenId } : {}) });
  }

  // -- handbook ------------------------------------------------------------ //
  handbookIndex(lang?: string): Promise<{ chapters: HandbookChapterMeta[]; glossary: Record<string, GlossaryEntry> }> {
    return this.call("handbook/index", lang ? { lang } : {});
  }

  handbookChapter(chapterId: string, lang?: string): Promise<HandbookChapterMeta & { body: string }> {
    return this.call("handbook/chapter", { chapter_id: chapterId, ...(lang ? { lang } : {}) });
  }

  handbookSearch(query: string, lang?: string): Promise<{ results: { id: string; title: string; snippet: string; score: number }[] }> {
    return this.call("handbook/search", { query, ...(lang ? { lang } : {}) });
  }

  // -- irrigation ---------------------------------------------------------- //
  irrigationPlan(): Promise<IrrigationPlan> {
    return this.call("irrigation/plan");
  }

  irrigationRun(bedIds?: string[], amountMm?: number): Promise<IrrigationPlan & { started: boolean }> {
    return this.call("irrigation/run", { ...(bedIds ? { bed_ids: bedIds } : {}), ...(amountMm ? { amount_mm: amountMm } : {}) });
  }

  irrigationStop(): Promise<void> {
    return this.call("irrigation/stop");
  }

  /** Open a valve for a few seconds and check it reports open and closed. */
  irrigationTest(entityId: string, seconds = 5, withPump = true): Promise<ValveTest> {
    return this.call("irrigation/test", { entity_id: entityId, seconds, with_pump: withPump });
  }

  irrigationClose(entityId: string): Promise<{ state: string | null }> {
    return this.call("irrigation/close", { entity_id: entityId });
  }

  /** Home Assistant's recorder: states of a few entities over a period (minimal form). */
  async history(entityIds: string[], start: Date, end = new Date()): Promise<Record<string, { s: string; lu: number }[]>> {
    if (!entityIds.length) return {};
    return this.hass.connection.sendMessagePromise({
      type: "history/history_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: entityIds,
      minimal_response: true,
      no_attributes: true,
      significant_changes_only: false,
    });
  }

  // -- advice, Q&A, supplies ------------------------------------------------ //
  advice(): Promise<AdviceResult> {
    return this.call("advice");
  }

  qaOptions(): Promise<QaOptions> {
    return this.call("qa/options");
  }

  qaAsk(subject: string, problem: string, target: string | null): Promise<QaAnswer> {
    return this.call("qa/ask", { subject, problem, target });
  }

  supplies(): Promise<Supplies> {
    return this.call("supplies");
  }

  // -- kitchen ------------------------------------------------------------- //
  cookingSuggest(opts: { prefs?: CookingPrefs; produce?: string[]; limit?: number; lang?: string } = {}): Promise<CookingOverview> {
    return this.call("cooking/suggest", opts as Record<string, unknown>);
  }

  cookingRender(spec: RecipeSpec, lang?: string, pantry?: string[]): Promise<{ recipe: Recipe; saved: boolean }> {
    return this.call("cooking/render", { spec, ...(lang ? { lang } : {}), ...(pantry ? { pantry } : {}) });
  }

  cookbookSave(recipe: { spec: RecipeSpec; favorite?: boolean; shared?: boolean; title?: string; note?: string; ingredients?: CustomIngredient[]; steps?: string[] }, lang?: string, pantry?: string[]): Promise<{ id: string; book: Recipe[] }> {
    return this.call("cooking/book/save", { recipe, ...(lang ? { lang } : {}), ...(pantry ? { pantry } : {}) });
  }

  cookbookUpdate(recipeId: string, changes: Record<string, unknown>, lang?: string, pantry?: string[]): Promise<{ id: string; book: Recipe[] }> {
    return this.call("cooking/book/update", { recipe_id: recipeId, changes, ...(lang ? { lang } : {}), ...(pantry ? { pantry } : {}) });
  }

  cookbookDelete(recipeId: string, lang?: string, pantry?: string[]): Promise<{ book: Recipe[] }> {
    return this.call("cooking/book/delete", { recipe_id: recipeId, ...(lang ? { lang } : {}), ...(pantry ? { pantry } : {}) });
  }

  cookingPrefs(prefs: CookingPrefs): Promise<{ prefs: CookingPrefs }> {
    return this.call("cooking/prefs", { prefs });
  }

  cookingPdf(kind: "recipe" | "book" | "shopping", what: RecipeTarget, images: Record<string, string> = {},
    lang?: string, title?: string): Promise<{ pdf: string; filename: string }> {
    return this.call("cooking/pdf", { kind, ...what, images, ...(lang ? { lang } : {}), ...(title ? { title } : {}) });
  }

  cookingSend(what: "recipe" | "shopping", recipes: RecipeTarget, opts: { service?: string; dryRun?: boolean; lang?: string } = {}):
    Promise<{ sent: boolean; title: string; text: string }> {
    return this.call("cooking/send", {
      what, ...recipes, ...(opts.service ? { service: opts.service } : {}), ...(opts.dryRun ? { dry_run: true } : {}), ...(opts.lang ? { lang: opts.lang } : {}),
    });
  }

  cookingToTodo(entityId: string, recipes: RecipeTarget, lang?: string): Promise<{ added: number; skipped: number }> {
    return this.call("cooking/to_todo", { entity_id: entityId, ...recipes, ...(lang ? { lang } : {}) });
  }

  // -- records ------------------------------------------------------------- //
  records(): Promise<RecordsOverview> {
    return this.call("records/overview");
  }

  logHarvest(entry: {
    planting_id?: string | null; plant_id?: string | null; kg?: number; count?: number | null; quality?: number | null; day?: string; note?: string;
  }): Promise<{ harvest: HarvestEntry }> {
    return this.call("records/harvest/add", entry as Record<string, unknown>);
  }

  starterGarden(size: "small" | "medium" | "large", greenhouse: boolean): Promise<{ beds: number; plantings: number }> {
    return this.call("garden/starter", { size, greenhouse });
  }

  saveExpense(expense: { id?: string; amount: number; category: string; day?: string; note?: string }): Promise<{ expense: Expense }> {
    return this.call("records/expense/save", { expense });
  }

  deleteRecord(kind: "harvest" | "journal" | "seed" | "expense", recordId: string): Promise<void> {
    return this.call("records/delete", { kind, record_id: recordId });
  }

  diagnosePhoto(photo: string, where: { planting_id?: string | null; bed_id?: string | null }): Promise<PhotoDiagnosis> {
    const extra: Record<string, string> = {};
    if (where.planting_id) extra.planting_id = where.planting_id;
    if (where.bed_id) extra.bed_id = where.bed_id;
    return this.call("photo/diagnose", { photo, ...extra });
  }

  saveJournal(entry: Partial<JournalEntry>): Promise<{ entry: JournalEntry }> {
    return this.call("records/journal/save", { entry });
  }

  saveSeed(packet: Partial<SeedPacket>): Promise<{ packet: SeedPacket }> {
    return this.call("records/seeds/save", { packet });
  }

  saveSoilTest(bedId: string, test: Partial<SoilTest>): Promise<{ test: SoilTest }> {
    return this.call("records/soil/save", { bed_id: bedId, test });
  }

  deleteSoilTest(bedId: string, date: string): Promise<void> {
    return this.call("records/soil/delete", { bed_id: bedId, date });
  }

  /** Upload a photo through HA's image_upload integration; returns the image id. */
  async uploadPhoto(file: File): Promise<string> {
    const body = new FormData();
    body.append("file", file);
    const resp = await this.hass.fetchWithAuth("/api/image/upload", { method: "POST", body });
    if (!resp.ok) throw new Error(`Upload failed (${resp.status})`);
    const json = (await resp.json()) as { id: string };
    return json.id;
  }
}

/** Prefix for photo URLs when the panel is served below a sub-path (the web version sets it); empty in Home Assistant. */
const photoBase = (): string => (globalThis as { HORTULUS_BASE?: string }).HORTULUS_BASE ?? "";

export const photoUrl = (id: string, size = "256x256"): string =>
  id.startsWith("http") || id.startsWith("/") ? id : `${photoBase()}/api/image/serve/${id}/${size}`;
