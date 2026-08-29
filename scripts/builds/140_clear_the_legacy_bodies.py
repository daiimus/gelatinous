"""Build 140 — clear six legacy bodies (#2362).

The last of the population merge. Eight unsouled bodies were standing in
the colony; two were witnesses stranded by a reload and left on their
own feet once the leak was fixed (#2367). These six are what remained,
and none is finished content:

    #737   Juan Sanchez         prototype commented "# Example corner
                                store merchant" — a HOLOGRAPHIC demo
                                from the shop spec, keeping nothing
    #4917  Jorge de la Schmidt  name appears only in test files
    #4897  Marsha Miller        no reference anywhere in the repo
    #5177  Iris Devlin          no reference anywhere in the repo
    #7559  Aiko                 no desc, no identity axes, no is_npc
    #7560  Bex                  marker — the code reads absence as PC

None carries a persona, a longdesc, or the height/build/sdesc_keyword
the identity system needs, so every one of them renders to observers by
its raw key instead of as "a wiry woman". Their prototypes remain in the
repo: anything wanted back can be respawned COMPLETE.

THE GUARD IS THE POINT. Every deletion is checked against
`world.ownership.is_player_owned`, which asks all three ways a body can
belong to somebody — currently puppeted, listed in an account's
`_playable_characters`, or carrying a puppet lock naming an account id.
`db_account_id` alone is NOT ownership: it is set only while a character
is online, so every logged-out player character reads as ownerless by
it. 56 characters in this game are claimed only by the second signal.
This project has already lost player characters to that exact mistake.

Idempotent: an already-deleted body is skipped, and a body that ANY
signal calls owned is refused out loud rather than skipped quietly.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/140_clear_the_legacy_bodies.py
"""

from evennia.objects.models import ObjectDB

from world.ownership import is_player_owned, owning_accounts

DOOMED = {
    737: "Juan Sanchez",
    4897: "Marsha Miller",
    4917: "Jorge de la Schmidt",
    5177: "Iris Devlin",
    7559: "Aiko",
    7560: "Bex",
}

removed = refused = missing = mismatched = 0

for oid, expected in sorted(DOOMED.items()):
    try:
        obj = ObjectDB.objects.get(id=oid)
    except ObjectDB.DoesNotExist:
        print(f"BUILD 140: #{oid} {expected} — already gone")
        missing += 1
        continue

    # Never delete by dbref alone. Ids get reused across a restore, and
    # a build script that trusts a number will happily delete whatever
    # is standing at that number today.
    if (obj.db_key or "").strip() != expected:
        print(f"BUILD 140: #{oid} REFUSED — expected {expected!r}, "
              f"found {obj.db_key!r}")
        mismatched += 1
        continue

    claims = owning_accounts(obj)
    if claims:
        print(f"BUILD 140: #{oid} {expected} REFUSED — claimed by "
              f"{claims}")
        refused += 1
        continue
    if is_player_owned(obj):        # belt and braces; fails closed
        print(f"BUILD 140: #{oid} {expected} REFUSED — ownership unclear")
        refused += 1
        continue

    where = obj.location.key if obj.location else "nowhere"
    obj.delete()
    print(f"BUILD 140: #{oid} {expected} deleted (was at {where})")
    removed += 1

print(f"BUILD 140: removed={removed} refused={refused} "
      f"missing={missing} name-mismatched={mismatched}")
print("BUILD 140: done")
