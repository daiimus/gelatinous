"""Surgical procedure commands (#307 follow-up).

Four verbs forming the canonical procedure loop:

* ``incise <target> at <location>`` — open
* ``harvest <organ> from <target>`` — extract
* ``install <organ> in <target>`` — implant
* ``suture <target>`` — close (alias: ``stitch``)

All four route through :mod:`world.medical.procedures`.  Commands
are thin: argument parsing, target / item resolution, validation
(surgical kit, incision requirement, anesthesia hint), then
``start_procedure`` schedules the delayed resolver.

Surface treatments (bandages on skin, drugs into bloodstream)
remain on ``apply`` / ``inject`` / ``spray`` — see
:class:`commands.CmdConsumption.CmdApply` for the location-precision
upgrade.
"""

from __future__ import annotations

from evennia import Command

from world.medical.procedures import (
    PROCEDURE_DURATIONS,
    get_organ_snapshot,
    has_incision,
    is_procedure_active,
    open_incision_locations,
    organs_at_location,
    start_procedure,
)


def _incision_required(organ_data: dict) -> bool:
    """Whether an organ at ``organ_data`` requires an open incision
    at its container to be reached.

    The rule, settled in the #307 design pass: an organ whose
    ``display_location`` is *distinct* from its ``container`` has its
    own surface (eyes, ears, nose, tongue, jaw on humans).  Those
    organs are reachable without first opening the cavity that nominally
    houses them.  Organs whose ``display_location`` falls back to their
    ``container`` (the default when none is declared) live "inside"
    and need the container incised before they can be touched.

    Symmetric for harvest and install — the source/destination
    location's slot data drives the call equally for either verb.
    """
    container = organ_data.get("container")
    display = organ_data.get("display_location") or container
    return display == container


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------


def _find_surgical_kit(caller):
    """Return the first surgical kit in ``caller``'s inventory, or None."""
    for obj in caller.contents:
        attrs = getattr(obj, "attributes", None)
        if attrs is None:
            continue
        if attrs.get("medical_type") == "surgical_treatment":
            return obj
    return None


def _resolve_target(caller, raw_name):
    """Search the caller's location for a procedure target.

    Returns the matched object or ``None`` (search() already
    messages on ambiguity / not-found).
    """
    if raw_name.lower() in ("me", "self", "myself"):
        return caller
    return caller.search(raw_name, location=caller.location)


def _is_body_container(target) -> bool:
    """True when ``target`` exposes an organ snapshot."""
    return bool(get_organ_snapshot(target))


def _parse_target_with_location(args: str):
    """Parse ``"<target>'s <location>"`` or ``"<target> at <location>"``.

    Returns ``(target_phrase, location)`` with location normalised to
    its canonical underscore form, or ``(args, None)`` when no
    location qualifier is present.
    """
    args = args.strip()
    if "'s " in args:
        before, _, after = args.partition("'s ")
        return before.strip(), after.strip().replace(" ", "_")
    if " at " in args:
        before, _, after = args.partition(" at ")
        return before.strip(), after.strip().replace(" ", "_")
    return args, None


def _reject_if_busy(caller, target) -> bool:
    """True (and message-sent) when the target already has an active
    procedure that hasn't resolved yet."""
    if is_procedure_active(target):
        caller.msg(
            f"{target.get_display_name(caller)} is already partway "
            f"through a procedure. Wait for it to resolve or "
            f"interrupt them."
        )
        return True
    return False


# ---------------------------------------------------------------------
# CmdIncise — open
# ---------------------------------------------------------------------


class CmdIncise(Command):
    """Open an incision at a body location.

    Usage:
        incise <target> at <location>

    Examples:
        incise bob at chest
        incise the corpse at abdomen
        incise a severed left arm at left arm

    Required for deep procedures (harvest, install, applying
    treatments to internal organs).  Surface locations (limbs) and
    surface treatments (bandages on skin) don't need this.

    Requires a surgical kit in your inventory.  Conscious patients
    add difficulty and accumulate pain; unconscious / anesthetized
    patients are easier to work on.

    Related:  harvest, install, suture, apply.
    """

    key = "incise"
    aliases = ()
    help_category = "Medical"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg("Usage: incise <target> at <location>")
            return

        target_phrase, location = _parse_target_with_location(raw)
        if location is None:
            caller.msg(
                "Where do you want to make the incision? "
                "Usage: incise <target> at <location>"
            )
            return

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return  # search() messaged

        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can perform surgery on."
            )
            return

        if not organs_at_location(target, location):
            caller.msg(
                f"There's nothing at {location.replace('_', ' ')} on "
                f"{target.get_display_name(caller)} to incise."
            )
            return

        if has_incision(target, location):
            caller.msg(
                f"{target.get_display_name(caller)}'s "
                f"{location.replace('_', ' ')} is already open."
            )
            return

        if _reject_if_busy(caller, target):
            return

        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to perform an incision.")
            return

        # Stage the procedure — delay-resolved in
        # ``world.medical.procedures._resolve_incise``.
        start_procedure(
            target, verb="incise", actor=caller,
            location=location,
        )
        duration = PROCEDURE_DURATIONS["incise"]
        caller.msg(
            f"You begin cutting into {target.get_display_name(caller)}'s "
            f"{location.replace('_', ' ')}... ({duration}s)"
        )


