# Discourse Forum Integration

The game's Django site is the sign-in provider for a Discourse forum
(forum.gel.monster). A player signed in to the game is signed in to the forum
through DiscourseConnect (SSO). The forum hides its own header and shows the
game site's header in an iframe, served from `/header-only/`. A theme
component and a colour scheme make the forum look like the site, and the
site's skins carry over to it. Logging out of one logs out of the other.

The forum is optional. See `FORUM_INTEGRATION_GUIDE.md` for whether a game
needs one at all. Without a forum the Django code still works: the SSO
endpoints return errors when SSO is not configured, and nothing else breaks.

---

## Step 1: Configure Django (Game Side)

### Settings

Set these in `server/conf/secret_settings.py`, then reload the server
(`evennia reload`, or `docker-compose restart` under Docker):

```python
# Discourse SSO Configuration (Optional)
DISCOURSE_SSO_SECRET = "your-shared-secret-here"  # Must match Discourse
DISCOURSE_URL = "https://forum.yourgame.com"      # Your forum URL
DISCOURSE_API_KEY = "your-discourse-api-key"      # For logout sync (optional)
```

| setting | meaning |
|---|---|
| `DISCOURSE_SSO_SECRET` | shared secret; the same string goes in Discourse's `discourse connect secret` |
| `DISCOURSE_URL` | forum URL |
| `DISCOURSE_API_KEY` | optional; lets game logout end the forum session through the forum API |
| `DISCOURSE_INTERNAL_URL` | optional; forum address for the server-to-server logout API calls; falls back to `DISCOURSE_URL` |
| `DISCOURSE_LOGOUT_REDIRECT` | optional, default `/`; where the game sends a user after the forum logs them out |

The secret is a random string of 32 or more characters, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Setting up a forum also needs a running Discourse instance (self-hosted or
managed) with admin access.

### Endpoints

| route | what it does |
|---|---|
| `/sso/discourse/` | SSO authentication. Requires a signed-in game session: a visitor who is not signed in is redirected to the game's login page. Signed in, with no `sso`/`sig` parameters, it answers "Missing SSO parameters". With no shared secret set, it answers "SSO is not configured". |
| `/sso/discourse/logout/` | where the forum sends a user after forum logout (see "Forum logout" below) |
| `/sso/discourse/session-sync/` | sends a signed-in user to the forum's own sign-in, so they arrive signed in |
| `/auth/logout/` | game logout (POST, `logout_with_discourse`); with `DISCOURSE_API_KEY` set it also ends the forum session through the forum API |
| `/forum/` | redirects to `DISCOURSE_URL`, or to `/` if that is unset |
| `/header-only/` | the header page the forum iframes |

The game sends the forum only email, external id, username and name. It
sends no avatar and no bio.

### Forum logout

The game accepts the forum's logout redirect (`/sso/discourse/logout/`) from a
signed-in user only when the browser sends a Referer whose host is the
`DISCOURSE_URL` host. A missing or different Referer is refused with 403
("Invalid logout request"). If `DISCOURSE_URL` is not set, every signed-in
logout through this route is refused with 403. A visitor who is not signed in
is simply redirected.

### Origins written by hand

Not everything follows `DISCOURSE_URL`. The forum origin is also written by
hand into:

- the header page's CSP `frame-ancestors` (`_HEADER_ONLY_CSP` in
  `web/utils/security_middleware.py`);
- the iframe menu's Forum link (`web/templates/website/_menu_iframe.html`);
- the skin messages in `web/static/website/js/skins.js`.

The game-site origin is written by hand as `SITE_ORIGIN` in the forum
component's `skins.gjs`, and in the forum-side header component's head markup
and listener (below). Change all of these if the forum or the site moves.

---

## Step 2: Configure Discourse SSO

### DiscourseConnect

In **Discourse Admin → Settings → Login**:

- `enable discourse connect` = `true`
- `discourse connect url` = `https://yourgame.com/sso/discourse/`
- `discourse connect secret` = the same secret as `DISCOURSE_SSO_SECRET`
- `logout redirect` = `https://yourgame.com/sso/discourse/logout/`
- `enable local logins` = `false` (recommended: SSO only)

### Overrides and account identity

