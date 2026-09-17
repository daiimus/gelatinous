"""Builder quality-of-life: ``@room`` (one surface for a room's whole
profile) and ``@building`` (audit a structure at a glance).

Room "dressing" was scattered across five touches — ``db.type``,
``crowd_base_level``, ``outside``, sense layers, coordinates — and
reviewing a building meant shell archaeology. These two commands make
the profile visible and settable in place, and make drift (a street
crowd pool indoors, an untyped rooftop, a missing sense layer) a look
instead of an investigation.
"""

from evennia import default_cmds

#: The sense layers a room can author (visual = db.desc itself).
_SENSE_KEYS = ("auditory", "olfactory", "tactile", "atmospheric")


def _room_profile_lines(room, caller):
    """The full dressing of one room, as report lines."""
    from world.crowd import crowd_system
    from world.crowd.crowd_messages import crowd_profile_for_room_type
    from world.spatial import get_xyz

    rtype = room.db.type
    base = room.db.crowd_base_level
    lines = [
        f"|w{room.get_display_name(caller)}|n  "
        f"[{room.typeclass_path.rsplit('.', 1)[-1]}]",
        f"  type:    {rtype!r}  (crowd pool: "
        f"{crowd_profile_for_room_type(rtype)})",
        f"  crowd:   base {base!r}, computed "
        f"{crowd_system.calculate_crowd_level(room)}"
        + ("  |x(base 0 = crowd messages disabled)|n" if not base else ""),
        f"  outside: {room.db.outside!r}",
        f"  coords:  {get_xyz(room)}",
    ]
    senses = room.db.sense_descs or {}
    have = [k for k in _SENSE_KEYS if (senses.get(k) or "").strip()]
    missing = [k for k in _SENSE_KEYS if k not in have]
    desc_len = len(room.db.desc or "")
    lines.append(f"  desc:    {desc_len} chars"
                 + ("  |r(none)|n" if not desc_len else ""))
    lines.append(f"  senses:  {', '.join(have) or '|x(none authored)|n'}"
                 + (f"  |xmissing: {', '.join(missing)}|n" if missing and have
                    else ""))
    doors = _door_states(room)
    if doors:
        lines.append(f"  doors:   {doors}")
    return lines


def _door_states(room):
    """'west locked, south open' — every doored exit in the room."""
    out = []
    for ex in (getattr(room, "exits", None) or []):
        if getattr(ex.db, "door_closed", None) is None \
                and getattr(ex.db, "door_locked", None) is None:
            continue
        if getattr(ex.db, "door_locked", None) is True:
            state = "locked"
        elif getattr(ex.db, "door_closed", None) is True:
            state = "closed"
        else:
            state = "open"
        out.append(f"{ex.key} {state}")
    return ", ".join(out)


class CmdRoomProfile(default_cmds.MuxCommand):
    """
    View or set a room's whole profile in one place.

    Usage:
        @room                     - this room's full profile
        @room/type <room type>    - set db.type ("cube hotel", "street", ...)
        @room/crowd <n>           - set crowd_base_level (0 disables crowd)
        @room/outside on|off      - set the outside flag (weather exposure)

    The profile shows the room type and which crowd message pool it
    routes to, the base and computed crowd level, the outside flag,
    coordinates, description length, authored sense layers, and any
    door states — everything that decides how the room reads, on one
    screen. Setting a type reports its crowd-pool routing immediately,
    so a street pool indoors is caught at set time.

    Sense layers are authored in build scripts by writing
    |wroom.db.sense_descs|n — |w@room|n only shows them; coordinates
    come from |w@coordseed|n.
    """

    key = "@room"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        room = caller.location
        if room is None:
            caller.msg("You are nowhere.")
            return
        switches = self.switches or []
        args = (self.args or "").strip()

        if "type" in switches:
            if not args:
                caller.msg("Usage: @room/type <room type>")
                return
            from world.crowd.crowd_messages import crowd_profile_for_room_type
            room.db.type = args
            caller.msg(f"type = {args!r} — crowd pool: "
                       f"|w{crowd_profile_for_room_type(args)}|n.")
            return
        if "crowd" in switches:
            try:
                level = int(args)
            except (TypeError, ValueError):
                caller.msg("Usage: @room/crowd <whole number>")
                return
            room.db.crowd_base_level = level
            caller.msg(f"crowd_base_level = {level}"
                       + (" (crowd messages disabled)" if level == 0 else ""))
            return
        if "outside" in switches:
            if args.lower() not in ("on", "off"):
                caller.msg("Usage: @room/outside on|off")
                return
            room.db.outside = args.lower() == "on"
            caller.msg(f"outside = {room.db.outside}")
            return

        caller.msg("\n".join(_room_profile_lines(room, caller)))


class CmdBuildingAudit(default_cmds.MuxCommand):
    """
    Audit a whole structure at a glance.

    Usage:
        @building <key prefix>    - every room whose name starts with this
        @building/radius [cells]  - every on-grid room within N cells (default 3)

    One row per room: type, crowd (base/computed), coordinates, authored
    sense layers (a/o/t/s), and door states. Drift — a street crowd pool
    indoors, an untyped room, a missing sense layer, a door left
    unlocked — reads straight off the table.
    """

    key = "@building"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def _rooms_by_prefix(self, prefix):
        from evennia.objects.models import ObjectDB
        return list(ObjectDB.objects.filter(
            db_key__istartswith=prefix,
            db_typeclass_path__startswith="typeclasses.rooms"))

    def _rooms_by_radius(self, center_xyz, cells):
        from evennia.objects.models import ObjectDB
        from world.spatial import get_xyz
        out = []
        for room in ObjectDB.objects.filter(
                db_typeclass_path__startswith="typeclasses.rooms",
                db_attributes__db_key="xyz").distinct():
            xyz = get_xyz(room)
            if xyz is None:
                continue
            if (max(abs(xyz[0] - center_xyz[0]), abs(xyz[1] - center_xyz[1]))
                    + abs(xyz[2] - center_xyz[2])) <= cells:
                out.append(room)
        return out

    def func(self):
        caller = self.caller
        switches = self.switches or []
        args = (self.args or "").strip()

        if "radius" in switches:
            from world.spatial import get_xyz
            here = get_xyz(caller.location)
            if here is None:
                caller.msg("This room is off-grid — no radius to audit.")
                return
            try:
                cells = int(args) if args else 3
            except (TypeError, ValueError):
                caller.msg("Usage: @building/radius [whole number of cells]")
                return
            rooms = self._rooms_by_radius(here, cells)
            title = f"within {cells} cell(s) of here"
        else:
            if not args:
                caller.msg("Usage: @building <key prefix>  or  "
                           "@building/radius [cells]")
                return
            rooms = self._rooms_by_prefix(args)
            title = f"matching '{args}'"

        if not rooms:
            caller.msg(f"No rooms {title}.")
            return

        from evennia.utils.evtable import EvTable
        from world.crowd import crowd_system
        from world.spatial import get_xyz

        rooms.sort(key=lambda r: (get_xyz(r) or (0, 0, 99),))
        table = EvTable("|wroom|n", "|wtype|n", "|wcrowd|n", "|wxyz|n",
                        "|wsenses|n", "|wdoors|n", border="cells")
        for room in rooms:
            senses = room.db.sense_descs or {}
            flags = "".join(k[0] if (senses.get(k) or "").strip() else "-"
                            for k in _SENSE_KEYS)
            base = room.db.crowd_base_level
            table.add_row(
                f"{room.key[:30]} ({room.dbref})",
                str(room.db.type or "|r—|n"),
                f"{base if base is not None else '—'}/"
                f"{crowd_system.calculate_crowd_level(room)}",
                str(get_xyz(room) or "|roff-grid|n"),
                flags,
                _door_states(room) or "—",
            )
        caller.msg(f"|w{len(rooms)} room(s) {title}:|n\n{table}")


# ---------------------------------------------------------------------------
# @airfill — generate the aerial lattice (parkour substrate, 2026-07-13).
# The atom is hand-proven at "In the Air" #190: a SkyRoom over the street,
# plain exits out to adjacent rooftops, a one-way `down` fall edge, and
# jump-only exits FROM the rooftops in: always an EDGE (jump off into the
# cell), and a GAP only when another walkable surface stands exactly one
# cell across, in which case the far perch is written with it (#3415 --
# a gap without a perch is refused on the roof, so the generator never
# stamps one). This command stamps that atom over empty cells so rooftop
# routes exist wherever the geometry allows, and `@airfill/audit` reports
# where the built world falls short of it (#3582).
# ---------------------------------------------------------------------------

#: Cardinal steps the lattice links across (diagonals read badly in jumps).
_AIR_STEPS = {"north": (0, 1), "south": (0, -1),
              "east": (1, 0), "west": (-1, 0)}
_AIR_BACK = {"north": "south", "south": "north",
             "east": "west", "west": "east"}
_AIR_ALIAS = {"north": "n", "south": "s", "east": "e", "west": "w"}

_AIR_DESC = (
    "Open air over the colony. Wind owns this space — it leans on you "
    "in gusts that smell of the processor and the streets below, and "
    "there is nothing up here to hold. The grid spreads underneath: "
    "rooflines, laundry, light. Gravity is patient."
)


def _room_cell_index():
    """Every on-grid room, keyed by (x, y, z)."""
    from evennia.objects.models import ObjectDB
    from world.spatial import get_xyz
    index = {}
    for room in ObjectDB.objects.filter(
            db_typeclass_path__startswith="typeclasses.rooms",
            db_attributes__db_key="xyz").distinct():
        xyz = get_xyz(room)
        if xyz:
            index[xyz] = room
    return index


def _is_sky(room):
    return getattr(getattr(room, "db", None), "is_sky_room", None) is True


def _is_walkable_surface(room):
    """A rooftop or any outdoor room that is not air: somewhere a body can
    stand beside the sky. Interiors never qualify (the B-line incident)."""
    if room is None or _is_sky(room):
        return False
    db = getattr(room, "db", None)
    return (getattr(db, "type", None) == "rooftop"
            or getattr(db, "outside", None) is True)


#: The four diagonals, for the audit's tally only -- the lattice never
#: links across them (diagonals read badly in jumps).
_AIR_DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def air_candidates(z, index, box=None):
    """Empty cells at *z* worth filling: at least one NON-sky neighbour
    at the same level (a rooftop to jump from — sky neighbours don't
    seed, so re-runs never balloon outward) and an occupied cell
    directly below (somewhere for gravity to deliver you)."""
    out, seen = [], set()
    for (x, y, cz), room in index.items():
        if cz != z or _is_sky(room):
            continue
        for dx, dy in _AIR_STEPS.values():
            cell = (x + dx, y + dy, z)
            if cell in index or cell in seen:
                continue
            if box and not (box[0] <= cell[0] <= box[2]
                            and box[1] <= cell[1] <= box[3]):
                continue
            if (cell[0], cell[1], z - 1) not in index:
                continue
            seen.add(cell)
            out.append(cell)
    return sorted(out)


def fill_air_cell(cell, index):
    """Stamp the parkour atom at *cell*: SkyRoom + fall edge + links.
    Returns (room, exits_created). Never stomps an existing exit."""
    from evennia import create_object
    from world.spatial import set_xyz
    x, y, z = cell
    room = create_object("typeclasses.rooms.SkyRoom", key="In the Air",
                         location=None)
    room.db.desc = _AIR_DESC
    room.db.crowd_base_level = 0        # nobody loiters in mid-air
    set_xyz(room, x, y, z)
    index[cell] = room
    made = 0

    def _exit(source, dest, key, **flags):
        nonlocal made
        for ex in (getattr(source, "exits", None) or []):
            if ex.key == key:
                return                   # never stomp authored geometry
        ex = create_object("typeclasses.exits.Exit", key=key,
                           aliases=[_AIR_ALIAS.get(key, key[0])],
                           location=source, destination=dest)
        for attr, value in flags.items():
            setattr(ex.db, attr, value)
        made += 1

    below = index.get((x, y, z - 1))
    if below is not None:
        _exit(room, below, "down")       # one-way: gravity's edge
    for direction, (dx, dy) in _AIR_STEPS.items():
        neighbour = index.get((x + dx, y + dy, z))
        if neighbour is None:
            continue
        if _is_sky(neighbour):
            _exit(room, neighbour, direction)
            _exit(neighbour, room, _AIR_BACK[direction])
        elif _is_walkable_surface(neighbour):
            # air reaches a walkable OUTDOOR surface plainly; its way IN
            # is a jump. Always an EDGE (jump off into this cell). A GAP
            # only when another walkable surface stands exactly one cell
            # across, and then the far perch is written with it -- a gap
            # exit with no perch is refused on the roof (#3579), so
            # stamping one would build a crossing nobody can make (#3415).
            _exit(room, neighbour, direction)
            far = index.get((x - dx, y - dy, z))
            flags = {"is_edge": True}
            if _is_walkable_surface(far):
                flags.update(is_gap=True, gap_destination=far.id)
            _exit(neighbour, room, _AIR_BACK[direction], **flags)
        # interiors get NO links: the helper cannot tell a rooftop from
        # an apartment behind a wall, and it once gave six tenants
        # jump-out-window edges (the B-line incident, 2026-07-25)
    return room, made


def audit_air(z, index):
    """The edge audit (#3582), read-only: where the built world at *z*
    falls short of the atom. Returns a dict of findings:

    - ``missing_edges``: ``(room, cell, direction)`` for every walkable
      surface with an air cell beside it (cardinal) and no ``is_edge``
      exit into that cell. A room carrying ``db.no_edge = "<reason>"``
      is deliberate and skipped.
    - ``bad_gaps``: ``(exit, reason)`` for every ``is_gap`` exit whose
      far perch is missing, unresolvable, not a walkable surface, or not
      exactly one cell across the air it leads into.
    - ``bare_cells``: air cells with no ``down`` exit (the parked
      impasse, #3581 -- reported, never repaired here).
    - ``diagonal_only``: a count of walkable surfaces that touch air only
      diagonally with no edge, which the lattice never wires.
    """
    from world.gravity import down_exit
    findings = {"missing_edges": [], "bad_gaps": [], "bare_cells": [],
                "diagonal_only": 0}
    level = {xyz: room for xyz, room in index.items() if xyz[2] == z}
    where = {room: xyz for xyz, room in index.items()}
    by_id = {getattr(room, "id", None): room for room in index.values()}

    def edge_into(room, cell):
        for ex in (getattr(room, "exits", None) or []):
            if getattr(ex.db, "is_edge", None) is True \
                    and getattr(ex, "destination", None) is cell:
                return True
        return False

    for (x, y, _z), room in sorted(level.items(), key=lambda kv: kv[0]):
        if _is_sky(room):
            if down_exit(room) is None:
                findings["bare_cells"].append(room)
            continue
        if not _is_walkable_surface(room):
            continue
        if getattr(room.db, "no_edge", None):
            continue                     # deliberate, and the reason is on the room
        for direction, (dx, dy) in _AIR_STEPS.items():
            cell = level.get((x + dx, y + dy, z))
            if cell is None or not _is_sky(cell):
                continue
            if not edge_into(room, cell):
                findings["missing_edges"].append((room, cell, direction))
        touched_diagonally = False
        for dx, dy in _AIR_DIAGONALS:
            cell = level.get((x + dx, y + dy, z))
            if cell is not None and _is_sky(cell) and not edge_into(room, cell):
                touched_diagonally = True
        if touched_diagonally:
            findings["diagonal_only"] += 1

    for (x, y, _z), room in sorted(level.items(), key=lambda kv: kv[0]):
        if _is_sky(room):
            continue
        for ex in (getattr(room, "exits", None) or []):
            if getattr(ex.db, "is_gap", None) is not True:
                continue
            air = getattr(ex, "destination", None)
            if not _is_sky(air):
                findings["bad_gaps"].append((ex, "gap exit does not lead into air"))
                continue
            raw = getattr(ex.db, "gap_destination", None)
            if not raw:
                findings["bad_gaps"].append((ex, "no gap_destination"))
                continue
            perch = raw if not isinstance(raw, (int, str)) else by_id.get(int(raw))
            if perch is None:
                findings["bad_gaps"].append(
                    (ex, f"gap_destination #{raw} does not resolve on the grid"))
                continue
            if not _is_walkable_surface(perch):
                findings["bad_gaps"].append(
                    (ex, "gap_destination is not a walkable surface"))
                continue
            ax, ay, _az = where.get(air, (None, None, None))
            if ax is None:
                continue                 # off-grid air: nothing to measure
            expected = (2 * ax - x, 2 * ay - y, z)
            if where.get(perch) != expected:
                findings["bad_gaps"].append(
                    (ex, f"gap_destination is not one cell across "
                         f"(expected the room at {expected[:2]})"))
    return findings


