# RAI Design System

**Status:** normative. Everything here is a decision, not a suggestion. Three agents build the
interface from this document; if a value you need is not here, that is a bug in this document —
raise it rather than inventing one.

**Scope:** `web/` (Next.js App Router). Consumes `docs/API_CONTRACT.md` verbatim.

---

## 0. Direction

RAI is the screen an operations engineer opens at 06:40 before the day shift walk-round, on a
laptop wedged next to a plant radio. It must answer three questions in under ten seconds:
*what changed, is it real, and what does it cost me to wait.*

The reference points are **Bloomberg-terminal information density**, **Linear's precision**, and
**real SCADA/control-room software**. The product is an **instrument panel**, not a dashboard:
labelled, calibrated, unit-bearing, hairline-ruled. Every number is traceable to an API field.

Three ideas carry the whole identity. Spend design effort here and nowhere else:

1. **The expected-vs-actual band with a residual strip beneath it.** This is the hero chart and
   the single most important graphic in the product. It is what makes "underperformance" a
   measurable quantity rather than an opinion.
2. **The evidence ledger.** The investigation view is a ruled ledger you read top to bottom:
   anomaly → environment → peers → history → knowledge → economics → decision. Each row is a
   claim with the number that supports it. No cards, no tiles, no chat.
3. **The source line.** Every panel ends in a 24 px hairline-topped strip naming the API field
   and method behind its numbers. This is the trust device and it is mandatory.

Restraint rule: if a decoration does not carry data, remove it.

---

## 1. Colour

### 1.1 How the tokens are defined

All colour is authored in **OKLCH** as CSS custom properties. The light theme is the product;
the dark theme is a secondary convenience for night shift. Every value below was generated from
its OKLCH triple and verified in sRGB gamut; the hex column is the resolved value and is given
for reference only — **author CSS against the OKLCH values and the token names, never the hex.**

Declare the light palette on bare `:root`. Redefine *only* the changed tokens in the two dark
scopes so an explicit theme choice wins in both directions:

```css
:root { /* light values — Section 1.2 */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark values — Section 1.4 */ }
}
:root[data-theme="dark"] { /* dark values — Section 1.4 */ }
```

Never give a colour its only definition inside a media query or a `[data-theme]` block.
`body` always carries an explicit `background: var(--surface)`.

### 1.2 Light theme — semantic tokens (default, `:root`)

Neutrals are warm (hue 85, the off-white ground). Ink is cool graphite (hue 220–225). The
slight hue tension between warm paper and cool ink is deliberate and is what keeps the light
theme from reading as cream-and-brown.

| Token | OKLCH | Hex | Contrast on `--surface` | Use |
|---|---|---|---|---|
| `--surface` | `oklch(0.980 0.006 85)` | `#faf8f4` | — | Page ground. Never `#ffffff`. |
| `--surface-raised` | `oklch(0.993 0.004 85)` | `#fefdfa` | — | Panels, table body, popovers |
| `--surface-sunken` | `oklch(0.950 0.007 85)` | `#f1eee9` | — | Row hover, inactive tab, well |
| `--surface-inset` | `oklch(0.925 0.008 85)` | `#e9e6e0` | — | Table header, code block, rail |
| `--border` | `oklch(0.905 0.008 85)` | `#e2dfda` | 1.25:1 | Hairline. Structural default. |
| `--border-strong` | `oklch(0.800 0.010 85)` | `#c1bdb7` | 1.76:1 | Panel outer edge, table frame |
| `--border-control` | `oklch(0.615 0.012 85)` | `#88847d` | 3.15:1 | Input/checkbox/select boundary |
| `--text-primary` | `oklch(0.245 0.010 220)` | `#1b2224` | **15.22:1** | Values, headings, table cells |
| `--text-secondary` | `oklch(0.470 0.012 225)` | `#545c60` | **6.43:1** | Prose, labels, descriptions |
| `--text-tertiary` | `oklch(0.545 0.012 225)` | `#697275` | **4.64:1** | Units, axis labels, metadata, null |
| `--text-inverse` | `oklch(0.993 0.004 85)` | `#fefdfa` | — | Text on `--accent`/`--critical` fills |
| `--accent` | `oklch(0.470 0.075 185)` | `#186860` | **6.21:1** | Primary action, subject asset, links |
| `--accent-hover` | `oklch(0.410 0.070 185)` | `#07564f` | 8.07:1 | Hover/active of accent |
| `--accent-border` | `oklch(0.740 0.070 185)` | `#76bab0` | 2.10:1 | Selected row edge, focus tint edge |
| `--accent-surface` | `oklch(0.955 0.022 185)` | `#e1f5f2` | — | Selected row fill, accent tint |
| `--ok` | `oklch(0.520 0.120 150)` | `#287c42` | **4.89:1** | Healthy / nominal / resolved |
| `--ok-surface` | `oklch(0.960 0.030 150)` | `#e4f8e7` | — | OK pill background |
| `--warn` | `oklch(0.660 0.145 66)` | `#cd7d09` | 3.03:1 | Warning marks, borders, glyphs |
| `--warn-ink` | `oklch(0.500 0.115 62)` | `#905100` | **5.89:1** | Warning *text* (`--warn` is too light) |
| `--warn-surface` | `oklch(0.960 0.026 68)` | `#feefe0` | — | Warning pill background |
| `--critical` | `oklch(0.540 0.190 25)` | `#c52b30` | **5.26:1** | Critical marks and text |
| `--critical-ink` | `oklch(0.470 0.175 25)` | `#a71922` | **7.06:1** | Critical text on a tint background |
| `--critical-surface` | `oklch(0.955 0.020 25)` | `#feebe9` | — | Critical pill background |
| `--info` | `oklch(0.510 0.120 248)` | `#1f6aa7` | **5.38:1** | Informational, environmental verdict |
| `--info-surface` | `oklch(0.960 0.018 248)` | `#e9f3fe` | — | Info pill background |

**Colour semantics are reserved and non-negotiable.**

- `--critical` (red) appears **only** for `risk_band: "critical"`, `severity: "critical"`,
  `sensor_health: "failed"`, and hard errors. Nothing else may be red. A "high" risk band is
  amber, not red.
- `--warn` (amber) is `risk_band: "high" | "elevated"`, `severity: "high" | "medium"`,
  `sensor_health: "suspect"`, and the "requires human review" state.
- `--ok` (green) is nominal, `risk_band: "low"`, resolved, and "environmental — not escalated".
- `--info` (blue) is informational: curtailment, night, below-cut-in, environmental attribution,
  "not evaluated" explanations.
- `--accent` (teal) is **interaction and subject identity**, never a status. The asset under
  investigation is teal; a healthy asset is not.

### 1.3 Light theme — data-visualisation palette

Chart chrome:

| Token | OKLCH | Hex | Use |
|---|---|---|---|
| `--viz-grid` | `oklch(0.930 0.007 85)` | `#eae8e3` | Horizontal gridlines, 1 px |
| `--viz-axis` | `oklch(0.830 0.009 85)` | `#cac7c1` | x baseline, tick marks, zero rule |
| `--viz-expected` | `oklch(0.600 0.011 85)` | `#838079` | The *expected* series and peer dots (3.66:1) |
| `--viz-band` | `color-mix(in oklch, var(--accent) 12%, var(--surface-raised))` | — | Prediction-interval fill, no stroke |
| `--viz-band-outer` | `color-mix(in oklch, var(--accent) 6%, var(--surface-raised))` | — | p05–p95 outer band when two bands shown |

Categorical series — **fixed slot order, never cycled, never re-assigned by rank**:

| Slot | Hue | OKLCH | Hex | Conventional meaning in RAI |
|---|---|---|---|---|
| `--series-1` | blue | `oklch(0.505 0.150 256)` | `#1f63b8` | Power / the primary measured signal |
| `--series-2` | orange | `oklch(0.594 0.147 48)` | `#c25e1f` | Temperature signals |
| `--series-3` | teal | `oklch(0.583 0.105 176)` | `#148f79` | Vibration / mechanical signals |
| `--series-4` | violet | `oklch(0.512 0.180 290)` | `#6a4bc4` | Electrical (voltage, current) |
| `--series-5` | magenta | `oklch(0.554 0.163 351)` | `#b5417e` | Environmental covariates |
| `--series-6` | olive | `oklch(0.616 0.128 109)` | `#8c8a12` | Derived ratios (PR, soiling, CF) |

Sequential ramp (single hue — magnitude only: risk-driver bars, soiling zone grid, heatmaps):

| Step | Hex | Step | Hex | Step | Hex |
|---|---|---|---|---|---|
| 100 | `#dfe9f6` | 300 | `#84a8d8` | 500 | `#2f6cb4` |
| 200 | `#b4cbe9` | 400 | `#5589c6` | 600 | `#1e4a80` |