On the installed forum (Discourse 2026.8.0, checked 2026-10-10, #3743) the
setting names `sso overrides avatar`, `sso overrides bio`,
`sso overrides email` and `sso overrides name` do not exist; stored rows
under those names do nothing. Only `discourse_connect_overrides_avatar` is in
force. The email, name and username overrides are **off** (`auth_overrides_*`
at their defaults). Since the game sends no avatar and no bio, an avatar or
bio override has nothing to apply.

Overrides off is safe because a game account's email is set once, at
registration, is unique in any letter case, and can never be changed. A
forum account's address is therefore held by exactly one live game account.
That uniqueness, not email verification, is what keeps forum sign-on safe
(verification is off by owner decision). Two rules follow:

- **If the game ever gains an email-change path, turn `auth_overrides_email`
  on with it**, or a freed address can be registered by someone else and
  matched to the old forum account.
- **Deleting a game account must also retire its forum account**, for the
  same reason. 📋 UNBUILT (no issue): no game code calls the forum when an
  account is deleted.

Role sync is 📋 UNBUILT, #3744.

The forum's developer-address list (`DISCOURSE_DEVELOPER_EMAILS`, compose
file in the infra repo) names the two root game accounts. It promotes a
matching user to admin on login, so it must never name an address no live
game account holds.

---

## Step 3: Apply Color Palette

### The palette

Create it in **Admin → Customize → Colors → + New Color Scheme**. Name it
exactly "Domino's Gambit": the skins script finds palettes by name. The live
scheme is Discourse colour scheme id 21.

The values match the site palette in `STYLING_SPEC.md` / `custom.css` (the
Atlas register: ink ground, bone text, amber accent):

```
Primary (text):           #d8d3c4   (bone)
Primary-medium:           #8f8d82   (--terminal-text-muted)
Primary-low-mid:          #6b6f78
Secondary (background):   #0b0e14   (ink)
Tertiary (accent):        #e0a86f   (amber)
Quaternary:               #6fd6e0   (cyan — data)
Header Background:        #0b0e14
Header Primary:           #d8d3c4
Highlight:                #e0a86f
Selected:                 #11161f
Hover:                    #182030
Danger (errors):          #e85555
Success (confirmations):  #5fd38d   (jade — STATE only)
Love (likes):             #e0a86f
```

The `tertiary-med-or-tertiary` override is set to `#e0a86f`. If a scheme being
replaced had that override, set it too, or the old accent bleeds through in a
handful of places.

`primary-medium` is `#8f8d82` on the live scheme, the site's
`--terminal-text-muted` (`custom.css`, `STYLING_SPEC.md` § Color Palette).
The tracked component's `web/discourse-theme/about.json` declares
`#a9a49a` instead, so the repository does not record the value that is
serving. This is harmless in itself, because colour schemes do not travel with
components. `#a9a49a` and `#6b6f78` appear nowhere in `custom.css` or
`STYLING_SPEC.md`.

### Applying it: the light slot only

Select the scheme on the parent theme (**Admin → Customize → Themes**, the
default theme, **Colors**, **Save**). The live parent theme is Foundation
(theme -1): `color_scheme_id = 21` ("Domino's Gambit") and an **empty**
`dark_color_scheme_id`. **Empty is the only correct value** for the dark slot.

A theme has two slots: `color_scheme_id` (light) and `dark_color_scheme_id`
(dark). Discourse serves the dark one to anyone whose OS is in dark mode. If
the dark slot points at an old palette while only the light one was changed,
it looks exactly as if the change never applied: the old palette keeps
showing, accent and all.

