"""``hide`` / ``unhide`` / ``sneak`` / ``search`` — presence concealment.

STEALTH_AND_DETECTION_SPEC §3.3. The contest engine and awareness store live
in ``world/stealth.py``; these commands are the player surface. Identity
concealment (disguises) and phase are separate axes — this is only about
whether you're NOTICED.
"""

from evennia import Command

from world.grammar import capitalize_first
from world.stealth import (
    active_search, attempt_hide, break_stealth,
)


class CmdHide(Command):
    """
    Slip out of sight — or stash an object.

    Usage:
        hide
        hide <object>
        unhide

    Hiding is a contest: everyone watching rolls to keep track of you.
    Those who win see exactly what you are — someone lurking. Those who
    lose forget you're there until they search, stumble over you, or you
    give yourself away (speaking, attacking, or walking off openly all
    break hiding; use ``sneak`` to move while staying hidden).

    ``hide <object>`` stashes an item from your inventory somewhere in
    the room — a searcher may turn it up.
    """

    key = "hide"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if args:
            self._stash(args)
            return
        if caller.db.hidden:
            caller.msg("You're already keeping out of sight.")
            return
        # Owner, 2026-10-24 (#3763): "You shouldn't be able to hide while
        # someone is aiming at you or fighting you."
        from world.combat.constants import (NDB_AIMED_AT_BY, NDB_AIMING_AT,
                                            NDB_COMBAT_HANDLER)
        if getattr(caller.ndb, NDB_COMBAT_HANDLER, None):
            caller.msg("You can't slip out of sight in the middle of a fight.")
            return
        aimer = getattr(caller.ndb, NDB_AIMED_AT_BY, None)
        if (aimer is not None
                and getattr(aimer, "location", None) == caller.location
                and getattr(aimer.ndb, NDB_AIMING_AT, None) == caller):
            caller.msg("You can't slip out of sight with a weapon trained on you.")
            return
        kept = attempt_hide(caller)
        caller.msg("You slip out of sight.")
        for observer in kept:
            observer.msg(
                f"{capitalize_first(caller.get_display_name(observer))} "
                f"tries to melt out of sight — but you keep track of them."
            )

    def _stash(self, phrase):
        caller = self.caller
        item = caller.search(phrase, location=caller, quiet=True)
        if not item:
            caller.msg(f"You aren't carrying '{phrase}'.")
            return
        if isinstance(item, list):
            item = item[0]
        if not caller.location:
            return
        # A trap is in plain sight to anyone in the room with it (#3767;
        # owner, 2026-10-24: "You shouldn't be able to hide a rigged
        # grenade or charge."). Live means the pin is out; rigged means
        # it is wired to an exit.
        # Strict `is True`, as break_stealth reads db.hidden: a test double
        # with auto-attributes must not read as a live device.
        if item.db.is_explosive is True and (item.db.pin_pulled is True
                                             or item.db.rigged_to_exit is not None):
            caller.msg(f"{item.get_display_name(caller)} is live. A trap is in "
                       "plain sight to anyone in the room with it.")
            return
        from random import randint

        # THE SAME GUARDS `drop` OWES (#2561). This used to be a bare
        # `move_to`, and `caller.search(phrase, location=caller)`
        # searches `caller.contents` — which holds worn clothing and
        # held weapons alike. So `hide <garment>` stashed something you
        # were wearing, `hide <weapon>` left the hand slot still
        # pointing at an item now lying on the floor (the fourth
        # instance of the PR-H2 derived-view desync), and integrated
        # cyberware could be posted out of your own arm. One word, no
        # guards.
        from commands.CmdInventory import release_to_ground
        ok, refusal, _hand = release_to_ground(caller, item)
        if not ok:
            if refusal:
                caller.msg(refusal)
            return
        item.db.hidden = True
        # The stash quality is rolled once, at stash time — the hider's
        # craft frozen into the hiding spot for later searches to beat.
        item.db.stash_roll = randint(1, 20) + int(
            getattr(caller, "motorics", 1) or 1)
        caller.msg(f"You stash {item.get_display_name(caller)} out of sight.")


class CmdUnhide(Command):
    """
    Step out of hiding.

    Usage:
        unhide
    """

    key = "unhide"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not caller.db.hidden:
            caller.msg("You aren't hiding.")
            return
        break_stealth(caller, quiet=True)
        caller.msg("You step out of hiding.")
        from world.identity_utils import msg_room_identity
        if caller.location:
            msg_room_identity(
                location=caller.location,
                template="{actor} steps out of hiding.",
                char_refs={"actor": caller},
                exclude=[caller],
            )


