"""
Consumption Method Commands

Natural language commands for consuming medical items and substances.
Implements the universal consumption system with inject, apply, bandage, etc.
"""

from evennia import Command
from commands._identity_targeting import resolve_character_target
from world.identity_utils import msg_room_identity
from world.medical.utils import (
    is_medical_item, can_be_used, get_medical_type, get_stat_requirement,
    calculate_treatment_success, apply_medical_effects, use_item
)


class ConsumptionCommand(Command):
    """
    Base class for all consumption method commands.
    
    Provides common functionality for:
    - Item targeting and validation
    - Target character handling (self vs others)
    - Medical state checking
    - Treatment success calculation
    - Time-based actions (multi-round procedures)
    """
    
    def get_item_and_target(self, args, allow_body_location=False):
        """
        Parse command arguments to get item and target.
        
        Args:
            args (str): Command arguments
            allow_body_location (bool): Whether to parse body location
            
        Returns:
            dict: Contains item, target, body_location, errors
        """
        caller = self.caller
        result = {
            "item": None,
            "target": caller,  # Default to self
            "body_location": None,
            "errors": []
        }
        
        if not args:
            result["errors"].append(f"Usage: {self.key} <item> [target]")
            return result
            
        # Parse arguments
        parts = args.split()
        item_name = parts[0]
        
        # Find the item
        item = caller.search(item_name, location=caller, quiet=True)
        if not item:
            result["errors"].append(f"You don't have '{item_name}'.")
            return result
        elif len(item) > 1:
            result["errors"].append(f"Multiple items match '{item_name}'. Be more specific.")
            return result
        
        result["item"] = item[0]
        
        # Check if it's a medical item
        if not is_medical_item(result["item"]):
            result["errors"].append(f"{result['item'].get_display_name(caller)} is not a medical item.")
            return result
            
        # Parse target (if specified)
        if len(parts) > 1:
            target_name = parts[1]
            if target_name.lower() in ["me", "myself", "self"]:
                result["target"] = caller
            else:
                # Identity-aware target lookup. The helper handles
                # disambiguation messaging and returns None on no/many.
                target = resolve_character_target(caller, target_name)
                if not target:
                    result["errors"].append(f"Cannot find '{target_name}'.")
                    return result
                result["target"] = target
                
        # Parse body location (for commands that support it)
        if allow_body_location and len(parts) > 2:
            result["body_location"] = parts[2]
            
        return result
        
    def check_medical_requirements(self, item, user, target):
        """
        Check if medical requirements are met for using the item.
        
        Returns:
            list: List of error messages, empty if all requirements met
        """
        errors = []
        
        # Check if item can be used
        if not can_be_used(item):
            errors.append(f"{item.get_display_name(user)} is empty or used up.")
            return errors
            
        # Check stat requirements
        stat_req = get_stat_requirement(item)
        if stat_req:
            user_intellect = getattr(user, 'intellect', 1)
            if user_intellect < stat_req:
                errors.append(f"You need Intellect {stat_req} to use {item.get_display_name(user)}.")
                
        # Check if target has medical state
        try:
            medical_state = target.medical_state
            if medical_state is None:
                errors.append(f"{target.get_display_name(user)} has no medical state to treat.")
        except AttributeError:
            errors.append(f"{target.get_display_name(user)} cannot receive medical treatment.")
            
        # Check consciousness for certain procedures
        if hasattr(target, 'is_unconscious') and target.is_unconscious():
            # Some procedures can be done on unconscious patients
            medical_type = get_medical_type(item)
            if medical_type not in ["blood_restoration", "surgical_treatment", "wound_care", "antiseptic", "fracture_treatment", "organ_repair"]:
                errors.append(f"{target.get_display_name(user)} is unconscious and cannot cooperate.")
                
        return errors
        
    def execute_treatment(self, item, user, target, **kwargs):
        """
        Execute the medical treatment with the item.
        
        Returns:
            str: Result message
        """
        # Calculate treatment success
        condition_type = kwargs.get('condition_type', 'bleeding')  # Default condition
        success_result = calculate_treatment_success(item, user, target, condition_type)
        
        # Apply item effects based on success
        if success_result["success_level"] == "success":
            # Check if actual treatment is possible before applying effects
            medical_type = get_medical_type(item)
            treatment_possible = self._check_treatment_possible(target, medical_type)
            
            result_msg = apply_medical_effects(item, user, target, **kwargs)
            
            if treatment_possible:
                use_result = use_item(item)  # Only consume if treatment actually happened
                if use_result["destroyed"]:
                    result_msg += f" {use_result['message']}"
            else:
                # No treatment occurred - don't consume the item
                result_msg += " No supplies were used."
            
        elif success_result["success_level"] == "partial_success":
            # Partial success - reduced effects
            result_msg = f"Partial success: {apply_medical_effects(item, user, target, **kwargs)}"
            result_msg += " (Treatment was not fully effective.)"
            use_result = use_item(item)
            if use_result["destroyed"]:
                result_msg += f" {use_result['message']}"
            
        else:  # failure
            result_msg = f"Treatment failed! {item.get_display_name(user)} was wasted."
            use_result = use_item(item)
            if use_result["destroyed"]:
                result_msg += f" {use_result['message']}"
            
        # Add dice roll information for feedback
        if success_result["success_level"] != "success":
            result_msg += f" (Rolled {success_result['roll']} + {success_result['medical_skill']:.1f} = {success_result['total']:.1f} vs {success_result['difficulty']})"
            
        return result_msg
        
    def _check_treatment_possible(self, target, medical_type):
        """
        Check if actual treatment is possible based on target's medical state.
        
        Args:
            target: Character to be treated
            medical_type: Type of medical treatment
            
        Returns:
            bool: True if treatment can actually occur, False if only examination possible
        """
        try:
            medical_state = target.medical_state
        except AttributeError:
            return False
            
        if medical_type == "surgical_treatment":
            # Check for damaged soft tissue organs (excludes bones and destroyed organs)
            damaged_organs = [organ for name, organ in medical_state.organs.items() 
                            if (organ.current_hp < organ.max_hp and organ.current_hp > 0 and 
                                not (organ.data.get("fracture_vulnerable", False) or organ.data.get("bone_type")))]
            return len(damaged_organs) > 0
            
        elif medical_type == "fracture_treatment":
            # Check for damaged bones (excludes destroyed bones)
            damaged_bones = [organ for name, organ in medical_state.organs.items() 
                           if (organ.current_hp < organ.max_hp and organ.current_hp > 0 and 
                               (organ.data.get("fracture_vulnerable", False) or organ.data.get("bone_type")))]
            return len(damaged_bones) > 0
            
        elif medical_type == "blood_restoration":
            # Check if character actually needs blood restoration
            try:
                # Check for low blood level or bleeding conditions
                blood_level = getattr(target.medical_state, 'blood_level', 100)
                has_bleeding = any(condition.condition_type == "minor_bleeding" 
                                 for condition in getattr(target.medical_state, 'conditions', []))
                return blood_level < 100 or has_bleeding
            except Exception:
                return False
                
        elif medical_type == "wound_care":
            # Check if character has bleeding conditions that bandages can treat
            try:
                # Check for bleeding conditions (bandages help with external bleeding)
                has_bleeding = any(condition.condition_type == "minor_bleeding" 
                                 for condition in getattr(target.medical_state, 'conditions', []))
                return has_bleeding
            except Exception:
                return False
                
        elif medical_type in ["pain_relief", "antiseptic"]:
            # These can still always be applied (harder to detect pain/infection need)
            return True
            
        else:
            # For other medical types, assume treatment is always possible
            return True


