"""Build 060 — wire the Greenhaus gap jumps the way the engine expects.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/060_gap_wiring.py
    then a foreground reload.

Owner report: jumping the cistern crossing left them stuck in the air
cell. Root cause (canon read from the Halcyon↔Antenna crossing): a gap
exit needs THREE pieces — `destination` = the air cell (used by
`jump off` descents), `db.gap_destination` = the far perch dbref (where
`jump across` actually lands), `db.sky_room` = the air cell dbref (the
transit hop). Builds 055/056 set only destination, so a SUCCESSFUL
crossing "landed" in the air. This wires gap_destination + sky_room on
every Greenhaus gap edge:

  - cistern diagonal: C1 lid <-> C2 catwalk through the air (5,-18,1)
  - every farm platform/roof lateral: x7<->x9<->x11 through the air
    columns at x8/x10, same y, same z
  - the Constabulary entry becomes a pure DESCENT over the fence:
    destination retargeted to the farm's own air (8,-17,2) so the fall
    lands on the West Lawn INSIDE the fence (it previously fell to
    Kaspar Street outside); is_gap removed, the orphan connector air
    over Kaspar is deleted.

Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def wire(room, key, far, air):
    for e in room.exits:
        if e.key == key and e.db.is_gap:
            e.db.gap_destination = far.id
            e.db.sky_room = air.id
            return 1
    return 0


wired = 0

# ── the cistern diagonal ───────────────────────────────────────────────
c1 = by_key("Greenhaus Cistern No. 1 - Tank Top")
walk = by_key("Greenhaus Cistern No. 2 - Service Catwalk")
air = at((5, -18, 1))
wired += wire(c1, "northeast", walk, air)
wired += wire(walk, "southwest", c1, air)

# ── the farm laterals: platforms and roof greens ───────────────────────
TOWERS = {7: "The Fungary", 9: "The Leafworks", 11: "The Fruiting House"}


def perch(x, y, z):
    name = TOWERS[x]
    if z == 10:
        side = "North" if y == -17 else "South"
        return by_key(f"{name} - Roof Green ({side})")
    side = "North" if y == -17 else "South"
    return by_key(f"{name} - {side} Platform (Level {z})")


for x in TOWERS:
    for y in (-17, -19):
        for z in range(1, 11):
            me = perch(x, y, z)
            if me is None:
                continue
            if x in (7, 9):                      # east across the gap
                gap_air = at((x + 1, y, z))
                far = perch(x + 2, y, z)
                if gap_air and far:
                    wired += wire(me, "east", far, gap_air)
            if x in (9, 11):                     # west across the gap
                gap_air = at((x - 1, y, z))
                far = perch(x - 2, y, z)
                if gap_air and far:
                    wired += wire(me, "west", far, gap_air)

# ── the Constabulary entry: descent over the fence, landing inside ─────
constab = by_key("Colonial Constabulary Rooftop (South)")
farm_air = at((8, -17, 2))
old_conn = at((8, -16, 2))
retargeted = 0
for e in constab.exits:
    if e.key == "south" and e.db.is_edge:
        if e.destination != farm_air:
            e.destination = farm_air
            retargeted += 1
        e.db.is_gap = None
        e.db.gap_difficulty = None
        e.db.sky_room = None
        e.db.gap_destination = None
if old_conn is not None:
    inbound = [x for x in ObjectDB.objects.filter(db_destination=old_conn.id)]
    if not inbound:
        old_conn.delete()

print(f"BUILD 060: {wired} gap edges wired (gap_destination + sky_room), "
      f"constab entry retargeted={retargeted} to the fenced airspace, "
      f"orphan connector removed.")
