"""Build 122 — tidy the charging estate, and leave the wrench work
to somebody with hands (#2246).

Three findings while adding a rack on floor 2:

**The dispatch console advertised `charge` and `maintenance`** at the
same values as the fleet cradle — attributes copied onto the wrong
object at build time. A radio bolted to a desk is not a docking point,
and a flat unit would have walked to the operator's console and tried
to plug into it. Stripped.

**Both the console and the cradle advertised `maintenance`.** The
dwell step's maintenance branch also CLEARS a logged defect, so a unit
could service itself by leaning on a wall fitting — which quietly
deletes the job the owner wants a person doing (three shifts of a
mechanic, servicing security units). Maintenance stops being
advertised anywhere: a neglected unit keeps the defects it earns until
somebody works on it.

Expect, once units are ensouled: `maintenance` will have no plan and
will fault weekly. That is the vacancy, not a bug.

**Charging stays in two places** and that is deliberate. The lobby
cradle's own description says "bolted to the lobby floor", so moving
it would falsify its prose; the new rack sits on floor 2 behind the
biometric lock. `_advertisers` scores by value over distance, so a
unit simply docks at whichever is nearer.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/122_the_rack_and_the_wrench.py
"""

from evennia.objects.models import ObjectDB

CONSOLE = 4931          # a dispatch console — not a charging point
CRADLE = 8255           # a Boiler Run fleet cradle — charging, not repair


def _ads(obj):
    return dict(obj.db.advertises or {})


console = ObjectDB.objects.filter(id=CONSOLE).first()
if console is not None:
    ads = _ads(console)
    stripped = {k: ads.pop(k) for k in ("charge", "maintenance") if k in ads}
    if stripped:
        console.db.advertises = ads or None
        print(f"BUILD 122: {console.key} no longer advertises {stripped} "
              f"(it is a radio, not a socket)")
    else:
        print(f"BUILD 122: {console.key} already clean")

cradle = ObjectDB.objects.filter(id=CRADLE).first()
if cradle is not None:
    ads = _ads(cradle)
    if "maintenance" in ads:
        gone = ads.pop("maintenance")
        cradle.db.advertises = ads
        print(f"BUILD 122: {cradle.key} no longer services itself "
              f"(maintenance={gone} removed — that is somebody's job)")
    else:
        print(f"BUILD 122: {cradle.key} already charge-only")
    # it had none, so it was falling back to the generic cradle poses
    if not cradle.db.dwell_pose_in:
        cradle.db.dwell_pose_in = (
            "reverses into the fleet cradle with a chime, contact rails "
            "taking the weight, and the status strip settles to a "
            "working red."
        )
        cradle.db.dwell_pose_out = (
            "rolls clear of the cradle, rails ringing faintly as the "
            "contacts break, strip gone green."
        )
        print(f"BUILD 122: {cradle.key} given its own dwell poses")

print("BUILD 122: charge advertisers now --")
for obj in ObjectDB.objects.filter(
        db_attributes__db_key="advertises").distinct():
    ads = _ads(obj)
    if ads:
        print(f"   {obj.key:<40} {ads}")
