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
    """Drop a follow link (both parties AND the room notified unless silent).

    The room half matters because every ESTABLISHMENT is broadcast — the
    room is told "{actor} falls in behind {target}" — while no release
    ever was (#2572). Bystanders watched people fall in behind each other
    and never watched anyone peel off, so the coupling a room had seen
    form was, as far as anyone standing there could tell, permanent.

    Broadcast only when the two are still in the same room: after a
    follower loses the trail they are a room apart, and there is no
    single room that witnessed the parting. Those paths pass
    ``silent=True`` anyway and say something more specific.
    """
    leader = follower.db.following
    follower.db.following = None
    if silent or not _valid(leader):
        return
    try:
        follower.msg(f"You stop following {leader.get_display_name(follower)}.")
        leader.msg(f"{follower.get_display_name(leader)} stops following you.")
    except Exception:  # noqa: BLE001 — notification is best-effort
        pass
    if follower.location and follower.location is leader.location:
        try:
            from world.identity_utils import msg_room_identity
            msg_room_identity(
                location=follower.location,
                template="{actor} stops following {target}.",
                char_refs={"actor": follower, "target": leader},
                exclude=[follower, leader],
            )
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
        return True

    # RE-ENTRANCY GUARD (#2454). A escorting B while B escorts A made
    # any movement recurse until the interpreter stack blew: A's
    # `at_pre_move` ushers B, B's `at_pre_move` ushers A, and neither
    # can reach `move_to`'s actual relocation until its escortee has
    # already moved — so no state changes between iterations and the
    # early-outs above are all false. The player got a RecursionError
    # traceback and BOTH characters were wedged, since every later move
    # by either re-triggered it.
    #
    # The FOLLOW direction is safe and the author knew it:
    # `bring_followers` runs from `at_post_move` AFTER the leader has
    # arrived, and only moves followers still in the SOURCE room, so
    # each hop empties that room. Escort is the exact inverse —
    # pre-move, before anyone has left — and never got the equivalent
    # reasoning.
    #
    # Refusing the RE-ENTRANT move (rather than allowing it) is what
    # makes each party move exactly once: the inner call is cancelled,
    # the escortee completes its own move, and the outer frame then
    # moves the leader normally.
    # STRICT `is True`, the same idiom `is_hidden_from` uses on
    # `db.hidden`. Two reasons, both load-bearing: Evennia's DbHolder
    # returns None for a missing ndb key rather than the getattr
    # default, and a MagicMock stand-in auto-creates the attribute as a
    # truthy Mock — so a plain truthiness test fires on every test
    # fixture and refuses ordinary escorts.
    if getattr(leader.ndb, "ushering_escortee", None) is True:
        return False
    setattr(leader.ndb, "ushering_escortee", True)
    try:
        return _usher(leader, escortee, exit_obj, destination)
    finally:
        try:
            delattr(leader.ndb, "ushering_escortee")
        except Exception:  # noqa: BLE001 — a missing flag is already clear
            pass


def _usher(leader, escortee, exit_obj, destination):
    """Send the escortee through, then report whether the leader may
    follow. Split out so the re-entrancy flag above has a single scope
    to wrap."""
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
