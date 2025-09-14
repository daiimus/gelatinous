# Health and Substance System Specification

## Implementation Status

### ✅ COMPLETED PHASES
**Medical Foundation Complete (Phases 1-2.5):**
- Complete anatomical damage system (15 body regions + 6 organs)
- Medical conditions with severity tracking (bleeding, fractures, pain, etc.)
- Vital signs calculation (consciousness, blood level, pain level)
- Death/unconsciousness determination based on organ failure

**Medical Tools & Consumption Complete:**
- 7 medical item prototypes using Evennia's attribute-based system
- Natural language consumption commands (`inject`, `apply`, `bandage`, `eat`, `drink`, `inhale`, `smoke`)
- Medical inventory management commands (`medlist`, `mediteminfo`, `refillmed`)
- Skill-based treatment success using G.R.I.M. stats (Intellect-based medical skill)

**Evennia Integration Complete:**
- Proper attribute-based medical items (no custom typeclass required)
- Integration with built-in `spawn` command
- Medical system integrated with character `take_damage()` and combat
- Persistent medical state storage and retrieval

**Combat-Medical Integration Complete (December 2024):**
- ✅ Combat handler now uses weapon-specific damage types (bullet, cut, stab, blunt, laceration, burn)
- ✅ All weapon prototypes have damage_type attributes for medical integration
- ✅ All apply_damage() calls use proper 4-parameter signature (character, damage, location, injury_type)
- ✅ Fixed location mapping - combat damage to "chest" properly affects heart/lung organs
- ✅ Admin heal command fixed for medical condition list structure
- ✅ Destroyed organ protection - prevents damage to 0 HP organs
- ✅ Limb loss detection when all organs in body part destroyed
- ✅ **Individual bone anatomy system** - hospital-grade anatomical accuracy
- ✅ **Organ naming consistency** - eliminated "unknown" container issues
- ✅ **Enhanced medinfo diagnostics** - comprehensive medical status reporting
- ✅ **Medical system migration tools** - administrative commands for mass updates
- ✅ **Two-stage precision targeting system** - success margin + skill-based organ targeting
- ✅ **Single organ damage model** - focused wounds replace damage spreading

**Pure Medical System Complete (December 2024):**
- ✅ **Legacy HP completely eliminated** - no backwards compatibility layer needed
- ✅ **100% medical-based health** - death/unconsciousness based purely on organ function
- ✅ **No HP attributes** - character health entirely managed by medical system
- ✅ **Simplified architecture** - single system for all health management

### 🔄 CURRENT STATE: DEATH CURTAIN INTEGRATION & FORENSIC SYSTEM
The medical system now features **comprehensive death processing and persistent state visualization**:
- **Death curtain protection** with no personal medical messages sent to deceased characters
- **Persistent placement descriptions** providing visual indicators for unconscious/dead states without scrolling
- **Enhanced observer messaging** with atmospheric blood descriptions for deceased characters
- **Race condition elimination** through centralized death processing and delayed attack validation
- **Integrated infection messaging** with consolidated medical system using consistent red coloring
- **BloodPool forensic evidence** with aging and room description integration
- **Unified cleaning system** supporting both graffiti and blood evidence removal

### � UNIFIED MEDICAL MESSAGING SYSTEM (September 2025)
**Consolidated Message Architecture:**
- **Single medical message per tick** instead of separate bleeding/pain messages
- **Combined severity assessment** showing both bleeding and pain status
- **Consistent |R bright red coloring** for all medical-related text
- **Smart message timing** prevents message spam while maintaining medical urgency

**Message Consolidation Logic:**
```python
def _send_medical_messages(self):
    """Send consolidated medical status message combining bleeding and pain"""
    bleeding_messages = []
    total_pain = 0
    
    # Collect all bleeding conditions
    for condition in self.obj.medical_state.conditions:
        if condition.condition_type == "bleeding":
            bleeding_messages.append(condition.get_description())
        elif condition.condition_type == "pain":
            total_pain += condition.severity
    
    # Create unified message
    if bleeding_messages or total_pain > 0:
        combined_msg = "|RYou are "
        
        if bleeding_messages:
            combined_msg += ", ".join(bleeding_messages)
            if total_pain > 0:
                combined_msg += " and experiencing "
        
        if total_pain > 0:
            pain_desc = self._get_pain_description(total_pain)
            combined_msg += f"{pain_desc}"
        
        combined_msg += ".|n"
        self.obj.msg(combined_msg)
```

**Benefits:**
- **Reduced message spam** - One message instead of multiple per tick
- **Better player experience** - Clear, consolidated medical status
- **Consistent formatting** - All medical text uses same color scheme
- **Scalable system** - Easy to add new medical conditions to unified message

### 🏠 BLOOD POOL ROOM INTEGRATION SYSTEM (September 2025)
**Forensic Evidence Integration (PROOF-OF-CONCEPT):**
- **BloodPool objects integrate into room descriptions** alongside GraffitiObject for atmospheric forensic scenes
- **Graffiti-style evidence system** with incident tracking and aging mechanics
- **Room description enhancement** showing blood stains as part of environment rather than object listings
- **Forensic timeline tracking** with creation timestamps and deterioration over time

> **⚠️ IMPLEMENTATION NOTE**: Current forensic system is a **proof-of-concept only**. Blood evidence appears automatically in room descriptions via the `look` command. A proper player-facing forensic system would require dedicated investigation commands (`examine evidence`, `analyze bloodstain`, `forensic scan`, etc.) and skill-based discovery mechanics. The current integration is primarily for atmospheric effect and technical foundation.

**Integration Architecture:**
```python
# Room Integration System
def get_integrated_objects_content(self, looker):
    """Include BloodPool objects in room description integration"""
    integrated_objects = []
    
    for obj in self.contents:
        if obj.tags.has("graffiti", category="item_type"):
            integrated_objects.append(obj)
        elif obj.tags.has("blood_pool", category="item_type"):  # NEW
            integrated_objects.append(obj)
    
    return integrated_objects

# BloodPool Integration Description
def integration_desc(self):
    """Room description integration for blood stains"""
    age_hours = (time.time() - self.db.created_at) / 3600
    
    if age_hours < 1:
        return f"|R{self.db.description}|n"  # Fresh blood
    elif age_hours < 24:
        return f"|rDried {self.db.description.lower()}|n"  # Dried blood
    else:
        return f"|xDark stains mark where {self.db.description.lower()} once was|n"  # Old stains
```

**Forensic Features (Proof-of-Concept):**
- **Incident tracking** - Each blood pool tracks creation timestamp and source incident
- **Natural aging** - Blood evidence changes appearance over time (fresh → dried → stained)
- **Room atmosphere** - Blood stains become part of room description for immersive crime scenes
- **Evidence management** - Blood pools can be cleaned with spray command like graffiti

> **🔮 FUTURE FORENSIC SYSTEM**: A complete forensic investigation system would include:
> - Dedicated investigation commands (`examine bloodstain`, `analyze evidence`, `forensic scan`)
> - Skill-based evidence discovery (hidden evidence only visible to skilled investigators)
> - Evidence collection and laboratory analysis mechanics
> - DNA/blood type identification systems
> - Crime scene reconstruction tools
> - Time-of-death estimation based on evidence age
> - The current system provides the foundational data structure for these advanced features

### 🧽 ENHANCED SPRAY COMMAND SYSTEM (September 2025)
**Unified Evidence Cleaning:**
- **Dual-purpose cleaning** - Single spray command handles both graffiti and blood evidence
- **Context-appropriate messaging** - Different messages based on what's being cleaned
- **Smart detection** - Automatically identifies and cleans appropriate evidence types
- **Realistic solvent mechanics** - Spray removes both paint and biological evidence

**Enhanced Cleaning Logic:**
```python
def func(self):
    """Enhanced spray command with blood pool cleaning"""
    location = self.caller.location
    graffiti_objects = [obj for obj in location.contents 
                       if obj.tags.has("graffiti", category="item_type")]
    blood_pools = [obj for obj in location.contents 
                   if obj.tags.has("blood_pool", category="item_type")]
    
    if not graffiti_objects and not blood_pools:
        self.caller.msg("There's nothing here that needs cleaning.")
        return
    
    # Context-appropriate cleaning messages
    if graffiti_objects and blood_pools:
        self.caller.msg("You spray solvent over the colors and stains, watching them dissolve and run off.")
    elif graffiti_objects:
        self.caller.msg("You spray solvent over the colors, watching them dissolve and run off.")
    elif blood_pools:
        self.caller.msg("You spray solvent over the stains, watching them dissolve and wash away.")
    
    # Clean all evidence
    for obj in graffiti_objects + blood_pools:
        obj.delete()
```

**Cleaning Features:**
- **Comprehensive evidence removal** - Cleans both graffiti and blood in single action
- **Realistic messaging** - References "colors" for graffiti, "stains" for blood
- **Combined scenarios** - Smart messaging when both evidence types present
- **Consistent mechanics** - Same solvent works on both paint and biological evidence

### 💀 CENTRALIZED DEATH ANALYSIS SYSTEM (September 2025)
**Consistent Death Reporting:**
- **Centralized death analysis** in Character.at_death() method ensures consistent reporting
- **Debug output standardization** - All death scenarios now trigger Splattercast debug analysis
- **Medical integration** - Death analysis includes medical condition information
- **Combat integration** - Removed duplicate death analysis from combat handler

**Death Analysis Architecture:**
```python
def at_death(self):
    """Centralized death handling with consistent analysis"""
    # Standard death processing
    self.msg("|rYou have died.|n")
    
    # Centralized death analysis for all scenarios
    self._perform_death_analysis()
    
    # Continue with death processing
    super().at_death()

def _perform_death_analysis(self):
    """Consistent death analysis across all death scenarios"""
    from world.combat.utils import perform_death_analysis
    perform_death_analysis(self, "medical system")
```

**Analysis Consistency:**
- **All death scenarios covered** - Combat deaths, medical deaths, other causes
- **Unified debug output** - Consistent format for all death analysis
- **Medical condition reporting** - Death analysis includes current medical state
- **Elimination of gaps** - No more inconsistent death analysis between different systems
**Individual Bone Structure:**
- **Arms:** `left/right_humerus` (main arm bones) → 40% manipulation each
- **Hands:** `left/right_metacarpals` (hand bones) → 20% manipulation each  
- **Thighs:** `left/right_femur` (thigh bones) → 40% movement each
- **Shins:** `left/right_tibia` (shin bones) → 40% movement each
- **Feet:** `left/right_metatarsals` (foot bones) → 10% movement each

**Medical Benefits:**
- Realistic fractures (can break humerus without affecting other bones)
- Proper orthopedic injury patterns (blunt trauma to leg can fracture femur)
- Anatomically accurate damage distribution
- Enhanced surgical/treatment targeting
- One bone per body location for clean display

### 🏗️ MEDICAL SYSTEM ARCHITECTURE
**Organ Classification System:**
- **Individual Organs** (vital/complex): `brain`, `heart`, `liver`, `left_eye`, etc.
- **Individual Bones** (structural): `left_humerus`, `left_femur`, `left_tibia`, etc.
- **Container Hierarchy**: Organs exist within body location containers (`head`, `chest`, `left_arm`, etc.)

**Critical Integration Points:**
- `ORGANS` constants define available organs with their containers and properties
- `BODY_CAPACITIES` must reference organs that exist in `ORGANS` 
- **Auto-creation Gap**: `get_organ()` creates undefined organs with `container="unknown"`
- **Solution**: All capacity calculations use properly defined organ names

**Capacity Calculation Flow:**
1. Medical state initialized with organs from `ORGANS.keys()`
2. Body capacity calculation references `BODY_CAPACITIES[capacity]["organs"]`
3. Each referenced organ must exist in `ORGANS` or gets auto-created with "unknown" container
4. Bone-specific contributions (femur_contribution, humerus_contribution) provide balanced capacity totals

**Enhanced Medical Commands:**
- `medinfo [target] [organs|conditions|capacities|summary]` - Comprehensive medical diagnostics
- `@resetmedical <character>` - Reset medical states after system updates
- `@medaudit [details]` - Audit medical system health across all characters

### 🔧 MEDICAL SYSTEM MIGRATION TOOLS
**Administrative Commands (Builder+):**
- `@resetmedical confirm all` - Mass reset all character medical states
- `@resetmedical <character>` - Reset individual character medical state
- `@medaudit` - Quick overview of medical system health across game
- `@medaudit details` - Detailed character-by-character medical state analysis

**Migration Workflow:**
1. `@medaudit` - Assess current medical state distribution
2. `@resetmedical confirm all` - Clean slate migration (recommended)
3. Characters automatically receive current medical structure on next access
4. `@medaudit` - Verify successful migration to new structure

**Use Cases:**
- Medical system updates (new organs, changed mechanics)
- Server maintenance and cleanup
- Development testing and debugging
- Version migration between game updates

### 🎯 NEXT PRIORITIES: ENHANCED MEDICAL MECHANICS
**Phase 2.5 - Complete Consumption System (✅ COMPLETED September 2024):**
- ✅ Complete consumption commands: `inhale/smoke` for inhalers, gases, medicinal herbs
- ✅ Natural language consumption method system complete

**Phase 2.6 - Ticker-Based Medical Conditions (✅ COMPLETED December 2024):**
- ✅ Dynamic medical conditions with time-based progression using Evennia ticker system
- ✅ Multi-speed ticker system: Combat (6s), severe bleeding (12s), medical (60s)
- ✅ BleedingCondition with natural clotting, BurningCondition with spreading, AcidCondition with equipment damage
- ✅ Automatic condition creation integrated with damage system
- ✅ Synchronized effects and messaging to prevent mysterious deaths

