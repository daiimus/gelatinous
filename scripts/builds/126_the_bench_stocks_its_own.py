"""Build 126 — take the organic kit off the mechanics (#2268).

Build 125's restock drew the CLINIC's par list, so Halina and Tuck are
carrying gauze, human surgical sealant and painkillers. Since the
species gate landed those articles REFUSE a chassis, so every one of
them is now dead weight in a mechanic's hands: she would reach for a
dressing, be told it is meant for living tissue, and have nothing else
to try.

Restock only ever ADDS to par, so it cannot clear this itself. This
strips the organic supplies from the three bench keepers and lets the
next work step draw the machine kit in their place.

Only supplies the gate refuses to a robot are taken, and only from the
three people at this bench. Nothing else is touched.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/126_the_bench_stocks_its_own.py
"""

from evennia.utils.search import search_object

from world.medical.utils import is_medical_item, serves_species

BENCH = "#8986"

bench = next(iter(search_object(BENCH)), None)
if bench is None:
    print("BUILD 126: the service bench is gone; aborted")
    raise SystemExit


class _Chassis:
    """Stands in for a unit, so the gate itself decides what is useless
    rather than this script keeping its own second list."""
    key = "a security unit"
    db = type("_db", (), {"species": "robot"})()

    def get_display_name(self, looker=None):
        return self.key


probe = _Chassis()
stripped = 0

for shift, slot in sorted((bench.db.post_slots or {}).items()):
    who = (slot or {}).get("keeper")
    if who is None or not who.pk:
        print(f"BUILD 126: {shift:6} (vacant)")
        continue
    dead = [o for o in who.contents
            if is_medical_item(o) and not serves_species(o, probe)[0]]
    for item in dead:
        item.delete()
        stripped += 1
    kept = sorted(o.key for o in who.contents if is_medical_item(o))
    print(f"BUILD 126: {shift:6} {who.key} — took {len(dead)}, "
          f"still holds {kept or 'nothing'}")

print(f"BUILD 126: {stripped} organic supplies removed; the next work "
      f"step draws the machine kit")
