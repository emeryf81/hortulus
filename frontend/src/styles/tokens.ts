import { css } from "lit";

/**
 * Hortulus design tokens.
 *
 * Palette - "kitchen garden at golden hour": leaf greens for primary actions,
 * warm soil browns for structure, marigold for highlights, tomato for errors,
 * frost blue for cold.  All text/background pairs meet WCAG AA (4.5:1) in both
 * light and dark themes; colour is never the only carrier of meaning (status
 * chips have icons/labels, plant families have letters + outlines).
 *
 * Typography follows Home Assistant's font stack so the panel feels native,
 * on a 1.2 modular scale (12 / 14 / 16 / 20 / 24 / 32).
 * Spacing uses a 4 px base grid.
 */
export const tokens = css`
  :host {
    /* -- brand palette ------------------------------------------------ */
    --hl-leaf-900: #1f3d1c;
    --hl-leaf-700: #2f5d2a;
    --hl-leaf-600: #3b7334;
    --hl-leaf-500: #4c8c3f;
    --hl-leaf-300: #9cc58a;
    --hl-leaf-100: #e4f0dc;
    --hl-leaf-50: #f3f8ef;
    --hl-soil-900: #2e2118;
    --hl-soil-700: #5a3f2b;
    --hl-soil-500: #8b6446;
    --hl-soil-300: #c4a587;
    --hl-soil-100: #efe4d6;
    --hl-sun-500: #e8a33d;
    --hl-sun-100: #fbefd9;
    --hl-tomato-600: #a8331f;
    --hl-tomato-500: #c8432f;
    --hl-tomato-100: #f8e1dc;
    --hl-frost-600: #2f6690;
    --hl-frost-500: #5b8db8;
    --hl-frost-100: #e1ecf5;
    --hl-water-500: #3a7ca5;
    --hl-water-ink: #2a5f86; /* text in water blue (AA on every light surface) */

    /* -- semantic (light) --------------------------------------------- */
    --hl-bg: #faf7f0;
    --hl-surface: #ffffff;
    --hl-surface-2: #f3efe6;
    --hl-surface-3: #e9e3d6;
    --hl-text: #22281f;
    --hl-text-muted: #5e6658;
    --hl-border: #e2dccd;
    --hl-primary: var(--hl-leaf-600);
    --hl-primary-hover: var(--hl-leaf-700);
    --hl-on-primary: #ffffff;
    --hl-accent: var(--hl-sun-500);
    --hl-danger: var(--hl-tomato-500);
    --hl-warning: #b26b00;
    --hl-info: var(--hl-frost-600);
    --hl-success: var(--hl-leaf-600);
    --hl-focus: #2f7dd1;
    --hl-canvas-bg: #f6f1e4;
    --hl-grid-line: rgba(90, 63, 43, 0.12);
    --hl-grid-line-strong: rgba(90, 63, 43, 0.25);
    --hl-bed-fill: #8b6446;
    --hl-bed-fill-raised: #7a5539;
    --hl-container-fill: #a07b5a;
    --hl-zone-outdoor: rgba(76, 140, 63, 0.08);
    --hl-zone-greenhouse: rgba(91, 141, 184, 0.12);

    /* -- typography --------------------------------------------------- */
    --hl-font: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, "Roboto", "Noto Sans", system-ui, sans-serif));
    --hl-font-display: var(--ha-font-family-heading, var(--hl-font));
    /* editorial serif for display type - the same voice as the printed season book */
    --hl-font-serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", "URW Palladio L", Georgia, serif;
    --hl-fs-xs: 12px;
    --hl-fs-sm: 13px;
    --hl-fs-md: 14px;
    --hl-fs-lg: 16px;
    --hl-fs-xl: 20px;
    --hl-fs-2xl: 24px;
    --hl-fs-3xl: 32px;
    --hl-lh: 1.45;

    /* -- spacing, radii, elevation, motion ---------------------------- */
    --hl-s1: 4px;
    --hl-s2: 8px;
    --hl-s3: 12px;
    --hl-s4: 16px;
    --hl-s5: 24px;
    --hl-s6: 32px;
    --hl-s8: 48px;
    --hl-r-sm: 6px;
    --hl-r-md: 10px;
    --hl-r-lg: 16px;
    --hl-r-pill: 999px;
    /* layered, warm-tinted elevation (ambient + key light) */
    --hl-shadow-1: 0 1px 1px rgba(46, 33, 24, 0.04), 0 2px 4px rgba(46, 33, 24, 0.04), 0 0 0 1px rgba(46, 33, 24, 0.02);
    --hl-shadow-2: 0 1px 2px rgba(46, 33, 24, 0.05), 0 4px 8px rgba(46, 33, 24, 0.06), 0 12px 24px rgba(46, 33, 24, 0.06);
    --hl-shadow-3: 0 2px 4px rgba(46, 33, 24, 0.06), 0 12px 24px rgba(46, 33, 24, 0.12), 0 32px 64px rgba(46, 33, 24, 0.14);
    --hl-shadow-primary: 0 1px 2px rgba(31, 61, 28, 0.25), 0 4px 12px rgba(59, 115, 52, 0.28);
    --hl-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.65);
    --hl-ease: cubic-bezier(0.2, 0.8, 0.2, 1);
    --hl-ease-spring: cubic-bezier(0.34, 1.4, 0.64, 1);
    --hl-dur: 160ms;
    --hl-dur-slow: 320ms;
    /* seasonal light for heroes and covers */
    --hl-grad-spring: linear-gradient(135deg, #e9f3df 0%, #cfe6bd 45%, #a9d18e 100%);
    --hl-grad-summer: linear-gradient(135deg, #fff4dc 0%, #ffe1a6 45%, #f6c26b 100%);
    --hl-grad-autumn: linear-gradient(135deg, #fbeadb 0%, #f2c6a0 45%, #d98e57 100%);
    --hl-grad-winter: linear-gradient(135deg, #eef3f7 0%, #d6e3ee 45%, #b3c9dc 100%);
    --hl-hero-ink: #1f2a1c;

    /* -- plant families (also served by the backend FAMILIES table) --- */
    --hl-fam-solanaceae: #c8432f;
    --hl-fam-cucurbitaceae: #e0a526;
    --hl-fam-fabaceae: #6a9f3a;
    --hl-fam-brassicaceae: #3e7c8c;
    --hl-fam-apiaceae: #e07a2e;
    --hl-fam-amaryllidaceae: #8e5ba8;
    --hl-fam-amaranthaceae: #a23e6b;
    --hl-fam-asteraceae: #4fa38a;
    --hl-fam-lamiaceae: #4f6fb0;
    --hl-fam-poaceae: #b79f2e;

    --hl-chip-active-fg: var(--hl-leaf-700);
    color-scheme: light;
  }

`;

