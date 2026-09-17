"""
Gravity -- what happens to anything in an air cell that cannot stay up.

Owner ruling (#3579, 2026-09-16): *"They should traverse the air rooms
falling ... if I'm flying in a room or in a flying vehicle in one of the
sky rooms, I'd see someone fall past me."* So a fall is a sequence of
real moves down the column, one air cell per tick, for bodies and
objects alike; damage is charged once at the bottom for the cells
actually passed; and gravity is a property of the ROOM, not of the verb
that put you there.

The whole layer:

- ``on_enter_air`` is called from :meth:`typeclasses.rooms.Room.at_object_receive`
  for every arrival in a room whose ``db.is_sky_room is True`` (the flag,
  never the typeclass -- the colony's highest crossings are plain Rooms
  flagged in place, and one SkyRoom was flipped into a walkable catwalk).
  Anyone who cannot stay up starts falling. A leap carries a one-tick
  ``ndb.airborne_token`` and continues to its far perch instead.
- ``start_fall`` writes ONE persistent record, ``db.falling`` (grenade
  fuse shape, #505): cells passed, the edge's difficulty, whether the
  landing rolls, a grappled companion, and the absolute epoch of the next
  step so the boot sweep knows how overdue it is. The live chain is an
  ephemeral ``delay``; ``sweep_airborne`` resumes it after a reload.
- ``_fall_step`` re-resolves the ``down`` exit every tick (the crane
  rebuilds its column on every trip), moves the body with hooks ON so the
  next cell's hook is what continues the fall, announces to the cell left,
  the cell entered and the rooftops beside it, and lands when the next
  room is not air. A cell with no ``down`` stops the fall cleanly where it
  is -- the parked impasse (#3581), never a strand and never a crash.
- ``_land`` rolls (edge descents only), absorbs cells on a make, and
  applies ``FALL_DAMAGE_PER_STORY`` x cells through ``apply_fall_damage``,
  which fills the body from the ground up: legs (every destroyable organ
  that feeds ``moving``, feet before shins before thighs), then the other
  severable limbs, then everything else at random.

Balance knobs live in ``world/combat/constants.py`` under GRAVITY &
FALLING and in ``specs/roadmaps/BALANCE_LEDGER.md``.
"""

from __future__ import annotations

import random
import time
from collections.abc import Mapping

from evennia.utils import logger
from evennia.utils.utils import delay

from world.combat.constants import (
    DB_FALLING,
    FALL_BODYSHIELD_FAILED_GRAPPLER,
    FALL_BODYSHIELD_FAILED_VICTIM,
    FALL_BODYSHIELD_MADE_GRAPPLER,
    FALL_BODYSHIELD_MADE_VICTIM,
    FALL_DAMAGE_PER_STORY,
    FALL_EDGE_DIFFICULTY_DEFAULT,
    FALL_LANDING_ABSORBED_CELLS,
    FALL_LANDING_DIFFICULTY_PER_CELL,
    FALL_MAX_CELLS,
    FALL_SECONDS_PER_CELL,
    NDB_AIRBORNE_TOKEN,
    NDB_PROXIMITY_UNIVERSAL,
    NDB_SKIP_ROUND,
)
from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity

#: Reverse of every compass key -- a body in the cell EAST of a roof is
#: seen from that roof to the east, but the cell's exit to the roof is
#: keyed "west". Shared with the jump verb's rigged-edge search.
DIRECTION_OPPOSITES = {
    "north": "south", "n": "s",
    "south": "north", "s": "n",
    "east": "west", "e": "w",
    "west": "east", "w": "e",
    "northeast": "southwest", "ne": "sw",
    "northwest": "southeast", "nw": "se",
    "southeast": "northwest", "se": "nw",
    "southwest": "northeast", "sw": "ne",
    "up": "down", "u": "d",
    "down": "up", "d": "u",
}

#: ndb keys. ``fall_active`` marks a chain that is running in THIS process
#: (so the hook treats the next cell as a continuation, not a new fall);
#: it dies with the process, which is exactly how the sweep and the
#: reconnect path know to resume instead. ``fall_intent`` is how a verb
#: hands the hook the edge's difficulty / the roll / a dragged companion.
#: ``leap`` carries the far perch and the verb's finish callback.
NDB_FALL_ACTIVE = "fall_active"
NDB_FALL_INTENT = "fall_intent"
NDB_LEAP = "leap"

# --------------------------------------------------------------------------
# predicates -- pure, DB-free, testable without a harness
# --------------------------------------------------------------------------


def is_sky(room) -> bool:
    """The flag is the truth, and only a literal ``True`` counts
    (world/spatial/pathfind.py:180-185 on why truthiness lied)."""
    return getattr(getattr(room, "db", None), "is_sky_room", None) is True


