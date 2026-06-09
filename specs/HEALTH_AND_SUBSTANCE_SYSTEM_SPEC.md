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
- Smart consumption system preventing resource waste through need-based analysis

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

**Death Progression System Complete (September 2025):**
- ✅ **6-minute revival window** - Time-delayed death progression allowing medical intervention
- ✅ **Progressive dying messages** - Chuck Palahniuk/Hunter S. Thompson inspired visceral narrative 
- ✅ **Medical system integration** - Automatic revival if medical conditions resolved during progression
- ✅ **Session-aware formatting** - Text centering using curtain of death patterns for consistent presentation
- ✅ **Emotional resonance** - 11 progression messages with substantial literary content creating meaningful death experience
- ✅ **Observer messaging** - Room occupants see progression indicators while dying character experiences internal narrative
- ✅ **Script-based timer** - Robust 30-second interval system with cleanup and state management
- ✅ **Universal themes** - Death messaging avoids specific cultural/family references for inclusive player experience

### ✅ CURRENT STATE: COMPREHENSIVE DEATH AND MEDICAL SYSTEM (September 2025)
**Complete Death Processing and Revival Mechanics:**
- **Death curtain protection** with no personal medical messages sent to deceased characters
- **Persistent placement descriptions** providing visual indicators for unconscious/dead states without scrolling
- **Enhanced observer messaging** with atmospheric blood descriptions for deceased characters
- **Race condition elimination** through centralized death processing and delayed attack validation
- **Integrated infection messaging** with consolidated medical system using consistent red coloring
- **BloodPool forensic evidence** with aging and room description integration
- **Unified cleaning system** supporting both graffiti and blood evidence removal
- **Death progression system** with 6-minute revival window and medical intervention mechanics
- **Smart medical item consumption** with need-based resource management preventing waste

**Death System Implementation Complete:**
- **✅ Death script cleanup** - Death progression script automatically stops and deletes after 6-minute window expires
- **✅ Character teleportation** - Character moved to temporary death room/limbo area for processing using reliable script pattern
- **✅ Corpse object creation** - Robust corpse generation inheriting character attributes for forensic examination:
  - **✅ Inventory transfer** - All carried items, equipment, and worn clothing transferred to corpse with comprehensive source checking
  - **✅ Physical description** - Complete character appearance preservation including longdesc, clothing coverage, and template processing
  - **✅ Template variable processing** - Proper {They}, {their}, {color} substitution with universal skintone color application

**Unified Medical Messaging System Complete:**
- **✅ Single medical message per tick** instead of separate bleeding/pain messages
- **✅ Combined severity assessment** showing both bleeding and pain status
- **✅ Consistent |R bright red coloring** for all medical-related text
- **✅ Smart message timing** prevents message spam while maintaining medical urgency

**Smart Medical Item Consumption System Complete (September 2025):**
- **✅ Need-based consumption logic** - Medical supplies only consumed when actual treatment can occur, not during examination-only procedures
- **✅ Medical specialization** - Surgery kits for soft tissue organs, splints for bones, bandages for bleeding, blood bags for blood loss
- **✅ Architectural robustness** - Direct medical state analysis replaces fragile message text parsing for consumption decisions
- **✅ Resource efficiency** - Prevents wasteful consumption on healthy patients or inappropriate conditions
- **✅ Unconscious patient support** - Medical procedures that don't require cooperation work on unconscious patients
- **✅ Real condition detection** - Uses actual condition types (`minor_bleeding`, `pain`, `infection`) from medical system classes

**Smart Consumption Matrix:**
```python
# Medical item consumption logic based on actual medical need
CONSUMPTION_RULES = {
    "surgical_treatment": "Only consumed for damaged soft tissue organs (excludes bones and destroyed organs)",
    "fracture_treatment": "Only consumed for damaged bones (fracture_vulnerable or bone_type properties)",
    "blood_restoration": "Consumed for blood_level < 100 OR minor_bleeding conditions present",
    "wound_care": "Consumed only for minor_bleeding conditions (external wound dressing)",
    "pain_relief": "Always consumed (pain detection complexity)",
    "antiseptic": "Always consumed (infection prevention)"
}
```

