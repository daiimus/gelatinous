"""Build 154 — put already-spawned scrubs on the rung they now derive to.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/154_scrubs_are_not_outerwear.py
    then a foreground reload.

Scrubs were on the OUTERWEAR rung (4) with the coats, so nothing could
be worn over them: a lab coat collided at the same rung, and a
windbreaker was refused for going UNDER. They are a shirt-and-trousers
SET, so the ladder moved them to rung 1 with the suits and jumpsuits.

That fixes everything spawned FROM NOW ON. It does not touch what is
already in the world, because an EXPLICIT stored `layer` always beats
derivation by design -- "prototypes and builders keep control". Five
`surgical scrubs` carry a stale explicit value written by the old
prototype:

    #5135  layer 4   on a rotting corpse
    #8395  layer 4   worn by Marta Okoye          <- live, in play
    #8723  layer 2   Limbo
    #16280 layer 4   Limbo
    #16284 layer 4   Limbo

The `faded green scrub top` / `scrub trousers` pieces are already at
rung 1 and are left alone -- they are separate two-piece garments and
were never on the wrong rung.

Same shape as build 146 for #2467: the code fix stops new drift, and
the drift already banked needs its own sweep or it sits there forever.

WHAT THIS DOES. Rewrites `layer` to the derived rung on any object
whose key derives to a rung and whose stored layer disagrees, limited
to scrubs. Deliberately re-derives rather than hardcoding 1, so this
stays correct if the ladder moves again.

Re-run-safe: an object already on its derived rung is not written.
"""
from evennia.objects.models import ObjectDB

from world.style import derive_rung

CHANGED = 0
SKIPPED = 0

for obj in ObjectDB.objects.all():
    key = (obj.db_key or "")
    if "scrub" not in key.lower():
        continue
    if obj.attributes.get("coverage") is None:
        continue                      # not a garment
    rung = derive_rung(key)
    if rung is None:
        continue
    stored = obj.attributes.get("layer")
    if stored == rung:
        SKIPPED += 1
        continue
    print(f"  #{obj.id} {key!r}: layer {stored!r} -> {rung} "
          f"(on {obj.location})")
    obj.attributes.add("layer", rung)
    CHANGED += 1

print(f"\nrewritten: {CHANGED}   already correct: {SKIPPED}")
