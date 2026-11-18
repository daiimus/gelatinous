# Website Styling Specification

## Overview

Gelatinous uses a custom **terminal/brutalist** web theme on top of Bootstrap
4.6. The house style is the **Atlas register**: an ink ground, bone text and a
single amber accent, set in the **Monaspace** family. The look is built from a
small set of CSS custom properties plus subtle CRT-style effects (scanlines,
flicker, glow). It covers four surfaces: the website, the Atlas, the forum and
the webclient.

Where the styling lives:

- **Website:** `web/static/website/css/custom.css`, which overrides Bootstrap
  and Evennia defaults. Each section and rule in it appears once, so "the CSS
  wins" is a usable tiebreak;
  `world/tests/test_the_website_stylesheet_defines_its_theme_once.py` keeps it
  that way (#3356).
- **Atlas:** `scripts/atlas/template3d.html` and `scripts/atlas/template.html`.
- **Forum:** `web/discourse-theme/` (`common/common.scss` and the rest of the
  theme component).
- **Webclient:** `web/static/webclient/css/webclient.css`.

**Source of truth:** the live `custom.css` is canonical. This spec describes
what that file implements; if they disagree, the CSS wins and this document
should be updated to match.

**Design philosophy:**
- Terminal/brutalist aesthetic, set entirely in Monaspace. The typeface does
  the terminal work, so the chrome doesn't have to shout.
- Dark, low-glare ground (`#0b0e14`, Atlas ink) rather than pure black.
- **Amber (`#e0a86f`) is the accent**: links, focus, emphasis, the control
  you're using. One accent, used sparingly.
- Subtle glow / scanline / flicker effects for atmosphere, kept understated.
- Uppercase navigation, headings, labels and buttons for a corporate-terminal
  feel.
- Minimal decoration, high information density.

### The colour rule (applies to every surface)

**Jade is STATE. Amber is ACCENT. Cyan is DATA.**

Jade `#5fd38d` used to be the accent, and was demoted deliberately. It means
one thing, *good*, and it sits in a set with `--terminal-yellow` (warning /
connecting) and `--terminal-red` (error / disconnected). Spending it on
decoration dilutes a signal, so plate borders, rules, focus rings and headings
take amber instead.

Cyan `#6fd6e0` is reserved for machine-readable data in the Atlas and in-game
readouts. It is never decoration and never inherited into site chrome.

This rule holds across all four surfaces: website, Atlas, forum and webclient.

## File Location & Version Control

`custom.css` lives at `web/static/website/css/custom.css` and is **tracked**
in git, through narrow `.gitignore` exceptions under `web/static/website/css/`.
Edits belong in the dev repo and ship through the normal deploy cycle. **Do
not untrack it.** While it was an untracked file that existed only in the live
deployment, the deploy's `git reset --hard` overwrote it and the theme was
lost (2026-07-29).

`evennia_logo.png` and `favicon.ico` are committed for the same reason. The
original cube logo is not kept in the tree; it survives only in git history
(`legacy-cube-logo.png` / `legacy-favicon.ico`).

Files under `web/static/website/images/`, `fonts/`, `js/` and `skins/` are
tracked by default. `css/` is not: only `custom.css` is un-ignored there, so a
new stylesheet needs its own narrow `.gitignore` exception. **Verify with `git
add --dry-run`.** `git check-ignore -v` prints the matching rule even when that
rule is a *negation*, which is easy to misread as "still ignored".

## Loading Mechanism

`custom.css` is loaded **after** Bootstrap and Evennia's `website.css`, so its
rules win on specificity ties (and it uses `!important` where Bootstrap is
stubborn).

- **Main site:** our `base.html` (`web/templates/website/base.html`, forked
  from Evennia's) links the Bootstrap CDN stylesheet, then `website.css`, then
  `website/css/custom.css`. Because the template is ours, keeping that order
  is ours to check on every Evennia upgrade (see *The forked `base.html`*
  below).
- **Discourse iframe header:** `web/templates/website/header_only.html`, a
  minimal navbar-only template embedded in the forum, links the same three
  stylesheets in the same order:

  ```html
  <!-- header_only.html -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css" ...>
  <link rel="stylesheet" href="{% static 'website/css/website.css' %}">
  <link rel="stylesheet" href="{% static 'website/css/custom.css' %}">
  ```

  `header_only.html` also inlines a critical-CSS block that paints the ink
  ground immediately, before external CSS loads, so the embedded navbar
  matches the main site with no flash. **That block must use a literal
  colour, not `var(--terminal-bg-dark)`**: the token is defined in
  `custom.css`, which has not loaded yet, and an undefined custom property
  invalidates the whole declaration. It shipped broken for exactly that
  reason. The view `header_only()` in `web/website/views/header_only.py` picks
  the literal from `SKIN_INK` by the viewer's `gel_skin` cookie (the default
  skin when the cookie is missing or unknown). `scripts/brand/build_skins.py`
  generates `SKIN_INK`; do not edit it by hand.

  The header does not load Google Fonts. Monaspace is self-hosted and
  same-origin with the iframe, so the header picks it up from `custom.css`
  directly.

### Bootstrap versions

Bootstrap **CSS** is **4.6.0** on both surfaces, from the CDN links in our
`base.html` and in `header_only.html`. The JavaScript is not pinned with it,
and the two surfaces do not match:

| surface | jQuery | Popper | Bootstrap JS |
|---|---|---|---|
| main site (`base.html`) | 3.2.1-slim | 1.12.9 | 4.0.0 |
| forum header (`header_only.html`) | 3.6.0 | — | 4.6.2 bundle |

The main site therefore runs 4.0 JS against 4.6 CSS in one page. These
version strings came in verbatim from upstream Evennia when the fork was
taken; `base.html` is ours now, so the drift is ours to own. Read the
*Maintenance Notes* obligation ("Bootstrap stays at 4.6") as covering **both
files and both asset types**. Low severity, since 4.0 JS is broadly
API-compatible with 4.6 CSS, but the navbar dropdown behaviour documented in
`DISCOURSE_INTEGRATION` / #1466 rides this JS.

## Color Palette

Defined as CSS custom properties on `:root` (the Atlas register):

| Variable | Value | Usage |
|----------|-------|-------|
| `--terminal-bg-dark` | `#0b0e14` | Atlas ink, the ground: body, navbar, footer, card headers |
| `--terminal-bg-medium` | `#11161f` | Atlas plate, raised: cards, dropdowns, alerts, list groups |
| `--terminal-bg-light` | `#182030` | Atlas plate-hi: form inputs, hover |
| `--terminal-accent` | `#e0a86f` | Atlas amber, the highlight: links, focus, emphasis, plate chrome |
| `--terminal-accent-dim` | `#b8834f` | Dimmed amber: accent at rest |
| `--terminal-text` | `#d8d3c4` | Atlas bone, creamy not white: primary text |
| `--terminal-text-muted` | `#8f8d82` | Atlas bone-dim: secondary/disabled text |
| `--terminal-success` | `#5fd38d` | Jade, **state only**: healthy / active / success |
| `--terminal-success-dim` | `#4a9d6d` | Dimmed jade |
| `--terminal-yellow` | `#e6c547` | Softer warning yellow: warnings, archived |
| `--terminal-red` | `#e85555` | Softer error red: errors / destructive actions |
| `--terminal-border` | `#232c3a` | Atlas line, a cool rule: borders, separators |
| `--terminal-glow` | `rgba(224, 168, 111, 0.30)` | Amber glow on hover/focus |
| `--terminal-success-glow` | `rgba(95, 211, 141, 0.3)` | Jade glow, for state indicators |

**There is no `--terminal-green`.** Jade's token is `--terminal-success`.
Anything referencing `--terminal-green` or `--terminal-green-dim` is a bug, not
a fallback.

The palette is deliberately *softened*: no pure black, no pure white, no pure
`#00ff00`. Ink is blue-black rather than neutral grey, and text is bone rather
than white, which is what makes the surfaces read warm instead of clinical.

These `:root` values are the default (atlas) skin. The six other skins are
described under *Customization Guide*.

## Typography

### Font Stack

The site is set in **Monaspace**, self-hosted as variable `woff2` files from
`web/static/website/fonts/` via four `@font-face` blocks. Nothing is loaded
from Google Fonts.

Type is assigned **by role**, not globally. Each role is a custom property;
every face falls back to `ui-monospace, 'SF Mono', Menlo, monospace`, except
`--font-hand`, which falls back to `'Monaspace Neon', cursive`.

| Role | Property | Face | Used for |
|------|----------|------|----------|
| prose | `--font-prose` | Neon | body copy, lore |
| reading | `--font-reading` | Argon | longer reading passages; today only the `ed` skin uses it (nav links, heading words) |
| display | `--font-display` | Xenon | headings, plate heads |
| data | `--font-data` | Neon | figures, labels, status chips |
| hand | `--font-hand` | Radon | reserved for human marks; its one user (the memorial wall) was folded into the sleeve listing; today only the `ed` skin uses it (nav links, heading words) |

Body size is `--size-body: 15.5px`; `h1` is `--size-h1: 32px`.

Because these are variable fonts, `@font-face` declares the axes
(`font-weight: 200 800`, `font-stretch: 100% 125%`, `font-style: oblique 0deg
11deg`) and `font-synthesis: none` prevents the browser faking what it can
already interpolate. Feature settings are `"calt" 1, "liga" 1, "cv01" 1`:
texture healing, standard ligatures and the slashed zero. Code ligatures
(`ss01`–`ss10`) stay **off** in prose. Machine surfaces (tables, code, inputs,
badges, `.dbref` / `.uid` / `.coords`) turn on `ss03` (arrows) with the
slashed zero, and the navbar brand adds `cv02` (alternate one).

**Do not introduce a global `!important` font rule.** A global
`* { font-family: 'Inter' … !important }` rule once also captured the Atlas
plate and made two-thirds of the homepage lore unreadable at the wrong weight
and slant.

### Uppercase Chrome

Headings, navbar links, card headers, table headers, labels and buttons are
`text-transform: uppercase` with increased `letter-spacing`, for a
corporate/military terminal feel. Headings are `--terminal-text` (bone). The letter-spacings:

| element | letter-spacing |
|---|---|
| nav links | 0.14em |
| labels and buttons | 0.12em |
| h4–h6 and card headers | 0.1em |
| h1–h3 | 0.08em |
| `.table` headers | 0.05em |

## Layout & Measure

**One column, everywhere.** `.container` *is* that column, which is what makes
the navbar (`_menu.html`, included by our `base.html`) share its left and
right edges with page content for free.

The layout tokens on `:root`:

| token | value | meaning |
|---|---|---|
| `--page-col` | `min(92vw, 1140px)` | the shared column |
| `--measure` | `72ch` | readable line length |
| `--s1` … `--s6` | `8px`, `16px`, `24px`, `40px`, `64px`, `96px` | spacing scale |

**Prose is bounded by MEASURE, not by centring.** Two centred objects of
different widths that share no edge read as floating rather than composed, so
everything sits in the one column. Running paragraphs (`.lore p`,
`.status-note`) are blocks capped at `--measure` and centred in the column,
with their text left-aligned. The headline, deck and action (`.hero`), the
figures and the recent list are centred text.

Plate captions (`.plate-lore`, on the Atlas and the sleeve pages) are capped
at 85ch. Paragraphs take `1.75` line-height; the deck and plate captions take
`1.7`.

Use the spacing scale (`--s1`…`--s6`) rather than ad-hoc margins.

**The Atlas opts out**, because a map wants width, not measure:

```css
.atlas-plate {
    width: min(96vw, 2100px);
    margin-left: calc((100% - min(96vw, 2100px)) / 2);
}
```

It uses a negative margin rather than a `transform`, which would soften the
plate's hairlines.

**Retuning:** `--page-col` moves every surface at once. It narrows
table-heavy pages (Manage Sleeves) relative to a wider shell; widen the token
or give those pages the Atlas break-out treatment if that proves too tight.

### Homepage structure

Hierarchy carries the argument: **thesis → deck → one action → lore → honest
statement of state → figures**. The classes are `.hero`, `.deck`, `.actions`
with one `.btn-play` (`.btn-quiet` is defined in `custom.css` for a secondary
action, and no template uses it), `.status-note` (the pre-alpha statement),
`.status-band` with five `.figure`s (connected now, accounts, sleeves, rooms,
active this week), and `.recent`.

Two rules:

- **One primary action.** A reader who finishes the lore must have somewhere
  to go; "play" as the eighth item in the nav is not that.
- **Figures are not features.** Accounts / sleeves / rooms are context for
  regulars, not a headline for a first-time reader, so they sit in one quiet
  band rather than three cards competing with the pitch. Only "connected now"
  is jade, because it is the only figure that is STATE.

The homepage overrides Evennia's `index.html` and
`recently-connected-widget.html` locally. `index.html` is overridden because
the widget layout is where the two-measure problem lived. Overriding a template is the
sanctioned route; do not patch Evennia in place. The widget override puts
spaces around the em dash (`Drivel — 50 minutes ago`, not
`Drivel—50 minutes ago`, which at Monaspace's tracking reads as one word), and
renders the list as a flat inline strip (`.recent`) under the figures band
rather than a card.

## Brand Mark

The site's mark is the canted ringed world, built by
`scripts/brand/build_brand.py`: an ink disc (`.plate`) with an amber rim
(`.rim`), a ring tilted −22° (`.ring`), a bone planet (`.body`) with the near
arc of the ring passing in front of it over an ink underlay, and a moon
(`.knock` + `.node`). The generator writes `gm-mark.svg` (the mark alone) and
`gm-patch.svg` (the mark inside the GELATINOUS / MONSTER wordmark), plus the
PNG and ICO rasters. There is no monogram, no `.mono` class, no
`gm-orbit.svg` and no compact cut.

This section used to describe the retired **GM orbit mark**: a bounding
circle, one inclined orbit (−20°), a dashed inner track, a broken polar axis
and two bodies on their paths, with a **GM** monogram in a knockout disc at
the centre, in a full and a compact cut. Whether that history is kept here as
one note is not decided (#3285).

**It carries no colour of its own.** The mark is inlined into `_menu.html` and
`_menu_iframe.html` (both ours), and every stroke and fill reads a theme
token:

| part | property | token |
|---|---|---|
| `.plate` | fill | `--terminal-bg-dark` |
| `.rim` | stroke | `--terminal-accent` |
| `.ring` | stroke | `--terminal-accent` |
| `.node` | fill | `--terminal-accent` |
| `.knock` | fill | `--terminal-bg-dark` |
| `.body` | fill | `--terminal-text` |
| `.knock-stroke` | stroke | `--terminal-bg-dark` |

Change `--terminal-accent` and the inlined mark follows. The planet (`.body`)
takes `--terminal-text`, not the accent, so it stays legible against its ring.
Inlining also costs no HTTP request.

The standalone SVGs (`gm-mark.svg`, `gm-patch.svg`) use the same tokens with
**literal fallbacks** (`var(--terminal-accent, #e0a86f)`), so they render
correctly outside a page.

The rasters (PNG/ICO) are flattened to literal hex **on purpose**: librsvg,
which does the rasterising, does not implement CSS custom properties and
renders unresolved ones as silent grey. SVG follows the skin; PNG/ICO cannot
and must not try.

**The plate is a disc, not a tile.** Anywhere the mark needs a ground behind
it (the standalone SVG, the favicon raster) that ground is a circle at the
ring radius, with transparent corners. A full-bleed `<rect>` renders the mark
as a dark square in a browser tab and against any non-ink surface. When
re-exporting the raster, confirm the alpha channel survived (`sips -g
hasAlpha`): a flattened render silently re-bakes the square and looks
identical in a file listing.

The inline navbar mark sits on the same ink disc (`.plate`) as the exports;
neither has a square ground.

### Regenerating the mark

If the accent moves, run `scripts/brand/build_brand.py <outdir>`. It
regenerates both SVGs plus `gm-patch-{512,192}.png`, `gm-mark-{256,180,64}.png`
and `favicon.ico` from one definition.

**Two hand steps remain, because the generator emits neither filename the site
actually links:**

1. `evennia_logo.png` is `gm-mark-256.png` under the Evennia name (256×256,
   alpha intact; see *The favicon is named `evennia_logo.png` on purpose* for
   why the name stays).
2. `apple-touch-icon.png` is the 180 cut composited onto an ink ground, which
   must stay **fully opaque** (`sips -g hasAlpha` → `no`) because Apple
   flattens transparency onto black.

### Apple touch icons (iOS/iPadOS) span three systems

iOS ignores `rel="icon"` for home-screen/bookmark/share icons and probes
**root paths** (`/apple-touch-icon.png`, `-precomposed`, sized variants)
whenever a page declares no `apple-touch-icon` link, and Apple **flattens
transparency onto black**, so the disc-with-transparent-corners cuts become
mismatched black tiles. iOS also keeps a stored touch icon forever and never
re-probes while an entry exists, so a page that *declares* a touch-icon URL it
has not seen is the only reliable refetch trigger. The setup:

- `web/static/website/images/apple-touch-icon.png`: 180×180, **fully
  opaque**, an Atlas-ink full-bleed ground with the mark composited on it.
- `web/urls.py` (`_icon()`) serves the file's bytes directly, with no
  redirect, at `/favicon.ico` and the whole `/apple-touch-icon*.png` probe
  family, with public, must-revalidate cache headers, so the response carries
  no cookie and the edge can cache it. Both `base.html` files (website and
  webclient) also declare it explicitly.
- **Cloudflare**: the zone's path-allowlist firewall rule must include
  `starts_with(http.request.uri.path, "/apple-touch-icon")` (it sits right
  after the `/favicon.ico` clause). Without it, iOS probes are BLOCKED at the
  edge and Apple devices improvise icons (the "favicon is all over the place"
  bug). Anything added at a root path needs an allowlist clause or it does not
  exist outside the LAN.
- **Discourse**: the `apple_touch_icon` site setting carries the same opaque
  icon (uploaded via rails `UploadCreator`; the tab `favicon` stays the plain
  disc mark).

### The favicon is named `evennia_logo.png` on purpose

Both `base.html` files (`web/templates/website/base.html` and
`web/templates/webclient/base.html`, forked from Evennia's) point `rel="icon"`
at `website/images/evennia_logo.png`, the name they carried upstream. Our
static dir **shadows** that path: `STATICFILES_DIRS` is searched before the
package (confirmed with
`finders.find('website/images/evennia_logo.png', all=True)`), so our file wins
over Evennia's own logo. Do not "tidy" the filename without editing both
templates.

### The forked `base.html`

`web/templates/website/base.html` shadows Evennia's `website/base.html`, the
sanctioned template-shadow route. It differs from upstream in two places, both
in `<head>`:

1. It declares an `apple-touch-icon` link (#1909), for the refetch reason
   above.
2. Its `rel="icon"` declaration is `type="image/png" sizes="256x256"` (#1911).
   The stock `type="image/x-icon"` pointing at a PNG is a MIME mismatch that
   WebKit treats as licence to ignore the declaration and keep its stored icon
   forever.

The `evennia_logo.png` shadow is still how the `rel="icon"` target is
replaced; the `href` is unchanged. The navbar still lives in `_menu.html`, so
the shared-column layout is unaffected. A forked template carries an
obligation an unforked one does not: **resync it against upstream on every
Evennia upgrade.**

## Component Styling

`custom.css` themes the Bootstrap 4.6 component set against the palette:

- **Navbar / footer:** painted the body's ink (`--terminal-bg-dark`),
  borderless, no shadow, so they blend into the body ground rather than
  banding against it. Links are uppercase with an amber glow (`text-shadow`)
  on hover. Dropdowns use `--terminal-bg-medium`. The footer is unpinned from
  Evennia's `position: absolute` band and the reserved `body` margin is
  released, because a viewport-pinned footer misplaces itself on tall pages
  (the Atlas). This is the first of the two rules in the
  `ADDITIONS (2026-07-29)` block of `custom.css`.
- **Cards:** `--terminal-bg-medium` body, `--terminal-bg-dark` header
  (uppercase); all nested content forced to the dark theme. Brief
  `terminal-flicker` animation on load.
- **Links:** `--terminal-accent-dim` at rest → `--terminal-accent` + glow on
  hover.
- **Buttons** (`primary`, `secondary`, `danger`, `warning`): plate-hi fill
  (`--terminal-bg-light`), a 1px border and text in the button's hue
  (amber-dim for primary, red, yellow), uppercase; on hover/focus the fill
  goes to ink and a `box-shadow` glow in that hue appears (primary also
  brightens to amber). Secondary is neutral: a rule-coloured border, bone
  text, and no glow.
- **Forms:** dark inputs; on focus the border turns amber with a glow. (No
  cursor shows; see *Cursor* below.)
- **Alerts:** dark fill with a coloured border/text per state (success=jade,
  warning=yellow, danger=red). These are state, so they keep their hues.
- **Tables / pagination / breadcrumbs / code blocks:** re-skinned to the
  palette. Plate tables (`.plate-stage .table`) hover on
  `--terminal-bg-light`; the generic `.table-hover` rule tints rows jade
  (`rgba(95, 211, 141, 0.08)`), against the colour rule (see *Not decided*).
  List groups and badges have no colour rules.
- **Plates:** the `.plate-head` / `.plate-place` / `.plate-stamp` /
  `.plate-lore` / `.plate-stage` / `.plate-empty` set is the house page
  pattern, shared by the Atlas and the sleeve pages: a centred head, a caption
  at measure, and a stage holding the content.

### Evennia help and channel pages

`custom.css` has no override block for Evennia's default web help and channel
pages: it contains no rule for `.thead-light`, `.list-group-item`,
`.badge-light` or `.alert-secondary`. Whether those pages currently render
pale Bootstrap defaults on the ink ground has not been confirmed in a
browser.

Such a block existed and is recoverable verbatim from git history:
`git show fa1a9a64:web/static/website/css/custom.css`, the section headed
`/* ===== EVENNIA HELP/CHANNEL PAGE OVERRIDES ===== */`, covering
`.thead-light`, `.thead-light th`, `.card-header`, `.list-group-item`
(+ `:hover`, `.active`), `.badge-light`, `.card.border-light`,
`.alert-secondary`, `.alert-warning`, `.table` and `pre`. Reinstating it is
close to a copy, with two caveats: that copy predates the Atlas repalette and
references `--terminal-green` / `--terminal-green-dim`, which must be renamed
`--terminal-success` / `--terminal-success-dim`; and its jade
`.list-group-item:hover` / `.active` treatment needs checking against *Jade is
STATE, never decoration* before it goes back in unchanged.

## Terminal Effects

### Scanline Overlay

A fixed full-viewport `body::before` paints faint horizontal scanlines
(`repeating-linear-gradient`, `opacity: 0.15`, `pointer-events: none`,
`z-index: 9999`) for a subtle CRT texture.

### Flicker

Cards run a one-shot `terminal-flicker` keyframe (opacity 0.95→1→0.95) on load
to mimic a CRT refresh.

### Glow

Hover/focus states on links, buttons, nav items and inputs add
`text-shadow`/`box-shadow` using `--terminal-glow` (amber). Danger/warning
variants use softened red/yellow-tinted glows; `--terminal-success-glow`
remains jade for state indicators.

### Cursor

A `.form-control:focus::after` rule asks for a blinking `▋` block cursor via a
`cursor-blink` keyframe. Inputs, textareas and selects do not render
`::after`, so the cursor never appears.

## Utility Classes

Custom terminal helpers beyond Bootstrap:

| class | effect |
|---|---|
| `.terminal-prompt` | a `>` before the element (`::before`), in `--terminal-accent` |
| `.terminal-command` | `--terminal-accent` text |
| `.terminal-output` | `--terminal-text-muted` text |
| `.terminal-error` | `--terminal-red` text |
| `.terminal-warning` | `--terminal-yellow` text |
| `.text-accent` | `--terminal-accent` text (`!important`) |
| `.border-accent` | `--terminal-accent` border colour (`!important`) |

**Use `.text-accent` / `.border-accent` for decoration.** Reach for
`.text-success` only when the element genuinely reports a healthy state. If a
class says *success*, the element should be reporting success (#1432). The
sleeve pages follow this: their plates no longer borrow `.text-success` /
`.border-success`, which put green on pages with nothing to report.

## Responsive Design

A `@media (max-width: 768px)` block shrinks the navbar brand and `h1`/`h2`,
and adds card spacing. A `@media (max-width: 600px)` block tightens the
homepage hero padding and the gap between actions, and
`prefers-reduced-motion` turns off the brand mark's hover transition. Broader
responsive layout/screen-size behaviour is covered by
`WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md`.

## Accessibility

- **Focus indicators:** every interactive element gets a `1px solid` amber
  outline with `2px` offset.
- **Contrast (measured, not estimated):** bone `#d8d3c4` on ink `#0b0e14` is
  **12.9:1**, comfortably past WCAG AAA for body text. Muted bone on ink is
  **5.8:1**; amber-dim on plate is **5.5:1**. Jade, yellow and red are tuned
  to stay legible on the dark ground while remaining muted.
- **Measure:** homepage prose (the deck, the lore, the status note) is capped
  at `--measure` (72ch); plate captions at 85ch. See *Layout & Measure*.
- **Print styles:** `@media print` swaps to black-on-white and hides
  scanlines, navbar and footer.

## The Atlas (addendum)

**The Atlas is a second visual world, on purpose.** `scripts/atlas/` renders
the colony map as a self-contained document in its own register (night plate
`#0b0e14`, bone text, amber emphasis, cyan reserved for data, condensed /
serif / mono type roles). It is embedded into the site at `/atlas/` through
`web/templates/website/atlas.html` in *fragment* mode, so the site's header
and footer carry through.

- The picture inside the plate is the *live render*: `/atlas/` serves
  `scripts/atlas/template3d.html` (three.js), built by `build_atlas3d_html()`
  in `world/atlas.py` and cached by `atlas_view()` in
  `web/website/views/atlas.py`. The plate chrome (title row, place line, lore,
  staged frame, house-token `:root` mapping) is not 3D; only the stage is
  3D.
- The painted sprite plate, `scripts/atlas/template.html`, is not served. It
  survives as the builder's staff instrument: `scripts/atlas/generate.py`
  emits it through `build_atlas_html()` in `world/atlas.py`, and it is opened
  as a standalone file.
- The plate re-asserts its own type roles inside `.atlas-plate` with
  `!important`, so it renders the same embedded or standalone. The scoping is
  deliberate, not a leak.
- The plate's canvas is kept free of inherited letter-spacing (the second rule
  in the `ADDITIONS (2026-07-29)` block of `custom.css`).

## The Webclient

The webclient (`web/static/webclient/css/webclient.css`, #1434 / #1436) uses
the site palette. Six tokens mirror the site's: ink, plate, plate-hi, bone,
bone-dim, cool rule. The command bar's focus ring and send button are amber.
Every colour in that file resolves through `:root`, so the tokens do the whole
shell.

**The webclient is safe to restyle.** `webclient.css` styles **chrome only**.
Game output colour comes from `ansi_up` with `use_classes = false` (see
`web/static/webclient/js/gel.js`), i.e. inline styles straight off the
xterm-256 table. No stylesheet change can affect ANSI or GMCP output, which is
why the client can be themed without risking the game.

**What stays jade, deliberately:** `#connection-state .state-dot.connected`
and `.sys-msg.success`. Both sit in a green/yellow/red triad
(connected/connecting/disconnected, success/warning/error). Recolouring them
would break a signal to fix a decoration.

**Contrast, measured** on the ground each element sits on (the placeholder
sits on `#input-field`'s own background, `--bg-light` `#182030`, not the bar
behind it):

| element | colours | ratio |
|---|---|---|
| output text | bone on ink | 12.91:1 |
| input text | bone on plate-hi | 10.90:1 |
| muted status | muted on ink | 5.80:1 |
| send button | amber-dim on plate | 5.52:1 |
| input placeholder | opacity `0.8` | 3.63:1 |

The placeholder's opacity is `0.8` rather than `0.6` (2.63:1): still clearly a
hint, now legible.

The code comment on `#input-field::placeholder` in `webclient.css` says "0.8
lifts it to ~3.3:1", and no candidate ground yields 3.3 (`--bg-medium` gives
3.93, ink gives 4.09). **Fix the comment, not this figure.** Unfiled code
defect.

## Discourse Integration

The forum embeds the game navbar via `header_only.html`, which loads the same
`custom.css`, so the iframe header matches the main site automatically.

The surrounding forum is themed by a **Discourse theme component**,
"Domino's Gambit", built from `web/discourse-theme/`, plus a matching colour
scheme. Two things about it are load-bearing:

- **It must be a component (`"component": true`), never a standalone theme.**
  The header iframe is injected by JavaScript living in a *different*
  component. Installing a standalone theme and setting it default replaces the
  parent theme and takes the header with it. This is documented in
  `DISCOURSE_INTEGRATION.md` Step 4, and was still got wrong once.
- **Colour schemes do not travel with components.** The palette has to be
  created separately and selected on the parent theme's **light slot**
  (`color_scheme_id`), and the **dark slot (`dark_color_scheme_id`) must stay
  EMPTY**. Every palette we ship is dark-styled, so a single `media=all`
  stylesheet serves all viewers, which is exactly what the skins component
  (`web/discourse-theme/…/skins.gjs`) is built against. Filling the dark slot
  makes Discourse emit a second `(prefers-color-scheme: dark)` stylesheet the
  moment any skin cookie is present, and that dark link resurrects the default
  palette for dark-OS viewers: every skin toggle silently refuses to apply on
  full loads (it looks exactly like "signed-in users can't change themes"). If
  the dark slot ever points at an OLD palette instead, dark viewers stay on
  stale colours. Empty is the only correct value.

Fonts ship as theme uploads inside the component, so the forum does not depend
on gel.monster being reachable for its typography. See
`DISCOURSE_INTEGRATION.md` / `FORUM_INTEGRATION_GUIDE.md`.

## Editing & Deploying Styling

`custom.css` is **tracked**, so styling ships through the normal issue →
branch → PR → squash-merge → live reset cycle like any other change. The one
extra step is `collectstatic`, because static assets are hashed
(`ForgivingManifestStaticFilesStorage` in `web/utils/staticfiles.py`, wired
through `STORAGES` in `server/conf/settings.py`). Hashed filenames give every
change a new URL; without them a CSS deploy stays invisible until Cloudflare's
edge TTL expires, because the file keeps one URL and the edge serves a stale
copy.

1. Edit `web/static/website/css/custom.css` in the **dev repo** and ship it
   through the deploy cycle.
2. Run `collectstatic` in the container so the change gets a new hashed URL:
   ```bash
   docker exec <CONTAINER> evennia collectstatic --noinput --settings settings.py
   ```
3. Reload so templates pick up the refreshed static files. With the owner's
   go and after looking at who is connected, type `@reload` from a logged-in
   developer character, then check within 30 seconds that the Server is
   running (see `AGENTS.md`, "Reload from inside the game"):
   ```bash
   docker exec <CONTAINER> evennia status --settings settings.py
   ```
4. Hard-refresh the browser (cache-bust) to confirm.

The same applies after changing any static asset: `collectstatic`, then
reload.

### Django template comments

**`{# … #}` is single-line only in Django.** A multi-line one renders as
literal text on the page. Multi-line comments need `{% comment %}` /
`{% endcomment %}`. A *newly shadowed template* is the gap a sweep of the
existing tree cannot cover. An in-tree reminder sits in
`web/templates/website/homepage/main-content.html`; it is worth repeating in
any template we newly fork.

## Customization Guide

Recolor by editing the `:root` variables; every component references them:

```css
:root {
    --terminal-accent: #e0a86f;    /* accent */
    --terminal-bg-dark: #0b0e14;   /* ground */
    --terminal-glow: rgba(224, 168, 111, 0.30);
}
```

Changing the accent means changing it in **five** files, or the surfaces drift
apart:

1. `custom.css` (`:root`);
2. `scripts/atlas/template3d.html`, the plate `/atlas/` serves;
3. `scripts/atlas/template.html`, the sprite plate, which inherits the tokens
   with standalone fallbacks and needs the same fallback edit because the staff
   instrument is opened as a standalone file;
4. `web/static/webclient/css/webclient.css`;
5. the Discourse colour scheme.

**Skins.** The Atlas register is one of seven skins. `custom.css` carries six
`[data-skin]` palette blocks (`terminal`, `stray`, `dub`, `prism`, `laughing`,
`ed`). None of the skin entries is edited by hand: the six palette blocks,
`SKIN_INK` in `web/website/views/header_only.py` (the forum header's
critical-CSS ground, per skin), the webclient's skin block, `skins.js` and
`skins.gjs` sit between `GENERATED SKINS (build_skins.py)` markers, and
`scripts/brand/build_skins.py` rewrites them from the `.ghostty` manifests in
`web/static/website/skins/` (7 files), along with
`scripts/brand/seed_skins.rb` and
`scripts/brand/nginx-gel-skin-map.generated.conf` for the Discourse side. Only
the default (atlas) values in `:root` are edited by hand.

**Brand mark.** It follows automatically wherever it is inlined, since it
reads the tokens. `gm-mark.svg` and `gm-patch.svg` carry literal fallbacks for
standalone use, and the rasters are flattened to literal hex. If the accent
moves, regenerate them (see *Regenerating the mark*).

Adjust glow by changing the `--terminal-glow` alpha and the `text-shadow`/
`box-shadow` blur radii. Disable scanlines by removing the `body::before`
block.

## Maintenance Notes

When updating Evennia or Bootstrap, verify:

- `base.html`/`header_only.html` still link `custom.css` after the framework
  CSS;
- no new default styles conflict;
- Bootstrap stays at 4.6 (or the overrides are reviewed against the new
  version), on both files and for both CSS and JS;
- `collectstatic` still publishes the file;
- the forked `web/templates/website/base.html` is resynced against upstream.

## Not decided

- **`.table-hover` tints rows jade** (`rgba(95, 211, 141, 0.08)`), which the
  colour rule forbids; plate tables hover on `--terminal-bg-light`. No repo or
  Evennia template uses `.table-hover` today, so nothing renders it either way.
  OPEN for the owner.
- **The scanline weight.** A stale duplicate copy of the theme, removed in
  #3356, produced a heavier scanline than the `opacity: 0.15` the file now
  declares. Whether that heavier scanline had become the look to keep is
  #3285's question.
- **How this spec describes the brand mark.** Whether the *Brand Mark* section
  stays written around the current mark, with the retired GM orbit mark kept
  as one historical note, is not decided (#3285).
- **The site-side skin system has no spec anywhere in `specs/`.** This is the
  only document that could hold it. Owner question.

## Related Documentation

- `WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md`: responsive client layout.
- `WEB_CHARACTER_CREATION_ALIGNMENT.md`, `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md`: web flows.
- `DISCOURSE_INTEGRATION.md`, `FORUM_INTEGRATION_GUIDE.md`: forum theming.
- Bootstrap 4.6: https://getbootstrap.com/docs/4.6/
- Evennia web templates: https://www.evennia.com/docs/latest/Components/Web-Templates.html
