# Clothing System Commands
#
# Complete clothing management system including:
# - CmdWear/CmdRemove: Basic wear/remove functionality
# - CmdRollUp/CmdUnroll: Adjustable clothing features
# - CmdZip/CmdUnzip: Closure management
#
from evennia import Command
from evennia.utils.utils import iter_to_str

from world.combat.constants import (
    STYLE_ADJUSTABLE,
    STYLE_CLOSURE,
    STYLE_STATE_NORMAL,
    STYLE_STATE_ROLLED,
    STYLE_STATE_UNZIPPED,
    STYLE_STATE_ZIPPED,
)
from world.grammar import with_article
from world.identity_utils import msg_room_identity


def _snapshot_actor_names(caller, char_refs):
    """Capture per-observer display names for *char_refs* before mutation.

    Returns a ``pre_resolved_refs`` mapping suitable for
    :func:`world.identity_utils.msg_room_identity` of the shape
    ``{placeholder: {observer: display_name}}``.

    This is the snapshot idiom for actions that mutate the actor's own
    sdesc inputs (clothing, future ``wield``/``appear``).  Without it,
    observers receive the broadcast describing the actor's *post-action*
    sdesc, which produces nonsense like "a lithe masked droog in a
    black balaclava puts on a black balaclava" — the message describes
    the actor as if the action had already taken effect on their
    appearance.  See specs/IDENTITY_RECOGNITION_SPEC.md
    §"Action Broadcast Sdesc Stability".

    Defensive: snapshots every placeholder in *char_refs* so future
    multi-actor templates (e.g. forced equip with ``{actor}`` and
    ``{victim}``) get stable names too, not only the placeholder we
    know mutates today.
    """
    location = caller.location
    if location is None:
        return {}
    observers = [
        obs
        for obs in location.contents
        if obs is not caller and hasattr(obs, "msg")
    ]
    return {
        placeholder: {obs: char.get_display_name(obs) for obs in observers}
        for placeholder, char in char_refs.items()
    }


def _articled(item_key: str) -> str:
    """Return ``"a black balaclava"`` / ``"blue jeans"`` for *item_key*.

    Pluralia-tantum nouns (``"blue jeans"``) are returned bare; all
    other nouns receive the appropriate indefinite article.
    """
    return with_article(item_key)


class CmdWear(Command):
    """
    Wear a clothing item from your inventory.

    Usage:
        wear <item>

    Examples:
        wear jacket
        wear leather boots
        wear 2nd shirt
    """

    key = "wear"
    aliases = []
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Wear what?")
            return
        
        # Find the item in inventory
        item = caller.search(self.args.strip(), location=caller, quiet=True)
        
        # If not found in inventory, check hands (wielded items)
        if not item:
            hands = getattr(caller, 'hands', {})
            for hand, held_item in hands.items():
                if held_item and held_item.key.lower() == self.args.strip().lower():
                    item = held_item
                    break
        
        if not item:
            caller.msg(f"You don't have '{self.args.strip()}'.")
            return
        
        # Use first match if multiple found
        if isinstance(item, list):
            item = item[0]
        
        # Check if item is wearable
        if not item.is_wearable():
            caller.msg(f"You can't wear {item.key}.")
            return
        
        # Check if already worn
        if caller.is_item_worn(item):
            caller.msg(f"You're already wearing {item.key}.")
            return
        
        # Attempt to wear the item.  Snapshot observer names BEFORE
        # mutating worn_items so the broadcast describes the actor as
        # they appeared at the moment they began the action.
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)
        success, message = caller.wear_item(item)
        caller.msg(message)

        if success:
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} puts on {_articled(item.key)}.",
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )


class CmdRemove(Command):
    """
    Remove a worn clothing item.

    Usage:
        remove <item>
        unwear <item>
        remove all

    Examples:
        remove jacket
        unwear boots
        remove all
    """

    key = "remove"
    aliases = ["unwear"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Remove what?")
            return
        
        args = self.args.strip().lower()
        
        # Handle "remove all"
        if args == "all":
            worn_items = caller.get_worn_items()
            if not worn_items:
                caller.msg("You're not wearing anything.")
                return

            # Snapshot observer names BEFORE mutating worn state so the
            # broadcast describes the actor as they appeared at the
            # moment they began the action.
            char_refs = {"actor": caller}
            pre_resolved = _snapshot_actor_names(caller, char_refs)

            removed_items = []
            for item in worn_items:
                success, message = caller.remove_item(item)
                if success:
                    removed_items.append(item.key)

            if removed_items:
                caller.msg(f"You remove: {', '.join(removed_items)}")
                articled = iter_to_str([_articled(key) for key in removed_items])
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} removes {articled}.",
                    char_refs=char_refs,
                    exclude=[caller],
                    pre_resolved_refs=pre_resolved,
                )
            else:
                caller.msg("You couldn't remove anything.")
            return
        
        # Find worn item by name
        worn_items = caller.get_worn_items()
        item = None
        
        # Search through worn items
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # STICKY GRENADE WARNING - Check for stuck grenades before removal
        # Snapshot actor names BEFORE remove_item mutates worn state.
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        if item.db.stuck_grenade is not None:
            grenade = item.db.stuck_grenade
            
            # Get remaining countdown time if any
            remaining = getattr(grenade.ndb, 'countdown_remaining', 0)
            stuck_location = grenade.db.stuck_to_location if grenade.db.stuck_to_location is not None else 'unknown'
            
            # Send dramatic warning
            if remaining > 0:
                caller.msg(
                    f"\n|R╔══════════════════════════════════════╗|n\n"
                    f"|R║  ⚠️  CRITICAL WARNING  ⚠️           ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  LIVE {grenade.key.upper()} ATTACHED       ║|n\n"
                    f"|R║  COUNTDOWN: {remaining} SECONDS REMAINING   ║|n\n"
                    f"|R║  MAGNETICALLY CLAMPED AT {stuck_location.upper():^7}  ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  Removing this armor will NOT       ║|n\n"
                    f"|R║  break the magnetic bond!           ║|n\n"
                    f"|R║  Grenade stays stuck to armor!      ║|n\n"
                    f"|R║                                      ║|n\n"
                    f"|R║  DROP ARMOR AND FLEE TO SURVIVE!    ║|n\n"
                    f"|R╚══════════════════════════════════════╝|n\n"
                )
            else:
                caller.msg(
                    f"\n|y*** WARNING ***|n\n"
                    f"A {grenade.key} is magnetically clamped to this {item.key}.\n"
                    f"Removing the armor will NOT break the magnetic bond.\n"
                    f"The grenade will remain stuck to the armor.\n"
                )
            
            # Warn the room (possessive form: "their X" stays as-is)
            msg_room_identity(
                location=caller.location,
                template=(
                    f"|R{{actor}} carefully removes their {item.key} - "
                    f"the magnetically attached {_articled(grenade.key)} moves "
                    f"with it!|n"
                ),
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )
        
        # Remove the item
        success, message = caller.remove_item(item)
        caller.msg(message)
        
        if success:
            # Message to room (only if no grenade warning was sent)
            if item.db.stuck_grenade is None:
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} removes {_articled(item.key)}.",
                    char_refs=char_refs,
                    exclude=[caller],
                    pre_resolved_refs=pre_resolved,
                )


