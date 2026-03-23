"""
Combat Actions Module

Standalone functions for resolving special combat actions (disarm,
dict-based grapple attempts, manual escape grapple) within the combat
handler.

Extracted from CombatHandler to reduce handler.py size and improve
modularity.

All functions take ``handler`` as their first parameter (the CombatHandler
script instance) instead of operating as methods on the class.
"""

from random import randint

from evennia.comms.models import ChannelDB

from world.combat.messages import get_combat_message
from world.grammar import capitalize_first
from world.identity_utils import msg_room_identity

from .constants import (
    SPLATTERCAST_CHANNEL,
    DEBUG_PREFIX_HANDLER,
    DB_CHAR, DB_COMBAT_ACTION, DB_COMBAT_ACTION_TARGET,
    DB_IS_YIELDING,
    DB_GRAPPLING_DBREF, DB_GRAPPLED_BY_DBREF,
    NDB_PROXIMITY,
    COMBAT_ACTION_ESCAPE_GRAPPLE,
    MSG_DISARM_FAILED, MSG_DISARM_RESISTED,
    MSG_DISARM_TARGET_EMPTY_HANDS, MSG_DISARM_NOTHING_TO_DISARM,
    MSG_DISARM_SUCCESS_ATTACKER, MSG_DISARM_SUCCESS_VICTIM,
    MSG_DISARM_SUCCESS_OBSERVER,
)
from .debug import log_combat_action
from .dice import roll_stat
from .utils import (
    get_numeric_stat, initialize_proximity_ndb,
    get_character_dbref, get_display_name_safe,
)
from .proximity import is_in_proximity


