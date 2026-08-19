"""Build 075 — the medic's working equipment (souls spec §14 layer 2).

Maritza gets what the job needs, all real and all loose (no carried
containers, by law): an AWE Magpie-01 walkie powered and tuned to the
emergency band — dispatch orders are radio traffic, and a medic
without a set is honestly unreachable — plus par-level field supplies
in her pockets. Her director role and return-post are set so the
assignment machinery can raise her and send her home.

Idempotent: role/post/frequency re-mirror; walkie and supplies only
spawn to fill deficits.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/075_medic_equipment.py
"""

from evennia.prototypes.spawner import spawn
from evennia.utils.search import search_object

from world import prototypes
from world.director.medical import PAR, _carried
from world.radio import EMERGENCY_BAND

mar = next(iter(search_object("#8288")), None)
clinic = next((r for r in search_object("Maxwell Medical Clinic")
               if r.pk and not r.destination
               and r.key == "Maxwell Medical Clinic"), None)

if mar is None or not mar.pk:
    print("BUILD 075: medic not found; aborted")
else:
    OUT = []
    mar.db.role = "medic"              # the dispatcher's routing key
    mar.db.post = clinic               # assignment return point
    OUT.append(f"role=medic, post={clinic.key}")

    walkie = next((o for o in mar.contents
                   if "Magpie-01" in o.key), None)
    if walkie is None:
        walkie = spawn(prototypes.WALKIE_TALKIE)[0]
        walkie.move_to(mar, quiet=True, move_hooks=False)
    walkie.db.frequency = EMERGENCY_BAND
    walkie.db.radio_on = True
    OUT.append(f"walkie: {walkie.key} tuned {walkie.db.frequency}, on")

    drawn = 0
    for proto_attr, par in PAR.items():
        proto = getattr(prototypes, proto_attr)
        short = par - len(_carried(mar, proto_attr))
        for _ in range(max(0, short)):
            item = spawn(proto)[0]
            item.move_to(mar, quiet=True, move_hooks=False)
            drawn += 1
    OUT.append(f"supplies drawn to par: +{drawn} "
               f"(carrying: {[o.key for o in mar.contents if not o.destination]})")

    print("BUILD 075: medic equipment")
    for line in OUT:
        print(f"  {line}")
