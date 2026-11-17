# Forum Integration Guide

> **Status:** ✅ **SHIPPED & LIVE** — companion guide to `DISCOURSE_INTEGRATION.md`. ~~Verified 2026-08-02~~ **re-checked 2026-09-11: 19 claim(s) false, annotated inline**.

## Optional Discourse Forum Setup for Gelatinous

This guide covers the optional integration between your Evennia game and a Discourse forum. **This is completely optional** - the game works perfectly fine without it.

---

## Overview

The Gelatinous project includes optional support for integrating with a Discourse forum, providing:

- **Single Sign-On (SSO)**: Users log in once, access both game and forum
- **Visual Consistency**: Embedded Django header in forum for seamless navigation
- **Session Synchronization**: following the menu's Forum link while logged in signs you into the forum (via `/sso/discourse/session-sync/`); logging out of the game logs you out of the forum (needs `DISCOURSE_API_KEY`); logging out of the forum logs you out of the game (via the forum's logout redirect)
- **Custom Styling**: Forum themed to match game aesthetic

**If you don't plan to run a forum**: You can safely ignore all Discourse-related files and configuration. The game will work normally.

---

## What's Already Built (Optional to Use)

### Django Side (Game)

The following files support forum integration but are **non-invasive**:

**Views** (`web/website/views/`):
- `discourse_sso.py` - SSO handler. Requires a logged-in game account. Needs both `DISCOURSE_SSO_SECRET` and `DISCOURSE_URL`, and only redirects back to an https address on the `DISCOURSE_URL` host
- `discourse_logout.py` - Forum logout handler
- `discourse_session_sync.py` - Session synchronization
- `logout_with_discourse.py` - Dual logout
- `header_only.py` - Header iframe endpoint (harmless even if unused). It picks its skin on the server from the `gel_skin` cookie (only known skins are accepted, otherwise the default), so it matches the forum's skin from the first paint

**URL Routes** (`web/website/urls.py`):
- `/header-only/` - Renders just the header for iframe embedding (only the forum address in `web/utils/security_middleware.py` may frame it)
- `/sso/discourse/` - SSO endpoint (login required; returns a 400 error if not configured)
- `/sso/discourse/logout/` - Logout endpoint
- `/sso/discourse/session-sync/` - Session sync endpoint
- *2026-09-11: two more routes in `web/website/urls.py` belong to this
  integration and are missing from this list: `/forum/` (a redirect to
  `DISCOURSE_URL`, falling back to `/`) and `auth/logout/`, which overrides the
  site-wide logout with `logout_with_discourse`.*

**Templates** (`web/templates/website/`):
- `header_only.html` - Minimal header template for embedding
- *2026-09-11: and `_menu_iframe.html`, the iframe variant of the site menu.
  `header_only.html` includes it and nothing else does, so it is part of this
  integration too.*

### Discourse Side (Forum)

If you set up a Discourse forum, the complete theme configuration —
color scheme, header-integration CSS, iframe-embedding JavaScript, and
caching/preconnect setup — lives in **`DISCOURSE_INTEGRATION.md`**
(Steps 3–7, plus its sections on the header height contract and on caching). (The previously-separate `DISCOURSE_COLOR_PALETTE.md` /
`DISCOURSE_DARK_THEME_CSS.md` / `DISCOURSE_THEME_CODE_FIXED.md` /
`CACHING_AND_PRECONNECT_SETUP.md` files were consolidated into it.)

---

## Do I Need This?

### ✅ Use Forum Integration If:
- You want a community discussion platform separate from in-game chat
- You want persistent, searchable discussions
- You want to provide game announcements, guides, or support forums
- You have the resources to maintain a separate Discourse instance

### ❌ Skip Forum Integration If:
- You only want in-game chat and bulletin boards (Evennia has these built-in)
- You don't want to manage a separate forum platform
- You're just getting started and want to keep things simple
- You prefer Discord or another existing community platform

---

## Setup Instructions (If You Want a Forum)

### Prerequisites

1. **Discourse Forum**: You need a running Discourse instance
   - Self-hosted (Docker): https://github.com/discourse/discourse
   - Managed hosting: https://www.discourse.org/pricing
   - Minimum recommended: 1GB RAM, 10GB storage

2. **Secret Settings**: Configure SSO credentials

### Step 1: Configure Django (Game Side)

1. **Add Discourse credentials to `server/conf/secret_settings.py`:**

```python
# Discourse SSO Configuration (Optional)
DISCOURSE_SSO_SECRET = "your-shared-secret-here"  # Must match Discourse setting
DISCOURSE_URL = "https://forum.yourgame.com"      # Your forum URL
```

   For logout sync, also set `DISCOURSE_API_KEY` (an admin API key from the forum). Without it, logging out of the game does not log you out of the forum. Optional: `DISCOURSE_INTERNAL_URL`, an internal address the game uses for its API calls to the forum (it falls back to `DISCOURSE_URL`), and `DISCOURSE_LOGOUT_REDIRECT`, where a logout started from the forum lands (default `/`).

