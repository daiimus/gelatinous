"""Door verbs (verticality §2.1) — all real player commands, and the
same verbs NPCs use (the level-playing-field mandate).

    open <door>     - open it (a locked door needs your sleeve granted;
                      opening it granted UNLOCKS it for real)
    close <door>    - shut it
    lock <door>     - shut and seal it (granted sleeves only)
    unlock <door>   - release the lock (granted sleeves only)
    knock <door>    - heard on the far side, attributed by sound only

Builders manage the §2.2 grant file with ``@door``:

    @door <exit>                  - hang a door on an exit pair
    @door/grant <door> = <char>   - add <char>'s sleeve to the grant file
    @door/revoke <door> = <char>  - remove it
    @door/list <door>             - read the grant file
    @door/lock|unlock|open|close <door>  - force state (no sleeve check)
"""

from evennia import Command, default_cmds

from world.access import is_granted, make_grant, sleeve_uid_of


def find_door(caller, arg):
    """A DoorExit in the caller's room matching *arg* (or the only one)."""
    location = caller.location
    if location is None:
        return None
    doors = [ex for ex in (getattr(location, "exits", None) or [])
             if getattr(ex.db, "is_door", None) is True]
    if not doors:
        caller.msg("There's no door here.")
        return None
    arg = (arg or "").strip().lower()
    if not arg or arg == "door":
        if len(doors) == 1:
            return doors[0]
        names = ", ".join(d.key for d in doors)
        caller.msg(f"Which door? ({names})")
        return None
    for door in doors:
        names = [door.key.lower()] + [a.lower() for a in door.aliases.all()]
        if arg in names:
            return door
    caller.msg(f"No door called '{arg}' here.")
    return None


class CmdOpenDoor(Command):
    """
    Open a door.

    Usage:
        open <door>

    A locked door reads your sleeve: granted, it unlocks and opens;
    otherwise the reader blinks red. With one door in the room, plain
    ``open door`` works.
    """

    key = "open"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        door = find_door(self.caller, self.args)
        if not door:
            return
        if door.is_open():
            self.caller.msg("It's already open.")
            return
        if door.db.door_locked is True:
            if not is_granted(self.caller, door.db.access_grants):
                self.caller.msg("The reader beside the door blinks |rred|n. "
                                "The lock holds.")
                return
            door._mirror(door_locked=False, door_closed=False)
            self.caller.msg("The reader flashes |ggreen|n; the lock releases "
                            "and you swing the door open.")
        else:
            door._mirror(door_closed=False)
            self.caller.msg("You swing the door open.")
        door._both_rooms_msg("The door swings open.", exclude=[self.caller])


class CmdCloseDoor(Command):
    """
    Close a door.

    Usage:
        close <door>
    """

    key = "close"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        door = find_door(self.caller, self.args)
        if not door:
            return
        if door.db.door_broken is True:
            self.caller.msg("The door hangs broken; it won't close.")
            return
        if not door.is_open():
            self.caller.msg("It's already closed.")
            return
        if door.db.door_autolock is True:
            # the spring latch: anyone may close it, and closing it
            # seals it — restoring security needs no authority
            door._mirror(door_closed=True, door_locked=True)
            self.caller.msg("You pull the door shut; the lock "
                            "re-engages with a |rclunk|n.")
            door._both_rooms_msg("The door swings shut and its lock "
                                 "re-engages with a clunk.",
                                 exclude=[self.caller])
            return
        door._mirror(door_closed=True)
        self.caller.msg("You pull the door shut.")
        door._both_rooms_msg("The door swings shut.", exclude=[self.caller])


class CmdLockDoor(Command):
    """
    Lock a door (closes it first if open). Granted sleeves only.

    Usage:
        lock <door>
    """

    key = "lock"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        door = find_door(self.caller, self.args)
        if not door:
            return
        if door.db.door_broken is True:
            self.caller.msg("The door hangs broken; there's nothing left "
                            "to lock.")
            return
        if not is_granted(self.caller, door.db.access_grants):
            self.caller.msg("The reader blinks |rred|n — this lock doesn't "
                            "answer to your sleeve.")
            return
        if door.db.door_locked is True:
            self.caller.msg("It's already locked.")
            return
        door._mirror(door_closed=True, door_locked=True)
        self.caller.msg("The reader flashes |rred|n; the door seals with a "
                        "solid clunk.")
        door._both_rooms_msg("The reader flashes |rred|n as the door seals "
                             "with a solid clunk.",
                             exclude=[self.caller])


