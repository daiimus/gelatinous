# Cloudflare Turnstile Integration Guide

> **Status:** ✅ **SHIPPED & LIVE** — verified 2026-08-03: the widget renders on the live registration page and both keys resolve non-empty at runtime.
>
> **⚠ Spec-vs-code corrections — the following claims were FALSE when audited:**
> - An earlier audit called this inactive because `settings.py` holds empty strings. **That was wrong.** The real keys live in `server/conf/secret_settings.py`, which is gitignored — reading the committed repo says nothing about what the deployment is running. Empty keys *would* skip verification, so the check is worth keeping in mind, but it does not apply here. *(2026-09-12: this pointer used to read `views/accounts.py:62-63`, and it was exactly right when written — at commit 6c429af2 those two lines were `turnstile_secret = getattr(settings, 'TURNSTILE_SECRET_KEY', None)` / `if turnstile_secret:`. They are now `template_name` / `success_url`. The skip lives in `turnstile_config()` at `web/website/views/accounts.py:22-50`, consumed by `form_valid` at `:97-98`.)*
>
> **⚠ 2026-09-12 — #2747 (closed 2026-09-05) restructured the on-switch; the body of this guide predates it and still describes the two-switch design.** There is now ONE answer to "is the CAPTCHA on?": `turnstile_config()` (`web/website/views/accounts.py:22-50`) returns `(site_key, secret_key, enabled)` and **`enabled` requires BOTH keys** (`:50`). Consequences the sections below do not reflect:
> - A half-configured deployment (one key only) is **off**, not half-on, and logs `"Turnstile is half-configured: … The CAPTCHA is NOT protecting registration. Set both or neither."` naming the missing key (`accounts.py:44-49`).
> - The widget div *and* the script tag are gated on `turnstile_enabled`, not on the site key (`web/templates/website/registration/register.html:50` and `:83`) — so a missing **secret** key also makes the widget vanish.
> - `verify_turnstile()` with no secret now **fails closed** (`accounts.py:136-147`); it used to `return True`. Network / JSON / timeout failures fail closed too (`:167-173`).
> - Pinned by `world/tests/test_registration_captcha.py` (9 tests across `TestOneDecision`, `TestAHalfConfiguredDeploymentSaysSo`, `TestVerificationFailsClosed`).
> - Issue #1513 still carries the superseded wording "empty keys cause `views/accounts.py:62-63` to skip verification **and return True**" — the `return True` is gone; only the skip remains.
>
> Read every note dated 2026-09-12 below alongside the section it sits in; those sections were written against the pre-#2747 design.
>
> **Live evidence, probed read-only 2026-09-12:** inside the `gelatinous` container `/auth/register` returns 200 and the rendered HTML contains the `cf-turnstile` div, `challenges.cloudflare.com/turnstile/v0/api.js`, `data-theme="dark"` and `id_cf_turnstile_response`; `/accounts/register/` returns 404. Both keys in the live `server/conf/secret_settings.py` are non-empty and neither matches Cloudflare's `1x0…`/`2x0…`/`3x0…` test-key prefixes (checked without printing values).

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
- `specs/TURNSTILE_INTEGRATION_SPEC.md` - This file *(2026-09-12: this line used to read `docs/TURNSTILE_INTEGRATION.md`, which was correct when the integration shipped — commit b47ba753, 2025-10-18, created the file at exactly that path. The later documentation reorg, commit b749c50e, renamed it into `specs/` and this self-reference was never updated; there is no `docs/` directory in the repo today. `specs/README.md` lists the guide at its real path.)*

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

1. Navigate to `/auth/register` or click "Create Account" on login page *(2026-09-12: the path used to read `/accounts/register/`, which was the real route when this guide shipped — `path("accounts/register/", TurnstileAccountCreateView.as_view(), name="register")` at commit b47ba753. It was later realigned to Evennia 6.1.0's own route, `path("auth/register", TurnstileAccountCreateView.as_view(), name="register")` — `web/website/urls.py:61`, matching `evennia/web/website/urls.py:20` — and this line was not updated. Nothing broke, because every link is reversed by name: `{% url 'register' %}` in `registration/login.html:41`, `_menu.html:186` and `_menu_iframe.html:188`. That is why the stale path went unnoticed. Probed 2026-09-12: `/auth/register` → 200, `/accounts/register/` → 404.)*
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
- Secret Key: `3x0000000000000000000000000000000FF` — **wrong key (2026-09-12).** This is not one of Cloudflare's dummy secrets; the real third one is `3x0000000000000000000000000000000AA`. Probed against `siteverify` on 2026-09-12: the three genuine dummy secrets (`1x…AA`, `2x…AA`, `3x…AA`) each answer with `metadata.result_with_testing_key` present — `success: true`, `invalid-input-response`, and `timeout-or-duplicate` respectively — while the `…FF` value above answers `{"success": false, "error-codes": ["invalid-input-secret"]}` with no such metadata, i.e. Cloudflare does not recognise it as a test key at all. The `FF` suffix belongs only to the **site** key on the line above. An operator who pairs these two to exercise the block path gets `invalid-input-secret` and will wrongly conclude their secret-key wiring is broken.

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
- IP address included in verification — **but not as a security control (2026-09-12).** `get_client_ip()` takes the leftmost element of the client-supplied `X-Forwarded-For` header (`web/website/views/accounts.py:182-184`) and sends it to Cloudflare as `remoteip` (`:156`). The Cloudflare tunnel that fronts this site *appends* the real client IP to whatever `X-Forwarded-For` arrived rather than replacing it, so the leftmost value is whatever the client chose to send. It is therefore forgeable and adds nothing; the only realistic effect of a forged value is siteverify rejecting a legitimate registration. `CF-Connecting-IP`, which the tunnel sets and a client cannot forge, is available and unused — see owner question. This is a code weakness, not a CAPTCHA bypass: a wrong `remoteip` makes verification stricter, never looser.
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
