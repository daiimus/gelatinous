"""
Medical System Utilities

Utility functions for medical system integration, damage calculation,
and medical state management.
"""

from .constants import ORGANS, HIT_WEIGHTS
from .core import MedicalState


def get_organ_by_body_location(location):
    """
    Get all organs that are contained within a specific body location.
    
    Args:
        location (str): Body location (e.g., "chest", "head", "left_arm")
        
    Returns:
        list: List of organ names in that location
    """
    organs_in_location = []
    for organ_name, organ_data in ORGANS.items():
        if organ_data.get("container") == location:
            organs_in_location.append(organ_name)
    return organs_in_location


def calculate_hit_weights_for_location(location):
    """
    Calculate hit weights for all organs in a body location.
    
    Args:
        location (str): Body location
        
    Returns:
        dict: {organ_name: hit_weight_value} mapping
    """
    organs = get_organ_by_body_location(location)
    hit_weights = {}
    
    for organ_name in organs:
        organ_data = ORGANS.get(organ_name, {})
        weight_category = organ_data.get("hit_weight", "common")
        weight_value = HIT_WEIGHTS.get(weight_category, HIT_WEIGHTS["common"])
        hit_weights[organ_name] = weight_value
        
    return hit_weights


def select_hit_location(character, success_margin=0):
    """
    Dynamically select a hit location based on character's anatomy and organ hit weights.
    Success margin biases selection toward vital areas for skilled attacks.
    
    Args:
        character: Character object with longdesc anatomy structure
        success_margin (int): Attack roll margin (attacker_roll - target_roll)
        
    Returns:
        str: Selected body location (e.g., "chest", "head", "left_arm")
    """
    import random
    
    # Get all available body locations from character's longdesc
    if not hasattr(character, 'longdesc') or not character.longdesc:
        # Fallback to chest if no longdesc defined
        return "chest"
    
    available_locations = list(character.longdesc.keys())
    if not available_locations:
        return "chest"
    
    # Calculate total hit weights for each body location
    location_weights = {}
    
    # Define vital areas for success margin bias
    vital_areas = {"head", "chest", "neck", "abdomen"}
    
    # Calculate success margin bias multiplier
    if success_margin <= 3:
        vital_bias = 1.25  # +25% weight to vital areas
    elif success_margin <= 8:
        vital_bias = 1.5   # +50% weight to vital areas
    elif success_margin <= 15:
        vital_bias = 2.0   # +100% weight to vital areas
    else:
        vital_bias = 3.0   # +200% weight to vital areas
    
    for location in available_locations:
        # Get all organs in this location and sum their hit weights
        organs = get_organ_by_body_location(location)
        total_weight = 0
        
        for organ_name in organs:
            organ_data = ORGANS.get(organ_name, {})
            weight_category = organ_data.get("hit_weight", "common")
            weight_value = HIT_WEIGHTS.get(weight_category, HIT_WEIGHTS["common"])
            total_weight += weight_value
            
        # Apply success margin bias to vital areas
        if location in vital_areas and success_margin > 0:
            total_weight = int(total_weight * vital_bias)
            
        # Use a minimum weight to ensure all locations are possible targets
        location_weights[location] = max(total_weight, 1)
    
    # Perform weighted random selection
    total_weight = sum(location_weights.values())
    if total_weight == 0:
        return "chest"  # Fallback
        
    # Generate random number and select location
    rand_value = random.randint(1, total_weight)
    cumulative_weight = 0
    
    for location, weight in location_weights.items():
        cumulative_weight += weight
        if rand_value <= cumulative_weight:
            return location
            
    # Fallback (should never reach here, but safety first)
    return available_locations[0]