Why the dark slot stays empty: every palette shipped is dark-styled, so the
light slot alone serves everyone from one `media=all` stylesheet, which is
what `web/discourse-theme/javascripts/discourse/api-initializers/skins.gjs` is
built against. With a dark slot set, a browser carrying a `gel_skin` cookie
gets two palette stylesheets: the skin under
`media=(prefers-color-scheme: light)` and the parent theme's default under
`media=(prefers-color-scheme: dark)`. On a dark-mode OS the default wins, and
`skins.gjs`, which reads only the light link, treats the skin as already
applied. Every browser with a skin cookie (the signed-in one) is then stuck
on the default while cookie-less windows work (#1898). Filling the dark slot
with this palette was once this guide's advice; #1898 (2026-08-10) replaced it
with the empty dark slot. `STYLING_SPEC.md` § Discourse Integration carries
the full account.

**Colour schemes do not travel with theme components.** Installing a
component that declares `color_schemes` in `about.json` does not create the
scheme. Build it by hand as above, or through the API, and select it on the
parent theme.

---

## Step 4: Create Theme Components

Two components sit on the parent theme:

- **Domino's Gambit**, tracked at `web/discourse-theme/`: typography, palette
  declaration and skin switching (`skins.gjs`). Install and update it as its
  `README.md` says.
- **The header component**, which hides the Discourse header and iframes
  `/header-only/`. On the live forum it is the "Gelatinous" component
  (Discourse theme id 1). Its listener
  (`discourse/api-initializers/theme-initializer.gjs`) lives only on the forum
  and is not tracked in this repository.

To create a header component on a new forum: **Admin → Customize → Themes →
Install → Create New**, name "Django Header Integration", type **Theme
Component**, **Create**. Then edit the main theme (not the component), add it
under **Included Components**, and **Save**.

## Step 5: Add HTML (head markup)

The component's `head_tag` ships the iframe itself, inline. The live field:

```html
<div id="gel-django-header-container">
  <iframe
    id="gel-django-header-iframe"
    src="https://gel.monster/header-only/"
    frameborder="0"
    scrolling="no"
    style="width: 100%; height: 80px; border: none; display: block; background: #0b0e14;">
  </iframe>
</div>
<link rel="preconnect" href="https://gel.monster">
<link rel="dns-prefetch" href="https://gel.monster">
```

The site domain lives in this markup (the iframe `src`), not in the
component's JavaScript. The inline `background: #0b0e14` is a literal; the
container's ground is `var(--secondary)` (#1528). The literal shows only for
the instant before the iframe document paints its own skin ground, so it is
cosmetic, not the seam bug #1528 fixed.

## Step 6: Add CSS

In the component, **Common → CSS**:

```css
/* ===== DJANGO HEADER IFRAME INTEGRATION ===== */

/* Hide standard Discourse header - prevent flash */
.d-header {
  display: none !important;
}

/* Pre-allocate space to prevent layout shift */
body {
  padding-top: 80px;
}

#main-outlet {
  margin-top: 80px !important;
  padding-top: 20px;
}

/* Container for Django header iframe */
#gel-django-header-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 80px; /* Fixed height prevents reflow */
  z-index: 1031;
  background-color: #0b0e14; /* ink — match --terminal-bg-dark */
  /* Optimize rendering */
  will-change: contents;
  contain: layout style;
}

/* Iframe styling - seamless integration */
#gel-django-header-iframe {
  width: 100%;
  height: 80px;
  border: none;
  display: block;
  margin: 0;
  padding: 0;
  background: transparent;
  overflow: hidden;
  /* Performance optimizations */
  pointer-events: auto;
}

.sidebar-wrapper {
  top: 80px !important;
}

/* Hide Discourse footer */
.about-footer {
  display: none !important;
}

/* Simplified loading state - no jitter */
#gel-django-header-container.loading {
  background-color: #0b0e14; /* ink — match --terminal-bg-dark */
}

/* Mobile responsive - keep same height as desktop */
/* Django header handles its own mobile layout */
@media (max-width: 768px) {
  body {
    padding-top: 80px;
  }

  #main-outlet {
    margin-top: 80px !important;
  }

  #gel-django-header-container {
    height: 80px;
  }

  #gel-django-header-iframe {
    height: 80px;
  }

  .sidebar-wrapper {
    top: 80px !important;
  }
}
```

The live component's mobile media query uses **60px** for all five values
(`body` padding, `#main-outlet` margin, container, iframe, `.sidebar-wrapper`),
not the 80px above. Which is right is not decided (see "Not decided"); do not
change either side from this document.

## Step 7: Add JavaScript (the forum-side listener)

`theme-initializer.gjs` on the header component:

- creates no iframe (the iframe is in the head markup);
- on a `gel-header-height` message from the site origin, sets **both**
  `iframe.style.height` and `container.style.height`, and nothing else. It
  never touches `body` padding, `#main-outlet` or `.sidebar-wrapper`, so an
  open dropdown overlays the page rather than pushing it down;
- carries none of the skin protocol that shares this channel (that is
  `skins.gjs`);
- has a `hashchange` listener that redirects `#logout` to
  `https://gel.monster/logout`. That URL 404s (the real route is
  `/auth/logout/`), and the mechanism is vestigial: nothing sets `#logout`,
  and the header's logout is a POST form in `_menu_iframe.html`.

---

## The header height contract

The header is an iframe, and an iframe **clips its own content**. Anything the
header draws below its own height (an account dropdown, a flash message) is
invisible unless the parent is told to grow. The contract spans both sides,
and every piece of it is load-bearing.

**Site side** (`web/templates/website/header_only.html`) posts its height to
the parent:

```js
window.parent.postMessage({ type: 'gel-header-height', height: measuredHeight() },
                          TARGET_ORIGIN);
```

The same message carries `skin` (the header's `data-skin`, default `atlas`),
and the header sends it again whenever its skin changes. The forum
component's `skins.gjs` reads it, and also sends `gel-skin` and
`gel-skin-query` messages into the iframe, which the header's `skins.js`
answers. The header page picks its first-paint ground colour on the server
from the `gel_skin` cookie (`SKIN_INK` in `web/website/views/header_only.py`,
which must match each skin's `--terminal-bg-dark` in `custom.css`).

**Forum side** (`theme-initializer.gjs`) listens, checks the origin, and sets
both the iframe and its container:

```js
if (event.origin !== 'https://gel.monster') return;
iframe.style.height = newHeight;
container.style.height = newHeight;
```

### Four things that must all be true

1. **Measure the open menu, not the document.** `document.body.scrollHeight`
   is not enough: a Bootstrap dropdown is absolutely positioned and never
   touches it. Take the lowest edge of any `.dropdown-menu.show` via
   `getBoundingClientRect()`. The element has layout even while the iframe
   visually clips it, which is what makes it measurable at all.
2. **Grow the body too.** Asking the parent to resize does not stop the
   *document* clipping the menu at its own 80px box, and until the body is
   tall enough the reported height stays wrong. On open, the body takes a
   `min-height` containing the menu; cleared on close.
3. **Do not disable dropdowns in CSS.** `.dropdown-menu { display: none !important }`
   denies the menu the layout the measurement depends on, and the protocol
   then silently measures nothing. **If dropdowns ever need removing, remove
   the markup, not the layout.**
4. **Every link needs `target="_top"`.** Without it, navigation loads the
   destination *inside* the 80px header frame.

### The header is never cached

`/header-only/` is auth state: it names the logged-in account and renders a
different menu for anonymous visitors. It is sent
`no_store, no_cache, must_revalidate, private` (`header_only` in
`web/website/views/header_only.py`). `private` alone stops shared caches, not
the browser's; a cached header keeps saying "Logged in as X" after logout and
makes template changes appear not to ship. Because it is never cached, a
change to the header's styling shows on the forum on the next page load, with
no theme update.

---

## Forum branding is not inherited

Discourse serves its own icons and picks up nothing from the game site. Four
settings decide how the forum appears in a tab, a bookmark, a phone home
screen and a shared link:

| setting | used for |
|---------|----------|
| `favicon` | browser tab |
| `logo_small` | collapsed header |
| `large_icon` | PWA / manifest |
| `apple_touch_icon` | iOS home screen |

Left empty, the forum shows Discourse's stock icon while the game site shows
the brand mark. They are uploads, not URLs: set them in
**Admin → Settings → Branding**, or create an `Upload` and assign it.

Uploading via `rails runner` fails with `EPERM` if the file was placed with
`docker cp`: `image_optim` rewrites the image **in place**, and the copied
file is not owned by the `discourse` user. `chown discourse:discourse` it
first.

---

## Bootstrap versions

Only the Bootstrap CSS is synced: both `base.html` and `header_only.html` load
Bootstrap CSS 4.6.0 (jsDelivr). The JavaScript is not version-matched:

| page | Bootstrap JS | jQuery |
|---|---|---|
| `base.html` | 4.0.0 (maxcdn) | 3.2.1 slim |
| `header_only.html` | 4.6.2 (jsDelivr) | 3.6.0 |

Both CDN sets are allowlisted deliberately (`_SCRIPT_CDNS` and `_STYLE_CDNS`
in `web/utils/security_middleware.py`). Keep the header's Bootstrap CSS the
same version as the main site's.

---

## Performance

- **No caching**: the header endpoint is sent with `no-store` (see above).
- **Preconnect**: the head markup's `preconnect` / `dns-prefetch` let the
  browser open the connection early.
- **CSS containment**: `contain: layout style` isolates iframe rendering.
- **Fixed height**: 80px is pre-allocated, preventing layout reflow.

Expected: initial load 50–200ms iframe load time; cached load under 50ms; no
impact on game server performance.

---

## Discourse updates

**If the admin panel says an upgrade is required, that means REBUILD the
container, not press the upgrade button.**

Discourse updates in two tiers. The admin UI upgrade (`docker_manager`)
handles the **app tier**: `bundle install`, `pnpm install`, migrations and
`assets:precompile`. It cannot touch the **image tier** (Ruby, Node, Postgres,
system libraries), which is baked into `discourse/base`.

`docker_manager` compares the running Ruby and base image against what core
expects and flags `upgrade_required` when either is behind. **It only
warns.** It still lets you press upgrade, and the git pull happens *before*
`bundle install` can fail, so a version-skewed site ends up on code it cannot
run, with no rollback. Symptoms: every page 500s with errors like
`undefined method 'generate_import_map'` or a missing JS package.

Recovery: the pulled source is only in the container's writable layer, so
`git reset --hard <previous-commit>` inside the container plus
`docker restart` restores service. `sv restart unicorn` is **not**
sufficient: it restarts the runit wrapper but can leave the old unicorn
master alive serving stale code from memory.

After a major Discourse upgrade, test SSO login, header display, theme
component behaviour and the colour scheme, **in dark mode too** (see "Applying
it: the light slot only").

---

## Testing

**SSO login.** Signed in to the game, open the forum and click "Login". The
browser goes to the Django SSO endpoint, signs in with no password prompt,
and returns to the forum signed in.

**Header display.** On the forum, the Django header shows at the top, the
Discourse header is hidden, and the header matches the main site exactly.

**Logout sync.** Signed in to both, click "Log Out" in the header on the
forum. Both the game and the forum are logged out; a forum refresh shows
logged out.

**Mobile.** On a phone or narrow browser, the header shows the hamburger
menu, and the menu collapses properly. The mobile height is not decided (see
"Not decided"); settle it on a real device.

---

## Troubleshooting

**Can't log in to the forum.** Check `DISCOURSE_SSO_SECRET` is set in Django,
the same secret is in Discourse, `discourse connect url` points at the Django
endpoint, and the user is signed in to the game first. Not signed in,
`curl -i https://yourgame.com/sso/discourse/` answers with a redirect to the
game's login page, which proves the route exists; a plain `curl` never
reaches the SSO checks (see "Endpoints" for the signed-in answers).

**No header on the forum.** Check the theme component is active, the browser
console (F12) shows no JavaScript errors, `/header-only/` is reachable
(`curl https://yourgame.com/header-only/` returns HTML with a navbar), and the
iframe `src` in the component's head markup has the right domain.

**Forum logout shows "Invalid logout request" (403).** See "Forum logout":
the Referer must name the `DISCOURSE_URL` host, and `DISCOURSE_URL` must be
set.

**Forum colours don't match the game.** Check the scheme is selected on the
parent theme (and the dark slot is empty), the component CSS is saved, and
hard-refresh the browser (Cmd+Shift+R or Ctrl+Shift+R).

**Both Discourse and Django headers show.** Check the CSS has
`.d-header { display: none !important; }`, the component is included in the
main theme, and the head markup holds exactly one `#gel-django-header-iframe`.

**Header looks wrong on mobile.** Check the mobile media query is present and
there are no font-size overrides in `header_only.html`. The forum listener
resizes only the container and the iframe; `body { padding-top }` and
`#main-outlet { margin-top }` keep whatever the media query gave them, so if
the mobile header does not rest at exactly the media query's height, the two
disagree and content sits under the header. Bootstrap JS is not
version-matched between the pages (see "Bootstrap versions").

---

## Unbuilt

- 📋 UNBUILT (no issue): retiring the forum account when a game account is
  deleted. No game code calls the forum when an account is deleted (see
  "Overrides and account identity").
- 📋 UNBUILT, #3744: role sync.

---

## Not decided

- **Mobile header height.** The CSS in this document uses 80px in the mobile
  media query; the live component uses 60px (measured 2026-09-11). Which is
  right needs a real device. Do not "fix" either side from this document.
- **`primary-medium`.** Should it be `#8f8d82` (the live value, the site's
  `--terminal-text-muted`) both in this document's palette table and in
  `web/discourse-theme/about.json`, instead of `#a9a49a`?

---

## Related documents

- `FORUM_INTEGRATION_GUIDE.md`: whether a game needs a forum.
- `STYLING_SPEC.md` § Color Palette and § Discourse Integration: the site
  palette and the full colour-slot account.
- `web/discourse-theme/README.md`: installing and updating the Domino's
  Gambit component.
