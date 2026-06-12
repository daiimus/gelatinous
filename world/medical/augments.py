"""Toggled cyberware abilities (AUGMENT_ABILITIES_SPEC, issue #516).

Abilities live on organs: an augment item's organ spec carries an
``abilities`` dict (see spec §2), which the anatomy substrate
persists and severs with the organ.  Installed means the ability
exists; severed means it's gone — no registry.

The single dispatcher command (``commands.CmdCyberware``) parses
``/<ability>`` and calls :func:`toggle_ability` here.  The prefix
lives in :data:`CYBERWARE_COMMAND_PREFIX` — swapping ``/`` for ``=``
later is this one constant.

The integrated_weapon type exploits held-is-wielded: deploying
moves a locked weapon item INTO the hand slot, which simultaneously
makes the hand unusable for holding and makes the weapon the active
combat weapon (``get_wielded_weapon`` reads hands).  Retracting
parks the item off-grid (``location = None`` — it is folded inside
your arm, not in your backpack).
"""

from __future__ import annotations


#: The cyberware command prefix.  ``/shotgun`` toggles the shotgun
#: ability.  May become ``=`` or anything else — change it HERE ONLY
#: (the dispatcher keys itself on this constant).
CYBERWARE_COMMAND_PREFIX = "/"


# ---------------------------------------------------------------------
# Ability lookup
# ---------------------------------------------------------------------


def iter_abilities(character):
    """Yield ``(organ, ability_name, spec)`` for every ability on the
    character's body.  Severed organs are skipped — the hardware left
    with the limb."""
    state = getattr(character, "medical_state", None)
    organs = getattr(state, "organs", None) if state else None
    if not organs:
        return
    for organ in organs.values():
        if getattr(organ, "wound_stage", None) == "severed":
            continue
        data = getattr(organ, "data", None)
        abilities = data.get("abilities") if data else None
        if not abilities:
            continue
        for name, spec in abilities.items():
            yield organ, name, spec


def find_ability(character, name):
    """Return ``(organ, spec)`` for the named ability, or
    ``(None, None)``."""
    wanted = (name or "").strip().lower()
    for organ, ability_name, spec in iter_abilities(character):
        if ability_name.lower() == wanted:
            return organ, spec
    return None, None


# ---------------------------------------------------------------------
# Toggle dispatch
# ---------------------------------------------------------------------


def toggle_ability(character, name) -> str:
    """Toggle the named ability.  Returns the message for the caller
    (room messages are broadcast inside).  All gates live here so the
    dispatcher command stays a thin parser."""
    organ, spec = find_ability(character, name)
    if organ is None:
        available = sorted(
            ability for _o, ability, _s in iter_abilities(character)
        )
        if available:
            listing = ", ".join(
                f"{CYBERWARE_COMMAND_PREFIX}{a}" for a in available
            )
            return f"No such cyberware. You have: {listing}"
        return "You have no cyberware to command."

    # Body gates: the dead and the unconscious don't toggle hardware.
    state = getattr(character, "medical_state", None)
    if state is not None and callable(getattr(state, "is_dead", None)) and state.is_dead():
        return "You are dead."
    if callable(getattr(character, "is_unconscious", None)) and character.is_unconscious():
        return "You are unconscious."

    ability_type = spec.get("type")
    if ability_type == "integrated_weapon":
        return _toggle_integrated_weapon(character, organ, name, spec)
    return f"{name} doesn't respond. (unknown ability type {ability_type!r})"


def list_abilities(character) -> str:
    """The bare-prefix listing: every installed ability + state."""
    lines = []
    for organ, name, spec in iter_abilities(character):
        ability_state = _ability_state(organ, name)
        deployed = ability_state.get("deployed", False)
        tag = "deployed" if deployed else "retracted"
        lines.append(f"  {CYBERWARE_COMMAND_PREFIX}{name} — {tag}")
    if not lines:
        return "You have no cyberware to command."
    return "Installed cyberware:\n" + "\n".join(lines)


# ---------------------------------------------------------------------
# integrated_weapon
# ---------------------------------------------------------------------


def _ability_state(organ, name) -> dict:
    """Runtime state bucket for one ability on one organ.  Lives on
    ``organ.ability_state`` (persisted alongside stabilized /
    tourniqueted)."""
    store = getattr(organ, "ability_state", None)
    if store is None:
        store = {}
        organ.ability_state = store
    return store.setdefault(name, {})