def select_target_organ(location, precision_roll=0, attacker_skill=1):
    """
    Select a specific organ within a body location based on precision.
    Higher precision rolls are more likely to hit rare/vital organs.
    
    Args:
        location (str): Body location that was hit
        precision_roll (int): d20 roll for precision targeting
        attacker_skill (int): Attacker's skill for precision calculation
        
    Returns:
        str: Selected organ name, or None if no organs in location
    """
    import random
    
    organs = get_organ_by_body_location(location)
    if not organs:
        return None
        
    # Calculate precision-based organ weights
    organ_weights = {}
    precision_total = precision_roll + attacker_skill
    
    for organ_name in organs:
        organ_data = ORGANS.get(organ_name, {})
        hit_weight_category = organ_data.get("hit_weight", "common")
        base_weight = HIT_WEIGHTS.get(hit_weight_category, HIT_WEIGHTS["common"])
        
        # Precision affects targeting of rare organs
        # Higher precision = more likely to hit rare/vital organs
        if hit_weight_category == "very_rare":
            # Very rare organs: need high precision to target
            if precision_total >= 25:
                weight = base_weight * 3.0  # Much more likely with exceptional precision
            elif precision_total >= 20:
                weight = base_weight * 2.0  # More likely with good precision
            else:
                weight = base_weight * 0.5  # Less likely with poor precision
        elif hit_weight_category == "rare":
            # Rare organs: moderate precision helps
            if precision_total >= 20:
                weight = base_weight * 2.0
            elif precision_total >= 15:
                weight = base_weight * 1.5
            else:
                weight = base_weight
        else:
            # Common/uncommon organs: always hittable, but less likely with high precision
            if precision_total >= 20:
                weight = base_weight * 0.7  # Skilled attackers avoid hitting "easy" targets
            else:
                weight = base_weight
                
        organ_weights[organ_name] = max(int(weight), 1)
    
    # Weighted random selection of specific organ
    total_weight = sum(organ_weights.values())
    if total_weight == 0:
        return organs[0] if organs else None
        
    rand_value = random.randint(1, total_weight)
    cumulative_weight = 0
    
    for organ_name, weight in organ_weights.items():
        cumulative_weight += weight
        if rand_value <= cumulative_weight:
            return organ_name
            
    # Fallback
    return organs[0] if organs else None


def distribute_damage_to_organs(location, total_damage, medical_state, injury_type="generic", target_organ=None):
    """
    Distribute damage across organs in a body location based on hit weights.
    Only distributes damage to organs that aren't already destroyed.
    
    Args:
        location (str): Body location hit
        total_damage (int): Total damage to distribute
        medical_state: Character's medical state to check organ status
        injury_type (str): Type of injury
        target_organ (str): If specified, apply ALL damage to this organ only
        
    Returns:
        dict: {organ_name: damage_amount} mapping
    """
    organs = get_organ_by_body_location(location)
    if not organs:
        return {}
    
    # Filter out destroyed organs - can't damage what's already destroyed
    functional_organs = []
    for organ_name in organs:
        organ = medical_state.get_organ(organ_name)
        if not organ.is_destroyed():
            functional_organs.append(organ_name)
    
    # If all organs in this location are destroyed, no damage can be applied
    if not functional_organs:
        return {}
    
    # Single organ targeting - apply all damage to specified organ
    if target_organ and target_organ in functional_organs:
        return {target_organ: total_damage}
    
    # If target organ specified but not functional, fall back to distribution
    if target_organ and target_organ not in functional_organs:
        # Target organ is destroyed or doesn't exist in this location
        # Fall back to proportional distribution among functional organs
        pass
        
    hit_weights = calculate_hit_weights_for_location(location)
    # Recalculate total weight using only functional organs
    total_weight = sum(hit_weights.get(organ_name, 0) for organ_name in functional_organs)
    
    if total_weight == 0:
        return {}
        
    damage_distribution = {}
    remaining_damage = total_damage
    
    # Distribute damage proportionally based on hit weights (functional organs only)
    for organ_name in functional_organs[:-1]:  # All but last functional organ
        organ_weight = hit_weights.get(organ_name, 0)
        organ_damage = int((organ_weight / total_weight) * total_damage)
        damage_distribution[organ_name] = organ_damage
        remaining_damage -= organ_damage
        
    # Give remaining damage to last functional organ to ensure total is preserved
    if functional_organs:
        damage_distribution[functional_organs[-1]] = remaining_damage
        
    return damage_distribution