Ordinal use (discrete ordered marks) must start no lighter than step 300.

Diverging pair for signed residuals — **blue ↔ red with a neutral grey midpoint**:
negative arm `--series-1` → midpoint `oklch(0.905 0.008 85)` (`#e2dfda`) → positive arm
`--critical`. Equal step count per arm. No hue at the midpoint.

**Measured validation** (dataviz validator, surface `#faf8f4`, light mode):

```
Palette (light, surface #faf8f4, categorical): 6 slots
  [PASS] Lightness band         all 6 inside L 0.43-0.77
  [PASS] Chroma floor           all 6 >= 0.1
  [PASS] CVD separation         worst adjacent #148f79<->#c25e1f dE 12.0 (protan) - tritan 12.6
  [PASS] Normal-vision floor    worst adjacent #b5417e<->#6a4bc4 dE 17.9 (normal)
  [PASS] Contrast vs surface    all 6 >= 3:1
```

**Series cap.** The six slots clear every gate on the *adjacent* pairlist — stacked bars, lines,
grouped bars. On the *all-pairs* pairlist (scatter, bubble, small multiples, the fleet status
grid) only the **first three slots** validate. Past three series in an all-pairs form: fold the
remainder into a neutral "Other" in `--viz-expected`, or facet into small multiples. On
all-pairs forms the teal↔orange pair sits at tritan ΔE 7.9 (light) / 3.4 (dark) — inside the
warn band — so **direct labels are mandatory on every scatter and dot plot**, not optional.

Status colours are deliberately distinct steps from the categorical slots, but `--critical` and
`--series-2`/`--series-5` are same-family; this is why a status colour **always** ships with a
glyph and a text label (Section 7). Hue never carries status alone.

### 1.4 Dark theme (secondary — night shift only)

> **Clearly marked as secondary.** The light theme is the designed product and the demo runs in
> light. The dark theme must be correct and accessible, but no layout, density or component
> decision is ever made for the sake of dark mode.

Dark steps are *selected for the dark surface*, not an inversion of the light values.

| Token | OKLCH | Hex | Contrast on `--surface-raised` |
|---|---|---|---|
| `--surface` | `oklch(0.185 0.007 240)` | `#101316` | — |
| `--surface-raised` | `oklch(0.236 0.008 240)` | `#1b1f22` | — |
| `--surface-sunken` | `oklch(0.160 0.006 240)` | `#0b0e10` | — |
| `--surface-inset` | `oklch(0.280 0.008 240)` | `#25292c` | — |
| `--border` | `oklch(0.320 0.009 240)` | `#2f3437` | — |
| `--border-strong` | `oklch(0.420 0.010 240)` | `#484e52` | — |
| `--border-control` | `oklch(0.545 0.010 240)` | `#6b7175` | 3.07:1 |
| `--text-primary` | `oklch(0.960 0.004 85)` | `#f3f2ef` | **14.82:1** |
| `--text-secondary` | `oklch(0.760 0.008 230)` | `#acb2b5` | **7.73:1** |
| `--text-tertiary` | `oklch(0.620 0.010 230)` | `#80878b` | **4.55:1** |
| `--text-inverse` | `oklch(0.185 0.007 240)` | `#101316` | — |
| `--accent` | `oklch(0.720 0.090 185)` | `#5bb7ac` | **6.96:1** |
| `--accent-hover` | `oklch(0.780 0.085 185)` | `#74c9be` | 8.6:1 |
| `--accent-surface` | `oklch(0.300 0.030 185)` | `#1c3330` | — |
| `--ok` | `oklch(0.700 0.130 150)` | `#5cb572` | **6.56:1** |
| `--ok-surface` | `oklch(0.300 0.034 150)` | `#213325` | — |
| `--warn` | `oklch(0.780 0.140 72)` | `#eea743` | **8.09:1** |
| `--warn-ink` | `oklch(0.780 0.140 72)` | `#eea743` | **8.09:1** (same step; dark needs no split) |
| `--warn-surface` | `oklch(0.310 0.034 72)` | `#3b2e1d` | — |
| `--critical` | `oklch(0.650 0.170 25)` | `#e45d58` | **4.74:1** |
| `--critical-ink` | `oklch(0.650 0.170 25)` | `#e45d58` | **4.74:1** |
| `--critical-surface` | `oklch(0.300 0.040 25)` | `#402624` | — |
| `--info` | `oklch(0.690 0.110 248)` | `#61a1dc` | **6.04:1** |
| `--info-surface` | `oklch(0.300 0.030 248)` | `#222f3c` | — |
| `--viz-grid` | `oklch(0.300 0.008 240)` | `#2a2e31` | — |
| `--viz-axis` | `oklch(0.400 0.010 240)` | `#43494d` | — |
| `--viz-expected` | `oklch(0.640 0.011 230)` | `#868e92` | 5.20:1 |
| `--series-1` | `oklch(0.645 0.148 256)` | `#4c8ee6` | 4.99:1 |
| `--series-2` | `oklch(0.645 0.145 48)` | `#d36e34` | 4.78:1 |
| `--series-3` | `oklch(0.645 0.115 176)` | `#1ca48b` | 5.32:1 |
| `--series-4` | `oklch(0.655 0.150 290)` | `#917ee5` | 4.99:1 |
| `--series-5` | `oklch(0.645 0.150 351)` | `#d06399` | 4.68:1 |
| `--series-6` | `oklch(0.645 0.125 109)` | `#959328` | 5.12:1 |

**Measured validation** (dataviz validator, surface `#1b1f22`, dark mode):

```
Palette (dark, surface #1b1f22, categorical): 6 slots
  [PASS] Lightness band         all 6 inside L 0.48-0.67
  [PASS] Chroma floor           all 6 >= 0.1
  [PASS] CVD separation         worst adjacent #1ca48b<->#d36e34 dE 11.7 (deutan) - tritan 9.9
  [PASS] Normal-vision floor    worst adjacent #d06399<->#917ee5 dE 15.3 (normal)
  [PASS] Contrast vs surface    all 6 >= 3:1
  -> ALL CHECKS PASS
```

Theme is stored in `localStorage` under `rai.theme` (`"light" | "dark" | "system"`, default
`"system"`), wrapped in try/catch, and stamped on `<html data-theme>` before first paint to avoid
a flash. The toggle lives in the top bar and is the only place theme is changeable.

---

## 2. Typography

### 2.1 The pairing

**Not Inter, not Inter anywhere.** Two families, both loaded via `next/font/google`, chosen for
what this product does rather than for neutrality:

**UI, prose, headings — Archivo.** A grotesk with a signage lineage (Omnibus-Type, drawn from
American gothic signage and reverse-contrast wood type). Two properties earn it the job: it holds
legibility at 11–13 px where a control-room table lives, and its slightly narrowed lowercase fits
more label into a column than a neutral geometric grotesk. It reads as engineered rather than
friendly, which is the correct register for a screen that recommends spending ₹12.5 lakh.

**Numerics, identifiers, timestamps, code — IBM Plex Mono.** Every number that a person will
compare down a column, or watch change in place, is set in Plex Mono. Reasons, in order: true
monospace advance guarantees decimal alignment without hacks; the figures are unambiguous
(slashed zero, disambiguated 1/l/I) which matters when the asset id is `INV-023` and the status
code is `1001`; and its engineered, slightly squared skeleton harmonises with Archivo's signage
geometry without being from the same family, so the two roles stay visually separate.

```ts
// web/app/fonts.ts
import { Archivo, IBM_Plex_Mono } from "next/font/google";

export const sans = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
});                                   // variable font: weights 400-600 available

export const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});
```

```css
:root {
  --font-sans: var(--font-archivo), "Archivo", "Helvetica Neue", Arial, system-ui, sans-serif;
  --font-mono: var(--font-plex-mono), "IBM Plex Mono", ui-monospace, "SFMono-Regular",
               "Cascadia Mono", "Roboto Mono", monospace;
}
body { font-family: var(--font-sans); font-feature-settings: "tnum" 1, "cv05" 1; }
.mono, td.num, .metric-value { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
```

Weights in use: **400** (body, table cells), **500** (labels, column headers, metric values,
emphasis), **600** (panel titles, the one display line per screen). No 300, no 700, no italic
except in a citation's source attribution.

### 2.2 Type scale

Root is 16 px. A dense operations UI lives at 13 px body; prose blocks step up to 14 px so
evidence sentences stay comfortable. Ratio is ~1.14 in the UI range and opens up for values.

