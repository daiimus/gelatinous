# Forum Integration Guide

## Optional Discourse Forum Setup for Gelatinous

This guide covers the optional integration between the Evennia game and a Discourse forum. It is the companion to `DISCOURSE_INTEGRATION.md`. **The integration is completely optional**: the game works without it.

---

## Overview

The integration provides:

- **Single Sign-On (SSO)**: users log in once and can use both the game and the forum.
- **Visual Consistency**: the forum embeds the Django header, so navigation looks the same on both.
- **Session Synchronization**:
  - Following the menu's Forum link while logged in signs you into the forum (via `/sso/discourse/session-sync/`).
  - Logging out of the game logs you out of the forum (needs `DISCOURSE_API_KEY`).
  - Logging out of the forum logs you out of the game (via the forum's logout redirect).
- **Custom Styling**: the forum is themed to match the game.

**If you don't plan to run a forum**, you can ignore all Discourse-related files and configuration. The game works normally.

---

## The Pieces

### Django Side (Game)

These files support the integration and are **non-invasive**.

**Views** (`web/website/views/`):
- `discourse_sso.py`: the SSO handler. It requires a logged-in game account. It needs both `DISCOURSE_SSO_SECRET` and `DISCOURSE_URL`, and it only redirects back to an https address on the `DISCOURSE_URL` host.
- `discourse_logout.py`: the forum logout handler.
- `discourse_session_sync.py`: session synchronization.
- `logout_with_discourse.py`: dual logout.
- `header_only.py`: the header iframe endpoint (harmless even if unused). It picks its skin on the server from the `gel_skin` cookie. Only known skins are accepted; anything else gets the default. So the header matches the forum's skin from the first paint.

**URL Routes** (`web/website/urls.py`):
- `/header-only/`: renders just the header, for iframe embedding. Only the forum address in `web/utils/security_middleware.py` may frame it.
- `/sso/discourse/`: the SSO endpoint. Login required; returns a 400 error if not configured.
- `/sso/discourse/logout/`: the logout endpoint.
- `/sso/discourse/session-sync/`: the session sync endpoint.
- `/forum/`: a redirect to `DISCOURSE_URL`, falling back to `/`.
- `auth/logout/`: overrides the site-wide logout with `logout_with_discourse`. The project pattern comes first in `urlpatterns`, so every logout on the site runs through `logout_with_discourse`.

**Templates** (`web/templates/website/`):
- `header_only.html`: the minimal header template for embedding.
- `_menu_iframe.html`: the iframe variant of the site menu. `header_only.html` includes it and nothing else does, so it belongs to this integration.

### Discourse Side (Forum)

The complete forum theme configuration (color scheme, header-integration CSS, iframe-embedding JavaScript, and caching/preconnect setup) lives in **`DISCOURSE_INTEGRATION.md`**: Steps 3–7, plus its sections on the header height contract and on caching.

---

## Do I Need This?

### Use Forum Integration If:
- You want a community discussion platform separate from in-game chat
- You want persistent, searchable discussions
- You want to provide game announcements, guides, or support forums
- You have the resources to maintain a separate Discourse instance

### Skip Forum Integration If:
- You only want in-game chat and bulletin boards (Evennia has these built-in)
- You don't want to manage a separate forum platform
- You're just getting started and want to keep things simple
- You prefer Discord or another existing community platform

---

## Setup Instructions (If You Want a Forum)

### Prerequisites

1. **Discourse Forum**: you need a running Discourse instance.
   - Self-hosted (Docker): https://github.com/discourse/discourse
   - Managed hosting: https://www.discourse.org/pricing
   - Minimum recommended: 1GB RAM, 10GB storage
2. **Secret Settings**: configure SSO credentials.

### Step 1: Configure Django (Game Side)

1. **Add Discourse credentials to `server/conf/secret_settings.py`:**

```python
# Discourse SSO Configuration (Optional)
DISCOURSE_SSO_SECRET = "your-shared-secret-here"  # Must match Discourse setting
DISCOURSE_URL = "https://forum.yourgame.com"      # Your forum URL
```

   For logout sync, also set `DISCOURSE_API_KEY` (an admin API key from the forum). Without it, logging out of the game does not log you out of the forum.

   Optional settings:
   - `DISCOURSE_INTERNAL_URL`: an internal address the game uses for its API calls to the forum. It falls back to `DISCOURSE_URL`.
   - `DISCOURSE_LOGOUT_REDIRECT`: where a logout started from the forum lands. Default `/`.

2. **Restart your game server** (Docker or Evennia reload).

The routes and views are already in place; nothing else is needed on the Django side.

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
2. Create a new color scheme using the values in `DISCOURSE_INTEGRATION.md`, Step 3
3. Apply it to your main theme

#### D. Add CSS

1. Edit your theme component
2. Go to **Common** → **CSS**
3. Paste the CSS from `DISCOURSE_INTEGRATION.md`, Step 6
4. **Save**

#### E. Add HTML

1. Edit your theme component
2. Go to **Common** → `</head>`
3. Paste the head markup from `DISCOURSE_INTEGRATION.md`, Step 5
4. **Save**

#### F. Add JavaScript

1. Edit your theme component
2. Go to **Common** → **JavaScript**
3. The forum-side listener is described in `DISCOURSE_INTEGRATION.md`, Step 7; it lives only on the forum and is not tracked in the repo
4. **Save**

#### G. Activate Theme

1. Go to your main theme (not the component)
2. Click **Edit**
3. Under **Included Components**, add "Django Header Integration"
4. **Save**

### Step 3: Test Integration

1. **Test SSO Login**:
   - Go to your forum while logged into your game
   - Click "Login" on the forum
   - It should log you in without a password
2. **Test Logout Sync**:
   - Log out from the game
   - You should also be logged out from the forum
3. **Test Header**:
   - Navigate to the forum
   - You should see your game's header at the top

---

## Removing Forum Integration

### Option 1: Just Don't Configure It

Don't set `DISCOURSE_SSO_SECRET` or `DISCOURSE_URL` in settings. Then:
- `/sso/discourse/` returns a 400 error.
- `/sso/discourse/logout/` returns 403 for a logged-in user.
- `/sso/discourse/session-sync/` and `/forum/` send you to the home page.
- Site logout works as a normal logout.
- The site menu still shows a Forum link (`web/templates/website/_menu.html`): visitors get a fixed forum address, and logged-in users go through session-sync to the home page. Remove it if you have no forum.
- The `/header-only/` endpoint is harmless.

### Option 2: Remove Forum-Specific Files

If you want to clean up:

**Files to delete (optional):**
- Views: `web/website/views/discourse_*.py`, `web/website/views/logout_with_discourse.py`, `web/website/views/header_only.py`.
- Templates: `web/templates/website/header_only.html`, and `web/templates/website/_menu_iframe.html` (`header_only.html` is its only referrer).
- Specs: `specs/DISCOURSE_*.md`, `specs/FORUM_INTEGRATION_*.md`.
- The forum theme component: `web/discourse-theme/`.

**`web/website/urls.py`:** remove the imports of `discourse_sso`, `discourse_logout`, `logout_with_discourse`, `discourse_session_sync` and `header_only`, and these URL patterns:
- `header-only/` (name `header-only`)
- `sso/discourse/` (name `discourse-sso`)
- `sso/discourse/logout/` (name `discourse-logout`)
- `sso/discourse/session-sync/` (name `discourse-session-sync`)
- `auth/logout/` (name `logout`, view `logout_with_discourse`)
- `forum/` (name `forum-redirect`, a `RedirectView` with `permanent=False`, a temporary redirect to `DISCOURSE_URL`, falling back to `/`)

The `auth/logout/` pattern must go with the `logout_with_discourse` import: removing the import while leaving the pattern raises `NameError` at import, and the site will not start. Removing it is safe. Evennia's website urlpatterns include `django.contrib.auth.urls` under `auth/`, which already provides `auth/logout/` named `logout`. So `{% url 'logout' %}` in `_menu.html` and `_menu_iframe.html` keeps resolving, to a plain Django logout with no forum sync, which is what you want once the forum is gone.

**`web/templates/website/_menu.html`:** its Forum link uses `{% url 'discourse-session-sync' %}` for logged-in users and a fixed forum address for visitors. Remove both Forum entries, or every page that shows the menu fails with an error once the `discourse-session-sync` pattern is gone.

**Other forum pieces:**
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
- **NodeBB**: similar theme customization system
- **Flarum**: supports custom headers via extensions
- **Vanilla Forums**: has iframe embedding capabilities
- **phpBB**: requires custom theme modifications

Change the SSO implementation to match your platform's protocol.

### Using Discord Instead

If you prefer Discord:
- Use Discord's OAuth2 for authentication
- Embed the Discord widget in your website
- No need for SSO complexity
- Simpler to maintain

---

## Troubleshooting

### SSO Not Working

**Check:**
1. `DISCOURSE_SSO_SECRET` is set in Django settings
2. The same secret is configured in Discourse
3. `discourse connect url` points to `https://yourgame.com/sso/discourse/`
4. The user is logged into Django before trying to access the forum

**Debug:**
```bash
# Check if endpoint is accessible
curl https://yourgame.com/sso/discourse/
```

What it returns:
- Logged out (plain curl): a redirect to the login page. That is expected; the endpoint needs a logged-in game session.
- Logged in, with no `sso`/`sig` parameters: "Missing SSO parameters".
- Logged in, with no `DISCOURSE_SSO_SECRET` set: "SSO is not configured".

### Header Not Showing

**Check:**
1. The theme component is activated
2. The JavaScript has no errors (check the browser console)
3. The `/header-only/` endpoint is accessible: `curl https://yourgame.com/header-only/`

### Colors Wrong

**Check:**
1. The Color Palette is applied to the theme
2. The CSS is saved in the theme component
3. Hard refresh the browser (Cmd+Shift+R or Ctrl+Shift+R)

---

## Performance Notes

- **No caching**: the header endpoint is sent with `no-store` and is never cached, because it shows who is logged in. Every forum page view asks the game's web server for the header.
- **Preconnect**: the browser establishes the connection early.
- **CSS Containment**: isolates iframe rendering.
- **Lazy Loading**: the iframe loads after the main content.

Expected initial load: 50-200ms iframe load time.

---

## Maintenance

### Keeping Theme Updated

When you change the Django header styling:
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

**Related documents:**
- `DISCOURSE_INTEGRATION.md`: forum theme configuration.

**Discourse Documentation**:
- DiscourseConnect (SSO): https://meta.discourse.org/t/13045
- Theme Components: https://meta.discourse.org/t/93648
- Color Schemes: https://meta.discourse.org/t/108801

**Evennia Documentation**:
- Web Views: https://www.evennia.com/docs/latest/Components/Web-Views.html
- Web Configuration: https://www.evennia.com/docs/latest/Setup/Web-Config.html
