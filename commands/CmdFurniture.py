"""Posture commands — sit / lie / stand on furniture (FURNITURE_AND_POSTURE).

Thin verbs over :class:`typeclasses.furniture.Furniture`: they validate the
posture + capacity, record ``db.posture`` / ``db.furniture`` on the character,
set the room ``temp_place`` line, and broadcast a per-observer pose. Moving
auto-stands you (``Character.at_post_move``). No combat coupling.
"""

import re

from commands.command import Command
from world.grammar import with_article

from typeclasses.furniture import Furniture

#: Leading prepositions a player may type ("sit DOWN ON the stool").
_LEAD = re.compile(r"^(down\s+|back\s+)?(on|in|at|onto|into)\s+", re.I)


def _verb(posture):
    return "lie down" if posture == "lying" else "sit down"


def _available(furnis, posture, caller):
    """First furniture in the list that allows ``posture`` and has room (or that
    the caller already occupies). ``None`` if none qualify."""
    for furn in furnis:
        if not furn.allows(posture):
            continue
        if not furn.is_full() or caller.db.furniture == furn:
            return furn
    return None


def _find_furniture(caller, arg, posture):
    """Locate the furniture to occupy: among the named ones (or all in the room),
    the first that allows this posture and has room. Messages + returns None on
    failure. With many identical seats (10 bar stools) this picks an open one."""
    loc = caller.location
    if not loc:
        caller.msg("There's nothing here to do that on.")
        return None
    furnis = [o for o in loc.contents if isinstance(o, Furniture)]
    on_what = "lie on" if posture == "lying" else "sit on"
    if arg:
        matches = caller.search(arg, candidates=furnis, quiet=True) or []
        if not matches:
            caller.msg(f"You don't see '{arg}' to {on_what} here.")
            return None
        if not any(m.allows(posture) for m in matches):
            m = matches[0]
            verb = "lie" if posture == "lying" else "sit"
            caller.msg(f"You can't {verb} {m.db.preposition or 'on'} "
                       f"{m.get_display_name(caller)}.")
            return None
        furn = _available(matches, posture, caller)
        if not furn:
            caller.msg(f"There's no room — they're all taken.")
            return None
        return furn
    furn = _available(furnis, posture, caller)
    if not furn:
        caller.msg(f"There's nothing free here to {on_what}.")
        return None
    return furn


def _take_posture(cmd, posture):
    caller = cmd.caller
    arg = _LEAD.sub("", (cmd.args or "").strip()).strip()
    furn = _find_furniture(caller, arg, posture)
    if furn is None:
        return
    prep = furn.db.preposition or "on"
    name = with_article(furn.key)
    if caller.db.furniture == furn and caller.db.posture == posture:
        caller.msg(f"You're already {posture} {prep} {name}.")
        return
    caller.db.posture = posture
    caller.db.furniture = furn
    caller.temp_place = f"{posture} {prep} {name}."
    caller.execute_cmd(f".{_verb(posture)} {prep} {name}")


class CmdSit(Command):
    """
    Sit down — on a stool, a couch, whatever's to hand.

    Usage:
      sit
      sit [on] <furniture>

    With no target you take the nearest seat; name one to choose it. You stand
    automatically when you move on.
    """

    key = "sit"
    aliases = ("seat",)
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        _take_posture(self, "sitting")


class CmdLie(Command):
    """
    Lie down — on a bed, a stretcher, a medical pod.

    Usage:
      lie
      lie [down on] <furniture>
      recline [on] <furniture>

    With no target you take the nearest place to lie; name one to choose it.
    """

    key = "lie"
    aliases = ("recline", "lay", "liedown")
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        _take_posture(self, "lying")


class CmdStand(Command):
    """
    Get to your feet.

    Usage:
      stand
      get up
    """

    key = "stand"
    aliases = ("rise", "standup", "stand up", "getup", "get up")
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if (caller.db.posture or "standing") == "standing" and not caller.db.furniture:
            caller.msg("You're already on your feet.")
            return
        caller._clear_posture()
        caller.execute_cmd(".stand up")
