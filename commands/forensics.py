"""Forensic command surfaces.

Player-facing commands that route through
:mod:`world.forensics`'s canonical engine.

Currently ships:

* :class:`CmdAutopsy` — examine a corpse to recover the preserved
  identity signature, fuzzy time-of-death, apparent cause of death,
  wounds, organ inventory, and worn essentials.  Single-tier
  (the legacy ``/deep`` switch was dropped in PR #186 in favour of
  the unified five-section report).
* :class:`CmdHarvest` — extract a named organ from a corpse via a
  Motorics roll, spawning a :class:`typeclasses.items.Organ` item
  into the harvester's inventory and marking the organ ``absent`` on
  subsequent autopsies (PR #188).
"""

from __future__ import annotations

from evennia import Command, create_object

from typeclasses.corpse import Corpse
from world.combat.constants import (
    AUTOPSY_DC_BASIC,
    HARVEST_CRIT_FAIL,
    HARVEST_DC_BASIC,
    ORGAN_CONDITION_BY_DECAY,
)
from world.combat.dice import roll_stat
from world.forensics import (
    attempt_forensic_recognition,
    extract_subject_from_corpse,
    render_forensic_report,
)
from world.identity_utils import msg_room_identity
from world.medical.constants import ORGANS


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


# ---------------------------------------------------------------------
# CmdHarvest (PR #188)
# ---------------------------------------------------------------------


def _harvestable_organs(corpse) -> list[str]:
    """Return organ names that are still extractable from *corpse*.

    Filters the death-time medical snapshot against three gates:

    1. Organ must declare ``can_be_harvested: True`` in
       :data:`world.medical.constants.ORGANS`.
    2. Organ must not already be in ``corpse.db.removed_organs``.
    3. Organ's container must not be in ``corpse.db.severed_locations``
       (a severed limb takes its contained organs with it; PR #189
       will produce the severed limb item itself).
    4. Organ must still have ``current_hp > 0`` in the snapshot
       (destroyed organs are not recoverable as items).

    Returns an empty list if the snapshot is missing.
    """
    snapshot = corpse.get_medical_snapshot()
    if snapshot is None:
        return []
    removed = set(corpse.db.removed_organs or ())
    severed = set(corpse.db.severed_locations or ())
    organs = snapshot.get("organs") or {}
    out: list[str] = []
    for name, organ_data in organs.items():
        spec = ORGANS.get(name) or {}
        if not spec.get("can_be_harvested"):
            continue
        if name in removed:
            continue
        if organ_data.get("container") in severed:
            continue
        if (organ_data.get("current_hp") or 0) <= 0:
            continue
        out.append(name)
    return out