def can_stay_up(obj) -> bool:
    """Flight, a vehicle, a future capability: one attribute, strict."""
    return getattr(getattr(obj, "db", None), "stays_aloft", None) is True


def has_airborne_token(obj) -> bool:
    """The leap's one-tick token. An ndb miss answers None, never a
    default (test_no_ndb_default_leaks_none), hence the ``or 0``."""
    return (getattr(getattr(obj, "ndb", None), NDB_AIRBORNE_TOKEN, None) or 0) > 0


def is_falling(obj) -> bool:
    return bool(getattr(getattr(obj, "db", None), DB_FALLING, None))


def _is_character(obj) -> bool:
    from typeclasses.characters import Character
    return isinstance(obj, Character)


def _falls_at_all(obj) -> bool:
    """Only bodies and things fall. Exits are created INTO air cells by
    @airfill and fire the receive hook (Evennia calls it from
    at_first_save); a positive gate keeps them out."""
    from typeclasses.characters import Character
    from typeclasses.items import Item
    return isinstance(obj, (Character, Item))


def can_leave_by(mover, exit_obj) -> bool:
    """Can this mover leave by this exit without falling? An exit that is
    an edge or a gap, or that leads into air, refuses anyone who cannot
    stay up -- the one predicate flee, advance and charge ask before
    relocating (#3583: "refused at the edge"). Walking already refuses
    these at ``Exit.at_traverse``; combat movement relocates with
    ``move_to`` and never reaches it, so it asks here."""
    if exit_obj is None:
        return False
    db = getattr(exit_obj, "db", None)
    over_the_edge = (getattr(db, "is_edge", None) is True
                     or getattr(db, "is_gap", None) is True
                     or is_sky(getattr(exit_obj, "destination", None)))
    return not over_the_edge or can_stay_up(mover)


def is_surface(room) -> bool:
    """A rooftop or any outdoor room that is not air: somewhere a body can
    stand beside the sky. Interiors never qualify (the B-line incident):
    for the builder's air fill they are not a place to jump from, and for
    a shot from above an interior straight below an air cell means an
    unbuilt roof is in the way."""
    if room is None or is_sky(room):
        return False
    db = getattr(room, "db", None)
    return (getattr(db, "type", None) == "rooftop"
            or getattr(db, "outside", None) is True)


def ground_below(cell):
    """What is under *cell*, by geometry, without moving anyone (#3589):
    the highest room straight below it in the same column that is not
    air. A shot needs this answer whether or not the column is wired, so
    geometry comes first: on the grid, the coordinate index decides, and
    a bare column (no ``down``, #3581) still resolves to the street a
    body would reach once the column is wired -- the fall stopping short
    there is the parked impasse, not the shot's business. Off the grid,
    or with nothing seeded below, the ``down`` chain the fall itself
    walks decides instead. An interior straight below is an unbuilt roof
    in the way: ``None``, nothing to hit. ``None`` too when nothing solid
    is below at all. A cell that is not air is its own ground."""
    if cell is None:
        return None
    if not is_sky(cell):
        return cell
    try:
        from world.spatial import coordinate_index, get_xyz
        xyz = get_xyz(cell)
    except Exception:  # noqa: BLE001 -- no spatial layer in a bare harness
        xyz = None
    if xyz is not None:
        x, y, z = xyz
        best = None
        for (cx, cy, cz), room in coordinate_index().items():
            if cx != x or cy != y or cz >= z or is_sky(room):
                continue
            if best is None or cz > best[0]:
                best = (cz, room)
        if best is not None:
            return best[1] if is_surface(best[1]) else None
    seen = 0
    while cell is not None and is_sky(cell) and seen < FALL_MAX_CELLS:
        ex = down_exit(cell)
        cell = getattr(ex, "destination", None) if ex is not None else None
        seen += 1
    return cell if cell is not None and not is_sky(cell) else None


def gap_destination(exit_obj):
    """The room a made leap across *exit_obj* lands on: its
    ``gap_destination`` (a dbref or an object), else the exit's own
    destination when that is not air. ``None`` when nothing usable
    exists. Shared by the leap (jump across) and the shot (#3589)."""
    raw = getattr(getattr(exit_obj, "db", None), "gap_destination", None)
    if raw:
        if isinstance(raw, (str, int)):
            from evennia import search_object
            found = search_object(f"#{raw}")
            room = found[0] if found else None
        else:
            room = raw if getattr(raw, "pk", None) else None
        return room if room is not None and not is_sky(room) else None
    dest = getattr(exit_obj, "destination", None)
    if dest is not None and not is_sky(dest):
        return dest
    return None