def apply_anatomical_damage(character, damage_amount, location, injury_type="generic", target_organ=None):
    """
    Apply damage to a specific body location, affecting relevant organs.
    
    This is the main integration point with the combat system.
    
    Args:
        character: Character object with medical state
        damage_amount (int): Amount of damage
        location (str): Body location hit
        injury_type (str): Type of injury
        target_organ (str): If specified, target this specific organ
        
    Returns:
        dict: Results of damage application
    """
    # Ensure medical state exists - access property to trigger initialization
    try:
        medical_state = character.medical_state
    except AttributeError:
        # Initialize medical state if character doesn't have the property
        initialize_character_medical_state(character)
        medical_state = character.medical_state
        
    medical_state = character.medical_state
    
    # Distribute damage to organs in the location (only to functional organs)
    damage_distribution = distribute_damage_to_organs(location, damage_amount, medical_state, injury_type, target_organ)
    
    # Check if all organs in this location are destroyed (potential limb loss)
    if not damage_distribution:
        organs_in_location = get_organ_by_body_location(location)
        if organs_in_location:
            # All organs destroyed - this represents total destruction of body part
            return {
                "organs_damaged": [],
                "organs_destroyed": [],
                "conditions_added": [],
                "total_damage": 0,  # No damage applied since everything is already destroyed
                "location": location,
                "limb_lost": True,  # Flag for future limb loss mechanics
                "message": f"No damage applied - all organs in {location} are already destroyed"
            }
    
    results = {
        "organs_damaged": [],
        "organs_destroyed": [],
        "conditions_added": [],
        "total_damage": damage_amount,
        "location": location
    }
    
    # Apply damage to each organ
    for organ_name, organ_damage in damage_distribution.items():
        if organ_damage > 0:
            was_destroyed = medical_state.take_organ_damage(organ_name, organ_damage, injury_type)
            results["organs_damaged"].append((organ_name, organ_damage))
            
            if was_destroyed:
                results["organs_destroyed"].append(organ_name)
                
    # Note: Medical conditions are now automatically created by 
    # MedicalState.take_organ_damage() in core.py, so we don't need
    # to manually add them here anymore.
                
    # Update vital signs after damage
    medical_state.update_vital_signs()
    
    return results


# DEPRECATED: _generate_conditions_for_injury() is no longer used.
# Medical conditions are now automatically created by the new ticker-based
# condition system in world.medical.conditions.py via MedicalState.take_organ_damage()
# 
# def _generate_conditions_for_injury(location, damage_amount, injury_type):
#     """This function has been replaced by the new automatic condition creation system."""
#     pass


def get_medical_status_summary(character):
    """
    Generate a human-readable summary of character's medical status.
    
    Args:
        character: Character with medical state
        
    Returns:
        str: Medical status description
    """
    try:
        medical_state = character.medical_state
    except AttributeError:
        return "No medical information available."
        
    if medical_state is None:
        return "No medical information available."
        
    medical_state = character.medical_state
    lines = []
    
    # Overall status
    if medical_state.is_dead():
        return "DECEASED"
    elif medical_state.is_unconscious():
        lines.append("UNCONSCIOUS")
    else:
        lines.append("CONSCIOUS")
        
    # Vital signs
    lines.append(f"Blood Level: {medical_state.blood_level:.1f}%")
    lines.append(f"Pain Level: {medical_state.pain_level:.1f}")
    lines.append(f"Consciousness: {medical_state.consciousness * 100:.1f}%")
    
    # Active conditions
    if medical_state.conditions:
        lines.append("Active Conditions:")
        for condition in medical_state.conditions:
            location_str = f" ({condition.location})" if condition.location else ""
            condition_name = condition.condition_type.title() if hasattr(condition, 'condition_type') else "Unknown"
            lines.append(f"  - {condition_name} ({condition.severity}){location_str}")
    else:
        lines.append("No active medical conditions")
        
    # Damaged organs
    damaged_organs = [name for name, organ in medical_state.organs.items() 
                     if organ.current_hp < organ.max_hp]
    if damaged_organs:
        lines.append("Damaged Organs:")
        for organ_name in damaged_organs:
            organ = medical_state.organs[organ_name]
            hp_percent = (organ.current_hp / organ.max_hp) * 100
            lines.append(f"  - {organ_name}: {hp_percent:.1f}% functional")
            
    return "\n".join(lines)


def initialize_character_medical_state(character):
    """
    Initialize medical state for a character if it doesn't exist.
    
    Args:
        character: Character object to initialize
    """
    if not hasattr(character, '_medical_state') or character._medical_state is None:
        character._medical_state = MedicalState(character)
        
        # Store in db for persistence
        character.db.medical_state = character._medical_state.to_dict()


def save_medical_state(character):
    """
    Save character's medical state to database.
    
    Args:
        character: Character with medical state to save
    """
    try:
        medical_state = character.medical_state
        if medical_state is not None:
            character.db.medical_state = medical_state.to_dict()
    except AttributeError:
        pass  # Character doesn't have medical state