| Token | px | rem | Line height | Tracking | Weight | Family | Use |
|---|---|---|---|---|---|---|---|
| `--t-micro` | 11 | 0.6875 | 1.27 (14 px) | `+0.06em` | 500 | sans | Table column headers, axis labels, source line, unit legend |
| `--t-small` | 12 | 0.75 | 1.33 (16 px) | `+0.01em` | 400/500 | sans | Pill text, metadata, tooltip body, breadcrumb |
| `--t-body` | 13 | 0.8125 | 1.38 (18 px) | `0` | 400 | sans | Table cells, form labels, nav items, buttons |
| `--t-prose` | 14 | 0.875 | 1.57 (22 px) | `0` | 400 | sans | Evidence sentences, citation snippets, rationale, help |
| `--t-lead` | 16 | 1.0 | 1.38 (22 px) | `-0.006em` | 600 | sans | Panel titles, section headings (h2/h3) |
| `--t-metric` | 22 | 1.375 | 1.09 (24 px) | `-0.011em` | 500 | mono | Metric-tile values |
| `--t-metric-lg` | 30 | 1.875 | 1.07 (32 px) | `-0.018em` | 500 | mono | Hero values: fleet health, avoidable exposure |
| `--t-display` | 40 | 2.5 | 1.05 (42 px) | `-0.022em` | 600 | sans | One line per screen maximum — the verdict headline |

Prose measure: **max 68 characters** (`max-width: 62ch` at `--t-prose`). Evidence bullets and
citation snippets obey this even inside a wide panel.

`--t-display` is permitted on exactly two surfaces: the investigation verdict headline and the
empty state of the fleet view. Nowhere else.

### 2.3 Casing and label rules

- **Uppercase is permitted in exactly three places:** table column headers, chart axis/unit
  labels, and the source line — all at `--t-micro` with `+0.06em` tracking. It is the SCADA
  vernacular and it earns its place by being the densest legible form for a repeated label.
- **Uppercase is banned** above section headings, on buttons, on pills, on nav items, and as a
  tracked-out eyebrow over a heading. There are no eyebrow labels in this product.
- Sentence case everywhere else, including headings and button labels.
- No meta strings joined with middle dots (`A · B · C`) except the source line, which uses a
  single ` · ` between the endpoint and the method and nothing more.
- No `→` appended to link or button text. The label states the action: "Investigate",
  "Create inspection ticket", "Compare with peers".
- No em-dash-plus-fragment label construction (`POWER — 1,284 kW`). The unit rule handles it.

---

## 3. Space, grid, and structure

### 3.1 Spacing scale

4 px base. Only these values exist; nothing between them.

| Token | px | Typical use |
|---|---|---|
| `--sp-0` | 0 | — |
| `--sp-05` | 2 | Glyph-to-label gap, segment gap in a stacked bar |
| `--sp-1` | 4 | Pill padding-block, icon-to-text |
| `--sp-15` | 6 | Dense cell padding-block, chip gap |
| `--sp-2` | 8 | Table cell padding-block, label-to-field |
| `--sp-3` | 12 | Table cell padding-inline, panel padding at 390 px |
| `--sp-4` | 16 | Panel padding, grid gutter, stack gap |
| `--sp-5` | 20 | Panel padding (comfortable), section gap |
| `--sp-6` | 24 | Page gutter, gap between panel groups |
| `--sp-8` | 32 | Major section separation |
| `--sp-10` | 40 | Above a page-level heading |
| `--sp-12` | 48 | Empty-state vertical padding |
| `--sp-16` | 64 | Reserved: empty-state hero only |

### 3.2 Grid

- 12 columns, gutter `--sp-4` (16 px), outer page gutter `--sp-6` (24 px) at ≥1280 px and
  `--sp-4` (16 px) below. Minimum side gutter is never less than 16 px at any width.
- Content max width **1680 px**, centred. Tables extend to the page gutters; prose does not.
- Standard splits: fleet view `8 / 4` (queue + context rail). Investigation view `7 / 5`
  (evidence ledger + chart column) at ≥1440, `12` stacked below 1280.
- Vertical rhythm: panels sit in a single-column stack with `--sp-4` gap. No masonry.

### 3.3 App shell geometry

| Region | Size | Notes |
|---|---|---|
| Top bar | 48 px, sticky, `--surface-raised`, 1 px bottom `--border` | Site switcher, `data_as_of` clock, Needle status chip, theme toggle, command-palette trigger |
| Left nav rail | 224 px fixed at ≥1280 px; 64 px icon-only at 1024–1279 px; hidden at <1024 px | `--surface-inset`, 1 px right `--border`. Never a hamburger drawer at desktop width. |
| Main | fills remainder, own scroll container | `--surface` |
| Context rail (investigation) | 380 px at ≥1440 px | 1 px left `--border`, not a floating panel |
| Bottom bar (<768 px) | 52 px, 4 tabs | Replaces the rail |

The rail is a persistent rail, not a collapsible drawer: at control-room widths the navigation is
always visible, because a drawer costs a click at 06:40.

### 3.4 Radius, border, elevation

**Radius.** Small and consistent. `--r-sm: 2px` (pills, chips, inputs, checkboxes),
`--r-md: 3px` (panels, buttons, table frame), `--r-lg: 4px` (modals, popovers, command palette).
**Nothing above 4 px.** `border-radius: 50%` only on the 8 px status dot. No rounded-square icon
tiles anywhere.

**Border.** Structure is carried by 1 px borders, not shadows.

- Every panel: `1px solid var(--border)` + `--r-md` + `background: var(--surface-raised)`.
- Panel outer edge where a panel meets the page ground: `--border-strong`.
- Status on a row: **3 px left stripe** in the band colour, `border-inline-start`. This is the
  only decorative border in the system and it always carries data.
- Table internal rules: horizontal 1 px `--border` only. Never vertical rules. Never zebra
  banding — hairlines do the work at lower visual cost.

**Elevation.** Three levels, and the default is flat.

| Token | Value | Permitted on |
|---|---|---|
| `--e-0` | `none` (border only) | **Default.** Every panel, tile, row, table, chart. |
| `--e-1` | `0 1px 2px -1px oklch(0.245 0.010 220 / 0.10)` | Sticky table header once scrolled; sticky top bar once scrolled |
| `--e-2` | `0 8px 24px -8px oklch(0.245 0.010 220 / 0.18)` + 1 px `--border` | Popover, dropdown, tooltip, modal, command palette only |

Shadows on static panels, tiles, rows or cards are **prohibited**. A card that needs separation
gets a border, not a shadow.

---

## 4. Data density and tables

### 4.1 Row metrics

| Density | Row height | Cell padding | Default for |
|---|---|---|---|
| Compact | 28 px | `--sp-15` `--sp-3` | Fleet asset table (42 rows), peer table |
| Default | 32 px | `--sp-2` `--sp-3` | Priority queue, signal residual table, case list |
| Comfortable | 40 px | `--sp-3` `--sp-3` | Economic option comparison (3 rows, carries a bar) |

- Header: 30 px, `--surface-inset`, `--t-micro` uppercase 500, `position: sticky; top: 0`, gains
  `--e-1` when scrolled.
- First cell's inline-start padding aligns to the panel's inner edge (`--sp-3`), so the asset id
  column forms a hard left edge down the table.
- Row hover `--surface-sunken`; row selected `--accent-surface` + 3 px `--accent` left stripe.
  Hover must never move, lift, scale or shadow a row.
- Above 60 rows, virtualise; the fleet is 42 so the v1 tables render in full.
- Sort: single-column, click header, `aria-sort` reflected, active header shows a 10 px caret in
  `--text-secondary`. Default sorts: priority queue by `revenue_at_risk_inr × risk_score` desc
  (server order — do not re-sort client-side by default); asset table by `asset_id` asc.

### 4.2 Column rules

- Numeric columns: **right-aligned**, `--font-mono`, `tabular-nums`. The decimal point therefore
  lines up without any extra work.
- Text columns: left-aligned, `--font-sans`.
- Status/pill columns: left-aligned, fixed width, never last (the last column is the row action).
- Column header carries the unit when the whole column shares one (`POWER (kW)`), and the cells
  then omit it. Mixed-unit lists (the signal residual table) put the unit in the cell.
- Minimum column widths: asset id 76 px, status pill 112 px, a `z` score 64 px, an INR value
  96 px, a timestamp 132 px.
- No column may be the only carrier of meaning by colour — see Section 7.

### 4.3 Number formatting

One module owns all of this: `web/lib/format.ts`. No component formats a number inline.

| Quantity | Rule | Example |
|---|---|---|
| Power (kW) | 0 dp at ≥100, 1 dp below 100. Unit always shown. | `1,284 kW` · `48.6 kW` |
| Energy (kWh) | 0 dp, grouped | `3,140 kWh` |
| Temperature | 1 dp, `°C` with no space before the degree sign | `71.4 °C` |
| Vibration | 2 dp, `mm/s` | `4.62 mm/s` |
| Percent | 1 dp, `%`. Residual percentages always signed. | `29.1 %` · `−9.4 %` |
| Ratio (PR, soiling) | 3 dp, unitless, label states it is a ratio | `0.916` |
| z-score | 1 dp, **always signed**, mono | `+3.4` · `−2.1` |
| Probability / confidence | 2 dp in 0.00–1.00, shown beside its threshold | `0.87 / 0.80` |
| Duration | 1 dp + unit; absolute time in the tooltip | `18.5 h` |
| Timestamp (UI) | `12 Sep 06:40 IST`, mono | |
| Timestamp (tooltip, export) | full ISO-8601 UTC | `2026-09-12T06:40:00Z` |
| Count | integer, grouped | `18` · `24,192` |

