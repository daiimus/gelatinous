"""Forensic command surfaces.

Player-facing commands that route through
:mod:`world.forensics`'s canonical engine.

Currently ships:

* :class:`CmdInspect` (alias: ``autopsy``) — examine a corpse,
  severed head, or blood pool to recover the preserved identity
  signature.  Corpses get the full report (signature, fuzzy
  time-of-death, cause of death, wounds, organ inventory, worn
  essentials); blood pools render one entry per distinct bleeder.
  Single-tier (the legacy ``/deep`` switch was dropped in PR #186
  in favour of the unified report).  Slated to retire as a
  standalone command when ``inspect`` becomes a procedure type
  under ``operate``.
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
    NDB_COMBAT_HANDLER,
    ORGAN_CONDITION_BY_DECAY,
    SEVER_CRIT_FAIL_SUM,
    SEVER_DC_INT_MOT,
    SEVER_TIME_SECONDS,
)
from world.combat.dice import roll_stat
from world.combat.utils import get_wielded_weapon
from typeclasses.objects import BloodPool
from world.forensics import (
    attempt_forensic_recognition,
    extract_subject_from_blood_pool_incident,
    extract_subject_from_corpse,
    render_forensic_report,
)
from world.identity_utils import msg_room_identity


class CmdInspect(Command):
    """Forensic examination of a corpse, severed head, or blood pool.

    Usage:
      inspect <evidence>
      autopsy <evidence>    (alias)

    Rolls Intellect vs ``AUTOPSY_DC_BASIC``.  On success the
    evidence's preserved identity signature is rendered — apparent
    height, build, keyword, and for corpses also: fuzzy time of
    death, cause of death, wounds grouped by body location, organ
    inventory (with harvested / severed organs marked ``absent``
    per PR-186 Q3), and any disguise-essential items still worn on
    the remains.

    Blood pools render one entry per distinct bleeding incident
    (keyed by apparent UID) — useful for crime scenes where
    multiple bleeders left evidence over time.

    Does **not** assign a name to the evidence unless the looker
    already holds the apparent UID in their recognition memory —
    that lookup is the responsibility of the recognition pipeline,
    not the forensic engine, so this command never leaks
    identities.

    Results are cached per ``(observer, evidence)`` — a second
    inspect by the same character silently re-renders the cached
    outcome rather than rolling again.  This rewards careful
    single-pass examination and is consistent with the
    disguise-pierce convention.

    Skeletal remains are too far decomposed for forensic
    examination; pre-PR-#186 corpses still in the live DB lack the
    death-time medical snapshot and report an empty internal
    examination instead.

    **Future:** ``inspect`` is slated to become a procedure type
    under the ``operate`` charting menu — only performable on a
    deceased body the surgeon is operating on.  When that ships,
    this standalone command surface retires.  Until then ``autopsy``
    survives as a command alias for muscle-memory continuity.
    """

    key = "inspect"
    aliases = ("autopsy",)
    locks = "cmd:all()"
    help_category = "Forensics"

    def func(self):
        caller = self.caller
        if not self.args or not self.args.strip():
            caller.msg("Usage: inspect <evidence>")
            return

        target = caller.search(self.args.strip(), location=caller.location)
        if target is None:
            return  # search() already messaged the caller

        if isinstance(target, BloodPool):
            self._inspect_blood_pool(caller, target)
            return

        if not isinstance(target, (Corpse, SeveredHead)):
            caller.msg(
                "You can only inspect a corpse, severed head, or "
                "blood pool."
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

    def _inspect_blood_pool(self, caller, pool):
        """Forensic read of a blood pool — one entry per unique
        apparent UID across the pool's recorded incidents.

        Same recognition contract as the corpse path: surface an
        assigned name only if the observer already holds the UID
        in their recognition memory.  Roll is per-incident; failures
        produce a generic line so observers know the pool was
        examined but yielded nothing recoverable for that bleeder.
        """
        incidents = list(pool.db.bleeding_incidents or ())
        pool_name = pool.get_display_name(caller)

        msg_room_identity(
            location=caller.location,
            template="{actor} examines {pool}.",
            char_refs={"actor": caller, "pool": pool},
            exclude=[caller],
        )

        if not incidents:
            caller.msg(
                f"You examine {pool_name} but there's nothing to recover "
                f"— no preserved identity from the bleeders."
            )
            return

        # Dedupe by apparent_uid — multiple drips from the same
        # bleeder collapse to one report entry.  Picks the most
        # recent incident per UID so the timestamp reflects last
        # contact rather than first.
        # Duck-type: Evennia wraps persisted incident dicts in
        # ``_SaverDict``, which is NOT a ``dict`` subclass for
        # isinstance purposes.  Check for ``.get`` surface instead.
        latest_per_uid: dict = {}
        for incident in incidents:
            if not hasattr(incident, "get"):
                continue
            uid = incident.get("apparent_uid")
            if uid is None:
                continue
            prior = latest_per_uid.get(uid)
            if prior is None or incident.get("timestamp", 0) > prior.get(
                "timestamp", 0
            ):
                latest_per_uid[uid] = incident

        if not latest_per_uid:
            caller.msg(
                f"You examine {pool_name} but the bleeders left no "
                f"recoverable identity signature."
            )
            return

        sections = [f"You examine {pool_name}."]
        memory = getattr(caller, "recognition_memory", None) or {}

        for uid, incident in latest_per_uid.items():
            subject = extract_subject_from_blood_pool_incident(
                pool, incident,
            )
            # Per-incident roll (and cache).  Cache key uses the pool
            # plus the apparent UID so different bleeders cache
            # independently.
            result = attempt_forensic_recognition(
                caller, subject, AUTOPSY_DC_BASIC,
                cache_owner=pool,
                cache_attr=f"forensic_recognition_cache_{uid}",
            )

            if not result.success:
                sections.append(
                    "  — One bleeder's signature could not be "
                    "reconstructed from the pooled blood."
                )
                continue

            report = render_forensic_report(subject, observer=caller)
            # Recognition contract — same as the corpse path.
            header = "  — Bleeder's signature:"
            if result.revealed_uid and result.revealed_uid in memory:
                assigned = memory[result.revealed_uid].get("assigned_name")
                if assigned:
                    header = (
                        f"  — Bleeder's signature, matching {assigned}:"
                    )
            sections.append(f"{header}\n{report}")

        caller.msg("\n".join(sections))


# Backward-compat alias for old imports.
CmdAutopsy = CmdInspect


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
    # Issue #356 Phase 2: species-aware severable set.  Rats sever at
    # foreleg / forepaw / hindleg / hindpaw / tail, not human arm /
    # hand / thigh / shin / foot.
    from world.anatomy import get_species_severable_containers
    severable = get_species_severable_containers(
        getattr(getattr(corpse, "db", None), "species", None)
    )
    out = [
        loc for loc in severable
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
    # ``amputate`` is the medical-context alias.  Same command,
    # same dispatch — the operate menu uses ``amputate`` as the
    # procedure-verb name to align with surgical vocabulary, and
    # direct-command users can reach the same severance from
    # either verb.
    aliases = ("amputate",)
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

        # Specific location requested.  Issue #356 Phase 2: consult
        # the species-aware severable set so rat tails / forelegs are
        # recognised.
        from world.anatomy import get_species_severable_containers
        target_severable = get_species_severable_containers(
            getattr(getattr(target, "db", None), "species", None)
        )
        if location_arg not in target_severable:
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

        # Location still severable and not already taken (species-
        # aware per #356 Phase 2 — rats sever at tail / fore-/hindleg
        # not human containers).
        from world.anatomy import get_species_severable_containers
        if location_arg not in get_species_severable_containers(
            getattr(getattr(target, "db", None), "species", None)
        ):
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