class CmdRollUp(Command):
    """
    Roll up sleeves or similar adjustable clothing features.

    Usage:
        rollup <item>
        unroll <item>

    Examples:
        rollup shirt
        unroll sleeves
        rollup jacket
    """

    key = "rollup"
    aliases = ["unroll"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Roll up what?")
            return
        
        # Find worn item
        worn_items = caller.get_worn_items()
        item = None
        
        args = self.args.strip().lower()
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # Determine target state based on command
        if self.cmdstring.lower() == "rollup":
            target_state = STYLE_STATE_ROLLED
            action = "roll up"
        else:  # unroll
            target_state = STYLE_STATE_NORMAL
            action = "unroll"
        
        # Check if item supports adjustable property
        if STYLE_ADJUSTABLE not in item.style_configs:
            caller.msg(f"The {item.key} doesn't have anything to {action}.")
            return
        
        # Check if already in target state
        current_state = item.get_style_property(STYLE_ADJUSTABLE)
        if current_state == target_state:
            if target_state == STYLE_STATE_ROLLED:
                caller.msg(f"The {item.key} is already rolled up.")
            else:
                caller.msg(f"The {item.key} is already unrolled.")
            return
        
        # Check if transition is valid (has both coverage and desc changes)
        if not item.can_style_property_to(STYLE_ADJUSTABLE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Snapshot observer names BEFORE the style change so the
        # broadcast describes the actor as they appeared at the
        # moment they began the action (rolling/unrolling can
        # change worn_sdesc_short and thus the sdesc).
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        # Apply the style change
        success = item.set_style_property(STYLE_ADJUSTABLE, target_state)
        
        if success:
            if target_state == STYLE_STATE_ROLLED:
                caller.msg(f"You roll up the {item.key}.")
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} rolls up {_articled(item.key)}.",
                    char_refs=char_refs,
                    exclude=[caller],
                    pre_resolved_refs=pre_resolved,
                )
            else:
                caller.msg(f"You unroll the {item.key}.")
                msg_room_identity(
                    location=caller.location,
                    template=f"{{actor}} unrolls {_articled(item.key)}.",
                    char_refs=char_refs,
                    exclude=[caller],
                    pre_resolved_refs=pre_resolved,
                )
        else:
            caller.msg(f"You can't {action} the {item.key}.")


class CmdZip(Command):
    """
    Zip, unzip, button, or unbutton clothing items with closures.

    Usage:
        zip <item>
        unzip <item>
        button <item>
        unbutton <item>

    Examples:
        zip jacket
        unzip boots
        button shirt
        unbutton coat
        zip up coat
    """

    key = "zip"
    aliases = ["unzip", "button", "unbutton"]
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        
        if not self.args:
            caller.msg("Zip what?")
            return
        
        # Find worn item
        worn_items = caller.get_worn_items()
        item = None
        
        args = self.args.strip().lower()
        # Handle "zip up" as just "zip"
        if args.startswith("up "):
            args = args[3:]
        
        for worn_item in worn_items:
            if args in worn_item.key.lower():
                item = worn_item
                break
        
        if not item:
            caller.msg(f"You're not wearing '{self.args.strip()}'.")
            return
        
        # Determine target state based on command
        cmd = self.cmdstring.lower()
        if cmd in ["zip", "button"]:
            target_state = STYLE_STATE_ZIPPED
            action = "zip up" if cmd == "zip" else "button up"
            action_past = "zipped up" if cmd == "zip" else "buttoned up"
        else:  # unzip, unbutton
            target_state = STYLE_STATE_UNZIPPED
            action = "unzip" if cmd == "unzip" else "unbutton"
            action_past = "unzipped" if cmd == "unzip" else "unbuttoned"
        
        # Check if item supports closure property
        if STYLE_CLOSURE not in item.style_configs:
            if cmd in ["zip", "unzip"]:
                caller.msg(f"The {item.key} doesn't have a zipper.")
            else:  # button, unbutton
                caller.msg(f"The {item.key} doesn't have buttons.")
            return
        
        # Check if already in target state
        current_state = item.get_style_property(STYLE_CLOSURE)
        if current_state == target_state:
            if target_state == STYLE_STATE_ZIPPED:
                if cmd == "zip":
                    caller.msg(f"The {item.key} is already zipped up.")
                else:  # button
                    caller.msg(f"The {item.key} is already buttoned up.")
            else:  # UNZIPPED
                if cmd == "unzip":
                    caller.msg(f"The {item.key} is already unzipped.")
                else:  # unbutton
                    caller.msg(f"The {item.key} is already unbuttoned.")
            return
        
        # Check if transition is valid (has both coverage and desc changes)
        if not item.can_style_property_to(STYLE_CLOSURE, target_state):
            caller.msg(f"That wouldn't change anything about the {item.key}.")
            return
        
        # Snapshot observer names BEFORE the style change so the
        # broadcast describes the actor as they appeared at the
        # moment they began the action (zipping/buttoning can
        # change worn_sdesc_short and thus the sdesc).
        char_refs = {"actor": caller}
        pre_resolved = _snapshot_actor_names(caller, char_refs)

        # Apply the style change
        success = item.set_style_property(STYLE_CLOSURE, target_state)
        
        if success:
            caller.msg(f"You {action} the {item.key}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} {action_past} {_articled(item.key)}.",
                char_refs=char_refs,
                exclude=[caller],
                pre_resolved_refs=pre_resolved,
            )
        else:
            caller.msg(f"You can't {action} the {item.key}.")


