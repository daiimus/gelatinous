"""Forensic command surfaces.

Player-facing commands that route through
:mod:`world.forensics`'s canonical engine.

Currently ships:

* :class:`CmdAutopsy` — examine a corpse to recover the preserved
  identity signature, fuzzy time-of-death, apparent cause of death,
  wounds, organ inventory, and worn essentials.  Single-tier
  (the legacy ``/deep`` switch was dropped in PR #186 in favour of
  the unified five-section report).
"""

from __future__ import annotations

from evennia import Command

from typeclasses.corpse import Corpse
from world.combat.constants import AUTOPSY_DC_BASIC
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

    Rolls Intellect vs ``AUTOPSY_DC_BASIC``.  On success the corpse's
    preserved death-time signature is rendered — apparent height,
    build, keyword, fuzzy time of death, cause of death, wounds
    grouped by body location, organ inventory (with harvested /
    severed organs marked ``absent`` per PR-186 Q3), and any
    disguise-essential items still worn on the remains.

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

    Skeletal remains are too far decomposed for forensic
    examination; pre-PR-#186 corpses still in the live DB lack
    the death-time medical snapshot and report an empty internal
    examination instead.
    """

    key = "autopsy"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Forensics"

    def func(self):
        caller = self.caller
        if not self.args or not self.args.strip():
            caller.msg("Usage: autopsy <corpse>")
            return

        target = caller.search(self.args.strip(), location=caller.location)
        if target is None:
            return  # search() already messaged the caller

        if not isinstance(target, Corpse):
            caller.msg("You can only perform an autopsy on a corpse.")
            return

        # Skeletal-stage guard: no soft tissue, no signature axes worth
        # recovering.  Cheaper to short-circuit here than to render a
        # report full of "absent" lines.
        if target.get_decay_stage() == "skeletal":
            caller.msg(
                "The remains are too far decomposed for forensic "
                "examination — only bone is left."
            )
            return

        # Build the subject envelope.  Pre-PR-#183 corpses still in
        # the live DB have no snapshot; render_forensic_report will
        # produce a graceful "no further detail" message.
        subject = extract_subject_from_corpse(target)

        # Broadcast the activity to the room (per-observer rendering)
        # before doing the roll, so observers see the investigator
        # working regardless of outcome.
        corpse_name_for_caller = target.get_display_name(caller)
        msg_room_identity(
            location=caller.location,
            template="{actor} examines {corpse}.",
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )

        # Roll (and cache) the recognition attempt.  Result.success
        # gates whether we render the report; revealed_uid lets us
        # opportunistically enrich the report header if the looker
        # already knows the UID.
        result = attempt_forensic_recognition(
            caller, subject, AUTOPSY_DC_BASIC,
            cache_owner=target, cache_attr="forensic_recognition_cache",
        )

        if not result.success:
            caller.msg(
                f"You examine {corpse_name_for_caller} but cannot determine "
                f"anything conclusive."
            )
            return

        report = render_forensic_report(subject, observer=caller)

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