def room_through(exit_obj):
    """The room a shot, a look or a throw through *exit_obj* is really
    aimed at (#3589). A gap: the far perch. An edge, or any exit into
    air: the ground below it (:func:`ground_below`). Any other exit: its
    destination. ``None`` when there is nothing to aim at down there. A
    gap with no perch is aimed like an edge: the leap refuses it, the
    shot drops to whatever is under it."""
    if exit_obj is None:
        return None
    db = getattr(exit_obj, "db", None)
    dest = getattr(exit_obj, "destination", None)
    if getattr(db, "is_gap", None) is True:
        perch = gap_destination(exit_obj)
        if perch is not None:
            return perch
    if dest is None:
        return None
    if is_sky(dest) or getattr(db, "is_edge", None) is True:
        return ground_below(dest)
    return dest


def is_stranded_aloft(obj) -> bool:
    """The boot sweep's cold-half predicate: in air, no record, cannot stay
    up, and somewhere to fall TO -- a body parked in a bare cell by the
    impasse is left alone, or every boot would restart and re-strand it.
    Split out so it is testable without tripping the harness."""
    cell = getattr(obj, "location", None)
    return (
        _falls_at_all(obj)
        and is_sky(cell)
        and not is_falling(obj)
        and not can_stay_up(obj)
        and getattr(down_exit(cell), "destination", None) is not None
    )


def down_exit(cell):
    """The cell's ``down`` exit by key OR alias ``d`` -- @airfill keys it
    "down" with alias "d", build scripts vary. Read off ``cell.exits``,
    never ``room.search`` (that needs a searcher)."""
    for ex in getattr(cell, "exits", None) or []:
        key = (getattr(ex, "key", "") or "").lower()
        if key in ("down", "d"):
            return ex
        try:
            aliases = [a.lower() for a in ex.aliases.all()]
        except Exception:  # noqa: BLE001 -- a double without aliases
            aliases = []
        if "down" in aliases or "d" in aliases:
            return ex
    return None


def neighbour_surfaces(cell):
    """``[(direction_from_cell, room), ...]`` for every walkable surface
    beside the cell -- its non-down exits whose destination is not air.
    @airfill wires exactly that shape (commands/CmdBuildTools.py)."""
    out = []
    down = down_exit(cell)
    for ex in getattr(cell, "exits", None) or []:
        if ex is down:
            continue
        key = getattr(ex, "key", "") or ""
        if key.lower() in ("up", "u", "down", "d"):
            continue                     # a vertical neighbour is not "beside"
        dest = getattr(ex, "destination", None)
        if dest is None or is_sky(dest):
            continue
        out.append((key, dest))
    return out


# --------------------------------------------------------------------------
# the hook
# --------------------------------------------------------------------------


def on_enter_air(room, obj) -> None:
    """Called by ``Room.at_object_receive`` for EVERY arrival. Decides
    nothing unless the room is air. Never raises: an exception inside
    ``at_object_receive`` makes Evennia report the completed move as a
    failure (objects.py:1318-1325)."""
    try:
        _on_enter_air(room, obj)
    except Exception:  # noqa: BLE001 -- a broken fall must not undo a move
        logger.log_trace("gravity: on_enter_air failed")


def _on_enter_air(room, obj) -> None:
    if not is_sky(room) or not _falls_at_all(obj):
        return
    # The flight plan a verb handed over is consumed on EVERY branch, so
    # a plan meant for one edge can never roll a later arrival against
    # another edge's difficulty.
    intent = getattr(obj.ndb, NDB_FALL_INTENT, None) or {}
    try:
        delattr(obj.ndb, NDB_FALL_INTENT)
    except AttributeError:
        pass
    record = getattr(obj.db, DB_FALLING, None)
    if record:
        if "led_by" in record:
            return                      # the leader's step moves them
        if getattr(obj.ndb, NDB_FALL_ACTIVE, None):
            return                      # a running chain: this IS the step
        # A record with no live chain: a reload or a reconnect. Resume.
        setattr(obj.ndb, NDB_FALL_ACTIVE, True)
        _schedule(obj, FALL_SECONDS_PER_CELL)
        return
    if can_stay_up(obj):
        return
    if has_airborne_token(obj):
        # The leap: consume the token NOW (or a far perch that is itself
        # air would re-grant it forever) and carry on to the perch.
        setattr(obj.ndb, NDB_AIRBORNE_TOKEN, 0)
        setattr(obj.ndb, NDB_FALL_ACTIVE, True)
        delay(FALL_SECONDS_PER_CELL, _continue_leap, obj)
        return
    start_fall(obj, **intent)


# --------------------------------------------------------------------------
# the leap
# --------------------------------------------------------------------------


