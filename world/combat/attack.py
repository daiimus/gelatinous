"""
Attack Processing Module

Standalone functions for processing attacks within the combat handler.
Extracted from CombatHandler to reduce handler.py size and improve
modularity.

All functions take `handler` as their first parameter (the CombatHandler
script instance) instead of operating as methods on the class.
"""

from random import randint

from evennia.comms.models import ChannelDB

from world.combat.messages import get_combat_message
from world.medical.utils import select_hit_location, select_target_organ

from .constants import (
    SPLATTERCAST_CHANNEL,
    DB_CHAR, DB_IS_YIELDING,
    NDB_CHARGE_BONUS,
    NDB_PROXIMITY,
    WEAPON_TYPE_UNARMED,
    STAGGER_DELAY_INTERVAL, MAX_STAGGER_DELAY,
)
from .utils import (
    get_numeric_stat, get_display_name_safe,
    get_wielded_weapon, is_wielding_ranged_weapon,
    get_weapon_damage, get_combatant_grappling_target,
    get_character_dbref,
)


def calculate_attack_delay(handler, attacker, initiative_order):
    """
    Calculate attack delay to stagger combat messages within a round.

    Args:
        handler: The CombatHandler script instance.
        attacker: The attacking character.
        initiative_order: List of combatant entries in initiative order.

    Returns:
        float: Delay in seconds for this attacker's attack.
    """
    # Find attacker's position in initiative order
    attacker_position = 0
    for i, entry in enumerate(initiative_order):
        if entry.get(DB_CHAR) == attacker:
            attacker_position = i
            break

    # Stagger attacks using configurable interval
    # First attacker goes immediately, subsequent attackers are delayed
    base_delay = attacker_position * STAGGER_DELAY_INTERVAL

    # Cap at max delay to ensure all attacks complete before next round
    return min(base_delay, MAX_STAGGER_DELAY)