def load_medical_state(character):
    """
    Load character's medical state from database.
    
    Args:
        character: Character to load medical state for
        
    Returns:
        bool: True if state was loaded, False if none existed
    """
    medical_data = character.db.medical_state
    if medical_data:
        character._medical_state = MedicalState.from_dict(medical_data, character)
        return True
    else:
        # Initialize new medical state if none exists
        initialize_character_medical_state(character)
        return False


# =============================================================================
# MEDICAL ITEM UTILITIES
# =============================================================================

def is_medical_item(item):
    """Check if an item is a medical item."""
    return item.tags.has("medical_item", category="item_type")


def get_medical_type(item):
    """Get the medical type of an item."""
    return item.attributes.get("medical_type", "")


def can_be_used(item):
    """Check if this medical item can still be used."""
    if not is_medical_item(item):
        return False
    
    uses_left = item.attributes.get("uses_left", 1)
    return uses_left > 0


def use_item(item):
    """Use the item, reducing uses left."""
    if not is_medical_item(item):
        return False
        
    uses_left = item.attributes.get("uses_left", 1)
    if uses_left > 0:
        item.attributes.add("uses_left", uses_left - 1)
        return True
    return False


def get_stat_requirement(item):
    """Get the stat requirement for using this item."""
    return item.attributes.get("stat_requirement", 0)


def get_effectiveness(item, condition_type):
    """Get item effectiveness for a specific condition."""
    effectiveness = item.attributes.get("effectiveness", {})
    return effectiveness.get(condition_type, 5)  # Default 5/10


def calculate_treatment_success(item, user, target, condition_type):
    """
    Calculate treatment success based on user's medical skill and item effectiveness.
    
    Args:
        item: Medical item being used
        user: Character using the item
        target: Character being treated
        condition_type: Type of condition being treated
        
    Returns:
        dict: Contains roll, medical_skill, total, difficulty, success_level
    """
    import random
    
    # Get user's medical skill (based on Intellect)
    user_intellect = getattr(user, 'intellect', 1)
    medical_skill = user_intellect * 2  # Convert intellect to medical skill
    
    # Get item effectiveness for this condition
    effectiveness = get_effectiveness(item, condition_type)
    
    # Calculate difficulty (higher effectiveness = easier treatment)
    base_difficulty = 15
    difficulty = base_difficulty - effectiveness
    
    # Roll dice (3d6)
    roll = sum(random.randint(1, 6) for _ in range(3))
    total = roll + medical_skill
    
    # Determine success level
    if total >= difficulty + 5:
        success_level = "success"
    elif total >= difficulty:
        success_level = "partial_success"
    else:
        success_level = "failure"
        
    return {
        "roll": roll,
        "medical_skill": medical_skill,
        "total": total,
        "difficulty": difficulty,
        "success_level": success_level
    }


