---
name: Fact Knowledge Layer
description: Evidence Docket for tracing structured facts to exact source evidence.
colors:
  mineral-white: "#f4fafd"
  graphite: "#161d1f"
  paper-white: "#ffffff"
  deep-ink: "#162839"
  deep-ink-hover: "#2c3e50"
  cool-aqua: "#e8eff1"
  cool-muted: "#dde4e6"
  muted-graphite: "#4b565b"
  institutional-green: "#006b55"
  verification-green: "#00765e"
  exception-amber: "#806600"
  alert-red: "#ba1a1a"
  hairline: "#c4c6cd"
  input-stroke: "#9299a0"
  surface-low: "#eef5f7"
  surface-high: "#e2e9ec"
  selected-evidence: "#e7f3ef"
  quote-paper: "#fffef8"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 2.2vw, 2rem)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.625rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.07em"
rounded:
  badge: "2px"
  field: "3px"
  standard: "4px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.deep-ink}"
    textColor: "{colors.paper-white}"
    typography: "{typography.body}"
    rounded: "{rounded.standard}"
    padding: "8px 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.deep-ink-hover}"
    textColor: "{colors.paper-white}"
  button-outline:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.graphite}"
    typography: "{typography.body}"
    rounded: "{rounded.standard}"
    padding: "8px 16px"
    height: "40px"
  input:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.graphite}"
    typography: "{typography.body}"
    rounded: "{rounded.field}"
    padding: "8px 12px"
    height: "40px"
  card:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.graphite}"
    rounded: "{rounded.standard}"
    padding: "20px"
  status-badge:
    backgroundColor: "{colors.surface-low}"
    textColor: "{colors.muted-graphite}"
    typography: "{typography.label}"
    rounded: "{rounded.badge}"
    padding: "2px 8px"
  navigation-active:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.graphite}"
    typography: "{typography.label}"
    padding: "0 16px"
    height: "56px"
  exhibit-header:
    backgroundColor: "{colors.deep-ink}"
    textColor: "{colors.paper-white}"
    rounded: "{rounded.standard}"
    padding: "12px 16px"
---

# Design System: Fact Knowledge Layer

## Overview

**Creative North Star: "Evidence Docket"**

Evidence Docket treats every selected fact as an indexed exhibit visibly bound to exact source evidence. The interface feels like a precise working record: mineral paper, deep ink title bands, hairline grids, compact metadata, and small verification marks establish authority without theatrical decoration.

The system is quiet, professional, and deliberately information-dense. One continuous evidence desk preserves the chain from source document to fact ledger, exhibit, and deterministic reasoning; it refuses the generic dashboard pattern of disconnected cards. On mobile, that same chain becomes explicit task tabs rather than a compressed desktop grid.

**Key Characteristics:**

- Mineral-white working surfaces with graphite text and deep-ink anchors.
- Hairline grids and compact rows that make provenance relationships visible.
- Workhorse sans typography paired with tabular mono metadata.
- Verification green, exception amber, and alert red used as semantic evidence states.
- Four-pixel core corners and flat, shadowless construction.

## Colors

The palette reads as cool archival paper marked with ink and sparse, auditable status color.

### Primary

- **Deep Ink** (`#162839`): anchors docket headers, exhibit bands, primary actions, and the decision record.
- **Paper White** (`#ffffff`): supplies text on ink and the clean working surface for cards and panels.

### Secondary

- **Institutional Green** (`#006b55`): fills progress and selected success accents where completion needs clear emphasis.
- **Verification Green** (`#00765e`): marks verified evidence and the one-pixel binding rule between a selected ledger item and its exhibit.
- **Selected Evidence Wash** (`#e7f3ef`): identifies the currently indexed document or fact without breaking the paper-like field.

### Tertiary

- **Exception Amber** (`#806600`): communicates uncertain, pending, or review-required states.
- **Alert Red** (`#ba1a1a`): communicates failed verification, contradiction, or service failure.

### Neutral

