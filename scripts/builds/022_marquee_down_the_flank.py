"""Build 022 — the sign moves onto the building (owner rework).

    evennia shell < scripts/builds/022_marquee_down_the_flank.py
    then foreground reload.

Owner: the perch should read as SOLELY a floor/railing; the sign
should be a MARQUEE running down the side of the Brackett Arms, so the
two stop looking like a free-standing billboard in the gap. So:
  * the perch (-8,-16,12) drops the billboard skin for a bare `catwalk`
  * the dead-terraform holo-sign becomes a `marquee` blade running down
    the Brackett's NE corner (-9,-16, z1..z11), under the #6963 crossing
The projector object stays as the marquee's emitter on the catwalk.
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


# ---- the perch becomes a bare catwalk --------------------------------
perch = at((-8, -16, 12))
perch.key = "Kaspar Catwalk"
perch.db.atlas_skin = "catwalk"
perch.db.desc = (
    "A bare maintenance catwalk slung over Kaspar Street between the "
    "Brackett Arms and the Halcyon — grating underfoot, a rail, and a "
    "long drop past it. Down the Brackett's corner beside you runs the "
    "old holo-marquee, a green world turning the whole height of the "
    "flank under its dead promise: A GREEN WORLD BY 3181. You cross "
    "from the Brackett's roof to the Halcyon's deck.")
perch.db.sense_descs = {
    "auditory": "The marquee's emitter hums; the grating rings underfoot.",
    "olfactory": "Hot dust off the projector, cold wind off the drop.",
    "tactile": "The green light washes over the rail and casts nothing.",
    "atmospheric": "A future nobody got, still lit, still running."}

# ---- the marquee runs down the Brackett's NE corner ------------------
marq = 0
for z in range(1, 12):                       # z1..z11 (under #6963 at z12)
    cell = at((-9, -16, z))
    if cell is not None:
        cell.db.atlas_skin = "marquee"
        marq += 1

# ---- the projector object -> the marquee emitter ---------------------
proj = next((o for o in perch.contents
             if o.key in ("holo-billboard", "holo-marquee")), None)
if proj is not None:
    proj.key = "holo-marquee"
    proj.db.desc = (
        "The emitter head of a colonization-era holo-marquee, bolted to "
        "the Brackett's corner and still faithfully running the sign "
        "down the flank: a slow green world and the caption A GREEN WORLD "
        "BY 3181, forty-five years dead. Someone keyed one word under it, "
        "years ago: SOON.")
    proj.db.integration_desc = (
        "A |gholo-marquee|n runs the height of the Brackett's corner, "
        "projecting a green world that never arrived.")

print(f"BUILD 022: perch -> catwalk; marquee skinned on {marq} Brackett "
      f"flank cells (-9,-16,z1-11).")
