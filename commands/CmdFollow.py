"""``follow`` / ``escort`` — voluntary movement coupling.

Follow is ungated self-action (you trail someone, openly). Escort is the
trust-gated lead (TRUST_AND_CONSENT_SPEC §3 ``escort`` class): the escortee
is ushered through each exit AHEAD of the leader. Forcible movement is NOT
here — dragging is emergent from grapple + movement, no command by design.
"""

from evennia import Command

from world.identity_utils import msg_room_identity
from world.movement_coupling import sever_follow


def _resolve_present_character(caller, phrase):
    """A character here, by identity-aware search. Not yourself."""
    target = caller.search(phrase)
    if target is None:
        return None
    if target is caller:
        caller.msg("You can't couple your movement to yourself.")
        return None
    if not hasattr(target, "get_sdesc"):
        caller.msg(f"{target.get_display_name(caller)} doesn't go anywhere.")
        return None
    return target


class CmdFollow(Command):
    """
    Follow someone — trail them through exits as they move.

    Usage:
        follow <person>
        stop following

    You couple your own movement to theirs: when they leave a room, you
    take the same exit right after them (a follower moves second). It's
    open — they see you fall in behind them. You stop with ``stop
    following``, and you lose the trail naturally if you can't keep up
    (a door that refuses you, being unable to move).

    ``stop following`` also breaks away from someone escorting you.
    """

    key = "follow"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Follow whom?")
            return
        target = _resolve_present_character(caller, args)
        if target is None:
            return
        if caller.db.escorting == target:
            caller.msg("You're escorting them — they move with you already.")
            return
        if caller.db.following == target:
            caller.msg(
                f"You're already following {target.get_display_name(caller)}."
            )
            return
        caller.db.following = target
        caller.msg(f"You fall in behind {target.get_display_name(caller)}.")
        target.msg(f"{caller.get_display_name(target)} falls in behind you.")
        msg_room_identity(
            location=caller.location,
            template="{actor} falls in behind {target}.",
            char_refs={"actor": caller, "target": target},
            exclude=[caller, target],
        )


class CmdStopFollowing(Command):
    """
    Stop following (or break away from an escort).

    Usage:
        stop following
    """

    key = "stop following"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.db.following:
            sever_follow(caller)
            return
        # Break away from anyone escorting us — it's our movement.
        location = caller.location
        escorts = [obj for obj in (location.contents if location else [])
                   if getattr(obj.db, "escorting", None) == caller]
        if escorts:
            for leader in escorts:
                leader.db.escorting = None
                leader.msg(
                    f"{caller.get_display_name(leader)} breaks away from "
                    f"your lead."
                )
            caller.msg("You break away.")
            return
        caller.msg("You aren't following anyone.")


class CmdEscort(Command):
    """
    Escort someone — lead them along as you move.

    Usage:
        escort <person>
        stop escorting

    Your escort moves FIRST: each time you take an exit, they are ushered
    through ahead of you and you come behind. A conscious, free person
    must have trusted you to escort them (``trust <you> to escort``);
    someone restrained (cuffed, grappled by another) can be led without
    asking — and someone unconscious can't walk at all (drag them by
    grapple instead). Consent is re-checked at every move: a revoked
    grant releases them at the next doorway.
    """

    key = "escort"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Escort whom?")
            return
        target = _resolve_present_character(caller, args)
        if target is None:
            return
        if caller.db.following == target:
            caller.msg("You're following them — you can't also lead them.")
            return
        from world.consent import check_consent, is_conscious
        if not is_conscious(target):
            caller.msg(
                f"{target.get_display_name(caller)} can't walk anywhere — "
                f"carry or drag them."
            )
            return
        if not check_consent(caller, target, "escort"):
            caller.msg(
                f"{target.get_display_name(caller)} is conscious and won't "
                f"be led — they'd need to trust you to escort them (or be "
                f"restrained)."
            )
            return
        if caller.db.escorting and caller.db.escorting != target:
            old = caller.db.escorting
            caller.msg(
                f"You stop escorting {old.get_display_name(caller)}."
            )
        caller.db.escorting = target
        caller.msg(f"You take {target.get_display_name(caller)} under your "
                   f"lead — they'll move ahead of you.")
        target.msg(f"{caller.get_display_name(target)} takes you under "
                   f"their lead.")
        msg_room_identity(
            location=caller.location,
            template="{actor} takes {target} under their lead.",
            char_refs={"actor": caller, "target": target},
            exclude=[caller, target],
        )


class CmdStopEscorting(Command):
    """
    Release your escort.

    Usage:
        stop escorting
    """

    key = "stop escorting"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        escortee = caller.db.escorting
        if not escortee:
            caller.msg("You aren't escorting anyone.")
            return
        caller.db.escorting = None
        caller.msg(f"You release {escortee.get_display_name(caller)} from "
                   f"your lead.")
        try:
            escortee.msg(f"{caller.get_display_name(escortee)} releases you "
                         f"from their lead.")
        except Exception:  # noqa: BLE001
            pass