# =====================================================================
# Third-party clothing manipulation (#307, PR-H3)
# =====================================================================
#
# Two new verbs surface the third-party clothing interface settled
# in the design discussion:
#
#   dress <target> in <item>     — put clothing on someone / something
#   undress <target> [<item>]    — remove clothing from someone / something
#
# Both verbs gate on the target being unwilling-or-incapacitated:
#
#   * Severed appendages (worn-on-severed structure introduced in
#     this PR)
#   * Unconscious characters
#   * Dead characters / corpses
#
# Conscious cooperative dressing is intentionally deferred to the
# future trust/consent layer (per the project memory:
# project_gelatinous_trust_consent).  Until that ships, conscious
# targets get a clear rejection that hints at the future system.
# Do not paint into a corner by hard-coding rejection logic that
# the consent layer can't gracefully extend.


def _can_third_party_clothing(target):
    """Permission gate for dress / undress (#307 PR-H3 + memory).

    Returns True when the target is in a state where third-party
    clothing manipulation is allowed without explicit consent:
    severed appendage, unconscious character, dead character.
    The trust/consent layer will extend this contract to cover
    conscious cooperative targets; until then it's the limit.
    """
    from typeclasses.items import Appendage
    if isinstance(target, Appendage):
        return True

    medical_state = getattr(target, "medical_state", None)
    if medical_state is None:
        return False
    is_dead = getattr(medical_state, "is_dead", None)
    is_unconscious = getattr(medical_state, "is_unconscious", None)
    if callable(is_dead) and is_dead():
        return True
    if callable(is_unconscious) and is_unconscious():
        return True
    return False


def _resolve_clothing_target(caller, target_phrase):
    """Resolve a third-party clothing target.

    Three resolution stages, mirroring ``CmdSurgical._resolve_target``
    so the surface for ``dress`` / ``undress`` matches the rest of
    the medical / interaction verbs:

    1. **Identity pipeline** — handles default sdescs ("towering",
       "woman"), recognised-name keywords, and disguise overrides
       for character targets in the same room.
    2. **Inventory fallback** — catches severed appendages the caller
       is carrying so they resolve without setting them down.
    3. **Room fallback** — plain Evennia search for non-character
       targets (corpses, items) that don't surface on the identity
       bus.

    Returns ``None`` on no match.  The identity helper / plain
    search emit their own messages on ambiguity or not-found.
    """
    raw = target_phrase.strip()
    if not raw:
        return None

    # Identity pipeline — characters with sdescs or disguise overrides.
    from commands._identity_targeting import resolve_character_target
    identity_match = resolve_character_target(
        caller, raw, allow_self=False,
    )
    if identity_match is not None:
        return identity_match

    # Inventory — severed parts the caller is carrying.
    candidates = list(caller.contents)
    if candidates:
        inventory_match = caller.search(
            raw, candidates=candidates, quiet=True,
        )
        if inventory_match:
            return (
                inventory_match[0]
                if isinstance(inventory_match, list)
                else inventory_match
            )

    # Room — corpses and any other non-character targets.
    return caller.search(raw)