def _continue_leap(obj) -> None:
    """One tick after entering the air cell, a successful leap lands on
    its far perch. The verb's own finish callback (rigged-edge check,
    arrival line, combat cleanup) runs after the move. No perch, or a
    perch that is not a room: the token is spent, gravity takes over."""
    if not is_falling(obj):
        # The flag belongs to a fall chain if one has started meanwhile.
        try:
            delattr(obj.ndb, NDB_FALL_ACTIVE)
        except AttributeError:
            pass
    leap = getattr(obj.ndb, NDB_LEAP, None) or {}
    try:
        delattr(obj.ndb, NDB_LEAP)
    except AttributeError:
        pass
    cell = obj.location
    if not is_sky(cell):
        return                           # left the air by another door
    perch = leap.get("destination")
    if perch is None or getattr(perch, "pk", None) is None:
        _splat(f"GRAVITY_LEAP_NO_PERCH: {obj.key} had no perch; falling")
        start_fall(obj)
        return
    _interrupt(obj)
    moved = obj.move_to(perch, quiet=True)
    if not moved or obj.location is not perch:
        start_fall(obj)
        return
    finish = leap.get("finish")
    if callable(finish):
        try:
            finish(perch)
        except Exception:  # noqa: BLE001 -- the landing already happened
            logger.log_trace("gravity: leap finish callback failed")


# --------------------------------------------------------------------------
# the fall
# --------------------------------------------------------------------------


def start_fall(obj, *, edge_difficulty=None, roll=False, companion=None) -> bool:
    """Begin a fall from the air cell ``obj`` is in. Idempotent: a body
    already falling is left to its chain. Returns whether a fall began."""
    if is_falling(obj):
        return False
    cell = getattr(obj, "location", None)
    if not is_sky(cell):
        return False
    _clear_escort(obj)
    _interrupt(obj)
    if companion is not None and getattr(companion, "location", None) is not cell:
        companion = None
    record = {
        "cells": 0,
        "origin": cell,
        "edge_difficulty": (
            FALL_EDGE_DIFFICULTY_DEFAULT if edge_difficulty is None
            else int(edge_difficulty)),
        "roll": bool(roll),
        "companion": companion,
        "next_step_at": time.time() + FALL_SECONDS_PER_CELL,
    }
    setattr(obj.db, DB_FALLING, record)
    if companion is not None:
        _clear_escort(companion)
        setattr(companion.db, DB_FALLING, {"led_by": obj})
    setattr(obj.ndb, NDB_FALL_ACTIVE, True)
    _splat(f"GRAVITY_START: {obj.key} falling from {cell.key} (#{cell.id})")
    _schedule(obj, FALL_SECONDS_PER_CELL)
    return True


def _schedule(obj, seconds: float) -> None:
    delay(seconds, _fall_step, obj)


def _fall_step(obj) -> None:
    try:
        _step(obj)
    except Exception:  # noqa: BLE001 -- log, then stop where the body is
        logger.log_trace("gravity: fall step failed")
        record = getattr(getattr(obj, "db", None), DB_FALLING, None)
        cell = getattr(obj, "location", None)
        if record and is_sky(cell):
            try:
                _strand(obj, record, cell, reason="fault")
                return
            except Exception:  # noqa: BLE001
                logger.log_trace("gravity: strand after fault failed")
        _clear(obj)


def _step(obj) -> None:
    record = getattr(obj.db, DB_FALLING, None)
    if not record or "led_by" in record:
        _clear(obj)
        return
    cell = getattr(obj, "location", None)
    if cell is None:
        # Logged out mid-fall: keep the record, let the reconnect resume it.
        try:
            delattr(obj.ndb, NDB_FALL_ACTIVE)
        except AttributeError:
            pass
        return
    if not is_sky(cell):
        _clear(obj)                     # left the air by another door
        return
    ex = down_exit(cell)
    dest = getattr(ex, "destination", None) if ex is not None else None
    if dest is None or getattr(dest, "pk", None) is None:
        _strand(obj, record, cell, reason="no_down")
        return
    if int(record.get("cells", 0)) >= FALL_MAX_CELLS:
        _splat(f"GRAVITY_LIMIT: {obj.key} hit FALL_MAX_CELLS in {cell.key}")
        _strand(obj, record, cell, reason="limit")
        return
    _interrupt(obj)
    moved = obj.move_to(dest, quiet=True)
    if not moved or obj.location is not dest:
        _splat(f"GRAVITY_REFUSED: {obj.key} could not leave {cell.key}")
        _strand(obj, record, cell, reason="refused")
        return
    companion = record.get("companion")
    if companion is not None and getattr(companion, "location", None) is cell:
        # Hooks ON: the companion's marker record makes the next cell's
        # hook ignore them, and at_post_move still clears their posture
        # and follower links the way the old verb did.
        _interrupt(companion)
        if not companion.move_to(dest, quiet=True) \
                or getattr(companion, "location", None) is not dest:
            _release_companion(companion, obj)
            companion = None
    elif companion is not None:
        _release_companion(companion, obj)  # separated on the way down
        companion = None
    record = dict(record)
    record["cells"] = int(record.get("cells", 0)) + 1
    record["companion"] = companion
    _reset_proximity(obj)
    if companion is not None:
        _reset_proximity(companion)
    if not is_sky(dest):
        _announce_pass(obj, cell, dest, companion)
        _land(obj, record, dest, companion)
        return
    # Persist and re-arm BEFORE announcing: a broadcast that raises must
    # never leave a body parked mid-column with no record and no line.
    record["next_step_at"] = time.time() + FALL_SECONDS_PER_CELL
    setattr(obj.db, DB_FALLING, record)
    _schedule(obj, FALL_SECONDS_PER_CELL)
    _announce_pass(obj, cell, dest, companion)


