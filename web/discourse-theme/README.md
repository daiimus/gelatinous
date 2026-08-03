# Domino's Gambit — forum theme

Brings `forum.gel.monster` into the same visual world as the site: ink
ground, bone text, amber accent, jade for genuine state, and the
Monaspace superfamily (Neon for prose and interface, Xenon for
headings).

## Installing

This is a **theme component**, not a standalone theme — that matters.
The forum's existing theme owns the header integration (the JavaScript
that iframes `/header-only/` from gel.monster, documented in
`specs/DISCOURSE_INTEGRATION.md`). A standalone theme *replaces* that
one and the forum loses its header; a component layers on top of it.

1. Zip the contents of this directory (not the directory itself):
   `cd web/discourse-theme && zip -r ../../dominos-gambit-theme.zip .`
2. In Discourse: **Admin → Customize → Themes → Install → From your
   device**, and upload the zip.
3. It appears under **Components**. Open your existing default theme and
   add it under *Included components*.
4. Select the **Domino's Gambit** colour scheme on the parent theme.

### Updating it later

**A zip install always creates a NEW component — it does not update the
existing one in place.** Uploading a newer zip leaves you with two
components of the same name, one attached to the parent theme and one
`Unused`, distinguishable only by that column.

To update:

1. Upload the new zip. Note which entry says `Unused` — that is the new
   one.
2. Rename the *old* one (the one marked `Used on Foundation`) so the two
   can be told apart.
3. On the parent theme, **add the new component first, then remove the
   old one.** Doing it in that order matters: removing the last component
   silently strips the forum's typography with no warning, and the
   palette keeps looking correct because the parent theme points at the
   colour scheme directly.
4. Verify the forum, then delete the renamed old component.

Deleting a component never deletes a colour scheme — the palettes are
standalone records (`theme_id` null) and survive independently.

Installing **from a git repository** instead would give proper in-place
updates via *Check for updates*, which is Discourse's real upgrade path.
The obstacle is that its importer expects `about.json` at the repository
root, and this lives in a subdirectory of the game monorepo, so it would
need its own repository or a dedicated branch. Worth doing if component
changes become frequent.

### If the header has already disappeared

Installing a standalone theme does not delete the old one. Go to
**Admin → Customize → Themes**, select the previous theme, and **Set as
default** — the header comes back. Then add this component to it.

## How it is organised

- `about.json` — theme metadata, font assets, and the colour scheme.
  Discourse derives its own tints and shades from these values, which is
  why the palette lives here rather than in CSS.
- `common/common.scss` — typography and the details a colour scheme
  cannot reach: the type roles, texture healing, the slashed zero,
  reading measure on posts, rules instead of boxes.
- `assets/` — the Monaspace variable fonts, bundled deliberately. A
  cross-origin webfont served from `gel.monster` would need CORS
  headers on `/static/`; bundling avoids that entirely. OFL licence
  included.

## Keeping it in step

The source of truth for the palette and type roles is
`web/static/website/css/custom.css`. When those tokens change, mirror
them here — the values are duplicated because Discourse cannot read the
site's stylesheet, and that duplication is the price of one visual
identity across two applications.