def resolve_disarm(handler, char, entry):
    """
    Resolve a disarm action for a character in combat.

    The attacker makes a grit vs grit opposed roll. On success the
    target's held weapon (or other item) is dropped to the room.

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to disarm.
        entry: The character's combat entry dict.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    target = entry.get(DB_COMBAT_ACTION_TARGET)

    if not target:
        char.msg("|rNo target specified for disarm action.|n")
        return

    target_name = get_display_name_safe(target, char)

    # Validate target is still in combat and same room
    if target.location != char.location:
        char.msg(f"|r{target_name} is no longer in the same room.|n")
        return

    combatants_list = handler.db.combatants or []
    if not any(e[DB_CHAR] == target for e in combatants_list):
        char.msg(f"|r{target_name} is no longer in combat.|n")
        return

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_DISARM: {char.key} executing disarm "
        f"action on {target.key}."
    )

    # Check proximity
    initialize_proximity_ndb(char)
    if not is_in_proximity(char, target):
        char.msg(
            f"|rYou must be in melee proximity with {target_name} to "
            f"disarm them.|n"
        )
        return

    # Check target's hands (hands is an AttributeProperty on Character)
    hands = target.hands if target.hands is not None else {}
    if not hands:
        char.msg(
            MSG_DISARM_TARGET_EMPTY_HANDS.format(target=target_name)
        )
        log_combat_action(
            char, "disarm_fail", target,
            details="target has nothing in their hands",
        )
        return

    # Find weapon to disarm (prioritize weapons, then any held item)
    weapon_hand = None
    for hand, item in hands.items():
        if item and item.db.weapon_type:
            weapon_hand = hand
            break

    if not weapon_hand:
        for hand, item in hands.items():
            if item:
                weapon_hand = hand
                break

    if not weapon_hand:
        char.msg(
            MSG_DISARM_NOTHING_TO_DISARM.format(target=target_name)
        )
        log_combat_action(
            char, "disarm_fail", target,
            details="nothing found to disarm",
        )
        return

    # Grit vs Grit opposed roll
    disarm_roll = roll_stat(char, "grit")
    resist_roll = roll_stat(target, "grit")

    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_DISARM: {char.key} "
        f"(grit roll:{disarm_roll}) vs {target.key} "
        f"(grit roll:{resist_roll})"
    )
    log_combat_action(
        char, "disarm_attempt", target,
        details=f"rolls {disarm_roll} (grit) vs {resist_roll} (grit)",
    )

    if disarm_roll <= resist_roll:
        char.msg(MSG_DISARM_FAILED.format(target=target_name))
        target.msg(MSG_DISARM_RESISTED.format(
            attacker=capitalize_first(
                get_display_name_safe(char, target)
            ),
        ))
        log_combat_action(
            char, "disarm_fail", target, success=False,
        )
        splattercast.msg(
            f"{DEBUG_PREFIX_HANDLER}_DISARM: {char.key} failed to disarm "
            f"{target.key}."
        )
        return

    # Success — disarm the item
    item = hands[weapon_hand]
    hands[weapon_hand] = None
    item.move_to(target.location, quiet=True)

    char.msg(
        MSG_DISARM_SUCCESS_ATTACKER.format(
            target=target_name, item=item.key,
        )
    )
    target.msg(
        MSG_DISARM_SUCCESS_VICTIM.format(
            attacker=capitalize_first(
                get_display_name_safe(char, target)
            ),
            item=item.key,
        )
    )
    msg_room_identity(
        location=target.location,
        template=MSG_DISARM_SUCCESS_OBSERVER.format(
            attacker="{actor}", target="{target_char}",
            item=item.key,
        ),
        char_refs={"actor": char, "target_char": target},
        exclude=[char, target],
    )
    log_combat_action(
        char, "disarm_success", target,
        details=f"disarmed {item.key}",
    )
    splattercast.msg(
        f"{DEBUG_PREFIX_HANDLER}_DISARM: {char.key} successfully disarmed "
        f"{item.key} from {target.key}."
    )


def resolve_grapple_attempt(handler, char, entry, combatants_list):
    """
    Resolve a dict-based grapple attempt (``combat_action`` is a dict
    with ``type == "grapple"``).

    This handles the inline grapple attempt logic that was previously
    embedded in ``at_repeat()``.

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting the grapple.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)
    combat_action = entry.get(DB_COMBAT_ACTION)

    action_target_char = combat_action.get("target")

    # Validate target
    is_action_target_valid = False
    if action_target_char and any(
        e.get(DB_CHAR) == action_target_char for e in combatants_list
    ):
        managed_rooms = handler.db.managed_rooms or []
        if (
            action_target_char.location
            and action_target_char.location in managed_rooms
        ):
            is_action_target_valid = True

    if not is_action_target_valid and action_target_char:
        char.msg(
            f"The target of your planned action "
            f"({get_display_name_safe(action_target_char, char)}) "
            f"is no longer valid."
        )
        splattercast.msg(
            f"{char.key}'s action_intent target "
            f"{action_target_char.key} is invalid. Intent cleared, "
            f"falling through."
        )
        entry[DB_COMBAT_ACTION] = None
        return False  # Signal that action was not consumed

    if not is_action_target_valid:
        entry[DB_COMBAT_ACTION] = None
        return False

    can_grapple_target = (
        char.location == action_target_char.location
    )

    if can_grapple_target:
        # Proximity Check for Grapple
        if not hasattr(char.ndb, NDB_PROXIMITY):
            setattr(char.ndb, NDB_PROXIMITY, set())

        proximity_set = getattr(char.ndb, NDB_PROXIMITY, set())
        if not proximity_set:
            setattr(char.ndb, NDB_PROXIMITY, set())
            proximity_set = set()

        # RELOAD RECOVERY: If characters are in mutual combat, restore
        # proximity
        if (
            action_target_char not in proximity_set
            and handler._are_characters_in_mutual_combat(
                char, action_target_char
            )
        ):
            proximity_set.add(action_target_char)
            setattr(char.ndb, NDB_PROXIMITY, proximity_set)
            splattercast.msg(
                f"GRAPPLE_PROXIMITY_RESTORE: {char.key} and "
                f"{action_target_char.key} proximity restored."
            )

        if action_target_char not in proximity_set:
            char.msg(
                f"You need to be in melee proximity with "
                f"{get_display_name_safe(action_target_char, char)} "
                f"to grapple them. Try advancing or charging."
            )
            splattercast.msg(
                f"GRAPPLE FAIL (PROXIMITY): {char.key} not in "
                f"proximity with {action_target_char.key}."
            )
            entry[DB_COMBAT_ACTION] = None
            return True  # Turn consumed

        attacker_roll = randint(
            1, max(1, get_numeric_stat(char, "motorics", 1))
        )
        defender_roll = randint(
            1, max(1, get_numeric_stat(action_target_char, "motorics", 1))
        )
        splattercast.msg(
            f"GRAPPLE ATTEMPT: {char.key} (roll {attacker_roll}) vs "
            f"{action_target_char.key} (roll {defender_roll})."
        )

        if attacker_roll > defender_roll:
            # NOTE: Strict > means ties favor the defender. This is
            # intentional.
            entry[DB_GRAPPLING_DBREF] = get_character_dbref(
                action_target_char
            )
            target_entry = next(
                (
                    e for e in combatants_list
                    if e.get(DB_CHAR) == action_target_char
                ),
                None,
            )
            if target_entry:
                target_entry[DB_GRAPPLED_BY_DBREF] = (
                    get_character_dbref(char)
                )

            # Auto-yield only the grappler (restraint intent)
            # Victim stays non-yielding so they auto-resist each turn
            entry[DB_IS_YIELDING] = True

            grapple_messages = get_combat_message(
                "grapple", "hit",
                attacker=char, target=action_target_char,
            )
            char.msg(grapple_messages.get("attacker_msg"))
            action_target_char.msg(grapple_messages.get("victim_msg"))
            if char.location:
                msg_room_identity(
                    location=char.location,
                    template=grapple_messages.get(
                        "observer_template",
                        grapple_messages.get("observer_msg", ""),
                    ),
                    char_refs=grapple_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": action_target_char},
                    ),
                    exclude=[char, action_target_char],
                )
            splattercast.msg(
                f"GRAPPLE_SUCCESS: {char.key} grappled "
                f"{action_target_char.key}."
            )
        else:
            # Grapple failed
            grapple_messages = get_combat_message(
                "grapple", "miss",
                attacker=char, target=action_target_char,
            )
            char.msg(grapple_messages.get("attacker_msg"))
            action_target_char.msg(grapple_messages.get("victim_msg"))
            if char.location:
                msg_room_identity(
                    location=char.location,
                    template=grapple_messages.get(
                        "observer_template",
                        grapple_messages.get("observer_msg", ""),
                    ),
                    char_refs=grapple_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": action_target_char},
                    ),
                    exclude=[char, action_target_char],
                )
            splattercast.msg(
                f"GRAPPLE_FAIL: {char.key} failed to grapple "
                f"{action_target_char.key}."
            )
    else:
        char.msg(
            f"You can't reach "
            f"{get_display_name_safe(action_target_char, char)} to "
            f"grapple them from here."
        )
        splattercast.msg(
            f"GRAPPLE FAIL (REACH): {char.key} cannot reach "
            f"{action_target_char.key}."
        )

    entry[DB_COMBAT_ACTION] = None
    entry[DB_COMBAT_ACTION_TARGET] = None
    return True  # Turn consumed


