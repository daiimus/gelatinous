# Sleeping Sleeves — Logout Persistence Proposal

A proposal: when a player logs out, their body stays in the world, asleep,
instead of being stowed off-grid. The owner deferred it (owner call,
2026-08-04): do not build until the mechanisms for players to thrive under
the resulting hostility exist. This document keeps the design thesis and its
dependencies written down rather than only in conversation.

## Logout today

`Character.at_post_unpuppet` (`typeclasses/characters.py`) is the single
switch point. When the last session leaves, it does three things in order:

1. It shows the vacant-sleeve line ("the vacant sleeve is quietly gone") to
   the room, but only to observers who can see the character. A hidden
   character leaves unseen.
2. It stands the character up and frees any seat it held (#2579), so no seat
   is held by a body that has left.
3. It saves `db.prelogout_location` and sets `location = None`, taking the
   body off-grid.

On the next login, Evennia's default `at_pre_puppet` puts the body back from
`prelogout_location`. Web character creation also writes that attribute
(`web/website/views/characters.py`).

## Thesis

The end state this proposal describes is the opposite of logout today:
**the body stays in the world, asleep.** A sleeve is a possession; an
unattended possession is exposed.

That exposure is the point, not a side effect:

- A sleeping body can be robbed, moved, harmed, harvested — full contact
  with the crime systems the world already runs (frisk/trust, grapple,
  medical, the coming Ripper economy).
- Which makes **housing load-bearing rather than flavor**: the guaranteed
  rental credit (Queen of Cups' 60 cubes, the Brackett Arms' ~134 leases,
  spring-latch doors keyed to tenancy) becomes the survival answer — *rent a
  room or your body is loot*. The housing guarantee comes first,
  deliberately.

## The proposal

Replace the stow-away (body off-grid) with a sleeping state in place:
pose/longdesc to "asleep", and the vacant-sleeve line retired in favor of the
body simply staying. `at_post_puppet`'s stir line ("stirs as consciousness
returns") already reads correctly for waking a persisted body.

Everything else — what sleep means to combat, medical, frisk, drag — is
design work for when this revives.

## Blocking dependencies (why deferred)

The hostility is only good design if a player can realistically live with
it. Missing, in the owner's words: "the mechanisms for them to thrive with
that hostility." Concretely that means things like these, to be scoped when
this revives. Read them as design axes:

- Meaningful defensive options for the sleeping. Locked doors are one; what
  else?
- Consequences and recourse for sleeve crime: witnesses, dispatch, the
  favor/rep loop. The witness and dispatch machinery is
  `world/director/witness.py` (crowd-gated flash-temp witness NPC) and
  `world/director/dispatch.py`, with the 911MHz report path and its
  interdiction/sabotage seam in `world/radio.py` (see `RADIO_COMMS_SPEC.md`).
  The favor/rep loop is absent from the code. For witnesses and dispatch,
  what is missing is their wiring to sleeve crime, not the machinery.
- An economy where losing pocket contents isn't losing everything.

## Not decided

- Whether a sleeper keeps their seat.
- Whether a hidden sleeper stays hidden.

## Cross-references

- [`../NEW_PLAYER_EXPERIENCE_SPEC.md`](../NEW_PLAYER_EXPERIENCE_SPEC.md) §5 —
  current puppet lifecycle messaging.
- [`DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`](DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md) —
  what happens when the exposure goes badly.
- [`../SLEEVE_INSURANCE_SPEC.md`](../SLEEVE_INSURANCE_SPEC.md) — every
  character starts uninsured, and an uninsured death is permanent (#3667).
  This decides what a sleeping body risks.
- Housing: [`VERTICALITY_AND_BUILDINGS_SPEC.md`](VERTICALITY_AND_BUILDINGS_SPEC.md)
  §2.5 (cube hotels and the housing guarantee) and §3 (tenancy and the rental
  kiosk); code in `world/rental.py`.
- [`GIG_RIPPER_SPEC.md`](GIG_RIPPER_SPEC.md) — the economy sleeping bodies
  would feed.