**Phase 2.7 - Unified Medical Messaging & Forensic Evidence (✅ COMPLETED September 2025):**
- ✅ **Consolidated medical messaging system** - Single combined message per tick instead of separate bleeding/pain spam
- ✅ **Blood pool room integration** - BloodPool objects properly integrate into room descriptions like graffiti
- ✅ **Enhanced spray command** - Unified cleaning system for both graffiti and blood evidence with context-appropriate messaging
- ✅ **Death analysis consistency** - Centralized death reporting via Character.at_death() for all death scenarios
- ✅ **Standardized medical color coding** - Consistent |R bright red coloring for all medical-related messages
- ✅ **Forensic evidence management** - Blood pools age and deteriorate over time, creating realistic crime scene evolution

**Phase 2.8 - Death Curtain Integration & Race Condition Fixes (✅ COMPLETED September 2025):**
- ✅ **Placement description system** - Persistent visual indicators for unconscious ("unconscious and motionless.") and death ("lying motionless and deceased.") states  
- ✅ **Death curtain protection** - Medical messaging respects death curtain experience by not sending personal messages to deceased characters
- ✅ **Enhanced observer messaging** - Special bleeding descriptions for deceased characters ("Blood flows freely from [name]'s lifeless body, forming a growing pool of crimson.")
- ✅ **Automated placement cleanup** - Placement descriptions automatically cleared on consciousness recovery and manual healing
- ✅ **Death processing race condition fixes** - Centralized death processing with proper flag timing prevents duplicate death curtains
- ✅ **Delayed attack validation** - Combat system now validates attacker/target death status before executing delayed attacks
- ✅ **Medical/combat coordination** - Elimination of redundant death handling code, single source of truth through Character.at_death()
- ✅ **Infection message integration** - Infection conditions now part of consolidated medical messaging system with consistent |r red coloring

**Death Processing Architecture:**
```python
def at_death(self):
    """Centralized death processing with race condition protection"""
    # Prevent duplicate processing with immediate flag setting
    if hasattr(self, 'ndb') and getattr(self.ndb, 'death_processed', False):
        return
    self.ndb.death_processed = True
    
    # Clear unconsciousness state since death supersedes it
    if getattr(self.ndb, 'unconsciousness_processed', False):
        self.ndb.unconsciousness_processed = False
    
    # Set death placement description for persistent visual indication
    self.override_place = "lying motionless and deceased."
    
    # Always show death analysis and start death curtain
    self._show_death_analysis()
    show_death_curtain(self)
```

**Medical Messaging for Deceased Characters:**
```python
def _send_medical_messages(self, bleeding_severity, pain_severity, infection_severity=0):
    """Enhanced messaging with death curtain protection"""
    # Check if character is dead - don't send personal messages
    is_dead = self.obj.medical_state and self.obj.medical_state.is_dead()
    
    if is_dead:
        # Special observer messages for deceased characters
        if bleeding_severity > 12:
            room_msg = f"Blood flows freely from {self.obj.key}'s lifeless body, forming a growing pool of crimson."
            self.obj.location.msg_contents(room_msg, exclude=self.obj)
    else:
        # Normal personal + observer messages for living characters
        self.obj.msg(personal_medical_message)
        self.obj.location.msg_contents(observer_message, exclude=self.obj)
```

**Combat Race Condition Fixes:**
```python
def _process_delayed_attack(self, attacker, target, attacker_entry, combatants_list):
    """Enhanced delayed attack validation with death checks"""
    # Check if attacker is dead - dead characters can't attack
    if attacker.is_dead():
        splattercast.msg(f"DELAYED_ATTACK: {attacker.key} has died, attack cancelled.")
        return
        
    # Check if target is dead - no point attacking the dead  
    if target.is_dead():
        splattercast.msg(f"DELAYED_ATTACK: {target.key} has died, {attacker.key}'s attack cancelled.")
        return
    
    # Proceed with attack processing...
```

**Phase 3 - Advanced Features (Future Development):**

**Phase 3.1 - Comprehensive Forensic Investigation System (🔮 FUTURE):**
- **Dedicated Investigation Commands**: `examine evidence`, `analyze bloodstain`, `forensic scan`, `collect sample`
- **Skill-Based Evidence Discovery**: Hidden evidence only visible to characters with investigation skills
- **Evidence Collection & Analysis**: Laboratory mechanics for DNA/blood type identification
- **Crime Scene Reconstruction**: Timeline analysis and incident recreation tools
- **Advanced Evidence Types**: Fingerprints, DNA traces, ballistic evidence, chemical residues
- **Investigation Equipment**: Forensic kits, evidence bags, portable labs, scanning devices
- **Evidence Chain of Custody**: Proper evidence handling and legal admissibility mechanics
- **Time-Based Degradation**: Evidence quality decreases over time, affecting analysis accuracy

**Phase 3.2 - Death Progression & Organ Harvesting (🔮 FUTURE):**
- Progressive organ failure system after character death
- Realistic organ deterioration timelines (brain dies in 3 rounds, heart in 8, etc.)
- Organ harvesting commands (`harvest <organ> from <corpse>`)
- Corpse examination system (`examine corpse <target>`, organ viability reports)
- Harvested organ inventory management (`viability`, `organs`)
- Foundation for cybernetics integration (organ replacement demand)

**Phase 3.3 - Cybernetics & Prosthetics (🔮 FUTURE):**
- Limb replacement mechanics (prosthetics, cybernetics) 
- Advanced surgical procedures and medical equipment
- Disease and infection progression systems
- Drug addiction and dependency mechanics
- Complex organ transplant procedures

## Overview

The Gelatinous Monster health and substance system creates tactical medical gameplay that emphasizes realistic injury consequences and meaningful substance interaction choices through detailed anatomical damage modeling, field medical tools, and comprehensive consumption methods.

## Design Philosophy

### Core Principles
- **Anatomical Realism**: Injuries affect specific body parts and organs with logical consequences
- **Tactical Medicine**: Medical tools have specific purposes and limited effectiveness  
- **Consequence-Driven**: Injuries create meaningful gameplay effects, not just HP reduction
- **Resource Management**: Medical supplies are valuable and consumable
- **Skill-Based**: Medical treatment success depends on character abilities

### Integration with Existing Systems
- **Longdesc System**: Medical conditions visible in character descriptions
- **Combat System**: Damage targeting specific anatomical locations
- **G.R.I.M. Stats**: Medical skill primarily based on Intellect (3/4 weight), with Motorics for surgical precision (1/4 weight)
- **Clothing System**: Armor/clothing affects injury locations and severity

## ANATOMICAL SYSTEM ARCHITECTURE

### Dynamic Hit Location Targeting
The medical system implements **dynamic anatomy** where each character's hit-targetable locations are determined by their individual body structure, not static tables.

#### **Three-Layer Architecture**
```python
# Layer 1: Longdesc Locations (Character Description System)
character.longdesc = {
    "head": "scarred from battle",     # Exists with description
    "left_arm": None,                  # Exists but no description set  
    "chest": "muscular torso",         # Exists with description
    # "right_leg" not in dict = location doesn't exist on this character
}

# Layer 2: Organ Container Mapping (Medical Constants)
ORGANS = {
    "brain": {"container": "head", "max_hp": 10, "vital": True},
    "left_humerus": {"container": "left_arm", "max_hp": 25, "vital": False},
    "heart": {"container": "chest", "max_hp": 15, "vital": True},
}

# Layer 3: Character Medical State (Runtime Organ Tracking)
character.medical_state.organs = {
    "brain": Organ(current_hp=10, max_hp=10),        # Functional
    "left_humerus": Organ(current_hp=0, max_hp=25),  # Destroyed but present
    "heart": Organ(current_hp=8, max_hp=15),         # Damaged but functional
}
```

#### **Hit Location Resolution Logic**
```python
def determine_valid_hit_locations(character):
    """
    Dynamic hit location discovery based on character's actual anatomy.
    
    Returns locations that:
    1. Exist in character's longdesc system (even if description is None)  
    2. Contain at least one functional (non-destroyed) organ
    """
    valid_locations = []
    
    for location_name in character.longdesc.keys():  # Layer 1: Available locations
        organs_in_location = get_organ_by_body_location(location_name)  # Layer 2: Organ mapping
        
        # Layer 3: Check for functional organs
        has_functional_organs = any(
            not character.medical_state.organs[organ_name].is_destroyed()
            for organ_name in organs_in_location
            if organ_name in character.medical_state.organs
        )
        
        if has_functional_organs:
            valid_locations.append(location_name)
    
    return valid_locations
```

#### **Key Architectural Benefits**
- **Species Flexibility**: Spider characters automatically get different hit locations based on their longdesc anatomy
- **Injury Progression**: Lost limbs automatically become invalid targets (no functional organs)
- **Prosthetic Integration**: New artificial limbs add new hit locations with their own organ mappings
- **Medical History**: Destroyed organs remain tracked (HP=0) for healing/replacement possibilities
- **Mr. Hands Compatibility**: Custom anatomy modifications work seamlessly with existing hit targeting

#### **Organ Lifecycle States**
```python
# Organs exist in one of these states:
ORGAN_FUNCTIONAL = "current_hp > 0"     # Can be targeted and damaged
ORGAN_DESTROYED = "current_hp = 0"      # Cannot be damaged further, doesn't contribute to capacities
ORGAN_MISSING = "not in medical_state"  # Removed/never existed (rare, for extreme modifications)

# Hit targeting only considers locations with FUNCTIONAL organs
# Destroyed organs remain in medical state for potential healing/replacement
```

### Character Anatomy Customization
Characters can have varied anatomy through:
1. **Species Templates**: Different creature types get different default organs/locations
2. **Injury Loss**: Destroyed organs stop contributing to hit targeting for that location
3. **Prosthetic Addition**: New locations and organs can be dynamically added
4. **Mr. Hands Integration**: Custom body modifications extend the longdesc + organ system

## CONFIGURATION CONSTANTS

*All numerical values use constants for easy balance modification during implementation:*

```python
# Death/Unconsciousness Thresholds  
BLOOD_LOSS_DEATH_THRESHOLD = 85        # Placeholder - needs balancing
CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD = 30  # Placeholder - needs balancing

# Hit Weight Distribution (combat handler integration)
HIT_WEIGHT_VERY_RARE = 2              # Brain, spinal cord
HIT_WEIGHT_RARE = 8                   # Eyes, ears, jaw, neck  
HIT_WEIGHT_UNCOMMON = 15              # Heart, lungs, organs, hands
HIT_WEIGHT_COMMON = 25                # Arms, legs, major limbs

# Pain/Consciousness Modifiers
PAIN_UNCONSCIOUS_THRESHOLD = 80       # High pain causes unconsciousness
PAIN_CONSCIOUSNESS_MODIFIER = 0.5     # How much pain affects consciousness

# Treatment Success Modifiers  
BASE_TREATMENT_SUCCESS = 50           # Base % before stat modifiers
STAT_MODIFIER_SCALING = 5             # Points per stat level
TOOL_EFFECTIVENESS_SCALING = 10       # Effectiveness points per tool quality

# Medical Resource Constants
BANDAGE_EFFECTIVENESS = 15            # HP healed per bandage
SURGERY_BASE_DIFFICULTY = 75          # Base difficulty for surgery
INFECTION_CHANCE_BASE = 10            # Base infection chance %

# Medical Treatment Success Constants (Added for Phase 2)
MEDICAL_TREATMENT_BASE_DIFFICULTY = 12  # Base d20 target for medical treatments
PARTIAL_SUCCESS_MARGIN = 3            # How close to success counts as partial
TOOL_EFFECTIVENESS_MODIFIERS = {      # Modifier table - tool appropriateness
    # Example: {"blood_bag": {"bleeding": -2, "fracture": +5}, ...}
    # Negative = easier, Positive = harder
    "placeholder": "to_be_defined_in_phase_2"
}
```

*NOTE: All values are speculative/unbalanced - constants make modification easy*

## Current Health System Implementation

### ✅ Implemented Medical System
```python
# MEDICAL STATE SYSTEM (IMPLEMENTED)
class MedicalState:
    """Complete medical state tracking"""
    def __init__(self, character=None):
        self.organs = {}              # Organ health tracking
        self.conditions = []          # Medical conditions (bleeding, fractures, etc.)
        self.blood_level = 100.0      # Current blood percentage
        self.pain_level = 0.0         # Pain accumulation
        self.consciousness = 100.0    # Consciousness level
    
    def is_dead(self):
        """Multi-factor death determination"""
        # Death from vital organ failure
        if self.calculate_body_capacity("blood_pumping") <= 0.0:  # Heart
            return True
        if self.calculate_body_capacity("breathing") <= 0.0:      # Lungs
            return True
        if self.calculate_body_capacity("digestion") <= 0.0:      # Liver
            return True
        # Death from catastrophic blood loss (85%+ loss)
        if self.blood_level <= 15.0:
            return True
        return False
    
    def is_unconscious(self):
        """Multi-factor unconsciousness"""
        consciousness_level = self.calculate_body_capacity("consciousness")
        return consciousness_level < 0.30  # 30% threshold

# CHARACTER INTEGRATION (IMPLEMENTED)
class Character:
    @property
    def medical_state(self):
        """Access persistent medical state"""
        
    def take_damage(self, amount, location="chest", injury_type="generic"):
        """Pure medical system damage - the only health system"""
        from world.medical.utils import apply_anatomical_damage
        damage_results = apply_anatomical_damage(self, amount, location, injury_type)
        
        # Death/unconsciousness determined purely by medical state
        return self.medical_state.is_dead()

# MEDICAL TOOLS SYSTEM (IMPLEMENTED)
# Uses Evennia's attribute-based approach with regular Item typeclass
# Example prototype:
BLOOD_BAG = {
    "key": "blood bag",
    "typeclass": "typeclasses.items.Item",  # Regular Item, not custom
    "tags": [("medical_item", "item_type")],
    "attrs": [
        ("medical_type", "blood_restoration"),
        ("uses_left", 1),
        ("effectiveness", {"bleeding": 9, "blood_loss": 10}),
    ]
}

# Accessed via utility functions:
is_medical_item(item)           # Check if item is medical
can_be_used(item)              # Check if item has uses left  
get_medical_type(item)         # Get medical type
apply_medical_effects(...)     # Apply treatment effects
```