class CmdHarvest(Command):
    """Extract a named organ from a corpse.

    Usage:
      harvest <organ> from <corpse>
      harvest <corpse>          (lists harvestable organs)

    Rolls Motorics vs ``HARVEST_DC_BASIC``.  On success an
    :class:`~typeclasses.items.Organ` item is spawned into the
    harvester's inventory, the organ is appended to the corpse's
    ``removed_organs`` list, and the death-time medical snapshot is
    mutated in place so subsequent autopsies render the organ as
    *absent*.  A natural roll of ``HARVEST_CRIT_FAIL`` destroys the
    organ instead — the snapshot's ``current_hp`` is zeroed and no
    item is produced.

    Refused outright when:

    * The corpse is skeletal (no soft tissue remains).
    * The corpse predates PR #186 and has no medical snapshot.
    * The named organ is missing, undeclared as harvestable, or
      flagged ``cannot_be_destroyed`` (spine).
    * The organ has already been harvested, lives inside a severed
      limb container, or is destroyed.

    The freshness of the spawned organ tracks the corpse's decay stage
    via :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`:
    fresh / early → ``pristine``; moderate → ``damaged``; advanced →
    ``putrid``; skeletal → refused outright.
    """

    key = "harvest"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Forensics"

    def func(self):  # noqa: C901 — straight-line guard-clause flow
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg("Usage: harvest <organ> from <corpse>")
            return

        # Split on ' from ' once; if absent, treat the whole arg as a
        # corpse and surface the harvestable-organ list.
        if " from " in raw:
            organ_arg, _, corpse_arg = raw.partition(" from ")
            organ_arg = organ_arg.strip().lower().replace(" ", "_")
            corpse_arg = corpse_arg.strip()
        else:
            organ_arg = ""
            corpse_arg = raw

        target = caller.search(corpse_arg, location=caller.location)
        if target is None:
            return  # search() already messaged

        if not isinstance(target, Corpse):
            caller.msg("You can only harvest organs from a corpse.")
            return

        if target.get_decay_stage() == "skeletal":
            caller.msg(
                "The remains are too far decomposed — only bone is left."
            )
            return

        snapshot = target.get_medical_snapshot()
        if snapshot is None:
            caller.msg(
                "These remains predate forensic record-keeping; no "
                "internal examination is possible."
            )
            return

        harvestable = _harvestable_organs(target)

        if not organ_arg:
            # Ambiguous form — list options.
            if not harvestable:
                caller.msg(
                    f"There are no harvestable organs left in "
                    f"{target.get_display_name(caller)}."
                )
                return
            readable = ", ".join(o.replace("_", " ") for o in harvestable)
            caller.msg(
                f"Harvestable organs in {target.get_display_name(caller)}: "
                f"{readable}.\nUsage: harvest <organ> from <corpse>"
            )
            return

        # Specific organ requested.  Validate against the snapshot
        # *and* the ORGANS spec to produce useful error messages.
        organs = snapshot.get("organs") or {}
        if organ_arg not in organs:
            caller.msg(
                f"There is no {organ_arg.replace('_', ' ')} in "
                f"{target.get_display_name(caller)}."
            )
            return

        spec = ORGANS.get(organ_arg) or {}
        if spec.get("cannot_be_destroyed"):
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} is too deeply "
                f"integrated to extract."
            )
            return
        if not spec.get("can_be_harvested"):
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} cannot be harvested."
            )
            return

        organ_data = organs[organ_arg]
        if organ_arg in (target.db.removed_organs or ()):
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} has already been "
                f"removed from these remains."
            )
            return
        if organ_data.get("container") in (target.db.severed_locations or ()):
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} went with the "
                f"severed {organ_data.get('container')}."
            )
            return
        if (organ_data.get("current_hp") or 0) <= 0:
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} is already destroyed."
            )
            return

        # Pre-roll broadcast — observers see the surgical attempt
        # regardless of outcome.
        readable_name = organ_arg.replace("_", " ")
        corpse_display = target.get_display_name(caller)
        msg_room_identity(
            location=caller.location,
            template=(
                f"{{actor}} begins extracting the {readable_name} "
                f"from {{corpse}}."
            ),
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )

        roll = roll_stat(caller, "motorics")

        if roll == HARVEST_CRIT_FAIL:
            # Critical fail destroys the organ in place — no item
            # spawned, but the snapshot must be mutated and re-saved
            # so autopsies render the organ as ``destroyed``.
            organ_data["current_hp"] = 0
            target.db.medical_state_at_death = snapshot
            caller.msg(
                f"Your hand slips — the {readable_name} ruptures and is "
                f"destroyed beyond recovery."
            )
            msg_room_identity(
                location=caller.location,
                template=(
                    f"{{actor}}'s extraction goes wrong; the "
                    f"{readable_name} ruptures inside {{corpse}}."
                ),
                char_refs={"actor": caller, "corpse": target},
                exclude=[caller],
            )
            return

        if roll < HARVEST_DC_BASIC:
            caller.msg(
                f"You probe at {corpse_display} but cannot extract the "
                f"{readable_name} cleanly. The organ remains in place."
            )
            return

        # Success: mutate snapshot, append to removed_organs, spawn item.
        condition = ORGAN_CONDITION_BY_DECAY.get(
            target.get_decay_stage(), "damaged"
        )
        removed_list = list(target.db.removed_organs or ())
        removed_list.append(organ_arg)
        target.db.removed_organs = removed_list
        target.db.medical_state_at_death = snapshot  # re-save no-op for
        # parity with crit-fail branch; future per-organ HP tweaks rely
        # on this contract.

        organ_item = create_object(
            "typeclasses.items.Organ",
            key=f"{condition} {readable_name}",
            location=caller,
        )
        organ_item.configure_from_harvest(
            organ_name=organ_arg, condition=condition, corpse=target,
        )

        caller.msg(
            f"You extract the {readable_name} from {corpse_display} — "
            f"the organ is {condition}."
        )
        msg_room_identity(
            location=caller.location,
            template=(
                f"{{actor}} extracts the {condition} {readable_name} "
                f"from {{corpse}}."
            ),
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )
