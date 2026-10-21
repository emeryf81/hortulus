// Date field that always reads day-month-year in the panel's language
// (13-04-2026 in Dutch, 13/04/2026 in English) whatever the browser's locale;
// the calendar button opens the browser's own date picker.
import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { displayDate, parseDate } from "../util/dates";

@customElement("hl-date-input")
export class DateInput extends LitElement {
  /** Takes part in a <form> like an <input name=...> (form.elements, FormData). */
  static formAssociated = true;
  private internals?: ElementInternals;
  @property({ reflect: true }) name = "";
  /** Earliest allowed date (ISO), for the picker and typed input. */
  @property() min = "";
  /** ISO date (``YYYY-MM-DD``) or empty. */
  @property() value = "";
  @property() lang = "en";
  @property() label = "";
  @property() pickLabel = "Calendar";
  /** Shown by the browser when a form is submitted with unreadable text. */
  @property() invalidMessage = "dd-mm-yyyy";
  @property({ type: Boolean }) disabled = false;
  @state() private invalid = false;
  @query("input[type=date]") private picker!: HTMLInputElement;

  static styles = css`
    :host { display: inline-flex; align-items: stretch; border: 1px solid var(--hl-border-strong, #c9c2b4); border-radius: var(--hl-r-sm, 6px);
      background: var(--hl-surface, #fff); position: relative; min-height: 30px; max-width: 150px; }
    :host([disabled]) { opacity: 0.6; }
    input.text { border: 0; background: transparent; font: inherit; font-size: var(--hl-fs-sm, 14px); color: var(--hl-text, #222);
      width: 100%; min-width: 0; padding: 2px 6px; outline: none; }
    input.text.invalid { color: var(--hl-danger, #b3261e); }
    :host(:focus-within) { outline: 2px solid var(--hl-focus, #4b8b3b); outline-offset: 1px; }
    button { border: 0; background: transparent; cursor: pointer; padding: 0 6px; color: var(--hl-text-muted, #666); font-size: 14px; }
    button:disabled { cursor: default; }
    input[type="date"] { position: absolute; right: 0; bottom: 0; width: 1px; height: 1px; opacity: 0; border: 0; padding: 0; pointer-events: none; }
  `;

  constructor() {
    super();
    try {
      this.internals = this.attachInternals();
    } catch {
      /* very old browser: works without forms */
    }
  }

  protected updated(changed: Map<string, unknown>): void {
    if (changed.has("value")) this.internals?.setFormValue(this.value || "");
  }

  /** Mark the field (and its form) invalid while the text cannot be used. */
  private setInvalid(invalid: boolean): void {
    this.invalid = invalid;
    if (!this.internals) return;
    const anchor = this.renderRoot.querySelector<HTMLInputElement>("input.text") ?? undefined;
    if (invalid) this.internals.setValidity({ badInput: true }, this.invalidMessage, anchor);
    else this.internals.setValidity({});
  }

  private emit(value: string | null): void {
    if (value && this.min && value < this.min) {
      this.setInvalid(true);
      return;
    }
    this.setInvalid(false);
    this.value = value ?? "";
    this.dispatchEvent(new CustomEvent("date-change", { detail: value, bubbles: true, composed: true }));
  }

  private onText(e: Event): void {
    const el = e.target as HTMLInputElement;
    const parsed = parseDate(el.value);
    if (parsed === undefined) {
      // keep the typed text for correction; the form cannot submit the old date meanwhile
      this.setInvalid(true);
      return;
    }
    if (parsed && this.min && parsed < this.min) {
      this.setInvalid(true); // also when it is the value already there
      return;
    }
    this.setInvalid(false);
    el.value = displayDate(parsed, this.lang);
    if ((parsed ?? "") !== (this.value ?? "")) this.emit(parsed);
  }

  private openPicker(): void {
    const picker = this.picker as HTMLInputElement & { showPicker?: () => void };
    picker.value = this.value || "";
    try {
      picker.showPicker ? picker.showPicker() : picker.click();
    } catch {
      picker.click();
    }
  }

  render(): TemplateResult {
    const placeholder = this.lang === "nl" ? "dd-mm-jjjj" : this.lang === "fr" ? "jj/mm/aaaa" : "dd/mm/yyyy";
    return html`<input class="text ${this.invalid ? "invalid" : ""}" .value=${displayDate(this.value, this.lang)} placeholder=${placeholder}
        aria-label=${this.label} aria-invalid=${String(this.invalid)} ?disabled=${this.disabled} inputmode="numeric" @change=${this.onText} />
      ${this.disabled ? nothing : html`<button type="button" aria-label=${this.pickLabel} title=${this.pickLabel} @click=${this.openPicker}>📅</button>`}
      <input type="date" tabindex="-1" aria-hidden="true" .min=${this.min} @change=${(e: Event) => this.emit((e.target as HTMLInputElement).value || null)} />`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hl-date-input": DateInput;
  }
}
