"""Build 121 — a charging rack on the constabulary's second floor.

Security units run on the `robot` needs profile: `charge` (~12h to
critical) and `maintenance` (~1 week). Both are `dwell_venue` shaped —
the soul walks to the best ADVERTISER and occupies it until the meter
recovers. The colony had no advertiser for either, so the profile was
theory.

This is the charge half. It goes in the Secure Corridor, which is
where the lift opens on floor 2 — units come up, dock, and are behind
the same biometric floor lock as the dispatch desk they answer to.

Deliberately NOT advertising `maintenance`. The dwell step's
maintenance branch also CLEARS a logged defect, and owner ruling is
that servicing a unit is a person's job through the `operate` system
with robot parts — a rack that quietly repaired itself would take that
away before it is built. So a neglected unit still earns defects it
cannot shrug off alone, which is the point of them.

Consequence to expect once units are ensouled (Phase 2): `maintenance`
will have no plan and will fault. That gap is the job opening.

Idempotent — keyed on `db.is_charge_rack`.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/121_the_charging_rack.py
"""

from evennia import create_object
from evennia.utils.search import search_object

ROOM = "#4960"          # Colonial Constabulary Secure Corridor (floor 2)
KEY = "a Boiler Run Mechanics charging rack"

room = next(iter(search_object(ROOM)), None)
if room is None:
    print("BUILD 121: the secure corridor is gone; aborted")
    raise SystemExit

existing = next((o for o in room.contents
                 if getattr(o.db, "is_charge_rack", None) is True), None)
if existing is not None:
    print(f"BUILD 121: {existing.key} #{existing.id} already racked here")
else:
    rack = create_object("typeclasses.items.Item", key=KEY, location=room)
    rack.aliases.add(["rack", "charging rack", "cradle"])
    rack.db.is_charge_rack = True
    rack.db.desc = (
        "Four steel cradles bolted in a row to the corridor wall, each "
        "with a shaped backplate and a contact bar worn to bright metal "
        "by shoulders that have leaned there ten thousand times. A "
        "Boiler Run Mechanics plate is riveted at the end of the run, "
        "the lettering half scoured off. Above each cradle a status "
        "strip idles amber, and the whole rack gives off the faint "
        "ozone-and-hot-dust smell of things that are always warm."
    )
    # The fixture authors its own dwell poses (souls spec §12) — the
    # cradle defaults are generic; these are this rack's.
    rack.db.dwell_pose_in = (
        "backs into a cradle, contacts finding the bar with a soft "
        "clunk, and the status strip above it climbs from amber to a "
        "steady working red."
    )
    rack.db.dwell_pose_out = (
        "unseats from the cradle with a hydraulic sigh, the status "
        "strip dropping to green behind it."
    )
    # Purpose-built and behind the lock, so it outbids anything
    # improvised. Charge only — maintenance is a person's job.
    rack.db.advertises = {"charge": 0.9}
    rack.locks.add("get:false()")
    print(f"BUILD 121: {rack.key} #{rack.id} racked in {room.key}")

# Prove the planner can actually find it from where units live.
print("BUILD 121: can a unit reach it? --")
from world.souls import actions
from evennia.objects.models import ObjectDB
bots = [o for o in ObjectDB.objects.filter(
    db_attributes__db_key="role").distinct() if o.db.role == "security"][:3]
for b in bots:
    ads = actions._advertisers(b, "charge")
    best = ads[0] if ads else None
    print(f"   {b.key} #{b.id} at {getattr(b.location,'key','?')}: "
          f"{'finds ' + best[1].key if best else 'NO ADVERTISER'}")