# ---------------------------------------------------------------------
# CmdHarvest — extract
# ---------------------------------------------------------------------


class CmdHarvest(Command):
    """Extract an organ from a body container.

    Usage:
        harvest <organ> from <target>
        harvest <target>        (lists harvestable organs)

    Works on:
        * Corpses
        * Severed heads and limbs (each is an organ container)
        * Unconscious living characters
        * Conscious living characters (harder, more painful, organ
          may come out damaged — anesthetize them first via
          inject/apply)

    Requires an open incision at the organ's container.  Use
    ``incise`` first.  Surface anatomy (limbs) doesn't need
    incision; internal containers (head, chest, abdomen, back,
    neck, groin) do.

    Related:  incise, install, suture.
    """

    key = "harvest"
    aliases = ()
    help_category = "Medical"

    def func(self):  # noqa: C901
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg("Usage: harvest <organ> from <target>")
            return

        # Two forms: with " from " (do the harvest), without (list).
        if " from " in raw:
            organ_arg, _, target_phrase = raw.partition(" from ")
            organ_arg = organ_arg.strip().lower().replace(" ", "_")
        else:
            organ_arg = ""
            target_phrase = raw

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return

        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can harvest from."
            )
            return

        snapshot = get_organ_snapshot(target)
        organs = snapshot.get("organs") or {}

        # Build the harvestable set with the species-aware filter the
        # legacy CmdHarvest used on corpses — checks ``can_be_harvested``
        # against the proper organ spec, drops removed organs, drops
        # organs whose container has been severed off (the heart in
        # an arm-severed body is fine; in a torso-severed body it
        # left with the torso), and drops destroyed organs.
        from world.anatomy import get_organ_spec
        species = getattr(getattr(target, "db", None), "species", None)
        removed = set(getattr(target.db, "removed_organs", None) or [])
        severed_locs = set(
            getattr(target.db, "severed_locations", None) or []
        )
        harvestable = []
        for name, data in organs.items():
            if not isinstance(data, dict):
                continue
            spec = get_organ_spec(name, species) or {}
            if not spec.get("can_be_harvested"):
                continue
            if name in removed:
                continue
            if data.get("container") in severed_locs:
                continue
            if data.get("current_hp", 0) <= 0:
                continue
            harvestable.append(name)
        harvestable.sort()

        if not organ_arg:
            if not harvestable:
                caller.msg(
                    f"There are no harvestable organs in "
                    f"{target.get_display_name(caller)}."
                )
                return
            readable = ", ".join(o.replace("_", " ") for o in harvestable)
            caller.msg(
                f"Harvestable organs in {target.get_display_name(caller)}: "
                f"{readable}.\nUsage: harvest <organ> from <target>"
            )
            return

        if organ_arg not in organs:
            caller.msg(
                f"There is no {organ_arg.replace('_', ' ')} in "
                f"{target.get_display_name(caller)}."
            )
            return

        if organ_arg not in harvestable:
            caller.msg(
                f"The {organ_arg.replace('_', ' ')} in "
                f"{target.get_display_name(caller)} cannot be harvested "
                f"(already removed, destroyed, or not extractable)."
            )
            return

        organ_data = organs[organ_arg]
        container = organ_data.get("container")

        # Incision requirement: organs without a distinct display_location
        # live inside the container and need it opened first.  Surface
        # organs (eyes, ears, jaw, nose, tongue on humans) skip this.
        if _incision_required(organ_data) and not has_incision(target, container):
            caller.msg(
                f"You can't reach the {organ_arg.replace('_', ' ')} — "
                f"{container.replace('_', ' ')} isn't open. "
                f"Try ``incise {target_phrase} at {container.replace('_', ' ')}``."
            )
            return

        if _reject_if_busy(caller, target):
            return

        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to harvest an organ.")
            return

        start_procedure(
            target, verb="harvest", actor=caller,
            organ_name=organ_arg, location=container or "",
        )
        duration = PROCEDURE_DURATIONS["harvest"]
        caller.msg(
            f"You begin extracting the {organ_arg.replace('_', ' ')} "
            f"from {target.get_display_name(caller)}... ({duration}s)"
        )


