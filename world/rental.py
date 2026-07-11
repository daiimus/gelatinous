"""Cube rental — the colony housing guarantee (user design 2026-07-11).

Every person carries ONE rental credit: it guarantees them one
PERMANENT residence. The credit isn't money — it's a right. Claiming
a cube at a hotel's rental terminal spends nothing and reserves the
cube for as long as they keep it.

The tenancy IS the grant file (§2.2 doors): a permanent residence is a
grant with ``until=None`` on the cube's door; the resident's sleeve
opens, locks, and unlocks it like any granted door. ``cube.db.resident``
is the authoritative occupancy record; ``char.db.residence`` is the
credit's spend.

**Relocation window:** claiming a new residence releases the old cube,
but the old door keeps answering the mover's sleeve for
``RELOCATION_WINDOW`` seconds — time to move your stuff — after which
the grant fails closed on its own (``world.access`` honours ``until``).
A vacated cube is NOT offered to new tenants until that window has
fully expired: no awkward overlaps.
"""

from __future__ import annotations

import time

from world.access import is_granted, make_grant, sleeve_uid_of

#: Seconds the old cube keeps answering a mover's sleeve.
RELOCATION_WINDOW = 48 * 3600


def cube_door(cube):
    """The cube's DoorExit (stored at build time)."""
    door = getattr(getattr(cube, "db", None), "cube_door", None)
    return door if door is not None and getattr(door, "pk", None) else None


def _live_grants(door):
    """Unexpired entries only — expired tenancies prune on contact."""
    now = time.time()
    out = []
    for entry in (door.db.access_grants or []):
        try:
            until = entry.get("until")
            if until and now > float(until):
                continue
            out.append(dict(entry))
        except Exception:  # noqa: BLE001 — malformed entries prune too
            continue
    return out


def _prune_dead_tenancy(cube):
    """Sleeve-lifecycle seam (2026-07-12): a resident that is DELETED or
    an ARCHIVED husk (its person resleeved into a new body, or gone for
    good) no longer holds the cube. Lazily clears the occupancy record
    and strips the stamped sleeve's grant so the cube returns to market
    the moment anyone asks after it. Returns the live resident, or None."""
    db = getattr(cube, "db", None)
    resident = getattr(db, "resident", None)
    if resident is None:
        return None
    alive = (getattr(resident, "pk", None)
             and getattr(resident, "is_archived", False) is not True)
    if alive:
        return resident
    cube.db.resident = None
    uid = getattr(db, "resident_sleeve", None) or sleeve_uid_of(resident)
    door = cube_door(cube)
    if door is not None and uid:
        grants = [g for g in _live_grants(door) if g.get("sleeve") != uid]
        door._mirror(access_grants=grants)
    return None


def is_free(cube):
    """Claimable: no LIVE resident AND no live grants (a mover's
    relocation window keeps the cube off the market until it expires;
    a dead or archived tenant prunes on contact)."""
    if _prune_dead_tenancy(cube) is not None:
        return False
    door = cube_door(cube)
    if door is None:
        return False           # doorless cube isn't rentable
    return not _live_grants(door)


def residence_of(char):
    """The char's current permanent residence, or None."""
    cube = getattr(getattr(char, "db", None), "residence", None)
    return cube if cube is not None and getattr(cube, "pk", None) else None


def release_with_window(char, cube):
    """Vacate: occupancy clears now; the mover's sleeve keeps answering
    the old door for RELOCATION_WINDOW, then fails closed on its own."""
    cube.db.resident = None
    door = cube_door(cube)
    if door is None:
        return
    uid = sleeve_uid_of(char)
    deadline = time.time() + RELOCATION_WINDOW
    grants = _live_grants(door)
    for entry in grants:
        if entry.get("sleeve") == uid:
            entry["until"] = deadline
    door._mirror(access_grants=grants)
    char.db.residence_handover = {"cube": cube, "until": deadline}


def claim(char, cube, issued_by="rental terminal"):
    """Make *cube* the char's permanent residence (grant + records)."""
    door = cube_door(cube)
    grants = _live_grants(door)
    uid = sleeve_uid_of(char)
    grants = [g for g in grants if g.get("sleeve") != uid]
    grants.append(make_grant(char, issued_by=issued_by))   # until=None
    door._mirror(access_grants=grants)
    cube.db.resident = char
    cube.db.resident_sleeve = sleeve_uid_of(char)   # survives deletion
    char.db.residence = cube
    from world.identity import _recognition_now_iso
    char.db.residence_registered_at = _recognition_now_iso()


def residence_report(char):
    """The residence dossier for the ``memory`` report: unit, building/
    vehicle name, street/port of origin, registration age, and any live
    relocation handover. ``None`` if the credit is unspent."""
    cube = residence_of(char)
    if cube is None:
        return None
    handover = None
    entry = getattr(getattr(char, "db", None), "residence_handover", None)
    if entry:
        try:
            old = entry.get("cube")
            left = float(entry.get("until") or 0) - time.time()
            if left > 0 and old is not None and getattr(old, "pk", None):
                # ceil: "answers 2h more" at 1h59m, never "0h"
                handover = {"unit": old.key,
                            "hours_left": max(1, -int(-left // 3600))}
            else:
                char.db.residence_handover = None    # expired: prune
        except Exception:  # noqa: BLE001 — malformed handover prunes too
            char.db.residence_handover = None
    return {
        "unit": cube.key,
        "building": cube.db.residence_building,
        "origin": cube.db.residence_origin,
        "registered_at": char.db.residence_registered_at,
        "handover": handover,
    }


def assign_cube(char, terminal):
    """The terminal transaction. Returns ``(ok, message)``; relocation
    from an existing residence is handled here (old cube released with
    the window, new cube claimed permanent)."""
    if sleeve_uid_of(char) is None:
        return False, ("The terminal's reader passes over you and finds "
                       "no sleeve signature to register.")
    cubes = [c for c in (terminal.db.cubes or [])
             if c is not None and getattr(c, "pk", None)]
    if not cubes:
        return False, "The terminal blinks: NO UNITS CONFIGURED."
    current = residence_of(char)
    if current in cubes:
        return False, (f"The terminal blinks green: you are already "
                       f"registered to {current.key}.")
    free = [c for c in cubes if is_free(c)]
    if not free:
        return False, ("The terminal blinks |rred|n: NO VACANCY. Every "
                       "cube is registered or in handover.")
    cube = free[0]
    moved = ""
    if current is not None:
        release_with_window(char, cube=current)
        hours = int(RELOCATION_WINDOW // 3600)
        moved = (f" Your old door at {current.key} answers your sleeve "
                 f"for another {hours} hours — move your things.")
    claim(char, cube, issued_by=getattr(terminal, "key", "rental terminal"))
    return True, (f"The terminal chirps and flashes |ggreen|n: "
                  f"{cube.key} is yours — permanent registration, one "
                  f"credit, one residence. The door reader knows your "
                  f"sleeve.{moved}")