class CmdUnlockDoor(Command):
    """
    Unlock a door (it stays closed). Granted sleeves only.

    Usage:
        unlock <door>
    """

    key = "unlock"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        door = find_door(self.caller, self.args)
        if not door:
            return
        if door.db.door_locked is not True:
            self.caller.msg("It isn't locked.")
            return
        if not is_granted(self.caller, door.db.access_grants):
            self.caller.msg("The reader blinks |rred|n — this lock doesn't "
                            "answer to your sleeve.")
            return
        door._mirror(door_locked=False)
        self.caller.msg("The reader flashes |ggreen|n; the lock releases.")
        door._both_rooms_msg("The reader flashes |ggreen|n; the lock "
                             "releases with a click.",
                             exclude=[self.caller])


class CmdKnock(Command):
    """
    Knock on a door — heard on the far side, attributed by sound only.

    Usage:
        knock <door>
    """

    key = "knock"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        door = find_door(self.caller, self.args)
        if not door:
            return
        if door.is_open():
            self.caller.msg("It's open — just walk through.")
            return
        self.caller.msg("You knock on the door.")
        if door.location:
            door.location.msg_contents("Someone knocks on the door.",
                                       exclude=[self.caller])
        if door.destination:
            door.destination.msg_contents(
                "A knock sounds against the door.")


class CmdDoorAdmin(default_cmds.MuxCommand):
    """
    Hang and administer doors (builder).

    Usage:
        @door <exit>                    - convert an exit pair into a door
        @door/grant <door> = <char>     - add <char>'s sleeve to the grant file
        @door/revoke <door> = <char>    - remove <char>'s sleeve
        @door/list <door>               - read the grant file
        @door/lock <door>               - force-lock (no sleeve check)
        @door/unlock <door>             - force-unlock
        @door/open <door>               - force-open
        @door/close <door>              - force-close
    """

    key = "@door"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        if not self.lhs:
            caller.msg("Usage: @door <exit> (see help @door)")
            return

        # bare form: hang a door on an existing exit pair
        if not self.switches:
            ex = caller.search(self.lhs,
                               candidates=list(caller.location.exits))
            if not ex:
                return
            if getattr(ex.db, "is_door", None) is True:
                caller.msg("That exit is already a door.")
                return
            back = None
            for cand in (getattr(ex.destination, "exits", None) or []):
                if cand.destination is caller.location:
                    back = cand
                    break
            for side in filter(None, (ex, back)):
                side.swap_typeclass("typeclasses.doors.DoorExit",
                                    clean_attributes=False,
                                    run_start_hooks="at_object_creation")
            if back:
                ex.db.door_twin = back
                back.db.door_twin = ex
            caller.msg(f"Door hung on {ex.key}"
                       + (f" / {back.key} (both sides)" if back
                          else " (WARNING: no return exit found — one-sided)")
                       + ". It starts closed and unlocked; use "
                         "@door/grant then lock.")
            return

        door = find_door(caller, self.lhs)
        if not door:
            return
        switch = self.switches[0]

        if switch in ("lock", "unlock", "open", "close"):
            if switch == "lock":
                door._mirror(door_closed=True, door_locked=True)
            elif switch == "unlock":
                door._mirror(door_locked=False)
            elif switch == "open":
                door._mirror(door_closed=False, door_locked=False)
            else:
                door._mirror(door_closed=True)
            caller.msg(f"Door {door.key}: forced {switch}.")
            return

        if switch == "list":
            grants = door.db.access_grants or []
            if not grants:
                caller.msg("Grant file: empty.")
                return
            lines = [f"  sleeve {g.get('sleeve', '?')[:8]}… "
                     f"issued_by={g.get('issued_by')} until={g.get('until')}"
                     for g in grants]
            caller.msg("Grant file:\n" + "\n".join(lines))
            return

        if switch in ("grant", "revoke"):
            if not self.rhs:
                caller.msg(f"Usage: @door/{switch} <door> = <character>")
                return
            target = caller.search(self.rhs, global_search=True)
            if not target:
                return
            uid = sleeve_uid_of(target)
            if not uid:
                caller.msg(f"{target.key} has no sleeve uid — nothing to "
                           f"{switch}.")
                return
            grants = list(door.db.access_grants or [])
            if switch == "grant":
                if any(g.get("sleeve") == uid for g in grants):
                    caller.msg(f"{target.key} is already on the grant file.")
                    return
                grants.append(make_grant(target, issued_by=caller.key))
                door._mirror(access_grants=grants)
                caller.msg(f"Granted: {target.key}'s sleeve now opens "
                           f"{door.key}.")
            else:
                kept = [g for g in grants if g.get("sleeve") != uid]
                door._mirror(access_grants=kept)
                caller.msg(f"Revoked: {target.key}'s sleeve no longer opens "
                           f"{door.key}.")
            return

        caller.msg(f"Unknown switch '/{switch}' (see help @door).")