# ---------------------------------------------------------------------
# CmdInstall — implant
# ---------------------------------------------------------------------


class CmdInstall(Command):
    """Install a harvested organ into a patient.

    Usage:
        install <organ> in <target>

    Examples:
        install heart in bob
        install left kidney in the corpse

    Requires the named organ in your inventory and an open incision
    at the appropriate body container on the target.  Use ``incise``
    first.  The harvested organ's condition and any organ-bound
    medical conditions (e.g. endocarditis from a previous host) travel
    with the install — a putrid heart that's been infected installs
    that way.

    Related:  incise, harvest, suture.
    """

    key = "install"
    aliases = ()
    help_category = "Medical"

    def func(self):  # noqa: C901
        caller = self.caller
        raw = (self.args or "").strip()
        if " in " not in raw:
            caller.msg("Usage: install <organ> in <target>")
            return

        item_phrase, _, target_phrase = raw.partition(" in ")
        item_phrase = item_phrase.strip()
        target_phrase = target_phrase.strip()

        organ_item = caller.search(item_phrase, location=caller)
        if organ_item is None:
            return

        organ_name = getattr(organ_item.db, "organ_name", None)
        if not organ_name:
            caller.msg(
                f"{organ_item.get_display_name(caller)} isn't a "
                f"harvested organ you can install."
            )
            return

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return

        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can install an organ into."
            )
            return

        # Find the target organ slot and its container.
        snapshot = get_organ_snapshot(target)
        target_organ_data = (snapshot.get("organs") or {}).get(organ_name)
        if target_organ_data is None:
            caller.msg(
                f"{target.get_display_name(caller)} has no slot for a "
                f"{organ_name.replace('_', ' ')}."
            )
            return

        container = target_organ_data.get("container")

        # Symmetric to harvest: organs with a distinct display_location
        # are surface-accessible and skip the incision requirement.
        if _incision_required(target_organ_data) and not has_incision(target, container):
            caller.msg(
                f"You can't reach the {organ_name.replace('_', ' ')} "
                f"slot — {container.replace('_', ' ')} isn't open. "
                f"Try ``incise {target_phrase} at {container.replace('_', ' ')}``."
            )
            return

        if _reject_if_busy(caller, target):
            return

        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to install an organ.")
            return

        start_procedure(
            target, verb="install", actor=caller,
            organ_item=organ_item, location=container or "",
        )
        duration = PROCEDURE_DURATIONS["install"]
        caller.msg(
            f"You begin installing the {organ_item.key} into "
            f"{target.get_display_name(caller)}... ({duration}s)"
        )


# ---------------------------------------------------------------------
# CmdSuture — close
# ---------------------------------------------------------------------


class CmdSuture(Command):
    """Close an open incision on a patient.

    Usage:
        suture <target>             (closes all open incisions)
        suture <target>'s <location> (closes one specific incision)

    Aliases:
        stitch

    Closes the wound created by ``incise``.  Leaving incisions open
    is bad for the patient — they bleed and risk infection.  A botched
    close seeds infection; a partial close holds but reads rough.

    Related:  incise, harvest, install.
    """

    key = "suture"
    aliases = ("stitch",)
    help_category = "Medical"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()
        if not raw:
            caller.msg(
                "Usage: suture <target>  (or)  "
                "suture <target>'s <location>"
            )
            return

        target_phrase, location = _parse_target_with_location(raw)
        target = _resolve_target(caller, target_phrase)
        if target is None:
            return

        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can suture."
            )
            return

        open_locs = open_incision_locations(target)
        if not open_locs:
            caller.msg(
                f"{target.get_display_name(caller)} has no open "
                f"incisions to close."
            )
            return

        if location is not None and location not in open_locs:
            caller.msg(
                f"{target.get_display_name(caller)}'s "
                f"{location.replace('_', ' ')} isn't incised."
            )
            return

        if _reject_if_busy(caller, target):
            return

        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to suture an incision.")
            return

        start_procedure(
            target, verb="suture", actor=caller,
            location=location,
        )
        duration = PROCEDURE_DURATIONS["suture"]
        caller.msg(
            f"You begin suturing "
            f"{target.get_display_name(caller)}'s wound... ({duration}s)"
        )