**Organ Harvesting and Biotech Foundation (Phase 3.1 → shipped as Phase 2.8):**
- **✅ Organ viability system** - Time-based organ deterioration after death drives harvested-organ condition (`ORGAN_CONDITION_BY_DECAY`)
- **✅ Corpse examination** - `autopsy <corpse>` renders organ inventory with harvested / severed marked absent (PR #186)
- **✅ Organ harvesting commands** - `harvest <organ> from <target>` works on corpses, severed parts, unconscious, AND conscious living targets via the procedure verb set (PR #380, #307)
- **✅ Harvested organ inventory** - Organ items spawn with condition (`pristine` / `damaged` / `putrid`) tracking decay tier at extraction time
- **✅ Foundation for cybernetics** - `install <organ> in <target>` is the inverse of harvest; organ-bound conditions travel with the organ on transfer (PR #379)
- **🎯 Death progression message themes refinement** - Narrative consistency and emotional progression pass still pending

*See ``Phase 2.8: Procedural Surgery System`` below for the full shipped model.*

**Medical System Testing and Validation (Completed September 2025):**
- **✅ Medical conditions** - Extensive testing of bleeding, pain, infection condition preservation and treatment
- **✅ Smart consumption system** - Comprehensive testing of need-based medical item consumption logic
- **✅ Revival mechanics** - Production testing of 6-minute death progression and medical intervention
- **✅ Unconscious patient treatment** - Verified medical procedures work correctly on unconscious patients  
- **✅ Medical specialization** - Tested surgery vs splint specialization with appropriate organ targeting
- **✅ Item consumption accuracy** - Verified items only consumed when actual treatment occurs vs examination only

**Forensic Evidence System (Lower Priority Future Features):**
- **🔨 Death cause attribution** - Enhanced storage of cause of death, weapon used, attacker information *(future enhancement)*
- **🔨 Advanced forensic evidence** - DNA markers, blood typing, time of death analysis *(future enhancement)*  
- **🔨 Decay progression** - Enhanced corpse aging and decomposition mechanics *(future enhancement)*

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

### ⏳ DEATH PROGRESSION SYSTEM (September 2025)
**6-Minute Revival Window:**
- **Time-delayed death** - Characters enter 6-minute dying state instead of instant death
- **Medical intervention window** - Healthcare providers can attempt revival during progression
- **Dramatic tension** - Creates urgency and meaningful medical response opportunities
- **Automatic revival** - Medical system integration allows natural recovery if conditions improve

**Progressive Narrative Experience:**
- **11 message intervals** - Every 30 seconds during 6-minute progression
- **Literary styling** - Chuck Palahniuk/Hunter S. Thompson inspired visceral stream-of-consciousness
- **Emotional progression** - Messages evolve from medical shock to existential acceptance to peaceful transition
- **Universal themes** - Content avoids specific cultural/family references for inclusive player experience
- **Session-aware formatting** - Text centering using death curtain patterns for consistent presentation

**Death Progression Architecture:**
```python
class DeathProgressionScript(DefaultScript):
    """Time-delayed death progression with medical intervention window"""
    
    def at_script_creation(self):
        self.db.total_duration = 360  # 6 minutes
        self.db.message_intervals = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]
        self.db.can_be_revived = True
        
    def _check_medical_revival_conditions(self, character):
        """Check if medical treatment has resolved fatal conditions"""
        # Brain death blocks revival — tracked as Phase 2 of the
        # MEDICAL_COMBAT_AUDIT_AND_REMEDIATION_SPEC remediation plan.
        # Below is the intended shape; the live code in
        # typeclasses/death_progression.py:_check_medical_revival_conditions
        # currently only calls medical_state.is_dead() and will gain
        # this guard when Phase 2 ships.
        brain_organ = character.medical_state.get_organ("brain")
        if brain_organ and brain_organ.current_hp <= 0:
            return False  # Brain death = no revival possible

        # Check overall medical death status
        if character.medical_state and not character.medical_state.is_dead():
            return True  # Medical intervention successful
        return False
        
    def _send_progression_message(self, interval):
        """Send visceral dying narrative to character and observers"""
        messages = self._get_progression_messages()
        character.msg(messages[interval]["dying"])
        location.msg_contents(messages[interval]["observer"], exclude=[character])
```

**Integration Features:**
- **Medical system compatibility** - Automatic revival if fatal conditions resolved
- **Brain death mechanics** - Characters with destroyed brain cannot be revived (medical realism)
- **Consciousness threshold** - Revival eligibility tied to brain organ health and consciousness capacity
- **Progressive brain damage** - Brain deterioration during death progression affects revival chances over time
- **Observer messaging** - Room occupants see progression indicators
- **Script-based timer** - Robust interval system with cleanup and state management
- **Placement descriptions** - Death state visible in room descriptions
- **Debug logging** - Comprehensive Splattercast integration for monitoring

**Revival Mechanics (Currently Functional):**
- **✅ 6-minute revival window** - Medical intervention during death progression works as intended
- **✅ Medical system integration** - Automatic revival when fatal conditions resolved
- **✅ Death progression messaging** - Complete narrative experience with observer integration
- **Future enhancement potential** - Brain death mechanics could be added but current system is sufficient

**Progression Message Themes:**
- **Early stages (30-120s)** - Medical shock, surreal sensory experiences, dark humor
- **Middle stages (150-240s)** - Existential reflection, memory fragmentation, acceptance
- **Final stages (270-330s)** - Peaceful transition, universal human experiences, gentle release

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

**Phase 3.1 - Organ Harvesting & Biotech Foundation (✅ MOSTLY SHIPPED — see Phase 2.8):**
- **✅ Organ harvesting commands** - `harvest <organ> from <target>` via procedure verb set (PR #380); works on corpses, severed parts, unconscious, and conscious targets
- **✅ Corpse examination system** - `autopsy <corpse>` (PR #186); organ inventory with absent / damaged status
- **✅ Harvested organ inventory management** - Organ items spawn with decay-tier condition; PR #200's sever-overlay carries harvest provenance onto severed items
- **✅ Foundation for cybernetics integration** - `install` is the inverse of `harvest`; three-tier condition model (PR #378/#379) ensures organ-bound conditions travel correctly during transfer
- **🎯 Death progression message enhancement** - Narrative theme refinement still pending
- **🎯 Progressive organ failure system** - Time-based post-death organ deterioration with realistic timelines (brain ~3 rounds, heart ~8, liver ~12, etc.)

**Phase 3.2 - Cybernetics & Prosthetics (✅ FOUNDATION SHIPPED, 🔮 ELABORATION PENDING):**
- **✅ Organ transplant procedures** - `incise → harvest → install → suture` chain (PR #380); scan-based architecture (PR #378) ensures replaced organs immediately reflect functional state
- **✅ Procedure verb framework** - Extensible dispatch (`world/medical/procedures.py`) supports new verbs (e.g., future `graft`) without architectural rework
- **🎯 ``operate`` charting menu** - Menu-driven planner over the procedure dispatch (see Phase 5)
- **🔮 Limb replacement mechanics** - Prosthetics and cybernetic limb systems built on the install/harvest flow
- **🔮 Cybernetic enhancement systems** - Performance-boosting implants and modifications
- **🔮 Bio-compatibility mechanics** - Rejection, adaptation, and maintenance systems
- **🔮 Mr. Hands integration** - Seamless body modification system compatibility

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

### Spinal Anatomy, Decapitation & Combat Severance

This is the **canonical reference** for the spinal/decapitation/severance
anatomy model (combat-sever Phases A–D, issues #243/#245/#247/#249). The
detailed *identity / forensic* consequences live in
`IDENTITY_RECOGNITION_SPEC.md` § "Combat-Driven Severance"; the *vital-area
targeting* math lives in `MODULAR_ARMOR_SYSTEM_SPEC.md` § "Vital Area
Targeting Ability". This section owns the underlying anatomy and death wiring.

#### Two spinal organs

The anatomy models the spine as **two distinct organs**, not one:

| Organ | Container | Destroyable? | Capacity | Loss effect |
|-------|-----------|--------------|----------|-------------|
| `cervical_spine` | `neck` | **Yes** (`can_be_destroyed`) | `neck_integrity` | Decapitation → death |
| `thoracolumbar_spine` | `back` | **No** (`cannot_be_destroyed`) | `moving` | Paralysis (`paralysis_if_destroyed`) |

`cervical_spine` is the **decapitation locus**: it bundles the airway, the
great vessels, and the cord at the neck, so bringing it to 0 HP is immediately
fatal. `thoracolumbar_spine` is the thoracic/lumbar column in the back — it
contributes `1.0` (total) to the `moving` capacity and gates paralysis, but it
cannot be destroyed. (It was renamed from a plain `spine` in #254 to remove the
ambiguity with `cervical_spine`; a one-shot DB migration renamed the persisted
organ key on existing characters.)

#### `neck_integrity` capacity & death wiring

```python
# world/medical/constants.py — BODY_CAPACITIES
"neck_integrity": {
    "organs": ["cervical_spine"],
    "fatal_threshold": 0.0,
    "directly_fatal": True,
    # ...
}
```

`MedicalState.is_dead()` (see the corrected listing below) treats
`neck_integrity <= 0.0` as a death condition, alongside `blood_pumping`,
`breathing`, and `digestion`. A destroyed cervical spine drives
`neck_integrity` to 0.0 and reads as a clean decapitation death without
perturbing the lungs' contribution math.

#### Hit routing to the neck

`neck` resolves to a **single organ** (`cervical_spine`), so neck hits are
deterministic at the organ-selection stage and concentrate 100% of post-armor
damage on the kill organ. The neck is nonetheless a **low-probability**
location: its only organ carries `hit_weight: "rare"` (8) versus `uncommon`
(15) for the chest and `common` (25) for limbs.

#### Combat-driven severance trigger (Phase C)

Body parts come off **during combat** (not only via the corpse `sever`
command) when a location's representative bone hits 0 HP **and** the damaging
blow used an edged weapon:

```python
# world/combat/constants.py
SEVERING_INJURY_TYPES = frozenset({"cut", "stab", "laceration"})
```

`ArmorMixin.take_damage` detects a freshly-destroyed representative bone and,
if the injury type is severing, applies the severance. For the neck, the death
hook defers realisation: `db.decapitation_pending` is set during the synchronous
hit and consumed later in the asynchronous death flow
(`_create_corpse_from_character`), which spawns a `SeveredHead`. See the
IDENTITY spec for the full Phase A–D narrative and the item-retention rules.

#### Vital-location derivation (`_get_vital_locations`)

The set of **vital body locations** used by the combat hit-location bias is
derived dynamically (issue #251), not hardcoded:

```python
# world/medical/constants.py
LETHAL_CAPACITY_NAMES = (
    "blood_pumping", "breathing", "digestion", "neck_integrity", "consciousness",
)
```

`_get_vital_locations` maps each lethal capacity's `organs` to their
`container`, yielding `{head, chest, neck, abdomen}` for the stock anatomy.
Because it is data-driven, `neck` is vital *by data* (cervical spine →
neck_integrity), and anatomy changes propagate automatically. See
`MODULAR_ARMOR_SYSTEM_SPEC.md` for how the vital set feeds targeting bias.

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
        # Death from vital capacity failure. These mirror the lethal members
        # of LETHAL_CAPACITY_NAMES (consciousness is unconsciousness, not death,
        # so it is excluded here). See "Spinal Anatomy, Decapitation & Combat
        # Severance" above.
        if self.calculate_body_capacity("blood_pumping") <= 0.0:  # Heart
            return True
        if self.calculate_body_capacity("breathing") <= 0.0:      # Lungs
            return True
        if self.calculate_body_capacity("digestion") <= 0.0:      # Liver
            return True
        if self.calculate_body_capacity("neck_integrity") <= 0.0:  # Decapitation (#243)
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
- **Death conditions**: Destruction of vital organs (heart, both lungs, liver, or the `cervical_spine` → decapitation) = death
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
- **Neck integrity = 0**: Death (cervical spine destroyed → decapitation, #243)
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
        "applicable_to": ["painkillers", "stimpaks", "adrenal boosters", "toxins", "vaccines"],
        "consumption_logic": "need-based analysis prevents waste on inappropriate conditions"
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
- **Smart Resource Management**: Direct medical state analysis prevents wasteful consumption on healthy/inappropriate patients
- **Architectural Robustness**: Need-based consumption logic replaces fragile message parsing with direct condition inspection

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
#
# Two render paths share one summarizer so multi-wound output is concise:
#   - append_wounds_to_longdesc        -> location already has a longdesc
#   - get_standalone_wound_description -> location has wounds but no longdesc
# Both delegate to _summarize_location_wounds.

def append_wounds_to_longdesc(original_desc, character, location, looker=None):
    """Append a wound summary onto an existing longdesc for a location."""
    summary = _summarize_location_wounds(
        [w for w in get_character_wounds(character) if w['location'] == location],
        character,
    )
    if not summary:
        return original_desc
    # Strip the summary's terminal period (preserving any |n reset) so the
    # combined sentence flows, then re-terminate.
    return f"{original_desc} {summary.rstrip('.|n')}."

def get_standalone_wound_description(character, location, looker=None):
    """Return a standalone wound sentence for a location with no longdesc."""
    return _summarize_location_wounds(
        [w for w in get_character_wounds(character) if w['location'] == location],
        character,
    )

def _summarize_location_wounds(location_wounds, character=None):
    """One wound -> type/stage description; two or more -> one compound line."""
    prioritized = _prioritize_wounds_for_display(location_wounds)
    if len(prioritized) == 1:
        return get_wound_description(**prioritized[0], character=character)
    return _compound_phrase(prioritized[0], len(prioritized) - 1, character)
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

**Multiple Wound Handling** (consolidated in #258):
- Both render paths share one summarizer, `_summarize_location_wounds`
  (`world/medical/wounds/longdesc_hooks.py`):
  - **Locations with longdesc** — `append_wounds_to_longdesc` appends the
    summary as a trailing clause.
  - **Locations without longdesc** — `get_standalone_wound_description`
    returns the summary as its own sentence (consumed by
    `typeclasses/appearance_mixin.py`).
- **One wound**: rendered via the type/stage-specific
  `get_wound_description` (the per-injury-type message modules).
- **Two or more wounds at the same location**: collapse into a single
  concise line via `_compound_phrase` — the worst wound (severity → stage
  priority) plus a count of the rest ("a grievous cut wound **and another
  wound** mark the left arm", or "**and several other wounds**"), rather
  than concatenating every wound's full description. An all-healed mix
  renders a calm, skintone-colored "multiple old wounds" summary.
- **Future hook (not yet built)**: per-injury-type compound templates,
  mirroring the single-wound `messages.<type>.WOUND_DESCRIPTIONS` dicts. A
  later pass can add `messages.<worst_type>.COMPOUND_DESCRIPTIONS[stage]`,
  `random.choice` a variant, and fall back to `messages.generic` then to the
  generic phrasing — exactly how `get_wound_description` resolves single
  wounds. The type message modules are intentionally left untouched until
  then; `_compound_phrase` is the single seam to flip.

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

### Phase 2.8: Procedural Surgery System - ✅ COMPLETED (June 2026)

PRs #378 / #379 / #380 (issue #307) replaced the open-ended ``surgery <target>`` button with a procedural verb set that hands order-of-operations onus to the player. The system is anchored on a three-tier condition model and a scan-based architecture so organ replacement (cybernetics included) flows naturally through the same mechanics.

#### Three-Tier Condition Model (PR #378 / #379)

Conditions now bind at one of three scopes:

* **Body-bound** — systemic state (blood level, total pain, consciousness). Persists across organ replacement; swapping a kidney does not reset a sepsis condition.
* **Location-bound** — attached to a body location (chest infection, leg fracture). Treatments target the location. Carries forward through PR #200's sever-overlay when the location is severed.
* **Organ-bound** — attached to an individual organ (heart arrhythmia, damaged liver). Travels with the organ on harvest and install — install a damaged heart and the recipient inherits its arrhythmia.

The three tiers share a common ``MedicalCondition`` base but specialise treatment-correlation: splints resolve location-bound fractures; organ-specific treatments resolve organ-bound damage; systemic drugs resolve body-bound infection. See ``world/medical/conditions.py``.

#### Scan-Based Architecture (PR #378)

Per #378, condition modifiers re-derive from the current organ snapshot on each scan rather than mirroring an internal table. Replacing an organ rolls the modifier set forward automatically — no cleanup pass required. This was the predicate for shipping harvest/install without organ-state leak across transplants.

#### Procedure Verb Set (PR #380)

Four verbs, all gated on a surgical kit in inventory:

| Verb | Syntax | Delay |
| --- | --- | --- |
| ``incise`` | ``incise <target> at <location>`` | 6s |
| ``harvest`` | ``harvest <organ> from <target>`` | 18s |
| ``install`` | ``install <organ> in <target>`` | 18s |
| ``suture`` (alias ``stitch``) | ``suture <target>`` | 9s |

All four operate on a unified ``get_organ_snapshot`` accessor that handles living characters, corpses, severed heads, and severed appendages identically. Consistency is the learning surface — practising on corpses transfers directly to operating on living patients.

Skill formula (G.R.I.M., matching the formula at "Medical Treatment Formula" below):

```python
medical_effectiveness = (intellect * 0.75) + (motorics * 0.25)
```

Procedure base difficulty is **12** (``PROCEDURE_BASE_DIFFICULTY``), with **+5** when the patient is conscious (resistance) and **−3** when anesthetized / corpse / severed (no resistance, full focus). The legacy ``SURGERY_BASE_DIFFICULTY = 75`` constant remains in ``world/medical/constants.py`` for the moment but is dead — the procedure dispatch reads the new constants from ``world/medical/procedures.py``. Future cleanup pass can remove it.

#### Tri-Modal Outcomes

Each verb resolves to success / partial / failure on a ``3d6 + skill`` vs. difficulty roll. Failure modes seed conditions on the patient:

* ``incise`` failure → no incision opens + location-bound ``InfectionCondition`` seed
* ``harvest`` failure → organ extracted but condition tier worse, plus ``InfectionCondition`` and ``PainCondition`` seeds (pain skipped on unconscious targets)
* ``install`` failure → organ doesn't take + ``InfectionCondition`` seed
* ``suture`` failure → closes but seeded ``InfectionCondition``

Failure-consequence *paths* are real and tested; *severity values* are placeholders pending treatment-depth calibration.

#### Anesthesia Is a Drug, Not a Verb

There is no ``anesthetize`` verb. Anesthesia goes through the existing consumption surfaces (``inject anesthetic into <target>``, etc.). The procedure dispatch reads ``target.is_unconscious()`` to apply the difficulty bonus and skip pain seeding — the unconscious state itself is the contract, not its cause.

Conscious-patient procedures accumulate ``PainCondition`` seeds during each verb's resolution, scaled by the verb's invasiveness (``CONSCIOUS_PAIN_SEVERITY`` in ``procedures.py``).

#### CmdApply Upgrade

``apply`` is now location-precision aware: ``apply <item> on <target>'s <location>`` targets a specific body location. When the location is an internal container (``head``, ``chest``, ``abdomen``, ``back``, ``neck``, ``groin``), ``apply`` rejects unless an incision is currently open at that location. Surface treatments (bandages on skin) skip the requirement. The legacy ``surgery`` / ``operate`` aliases on ``apply`` were removed — the procedure verbs replace them entirely.

Note that the ``TOOL_APPROPRIATENESS`` table below still records surgical kits as effective for severe internal bleeding, infection cleaning, and complex fractures — but surgical kits are now consumed as a *tool prerequisite* for the procedure verbs, not by ``apply``. The effectiveness mapping is design intent; the consumption surface moved.

#### Forensics Pipeline Continuity

The ``harvested`` injury type (``world/medical/wounds/messages/harvested.py``) is synthesised by ``world.medical.procedures._mark_organ_removed`` after a successful harvest on a corpse-shaped source. This feeds autopsy narrative and PR #200's sever-overlay carry-forward unchanged. The legacy ``commands/forensics.py:CmdHarvest`` was retired in the cleanup pass following PR #380; its forensics-side responsibilities moved into the procedure dispatch.

#### Files

* ``world/medical/procedures.py`` — dispatch module
* ``commands/CmdSurgical.py`` — four command classes
* ``commands/CmdConsumption.py`` — ``CmdApply`` location-precision upgrade
* ``world/tests/test_surgical_procedures.py`` — 34 tests covering snapshot accessor, incision lifecycle, skill/difficulty, roll outcomes, failure seeders, resolver outcomes, and ``_mark_organ_removed`` wound synthesis

See also: Phase 5 "Proposed: ``operate`` Charting Command" — a future menu-driven planner that drives the same procedure dispatch as a higher-level surface.

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
- [ ] `operate` charting menu (see below)

### Phase 2.9: `operate` Charting Command - ✅ COMPLETED (June 2026)

PRs in the #307 follow-on arc shipped the `operate` charting command alongside the procedural verbs. The verbs stay the canonical "what's happening right now" layer; `operate` is the canonical "here is the plan" layer.

This section was authored as a forward-looking proposal and is retained as the design rationale for the menu surface. Where the implementation diverged from the original plan, deviations are called out inline below — the design intent should be read alongside the **As Built** notes for current behaviour.

#### Intent and Positioning

`operate <target>` opens an EvMenu (per `EVMENU_PATTERNS_SPEC.md`) where a surgeon can **diagnose** the patient, **chart** a sequence of procedures and treatments, then either **commence** the plan or **leave the chart** on the patient for asynchronous handoff. Same dispatch as the verbs underneath; different ergonomic surface.

The two surfaces serve different play modes:

| Layer | When it's right | What it optimises for |
| --- | --- | --- |
| Procedure verbs (`incise`, `harvest`, `install`, `suture`) | Back-alley triage, mid-combat field work, single-step improvisation | Tension, immediacy, per-step risk |
| `operate` chart | Planned multi-step transplants, training, async handoff, complex diagnoses | Deliberation, sequencing, persistence across sessions |

A surgeon mid-firefight uses the verbs. A surgeon at a hospital bed plans with `operate`, optionally hands the chart to a colleague, and either party can switch to the verbs when the situation demands it. The chart is never compulsory — it's a planning aid the procedural layer is happy to ignore.

#### Visual Design Conventions

The menu inherits two existing conventions and breaks from a third:

**EvMenu patterns from ``describe`` (``commands/CmdCharacter.py`` ``_DescribeEvMenu``).**

* Custom ``EvMenu`` subclass that suppresses the default decorations — ``nodetext_formatter`` / ``options_formatter`` / ``node_formatter`` collapse to pass-through, so each node owns its full visual.
* Top-level node renders its own numbered list with column-aligned label and ``::`` separators:
  ``  |w 1.|n |WLabel column     :: value preview|n``
* ``x`` is the universal exit token; ``_default`` is the sole option, routing through a ``_process_*_choice`` dispatcher that validates the input and returns the next node name.
* All transient menu state lives on ``caller.ndb._operate_*`` and is cleared by a ``cmd_on_exit`` callback.
* Per ``EVMENU_PATTERNS_SPEC.md``: text-input nodes guard ``if raw_string and raw_string.strip():`` (not bare ``if raw_string:``) to avoid the blank-input regression.

**Chrome from ``score`` (``commands/CmdCharacter.py`` ``CmdStats``).**

* Box-drawn frame using the shared ``BOX_TOP_LEFT`` / ``BOX_HORIZONTAL`` / ``BOX_VERTICAL`` / ``BOX_TEE_RIGHT`` / ``BOX_TEE_LEFT`` / ``BOX_BOTTOM_LEFT`` constants.
* ``COLOR_SUCCESS`` (medical-green) for the chrome — the colour says *medical readout* the same way ``score`` says *evaluation report*.
* Fixed 48-character visible content width inside the box, with row content left-padded to keep the right border aligned.
* Tee separators (``BOX_TEE_RIGHT … BOX_TEE_LEFT``) divide the readout into logical bands: header → diagnose summary → chart steps → action options.
* A header band with the title and patient-identity row, mirroring the ``score`` subject + file-reference layout. ``operate`` substitutes patient identity and chart status for those rows.

**The break from ``score``: NOT centered.**

``score`` wraps its output in ``_center_text`` and renders flush-centre. ``operate`` does **not**. Rationale: the chart is a working document, not a presentation. A surgeon scans, edits, and re-scans many times in one session — centering forces the eye to re-anchor on every refresh, whereas a left-flush block sits in a stable reading column and matches the editing posture of ``describe``. Operationally, ``operate`` skips the ``_center_text`` call and emits the box flush to the left margin.

A practical consequence: the box width is set from the menu's content needs (48 inside chrome, matching ``score``), not from terminal-width centering math. Lines longer than the content width wrap inside cells; the chrome stays square.

#### Chart Data Structure

Chart persists on `target.db.medical_chart` as a dict:

```python
target.db.medical_chart = {
    "version": 1,
    "authored_by": <surgeon dbref>,
    "authored_at": <timestamp>,
    "last_modified_by": <surgeon dbref>,
    "last_modified_at": <timestamp>,
    "status": "draft" | "in_progress" | "completed" | "aborted",
    "steps": [
        {
            "id": <int, stable across edits>,
            "verb": "incise" | "harvest" | "install" | "suture"
                  | "inject" | "apply" | "spray" | "inhale",
            "args": {...},          # verb-specific, mirrors the command argspec
            "notes": <str>,         # surgeon's free-text annotation
            "status": "pending" | "running" | "done" | "skipped" | "failed",
            "outcome": <str|None>,  # populated after execution
        },
        ...
    ],
    "diagnoses": [
        {"location": "chest", "finding": "...", "noted_by": <dbref>, "at": <ts>},
        ...
    ],
}
```

Survives reload/restart per Evennia attribute semantics. Step IDs are stable so a surgeon resuming an interrupted plan can reorder and edit individual steps without losing references. `args` mirrors each command's existing argument shape — the dispatcher reconstructs the same call the verb would make at the prompt, so there's only one execution path to test and maintain.

#### Menu Wireframe

Top-level node rendered with ``score``-style box chrome (``BOX_*`` constants, ``COLOR_SUCCESS`` chrome colour, 48-char content width, tee separators between bands), flush-left (no ``_center_text``). Row content follows the ``describe`` numbered-list pattern (``num. label :: value``). The ``x`` exit token is universal.

```
┌────────────────────────────────────────────────┐
│ SURGICAL CHART                                 │
│ Patient: a battered drifter                    │
│ Chart:   draft · 3 steps · Dr. Vance, 14m ago  │
├────────────────────────────────────────────────┤
│ Vitals:  unconscious                           │
│ Notes:   severe bleeding (chest) · pain 3      │
│ Open incisions: none                           │
├────────────────────────────────────────────────┤
│ Steps charted:                                 │
│   1. incise chest                   [pending]  │
│   2. harvest left lung              [pending]  │
│   3. suture chest                   [pending]  │
├────────────────────────────────────────────────┤
│  1. Diagnose patient                           │
│  2. Add procedure step                         │
│  3. Add treatment step                         │
│  4. Reorder / remove steps                     │
│  5. Annotate step                              │
│  6. Commence chart                             │
│  7. Save chart and exit                        │
│  8. Discard chart                              │
│  x. Exit                                       │
└────────────────────────────────────────────────┘
```

Production rendering substitutes the ASCII box-drawing characters for the project's ``BOX_*`` Unicode constants and wraps each cell line in ``COLOR_SUCCESS``…``COLOR_NORMAL``. The whole block emits flush-left; no ``_center_text`` call.

Child nodes follow the same EvMenu text-input patterns ``describe`` uses (``if raw_string and raw_string.strip():`` guards, ``_default`` routing, ``cmd_on_exit`` cleanup). Reordering uses a numbered swap-target pattern rather than freeform input. "Add procedure step" walks the surgeon through verb → target → location → notes; each prompt validates against the patient's current state (e.g., the location picker for `harvest` shows only locations with extractable organs).

#### Diagnose Pane

The diagnose node is the consolidation surface for medical observation. Today the same data is scattered across `medical info`, autopsy output, and inferred-from-flavor text. The pane should aggregate:

- **Organ snapshot** — every container with its organ contents and per-organ condition tier
- **Condition stack** — bleeding / pain / infection / fractures / organ-bound conditions, with severity and location
- **Open incisions** — locations currently incised, who opened them, how long ago
- **Cybernetic vs. biological tags** — visible to surgeons with the appropriate skill
- **Prior chart history** — previous chart runs on this patient, who authored, outcomes
- **Recent vitals trajectory** — unconscious/conscious transitions, recent damage events

Surgeon's medical skill (G.R.I.M. — `(intellect * 0.75) + (motorics * 0.25)`) gates the depth of the reveal. Low skill shows surface findings (visible bleeding, gross fractures); higher skill surfaces internal organ condition and cybernetic identification. This is the same difficulty ladder as the procedure verbs — consistency for learning.

The pane is read-only as a diagnostic surface but offers a "note a finding" action that appends to the chart's `diagnoses` list, giving the surgeon a place to record observations that other surgeons can see on handoff.

#### Step Validation and Prerequisites

The dispatcher validates each step against the patient's current state at the moment of execution, not at the moment of charting. This matters because the patient's state can change between sessions. Validation rules:

| Verb | Prerequisite check |
| --- | --- |
| `incise <loc>` | location is a valid internal container; not already incised |
| `harvest <organ>` from internal location | location currently incised; organ still present |
| `harvest <organ>` from external (severed parts, corpse) | organ still present |
| `install <organ>` in internal location | location currently incised; donor organ on hand; recipient slot vacant |
| `suture <loc>` | location currently incised |
| `inject` / `apply` / `spray` / `inhale` | item still on hand; target reachable |

Failure modes per step:

- **Hard fail** (step cannot run): mark `status: "skipped"`, surface a prompt-or-continue choice to the surgeon ("the left lung is no longer present — skip step or abort chart?")
- **Soft fail** (verb dispatch fails its roll): mark `status: "failed"`, record `outcome`, continue to next step (surgeon's plan accounted for risk; subsequent steps may compensate)

Charting *can* enqueue steps that aren't currently valid (e.g., chart `harvest` before the prior `incise` has executed) — the validation runs at execution time, not chart time, so plans can include future state.

#### Example Session: Lung Transplant

Walk-through of a routine multi-step procedure:

```
> operate patient

[ menu opens, status: empty, vitals: unconscious post-anesthetic ]

→ Add procedure step
  Verb? incise
  Location? chest
  Notes? "midline approach"

→ Add procedure step
  Verb? harvest
  Organ? left lung
  Notes? "diseased — discard"

→ Add procedure step
  Verb? install
  Organ? donor lung (from inventory)
  Location? chest
  Notes? "cross-match confirmed"

→ Add procedure step
  Verb? suture
  Location? chest
  Notes? ""

→ Add treatment step
  Verb? inject
  Item? antibiotic
  Notes? "post-op prophylaxis"

→ Commence chart
  Confirm? yes

[ dispatcher executes step 1 (incise, 6s delay) → step 2 (harvest, 18s)
  → step 3 (install, 18s) → step 4 (suture, 9s) → step 5 (inject, instant) ]

Chart completed. 5/5 steps succeeded. Patient stable.
```

If the patient regained consciousness between charting and execution (anesthesia wore off), step 1 picks up the conscious-patient +5 difficulty automatically. If the donor lung was lost between charting and execution, step 3 hard-fails and prompts the surgeon.

#### Execution Flow ("Commence")

The dispatcher is a thin wrapper around the existing per-verb resolvers in `world/medical/procedures.py`:

```python
def commence_chart(surgeon, target):
    chart = target.db.medical_chart
    chart["status"] = "in_progress"
    _run_next_step(surgeon, target, chart, step_idx=0)

def _run_next_step(surgeon, target, chart, step_idx):
    if step_idx >= len(chart["steps"]):
        chart["status"] = "completed"
        return
    step = chart["steps"][step_idx]
    if not _validate_step(target, step):
        step["status"] = "skipped"
        # prompt surgeon: skip-and-continue / abort
        return
    step["status"] = "running"
    # Dispatch into the same path the verb would take, with a
    # continuation callback so the next step fires after delay.
    start_procedure(
        surgeon, target, step["verb"], step["args"],
        on_complete=lambda outcome: _step_finished(
            surgeon, target, chart, step_idx, outcome,
        ),
    )

def _step_finished(surgeon, target, chart, step_idx, outcome):
    step = chart["steps"][step_idx]
    step["status"] = "done" if outcome.ok else "failed"
    step["outcome"] = outcome.summary
    _run_next_step(surgeon, target, chart, step_idx + 1)
```

The `on_complete` callback is the only extension to the existing procedure dispatch — verbs already use `evennia.utils.delay`, so the chart runner hooks the same staging.

#### Interruption Semantics

- **Surgeon disconnect mid-chart.** The currently-running step continues to its resolver (the existing verb behaviour). Subsequent steps do not auto-resume. Chart status flips to `aborted` with `last_step_completed` recorded. Another surgeon can pick up the chart and resume from the next pending step.
- **Combat interrupts surgeon.** The current step is interrupted via the existing `interrupt_procedure` path. Chart aborts. No automatic recovery — the surgeon must re-`operate` and resume manually.
- **Patient moves / dies.** Death halts the chart immediately and flips status to `aborted`; subsequent diagnostic value of the chart is preserved for autopsy. Movement aborts the current step per the existing procedure interrupt rules.
- **Resume by a different surgeon.** Any surgeon with permission can open `operate` on the patient, see the chart's pending steps, and choose *Commence (resume from step N)*. This is the explicit handoff path.

#### Permissions and Visibility

| Action | Who can do it |
| --- | --- |
| Read the chart (diagnose pane) | Any character with non-zero medical skill in line of sight of the patient |
| Author / edit a chart | The character who initiated `operate` (becomes `authored_by`); subsequent edits permitted to anyone with edit permission (see below) |
| Grant edit permission | The chart author, via a menu action; defaults to author-only |
| Commence the chart | Anyone with edit permission |
| Resume an aborted chart | Anyone with edit permission |
| Annotate diagnoses | Anyone with read permission (additive only) |
| Patient's own visibility | The patient sees the chart in `operate` when conscious (consent model); unconscious patients have no recourse — narrative tension is intentional |

The patient-consent model is intentionally light: there's no hard block on charting an unconscious or unwilling patient, and the resulting chart sits on `target.db.medical_chart` regardless. The fiction is that consent and ethics are roleplay concerns, not enforced mechanics — paralleling how the procedure verbs themselves don't require consent.

#### Display Surface

The chart surfaces in three places beyond the menu itself:

1. **`medical info <target>`** — gains a "Active chart" footer if one is present, naming the author and step count. Full chart contents require opening `operate`.
2. **Look at patient** — characters with sufficient medical skill see a subtle observable cue, e.g., *"a paper chart is clipped to a board at the foot of the bed"* or *"a tablet rests on her chest, displaying surgical annotations"*. Flavour scales with setting.
3. **Autopsy** — completed and aborted charts are surfaced in autopsy output as the medical history record, providing forensic narrative even when the patient died on the table.

The chart is *not* surfaced in standard `look` output to non-medical observers — it requires skill or `operate` access.

#### Integration with Existing Systems

- **Procedure verbs.** Single execution path: chart dispatcher and direct verb invocation both go through `start_procedure`. Adding new verbs (e.g., a future `graft`) automatically makes them chartable with no menu changes beyond surfacing them in the verb picker.
- **Consumption commands.** Treatment steps (`inject`, `apply`, `spray`, `inhale`) reuse the existing consumption command implementations via internal dispatch. The chart's `args` carries the same item/target/location parameters the player would have typed at the prompt.
- **Conditions and tickers.** No new condition types required. Failure-mode seeding (infection, pain, organ damage) already lives in the procedure resolvers and applies identically whether the verb was invoked directly or via chart.
- **Forensics / autopsy.** Completed chart records become first-class evidence in autopsy output. Aborted charts on a deceased patient provide narrative context for cause of death.
- **G.R.I.M. skill.** Diagnose-pane reveal depth and procedure success rolls share the same formula; surgeons don't learn separate skill ladders for planning vs. execution.

#### Phased Implementation Plan

The proposal naturally factors into shippable slices, each with its own value:

1. **MVP: Read-only chart + manual commence.** Add `target.db.medical_chart` schema, a minimal menu with Diagnose / Add step / Commence / Save, and the chart-runner dispatcher. No edit permissions, no annotations, no autopsy integration. Single surgeon, single chart, basic flow.
2. **Handoff + resume.** Add edit-permission delegation, resume-from-step-N, multi-author chart edits, status transitions through `aborted` and back.
3. **Diagnostic depth.** Skill-gated reveal in the diagnose pane, cybernetic identification, diagnosis-note recording, vitals trajectory.
4. **Display integration.** `medical info` footer, look-at-patient cue, autopsy integration.
5. **Stretch: templates and recipes.** Saved procedure templates ("standard appendectomy"), faction-shared chart libraries, billing hooks — all explicitly out of scope for #307-followup but architecturally compatible.

Each phase is independently useful and testable; nothing in a later phase requires a redesign of earlier phases.

#### Open Questions

- **Should aborted charts auto-purge after some time, or persist indefinitely?** Leaning persist — narrative value outweighs storage cost, and autopsy use depends on retention.
- **Chart-driven anesthesia loop.** If anesthesia wears off mid-chart and pain spikes, should the dispatcher pause and prompt for re-anesthetizing, or just barrel through with the conscious-patient penalty? Probably prompt-with-default-continue, surgeon's call.
- **Multiple concurrent charts on the same patient.** Realistically only one active chart at a time; should drafts queue, or does the menu enforce single-active-chart? Single-active is simpler.
- **Patient-authored "advance directives."** A patient pre-authors a chart on themselves while conscious (DNR, organ donor flags, allergies); other surgeons see it on diagnose. Probably stretch, but the schema accommodates it.
- **NPC use.** Should NPC surgeons (faction medics, hospital staff) chart on patients to telegraph intent? Could be a strong narrative tool; needs AI behaviour design beyond this spec's scope.

#### As Built — Deviations and Realisations

The implementation matches the proposal at the chart-data-structure and procedure-dispatch level. The following deviations and additions are visible in the shipped menu:

* **Visual layout** — the box-drawn `score`-style chrome was replaced with **tree-branched section labels** (`PATIENT` / `CHART` / `OPTIONS` connected with box-drawing characters). The `describe`-style flush-left layout was retained. The current design idiom matches `armor comprehensive`.
* **Charting + treatment unified.** The proposal split "Add procedure step" from "Add treatment step." Implementation collapses to a single "Add procedure step" because treatment verbs (`apply` / `inject` / `spray` / `inhale`) are now dispatched through a future PR-OP3 path; they're skipped with an outcome note today and the surgeon adds them inline once that lands.
* **`amputate` is a procedure verb.** Combat-side severance went through `apply_sever_to_character` / `spawn_severed_head_for_living` directly; the chart now exposes `amputate` as a fifth procedure verb that routes through the same severance pipeline (with surgical-kit gating instead of edged-weapon gating). `CmdSever` retains `amputate` as a command alias.
* **Multi-source pickers.** The suture location picker reads from three sources (open incisions, planned chart steps, severed-organ stumps from the medical state); the install location picker filters slots by species + donor-organ compatibility. See [EVMENU_PATTERNS_SPEC.md](EVMENU_PATTERNS_SPEC.md) "Pattern D — Multi-Source Picker with Status Tags" for the canonical shape.
* **Diagnose pane** is the only proposed sub-feature still pending — currently rolled into the patient panel header (status indicators + open-incision list). The proposal-grade dedicated pane with skill-gated reveal is open work.
* **Target resolution** — `operate <mob>` now correctly finds the body even when severed parts are in the room. Identity-pipeline candidate set excludes `Appendage` / `SeveredHead` items at stage 1; the NPC-fallback in the sdesc matcher falls through to word-boundary when prefix doesn't fire (otherwise `operate rat` couldn't reach a `"a scrawny ragged rat"` mob — the article prefix would defeat the prefix-only match).
* **Chart status fields** — `last_modified_by` is not stored separately; the chart's most-recent step author is implicit in `_step_finished` records. `diagnoses` field is reserved but unused pending the diagnose pane.
* **Tests** — node-level coverage seeded in `world/tests/test_operate_menu.py` (42 tests across the suture picker, install picker, top-choice routing, verb-choice routing). Chart-data layer covered in `world/tests/test_operate_charts.py`.

### Phase 2.10: Severance, Suture Stumps, and Install Picker - ✅ COMPLETED (June 2026)

The procedural verbs and the operate menu went live on a model that mostly worked but accumulated playtest-driven gaps as soon as decapitation and amputation hit real bodies. This phase consolidates the corrective arc:

#### Severance helper module (PR #427)

`world/medical/severance.py` is the single source of truth for severance-related queries. Three functions:

* `compute_severed_containers(target)` — the set of containers carrying at least one organ with `wound_stage="severed"` and `current_hp == 0`. Both gates so a partially-zeroed organ isn't promoted to a severance.
* `compute_cut_points(target)` — the canonical *one-entry-per-severance* set after two collapse rules:
  - **Head cluster** — when `"head"` is in the severed set (brain lives there and is zeroed by `sever_character_body` during any decapitation), every cluster peer from `get_species_severed_head_locations` (face / neck / eyes / ears / hair-or-fur, species-dependent) collapses into a single `"head"` cut point.
  - **Limb chain** — downstream containers whose `get_species_limb_parent` ancestor is also severed collapse into the chain root. Thigh amputation surfaces as `"left_thigh"`; shin and foot ride with it.
* `normalize_sutured_stumps(target)` — returns a `{location: outcome}` dict regardless of underlying storage shape. The legacy flat-list shape (pre-outcome-flavoured renderer) imports each entry as `"success"` outcome.

Three consumers route through these helpers and agree on the answers:

| Consumer | Reads | Purpose |
|---|---|---|
| `world.medical.wounds.wound_descriptions.get_character_wounds` | `compute_cut_points` | Synthetic cut-point wound emission |
| `commands.CmdOperate._list_severed_locations` | `compute_cut_points` − `normalize_sutured_stumps.keys()` | Suture picker entries |
| `world.medical.procedures._resolve_suture` | same | Runtime untreated-stumps set for `suture all` |

Pre-consolidation each consumer reimplemented the cluster + chain filter and the storage-shape shim. Three copies of the same logic; the consolidation collapses to one.

#### Synthetic severance wound contract (PRs #420 / #421 / #422)

`get_character_wounds` was previously emitting one severance wound per severed organ, so a decapitation rendered as "brain destroyed" / "left eye destroyed" / "right ear destroyed" / etc. The renderer now:

* Suppresses *every* per-organ wound at any container in `compute_severed_containers` (subsumes the old head-cluster + limb-chain dual-filter).
* Emits **one** synthetic wound per entry in `compute_cut_points`, matching the corpse-side `apply_sever_to_corpse` shape exactly:
  ```python
  {
      "injury_type": "severed",
      "location": cut_point,
      "severity": "Critical",
      "stage": _stump_stage(character, cut_point),  # see below
      "organ": None,
      "organ_obj": None,
  }
  ```

Same renderer key the corpse path uses, so the live-body view during the death-progression window and the eventual corpse view render identical prose. Routes through `world/medical/wounds/messages/severed.py`.

#### Sutured stump progression (PRs #423 / #426)

`_resolve_suture` now records each cut point it closes in `character.db.sutured_stumps` keyed by location, valued by the suture-roll outcome:

```python
character.db.sutured_stumps = {
    "head": "success",
    "left_arm": "partial",
    "right_arm": "failure",
}
```

`_stump_stage(character, location)` reads the outcome and routes the synthetic wound to one of three flavoured renderer stages — `treated_success`, `treated_partial`, `treated_failure`. `severed.py` carries 3–4 variants per subgroup, so a clean roll reads "carefully sutured shut, the dressing clean" while a botched roll reads "crudely bandaged, the seam pulling dirty." The failure subgroup aligns prose with the existing infection-condition seeding `_resolve_suture` does on a failure outcome.

Backward-compat lives in `normalize_sutured_stumps`: a legacy flat-list `sutured_stumps` reads as `{loc: "success"}`. The picker and runtime never see the legacy shape.

Time-based progression past `treated_<outcome>` (the `healing` and `scarred` stages already populated in severed.py) is parked — needs research on Evennia ticker semantics before wiring.

#### Combat amputation symmetry (PR #428)

`open_incision`'s `surgeon` parameter is now optional (default `None`). `apply_sever_to_character` and `spawn_severed_head_for_living` both call `open_incision` immediately after `sever_character_body`. Result: any severance — combat-driven via `ArmorMixin.take_damage`, chart-driven via `_resolve_amputate` — leaves a recorded incision at the cut point, so the suture verb finds an open wound to close regardless of how the stump came to be.

`_resolve_amputate` retains its own `open_incision` call afterward, which overwrites the location entry to record the chart surgeon as `opened_by` (chart-attribution win); `opened_by` is forensic-only state with no readers. Combat keeps the attacker as `opened_by`.

#### Decapitation pipeline ownership (PR #419)

`spawn_severed_head_for_living` now sets both `head_severed_at_decap = True` *and* `decapitation_pending = True`. The corpse-side cleanup hook in `DeathProgressionScript._create_corpse_from_character` gates on `decapitation_pending` to strip head-cluster prose / wounds and synthesise the neck-stump wound on the corpse. Pre-fix the combat path set `decapitation_pending` upstream but the chart-amputate path didn't — so chart-driven decap left the corpse rendering wounds at every cluster location. Owning both flags inside the spawn makes the cleanup fire regardless of caller.

#### Install picker species + organ filter (PR #431)

`_node_install_location` was reading `_list_containers(target)` (every container on the target) so installing a heart offered every body region as a target. Replaced with `_list_install_locations(target, donor_item)` which converges two paths through one helper:

| Path | When it fires | Source of truth |
|---|---|---|
| **Biological** | Donor's `db.organ_name` is in the target species' organ spec | `get_species_organs(target_species)[organ_name]` — picks display_location if distinct from container, else container |
| **Cyberware** | Donor declares `db.target_container` and / or `db.target_display_locations` | Item-side overrides; the donor doesn't need an entry in the species spec |

Cross-species gate runs first: `donor_item.db.compatible_species` (stamped `[source_species]` at harvest by `_configure_harvested_item`) must include the target's species or the picker shows nothing. Legacy items pre-dating this field fall back to `[source_species]` via the existing harvest provenance.

Each slot is tagged `(empty)` or `(occupied)` based on the slot organ's current HP. Surgeon can still pick occupied slots — the resolver replaces — but the tag warns. Multi-slot capacity (cybernetic limb augmentation — Doctor Octopus arms) is future work and will plug into the same `target_display_locations` declaration without rework.

#### Operate target resolution (PR #425)

Two fixes, two surgical edits:

1. **NPC-fallback in `_match_sdesc`** — when an NPC's `get_sdesc()` returns the bare key (no explicit sdesc set, the default for spawned mobs), the matcher tried prefix-only and silently failed for mob keys that started with an article (`"a scrawny ragged rat"`). Fixed by letting the NPC fallback fall through to the word-boundary check below — `"tom"` → `"Tom Hanks"` (prefix wins), `"rat"` → `"a scrawny ragged rat"` (word-boundary catches it).
2. **Detached-parts filter in `_resolve_target`** — `SeveredHead` / `Appendage` participate in identity (forensic-chain `apparent_uid_at_death`) so they could theoretically end up as identity matches. Surgical commands target whole-body patients only. Filtering `isinstance(obj, Appendage)` out of the stage-1 candidate set means the picker never has detached parts to compete with the body. Detached parts continue routing through stages 2/3 where `autopsy` / `sever` / `harvest` find them.

#### Files

* `world/medical/severance.py` — single-source-of-truth helpers
* `world/medical/wounds/wound_descriptions.py` — `_stump_stage`, simplified cut-point synthesis
* `world/medical/wounds/messages/severed.py` — outcome-flavoured stages, prose stocked
* `world/medical/procedures.py` — `open_incision` made surgeon-optional, `_resolve_suture` simplified via helpers, `_configure_harvested_item` stamps `compatible_species`
* `typeclasses/items.py` — `apply_sever_to_character` + `spawn_severed_head_for_living` call `open_incision`; `apply_severed_head_overlay` drops redundant snapshot write (base `apply_organ_snapshot_overlay` owns it via the super-call)
* `commands/CmdOperate.py` — multi-source suture picker, species-filtered install picker
* `commands/CmdSurgical.py` — detached-parts filter in `_resolve_target`
* `world/search.py` — NPC-fallback word-boundary fall-through
* `world/tests/test_severance_helpers.py` — 13 tests covering the helper module
* `world/tests/test_operate_menu.py` — 42 tests covering picker + routing nodes

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
- **Phase 2.8**: ✅ Procedural surgery system (`incise` / `harvest` / `install` / `suture` / `amputate`) (Completed June 2026)
- **Phase 2.9**: ✅ `operate` charting command — menu-driven surgery planning (Completed June 2026)
- **Phase 2.10**: ✅ Severance helper module, sutured-stump outcome flavour, install picker species filter, combat-amputation incision symmetry (Completed June 2026)
- **Phase 3**: 🔮 Advanced features (cybernetics implementation, multi-slot capacity, healing-tick progression) - Future development

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
