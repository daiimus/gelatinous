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
    """Resolve a procedure target with identity-layer obfuscation.

    Three resolution stages, in order:

    1. **Identity pipeline** (``resolve_character_target``) — the
       *only* path to a character target.  Handles default sdescs
       ("towering", "woman"), recognised-name keywords, and disguise
       overrides.  Has its own staff fallback for builders that
       cannot find an identity match (key-based search), so the
       privileged-key path is preserved for admins without leaking
       through to ordinary players.
    2. **Inventory fallback** — searches the caller's contents for
       non-character targets (severed appendages held in hand,
       corpses being carried, etc.).  Characters can't be in
       inventory, so this is naturally character-free.
    3. **Room fallback** — searches the caller's location for
       non-character targets only.  Characters are filtered out so
       a player can't bypass identity obfuscation by typing a real
       character key.  Corpses, severed appendages, and items
       resolve here.

    Returns the matched object or ``None``.  The identity helper
    emits its own messages on ambiguity; the search fallbacks emit
    not-found messages.
    """
    if raw_name.lower() in ("me", "self", "myself"):
        return caller

    # Stage 1 — identity pipeline (only path to character targets).
    #
    # Detached body parts (``SeveredHead``, ``Appendage``) participate in
    # identity for forensic chain / autopsy purposes — they have a
    # ``get_sdesc`` and carry an ``apparent_uid_at_death``.  But surgical
    # commands target whole-body patients, not detached parts.  When
    # both a body and its severed head are in the room (e.g.
    # ``operate 1st rat`` after decapitation), the ordinal pick from
    # the identity match would silently land on whichever the room
    # iteration orders first — usually the head, since severed parts
    # spawn after the body.  Filtering detached parts out at this
    # stage means the identity matcher's candidate set only contains
    # whole-body patients, so the ordinal picks among them
    # unambiguously and detached parts route through stages 2/3 (where
    # ``autopsy`` / ``sever`` / ``harvest`` find them).
    from commands._identity_targeting import resolve_character_target
    from typeclasses.items import Appendage  # base for SeveredHead too
    location = caller.location
    if location is not None:
        whole_body_candidates = [
            obj for obj in location.contents
            if not isinstance(obj, Appendage)
        ]
    else:
        whole_body_candidates = None
    identity_match = resolve_character_target(
        caller, raw_name,
        candidates=whole_body_candidates,
        allow_self=False,
    )
    if identity_match is not None:
        return identity_match

    # Stage 2 — inventory fallback (non-character targets only;
    # characters can't be held).
    inventory_match = caller.search(
        raw_name, location=caller, quiet=True,
    )
    if inventory_match:
        return (
            inventory_match[0]
            if isinstance(inventory_match, list)
            else inventory_match
        )

    # Stage 3 — room fallback, characters filtered out so the
    # identity layer is the only path to a character target.
    # Characters in the same room would otherwise match their real
    # key here, leaking through identity obfuscation.
    from typeclasses.characters import Character
    location = caller.location
    if location is None:
        return None
    non_character_candidates = [
        obj for obj in location.contents
        if not isinstance(obj, Character)
    ]
    if not non_character_candidates:
        # Send a "not found" message via caller.search with the
        # filtered candidate set — empty candidate list still
        # triggers the standard not-found broadcast.
        return caller.search(raw_name, candidates=[], quiet=False)
    return caller.search(
        raw_name, candidates=non_character_candidates,
    )


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
        caller.msg(
            f"You begin cutting into {target.get_display_name(caller)}'s "
            f"{location.replace('_', ' ')}..."
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
            # Duck-type rather than ``isinstance(data, dict)`` —
            # Evennia's ``_SaverDict`` wraps persisted snapshot
            # entries and isn't a dict subclass, so isinstance
            # would silently filter every organ on a corpse target.
            # See ``world.medical.procedures.organs_at_location``
            # for the original bug + fix this mirrors.
            if not hasattr(data, "get"):
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
        caller.msg(
            f"You begin extracting the {organ_arg.replace('_', ' ')} "
            f"from {target.get_display_name(caller)}..."
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
            caller.msg("Usage: install <organ> in <target> [at <side/location>]")
            return

        item_phrase, _, target_phrase = raw.partition(" in ")
        item_phrase = item_phrase.strip()
        target_phrase = target_phrase.strip()

        # Optional side / location suffix (#526 M2/M3):
        # ``install cyber arm in bob at left`` (side-agnostic chassis)
        # ``install shotgun module in bob at left arm`` (hardpoint pick)
        side_or_location = None
        if " at " in target_phrase:
            target_phrase, _, side_or_location = target_phrase.partition(" at ")
            target_phrase = target_phrase.strip()
            side_or_location = (
                side_or_location.strip().lower().replace(" ", "_")
            )

        organ_item = caller.search(item_phrase, location=caller)
        if organ_item is None:
            return

        # Augment items (ANATOMY_AUGMENTS_SPEC §3.3) carry their own
        # anatomy and CREATE their slot instead of requiring one —
        # they branch before the harvested-organ gate.
        if getattr(organ_item.db, "augment_organs", None):
            self._install_augment(
                caller, organ_item, target_phrase,
                side=side_or_location,
            )
            return

        # Ability modules (#526 M3) seat into chassis hardpoints —
        # placement comes from the slot, not the organ name.
        module_type = (
            getattr(organ_item.db, "module_type", None)
            or (getattr(organ_item.db, "organ_spec", None) or {}).get("module_type")
        )
        if module_type:
            self._install_module(
                caller, organ_item, target_phrase, module_type,
                side_or_location=side_or_location,
            )
            return

        # Severed cybernetic limbs (#526 follow-up) reattach whole —
        # an Appendage whose snapshot carries inorganic anatomy.
        from world.medical.procedures import is_cybernetic_limb
        if is_cybernetic_limb(organ_item):
            self._install_limb(caller, organ_item, target_phrase)
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
        caller.msg(
            f"You begin installing the {organ_item.key} into "
            f"{target.get_display_name(caller)}..."
        )

    def _install_augment(self, caller, organ_item, target_phrase,
                         side=None):
        """Stage an augment install (ANATOMY_AUGMENTS_SPEC §3.3).

        Pre-dispatch gates: living target, species compatibility
        (carried on the item — synth expansion is an item-data
        edit), no healthy anatomy already at the augment container,
        and an open incision at the **anchor** (the slot doesn't
        exist yet; you cut where the hardware mounts).

        ``side`` resolves side-agnostic chassis (#526 M2): one
        CYBER_ARM prototype mounts left or right; the surgeon names
        the side (``install cyber arm in bob at left``).
        """
        # Normalize side input ("left arm" → "left").
        if side:
            side = side.split("_")[0]
            if side not in ("left", "right"):
                caller.msg("Side must be left or right.")
                return

        from world.medical.procedures import resolve_augment_declaration
        declaration = resolve_augment_declaration(organ_item.db, side=side)
        if declaration["side_agnostic"] and not side:
            caller.msg(
                f"The {organ_item.key} mounts on either side — name "
                f"one: ``install {organ_item.key} in {target_phrase} "
                f"at left`` (or right)."
            )
            return

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return

        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can install an augment into."
            )
            return

        # Living integration only: corpse organ snapshots can't grow
        # new anatomy.
        state = getattr(target, "medical_state", None)
        if state is None or not getattr(state, "organs", None):
            caller.msg(
                f"The {organ_item.key} needs a living body to "
                f"integrate with."
            )
            return

        species = getattr(target.db, "species", None) or "human"
        # ``compatible_species`` is the established cyberware gate;
        # ``species_compat`` accepted for pre-unification items.
        compat = [
            s.lower() for s in (
                organ_item.db.compatible_species
                or organ_item.db.species_compat or []
            )
        ]
        if species.lower() not in compat:
            caller.msg(
                f"The {organ_item.key}'s mounting hardware isn't "
                f"rated for {species} anatomy."
            )
            return

        # Multi-container gate (spec §3.5): a replacement augment
        # (the shotgun arm spans right_arm + right_hand) declares
        # organs at several containers — every one must be free of
        # LIVING anatomy.  Stumps and pulped wreckage both admit the
        # mount (user decision 2026-06-13: sever and amputate are one
        # path, and the install surgery clears ruined remains the
        # same way it clears severed remnants).
        augment_container = declaration["container"]
        augment_organs = declaration["organs"]
        declared = {
            spec.get("container")
            for spec in augment_organs.values()
            if hasattr(spec, "get")
        } - {None}
        blocking = [
            organ for organ in state.organs.values()
            if getattr(organ, "container", None) in declared
            and organ.current_hp > 0
        ]
        if blocking:
            container = blocking[0].container
            caller.msg(
                f"{target.get_display_name(caller)} still has a "
                f"living {container.replace('_', ' ')} — the "
                f"{organ_item.key} mounts over a stump or wreckage, "
                f"not living anatomy."
            )
            return

        anchor = declaration["anchor"] or augment_container
        if not has_incision(target, anchor):
            caller.msg(
                f"The {organ_item.key} mounts at the "
                f"{anchor.replace('_', ' ')}, and "
                f"{target.get_display_name(caller)}'s "
                f"{anchor.replace('_', ' ')} isn't open. "
                f"Try ``incise {target_phrase} at "
                f"{anchor.replace('_', ' ')}``."
            )
            return

        if _reject_if_busy(caller, target):
            return

        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to install an augment.")
            return

        start_procedure(
            target, verb="install_augment", actor=caller,
            organ_item=organ_item, location=anchor, side=side,
        )
        caller.msg(
            f"You begin mounting the {organ_item.key} at "
            f"{target.get_display_name(caller)}'s "
            f"{anchor.replace('_', ' ')}..."
        )

    def _install_module(self, caller, organ_item, target_phrase,
                        module_type, side_or_location=None):
        """Stage an ability-module install (#526 M3): the module
        seats into a free chassis hardpoint.  With hardpoints on
        both sides, the surgeon names one (``at left`` /
        ``at left arm``)."""
        from world.medical.procedures import find_hardpoint

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return
        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can install a module into."
            )
            return
        state = getattr(target, "medical_state", None)
        if state is None or not getattr(state, "organs", None):
            caller.msg(
                f"The {organ_item.key} needs a living body to "
                f"integrate with."
            )
            return

        species = getattr(target.db, "species", None) or "human"
        compat = [
            s.lower() for s in (organ_item.db.compatible_species or [])
        ]
        if compat and species.lower() not in compat:
            caller.msg(
                f"The {organ_item.key} isn't rated for {species} "
                f"anatomy."
            )
            return

        # Collect candidate mount containers, optionally filtered by
        # side.  Hardpoint modules want a free chassis slot; flesh
        # modules (#526 M4 — Nailz/Jawz class) want LIVING anatomy
        # at one of their declared containers.
        mount_mode = (
            getattr(organ_item.db, "module_mount", None) or "hardpoint"
        )
        candidates = []
        if mount_mode == "flesh":
            declared = []
            for raw in (organ_item.db.flesh_containers or []):
                if "{side}" in raw:
                    declared.extend(
                        raw.replace("{side}", s) for s in ("left", "right")
                    )
                else:
                    declared.append(raw)
            new_ability_names = set(
                ((organ_item.db.organ_spec or {}).get("abilities") or {})
            )
            flesh_organ = getattr(organ_item.db, "flesh_organ", None)
            for container in declared:
                if side_or_location:
                    side = side_or_location.split("_")[0]
                    if not container.startswith(side):
                        continue
                # Specific named host (JAWZ → jaw) or first living
                # organ at the container (NAILZ → the lone hand organ).
                if flesh_organ:
                    host = state.organs.get(flesh_organ)
                    if host is not None and host.current_hp <= 0:
                        host = None
                else:
                    host = next(
                        (o for o in state.organs.values()
                         if getattr(o, "container", None) == container
                         and o.current_hp > 0),
                        None,
                    )
                if host is None:
                    continue
                if new_ability_names & set(host.data.get("abilities") or {}):
                    continue  # already carries this hardware
                candidates.append((container, container))
        else:
            for organ_name, organ in state.organs.items():
                data = getattr(organ, "data", None)
                if not data or data.get("hardpoint") != module_type:
                    continue
                if bool(data.get("abilities")) and organ.current_hp > 0:
                    continue  # occupied
                container = getattr(organ, "container", None) or ""
                if side_or_location:
                    side = side_or_location.split("_")[0]
                    if not container.startswith(side):
                        continue
                candidates.append((organ_name, container))

        if not candidates:
            if mount_mode == "flesh":
                caller.msg(
                    f"Nowhere on {target.get_display_name(caller)} "
                    f"for the {organ_item.key} — it needs living "
                    f"anatomy at a compatible location, without that "
                    f"hardware already in it."
                )
            else:
                caller.msg(
                    f"No free {module_type.replace('_', ' ')} hardpoint "
                    f"on {target.get_display_name(caller)} — the "
                    f"{organ_item.key} needs a chassis slot (and an "
                    f"unoccupied one)."
                )
            return
        if len({c for _n, c in candidates}) > 1:
            sides = ", ".join(sorted(c.replace("_", " ") for _n, c in candidates))
            caller.msg(
                f"{target.get_display_name(caller)} has free "
                f"hardpoints at: {sides}.  Name one — ``install "
                f"{organ_item.key} in {target_phrase} at left`` (or "
                f"right)."
            )
            return

        container = candidates[0][1]
        if not has_incision(target, container):
            caller.msg(
                f"The hardpoint sits inside "
                f"{target.get_display_name(caller)}'s "
                f"{container.replace('_', ' ')} — it isn't open. "
                f"Try ``incise {target_phrase} at "
                f"{container.replace('_', ' ')}``."
            )
            return

        if _reject_if_busy(caller, target):
            return
        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to seat a module.")
            return

        start_procedure(
            target, verb="install_module", actor=caller,
            organ_item=organ_item, location=container,
        )
        caller.msg(
            f"You begin seating the {organ_item.key} into the "
            f"hardpoint at {target.get_display_name(caller)}'s "
            f"{container.replace('_', ' ')}..."
        )

    def _install_limb(self, caller, organ_item, target_phrase):
        """Stage a severed-cybernetic-limb reattachment (#526
        follow-up): bolt the whole limb back on over a stump.

        Pre-dispatch gates: living target, the target has a stump at
        every one of the limb's containers (amputate first — looted
        chrome bolts onto any compatible body), and an open incision
        at the cut point.  The resolver re-checks all of these.
        """
        from world.medical.procedures import get_organ_snapshot

        target = _resolve_target(caller, target_phrase)
        if target is None:
            return
        if not _is_body_container(target):
            caller.msg(
                f"{target.get_display_name(caller)} isn't something "
                f"you can reattach a limb to."
            )
            return
        state = getattr(target, "medical_state", None)
        if state is None or not getattr(state, "organs", None):
            caller.msg(
                f"The {organ_item.key} needs a living body to "
                f"reattach to."
            )
            return

        snapshot = get_organ_snapshot(organ_item)
        organs_data = (snapshot or {}).get("organs") or {}
        declared = {
            d.get("container") for d in organs_data.values()
            if hasattr(d, "get") and d.get("container")
        }
        target_containers = {
            getattr(o, "container", None) for o in state.organs.values()
        }
        missing = declared - target_containers
        if missing:
            nice = ", ".join(sorted(c.replace("_", " ") for c in missing))
            caller.msg(
                f"{target.get_display_name(caller)} has nowhere to "
                f"attach the {organ_item.key} — no {nice}."
            )
            return
        living = [
            o for o in state.organs.values()
            if getattr(o, "container", None) in declared and o.current_hp > 0
        ]
        if living:
            container = living[0].container
            caller.msg(
                f"{target.get_display_name(caller)} still has a living "
                f"{container.replace('_', ' ')} — amputate before "
                f"reattaching the {organ_item.key}."
            )
            return

        # Anchor = the limb's cut point (its severed location).
        anchor = getattr(organ_item.db, "location_name", None)
        if anchor not in declared:
            anchor = sorted(declared)[0] if declared else None
        if not anchor or not has_incision(target, anchor):
            anchor_disp = (anchor or "the stump").replace("_", " ")
            caller.msg(
                f"The {organ_item.key} bolts on at the {anchor_disp}, "
                f"and {target.get_display_name(caller)}'s {anchor_disp} "
                f"isn't open. Try ``incise {target_phrase} at "
                f"{anchor_disp}``."
            )
            return

        if _reject_if_busy(caller, target):
            return
        kit = _find_surgical_kit(caller)
        if kit is None:
            caller.msg("You need a surgical kit to reattach a limb.")
            return

        start_procedure(
            target, verb="install_limb", actor=caller,
            organ_item=organ_item, location=anchor,
        )
        caller.msg(
            f"You begin reattaching the {organ_item.key} to "
            f"{target.get_display_name(caller)}'s "
            f"{anchor.replace('_', ' ')}..."
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
        caller.msg(
            f"You begin suturing "
            f"{target.get_display_name(caller)}'s wound..."
        )
