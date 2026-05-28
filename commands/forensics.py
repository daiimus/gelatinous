"""Forensic command surfaces (PR-E).

Player-facing commands that route through
:mod:`world.forensics`'s canonical engine.

Currently ships:

* :class:`CmdAutopsy` — examine a corpse to recover signature axes
  via an Intellect roll.  Two-tier (basic + ``/deep``) per the
  PR-E scope lock.
"""

from __future__ import annotations

from evennia import Command

from typeclasses.corpse import Corpse
from world.combat.constants import AUTOPSY_DC_BASIC, AUTOPSY_DC_DEEP_OFFSET
from world.forensics import (
    attempt_forensic_recognition,
    extract_subject_from_corpse,
    render_forensic_report,
)
from world.identity_utils import msg_room_identity


class CmdAutopsy(Command):
    """Forensic examination of a corpse.

    Usage:
      autopsy <corpse>
      autopsy/deep <corpse>

    Rolls Intellect vs a DC determined by ``AUTOPSY_DC_BASIC``
    (or ``AUTOPSY_DC_BASIC + AUTOPSY_DC_DEEP_OFFSET`` with
    ``/deep``).  Success reveals the corpse's preserved identity
    signature: apparent height, build, keyword, and (deep only)
    the type IDs of any disguise-essential items recovered.

    Does **not** assign a name to the corpse unless the looker
    already holds the corpse's apparent UID in their recognition
    memory — that lookup is the responsibility of the recognition
    pipeline, not the forensic engine, so this command never
    leaks identities.

    Results are cached per ``(observer, corpse)`` — a second
    autopsy by the same character silently re-renders the cached
    outcome rather than rolling again.  This rewards careful
    single-pass examination and is consistent with the
    disguise-pierce convention.
    """

    key = "autopsy"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Forensics"
    switch_options = ("deep",)

    def func(self):
        caller = self.caller
        if not self.args or not self.args.strip():
            caller.msg("Usage: autopsy[/deep] <corpse>")
            return

        target = caller.search(self.args.strip(), location=caller.location)
        if target is None:
            return  # search() already messaged the caller

        if not isinstance(target, Corpse):
            caller.msg("You can only perform an autopsy on a corpse.")
            return

        deep = "deep" in self.switches
        dc = AUTOPSY_DC_BASIC + (AUTOPSY_DC_DEEP_OFFSET if deep else 0)
        depth = "detailed" if deep else "summary"

        # Build the subject envelope.  Pre-PR-#183 corpses still in
        # the live DB have no snapshot; render_forensic_report will
        # produce a graceful "no further detail" message.
        subject = extract_subject_from_corpse(target)

        # Broadcast the activity to the room (per-observer rendering)
        # before doing the roll, so observers see the investigator
        # working regardless of outcome.  The corpse is rendered via
        # ``get_display_name`` per-observer downstream of the
        # template; we pre-format it for the actor.
        corpse_name_for_caller = target.get_display_name(caller)
        verb = "performs a deep autopsy on" if deep else "examines"
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} {verb} {{corpse}}.",
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )

        # Roll (and cache) the recognition attempt.  Result.success
        # gates whether we render the report; revealed_uid lets us
        # opportunistically enrich the report header if the looker
        # already knows the UID.
        result = attempt_forensic_recognition(
            caller, subject, dc,
            cache_owner=target, cache_attr="forensic_recognition_cache",
        )

        if not result.success:
            caller.msg(
                f"You examine {corpse_name_for_caller} but cannot determine "
                f"anything conclusive."
            )
            return

        report = render_forensic_report(subject, observer=caller, depth=depth)

        # Recognition contract: only surface an assigned name if the
        # looker already holds the UID.  The engine does not assign
        # names on its own.
        memory = getattr(caller, "recognition_memory", None) or {}
        header = f"You examine {corpse_name_for_caller}."
        if result.revealed_uid and result.revealed_uid in memory:
            assigned = memory[result.revealed_uid].get("assigned_name")
            if assigned:
                header = (
                    f"You examine {corpse_name_for_caller} and confirm the "
                    f"remains are those of {assigned}."
                )

        caller.msg(f"{header}\n{report}")
