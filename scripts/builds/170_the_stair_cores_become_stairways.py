"""Build 170 — the stair cores become stairways, and every stair is a `stairwell` (#3757).

Owner, 2026-10-23, reading the #3755 footer: "Stair core should be
'stairway' ... Stair core is not a phrase..." / "It sounds like in those
instances, the room type will need to be changed from tenement or farm to
stairwell/straiway - right?" / 2026-10-24: "stairwell should be fine."

Two things, both on rooms that already exist:

1. The 30 Greenhaus rooms keyed "<Tower> - Stair Core (Ground|Level N)"
   (build 055) are re-keyed "<Tower> - Stairway (...)", and the 27 of them
   that share a tower's "core" description have "stair core" re-worded to
   "stairway" in it. The three "Stair Head (Roof)" rooms keep their name.
2. All 50 stair rooms — those 33 Greenhaus rooms (`farm` until now) and
   the 17 Brackett Arms stairwells, Basement to Floor 15 (`tenement`) —
   are typed `stairwell`, a type the code already knows: crowd modifier
   +0.1 (`crowd_system.room_type_modifiers`, the same as `tenement`),
   witness role `tenant` (`world/director/witness.py`), route cost 1.2
   (`world/spatial/pathfind.py`). It is not on `OPEN_AIR_ROOM_TYPES`, so
   the neighbour glance stops looking into the Greenhaus stairways from
   the platforms beside them (#3753, #3755). `outside`, crowd base, skins,
   exits and contents are untouched.

The footer then reads, with no special case: "The stairwell continues
up (u) and down (d). There is a tenement to the southeast (se)." and
"There is a stairwell to the west (w)." from a landing.

Every room is named by dbref AND checked against the key it had on
2026-10-24 before anything is written; one mismatch aborts the whole
build with nothing changed. Idempotent: a room already done is reported
and skipped. DRY_RUN=True prints the plan and writes nothing.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/170_the_stair_cores_become_stairways.py
then `evennia reload`: the running server caches `key` and `db.type`,
and an external write reaches it only after one.
"""

from evennia.utils.search import search_object

DRY_RUN = False

TYPE = "stairwell"

# (dbref, key on 2026-10-24, key after)  -- the Greenhaus stair column
GREENHAUS = []
for tower, ground, first in (("The Fungary", 7585, 7588),
                             ("The Leafworks", 7618, 7621),
                             ("The Fruiting House", 7651, 7654)):
    GREENHAUS.append((ground, f"{tower} - Stair Core (Ground)",
                      f"{tower} - Stairway (Ground)"))
    for i in range(9):
        GREENHAUS.append((first + 3 * i, f"{tower} - Stair Core (Level {i + 1})",
                          f"{tower} - Stairway (Level {i + 1})"))
    GREENHAUS.append((first + 27, f"{tower} - Stair Head (Roof)",
                      f"{tower} - Stair Head (Roof)"))

BRACKETT = [(5279, "Basement"), (5292, "Ground"), (5309, "Floor 1"),
            (5333, "Floor 2"), (5357, "Floor 3"), (5381, "Floor 4"),
            (5405, "Floor 5"), (5429, "Floor 6"), (6208, "Floor 7"),
            (6413, "Floor 8"), (6454, "Floor 9"), (6495, "Floor 10"),
            (6536, "Floor 11"), (6641, "Floor 12"), (6664, "Floor 13"),
            (6687, "Floor 14"), (6710, "Floor 15")]
BRACKETT = [(i, f"The Brackett Arms - Stairwell ({f})",
             f"The Brackett Arms - Stairwell ({f})") for i, f in BRACKETT]

PLAN = GREENHAUS + BRACKETT
assert len(PLAN) == 50, len(PLAN)

# the three tower descriptions, build 055: the phrase goes, the sentence stays
DESC_REWORD = (
    ("The Fungary's stair core —", "The Fungary's stairway —"),
    ("The Leafworks' stair core —", "The Leafworks' stairway —"),
    ("The Fruiting House stair core —", "The Fruiting House stairway —"),
)

# ── check everything before touching anything ─────────────────────────
rooms = []
problems = []
for dbref, before, after in PLAN:
    found = [o for o in search_object(f"#{dbref}") if o.pk]
    room = found[0] if len(found) == 1 else None
    if room is None:
        problems.append(f"#{dbref}: not found")
        continue
    if room.key not in (before, after):
        problems.append(f"#{dbref}: key is {room.key!r}, expected {before!r}")
        continue
    if room.db.type not in ("farm", "tenement", TYPE):
        problems.append(f"#{dbref}: type is {room.db.type!r}, expected farm/tenement")
        continue
    rooms.append((room, before, after))
if problems:
    print("BUILD 170: aborted, nothing written:")
    for p in problems:
        print("  " + p)
    raise SystemExit

# ── apply ─────────────────────────────────────────────────────────────
renamed = retyped = reworded = skipped = 0
for room, before, after in rooms:
    changes = []
    if room.key != after:
        changes.append(f"key {room.key!r} -> {after!r}")
        if not DRY_RUN:
            room.key = after
        renamed += 1
    if room.db.type != TYPE:
        changes.append(f"type {room.db.type!r} -> {TYPE!r}")
        if not DRY_RUN:
            room.db.type = TYPE
        retyped += 1
    desc = room.db.desc or ""
    for old, new in DESC_REWORD:
        if old in desc:
            changes.append("desc: 'stair core' -> 'stairway'")
            if not DRY_RUN:
                room.db.desc = desc.replace(old, new)
            reworded += 1
    if changes:
        print(f"#{room.id} {before}: " + "; ".join(changes))
    else:
        skipped += 1

print(f"BUILD 170{' (dry run)' if DRY_RUN else ''}: {len(rooms)} rooms checked, "
      f"{renamed} renamed, {retyped} retyped to {TYPE!r}, {reworded} descriptions "
      f"re-worded, {skipped} already done")
