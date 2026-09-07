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
    character's body.  Abilities require a FUNCTIONAL organ: severed
    limbs took their hardware with them, harvested-out modules left a
    dead slot, and a destroyed hardpoint is so much shrapnel — all of
    those are 0-HP tombstones and power nothing."""
    state = getattr(character, "medical_state", None)
    organs = getattr(state, "organs", None) if state else None
    if not organs:
        return
    for organ in organs.values():
        if getattr(organ, "current_hp", 0) <= 0:
            continue
        data = getattr(organ, "data", None)
        abilities = data.get("abilities") if data else None
        if not abilities:
            continue
        for name, spec in abilities.items():
            yield organ, name, spec


def find_ability(character, name):
    """Return ``(organ, spec)`` for the named ability, or
    ``(None, None)``.

    The FIRST host, which is the right answer for reading a spec or
    asking whether an ability is deployed — :func:`find_ability_hosts`
    keeps every host's state identical. Use that one to WRITE.
    """
    wanted = (name or "").strip().lower()
    for organ, ability_name, spec in iter_abilities(character):
        if ability_name.lower() == wanted:
            return organ, spec
    return None, None


def find_ability_hosts(character, name):
    """Every living organ hosting the named ability.

    An ability can seat into more than one organ: a prototype's
    ``flesh_containers`` names each host, and the install loop in
    ``procedures.py`` seats the ability into all of them. ``NAILZ``
    declares both hands, and its own prose is unambiguous about being
    one thing — *"five per hand, both hands"*, *"ten carbide blades"*,
    *"your hands are just hands again"*.

    ``find_ability`` returned the first host and the toggles wrote to
    that organ alone, so the second hand's claws could never be reached
    and half the install was permanently inert (#2483).
    """
    wanted = (name or "").strip().lower()
    return [organ for organ, ability_name, _spec
            in iter_abilities(character)
            if ability_name.lower() == wanted]


def _mirror_ability_state(hosts, name, source):
    """Give every host of one ability the same runtime state.

    One ability is one thing even when it lives in two hands, so
    "deployed" and the weapon it points at must not differ between them.

    Severance is deliberately NOT mirrored: ``retract_all_hardware`` and
    ``carry_hardware_to_appendage`` walk organs themselves and clear the
    hand they are given, so losing a hand leaves the other one's blades
    out — which is what the prototype's own comment says should happen.
    """
    for host in hosts or ():
        state = _ability_state(host, name)
        if state is source:
            continue
        state.clear()
        state.update(source)


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

    # Every organ carrying this ability, not just the first: one tray
    # claws both hands (#2483).
    hosts = find_ability_hosts(character, name)

    ability_type = spec.get("type")
    if ability_type == "integrated_weapon":
        return _toggle_integrated_weapon(character, organ, name, spec, hosts)
    if ability_type == "natural_weapon":
        return _toggle_natural_weapon(character, organ, name, spec, hosts)
    if ability_type == "voice_modulator":
        return _toggle_voice_modulator(character, organ, name, spec, hosts)
    if ability_type == "blindsight":
        return _toggle_blindsight(character, organ, name, spec, hosts)
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


def _toggle_integrated_weapon(character, organ, name, spec, hosts=()) -> str:
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
        _mirror_ability_state(hosts, name, state)
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
    _mirror_ability_state(hosts, name, state)
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


def _toggle_natural_weapon(character, organ, name, spec, hosts=()) -> str:
    """Toggle a natural cyberweapon (#526 M4 — the claws family).

    Unlike integrated weapons, natural weapons never touch the hand
    slots: the claws ARE the hand.  The weapon item lives off-grid
    permanently; combat resolution reads it via the precedence rule
    (active natural cyberweapon > held weapon > fists — settled
    decision 2026-06-12: claws out means you fight with claws,
    knife in hand or not).
    """
    from world.identity_utils import msg_room_identity

    state = _ability_state(organ, name)
    if not state.get("deployed"):
        weapon = _get_or_spawn_weapon(character, state, spec)
        if weapon is None:
            return f"{name} grinds and fails — no hardware found."
        state["deployed"] = True
        _mirror_ability_state(hosts, name, state)
        _persist(character)
        msg = spec.get("deploy_msg") or (
            f"The {weapon.key} extend with a wet metallic whisper."
        )
        if character.location is not None:
            msg_room_identity(
                location=character.location,
                template=spec.get("deploy_room") or (
                    f"{{actor}}'s {weapon.key} slide out, catching "
                    f"the light."
                ),
                char_refs={"actor": character},
                exclude=[character],
            )
        return msg

    state["deployed"] = False
    _mirror_ability_state(hosts, name, state)
    _persist(character)
    weapon = _find_weapon(state)
    weapon_name = weapon.key if weapon else name
    msg = spec.get("retract_msg") or (
        f"The {weapon_name} retract, gone like they were never there."
    )
    if character.location is not None:
        msg_room_identity(
            location=character.location,
            template=spec.get("retract_room") or (
                f"{{actor}}'s {weapon_name} slide away out of sight."
            ),
            char_refs={"actor": character},
            exclude=[character],
        )
    return msg


def _toggle_voice_modulator(character, organ, name, spec, hosts=()) -> str:
    """Toggle a voice modulator (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4.2).

    The voice-disguise parallel to a worn mask: while engaged it sets
    ``character.db.voice_modulator_active``, which shifts the voice signature
    to a different UID (``world.voice.get_voice_signature``) so listeners no
    longer recognise the voice (and the discernment determination re-rolls
    against the new presentation). Covert by design — engaging it draws no room
    message; only the change in voice when the wearer next speaks is observable.
    """
    state = _ability_state(organ, name)
    if not state.get("deployed"):
        state["deployed"] = True
        character.db.voice_modulator_active = True
        _mirror_ability_state(hosts, name, state)
        _persist(character)
        return spec.get("deploy_msg") or (
            "Your voice modulator hums to life — your next words will carry "
            "a stranger's timbre."
        )

    state["deployed"] = False
    character.db.voice_modulator_active = False
    _mirror_ability_state(hosts, name, state)
    _persist(character)
    return spec.get("retract_msg") or (
        "Your voice modulator powers down — your own voice returns."
    )


def _toggle_blindsight(character, organ, name, spec, hosts=()) -> str:
    """Toggle a combat targeting / sonar suite — "blindsight".

    Sets ``character.db.blindsight_active``, which `world.combat.capacity`
    honours to restore combat aim even when the eyes are gone. Combat-only:
    it does NOT restore perception (rooms / faces stay dark) — that's the
    separate full-vision seam. (CAPACITY_CONSUMERS spec; user-decided
    combat-only 2026-06-20.)
    """
    from world.combat.capacity import BLINDSIGHT_FLAG

    state = _ability_state(organ, name)
    if not state.get("deployed"):
        state["deployed"] = True
        setattr(character.db, BLINDSIGHT_FLAG, True)
        _mirror_ability_state(hosts, name, state)
        _persist(character)
        return spec.get("deploy_msg") or (
            "Your targeting suite spins up — the world goes to wireframe and "
            "ranging data, and your aim steadies even with your eyes shut."
        )

    state["deployed"] = False
    setattr(character.db, BLINDSIGHT_FLAG, False)
    _mirror_ability_state(hosts, name, state)
    _persist(character)
    return spec.get("retract_msg") or (
        "Your targeting suite powers down; the firing solutions fade."
    )


def get_active_natural_weapon(character):
    """The deployed natural cyberweapon's item, or ``None`` (#526
    M4).  Consumed by combat's weapon resolution: active natural
    cyberweapons take precedence over held weapons (settled decision
    2026-06-12).  Severed organs drop out via :func:`iter_abilities`.
    """
    for organ, name, spec in iter_abilities(character):
        if spec.get("type") != "natural_weapon":
            continue
        store = getattr(organ, "ability_state", None) or {}
        if not (store.get(name) or {}).get("deployed"):
            continue
        weapon = _find_weapon(store.get(name) or {})
        if weapon is not None:
            return weapon
    return None


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


def _character_flag_for(ability_type):
    """The CHARACTER-level flag an ability type writes, if any.

    Two of the four toggleable abilities record the same fact twice —
    once on the organ (``ability_state["deployed"]``) and once on the
    character, because that is where the consumers read it
    (``world.voice.get_voice_signature``,
    ``world.combat.capacity``). The normal toggle-off clears both; the
    organ-LOSS hooks cleared only the organ half (#2580), so losing the
    limb while the ability was engaged left the effect on permanently —
    full accuracy with no eyes and no hardware — and the toggle refused
    to switch it off, because the organ it looks for was gone.
    """
    from world.combat.capacity import BLINDSIGHT_FLAG
    return {
        "voice_modulator": "voice_modulator_active",
        "blindsight": BLINDSIGHT_FLAG,
    }.get(ability_type)


def _clear_character_effect(character, organ, name):
    """Drop the character-level flag for ``name``, if losing this organ
    means nothing is driving it any more.

    Checked across the REMAINING living hosts rather than cleared
    outright: an ability can be seated in more than one organ (#2483),
    and losing one of a pair must not switch off the other.
    """
    data = getattr(organ, "data", None) or {}
    spec = (data.get("abilities") or {}).get(name) or {}
    flag = _character_flag_for(spec.get("type"))
    if not flag:
        return
    for other, other_name, _spec in iter_abilities(character):
        if other is organ or other_name.lower() != str(name).lower():
            continue
        if (_ability_state(other, other_name) or {}).get("deployed"):
            return          # another host still has it running
    try:
        setattr(character.db, flag, False)
    except Exception:  # noqa: BLE001 — losing a limb never fails on this
        pass


def park_organ_hardware(character, organ) -> None:
    """Retract and park one organ's ability hardware (#526 M3).

    Called when the organ is being removed from the body (module or
    organ harvest): any deployed weapon comes out of the hands and
    off the grid so it travels with the harvested item's spec rather
    than being orphaned — locked, undroppable, unretractable — in
    the hand of a body that no longer has the ability.
    """
    store = getattr(organ, "ability_state", None) or {}
    held = dict(getattr(character, "held_items", None) or {})
    held_changed = False
    for name, ability_state in store.items():
        if not isinstance(ability_state, dict):
            continue
        weapon = _find_weapon(ability_state)
        if weapon is not None:
            for slot, item in held.items():
                if item == weapon:
                    held[slot] = None
                    held_changed = True
            if weapon.location == character:
                weapon.location = None
        ability_state["deployed"] = False
        _clear_character_effect(character, organ, name)
    if held_changed:
        character.held_items = held


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
            _clear_character_effect(character, organ, name)
