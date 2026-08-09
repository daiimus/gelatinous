"""Build 028 — the canyon marquee is a salvaged deco blade sign now.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/028_blade_sign_prose.py
    then a foreground reload.

Owner reference: a classic art-deco theater blade (vertical fin, gold
banding, stacked letters both faces, crown at top). The sprites carry
the form; here the prose catches up — the thing hanging under the
catwalk is an old theater blade someone salvaged and bolted holo
emitters onto, not a bare projection. Data-only; re-run-safe.
"""
from evennia.objects.models import ObjectDB


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


perch = at((-8, -16, 12))                      # the Kaspar Catwalk
assert perch is not None, "catwalk missing"
perch.db.desc = (
    "A little maintenance catwalk slung over Kaspar Street between the "
    "Brackett Arms and the Halcyon — a scrap of grating and a rail, a "
    "long drop past it. Bolted under your feet hangs an old theater "
    "blade sign, oxblood paint and gold banding, salvaged from somewhere "
    "with better days: down both its faces the dead neon has been "
    "replaced with green holo emitters spelling BRACKETT ARMS, letter "
    "over letter into the canyon. You cross from the Brackett's roof to "
    "the Halcyon's deck.")
proj = next((o for o in perch.contents
             if o.key in ("holo-marquee", "holo-billboard")), None)
if proj is not None:
    proj.key = "holo-marquee"
    proj.db.desc = (
        "A salvaged art-deco blade sign hung from the catwalk's underside "
        "— a tall oxblood fin wrapped in gold banding ribs, crowned with "
        "scrollwork shoulders, capped below with a finial. Its neon tubes "
        "died a colony ago; someone re-lit it with green holo emitters "
        "instead, and now B-R-A-C-K-E-T-T, then A-R-M-S, burns down both "
        "faces in slab-cut light. Half the letters flicker.")
    proj.db.integration_desc = (
        "An old |gholo-marquee|n blade sign hangs beneath the catwalk, "
        "the building's name burning down both faces into the canyon.")

print("BUILD 028: catwalk + holo-marquee prose updated to the blade sign.")
