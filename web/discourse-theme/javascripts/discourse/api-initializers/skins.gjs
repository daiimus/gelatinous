/*
 * Skins — the forum half of the brand-mark Easter egg.
 *
 * gel.monster writes a `gel_skin` cookie scoped to `.gel.monster`. This reads
 * it and translates it into Discourse's OWN palette machinery rather than
 * fighting the palette with CSS overrides: Discourse compiles dozens of
 * derived shades (--primary-low, --primary-50 …) from a palette at build
 * time, so hand-overriding a few variables leaves the forum wearing two
 * palettes at once. Swapping the compiled stylesheet is the only coherent
 * move, and it is what core's own bundled Horizon theme does.
 *
 * We deliberately do NOT write Discourse's `color_scheme_id` cookie from
 * gel.monster. Core writes that cookie host-only; a second one scoped to the
 * parent domain would collide, and both Rack and Discourse's own cookie
 * reader take whichever appears first in the header — which browsers order by
 * creation time, so the older cookie can silently win. Our own cookie, our
 * own name, translated here on the forum's own origin. No collision.
 *
 * BY NAME, NOT BY ID: about.json ships the palettes, so a reinstall can
 * renumber them. Names are the stable handle.
 *
 * Palettes must stay marked "user selectable" (Admin → Customize → Colors) or
 * the server ignores the cookie on the next load — see
 * `application_helper.rb#user_scheme_id`, which gates on
 * `ColorScheme.exists?(id:, user_selectable: true)`.
 */

import { apiInitializer } from "discourse/lib/api";
import { ajax } from "discourse/lib/ajax";
import {
  listColorSchemes,
  updateColorSchemeCookie,
} from "discourse/lib/color-scheme-picker";

/** Skin slug (owned by the site) → palette name (owned by about.json). */
// GENERATED SKINS (build_skins.py) BEGIN
const PALETTES = {
  atlas: "Domino's Gambit",
  terminal: "Terminal",
  stray: "Stray",
  dub: "Dub",
  prism: "Prism",
};
// GENERATED SKINS (build_skins.py) END

const SITE_ORIGIN = "https://gel.monster";

function currentSkin() {
  // Test hook: Safari private mode can deny script cookie access that the
  // HTTP layer was granted, and no harness can produce that state on
  // demand — this flag can. Inert unless deliberately set.
  try {
    if (localStorage.getItem("gel-skin-test-blind")) {
      return null;
    }
  } catch (e) {
    // storage unavailable: fall through to the real read
  }
  const hit = document.cookie.match(/(?:^|;\s*)gel_skin=([^;]+)/);
  return hit ? decodeURIComponent(hit[1]) : null;
}

