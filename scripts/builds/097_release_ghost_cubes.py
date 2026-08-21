"""Build 097 — release the cubes held by nobody (#2130).

A deleted tenant's reference resolves to None, and the lazy prune
bailed out on that before it could strip the door grant — so every
resident who died-and-deleted, or was generated and removed, left
their apartment locked behind them forever. The Brackett had 61 of
134 units held by ghosts.

The prune is fixed; this walks every cube so the building doesn't
have to wait for someone to ask after each one.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/097_release_ghost_cubes.py
"""

from evennia.utils.search import search_object

from world import rental

kiosks = [o for o in search_object("#5640") if o.pk]
kiosks += [o for o in search_object("#8093") if o.pk]      # Brackett board
seen, freed, held = set(), 0, 0
for kiosk in kiosks:
    for cube in (kiosk.db.cubes or []):
        if cube is None or not cube.pk or cube.id in seen:
            continue
        seen.add(cube.id)
        before = cube.db.resident_sleeve
        if rental.is_free(cube):          # prunes on contact
            if before:
                freed += 1
        else:
            held += 1
print(f"BUILD 097: {len(seen)} cubes checked — {freed} released from ghost "
      f"tenancies, {held} genuinely held")