**Indian money conventions — mandatory.** Money is INR and only INR. One locale (`en-IN`) is
used for all grouping, including engineering quantities, because the operators and the sites are
Indian and a single grouping rule prevents mixed conventions on one screen.

| Magnitude | Rendering | Example |
|---|---|---|
| `< 1,00,000` | `₹` + `en-IN` grouped integer | `₹85,000` |
| `1,00,000 – 99,99,999` | `₹` + 1–2 dp + ` L` | `₹12.5 L` · `₹1.55 L` |
| `≥ 1,00,00,000` | `₹` + 2 dp + ` Cr` | `₹4.50 Cr` |
| Rate | suffix the period | `₹1.84 L/day` · `₹3.20/kWh` |

- The `₹` glyph, always. Never `Rs.`, never `INR` inside a value, never `$`.
- The **exact rupee figure** appears in the cell's `title`/tooltip and in any CSV export, so the
  abbreviation never hides the number.
- Tariff and per-kWh rates are shown to 2 dp and never abbreviated.

**Units are part of the type system.** A unit is a `<span class="unit">` at `0.85em`, weight 400,
`--text-tertiary`, preceded by a thin space (U+2009) — except `°C`, `%`, and `₹`, which sit tight
to the figure. A unit is never bold, never coloured, never the same weight as its value.

**Null is an em-dash.** `null` renders as `—` in `--text-tertiary` with
`title="not evaluated"` and `aria-label="not evaluated"`. Never `0`, never `N/A`, never `-`,
never an empty cell, never a plausible placeholder. If a whole panel's inputs are null, the panel
shows the *not-evaluated* variant of the empty state (Section 6.16) naming which endpoint field
was null. This is the numerical-honesty rule made visible, and it is the single most important
formatting rule in the product.

**Alignment.** Values right, units inside the value's box (so the unit does not break the
decimal alignment), labels left, actions right. A metric tile's value is left-aligned to its
label, not centred — nothing in this product is centre-aligned except an empty state.

---

## 5. Charts

Read this section together with `references/anti-patterns.md` of the dataviz skill. Chart code
lives in `web/components/viz/`, one component per form, all sharing one axis/tooltip/legend layer.

### 5.1 Which form answers which question

| The question | The form | Never |
|---|---|---|
| Is it producing what it should, over time? | **Expected-vs-actual line + prediction band** | Bars; a single line with no expectation |
| How far off is it, and is it drifting? | **Residual strip** (signed columns, shared x) | A second y-axis on the power chart |
| Is this asset different from its peers? | **Peer dot plot**, one row, subject highlighted | A bar chart of 9 turbine names |
| How does power relate to wind speed? | **Power-curve scatter** + binned reference line | A line chart through scattered points |
| What drives the risk score? | **Horizontal bars, sequential single hue**, sorted desc | Radar/spider; a pie |
| Which intervention costs least? | **Stacked horizontal bars**, one row per option | Grouped vertical bars; a waterfall |
| Where is the soiling? | **Zone table + sequential block grid** | A geographic choropleth |
| How is the fleet doing right now? | **Priority queue table + 4 metric tiles** | A fleet "heatmap" as the primary object |
| What is the single headline number? | **Metric tile, no chart** | A gauge, a donut, a radial progress ring |
| Is the fleet's status spatially clustered? | **42-cell status grid**, secondary, each cell labelled | Any unlabelled colour grid |

If the answer is one number, it is not a chart.

### 5.2 The hero chart — expected vs actual with band

Data: `GET /api/assets/{id}/timeseries`. 168 h default, 10 min (wind) / 15 min (solar) cadence.

- Plot height 280 px at ≥1280 px, 220 px below. Left axis gutter 56 px, right 16 px, top 20 px,
  bottom 28 px.
- **Band** (`lower`..`upper`, the prediction interval): fill `--viz-band`, **no stroke**, drawn
  first. If two intervals are supplied, the outer uses `--viz-band-outer`. The band legend entry
  reads "expected range (p10–p90)" — the interval must be named, never left implicit.
- **Expected** (`expected`): 1.5 px, `--viz-expected`, dash `4 3`.
- **Actual** (`actual`): 2 px solid, `--series-1`, round caps, no point markers except the last
  sample (7 px dot, 2 px `--surface-raised` ring).
- Where `actual` falls outside the band, the gap between actual and the nearest band edge is
  filled at 18 % `--critical` — this is the one place the chart editorialises, and it is the whole
  point of the graphic.
- Gaps in data are **breaks in the line**, never interpolated across. A gap ≥3 samples gets a
  1 px `--viz-grid` hatch in the plot area and appears in the legend as "no data".
- Direct label the last value of each series at the right edge (2 series → 2 labels); no legend
  box needed at two series, but the chart title must name both ("Power: actual vs expected").

### 5.3 Residual strip

Always directly beneath the hero chart, sharing the identical x scale and left gutter. This
pairing is the substitute for a dual y-axis and it is why dual axes are banned.

- Height 88 px. Signed columns from a zero baseline, 1 px `--viz-axis` zero rule drawn above the
  marks.
- Fill from the diverging pair: below expected → `--series-1`; above expected → `--critical`;
  within ±1σ → `--border` (neutral). 2 px gap between adjacent columns; where the cadence makes
  columns sub-pixel, switch to a signed area.
- Right axis label: `RESIDUAL (Z)` at `--t-micro`. Horizontal guides at z = ±2 (1 px dashed
  `--viz-grid`) and z = ±3 (1 px dashed `--warn`), both labelled once at the right edge.
- Alternative mode toggled by a segmented control: `z` | `% of expected` | absolute unit. The
  toggle label states the current mode; the axis label changes with it.

### 5.4 Axes and labels

- Y axis: no axis line. 1 px horizontal gridlines in `--viz-grid`, **maximum 6**. Tick labels
  outside the plot, `--t-micro`, `--text-tertiary`, mono figures, right-aligned to the gutter.
- Y axis title: quantity + unit, `--t-micro` uppercase, top-left above the plot, not rotated.
  Rotated axis titles are banned.
- X axis: 1 px baseline in `--viz-axis`. Time ticks land on natural boundaries (00:00, 06:00,
  12:00, 18:00 for a week view). The **date appears once per day change**, the time on every
  tick; never repeat the date on every label.
- Zero inclusion: **mandatory** for magnitude quantities (power, energy, money, counts).
  Permitted to truncate for temperature, ratios and z-scores, and when truncated the axis carries
  a `⌁`-marked note "axis truncated" at `--t-micro` beside the lowest tick.
- Every chart has a title stating the subject and the measure. "Power" is not a title; "WT-017
  power: actual vs expected, last 7 days" is.
- Units appear in the axis title, not on every tick label.

### 5.5 Uncertainty

- A model estimate that has an interval is **never** drawn as a bare line. Band, whisker, or
  nothing.
- Point estimates with σ: 1 px whisker at ±1σ through the mark, cap 6 px.
- Probabilities (`risk_score`, `failure_probability`, `confidence`): the number, plus a 3 px
  track bar at 100 % width with the value filled and the **threshold marked by a 1 px vertical
  rule** in `--text-secondary`. The threshold's numeric value is printed beside the bar.
- `risk_window_days` renders as a shaded x-range on the timeseries (`--warn` at 10 %) with both
  bounds labelled: `7–21 d`. Never a single "predicted failure date".
- Anything not computed shows the null em-dash, and the chart shows a "partially evaluated"
  footnote naming the missing field. A chart never silently drops a null series.

### 5.6 Events on a time axis

Event kinds from the contract: `changepoint`, `alert`, `maintenance`, `curtailment`, `weather`,
`repair`.

- 1 px vertical rule, full plot height, at 55 % opacity, in the event's semantic colour:
  changepoint `--info`, alert `--warn` (or `--critical` at critical severity), maintenance
  `--text-tertiary`, curtailment `--info`, weather `--info`, repair `--ok`.
- A 7 px glyph in a 16 px gutter strip above the plot, with **shape carrying kind**: diamond =
  changepoint, triangle-up = alert, square = maintenance, circle = weather, vertical bar =
  curtailment, cross = repair. Shape is the primary channel; colour is secondary.
- Label on hover/focus only, in the shared tooltip. No floating callout balloons over the plot,
  no leader lines.
- Collision: when more than 3 events fall within 2 % of the plot width, collapse to a single
  count chip (`3`) that expands into a list on click.
