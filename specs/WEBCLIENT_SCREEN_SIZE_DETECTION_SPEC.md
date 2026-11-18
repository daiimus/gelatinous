# Webclient Screen Size Detection Specification

The webclient measures how many characters fit in its output pane and reports
that width and height to the server, the way a telnet client does with NAWS
(Negotiate About Window Size, RFC 1073). Server code that formats to the
screen reads the reported width from the session. The logic lives in
`web/static/webclient/js/gel.js` (`measureScreen()`, `sendScreenSize()`,
`onResize()`). It is not a plugin: this repo replaced Evennia's GoldenLayout
webclient with its own client, one bare script with no plugin architecture,
no GoldenLayout, no jQuery and no font picker.

---

## When the client reports

- **On connect.** `ws.onopen` calls `sendScreenSize()`.
- **After a resize.** `onResize()` waits until 250 ms after the last resize
  (`RESIZE_DEBOUNCE_MS = 250`, an inline timer) and then calls
  `sendScreenSize()`. Resize events fire continuously while a window is
  dragged; the debounce means one report after the user stops, not one per
  event.
- `onResize()` is bound to `window.visualViewport` when the browser has that
  API, and to `window` only otherwise. A `visualViewport` resize fires on
  device rotation and when the virtual keyboard shows or hides, so both are
  re-measured without an `orientationchange` listener.
- **There is no font-change and no layout-change trigger.** A font change
  takes effect at the next resize or reconnect.

The character cell is re-measured on every report; nothing is cached.

## How the client measures (`measureScreen()`)

