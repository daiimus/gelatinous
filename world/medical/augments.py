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

#: Toggle prose keys an ability spec may carry for the case where it
#: lives in two or more hosts and exactly ONE of them changed (a hand
#: the other hand's claws are already out of). They take ``{hand}``,
#: pre-interpolated here before any room broadcast. Absent, the base
#: keys are used (MULTI_WEAPON_COMBAT_SPEC §7).
ABILITY_MSG_DEPLOY_ONE = "deploy_msg_one"
ABILITY_MSG_RETRACT_ONE = "retract_msg_one"
ABILITY_ROOM_DEPLOY_ONE = "deploy_room_one"
ABILITY_ROOM_RETRACT_ONE = "retract_room_one"


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

    The FIRST host, which is the right answer for reading a spec. Each
    host keeps its OWN state since MULTI_WEAPON_COMBAT_SPEC (a hand's
    claws are that hand's): ask :func:`is_ability_deployed` whether an
    ability is out anywhere, and :func:`find_ability_hosts` to act on
    every host.
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


def is_ability_deployed(character, name) -> bool:
    """Is the named ability out on ANY living host? One predicate for
    every reader that wants a yes or no (the toggle's mixed-state rule,
    the security director's draw and stow, the readouts)."""
    return any(_ability_state(host, name).get("deployed")
               for host in find_ability_hosts(character, name))


def _spec_of(organ, name):
    """The ability spec as THIS host carries it (an install bakes the
    side into a hand's or arm's prose and slot)."""
    data = getattr(organ, "data", None) or {}
    return (data.get("abilities") or {}).get(name) or {}


def _hand_of(organ) -> str:
    container = getattr(organ, "display_location", None) or getattr(organ, "container", None) or "hand"
    return str(container).replace("_", " ")


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
    # Busy gate (AUGMENT_ABILITIES_SPEC §3.2, #3360): nobody works their
    # hardware while a surgeon is inside them. The surgeon stows anything
    # deployed at the cut when the procedure starts (`stow_abilities_at`);
    # this keeps the patient from popping it back out mid-incision.
    # Deliberately NOT gated on channeled acts (owner ruling 2026-09-13):
    # a shotgun arm must deploy the moment combat starts, and sensory
    # hardware is meant to be used whenever.
    from world.medical.procedures import is_procedure_active
    if is_procedure_active(character):
        return "You can't work your hardware while a procedure is underway on you."

    # Every organ carrying this ability, not just the first: one tray
    # claws both hands (#2483). Each hand keeps its own state; the one
    # word acts on all of them, and a mixed state syncs by retracting
    # (owner, 2026-10-05: "Retract both to sync up makes sense.").
    hosts = find_ability_hosts(character, name)
    return _dispatch_toggle(character, name, spec, hosts,
                            deploy=not is_ability_deployed(character, name))


_TOGGLERS = {
    "integrated_weapon": "_toggle_integrated_weapon",
    "natural_weapon": "_toggle_natural_weapon",
    "voice_modulator": "_toggle_voice_modulator",
    "blindsight": "_toggle_blindsight",
}

#: Ability types whose toggle is covert: no room line (the voice
#: modulator is noticed only when the wearer next speaks).
_COVERT_TYPES = ("voice_modulator", "blindsight")


def _dispatch_toggle(character, name, spec, hosts, deploy) -> str:
    """Bring every host in ``hosts`` to ``deploy`` (True = out). Each
    per-type toggle acts on ONE host and changes state only; this is the
    one place prose is spoken, so a two-handed ability says one self
    line and one room line however many hosts changed. Shared by
    `toggle_ability` and `stow_abilities_at`, so the surgical stow uses
    the SAME retract path (hands restored, room told) as a player's own
    `retract`."""
    from world.identity_utils import msg_room_identity

    ability_type = spec.get("type")
    toggler_name = _TOGGLERS.get(ability_type)
    if toggler_name is None:
        return f"{name} doesn't respond. (unknown ability type {ability_type!r})"
    toggler = globals()[toggler_name]

    changed, failures, weapon = [], [], None
    for host in hosts:
        state = _ability_state(host, name)
        if bool(state.get("deployed")) == deploy:
            continue
        ok, failure, item = toggler(character, host, name, _spec_of(host, name) or spec, state, deploy)
        if ok:
            changed.append(host)
            weapon = weapon or item
        elif failure:
            failures.append(failure)
    if not changed:
        return " ".join(failures) if failures else (
            f"{name} is already {'deployed' if deploy else 'retracted'}.")
    _persist(character)

    one_of_many = len(hosts) >= 2 and len(changed) == 1
    hand = _hand_of(changed[0])
    weapon_name = weapon.key if weapon is not None else name
    slot = (_spec_of(changed[0], name) or spec).get("slot") or hand
    self_line, room_line = _toggle_prose(
        ability_type, spec, deploy, one_of_many, hand, weapon_name, slot)
    if room_line and ability_type not in _COVERT_TYPES and character.location is not None:
        msg_room_identity(
            location=character.location,
            template=room_line,
            char_refs={"actor": character},
            exclude=[character],
        )
    if failures:
        self_line = self_line + " " + " ".join(failures)
    return self_line


def _toggle_prose(ability_type, spec, deploy, one_of_many, hand, weapon_name, slot):
    """The self line and the room template for a toggle. The spec's own
    prose first (the ``_one`` keys when exactly one of several hosts
    changed), then the type's default. ``{hand}`` is interpolated here;
    ``{actor}`` is left for `msg_room_identity`."""
    if deploy:
        self_key, room_key = ("deploy_msg", "deploy_room")
        one_self, one_room = (ABILITY_MSG_DEPLOY_ONE, ABILITY_ROOM_DEPLOY_ONE)
    else:
        self_key, room_key = ("retract_msg", "retract_room")
        one_self, one_room = (ABILITY_MSG_RETRACT_ONE, ABILITY_ROOM_RETRACT_ONE)
    self_line = (one_of_many and spec.get(one_self)) or spec.get(self_key)
    room_line = (one_of_many and spec.get(one_room)) or spec.get(room_key)
    slot_words = str(slot).replace("_", " ")
    if ability_type == "integrated_weapon":
        self_line = self_line or (
            f"Servos whine — the {weapon_name} deploys from your {slot_words}." if deploy
            else f"The hardware folds away — your {slot_words} is a hand again.")
        room_line = room_line or (
            f"{{actor}}'s {slot_words} reconfigures into a {weapon_name} with a snap of locking servos." if deploy
            else f"{{actor}}'s weapon hardware folds back into their {slot_words}.")
    elif ability_type == "natural_weapon":
        self_line = self_line or (
            f"The {weapon_name} extend with a wet metallic whisper." if deploy
            else f"The {weapon_name} retract, gone like they were never there.")
        room_line = room_line or (
            f"{{actor}}'s {weapon_name} slide out, catching the light." if deploy
            else f"{{actor}}'s {weapon_name} slide away out of sight.")
    elif ability_type == "voice_modulator":
        self_line = self_line or (
            "Your voice modulator hums to life — your next words will carry a stranger's timbre." if deploy
            else "Your voice modulator powers down — your own voice returns.")
        room_line = None
    elif ability_type == "blindsight":
        self_line = self_line or (
            "Your targeting suite spins up — the world goes to wireframe and ranging data, and your aim steadies even with your eyes shut." if deploy
            else "Your targeting suite powers down; the firing solutions fade.")
        room_line = None
    self_line = str(self_line).replace("{hand}", hand)
    room_line = str(room_line).replace("{hand}", hand) if room_line else None
    return self_line, room_line


def stow_abilities_at(character, location) -> list[str]:
    """Retract every DEPLOYED ability hosted at ``location`` -- the first
    element of any procedure on that location (#3360, owner ruling
    2026-09-13: the surgeon restores the hardware at the cut to its
    default, undeployed state; hardware elsewhere on the body is left
    alone). Bypasses the busy gate on purpose: it runs as the procedure
    begins. Returns the retract messages, for the patient."""
    if not location:
        return []
    messages = []
    for organ, name, spec in list(iter_abilities(character)):
        if not (getattr(organ, "container", None) == location
                or getattr(organ, "display_location", None) == location):
            continue
        if not _ability_state(organ, name).get("deployed"):
            continue
        # This host only: the other hand's claws are not at the cut.
        messages.append(_dispatch_toggle(character, name, spec, [organ], deploy=False))
    return messages


def list_abilities(character) -> str:
    """The bare-prefix listing: every installed ability + state."""
    by_name = {}
    for organ, name, spec in iter_abilities(character):
        by_name.setdefault(name, []).append(organ)
    lines = []
    for name, hosts in by_name.items():
        states = [bool(_ability_state(h, name).get("deployed")) for h in hosts]
        if len(hosts) == 1 or len(set(states)) == 1:
            tag = "deployed" if states[0] else "retracted"
        else:
            tag = " / ".join(
                f"{_hand_of(h)} {'deployed' if d else 'retracted'}"
                for h, d in zip(hosts, states))
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


def _toggle_integrated_weapon(character, organ, name, spec, state, deploy):
    """One host's integrated weapon in or out of its spec slot. Returns
    ``(ok, failure_line, weapon)``; the dispatcher speaks."""
    from world.identity_utils import msg_room_identity

    slot = spec.get("slot")
    if not slot:
        return False, f"{name} has no slot configured — report this.", None

    if deploy:
        hands = getattr(character, "hands", None) or {}
        if slot not in hands:
            # Slot anatomy gone (severed hand on a surviving arm
            # organ, or species drift) — nothing to transform.
            return False, f"Your {slot.replace('_', ' ')} isn't there to transform.", None

        weapon = _get_or_spawn_weapon(character, state, spec)
        if weapon is None:
            return False, f"{name} grinds and fails — no weapon hardware found.", None

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
        held_map = dict(character.held_items or {})
        stale = [k for k, v in held_map.items() if v == weapon and k != slot]
        if stale:
            for k in stale:
                held_map[k] = None
            character.held_items = held_map

        weapon.location = character
        character.hands = {slot: weapon}
        state["deployed"] = True
        return True, None, weapon

    # ── Retract ───────────────────────────────────────────────────
    weapon = _find_weapon(state)
    if weapon is not None:
        # Clear the slot the weapon is ACTUALLY in — scanned, not
        # assumed — so a gun displaced into the wrong slot by legacy
        # state still retracts cleanly instead of leaving a ghost.
        held_map = dict(character.held_items or {})
        cleared = False
        for k, v in held_map.items():
            if v == weapon:
                held_map[k] = None
                cleared = True
        if cleared:
            character.held_items = held_map
        if weapon.location == character:
            weapon.location = None  # folded back inside the arm
    state["deployed"] = False
    return True, None, weapon


def _toggle_natural_weapon(character, organ, name, spec, state, deploy):
    """One host's natural cyberweapon (#526 M4 — the claws family) in
    or out. Natural weapons never touch the hand slots: the claws ARE the
    hand. Each host's weapon item lives off-grid (``location`` None);
    combat reads the deployed ones via `get_active_natural_weapons`.
    Returns ``(ok, failure_line, weapon)``; the dispatcher speaks."""
    if deploy:
        weapon = _get_or_spawn_weapon(character, state, spec)
        if weapon is None:
            return False, f"{name} grinds and fails — no hardware found.", None
        state["deployed"] = True
        return True, None, weapon
    state["deployed"] = False
    return True, None, _find_weapon(state)


def _toggle_voice_modulator(character, organ, name, spec, state, deploy):
    """One host's voice modulator (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC
    §4.2). The voice-disguise parallel to a worn mask: while engaged,
    ``world.voice.is_voice_modulated`` reads the deployed state off this
    organ and shifts the voice signature to a different UID. Covert by
    design — the dispatcher sends no room line; only the change in voice
    when the wearer next speaks is observable."""
    state["deployed"] = bool(deploy)
    return True, None, None


def _toggle_blindsight(character, organ, name, spec, state, deploy):
    """One host's combat targeting / sonar suite — "blindsight".
    `world.combat.capacity` reads the deployed state off this organ and
    restores combat aim even when the eyes are gone. Combat-only (user
    decided 2026-06-20); covert, no room line."""
    state["deployed"] = bool(deploy)
    return True, None, None


def get_active_natural_weapons(character):
    """Every deployed natural cyberweapon, as ``(host_container, item)``
    in organ order (#526 M4; MULTI_WEAPON_COMBAT_SPEC §3). Consumed by
    combat's weapon resolution, where active natural cyberweapons take
    precedence over held weapons (settled decision 2026-06-12). Only
    items parked in the body (``location`` None) count: an object lying
    on a severed limb is not a weapon anyone fights with. Severed organs
    drop out via :func:`iter_abilities`."""
    out = []
    for organ, name, spec in iter_abilities(character):
        if spec.get("type") != "natural_weapon":
            continue
        store = getattr(organ, "ability_state", None) or {}
        if not (store.get(name) or {}).get("deployed"):
            continue
        weapon = _find_weapon(store.get(name) or {})
        if weapon is not None and weapon.location is None:
            out.append((getattr(organ, "container", None), weapon))
    return out


def has_deployed_ability(character, ability_type) -> bool:
    """Is an ability of this TYPE deployed on a living organ?

    The general form of :func:`get_active_natural_weapons`, and the
    single source of truth for the two abilities whose effect is a
    character-wide state rather than an item: blindsight
    (``world.combat.capacity``) and the voice modulator
    (``world.voice``).

    Both used to record the fact TWICE — once here on the organ, once
    as a flag on the character, because that is where the consumers
    read it. Every teardown path then had to remember to clear the
    second copy, and one of them could not: a forearm module shot to
    0 HP while the arm stays attached calls no teardown hook at all.
    Nothing ran, and :func:`iter_abilities` then skipped the dead organ
    — so the toggle answered "you have no cyberware to command" and the
    flag could never be switched off again. Permanent free accuracy
    with no eyes and no hardware, or a permanent stranger's voice
    (#2484, after #2580 closed the harvest and severance routes).

    Derived, there is no second copy to strand: a dead organ stops
    matching and the effect ends on its own, whichever way it died.
    """
    for organ, name, spec in iter_abilities(character):
        if spec.get("type") != ability_type:
            continue
        store = getattr(organ, "ability_state", None) or {}
        if (store.get(name) or {}).get("deployed"):
            return True
    return False


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
    if held_changed:
        character.held_items = held


def park_all_hardware(character) -> None:
    """Park every deployed weapon on the body (#3486): death runs neither
    retract nor sever, so a character who died with an arm-shotgun out
    left a locked, undroppable gun loose inside the corpse with
    ``deployed`` still True in the death snapshot. Called by the corpse
    factory BEFORE the medical snapshot and the contents sweep, so the
    gun folds back inside the arm (``location=None``, dbref kept on the
    organ) and travels with the chrome from there."""
    state = getattr(character, "medical_state", None)
    organs = getattr(state, "organs", None) if state else None
    for organ in list((organs or {}).values()):
        if getattr(organ, "ability_state", None):
            park_organ_hardware(character, organ)


def carry_snapshot_hardware_to_appendage(appendage) -> None:
    """The corpse-side twin of :func:`carry_hardware_to_appendage`
    (#3487): a limb cut off a CORPSE takes its integrated hardware too.
    Reads the appendage's OWN snapshot (the overlay already copied the
    chain's organs, ``ability_state`` and ``weapon_dbref`` included)
    rather than walking live ``Organ`` objects, moves each weapon onto
    the appendage wherever it sits (parked off-grid, or loose inside a
    pre-#3486 corpse) and records it retracted. Reassigns the snapshot
    so the attribute persists."""
    getter = getattr(appendage, "get_medical_snapshot", None)
    snapshot = getter() if callable(getter) else None
    organs = (snapshot or {}).get("organs") if hasattr(snapshot, "get") else None
    if not organs:
        return
    changed = False
    for entry in organs.values():
        store = entry.get("ability_state") if hasattr(entry, "get") else None
        if not store or not hasattr(store, "items"):
            continue
        for name, ability_state in store.items():
            if not hasattr(ability_state, "get"):
                continue
            weapon = _find_weapon(ability_state)
            if weapon is not None and weapon.location is not appendage:
                weapon.location = appendage
                changed = True
            if ability_state.get("deployed"):
                ability_state["deployed"] = False
                changed = True
    if changed:
        appendage.db.medical_state_at_death = snapshot


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
