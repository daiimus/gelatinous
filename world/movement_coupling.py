"""Movement coupling — follow (trail) and escort (usher ahead).

TRUST_AND_CONSENT_SPEC §9 Phase 3, minus dragging: forcible movement already
exists as an emergent property of grapple + movement (no command, by design).
This module owns the two VOLUNTARY couplings:

* **follow** — self-action, ungated: the follower couples their own movement
  to a leader and moves SECONDARY (leader moves, follower trails through the
  same exit). Open and visible; covert tailing is the stealth spec's future
  ``shadow``.
* **escort** — trust-gated (``escort`` class): the leader ushers the escortee
  AHEAD — the escortee moves FIRST through the exit, the leader comes behind.
  Re-checked per move (spec §7.2: revoking trust takes effect at the next
  step, nothing aborts mid-swing).

Every coupled move is a REAL exit traversal (``execute_cmd(exit.key)``), so
exit locks, movement gates (unconsciousness, combat cmdsets), and the future
motorics-timed movement all apply to coupled movers exactly as to anyone —
the planned per-character movement delay will sequence these beats into
organic chase scenes with no changes here.
"""


def _exit_to(source, destination):
    """The exit object in ``source`` leading to ``destination`` (or None)."""
    if not source or not destination:
        return None
    for obj in source.contents:
        if getattr(obj, "destination", None) == destination:
            return obj
    return None


def _valid(char) -> bool:
    """Object still exists (not deleted mid-link)."""
    return bool(char and getattr(char, "pk", None))


def followers_of(leader, room):
    """Characters in ``room`` currently following ``leader``."""
    if not room:
        return []
    return [obj for obj in room.contents
            if _valid(obj) and getattr(obj.db, "following", None) == leader]


def sever_follow(follower, silent=False):
    """Drop a follow link (both parties notified unless silent)."""
    leader = follower.db.following
    follower.db.following = None
    if silent or not _valid(leader):
        return
    try:
        follower.msg(f"You stop following {leader.get_display_name(follower)}.")
        leader.msg(f"{follower.get_display_name(leader)} stops following you.")
    except Exception:  # noqa: BLE001 — notification is best-effort
        pass


def bring_followers(leader, source_location):
    """Trail the leader's followers through the exit just taken.

    Called from the leader's ``at_post_move`` — the leader has ALREADY
    arrived (followers move secondary). Each follower traverses the same
    exit via the real exit command; a follower who can't make it (locked
    out, unconscious, in combat) loses the trail and the link breaks. A
    leader move with no traceable exit (teleport) sheds followers too.
    """
    destination = leader.location
    if not source_location or destination is source_location:
        return
    followers = followers_of(leader, source_location)
    if not followers:
        return
    exit_obj = _exit_to(source_location, destination)
    for follower in followers:
        if exit_obj is None:
            sever_follow(follower, silent=True)
            follower.msg("You lose them — they're simply gone.")
            continue
        follower.execute_cmd(exit_obj.key)
        if follower.location is not destination:
            # Couldn't keep up (lock, state, combat) — the trail is lost.
            sever_follow(follower, silent=True)
            follower.msg(
                f"You can't keep up with "
                f"{leader.get_display_name(follower)} and lose them."
            )


def usher_escortee(leader, destination):
    """Send the escortee through the exit FIRST (an escort moves ahead).

    Called from the leader's ``at_pre_move``. Returns True when the leader's
    own move may proceed. Consent is re-checked per move — a revoked or
    lapsed grant releases the escortee here, and the leader walks on alone.
    """
    escortee = leader.db.escorting
    if not _valid(escortee):
        leader.db.escorting = None
        return True
    if escortee.location is not leader.location:
        # Separated (they broke away, fled, were moved) — link dissolves.
        leader.db.escorting = None
        leader.msg("Your escort is no longer with you.")
        return True

    from world.consent import check_consent, is_conscious
    if not is_conscious(escortee) or not check_consent(
            leader, escortee, "escort"):
        # Can't walk, or no longer willing — release, leader proceeds alone.
        leader.db.escorting = None
        leader.msg(
            f"{escortee.get_display_name(leader)} no longer follows "
            f"your lead."
        )
        try:
            escortee.msg(
                f"You slip free of {leader.get_display_name(escortee)}'s lead."
            )
        except Exception:  # noqa: BLE001
            pass
        return True

    exit_obj = _exit_to(leader.location, destination)
    if exit_obj is None:
        return True  # teleport-style move: no doorway to usher through
    escortee.execute_cmd(exit_obj.key)
    if escortee.location is not destination:
        # The escortee bounced (lock, state). Ushering someone through a
        # door that refuses them stops YOU at the threshold too — the
        # coupling holds, the move doesn't happen.
        leader.msg(
            f"You can't lead {escortee.get_display_name(leader)} through "
            f"— the way refuses them."
        )
        return False
    return True