### Anatomical Foundation (Dynamic Integration)
```python
# UNIFIED ANATOMY SYSTEM DESIGN:
# 1. Character typeclasses define both longdesc anatomy AND organ mappings
# 2. Medical system adapts to whatever anatomy exists on character
# 3. Creature-type templates provide standard organ-to-location mappings
# 4. NO FALLBACK RULES - all organ-to-location mappings must be explicit per typeclass
# 5. UNIVERSAL INJURY TYPES - fractures, bleeding, infections work on any anatomy

# CROSS-SPECIES FRACTURE COMPATIBILITY:
# - Human: left_arm, right_arm, left_leg, right_leg can be fractured
# - Tentacle Monster: tentacle_1, tentacle_2, tentacle_3, tentacle_4 can be fractured  
# - Spider Creature: leg_1, leg_2, leg_3, leg_4, leg_5, leg_6, leg_7, leg_8 can be fractured
# Same splint mechanics work universally across all appendage types

# Example: Human character (default)
DEFAULT_LONGDESC_LOCATIONS = {
    "head": None, "face": None, "left_eye": None, "right_eye": None,
    "chest": None, "back": None, "abdomen": None, "groin": None,
    "left_arm": None, "right_arm": None, "left_hand": None, "right_hand": None,
    "left_thigh": None, "right_thigh": None, "left_shin": None, "right_shin": None,
    "left_foot": None, "right_foot": None
}

# Example: Tentacle monster character 
TENTACLE_MONSTER_LOCATIONS = {
    "core_mass": None, "feeding_maw": None, "sensory_cluster": None,
    "tentacle_1": None, "tentacle_2": None, "tentacle_3": None, "tentacle_4": None
}

# Organ mapping defined per character type via creature templates
```

## CORE MECHANICS CLARIFICATION

### Organ Damage System
- **Organs have HP**: Each organ has max_hp (see ORGANS definition above)  
- **Damage reduces HP**: Incoming damage reduces current HP from max_hp
- **Destruction at 0 HP**: When organ HP reaches 0, organ is destroyed/non-functional
- **Death conditions**: Destruction of vital organs (heart, both lungs, liver) = death
- **Paired organ logic**: Both kidneys/lungs destroyed = death, single destruction = reduced function

### Hit Distribution Formula  
*NOTE: Formula will be based on attack roll/success from combat handler*
```python
# Hit weight distribution (placeholder - needs combat handler integration)
HIT_WEIGHTS = {
    "very_rare": HIT_WEIGHT_VERY_RARE,      # Brain, spinal cord - use constants
    "rare": HIT_WEIGHT_RARE,                # Eyes, ears, jaw, neck
    "uncommon": HIT_WEIGHT_UNCOMMON,        # Heart, lungs, organs, hands
    "common": HIT_WEIGHT_COMMON             # Arms, legs, major limbs
}
```

### Death vs Unconsciousness vs Functionality
- **Blood loss kills**: Tracked separately, reaches fatal threshold = death
- **Blood pumping = 0**: Death (heart destroyed/stopped)
- **Consciousness**: Flag system (is_unconscious = True/False), not death
- **Functionality**: Reduced stats/capabilities, but character remains conscious

### Constants for Balance
*All numerical thresholds use constants for easy modification:*
- CONSCIOUSNESS_UNCONSCIOUS_THRESHOLD  
- BLOOD_LOSS_DEATH_THRESHOLD
- HIT_WEIGHT_* values
- PAIN_MODIFIER_*
- All treatment success rates and failure penalties

### Medical Conditions

#### Injury Types
```python
# NOTE: All injury complexity implemented as values - exact mechanics to be balanced during implementation
INJURY_TYPES = {
    "cut": {
        "pain_per_damage": "low",
        "bleed_rate": "moderate", 
        "infection_chance": "low",
        "scar_chance": "low",
        "healing_time": "moderate",
        "treatment_difficulty": "easy",
        "description": "Clean cuts from blades or sharp objects"
    },
    "burn": {
        "pain_per_damage": "high",
        "bleed_rate": "minimal",
        "infection_chance": "high", 
        "scar_chance": "high",
        "healing_time": "slow",
        "treatment_difficulty": "moderate",
        "permanent_damage_chance": "moderate",
        "description": "Fire, heat, or chemical burns"
    },
    "blunt": {
        "pain_per_damage": "moderate",
        "bleed_rate": "minimal",
        "fracture_chance": "moderate",
        "internal_damage_chance": "high",
        "healing_time": "slow",
        "treatment_difficulty": "easy",
        "description": "Crushing, impact, or bludgeoning damage"
    },
    "bullet": {
        "pain_per_damage": "moderate", 
        "bleed_rate": "severe",
        "penetration_chance": "high",
        "fragmentation_chance": "low",
        "infection_chance": "moderate",
        "healing_time": "slow",
        "treatment_difficulty": "hard",
        "description": "Projectile wounds from firearms"
    },
    "stab": {
        "pain_per_damage": "low",
        "bleed_rate": "severe",
        "organ_damage_chance": "high",
        "infection_chance": "moderate", 
        "healing_time": "moderate",
        "treatment_difficulty": "moderate",
        "description": "Deep puncture wounds from thrusting weapons"
    },
    "laceration": {
        "pain_per_damage": "high",
        "bleed_rate": "high",
        "infection_chance": "high",
        "scar_chance": "very_high", 
        "healing_time": "slow",
        "treatment_difficulty": "hard",
        "description": "Ragged tears from claws, shrapnel, or serrated weapons"
    },
    "frostbite": {
        "pain_per_damage": "very_high",
        "bleed_rate": "none",
        "infection_chance": "high",
        "permanent_damage_chance": "high",
        "healing_time": "very_slow",
        "treatment_difficulty": "hard", 
        "amputation_risk": "moderate",
        "description": "Cold damage causing tissue death"
    }
}
```

#### 🔧 Current Weapon Implementation Status
As of December 2024, all weapon prototypes have been updated with appropriate damage types:

```python
# IMPLEMENTED WEAPON DAMAGE TYPES:
WEAPON_DAMAGES = {
    # Firearms - high bleeding, hard to treat
    "bullet": ["pistol", "shotgun", "assault_rifle", "sniper_rifle", "heavy_machine_gun"],
    
    # Cutting weapons - moderate bleeding, easy to treat  
    "cut": ["knife", "machete", "sword", "katana", "claymore", "battle_axe", "small_axe"],
    
    # Stabbing weapons - severe bleeding, organ damage risk
    "stab": ["dagger", "spear", "straight_razor", "awl", "ice_pick"],
    
    # Blunt weapons - minimal bleeding, fracture risk
    "blunt": ["club", "hammer", "sledgehammer", "pipe_wrench", "baseball_bat", "crowbar"],
    
    # High-damage ragged weapons - severe bleeding and pain
    "laceration": ["chainsaw", "shuriken", "meat_hook", "rebar", "nailed_board"],
    
    # Chemical/fire weapons - high infection risk  
    "burn": ["spray_can", "solvent_can", "flamethrower"]
}

# Combat handler automatically maps weapon.db.damage_type to appropriate injury mechanics
# All apply_damage() calls throughout codebase use 4-parameter signature
```

#### Pain System
```python
# NOTE: Pain system uses descriptive thresholds - exact formulas to be balanced during implementation
PAIN_SYSTEM = {
    "calculation": {
        "base_formula": "sum(injury_severity * pain_per_damage_rating)",
        "creature_size_modifier": True,    # Large creatures have reduced pain sensitivity
        "pain_tolerance_modifier": True,   # Drug effects, traits, training modify pain
        "adrenaline_modifier": True        # Combat/stress can temporarily reduce pain
    },
    
    "pain_levels": {
        # Descriptive pain levels with gameplay effects
        "none": {
            "threshold": "0%", "mood_penalty": 0, "consciousness_penalty": "none",
            "description": "no discomfort", "gameplay_effects": []
        },
        "minor": {
            "threshold": "1-10%", "mood_penalty": "slight", "consciousness_penalty": "none", 
            "description": "a little discomfort", "gameplay_effects": []
        },
        "moderate": {
            "threshold": "10-25%", "mood_penalty": "noticeable", "consciousness_penalty": "minimal",
            "description": "distracting pain", "gameplay_effects": ["concentration_penalty"]
        },
        "severe": {
            "threshold": "25-50%", "mood_penalty": "significant", "consciousness_penalty": "moderate",
            "description": "intense pain", "gameplay_effects": ["action_penalties", "focus_loss"]
        },
        "extreme": {
            "threshold": "50-80%", "mood_penalty": "major", "consciousness_penalty": "severe", 
            "description": "excruciating agony", "gameplay_effects": ["severe_penalties", "periodic_stunning"]
        },
        "unbearable": {
            "threshold": "80%+", "mood_penalty": "overwhelming", "consciousness_penalty": "critical",
            "description": "mind-shattering torture", "gameplay_effects": ["unconsciousness_risk", "shock"]
        }
    },
    
    "consciousness_interaction": {
        # Consciousness is single value affected by multiple factors
        "pain_contribution": "moderate_to_severe",     # Pain reduces consciousness
        "blood_loss_contribution": "severe",           # Blood loss majorly reduces consciousness  
        "organ_damage_contribution": "varies_by_organ", # Brain damage = direct consciousness loss
        "cumulative_effects": True,                    # All factors stack
        "unconscious_threshold": "30% consciousness",
        "death_threshold": "0% consciousness"
    }
}
```

#### Blood System
```python
BLOOD_SYSTEM = {
    "blood_as_resource": {
        "tracked_like_pain": True,
        "max_blood": "100% (varies by creature size)",
        "current_blood": "percentage of maximum", 
        "blood_loss_per_round": "sum of all bleeding wounds",
        "consciousness_impact": "severe at <60% blood"
    },
    
    "blood_loss_effects": {
        "90-100%": {"status": "healthy", "consciousness_penalty": "none"},
        "70-90%": {"status": "light_blood_loss", "consciousness_penalty": "minimal"},
        "50-70%": {"status": "moderate_blood_loss", "consciousness_penalty": "moderate"},
        "30-50%": {"status": "severe_blood_loss", "consciousness_penalty": "major"},
        "10-30%": {"status": "critical_blood_loss", "consciousness_penalty": "severe"},
        "0-10%": {"status": "exsanguination", "consciousness_penalty": "unconscious"}
    }
}
```

#### Status Effects (Medical Conditions)
```python
MEDICAL_CONDITIONS = {
    "bleeding": {
        "description": "Contributes to blood loss per round - multiple wounds stack",
        "severity_levels": {
            "minor": {"blood_loss_per_round": "1%", "visible": "small bloodstains"},
            "moderate": {"blood_loss_per_round": "3%", "visible": "steady bleeding"}, 
            "severe": {"blood_loss_per_round": "8%", "visible": "heavy blood loss"},
            "arterial": {"blood_loss_per_round": "15%", "visible": "spurting blood"}
        },
        "stacking": "multiple_wounds_add_blood_loss",
        "treatments": {
            "basic_bandage": {"success_rate": "moderate", "requirements": ["bandage"], "stops": ["minor", "moderate"]},
            "surgical_kit": {"success_rate": "high", "requirements": ["surgical_kit", "medical_skill"], "stops": ["all_levels"]},
            "blood_bag": {"success_rate": "guaranteed", "requirements": ["blood_bag"], "restores": "blood_volume"}
        },
        "progression": "stable_until_treated"
    },
    
    "infection": {
        "description": "Develops over time from untreated wounds",
        "severity_levels": ["minor", "major", "systemic"],
        "treatments": ["basic_cleaning", "surgical_kit", "antibiotics"],
        "failure_consequences": "chronic_infection_permanent_pain"
    },
    
    "fracture": {
        "description": "Universal injury type - affects any appendage regardless of species",
        "effects": ["appendage_unusable", "constant_pain", "movement_impaired"],
        "treatments": ["splint", "surgical_kit"],
        "failure_consequences": "permanent_reduced_function_chronic_pain"
    }
}
```

## Field Medical Tools

### Medical Equipment

#### Blood Bag
```python
BLOOD_BAG = {
    "name": "Blood Bag",
    "uses": 1,
    "time_to_use": "3 rounds",
    "effects": {
        "restores_blood": "25% of maximum",
        "stops_bleeding": "minor_to_moderate",
        "reduces_shock": True
    },
    "stat_requirement": "intellect >= 2",  # Basic medical knowledge needed
    "success_formula": "(intellect * 0.75) + (motorics * 0.25)",
    "failure_consequences": "infection_risk_scar_tissue",
    "description": "Emergency blood transfusion kit"
}
```

#### Painkiller
```python
PAINKILLER = {
    "name": "Painkiller",
    "uses": 1,
    "time_to_use": "1 round",
    "effects": {
        "reduces_pain": "significant_temporary",
        "temporary_stat_boost": {"grit": +1},
        "duration": "10 rounds"
    },
    "side_effects": "dulled_awareness_after_effect",
    "stat_requirement": None,  # Anyone can inject
    "failure_consequences": "overdose_risk_addiction_chance",
    "description": "Military-grade analgesic injection"
}
```

