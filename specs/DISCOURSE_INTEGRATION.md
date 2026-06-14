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
`custom.css` — the muted jade-green "Blade Runner" scheme, **not** the
old blue accent):

```
Primary (text):           #e0e0e0
Secondary (background):   #1a1a1a
Tertiary (accent):        #5fd38d   (muted jade green)
Quaternary (borders):     #404040
Header Background:        #1a1a1a
Header Primary:           #e0e0e0
Highlight (selected):     #4a9d6d   (dimmed jade)
Danger (errors):          #e85555
Success (confirmations):  #5fd38d
Love (likes):             #e6c547
```

### 3.3 Apply to Theme

1. Go to **Admin** → **Customize** → **Themes**
2. Select your default theme
3. Under **Colors**, select "Gelatinous Dark"
4. **Save**

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
  background-color: #1a1a1a;
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
  background-color: #1a1a1a;
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

After major Discourse upgrades, test:
- SSO login flow
- Header display
- Theme component functionality
- Color scheme application

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