/** Colour themes and the dark palette: see ``palettes.ts`` (set inline by the panel). */
export const themes = css``;

/**
 * Reusable component styles - buttons, cards, chips, inputs (with all states).
 * Child components include only ``shared``: the tokens are declared once on
 * <hortulus-panel> and inherit through every shadow root, so a single
 * ``dark`` attribute on the panel re-themes the whole tree.
 */
export const shared = css`
  :host {
    font-family: var(--hl-font);
    font-size: var(--hl-fs-md);
    line-height: var(--hl-lh);
    color: var(--hl-text);
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  h1, h2, h3, h4 {
    font-family: var(--hl-font-display);
    margin: 0;
    line-height: 1.25;
    color: var(--hl-text);
  }
  h1 { font-family: var(--hl-font-serif); font-size: var(--hl-fs-3xl); font-weight: 600; letter-spacing: -0.015em; }
  h2 { font-family: var(--hl-font-serif); font-size: var(--hl-fs-xl); font-weight: 600; letter-spacing: -0.005em; }
  h3 { font-size: var(--hl-fs-lg); font-weight: 600; }
  h4 { font-size: var(--hl-fs-md); font-weight: 600; }
  p { margin: 0; }
  .muted { color: var(--hl-text-muted); }
  .eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--hl-text-muted); }
  .num, td, .big, .temp { font-variant-numeric: tabular-nums; }
  ::selection { background: color-mix(in srgb, var(--hl-leaf-300) 55%, transparent); }
  .small { font-size: var(--hl-fs-sm); }
  .xs { font-size: var(--hl-fs-xs); }
  .row { display: flex; align-items: center; gap: var(--hl-s2); }
  .row.wrap { flex-wrap: wrap; }
  .spacer { flex: 1; }
  .stack { display: flex; flex-direction: column; gap: var(--hl-s3); }
  .visually-hidden {
    position: absolute !important; width: 1px; height: 1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap; border: 0; padding: 0; margin: -1px;
  }

  /* -- cards ---------------------------------------------------------- */
  .card {
    background: var(--hl-surface);
    border: 1px solid color-mix(in srgb, var(--hl-border) 80%, transparent);
    border-radius: var(--hl-r-lg);
    box-shadow: var(--hl-shadow-1), var(--hl-highlight);
    padding: var(--hl-s5);
    transition: box-shadow var(--hl-dur-slow) var(--hl-ease), transform var(--hl-dur-slow) var(--hl-ease);
  }
  .card:hover { box-shadow: var(--hl-shadow-2), var(--hl-highlight); }
  .card > header { display: flex; align-items: center; gap: var(--hl-s2); margin-bottom: var(--hl-s4); }
  .card > header h2 { font-size: 19px; }

  /* -- buttons: default / hover / active / focus / disabled ------------ */
  button { font: inherit; }
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: var(--hl-s2);
    min-height: 36px; padding: 0 var(--hl-s4);
    border-radius: var(--hl-r-pill); border: 1px solid var(--hl-border);
    background: var(--hl-surface); color: var(--hl-text);
    font-weight: 500; font-size: var(--hl-fs-md); cursor: pointer;
    transition: background var(--hl-dur) var(--hl-ease), border-color var(--hl-dur) var(--hl-ease),
      transform var(--hl-dur) var(--hl-ease), box-shadow var(--hl-dur) var(--hl-ease);
    white-space: nowrap;
  }
  .btn:hover { background: var(--hl-surface-2); }
  .btn:active { transform: scale(0.97); }
  .btn:focus-visible, .icon-btn:focus-visible, .chip:focus-visible, input:focus-visible,
  select:focus-visible, textarea:focus-visible, [tabindex]:focus-visible {
    outline: 2px solid var(--hl-focus); outline-offset: 2px;
  }
  .btn[disabled], .icon-btn[disabled] { opacity: 0.45; cursor: not-allowed; transform: none; }
  .btn { box-shadow: var(--hl-shadow-1); }
  .btn:hover { box-shadow: var(--hl-shadow-2); }
  .btn.primary {
    background: linear-gradient(180deg, color-mix(in srgb, var(--hl-primary) 88%, #fff) 0%, var(--hl-primary) 100%);
    border-color: color-mix(in srgb, var(--hl-primary) 70%, #000); color: var(--hl-on-primary);
    box-shadow: var(--hl-shadow-primary), inset 0 1px 0 rgba(255, 255, 255, 0.22);
  }
  .btn.primary:hover { background: linear-gradient(180deg, var(--hl-primary) 0%, var(--hl-primary-hover) 100%); transform: translateY(-1px); }
  .btn.primary:active { transform: translateY(0) scale(0.98); }
  .btn.danger { color: var(--hl-danger); border-color: color-mix(in srgb, var(--hl-danger) 40%, transparent); }
  .btn.danger:hover { background: var(--hl-tomato-100); }
  .btn.ghost { background: transparent; border-color: transparent; box-shadow: none; }
  .btn.ghost:hover { background: var(--hl-surface-2); }
  .btn.small { min-height: 28px; padding: 0 var(--hl-s3); font-size: var(--hl-fs-sm); }
  .icon-btn {
    display: inline-grid; place-items: center; width: 36px; height: 36px; border-radius: var(--hl-r-md);
    border: 1px solid transparent; background: transparent; color: var(--hl-text); cursor: pointer;
    transition: background var(--hl-dur) var(--hl-ease);
    --mdc-icon-size: 20px;
  }
  .icon-btn:hover { background: var(--hl-surface-2); }
  .icon-btn[aria-pressed="true"] { background: var(--hl-leaf-100); color: var(--hl-primary); border-color: var(--hl-leaf-300); }

  /* -- chips ---------------------------------------------------------- */
  .chip {
    display: inline-flex; align-items: center; gap: var(--hl-s1);
    height: 26px; padding: 0 var(--hl-s3); border-radius: var(--hl-r-pill);
    font-size: var(--hl-fs-xs); font-weight: 600; letter-spacing: 0.01em;
    background: var(--hl-surface-2); color: var(--hl-text-muted); border: 1px solid transparent;
    --mdc-icon-size: 14px;
  }
  button.chip { cursor: pointer; }
  button.chip:hover { border-color: var(--hl-border); }
  .chip[aria-pressed="true"] { background: var(--hl-leaf-100); color: var(--hl-chip-active-fg); border-color: var(--hl-leaf-300); }
  .chip.ok { background: var(--hl-leaf-100); color: var(--hl-success); }
  .chip.warn { background: var(--hl-sun-100); color: var(--hl-warning-ink, #865000); }
  .chip.bad { background: var(--hl-tomato-100); color: var(--hl-danger-ink, #9a2e1c); }
  .chip.cold { background: var(--hl-frost-100); color: var(--hl-info); }

  /* -- forms: default / focus / error / disabled ---------------------- */
  label.field { display: flex; flex-direction: column; gap: var(--hl-s1); font-size: var(--hl-fs-sm); color: var(--hl-text-muted); }
  input, select, textarea {
    font: inherit; color: var(--hl-text); background: var(--hl-surface);
    border: 1px solid var(--hl-border); border-radius: var(--hl-r-sm);
    padding: 8px 10px; min-height: 36px; width: 100%;
    transition: border-color var(--hl-dur) var(--hl-ease);
  }
  input:hover, select:hover, textarea:hover { border-color: var(--hl-soil-300); }
  input:focus, select:focus, textarea:focus {
    outline: none; border-color: var(--hl-primary);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--hl-primary) 22%, transparent);
  }
  input[aria-invalid="true"] { border-color: var(--hl-danger); }
  input:disabled, select:disabled { opacity: 0.55; cursor: not-allowed; }
  input[type="checkbox"] { width: 18px; min-height: 18px; accent-color: var(--hl-primary); }
  .field-error { color: var(--hl-danger); font-size: var(--hl-fs-xs); }

  /* -- misc ----------------------------------------------------------- */
  .family-dot { width: 10px; height: 10px; border-radius: 50%; flex: none; display: inline-block; }
  .empty { padding: var(--hl-s6); text-align: center; color: var(--hl-text-muted); font-family: var(--hl-font-serif); font-style: italic; }

  /* -- data tables ------------------------------------------------------ */
  table th { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--hl-text-muted); }
  table tbody tr { transition: background var(--hl-dur) var(--hl-ease); }
  table tbody tr:hover { background: color-mix(in srgb, var(--hl-leaf-50) 70%, transparent); }

  /* -- motion ------------------------------------------------------------ */
  @keyframes hl-rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  @keyframes hl-shimmer { from { background-position: -400px 0; } to { background-position: 400px 0; } }
  .rise { animation: hl-rise var(--hl-dur-slow) var(--hl-ease) both; }
  .skeleton {
    border-radius: var(--hl-r-sm); min-height: 14px;
    background: linear-gradient(90deg, var(--hl-surface-2) 0%, var(--hl-surface-3) 50%, var(--hl-surface-2) 100%);
    background-size: 800px 100%; animation: hl-shimmer 1.4s linear infinite;
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }

  /* -- scrollbars ------------------------------------------------------- */
  * { scrollbar-width: thin; scrollbar-color: var(--hl-surface-3) transparent; }
  .divider { height: 1px; background: var(--hl-border); margin: var(--hl-s3) 0; }
  ha-icon { --mdc-icon-size: 20px; }
`;
