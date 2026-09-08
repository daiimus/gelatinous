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
        from world.stealth import is_hidden_from

        # ONLY PEOPLE WHO CAN PERCEIVE YOU SEE YOU SEARCHING (#2562).
        # `msg_room_identity` does no perception filtering — it walks
        # `location.contents`, skips the exclude set, and messages
        # everyone else. So a HIDDEN character running `search` announced
        # themselves to the very observers who cannot see them, and
        # stayed hidden afterwards, so those same observers still could
        # not target or even list the person they had just been told
        # about.
        #
        # `is_hidden_from` is the display gate the rest of the codebase
        # uses for exactly this question — `CmdCommunication` filters a
        # whisper's bystanders on it, because a whisper is a visual
        # event. So is a search.
        unseen_by = [obj for obj in caller.location.contents
                     if obj is not caller and is_hidden_from(caller, obj)]
        msg_room_identity(
            location=caller.location,
            template="{actor} searches the area carefully.",
            char_refs={"actor": caller},
            exclude=[caller] + unseen_by,
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