- Events are keyboard reachable: the glyph strip is a single tab stop with left/right arrow
  traversal and the tooltip bound to focus, not only hover.

### 5.7 Interaction

- Line and area charts: a **crosshair plus one shared tooltip** showing every series at the
  hovered x, with the timestamp as the tooltip heading. Snap to the nearest sample. Hit area is
  the full plot height.
- Bar, dot and cell charts: per-mark tooltip, hit target at least 24 × 24 px.
- Tooltip: `--surface-raised`, 1 px `--border`, `--r-lg`, `--e-2`, `--sp-2` padding,
  `--t-small`, values in mono, max width 280 px. Never follows the cursor jitterily — it snaps
  to the sample and flips side at the plot edge.
- Brush-to-zoom on the hero chart only, with a visible "Reset range" control and the selected
  range printed as text.
- Filters (time range, signal) sit in **one row above** the chart, never inside the plot.

### 5.8 Colour-blind safety and what is banned

- Series slots assigned in fixed order 1→6, never cycled, never reassigned when a filter changes
  the series count. Colour follows the entity.
- ≥2 series → a legend is always present. ≤4 series → also direct-labelled. A single series needs
  no legend; the title names it.
- All-pairs forms (scatter, dot plot, small multiples, status grid) cap at **3 series**; direct
  labels are mandatory there.
- Every chart ships a **"View as table"** toggle rendering the same data as an accessible table.
  This is not optional; it is the accessibility fallback and the honesty fallback.
- A texture channel (45° / 135° line fill) must be available for stacked fills under
  `forced-colors`, print, and the accessibility setting.

**Banned outright:**

- Rainbow, viridis, turbo or any continuous ramp used for categories.
- Gradients as decoration. A gradient is permitted only as a band fill's opacity falloff, and
  only if it encodes uncertainty.
- 3D anything. Isometric bars, extruded pies, perspective.
- **Dual y-axes.** Two measures of different scale become two stacked charts sharing an x axis
  (this is exactly the hero + residual pairing). An exception requires a written justification in
  the component's docstring and sign-off in `docs/DECISIONS.md`.
- Pie and donut charts with more than two slices; radial progress rings; gauges; radar/spider.
- Area charts for anything that is not part-of-a-whole over time.
- Animated transitions on data refresh (the SSE tick must not re-animate the chart).
- Sparklines as decoration — see the prohibited-patterns list.
- A value label on every point. Label the first, last, extreme, and hovered points only.
- Any chart without a title, or with a legend but no title.

---

## 6. Component inventory

Every component: `web/components/<Name>/`. Props typed against the API contract's shapes. No
component fetches; data comes from a route-level loader.

Common contract for all of them: they accept `null` for any value and render the null em-dash;
they never render a placeholder number; they expose a `loading` and an `error` state.

### 6.1 App shell (`AppShell`)

Top bar 48 px + left rail 224 px + main. Top bar contains, left to right: product mark (a 20 px
wordmark "RAI" in Archivo 600, no logo graphic, no glowing orb), site switcher (`Kutch Wind
Farm` / `Charanka Solar Park` / `All sites`), a spacer, the `data_as_of` clock (mono, 12 px,
with a 6 px `--ok` dot when `data_freshness_s < 60`, `--warn` to 300 s, `--critical` beyond),
the Needle status chip (`needle2` / `deterministic reasoner` from `GET /api/health`), the
command-palette trigger (`⌘K`), and the theme toggle.

Rail: 5 nav items, `--t-body`, 32 px rows, 16 px icon + label, active item = `--accent-surface`
fill + 2 px `--accent` left stripe + 500 weight. Below them, a hairline, then a compact fleet
counter block (`42 assets · 3 at risk · 1 offline`). Routes:

| Route | Label | Primary object |
|---|---|---|
| `/` | Fleet | Priority queue + fleet metrics |
| `/assets/[id]` | Assets | Investigation view |
| `/simulator` | Simulator | Scenario console |
| `/soiling` | Soiling | Site soiling intelligence |
| `/knowledge` | Knowledge | Corpus search + document list |

Landmarks: `<header>`, `<nav aria-label="Primary">`, `<main>`, `<aside aria-label="Asset
context">`. Exactly one `<h1>` per route, matching the route's primary object.

### 6.2 Metric tile (`MetricTile`)

Panel, `--e-0`, `--sp-4` padding, min-height 92 px, min-width 168 px.

Layout, top to bottom, all left-aligned: label (`--t-micro`, `--text-secondary`, sentence case —
*not* uppercase, this is not a column header); value (`--t-metric`, mono 500, `--text-primary`)
with its unit inline in `--text-tertiary`; one delta or context line (`--t-small`,
`--text-secondary`) such as `expected 22,710 kW` or `+1.4 pts vs 24 h`.

Rules: no sparkline unless the tile's footer names the series and states its range. No icon. No
coloured background — a tile is never tinted by status; status lives in the value's colour only
when the value *is* a status. Delta sign always shown; delta colour is `--ok`/`--critical` only
when direction has a clear polarity, and is accompanied by a `▲`/`▼` glyph.

Fleet view tiles (exactly four): Fleet health (`fleet_health`, hero variant `--t-metric-lg`),
Generation vs expected (`generation_kw` / `expected_generation_kw`), Availability
(`availability_pct`), and modeled 30-day revenue exposure
(`revenue_at_risk_inr_30d`).

### 6.3 Priority action row (`PriorityRow`)

The most important row in the product: `GET /api/fleet/priority`. 64 px tall, full panel width,
1 px bottom `--border`, 3 px left stripe in the `risk_band` colour.

Grid: `[stripe] [asset 148px] [headline 1fr] [risk 120px] [revenue 112px] [deadline 96px]
[action 132px]`.

- Asset cell: `WT-017` mono 500 `--t-body` on line 1, `Turbine 17 · Kutch` `--t-small`
  `--text-tertiary` on line 2, with a 14 px asset-type glyph (turbine / inverter outline, 1.5 px
  stroke — **not** an emoji, not a filled icon tile).
- Headline: `headline` at `--t-body` `--text-primary`, plus `dominant_signal` humanised at
  `--t-small` `--text-tertiary`.
- Risk: status pill with band label, then the probability track bar (Section 5.5).
- Revenue: `₹1.55 L` right-aligned mono, `title` carrying the exact rupees.
- Deadline: `72 h` mono, amber ink below 24 h, critical below 6 h.
- Action: a single `Investigate` button (secondary style). When `requires_human_review` is true,
  the row instead shows a `Needs review` pill in `--warn-surface` before the button, and the
  button label becomes `Review`.

Rows are keyboard navigable with up/down; Enter opens the investigation.

### 6.4 Asset row (`AssetRow`)

Compact 28 px row for the 42-asset table. Columns: asset id (mono), name, type glyph, site,
status pill, `health_score` (mono, 1 dp), `risk_score` + 2 px inline track, `power_kw`,
`expected_power_kw`, residual % (signed, coloured by sign, with `▲`/`▼`), `operating_state`
pill, freshness dot. Left stripe 3 px in band colour. No action button — the whole row is the
link (`<tr>` wrapping an `<a>` on the id cell for a real keyboard target).

### 6.5 Evidence accordion (`EvidenceAccordion`)

The spine of the investigation view. One `<section>` per evidence layer in fixed order:
**Anomaly · Environment · Peers · History · Knowledge · Economics · Decision**.

Each header row: 40 px, `--surface-inset`, 1 px bottom `--border`, containing a 20 px stage
glyph, the stage name (`--t-body` 500), a one-line verdict summary (`--t-small`,
`--text-secondary`), a verdict pill, and a chevron. Body: `--sp-4` padding on
`--surface-raised`.

Behaviour: multiple sections open simultaneously (it is a ledger, not a wizard). Default open
state on load: Anomaly, Environment, Peers, Decision. Open/close animates height in 180 ms
`--ease-inout`. Each section ends in its source line. `aria-expanded`, `aria-controls`, and a
real `<button>` on the header. **Never nest an accordion inside an accordion.**

### 6.6 Signal residual card (`SignalResidualCard`)

One per `ResidualSignal`. Not a card in the SaaS sense — a 56 px ruled row inside the Anomaly
section, 1 px bottom `--border`, no border on the sides, no shadow, no radius.

Grid: `[signal name 1fr] [actual 96px] [expected 96px] [residual 96px] [z 72px] [trend 104px]
[bar 120px]`.

- Name humanised (`Gearbox oil temp`), unit in the column header.
- Actual / expected / residual: mono, right-aligned, residual signed.
- `z_score`: mono 500, signed; ink `--text-primary` below |2|, `--warn-ink` at |2|–|3|,
  `--critical` above |3|. A `▲`/`▼` glyph accompanies the colour.
