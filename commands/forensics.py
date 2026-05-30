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
* :class:`CmdSever` — remove a limb (or the head) from a corpse via
  a Motorics roll, spawning a :class:`typeclasses.items.Appendage`
  item.  The severed location is appended to
  ``corpse.db.severed_locations`` so :class:`CmdHarvest` correctly
  refuses to extract organs that left with the limb (PR #190).
"""

from __future__ import annotations

from evennia import Command, create_object
from evennia.utils import utils

from typeclasses.corpse import Corpse
from typeclasses.items import SeveredHead, apply_sever_to_corpse
from world.combat.constants import (
    AUTOPSY_DC_BASIC,
    HARVEST_CRIT_FAIL,
    HARVEST_DC_BASIC,
    NDB_COMBAT_HANDLER,
    ORGAN_CONDITION_BY_DECAY,
    SEVER_CRIT_FAIL_SUM,
    SEVER_DC_INT_MOT,
    SEVER_TIME_SECONDS,
    SEVERABLE_CONTAINERS,
)
from world.combat.dice import roll_stat
from world.combat.utils import get_wielded_weapon
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

        if not isinstance(target, (Corpse, SeveredHead)):
            caller.msg(
                "You can only perform an autopsy on a corpse or a "
                "severed head."
            )
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
      flagged ``cannot_be_destroyed`` (thoracolumbar spine).
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

        if not isinstance(target, (Corpse, SeveredHead)):
            caller.msg(
                "You can only harvest organs from a corpse or a "
                "severed head."
            )
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

        # PR #200 (PR-F): synthesize a ``harvested``-type wound on the
        # corpse at the organ's *container* location.  Targeting the
        # container (not the organ name) lets PR-D's wound + longdesc
        # carry-forward overlay move this wound onto severed limbs /
        # heads automatically when those locations are later severed.
        # Harvests of organs whose container is unseverable (chest,
        # abdomen, back) leave the wound on the corpse permanently —
        # which is the correct narrative for torso excisions.
        wounds = list(target.db.wounds_at_death or ())
        wounds.append({
            "injury_type": "harvested",
            "location": organ_data.get("container") or organ_arg,
            "severity": "Critical",
            "stage": "old",
            "organ": organ_arg,
            "organ_damage": {
                "current_hp": 0,
                "max_hp": 0,
                "container": organ_data.get("container") or organ_arg,
            },
        })
        target.db.wounds_at_death = wounds

        organ_item = create_object(
            "typeclasses.items.Organ",
            key=organ_arg,
            location=caller,
        )
        # Issue #212: ``configure_from_harvest`` is the sole authority
        # for the final key (species + decay-tier aware via
        # :func:`world.anatomy.species.get_species_organ_name`).  The
        # ``key=organ_arg`` above is a transient placeholder for the
        # window between spawn and configuration.
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


# ---------------------------------------------------------------------
# CmdSever (PR #190)
# ---------------------------------------------------------------------


def _severable_locations(corpse) -> list[str]:
    """Return body-location identifiers still detachable from *corpse*.

    A location is severable when **all** of the following hold:

    * It is present in :data:`world.combat.constants.SEVERABLE_CONTAINERS`
      (the limb partition + ``head``).
    * The death-time medical snapshot mentions at least one organ
      housed in that container (so we know the corpse had the limb
      in the first place — bare anatomy without organs is treated
      as not severable to avoid spawning items for missing
      structures).
    * The location is not already in ``corpse.db.severed_locations``.

    Returns an empty list if the snapshot is missing.
    """
    snapshot = corpse.get_medical_snapshot()
    if snapshot is None:
        return []
    organs = snapshot.get("organs") or {}
    present_containers = {
        (data.get("container") or "")
        for data in organs.values()
    }
    severed = set(corpse.db.severed_locations or ())
    out = [
        loc for loc in SEVERABLE_CONTAINERS
        if loc in present_containers and loc not in severed
    ]
    out.sort()
    return out


class CmdSever(Command):
    """Detach a limb (or the head) from a corpse.

    Usage:
      sever <location> from <corpse>
      sever <corpse>            (lists severable locations)

    Requires a wielded edged weapon flagged ``db.can_sever`` (PR #190).
    The cut takes :data:`world.combat.constants.SEVER_TIME_SECONDS`
    real-seconds and resolves on a combined
    ``intellect + motorics`` roll vs
    :data:`world.combat.constants.SEVER_DC_INT_MOT` — anatomical
    know-how *and* a steady hand.  On success an
    :class:`~typeclasses.items.Appendage` item is spawned into the
    severer's inventory and the location is appended to
    ``corpse.db.severed_locations``.  Subsequent ``harvest`` attempts
    targeting organs whose container matches the severed location are
    refused — the contained organs went with the limb (v1 does not
    spawn separate organ items for the contained anatomy; a future
    butchery pass may unbundle them).

    A combined sum at or below
    :data:`world.combat.constants.SEVER_CRIT_FAIL_SUM` botches the cut:
    no item, no bookkeeping mutation, just a "mangled" message.  Unlike
    organ harvest crit-fail (which destroys the organ), limb
    botches are recoverable — try again.

    The cut is **re-validated on completion** rather than actively
    interrupted (the codebase has no channeled-action infrastructure).
    If, when the timer fires, the actor has moved away from the corpse,
    stopped wielding the blade, entered combat, or the corpse has been
    moved or destroyed, the cut aborts with no mutation.

    Refused outright when:

    * The actor is not wielding a ``can_sever`` weapon.
    * A sever is already in progress for the actor.
    * The corpse is skeletal (no soft tissue left to cut through).
    * The corpse predates PR #186 and has no medical snapshot.
    * The named location is not in
      :data:`world.combat.constants.SEVERABLE_CONTAINERS`.
    * The snapshot mentions no organs in that container (the corpse
      never had that limb).
    * The location is already in ``corpse.db.severed_locations``.

    Appendage freshness tracks the source corpse's decay stage via
    :data:`world.combat.constants.ORGAN_CONDITION_BY_DECAY`.
    """

    key = "sever"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Forensics"

    def func(self):  # noqa: C901 — straight-line guard-clause flow
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg("Usage: sever <location> from <corpse>")
            return

        if " from " in raw:
            location_arg, _, corpse_arg = raw.partition(" from ")
            location_arg = location_arg.strip().lower().replace(" ", "_")
            corpse_arg = corpse_arg.strip()
        else:
            location_arg = ""
            corpse_arg = raw

        target = caller.search(corpse_arg, location=caller.location)
        if target is None:
            return

        if not isinstance(target, Corpse):
            caller.msg("You can only sever limbs from a corpse.")
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

        severable = _severable_locations(target)

        if not location_arg:
            if not severable:
                caller.msg(
                    f"There are no limbs left to sever on "
                    f"{target.get_display_name(caller)}."
                )
                return
            readable = ", ".join(loc.replace("_", " ") for loc in severable)
            caller.msg(
                f"Severable locations on {target.get_display_name(caller)}:"
                f" {readable}.\nUsage: sever <location> from <corpse>"
            )
            return

        # Specific location requested.
        if location_arg not in SEVERABLE_CONTAINERS:
            caller.msg(
                f"You cannot sever the {location_arg.replace('_', ' ')} "
                f"— it is not a detachable body location."
            )
            return

        organs = snapshot.get("organs") or {}
        present = any(
            (data.get("container") or "") == location_arg
            for data in organs.values()
        )
        if not present:
            caller.msg(
                f"{target.get_display_name(caller)} has no "
                f"{location_arg.replace('_', ' ')} to sever."
            )
            return

        if location_arg in (target.db.severed_locations or ()):
            caller.msg(
                f"The {location_arg.replace('_', ' ')} has already been "
                f"severed from these remains."
            )
            return

        # Wielded-blade gate (PR #190): the cut requires an edged
        # weapon flagged ``can_sever``.  ``db.can_sever is not True``
        # treats an unset / non-edged weapon as ineligible.
        weapon = get_wielded_weapon(caller)
        if weapon is None:
            caller.msg(
                "You need a bladed weapon in hand to sever a limb."
            )
            return
        if weapon.db.can_sever is not True:
            caller.msg(
                f"{weapon.get_display_name(caller)} is too dull to "
                f"sever a limb — you need a keener edge."
            )
            return

        # One cut at a time.
        if caller.ndb.sever_task is not None:
            caller.msg("You are already mid-cut.")
            return

        readable_name = location_arg.replace("_", " ")

        # Pre-cut broadcast.
        caller.msg(
            f"You set your {weapon.get_display_name(caller)} to the "
            f"{readable_name} and begin to cut..."
        )
        msg_room_identity(
            location=caller.location,
            template=(
                f"{{actor}} begins severing the {readable_name} "
                f"from {{corpse}}."
            ),
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )

        # Schedule the resolution.  The cut is re-validated on
        # completion rather than actively interrupted.
        caller.ndb.sever_task = utils.delay(
            SEVER_TIME_SECONDS,
            self._complete_sever,
            caller,
            target,
            location_arg,
        )

    def _complete_sever(self, caller, target, location_arg):
        """Resolve a scheduled sever after re-validating the situation.

        Called by ``utils.delay`` once ``SEVER_TIME_SECONDS`` elapses.
        Re-checks every precondition that could have changed during the
        cut (the actor moving away, unwielding the blade, entering
        combat, or the corpse being moved / destroyed) before rolling.
        Any failed check aborts the cut with no mutation.
        """
        caller.ndb.sever_task = None
        readable_name = location_arg.replace("_", " ")

        # Corpse still present and intact?
        if (
            target is None
            or target.pk is None
            or target.location is None
            or target.location != caller.location
        ):
            caller.msg(
                f"The remains are gone; your cut for the "
                f"{readable_name} finds nothing."
            )
            return
        if target.get_decay_stage() == "skeletal":
            caller.msg(
                "The remains are too far decomposed — only bone is left."
            )
            return

        # Blade still in hand and still keen?
        weapon = get_wielded_weapon(caller)
        if weapon is None or weapon.db.can_sever is not True:
            caller.msg(
                f"Without a blade in hand the cut for the "
                f"{readable_name} comes to nothing."
            )
            return

        # Not dragged into combat mid-cut.
        if getattr(caller.ndb, NDB_COMBAT_HANDLER, None) is not None:
            caller.msg(
                f"The fighting breaks your concentration; you abandon "
                f"the cut for the {readable_name}."
            )
            return

        # Location still severable and not already taken.
        if location_arg not in SEVERABLE_CONTAINERS:
            return
        if location_arg in (target.db.severed_locations or ()):
            caller.msg(
                f"The {readable_name} has already been severed from "
                f"these remains."
            )
            return

        corpse_display = target.get_display_name(caller)

        # Combined Intellect + Motorics roll (PR #190).
        roll = roll_stat(caller, "intellect") + roll_stat(caller, "motorics")

        if roll <= SEVER_CRIT_FAIL_SUM:
            caller.msg(
                f"Your cut goes wide — you mangle the {readable_name} "
                f"but fail to detach it."
            )
            msg_room_identity(
                location=caller.location,
                template=(
                    f"{{actor}} mangles the {readable_name} on "
                    f"{{corpse}} but fails to sever it."
                ),
                char_refs={"actor": caller, "corpse": target},
                exclude=[caller],
            )
            return

        if roll < SEVER_DC_INT_MOT:
            caller.msg(
                f"You hack at {corpse_display} but cannot detach the "
                f"{readable_name} cleanly. The limb remains attached."
            )
            return

        # Success.
        condition = ORGAN_CONDITION_BY_DECAY.get(
            target.get_decay_stage(), "damaged"
        )
        severed_list = list(target.db.severed_locations or ())
        severed_list.append(location_arg)
        target.db.severed_locations = severed_list

        # Route ``head`` to the super-item typeclass so the head
        # carries identity / decay / trimmed snapshot state forward
        # for downstream autopsy and harvest.  All other severable
        # locations spawn a plain Appendage.
        if location_arg == "head":
            appendage_typeclass = "typeclasses.items.SeveredHead"
        else:
            appendage_typeclass = "typeclasses.items.Appendage"

        appendage = create_object(
            appendage_typeclass,
            key=f"{condition} {readable_name}",
            location=caller,
        )
        appendage.configure_from_sever(
            location_name=location_arg, condition=condition, corpse=target,
        )

        # PR #198: mirror the appendage-side wound/longdesc overlay by
        # clearing that prose off the corpse and synthesizing a stump
        # wound at the canonical severed location.  Handles the
        # head-cluster fan-out internally (head sever also clears
        # face / neck / eyes / ears prose).
        apply_sever_to_corpse(target, location_arg)

        caller.msg(
            f"You sever the {readable_name} from {corpse_display} — "
            f"the limb is {condition}."
        )
        msg_room_identity(
            location=caller.location,
            template=(
                f"{{actor}} severs the {condition} {readable_name} "
                f"from {{corpse}}."
            ),
            char_refs={"actor": caller, "corpse": target},
            exclude=[caller],
        )