def format_air_audit(z, findings, index):
    """The audit as the builder reads it. Every row carries a dbref and a
    coordinate; the last line says whether it is clean."""
    where = {room: xyz for xyz, room in index.items()}

    def at(room):
        xyz = where.get(room)
        return f"#{getattr(room, 'id', '?')} at ({xyz[0]},{xyz[1]})" if xyz \
            else f"#{getattr(room, 'id', '?')}"

    lines = [f"|wEdge audit at z={z}|n |x(read-only -- nothing written)|n"]
    for room, cell, direction in findings["missing_edges"]:
        lines.append(f"  |ymissing edge|n  {room.key} {at(room)}: air to the "
                     f"{direction} (#{getattr(cell, 'id', '?')}) with no is_edge "
                     f"exit into it")
    for ex, reason in findings["bad_gaps"]:
        src = getattr(ex, "location", None)
        lines.append(f"  |rbad gap|n       {getattr(src, 'key', '?')} "
                     f"{at(src)} exit '{ex.key}' (#{getattr(ex, 'id', '?')}): {reason}")
    for cell in findings["bare_cells"]:
        lines.append(f"  |xbare cell|n     {cell.key} {at(cell)}: no down "
                     f"(the parked impasse, #3581)")
    if findings["diagonal_only"]:
        lines.append(f"  |x{findings['diagonal_only']} surface(s) touch air only "
                     f"diagonally with no edge; the lattice never wires diagonals.|n")
    problems = (len(findings["missing_edges"]) + len(findings["bad_gaps"])
                + len(findings["bare_cells"]))
    lines.append("|gClean.|n" if not problems else
                 f"|y{problems} finding(s).|n Mark a deliberate omission with "
                 f"`db.no_edge = \"<reason>\"` on the room.")
    return "\n".join(lines)


class CmdAirFill(default_cmds.MuxCommand):
    """
    Fill the sky: generate aerial transit cells over the colony.

    Usage:
        @airfill/check <z>                    - dry run: report, write nothing
        @airfill/audit <z>                    - the edge audit: report, write nothing
        @airfill <z>                          - fill every eligible cell at z
        @airfill <z> = <x1,y1> : <x2,y2>      - limit to a bounding box

    A cell qualifies when it is empty, has at least one non-sky room
    beside it at the same level (a rooftop to jump from), and has an
    occupied cell directly below (somewhere to fall). Each new cell is a
    SkyRoom (jump-only, no exit display, civilians excluded) with a
    one-way |wdown|n fall edge, plain exits onto adjacent rooftops, and
    jump-only exits from those rooftops in: |wis_edge|n always, and
    |wis_gap|n with its |wgap_destination|n only where another walkable
    surface stands one cell across — the hand-built "In the Air" atom,
    stamped wherever geometry allows. Existing exits are never
    overwritten; re-runs only add what's missing.

    |w/audit|n closes an air build: it lists every walkable surface beside
    air with no edge into it, every gap whose far perch is missing or not
    one cell across, and every air cell with no |wdown|n. Nothing is
    written. Mark a deliberate omission with |wdb.no_edge = "<reason>"|n
    on the room and the audit skips it.
    """

    key = "@airfill"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        parts = (self.lhs or self.args or "").strip()
        box = None
        if self.rhs:
            try:
                a, b = self.rhs.split(":")
                x1, y1 = (int(v) for v in a.split(","))
                x2, y2 = (int(v) for v in b.split(","))
                box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            except (TypeError, ValueError):
                caller.msg("Usage: @airfill <z> = <x1,y1> : <x2,y2>")
                return
        try:
            z = int(parts)
        except (TypeError, ValueError):
            caller.msg("Usage: @airfill[/check] <z> [= x1,y1 : x2,y2]")
            return
        if z < 1:
            caller.msg("The sky starts at z=1 — ground level is not air.")
            return

        index = _room_cell_index()
        if "audit" in (self.switches or []):
            caller.msg(format_air_audit(z, audit_air(z, index), index))
            return
        cells = air_candidates(z, index, box=box)
        if not cells:
            caller.msg(f"No eligible empty cells at z={z}"
                       + (" in that box." if box else "."))
            return
        if "check" in (self.switches or []):
            caller.msg(f"|gWould fill {len(cells)} cell(s) at z={z}:|n "
                       + ", ".join(f"({x},{y})" for x, y, _ in cells[:30])
                       + (" ..." if len(cells) > 30 else "")
                       + "\n|y(dry run — nothing was written)|n")
            return
        if len(cells) > 300:
            caller.msg(f"|r{len(cells)} cells is a lot of sky|n — narrow "
                       "it with a bounding box, or run /check first.")
            return
        rooms = 0
        exits = 0
        for cell in cells:
            _, made = fill_air_cell(cell, index)
            rooms += 1
            exits += made
        caller.msg(f"|gFilled {rooms} air cell(s) at z={z}|n "
                   f"({exits} exits hung, existing geometry untouched).")
