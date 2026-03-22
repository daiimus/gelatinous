"""
Consumption Method Commands

Natural language commands for consuming medical items and substances.
Implements the universal consumption system with inject, apply, bandage, etc.
"""

from evennia import Command
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
                target = caller.search(target_name, location=caller.location, quiet=True)
                if not target:
                    result["errors"].append(f"Cannot find '{target_name}'.")
                    return result
                elif len(target) > 1:
                    result["errors"].append(f"Multiple people match '{target_name}'. Be more specific.")
                    return result
                result["target"] = target[0]
                
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
            if medical_type not in ["blood_restoration", "surgical_treatment", "wound_care", "antiseptic", "fracture_treatment"]:
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} injects {item.get_display_name()}.",
                exclude=caller
            )
        else:
            caller.msg(f"You inject {item.get_display_name(caller)} into {target.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} injects {item.get_display_name(target)} into you.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} injects {item.get_display_name()} into {target.get_display_name()}.",
                exclude=[caller, target]
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
        apply <item>
        apply <item> <target>
        apply <item> to <target>
        
    Examples:
        apply burn gel
        apply antiseptic to Alice
        apply surgical kit to Bob
        apply splint to Charlie
        
    Applicable items include burn gel, antiseptic, healing salves, surgical
    kits, splints, and other medical treatments. Takes time to apply properly.
    Surgery requires high medical skill (Intellect 3+).
    """
    
    key = "apply"
    aliases = ["rub", "spread", "operate", "surgery"]
    help_category = "Medical"
    
    def func(self):
        """Execute the apply command."""
        caller = self.caller
        
        # Handle special surgery/operate aliases that auto-find surgical kits
        if self.cmdstring.lower() in ["surgery", "operate"]:
            # Look for surgical kit in caller's inventory
            surgical_kits = [obj for obj in caller.contents 
                           if hasattr(obj, 'attributes') and 
                           obj.attributes.get('medical_type') == 'surgical_treatment']
            
            if not surgical_kits:
                caller.msg("You don't have a surgical kit to perform surgery.")
                return
                
            # Use the first surgical kit found
            surgical_kit = surgical_kits[0]
            
            # Parse target (surgery/operate only takes target, no item name needed)
            if not self.args.strip():
                caller.msg("Surgery on whom? Usage: surgery <target>")
                return
                
            # Get target
            target = caller.search(self.args.strip(), location=caller.location)
            if not target:
                return
                
            item = surgical_kit
            is_self = (caller == target)
        else:
            # Handle normal "apply item to target" syntax
            args = self.args.replace(" to ", " ")
            
            # Parse arguments
            result = self.get_item_and_target(args)
            if result["errors"]:
                caller.msg(result["errors"][0])
                return
                
            item, target = result["item"], result["target"]
            is_self = (caller == target)
        
        # Check if item can be applied (topically, surgically, or orthopedically)
        applicable_types = ["burn_treatment", "antiseptic", "healing_salve", "wound_care", "surgical_treatment", "fracture_treatment"]
        medical_type = get_medical_type(item)
        if medical_type not in applicable_types:
            caller.msg(f"{item.get_display_name(caller)} cannot be applied.")
            return
            
        # Check medical requirements
        errors = self.check_medical_requirements(item, caller, target)
        if errors:
            caller.msg(errors[0])
            return
            
        # Execute application
        if is_self:
            caller.msg(f"You carefully apply {item.get_display_name(caller)} to your wounds.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} applies {item.get_display_name()} to their wounds.",
                exclude=caller
            )
        else:
            caller.msg(f"You carefully apply {item.get_display_name(caller)} to {target.get_display_name(caller)}'s wounds.")
            target.msg(f"{caller.get_display_name(target)} applies {item.get_display_name(target)} to your wounds.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} applies {item.get_display_name()} to {target.get_display_name()}'s wounds.",
                exclude=[caller, target]
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
    aliases = ["wrap", "dress"]
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
            target = caller.search(self.target_name, location=caller.location, quiet=True)
            if not target:
                caller.msg(f"Cannot find '{self.target_name}'.")
                return
            elif len(target) > 1:
                caller.msg(f"Multiple people match '{self.target_name}'. Be more specific.")
                return
            target = target[0]
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} bandages their{location_desc} wounds.",
                exclude=caller
            )
        else:
            caller.msg(f"You bandage {target.get_display_name(caller)}'s{location_desc} wounds with {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} bandages your{location_desc} wounds.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} bandages {target.get_display_name()}'s{location_desc} wounds.",
                exclude=[caller, target]
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} swallows {item.get_display_name()}.",
                exclude=caller
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} swallow {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you swallow {item.get_display_name(target)}.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} helps {target.get_display_name()} swallow {item.get_display_name()}.",
                exclude=[caller, target]
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} drinks {item.get_display_name()}.",
                exclude=caller
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} drink {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you drink {item.get_display_name(target)}.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} helps {target.get_display_name()} drink {item.get_display_name()}.",
                exclude=[caller, target]
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} inhales {item.get_display_name()}.",
                exclude=caller
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} inhale {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you inhale {item.get_display_name(target)}.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} helps {target.get_display_name()} inhale {item.get_display_name()}.",
                exclude=[caller, target]
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
            caller.location.msg_contents(
                f"{caller.get_display_name()} lights and smokes {item.get_display_name()}, creating aromatic smoke.",
                exclude=caller
            )
        else:
            caller.msg(f"You help {target.get_display_name(caller)} smoke {item.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} helps you smoke {item.get_display_name(target)}.")
            caller.location.msg_contents(
                f"{caller.get_display_name()} helps {target.get_display_name()} smoke {item.get_display_name()}.",
                exclude=[caller, target]
            )
            
        # Apply treatment effects
        result_msg = self.execute_treatment(item, caller, target)
        caller.msg(f"Smoking result: {result_msg}")
        
        if not is_self:
            target.msg(f"Treatment result: {result_msg}")
