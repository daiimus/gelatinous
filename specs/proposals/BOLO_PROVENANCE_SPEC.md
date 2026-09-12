# BOLO Provenance — how a description travels

**Status:** ✅ BUILT 2026-08-23 (#2247) — provenance, enforcement,
and the machine-witness path. Clothing remains unbuilt (§4.4).
**Correction 2026-09-11:** §4.4 clothing SHIPPED the same day, ~30 min
after this banner was written — PR #2253 ("What they were wearing",
commit `43539842`, also under #2247). All four §4 items are in the code.
**Depends on:** `world/director/security.py` (`build_bolo`, `match_bolo`),
`world/director/crime.py`, `world/director/calls.py`

---

## 1. The hole

A BOLO is what a responding unit matches people against:

```python
{"uid": <apparent presentation hash>, "height": ..., "build": ...}
```

`uid` is a **16-character hex digest** of the presentation signature.
`match_bolo` reads it as `high` confidence — a positive identification —
and falls back to `low` when only the height+build silhouette agrees.

Today there is exactly ONE producer: `crime.py` calls `build_bolo(perp)`
at crime time and drops it in the event payload, where the responder
reads it directly. **The identity never travels through any channel.**
(**Stale 2026-09-11:** three producers now — `crime.py` twice, with
`via="machine"` and `via="witness"`; `calls.py::describe_suspect`, which
builds the same shape with `via="radio"`; and `commands/CmdDispatch.py`,
which passes no channel and so takes the `"witness"` default.)
It teleports from the crime into the robot's sensor loop — no witness
statement, no radio call, no relay.

Which raises the question that started this: *how would anyone
communicate a uid over the radio?* Nobody says a hex digest out loud. A
witness can't. Dispatch can't relay it. A player certainly can't shout
it on 911.

So the fidelity of a BOLO is currently independent of how it was
learned, and everything gets the highest fidelity there is.

> **Stale 2026-09-11:** §1 is preserved as the problem statement, but it
> describes the PRE-#2247 code. `match_bolo` now gates `high` on
> `bolo.get("via") == "machine"` in `world/director/security.py`, so
> fidelity does depend on how the BOLO was learned. Read §1 in the past
> tense.

## 2. The principle

**A BOLO should carry how it was learned, and only some channels may
carry a uid.**

The world already implies three, and they map onto confidences that
`match_bolo` has always had:

| channel | what travels | best confidence |
|---|---|---|
| **machine → machine** | a presentation hash | `high` |
| **person, face to face** | detailed words: height, build, clothing, a face they'd know again | `low`, richly |
| **voice on the radio** | words, usually poor | `low` at best, often nothing |

The machine case is not a cheat — it is the setting. Security units have
comms organs and a shared record; a bot that *saw* someone and puts it
on the net is passing data, not describing a person. That is exactly the
kind of asymmetry between machines and people the colony is made of, and
it gives players a real reason to care whether the witness was a person
or a camera.

## 3. What already fits

`world/director/calls.py::describe_suspect` (built #2246) reads a
caller's ordinary words into a silhouette and **never** sets a uid.
That is this principle applied to one channel; it just isn't a rule yet.

`match_bolo` also requires BOTH axes for a `low` match, so a half
description ("a svelte lady") matches nobody — the units are simply
hoping to catch the person at it. Owner ruling 2026-08-23, and correct:
vague hearsay should not put a stranger under aim.

**Amended 2026-09-11:** #2253 relaxed the both-axes rule. In `match_bolo`
today both axes are still required when the BOLO carries both, but ONE
axis plus a matching worn garment also returns `low` — "a svelte lady in
a black trenchcoat" matches. The bare "a svelte lady" above still matches
nobody, so the owner ruling holds; the stated rule no longer does.

## 4. What changes

1. **A BOLO gains provenance** — `{"via": "machine"|"witness"|"radio",
   "source": ...}` — and `build_bolo` requires it rather than defaulting.
   (**As shipped 2026-08-23:** the second key is `by` — the observer's
   `key` — not `"source"`; `event.source` stays reserved for the ground
   truth `is_the_right_person` checks against. And `via` is keyword-only
   with a fail-safe default of `"witness"`, not required: an undeclared
   producer gets the no-uid channel rather than an error.
   `commands/CmdDispatch.py` is the one caller relying on that default.)
2. **`match_bolo` refuses `high` unless `via == "machine"`.** A uid
   arriving by any other route is a bug or a forgery, and should be
   treated as one.
3. **`crime.py` declares its channel.** A crime witnessed by a security
   unit is `machine`; one witnessed by a person is `witness` and must
   degrade to words before it reaches anybody else.
4. **Clothing enters the vocabulary.** ✅ NOT DONE. "A black trenchcoat"
   is the most useful thing a caller says and there is still nowhere to
   put it — the BOLO record has no garment field and `match_bolo`
   cannot compare worn items. This is the remaining half of the spec.

   **Stale 2026-09-11 — this shipped.** PR #2253 (commit `43539842`,
   under #2247) added a `worn` key to the BOLO record plus
   `_worn_signature()` in `world/director/security.py` (colour+garment
   pairs off `get_worn_items`); `_GARMENTS`, `_COLOURS` and
   `_garments_named()` in `world/director/calls.py` so a caller's
   "black trenchcoat" is parsed; and a `worn` branch in `match_bolo`.
   Exercised by `world/tests/test_bolo_provenance.py`.

## 5. Consequences worth wanting

* **Disguise gets teeth from the other side.** A uid is a *presentation*
  hash, so changing clothes already breaks it. Under provenance, only
  machines hold that against you — a human witness's description
  degrades naturally, which is how it should feel.
  (**Precision 2026-09-11:** only *disguise-essential* garments shift the
  uid — `get_apparent_uid` hashes `get_essential_item_type_ids`, which
  selects worn items flagged `disguise_essential=True`: masks, hoods,
  wigs, contacts, sunglasses. Swapping an ordinary coat does NOT break
  the hash. It is the `worn` field from #2253 that a coat change defeats,
  so the machine hash is the more durable of the two.)
* **Forgery has a target.** If a uid can only travel machine-to-machine,
  then injecting one is a decking objective: put your enemy's
  presentation in the net and the whole security force sees them
  everywhere.
* **Bad calls stop convicting people.** A vague radio report can no
  longer produce a positive ID, which is the difference between
  "security investigates" and "security detains the wrong person".

## 6. Deliberately out of scope

* The **case system / hackable records**. Provenance is a prerequisite —
  a record worth hacking has to say where it came from — but the
  database is its own build.
* **Investigation** (canvassing, asking witnesses, following up). Noted
  by the owner as later work.
