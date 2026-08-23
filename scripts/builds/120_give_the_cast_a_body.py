"""Build 120 — describe the people who were never described (#2245).

Eleven NPCs carried an empty `longdesc` — the attribute present, every
slot blank — so looking at them showed a face and nothing below it.
Petra, Auntie Lin, both new dispatchers, and seven street civilians.

Two separate holes fed it:

* `build_npc` applied whatever a blueprint authored and stopped there.
  The random-civilian spawner has always called
  `fill_missing_longdescs`; the NAMED cast never got it — and the
  blueprints written as `BLUEPRINTS["x"] = {...}` mostly author no
  longdesc at all.
* a handful of spawned civilians ended up with the attribute created
  but unfilled.

The code side is fixed in `build_npc`. This fills the bodies already
walking around.

`fill_missing_longdescs` fills only EMPTY slots — it never overwrites
authored prose and never touches a short desc — so this is safe to run
over everyone and will quietly do nothing to anyone already described.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/120_give_the_cast_a_body.py
"""

from evennia.objects.models import ObjectDB

from world.mob_flavor import fill_missing_longdescs

people = {}
for key in ("soul_post", "llm_driven", "is_npc"):
    for obj in ObjectDB.objects.filter(db_attributes__db_key=key).distinct():
        if obj.pk and hasattr(obj, "longdesc"):
            people[obj.id] = obj

print(f"BUILD 120: {len(people)} NPCs to check")
touched = 0
for npc in people.values():
    ld = npc.attributes.get("longdesc", category="appearance")
    before = sum(1 for v in (dict(ld) if ld else {}).values() if v)
    try:
        filled = fill_missing_longdescs(npc)
    except Exception as err:  # noqa: BLE001 — one bad body, not the run
        print(f"BUILD 120: {npc.key} #{npc.id} failed: {err}")
        continue
    if filled:
        touched += 1
        print(f"BUILD 120: {npc.key} #{npc.id}: {before} -> "
              f"{before + filled} slots (+{filled})")

print(f"BUILD 120: described {touched} NPCs")

# Anyone still bare is a real question, not a silent gap.
bare = []
for npc in people.values():
    ld = npc.attributes.get("longdesc", category="appearance")
    if not any((dict(ld) if ld else {}).values()):
        bare.append(npc)
if bare:
    print("BUILD 120: STILL BARE --")
    for npc in bare:
        print(f"   {npc.key} #{npc.id} species={npc.db.species!r} "
              f"sex={getattr(npc, 'sex', None)!r}")
else:
    print("BUILD 120: nobody left undescribed")