def apply_medical_effects(item, user, target, **kwargs):
    """
    Apply the medical item's effects to the target.
    
    This handles the core medical treatment logic.
    """
    medical_type = get_medical_type(item)
    
    if not hasattr(target, 'medical_state'):
        return "Target has no medical state to treat."
    
    medical_state = target.medical_state
    
    # Basic effect application based on medical type
    if medical_type == "blood_restoration":
        # Restore blood volume (using blood_level attribute)
        old_level = medical_state.blood_level
        medical_state.blood_level = min(100.0, old_level + 25.0)
        
        # Reduce bleeding (check for minor_bleeding condition type)
        bleeding_conditions = [c for c in medical_state.conditions 
                             if hasattr(c, 'condition_type') and c.condition_type == "minor_bleeding"]
        for condition in bleeding_conditions[:2]:  # Reduce up to 2 bleeding conditions
            condition.severity = max(0, condition.severity - 3)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return f"Blood transfusion successful! Blood level increased from {old_level:.1f} to {medical_state.blood_level:.1f}."
        
    elif medical_type == "pain_relief":
        # Reduce pain conditions
        pain_conditions = [c for c in medical_state.conditions 
                         if hasattr(c, 'condition_type') and c.condition_type == "pain"]
        for condition in pain_conditions[:3]:  # Reduce multiple pain sources
            condition.severity = max(0, condition.severity - 2)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Painkiller administered. Pain significantly reduced."
        
    elif medical_type == "wound_care":
        # Bandaging effects
        bleeding_conditions = [c for c in medical_state.conditions 
                             if hasattr(c, 'condition_type') and c.condition_type == "minor_bleeding"]
        for condition in bleeding_conditions[:1]:  # Stop one source of bleeding
            condition.severity = max(0, condition.severity - 2)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Wounds properly bandaged. Bleeding controlled."
        
    elif medical_type == "fracture_treatment":
        # Splint effects
        fracture_conditions = [c for c in medical_state.conditions 
                             if hasattr(c, 'condition_type') and c.condition_type == "fracture"]
        for condition in fracture_conditions[:1]:  # Stabilize one fracture
            condition.severity = max(0, condition.severity - 4)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Fracture stabilized with splint. Mobility partially restored."
        
    elif medical_type == "surgical_treatment":
        # Surgical intervention
        organ_conditions = [c for c in medical_state.conditions 
                          if hasattr(c, 'condition_type') and c.condition_type == "organ_damage"]
        for condition in organ_conditions[:1]:  # Repair one organ
            condition.severity = max(0, condition.severity - 5)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Surgical procedure completed. Internal injuries treated."
    
    elif medical_type == "healing_acceleration":
        # Stimpak effects - general healing boost
        all_conditions = medical_state.conditions[:]
        healed_count = 0
        for condition in all_conditions[:3]:  # Heal up to 3 conditions
            condition.severity = max(0, condition.severity - 1)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
                healed_count += 1
        
        return f"Stimpak administered. Rapid healing activated - {healed_count} conditions improved."
    
    elif medical_type == "antiseptic":
        # Infection prevention and wound cleaning
        infection_conditions = [c for c in medical_state.conditions 
                              if hasattr(c, 'condition_type') and c.condition_type == "infection"]
        for condition in infection_conditions[:2]:  # Clear multiple infections
            condition.severity = max(0, condition.severity - 3)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Antiseptic applied. Infections cleared and wounds sterilized."
    
    elif medical_type == "oxygen":
        # Oxygen therapy - improves consciousness and breathing
        medical_state.consciousness = min(100, medical_state.consciousness + 15)
        breathing_conditions = [c for c in medical_state.conditions 
                               if hasattr(c, 'condition_type') and c.condition_type in ["breathing_difficulty", "suffocation"]]
        for condition in breathing_conditions[:2]:
            condition.severity = max(0, condition.severity - 2)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Oxygen administered. Breathing improved and consciousness stabilized."
    
    elif medical_type == "anesthetic":
        # Anesthetic gas - reduces pain and consciousness
        medical_state.pain_level = max(0, medical_state.pain_level - 25)
        medical_state.consciousness = max(0, medical_state.consciousness - 10)
        
        return "Anesthetic inhaled. Pain reduced but consciousness lowered."
    
    elif medical_type == "inhaler":
        # Medical inhaler - targeted respiratory treatment
        breathing_conditions = [c for c in medical_state.conditions 
                               if hasattr(c, 'condition_type') and c.condition_type in ["breathing_difficulty", "lung_damage"]]
        for condition in breathing_conditions[:1]:
            condition.severity = max(0, condition.severity - 3)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Inhaler used. Respiratory function improved."
    
    elif medical_type == "gas":
        # Medical gas treatment - various effects
        medical_state.consciousness = min(100, medical_state.consciousness + 5)
        return "Medical gas inhaled. Minor therapeutic effects applied."
    
    elif medical_type == "vapor":
        # Vaporized medicine - fast absorption
        medical_state.pain_level = max(0, medical_state.pain_level - 10)
        medical_state.blood_level = min(100, medical_state.blood_level + 5)
        
        return "Vaporized medicine inhaled. Rapid absorption achieved."
    
    elif medical_type == "herb":
        # Medicinal herb - natural pain relief
        medical_state.pain_level = max(0, medical_state.pain_level - 15)
        stress_conditions = [c for c in medical_state.conditions 
                            if hasattr(c, 'condition_type') and c.condition_type in ["stress", "anxiety"]]
        for condition in stress_conditions[:1]:
            condition.severity = max(0, condition.severity - 2)
            if condition.severity <= 0:
                medical_state.conditions.remove(condition)
        
        return "Medicinal herb smoked. Natural pain relief and calming effects."
    
    elif medical_type == "cigarette":
        # Medicinal cigarette - mild therapeutic effects
        medical_state.pain_level = max(0, medical_state.pain_level - 8)
        return "Medicinal cigarette smoked. Mild pain relief achieved."
    
    elif medical_type in ["medicinal_plant", "dried_medicine"]:
        # Dried medicinal substances - concentrated effects
        medical_state.pain_level = max(0, medical_state.pain_level - 12)
        medical_state.consciousness = min(100, medical_state.consciousness + 3)
        
        return "Dried medicine smoked. Concentrated therapeutic effects applied."
    
    # Check for immediate revival after any medical treatment
    death_scripts = target.scripts.get("death_progression")
    if death_scripts:
        try:
            for script in death_scripts:
                if (script.is_active and 
                    hasattr(script, '_check_medical_revival_conditions')):
                    if script._check_medical_revival_conditions(target):
                        from evennia.comms.models import ChannelDB
                        splattercast = ChannelDB.objects.get_channel("Splattercast")
                        splattercast.msg(f"IMMEDIATE_REVIVAL_CHECK: {target.key} revival triggered by medical treatment")
                        script._handle_medical_revival()
                        break  # Revival handled, stop checking
        except Exception as e:
            # Don't let revival check errors break medical treatment
            try:
                from evennia.comms.models import ChannelDB
                splattercast = ChannelDB.objects.get_channel("Splattercast")
                splattercast.msg(f"REVIVAL_CHECK_ERROR: {target.key}: {e}")
            except:
                pass
    
    return f"Applied {medical_type.replace('_', ' ')} treatment."


