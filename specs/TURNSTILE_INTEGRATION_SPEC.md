# Cloudflare Turnstile Integration Guide

## Overview

Account registration on the Gelatinous Monster website is guarded by Cloudflare Turnstile, a free, privacy-friendly CAPTCHA alternative: no tracking, no cookies, and in many cases no user interaction. The widget uses the dark theme to match the site. The token is checked server-side, so the check cannot be bypassed in the browser.

## The on-switch: one decision, two keys

There is one answer to "is the CAPTCHA on?": `turnstile_config()` in `web/website/views/accounts.py`. It returns `(site_key, secret_key, enabled)`, and `enabled` requires BOTH `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` (#2747). Rendering the widget and enforcing the token both read this one answer.

- **Both keys empty:** registration runs with no CAPTCHA and logs nothing, so a fresh clone works without a Cloudflare account.
- **Both keys set:** the widget renders and the server verifies every token.
- **One key set (half-configured):** the CAPTCHA is off, not half-on. The server logs an error each time the registration page is shown or sent, naming the missing key: `"Turnstile is half-configured: … The CAPTCHA is NOT protecting registration. Set both or neither."`

The widget div and the script tag in `web/templates/website/registration/register.html` are gated on `turnstile_enabled`, not on the site key, so a missing secret key also makes the widget vanish.

`server/conf/settings.py` holds empty strings for both keys. The real keys live in `server/conf/secret_settings.py`, which is gitignored, so reading the committed repo says nothing about what a deployment is running.

## Where it lives

- `web/website/views/accounts.py`: `turnstile_config()`, and `TurnstileAccountCreateView` with `form_valid()`, `verify_turnstile()` and `get_client_ip()`.
- `web/templates/website/registration/register.html`: the registration page with the Turnstile widget.
- `web/website/forms.py`: `TurnstileAccountForm`, with the hidden, optional `cf_turnstile_response` field.
- `web/website/urls.py`: the route `auth/register`, named `register`, served by `TurnstileAccountCreateView`. It matches Evennia 6.1.0's own route. Every link to it is reversed by name (`{% url 'register' %}` in `registration/login.html`, `_menu.html` and `_menu_iframe.html`). `/accounts/register/` is not a route.
- `server/conf/settings.py`: the `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` settings.

## How it works

### Client side (template)

1. The Turnstile script loads: `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js">`.
2. The widget renders in the form: `<div class="cf-turnstile" data-sitekey="...">`, with `data-theme="dark"`.
3. On success, the callback `onTurnstileSuccess(token)` fills the hidden field `id_cf_turnstile_response`.
4. The form submits with the token in `cf_turnstile_response`.

The browser check only stops the form being sent before the widget finishes. It is not the protection: the server refuses an unverified post whatever the browser does.

### Server side (view)

1. The form is submitted.
2. `TurnstileAccountCreateView.form_valid()` asks `turnstile_config()` whether the CAPTCHA is on. If it is off, it goes straight to step 4.
3. If it is on, `verify_turnstile()` sends the token to Cloudflare. A refusal, network error, bad reply or timeout rejects the form with "CAPTCHA verification failed. Please try again." and no account is made. If the secret key is missing at verification, `verify_turnstile()` fails closed.
4. Email and username are checked against existing accounts (case-insensitive); a duplicate rejects the form.
5. Evennia creates the account and the player is sent to the login page with a success message.

### Security

- Token validation requires the secret key, which is never exposed to the client.
- A token is single-use; it cannot be reused.
- The client address sent to Cloudflare is only the address Cloudflare saw: `CF-Connecting-IP`, set by the tunnel and unforgeable through it (#3398). With no such header the payload carries no `remoteip` at all, which Cloudflare allows. Neither `X-Forwarded-For` (the client's own claim; proxies append) nor `REMOTE_ADDR` is trusted: Evennia's webserver rewrites `REMOTE_ADDR` from that same leftmost claim behind an upstream proxy. `remoteip` is optional and can only make verification stricter, never looser, so it is not a security control.
- `get_client_ip()` reads the address with `world.client_address.from_request`, the same helper the website login door uses (#3734).
- A refused verification logs Cloudflare's `error-codes`, so a genuine "CAPTCHA verification failed" can be diagnosed from the server log; the Turnstile dashboard shows aggregate outcomes only.

### Verification endpoint

- Endpoint: `https://challenges.cloudflare.com/turnstile/v0/siteverify`
- Method: POST
- Data: `{secret, response, remoteip (optional)}`
- Response: `{success: true/false, error-codes: []}`

## Setup

### 1. Get Cloudflare Turnstile keys

1. Visit https://dash.cloudflare.com/ and log in (or create a free account).
2. Navigate to **Turnstile** in the left sidebar.
3. Click **Add Site**.
4. Configure the site:
   - **Site name**: Gelatinous Monster
   - **Domain**: `gel.monster` (or your domain)
   - **Widget Mode**: Managed (recommended)
5. Click **Add** and copy the keys:
   - **Site Key** (public, visible in HTML)
   - **Secret Key** (private, server-side only)

### 2. Configure settings

Set both keys, or neither.

**Option A: direct configuration (development only).** In `server/conf/settings.py`:
```python
TURNSTILE_SITE_KEY = "your-site-key-here"
TURNSTILE_SECRET_KEY = "your-secret-key-here"
```

**Option B: secret settings (production, recommended).** In `server/conf/secret_settings.py`:
```python
# Cloudflare Turnstile
TURNSTILE_SITE_KEY = "your-site-key-here"
TURNSTILE_SECRET_KEY = "your-secret-key-here"
```

**Option C: environment variables.** `server/conf/settings.py` does not read environment variables; setting them does nothing on its own. To use them, replace the two Turnstile lines in `server/conf/settings.py` with:
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

### 3. The `requests` package

Verification uses the `requests` library, imported by `web/website/views/accounts.py`. The repo has no `requirements.txt`; its `docker-compose.yml` names the stock Evennia container image, which must provide `requests`. Outside that image, install it:
```bash
pip install requests
```

### 4. Enable account registration

In `server/conf/settings.py`:
```python
NEW_ACCOUNT_REGISTRATION_ENABLED = True
```

### 5. Reload

Run `@reload` from inside the game (see `AGENTS.md`, "Reload from inside the game"; a reload needs the owner's go). The keys are read by the Server, so a Portal restart is not needed.

### Before going live

- Keys in `secret_settings.py` (never committed to git).
- Production keys, not test keys.
- HTTPS enabled (required for Turnstile).
- The correct domain set in the Cloudflare dashboard.
- The registration flow tested on the production domain.
- Cloudflare Turnstile analytics monitored for bot attempts.

## Testing

### Registration flow

1. Go to `/auth/register`, or click "Create Account" on the login page.
2. Fill out the form (username, email, password).
3. Complete the Turnstile check (usually automatic).
4. Submit the form.
5. The browser lands on the login page with a success message.

### Cloudflare test keys

Cloudflare provides test keys that always give the same result, for development and testing without a Cloudflare account.

**Always passes:**
- Site Key: `1x00000000000000000000AA`
- Secret Key: `1x0000000000000000000000000000000AA`

**Always fails:**
- Site Key: `2x00000000000000000000AB`
- Secret Key: `2x0000000000000000000000000000000AA`

**Always blocks:**
- Site Key: `3x00000000000000000000FF`
- Secret Key: `3x0000000000000000000000000000000AA`

The three test secrets answer `siteverify` with `metadata.result_with_testing_key` present: `success: true`, `invalid-input-response` and `timeout-or-duplicate` respectively. The `FF` suffix belongs only to the **site** key. A secret ending in `FF` (`3x0000000000000000000000000000000FF`) is not a Cloudflare test key: it answers `{"success": false, "error-codes": ["invalid-input-secret"]}`, which makes working secret-key wiring look broken.

## Customization

### Widget appearance

The widget takes `data-theme` (`light`, `dark`, `auto`; this site uses `dark`), `data-size` (`normal`, `compact`) and `data-language` (a language code, e.g. `en`) on the `cf-turnstile` div.

### Error messages

The message shown when verification fails is set in `TurnstileAccountCreateView.form_valid` (`web/website/views/accounts.py`): "CAPTCHA verification failed. Please try again." The alert shown when someone submits before the widget finishes is in `web/templates/website/registration/register.html`. The `'required'` message on the form field in `web/website/forms.py` is never shown, because the field is optional.

## Troubleshooting

For any problem: check the Cloudflare Turnstile documentation (Resources below), review the server log, test with the Cloudflare test keys, and make sure the `requests` library is installed.

### "CAPTCHA verification failed"

**Causes:** an invalid or expired token; an incorrect secret key; a network error reaching Cloudflare; a token already used.

**What to check:**
- `TURNSTILE_SECRET_KEY` in settings.
- That the server can reach `challenges.cloudflare.com`.
- The server log: `Turnstile verification refused: error-codes=[…]` means Cloudflare said no, with its reason; `Turnstile verification error: …` means Cloudflare could not be reached or answered badly, and the registration is refused.
- Refresh the page and verify again.
- Test with the Cloudflare test keys.
- That the `requests` library is installed.

### Widget not appearing

**Causes:** one or both keys missing (the widget renders only when both are set; the server log names the missing one); an incorrect site key; JavaScript blocked; an ad blocker blocking Cloudflare; the Turnstile script tag missing.

**What to check:**
- That the template context has `turnstile_enabled` true and a non-empty `turnstile_site_key`.
- The browser console for errors.
- Temporarily disable ad blockers.
- That `<script src="https://challenges.cloudflare.com/turnstile/v0/api.js">` is loaded.

### Server log says "Turnstile is half-configured"

Only one of the two keys is set, so the CAPTCHA is off. Set both `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` in `server/conf/secret_settings.py`, or neither.

### Form submits without verification

The server checks the token only when both keys are set. With both empty, or only one set, registration has no CAPTCHA (see "The on-switch" above). Set both keys.

## Unbuilt

Potential improvements. 📋 UNBUILT (not decided): none of these is in the code, and none has a ruling or an issue.
- Add Turnstile to the password reset form.
- Add Turnstile to contact forms.
- Implement retry logic for network failures.
- Add a custom error page for verification failures.
- Track verification statistics in the admin panel.
- Add rate limiting per IP address.
- Implement invisible Turnstile mode for seamless UX.

## Resources

- **Cloudflare Turnstile Docs**: https://developers.cloudflare.com/turnstile/
- **Get Turnstile Keys**: https://dash.cloudflare.com/?to=/:account/turnstile
- **Turnstile API Reference**: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- **Widget Parameters**: https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/
