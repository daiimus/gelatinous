# Cloudflare Turnstile Integration Guide

> **Status:** ✅ **SHIPPED** — code shipped, but **inactive unless keys are configured**. Verified 2026-08-02.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` are empty strings in committed settings, and empty keys **skip verification** (`views/accounts.py:62-63`). The integration exists; that is not evidence CAPTCHA is live.

## Overview

Cloudflare Turnstile has been integrated into the Gelatinous Monster account registration system. Turnstile is a privacy-friendly, free CAPTCHA alternative that provides bot protection without the privacy concerns of traditional CAPTCHAs.

## Features

- **Privacy-Friendly**: No tracking, no cookies, respects user privacy
- **Free**: Completely free for unlimited use
- **Accessible**: Works without requiring user interaction in many cases
- **Dark Theme**: Matches Gelatinous Monster's dark aesthetic
- **Server-Side Verification**: Token validation happens server-side for security

## Files Modified

### New Files Created:
- `web/website/views/accounts.py` - Custom account creation view with Turnstile verification
- `web/templates/website/registration/register.html` - Registration template with Turnstile widget
- `docs/TURNSTILE_INTEGRATION.md` - This file

### Modified Files:
- `web/website/forms.py` - Added `TurnstileAccountForm` with hidden cf_turnstile_response field
- `web/website/urls.py` - Added route for custom registration view
- `server/conf/settings.py` - Added Turnstile configuration (TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY)

## Setup Instructions

### 1. Get Cloudflare Turnstile Keys

1. Visit https://dash.cloudflare.com/ and log in (or create a free account)
2. Navigate to **Turnstile** in the left sidebar
3. Click **Add Site**
4. Configure your site:
   - **Site name**: Gelatinous Monster
   - **Domain**: `gel.monster` (or your domain)
   - **Widget Mode**: Managed (recommended)
5. Click **Add** and copy your keys:
   - **Site Key** (public, visible in HTML)
   - **Secret Key** (private, server-side only)

### 2. Configure Settings

**Option A: Direct Configuration (Development Only)**

Edit `server/conf/settings.py`:
```python
TURNSTILE_SITE_KEY = "your-site-key-here"
TURNSTILE_SECRET_KEY = "your-secret-key-here"
```

**Option B: Secret Settings (Production - Recommended)**

Add to `server/conf/secret_settings.py`:
```python
# Cloudflare Turnstile
TURNSTILE_SITE_KEY = "your-site-key-here"
TURNSTILE_SECRET_KEY = "your-secret-key-here"
```

### 3. Install Required Python Package

The Turnstile integration uses the `requests` library for server-side verification:

```bash
pip install requests
```

Or add to your `requirements.txt`:
```
requests>=2.31.0
```

### 4. Enable Account Registration

Make sure account registration is enabled in `server/conf/settings.py`:
```python
NEW_ACCOUNT_REGISTRATION_ENABLED = True
```

### 5. Restart Evennia

```bash
evennia stop
evennia start
```

## Testing

### Test Registration Flow:

1. Navigate to `/accounts/register/` or click "Create Account" on login page
2. Fill out registration form (username, email, password)
3. Complete the Turnstile verification (usually automatic)
4. Submit the form
5. Should redirect to login page with success message

### Testing with Cloudflare Test Keys:

Cloudflare provides test keys that always pass/fail:

**Always Passes:**
- Site Key: `1x00000000000000000000AA`
- Secret Key: `1x0000000000000000000000000000000AA`

**Always Fails:**
- Site Key: `2x00000000000000000000AB`
- Secret Key: `2x0000000000000000000000000000000AA`

**Always Blocks:**
- Site Key: `3x00000000000000000000FF`
- Secret Key: `3x0000000000000000000000000000000FF`

Use these for development/testing without creating a Cloudflare account.

## How It Works

### Client-Side (Template):

1. Turnstile JavaScript widget loads: `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js">`
2. Widget renders in form: `<div class="cf-turnstile" data-sitekey="...">`
3. On successful verification, callback populates hidden field: `onTurnstileSuccess(token)`
4. Form submits with token in `cf_turnstile_response` field

