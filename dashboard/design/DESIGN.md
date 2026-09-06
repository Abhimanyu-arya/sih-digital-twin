---
name: AeroSCADA Telemetry Core
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d1f27'
  surface-container-high: '#272a32'
  surface-container-highest: '#32353d'
  on-surface: '#e1e2ec'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2d3038'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb95f'
  on-tertiary: '#472a00'
  tertiary-container: '#e79400'
  on-tertiary-container: '#563400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353d'
typography:
  display-lg:
    fontFamily: JetBrains Mono
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.01em
  display-md:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 24px
    letterSpacing: 0.04em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  body-default:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-compact:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  telemetry-data:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  telemetry-unit:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-code:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.08em
  label-micro:
    fontFamily: JetBrains Mono
    fontSize: 9px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.12em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit-2xs: 0.125rem
  unit-xs: 0.25rem
  unit-sm: 0.5rem
  unit-md: 0.75rem
  unit-lg: 1rem
  unit-xl: 1.5rem
  gutter-dense: 0.5rem
  gutter-panel: 0.75rem
  frame-pad: 1rem
---

## Brand & Style
This design system defines an industrial avionics and supervisory control and data acquisition (SCADA) interface for autonomous unmanned aerial vehicle (UAV) fleet telemetry, diagnostics, and mission control. 

The aesthetic is precision-engineered, brutalist-technical, and ultra-functional. It prioritizes low-cognitive-load scanning, immediate situational awareness, and zero ambiguity under high-stress command conditions. Interfaces avoid decorative illustrations, whimsical micro-interactions, or soft ambient diffusion. Surfaces are disciplined, flat, and compartmentalized through structural bordered grids, technical readouts, and unmistakable state signaling. The operational atmosphere is authoritative, tactical, and uncompromisingly precise.

## Colors
The color architecture relies on an extreme-contrast, pitch-tier dark mode designed to prevent eye fatigue in low-light tactical operations while rendering luminescent signal states with instantaneous recognition.

### Palette Architecture
- **Base Surfaces:**
  - `bg-void`: `#0A0D14` (Deepest canvas backing, master display root)
  - `surface-base`: `#0F141F` (Primary container, module panel background)
  - `surface-elevated`: `#151C2C` (Interactive cells, table headers, drawer panels)
  - `surface-overlay`: `#1E283D` (Active states, dropdowns, selected rows)
- **Structural Lines:**
  - `border-subtle`: `#1E293B` (Module boundaries, internal row divisions)
  - `border-strong`: `#334155` (Panel separators, active container frames)
  - `border-focus`: `#06B6D4` (Keyboard focus rings, selected channel frames)
- **Operational Status Accents:**
  - **NOMINAL:** `#10B981` (Telemetry lock, subsystem healthy, normal range)
  - **DEGRADED / CAUTION:** `#F59E0B` (Packet drop, thermal threshold warning, non-critical deviation)
  - **CRITICAL / ALERT:** `#EF4444` (Link loss, actuator failure, stall warning, emergency abort)
  - **TELEMETRY & VECTOR:** `#06B6D4` (Active flight vectors, scrubbers, real-time wave indicators)
- **Monochrome & Text:**
  - `text-primary`: `#F8FAFC` (High-visibility metrics, active labels, primary telemetry readouts)
  - `text-secondary`: `#94A3B8` (Engineering units, metadata, secondary captions)
  - `text-muted`: `#475569` (Inactive status, disabled toggles, timestamp prefixes)

Dynamic states use a 10% opacity tint of each respective status color for background badging (e.g., `#10B9811A` for nominal metric fills), ensuring the primary text glyph retains near-luminescent clarity.

## Typography
The typographic hierarchy implements a tripartite structure:
1. **Space Grotesk** serves as the system structural header font, bringing angular, military-spec geometry to module frames, card titles, and section markers. Always styled in uppercase for titles below 16px.
2. **JetBrains Mono** powers all numerical data, status indicators, telemetry scrubbers, payload readouts, and timestamps. It enforces tabular lining figures so metrics never cause horizontal layout jitter during real-time scalar fluctuations.
3. **Inter** handles narrative descriptions, operator logs, warning runbooks, and dense system documentation, ensuring high legibility at micro-scales.

All telemetry numbers must display with fixed decimal places matching sensor precision (e.g., `+024.582°` or `008.400 kPa`).

## Layout & Spacing
The layout model employs a strict, full-bleed 12-column or 24-column CSS Grid architecture that optimizes visual density. Whitespace is compressed; unused space is considered lost tactical real estate.

