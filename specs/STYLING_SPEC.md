# Website Styling Specification

> **Status:** ✅ **SHIPPED & LIVE** — the Atlas register across all four surfaces (site, Atlas, forum, webclient). ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 25 claim(s) false, annotated inline**; `custom.css` is the source of truth and this document describes it.

## Overview

Gelatinous uses a custom **terminal/brutalist** web theme layered on top of
Bootstrap 4.6. Since 2026-07-29 the house style is the **Atlas register**: an
ink ground, bone text, and a single amber accent, set in the **Monaspace**
family. The look is built from a small set of CSS custom properties plus
subtle CRT-style effects (scanlines, flicker, glow).

All styling lives in a single file, `web/static/website/css/custom.css`, which
overrides Bootstrap and Evennia defaults.

> **⚠ Re-verified 2026-09-11 — two corrections to the sentence above.**
>
> 1. "A single file" describes the *website* surface only. The four-surface
>    house style also lives in `web/static/webclient/css/webclient.css`,
>    `scripts/atlas/template.html` + `template3d.html`, and
>    `web/discourse-theme/common/common.scss` — all documented further down.
> 2. `custom.css` is not internally consistent, so "the CSS wins" is not a
>    usable tiebreak as written. Sections `NAVBAR` through `PRINT STYLES`
>    appear **twice** — `:144-670` and `:672-1199`, ~528 lines — and the
>    *second* copy is the stale pre-Atlas theme. Because it comes last it wins
>    every cascade tie the first copy did not settle with `!important`, so
>    several values this document states are correct *in the file* but are not
>    what renders. Flagged at each affected claim below.
>
> **Root cause, traced 2026-09-11: the restore reached for the wrong
> ancestor.** `497109f0` (#1398, 2026-07-29) recovered the theme from
> `2848e7e^` = `6b8bfcac` — verified by blob comparison: `497109f0`'s file is
> `6b8bfcac`'s 1080 lines plus that night's two additions and nothing else.
> But `6b8bfcac` is the copy that *had* the duplicate tail. Its other child,
> `fa1a9a64` (2025-10-24, sibling of the untracking commit `2848e7e2`), had
> already **deleted the 526-line duplicate** (`@@ -555,526 +555,87 @@`) and put
> the Evennia help/channel override block in its place. Restoring the shared
> parent instead of `fa1a9a64` resurrected the duplication *and* dropped that
> block in one move — which is why the two defects flagged below are one
> regression with one source:
>
> ```bash
> git show fa1a9a64:web/static/website/css/custom.css   # deduplicated, block intact
> ```
>
> That copy predates the Atlas repalette, so it still says `--terminal-green`
> / `--terminal-green-dim`; rename to `--terminal-success` /
> `--terminal-success-dim` before reuse (see the palette note below).
>
> **Unfiled code defect: the duplication is the thing to fix, not this
> document.**

> **Source of truth:** the live `custom.css` is canonical. This spec describes
> what that file implements; if they disagree, the CSS wins and this document
> should be updated to match.

**Design philosophy:**
- Terminal/brutalist aesthetic, set entirely in Monaspace — the typeface does
  the terminal work, so the chrome doesn't have to shout.
- Dark, low-glare ground (`#0b0e14`, Atlas ink) rather than pure black.
- **Amber (`#e0a86f`) is the accent** — links, focus, emphasis, the control
  you're using. One accent, used sparingly.
- Subtle glow / scanline / flicker effects for atmosphere, kept understated.
- Uppercase navigation, headings, labels, and buttons for a corporate-terminal feel.
- Minimal decoration, high information density.

### The colour rule (applies to every surface)

**Jade is STATE. Amber is ACCENT. Cyan is DATA.**

Jade `#5fd38d` used to be the accent, and was demoted deliberately. It now
means one thing — *good* — and it sits in a set with `--terminal-yellow`
(warning / connecting) and `--terminal-red` (error / disconnected). Spending
it on decoration dilutes a signal, so plate borders, rules, focus rings, and
headings take amber instead.

Cyan `#6fd6e0` is reserved for machine-readable data in the Atlas and in-game
readouts. It is never decoration and never inherited into site chrome.

This rule holds across all four surfaces: website, Atlas, forum, and webclient.

## File Location & Version Control

```
web/static/website/css/custom.css
```

> **⚠ CHANGED 2026-07-29 — the file is now TRACKED, and this is why.**
> Being untracked cost us the theme. An agent (me) read the empty dev-repo
> path, concluded the site was unthemed stock Bootstrap, wrote a new
> theme to that path, tracked it, and the live-dir `git reset --hard`
> overwrote the untracked original. The 1080-line theme survived only
> because it had been tracked once, before `2848e7e` — everything edited
> live after 2025-10-24 was unrecoverable.
>
> `custom.css` is therefore **tracked** now, via narrow `.gitignore`
> exceptions under `web/static/website/css/`, and edits belong in the dev
> repo and ship through the normal deploy cycle. **Do not untrack it
> again.** The paragraph below records the old arrangement for history.

**(Historical) `custom.css` was not tracked in git.** `.gitignore` ignores `web/static/*`
(excepting only `web/static/webclient/`), and the file was removed from tracking
in commit `2848e7e` ("Remove custom.css from git tracking (should be generated by
collectstatic)").

Consequences worth knowing before editing:

- The file exists **only as an untracked file in the live deployment**
  (`<LIVE_DIR>/web/static/website/css/custom.css`). There is no copy in the dev
  repo and none in git history.
- Because it is untracked, it is **not** carried by the deploy hard-reset
  (`git reset --hard origin/master`). Editing styling means editing the file in
  the live checkout directly, then running `collectstatic`.
- Treat it as deployment-local state. Back it up out-of-band; a clean checkout
  will not contain it.

## Loading Mechanism

`custom.css` is loaded **after** Bootstrap and Evennia's `website.css`, so its
rules win on specificity ties (and it uses `!important` where Bootstrap is
stubborn).

- **Main site:** Evennia's default `base.html` head block links
  `website/css/custom.css` after Bootstrap and `website.css`.
  > **2026-09-11:** it is **our** `base.html` now, not Evennia's default —
  > `web/templates/website/base.html`, forked 2026-08-10 by `38df091a`
  > (#1909). The load order the argument depends on is unchanged (Bootstrap
  > CDN `:18`, `website.css` `:20`, `custom.css` `:25`), so the specificity
  > reasoning still holds — but the file that guarantees it is ours to keep in
  > step on every Evennia upgrade. See *The favicon is named
  > `evennia_logo.png` on purpose* below.
- **Discourse iframe header:** `web/templates/website/header_only.html` (a minimal
  navbar-only template embedded in the forum) links the same file explicitly:

  ```html
  <!-- header_only.html -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css" ...>
  <link rel="stylesheet" href="{% static 'website/css/website.css' %}">
  <link rel="stylesheet" href="{% static 'website/css/custom.css' %}">
  ```

  `header_only.html` also inlines a critical-CSS block painting the ink ground
  immediately, before external CSS loads, so the embedded navbar matches the
  main site with no flash. **That block must use the literal `#0b0e14`, not
  `var(--terminal-bg-dark)`** — the token is defined in `custom.css`, which has
  not loaded yet, and an undefined custom property invalidates the whole
  declaration. It shipped broken for exactly that reason; keep the literal in
  sync with the token by hand.

  It no longer loads Google Fonts. Monaspace is self-hosted and same-origin
  with the iframe, so the header picks it up from `custom.css` directly.

Bootstrap is pinned to **4.6** (CDN in `header_only.html`; Evennia ships 4.6 for
the main site).

> **⚠ 2026-09-11 — true of the CSS only, and the two surfaces disagree.**
> Bootstrap *CSS* is 4.6.0 on both (`base.html:18`, `header_only.html:33`).
> The *JavaScript* is not pinned with it: the main site loads jQuery
> 3.2.1-slim, Popper 1.12.9 and **Bootstrap 4.0.0** JS (`base.html:69`, `:74`,
> `:75`), while the forum header loads jQuery 3.6.0 and the **Bootstrap
> 4.6.2** bundle (`header_only.html:96-97`). A 4.6/4.0 split inside one page,
> and two surfaces that do not match each other.
>
> Those version strings came in verbatim from upstream Evennia when the fork
> was taken, so this was already the case on the 2026-08-02 banner date — but
> `base.html` is ours now, so the drift is ours to own. Read the *Maintenance
> Notes* obligation ("Bootstrap stays at 4.6") as covering **both files and
> both asset types**. Low severity — 4.0 JS is broadly API-compatible with 4.6
> CSS — but the navbar dropdown behaviour documented in
> `DISCOURSE_INTEGRATION` / #1466 rides this JS, and it is now invisible debt
> in a file nobody expects to own.

## Color Palette

Defined as CSS custom properties on `:root` (the Atlas register):

```css
:root {
    --terminal-bg-dark: #0b0e14;         /* Atlas ink — the ground */
    --terminal-bg-medium: #11161f;       /* Atlas plate — cards, raised */
    --terminal-bg-light: #182030;        /* Atlas plate-hi — inputs, hover */
    --terminal-accent: #e0a86f;          /* Atlas amber — the highlight */
    --terminal-accent-dim: #b8834f;      /* Dimmed amber */
    --terminal-text: #d8d3c4;            /* Atlas bone — creamy, not white */
    --terminal-text-muted: #8f8d82;      /* Atlas bone-dim */
    --terminal-success: #5fd38d;         /* jade — STATE only */
    --terminal-success-dim: #4a9d6d;
    --terminal-yellow: #e6c547;          /* Softer warning yellow */
    --terminal-red: #e85555;             /* Softer error red */
    --terminal-border: #232c3a;          /* Atlas line — cool rule */
    --terminal-glow: rgba(224, 168, 111, 0.30);   /* amber glow */
    --terminal-success-glow: rgba(95, 211, 141, 0.3);
}
```

| Variable | Value | Usage |
|----------|-------|-------|
| `--terminal-bg-dark` | `#0b0e14` | Body, navbar, footer, card headers |
| `--terminal-bg-medium` | `#11161f` | Cards, dropdowns, alerts, list groups |
| `--terminal-bg-light` | `#182030` | Form inputs, hover |
| `--terminal-accent` | `#e0a86f` | Links, focus, emphasis, plate chrome |
| `--terminal-accent-dim` | `#b8834f` | Accent at rest |
| `--terminal-text` | `#d8d3c4` | Primary text |
| `--terminal-text-muted` | `#8f8d82` | Secondary/disabled text |
| `--terminal-success` | `#5fd38d` | **State only:** healthy / active / success |
| `--terminal-yellow` | `#e6c547` | Warnings, archived |
| `--terminal-red` | `#e85555` | Errors / destructive actions |
| `--terminal-border` | `#232c3a` | Borders, separators |
| `--terminal-glow` | `rgba(224,168,111,0.30)` | Glow on hover/focus |

> **`--terminal-green` no longer exists.** It was renamed `--terminal-success`
> when jade was demoted to state. Anything still referencing the old name is a
> bug, not a fallback — there is no `--terminal-green` in the file.

The palette is deliberately *softened*: no pure black, no pure white, no pure
`#00ff00`. Ink is blue-black rather than neutral grey, and text is bone rather
than white, which is what makes the surfaces read warm instead of clinical.

## Typography

### Font Stack

The site is set in **Monaspace**, self-hosted as variable `woff2` files from
`web/static/website/fonts/` via four `@font-face` blocks. Nothing is loaded
from Google Fonts.

Type is assigned **by role**, not globally:

```css
--font-prose:   'Monaspace Neon',  ui-monospace, 'SF Mono', Menlo, monospace;
--font-reading: 'Monaspace Argon', ui-monospace, 'SF Mono', Menlo, monospace;
--font-display: 'Monaspace Xenon', ui-monospace, 'SF Mono', Menlo, monospace;
--font-data:    'Monaspace Neon',  ui-monospace, 'SF Mono', Menlo, monospace;
--font-hand:    'Monaspace Radon', 'Monaspace Neon', cursive;
--size-body: 15.5px;
--size-h1: 32px;
```

| Role | Face | Used for |
|------|------|----------|
| prose | Neon | body copy, lore |
| reading | Argon | longer reading passages |
| display | Xenon | headings, plate heads |
| data | Neon | figures, labels, status chips |
| hand | Radon | reserved for human marks; its one user (the memorial wall) was folded into the sleeve listing |

Because these are variable fonts, `@font-face` declares the axes
(`font-weight: 200 800`, `font-stretch: 100% 125%`, `font-style: oblique 0deg
11deg`) and `font-synthesis: none` prevents the browser faking what it can
already interpolate. Feature settings are `"calt" 1, "liga" 1, "cv01" 1` —
texture healing, standard ligatures, and the slashed zero. Code ligatures
(`ss01`–`ss10`) stay **off**.

> **The old `* { font-family: 'Inter' … !important }` rule is gone.** It was a
> global override that also captured the Atlas plate and made two-thirds of the
> homepage lore unreadable at the wrong weight and slant. Type is assigned per
> role now; do not reintroduce a global `!important` font rule.

### Uppercase Chrome

Headings, navbar links, card headers, table headers, labels, and buttons are
`text-transform: uppercase` with increased `letter-spacing` (0.05–0.1em) for a
corporate/military terminal feel.

```css
h1, h2, h3, h4, h5, h6 {
    color: var(--terminal-text);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
```

## Layout & Measure

**One column, everywhere.** `.container` *is* that column, which is what makes
Evennia's navbar (defined in `base.html`, which we never fork) share its left
and right edges with page content for free.

> **⚠ 2026-09-11: `base.html` IS forked now.** `38df091a` (#1909, 2026-08-10)
> created `web/templates/website/base.html` — the sanctioned template-shadow
> route — to declare an `apple-touch-icon` (`:12`). The shared-column argument
> here is unaffected: the navbar still lives in `_menu.html`, and the fork
> touches nothing but two `<head>` links.
>
> It is **not** otherwise identical to upstream, though, and the second
> deviation is easy to lose: `4b7f7b54` (#1911) also rewrote the stock
> `rel="icon"` declaration to `type="image/png" sizes="256x256"` (`:11`),
> because the stock `type="image/x-icon"` pointing at a PNG is a MIME mismatch
> WebKit treats as licence to ignore the declaration and keep its stored icon
> forever (edge logs: no device ever fetched the hashed logo). Two deviations,
> both in `<head>`.
>
> This spec asserts "we never fork `base.html`" in **four** places — here,
> `:86`, `:278` and `:339` — and all four are now stale. A forked template
> carries an obligation the unforked one did not: **resync it against upstream
> on every Evennia upgrade.**

```css
:root {
    --page-col: min(92vw, 1140px);   /* the shared column */
    --measure: 72ch;                 /* readable line length */
    --s1: 8px;  --s2: 16px; --s3: 24px;
    --s4: 40px; --s5: 64px; --s6: 96px;
}
```

**Prose is bounded by MEASURE, not by centring.** This is the distinction that
matters. The homepage previously centred an ~85ch text column inside a shell up
to 2100px wide and then filled that shell with a widget row — two centred
objects of different widths, sharing no edge, which reads as floating rather
than composed. Text now starts on the shared left edge and simply *stops* at
`--measure`.

Use the spacing scale (`--s1`…`--s6`) rather than ad-hoc margins.

**The Atlas opts out**, because a map wants width, not measure:

```css
.atlas-plate {
    width: min(96vw, 2100px);
    margin-left: calc((100% - min(96vw, 2100px)) / 2);
}
```

A negative margin rather than a `transform`, which would soften the plate's
hairlines.

> **Retuning:** `--page-col` moves every surface at once. Note it currently
> narrows table-heavy pages (Manage Sleeves) relative to the wider shell they
> had before; widen the token or give those pages the Atlas break-out treatment
> if that proves too tight.

### Homepage structure

Hierarchy carries the argument: **thesis → deck → one action → lore → honest
statement of state → figures**. The classes are `.hero`, `.deck`, `.actions`
with `.btn-play` (exactly one primary) and `.btn-quiet` (secondary),
`.status-note` (the pre-alpha statement), `.status-band` with `.figure`, and
`.recent`.

Two rules worth keeping:

- **One primary action.** Previously the page had none — "play" was the eighth
  item in the nav — so a reader who finished the lore had nowhere to go.
- **Figures are not features.** Accounts / sleeves / rooms are context for
  regulars, not a headline for a first-time reader, so they sit in one quiet
  band rather than three cards competing with the pitch. Only "connected now"
  is jade, because it is the only figure that is STATE.

## Brand Mark

The **GM orbit mark**: a bounding circle, one inclined orbit (−20°), a dashed
inner track, a broken polar axis, and two bodies on their paths, with a **GM**
monogram in a knockout disc at the centre so the orbit passes *behind* the
letters instead of through them.

**It carries no colour of its own.** The mark is inlined into
`_menu.html` and `_menu_iframe.html` (both ours — no `base.html` fork), and
every stroke and fill reads a theme token:

```css
.brand-mark .ring  { stroke: var(--terminal-accent); }
.brand-mark .node  { fill:   var(--terminal-accent); }
.brand-mark .knock { fill:   var(--terminal-bg-dark); }
.brand-mark .mono  { fill:   var(--terminal-text); font-family: var(--font-display); }
```

Change `--terminal-accent` and the mark follows. The monogram is set in the
display face, so the logo is built from the same type system as the headings.
Inlining also costs no HTTP request.

**Two cuts, deliberately.** The detailed mark turns to mud below ~60px:

| cut | where | what changes |
|-----|-------|--------------|
| full | `web/static/website/images/gm-orbit.svg`, forum, social | all five elements, hairline strokes |
| compact | navbar, favicon | dashes and axis dropped, strokes thickened, monogram enlarged |

The standalone SVG uses the same tokens with **literal fallbacks**
(`var(--terminal-accent, #e0a86f)`), so it renders correctly outside a page —
verified by rendering it in isolation, not assumed.

**The plate is a disc, not a tile.** Anywhere the mark needs a ground behind
it (the standalone SVG, the favicon raster) that ground is a circle at the
ring radius, with transparent corners. A full-bleed `<rect>` renders the mark
as a dark square in a browser tab and against any non-ink surface. When
re-exporting the raster, confirm the alpha channel survived (`sips -g
hasAlpha`) — a flattened render silently re-bakes the square and looks
identical in a file listing.

The inline navbar mark has no background element at all, which is why it can
look right on the site while an exported icon looks like a tile.

### Apple touch icons (iOS/iPadOS) span three systems

iOS ignores `rel="icon"` for home-screen/bookmark/share icons and probes
**root paths** (`/apple-touch-icon.png`, `-precomposed`, sized variants)
whenever a page declares no `apple-touch-icon` link — and Apple **flattens
transparency onto black**, so the disc-with-transparent-corners cuts become
mismatched black tiles. The working setup (2026-08-20):

- `web/static/website/images/apple-touch-icon.png` — 180×180, **fully
  opaque**: Atlas-ink full-bleed ground with the mark composited on it.
- `web/urls.py` routes the whole root probe family to it (same RedirectView
  pattern Evennia uses for `/favicon.ico`); the webclient template also
  declares it explicitly.
- **Cloudflare**: the zone's path-allowlist firewall rule must include
  `starts_with(http.request.uri.path, "/apple-touch-icon")` (it sits right
  after the `/favicon.ico` clause). Before this, iOS probes were BLOCKED at
  the edge and Apple devices improvised icons — the "favicon is all over the
  place" bug. Anything added at a root path needs an allowlist clause or it
  does not exist outside the LAN.
- **Discourse**: `apple_touch_icon` site setting carries the same opaque
  icon (uploaded via rails `UploadCreator`; the tab `favicon` stays the
  plain disc mark).

### The favicon is named `evennia_logo.png` on purpose

`base.html` hardcodes `rel="icon"` to `website/images/evennia_logo.png`. Rather
than fork it, our static dir **shadows** that path — `STATICFILES_DIRS` is
searched before the package (confirmed with
`finders.find('website/images/evennia_logo.png', all=True)`), so our file wins
and the favicon changes on both the site and the webclient with no template
edit. Do not "tidy" the filename; the link target is not ours to change.

> **⚠ 2026-09-11: the fork happened anyway — but keep the shadow.** `38df091a`
> (#1909, 2026-08-10) shadowed `website/base.html` into
> `web/templates/website/base.html` for one reason: iOS keeps a stored touch
> icon forever and never re-probes while an entry exists, so a page that
> *declares* a touch-icon URL it has not seen is the only reliable refetch
> trigger (live-verified in edge logs — the webclient's declared link fetched
> instantly through a stale store, undeclared pages never fetched at all).
> `4b7f7b54` (#1911) then fixed the stock `rel="icon"` MIME mismatch in the
> same file.
>
> **The `evennia_logo.png` shadow is still how the `rel="icon"` target is
> replaced** — the `href` at `base.html:11` is unchanged, and
> `STATICFILES_DIRS` still wins. Both techniques are in use now, and
> everything above about not tidying the filename stands. Add one obligation:
> **resync the fork against upstream on every Evennia upgrade.**

> **⚠ `evennia_logo.png` and `favicon.ico` were untracked live-only files** —
> no repo copy, no history, invisible to review, gone on a clean checkout. The
> same fragility that destroyed `custom.css`. Both are committed now, and the
> original cube is preserved as `legacy-cube-logo.png` / `legacy-favicon.ico`
> rather than overwritten.
>
> Adding anything to `web/static/website/images/` needs a narrow `.gitignore`
> exception (the directory is ignored by default, like `css/` and `fonts/`).
> **Verify with `git add --dry-run`** — `git check-ignore -v` prints the
> matching rule even when that rule is a *negation*, which is easy to misread
> as "still ignored".

## Component Styling

`custom.css` themes the full Bootstrap 4.6 component set against the palette.
Highlights:

- **Navbar / footer:** transparent, borderless, no shadow — they blend
  seamlessly into the body ground rather than banding against it. Links
  uppercase with an amber glow (`text-shadow`) on hover. Dropdowns use
  `--terminal-bg-medium`. The footer is unpinned from Evennia's
  `position: absolute` so tall pages (the Atlas) place it correctly.
- **Cards:** `--terminal-bg-medium` body, `--terminal-bg-dark` header (uppercase);
  all nested content forced to the dark theme. Brief `terminal-flicker` animation
  on load.
- **Links:** `--terminal-accent-dim` at rest → `--terminal-accent` + glow on hover.
- **Buttons** (`primary`, `secondary`, `danger`, `warning`): dark fill, colored
  1px border + matching text, uppercase; on hover/focus the border/text brighten
  and gain a `box-shadow` glow in the relevant hue.
- **Forms:** dark inputs; on focus the border turns amber with a glow, plus a
  blinking terminal cursor (`▋`) via `::after`.
- **Alerts:** dark fill with a coloured border/text per state (success=jade,
  warning=yellow, danger=red) — these are state, so they keep their hues.
- **Tables / pagination / breadcrumbs / code blocks / list groups / badges:** all
  re-skinned to the palette; tables hover on `--terminal-bg-light`.
- **Plates:** the `.plate-head` / `.plate-place` / `.plate-stamp` / `.plate-lore`
  / `.plate-stage` / `.plate-empty` set is the house page pattern, shared by the
  Atlas and the sleeve pages — a centred head, a caption at measure, and a stage
  holding the content.
- **Evennia help/channel overrides:** a dedicated block re-skins `.thead-light`,
  `.list-group-item`, `.badge-light`, `.alert-secondary`, etc., so Evennia's
  default web help and channel pages match.
  > **⚠ 2026-09-11 — the block is GONE, but it was real and it is
  > recoverable.** In today's `custom.css`: `thead-light` 0 occurrences,
  > `list-group-item` 0, `badge-light` 0, `alert-secondary` 0. It was lost on
  > **2026-07-29** as collateral damage from the wrong-ancestor restore
  > described in the Overview note — `497109f0` (#1398) recovered the theme
  > from `2848e7e^` (`6b8bfcac`) rather than from `fa1a9a64`, and `fa1a9a64`
  > is the only commit that ever carried this block. That is *before* the
  > 2026-08-02 banner date, which is why the banner cannot be taken at its
  > word.
  >
  > It survives verbatim:
  > `git show fa1a9a64:web/static/website/css/custom.css`, a section headed
  > `/* ===== EVENNIA HELP/CHANNEL PAGE OVERRIDES ===== */` at `:558-641`,
  > covering `.thead-light`, `.thead-light th`, `.card-header`,
  > `.list-group-item` (+ `:hover`, `.active`), `.badge-light`,
  > `.card.border-light`, `.alert-secondary`, `.alert-warning`, `.table` and
  > `pre`. **So this bullet was an accurate description of shipped code when
  > it was written** — it is stale, not invented.
  >
  > Reinstating it is close to a copy, with two caveats: that copy predates
  > the Atlas repalette and still references `--terminal-green` /
  > `--terminal-green-dim`, which no longer exist (see the palette note
  > above), and its jade `.list-group-item:hover` / `.active` treatment needs
  > checking against *Jade is STATE, never decoration* before it goes back in
  > unchanged. Whether those pages currently render pale Bootstrap defaults on
  > the ink ground was **not** confirmed in a browser.

## Terminal Effects

### Scanline Overlay

A fixed full-viewport `body::before` paints faint horizontal scanlines
(`repeating-linear-gradient`, `opacity: 0.15`, `pointer-events: none`,
`z-index: 9999`) for a subtle CRT texture.

### Flicker

Cards run a one-shot `terminal-flicker` keyframe (opacity 0.95→1→0.95) on load to
mimic a CRT refresh.

### Glow

Hover/focus states on links, buttons, nav items, and inputs add
`text-shadow`/`box-shadow` using `--terminal-glow` (amber). Danger/warning
variants use red/yellow-tinted glows; `--terminal-success-glow` remains jade
for state indicators.

### Cursor

Focused `.form-control` shows a blinking `▋` block cursor via a `cursor-blink`
keyframe.

## Utility Classes

Custom terminal helpers beyond Bootstrap:

```css
.terminal-prompt::before { content: ">"; color: var(--terminal-accent); }
.terminal-command { color: var(--terminal-accent); }
.terminal-output  { color: var(--terminal-text-muted); }
.terminal-error   { color: var(--terminal-red); }
.terminal-warning { color: var(--terminal-yellow); }

/* Chrome that wants the accent, WITHOUT borrowing a semantic class.
   Added because the sleeve pages were dressing plates in .text-success /
   .border-success, which put green on pages with nothing to report. */
.text-accent   { color: var(--terminal-accent) !important; }
.border-accent { border-color: var(--terminal-accent) !important; }
```

**Use `.text-accent` / `.border-accent` for decoration.** Reach for
`.text-success` only when the element genuinely reports a healthy state.

## Responsive Design

A `@media (max-width: 768px)` block shrinks the navbar brand and `h1`/`h2`, and
adds card spacing. Broader responsive layout/screen-size behavior is covered by
`WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md`.

## Accessibility

- **Focus indicators:** every interactive element gets a `1px solid` amber
  outline with `2px` offset.
- **Contrast (measured, not estimated):** bone `#d8d3c4` on ink `#0b0e14` is
  **12.9:1**, comfortably past WCAG AAA for body text. Muted bone on ink is
  **5.8:1**; amber-dim on plate is **5.5:1**. Jade, yellow, and red are tuned to
  stay legible on the dark ground while remaining muted.
- **Measure:** prose is capped at `85ch` with `1.75` line-height. The Atlas and
  the homepage share that measure so the two read identically.
- **Print styles:** `@media print` swaps to black-on-white and hides scanlines,
  navbar, and footer.

## Discourse Integration

The forum embeds the game navbar via `header_only.html`, which loads the same
`custom.css`, so the iframe header matches the main site automatically.

The surrounding forum is themed by a **Discourse theme component** —
"Domino's Gambit", built from `web/discourse-theme/` — plus a matching colour
scheme. Two things about it are load-bearing:

- **It must be a component (`"component": true`), never a standalone theme.**
  The header iframe is injected by JavaScript living in a *different*
  component. Installing a standalone theme and setting it default replaces the
  parent theme and takes the header with it. This is documented in
  `DISCOURSE_INTEGRATION.md` Step 4 — and was still got wrong once.
- **Colour schemes do not travel with components.** The palette has to be
  created separately and selected on the parent theme's **light slot**
  (`color_scheme_id`) — and the **dark slot (`dark_color_scheme_id`) must stay
  EMPTY**. Every palette we ship is dark-styled, so a single `media=all`
  stylesheet serves all viewers — which is exactly what the skins component
  (`web/discourse-theme/…/skins.gjs`) is built against. Filling the dark slot
  makes Discourse emit a second `(prefers-color-scheme: dark)` stylesheet the
  moment any skin cookie is present, and that dark link resurrects the default
  palette for dark-OS viewers: every skin toggle silently refuses to apply on
  full loads (looked exactly like "signed-in users can't change themes",
  2026-08-19). If the dark slot ever points at an OLD palette instead, dark
  viewers stay on stale colours — the original 2026-08-02 bug. Empty is the
  only correct value.

Fonts ship as theme uploads inside the component, so the forum does not depend
on gel.monster being reachable for its typography. See
`DISCOURSE_INTEGRATION.md` / `FORUM_INTEGRATION_GUIDE.md`.

## Editing & Deploying Styling

`custom.css` is **tracked**, so styling ships through the normal
issue → branch → PR → squash-merge → live reset cycle like any other change.
The one extra step is `collectstatic`, because static assets are hashed:

1. Edit `web/static/website/css/custom.css` in the **dev repo** and ship it
   through the deploy cycle.
2. Run `collectstatic` in the container so the change gets a new hashed URL:
   ```bash
   docker exec <CONTAINER> evennia collectstatic --noinput --settings settings.py
   ```
3. Reload so templates pick up the refreshed static files:
   ```bash
   docker exec <CONTAINER> evennia reload --settings settings.py
   ```
4. Hard-refresh the browser (cache-bust) to confirm.

> **Resolved 2026-07-29.** The tech debt described above — the only copy of
> `custom.css` living as an untracked deployment file — is what destroyed the
> theme. It is now tracked via narrow `.gitignore` exceptions and carried by
> the deploy. Do not reverse this.

## Customization Guide

Recolor by editing the `:root` variables — every component references them:

```css
:root {
    --terminal-accent: #e0a86f;    /* accent */
    --terminal-bg-dark: #0b0e14;   /* ground */
    --terminal-glow: rgba(224, 168, 111, 0.30);
}
```

Changing the accent means changing it in **four** places, or the surfaces drift
apart: `custom.css`, `scripts/atlas/template.html` (which inherits the tokens
with standalone fallbacks), `web/static/webclient/css/webclient.css`, and the
Discourse colour scheme.

> **⚠ 2026-09-11 — four is an undercount, and the Atlas entry needs splitting
> rather than correcting.** All four above are still real. But
> `scripts/atlas/template.html` is the *sprite* plate, and it is no longer
> served: `/atlas/` renders `scripts/atlas/template3d.html:13-18`
> (`world/atlas.py:148`, cached by `web/website/views/atlas.py:42`).
> `template.html` still needs the same fallback edit, because
> `scripts/atlas/generate.py` is its one consumer (`world/atlas.py:96`) and
> the staff instrument it emits *is* opened as a standalone file. So that is
> **five** files, not a substitution.
>
> Also required, none of them documented in this spec:
> - the **six `[data-skin]` palette blocks** at `custom.css:1914-1990`
>   (`terminal`, `stray`, `dub`, `prism`, `laughing`, `ed`) — the Atlas
>   register is now one of seven, not the only one;
> - **`SKIN_INK`** at `web/website/views/header_only.py:31-41`, the forum
>   header's critical-CSS ground, per skin;
> - the `.ghostty` sources in `web/static/website/skins/` (7 files) with
>   `scripts/brand/build_skins.py`, plus `scripts/brand/seed_skins.rb` and
>   `scripts/brand/nginx-gel-skin-map.generated.conf` for the Discourse side;
> - the raster brand exports, regenerated by
>   `scripts/brand/build_brand.py:135-158` (librsvg cannot resolve custom
>   properties, so PNG/ICO are flattened to literal hex by design).
>
> **The site-side skin system has no spec anywhere in `specs/`** — this is the
> only document that could hold it, and it mentions skins only on the
> Discourse side (`skins.gjs`). See owner questions.

The **brand mark follows automatically** wherever it is inlined, since it reads
the tokens — but `web/static/website/images/gm-orbit.svg` carries literal
fallbacks for standalone use, and `evennia_logo.png` is a raster export. Both
need re-rendering by hand if the accent moves.

> **2026-09-11.** `gm-orbit.svg` no longer exists (deleted `209b2acf`,
> 2026-08-03); read it as `gm-mark.svg` and `gm-patch.svg`, which carry the
> same `var(--terminal-accent, #e0a86f)` fallbacks (`gm-mark.svg:4-6`,
> `gm-patch.svg:4-6`). And "by hand" is no longer the procedure for the
> rasters: **run `scripts/brand/build_brand.py <outdir>`**, which regenerates
> both SVGs plus `gm-patch-{512,192}.png`, `gm-mark-{256,180,64}.png` and
> `favicon.ico` from one definition (`:135-158`).
>
> **Two hand steps remain, because the generator emits neither filename the
> site actually links.** `evennia_logo.png` is `gm-mark-256.png` under the
> Evennia name (256×256, alpha intact — see *The favicon is named
> `evennia_logo.png` on purpose* for why the name stays), and
> `apple-touch-icon.png` is the 180 composited onto an ink ground, which must
> stay **fully opaque** (`sips -g hasAlpha` → `no`) because Apple flattens
> transparency onto black.
>
> The librsvg caveat is worth carrying here too: rasters are flattened to
> literal hex **on purpose** (`build_brand.py:9-19`) — librsvg does not
> implement CSS custom properties and renders unresolved ones as silent grey.
> SVG follows the skin; PNG/ICO cannot and must not try.

Adjust glow by changing the `--terminal-glow` alpha and the `text-shadow`/
`box-shadow` blur radii. Disable scanlines by removing the `body::before` block.

## Related Documentation

- `WEBCLIENT_SCREEN_SIZE_DETECTION_SPEC.md` — responsive client layout.
- `WEB_CHARACTER_CREATION_ALIGNMENT.md`, `WEB_RESPAWN_CHARACTER_CREATION_SPEC.md` — web flows.
- `DISCOURSE_INTEGRATION.md`, `FORUM_INTEGRATION_GUIDE.md` — forum theming.
- Bootstrap 4.6: https://getbootstrap.com/docs/4.6/
- Evennia web templates: https://www.evennia.com/docs/latest/Components/Web-Templates.html

## Maintenance Notes

When updating Evennia or Bootstrap, verify: `base.html`/`header_only.html` still
link `custom.css` after the framework CSS; no new default styles conflict;
Bootstrap stays at 4.6 (or the overrides are reviewed against the new version);
`collectstatic` still publishes the file.

## Addendum (2026-07-29) — the Atlas, and cache-busting

**The Atlas is a second visual world, on purpose.** `scripts/atlas/` renders
the colony map as a self-contained document in its own register (night plate
`#0b0e14`, bone text, amber emphasis, cyan reserved for data, condensed /
serif / mono type roles). It is embedded into the site at `/atlas/` through
`web/templates/website/atlas.html` in *fragment* mode, so the site's header
and footer carry through. Since 2026-08-04 the picture inside the plate is
the *live render* (`template3d.html`, three.js) rather than the painted
sprite canvas — the plate chrome (title row, place line, lore, staged
frame, house-token `:root` mapping) is unchanged; only the stage went 3D.
The sprite plate survives as the builder's generated staff instrument
(`scripts/atlas/generate.py`). Because this theme sets a global
`* { font-family: 'Inter' … !important }`, the plate re-asserts its own type
roles inside `.atlas-plate` with `!important` — that scoping is deliberate,
not a leak.

**Two structural additions live at the bottom of `custom.css`:**

1. The footer is unpinned from Evennia's `position:absolute` band and the
   reserved `body` margin released, because a viewport-pinned footer
   misplaces itself on tall pages (the Atlas).
2. A note keeping the plate's canvas free of inherited letter-spacing.

**Static assets are now hashed** (`web/utils/staticfiles.py`,
`ForgivingManifestStaticFilesStorage` wired through `STORAGES` in
`server/conf/settings.py`). Before this, a CSS deploy was invisible until
Cloudflare's edge TTL expired — the file kept one URL forever, and the edge
served a stale copy through several rounds of "I don't see a difference".
Hashed filenames give every change a new URL. **After changing any static
asset: `evennia collectstatic --noinput`, then reload.**

## Addendum (2026-07-30) — the last two surfaces

The house style now covers **all four surfaces**: website, Atlas, forum, and
webclient. This addendum records the two that landed last, plus the rule that
finally made the palette coherent.

**The webclient joined the palette** (`web/static/webclient/css/webclient.css`,
#1434 / #1436). It had been on its own neutral greys (`#1a1a1a` / `#e0e0e0` /
`#404040`), which is why it read cooler and greyer than every other page. Six
tokens now mirror the site's — ink, plate, plate-hi, bone, bone-dim, cool rule
— and the command bar's focus ring and send button moved from jade to amber.
Every colour in that file resolves through `:root`, so the tokens do the whole
shell.

> **The webclient is safe to restyle.** `webclient.css` styles **chrome only**.
> Game output colour comes from `ansi_up` with `use_classes = false` (see
> `web/static/webclient/js/gel.js`) — i.e. inline styles straight off the
> xterm-256 table. No stylesheet change can affect ANSI or GMCP output. This
> was verified before touching it, and remains the reason the client can be
> themed without risking the game.

**What stayed jade, deliberately:** `#connection-state .state-dot.connected`
and `.sys-msg.success`. Both sit in a green/yellow/red triad
(connected/connecting/disconnected, success/warning/error). Recolouring them
would have broken a signal to fix a decoration.

**Contrast was measured, not eyeballed:** output text 12.9:1, input text
10.9:1, muted status 5.8:1, amber send button 5.5:1. The input placeholder was
the one weak spot at 2.6:1 (it had been 2.4:1), so its opacity went from `0.6`
to `0.8`, giving 3.6:1 — still clearly a hint, now legible.

> **2026-09-11 — recomputed; this paragraph holds, and the CODE COMMENT is the
> error.** All of it checks out against the shipped tokens, measured on the
> ground the placeholder actually sits on: `#input-field`'s own background,
> `--bg-light` `#182030` (`webclient.css:252`), not the bar behind it. Output
> text (bone on ink) **12.91:1**; input text (bone on plate-hi) **10.90:1**;
> muted status (muted on ink) **5.80:1**; amber send button (amber-dim on
> plate) **5.52:1**; placeholder at `0.6` **2.63:1**, at `0.8` **3.63:1**. The
> `0.6` → `0.8` change is confirmed at `webclient.css:269-274`.
>
> That code comment says "0.8 lifts it to ~3.3:1", and no candidate ground
> yields 3.3 — `--bg-medium` gives 3.93, ink gives 4.09. **Fix the comment,
> not this figure.** Unfiled code defect; it matters because this file is the
> spec's own evidence that contrast was measured rather than eyeballed.

**The sleeve pages stopped borrowing semantic classes** (#1432). The
Psychophysical Evaluation Report plate was dressed in `.text-success` /
`.border-success` — border, header, both `<hr>` rules — plus the Active label.
`.text-accent` / `.border-accent` exist now for chrome that just wants the
accent. If a class says *success*, the element should be reporting success.

**Evennia's `recently-connected-widget.html` is overridden locally**, purely to
put spaces around the em dash (`Drivel — 50 minutes ago`, not
`Drivel—50 minutes ago`, which at Monaspace's tracking reads as one word). It
is otherwise structurally identical to upstream. Overriding the template is the
sanctioned route; do not patch Evennia in place.

**The forum's theme is a component; its palette lives in the light slot only,
dark slot EMPTY** — see the Discourse Integration section above. Both facts
cost an outage's worth of confusion to learn (and the "both slots" advice this
paragraph used to give broke skin switching for a fortnight).

**The homepage was restructured and the brand mark landed** (#1440, #1442,
#1446, #1448). Both are documented in *Layout & Measure* and *Brand Mark*
above rather than here, because they are current behaviour rather than
history. Two lessons from doing it, though:

**`{# … #}` is single-line only in Django.** A three-line one rendered as body
copy on the live homepage. Multi-line comments need `{% comment %}` /
`{% endcomment %}`. Swept the whole template tree afterwards; that was the only
instance.

> **⚠ 2026-09-11: it recurred, in a template that did not exist yet when the
> sweep ran.** `38df091a` (#1909) and `4b7f7b54` (#1911) each added a
> multi-line `{# … #}` block to the freshly forked
> `web/templates/website/base.html` on 2026-08-10, and they rendered as
> literal text on **every website page** until `8750fcdc` (#1912) stripped
> them the same morning. The lesson survives; the "only instance" tally does
> not — and the shape of the recurrence is the useful part: a *newly shadowed
> template* is the gap a completed sweep cannot cover. The surviving in-tree
> reminder is at `web/templates/website/homepage/main-content.html:25`; it is
> worth repeating in any template we newly fork.

**Evennia's `recently-connected-widget.html` is overridden**, not patched
upstream — for the spaced em dash and to render the list as a flat strip rather
than a card. `index.html` is overridden for the same reason: the widget layout
is where the two-measure problem lived.