def _strand(obj, record, cell, reason="no_down") -> None:
    """The fall stops where the body is, cleanly: no damage, no crash.
    ``no_down`` is the parked impasse (#3581), the column ending in air
    with nothing beneath. ``limit``, ``refused`` and ``fault`` are the
    guards -- the message must not claim there is nothing below when
    there is."""
    _clear(obj)
    companion = record.get("companion") if record else None
    if companion is not None:
        _release_companion(companion, obj)
    _splat(f"GRAVITY_STRAND: {obj.key} stopped in {cell.key} (#{cell.id}): {reason}")
    body = _is_character(obj)
    if body:
        if reason == "no_down":
            obj.msg(
                "|yYou come to a stop in open air. There is nothing beneath "
                "you here -- no ledge, no street, only more sky that nobody "
                "has finished. Gravity is patient.|n")
        else:
            obj.msg("|ySomething arrests your fall, and you hang in the "
                    "open air.|n")
        if companion is not None and _is_character(companion):
            companion.msg("|yThe two of you hang in open air, going nowhere.|n")
    verb = "hangs in the open air" if body else "comes to rest in the open air"
    msg_room_identity(
        location=cell,
        template="{actor} " + verb + (", with nothing beneath." if reason == "no_down" else "."),
        char_refs={"actor": obj},
        exclude=[o for o in (obj, companion) if o is not None],
    )


def _announce_pass(obj, cell, dest, companion) -> None:
    """Three audiences per cell -- the cell left, the cell entered, and the
    walkable surfaces beside the cell entered -- plus one line for the
    faller, ON TOP OF the cell's full description: each step is a real
    move, so Evennia's arrival look fires in every air cell the way it
    does for anyone entering a room. Owner-ruled by design (#3585), not
    a bug. Every line here goes through ``msg_room_identity`` so a
    watcher sees a resolved sdesc, and an item renders through its own
    ``get_display_name``. A broadcast that raises is logged and skipped:
    the fall is already persisted and re-armed."""
    try:
        _announce(obj, cell, dest, companion)
    except Exception:  # noqa: BLE001
        logger.log_trace("gravity: fall announcement failed")


def _announce(obj, cell, dest, companion) -> None:
    body = _is_character(obj)
    if body:
        obj.msg("|yYou plummet downward through open air.|n")
        if companion is not None and _is_character(companion):
            companion.msg("|rYou are dragged down through open air.|n")
    exclude = [o for o in (obj, companion) if o is not None]
    verb_away = "drops away beneath you." if body else "tumbles away beneath you."
    msg_room_identity(
        location=cell,
        template="{actor} " + verb_away,
        char_refs={"actor": obj},
        exclude=exclude,
    )
    if is_sky(dest):
        verb_past = "falls past you, still dropping." if body else "tumbles past you."
        msg_room_identity(
            location=dest,
            template="{actor} " + verb_past,
            char_refs={"actor": obj},
            exclude=exclude,
        )
        for direction, surface in neighbour_surfaces(dest):
            seen_toward = DIRECTION_OPPOSITES.get(direction.lower(), direction)
            verb = "falls past the edge" if body else "tumbles past the edge"
            msg_room_identity(
                location=surface,
                template="{actor} " + f"{verb} to the {seen_toward}.",
                char_refs={"actor": obj},
            )


