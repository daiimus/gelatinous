# Discourse Forum Integration
## Complete Setup Guide for Gelatinous

This document provides everything you need to integrate a Discourse forum with your Evennia game.

**Note**: This is completely optional. See `FORUM_INTEGRATION_GUIDE.md` for a discussion of whether you need forum integration at all.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Configure Django (Game Side)](#step-1-configure-django-game-side)
4. [Step 2: Configure Discourse SSO](#step-2-configure-discourse-sso)
5. [Step 3: Apply Color Palette](#step-3-apply-color-palette)
6. [Step 4: Create Theme Component](#step-4-create-theme-component)
7. [Step 5: Add HTML](#step-5-add-html)
8. [Step 6: Add CSS](#step-6-add-css)
9. [Step 7: Add JavaScript](#step-7-add-javascript)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This integration provides:
- **Single Sign-On (SSO)**: Log in once, access both game and forum
- **Visual Consistency**: Django header embedded in forum
- **Session Sync**: Logout from one logs out of both
- **Custom Styling**: Forum themed to match game

**What you'll be setting up:**
- Django SSO provider (already implemented in code)
- Discourse DiscourseConnect (SSO consumer)
- Custom Discourse theme with embedded Django header
- Color palette matching your game's aesthetic

---

## Prerequisites

1. **Running Discourse instance**
   - Self-hosted or managed hosting
   - Admin access required

2. **Django settings access**
   - Ability to edit `server/conf/secret_settings.py`
   - Ability to restart server

3. **Shared secret**
   - Generate a secure random string (32+ characters)
   - Use same secret in both Django and Discourse

---

## Step 1: Configure Django (Game Side)

### 1.1 Add Settings

Edit `server/conf/secret_settings.py`:

```python
# Discourse SSO Configuration (Optional)
DISCOURSE_SSO_SECRET = "your-shared-secret-here"  # Must match Discourse
DISCOURSE_URL = "https://forum.yourgame.com"      # Your forum URL
DISCOURSE_API_KEY = "your-discourse-api-key"      # For logout sync (optional)
```

### 1.2 Generate Shared Secret

```bash
# Generate a secure random secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 1.3 Restart Server

```bash
# If using Docker
docker-compose restart

# Or direct Evennia
evennia reload
```

**That's it for Django!** The SSO endpoints are already implemented:
- `/sso/discourse/` - SSO authentication
- `/sso/discourse/logout/` - Logout handler
- `/sso/discourse/session-sync/` - Session sync
- `/header-only/` - Header iframe endpoint

---

## Step 2: Configure Discourse SSO

### 2.1 Enable DiscourseConnect

1. Go to **Discourse Admin** → **Settings** → **Login**
2. Enable: `enable discourse connect` = `true`
3. Set: `discourse connect url` = `https://yourgame.com/sso/discourse/`
4. Set: `discourse connect secret` = (same secret from Django settings)
5. Set: `logout redirect` = `https://yourgame.com/sso/discourse/logout/`

### 2.2 Optional SSO Settings

```
sso overrides avatar = true          # Use avatars from Django
sso overrides bio = true             # Use bio from Django
sso overrides email = true           # Trust Django email
sso overrides name = true            # Use Django display name
```

### 2.3 Disable Local Logins (Recommended)

```
enable local logins = false          # Force SSO only
```

---

## Step 3: Apply Color Palette

### 3.1 Create Color Scheme

1. Go to **Admin** → **Customize** → **Colors**
2. Click **+ New Color Scheme**
3. Name it: "Gelatinous Dark"

### 3.2 Set Color Values

Use these values (matching the live site palette in `STYLING_SPEC.md` /
`custom.css` — the Atlas register: ink ground, bone text, amber accent):

```
Primary (text):           #d8d3c4   (bone)
Primary-medium:           #a9a49a
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

If the scheme you are replacing had a `tertiary-med-or-tertiary` override, set
it too — otherwise the old accent bleeds through in a handful of places.

### 3.3 Apply to Theme

1. Go to **Admin** → **Customize** → **Themes**
2. Select your default theme
3. Under **Colors**, select your scheme
4. **Save**

> **⚠ There are TWO colour-scheme slots, and both matter.** A theme has
> `color_scheme_id` (light) and `dark_color_scheme_id` (dark). Discourse serves
> the dark one to anyone whose OS is in dark mode. Setting only the light slot
> looks *exactly* like the change never applied — the old palette keeps showing,
> accent and all.
>
> This palette is already dark, so put it in **both** slots unless you have
> built a genuine light variant.
>
> **Colour schemes do not travel with theme components.** Installing a component
> that declares `color_schemes` in `about.json` does not create the scheme —
> build it by hand as above, or via the API, and select it on the parent theme.

---

## Step 4: Create Theme Component

### 4.1 Create Component

1. Go to **Admin** → **Customize** → **Themes**
2. Click **Install** → **Create New**
3. Name: "Django Header Integration"
4. Type: **Theme Component**
5. Click **Create**

### 4.2 Add to Main Theme

1. Edit your main theme (not the component)
2. Scroll to **Included Components**
3. Select "Django Header Integration"
4. **Save**

---

## Step 5: Add HTML

1. Edit the "Django Header Integration" component
2. Click **Edit HTML**
3. Select `</head>` section
4. Paste:

```html
<link rel="preconnect" href="https://yourgame.com">
<link rel="dns-prefetch" href="https://yourgame.com">
<div id="gel-django-header-container"></div>
```

5. Replace `https://yourgame.com` with your actual domain
6. **Save**

---

## Step 6: Add CSS

1. Still editing the component
2. Go to **Common** → **CSS**
3. Paste this **entire CSS**:

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

4. **Save**

---

## Step 7: Add JavaScript

1. Still editing the component
2. Go to **Common** → **JavaScript**
3. Paste:

```javascript
import { apiInitializer } from "discourse/lib/api";

export default apiInitializer("1.8.0", (api) => {
  let iframeCreated = false;
  
  function createHeaderIframe() {
    // Prevent multiple iframes - check if already created
    if (iframeCreated) return;
    
    const container = document.getElementById('gel-django-header-container');
    if (!container) return;
    
    // Check if iframe already exists in DOM
    const existingIframe = document.getElementById('gel-django-header-iframe');
    if (existingIframe) {
      iframeCreated = true;
      return;
    }
    
    // Mark as created immediately to prevent race conditions
    iframeCreated = true;
    
    container.classList.add('loading');
    
    const iframe = document.createElement('iframe');
    iframe.id = 'gel-django-header-iframe';
    iframe.src = 'https://yourgame.com/header-only/'; // CHANGE THIS
    iframe.frameBorder = '0';
    iframe.scrolling = 'no';
    iframe.title = 'Game Navigation';
    
    iframe.onload = function() {
      container.classList.remove('loading');
    };
    
    container.appendChild(iframe);
  }
  
  // Handle height updates from Django header iframe
  window.addEventListener('message', (event) => {
    if (event.origin !== 'https://yourgame.com') return; // CHANGE THIS
    
    if (event.data.type === 'gel-header-height') {
      const iframe = document.getElementById('gel-django-header-iframe');
      const height = event.data.height;
      
      if (iframe) {
        iframe.style.height = height + 'px';
        document.body.style.paddingTop = height + 'px';
        
        const mainOutlet = document.getElementById('main-outlet');
        if (mainOutlet) {
          mainOutlet.style.marginTop = height + 'px';
        }
        
        const sidebar = document.querySelector('.sidebar-wrapper');
        if (sidebar) {
          sidebar.style.top = height + 'px';
        }
      }
    }
  });
  
  // Create header on initial load and page changes
  api.onPageChange(() => {
    createHeaderIframe();
  });
  
  // Handle logout redirect
  if (window.location.hash === '#logout') {
    document.cookie = '_forum_session=;expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    document.cookie = '_t=;expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    window.location.href = 'https://yourgame.com/'; // CHANGE THIS
  }
});
```

4. **IMPORTANT**: Replace all instances of `https://yourgame.com` with your actual domain
5. **Save**

---

## The header height contract

The header is an iframe, and an iframe **clips its own content**. Anything the
header needs to draw below its own height — an account dropdown, a flash
message — is invisible unless the parent is told to grow. That contract spans
both sides, and every piece of it is load-bearing.

**Site side** (`web/templates/website/header_only.html`):

```js
window.parent.postMessage({ type: 'gel-header-height', height: measuredHeight() },
                          TARGET_ORIGIN);
```

**Forum side** (the theme component's `theme-initializer.gjs`) listens, checks
the origin, and sets **both** the iframe and its container:

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
3. **Do not disable dropdowns in CSS.** An earlier attempt shipped
   `.dropdown-menu { display: none !important }` with the note "they render
   outside bounds". That was true then, but `display: none` also denies the
   menu the layout the measurement depends on — with it, the protocol
   silently measures nothing. **If dropdowns ever need removing, remove the
   markup, not the layout.**
4. **Every link needs `target="_top"`.** Without it, navigation loads the
   destination *inside* the 80px header frame.

### The header must never be cached

`/header-only/` is auth state — it names the logged-in account and renders a
different menu for anonymous visitors. It was previously
`Cache-Control: max-age=300, private`, which meant the forum header could keep
saying "Logged in as X" for five minutes after logout, and made template
changes appear not to ship. `private` stops shared caches, not the browser's.
It is now `no_store, no_cache, must_revalidate, private`.

## Forum branding is not inherited

Discourse serves its own icons and does **not** pick anything up from the
game site. Four settings decide how the forum appears in a tab, a bookmark, a
phone home screen and a shared link:

| setting | used for |
|---------|----------|
| `favicon` | browser tab |
| `logo_small` | collapsed header |
| `large_icon` | PWA / manifest |
| `apple_touch_icon` | iOS home screen |

All four were empty, so the forum showed Discourse's stock icon while the
game site showed the brand mark. They are uploads, not URLs — set them in
**Admin → Settings → Branding**, or create an `Upload` and assign it.

> Uploading via `rails runner` fails with `EPERM` if the file was placed with
> `docker cp`: `image_optim` rewrites the image **in place** and the copied
> file is not owned by the `discourse` user. `chown discourse:discourse` it
> first.

## Testing

### Test SSO Login

1. **Open forum while logged into game**
2. Click "Login" on forum
3. Should redirect to Django SSO endpoint
4. Should auto-login without password prompt
5. Should redirect back to forum as logged-in user

### Test Header Display

1. **Navigate to forum**
2. Should see Django header at top
3. Discourse header should be hidden
4. Header should match main site exactly

### Test Logout Sync

1. **While logged into both**
2. Click "Log Out" from header (on forum)
3. Should logout from both Django and Discourse
4. Refresh forum - should be logged out

### Test Mobile

1. **View forum on mobile device or narrow browser**
2. Header should show hamburger menu
3. Menu should collapse properly
4. Same 80px height as desktop

---

## Troubleshooting

### SSO Not Working

**Symptom**: Can't login to forum

**Check**:
1. `DISCOURSE_SSO_SECRET` set in Django
2. Same secret in Discourse settings
3. `discourse connect url` points to correct Django endpoint
4. User is logged into Django first

**Debug**:
```bash
# Test SSO endpoint (should show error - that's good!)
curl https://yourgame.com/sso/discourse/
# Output: "Missing SSO parameters" = endpoint is working
```

### Header Not Showing

**Symptom**: No header visible in forum

**Check**:
1. Theme component is activated
2. JavaScript has no errors (check browser console: F12)
3. `/header-only/` endpoint is accessible
4. Correct domain in JavaScript `iframe.src`

**Debug**:
```bash
# Test header endpoint
curl https://yourgame.com/header-only/
# Should return HTML with navbar
```

### Colors Wrong

**Symptom**: Forum colors don't match game

**Check**:
1. Color Palette is applied to theme
2. CSS is saved in theme component
3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### Double Headers

**Symptom**: See both Discourse and Django headers

**Check**:
1. CSS has `.d-header { display: none !important; }`
2. Theme component is included in main theme
3. JavaScript `iframeCreated` flag is working

### Mobile Layout Issues

**Symptom**: Header looks wrong on mobile

**Check**:
1. Mobile CSS media query is present
2. Both heights are 80px (not 60px)
3. Django Bootstrap version matches (4.6.0)
4. No font-size overrides in header_only.html

---

## Performance Notes

The integration includes several optimizations:

- **Caching**: Header endpoint cached for 5 minutes (`@cache_control`)
- **Preconnect**: Browser establishes connection early
- **CSS Containment**: Isolates iframe rendering (`contain: layout style`)
- **Fixed Height**: Prevents layout reflow (80px pre-allocated)

**Expected Performance**:
- Initial load: 50-200ms iframe load time
- Cached load: <50ms
- No impact on game server performance

---

## Maintenance

### Updating Header Styling

When you update Django header CSS:
1. Changes automatically apply to forum iframe
2. No theme updates needed
3. Cache clears after 5 minutes

### Discourse Updates

> **⚠ If the admin panel says an upgrade is required, that means REBUILD the
> container — not press the upgrade button.**
>
> Discourse splits updates in two tiers. The admin UI upgrade (`docker_manager`)
> handles the **app tier**: it runs `bundle install`, `pnpm install`, migrations
> and `assets:precompile`. It cannot touch the **image tier** — Ruby itself,
> Node, Postgres, system libraries — because those are baked into
> `discourse/base`.
>
> `docker_manager` compares the running Ruby and base image against what core
> expects and flags `upgrade_required` when either is behind. **It only warns.**
> It will still let you press upgrade, and the git pull happens *before*
> `bundle install` can fail — so a version-skewed site ends up on code it cannot
> run, with no rollback. Symptoms: every page 500s with errors like
> `undefined method 'generate_import_map'` or a missing JS package.
>
> Recovery, if it happens: the pulled source is only in the container's writable
> layer, so `git reset --hard <previous-commit>` inside the container plus
> `docker restart` restores service. Note `sv restart unicorn` is **not**
> sufficient — it restarts the runit wrapper but can leave the old unicorn
> master alive serving stale code from memory.

After major Discourse upgrades, test:
- SSO login flow
- Header display
- Theme component functionality
- Color scheme application — **check dark mode too**, see below

### Keeping Bootstrap Versions Synced

Ensure `header_only.html` uses same Bootstrap version as main site:
```html
<!-- Current: Bootstrap 4.6.0 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/...">
```

---

## Summary

✅ **Django Side**: SSO endpoints already implemented, just add settings
✅ **Discourse Side**: Configure SSO, apply theme component
✅ **Result**: Seamless integration with unified login and consistent UI

The integration is production-ready and handles edge cases gracefully. If you skip the forum entirely, the Django code works fine (returns errors for unconfigured SSO endpoints but doesn't break anything).

---

## Quick Reference

**Django Settings**:
- `DISCOURSE_SSO_SECRET` - Shared secret
- `DISCOURSE_URL` - Forum URL
- `DISCOURSE_API_KEY` - API key (optional, for logout sync)

**Django Endpoints**:
- `/sso/discourse/` - SSO authentication
- `/sso/discourse/logout/` - Logout handler
- `/header-only/` - Header iframe

**Discourse Settings**:
- `enable discourse connect` = true
- `discourse connect url` = `https://yourgame.com/sso/discourse/`
- `discourse connect secret` = (shared secret)
- `logout redirect` = `https://yourgame.com/sso/discourse/logout/`

**Files to Update**:
- `server/conf/secret_settings.py` - Django SSO config
- Discourse theme component - HTML, CSS, JavaScript
- Discourse color palette - Match game colors