export default apiInitializer("1.8.0", (api) => {
  const site = api.container.lookup("service:site");

  // Every skin is dark, so no dark palette is configured and Discourse emits
  // exactly one stylesheet link. If a light skin is ever added, this needs a
  // `dark_scheme_id` counterpart and a second link to swap.
  const sheet = () => document.querySelector("link.light-scheme");

  // Tracked here rather than read back off the element: the swap below is the
  // only thing that updates data-scheme-id, and trusting a stale attribute
  // would make switching back to the server-rendered palette a no-op.
  let applied = Number(sheet()?.dataset.schemeId) || null;

  function paletteId(skin) {
    const name = PALETTES[skin];
    if (!name) {
      return null;
    }
    const schemes = listColorSchemes(site) || [];
    return schemes.find((s) => s.name === name)?.id ?? null;
  }

  function pushToHeader(skin) {
    // The header iframe cannot always read the cookie itself: Safari private
    // mode denies a cross-origin iframe document.cookie access that this
    // top-level, first-party page is granted. We know the skin; tell it.
    // Runs on every application, INCLUDING the already-applied no-op path,
    // because the header can disagree even when the body already matches.
    const frame = document.getElementById("gel-django-header-iframe");
    frame?.contentWindow?.postMessage({ type: "gel-skin", skin }, SITE_ORIGIN);
  }

  // The skin the body is wearing, BY NAME, independent of the cookie — which
  // in Safari private mode may be unreadable or live in a different jar than
  // the one the header writes. This is what lets a reloaded header be re-armed
  // even when no cookie can be read at all.
  let wearing = null;
  // THE SEED: the server may have rendered a non-default palette from a
  // cookie the script cannot read (Safari private mode). The body knows
  // what it is wearing — data-scheme-id — it just never told itself.
  // Without this, `wearing` stays null, the header's honest "atlas" report
  // is (correctly) never adopted, and nothing ever pushes the real skin
  // down: the header stays default forever against a skinned body.
  for (const skin in PALETTES) {
    if (skin !== "atlas" && paletteId(skin) === applied) {
      wearing = skin;
      break;
    }
  }

  async function applySkin(skin) {
    if (skin in PALETTES) {
      wearing = skin;
      pushToHeader(skin);
    }
    const id = paletteId(skin);
    // An unknown skin, or a palette that has been deleted, leaves the forum
    // wearing whatever it already had. Failing to the default is correct: a
    // cosmetic Easter egg must never be why the forum looks broken.
    if (!id || id === applied) {
      return;
    }

    // Persist first, because this is the part that actually matters. The
    // server reads this cookie ahead of the user's own stored preference, so
    // the next page load is rendered in the right palette with no flash — and
    // it is part of the anonymous cache key, so logged-out visitors are
    // cached per palette rather than served someone else's.
    updateColorSchemeCookie(id);

    // Then repaint the page we are standing on.
    try {
      const { new_href } = await ajax(`/color-scheme-stylesheet/${id}.json`);
      const link = sheet();
      if (!new_href || !link) {
        return;
      }

      // Swap by inserting a real stylesheet and waiting for ITS load, not a
      // rel=preload probe: Safari does not reliably fire load/error on
      // preload links, and awaiting one hung this function forever — the
      // fetch succeeded, the swap never ran, and every retry piled into the
      // same silent hang (observed live: thirty fetches, zero swaps). A real
      // stylesheet's load event is dependable everywhere, and the timeout
      // guarantees convergence even if no event ever fires — the cost is a
      // one-frame flash in a case that otherwise never converges at all.
      const next = document.createElement("link");
      next.rel = "stylesheet";
      next.className = "light-scheme";
      next.dataset.schemeId = id;
      await new Promise((resolve) => {
        next.onload = next.onerror = resolve;
        setTimeout(resolve, 3000);
        next.href = new_href;
        link.insertAdjacentElement("afterend", next);
      });
      link.remove();
      applied = id;
    } catch (e) {
      // Observed live: Cloudflare can CHALLENGE the swap fetch — the page
      // navigation passed, but an in-page fetch from a session without
      // challenge clearance gets a 403 HTML page, which then fails JSON
      // parsing. No amount of client-side retrying beats the edge, and each
      // retry piled into the same wall. But the cookie was already written
      // before the fetch, so a full load renders the right palette
      // server-side with no fetch involved — the same fallback core's
      // Horizon theme uses. Guarded per palette so a still-failing reload
      // cannot loop.
      console.warn("[gel-skin] stylesheet swap failed; falling back to a reload", e);
      applied = null;
      try {
        const key = "gel-skin-reloaded-" + id;
        if (!sessionStorage.getItem(key)) {
          sessionStorage.setItem(key, "1");
          window.location.reload();
        }
      } catch (storageErr) {
        // No sessionStorage (private-mode quirks): swallow — the next
        // navigation still lands on the right palette via the cookie.
      }
    }
  }

  // Read-only state handle so a harness can see in: this saga's lesson is
  // that inference dies where instrumentation lives.
  window.__gelSkinState = () => ({ wearing, applied, ours: currentSkin() });

  applySkin(currentSkin());

  // Ask the header what it is wearing. We boot after the iframe's tiny
  // document, so its listener exists and the reply cannot be lost — this is
  // what recovers a skin clicked before Ember was listening, whose gel-skin
  // message died against an unregistered listener. If the iframe is not in
  // the DOM yet (we booted first), its load-time height message carries the
  // skin instead: both orderings are covered without retries.
  document.getElementById("gel-django-header-iframe")
    ?.contentWindow?.postMessage({ type: "gel-skin-query" }, SITE_ORIGIN);

  // The brand mark lives in an iframe served by gel.monster, so a click on it
  // happens cross-origin and cannot reach us any other way. This rides the
  // same postMessage channel the header already uses to report its height.
  window.addEventListener("message", (event) => {
    if (event.origin !== SITE_ORIGIN) {
      return;
    }
    if (event.data?.type === "gel-skin") {
      applySkin(event.data.skin);
    }
    // The header posts its height on load, on resize, and on every DOM
    // mutation — a frequent, unlosable signal, and it now carries the skin
    // the header is actually wearing. Two jars may be in play: in Safari
    // private mode the iframe's cookie jar is PARTITIONED from ours, so a
    // skin clicked in the header lands in a jar we can never read, and the
    // click's own gel-skin message can race Ember boot and be lost.
    //
    // Arbitration: our own cookie wins when we can read one (normal mode,
    // where both jars are the same and the server rendered from it) — answer
    // by pushing it down, which also re-arms a header that reloaded. When
    // our jar says nothing, the header's report is the only record of the
    // user's intent: adopt it.
    if (event.data?.type === "gel-header-height") {
      const ours = currentSkin();
      // What we would tell the header: our own cookie when readable, else
      // what the body is wearing (message-adopted or seeded from the
      // server render).
      const toPush = ours in PALETTES ? ours : wearing;
      if (toPush && event.data.skin !== toPush) {
        // Push ONLY when the header reports something different. An
        // unconditional push here closed a loop: push -> the header
        // applies -> its data-skin observer fires -> it reports height
        // again -> push. The inequality is what breaks the cycle, and it
        // still re-arms a header that reloaded into the default.
        pushToHeader(toPush);
      } else if (!toPush && event.data.skin in PALETTES && event.data.skin !== "atlas") {
        // We know nothing; the header's report is the only record of the
        // user's intent. The atlas exclusion keeps a default-stamped header
        // from ever overriding anything — atlas is what both sides wear
        // when nobody has chosen, so adopting it is never necessary.
        applySkin(event.data.skin);
      }
    }
  });

  // Belt and braces for the mid-load toggle. In principle the two paths above
  // cover every ordering — a toggle before boot is caught by the initial
  // cookie read, one after boot by the listener — and a timing sweep (50ms to
  // 2.5s) confirms it in Chromium. But a stuck palette was still observed
  // once in Safari and could not be reproduced in the harness, so: re-read
  // the cookie on every SPA navigation. If nothing was missed this is a
  // cheap no-op (applySkin bails when the id already matches); if anything
  // ever is, it converges one navigation later instead of never.
  api.onPageChange(() => applySkin(currentSkin()));
});