- **Mineral White** (`#f4fafd`): the application canvas behind the evidence desk.
- **Graphite** (`#161d1f`): the dominant text color for claims and controls.
- **Muted Graphite** (`#4b565b`): supports descriptions, secondary labels, and metadata.
- **Cool Aqua** (`#e8eff1`) and **Cool Muted** (`#dde4e6`): create quiet secondary controls and progress tracks.
- **Hairline Gray** (`#c4c6cd`): divides panels, rows, cells, and navigation states.
- **Input Stroke** (`#9299a0`): gives editable fields a stronger boundary than passive containers.
- **Low Surface** (`#eef5f7`) and **High Surface** (`#e2e9ec`): distinguish table headers, control bands, and compact tonal layers.
- **Quote Paper** (`#fffef8`): isolates recovered source language as the warmest paper in the system.
- **Ink Hover** (`#2c3e50`): deepens primary actions and supplies the visible focus-ring color.

### Named Rules

**The Evidence Color Rule.** Green means verified or actively bound, amber means exception or uncertainty, and red means failure or contradiction; color never decorates neutral structure.

**The Ink Anchor Rule.** Deep ink is reserved for headers, decisive actions, and record anchors so every use carries structural weight.

## Typography

**Display Font:** Inter (with `ui-sans-serif`, `system-ui`, and `sans-serif` fallbacks)

**Body Font:** Inter (with `ui-sans-serif`, `system-ui`, and `sans-serif` fallbacks)

**Label/Mono Font:** JetBrains Mono (with `ui-monospace` and `monospace` fallbacks)

**Character:** Inter provides a neutral, workhorse reading voice for dense operational material. JetBrains Mono makes indices, hashes, page references, offsets, counts, confidence values, and state labels feel reproducible and easy to compare.

### Hierarchy

- **Display** (650, `clamp(1.5rem, 2.2vw, 2rem)`, 1.15): page-level task framing, balanced and compact rather than promotional.
- **Headline** (600, `1.125rem`, 1.25): decision classifications and major record summaries.
- **Title** (600, `1rem`, 1.35): exhibit subjects, card titles, and section headings.
- **Body** (400, `0.875rem`, 1.55): descriptions and recovered evidence; explanatory lines stay near 72 characters where the layout permits.
- **Label** (600, `0.625rem`, `0.07em`, uppercase): terse metadata, table headings, identifiers, and status context.

### Named Rules

**The Mono-Is-Evidence Rule.** Use mono for values that can be indexed, compared, or reproduced; never use it for long explanations or source quotations.

## Layout

The desktop surface is one continuous evidence desk inside a centered container capped at 1800px with 24px side gutters. At large viewports, the desk uses three visibly connected columns: a fixed 280px document register, a flexible fact ledger with a practical 320px minimum, and a larger exhibit viewer with a 460px minimum. Ordered reasoning continues below on the same grid logic, binding the selected exhibit to its decision record.

Spacing is compact and regular: 8px for metadata gaps, 12px for row and control density, 16px for panel interiors, and 20–24px for page or card breathing room. Hairlines, not whitespace alone, carry most grouping work. Dense areas scroll within their own ledger column so headings and neighboring evidence remain stable.

Below the large breakpoint, the continuous desk becomes task views for Documents, Fact ledger, and Audit log. The sticky shell exposes these as full-width tabs; content stacks, columns collapse, and touch targets retain at least 40–44px height. At 640px and below, page titles and descriptions reduce modestly without changing the information hierarchy.

**The Docket Binding Rule.** Keep source, claim, exhibit, and reasoning visibly adjacent on desktop; on mobile, preserve their order through task tabs rather than shrinking the full desk into an unreadable grid.

## Elevation & Depth

The core Evidence Docket is flat and uses no shadows. Depth comes from tonal surface bands, deep-ink headers, one-pixel borders, and nested grid cells; focus rings communicate interaction without implying that a surface floats above the record.

### Named Rules

**The Flat Record Rule.** Never use ambient shadow to make evidence feel important; hierarchy must come from ink, paper, border, and placement.

## Shapes