class CmdDress(Command):
    """Dress another character or severed body part in a clothing item.

    Usage:
        dress <target> in <item>

    Examples:
        dress unconscious bob in jacket
        dress severed left arm in leather glove
        dress corpse in burial shroud

    Target must be unconscious, dead, or a severed appendage —
    conscious cooperative dressing requires the trust/consent
    system, which isn't implemented yet.  The clothing item must
    be in your inventory; it transfers to the target along with
    the worn registration.

    Related: undress, wear, remove.
    """

    key = "dress"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if " in " not in args:
            caller.msg("Usage: dress <target> in <item>")
            return

        target_phrase, _, item_phrase = args.partition(" in ")
        target_phrase = target_phrase.strip()
        item_phrase = item_phrase.strip()
        if not target_phrase or not item_phrase:
            caller.msg("Usage: dress <target> in <item>")
            return

        target = _resolve_clothing_target(caller, target_phrase)
        if target is None:
            return

        item = caller.search(item_phrase, location=caller, quiet=True)
        if not item:
            caller.msg(f"You don't have '{item_phrase}'.")
            return
        if isinstance(item, list):
            item = item[0]

        if not _can_third_party_clothing(target):
            caller.msg(
                f"{target.get_display_name(caller)} is conscious "
                f"and would resist. (Cooperative dressing of a "
                f"conscious target requires the trust/consent system, "
                f"which isn't implemented yet.)"
            )
            return

        if not hasattr(item, "is_wearable") or not item.is_wearable():
            caller.msg(f"{item.get_display_name(caller)} can't be worn.")
            return

        from typeclasses.items import Appendage
        if isinstance(target, Appendage):
            success, message = self._dress_appendage(target, item)
        elif hasattr(target, "wear_item"):
            success, message = self._dress_character(target, item)
        else:
            caller.msg(
                f"You can't dress {target.get_display_name(caller)}."
            )
            return

        if not success:
            caller.msg(message)
            return

        item_name_d = item.get_display_name(caller)
        target_name_d = target.get_display_name(caller)
        caller.msg(f"You dress {target_name_d} in {item_name_d}.")
        if (
            hasattr(target, "has_account")
            and getattr(target, "has_account", False)
            and hasattr(target, "msg")
        ):
            target.msg(
                f"{caller.get_display_name(target)} dresses you in "
                f"{item.get_display_name(target)}."
            )
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} dresses {{target}} in {item_name_d}.",
            char_refs={"actor": caller, "target": target},
            exclude=[caller, target],
        )

    def _dress_character(self, target, item):
        """Move the item into ``target``'s inventory and call its
        existing ``wear_item`` method.  On failure, roll the item
        back to the caller so it isn't orphaned on a target that
        wouldn't accept it."""
        item.move_to(target, quiet=True)
        success, message = target.wear_item(item)
        if not success:
            item.move_to(self.caller, quiet=True)
        return success, message

    def _dress_appendage(self, target, item):
        """Worn-on-severed-appendage path.  Match the item's
        coverage against the appendage's chain locations; wear at
        the intersection.

        Rejects items that don't cover any chain location (a right
        glove can't wear on a severed left arm; a chest piece can't
        wear on a severed leg).
        """
        chain = set(target.db.chain or (target.db.location_name,))
        if hasattr(item, "get_current_coverage"):
            coverage = set(item.get_current_coverage() or ())
        else:
            coverage = set()

        applicable = coverage & chain
        if not applicable:
            return False, (
                f"{item.get_display_name(self.caller)} doesn't fit on "
                f"{target.get_display_name(self.caller)}."
            )

        item.move_to(target, quiet=True)
        appendage_worn = dict(target.db.worn_items or {})
        for loc in applicable:
            existing = list(appendage_worn.get(loc) or ())
            if item not in existing:
                existing.append(item)
                appendage_worn[loc] = existing
        target.db.worn_items = appendage_worn
        return True, ""