class CmdInject(ConsumptionCommand):
    """
    Inject a medical substance into yourself or another character.
    
    Usage:
        inject <item>
        inject <item> <target>
        
    Examples:
        inject painkiller
        inject stimpak Alice
        inject blood bag Bob
        
    Injectable items include painkillers, blood bags, stimpaks, and other
    liquid medical substances. Requires basic medical knowledge for some items.
    """
    
    key = "inject"
    aliases = ["shot", "jab"]
    help_category = "Medical"
    
    def func(self):
        """Execute the inject command."""
        caller = self.caller
        
        # Parse arguments
        result = self.get_item_and_target(self.args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return
            
        item, target = result["item"], result["target"]
        is_self = (caller == target)
        
        # Check if item can be injected
        injectable_types = ["pain_relief", "blood_restoration", "stimulant", "toxin"]
        medical_type = get_medical_type(item)
        if medical_type not in injectable_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be injected.")
            return
            
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return
            
        # Execute injection
        if is_self:
            caller.msg(f"You inject {item.get_display_name(caller)} into your arm.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} injects {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You inject {item.get_display_name(caller)} into {target.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} injects {item.get_display_name(target)} into you.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} injects {item.key} into {{target}}.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply treatment effects
        result_msg = self.execute_treatment(item, caller, target)
        caller.msg(f"Injection result: {result_msg}")
        
        if not is_self:
            target.msg(f"Treatment result: {result_msg}")


class CmdApply(ConsumptionCommand):
    """
    Apply a medical treatment to yourself or another character.

    Usage:
        apply <item> on <target>
        apply <item> on <target>'s <location>
        apply <item> on <target>'s <organ>

    Examples:
        apply burn gel on Alice
        apply bandage on bob's chest
        apply antibiotic on bob's heart      (needs open chest incision)
        apply splint on charlie's left arm

    Surface treatments (bandages, salves, antiseptics on skin) work
    on any external location.  Deep treatments targeting internal
    organs (heart, lungs, liver, etc.) require an open incision at
    the organ's container — see ``incise``.

    For actual surgical procedures (opening, harvesting organs,
    installing organs, closing) see ``help procedures``.

    Related:  incise, harvest, install, suture, inject, spray.
    """

    key = "apply"
    aliases = ["rub", "spread"]
    help_category = "Medical"

    def func(self):
        """Execute the apply command."""
        caller = self.caller

        # Normalize "apply X to Y" → "apply X on Y" so both prepositions
        # work.  The location-precision parser below splits on "on" or
        # the possessive.
        raw = (self.args or "").replace(" to ", " on ")

        # Parse "<item> on <target>" / "<item> on <target>'s <location>"
        # via a quick precision-aware split before falling through to
        # the legacy item/target resolver.
        location: str | None = None
        if " on " in raw:
            item_phrase, _, target_phrase = raw.partition(" on ")
            target_phrase = target_phrase.strip()
            if "'s " in target_phrase:
                tname, _, location = target_phrase.partition("'s ")
                target_phrase = tname.strip()
                location = location.strip().replace(" ", "_")
            args = f"{item_phrase.strip()} {target_phrase}"
        else:
            args = raw

        # Hand off to the legacy item/target parser.
        result = self.get_item_and_target(args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return

        item, target = result["item"], result["target"]
        is_self = (caller == target)

        # Location precision: if the player named a specific organ or
        # body location, we still validate that the location is real on
        # the target — but we don't gate on incision state.  Per the
        # #307 design pass, substance application tolerates any delivery;
        # the future drug-system rules will determine whether the item
        # actually does anything useful at the chosen location.
        if location:
            from world.medical.procedures import organs_at_location

            container = location
            try:
                state = target.medical_state
            except AttributeError:
                state = None
            if state is not None and hasattr(state, "organs"):
                organ = state.organs.get(location)
                if organ is not None:
                    container = organ.container

            # Surface location with no organs at all → no anatomical
            # slot on this target.  Reject as nonsense input rather
            # than silently accepting an undefined location.  This is
            # location-validity, not substance-gating.
            if not organs_at_location(target, container) and container == location:
                caller.msg(
                    f"There's nothing at {location.replace('_', ' ')} on "
                    f"{target.get_display_name(caller)} to treat."
                )
                return
        
        # Check if item can be applied topically or orthopedically.
        # Surgical kits are NOT applicable — they're tools for the
        # procedure verbs (incise / harvest / install / suture).
        # See ``help procedures``.
        applicable_types = ["burn_treatment", "antiseptic", "healing_salve", "wound_care", "fracture_treatment", "organ_repair"]
        medical_type = get_medical_type(item)
        if medical_type not in applicable_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be applied.")
            return
            
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return

        # PR-B (#307): wound_care items applied with location precision
        # route through the stabilization dispatch.  Single application
        # both stabilizes the wound (always) and rolls per-category
        # for bleeding / infection / pain reduction.  Repeat-application
        # to a stabilized wound no-ops with a triage hint.
        # PR-D (#307): organ_repair items also route here — the
        # treatments dispatch resolves their organ_repair category
        # alongside bleeding/infection/pain.  Substance tolerance
        # principle keeps the surface uniform.
        if medical_type in ("wound_care", "organ_repair") and location:
            from world.medical.treatments import apply_wound_care
            treatment_target_location = location
            # Resolve location → container if the player named an organ.
            try:
                state = target.medical_state
            except AttributeError:
                state = None
            if state is not None and hasattr(state, "organs"):
                organ = state.organs.get(location)
                if organ is not None:
                    treatment_target_location = organ.container
            outcome = apply_wound_care(
                actor=caller, target=target, item=item,
                location=treatment_target_location,
            )
            if is_self:
                msg_room_identity(
                    location=caller.location,
                    template=(
                        f"{{actor}} applies {item.key} to their "
                        f"{treatment_target_location.replace('_', ' ')}."
                    ),
                    char_refs={"actor": caller},
                    exclude=[caller],
                )
            else:
                msg_room_identity(
                    location=caller.location,
                    template=(
                        f"{{actor}} applies {item.key} to {{target}}'s "
                        f"{treatment_target_location.replace('_', ' ')}."
                    ),
                    char_refs={"actor": caller, "target": target},
                    exclude=[caller, target],
                )
            for line in outcome["messages"]:
                caller.msg(line)
                if not is_self:
                    target.msg(line)
            return

        # Execute application (legacy flow — no location precision or
        # non-wound_care medical types).
        if is_self:
            caller.msg(f"You carefully apply {item.get_display_name(caller)} to your wounds.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} applies {item.key} to their wounds.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You carefully apply {item.get_display_name(caller)} to {target.get_display_name(caller)}'s wounds.")
            target.msg(f"{caller.get_display_name(target)} applies {item.get_display_name(target)} to your wounds.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} applies {item.key} to {{target}}'s wounds.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )

        # Apply treatment effects
        result_msg = self.execute_treatment(item, caller, target)
        caller.msg(f"Application result: {result_msg}")

        if not is_self:
            target.msg(f"Treatment result: {result_msg}")


class CmdBandage(ConsumptionCommand):
    """
    Bandage a wounded body part with medical supplies.
    
    Usage:
        bandage <body_part> with <item>
        bandage <target>'s <body_part> with <item>
        bandage <item>  (applies to worst wounds)
        
    Examples:
        bandage arm with gauze
        bandage Alice's leg with bandages
        bandage chest with medicated wrap
        
    Bandaging stops bleeding, prevents infection, and provides minor healing.
    Works best with proper bandaging supplies like gauze and medical wraps.
    """
    
    key = "bandage"
    # PR-H3 (#307): ``dress`` reclaimed for third-party clothing.
    # CmdBandage keeps ``bandage`` primary + ``wrap`` for the verb
    # space; "dressing a wound" is colloquial but still covered.
    aliases = ["wrap"]
    help_category = "Medical"
    
    def parse(self):
        """Parse bandage command syntax."""
        # Handle different syntax patterns
        args = self.args.strip()
        
        if " with " in args:
            # "bandage arm with gauze" or "bandage Alice's arm with gauze"
            parts = args.split(" with ")
            if len(parts) != 2:
                self.target_and_location = None
                self.item_name = None
                return
                
            target_and_location = parts[0].strip()
            self.item_name = parts[1].strip()
            
            # Parse target and body location
            if "'s " in target_and_location:
                # "Alice's arm" format
                target_parts = target_and_location.split("'s ")
                self.target_name = target_parts[0].strip()
                self.body_location = target_parts[1].strip()
            else:
                # Just body location, target is self
                self.target_name = None
                self.body_location = target_and_location
        else:
            # Just "bandage item" - apply to worst wounds
            self.item_name = args
            self.target_name = None
            self.body_location = None
            
    def func(self):
        """Execute the bandage command."""
        caller = self.caller
        
        if not self.item_name:
            caller.msg("Usage: bandage <body_part> with <item> or bandage <item>")
            return
            
        # Find the item
        item = caller.search(self.item_name, location=caller, quiet=True)
        if not item:
            caller.msg(f"You don't have '{self.item_name}'.")
            return
        elif len(item) > 1:
            caller.msg(f"Multiple items match '{self.item_name}'. Be more specific.")
            return
        item = item[0]
        
        # Check if it's suitable for bandaging
        if not is_medical_item(item):
            caller.msg(f"{item.get_display_name(caller)} is not a medical item.")
            return
            
        bandage_types = ["wound_care", "bandage", "gauze"]
        medical_type = get_medical_type(item)
        if medical_type not in bandage_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be used for bandaging.")
            return
            
        # Find target
        if self.target_name:
            if self.target_name.lower() in ("me", "myself", "self"):
                target = caller
            else:
                target = resolve_character_target(caller, self.target_name)
                if not target:
                    caller.msg(f"Cannot find '{self.target_name}'.")
                    return
        else:
            target = caller
            
        is_self = (caller == target)
        
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return
            
        # Execute bandaging
        location_desc = f" {self.body_location}" if self.body_location else ""
        if is_self:
            caller.msg(f"You bandage your{location_desc} wounds with {item.get_display_name(caller)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} bandages their{location_desc} wounds.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You bandage {target.get_display_name(caller)}'s{location_desc} wounds with {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} bandages your{location_desc} wounds.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} bandages {{target}}'s{location_desc} wounds.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply treatment effects with body location
        result_msg = self.execute_treatment(item, caller, target, body_location=self.body_location)
        caller.msg(f"Bandaging result: {result_msg}")
        
        if not is_self:
            target.msg(f"Treatment result: {result_msg}")


class CmdEat(ConsumptionCommand):
    """
    Eat or consume a solid medical item or food.
    
    Usage:
        eat <item>
        feed <item> to <target>
        
    Examples:
        eat ration bar
        eat painkiller pill
        feed medicine to Alice
        
    Eating is used for pills, tablets, emergency rations, and other solid
    consumables. Works for both medical items and regular food.
    """
    
    key = "eat"
    aliases = ["consume", "swallow"]
    help_category = "Medical"
    
    def func(self):
        """Execute the eat command."""
        caller = self.caller
        
        # Parse arguments  
        result = self.get_item_and_target(self.args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return
            
        item, target = result["item"], result["target"]
        is_self = (caller == target)
        
        # Check if item can be eaten
        edible_types = ["pill", "tablet", "food", "ration", "medicine"]
        medical_type = get_medical_type(item)
        if medical_type not in edible_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be eaten.")
            return
            
        # Check medical requirements (if it's a medical item)
        if is_medical_item(item):
            errors = self.check_medical_requirements(item, caller, target)
            if errors:
                caller.msg(errors[0])
                return
                
        # Execute eating
        if is_self:
            caller.msg(f"You swallow {item.get_display_name(caller)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} swallows {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} swallow {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you swallow {item.get_display_name(target)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} helps {{target}} swallow {item.key}.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply effects
        if is_medical_item(item):
            result_msg = self.execute_treatment(item, caller, target)
            caller.msg(f"Effects: {result_msg}")
            if not is_self:
                target.msg(f"You feel the effects: {result_msg}")
        else:
            # Regular food item
            caller.msg(f"You consumed {item.get_display_name(caller)}.")
            item.delete()  # Regular food items are consumed completely


class CmdDrink(ConsumptionCommand):
    """
    Drink a liquid medical item or beverage.
    
    Usage:
        drink <item>
        give <item> to <target> to drink
        
    Examples:
        drink medical brew
        drink water
        give healing potion to Bob
        
    Drinking is used for liquid medicines, water, alcohol, and other
    liquid consumables. Fast consumption method.
    """
    
    key = "drink"
    aliases = ["sip", "gulp"]
    help_category = "Medical"
    
    def func(self):
        """Execute the drink command."""
        caller = self.caller
        
        # Parse arguments
        result = self.get_item_and_target(self.args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return
            
        item, target = result["item"], result["target"]
        is_self = (caller == target)
        
        # Check if item can be drunk
        liquid_types = ["liquid_medicine", "water", "alcohol", "potion", "drink"]
        medical_type = get_medical_type(item)
        if medical_type not in liquid_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be drunk.")
            return
            
        # Check medical requirements (if it's a medical item)
        if is_medical_item(item):
            errors = self.check_medical_requirements(item, caller, target)
            if errors:
                caller.msg(errors[0])
                return
                
        # Execute drinking
        if is_self:
            caller.msg(f"You drink {item.get_display_name(caller)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} drinks {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} drink {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you drink {item.get_display_name(target)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} helps {{target}} drink {item.key}.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply effects
        if is_medical_item(item):
            result_msg = self.execute_treatment(item, caller, target)
            caller.msg(f"Effects: {result_msg}")
            if not is_self:
                target.msg(f"You feel the effects: {result_msg}")
        else:
            # Regular drink
            caller.msg(f"You drank {item.get_display_name(caller)}.")
            item.delete()  # Regular drinks are consumed completely


class CmdInhale(ConsumptionCommand):
    """
    Inhale gases, vapors, or use inhalers for medical treatment.
    
    Usage:
        inhale <item>
        help <target> inhale <item>
        
    Examples:
        inhale oxygen tank
        inhale stimpak vapor
        help Alice inhale anesthetic gas
        
    Inhalation is used for oxygen tanks, inhalers, anesthetic gases, 
    and vaporized medical substances. Requires conscious target.
    """
    
    key = "inhale"
    aliases = ["huff", "breathe"]
    help_category = "Medical"
    
    def func(self):
        """Execute the inhale command."""
        caller = self.caller
        
        # Parse arguments
        result = self.get_item_and_target(self.args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return
            
        item, target = result["item"], result["target"]
        is_self = (caller == target)
        
        # Check if item can be inhaled
        inhalable_types = ["oxygen", "anesthetic", "inhaler", "gas", "vapor"]
        medical_type = get_medical_type(item)
        if medical_type not in inhalable_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be inhaled.")
            return
            
        # Check if target is conscious (required for inhalation)
        if target.is_unconscious():
            if is_self:
                caller.msg("You cannot inhale while unconscious.")
            else:
                caller.msg(f"{target.get_display_name(caller)} is unconscious and cannot inhale.")
            return
            
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return
            
        # Execute inhalation
        if is_self:
            caller.msg(f"You breathe in {item.get_display_name(caller)} deeply.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} inhales {item.key}.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} inhale {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you inhale {item.get_display_name(target)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} helps {{target}} inhale {item.key}.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply treatment effects
        result_msg = self.execute_treatment(item, caller, target)
        caller.msg(f"Inhalation result: {result_msg}")
        
        if not is_self:
            target.msg(f"Treatment result: {result_msg}")


class CmdSmoke(ConsumptionCommand):
    """
    Smoke medicinal herbs, cigarettes, or combustible treatments.
    
    Usage:
        smoke <item>
        help <target> smoke <item>
        
    Examples:
        smoke medicinal herb
        smoke pain-relief cigarette
        help Bob smoke calming herb
        
    Smoking is used for dried herbs, medicinal cigarettes, and other
    combustible medical substances. Creates smoke and may affect others nearby.
    """
    
    key = "smoke"
    aliases = ["light", "burn"]
    help_category = "Medical"
    
    def func(self):
        """Execute the smoke command."""
        caller = self.caller
        
        # Parse arguments
        result = self.get_item_and_target(self.args)
        if result["errors"]:
            caller.msg(result["errors"][0])
            return
            
        item, target = result["item"], result["target"]
        is_self = (caller == target)
        
        # Check if item can be smoked
        smokable_types = ["herb", "cigarette", "medicinal_plant", "dried_medicine"]
        medical_type = get_medical_type(item)
        if medical_type not in smokable_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be smoked.")
            return
            
        # Check if target is conscious (required for smoking)
        if target.is_unconscious():
            if is_self:
                caller.msg("You cannot smoke while unconscious.")
            else:
                caller.msg(f"{target.get_display_name(caller)} is unconscious and cannot smoke.")
            return
            
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return
            
        # Execute smoking
        if is_self:
            caller.msg(f"You light and smoke {item.get_display_name(caller)}, inhaling the medicinal smoke.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} lights and smokes {item.key}, creating aromatic smoke.",
                char_refs={"actor": caller},
                exclude=[caller],
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} smoke {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you smoke {item.get_display_name(target)}.")
            msg_room_identity(
                location=caller.location,
                template=f"{{actor}} helps {{target}} smoke {item.key}.",
                char_refs={"actor": caller, "target": target},
                exclude=[caller, target],
            )
            
        # Apply treatment effects
        result_msg = self.execute_treatment(item, caller, target)
        caller.msg(f"Smoking result: {result_msg}")
        
        if not is_self:
            target.msg(f"Treatment result: {result_msg}")