#### Gauze/Bandages
```python
GAUZE = {
    "name": "Gauze Bandages",
    "uses": 3,  # Multiple applications
    "time_to_use": "2 rounds",
    "effects": {
        "stops_bleeding": "minor_to_moderate",
        "prevents_infection": "basic_protection",
        "stabilizes_wounds": True
    },
    "stat_requirement": "intellect >= 1",  # Basic first aid knowledge
    "success_formula": "(intellect * 0.75) + (motorics * 0.25)",
    "failure_consequences": "incomplete_bleeding_control_infection_risk",
    "description": "Sterile bandages and gauze pads for wound care"
}
```

#### Splint
```python
SPLINT = {
    "name": "Splint",
    "uses": 1,
    "time_to_use": "2 rounds", 
    "effects": {
        "stabilizes_fractures": True,
        "restores_partial_function": "50%_of_normal",
        "prevents_further_damage": True,
        "reduces_pain": "moderate"
    },
    "targets": "any_fractured_appendage",  # Universal - works on arms, legs, tentacles, wings, etc.
    "cross_species_examples": {
        "human": "left_arm, right_leg, left_hand",
        "tentacle_monster": "tentacle_1, tentacle_3, tentacle_7", 
        "spider": "leg_2, leg_5, leg_8",
        "winged_creature": "left_wing, right_wing"
    },
    "stat_requirement": "intellect >= 1",
    "success_formula": "(intellect * 0.75) + (motorics * 0.25)",
    "failure_consequences": "improper_healing_permanent_reduced_function",
    "description": "Universal immobilization device - adapts to any appendage type"
}
```

#### Surgical Kit
```python
SURGICAL_KIT = {
    "name": "Surgical Kit", 
    "uses": 3,  # Multiple procedures
    "time_to_use": "5 rounds",  # Lengthy procedure
    "effects": {
        "repairs_organs": True,
        "stops_internal_bleeding": True,
        "removes_foreign_objects": True,
        "restores_function": 0.8  # 80% restoration
    },
    "stat_requirement": "intellect >= 4",  # High stat needed
    "failure_effects": ["organ_damage", "massive_bleeding", "death"],
    "success_modifiers": {
        "sterile_environment": +2,
        "assistant_present": +1,
        "time_pressure": -3
    },
    "description": "Portable surgical suite with micro-instruments and nano-sutures"
}
```

## Consumption Method System

### Overview
The medical system serves as the foundation for a broader consumable substance system that encompasses both medical treatments and recreational substances. All consumable items utilize natural language commands that reflect realistic delivery methods.

### Core Philosophy
- **Realistic Delivery Methods**: Commands reflect how substances are actually consumed in reality
- **Universal System**: Medical items, drugs, and other consumables use the same underlying mechanics
- **Self-Administration & Third-Party**: Items can be used on oneself or administered to others
- **Natural Language**: Commands use familiar terminology (inject, apply, eat, drink, smoke, inhale, etc.)

### Consumption Commands

#### Primary Consumption Methods
```python
CONSUMPTION_METHODS = {
    # Injectable substances
    "inject": {
        "aliases": ["inject", "shot", "jab"],
        "self_syntax": "inject <item>",
        "other_syntax": "inject <item> <target>",
        "examples": ["inject painkiller", "inject stimpak Alice"],
        "time_required": "1-2 rounds",
        "stat_requirements": "varies by substance",
        "applicable_to": ["painkillers", "stimpaks", "adrenal boosters", "toxins", "vaccines"]
    },
    
    # Topical applications
    "apply": {
        "aliases": ["apply", "rub", "spread"],
        "self_syntax": "apply <item>",
        "other_syntax": "apply <item> to <target>",
        "examples": ["apply burn gel", "apply antiseptic to Bob's wound"],
        "time_required": "1-3 rounds",
        "stat_requirements": "basic motorics for precise application",
        "applicable_to": ["burn gel", "antiseptic", "healing salves", "contact toxins", "medicated patches"]
    },
    
    # Oral consumption - solids
    "eat": {
        "aliases": ["eat", "consume", "swallow"],
        "self_syntax": "eat <item>",
        "other_syntax": "feed <item> to <target>",
        "examples": ["eat ration bar", "feed medicine to Charlie"],
        "time_required": "1 round",
        "stat_requirements": None,
        "applicable_to": ["pills", "tablets", "food", "edible drugs", "emergency rations"]
    },
    
    # Oral consumption - liquids
    "drink": {
        "aliases": ["drink", "sip", "gulp"],
        "self_syntax": "drink <item>",
        "other_syntax": "give <item> to <target> to drink",
        "examples": ["drink medical brew", "give water to Dana"],
        "time_required": "1 round",
        "stat_requirements": None,
        "applicable_to": ["liquid medicines", "water", "alcohol", "liquid drugs", "nutritional drinks"]
    },
    
    # Inhalation methods
    "inhale": {
        "aliases": ["inhale", "huff", "breathe"],
        "self_syntax": "inhale <item>",
        "other_syntax": "help <target> inhale <item>",
        "examples": ["inhale oxygen", "inhale anesthetic gas"],
        "time_required": "1-2 rounds",
        "stat_requirements": "conscious target required",
        "applicable_to": ["inhalers", "oxygen tanks", "anesthetic gases", "vaporized drugs"]
    },
    
    # Smoking/burning consumption
    "smoke": {
        "aliases": ["smoke", "light", "burn"],
        "self_syntax": "smoke <item>",
        "other_syntax": "help <target> smoke <item>",
        "examples": ["smoke medicinal herb", "smoke pain-relief cigarette"],
        "time_required": "3-5 rounds",
        "stat_requirements": "fire source required",
        "applicable_to": ["medicinal herbs", "cigarettes", "pipes", "combustible drugs"]
    }
}
```

#### Special Consumption Cases
```python
SPECIAL_CONSUMPTION_METHODS = {
    # Suppository/rectal administration (boof)
    "boof": {
        "aliases": ["boof", "insert"],
        "self_syntax": "boof <item>",
        "other_syntax": "administer <item> to <target>",
        "examples": ["boof suppository", "administer rectal medication to patient"],
        "time_required": "2-3 rounds",
        "stat_requirements": "medical knowledge for third-party administration",
        "applicable_to": ["suppositories", "rectal medications", "emergency drugs"],
        "privacy_considerations": "requires consent for third-party administration"
    },
    
    # Combination methods
    "bandage": {
        "aliases": ["bandage", "wrap", "dress"],
        "self_syntax": "bandage <body_part> with <item>",
        "other_syntax": "bandage <target>'s <body_part> with <item>",
        "examples": ["bandage arm with gauze", "bandage Alice's leg with medicated bandage"],
        "time_required": "2-3 rounds",
        "stat_requirements": "basic first aid knowledge",
        "applicable_to": ["gauze", "bandages", "medicated wraps", "splints"]
    }
}
```

### Administration Mechanics

#### Self-Administration vs Third-Party
```python
def administer_substance(administrator, target, substance, method):
    """
    Universal substance administration system.
    Handles both self-administration and third-party scenarios.
    """
    is_self_admin = (administrator == target)
    
    # Base requirements
    base_requirements = substance.consumption_requirements
    method_modifiers = CONSUMPTION_METHODS[method]
    
    if is_self_admin:
        # Self-administration: simpler, faster, more private
        difficulty_modifier = 0
        time_modifier = 1.0
        consent_required = False
    else:
        # Third-party administration: more complex, requires consent/cooperation
        difficulty_modifier = +2  # Slightly harder
        time_modifier = 1.2       # Takes 20% longer
        consent_required = True
        
        # Check consciousness/cooperation of target
        if not target.conscious and method not in ["inject", "apply", "bandage"]:
            return "target_unconscious_method_inappropriate"
    
    # Calculate success based on administrator's stats
    admin_skill = calculate_medical_skill(administrator)
    success_chance = admin_skill + base_requirements + difficulty_modifier
    
    return execute_consumption(administrator, target, substance, method, success_chance)
```

#### Medical vs Recreational Substances
```python
SUBSTANCE_CATEGORIES = {
    "medical": {
        "priority": "healing",
        "side_effects": "minimal_therapeutic",
        "legal_status": "regulated_legal",
        "examples": ["painkillers", "antibiotics", "blood_bags", "burn_gel"]
    },
    "recreational": {
        "priority": "psychological_effect", 
        "side_effects": "varied_unpredictable",
        "legal_status": "varies_by_jurisdiction",
        "examples": ["alcohol", "stimulants", "hallucinogens", "depressants"]
    },
    "performance": {
        "priority": "stat_enhancement",
        "side_effects": "temporary_crash",
        "legal_status": "controlled_military",
        "examples": ["combat_stims", "focus_enhancers", "strength_boosters"]
    },
    "toxic": {
        "priority": "harm",
        "side_effects": "damage_death",
        "legal_status": "restricted_illegal",
        "examples": ["poisons", "nerve_agents", "corrosives"]
    }
}
```

### Command Integration Examples

#### Medical Scenarios
```
> inject painkiller
You inject the painkiller into your arm. The sharp pain in your chest begins to fade.

> apply burn gel to Alice
You carefully apply the cooling gel to Alice's burned arm. She winces but looks relieved.

> bandage Bob's leg with gauze  
You wrap Bob's wounded leg with sterile gauze, stemming the bleeding.
```

#### Cross-Category Usage
```
> drink whiskey
You take a swig of whiskey. The alcohol burns as it goes down, dulling the edge of your pain.

> smoke medicinal herb
You light the dried herb and inhale deeply. Your breathing becomes easier and the pain subsides.

> inhale stimpak vapor
You breathe in the aerosolized stimpak. Energy surges through your body as your wounds begin to close.
```

### Implementation Notes
- **Unified Backend**: All consumption methods use the same core mechanics with method-specific modifiers
- **Natural Language**: Commands reflect real-world familiarity with consumption methods
- **Scalability**: System supports easy addition of new substances and consumption methods
- **Medical Foundation**: Medical system provides the underlying health/condition framework for all substances

### Medical Tool Interactions

### Treatment Effectiveness (Simplified)
```python
# Simple tool appropriateness for conditions
TOOL_APPROPRIATENESS = {
    "bleeding": {
        "gauze": "highly_effective_for_minor_moderate",
        "blood_bag": "restores_blood_volume_only",
        "surgical_kit": "effective_for_severe_internal", 
        "splint": "ineffective",
        "painkiller": "counter_productive"
    },
    "fracture": {
        "splint": "highly_effective",
        "surgical_kit": "effective_but_complex",
        "gauze": "ineffective",
        "blood_bag": "ineffective",
        "painkiller": "helps_with_pain_only"
    },
    "infection": {
        "surgical_kit": "effective_with_cleaning",
        "gauze": "basic_prevention_only",
        "blood_bag": "ineffective",
        "splint": "ineffective", 
        "painkiller": "ineffective"
    }
    # Note: Exact effectiveness mechanics to be determined during implementation
}
```

## Medical Skill System

### G.R.I.M. Integration (Current Implementation)
- **Intellect (75%)**: Medical knowledge, diagnosis ability, understanding of anatomy and treatment
- **Motorics (25%)**: Steady hands for precise procedures, dexterity with medical tools

### G.R.I.M. Integration (Future Potential)  
- **Grit**: Pain tolerance during self-treatment, ability to work while injured
- **Resonance**: Bedside manner, patient stabilization, calming effect on others

### Medical Treatment Formula
```python
medical_effectiveness = (intellect * 0.75) + (motorics * 0.25)
treatment_success = d20_roll + medical_effectiveness vs difficulty_threshold
```

### Medical Actions

#### Diagnosis
```python
def diagnose_patient(medic, patient):
    """
    Determine what medical conditions affect the patient.
    Success reveals hidden conditions and treatment requirements.
    """
    intellect_roll = roll_d20() + medic.intellect
    difficulty = {
        "obvious_injuries": 8,    # Visible wounds
        "internal_injuries": 14,  # Requires examination  
        "systemic_conditions": 18 # Hidden organ damage
    }
```

#### Treatment Application
```python
def apply_medical_treatment(medic, patient, tool, condition):
    """
    Use medical tool to treat specific condition.
    Success based on G.R.I.M. stats and tool appropriateness.
    """
    medical_skill = (medic.intellect * 0.75) + (medic.motorics * 0.25)
    base_roll = roll_d20() + medical_skill
    
    # Tool appropriateness modifies difficulty
    base_difficulty = MEDICAL_TREATMENT_BASE_DIFFICULTY  # Constant for balance
    tool_modifier = TOOL_EFFECTIVENESS_MODIFIERS[tool.type][condition.type]  # Constant table
    actual_difficulty = base_difficulty + tool_modifier
    
    # Success determination
    if base_roll >= actual_difficulty:
        return "success"
    elif base_roll >= (actual_difficulty - PARTIAL_SUCCESS_MARGIN):  # Constant
        return "partial_success" 
    else:
        return "failure"
    
    # NOTE: All difficulty values use constants for easy balance adjustment
```

## Integration Points

### Combat System Integration

#### Damage Location Targeting
```python
def apply_anatomical_damage(character, damage, location):
    """
    Apply damage to specific body part, affecting relevant organs/systems.
    """
    # Determine which organs/systems are affected
    affected_systems = get_systems_for_location(location)
    
    # Distribute damage across systems
    for system in affected_systems:
        system_damage = calculate_system_damage(damage, system)
        apply_system_damage(character, system, system_damage)
        
    # Check for immediate effects
    check_critical_system_failure(character, affected_systems)
```

#### Weapon-Specific Injury Patterns
```python
WEAPON_INJURY_PATTERNS = {
    "blade": {"primary": "laceration", "secondary": "organ_damage"},
    "blunt": {"primary": "fracture", "secondary": "internal_bleeding"}, 
    "projectile": {"primary": "organ_damage", "secondary": "internal_bleeding"},
    "explosive": {"primary": "multiple_trauma", "secondary": "burns"}
}
```

### Longdesc System Integration

#### Medical Condition Visibility (Automatic Longdesc Appending)
```python
MEDICAL_DESCRIPTIONS = {
    "bleeding": {
        "obvious": "blood soaking through their clothing",
        "severe": "leaving a trail of blood behind them",
        "critical": "pale and trembling from blood loss"
    },
    "fracture_arm": {
        "splinted": "their arm held in a makeshift splint",
        "unsplinted": "cradling their obviously broken arm"
    },
    "vision_impaired": {
        "partial": "squinting as if having trouble seeing",
        "severe": "feeling around carefully with their hands"
    }
    # These descriptions automatically append to character longdesc when conditions are present
    # NOTE: Longdesc system is already designed to support this - implementation will use existing append hooks
}
```

### Integration Implementation Notes
- **Longdesc System**: Medical conditions visible in character descriptions
- **Condition Storage**: Medical conditions stored persistently across sessions
- **Priority System**: More severe conditions override less severe ones for display

---

*This specification reflects the current implemented state through Phase 2.5, with pure medical system architecture and complete consumption method interface. Future phases documented for development planning.*

#### Implemented Data Storage Architecture
```python
# Character medical state stored persistently in character.db
character.db.medical_state = {
    "organs": {
        "brain": {"current_hp": 8, "max_hp": 10, "conditions": []},
        "heart": {"current_hp": 15, "max_hp": 15, "conditions": []},
        "humerus_left": {"current_hp": 20, "max_hp": 20, "conditions": []},
        # ... all organs and bones
    },
    "conditions": [
        {"type": "fracture", "location": "left_arm", "severity": "moderate", "treated": False},
        {"type": "bleeding", "location": "chest", "severity": "minor", "rate": 1}
    ],
    "blood_level": 85.0,    # Percentage of normal blood volume
    "pain_level": 23.0,     # Current pain accumulation  
    "consciousness": 78.0   # Current consciousness level
}
```

#### Implemented Commands
- ✅ `medical [target]` - Check medical status with detailed health indicators
- ✅ `medinfo [organs|conditions|capacities]` - Detailed medical information system
- ✅ `damagetest <amount> [location] [injury_type]` - Test anatomical damage application
- ✅ `healtest [condition|all]` - Test healing mechanisms (development command)
- ✅ `@resetmedical [character|confirm all]` - Reset character medical states (admin)
- ✅ `@medaudit` - Comprehensive medical system diagnostics (admin)

### Phase 2: Medical Tools & Consumption Method Commands - ✅ COMPLETED
- ✅ **Medical item classes**: Full item management system with usage tracking
- ✅ **Consumption method commands implemented**: `inject`, `apply`, `bandage`, `eat`, `drink`, `inhale`, `smoke`
- ✅ **Self-administration & third-party administration**: Complete targeting and consent mechanics
- ✅ **Medical item management system**: Item discovery, validation, and usage tracking
- ✅ **G.R.I.M.-based treatment success/failure**: Medical effectiveness calculations implemented
- ✅ **Treatment appropriateness system**: Item-condition matching with success modifiers
- ✅ **Command Integration**: Natural language consumption commands fully functional

#### Implemented Consumption Commands
- ✅ `inject <item> [target]` - Injectable substances with full targeting support
- ✅ `apply <item> [to target]` - Topical treatments with natural language syntax
- ✅ `bandage <body_part> with <item>` - Advanced bandaging with body location targeting  
- ✅ `eat <item>` - Oral consumption of solid substances
- ✅ `drink <item>` - Liquid consumption system
- ✅ `inhale <item>` - Inhalation of gases, vapors, oxygen, anesthetic substances
- ✅ `smoke <item>` - Smoking medicinal herbs, cigarettes, dried medicines
- ✅ `drink <item>` - Liquid consumption system
- ✅ `medlist` - List medical items in inventory with status
- ✅ `inhale/smoke` - **COMPLETE** (Phase 2.5 - Consumption System Complete)

#### Medical Item Integration
- ✅ **Item type detection**: Automatic medical item classification
- ✅ **Usage tracking**: Items consume uses when applied
- ✅ **Treatment effects**: Medical conditions modified by successful treatments
- ✅ **Success calculation**: `(intellect * 0.75) + (motorics * 0.25)` formula implemented

*Note: Phase 2 consumption method system provides foundation for broader drug/substance system expansion*

### Phase 2.5: Complete Consumption System - ✅ COMPLETED (September 2025)
The final consumption method commands completing the natural language medical interface.

#### Implemented Inhalation Commands
- ✅ `inhale <item>` - Inhalation of gases, vapors, oxygen, anesthetic gases
- ✅ `smoke <item>` - Smoking medicinal herbs, cigarettes, dried medicines  
- ✅ Natural language syntax with help targeting: `help <target> inhale <item>`
- ✅ Consciousness requirements: Both commands require conscious targets
- ✅ Medical type validation: Items must have appropriate medical_type attributes

#### New Medical Types Supported
- ✅ **Inhalation types**: `oxygen`, `anesthetic`, `inhaler`, `gas`, `vapor`
- ✅ **Smoking types**: `herb`, `cigarette`, `medicinal_plant`, `dried_medicine`
- ✅ **Medical effects**: Respiratory treatment, pain relief, consciousness effects
- ✅ **Prototype examples**: Oxygen tank, stimpak inhaler, medicinal herbs, pain relief cigarettes

#### Command Integration
- ✅ Added to default command set with proper aliases (`huff`, `breathe`, `light`, `burn`)
- ✅ Full integration with existing medical utility functions
- ✅ Consistent syntax and behavior with other consumption commands
- ✅ Medical state persistence and treatment effect application

**Foundation Complete**: All planned consumption methods implemented - comprehensive natural language medical interface achieved.

### Phase 2.3: Precision Targeting System - ✅ COMPLETED (December 2024)
Advanced two-stage precision targeting system replacing simple weighted random hit location selection with skill-based anatomical targeting.

#### Two-Stage Targeting Architecture

**Stage 1: Success Margin Location Bias**
Attack success margin influences body region targeting with bias toward vital areas for skilled attacks:

```python
def select_hit_location(character, success_margin=0):
    # Base organ weights calculated for each location
    for location in available_locations:
        base_weight = sum(organ_hit_weights_in_location)
        
        # Apply success margin bias to vital areas
        if location in vital_areas and success_margin > 0:
            if success_margin <= 3:
                weight = base_weight * 1.25    # +25% vital area targeting
            elif success_margin <= 8:
                weight = base_weight * 1.5     # +50% vital area targeting  
            elif success_margin <= 15:
                weight = base_weight * 2.0     # +100% vital area targeting
            else:
                weight = base_weight * 3.0     # +200% vital area targeting
```

**Stage 2: Precision-Based Organ Selection**
Separate skill check determines specific organ targeting within the hit location:

```python
def select_target_organ(location, precision_roll, attacker_skill):
    # Mixed skill calculation: motorics (dexterity) + intellect (anatomy knowledge)
    precision_skill = int((motorics * 0.7) + (intellect * 0.3))
    precision_total = precision_roll + precision_skill
    
    # Precision affects rare/vital organ targeting probability
    for organ in location_organs:
        if organ.hit_weight == "very_rare":  # Heart, brain, arteries
            if precision_total >= 25:
                weight = base_weight * 3.0   # Exceptional precision
            elif precision_total >= 20:
                weight = base_weight * 2.0   # Good precision
            else:
                weight = base_weight * 0.5   # Poor precision
        elif organ.hit_weight == "rare":     # Liver, kidneys, eyes
            if precision_total >= 20:
                weight = base_weight * 2.0
            elif precision_total >= 15:
                weight = base_weight * 1.5
            # ... scaling continues for uncommon/common organs
```

#### Single Organ Damage Model
Replaces damage distribution across multiple organs with focused single-organ targeting:

**Previous System**: Damage spread proportionally across all organs in hit location
**New System**: ALL damage applied to single targeted organ for realistic wound patterns

```python
def distribute_damage_to_organs(location, total_damage, medical_state, injury_type, target_organ=None):
    if target_organ and target_organ in functional_organs:
        return {target_organ: total_damage}  # Single organ receives all damage
    # Falls back to proportional distribution if target organ destroyed
```

#### Combat Handler Integration
Complete integration with existing combat architecture:

```python
# Combat handler attack resolution (world/combat/handler.py ~line 1210)
if attacker_roll > target_roll:
    # Calculate success margin for location bias
    success_margin = attacker_roll - target_roll
    
    # Stage 1: Select hit location with success margin bias
    hit_location = select_hit_location(target, success_margin)
    
    # Stage 2: Make precision roll for organ targeting
    precision_roll = randint(1, 20)
    attacker_motorics = get_numeric_stat(attacker, "motorics", 1)
    attacker_intellect = get_numeric_stat(attacker, "intellect", 1)
    precision_skill = int((attacker_motorics * 0.7) + (attacker_intellect * 0.3))
    
    # Select specific target organ within location
    target_organ = select_target_organ(hit_location, precision_roll, precision_skill)
    
    # Apply focused damage to single organ
    target_died = target.take_damage(damage, location=hit_location, 
                                   injury_type=injury_type, target_organ=target_organ)
```

#### Updated Function Signatures
All medical system functions updated to support precision targeting:

```python
# Core targeting functions
select_hit_location(character, success_margin=0)
select_target_organ(location, precision_roll=0, attacker_skill=1)

# Damage application functions  
distribute_damage_to_organs(location, total_damage, medical_state, injury_type="generic", target_organ=None)
apply_anatomical_damage(character, damage_amount, location, injury_type="generic", target_organ=None)
take_damage(amount, location="chest", injury_type="generic", target_organ=None)
```

#### System Benefits
- **Skill-Based Targeting**: High motorics/intellect characters can target vital organs consistently
- **Tactical Combat**: Success margin rewards skilled attacks with vital area hits
- **Realistic Wounds**: Single organ damage creates focused injury patterns
- **Progressive Difficulty**: Hitting specific organs requires both good attack rolls AND precision skills
- **Medical Integration**: Sets foundation for surgical/medical skill interactions

#### Debug & Testing Support
Built-in debug output for precision targeting verification:
```
PRECISION_TARGET: attacker margin=8, precision=24, hit chest:heart
```

#### Backward Compatibility
All new parameters have default values maintaining compatibility with existing code:
- `success_margin=0` → no location bias (original behavior)
- `target_organ=None` → proportional damage distribution (original behavior)

**Foundation Complete**: Two-stage precision targeting fully integrated with combat system and Phase 2.4 wound description system fully implemented with comprehensive longdesc integration.

### Phase 2.4: Longdesc Wound Integration - ✅ COMPLETED
Dynamic wound descriptions that integrate with character longdesc system, featuring comprehensive wound state tracking and multi-variant descriptions.

#### Implementation Overview
Complete wound description system with organ-level state tracking, automated grammar formatting, and dynamic longdesc integration:

- **Multi-Variant Descriptions**: 20+ wound variants per injury type for variety
- **Organ State Tracking**: `wound_stage`, `injury_type`, `wound_timestamp` per organ
- **Grammar System**: Automatic capitalization and punctuation with color code preservation
- **Multiple Wound Handling**: Smart formatting for locations with multiple wounds
- **Dynamic Integration**: Flexible anatomy support with clothing concealment

#### Wound Description Lifecycle
Medical conditions dynamically modify character appearance through integrated longdesc hooks:

**Fresh Wounds** (`wound_stage: 'fresh'`):
- Bleeding, swelling, immediate trauma descriptions
- Severity-based intensity: minor cuts vs. gaping wounds
- Location-specific descriptions: "blood seeping from his left shoulder"

**Treated Wounds** (`wound_stage: 'treated'`):
- Bandaged, sutured, or medicated wound descriptions
- Treatment method visible: "neatly bandaged forearm" vs. "crude field dressing"
- Treatment quality affects description detail

**Healing Wounds** (`wound_stage: 'healing'`):
- Scabbing, bruising progression, reduced severity
- Time-based healing stages with evolving descriptions
- Natural recovery process visualization

**Destroyed Wounds** (`wound_stage: 'destroyed'`):
- Immediate aftermath of catastrophic organ/limb destruction
- Raw trauma visualization: "mangled beyond recognition", "bloody mess", "hanging by sinew"
- Requires immediate medical intervention to prevent death/infection
- Can be treated to "severed" state with proper medical care

**Severed Wounds** (`wound_stage: 'severed'`):
- Medically treated destruction - clean amputation with proper surgical care
- Professional medical descriptions: "surgical amputation", "sterile bandaging", "proper closure"
- Result of treating "destroyed" organs with advanced medical intervention
- Permanent state but clean and safe for prosthetic attachment

**Scarred Wounds** (`wound_stage: 'scarred'`):
- Permanent marking system for healed non-destroyed wounds
- Scar tissue descriptions based on original injury
- Character history preservation through appearance
- Only applies to wounds that healed naturally (not destroyed organs)

#### Wound Progression Paths
The medical system supports multiple wound progression paths based on damage severity and medical intervention:

**Normal Healing Path:**
1. `Fresh` → `Treated` (medical intervention) → `Healing` (time) → `Scarred` (permanent)
2. `Fresh` → `Healing` (natural) → `Scarred` (permanent)

**Catastrophic Damage Path:**
1. `Fresh` → `Destroyed` (damage exceeds threshold)
2. `Destroyed` → `Severed` (medical treatment transforms raw trauma into clean amputation)
3. `Destroyed/Severed` → **Prosthetic/Cybernetic Required** (permanent replacement)

**Key Distinction:** "Destroyed" represents immediate, raw trauma requiring urgent medical care to prevent death/infection, while "Severed" represents the clean, safe state achieved through proper medical treatment of destroyed organs. This creates a realistic progression where catastrophic injuries must be medically stabilized before prosthetic attachment is possible.

#### Organ-Specific Wound Descriptions
The wound system supports both location-level and organ-specific descriptions for enhanced medical accuracy and narrative detail:

**Current System Enhancement Opportunity:**
- **Location-based**: `"a severe bullet wound on the chest"` (generic)
- **Organ-specific**: `"a severe bullet wound through the heart"` (precise)

**Implementation Strategy:**
```python
# Enhanced wound description format variables
format_vars = {
    'severity': INJURY_SEVERITY_MAP.get(severity, severity.lower()),
    'location': location_display,           # "chest", "left arm"
    'organ': organ_display_name,            # "heart", "left lung", "brain"
    'organ_type': get_organ_type(organ),    # "vital organ", "bone", "sensory organ"
    'injury_type': injury_type
}

# Organ-specific description examples
def get_organ_display_name(organ_name):
    """Convert technical organ names to readable descriptions"""
    organ_mapping = {
        "left_eye": "left eye",
        "right_lung": "right lung", 
        "left_humerus": "left arm bone",
        "heart": "heart",
        "brain": "brain"
    }
    return organ_mapping.get(organ_name, organ_name)
```

**Organ Type Categories for Descriptions:**
```python
ORGAN_TYPE_MAPPING = {
    # Vital organs - catastrophic failure descriptions
    "heart": "vital_organ",
    "brain": "vital_organ", 
    "liver": "vital_organ",
    
    # Sensory organs - functionality loss descriptions  
    "left_eye": "sensory_organ",
    "right_eye": "sensory_organ",
    "left_ear": "sensory_organ",
    
    # Structural bones - fracture/break descriptions
    "left_humerus": "bone",
    "left_femur": "bone",
    "jaw": "bone",
    
    # Limb organs - amputation descriptions
    "left_hand_muscle": "limb_organ",
    "right_foot_muscle": "limb_organ"
}
```

**Enhanced Message File Examples:**
```python
# In world/medical/wounds/messages/bullet.py
WOUND_DESCRIPTIONS = {
    "fresh": [
        # Generic location-based (fallback)
        "|Ra {severity} bullet hole punched through the {location}|n",
        
        # Organ-specific variants (when organ provided)
        "|Ra {severity} bullet wound piercing the {organ}|n",
        "|Ra {severity} gunshot through the {organ} with devastating trauma|n",
        
        # Organ-type specific descriptions
        "|Ra {severity} bullet wound destroying the {organ} in a spray of blood|n",  # vital_organ
        "|Ra {severity} gunshot shattering the {organ} into fragments|n",           # bone
        "|Ra {severity} bullet puncturing the {organ} with precision damage|n"      # sensory_organ
    ],
    
    "destroyed": [
        # Vital organ destruction
        "|Ra devastating gunshot has obliterated the {organ} beyond repair|n",
        
        # Bone destruction  
        "|Ra high-caliber bullet has shattered the {organ} into fragments|n",
        
        # Sensory organ destruction
        "|Ra ballistic trauma has destroyed the {organ} completely|n"
    ]
}
```

**Benefits of Organ-Specific Descriptions:**
- **Medical Accuracy**: "bullet wound through the heart" vs "bullet wound to the chest"
- **Tactical Feedback**: Players understand exactly what was damaged
- **Narrative Depth**: More immersive and realistic injury descriptions
- **Surgical Precision**: Sets foundation for targeted medical treatment
- **Character History**: Specific organ damage creates unique character stories

**Implementation Phases:**
1. **Phase A**: Add organ parameter to existing wound message templates
2. **Phase B**: Create organ-type specific description variants  
3. **Phase C**: Implement organ display name mapping system
4. **Phase D**: Update all message files with organ-specific descriptions

This enhancement maintains backward compatibility while providing much richer medical detail when organ information is available.

#### Current Implementation Status & Enhancement Path

**✅ Currently Implemented:**
- Location-based wound descriptions (`"bullet wound on the chest"`)
- Organ parameter available in format variables but unused in message files
- Complete wound stage system (fresh/treated/healing/destroyed/severed/scarred)
- Grammar formatting system preserving color codes
- Multi-variant descriptions for narrative variety

**🔄 Enhancement Ready:**
- Organ-specific descriptions (`"bullet wound through the heart"`)
- Organ type categorization for description selection
- Enhanced medical accuracy and tactical feedback
- Foundation exists - just needs message file updates

**Implementation Required:**
```python
# 1. Add organ display name mapping
def get_organ_display_name(organ_name):
    return ORGAN_DISPLAY_MAPPING.get(organ_name, organ_name)

# 2. Add organ type categorization  
def get_organ_type(organ_name):
    return ORGAN_TYPE_MAPPING.get(organ_name, "generic")

# 3. Update message files to use {organ} variable
"destroyed": [
    "|Ra devastating bullet wound has obliterated the {organ} beyond repair|n",  # organ-specific
    "|Ra devastating bullet wound has destroyed the {location}|n",               # location fallback
]

# 4. Smart description selection logic
if format_vars['organ']:
    # Use organ-specific descriptions when available
    selected_descriptions = [desc for desc in stage_descriptions if '{organ}' in desc]
else:
    # Fall back to location-based descriptions  
    selected_descriptions = [desc for desc in stage_descriptions if '{organ}' not in desc]
```

**Benefits of Implementation:**
- **Immediate**: More precise medical descriptions without breaking existing system
- **Scalable**: Easy to add organ-specific variants to existing message files
- **Compatible**: Works with current wound generation and longdesc integration
- **Future-ready**: Sets foundation for surgical/medical targeting systems

The organ-specific enhancement can be implemented incrementally, starting with the most common organs (heart, brain, eyes) and expanding to cover the full anatomical system.

#### Actual Implementation Architecture
```python
# Organ-level wound state tracking (world/medical/core.py)
class Organ:
    def __init__(self, name, hp_max):
        self.wound_stage = 'fresh'         # fresh/treated/healing/destroyed/severed/scarred
        self.injury_type = 'generic'       # bullet/stab/cut/blunt/etc
        self.wound_timestamp = None        # For time-based healing
        self.treatment_quality = None      # poor/adequate/professional/surgical
        self.treatment_method = None       # bandage/suture/cauterize/field_dressing
    
    def apply_treatment(self, quality='adequate', method='bandage'):
        """Medical treatment with quality and method tracking"""
        if self.wound_stage == 'fresh':
            self.wound_stage = 'treated'
            self.treatment_quality = quality
            self.treatment_method = method
        elif self.wound_stage == 'destroyed':
            # Medical intervention can transform raw trauma into clean amputation
            self.wound_stage = 'severed'
            self.treatment_quality = quality
            self.treatment_method = method
    
    def advance_healing_stage(self):
        """Natural healing progression over time"""
        stage_progression = {
            'fresh': 'healing',
            'treated': 'healing', 
            'healing': 'scarred'
            # Note: destroyed/severed are permanent states requiring replacement
        }
        self.wound_stage = stage_progression.get(self.wound_stage, 'scarred')

# Dynamic wound description generation (world/medical/wounds/wound_descriptions.py)
def get_wound_description(injury_type, location, severity="Moderate", stage="fresh", organ=None, character=None):
    """Generate contextual wound description with organ-specific details"""
    stage = _determine_wound_stage_from_organ(organ)
    injury_type = getattr(organ, 'injury_type', 'generic')
    treatment_quality = getattr(organ, 'treatment_quality', None)
    treatment_method = getattr(organ, 'treatment_method', None)
    
    # Enhanced format variables with organ support
    format_vars = {
        'severity': INJURY_SEVERITY_MAP.get(severity, severity.lower()),
        'location': get_location_display_name(location, character),
        'organ': get_organ_display_name(organ) if organ else "",           # ENHANCEMENT OPPORTUNITY
        'organ_type': get_organ_type(organ) if organ else "",              # ENHANCEMENT OPPORTUNITY
        'injury_type': injury_type
    }
    
    description = _get_variant_description(organ, stage, injury_type, 
                                         treatment_quality, treatment_method, format_vars)
    return _format_wound_grammar(description)

def _get_variant_description(organ, stage, injury_type, treatment_quality, treatment_method, format_vars):
    """Select description variant with organ-specific logic"""
    # Current: Only uses location-based descriptions
    # Enhancement: Use organ-specific descriptions when available
    pass

def _format_wound_grammar(text):
    """Auto-format capitalization and punctuation while preserving color codes"""
    # Handles color codes like |r, |g, |n and template vars like {skintone}
    
# Longdesc integration hooks (world/medical/wounds/longdesc_hooks.py)
def append_wounds_to_longdesc(character, location, base_longdesc):
    """Integrate wound descriptions into character longdesc"""
    wounds = get_wounds_for_location(character, location)
    if wounds:
        wound_desc = _create_compound_wound_description_for_location(wounds, location)
        return f"{base_longdesc} {wound_desc}"
    return base_longdesc
```

#### Treatment Quality & Method System
**Treatment Quality Levels**:
- **`poor`**: Makeshift field treatment, improvised materials
  - *"crudely bandaged with torn cloth"*, *"hastily wrapped with dirty rags"*
- **`adequate`**: Basic first aid with proper supplies
  - *"bandaged with clean gauze"*, *"neatly dressed with field dressing"*  
- **`professional`**: Skilled medical treatment in clinical setting
  - *"expertly sutured and professionally bandaged"*, *"precisely stitched with medical precision"*
- **`surgical`**: Advanced surgical intervention with specialized equipment
  - *"surgically repaired with synthetic sutures"*, *"reconstructed with surgical mesh"*

**Treatment Methods**:
- **`bandage`**: Standard wound covering and pressure application
- **`suture`**: Stitching for deep lacerations and surgical wounds
- **`cauterize`**: Heat/chemical sealing for bleeding control
- **`field_dressing`**: Emergency battlefield treatment
- **`surgical_repair`**: Complex surgical reconstruction

**Quality-Dependent Descriptions** (treated stage examples):
```python
# Poor quality bandage treatment
"A crude bandage made from torn cloth covers the bullet wound on his arm, 
 already showing signs of seepage."

# Professional suture treatment  
"His arm bears an expertly sutured bullet wound with pristine white bandaging 
 and precise surgical tape."

# Surgical repair with mesh
"A complex surgical repair covers his chest, with visible surgical mesh beneath 
 transparent medical dressing."
```

**Implementation in Message Files**:
```python
# In world/medical/wounds/messages/bullet.py
TREATED_DESCRIPTIONS = {
    'poor': [
        "A crude {bandage_type} covers the bullet wound on {location}...",
        "Makeshift field dressing barely contains the gunshot wound..."
    ],
    'adequate': [
        "Clean white bandaging covers the bullet wound on {location}...", 
        "A proper field dressing protects the gunshot wound..."
    ],
    'professional': [
        "Expertly sutured bullet wound with pristine medical bandaging...",
        "Professional surgical repair evident in the treated gunshot wound..."
    ],
    'surgical': [
        "Advanced surgical reconstruction covers the bullet wound...",
        "Sophisticated medical intervention visible in the surgical repair..."
    ]
}
```

#### Wound Message System Implementation
Complete multi-variant wound description files covering all injury types and stages:

**Message File Structure** (`world/medical/wounds/messages/`):
- Individual files per injury type: `bullet.py`, `stab.py`, `cut.py`, `blunt.py`, `burn.py`, etc.
- 20+ description variants per wound stage for narrative variety
- Template variable support: `{skintone}`, `{location}`, medical colors `|r`, `|g`, `|n`

**Grammar Formatting System**:
```python
def _format_wound_grammar(text):
    """Intelligent grammar formatting preserving color codes and variables"""
    # Capitalizes first actual letter while preserving |r color codes
    # Ensures single period ending while avoiding double periods
    # Handles template variables like {skintone} correctly
```

**Multiple Wound Handling**:
- Locations with longdesc: Wound descriptions append seamlessly
- Locations without longdesc: Standalone descriptions using wound types
- Smart conjunction formatting: "A cut and a bullet wound mark his arm"
- Prevents redundancy while maintaining natural language flow

#### Character Integration Points
```python
# Character longdesc integration (typeclasses/characters.py)
def _get_visible_body_descriptions(self):
    """Generate dynamic body descriptions including wounds"""
    descriptions = {}
    for location in self.anatomy.locations:
        base_desc = self.db.longdesc.get(location, "")
        wound_desc = append_wounds_to_longdesc(self, location, base_desc)
        if wound_desc != base_desc:  # Only include if wounds present
            descriptions[location] = wound_desc
    return descriptions

# Clothing concealment support
def check_wound_visibility(character, location):
    """Check if wounds are concealed by clothing"""
    worn_items = character.get_worn_items_for_location(location)
    coverage = calculate_coverage_percentage(worn_items, location)
    return coverage < 90  # Wounds visible if <90% coverage
```

#### Future-Proof Architecture Features
- **Extensible State Tracking**: Organ-level `wound_stage` ready for medical system expansion
- **Treatment Quality System**: `treatment_quality` and `treatment_method` tracking for medical skill integration
- **Treatment Integration**: `apply_treatment(quality, method)` and `advance_healing_stage()` methods prepared
- **Time-Based Healing**: `wound_timestamp` tracking for temporal healing mechanics  
- **Dynamic Anatomy Support**: Flexible location handling for any anatomy configuration
- **Template System**: Variable substitution ready for expanded customization

#### Production Ready Features
✅ **Complete Message Coverage**: All injury types with full variant descriptions  
✅ **Grammar System**: Automatic formatting with color code preservation  
✅ **Multiple Wound Support**: Intelligent handling of complex wound combinations  
✅ **Longdesc Integration**: Seamless character description enhancement  
✅ **Clothing Interaction**: Concealment mechanics for realistic visibility  
✅ **State Persistence**: Organ-level tracking survives server restarts  
✅ **Debug Support**: External testing scripts validate all functionality