def resolve_escape_grapple(handler, char, entry, combatants_list):
    """
    Resolve a dict-based escape grapple attempt (``combat_action`` is a
    dict with ``type == "escape_grapple"``).

    This handles the inline escape logic that was previously embedded in
    ``at_repeat()``.

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to escape.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.

    Returns:
        bool: ``True`` if the action consumed the turn.
    """
    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    grappler = handler.get_grappled_by_obj(entry)
    if grappler and any(
        e.get(DB_CHAR) == grappler for e in combatants_list
    ):
        escaper_roll = randint(
            1, max(1, get_numeric_stat(char, "motorics", 1))
        )
        grappler_roll = randint(
            1, max(1, get_numeric_stat(grappler, "motorics", 1))
        )
        splattercast.msg(
            f"ESCAPE ATTEMPT: {char.key} (roll {escaper_roll}) vs "
            f"{grappler.key} (roll {grappler_roll})."
        )

        if escaper_roll > grappler_roll:
            # NOTE: Strict > means ties favor the grappler (defender).
            # This is intentional.
            entry[DB_GRAPPLED_BY_DBREF] = None
            grappler_entry = next(
                (
                    e for e in combatants_list
                    if e.get(DB_CHAR) == grappler
                ),
                None,
            )
            if grappler_entry:
                grappler_entry[DB_GRAPPLING_DBREF] = None
            escape_messages = get_combat_message(
                "grapple", "escape_hit",
                attacker=char, target=grappler,
            )
            char.msg(escape_messages.get("attacker_msg"))
            grappler.msg(escape_messages.get("victim_msg"))
            if char.location:
                msg_room_identity(
                    location=char.location,
                    template=escape_messages.get(
                        "observer_template",
                        escape_messages.get("observer_msg", ""),
                    ),
                    char_refs=escape_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": grappler},
                    ),
                    exclude=[char, grappler],
                )
            splattercast.msg(
                f"ESCAPE SUCCESS: {char.key} escaped from "
                f"{grappler.key}."
            )
        else:
            escape_messages = get_combat_message(
                "grapple", "escape_miss",
                attacker=char, target=grappler,
            )
            char.msg(escape_messages.get("attacker_msg"))
            grappler.msg(escape_messages.get("victim_msg"))
            if char.location:
                msg_room_identity(
                    location=char.location,
                    template=escape_messages.get(
                        "observer_template",
                        escape_messages.get("observer_msg", ""),
                    ),
                    char_refs=escape_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": grappler},
                    ),
                    exclude=[char, grappler],
                )
            splattercast.msg(
                f"ESCAPE FAIL: {char.key} failed to escape "
                f"{grappler.key}."
            )

    entry[DB_COMBAT_ACTION] = None
    entry[DB_COMBAT_ACTION_TARGET] = None
    return True  # Turn consumed