- `trend_per_day`: signed value + unit + `/day`; when `trend_7d_per_day` differs in sign, show
  both with labels `24 h` and `7 d`.
- Bar: a 120 px signed track centred on zero, mark from the diverging pair, ±3σ marked by 1 px
  rules. This is the only inline chart permitted in a table row, and it is permitted because the
  scale is named and identical across rows.
- Rows sort by `|z_score|` descending; the dominant signal gets a 3 px `--accent` left stripe and
  the label `dominant`.

### 6.7 Investigation timeline (`InvestigationTimeline`)

`timeline[]` from the investigate response. Vertical, 1 px `--border` spine at x = 11 px, one
step per contract stage in emission order (`telemetry → expected_behavior → environment → peers
→ history → knowledge → economics → decision`).

Per step: a 22 px node on the spine — `pending` = 7 px hollow ring `--border-control`,
`running` = 7 px ring in `--accent` with a 1 px rotating arc (the **only** looping animation in
the product, and only while a request is in flight), `done` = 9 px filled `--accent` disc with a
7 px check, `skipped` = 7 px hollow ring `--text-tertiary` with a 1 px diagonal. Then the stage
label (`--t-body` 500), `detail` (`--t-small`, `--text-secondary`), and elapsed ms (mono,
`--t-micro`, `--text-tertiary`) right-aligned.

Motion: steps arrive as the response streams (or, for a non-streaming response, are revealed on a
70 ms stagger): opacity 0→1 and `translateY(4px)→0` over 180 ms `--ease-out`, **once**. Never
replayed on re-render. Under `prefers-reduced-motion` the translate is dropped and the stagger
becomes 0.

The timeline is `<ol>` with `aria-live="polite"` on the list so a screen reader hears each stage
as it completes.

### 6.8 Confidence indicator (`ConfidenceIndicator`)

Three parts, always all three: the number (`0.87`, mono `--t-metric`), a 4 px track bar with the
fill in `--accent` and a 1 px `--text-secondary` threshold rule at `needle_confidence_threshold`,
and a verdict label — `Above threshold (0.80)` or `Below threshold (0.80) — human review
required`. When below threshold the whole component sits on `--warn-surface` with a 1 px `--warn`
border and a 14 px warning glyph. Colour is never the only signal: the label always states the
comparison in words.

Beneath it, `model_used` and `fallback_used` are printed as plain text:
`needle2` / `deterministic reasoner (fallback)`. The demo depends on this being honest.

### 6.9 Historical case card (`HistoricalCaseCard`)

A bordered block (`--e-0`, `--r-md`, `--sp-4`) — this is one of only two places a genuine card is
allowed, because a case is a separable object. **Never nested inside another card.**

Header: `CASE-0031` (mono 500) · similarity as a 3 px 0–1 track + `0.93` · component pill.
Body: `fault_mode` humanised at `--t-body` 500; `observed_signature[]` as up to 4 chips
(`--surface-sunken`, `--r-sm`, `--t-small`, mono numerals); `outcome` as prose at `--t-prose`
inside the 62ch measure; then a 2-column footer of `lead_time_days` and `repair_cost_inr`.
Footer strip: `source` verbatim (`synthetic_case_library`) at `--t-micro` — the corpus is
labelled as synthetic everywhere it appears, without exception.

### 6.10 Citation block (`CitationBlock`)

Not a card. A ruled block with a 2 px `--border-strong` left rule (a quotation device, matching
the ledger idiom).

Line 1: `title` (`--t-body` 500) · `section` (`--t-small`, `--text-secondary`).
Line 2: `snippet` in `--t-prose`, `--text-secondary`, max 62ch, with the matched query terms
marked by `<mark>` at `--accent-surface` background and `--text-primary` ink (no bold, no colour
change to the term itself).
Line 3: `doc_id` (mono `--t-micro`), `retrieval` method (`fts5`), `score` (mono, 2 dp), and a
`Open document` link. The retrieval method and score are always shown — a citation without its
score is not a citation.

A standing footnote under any citation group: *"Sample corpus authored for this project;
illustrative, not a manufacturer document."*

### 6.11 Economic option comparison (`EconomicComparison`)

A 3-row comfortable table (40 px rows) where each row carries a stacked horizontal bar. This is
the money moment of the demo; it must be legible from three metres.

Columns: `[option label 176px] [bar 1fr] [expected exposure 112px] [p(failure) 88px]`.

- Bar segments in fixed slots: `intervention_cost_inr` → `--series-1`, `energy_loss_inr` →
  `--series-2`, `failure_escalation_inr` → `--series-5`. 2 px `--surface-raised` gap between
  segments. All three rows share one x scale, and that scale's maximum is printed at the axis.
- `expected_exposure_inr` right-aligned mono, the row total labelled at the end of the bar.
- The row whose `option_id === recommended_option_id` carries a 3 px `--accent` left stripe and a
  `Recommended` pill; it is not re-ordered to the top (order stays `repair_now`, `defer_7d`,
  `defer_14d` so the reader sees the cost of delay increase down the column).
- Below the table: `avoidable_exposure_inr` as a `--t-metric-lg` hero value with the label
  "Avoidable exposure if actioned now", and a collapsed `Assumptions` disclosure listing every
  key of `assumptions` plus `tariff_inr_per_kwh`. **The assumptions disclosure is mandatory** —
  these are modelled figures and the UI says so.
- Legend always present (3 segments).

### 6.12 Scenario control (`ScenarioControl`)

The simulator console's input. A bordered panel with a field stack, not a modal.

Fields: asset (combobox over `/api/assets`), scenario (select over
`/api/simulator/scenarios`, grouped into **Equipment faults** and **Environmental / sensor**,
each option showing `expected_detection`), severity (slider 0.1–1.0, step 0.05, with the numeric
value in mono beside it and tick labels at 0.1 / 0.5 / 1.0), acceleration (segmented control:
`1×` `10×` `60×`), duration days (number input, 1–30).

Actions: primary `Inject scenario`, secondary `Reset asset`, tertiary `Reset all` (which requires
a confirm step). After injection, the returned `ground_truth` block renders in a
`--info-surface` strip labelled **Ground truth (simulator only — never shown to the agent)**.
That label is required; it is the honesty guarantee of the whole demo.

Inputs: 28 px height, `--r-sm`, 1 px `--border-control`, focus per Section 7.

### 6.13 Status pill (`StatusPill`)

The single carrier of categorical state. 20 px tall, `--r-sm`, `--sp-1`/`--sp-15` padding,
`--t-small` 500, and **always** three elements: a 8 px shape, a text label, a tint background.

| State | Shape | Ink | Background |
|---|---|---|---|
| `low` / nominal / `ok` | filled circle | `--ok` | `--ok-surface` |
| `elevated` | filled square | `--warn-ink` | `--warn-surface` |
| `high` | filled triangle-up | `--warn-ink` | `--warn-surface` |
| `critical` | filled diamond | `--critical-ink` | `--critical-surface` |
| `informational` | hollow circle | `--info` | `--info-surface` |
| `curtailed` / `night` / `below_cutin` | hollow square | `--info` | `--info-surface` |
| `stopped` / `failed` | filled diamond | `--critical-ink` | `--critical-surface` |
| `maintenance` | hollow diamond | `--text-secondary` | `--surface-sunken` |
| `suspect` | half-filled circle | `--warn-ink` | `--warn-surface` |
| `not evaluated` | hollow circle, dashed | `--text-tertiary` | `--surface-sunken` |

The shape differs per state, so the pill survives greyscale, protanopia and a monochrome print.
The label text is the enum value humanised — never abbreviated to a letter.

Verdict pills reuse the same component: `environmental` → `--info` hollow circle;
`partial` → `--warn-ink` square; `not_environmental` → `--critical-ink` diamond;
`asset_specific` → `--warn-ink` triangle; `fleet_wide` → `--info` square; `normal` → `--ok`
circle.

### 6.14 Empty state (`EmptyState`)

Centred in its panel, `--sp-12` vertical padding, max 46ch. A 24 px line glyph in
`--text-tertiary` (never an illustration, never an emoji), a `--t-lead` sentence naming the
situation, a `--t-prose` line naming the cause and the fix, and at most one action button.

Required variants, with exact copy:

| Situation | Heading | Body | Action |
|---|---|---|---|
| No assets at risk | `No assets need action` | `All 42 assets are within their expected bands. The queue refreshes every 5 seconds.` | — |
| Not evaluated | `Not evaluated` | `The risk model has not been trained on this asset yet, so no score exists. Run scripts/train_models.py, then reload.` | `View evaluation report` |
| No similar cases | `No similar historical cases` | `No past episode in the case library matches this trajectory above the 0.60 similarity floor.` | — |
| No citations | `No matching documents` | `No passage in the maintenance corpus matched this evidence. The corpus holds 18 sample documents.` | `Browse corpus` |
| Search no results | `No results for "<query>"` | `Try a component name (gearbox, inverter) or a symptom (vibration, derate).` | — |