#### Planned Extensions (Ready for Implementation)
🔲 **Treatment Quality Integration**: Message variants based on medical skill levels  
🔲 **Medical Skill Checks**: Treatment quality determined by character medical abilities  
🔲 **Treatment Tools**: Quality modifiers based on available medical equipment  
🔲 **Infection Mechanics**: Poor treatment quality leads to wound complications  
🔲 **Healing Speed**: Treatment quality affects recovery time via `wound_timestamp`

*Note: Phase 2.4 wound description system completed with comprehensive longdesc integration, multi-variant messaging, and future-proof organ state tracking architecture*

### Phase 2.5: Extended Consumption Methods - ✅ COMPLETED (September 2025)
- ✅ **Additional consumption commands**: `inhale`, `smoke`, `huff` with full aliasing implemented
- ✅ **Inhalation mechanics**: Respiratory delivery systems for gases, vapors, oxygen
- ✅ **Combustion consumption**: Smoking/burning substance delivery for herbs and medicinal plants
- 🔧 **Advanced substance interactions**: Command framework complete, substance effect refinement ongoing

*Note: All consumption method commands are implemented and functional. Substance effect balancing and advanced interactions are iterative improvements to the solid foundation.*

### Phase 2.6: Ticker-Based Medical Conditions - ✅ COMPLETED (Dec 2024)
Dynamic medical conditions that apply ongoing effects over time using Evennia's native ticker system.

**Implementation Complete:**
- ✅ **Multi-speed ticker system**: Combat (6s), severe bleeding (12s), medical (60s) intervals
- ✅ **MedicalCondition base class**: Full Evennia TICKER_HANDLER integration
- ✅ **BleedingCondition**: Natural clotting with decay rate and location tracking
- ✅ **BurningCondition**: Fire damage that spreads to adjacent body areas  
- ✅ **AcidCondition**: Chemical burns with equipment damage mechanics
- ✅ **Automatic condition creation**: Integrated with damage system via `take_organ_damage()`
- ✅ **Condition management**: Add/remove conditions with ticker lifecycle management
- ✅ **Factory function**: `create_condition_from_damage()` for damage-type based conditions
- ✅ **Synchronized messaging**: Collect effects → build message → apply effects → send message

**Tactical Balance:**
- Severe bleeding ticks every 12 seconds (2-3 combat rounds) - complements weapon damage
- Burning/acid tick every 6 seconds (every combat round) - creates urgency
- Minor bleeding ticks every 60 seconds - allows natural clotting over time

**Files Modified/Created:**
- `world/medical/constants.py`: Added ticker intervals and condition configuration
- `world/medical/conditions.py`: Complete condition class hierarchy (NEW)
- `world/medical/core.py`: Enhanced MedicalState with condition management

#### Condition Ticker Architecture
```python
# Implemented base condition class with ticker support (world/medical/conditions.py)
class MedicalCondition:
    def __init__(self, condition_type, severity, location=None, tick_interval=60):
        self.condition_type = condition_type
        self.severity = severity           # Current condition strength
        self.location = location           # Body location affected
        self.tick_interval = tick_interval # Seconds between ticks
        self.requires_ticker = True        # Uses Evennia ticker system
        
    def start_condition(self, character):
        """Begin ticking condition on character"""
        from evennia import TICKER_HANDLER
        TICKER_HANDLER.add(
            interval=self.tick_interval,
            callback=self.tick_effect,
            idstring=f"{character.id}_{self.condition_type}_{id(self)}",
            persistent=True
        )
        
    def tick_effect(self):
        """Apply condition effect each tick - implemented in subclasses"""
        pass
        
    def stop_condition(self):
        """Stop ticking and clean up"""
        from evennia import TICKER_HANDLER
        TICKER_HANDLER.remove(idstring=f"condition_{id(self)}")
```

#### Bleeding Condition Implementation
```python
class BleedingCondition(MedicalCondition):
    def __init__(self, severity, location=None, decay_rate=1):
        from .constants import CONDITION_INTERVALS
        
        # Determine tick interval based on severity
        if severity >= 3:
            tick_interval = CONDITION_INTERVALS['severe_bleeding']  # 12 seconds
        else:
            tick_interval = CONDITION_INTERVALS['minor_bleeding']   # 60 seconds
            
        super().__init__(
            condition_type="bleeding",
            severity=severity,
            location=location,
            tick_interval=tick_interval
        )
        self.decay_rate = decay_rate  # Natural clotting rate
        
    def tick_effect(self):
        """Apply bleeding effects with natural clotting"""
        if self.severity > 0:
            # Apply bleeding damage based on severity
            damage_amount = self.severity
            
            # Natural clotting - reduce severity over time
            self.severity = max(0, self.severity - self.decay_rate)
            
            # Build and send coordinated message
            effects = []
            if damage_amount > 0:
                effects.append(f"lost {damage_amount} blood")
            if self.severity <= 0:
                effects.append("bleeding has stopped")
                
            # Apply damage and send message together
            if effects:
                message = f"You {' and '.join(effects)}."
                # Send message to character
                # Apply actual damage to medical state
                # Remove condition if bleeding stopped
```
            # Apply blood loss
            blood_loss = self.severity
            character.medical_state.blood_current -= blood_loss
            
            # Decrease bleeding severity naturally
            self.severity = max(0, self.severity - self.decay_rate)
            
            # Wound description updates
            self.update_wound_descriptions(character)
            
            # Notify character
            if blood_loss > 3:
                character.msg(f"|rYou feel blood flowing from your {self.location}.|n")
            elif blood_loss > 1:
                character.msg(f"|RBlood seeps from your {self.location}.|n")
```

#### Condition Type Examples
**Natural Decay Bleeding**:
```python
# Arterial bleeding: 8->7->6->5->4->3->2->1->0 (stops naturally)
BleedingCondition(initial_severity=8, decay_rate=1, location="neck")

# Venous bleeding: 4->3->2->1->0 (stops naturally) 
BleedingCondition(initial_severity=4, decay_rate=1, location="arm")
```

**Persistent Conditions** (require treatment):
```python
class SevereBleedingCondition(BleedingCondition):
    def __init__(self, severity, location):
        super().__init__(severity, decay_rate=0, location=location)
        self.auto_resolve = False
        self.requires_treatment = True
        
    def apply_effect(self, character):
        """Constant blood loss until treated"""
        character.medical_state.blood_current -= self.severity
        # Severity doesn't decrease - must be bandaged/treated
```

**Fire Condition**:
```python
class BurningCondition(MedicalCondition):
    def __init__(self, intensity, spread_chance=0.1):
        super().__init__(
            name="burning",
            severity=intensity,
            tick_interval=30,  # Fire acts quickly
            auto_resolve=False  # Must be extinguished
        )
        self.spread_chance = spread_chance
        
    def apply_effect(self, character):
        """Burn damage each tick, chance to spread"""
        # Apply burn damage to random location
        damage = self.severity
        location = random.choice(character.anatomy.locations)
        character.take_damage(damage, location=location, injury_type="burn")
        
        # Chance to spread fire
        if random.random() < self.spread_chance:
            self.severity += 1
            
        character.msg(f"|YFlames sear your flesh!|n")
```

**Acid Exposure**:
```python
class AcidCondition(MedicalCondition):
    def __init__(self, concentration, duration):
        super().__init__(
            name="acid_exposure", 
            severity=concentration,
            max_duration=duration,
            tick_interval=45
        )
        
    def apply_effect(self, character):
        """Ongoing acid damage with equipment degradation"""
        # Damage character
        damage = self.severity
        character.take_damage(damage, location="chest", injury_type="acid")
        
        # Damage equipment
        for item in character.equipment:
            if hasattr(item, 'acid_resistance'):
                item.take_acid_damage(self.severity)
