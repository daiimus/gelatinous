# Trust & Consent Spec

> **Status: 🚧 DESIGN IN PROGRESS — NOT FOR IMPLEMENTATION.** Captures a
> decided core stance plus the open questions. The user has flagged this as
> **"SUPER IMPORTANT"** and explicitly wants **much further discussion before
> any implementation**. Do not build from this doc yet. It exists so the
> decisions so far survive, and so new third-party commands have a clean
> integration point to defer to rather than inventing one-off gates.

## 0 · Purpose

Many in-game actions are **third-party** — one character acting *on* another:
surgery, harvesting organs, installing/removing augments, dragging a body,
dressing/undressing, frisking, injecting, restraining. Without a consent layer,
every such command has to decide ad-hoc whether the target can refuse. This
spec defines the rule for when consent is required and how it's granted, so the
behaviour is consistent and not painted into a corner.

## 1 · Decided core stance (2026-06-20)

**Consent is required only when the target can resist** — i.e. an **awake /
conscious** character must agree (or be subdued first) before an invasive
third-party action lands. **Unconscious, restrained, or dead targets can be
acted on freely** — no consent needed.

- Rationale: fits the deliberately dangerous, squishy world. You can do anything
  to someone you've **subdued**; you can't grief someone who's **awake** and
  unwilling.
- This is **not** "always require consent" (that kills the danger) and **not**
  "never" (that's open griefing).
- It **generalizes the existing workaround.** Today, invasive commands gate on
  unconscious/dead state. That gate *is* the free-action path; the consent layer
  is simply the missing **conscious-target** path — a way for an awake character
  to *grant* permission (and to resist/refuse otherwise).

## 2 · Current mechanism (what exists today)

Invasive commands (operate/harvest/install, dress/undress, etc.) gate to
**unconscious / dead / severed** targets. A conscious target generally can't be
acted on. This is the accepted interim per [[project-gelatinous-trust-consent]]:
new third-party commands either keep that gate or leave a clean comment marking
the conscious-target path as deferred to this system. **No hard-coded
"reject on conscious target" logic** that the consent layer would have to unpick.

## 3 · The gap to build (later)

The conscious-target permission path. At minimum:
- A way for an awake character to **grant** another permission to perform
  (some set of) invasive actions on them.
- A way to **resist / refuse** — and what happens when an unwilling awake target
  is targeted (hard block? or an opposed/grapple path to *subdue* them first,
  after which the free-action path applies?).

## 4 · Open questions (the "discuss much further" list)

These are deliberately unresolved — they need a design conversation before any
build:

1. **Granularity.** Per-action, per-person, or blanket? "I trust Bob to operate
   on me" vs "I trust Bob with anything" vs "anyone may treat me." Is there a
   trust *level* or just a yes/no per (person, action-class)?
2. **Grant/revoke UX.** What command(s)? (`allow <who> [to <action>]`,
   `trust`/`distrust`, `consent`?) Time-limited or until revoked? Does it
   survive logout / death / sleeve change?
3. **Resistance model.** If an awake unwilling target is targeted, does the
   action simply **fail**, or does it open an **opposed/grapple** path (you can
   try to *subdue* them, and once subdued the existing free-action path applies)?
   How does this relate to the existing grapple/restrain systems?
4. **Action taxonomy.** Exactly which commands are gated — and are there tiers
   (e.g. "treat me" is lower-stakes than "cut out my kidney")? Candidate set:
   surgery (incise/operate/install/harvest), drag/move-body, dress/undress,
   frisk/loot, inject/apply, restrain. Where do borderline ones (e.g. handing
   someone an item, bandaging a willing ally) sit?
5. **Consciousness thresholds.** Is "can resist" strictly the unconscious gate,
   or is a groggy/restrained-but-awake target somewhere in between? Does the
   `consciousness` runtime value pick the line?
6. **NPCs / mobs.** Do NPCs participate (AI-granted consent / refusal), or are
   they free-action? Faction/relationship implications.
7. **Visibility / UX.** How does the actor learn they need consent? How does the
   target learn they're being asked / acted upon? Any prompt/confirm flow, or
   purely a pre-granted standing permission?
8. **Trust & the broader social loop.** Does consent tie into the planned
   gig/favor/rep system (a RipperDoc you've paid has standing consent; betrayal
   has rep cost)? See [[project-gelatinous-growth-direction]].
9. **Abuse / edge cases.** Consent extracted under duress; revoking mid-
   procedure; consent to one persona vs the person behind a disguise (ties to
   the identity system); severed parts and corpses (already free — confirm).

## 5 · Cross-references

- [[project-gelatinous-trust-consent]] — the standing project note + decided stance.
- Identity/recognition system — consent is granted to a *recognised identity*;
  disguises complicate "who did I consent to."
- Grapple / restrain (`world/combat/grappling.py`) — the likely "subdue first"
  substrate for the resistance model (§4.3).
- `world/medical` operate/harvest/install flows — the primary consumers that
  currently gate on unconscious/dead.