Empty-state copy never apologises, never says "Oops", and never contains placeholder or lorem
text. The demo path must show real copy in every state it can reach.

### 6.15 Loading skeleton (`Skeleton`)

Shape-matched to the content it replaces — a table skeleton is rows of bars at the real column
widths, not a grey blob. Fill `--surface-sunken`, `--r-sm`, bar heights 10 px (text) / 20 px
(value) / the real height (chart). Shimmer: a 1200 ms linear translate of a 20 %-opacity
`--surface-raised` band; under `prefers-reduced-motion` it becomes a static tint with no
animation.

Rules: skeletons only for the **first** load of a region. A refresh keeps the previous values in
place and marks the region `aria-busy="true"` with a 2 px top progress rule — data must never
flash to skeleton on a poll tick. Maximum skeleton lifetime 8 s, after which the error state
takes over.

### 6.16 Error state (`ErrorState`)

Consumes the contract error shape `{detail, code}`. Panel-scoped, never a full-page takeover
(one failing endpoint must not blank the screen).

Layout: 1 px `--critical` border, `--critical-surface` tint on a 32 px header strip carrying a
14 px glyph and the mapped title; body gives `detail` verbatim in `--t-prose`, then the `code` in
mono `--t-micro`, then one `Retry` button.

| `code` | Title | What the body adds |
|---|---|---|
| `asset_not_found` | `Asset not found` | the id that was requested |
| `signal_not_found` | `Signal not available for this asset` | the signal list that is available |
| `scenario_not_found` | `Unknown scenario` | link to the scenario list |
| `model_not_trained` | `Model not trained` | the training command to run |
| `index_not_built` | `Knowledge index not built` | the index-build command to run |
| `agent_unavailable` | `Agent unavailable` | that the deterministic reasoner is the fallback |
| network / timeout | `Cannot reach the API` | `Expected http://127.0.0.1:8000. The API route layer is still in progress; use the command-line demo meanwhile.` |

Errors state what happened and what to do. They do not apologise and they never invent a cause.

### 6.17 Source line (`SourceLine`) — required on every panel

24 px strip, 1 px top `--border`, `--t-micro`, `--text-tertiary`, mono for the path.
Content: the endpoint that produced the panel's numbers, ` · `, the method or model, ` · `, the
`as_of` timestamp. Example:

```
/api/assets/WT-017 · risk: xgboost + isotonic calibration · as of 12 Sep 06:40 IST
```

If a panel shows a modelled or assumed figure (all economics, all soiling projections), the
source line ends with ` · assumption` and the figure is additionally reachable through the
Assumptions disclosure. A panel with no source line is an incomplete panel.

---

## 7. Accessibility

**Contrast minimums (all measured values are in Section 1 and were computed, not estimated).**

- Body and value text: **≥ 4.5:1** against its own background. Every text token in Section 1
  meets this; `--text-tertiary` at 4.64:1 is the floor and is why it is used for units and axis
  labels rather than anything lighter.
- Non-text UI boundaries and meaningful graphics (control borders, chart marks, focus rings,
  status shapes): **≥ 3:1**. `--border-control` (3.15:1 light, 3.07:1 dark), `--warn` (3.03:1)
  and `--viz-expected` (3.66:1) are the constrained cases and were chosen at those values
  deliberately.
- Decorative hairlines (`--border`, `--viz-grid`) are exempt because removing them loses no
  information — every boundary they draw is also carried by spacing or a label.
- Disabled controls are exempt from contrast but must carry `aria-disabled="true"` and a text
  reason on hover/focus.

**Focus.** `:focus-visible` gets `outline: 2px solid var(--accent); outline-offset: 2px;
border-radius: inherit`. On `--accent-surface` backgrounds the ring switches to
`--text-primary`. Every interactive element has a visible ring — table rows, chart event glyphs,
accordion headers, pills that act as filters. `outline: none` without a replacement ring is
prohibited. Focus is never removed on mouse users via `:focus { outline: none }`.

**Keyboard paths.** These must work without a mouse:

| Path | Keys |
|---|---|
| Fleet queue → investigate the top asset | `Tab` to queue, `↓` through rows, `Enter` |
| Skip to content | `Tab` on load hits a visually-hidden `Skip to main content` link |
| Command palette | `⌘K` / `Ctrl+K`, type asset id, `Enter`; `Esc` closes and restores focus |
| Evidence accordion | `Tab` between headers, `Enter`/`Space` toggles, `↓`/`↑` moves header focus |
| Chart events | `Tab` to the event strip, `←`/`→` between events, tooltip follows focus |
| Chart to table | `Tab` to `View as table`, `Enter` |
| Signal table sort | `Tab` to header button, `Enter`; `aria-sort` announces the new order |
| Simulator | full form tab order; `Enter` in any field submits `Inject scenario` |
| Modal / popover | focus trapped, `Esc` closes, focus returns to the trigger |

