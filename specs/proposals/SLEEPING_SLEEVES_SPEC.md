# Sleeping Sleeves — Logout Persistence Proposal

> **Status:** 📋 **PROPOSAL — EXPLICITLY DEFERRED (owner call,
> 2026-08-04).** Do not build until the mechanisms for players to
> thrive under the resulting hostility exist. This document exists so
> the design thesis and its dependencies don't live only in
> conversation.

## Thesis

Today a logged-out character is stoved off-grid
(`at_post_unpuppet`: room sees "the vacant sleeve is quietly gone",
body → `location=None`, `prelogout_location` saved). The intended end
state is the opposite: **the body stays in the world, asleep.** A
sleeve is a possession; an unattended possession is exposed.

That exposure is the point, not a side effect:

- A sleeping body can be robbed, moved, harmed, harvested — full
  contact with the crime systems the world already runs (frisk/trust,
  grapple, medical, the coming Ripper economy).
- Which makes **housing load-bearing rather than flavor**: the
  guaranteed rental credit (Queen of Cups' 25 cubes, the Brackett
  Arms' 54 leases, spring-latch doors keyed to tenancy) becomes the
  survival answer — *rent a room or your body is loot*. The housing
  guarantee shipped first, deliberately.

## Blocking dependencies (why deferred)

The hostility is only good design if a player can realistically live
with it. Missing today, in the owner's words: "the mechanisms for them
to thrive with that hostility." Concretely that means things like — to
be scoped when this revives — meaningful defensive options for the
sleeping (locked doors are shipped; what else?), consequences/recourse
for sleeve crime (witnesses, dispatch, the favor/rep loop), and an
economy where losing pocket contents isn't losing everything.

## The seam

`Character.at_post_unpuppet` (typeclasses/characters.py) is the single
switch point: replace the stow-away (body off-grid) with a sleeping
state in place — pose/longdesc to "asleep", the vacant-sleeve line
retired in favor of the body simply staying. `at_post_puppet`'s stir
line ("stirs as consciousness returns") already reads correctly for
waking a persisted body. Everything else — what sleep means to combat,
medical, frisk, drag — is design work for when this revives.

## Cross-references

- [`../NEW_PLAYER_EXPERIENCE_SPEC.md`](../NEW_PLAYER_EXPERIENCE_SPEC.md)
  §5 — current puppet lifecycle messaging.
- [`DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md`](DEATH_AND_SLEEVE_LIFECYCLE_SPEC.md)
  — what happens when the exposure goes badly.
- Housing: cube rental + Brackett Arms (shipped; see project history).
- [`GIG_RIPPER_SPEC.md`](GIG_RIPPER_SPEC.md) — the economy sleeping
  bodies would feed.