2. **Restart your game server** (Docker or Evennia reload)

That's it for the Django side! The routes and views are already in place.

### Step 2: Configure Discourse (Forum Side)

#### A. Enable DiscourseConnect (SSO)

1. Go to **Discourse Admin** → **Settings** → **Login**
2. Enable: `enable discourse connect`
3. Set: `discourse connect url` = `https://yourgame.com/sso/discourse/`
4. Set: `discourse connect secret` = (same secret as in Django settings)
5. Set: `logout redirect` = `https://yourgame.com/sso/discourse/logout/`
   - The game only accepts this logout when the browser's Referer comes from the `DISCOURSE_URL` host. A missing or different Referer gets a 403 and the game session stays logged in, so the forum must not strip its referrer.

#### B. Create Theme Component

1. Go to **Admin** → **Customize** → **Themes**
2. Click **Install** → **Create New**
3. Name it: "Django Header Integration"
4. Type: **Theme Component**

#### C. Apply Color Palette

1. Go to **Admin** → **Customize** → **Colors**
2. Create new color scheme using the values in `DISCOURSE_INTEGRATION.md`, Step 3
3. Apply it to your main theme

#### D. Add CSS

1. Edit your theme component
2. Go to **Common** → **CSS**
3. Paste CSS from `DISCOURSE_INTEGRATION.md`, Step 6
4. **Save**

#### E. Add HTML

1. Edit your theme component
2. Go to **Common** → `</head>`
3. Paste:
```html
<link rel="preconnect" href="https://yourgame.com">
<link rel="dns-prefetch" href="https://yourgame.com">
<div id="gel-django-header-container"></div>
```
4. **Save**

#### F. Add JavaScript

1. Edit your theme component
2. Go to **Common** → **JavaScript**
3. Paste JavaScript from `DISCOURSE_INTEGRATION.md`, Step 7
4. **Save**

#### G. Activate Theme

1. Go to your main theme (not the component)
2. Click **Edit**
3. Under **Included Components**, add "Django Header Integration"
4. **Save**

### Step 3: Test Integration

1. **Test SSO Login**:
   - Go to your forum while logged into your game
   - Click "Login" on forum
   - Should auto-login without password

2. **Test Logout Sync**:
   - Logout from game
   - Should also logout from forum

3. **Test Header**:
   - Navigate to forum
   - Should see your game's header at top

---

## Removing Forum Integration

If you decide not to use forum integration:

### Option 1: Just Don't Configure It
- Don't set `DISCOURSE_SSO_SECRET` or `DISCOURSE_URL` in settings
- Then `/sso/discourse/` returns a 400 error, `/sso/discourse/logout/` returns 403 for a logged-in user, `/sso/discourse/session-sync/` and `/forum/` send you to the home page, and site logout works as a normal logout
- The site menu still shows a Forum link (`web/templates/website/_menu.html`): visitors get a fixed forum address, and logged-in users go through session-sync to the home page. Remove it if you have no forum
- The `/header-only/` endpoint is harmless

### Option 2: Remove Forum-Specific Files

If you want to clean up:

```bash
# Remove forum-specific views (optional)
rm web/website/views/discourse_*.py
rm web/website/views/logout_with_discourse.py
rm web/website/views/header_only.py

# Remove forum templates (optional)
rm web/templates/website/header_only.html
# 2026-09-11: also remove web/templates/website/_menu_iframe.html --
# header_only.html is its only referrer, so it is dead weight once this goes.

# Remove forum specs (optional)
rm specs/DISCOURSE_*.md
rm specs/FORUM_INTEGRATION_*.md

# Remove the forum theme component (optional)
rm -r web/discourse-theme/
```

Then remove the imports and URL patterns from `web/website/urls.py`:

```python
# Remove these imports:
# from web.website.views.discourse_sso import discourse_sso
# from web.website.views.discourse_logout import discourse_logout
# from web.website.views.logout_with_discourse import logout_with_discourse
# from web.website.views.discourse_session_sync import discourse_session_sync
# from web.website.views.header_only import header_only

# Remove these URL patterns:
# path("header-only/", header_only, name="header-only"),
# path("sso/discourse/", discourse_sso, name="discourse-sso"),
# path("sso/discourse/logout/", discourse_logout, name="discourse-logout"),
# path("sso/discourse/session-sync/", discourse_session_sync, name="discourse-session-sync"),

# 2026-09-11: this list is INCOMPLETE. Two more patterns in web/website/urls.py
# belong to the forum integration and are not named above:
#     path("auth/logout/", logout_with_discourse, name="logout"),
#     path("forum/", RedirectView.as_view(
#         url=getattr(settings, 'DISCOURSE_URL', '') or '/',
#         permanent=False,
#     ), name="forum-redirect"),
# The first is the site-wide logout route, so removing the import above while
# leaving the pattern raises NameError at import and the site will not start --
# it has to be removed too. Removing it IS safe: Evennia's website urlpatterns
# include django.contrib.auth.urls under "auth/", which already provides
# auth/logout/ named "logout", so the {% url 'logout' %} in _menu.html and
# _menu_iframe.html keeps resolving -- to a plain Django logout with no forum
# sync, which is what you want once the forum is gone. (Today the project
# pattern wins because it comes first in urlpatterns, so every logout on the
# live site does run through logout_with_discourse.)
```