1. **The character cell.** A hidden probe span holding `"MMMMMMMMMM"` (ten
   characters) is built once. On every call it takes the font family, font
   size and line height of `#output-inner` (#3396), so a font change at the
   600px breakpoint is picked up at the next measurement.
2. The cell width is the probe's `getBoundingClientRect()` width divided by
   10, and the cell height is the probe's height. Both are fractional. Reason:
   whole-pixel `offsetWidth` under-measured a 13px cell by enough to report a
   phone one column and one row too wide.
3. If the probe measures zero, an 8 × 16 px cell is assumed.
4. **The usable area** is the client area of `#output` minus its four
   computed paddings, read on every call (#3397). Reason: the phone rule pads
   `#output` `6px 8px`, less than the desktop, so fixed desktop figures
   understated a phone's screen by up to a cell.
5. Columns are the usable width ÷ cell width, rounded down, never below 40.
   Rows are the usable height ÷ cell height, rounded down, never below 10.
   There is no ceiling.

`gel.js` does no logging (it contains no `console.` call) and assigns nothing
to `window`, so there is no console-callable measuring function.

## What goes over the wire

- `sendScreenSize()` sends `{screenwidth, screenheight}` as the GMCP package
  `Client.Options`, in a websocket TEXT frame (`sendGMCP()` in `gel.js`).
- `server/conf/gmcp_websocket.py` translates `Client.Options` into Evennia's
  `client_options` inputfunc (`evennia/server/inputfuncs.py`).
- Evennia stores the values in `session.protocol_flags` as `SCREENWIDTH` and
  `SCREENHEIGHT`, each keyed by window ID:

  ```python
  session.protocol_flags["SCREENWIDTH"] = {0: 120}   # window 0 is 120 characters wide
  session.protocol_flags["SCREENHEIGHT"] = {0: 40}   # window 0 is 40 lines tall
  ```

  Window ID 0 is the main window. Evennia supports several windows per
  session; the webclient uses one.
- Evennia reads them back through `ServerSession.get_client_size()`
  (`evennia/server/serversession.py`) and `Command.client_width()`.
- Telnet clients reach the same inputfunc through Evennia's NAWS handler
  (`evennia/server/portal/naws.py`).

## Defaults

- Evennia 6.1.0 ships `CLIENT_DEFAULT_WIDTH = 78` and
  `CLIENT_DEFAULT_HEIGHT = 45` (`evennia/settings_default.py`). This repo does
  not override either.
- The server uses 78 only if no size was ever reported.

## Telnet and webclient compared

| Feature | Telnet (NAWS) | Webclient |
|---|---|---|
| **Width detection** | Automatic | Automatic |
| **Height detection** | Automatic | Automatic |
| **Window resize** | Updates on resize | Updates 250 ms after the last resize |
| **Font changes** | Terminal handles | No font-change event; picked up at the next resize or reconnect |
| **Protocol** | Telnet NAWS bytes | GMCP `Client.Options`, translated to the `client_options` inputfunc |

## The client's font

- `web/static/webclient/css/webclient.css` sets
  `--font-mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
  at `--font-size: 14px` and `--line-height: 1.4`.
- The only variation is `@media (max-width: 600px)`, which drops the font
  size to 13px. There is no user-selectable family and no size range, so
  crossing that breakpoint is the one font change this client has, and
  `measureScreen()` re-measures it on the next resize.
- The font is monospace, so every character has the same width and one
  measured cell stands for all of them. Columns, tables and ASCII art line up.

## Who uses the reported size

There are four readers of `SCREENWIDTH` in this repo:

| Reader | What it formats |
|---|---|
| `get_terminal_width()` in `world/utils/boxtable.py`, reached only from `commands/CmdArmor.py` | the `armor` table |
| `_get_terminal_width()` in `typeclasses/death_progression.py` | the death sequence |
| `_get_terminal_width()` in `typeclasses/curtain_of_death.py` | the death curtain |
| `_get_terminal_width()` in `commands/CmdCharacter.py` | the character sheet |

- **All four clamp with `max(60, detected_width)`.** Anything a client
  reports below 60 columns is discarded. The client floors at 40 columns, so
  a phone that reports 40–59 columns still gets output 60 wide.
- **Combat.** No file under `world/combat/` reads screen width. Combat
  messages are never wrapped or boxed to a width: they are emitted verbatim
  from the per-weapon tables in `world/combat/messages/`. There is no
  width-aware combat status display. Combat does drive the most visible
  consumer: `_handle_kill()` in `world/combat/attack.py` calls
  `show_death_curtain()`, and `typeclasses/curtain_of_death.py` scales the
  curtain to the reported width. The curtain is sent only to the character
  who died, at that character's reported width.
- **Height.** Nothing in this repo's own code reads `SCREENHEIGHT`. The client
  sends it and Evennia stores it, but only Evennia's own code can use it.

## Checking it in play

Per the house rule, these must be played in the live game, not asserted from
a helper.

- **What the client sent.** `gel.js` never logs. Watch the outgoing
  `Client.Options` GMCP frame in the browser DevTools, **Network → WS**
  messages pane.
- **What the server stored.** Inside the game container (not over SSH), in
  `evennia shell`:

  ```python
  from evennia.server.sessionhandler import SESSIONS
  session = SESSIONS.get()[0]  # First session
  width, height = session.get_client_size()
  print(f"Width: {width}, Height: {height}")
  ```

  Width and height match the last outgoing `Client.Options` frame.
- **Accuracy.** Measure the `#output` width in DevTools and compute
  `(width - padding) / char_width`. The reported width is within ±2
  characters of it. A reasonable cell is roughly 7–12px wide and 14–20px
  tall.
- **Resize and debounce.** Resize the window significantly (for example to
  half width), wait 350 ms (the 250 ms debounce plus a buffer), and check that
  one new frame was sent, not a stream during the drag. Rapidly resizing
  several times over 2 seconds sends 1–2 frames, not 10+.
- **Font change.** The only one available is crossing the 600px breakpoint;
  the next resize re-measures it.
- **Memory.** Take a heap snapshot, resize the window 20 times, force garbage
  collection, take another: no significant growth (< 1MB).
- **Consumers.** Be killed in combat and watch the curtain fill your own
  window. The other two observable consumers are `armor` and the character
  sheet. All clamp at 60, so nothing can be tested below 60 columns.
- **Browsers.** Chrome, Firefox, Safari and Edge, plus mobile on iOS and
  Android: width accuracy, height accuracy, resize and font change.

---

## Unbuilt

### Logging and error handling — 📋 UNBUILT (no issue)

Add logging and error handling to the measuring code. `gel.js` does no
logging.

### Manual override option — 📋 UNBUILT (no issue)

Let users set the dimensions by hand from an options dialog:

```
Options Dialog:
├── Screen Size Detection
│   ├── [x] Auto-detect screen size (recommended)
│   ├── Manual Width: [____] characters (disabled if auto)
│   └── Manual Height: [____] lines (disabled if auto)
```

- Users can override if automatic detection is inaccurate.
- Useful for accessibility tools.
- Lets users prefer a specific width (for example 80 characters).

### Visibility change optimisation — 📋 UNBUILT (no issue)

Pause measurement while the tab is hidden (`visibilitychange`), and resume
and re-measure when it is shown again. Reduces CPU use when the tab is in the
background and saves battery on mobile, while still updating when the user
returns.

### Telemetry — 📋 UNBUILT (no issue)

Optional telemetry to help tune defaults: screen width distribution, font
preferences, browser/OS combinations, mobile vs desktop ratio. Used to improve
default values, find common screen sizes for testing and optimise font
recommendations. Only if the user opts in, and all data anonymised.

---

## Not decided

- The client floors at 40 columns, but all four server readers clamp to at
  least 60, so a phone reporting 40–59 columns gets output 60 wide. Whether
  that is wanted is not decided.
- Are the manual override, the visibility change optimisation and the
  telemetry (see Unbuilt) wanted at all, or should they be deleted?

---

## Related documents

- `AGENTS.md` — agent operational reference: conventions, deploy workflow, file map
- `specs/COMBAT_SYSTEM.md` — combat system
- Evennia Documentation: [Web Client](https://www.evennia.com/docs/latest/Components/Webclient.html)
- Evennia Documentation: [Inputfuncs](https://www.evennia.com/docs/latest/Components/Inputfuncs.html)
- RFC 1073: [Telnet NAWS Protocol](https://www.ietf.org/rfc/rfc1073.txt)
