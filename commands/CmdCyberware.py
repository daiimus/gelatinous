"""The cyberware dispatcher (AUGMENT_ABILITIES_SPEC §3.1, #516).

One command, keyed on :data:`CYBERWARE_COMMAND_PREFIX`.  Evennia's
parser matches command keys as prefixes, so ``/shotgun`` resolves to
this command with ``args = "shotgun"`` — no per-weapon commands, no
dynamic cmdsets.  Swapping the prefix (``/`` → ``=``) is a one-line
change in ``world.medical.augments``.
"""

from __future__ import annotations

from evennia import Command

from world.medical.augments import (
    CYBERWARE_COMMAND_PREFIX,
    list_abilities,
    toggle_ability,
)
from world.medical.cyberware_status import render_system


class CmdCyberware(Command):
    """Command your installed cyberware.

    Usage:
        /            - list your installed cyberware and its state
        /system      - full diagnostic readout of your cyberware
        /<ability>   - toggle that ability (deploy / retract)

    Examples:
        /shotgun     - deploy or retract the arm-mounted shotgun

    Deploying an integrated weapon transforms the hand it lives in —
    anything that hand was holding drops to the ground, and the hand
    can't hold anything until the weapon is retracted.  Integrated
    weapons can't be dropped, given away, or disarmed; they are
    bolted to your skeleton.

    Abilities come from installed augments and leave with them — a
    severed gun arm takes the gun.
    """

    key = CYBERWARE_COMMAND_PREFIX
    locks = "cmd:all()"
    help_category = "Cyberware"
    # Accept args glued directly to the key ("/shotgun"), no space.
    arg_regex = r"(?s).*"

    def func(self):
        caller = self.caller
        name = (self.args or "").strip().lower()
        if not name:
            caller.msg(list_abilities(caller))
            return
        if name == "system":
            caller.msg(render_system(caller))
            return
        caller.msg(toggle_ability(caller, name))