def resolve_auto_escape(handler, char, entry, combatants_list):
    """
    Resolve an automatic escape attempt for a grappled, non-yielding
    character.

    This handles the auto-escape logic that fires every round for
    non-yielding grapple victims. On success the victim switches to
    violent mode and targets the grappler.

    Args:
        handler: The CombatHandler script instance.
        char: The character attempting to auto-escape.
        entry: The character's combat entry dict.
        combatants_list: List of all combat entry dicts.

    Returns:
        bool: ``True`` if an escape attempt was made (turn consumed).
    """
    from .constants import (
        DB_TARGET_DBREF,
        MSG_GRAPPLE_AUTO_ESCAPE_VIOLENT,
    )

    splattercast = ChannelDB.objects.get_channel(SPLATTERCAST_CHANNEL)

    grappler = handler.get_grappled_by_obj(entry)
    if not grappler:
        return False

    # Safety check: prevent self-grappling and invalid grappler
    if grappler == char:
        splattercast.msg(
            f"GRAPPLE_ERROR: {char.key} is grappled by themselves! "
            f"Clearing invalid state."
        )
        entry[DB_GRAPPLED_BY_DBREF] = None
        return False
    elif not any(
        e.get(DB_CHAR) == grappler for e in combatants_list
    ):
        splattercast.msg(
            f"GRAPPLE_ERROR: {char.key} is grappled by {grappler.key} "
            f"who is not in combat! Clearing invalid state."
        )
        entry[DB_GRAPPLED_BY_DBREF] = None
        return False

    # Check if the victim is yielding (restraint mode acceptance)
    if entry.get(DB_IS_YIELDING, False):
        # Victim is yielding/accepting restraint — no automatic escape
        grappler_name = get_display_name_safe(grappler, char)
        splattercast.msg(
            f"{char.key} is being grappled by {grappler.key} but is "
            f"yielding (accepting restraint)."
        )
        char.msg(
            f"|gYou remain still in {grappler_name}'s hold, not "
            f"resisting.|n"
        )
        msg_room_identity(
            location=char.location,
            template="|g{actor} does not resist {target_char}'s hold.|n",
            char_refs={"actor": char, "target_char": grappler},
            exclude=[char],
        )
        return True  # Turn consumed (passive)

    # Victim is not yielding — automatically attempt to escape
    splattercast.msg(
        f"{char.key} is being grappled by {grappler.key} and "
        f"automatically attempts to escape."
    )
    char.msg(
        f"|yYou struggle against "
        f"{get_display_name_safe(grappler, char)}'s grip!|n"
    )

    # Setup an escape attempt
    escaper_roll = randint(
        1, max(1, get_numeric_stat(char, "motorics", 1))
    )
    grappler_roll = randint(
        1, max(1, get_numeric_stat(grappler, "motorics", 1))
    )
    splattercast.msg(
        f"AUTO_ESCAPE_ATTEMPT: {char.key} (roll {escaper_roll}) vs "
        f"{grappler.key} (roll {grappler_roll})."
    )

    if escaper_roll > grappler_roll:
        # Success — clear grapple
        # NOTE: Strict > means ties favor the grappler (defender).
        # This is intentional.
        entry[DB_GRAPPLED_BY_DBREF] = None
        grappler_entry = next(
            (
                e for e in combatants_list
                if e.get(DB_CHAR) == grappler
            ),
            None,
        )
        if grappler_entry:
            grappler_entry[DB_GRAPPLING_DBREF] = None

        # Successful auto-escape switches victim to violent mode
        was_yielding = entry.get(DB_IS_YIELDING, False)
        entry[DB_IS_YIELDING] = False

        # Ensure the victim has the grappler as their target for
        # retaliation
        if not entry.get(DB_TARGET_DBREF):
            entry[DB_TARGET_DBREF] = get_character_dbref(grappler)
            splattercast.msg(
                f"AUTO_ESCAPE_TARGET: {char.key} targets {grappler.key} "
                f"after escaping."
            )

        escape_messages = get_combat_message(
            "grapple", "escape_hit",
            attacker=char, target=grappler,
        )
        grappler_name_for_char = get_display_name_safe(grappler, char)
        char_name_for_grappler = capitalize_first(
            get_display_name_safe(char, grappler)
        )
        char.msg(
            escape_messages.get(
                "attacker_msg",
                f"You break free from {grappler_name_for_char}'s grasp!",
            )
        )
        grappler.msg(
            escape_messages.get(
                "victim_msg",
                f"{char_name_for_grappler} breaks free from your grasp!",
            )
        )
        if char.location:
            obs_template = escape_messages.get("observer_template")
            if obs_template:
                msg_room_identity(
                    location=char.location,
                    template=obs_template,
                    char_refs=escape_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": grappler},
                    ),
                    exclude=[char, grappler],
                )
            else:
                msg_room_identity(
                    location=char.location,
                    template=(
                        "{actor} breaks free from "
                        "{target_char}'s grasp!"
                    ),
                    char_refs={"actor": char, "target_char": grappler},
                    exclude=[char, grappler],
                )

        # Additional message if they switched from yielding to violent
        if was_yielding:
            char.msg(MSG_GRAPPLE_AUTO_ESCAPE_VIOLENT)

        splattercast.msg(
            f"AUTO_ESCAPE_SUCCESS: {char.key} escaped from "
            f"{grappler.key}."
        )
    else:
        # Failure
        escape_messages = get_combat_message(
            "grapple", "escape_miss",
            attacker=char, target=grappler,
        )
        grappler_name_for_char = get_display_name_safe(grappler, char)
        char_name_for_grappler = capitalize_first(
            get_display_name_safe(char, grappler)
        )
        char.msg(
            escape_messages.get(
                "attacker_msg",
                f"You struggle but fail to break free from "
                f"{grappler_name_for_char}'s grasp!",
            )
        )
        grappler.msg(
            escape_messages.get(
                "victim_msg",
                f"{char_name_for_grappler} struggles but fails to break "
                f"free from your grasp!",
            )
        )
        if char.location:
            obs_template = escape_messages.get("observer_template")
            if obs_template:
                msg_room_identity(
                    location=char.location,
                    template=obs_template,
                    char_refs=escape_messages.get(
                        "observer_char_refs",
                        {"actor": char, "target_char": grappler},
                    ),
                    exclude=[char, grappler],
                )
            else:
                msg_room_identity(
                    location=char.location,
                    template=(
                        "{actor} struggles but fails to break free "
                        "from {target_char}'s grasp!"
                    ),
                    char_refs={"actor": char, "target_char": grappler},
                    exclude=[char, grappler],
                )
        splattercast.msg(
            f"AUTO_ESCAPE_FAIL: {char.key} failed to escape "
            f"{grappler.key}."
        )

    # Either way, turn ends after escape attempt
    return True
