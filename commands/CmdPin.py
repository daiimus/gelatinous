"""@pin / @unpin — freeze a soul in time (owner ruling 2026-09-14).

A pinned soul keeps everything that makes it a person -- persona,
needs, memory, the soul tag -- but the heartbeat leaves it alone: no
need decay, no thinking, no planning, no walking. It stands where it
was pinned until a GM puppets it or a developer tests against it, and
``@unpin`` lets it live again from that moment (the frozen interval is
not paid back as a lump of hunger).

Scope is the souls system only. Players and staff are refused
outright: a body an account owns, or one that holds Builder
permissions, is never a candidate, no matter who asks.
"""
from evennia import Command

from world.souls import engine


def _refuse_reason(target):
    """Why *target* may not be pinned, or ``None`` when it may."""
    from world.ownership import is_player_owned
    if is_player_owned(target):
        return "a player's character"
    try:
        if target.check_permstring("Builder"):
            return "staff"
    except Exception:  # noqa: BLE001 -- no permission surface, not staff
        pass
    if not target.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
        return "not a soul"
    return None


class CmdPin(Command):
    """
    Freeze a soul in time.

    Usage:
        @pin            - list every pinned soul
        @pin <npc>      - pin that soul where it stands

    A pinned soul keeps its persona, needs and memory but takes no
    beat: no need decay, no thinking, no walking. Use it to hold a
    spawned person for testing or for a GM to puppet later.
    ``@unpin`` releases it. Players and staff cannot be pinned.
    """
    key = "@pin"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            pinned = engine.pinned_souls()
            if not pinned:
                caller.msg("No souls are pinned.")
                return
            lines = ["|wPinned souls:|n"]
            for soul in pinned:
                where = soul.location.key if soul.location else "nowhere"
                lines.append(f"  {soul.key:<22} @ {where}")
            caller.msg("\n".join(lines))
            return
        target = caller.search(args, global_search=True)
        if not target:
            return
        reason = _refuse_reason(target)
        if reason:
            caller.msg(f"|r{target.key} is {reason} — @pin only holds souls.|n")
            return
        if engine.is_pinned(target):
            caller.msg(f"{target.key} is already pinned.")
            return
        engine.pin(target, by=caller)
        caller.msg(f"|w{target.key}|n is pinned in place — frozen in time until @unpin.")


class CmdUnpin(Command):
    """
    Let a pinned soul live again.

    Usage:
        @unpin <npc>

    The soul's clock restarts from now: it resumes needs, thinking
    and walking without paying back the time it spent frozen.
    """
    key = "@unpin"
    locks = "cmd:perm(Builders) or perm(Developers)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: @unpin <npc>")
            return
        target = caller.search(args, global_search=True)
        if not target:
            return
        reason = _refuse_reason(target)
        if reason:
            caller.msg(f"|r{target.key} is {reason} — @unpin only releases souls.|n")
            return
        if not engine.is_pinned(target):
            caller.msg(f"{target.key} is not pinned.")
            return
        engine.unpin(target, by=caller)
        caller.msg(f"|w{target.key}|n is unpinned — living again from now.")
        if not target.db.soul_home:
            caller.msg("|yThey have no home, so they will never sleep — house them "
                       "through a rental kiosk, or delete them when you are done.|n")
