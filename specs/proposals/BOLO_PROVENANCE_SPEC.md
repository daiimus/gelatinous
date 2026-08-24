# BOLO Provenance — how a description travels

**Status:** ✅ BUILT 2026-08-23 (#2247) — provenance, enforcement,
and the machine-witness path. Clothing remains unbuilt (§4.4).
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
It teleports from the crime into the robot's sensor loop — no witness
statement, no radio call, no relay.

Which raises the question that started this: *how would anyone
communicate a uid over the radio?* Nobody says a hex digest out loud. A
witness can't. Dispatch can't relay it. A player certainly can't shout
it on 911.

So the fidelity of a BOLO is currently independent of how it was
learned, and everything gets the highest fidelity there is.

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

## 4. What changes

1. **A BOLO gains provenance** — `{"via": "machine"|"witness"|"radio",
   "source": ...}` — and `build_bolo` requires it rather than defaulting.
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

## 5. Consequences worth wanting

* **Disguise gets teeth from the other side.** A uid is a *presentation*
  hash, so changing clothes already breaks it. Under provenance, only
  machines hold that against you — a human witness's description
  degrades naturally, which is how it should feel.
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