Core surfaces use restrained four-pixel corners (`4px`). Editable fields tighten to three pixels (`3px`), while compact status badges use two pixels (`2px`). Tables, reasoning traces, header bands, icon tiles, and nested evidence cells remain square or inherit the four-pixel outer frame. Borders are one-pixel hairlines, and active items gain a one-pixel verification-green rule on the left edge.

**The Four-Pixel Ceiling Rule.** Keep persistent workspace geometry at four pixels or less; rounded pills and soft dashboard bubbles do not belong in the docket.

## Components

Components feel precise, flat, and instrument-like: compact enough for audit work, but never below dependable keyboard and touch targets.

### Buttons

- **Shape:** compact rectangle with restrained corners (`4px`) and a one-pixel boundary.
- **Primary:** deep-ink fill with paper-white text, 40px height, and 16px horizontal padding; the small variant is 32px high with 12px horizontal padding.
- **Hover / Focus:** primary hover deepens to Ink Hover; keyboard focus uses a two-pixel ink ring with a one-pixel canvas offset.
- **Secondary / Ghost / Outline / Destructive:** cool tonal fill, transparent-to-low-surface hover, paper with a hairline border, and alert-red fill respectively.

### Chips

- **Style:** two-pixel corners, a one-pixel semantic border, compact mono type, and 8px horizontal padding.
- **State:** neutral, success, danger, warning, and information variants pair text, border, fill, and a dot so status does not rely on hue alone.

### Cards / Containers

- **Corner Style:** restrained (`4px`) for cards and ledger panels; internal table bands remain square.
- **Background:** paper white on the mineral-white canvas, with low-surface bands for headings and summaries.
- **Shadow Strategy:** none; see the Flat Record Rule.
- **Border:** one-pixel Hairline Gray around the perimeter and between evidence cells.
- **Internal Padding:** 12–16px for dense ledgers and exhibits; 20px for standalone cards.

### Inputs / Fields

- **Style:** paper-white fill, stronger Input Stroke border, three-pixel corners, 40px minimum height, and 12px horizontal padding.
- **Focus:** border shifts to Deep Ink and gains a low-opacity two-pixel ink ring.
- **Error / Disabled:** errors use alert-red text and a tinted border/fill; disabled controls retain structure at 50% opacity and remove pointer affordance.

### Navigation

Navigation is a ruled extension of the shell. Each task uses compact semibold type, a 44px mobile or 56px desktop target, and hairline separators. Hover adds Low Surface; the active task returns to Paper White and gains a two-pixel Deep Ink rule at the bottom. On smaller screens, navigation spans the full shell width as equal task tabs.

### Evidence Exhibit

The signature exhibit is a four-pixel ledger panel with a Deep Ink identity band, a Low Surface fact grid, paired confidence cells, page-and-offset metadata, and a warm Quote Paper block. A one-pixel Verification Green rule binds the exact recovered quote to the verified state. The selected ledger row uses the same green rule and Selected Evidence Wash, making the row-to-exhibit relationship visible without animation-dependent meaning.

### Reasoning Trace

The deterministic decision record uses an ink summary rail beside a hairline table of ordered checks. Mono indices and outcomes remain narrow; the human-readable check and machine-readable details receive the flexible columns. Passed, failed, and uncertain outcomes reuse the evidence status palette.

## Do's and Don'ts

### Do:

- **Do** keep a selected fact visibly bound to its exact quote, page, offsets, verification state, and confidence.
- **Do** use one-pixel grids, compact rows, and tonal bands to structure dense evidence.
- **Do** reserve mono typography for identifiers, counts, hashes, offsets, tabular values, and reproducible states.
- **Do** preserve the continuous evidence desk on desktop and the ordered task tabs on mobile.
- **Do** pair every semantic color with text, a dot, a border, or another non-color cue.

### Don't:

- **Don't** turn the product into a generic dashboard of disconnected cards.
- **Don't** add shadows, glass effects, glow, gradients, or oversized pill shapes to core evidence surfaces.
- **Don't** use verification green as decoration or let status color replace a readable label.
- **Don't** separate a fact summary from the source exhibit needed to verify it.
- **Don't** loosen the density until provenance relationships no longer fit in the working view.
