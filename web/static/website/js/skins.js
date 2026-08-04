/*
 * Skins — an Easter egg, cycled by clicking the brand mark.
 *
 * The choice rides in a cookie scoped to `.gel.monster` rather than
 * localStorage, because localStorage is per-origin and the forum is a
 * different origin. One cookie, four surfaces: site, atlas, webclient, and
 * the Discourse theme component that reads it on load.
 *
 * WHAT A SKIN MAY TOUCH: chrome only. On the webclient the game's own output
 * is inline-styled by ansi_up straight off the xterm-256 table, and it stays
 * that way — a room title is the same cyan here, in Mudlet, and over raw
 * telnet. The protocol is the source of truth for game text; skins dress the
 * room around it. Every skin is therefore DARK, so the fixed ANSI palette
 * stays legible on all of them.
 */
(function () {
  "use strict";

  var SKINS = ["atlas", "terminal", "stray"];
  var COOKIE = "gel_skin";
  var ROOT = document.documentElement;

  function readCookie() {
    var hit = document.cookie.match(/(?:^|;\s*)gel_skin=([^;]+)/);
    return hit ? decodeURIComponent(hit[1]) : null;
  }

  function writeCookie(skin) {
    // Domain-scoped so forum.gel.monster sees it too. A year, because an
    // Easter egg that forgets itself is just a flicker.
    var domain = location.hostname.endsWith("gel.monster") ? "; domain=.gel.monster" : "";
    document.cookie = "gel_skin=" + encodeURIComponent(skin) +
      "; path=/; max-age=31536000; samesite=lax" + domain;
  }

  function apply(skin) {
    if (SKINS.indexOf(skin) === -1) skin = SKINS[0];
    if (skin === SKINS[0]) ROOT.removeAttribute("data-skin");
    else ROOT.setAttribute("data-skin", skin);
  }

  function notifyForum(skin) {
    // On the forum this script runs inside the header iframe, which is a
    // different origin from the page around it. The cookie alone would only
    // take effect on the next load, so tell the theme component directly and
    // let it repaint immediately. Silent no-op everywhere else.
    if (window.parent === window) return;
    try {
      window.parent.postMessage(
        { type: "gel-skin", skin: skin }, "https://forum.gel.monster");
    } catch (e) {
      // Cross-origin refusal is not worth breaking the click over.
    }
  }

  // Apply only when the cookie is actually READABLE. Safari private mode can
  // deny a cross-origin iframe document.cookie access that the HTTP request
  // itself was granted — the header arrives server-stamped with the right
  // data-skin, and `apply(readCookie() || default)` was then REVERTING it to
  // the default on the strength of a cookie this document simply cannot see.
  // No cookie read → leave the server's stamp alone; on bare site pages there
  // is no stamp and no cookie, which is the default anyway.
  var initial = readCookie();
  if (initial) apply(initial);

  // And accept the skin FROM the forum page around us. The forum is top-level
  // and first-party, so its cookie read always works; when the component
  // applies a skin it pushes it down here, which keeps the header correct
  // even when this document's own cookie and storage access are dead.
  window.addEventListener("message", function (ev) {
    if (ev.origin !== "https://forum.gel.monster") return;
    var d = ev.data;
    if (d && d.type === "gel-skin" && SKINS.indexOf(d.skin) !== -1) {
      apply(d.skin);
    }
    // The forum asks what we are wearing when IT boots — it boots after us,
    // so this reply cannot race a listener that does not exist yet. This is
    // what recovers a click made before Ember was listening.
    if (d && d.type === "gel-skin-query") {
      notifyForum(ROOT.getAttribute("data-skin") || SKINS[0]);
    }
  });

  function cycle(ev) {
    // The mark sits inside the brand link; cycling must not navigate home.
    if (ev) { ev.preventDefault(); ev.stopPropagation(); }
    var current = readCookie() || SKINS[0];
    var next = SKINS[(SKINS.indexOf(current) + 1 + SKINS.length) % SKINS.length];
    writeCookie(next);
    apply(next);
    notifyForum(next);
    broadcast(next);
  }

  // ── cross-tab sync ─────────────────────────────────────────────────
  // A click only repaints the document it happens in, plus (via
  // notifyForum) the forum page around the header iframe. What nothing
  // covered: OTHER tabs. Toggling on the site homepage while a forum tab
  // sat open left that tab's header iframe wearing the old skin forever —
  // the iframe reads the cookie once at load, survives every SPA
  // navigation, and cookies fire no events. The forum BODY converges (the
  // component re-reads the cookie), so the header alone stayed stale:
  // a persistent seam that only appeared with two tabs in play.
  //
  // localStorage closes it. Every gel.monster document — site tabs AND
  // header iframes inside forum tabs — is the same origin, and a storage
  // write fires an event in all of them except the writer. Each follower
  // repaints, and a header iframe passes the change on to the forum page
  // around it through the postMessage channel that already exists.
  var SYNC_KEY = "gel_skin_sync";

  function broadcast(skin) {
    try {
      // Date.now suffix: the event only fires when the VALUE changes, and
      // toggling away and back again must still notify.
      localStorage.setItem(SYNC_KEY, skin + ":" + Date.now());
    } catch (e) {
      // Storage can be unavailable (private mode quotas); the cookie is
      // still written, so followers correct on their next load instead.
    }
  }

  window.addEventListener("storage", function (ev) {
    if (ev.key !== SYNC_KEY || !ev.newValue) return;
    var skin = ev.newValue.split(":")[0];
    if (SKINS.indexOf(skin) === -1) return;
    apply(skin);
    notifyForum(skin);
  });

  function wire() {
    var marks = document.querySelectorAll(".brand-mark");
    for (var i = 0; i < marks.length; i++) {
      marks[i].style.cursor = "pointer";
      marks[i].addEventListener("click", cycle);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
