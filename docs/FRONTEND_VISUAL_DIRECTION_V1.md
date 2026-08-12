# IDX Trade Frontend Visual Direction V1

Status: **DESIGN DIRECTION — implementation reference**

Scope: `apps/web` only. This document does **not** change research/model/data semantics.

## 1. Working name

### **Post-Swiss Interactive Editorial**

Alternative shorthand: **Editorial Tech Modernism**.

This is the design family IDX Trade should move toward.

It combines:

- Swiss / International-style structural discipline;
- editorial art direction rather than conventional SaaS-dashboard composition;
- oversized modern grotesk typography;
- restrained but high-quality interaction and motion;
- asymmetry inside a rigorous grid;
- premium institutional credibility;
- selective experimental details from creative-studio websites;
- information density where the product needs it, without visually turning into an admin dashboard.

The desired result is **not** a clone of any single reference site. It should feel like the same design culture while remaining an original IDX Trade interface.

---

## 2. Reference set

The direction is synthesized from these references supplied by the project owner:

1. https://alkares.com/
2. https://www.paradox.works/
3. https://orionix.framer.website/
4. https://kommakomma.is/
5. https://www.eleken.co/
6. https://www.thetriadicballetai.com/
7. https://evolt.dev/
8. https://www.cantor8.io/
9. https://www.fortvega.com/
10. https://lannino.com/

No third-party logos, illustrations, assets, copy, or pixel-identical trade dress should be copied.

---

## 3. What these sites have in common

The references vary in industry, but they share a surprisingly coherent visual grammar.

### 3.1 Typography is the primary visual object

The page is not designed by placing text inside cards. **The typography itself creates the composition.**

Common behavior:

- very large headlines;
- short, confident phrases;
- strong line breaks used intentionally;
- large scale contrast between headline, label, and metadata;
- uppercase micro-labels / section indices;
- numbers used as navigation and structure (`01`, `02`, `03`);
- occasional monospace or technical metadata as a secondary voice.

For IDX Trade, important model names, ranking counts, dates, and states should be allowed to become visual anchors instead of always being trapped inside generic metric cards.

### 3.2 Grid discipline with deliberate asymmetry

The pages feel free-form, but they are not random.

Typical pattern:

- strong desktop grid;
- content aligned to consistent left/right rails;
- large blank regions;
- one element intentionally offset or oversized;
- sections often split into a small label column + large content column;
- rules/hairlines establish structure instead of heavy card borders.

IDX Trade should retain predictable financial-product alignment while using asymmetric editorial composition to avoid looking like a standard analytics template.

### 3.3 Section transitions feel like chapters

Instead of a dashboard made from ten equal cards, these sites treat scrolling as a sequence of **chapters**.

Typical sequence:

`statement → evidence → detail → visual → next statement`

For IDX Trade:

`final ranker identity → promotion evidence → model lineage → forward status`

and on Monitoring:

`current session → capture state → scoring state → ranked universe → accumulated sessions → locked outcome vault`

Each section should have a distinct compositional idea.

### 3.4 Motion is part of hierarchy, not decoration

Desired motion language:

- smooth section entrances;
- text/reveal masks;
- line or rule expansion;
- subtle parallax / image drift where relevant;
- numbers counting/crossfading;
- shared-layout movement when selection changes;
- rows/cards responding slightly to pointer movement;
- custom tooltips that feel native to the visual system;
- marquees or horizontal motion only where they add rhythm.

Avoid:

- bouncing UI;
- excessive spring physics;
- every element fading independently;
- decorative animation that delays access to data;
- animation on critical operational actions that obscures state.

The target is **calm motion with moments of theatricality**.

### 3.5 Premium interfaces use fewer boxes

A recurring lesson across the references: hierarchy often comes from typography, whitespace, images, rules, and scale — **not from wrapping everything in rounded rectangles**.

IDX Trade currently uses too many conventional `surface/card` blocks.

Direction:

