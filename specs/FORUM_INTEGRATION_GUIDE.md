# Forum Integration Guide
## Optional Discourse Forum Setup for Gelatinous

This guide covers the optional integration between your Evennia game and a Discourse forum. **This is completely optional** - the game works perfectly fine without it.

---

## Overview

The Gelatinous project includes optional support for integrating with a Discourse forum, providing:

- **Single Sign-On (SSO)**: Users log in once, access both game and forum
- **Visual Consistency**: Embedded Django header in forum for seamless navigation
- **Session Synchronization**: Login/logout synced between platforms
- **Custom Styling**: Forum themed to match game aesthetic

**If you don't plan to run a forum**: You can safely ignore all Discourse-related files and configuration. The game will work normally.

---

## What's Already Built (Optional to Use)

### Django Side (Game)

The following files support forum integration but are **non-invasive**:

**Views** (`web/website/views/`):
- `discourse_sso.py` - SSO authentication handler (only runs if `DISCOURSE_SSO_SECRET` is set)
- `discourse_logout.py` - Forum logout handler
- `discourse_session_sync.py` - Session synchronization
- `logout_with_discourse.py` - Dual logout
- `header_only.py` - Header iframe endpoint (harmless even if unused)

**URL Routes** (`web/website/urls.py`):
- `/header-only/` - Renders just the header (can be used for any iframe embedding)
- `/sso/discourse/` - SSO endpoint (returns error if not configured)
- `/sso/discourse/logout/` - Logout endpoint
- `/sso/discourse/session-sync/` - Session sync endpoint

**Templates** (`web/templates/website/`):
- `header_only.html` - Minimal header template for embedding

### Discourse Side (Forum)

If you set up a Discourse forum, the complete theme configuration —
color scheme, header-integration CSS, iframe-embedding JavaScript, and
caching/preconnect setup — lives in **`DISCOURSE_INTEGRATION.md`**
(steps 3–9). (The previously-separate `DISCOURSE_COLOR_PALETTE.md` /
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

2. **Restart your game server** (Docker or Evennia reload)

That's it for the Django side! The routes and views are already in place.

### Step 2: Configure Discourse (Forum Side)

#### A. Enable DiscourseConnect (SSO)

1. Go to **Discourse Admin** → **Settings** → **Login**
2. Enable: `enable discourse connect`
3. Set: `discourse connect url` = `https://yourgame.com/sso/discourse/`
4. Set: `discourse connect secret` = (same secret as in Django settings)
5. Set: `logout redirect` = `https://yourgame.com/sso/discourse/logout/`

#### B. Create Theme Component

1. Go to **Admin** → **Customize** → **Themes**
2. Click **Install** → **Create New**
3. Name it: "Django Header Integration"
4. Type: **Theme Component**

#### C. Apply Color Palette

1. Go to **Admin** → **Customize** → **Colors**
2. Create new color scheme using values from `DISCOURSE_COLOR_PALETTE.md`
3. Apply it to your main theme

#### D. Add CSS

1. Edit your theme component
2. Go to **Common** → **CSS**
3. Paste CSS from `DISCOURSE_DARK_THEME_CSS.md`
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
3. Paste JavaScript from `DISCOURSE_THEME_CODE_FIXED.md`
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
- Don't set `DISCOURSE_SSO_SECRET` in settings
- The views will return errors if accessed, but won't break anything
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

# Remove forum specs (optional)
rm specs/DISCOURSE_*.md
rm specs/FORUM_INTEGRATION_*.md
rm specs/CACHING_AND_PRECONNECT_SETUP.md
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
```

---

## Customization

### Using a Different Forum Platform

The header iframe approach (`/header-only/`) works with any forum that supports:
- Custom HTML/CSS/JavaScript
- Iframe embedding

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

# Should return: "Missing SSO parameters" (that's good!)
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

- **Caching**: Header endpoint cached for 5 minutes
- **Preconnect**: Browser establishes connection early
- **CSS Containment**: Isolates iframe rendering
- **Lazy Loading**: Iframe loads after main content

Expected performance:
- Initial load: 50-200ms iframe load time
- Cached: <50ms
- No impact on game server performance

---

## Maintenance

### Keeping Theme Updated

If you update your Django header styling:
1. Changes automatically apply to forum iframe
2. No theme updates needed
3. Cache clears after 5 minutes

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
