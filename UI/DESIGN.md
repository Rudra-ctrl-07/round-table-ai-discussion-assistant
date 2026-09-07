---
name: Round Table Research System
colors:
  surface: '#f9f9ff'
  surface-dim: '#d3daef'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e1e8fd'
  surface-container-highest: '#dce2f7'
  on-surface: '#141b2b'
  on-surface-variant: '#44474c'
  inverse-surface: '#293040'
  inverse-on-surface: '#edf0ff'
  outline: '#74777d'
  outline-variant: '#c4c6cd'
  surface-tint: '#4f6073'
  primary: '#041627'
  on-primary: '#ffffff'
  primary-container: '#1a2b3c'
  on-primary-container: '#8192a7'
  inverse-primary: '#b7c8de'
  secondary: '#5a5f62'
  on-secondary: '#ffffff'
  secondary-container: '#dce0e4'
  on-secondary-container: '#5e6367'
  tertiary: '#001918'
  on-tertiary: '#ffffff'
  tertiary-container: '#00302e'
  on-tertiary-container: '#00a29e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4fb'
  primary-fixed-dim: '#b7c8de'
  on-primary-fixed: '#0b1d2d'
  on-primary-fixed-variant: '#38485a'
  secondary-fixed: '#dfe3e7'
  secondary-fixed-dim: '#c3c7cb'
  on-secondary-fixed: '#171c1f'
  on-secondary-fixed-variant: '#43474b'
  tertiary-fixed: '#72f7f1'
  tertiary-fixed-dim: '#50dad5'
  on-tertiary-fixed: '#00201f'
  on-tertiary-fixed-variant: '#00504d'
  background: '#f9f9ff'
  on-background: '#141b2b'
  surface-variant: '#dce2f7'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  panel-gutter: 1px
  container-max: 1440px
---

## Brand & Style

The design system is anchored in the concept of "Analytical Clarity." It targets researchers, analysts, and academic professionals who require a focused environment for high-density information processing. The aesthetic follows a **Modern Corporate Minimalism** approach—stripping away decorative elements to prioritize functional utility and cognitive ease.

The visual narrative is built on structure, precision, and trust. By utilizing a "Panel-First" architecture, the UI facilitates deep work and multi-document comparison without visual fatigue. The emotional response should be one of quiet confidence; the tool does not compete for attention but rather provides a stable, high-contrast canvas for AI-driven insights.

## Colors

This design system utilizes a cold, professional palette to reinforce an analytical atmosphere.

- **Primary (Navy):** Used for navigation, primary headers, and foundational structural elements. It conveys authority and stability.
- **Secondary (Slate Mist):** Applied to large surface areas, side panels, and background fills to reduce eye strain compared to pure white.
- **Accent (Refined Teal):** Reserved strictly for primary actions, success states, and progress indicators. It provides a sharp, purposeful contrast against the deep navy.
- **Neutrals:** A range of cool grays (from `#F8FAFC` to `#374151`) handles borders, secondary text, and UI scaffolding. Typography primarily uses a high-contrast dark gray (`#111827`) to ensure AAA accessibility.

## Typography

The system uses **Inter** for all interface and editorial needs due to its exceptional legibility and systematic weight distribution.

- **Headlines:** Set with tight letter spacing and bold weights to appear grounded and confident. Size is tempered to prevent a "marketing" feel; the scale remains modest to prioritize information density.
- **Body Text:** Designed for long-form research consumption. `body-lg` utilizes a generous 1.75x line-height to maximize readability across wide data panels.
- **Labels:** Small-caps or heavy-weight uppercase treatments are used for metadata and table headers to distinguish them from interactive content.
- **Monospace:** `JetBrains Mono` is introduced sparingly for AI-generated data strings or technical references.

## Layout & Spacing

The layout philosophy is based on a **Modular Panel System**. Rather than a traditional fluid page, the design system treats the viewport as a workbench divided into distinct, resizable regions.

- **Grid:** A 12-column grid is used within panels, but the high-level layout relies on a "Sidebar-Main-Inspector" 3-pane model.
- **Guttering:** 1px borders act as gutters between major panels to create a "blueprint" feel. Inner content uses a 16px or 24px padding rhythm.
- **Responsive Behavior:** 
  - **Desktop:** Side-by-side panel comparison. 
  - **Tablet:** Collapsible sidebars with overlay state.
  - **Mobile:** Single-column stack with bottom-sheet navigation for research tools.

## Elevation & Depth

This design system rejects heavy shadows and depth metaphors in favor of **Tonal Layering and Borders**.

- **Surfaces:** Depth is communicated through color. The base background is white, while "underlying" functional areas like sidebars use the Secondary Light Blue. 
- **Borders:** Hierarchy is defined by 1px solid strokes. Use `Gray-200` for standard dividers and `Primary-Navy` (at low opacity) for active element boundaries.
- **Interactive States:** Instead of raising an element on the Z-axis (shadows), use subtle background shifts (e.g., White to Gray-50) or border-weight emphasis to signal interactivity.
- **Modals:** Use a heavy backdrop blur (20px) with a simple 1px border container to maintain the "glass" research overlay feel without breaking the minimal aesthetic.

## Shapes

The shape language is "Soft-Geometric." To maintain a professional and analytical tone, roundedness is kept minimal.

- **Standard Elements:** Inputs, buttons, and cards use a 4px (0.25rem) radius. This provides just enough softness to feel modern without appearing "bubbly" or consumer-grade.
- **Large Containers:** Main panels and modals may use up to 8px (0.5rem) to define clear boundaries.
- **Avoidance:** Completely sharp 0px corners are avoided to prevent a "brutalist" look, and pill-shaped (fully rounded) buttons are strictly forbidden as they conflict with the structured research narrative.

## Components

### Buttons
- **Primary:** Solid `Primary-Navy` or `Accent-Teal` with 4px corners. Text is center-aligned, medium weight.
- **Secondary:** Transparent background with a 1px `Gray-300` border. High-contrast text.
- **Ghost:** No border or background; subtle gray fill on hover.

### Input Fields
- **Default:** White background, 1px `Gray-300` border. 
- **Focus:** Border transitions to `Accent-Teal` with a 2px outer "halo" of the same color at 10% opacity. No heavy inner shadows.

### Research Panels
- Cards should not have shadows. Use a 1px border and a subtle header background (`Secondary-Light Blue`) to separate the title from the content.

### Status Indicators
- **Chips:** Rectangular with 2px corners. Light background tints with dark text (e.g., Light Green background with Dark Green text). No icons unless strictly necessary for status (e.g., an error "X").

### Data Comparison
- Use a split-pane view with a vertical 1px divider. Each side should have independent scroll synchronization toggles.