def process_delayed_attack(handler, attacker, target, attacker_entry, combatants_list):
    """
    Process a delayed attack — wrapper for process_attack with validation.

    Called via ``delay()`` from the combat handler's ``at_repeat`` loop so
    that attack messages are staggered within a round.

    Args:
        handler: The CombatHandler script instance.
        attacker: The attacking character.
        target: The target character.
        attacker_entry: The attacker's combat entry dict (snapshot at
            scheduling time).
        combatants_list: List of all combat entry dicts (snapshot at
            scheduling time).
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    # Validate that combat is still active
    if not handler.db.combat_is_running:
        splattercast.msg(
            f"DELAYED_ATTACK: Combat ended before {attacker.key}'s attack "
            f"on {target.key} could execute."
        )
        return

    # Validate that both characters are still in combat
    current_combatants = handler.db.combatants or []
    attacker_still_in_combat = any(
        e.get(DB_CHAR) == attacker for e in current_combatants
    )
    target_still_in_combat = any(
        e.get(DB_CHAR) == target for e in current_combatants
    )

    if not attacker_still_in_combat:
        splattercast.msg(
            f"DELAYED_ATTACK: {attacker.key} no longer in combat, "
            f"attack cancelled."
        )
        return

    if not target_still_in_combat:
        splattercast.msg(
            f"DELAYED_ATTACK: {target.key} no longer in combat, "
            f"{attacker.key}'s attack cancelled."
        )
        return

    # Check if attacker is dead — dead characters can't attack
    if attacker.is_dead():
        splattercast.msg(
            f"DELAYED_ATTACK: {attacker.key} has died, attack cancelled."
        )
        return

    # Check if target is dead — no point attacking the dead
    if target.is_dead():
        splattercast.msg(
            f"DELAYED_ATTACK: {target.key} has died, "
            f"{attacker.key}'s attack cancelled."
        )
        return

    # Get fresh combat entries
    fresh_attacker_entry = next(
        (e for e in current_combatants if e.get(DB_CHAR) == attacker), None
    )
    if not fresh_attacker_entry:
        splattercast.msg(
            f"DELAYED_ATTACK: Could not find fresh entry for "
            f"{attacker.key}, attack cancelled."
        )
        return

    splattercast.msg(
        f"DELAYED_ATTACK: Executing {attacker.key} -> {target.key}"
    )

    try:
        process_attack(handler, attacker, target,
                       fresh_attacker_entry, current_combatants)
        splattercast.msg(
            f"DELAYED_ATTACK: _process_attack completed for "
            f"{attacker.key} -> {target.key}"
        )
    except Exception as e:
        splattercast.msg(
            f"DELAYED_ATTACK: ERROR in _process_attack for "
            f"{attacker.key} -> {target.key}: {e}"
        )
        import traceback
        splattercast.msg(
            f"DELAYED_ATTACK: Traceback: {traceback.format_exc()}"
        )


def determine_injury_type(weapon):
    """
    Determine the injury type based on weapon's damage_type attribute.

    Args:
        weapon: The weapon object being used (or ``None`` for unarmed).

    Returns:
        str: Valid injury type for the medical system.
    """
    if not weapon:
        return "blunt"  # Unarmed attacks are blunt trauma

    # Get damage_type from weapon, default to "blunt" if not specified
    damage_type = (
        weapon.db.damage_type
        if weapon.db.damage_type is not None
        else "blunt"
    )
    return damage_type


def calculate_shield_chance(
    handler, grappler, victim, is_ranged_attack, combatants_list
):
    """
    Calculate the chance that a grappled victim acts as a human shield.

    Args:
        handler: The CombatHandler script instance.
        grappler: The character doing the grappling.
        victim: The character being grappled (potential shield).
        is_ranged_attack: Whether this is a ranged attack.
        combatants_list: List of all combat entry dicts.

    Returns:
        int: Shield chance percentage (0–100).
    """
    # Base shield chance
    base_chance = 40

    # Grappler Motorics modifier: +5% per point above 1
    grappler_motorics = get_numeric_stat(grappler, "motorics", 1)
    motorics_bonus = (grappler_motorics - 1) * 5

    # Victim resistance modifier based on yielding state
    victim_entry = None
    for entry in combatants_list:
        if entry.get(DB_CHAR) == victim:
            victim_entry = entry
            break

    resistance_modifier = 0
    if victim_entry:
        is_yielding = victim_entry.get(DB_IS_YIELDING, False)
        if is_yielding:
            resistance_modifier = 10  # Easier to position yielding victim
        else:
            resistance_modifier = -10  # Struggling against positioning

    # Ranged attack modifier
    ranged_modifier = -20 if is_ranged_attack else 0

    # Calculate final chance
    final_chance = (
        base_chance + motorics_bonus + resistance_modifier + ranged_modifier
    )

    # Clamp to 0–100 range
    return max(0, min(100, final_chance))


def send_shield_messages(handler, attacker, grappler, victim):
    """
    Send human shield interception messages to all parties.

    Args:
        handler: The CombatHandler script instance.
        attacker: The character making the attack.
        grappler: The character using victim as shield.
        victim: The character being used as shield.
    """
    attacker_msg = (
        f"|rYour attack is intercepted by "
        f"{get_display_name_safe(victim)} as "
        f"{get_display_name_safe(grappler)} uses them as a shield!|n"
    )
    grappler_msg = (
        f"|yYou position {get_display_name_safe(victim)} to absorb "
        f"{get_display_name_safe(attacker)}'s attack!|n"
    )
    victim_msg = (
        f"|RYou are forced into the path of "
        f"{get_display_name_safe(attacker)}'s attack by "
        f"{get_display_name_safe(grappler)}!|n"
    )
    observer_msg = (
        f"|y{get_display_name_safe(grappler)} uses "
        f"{get_display_name_safe(victim)} as a human shield against "
        f"{get_display_name_safe(attacker)}'s attack!|n"
    )

    # Send messages
    attacker.msg(attacker_msg)
    grappler.msg(grappler_msg)
    victim.msg(victim_msg)

    # Send to observers (exclude the three participants)
    attacker.location.msg_contents(
        observer_msg, exclude=[attacker, grappler, victim]
    )


def process_attack(handler, attacker, target, attacker_entry, combatants_list):
    """
    Process an attack between two characters.

    This is the core attack resolution function handling melee/ranged
    validation, human-shield interception, hit/miss rolls, damage
    application, injury selection, and kill processing.

    Args:
        handler: The CombatHandler script instance.
        attacker: The attacking character.
        target: The target character.
        attacker_entry: The attacker's combat entry dict.
        combatants_list: List of all combat entry dicts.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    # Check if target is already dead or unconscious
    if target.is_dead():
        splattercast.msg(
            f"ATTACK_CANCELLED: {target.key} is already dead, "
            f"cancelling {attacker.key}'s attack."
        )
        return
    elif hasattr(target, "is_unconscious") and target.is_unconscious():
        splattercast.msg(
            f"ATTACK_CANCELLED: {target.key} is unconscious, "
            f"cancelling {attacker.key}'s attack."
        )
        return

    # Check if attacker is wielding a ranged weapon
    is_ranged_attack = is_wielding_ranged_weapon(attacker)

    # For melee attacks, check same-room and proximity requirements
    if not is_ranged_attack:
        # Check if attacker can reach target (same room for melee)
        if attacker.location != target.location:
            attacker.msg(f"You can't reach {get_display_name_safe(target, attacker)} from here.")
            splattercast.msg(
                f"ATTACK_FAIL (REACH): {attacker.key} cannot reach "
                f"{target.key}."
            )
            return

        # Check proximity for melee attacks
        if not hasattr(attacker.ndb, NDB_PROXIMITY):
            setattr(attacker.ndb, NDB_PROXIMITY, set())

        # Get proximity set — use proper attribute name
        proximity_set = getattr(attacker.ndb, NDB_PROXIMITY, set())
        if not proximity_set:  # Handle None/empty
            setattr(attacker.ndb, NDB_PROXIMITY, set())
            proximity_set = set()

        if target not in proximity_set:
            attacker.msg(
                f"You need to be in melee proximity with {get_display_name_safe(target, attacker)} "
                f"to attack them. Try advancing or charging."
            )
            splattercast.msg(
                f"ATTACK_FAIL (PROXIMITY): {attacker.key} not in "
                f"proximity with {target.key}."
            )
            return
    else:
        # For ranged attacks, just log that we're allowing cross-room attack
        splattercast.msg(
            f"ATTACK_RANGED: {attacker.key} making ranged attack on "
            f"{target.key} from {attacker.location.key} to "
            f"{target.location.key}."
        )

    # ── Human Shield System Check ──────────────────────────────────────
    # Check if target is grappling someone who could act as a human shield
    target_entry = None
    for entry in combatants_list:
        if entry.get(DB_CHAR) == target:
            target_entry = entry
            break

    original_target = target
    if target_entry:
        grappling_victim = get_combatant_grappling_target(
            target_entry, handler
        )
        if grappling_victim:
            # Target is grappling someone — check for shield interception
            shield_chance = calculate_shield_chance(
                handler, target, grappling_victim,
                is_ranged_attack, combatants_list,
            )
            shield_roll = randint(1, 100)

            splattercast.msg(
                f"HUMAN_SHIELD: {attacker.key} attacking {target.key} "
                f"who is grappling {grappling_victim.key}. "
                f"Shield chance: {shield_chance}%, roll: {shield_roll}"
            )

            if shield_roll <= shield_chance:
                # Shield successful — redirect attack to victim
                send_shield_messages(
                    handler, attacker, target, grappling_victim
                )
                target = grappling_victim  # Redirect the attack
                splattercast.msg(
                    f"HUMAN_SHIELD_SUCCESS: Attack redirected from "
                    f"{original_target.key} to {target.key}"
                )
            else:
                splattercast.msg(
                    f"HUMAN_SHIELD_FAIL: Attack proceeds normally "
                    f"against {target.key}"
                )

    # ── Get weapon and stats ───────────────────────────────────────────
    weapon = get_wielded_weapon(attacker)
    weapon_name = weapon.key if weapon else "unarmed"

    attacker_skill = get_numeric_stat(attacker, "motorics", 1)
    target_skill = get_numeric_stat(target, "motorics", 1)

    # Roll for attack
    attacker_roll = randint(1, 20) + attacker_skill
    target_roll = randint(1, 20) + target_skill

    # Check for charge bonus
    has_attr = hasattr(attacker.ndb, NDB_CHARGE_BONUS)
    attr_value = getattr(
        attacker.ndb, NDB_CHARGE_BONUS, "MISSING"
    )
    splattercast.msg(
        f"ATTACK_BONUS_DEBUG_DETAILED: {attacker.key} "
        f"hasattr={has_attr}, value={attr_value}"
    )

    if has_attr and getattr(
        attacker.ndb, NDB_CHARGE_BONUS, False
    ):
        attacker_roll += 2
        splattercast.msg(
            f"ATTACK_BONUS: {attacker.key} gets +2 charge attack bonus."
        )
        splattercast.msg(
            f"ATTACK_BONUS_DEBUG: {attacker.key} had "
            f"charge_attack_bonus_active set — this should only happen "
            f"after using the 'charge' command."
        )
        # Ensure complete attribute removal
        try:
            delattr(attacker.ndb, NDB_CHARGE_BONUS)
        except AttributeError:
            pass
        # Double-check removal worked
        if hasattr(attacker.ndb, NDB_CHARGE_BONUS):
            setattr(attacker.ndb, NDB_CHARGE_BONUS, None)
            delattr(attacker.ndb, NDB_CHARGE_BONUS)
    else:
        splattercast.msg(
            f"ATTACK_BONUS_DEBUG: {attacker.key} does not have "
            f"charge_attack_bonus_active — no bonus applied."
        )

    splattercast.msg(
        f"ATTACK: {attacker.key} (roll {attacker_roll}) vs "
        f"{target.key} (roll {target_roll}) with {weapon_name}"
    )

    if attacker_roll > target_roll:
        # Hit — calculate damage
        # NOTE: Strict > means ties favor the defender. This is intentional.
        damage = randint(1, 6)  # Base damage
        if weapon:
            weapon_damage = get_weapon_damage(weapon, 0)
            damage += weapon_damage

        # Determine injury type based on weapon
        injury_type = determine_injury_type(weapon)

        # Calculate success margin for precision targeting
        success_margin = attacker_roll - target_roll

        # Select hit location — Intellect characters target less armored areas
        hit_location = select_hit_location(target, success_margin, attacker)

        # Make precision roll for organ targeting within the location
        precision_roll = randint(1, 20)
        # Mix motorics (70%) and intellect (30%) for precision skill
        attacker_motorics = get_numeric_stat(attacker, "motorics", 1)
        attacker_intellect = get_numeric_stat(attacker, "intellect", 1)
        precision_skill = int(
            (attacker_motorics * 0.7) + (attacker_intellect * 0.3)
        )

        # Select specific target organ within the hit location
        target_organ = select_target_organ(
            hit_location, precision_roll, precision_skill
        )

        # Debug output for precision targeting
        splattercast.msg(
            f"PRECISION_TARGET: {attacker.key} margin={success_margin}, "
            f"precision={precision_roll + precision_skill}, "
            f"hit {hit_location}:{target_organ}"
        )

        # Determine weapon type for messages
        weapon_type = WEAPON_TYPE_UNARMED
        if weapon and hasattr(weapon, "db") and weapon.db.weapon_type:
            weapon_type = weapon.db.weapon_type

        # Apply damage first to determine if this is a killing blow
        # take_damage now returns (died, actual_damage_applied)
        target_died, actual_damage = target.take_damage(
            damage,
            location=hit_location,
            injury_type=injury_type,
            target_organ=target_organ,
        )

        if target_died:
            _handle_kill(
                handler, attacker, target, weapon, weapon_type,
                actual_damage, hit_location, combatants_list,
            )
        else:
            # Regular hit — send attack messages
            hit_messages = get_combat_message(
                weapon_type, "hit",
                attacker=attacker, target=target,
                item=weapon, damage=actual_damage,
                hit_location=hit_location,
            )

            attacker.msg(hit_messages["attacker_msg"])
            target.msg(hit_messages["victim_msg"])
            attacker.location.msg_contents(
                hit_messages["observer_msg"],
                exclude=[attacker, target],
            )

            splattercast.msg(
                f"ATTACK_HIT: {attacker.key} hit {target.key} for "
                f"{actual_damage} damage."
            )
    else:
        # Miss — get miss messages from the message system
        weapon_type = WEAPON_TYPE_UNARMED
        if weapon and hasattr(weapon, "db") and weapon.db.weapon_type:
            weapon_type = weapon.db.weapon_type

        miss_messages = get_combat_message(
            weapon_type, "miss",
            attacker=attacker, target=target, item=weapon,
        )

        attacker.msg(miss_messages["attacker_msg"])
        target.msg(miss_messages["victim_msg"])
        attacker.location.msg_contents(
            miss_messages["observer_msg"],
            exclude=[attacker, target],
        )

        splattercast.msg(
            f"ATTACK_MISS: {attacker.key} missed {target.key}."
        )


