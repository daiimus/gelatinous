# Domino's Gambit — forum theme

Brings `forum.gel.monster` into the same visual world as the site: ink
ground, bone text, amber accent, jade for genuine state, and the
Monaspace superfamily (Neon for prose and interface, Xenon for
headings).

## Installing

Discourse installs themes as a zip or from a git repository. This
directory is the theme root.

1. Zip the contents of this directory (not the directory itself):
   `cd web/discourse-theme && zip -r ../../dominos-gambit-theme.zip .`
2. In Discourse: **Admin → Customize → Themes → Install → From your
   device**, and upload the zip.
3. Set it as the default theme, and select the **Domino's Gambit**
   colour scheme (it arrives with the theme).

Re-uploading a newer zip updates the theme in place.

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