def _land(obj, record, room, companion) -> None:
    cells = int(record.get("cells", 0))
    _clear(obj)
    if companion is not None:
        _release_companion(companion, obj)
    if not _is_character(obj):
        _land_item(obj, room, cells)
        return
    made = False
    effective = cells
    if record.get("roll"):
        from world.combat.utils import get_numeric_stat, standard_roll
        difficulty = (int(record.get("edge_difficulty") or FALL_EDGE_DIFFICULTY_DEFAULT)
                      + FALL_LANDING_DIFFICULTY_PER_CELL * cells)
        rolled, _, _ = standard_roll(get_numeric_stat(obj, "motorics"))
        made = rolled >= difficulty
        if made:
            effective = max(0, cells - FALL_LANDING_ABSORBED_CELLS)
        _splat(f"GRAVITY_LANDING_ROLL: {obj.key} motorics:{rolled} vs {difficulty} made:{made}")
    damage = FALL_DAMAGE_PER_STORY * effective
    setattr(obj.ndb, NDB_SKIP_ROUND, True)
    storeys = f"{cells} {'storey' if cells == 1 else 'storeys'}"
    if companion is not None and _is_character(companion) \
            and getattr(companion, "location", None) is room:
        setattr(companion.ndb, NDB_SKIP_ROUND, True)
        _land_with_bodyshield(obj, companion, room, damage, made, storeys)
        return
    dealt, _died = apply_fall_damage(obj, damage)
    if dealt <= 0:
        if made:
            obj.msg(f"|gYou land clean, {storeys} down, and walk it off.|n")
        else:
            obj.msg(f"|gYou land, {storeys} down, without a scratch.|n")
        template = "{actor} lands with athletic grace from above!"
    elif made:
        obj.msg(f"|gYou land well after {storeys}, but the impact still "
                f"costs you {dealt} damage.|n")
        template = "{actor} lands with athletic grace from above!"
    else:
        obj.msg(f"|rYou crash hard into the ground after falling {storeys}! "
                f"You take {dealt} damage!|n")
        template = "{actor} crashes down from above with a bone-jarring impact!"
    msg_room_identity(location=room, template=template,
                      char_refs={"actor": obj}, exclude=[obj])
    _splat(f"GRAVITY_LAND: {obj.key} landed in {room.key} after {cells} cells, "
           f"made:{made} damage:{dealt}")


def _land_with_bodyshield(obj, victim, room, damage, made, storeys) -> None:
    """The dragged victim cushions the grappler (shipped behaviour, ratios
    now constants). Both alive afterwards: the grapple is rebuilt in a
    fresh handler at the landing room, the grappler yielding."""
    if made:
        v_share, g_share = FALL_BODYSHIELD_MADE_VICTIM, FALL_BODYSHIELD_MADE_GRAPPLER
    else:
        v_share, g_share = FALL_BODYSHIELD_FAILED_VICTIM, FALL_BODYSHIELD_FAILED_GRAPPLER
    v_dmg, _ = apply_fall_damage(victim, int(damage * v_share))
    g_dmg, _ = apply_fall_damage(obj, int(damage * g_share))
    from world.combat.utils import get_display_name_safe
    victim_for_obj = get_display_name_safe(victim, obj)
    obj_for_victim = capitalize_first(get_display_name_safe(obj, victim))
    if made:
        obj.msg(f"|gYou use {victim_for_obj} to cushion your landing after "
                f"{storeys}! You take {g_dmg} damage while they absorb most "
                f"of the impact.|n")
        victim.msg(f"|r{obj_for_victim} uses you as a bodyshield during the "
                   f"landing! You take {v_dmg} damage from being crushed "
                   f"beneath them!|n")
        template = "{actor} lands with {victim} crushed beneath them!"
    else:
        obj.msg(f"|rYou crash hard after {storeys} but {victim_for_obj} "
                f"cushions your impact! You take {g_dmg} damage while they "
                f"are crushed beneath you!|n")
        victim.msg(f"|R{obj_for_victim} uses you as a human cushion during "
                   f"the crash! You take {v_dmg} damage from being crushed!|n")
        template = "{actor} crashes down from above with {victim} taking the brunt of the impact!"
    msg_room_identity(location=room, template=template,
                      char_refs={"actor": obj, "victim": victim},
                      exclude=[obj, victim])
    victim_alive = not victim.is_dead()
    grappler_alive = not obj.is_dead()
    if victim_alive and grappler_alive:
        try:
            from world.combat.handler import get_or_create_combat
            handler = get_or_create_combat(room)
            handler.add_combatant(obj, target=None, initial_grappling=victim,
                                  initial_grappled_by=None, initial_is_yielding=True)
            handler.add_combatant(victim, target=None, initial_grappling=None,
                                  initial_grappled_by=obj, initial_is_yielding=False)
            obj.msg(f"|yYou maintain your grip on {victim_for_obj} after the fall!|n")
            victim.msg(f"|r{obj_for_victim} still has you in their grip after "
                       f"that brutal fall!|n")
        except Exception:  # noqa: BLE001 -- the landing already happened
            logger.log_trace("gravity: grapple restore failed")
            obj.msg(f"|rYour grip on {victim_for_obj} was lost during the fall!|n")
    elif grappler_alive:
        obj.msg(f"|RYou feel {victim_for_obj}'s body go limp in your grip -- "
                f"they didn't survive the fall!|n")
    elif victim_alive:
        victim.msg(f"|gYou feel {obj_for_victim}'s grip loosen as they succumb "
                   f"to their injuries!|n")
    _splat(f"GRAVITY_LAND_BODYSHIELD: {obj.key} on {victim.key} in {room.key} "
           f"made:{made} victim:{v_dmg} grappler:{g_dmg}")