# ── Internal helpers ───────────────────────────────────────────────────


def _handle_kill(
    handler, attacker, target, weapon, weapon_type,
    actual_damage, hit_location, combatants_list,
):
    """
    Handle a killing blow — send kill messages, process death, and
    remove the target from combat.

    Args:
        handler: The CombatHandler script instance.
        attacker: The character who dealt the killing blow.
        target: The character who died.
        weapon: The weapon used (or ``None``).
        weapon_type: String weapon type for message lookup.
        actual_damage: The damage that was applied.
        hit_location: The body location that was hit.
        combatants_list: List of all combat entry dicts.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    kill_messages = get_combat_message(
        weapon_type, "kill",
        attacker=attacker, target=target,
        item=weapon, damage=actual_damage,
        hit_location=hit_location,
    )

    # Send kill messages to establish lethal narrative before death curtain
    if "attacker_msg" in kill_messages:
        attacker.msg(kill_messages["attacker_msg"])
    if "victim_msg" in kill_messages:
        target.msg(kill_messages["victim_msg"])
    if "observer_msg" in kill_messages:
        # Send to attacker's room
        if attacker.location:
            attacker.location.msg_contents(
                kill_messages["observer_msg"],
                exclude=[attacker, target],
            )
        # Also send to target's room if it differs (cross-room combat)
        if (
            target.location
            and target.location != attacker.location
        ):
            target.location.msg_contents(
                kill_messages["observer_msg"],
                exclude=[attacker, target],
            )

    splattercast.msg(
        f"KILLING_BLOW: {attacker.key} delivered killing blow to "
        f"{target.key} for {actual_damage} damage."
    )

    # Check if death has already been processed to prevent double death
    # curtains
    if (
        hasattr(target, "ndb")
        and getattr(target.ndb, "death_processed", False)
    ):
        splattercast.msg(
            f"COMBAT_DEATH_SKIP: {target.key} death already processed"
        )

        # Check if death curtain was deferred and trigger it now
        if (
            hasattr(target.ndb, "death_curtain_pending")
            and target.ndb.death_curtain_pending
        ):
            from typeclasses.curtain_of_death import show_death_curtain

            splattercast.msg(
                f"COMBAT_DEATH_CURTAIN: {target.key} triggering "
                f"deferred death curtain after kill message"
            )
            show_death_curtain(target)
            target.ndb.death_curtain_pending = False
    else:
        # Trigger death processing — at_death() will handle death analysis
        # and potentially defer curtain
        target.at_death()

        # If death curtain was deferred, trigger it now after kill message
        if (
            hasattr(target.ndb, "death_curtain_pending")
            and target.ndb.death_curtain_pending
        ):
            from typeclasses.curtain_of_death import show_death_curtain

            splattercast.msg(
                f"COMBAT_DEATH_CURTAIN: {target.key} triggering "
                f"deferred death curtain after kill message"
            )
            show_death_curtain(target)
            target.ndb.death_curtain_pending = False

    # Remove from combat
    handler.remove_combatant(target)
