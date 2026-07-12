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