def _land_item(obj, room, cells) -> None:
    """Things do not take damage; they arrive and are heard arriving."""
    _reset_proximity(obj)
    msg_room_identity(
        location=room,
        template="{actor} falls from above and lands with a clatter.",
        char_refs={"actor": obj},
    )
    _splat(f"GRAVITY_LAND_ITEM: {obj.key} landed in {room.key} after {cells} cells")


# --------------------------------------------------------------------------
# damage placement: legs, then limbs, then anything -- from the ground up
# --------------------------------------------------------------------------


def _is_leg_bone(organ) -> bool:
    """A leg is any DESTROYABLE organ that feeds ``moving``. The spine
    feeds it and cannot be destroyed; the pelvis feeds it and carries
    neither flag; only ``can_be_destroyed is True`` yields exactly the
    femurs, tibias and metatarsals (hind legs and paws on a rat). Read
    off the live organ's data so chrome legs (CYBER_LEG) count."""
    spec = getattr(organ, "data", None) or {}
    caps = spec.get("capacities") or ()
    feeds_moving = spec.get("capacity") == "moving" or "moving" in caps
    return feeds_moving and spec.get("can_be_destroyed") is True


def fall_targets(character):
    """``(tier1, tier2, covered_containers)``: the live leg organs from the
    ground up, then the live organs of the other severable limbs (the
    head is not a limb), then the set of containers those two tiers
    cover so tier 3 can avoid them."""
    state = getattr(character, "medical_state", None)
    organs = list(getattr(state, "organs", {}).values()) if state else []
    live = [o for o in organs if getattr(o, "current_hp", 0) > 0]
    species = getattr(getattr(character, "db", None), "species", None) or "human"
    try:
        from world.anatomy import get_species_anatomical_display_order
        order = list(get_species_anatomical_display_order(species))
    except Exception:  # noqa: BLE001 -- an unknown table still falls
        order = []
    index = {loc: i for i, loc in enumerate(order)}

    def ground_up(organ):
        # Later in the display order = lower on the body = filled first.
        return -index.get(getattr(organ, "container", None), -1)

    tier1 = sorted((o for o in live if _is_leg_bone(o)), key=ground_up)
    leg_containers = {o.container for o in tier1}
    try:
        from world.medical.removable import severable_containers
        limbs = [c for c in severable_containers(character)
                 if c not in leg_containers and c != "head"]
    except Exception:  # noqa: BLE001
        limbs = []
    tier2 = sorted((o for o in live if o.container in limbs), key=ground_up)
    covered = set(leg_containers) | set(limbs)
    return tier1, tier2, covered


def apply_fall_damage(character, amount) -> tuple[int, bool]:
    """Fill the body with ``amount`` blunt damage from the feet up. Each
    organ is exhausted before the next; armour on a container softens the
    chunk it receives and the fill moves on (partial fill under armour is
    the honest reading). Stops the instant a chunk kills. Returns
    ``(damage dealt, died)``."""
    amount = int(amount or 0)
    if amount <= 0 or not _is_character(character):
        return 0, False
    if not hasattr(character, "take_damage"):
        return 0, False
    remaining = amount
    dealt = 0
    tier1, tier2, covered = fall_targets(character)
    for organ in tier1 + tier2:
        if remaining <= 0:
            break
        hp = int(getattr(organ, "current_hp", 0) or 0)
        if hp <= 0:
            continue
        chunk = min(remaining, hp)
        died, landed = character.take_damage(
            chunk, location=organ.container, injury_type="blunt",
            target_organ=organ.name)
        remaining -= chunk
        dealt += int(landed or 0)
        if died:
            return dealt, True
    state = getattr(character, "medical_state", None)
    guard = 0
    while remaining > 0 and state is not None and guard < 64:
        guard += 1
        others = [o for o in state.organs.values()
                  if getattr(o, "current_hp", 0) > 0
                  and o.container not in covered]
        if not others:
            break
        organ = random.choice(others)
        chunk = min(remaining, int(organ.current_hp))
        died, landed = character.take_damage(
            chunk, location=organ.container, injury_type="blunt",
            target_organ=organ.name)
        remaining -= chunk
        dealt += int(landed or 0)
        if died:
            return dealt, True
    return dealt, False