- reduce card count;
- use full-width editorial sections;
- use 1px rules and column boundaries;
- reserve cards for real interactive objects or bounded operational state;
- allow charts/tables to sit directly in a section when possible.

### 3.6 Visual identity comes from a few strong gestures

Do not spread five accent colors everywhere.

Use:

- one strong neutral foundation;
- one primary market accent;
- red only for negative / failure / risk;
- occasional warm or electric secondary accent for special states;
- one distinctive typography treatment;
- one or two recurring interaction motifs.

The brand should be recognizable from composition before color.

---

## 4. Individual reference lessons

### Alkares

Take:

- monumental industrial-premium typography;
- numbered technical sections;
- hard factual evidence presented with cinematic confidence;
- contrast between material imagery and sparse type-led layouts;
- engineering language treated as luxury presentation.

IDX application: make model evidence feel engineered and deliberate rather than like a BI report.

### Paradox Works

Take:

- editorial restraint;
- provocative short statements;
- large whitespace;
- content-led composition;
- philosophical / intellectual tone without visual clutter.

IDX application: use concise research statements and let whitespace carry authority.

### Orionix

Take:

- oversized creative-studio headlines;
- dynamic project presentation;
- marquee / repetition as rhythm;
- intentional interaction around portfolio elements;
- bold typography paired with clean systems.

IDX application: model lineage / research experiments can feel like a curated body of work, not a spreadsheet dump.

### Komma Komma

Take:

- anti-template feeling;
- playful-but-controlled typography;
- numbered service/project hierarchy;
- bespoke navigation and project interaction;
- strong point of view while retaining usability.

IDX application: introduce small signature details so the product no longer feels like a generic fintech dashboard.

### Eleken

Take:

- pragmatic product usability;
- clear hierarchy even with substantial information density;
- strong case-study/product framing;
- clean SaaS interaction patterns where experimentation would hurt usability.

IDX application: Monitoring must remain operationally obvious even if Overview becomes more editorial.

### The Triadic Ballet AI

Take:

- exhibition / art-book pacing;
- chapters / acts;
- type and imagery composing a narrative;
- large spatial changes between sections;
- restrained, concept-driven use of color;
- deliberate visual rhythm.

IDX application: research generations can be treated as acts/chapters; large whitespace and section numbering can make technical research feel legible and memorable.

### Evolt

Take:

- high-stakes technology tone;
- slash-prefixed uppercase section labels;
- assertive headline scale;
- technical credibility without conventional enterprise blandness;
- repeated typographic motifs and structured proof points.

IDX application: excellent reference for `MODEL`, `RUNTIME`, `OUTCOME VAULT`, artifact hashes, and system-health sections.

### Cantor8

Take:

- institutional-finance credibility;
- premium editorial pacing;
- minimal but confident product descriptions;
- strong hierarchy around infrastructure/product modules;
- modern financial-tech atmosphere without retail-trading clichés.

IDX application: this should heavily influence the institutional side of IDX Trade.

### Fort Vega

Take:

- luxury editorial whitespace;
- large imagery / atmospheric objects;
- elegant pacing;
- premium serif/grotesk-style contrast where appropriate;
- restraint and confidence.

IDX application: use more negative space and fewer obvious containers on Overview; do not overdecorate Monitoring.

### Lannino

Take:

- simplicity + animation rather than complexity + animation;
- micro-interaction quality;
- creative developer personality;
- bold typographic composition;
- small details that make otherwise simple pages memorable.

IDX application: interaction polish should come from cursor/hover/layout behavior, not additional widgets.

---

## 5. IDX Trade design principles

### Principle A — Editorial first, dashboard second

Overview should feel like an interactive research publication that happens to contain live product data.

Monitoring should feel like a precise operational instrument with editorial polish.

### Principle B — One dominant idea per viewport

At normal desktop height, the user should immediately understand what the section is about.

Do not show six equal-priority cards at once.

