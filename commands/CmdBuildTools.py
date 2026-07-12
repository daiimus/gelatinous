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

    Sense layers are authored with |w@roomsense|n; coordinates come
    from |w@coordseed|n.
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
# is_edge+is_gap exits FROM the rooftops in (jump-only). This command
# stamps that atom over empty cells so rooftop routes exist wherever the
# geometry allows.
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
        else:
            # air reaches the roof plainly; the roof's way IN is a jump
            _exit(room, neighbour, direction)
            _exit(neighbour, room, _AIR_BACK[direction],
                  is_edge=True, is_gap=True)
    return room, made


class CmdAirFill(default_cmds.MuxCommand):
    """
    Fill the sky: generate aerial transit cells over the colony.

    Usage:
        @airfill/check <z>                    - dry run: report, write nothing
        @airfill <z>                          - fill every eligible cell at z
        @airfill <z> = <x1,y1> : <x2,y2>      - limit to a bounding box

    A cell qualifies when it is empty, has at least one non-sky room
    beside it at the same level (a rooftop to jump from), and has an
    occupied cell directly below (somewhere to fall). Each new cell is a
    SkyRoom (jump-only, no exit display, civilians excluded) with a
    one-way |wdown|n fall edge, plain exits onto adjacent rooftops, and
    |wis_edge+is_gap|n exits from those rooftops in — the hand-built
    "In the Air" atom, stamped wherever geometry allows. Existing exits
    are never overwritten; re-runs only add what's missing.
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
