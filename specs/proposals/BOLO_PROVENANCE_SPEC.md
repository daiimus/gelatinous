# BOLO Provenance — how a description travels

A BOLO is what a responding unit matches people against. Every BOLO
carries how it was learned, and only a machine channel may carry a uid —
a positive identification. A description passed on by a person or over
the radio can only ever give a weak match (#2247).

Code: `world/director/security.py` (`build_bolo`, `match_bolo`,
`_worn_signature`), `world/director/crime.py`, `world/director/calls.py`
(`describe_suspect`, `_garments_named`), `world/director/radio_report.py`
(`consider_radio_report`).

---

## 1. Why a uid cannot travel by voice

A uid is a hash of a person's presentation. Nobody says a hex digest out
loud. A witness can't. Dispatch can't relay it. A player certainly can't
shout it on 911. So a BOLO's worth must depend on how it was learned.

## 2. The principle

**A BOLO carries how it was learned, and only some channels may carry a
uid.**

The world implies three channels, and they map onto the confidences
`match_bolo` returns:

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

## 3. The BOLO record

`build_bolo` and `describe_suspect` both produce:

```python
{"uid": str | None, "height": str | None, "build": str | None,
 "worn": set of (colour, garment), "via": "machine" | "witness" | "radio",
 "by": the observer's key or None}
```

* **`uid`** is a **16-character hex digest** of the presentation
  signature. It is set only when `via` is `"machine"`.
* **`via`** is the channel: `"machine"`, `"witness"` or `"radio"`.
* **`by`** is the observer's `key`, or None. It is not the ground truth:
  `event.source` stays reserved for the ground truth `is_the_right_person`
  checks against.
* **`worn`** is a set of (colour, garment) pairs — what the person was
  wearing.

## 4. Who builds a BOLO, and on which channel

* **`build_bolo`** takes `via` as a keyword-only argument with a
  fail-safe default of `"witness"`, the channel that carries no uid. A
  producer that forgets to declare a channel gets the no-uid channel
  rather than an error, and never hands out a positive identification. A
  channel name that is not one of the three is recorded as `"radio"`, the
  weakest, and carries no uid. `build_bolo` reads `worn` off the body's
  worn items (`_worn_signature` in `world/director/security.py`).
* **`crime.py` declares its channel.** A crime witnessed by a security
  unit is `machine`; one witnessed by a person is `witness`: it carries
  no uid, only the perpetrator's exact height, build and clothing (an
  accurate silhouette). Both `build_bolo` calls in
  `world/director/crime.py` pass `via=` explicitly, so no caller relies on
  the default.
* **`world/director/calls.py::describe_suspect`** (#2246) reads a
  caller's ordinary words into a silhouette and **never** sets a uid. It
  builds the same shape with `via="radio"`. It reads clothing out of the
  caller's words (`_garments_named` in `world/director/calls.py`), so
  "black trenchcoat" becomes ("black", "trenchcoat").

## 5. How `match_bolo` matches

1. **`high` only for `machine`.** `match_bolo` returns `high` — a
   positive identification — only when `via == "machine"` and the uid
   matches. A uid arriving by any other route (a bug or a forgery) is
   ignored, and the BOLO is matched on its silhouette and clothing alone.
2. **Both axes, when the BOLO has both.** When a BOLO carries both height
   and build, `match_bolo` decides on those two alone and does not look at
   clothing: both must agree for `low`.
3. **One axis plus clothing.** When the BOLO carries only one of height
   and build, that axis plus a matching worn garment returns `low` — "a
   svelte lady in a black trenchcoat" matches.
4. **Anything less matches nobody.** A half description with no clothing
   ("a svelte lady") matches nobody — the units are simply hoping to catch
   the person at it. A description with clothing but no height or build
   ("a guy in a black trenchcoat") matches nobody.

Owner ruling 2026-08-23, and correct: vague hearsay should not put a
stranger under aim. The ruling was given when `match_bolo` required both
axes for every `low` match; #2253 relaxed that to rule 3 above. The bare
"a svelte lady" still matches nobody, so the ruling holds.

## 6. Consequences worth wanting

* **Disguise gets teeth from the other side.** A uid is a *presentation*
  hash. Only *disguise-essential* garments shift it — `get_apparent_uid`
  hashes `get_essential_item_type_ids`, which selects worn items flagged
  `disguise_essential=True`: masks, hoods, wigs, contacts, sunglasses.
  Changing a presentation override (height, build or keyword) also
  shifts it. Swapping an ordinary coat does NOT break the hash; it is the
  `worn` field that a coat change defeats, so the machine hash is the
  more durable of the two. Under provenance, only machines hold the hash
  against you — a human witness's description degrades naturally, which
  is how it should feel.
* **Forgery has a target.** If a uid can only travel machine-to-machine,
  then injecting one is a decking objective: put your enemy's
  presentation in the net and the whole security force sees them
  everywhere. 📋 UNBUILT (no issue): decking does not exist yet.
* **Bad calls stop convicting people.** A vague radio report cannot
  produce a positive ID, which is the difference between "security
  investigates" and "security detains the wrong person".

## 7. Deliberately out of scope

* The **case system / hackable records**. Provenance is a prerequisite —
  a record worth hacking has to say where it came from — but the
  database is its own build.
* **Investigation** (canvassing, asking witnesses, following up). Noted
  by the owner as later work.