class CmdUndress(Command):
    """Remove clothing from another character or severed body part.

    Usage:
        undress <target>
        undress <target> <item>

    First form removes all worn items.  Second removes a single
    item by name (substring match against the target's worn
    items).  Removed items transfer to your inventory.

    Target must be unconscious, dead, or a severed appendage —
    same gate as ``dress``.

    Related: dress, remove.
    """

    key = "undress"
    locks = "cmd:all()"
    help_category = "Inventory"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("Usage: undress <target> [<item>]")
            return

        # Greedy on target first — multi-word targets like
        # ``severed left arm`` work.  Only narrow if the whole
        # phrase doesn't resolve.
        target = _resolve_clothing_target(caller, args)
        item_phrase = None
        if target is None:
            tokens = args.rsplit(" ", 1)
            if len(tokens) == 2:
                maybe_target = tokens[0].strip()
                maybe_item = tokens[1].strip()
                target = _resolve_clothing_target(caller, maybe_target)
                if target is not None:
                    item_phrase = maybe_item
        if target is None:
            return

        if not _can_third_party_clothing(target):
            caller.msg(
                f"{target.get_display_name(caller)} is conscious "
                f"and would resist. (Cooperative undressing of a "
                f"conscious target requires the trust/consent "
                f"system, which isn't implemented yet.)"
            )
            return

        from typeclasses.items import Appendage
        if isinstance(target, Appendage):
            removed = self._undress_appendage(target, item_phrase)
        elif hasattr(target, "get_worn_items"):
            removed = self._undress_character(target, item_phrase)
        else:
            caller.msg(
                f"You can't undress {target.get_display_name(caller)}."
            )
            return

        if not removed:
            if item_phrase:
                caller.msg(
                    f"{target.get_display_name(caller)} isn't wearing "
                    f"'{item_phrase}'."
                )
            else:
                caller.msg(
                    f"{target.get_display_name(caller)} isn't wearing "
                    f"anything."
                )
            return

        for item in removed:
            item.move_to(caller, quiet=True)

        names = ", ".join(item.get_display_name(caller) for item in removed)
        target_name = target.get_display_name(caller)
        caller.msg(f"You undress {target_name}, taking: {names}.")
        if (
            hasattr(target, "has_account")
            and getattr(target, "has_account", False)
            and hasattr(target, "msg")
        ):
            target.msg(
                f"{caller.get_display_name(target)} undresses you, "
                f"taking your clothing."
            )
        msg_room_identity(
            location=caller.location,
            template=f"{{actor}} undresses {{target}}.",
            char_refs={"actor": caller, "target": target},
            exclude=[caller, target],
        )

    def _undress_character(self, target, item_phrase):
        """Strip worn items off ``target`` and return the removed
        list.  Uses ``remove_item`` so layer-conflict / state
        cleanup runs the same way it does for self-removal."""
        worn = target.get_worn_items() or []
        if not worn:
            return []

        if item_phrase:
            phrase = item_phrase.lower()
            worn = [it for it in worn if phrase in it.key.lower()]
            if not worn:
                return []

        removed = []
        for item in worn:
            success, _msg = target.remove_item(item)
            if success:
                removed.append(item)
        return removed

    def _undress_appendage(self, target, item_phrase):
        """Strip worn items off a severed appendage and return the
        removed list.  Updates the appendage's ``worn_items`` dict
        in place to reflect the removal."""
        worn_dict = dict(target.db.worn_items or {})
        if not worn_dict:
            return []

        all_items = []
        for items in worn_dict.values():
            for item in (items or []):
                if item not in all_items:
                    all_items.append(item)

        if item_phrase:
            phrase = item_phrase.lower()
            all_items = [
                it for it in all_items if phrase in it.key.lower()
            ]
        if not all_items:
            return []

        new_worn = {}
        for loc, items in worn_dict.items():
            kept = [
                it for it in (items or []) if it not in all_items
            ]
            if kept:
                new_worn[loc] = kept
        target.db.worn_items = new_worn
        return all_items