**Semantics.** `<header>` / `<nav aria-label="Primary">` / `<main>` / `<aside>` / `<footer>`; one
`<h1>` per route; heading levels never skipped. Tables are real `<table>` with `<caption>` (may
be visually hidden), `<th scope="col">`, and `aria-sort`. The priority queue is a table, not a
list of divs. Charts are `role="img"` with an `aria-label` that states the finding in a sentence
("WT-017 power, last 7 days: actual 9.4 % below expected, outside the expected range since 11 Sep
11:40 UTC") plus the mandatory table fallback.

**Live updates.** The SSE feed updates a single `aria-live="polite"` summary node
("Fleet health 87.4, 3 assets at risk") at most once every 10 s. Individual cells are **not**
live regions — a 42-row table with live cells is unusable with a screen reader.

**Colour is never the only carrier of meaning.** Every status has a shape and a text label
(Section 6.13). Every signed number has a sign and a `▲`/`▼` glyph. Every chart series has a
direct label or a legend entry. Every threshold breach is stated in words, not only implied by a
colour change. Test: the screen must be fully readable as a greyscale print-out.

**Motion and reduced motion** are covered in Section 8. Target sizes: interactive targets ≥ 24 ×
24 px; the 28 px compact table row is met by making the whole row the target.

---

## 8. Motion

Animation exists to show what changed. If it does not aid comprehension, it does not ship.

```css
:root {
  --motion-fast: 120ms;
  --motion-base: 180ms;
  --motion-slow: 260ms;
  --motion-stagger: 70ms;
  --ease-out: cubic-bezier(0.16, 1, 0.30, 1);
  --ease-inout: cubic-bezier(0.40, 0.00, 0.20, 1);
  --ease-in: cubic-bezier(0.40, 0.00, 1.00, 1);
}
```

| What | Property | Duration | Easing | Notes |
|---|---|---|---|---|
| Investigation timeline step arriving | opacity 0→1, `translateY(4px)→0` | 180 ms | `--ease-out` | 70 ms stagger, **once per run**, never on re-render |
| Timeline `running` node | 1 px arc rotation | 900 ms linear, loops | linear | The only loop in the product; stops the moment the stage resolves |
| A value changing in place | opacity cross-fade 1→0.4→1 | 120 ms | `--ease-inout` | No odometer, no digit roll, no count-up |
| Chart primary series draw | `stroke-dashoffset` | 420 ms | `--ease-out` | **Once on mount only.** Never on refresh, never on a poll tick |
| Accordion open/close | `height`, opacity | 180 ms | `--ease-inout` | `content-visibility` to avoid layout thrash |
| Popover / dropdown / tooltip | opacity + `scale(0.98)→1` | 120 ms | `--ease-out` | Exit 90 ms `--ease-in` |
| Modal / command palette | opacity + `translateY(6px)→0`, backdrop opacity | 180 ms | `--ease-out` | Backdrop `--surface` at 60 % |
| Skeleton shimmer | `translateX` | 1200 ms linear, loops | linear | Only while pending; replaced by a static tint under reduced motion |
| Row / pill hover | `background-color` | 120 ms | `--ease-inout` | Colour only — never transform, lift, scale or shadow |
| Tab / segment selection | indicator `transform` | 180 ms | `--ease-inout` | |

**Banned:** hover lift on rows, cards or tiles; parallax; scroll-triggered reveals; page
transitions; autoplaying carousels; looping ambient motion of any kind other than the two loops
named above; spring/bounce physics on layout; animated counters; a chart re-animating on data
refresh; anything that moves while a person is reading a number.

**Reduced motion is a requirement, not a nicety:**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Plus these component-level behaviours: the timeline still reveals steps but with opacity only and
zero stagger; the chart draw is skipped and the final path renders immediately; the skeleton
shimmer becomes a static tint; the `running` arc becomes a static ring plus the text `running`.
No information is ever conveyed only by motion.

---

## 9. Responsive

Four widths are tested. 1440 × 900 is the design target.

| Width | Shell | Fleet view | Investigation view |
|---|---|---|---|
| **1440 × 900** (target) | 224 px rail + 380 px context rail | 4 metric tiles in one row; priority queue `8`, fleet context `4` | Evidence ledger `7`, chart column `5`; hero chart 280 px |
| **1280 × 800** | 224 px rail, context rail collapses into a tab below the ledger | 4 tiles in one row (tiles shrink to 168 px min); queue full width, fleet context moves below | Single column: chart block first, then ledger. Hero chart 280 px, full width |
| **1024 × 768** (tablet) | 64 px icon rail, labels on hover/focus and in a tooltip | 2 × 2 tiles; queue drops the `deadline` column into the asset cell's second line | Single column; residual strip stays (it is the point) |
| **390 × 844** (phone) | Rail → 4-item bottom bar; top bar keeps clock + theme only | Tiles become a 2 × 2 grid of 72 px tiles; **the queue becomes stacked cards** | Sections collapse; only Anomaly and Decision open by default |

**How the fleet table reflows.** The 42-asset table is a real table down to 1024 px, shedding
columns in this exact priority order as width is lost: `expected_power_kw`, `capacity_factor`,
`data_freshness_s` (moves to a dot on the row), `operating_state` (moves into the status pill's
tooltip), `site`. Below 768 px it stops being a table: each asset becomes a 96 px stacked block
carrying asset id + name, the status pill, `health_score`, and the signed residual — four facts,
the same four in every block, with `power_kw` and the rest behind a `Details` tap. The reflow is
a real DOM change (a `<table>` at ≥768 px, a `<ul>` of blocks below), not a CSS trick that leaves
a table semantically horizontal for a screen reader.

**How the investigation view reflows.** At ≥1440 px it is three columns: ledger, charts, context
rail. At 1280 px the context rail's contents (asset facts, peer list, operating state) fold into
a `Context` section appended to the ledger, and the layout becomes chart column above, ledger
below — charts first because the hero chart is the argument. At 1024 px the residual strip stays
(dropping it would remove the discrimination evidence) but the peer dot plot switches from a
horizontal value axis to a compact ranked list with an inline bar. At 390 px: the verdict
headline, the confidence indicator, the hero chart at 220 px with the residual strip at 72 px,
then the accordion with Anomaly and Decision open, everything else collapsed. The economic
comparison's bars remain — they stack to full width with the labels above each bar instead of
beside it.

Horizontal page scroll is prohibited at every width. Only three things may scroll horizontally,
each inside its own `overflow-x: auto` container with a visible edge fade: a wide table, a wide
chart, a code block.

---

## 10. Prohibited patterns

Stated bluntly, because these are the defaults the interface must not fall into. A pull request
containing any of these is rejected without discussion.

1. **No purple-to-blue gradient hero.** No gradient hero of any hue. The fleet view opens on a
   metric row and a work queue.
2. **No card inside a card inside a card.** Maximum nesting is one bordered container deep. A
   panel contains rows, tables, charts and ruled blocks — not more panels. The only nested
   bordered elements permitted are the historical case card and the citation block, and neither
   may contain another.
3. **No giant centred chatbot.** There is no conversational surface in this product. The agent's
   output is a structured verdict rendered as a ledger. No message bubbles, no input box waiting
   for a question, no typing indicator.
4. **No glowing orb, no animated AI mark, no pulsing gradient blob, no particle field, no
   aurora background.** The Needle status is a text chip.
5. **No rounded-square icon tiles.** No 40 × 40 tinted square with a centred glyph. Icons are
   1.5 px stroke line glyphs at 14/16/20 px, inline, unboxed, in a text colour.
6. **No emoji as iconography.** Not in the UI, not in labels, not in status, not in empty states,
   not in code. The status vocabulary is the ten shapes in Section 6.13.
7. **No unexplained sparkline decoration.** A sparkline appears only when its series is named and
   its y range is stated. A sparkline that exists to fill space is deleted.
8. **No animated counters.** Numbers cross-fade in 120 ms. Nothing counts up from zero, ever —
   most of all not money, where a rolling digit reads as a slot machine.
9. **No placeholder or lorem text on the demo path.** Every string a judge can reach is real
   product copy. No "Lorem ipsum", no "Coming soon", no "Chart goes here", no `TODO`, no dummy
   asset named "Asset 1".
10. **No decorative full-bleed imagery.** No stock photo of a wind farm, no hero video, no
    turbine silhouette watermark.
11. **No tracked-out all-caps eyebrow labels** above headings, and no `A · B · C` middle-dot meta
    strings outside the source line.
12. **No fake precision.** No number with more decimal places than the model supports, no
    "99.99 % accurate", no metric that did not come from an executed evaluation run. A metric
    that has not been computed shows the null em-dash and the words "not evaluated".
13. **No colour-only status**, no dual y-axes, no rainbow categorical ramps, no 3D, no gauges —
    see Section 5.8.
14. **No skeleton on refresh**, no layout shift when data arrives, no content jumping because a
    number got wider (reserve width with `tabular-nums` and a `min-width` on numeric columns).

---

## 11. Screen specifications

Enough detail to build; every field name below exists in `docs/API_CONTRACT.md`.

### `/` — Fleet command

`h1`: "Fleet". Sources: `GET /api/fleet`, `GET /api/fleet/priority`, `GET /api/assets`,
`GET /api/health`.

1. Metric row — 4 `MetricTile` (Section 6.2).
2. **Priority action queue** — panel titled "Action queue", `PriorityRow` list. This is the
   highest object on the page after the tiles and it is the reason the screen exists. Empty state:
   "No assets need action".
3. Two-up below: **Generation vs expected** (hero chart form, fleet aggregate, 7 days) and
   **Fleet status grid** (42 labelled cells, status by fill + shape, 3-series cap does not apply
   because it is a status encoding not a categorical one; each cell is a link).
4. Full asset table — `AssetRow`, compact, sortable, filterable by type/site/band.

### `/assets/[id]` — Investigation

`h1`: the asset name + id. Sources: `GET /api/assets/{id}`, `/timeseries`, `/peers`, `/cases`,
`/economics`, `POST /investigate`.

Header block: asset id + name + type glyph, site, `operating_state` pill, `health_score`
(`--t-metric-lg`), `risk_band` pill, `data_freshness_s` dot, and the primary action
**`Why?`** — which is the label on the investigate button, because that is the question the
operator is asking. Secondary: `Compare with peers`, `Create inspection ticket` (disabled until a
verdict exists).

Then, in order: verdict headline (`--t-display`, the `likely_cause`) + `ConfidenceIndicator` +
`recommended_action` with `action_deadline_hours`; `InvestigationTimeline`; hero chart + residual
strip; `EvidenceAccordion` with all seven sections; context rail (asset facts, peer dot plot,
environment conditions table).

Before an investigation has been run, the verdict block shows the "Not evaluated" empty state and
the `Why?` button is the only enabled action. The verdict is never pre-filled with a guess.

### `/simulator` — Scenario console

`h1`: "Simulator". `ScenarioControl` on the left (`5` columns), a live chart of the injected
asset on the right (`7`), the scenario catalogue table below with the
`is_equipment_fault` / `expected_detection` columns visible — this table is what makes the
environmental-discrimination demo legible, so it is not hidden behind a disclosure.

### `/soiling` — Soiling intelligence

`h1`: "Soiling". Site tiles (`site_soiling_loss_pct`, `dust_risk`, `days_since_rain`,
`rain_probability_48h`), the recommendation block (action, `wait_hours`, `rationale`,
`breakeven_days` — rationale rendered as prose in the 62ch measure), and the zone table with a
sequential block grid. `cleaning_cost_inr` is shown with its assumption footnote.

### `/knowledge` — Corpus

`h1`: "Knowledge". Search field (debounced 250 ms), `CitationBlock` results, document list from
`/api/knowledge/docs` with `source_note` displayed in full on every row. The synthetic-corpus
footnote is permanent on this page.

---

## 12. Build checklist

Before a view is called done:

- [ ] Every number traces to a named API field; no number is computed in the component.
- [ ] Every `null` renders the em-dash with "not evaluated", verified by forcing a null.
- [ ] Every panel has a source line.
- [ ] Every chart has a title, an axis unit, a legend (≥2 series), and a working "View as table".
- [ ] Keyboard-only pass completes the path in Section 7 with a visible focus ring at every stop.
- [ ] Greyscale screenshot pass: every status still readable.
- [ ] `prefers-reduced-motion: reduce` pass: nothing moves except ≤100 ms opacity.
- [ ] 1440 / 1280 / 1024 / 390 pass with no horizontal page scroll.
- [ ] Dark theme pass — correct, even though the demo is light.
- [ ] Grep the diff for each prohibited pattern in Section 10.
