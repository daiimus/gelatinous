"""Build 141 — release the displaced (#2371).

The population merge put forty unemployed souls into a colony with
twelve dark shifts. The job market has no reservation — it offers a slot
to whoever is nearest, repeatedly, until somebody claims it — and the
claim step verified the wrong thing: `post.db.post_keeper`, the legacy
SINGLE mirror that cannot tell one shift from another, and only if that
person was standing in the room.

Souls leave their post constantly, because a band-1 need outranks duty.
So a keeper who stepped out to eat was displaced by the next candidate
offered the same slot, and BOTH went on believing they held the job:

    the backlit bar    day    Jerry Lee-Kim   -> Camille Martins
    the backlit bar    night  Alfred Matsumoto-> Angela Contreras
    Maxwell clinic     swing  Candice Bruno   -> Cindy Santana
    Maxwell clinic     night  Glen Glass      -> Jody O' Fischer

The guard is fixed. This releases the four already carrying employment
no slot agrees with, so they re-enter the job market as themselves.

DELIBERATELY NARROW. A soul is only released when its `soul_role`
matches the `post_role` of a registered post in the room it thinks it
works — i.e. it clearly derived that role from a claim. `soul_post` is
overloaded: for a slot-holder it means "the post I hold", but for Wren
and the security units it means "where I am based", and those souls are
in no slot BY DESIGN. Releasing them would unemploy people who are
working perfectly well.

Their role reverts to the director `role` they were spawned with — a
ganger who briefly tended a bar is a ganger again, not a "resident".

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/141_release_the_displaced.py
"""

from evennia.objects.models import ObjectDB

from typeclasses.characters import Character
from world.souls import engine
from world.souls.posts import get_posts

# every (soul_id, shift) a slot actually agrees with
held = set()
posts_by_room = {}
for post in get_posts():
    room = post.location if post.location is not None else post
    posts_by_room.setdefault(room, []).append(post)
    for shift, slot in (post.db.post_slots or {}).items():
        keeper = slot.get("keeper")
        if keeper is not None and keeper.pk:
            held.add((keeper.id, shift))

released = kept = 0
for soul in engine.get_souls():
    room = soul.db.soul_post
    if room is None:
        continue
    if (soul.id, soul.db.soul_schedule) in held:
        continue                              # a slot agrees: employed
    here = posts_by_room.get(room) or []
    # Only a role that clearly CAME from a claim at this room.
    if not any((p.db.post_role or "") == (soul.db.soul_role or "")
               for p in here):
        kept += 1
        continue
    was = soul.db.soul_role
    soul.db.soul_post = None
    soul.db.soul_venue = None
    soul.db.soul_wage_rate = 0.0
    soul.db.soul_role = str(soul.db.role or "resident")
    soul.db.soul_job = None
    released += 1
    print(f"BUILD 141: {soul.key[:22]:22} released from {was} "
          f"at {room.key} -> {soul.db.soul_role}")

print(f"BUILD 141: released={released} left_alone={kept} "
      f"(based-somewhere souls like Wren and the units)")
print("BUILD 141: done")
