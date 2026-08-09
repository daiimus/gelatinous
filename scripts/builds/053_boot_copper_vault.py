"""Build 053 — re-clad Hammett's Boot as one hooped copper vault.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/053_boot_copper_vault.py
    then a foreground reload.

Owner: the whole thing should hoop up into a boot, star-roofed spur and
all, encased in the copper facade that hinted at its vague origin. Re-skin
every ground cell of the Boot to the copper vault family: the foot (sole)
as arched market bays, the edges falling away as lower flanks, the toe's
spur as a copper star-peak. Data-only (atlas skins); rooms/exits untouched.
Re-run-safe.
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

SKINS = {
    # the foot — arched copper market bays
    (-8, -18, 0): "boot_arch", (-7, -18, 0): "boot_arch",
    (-6, -18, 0): "boot_arch", (-5, -18, 0): "boot_arch",
    (-4, -18, 0): "boot_arch", (-3, -18, 0): "boot_arch",
    (-8, -17, 0): "boot_arch",                     # the ankle rising at the heel
    (-3, -19, 0): "boot_arch",                     # the toe base
    (-3, -17, 0): "boot_spur",                     # the star-peaked spur
    # the hull falling away at the edges — lower copper flanks
    (-9, -18, 0): "boot_flank",
    (-7, -17, 0): "boot_flank", (-6, -17, 0): "boot_flank",
    (-5, -17, 0): "boot_flank",
    (-8, -19, 0): "boot_flank", (-7, -19, 0): "boot_flank",
    (-6, -19, 0): "boot_flank", (-5, -19, 0): "boot_flank",
    (-4, -19, 0): "boot_flank",
}


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


n = 0
for xyz, skin in SKINS.items():
    r = at(xyz)
    if r is not None:
        r.db.atlas_skin = skin
        n += 1

print(f"BUILD 053: re-clad {n} Boot cells in copper "
      f"(arch/flank/spur).")