- **Desktop (Multi-Screen Mission Control / 1920px+):** Fixed full-viewport canvas (`100vh`) with zero window scroll. Interface organizes into docked sub-panels: Telemetry Horizon Left (3 cols), Tactical Map & Geofence Center (6 cols), Diagnostics & Comm Rig Right (3 cols), Scrubber & Command Stream Bottom (fixed 180px height).
- **Console / Laptop (1280px - 1919px):** Fluid re-docking where subsidiary telemetry shelves collapse into tabbed panels or secondary drawers.
- **Field Rugged Tablet (768px - 1279px):** 2-column stacked operational grid with 44px minimum touch targets on override switches.
- **Rhythm:** An ultra-compact 4px baseline sub-grid drives all internal paddings (`unit-xs` for metric-to-unit offsets, `unit-sm` for badge borders, `unit-md` for standard card interiors).

## Elevation & Depth
This system eliminates soft drop shadows, blurs, and skeuomorphic gradients. Elevation is communicated strictly through planar surface tinting and structural borders:

- **Level 0 (Backdrop):** `#0A0D14` – Raw background canvas, base viewport grid.
- **Level 1 (Module Shell):** `#0F141F` with a 1px solid border (`#1E293B`). Forms the perimeter for all telemetry blocks and radar scopes.
- **Level 2 (Active Sub-Cell / Interactive Plate):** `#151C2C` with a 1px solid border (`#334155`). Used for parameter inputs, selected flight paths, or hovered metric zones.
- **Level 3 (Modal / Tactical Override Overlay):** `#151C2C` elevated with a hard, 2px structural outline in `#06B6D4` or `#EF4444` (depending on urgency). Shadows are forbidden except for a high-intensity 4px color perimeter stroke (`box-shadow: 0 0 0 1px #EF4444, inset 0 0 8px #EF444433`) reserved exclusively for Class-A emergency alerts.

## Shapes
Geometry is utilitarian and hard-edged. All standard containers, badges, and buttons utilize either sharp right angles (`0px`) or an ultra-tight `2px` to `4px` maximum corner radius (`roundedness: 1`). 

Interactive buttons feature chamfered-style visual anchors or crisp 2px square corner ticks in the upper-left and lower-right borders to evoke avionics HUD target reticles. Pill-shapes, rounded bubbly overlays, and soft circular controls are strictly prohibited.

## Components

### Buttons & Tactical Triggers
- **Standard Action:** Background `#151C2C`, 1px border `#334155`, text `#F8FAFC`, font `JetBrains Mono` 12px bold uppercase. Hover: border `#06B6D4`, text `#06B6D4`.
- **Command / Arm State (Armed/Execute):** Two-step interaction. Neutral: `#EF44441A` fill with `#EF4444` 1px solid border. Active/Engaged: `#EF4444` solid fill with `#0A0D14` bold text, pulsing with a 1Hz keyframe flash.
- **Micro Action Buttons:** Height 24px, padding 0 8px, 0px border radius, monospaced 10px uppercase.

### Status Chips & Badges
- Constructed with a 1px border, 2px corner radius, and monospaced typography (`label-micro`).
- Layout: Small 6px square status pip on the left, followed by the uppercase state (`NOMINAL`, `DEGRADED`, `CRITICAL`).
- **Nominal:** Border `#10B981`, background `#10B9811A`, pip `#10B981`.
- **Caution:** Border `#F59E0B`, background `#F59E0B1A`, pip `#F59E0B`.
- **Critical:** Border `#EF4444`, background `#EF444426`, pip `#EF4444`, font weight bold.

### Metric Cards & Telemetry Blocks
- Structure: Header row containing parameter label (`Space Grotesk` 11px uppercase tracking 0.08em) and subsystem status icon; body displaying real-time numerical metric (`JetBrains Mono` 24px) paired inline with engineering unit (`JetBrains Mono` 11px muted); footer containing sparkline canvas or threshold range bar.
- Perimeter: 1px continuous border (`#1E293B`). When metrics cross safety limits, the entire card perimeter changes to `#EF4444` or `#F59E0B`.

### Telemetry Scrubber & Time Series Graphs
- Background: `#0A0D14`.
- Gridlines: `#1E293B` dotted at 100ms / 1-second intervals.
- Vector lines: 1.5px solid `#06B6D4` with zero anti-aliasing blur. Scrubber needle: 1px `#F8FAFC` line topped with a cyan inverted triangle marker.

### Input Fields & Toggles
- Inputs feature sunken fills (`#0A0D14`), 1px borders (`#334155`), and mono text in `#F8FAFC`. Active focus switches border to `#06B6D4` with no fuzzy outer glow.
- Toggles utilize rectangular slide blocks (not rounded lozenges) with binary `0` / `1` or `ARM` / `SAFE` internal monospaced indicators.

### Data Tables & Event Logs
- Row height: 26px (ultra-dense).
- Alternating row background: `#0F141F` and `#121824`.
- Timestamps locked to `YYYY-MM-DD HH:mm:ss.SSS` in `#94A3B8`.
- Column separators: 1px vertical borders (`#1E293B`).