Also edit `web/templates/website/_menu.html`: its Forum link uses `{% url 'discourse-session-sync' %}` for logged-in users and a fixed forum address for visitors. Remove both Forum entries, or every page that shows the menu fails with an error once the `discourse-session-sync` pattern is gone.

Other forum pieces outside these files:
- `scripts/brand/build_skins.py`: its `TARGETS` list writes into `web/website/views/header_only.py` and into the forum component under `web/discourse-theme/`. Remove those two entries, or the skin build fails.
- `web/utils/security_middleware.py`: remove `_HEADER_ONLY_CSP` and its `/header-only` branch in `ContentSecurityPolicyMiddleware`.
- `server/conf/settings.py`: remove the Discourse block (the empty `DISCOURSE_URL` and `DISCOURSE_SSO_SECRET` defaults).
- `web/templates/robots.txt`: remove the `/header-only/` and `/forum/` lines.

---

## Customization

### Using a Different Forum Platform

The header iframe approach (`/header-only/`) works with any forum that supports:
- Custom HTML/CSS/JavaScript
- Iframe embedding

The header page only allows framing by the forum address written into `web/utils/security_middleware.py` (`_HEADER_ONLY_CSP`). That address is not read from `DISCOURSE_URL`. A forum on a different host must be added there, or browsers will refuse to show the header.

You could adapt this for:
- **NodeBB**: Similar theme customization system
- **Flarum**: Supports custom headers via extensions
- **Vanilla Forums**: Has iframe embedding capabilities
- **phpBB**: Requires custom theme modifications

Just change the SSO implementation to match your platform's protocol.

### Using Discord Instead

If you prefer Discord:
- Use Discord's OAuth2 for authentication
- Embed Discord widget in your website
- No need for SSO complexity
- Simpler to maintain

---

## Troubleshooting

### SSO Not Working

**Check:**
1. `DISCOURSE_SSO_SECRET` is set in Django settings
2. Same secret is configured in Discourse
3. `discourse connect url` points to `https://yourgame.com/sso/discourse/`
4. User is logged into Django before trying to access forum

**Debug:**
```bash
# Check if endpoint is accessible
curl https://yourgame.com/sso/discourse/

# Logged out (plain curl): a redirect to the login page. That is expected;
# the endpoint needs a logged-in game session.
# Logged in, with no sso/sig parameters: "Missing SSO parameters".
# Logged in, with no DISCOURSE_SSO_SECRET set: "SSO is not configured".
```

### Header Not Showing

**Check:**
1. Theme component is activated
2. JavaScript has no errors (check browser console)
3. `/header-only/` endpoint is accessible: `curl https://yourgame.com/header-only/`

### Colors Wrong

**Check:**
1. Color Palette is applied to theme
2. CSS is saved in theme component
3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

---

## Performance Notes

The forum integration includes several optimizations:

- **No caching**: the header endpoint is sent with `no-store` and is never cached, because it shows who is logged in
- **Preconnect**: Browser establishes connection early
- **CSS Containment**: Isolates iframe rendering
- **Lazy Loading**: Iframe loads after main content

Expected performance:
- Initial load: 50-200ms iframe load time
- Every forum page view asks the game's web server for the header, since it is never cached

---

## Maintenance

### Keeping Theme Updated

If you update your Django header styling:
1. Changes to the header template and the site's stylesheet show on the forum at once, because the header is served by the game and never cached.
2. Skin colour changes are different: rerun `scripts/brand/build_skins.py`, which rewrites `SKIN_INK` in `web/website/views/header_only.py` and the forum component's `skins.gjs`, then re-upload `web/discourse-theme/` as its `README.md` describes.
3. Palette and type changes in `custom.css` must also be copied into `web/discourse-theme/` by hand (its `README.md`, "Keeping it in step").

### Discourse Updates

Discourse updates shouldn't affect the integration, but test after major upgrades:
- SSO endpoint (login flow)
- Theme component (header display)
- Color scheme (visual consistency)

---

## Resources

**Discourse Documentation**:
- DiscourseConnect (SSO): https://meta.discourse.org/t/13045
- Theme Components: https://meta.discourse.org/t/93648
- Color Schemes: https://meta.discourse.org/t/108801

**Evennia Documentation**:
- Web Views: https://www.evennia.com/docs/latest/Components/Web-Views.html
- Web Configuration: https://www.evennia.com/docs/latest/Setup/Web-Config.html

---

## Summary

Forum integration is:
- ✅ **Optional** - Game works fine without it
- ✅ **Non-invasive** - Doesn't affect core functionality
- ✅ **Removable** - Can be stripped out if not needed
- ✅ **Customizable** - Adapt to other platforms

If you're not using it, the code is harmless. If you are, it provides a polished integration between your game and community forum.