```

#### Treatment Integration
```python
def apply_medical_treatment(character, condition_name, treatment_quality):
    """Treat ongoing conditions"""
    condition = character.get_condition(condition_name)
    
    if condition_name == "bleeding":
        if treatment_quality >= "adequate":
            condition.end_condition(character)  # Stop bleeding immediately
            character.msg("The bleeding has been stopped with proper bandaging.")
        else:
            condition.severity = max(1, condition.severity // 2)  # Reduce severity
            character.msg("The bleeding has been slowed but not stopped.")
            
    elif condition_name == "burning":
        condition.end_condition(character)  # Fire extinguished
        character.msg("The flames have been extinguished.")
```

#### Condition Stacking & Interaction
```python
# Multiple bleeding sources
character.add_condition(BleedingCondition(5, location="arm"))
character.add_condition(BleedingCondition(3, location="leg"))
# Each ticks independently: 5+3=8 blood loss per tick initially

# Condition interactions
if character.has_condition("bleeding") and character.has_condition("burning"):
    # Fire cauterizes bleeding - reduce bleeding by 1 per tick
    bleeding.severity = max(0, bleeding.severity - 1)
```

#### System Benefits
- **Realistic Progression**: Bleeding naturally decreases over time
- **Treatment Urgency**: Severe conditions require immediate intervention
- **Dynamic Combat**: Ongoing effects create tactical decisions
- **Medical Depth**: Different treatments for different condition types
- **Performance Efficient**: Leverages Evennia's optimized ticker system
- **Persistent**: Conditions survive server restarts via ticker persistence

### Phase 3: Combat Integration & Stat Penalties - 🔲 IN PROGRESS
- [x] **Smart hit location system** based on attack success margin and precision targeting - ✅ COMPLETED
- [ ] **Organ density-based targeting** - vital organ areas harder to hit precisely
- [ ] **Armor protection layers** - clothing/armor reduces damage to protected organs  
- [ ] **Armor damage system** - protective gear degrades from absorbing hits
- [ ] **Weapon penetration mechanics** - different weapons vs different armor types
- [ ] **Limb loss system** - complete destruction of all organs in a location results in limb loss

#### Hit Location Mechanics (IMPLEMENTED)
```python
# Two-stage precision targeting system (CURRENT IMPLEMENTATION)

# Stage 1: Success margin affects location selection
attack_roll = d20 + attacker_skill
defense_roll = d20 + defender_skill  
success_margin = attack_roll - defense_roll

hit_location = select_hit_location(target, success_margin)
# Success margin biases targeting toward vital areas:
# margin 1-3:   +25% weight to head/chest/neck/abdomen
# margin 4-8:   +50% weight to vital areas
# margin 9-15:  +100% weight to vital areas  
# margin 16+:   +200% weight to vital areas

# Stage 2: Precision roll determines specific organ within location
precision_roll = d20
precision_skill = (motorics * 0.7) + (intellect * 0.3)
precision_total = precision_roll + precision_skill

target_organ = select_target_organ(hit_location, precision_roll, precision_skill)
# High precision (25+): 3x more likely to hit very_rare organs (heart, brain)
# Good precision (20+): 2x more likely to hit rare organs (liver, kidneys)
# Low precision (<20): Favors common organs (muscle, bone), avoids vitals

# Single organ damage application
target.take_damage(damage, location=hit_location, injury_type=weapon_type, target_organ=target_organ)
# ALL damage goes to the targeted organ (no spreading)
```

#### Armor Integration System
```python
# Layered protection check
worn_items = character.get_worn_items_for_location(hit_location)
protection_layers = []

for item in worn_items:
    if item.armor_rating and protects_location(item, hit_location):
        protection_layers.append({
            'item': item,
            'armor_rating': item.armor_rating,
            'armor_type': item.armor_type,  # 'leather', 'kevlar', 'plate', etc.
            'condition': item.condition      # 100% = perfect, 0% = destroyed
        })

# Calculate damage reduction
total_protection = 0
penetrating_damage = initial_damage

for layer in protection_layers:
    # Weapon vs armor type effectiveness
    penetration = get_penetration_value(weapon_type, layer['armor_type'])
    effective_armor = layer['armor_rating'] * (layer['condition'] / 100.0)
    
    damage_stopped = min(penetrating_damage, effective_armor * (1.0 - penetration))
    penetrating_damage -= damage_stopped
    
    # Damage the armor
    armor_damage = calculate_armor_damage(damage_stopped, weapon_type)
    layer['item'].take_armor_damage(armor_damage)
    
    if penetrating_damage <= 0:
        break  # Completely stopped by armor

# Apply remaining damage to organs
if penetrating_damage > 0:
    target_organ.take_damage(penetrating_damage, injury_type)
```

#### Weapon vs Armor Matrix
```python
PENETRATION_VALUES = {
    # weapon_type: { armor_type: penetration_percentage }
    'bullet': {
        'cloth': 0.95,      # Bullets easily penetrate cloth
        'leather': 0.80,    # Some protection vs bullets
        'kevlar': 0.30,     # Designed to stop bullets
        'plate': 0.60       # Depends on caliber vs thickness
    },
    'stab': {
        'cloth': 0.90,      # Knives cut through cloth
        'leather': 0.50,    # Leather provides good stab protection
        'kevlar': 0.70,     # Kevlar weak vs stabbing
        'plate': 0.20       # Plate excellent vs stabs
    },
    'cut': {
        'cloth': 0.85,      # Slashing cuts cloth easily  
        'leather': 0.60,    # Moderate protection
        'kevlar': 0.40,     # Good vs cuts
        'plate': 0.15       # Excellent protection
    },
    'blunt': {
        'cloth': 0.95,      # No protection vs blunt force
        'leather': 0.80,    # Minimal padding
        'kevlar': 0.70,     # Some cushioning
        'plate': 0.30       # Distributes impact well
    }
}
```

#### Integration with Current Combat System (IMPLEMENTED)
The precision targeting system is fully integrated with the existing combat architecture:

**Current Implementation**: Combat handler uses two-stage targeting with single organ damage
```python
# In combat handler attack resolution (world/combat/handler.py)
if attacker_roll > target_roll:
    # Calculate success margin for location bias
    success_margin = attacker_roll - target_roll
    
    # Stage 1: Location selection with vital area bias
    hit_location = select_hit_location(target, success_margin)
    
    # Stage 2: Precision-based organ targeting
    precision_roll = randint(1, 20)
    precision_skill = int((attacker_motorics * 0.7) + (attacker_intellect * 0.3))
    target_organ = select_target_organ(hit_location, precision_roll, precision_skill)
    
    # Apply focused damage to single targeted organ
    target_died = target.take_damage(damage, location=hit_location, 
                                   injury_type=injury_type, target_organ=target_organ)
```

**Combat Message Integration**:
- `{hit_location}` variable dynamically populated with actual hit location
- Debug output: `PRECISION_TARGET: attacker margin=X, precision=Y, hit location:organ`
- All weapon message files support dynamic hit location display

**Weapon System Integration**:
- Uses existing `weapon.db.damage_type` for injury classification
- Integrates with weapon damage calculation: `get_weapon_damage(weapon, 0)`
- Supports all current weapon types (unarmed, blades, firearms, etc.)

**Combat Command Integration**:
```python
# Enhanced attack commands with targeting options
> attack bandit             # Normal attack (success determines location)  
> attack bandit head        # Deliberate headshot (harder roll, -4 penalty)
> attack bandit center      # Aim for center mass (+2 bonus, chest/abdomen)
> attack bandit limbs       # Target extremities (+1 bonus, arms/legs only)
```

**Clothing/Armor System Integration**:
- Extends existing `clothing.py` system with armor ratings
- Uses current wear/remove mechanics  
- Builds on location-based coverage already in clothing system

#### Location Difficulty Modifiers
```python
HIT_LOCATION_DIFFICULTY = {
    # Higher values = harder to hit precisely
    'head': {
        'difficulty': 8,     # Small target, vital organs
        'organs': ['brain', 'left_eye', 'right_eye'],
        'vital_density': 'very_high'
    },
    'chest': {
        'difficulty': 4,     # Large target, but vital organs
        'organs': ['heart', 'left_lung', 'right_lung'],  
        'vital_density': 'high'
    },
    'abdomen': {
        'difficulty': 5,     # Medium target, some vital organs
        'organs': ['liver', 'stomach', 'left_kidney', 'right_kidney'],
        'vital_density': 'medium'
    },
    'left_arm': {
        'difficulty': 2,     # Easier to hit, no vital organs
        'organs': ['left_humerus', 'left_metacarpals'],
        'vital_density': 'none'
    },
    'right_leg': {
        'difficulty': 3,     # Large target, structural bones only
        'organs': ['right_femur', 'right_tibia', 'right_metatarsals'],
        'vital_density': 'none'  
    }
}
```

#### Technical Implementation Plan
**Phase 3.1: Hit Location System** - ✅ COMPLETED
1. ~~Create `world/combat/hit_location.py` module~~ → Implemented in `world/medical/utils.py`
2. ~~Add `calculate_hit_location(success_margin, targeting_intent)` function~~ → Implemented as `select_hit_location(character, success_margin)` and `select_target_organ(location, precision_roll, attacker_skill)`
3. ~~Define location difficulty constants and organ targeting weights~~ → Implemented with success margin thresholds and precision-based organ weights
4. ~~Update combat handler to use smart location targeting~~ → Fully integrated two-stage targeting system

**Phase 3.2: Armor Protection Layer** - 🔲 PLANNED 
1. Extend `typeclasses/items.py` with armor properties:
   ```python
   # Add to clothing items
   armor_rating = 0         # Protection points
   armor_type = "none"      # 'leather', 'kevlar', 'plate', etc.
   max_condition = 100      # Durability when new
   current_condition = 100  # Current condition (damaged = less protection)
   protects_locations = []  # ['chest', 'abdomen'] etc.
   ```

2. Create `world/medical/armor_system.py` module:
   ```python
   def apply_armor_protection(damage, location, character, weapon):
       """Calculate damage after armor protection"""
       
   def damage_armor(item, damage_amount, weapon_type):
       """Apply wear and tear to protective equipment"""
   ```

**Phase 3.3: Integration Points**
1. Update `world/combat/handler.py` damage application
2. Extend weapon definitions with penetration characteristics  
3. Add armor condition display to clothing commands
4. Create armor repair mechanics (future: crafting system integration)

**Phase 3.4: Balancing and Testing**
1. Define penetration values through combat testing
2. Balance armor degradation rates vs availability
3. Tune hit location probabilities for tactical depth vs playability
4. Test integration with existing medical condition system

#### Limb Loss System
**Trigger Condition**: Complete destruction of all organs in a location results in limb loss.

**Implementation Architecture**:
```python
# Location organ monitoring (world/medical/core.py)
def check_location_viability(character, location):
    """Check if a location has any functional organs remaining"""
    location_organs = character.anatomy.get_organs_in_location(location)
    
    for organ in location_organs:
        if organ.hp_current > 0:
            return True  # Location still viable
    return False  # All organs destroyed - limb loss

def process_limb_loss(character, location):
    """Handle complete limb loss when all organs destroyed"""
    # Mark location as lost
    character.anatomy.locations[location]['status'] = 'severed'
    character.anatomy.locations[location]['lost_timestamp'] = time.time()
    
    # Apply massive bleeding condition
    from world.medical.conditions import SevereBleedingCondition
    bleeding = SevereBleedingCondition(
        severity=10,  # Arterial bleeding from amputation
        location=location,
        requires_treatment=True
    )
    character.add_condition(bleeding)
    
    # Location-specific consequences
    apply_limb_loss_effects(character, location)
    
    # Permanent character modification
    update_longdesc_for_loss(character, location)
    
def apply_limb_loss_effects(character, location):
    """Apply permanent stat and capability penalties"""
    if location in ['left_arm', 'right_arm']:
        character.db.limb_loss_penalties['manipulation'] += 2
        character.db.limb_loss_penalties['equipment_capacity'] -= 0.5
        
    elif location in ['left_leg', 'right_leg']:
        character.db.limb_loss_penalties['movement'] += 3
        character.db.limb_loss_penalties['balance'] += 2
        
    elif location == 'head':
        # Instant death - complete brain destruction
        character.die("catastrophic head trauma")
        return
        
    elif location in ['chest', 'abdomen']:
        # Torso loss = death (heart, lungs, vital organs)
        character.die("massive organ failure")
        return
```

**Limb-Specific Consequences**:

**Arm Loss**:
```python
# Mechanical effects
- Cannot use two-handed weapons
- -50% equipment carrying capacity  
- Cannot perform actions requiring both hands (climbing, some crafting)
- Manipulation skill penalties: -2 to fine motor tasks

# Social/RP effects  
- Updated character longdesc: "missing his left arm from the elbow down"
- Equipment auto-drops from severed limb
- Phantom limb pain condition (optional RP mechanic)
```

**Leg Loss**:
```python
# Mechanical effects
- Movement speed reduced by 60%
- Cannot run or sprint
- Climbing becomes impossible without prosthetics
- Balance penalties: -3 to acrobatic actions, easier to knock down

# Social/RP effects
- Requires crutches or prosthetic for mobility
- Updated movement messages: "hobbles" instead of "walks"
- Sitting/standing requires assistance or extra time
```

**Prevention & Treatment**:
```python
# Emergency intervention can prevent limb loss
def emergency_stabilization(character, location, medical_skill):
    """Attempt to save critically damaged limb"""
    location_organs = character.anatomy.get_organs_in_location(location)
    destroyed_count = sum(1 for organ in location_organs if organ.hp_current <= 0)
    total_organs = len(location_organs)
    
    if destroyed_count == total_organs:
        # Too late - limb already lost
        return False
        
    if destroyed_count >= (total_organs * 0.8):
        # Critical damage - medical check required
        difficulty = 15 + (destroyed_count * 2)
        if medical_skill_check(character, difficulty):
            # Stabilize remaining organs at 1 HP
            for organ in location_organs:
                if organ.hp_current <= 0:
                    organ.hp_current = 1
            return True
    return False
```

**Prosthetics Integration** (Future Phase 5):
```python
# Prosthetic system foundation
class Prosthetic:
    def __init__(self, limb_type, quality_level):
        self.limb_type = limb_type      # 'arm', 'leg', 'hand', etc.
        self.quality = quality_level    # 'crude', 'mechanical', 'cybernetic'
        self.functionality = self.calculate_functionality()
        
    def calculate_functionality(self):
        """Determine what percentage of original function is restored"""
        quality_restoration = {
            'crude': 0.3,      # Wooden peg leg, hook hand
            'mechanical': 0.6,  # Articulated mechanical limbs  
            'cybernetic': 0.9   # Advanced neural-linked prosthetics
        }
        return quality_restoration.get(self.quality, 0.1)
```

**Narrative Integration**:
```python
# Limb loss creates permanent character story
- Battle scars and visible disabilities enhance RP depth
- Prosthetics become valuable equipment with mechanical benefits
- Medical professionals gain importance for limb-saving procedures
- Combat becomes more consequential with permanent stakes

# Longdesc modifications
"A weathered soldier missing his right arm from a old battlefield wound..."
"She moves with a pronounced limp, her left leg replaced by a crude wooden prosthetic..."
"Advanced cybernetic implants have replaced both his arms, gleaming chrome visible at the joints..."
```

**System Benefits**:
- **Permanent Consequences**: Combat decisions have lasting impact
- **Medical Urgency**: Creates time-pressure for emergency treatment
- **Character Development**: Disabilities become part of character identity
- **Equipment Value**: Prosthetics become significant equipment upgrades
- **Tactical Depth**: Targeting limbs vs vital areas becomes strategic choice
- **Realistic Escalation**: Natural progression from wound system to major trauma

### Phase 4: Combat Integration & Stat Penalties
- [ ] Location-based damage system in combat
- [ ] Weapon-specific injury patterns  
- [ ] Critical injury immediate effects
- [ ] **Pain/injury penalties affecting dice rolls**: Unified with existing stat calculation systems
- [ ] **Medical condition modifiers**: Integration with combat, skill checks, and other game mechanics
- [ ] Medical emergency scenarios

*Note: Penalty mechanics will be unified with existing stat vs health calculations*

### Phase 5: Advanced Systems
- [ ] Long-term healing and recovery
- [ ] Infection and complication systems
- [ ] Prosthetics and permanent disabilities
- [ ] Advanced surgical procedures

## Medical System Summary

This specification documents a comprehensive medical system architecture providing:

**Core Medical Mechanics:**
- Individual organ tracking with realistic anatomical accuracy
- Precision single-organ damage model with skill-based targeting
- Progressive condition system with natural healing and deterioration
- Complete substance consumption interface with 7 natural consumption methods
- **Unified medical messaging system eliminating message spam**
- **Forensic evidence management with blood pool aging and integration**

**Gameplay Integration:**
- Medical tools seamlessly integrate with standard Evennia Item typeclass
- G.R.I.M. stat system determines medical skill effectiveness  
- Combat system creates medical emergencies requiring tactical response
- Resource management through limited medical supplies and equipment uses
- **Room integration system for atmospheric forensic evidence display**
- **Enhanced cleaning mechanics for comprehensive evidence management**

**System Architecture:**
- Medical state persisted in character.db for save compatibility
- Utility function interface requires no custom typeclasses
- Modular condition system supports easy expansion
- Universal substance framework enables medical, recreational, and toxic substances
- **Consolidated messaging architecture preventing medical condition spam**
- **Centralized death analysis ensuring consistent debug reporting**

**Implementation Status:**
- **Phase 1**: ✅ Foundation anatomy and damage system (Completed December 2024)
- **Phase 2**: ✅ Medical tools and complete consumption interface (Completed September 2025)  
- **Phase 2.5**: ✅ Extended consumption methods and inhalation mechanics (Completed September 2025)
- **Phase 2.6**: ✅ Ticker-based medical conditions with time-based progression (Completed December 2024)
- **Phase 2.7**: ✅ Unified medical messaging and forensic evidence systems (Completed September 2025) - *Forensic system is proof-of-concept only*
- **Phase 3**: 🔮 Advanced features (cybernetics, complex procedures) - Future development

**Key Features Delivered:**
- Hospital-grade anatomical accuracy with individual bone tracking
- Natural language medical commands (`inject`, `apply`, `bandage`, `inhale`, etc.)
- Realistic injury progression and treatment mechanics
- Tactical medical gameplay requiring resource allocation and skill development
- **Single consolidated medical message per tick combining bleeding and pain**
- **Integrated forensic evidence system with blood pools and crime scene management**
- **Enhanced spray command for unified graffiti and blood evidence cleaning**
- **Consistent death analysis across all death scenarios (combat, medical, other)**

**Recent Major Improvements (September 2025):**
- **Message Spam Elimination**: Unified medical messaging prevents overwhelming players with multiple condition messages per tick
- **Forensic Evidence Integration (Proof-of-Concept)**: Blood pools now integrate into room descriptions like graffiti, creating atmospheric crime scenes - *foundation for future dedicated forensic investigation system*
- **Enhanced Evidence Cleaning**: Spray command now handles both graffiti and blood evidence with context-appropriate messaging
- **Death Analysis Consistency**: Centralized death reporting ensures debug information appears for all death scenarios
- **Medical Color Standardization**: All medical-related messages now use consistent |R bright red coloring

*The implemented system provides a solid foundation for medical gameplay while maintaining Evennia compatibility and extensibility for future enhancements. Recent improvements focus on user experience quality-of-life enhancements and proof-of-concept forensic evidence management.*

---

*"In space, a medical emergency doesn't wait for convenient timing. Every blood bag, every splint, every steady hand could mean the difference between coming home or floating in the void."*
- Dr. Sarah Chen, Frontier Medical Corps, 2387 TST