class CmdSneak(Command):
    """
    Move while staying hidden.

    Usage:
        sneak <exit>

    Carries you through an exit and re-attempts concealment on arrival —
    a fresh contest against everyone in the new room, at a penalty
    (hiding on the move is harder than hiding from cover). Anyone still
    tracking you in the room you leave sees you slip away.
    """

    key = "sneak"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Sneak where?")
            return
        location = caller.location
        exit_obj = None
        for obj in (location.contents if location else []):
            if not getattr(obj, "destination", None):
                continue
            names = [obj.key.lower()] + [a.lower() for a in (obj.aliases.all()
                                                             if obj.aliases
                                                             else [])]
            if args.lower() in names:
                exit_obj = obj
                break
        if exit_obj is None:
            caller.msg(f"There's no way '{args}' from here.")
            return
        # DON'T PAY THE CONTEST FOR A MOVE THAT CANNOT HAPPEN (#2563).
        #
        # The hide below has to come BEFORE the move — that is the point
        # of the comment: witnesses in the room you are LEAVING get their
        # contest, so they can keep track of your exit. But the old order
        # discovered whether the move was even possible only afterwards,
        # by comparing locations, and returned with no rollback. A
        # refused traversal left you silently hidden with every watcher's
        # awareness already rolled and stamped, from an action that did
        # not happen.
        #
        # The cheap half is checkable up front: a locked or unusable exit
        # is refused here, before anything is rolled.
        try:
            passable = exit_obj.access(caller, "traverse")
        except Exception:  # noqa: BLE001 — an unreadable lock is not a refusal
            passable = True
        if not passable:
            caller.msg("You can't get through that way.")
            return

        was_hidden = bool(caller.db.hidden)
        if not caller.db.hidden:
            # sneaking implies hiding: contest in the CURRENT room first,
            # so witnesses here may keep track of your exit
            attempt_hide(caller)
        caller.ndb.sneaking = True
        try:
            caller.execute_cmd(exit_obj.key)
        finally:
            caller.ndb.sneaking = None
        if caller.location is location:
            # Refused by something `access` cannot see — combat, an
            # aim-lock, a sky edge. Put back what we can: the hidden
            # flag. The awareness stamps already written cannot be
            # unrolled, and that is worth knowing rather than pretending
            # otherwise — but at least the state a player can observe
            # matches the action that failed.
            if not was_hidden:
                caller.db.hidden = False
            caller.msg("You can't get through that way.")
            return
        kept = attempt_hide(caller, sneak=True)
        caller.msg("You slip through, keeping to the edges.")
        for observer in kept:
            observer.msg(
                f"You catch {caller.get_display_name(observer)} slipping in."
            )
            # An LLM brain ignores the room's arrival notice while a body
            # is mid-sneak (awareness is stale until this contest runs)
            # and the cue above is plain text its hook never reads. The
            # contest has decided now: the observers who kept track get
            # the arrival, the ones who lost it get nothing (#2589).
            notice = getattr(observer, "notice_presence_change", None)
            if callable(notice):
                notice(caller, True)


class CmdSearch(Command):
    """
    Actively search the area for anything — or anyone — hidden.

    Usage:
        search

    A deliberate sweep of the room: stronger than the glance you get by
    walking in or looking around. Turns up hidden characters (for you)
    and stashed objects (for everyone). Searching is visible — people
    can see you hunting.
    """

    key = "search"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not caller.location:
            return
        from world.identity_utils import msg_room_identity

        # SEARCHING REVEALS YOU (#3769; owner, 2026-10-25: "Search
        # reveals"). This supersedes #2562, which hid the line from the
        # observers who could not see the searcher and left them hidden:
        # the announcer now breaks the hide first, so those observers read
        # "... emerges from concealment." and then the search, and can
        # target the person they were just told about.
        msg_room_identity(
            location=caller.location,
            template="{actor} searches the area carefully.",
            char_refs={"actor": caller},
            exclude=[caller],
        )
        found_chars, found_objs = active_search(caller)
        from world.stealth import search_hidden_exits
        found_exits = search_hidden_exits(caller)
        if not found_chars and not found_objs and not found_exits:
            caller.msg("You search the area and find nothing out of place.")
            return
        for char in found_chars:
            caller.msg(
                f"You spot {char.get_display_name(caller)} lurking here."
            )
            char.msg(
                f"{capitalize_first(caller.get_display_name(char))}'s "
                f"eyes find you — you've been spotted."
            )
        for obj in found_objs:
            caller.msg(
                f"You turn up {obj.get_display_name(caller)}, "
                f"stashed out of sight."
            )
        for ex in found_exits:
            caller.msg(ex.db.search_found_msg
                       or f"You uncover a hidden way out: {ex.key}.")