### Server-Side (View):

1. Form submitted with Turnstile token
2. `TurnstileAccountCreateView.form_valid()` extracts token
3. `verify_turnstile()` sends token to Cloudflare API for verification
4. If verified: Account creation proceeds
5. If failed: Form error displayed, account not created

### Security Features:

- Token validation requires secret key (never exposed to client)
- Token is single-use (can't be reused)
- IP address included in verification for additional security
- Verification happens server-side (can't be bypassed client-side)

## Customization

### Widget Appearance:

The Turnstile widget supports several themes and sizes:

```html
<div class="cf-turnstile" 
     data-sitekey="your-key"
     data-theme="dark"          <!-- light, dark, auto -->
     data-size="normal"          <!-- normal, compact -->
     data-language="en">         <!-- Language code -->
</div>
```

### Error Messages:

Customize error messages in `web/website/forms.py`:

```python
cf_turnstile_response = forms.CharField(
    error_messages={
        'required': 'Your custom error message here'
    }
)
```

### Verification Endpoint:

The verification happens at Cloudflare's API:
- Endpoint: `https://challenges.cloudflare.com/turnstile/v0/siteverify`
- Method: POST
- Data: `{secret, response, remoteip (optional)}`
- Response: `{success: true/false, error-codes: []}`

## Troubleshooting

### Issue: "CAPTCHA verification failed"

**Causes:**
- Invalid or expired token
- Incorrect secret key
- Network error contacting Cloudflare API
- Token already used (tokens are single-use)

**Solutions:**
- Check `TURNSTILE_SECRET_KEY` in settings
- Ensure server can reach `challenges.cloudflare.com`
- Check server logs for specific error messages
- Try refreshing the page and verifying again

### Issue: Widget not appearing

**Causes:**
- Missing or incorrect site key
- JavaScript blocked
- Ad blocker blocking Cloudflare
- Missing Turnstile script tag

**Solutions:**
- Verify `TURNSTILE_SITE_KEY` in template context
- Check browser console for errors
- Temporarily disable ad blockers
- Ensure `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js">` is loaded

### Issue: "TURNSTILE_SECRET_KEY not configured"

**Solution:**
- Add `TURNSTILE_SECRET_KEY` to `server/conf/settings.py` or `secret_settings.py`

### Issue: Form submits without verification

**Solution:**
- Ensure hidden field `id_cf_turnstile_response` exists in form
- Check JavaScript callback `onTurnstileSuccess()` is firing
- Verify form validation in template

## Production Deployment

### Security Checklist:

- [ ] Move Turnstile keys to `secret_settings.py` (never commit to git)
- [ ] Use production keys (not test keys)
- [ ] Ensure HTTPS is enabled (required for Turnstile)
- [ ] Set correct domain in Cloudflare dashboard
- [ ] Test registration flow on production domain
- [ ] Monitor Cloudflare Turnstile analytics for bot attempts

### Environment Variables (Alternative):

Instead of settings files, you can use environment variables:

```python
# In settings.py
import os
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')
```

Then set in your environment:
```bash
export TURNSTILE_SITE_KEY="your-key"
export TURNSTILE_SECRET_KEY="your-secret"
```

## Resources

- **Cloudflare Turnstile Docs**: https://developers.cloudflare.com/turnstile/
- **Get Turnstile Keys**: https://dash.cloudflare.com/?to=/:account/turnstile
- **Turnstile API Reference**: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- **Widget Parameters**: https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/

## Support

If you encounter issues:
1. Check Cloudflare Turnstile documentation
2. Review server logs for error messages
3. Test with Cloudflare test keys
4. Ensure `requests` library is installed

## Future Enhancements

Potential improvements:
- [ ] Add Turnstile to password reset form
- [ ] Add Turnstile to contact forms
- [ ] Implement retry logic for network failures
- [ ] Add custom error page for verification failures
- [ ] Track verification statistics in admin panel
- [ ] Add rate limiting per IP address
- [ ] Implement invisible Turnstile mode for seamless UX
