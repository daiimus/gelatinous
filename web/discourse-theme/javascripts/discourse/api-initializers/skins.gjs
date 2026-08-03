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
const PALETTES = {
  atlas: "Domino's Gambit",
  terminal: "Terminal",
  stray: "Stray",
};

const SITE_ORIGIN = "https://gel.monster";

function currentSkin() {
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

  async function applySkin(skin) {
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

      // Preload before swapping, or the page renders unstyled for a beat
      // while the new sheet is fetched.
      await new Promise((resolve) => {
        const pre = document.createElement("link");
        pre.rel = "preload";
        pre.as = "style";
        pre.href = new_href;
        pre.onload = pre.onerror = resolve;
        document.head.appendChild(pre);
      });

      link.href = new_href;
      link.dataset.schemeId = id;
      applied = id;
    } catch (e) {
      // The cookie is already set, so a reload lands on the right palette.
    }
  }

  applySkin(currentSkin());

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
  });
});