### Principle C — Large type for identity, small type for evidence

Examples:

- `V3-B` can be huge;
- `Structure-Lite` can be large but secondary;
- model SHA / feature SHA can be tiny monospace metadata;
- the 100-session counter should be visually dominant;
- status labels should remain compact.

### Principle D — Use rules before cards

Preferred hierarchy tools:

1. whitespace;
2. type scale;
3. alignment;
4. 1px rules;
5. background-field changes;
6. cards only when necessary.

### Principle E — Motion explains state

Examples:

- rank changes animate between positions;
- a new session appears by extending the timeline;
- a scoring artifact transitions `queued → scoring → verified` within one persistent row;
- chart tooltip follows the visual system;
- switching a research experiment morphs the evidence instead of fully replacing the screen.

### Principle F — Market color semantics stay semantic

Green/red remain useful because this is a market product.

But they must not become the entire brand identity.

- green: positive / healthy / active / verified;
- red: negative / failed / weak / invalid;
- amber: pending / protected / locked / caution;
- black/ink/cream/white/grey: core brand field.

---

## 6. Recommended visual system

### 6.1 Base palette

Prefer a high-contrast editorial neutral foundation.

Suggested direction, not frozen tokens:

- paper / bone: `#F2F0E9` to `#F7F5EF`;
- near-black ink: `#111311`;
- clean white: `#FCFCF8`;
- structural grey: `#D8D6CF`;
- secondary text: `#71756F`;
- market green: around `#0A8F61`;
- market red: around `#D84A50`;
- warm amber for protected/locked states.

Use occasional full-black or full-green sections for contrast rather than keeping every surface off-white.

### 6.2 Typography

Desired hierarchy:

- **Display grotesk**: very large, tight tracking, high confidence;
- **UI grotesk**: clear and neutral for controls/tables;
- **mono metadata**: hashes, model IDs, session IDs, timestamps.

Do not overuse all-caps. Reserve it for section labels and system metadata.

Example scale on wide desktop:

- hero display: 72–112px when composition allows;
- section headline: 40–64px;
- operational primary metric: 56–96px;
- body: 14–18px;
- UI label: 11–13px;
- metadata: 10–12px.

The current 48px hero ceiling is too conservative for this direction.

### 6.3 Radius

Current interface is overly card-like.

Direction:

- general section: no radius;
- large bounded interactive object: 16–24px;
- small controls: 8–12px;
- pills: fully rounded only for actual tags/statuses.

Rounded rectangles must become an exception, not the default layout primitive.

### 6.4 Borders and rules

Use hairlines extensively:

- horizontal section separators;
- table rules;
- timeline rules;
- vertical column dividers;
- animated rules during section reveal.

Avoid unnecessary box borders around large sections.

### 6.5 Shadows

Reduce conventional SaaS shadows substantially.

Most objects should rely on:

- layering;
- contrast;
- border/rule;
- backdrop;
- movement.

Use shadow only for floating interaction layers: tooltip, command palette, dropdown, temporary modal.

---

## 7. Motion specification

### Global motion character

`precise / smooth / slightly cinematic / never bouncy`

### Timings

- micro interaction: 120–200ms;
- selection/layout transition: 250–450ms;
- section reveal: 500–900ms;
- major editorial transition: up to ~1200ms if it never blocks the user.

### Easing

Prefer ease curves with decisive starts/stops, e.g. cubic-bezier families around:

- `(.2,.8,.2,1)`;
- `(.22,1,.36,1)`.

Avoid elastic/spring behavior for finance data.

### Recommended motifs

- clip-path / mask text reveals;
- translateY + opacity for section labels;
- line expansion from left to right;
- numbers crossfade rather than abruptly replace;
- chart strokes draw once on entry, not on every hover;
- ranking rows animate via shared layout positions;
- custom cursor only if it adds clear affordance to editorial sections;
- image/graphic parallax should be subtle.

### Reduced motion