def get_medical_item_info(item, viewer):
    """
    Get formatted information about a medical item.
    
    Returns a string with detailed medical item information.
    """
    if not is_medical_item(item):
        return f"{item.get_display_name(viewer)} is not a medical item."
    
    info = [
        f"|w{item.get_display_name(viewer).upper()}|n",
        "=" * 50
    ]
    
    # Basic info
    medical_type = get_medical_type(item)
    info.append(f"Type: {medical_type.replace('_', ' ').title()}")
    info.append(f"Description: {item.db.desc or 'No description.'}")
    
    # Usage info
    uses_left = item.attributes.get("uses_left", "∞")
    max_uses = item.attributes.get("max_uses", "∞")
    info.append(f"Uses remaining: {uses_left}/{max_uses}")
    
    # Requirements
    stat_req = get_stat_requirement(item)
    if stat_req > 0:
        info.append(f"Intellect requirement: {stat_req}")
    else:
        info.append("No skill requirements")
        
    # Effectiveness
    effectiveness = item.attributes.get("effectiveness", {})
    if effectiveness:
        info.append("Effectiveness ratings:")
        for condition, rating in effectiveness.items():
            info.append(f"  {condition.replace('_', ' ').title()}: {rating}/10")
            
    # Special properties
    if not can_be_used(item):
        info.append("|rThis item is empty or used up.|n")
        
    application_time = item.attributes.get("application_time", 1)
    if application_time > 1:
        info.append(f"Application time: {application_time} rounds")
        
    return "\n".join(info)


def get_medical_status_description(medical_state):
    """
    Get a descriptive medical status based on character's medical state.
    
    Args:
        medical_state: Character's medical state object
        
    Returns:
        tuple: (status_text, color_code) - medical status and appropriate color
    """
    if medical_state.is_dead():
        return ("DECEASED", "|r")
    
    if medical_state.is_unconscious():
        return ("UNCONSCIOUS", "|R")
    
    # Get vital signs
    blood_level = getattr(medical_state, 'blood_level', 100.0)
    pain_level = getattr(medical_state, 'pain_level', 0.0)
    consciousness = getattr(medical_state, 'consciousness', 1.0)
    condition_count = len(medical_state.conditions) if medical_state.conditions else 0
    
    # Check for critical conditions
    if blood_level < 30 or consciousness < 0.40:
        return ("CRITICAL", "|r")
    
    # Check for serious conditions  
    if blood_level < 60 or pain_level > 60 or consciousness < 0.70:
        return ("SERIOUS", "|y")
        
    # Check for stable with injuries
    if condition_count > 0:
        if blood_level < 80 or pain_level > 30:
            return ("INJURED", "|y")
        else:
            return ("STABLE", "|g")
    
    # Perfect health
    if blood_level >= 95 and pain_level <= 5 and consciousness >= 0.95:
        return ("OPTIMAL", "|g")
    
    # Good health with minor issues
    return ("HEALTHY", "|g")