# --------------------------------------------------------------------------
# the boot sweep
# --------------------------------------------------------------------------


def sweep_airborne() -> tuple[int, int]:
    """Resume every recorded fall the reload dropped (true remaining time;
    overdue steps run a beat after boot so the world is loaded), and start
    one for anything found in an air cell with no record that cannot stay
    up. Returns ``(resumed, started)``. A logged-out faller has no
    location and is resumed by the reconnect hook instead."""
    from evennia.objects.models import ObjectDB
    resumed = started = 0
    now = time.time()
    for obj in ObjectDB.objects.filter(db_attributes__db_key=DB_FALLING).distinct():
        try:
            record = getattr(obj.db, DB_FALLING, None)
            if not record:
                continue
            if "led_by" in record:
                # A companion marker whose leader is no longer falling is
                # stale: release it or that body can never fall again.
                leader = record.get("led_by")
                if leader is None or getattr(leader, "pk", None) is None \
                        or not is_falling(leader):
                    obj.attributes.remove(DB_FALLING)
                continue
            loc = getattr(obj, "location", None)
            if loc is None:
                continue
            if not is_sky(loc):
                obj.attributes.remove(DB_FALLING)
                continue
            due = float(record.get("next_step_at") or now) - now
            setattr(obj.ndb, NDB_FALL_ACTIVE, True)
            _schedule(obj, max(0.1, due) if due > 0 else 2.0)
            resumed += 1
        except Exception:  # noqa: BLE001 -- one bad row never stops the sweep
            continue
    for room in ObjectDB.objects.filter(db_typeclass_path__contains="rooms"):
        try:
            if not is_sky(room):
                continue
            for obj in list(room.contents):
                if is_stranded_aloft(obj) and start_fall(obj):
                    started += 1
        except Exception:  # noqa: BLE001
            continue
    return resumed, started


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def _clear(obj) -> None:
    """Forget the fall -- and release any companion the record names, so a
    body once dragged off a roof never keeps a marker that would stop it
    falling for the rest of its life."""
    # An Evennia db dict is a _SaverDict (a Mapping, NOT a dict subclass).
    record = getattr(getattr(obj, "db", None), DB_FALLING, None)
    companion = record.get("companion") if isinstance(record, Mapping) else None
    try:
        obj.attributes.remove(DB_FALLING)
    except Exception:  # noqa: BLE001
        pass
    for key in (NDB_FALL_ACTIVE, NDB_FALL_INTENT, NDB_LEAP):
        try:
            delattr(obj.ndb, key)
        except AttributeError:
            pass
    if companion is not None:
        _release_companion(companion, obj)


def _release_companion(companion, leader) -> None:
    """Remove the companion's marker record iff it points at this leader."""
    try:
        record = getattr(companion.db, DB_FALLING, None)
        if isinstance(record, Mapping) and "led_by" in record \
                and record.get("led_by") in (leader, None):
            companion.attributes.remove(DB_FALLING)
    except Exception:  # noqa: BLE001
        pass


def _clear_escort(obj) -> None:
    """A body in free fall is escorting nobody: `usher_escortee` would
    otherwise refuse every fall step at the sky block."""
    try:
        if getattr(obj.db, "escorting", None):
            obj.db.escorting = None
    except Exception:  # noqa: BLE001
        pass


def _interrupt(obj) -> None:
    """A channeling character cannot be moved by a hooked step
    (at_pre_move refuses); break the act first, the way a drag does."""
    try:
        from world.channeled import interrupt_channel
        interrupt_channel(obj)
    except Exception:  # noqa: BLE001 -- fail open
        pass


def _reset_proximity(obj) -> None:
    """Every cell is a new room: melee proximity and the item's universal
    list are stale the moment the body leaves."""
    try:
        if _is_character(obj):
            from world.combat.proximity import clear_proximity_on_room_change
            clear_proximity_on_room_change(obj)
        else:
            setattr(obj.ndb, NDB_PROXIMITY_UNIVERSAL, [])
    except Exception:  # noqa: BLE001
        pass


def _splat(text: str) -> None:
    try:
        from world.combat.debug import get_splattercast
        channel = get_splattercast()
        if channel is not None:
            channel.msg(text)
    except Exception:  # noqa: BLE001 -- no channel under test
        pass