Respect `prefers-reduced-motion` and remove non-essential transforms/scroll effects.

---

## 8. Page-specific direction

## 8.1 Overview

Desired feeling: **research publication / model dossier / interactive technical editorial**.

Suggested structure:

### Chapter 01 — Final Ranker

Large editorial opening:

`V3-B`

`STRUCTURE—LITE`

with small metadata alongside:

- final model ID;
- 33 features;
- frozen SHA;
- final refit size.

Do not put this inside a conventional card.

### Chapter 02 — Why It Won

One dominant chart, large typography around it, minimal explanatory copy.

Use paired uplift evidence as a visual story.

### Chapter 03 — Research Lineage

Instead of a normal business table first, consider a vertical indexed sequence:

`V2 / V3-A / V3-B / V3-C / ...`

Rows can expand on hover/click for details.

A compact table can remain as a secondary exact-data representation.

### Chapter 04 — Forward Contract

Large `0 / 100` counter with protected outcome state and a direct transition to Monitoring.

This section can use a contrasting dark or market-green background to punctuate the page.

---

## 8.2 Forward Monitoring

Desired feeling: **mission control without looking like enterprise admin software**.

Usability overrides experimentation here.

### Top strip

Show only:

- current session;
- capture state;
- V3-B score state;
- verified scored sessions / 100;
- outcome vault lock.

### Session timeline

Use a horizontal or responsive grid timeline with strong date typography and minimal labels.

States:

- recorded;
- scoring;
- verified;
- missing;
- failed.

### Daily ranking

Once scorer wiring exists, this should become the visual centerpiece.

Suggested table behavior:

- large rank number;
- ticker;
- score;
- percentile;
- rank Δ vs previous session;
- optional tiny inline spark/indicator;
- rows animate to new position when comparing sessions.

### System provenance

Hashes and completeness should live in a compact technical drawer/expandable panel, not consume the primary viewport.

### Outcome vault

A visually distinct locked section can exist at the bottom, but it must reveal **no outcome-derived values** before authorization.

---

## 9. Anti-patterns to remove from current frontend

- too many equally rounded white cards;
- every block having its own shadow;
- four KPI cards simply because dashboards commonly have four KPI cards;
- lengthy descriptive copy explaining obvious UI;
- generic SaaS hero treatment;
- tiny headline scale everywhere;
- excessive pills/badges;
- repetitive green-white-fintech appearance;
- UI components that feel independent rather than art-directed as a whole;
- motion added uniformly instead of selectively.

---

## 10. Design tokens are not the design

Changing `#4856d6` to green did not materially change the design language because the composition remained a conventional card dashboard.

The next redesign must change **composition**:

- scale;
- spatial rhythm;
- typography;
- card density;
- section pacing;
- interaction;
- motion;
- information hierarchy.

Color comes after those decisions.

---

## 11. One-sentence brief

> **Build IDX Trade like a high-end interactive research publication for a quantitative finance lab: Post-Swiss grid discipline, oversized editorial typography, institutional fintech credibility, sparse but expressive motion, market-semantic color, and far fewer dashboard cards.**

---

## 12. Prompt vocabulary for future implementation

When briefing a designer or coding agent, use phrases like:

- post-Swiss interactive editorial;
- editorial tech modernism;
- art-directed finance interface;
- premium institutional fintech;
- oversized grotesk typography;
- asymmetric grid with strict alignment;
- chapter-based scroll composition;
- hairline rules instead of card borders;
- sparse high-quality motion;
- motion-led hierarchy;
- custom microinteractions;
- calm but cinematic;
- typography as the main visual object;
- fewer cards, more spatial composition;
- product usability preserved inside experimental editorial framing;
- research dossier / quant lab publication, not admin dashboard.

Avoid vague prompts such as:

- make it modern;
- make it futuristic;
- make it premium;
- make it like a fintech website;
- add animations;
- make it Awwwards style.

Those phrases are too broad and tend to produce generic results.