def _toggle_integrated_weapon(character, organ, name, spec) -> str:
    from world.identity_utils import msg_room_identity

    state = _ability_state(organ, name)
    slot = spec.get("slot")
    if not slot:
        return f"{name} has no slot configured — report this."

    if not state.get("deployed"):
        # ── Deploy ────────────────────────────────────────────────
        hands = getattr(character, "hands", None) or {}
        if slot not in hands:
            # Slot anatomy gone (severed hand on a surviving arm
            # organ, or species drift) — nothing to transform.
            return (
                f"Your {slot.replace('_', ' ')} isn't there to "
                f"transform."
            )

        weapon = _get_or_spawn_weapon(character, state, spec)
        if weapon is None:
            return f"{name} grinds and fails — no weapon hardware found."

        # Auto-drop whatever the hand held (settled decision: the
        # hand transforms regardless; the knife clatters down).
        # Never the weapon itself — a state desync that left the gun
        # seated must not hurl the integrated gun to the floor.
        held = hands.get(slot)
        if held == weapon:
            held = None
        if held is not None and character.location is not None:
            held.move_to(character.location, quiet=True)
            character.msg(
                f"Your {slot.replace('_', ' ')} splits open — "
                f"{held.get_display_name(character)} clatters to the "
                f"ground."
            )
            msg_room_identity(
                location=character.location,
                template=(
                    f"{{actor}} drops {held.key} as their "
                    f"{slot.replace('_', ' ')} reconfigures."
                ),
                char_refs={"actor": character},
                exclude=[character],
            )

        # Self-healing seat (#516 playtest): if the weapon is somehow
        # referenced from another slot (legacy state from before the
        # inventory-verb guards), clear those references first so the
        # gun exists in exactly one place — its spec slot.
        held = dict(character.held_items or {})
        stale = [k for k, v in held.items() if v == weapon and k != slot]
        if stale:
            for k in stale:
                held[k] = None
            character.held_items = held

        weapon.location = character
        character.hands = {slot: weapon}
        state["deployed"] = True
        _persist(character)

        deploy_msg = spec.get("deploy_msg") or (
            f"Servos whine — the {weapon.key} deploys from your "
            f"{slot.replace('_', ' ')}."
        )
        if character.location is not None:
            msg_room_identity(
                location=character.location,
                template=spec.get("deploy_room") or (
                    f"{{actor}}'s {slot.replace('_', ' ')} "
                    f"reconfigures into a {weapon.key} with a snap of "
                    f"locking servos."
                ),
                char_refs={"actor": character},
                exclude=[character],
            )
        return deploy_msg

    # ── Retract ───────────────────────────────────────────────────
    weapon = _find_weapon(state)
    if weapon is not None:
        # Clear the slot the weapon is ACTUALLY in — scanned, not
        # assumed — so a gun displaced into the wrong slot by legacy
        # state still retracts cleanly instead of leaving a ghost.
        held = dict(character.held_items or {})
        cleared = False
        for k, v in held.items():
            if v == weapon:
                held[k] = None
                cleared = True
        if cleared:
            character.held_items = held
        if weapon.location == character:
            weapon.location = None  # folded back inside the arm
    state["deployed"] = False
    _persist(character)

    retract_msg = spec.get("retract_msg") or (
        f"The hardware folds away — your {slot.replace('_', ' ')} "
        f"is a hand again."
    )
    if character.location is not None:
        msg_room_identity(
            location=character.location,
            template=spec.get("retract_room") or (
                f"{{actor}}'s weapon hardware folds back into their "
                f"{slot.replace('_', ' ')}."
            ),
            char_refs={"actor": character},
            exclude=[character],
        )
    return retract_msg


def _find_weapon(state):
    """Resolve the ability's weapon item from its recorded dbref."""
    dbref = state.get("weapon_dbref")
    if not dbref:
        return None
    from evennia.utils.search import search_object
    found = search_object(dbref)
    return found[0] if found else None


def _get_or_spawn_weapon(character, state, spec):
    """The ability's weapon item — lazily spawned on first deploy,
    then reused for the life of the augment.  Locked and flagged
    integrated regardless of what the prototype declares
    (belt-and-suspenders: this item must never leave the body by any
    path but severance)."""
    weapon = _find_weapon(state)
    if weapon is not None:
        return weapon

    prototype = spec.get("weapon_prototype")
    if not prototype:
        return None
    try:
        from evennia.prototypes.spawner import spawn
        spawned = spawn(prototype)
    except Exception:
        return None
    if not spawned:
        return None
    weapon = spawned[0]
    weapon.locks.add("get:false();drop:false();give:false()")
    weapon.db.integrated = True
    state["weapon_dbref"] = weapon.dbref
    return weapon


def _persist(character):
    save = getattr(character, "save_medical_state", None)
    if callable(save):
        save()


# ---------------------------------------------------------------------
# Severance integration
# ---------------------------------------------------------------------


def carry_hardware_to_appendage(character, chain, appendage) -> None:
    """Move integrated hardware whose organ just severed onto the
    severed appendage (spec decision 7: the limb takes its gear).

    Deployed weapons travel automatically (they sit in ``held_items``
    and ``detach_items_to_appendage`` already moved them); this hook
    covers the RETRACTED case — the item parked at ``location=None``,
    folded inside the arm that just hit the floor.  Idempotent for
    the deployed case.
    """
    state = getattr(character, "medical_state", None)
    organs = getattr(state, "organs", None) if state else None
    if not organs:
        return
    chain_set = set(chain)
    for organ in organs.values():
        if getattr(organ, "container", None) not in chain_set:
            continue
        store = getattr(organ, "ability_state", None) or {}
        for name, ability_state in store.items():
            if not isinstance(ability_state, dict):
                continue
            weapon = _find_weapon(ability_state)
            if weapon is not None and weapon.location is not appendage:
                weapon.location = appendage
            ability_state["deployed"] = False
