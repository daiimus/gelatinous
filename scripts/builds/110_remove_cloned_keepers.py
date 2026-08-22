"""Build 110 — delete the bodies the insurance cloned (#2178).

`_slot_held` asked a souled keeper for `db.soul_post == room`, so a
keeper whose assignment was never recorded could not hold their slot
even standing in it. The sweep read the post as dark, `resleave` paid
out, `_archived_keeper` found nobody in Limbo — because the original
was alive and therefore never archived — and `build_npc` minted a
fresh body. Every sweep the till could afford.

Result: three Petras, two Marta Okoyes, two Nikolai Kasparovs.

The code holes are closed separately. This clears what they already
made.

A body is removed only if ALL THREE hold:

  * it shares a key with an NPC that HAS a blueprint_key, and
  * it has no blueprint_key of its own, and
  * it has no memories.

The copies are minutes old and remember nothing; the originals carry
thirty memories apiece, their dossiers, their Essential flag and their
soul wiring. Nothing that was lived is thrown away.

Duplicates with no wired original (the security-robot fleet) are left
alone — those are meant to be a fleet.

Placement is NOT touched. Some originals are standing somewhere odd
(Petra at Hammett's Boot, both doctors on the Kaspar rooftop) and
where people belong is the owner's call, not a script's.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/110_remove_cloned_keepers.py
"""

from collections import defaultdict

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute

owner_ids = set(
    Attribute.objects.filter(
        db_key="longdesc", db_category="appearance"
    ).values_list("objectdb__id", flat=True)
)
owner_ids.discard(None)

by_key = defaultdict(list)
for obj_id in sorted(owner_ids):
    try:
        body = ObjectDB.objects.get(id=obj_id)
    except ObjectDB.DoesNotExist:
        continue
    if body.attributes.get("is_npc"):
        by_key[body.key].append(body)

removed = []
kept = []
for key, bodies in sorted(by_key.items()):
    if len(bodies) < 2:
        continue
    wired = [b for b in bodies if b.db.blueprint_key]
    if not wired:
        continue                       # a fleet, not a clone
    for body in bodies:
        if body.db.blueprint_key:
            kept.append(f"{body.key} (#{body.id})")
            continue
        if body.db.llm_memories:
            print(f"BUILD 110: {body.key} (#{body.id}) has memories — "
                  f"left in place for review")
            continue
        # detach from any post slot still pointing at it
        for post in ObjectDB.objects.filter(db_attributes__db_key="post_slots"):
            slots = dict(post.db.post_slots or {})
            dirty = False
            for shift, slot in slots.items():
                if slot.get("keeper") == body:
                    slot["keeper"] = None
                    dirty = True
            if dirty:
                post.db.post_slots = slots
        removed.append(f"{body.key} (#{body.id})")
        body.delete()

print(f"BUILD 110: removed {len(removed)} cloned bodies")
for line in removed:
    print(f"  deleted {line}")
for line in kept:
    print(f"  kept    {line}")
if not removed:
    print("BUILD 110: nothing to do (already clean)")
