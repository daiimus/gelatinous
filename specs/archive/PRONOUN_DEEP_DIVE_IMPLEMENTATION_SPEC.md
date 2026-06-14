# Pronoun System Deep Dive: Clothing & Longdesc Integration

> **Status:** 🗄 Superseded — the $pron()/FuncParser design here was never built; perspective pronouns shipped via the grammar engine + brace tokens (see GRAMMAR_ENGINE_SPEC, LONGDESC_SYSTEM_SPEC, EMOTE_POSE_SPEC). Kept for historical design context.

> **STATUS: SUPERSEDED / HISTORICAL.** The `$pron()`/FuncParser design proposed here was not implemented. Perspective-aware pronouns shipped via the grammar engine and `{their}`/`{they}` brace tokens instead. See `GRAMMAR_ENGINE_SPEC.md` and `LONGDESC_SYSTEM_SPEC.md` for the actual implementation. Retained for historical design context.

## Overview

This specification focuses on integrating Evennia's `$pron()` system specifically with clothing and longdesc systems to create perspective-aware character descriptions. The goal is to make `look <character>` commands show different text based on who is looking - using "your" when examining yourself vs "his/her/their" when examining others.

## Core Focus: Dynamic Appearance for Clothing & Longdesc

**Target**: Replace static clothing and longdesc descriptions with dynamic, perspective-aware messages that automatically adjust pronouns based on the viewer.

### Current State (Static)
```python
# Self-examination and others see the same text:
"Sterling wears a black hoodie that clings to their frame."
"His face shows weathered features with high cheekbones."
```

### Target State (Dynamic)
```python  
# Self-examination:
"You wear a black hoodie that clings to your frame."
"Your face shows weathered features with high cheekbones."

# Others examining Sterling (male):
"He wears a black hoodie that clings to his frame." 
"His face shows weathered features with high cheekbones."
```

## Technical Architecture

### 1. Gender System Foundation

#### Character.gender Property (No Command Needed)
```python
# typeclasses/characters.py
class Character(ObjectParent, DefaultCharacter):
    sex = AttributeProperty("ambiguous", category="biology", autocreate=True)
    
    @property
    def gender(self):
        """Convert sex attribute to gender for Evennia's pronoun system."""
        gender_mapping = {
            "male": "male",
            "female": "female", 
            "ambiguous": "plural",  # they/them pronouns
            "neutral": "neutral",   # it/its pronouns (rarely used)
            "nonbinary": "plural",  # they/them pronouns
        }
        return gender_mapping.get(self.sex, "plural")
    
    # Gender can be set via existing mechanisms:
    # @set me/sex = male
    # @set me/sex = female  
    # @set me/sex = nonbinary
    # (Character creation will handle this)
```
```

### 2. Dynamic Appearance System

#### Enhanced return_appearance Method
```python
def return_appearance(self, looker, **kwargs):
    """
    Dynamic appearance using msg_contents() for perspective-aware descriptions.
    
    This method now sends different messages to the looker vs others watching,
    enabling full $pron() integration.
    """
    
    if looker == self:
        # Self-examination uses second person
        self._send_self_appearance(looker, **kwargs)
    else:
        # Others examining uses third person with proper pronouns  
        self._send_other_appearance(looker, **kwargs)
        
def _send_self_appearance(self, looker, **kwargs):
    """Send self-examination messages with 'you' perspective."""
    
    # Base header - consistent for self
    header = f"{self.get_display_name(looker)}"
    looker.msg(header)
    
    # Base description using second person
    base_desc = self.db.desc or ""
    if base_desc:
        processed_desc = self._process_description_with_pronouns(base_desc, perspective="self")
        looker.msg(processed_desc)
    
    # Body descriptions with full $pron() integration
    self._send_body_descriptions_to_self(looker)
    
def _send_other_appearance(self, looker, **kwargs):
    """Send examination messages with proper third-person pronouns."""
    
    # Base header 
    header = f"{self.get_display_name(looker)}"
    looker.msg(header)
    
    # Base description with third person pronouns
    base_desc = self.db.desc or ""
    if base_desc:
        processed_desc = self._process_description_with_pronouns(base_desc, perspective="other")
        looker.msg(processed_desc)
    
    # Body descriptions with full $pron() integration  
    self._send_body_descriptions_to_other(looker)
```

### 3. Perspective-Aware Body Descriptions

#### Self-Examination (Second Person)
```python
def _send_body_descriptions_to_self(self, looker):
    """Send body descriptions using 'you' perspective."""
    
    descriptions = self._get_visible_body_descriptions_with_pronouns(perspective="self")
    
    for location, desc in descriptions:
        # Process with $pron() for self-examination
        msg = f"$pron(You, 2nd) {desc}"
        
        # Use looker as both sender and receiver for self-messages
        self._send_pronoun_message(msg, sender=self, receiver=looker)
        
def _send_body_descriptions_to_other(self, looker):
    """Send body descriptions using third-person perspective."""
    
    descriptions = self._get_visible_body_descriptions_with_pronouns(perspective="other")
    
    for location, desc in descriptions:
        # Process with $pron() for observer perspective
        msg = f"$pron(They) {desc}"
        
        # Use self as sender, looker as receiver for proper pronoun resolution
        self._send_pronoun_message(msg, sender=self, receiver=looker)
```

### 4. Enhanced Clothing Descriptions

#### Dynamic Clothing with $pron()
```python
# typeclasses/items.py - Enhanced clothing descriptions
def get_current_worn_desc_with_pronouns(self, perspective="other"):
    """
    Get clothing description with $pron() integration.
    
    Args:
        perspective: "self" for self-examination, "other" for observers
        
    Returns:
        str: Description with $pron() tags for processing
    """
    base_desc = self.get_current_worn_desc()
    colored_desc = self._process_color_codes(base_desc)
    
    if perspective == "self":
        # Convert to second person $pron() tags
        return self._convert_to_second_person_pronouns(colored_desc)
    else:
        # Convert to third person $pron() tags  
        return self._convert_to_third_person_pronouns(colored_desc)

def _convert_to_third_person_pronouns(self, desc):
    """Convert static pronouns to $pron() for third person perspective."""
    conversions = {
        r'\btheir\b': '$pron(their)',
        r'\bthey\b': '$pron(they)', 
        r'\bthem\b': '$pron(them)',
        r'\bthemselves\b': '$pron(themselves)',
    }
    
    for pattern, replacement in conversions.items():
        desc = re.sub(pattern, replacement, desc, flags=re.IGNORECASE)
    
    return desc

def _convert_to_second_person_pronouns(self, desc):
    """Convert static pronouns to $pron() for second person perspective."""
    conversions = {
        r'\btheir\b': '$pron(your)',
        r'\bthey\b': '$pron(you)', 
        r'\bthem\b': '$pron(you)',
        r'\bthemselves\b': '$pron(yourself)',
    }
    
    for pattern, replacement in conversions.items():
        desc = re.sub(pattern, replacement, desc, flags=re.IGNORECASE)
    
    return desc
```

### 5. Enhanced Longdesc Integration

#### Dynamic Longdesc with Pronouns
```python
# typeclasses/characters.py - Enhanced longdesc system
def _get_visible_body_descriptions_with_pronouns(self, perspective="other"):
    """
    Get body descriptions with full $pron() integration.
    
    Args:
        perspective: "self" or "other" 
        
    Returns:
        list: (location, pronoun_desc) tuples ready for msg_contents()
    """
    from world.combat.constants import ANATOMICAL_DISPLAY_ORDER
    
    descriptions = []
    coverage_map = self._build_clothing_coverage_map()
    longdescs = self.longdesc or {}
    added_clothing_items = set()
    
    for location in ANATOMICAL_DISPLAY_ORDER:
        if location in coverage_map:
            # Clothing description with $pron()
            clothing_item = coverage_map[location]
            if clothing_item not in added_clothing_items:
                desc = clothing_item.get_current_worn_desc_with_pronouns(perspective)
                if desc:
                    descriptions.append((location, desc))
                    added_clothing_items.add(clothing_item)
        else:
            # Longdesc description with $pron() 
            if location in longdescs and longdescs[location]:
                longdesc = longdescs[location]
                pronoun_desc = self._convert_longdesc_to_pronouns(longdesc, perspective)
                descriptions.append((location, pronoun_desc))
    
    return descriptions

def _convert_longdesc_to_pronouns(self, longdesc, perspective):
    """Convert longdesc to use $pron() system."""
    if perspective == "self":
        # Self-examination: "Your chest shows..."
        conversions = {
            r'\b[Hh]is\b': '$pron(Your)',
            r'\b[Hh]er\b': '$pron(Your)', 
            r'\b[Tt]heir\b': '$pron(Your)',
            r'\b[Hh]e\b': '$pron(You)',
            r'\b[Ss]he\b': '$pron(You)',
            r'\b[Tt]hey\b': '$pron(You)',
        }
    else:
        # Observer: "His/Her/Their chest shows..."
        conversions = {
            # Keep existing pronouns but make them $pron() compatible
            r'\b[Hh]is\b': '$pron(his)',
            r'\b[Hh]er\b': '$pron(her)',
            r'\b[Tt]heir\b': '$pron(their)',
            r'\b[Hh]e\b': '$pron(he)',
            r'\b[Ss]he\b': '$pron(she)', 
            r'\b[Tt]hey\b': '$pron(they)',
        }
    
    processed = longdesc
    for pattern, replacement in conversions.items():
        processed = re.sub(pattern, replacement, processed)
    
    return processed
```

### 6. Message Processing System

#### Pronoun Message Handler
```python
def _send_pronoun_message(self, message, sender, receiver):
    """
    Send a message through Evennia's $pron() system.
    
    Args:
        message: String with $pron() tags
        sender: Object that pronouns refer to (usually self)
        receiver: Object receiving the message
    """
    from evennia.utils.funcparser import FuncParser
    from evennia.utils.funcparser import ACTOR_STANCE_CALLABLES
    
    # Create parser with actor-stance callables
    parser = FuncParser(ACTOR_STANCE_CALLABLES)
    
    # Process message with proper context
    processed_msg = parser.parse(
        message,
        caller=sender,        # Who the pronouns refer to
        receiver=receiver,    # Who is seeing the message
        mapping={}           # Additional object references if needed
    )
    
    # Send processed message
    receiver.msg(processed_msg)
```

## Implementation Examples

### Example 1: Self-Examination with Clothing
```python
# Player types: look me
# System processes:

# Header
looker.msg("Sterling Hobbs")

# Base description with second person
msg = "A breathing body without an identity. $pron(Your) eyes flicker, but $pron(you) do not move."
self._send_pronoun_message(msg, sender=self, receiver=looker)
# Result: "A breathing body without an identity. Your eyes flicker, but you do not move."

# Clothing with second person
clothing_msg = "$pron(You) wear a menacing black hoodie that clings to $pron(your) frame like digital shadow incarnate."
self._send_pronoun_message(clothing_msg, sender=self, receiver=looker)  
# Result: "You wear a menacing black hoodie that clings to your frame like digital shadow incarnate."

# Longdesc with second person
longdesc_msg = "$pron(Your) face shows weathered features with high cheekbones."
self._send_pronoun_message(longdesc_msg, sender=self, receiver=looker)
# Result: "Your face shows weathered features with high cheekbones."
```

### Example 2: Observer Examining Character
```python
# Alice examines Bob (male)
# System processes:

# Header
looker.msg("Bob Sterling")

# Base description with third person
msg = "A breathing body without an identity. $pron(His) eyes flicker, but $pron(he) does not move."
bob._send_pronoun_message(msg, sender=bob, receiver=alice)
# Result: "A breathing body without an identity. His eyes flicker, but he does not move."

# Clothing with third person
clothing_msg = "$pron(He) wears a menacing black hoodie that clings to $pron(his) frame like digital shadow incarnate."
bob._send_pronoun_message(clothing_msg, sender=bob, receiver=alice)
# Result: "He wears a menacing black hoodie that clings to his frame like digital shadow incarnate."

# Longdesc with third person
longdesc_msg = "$pron(His) face shows weathered features with high cheekbones."
bob._send_pronoun_message(longdesc_msg, sender=bob, receiver=alice)  
# Result: "His face shows weathered features with high cheekbones."
```

### Example 3: Nonbinary Character Examination
```python
# Taylor examines Sam (nonbinary)
# System processes with plural pronouns:

clothing_msg = "$pron(They) wear a menacing black hoodie that clings to $pron(their) frame like digital shadow incarnate."
sam._send_pronoun_message(clothing_msg, sender=sam, receiver=taylor)
# Result: "They wear a menaging black hoodie that clings to their frame like digital shadow incarnate."
```

## Advanced Features

### 1. Style Commands with Pronoun Messaging
```python
# Player types: rollup hoodie
# System sends message to room:
style_msg = "$You() $conj(roll) up the sleeves of $pron(your) hoodie, exposing $pron(your) forearms."

# To actor: "You roll up the sleeves of your hoodie, exposing your forearms."
# To room: "Bob rolls up the sleeves of his hoodie, exposing his forearms."
```

### 2. Wear/Remove Commands with Pronouns
```python
# Player types: wear hoodie
# System sends message to room:
wear_msg = "$You() $conj(put) on a black hoodie that clings to $pron(your) frame."

# To actor: "You put on a black hoodie that clings to your frame."
# To room: "Alice puts on a black hoodie that clings to her frame."
```

## Implementation Phases

### Phase 1: Foundation (1-2 hours)
- [ ] Add `gender` property to Character class (maps existing `sex` attribute)
- [ ] Test basic `$pron()` functionality with simple messages
- [ ] Create pronoun message processing utility

### Phase 2: Dynamic Appearance Core (3-4 hours)  
- [ ] Refactor `return_appearance()` to use perspective-aware messaging
- [ ] Implement separate self vs. other examination flows
- [ ] Create `_send_pronoun_message()` utility method
- [ ] Test basic character examination with pronouns

### Phase 3: Clothing Integration (2-3 hours)
- [ ] Update `get_current_worn_desc_with_perspective()` for $pron() conversion
- [ ] Implement clothing pronoun conversion (static "their" → $pron() tags)
- [ ] Test clothing descriptions with different gender pronouns
- [ ] Integrate with existing style system

### Phase 4: Longdesc Integration (2-3 hours)
- [ ] Update longdesc descriptions to use $pron() system
- [ ] Implement longdesc pronoun conversion for existing descriptions
- [ ] Test mixed longdesc + clothing scenarios
- [ ] Ensure anatomical ordering is maintained

### Phase 5: Command Enhancement (2-3 hours)
- [ ] Update wear/remove commands with pronoun messaging to room
- [ ] Update style commands (rollup, zip) with pronoun room messages  
- [ ] Test command integration with pronoun system
- [ ] Polish and edge case handling

## Benefits

### Player Experience
- **Immersive Self-Examination**: "You wear..." vs "Alice wears..."
- **Grammatically Correct Pronouns**: Proper he/she/they usage
- **Inclusive Character Creation**: Full gender identity support
- **Natural Language Flow**: Descriptions feel more natural

### Developer Benefits
- **Consistent Pronoun System**: One system for all descriptions
- **Future-Proof Architecture**: Ready for advanced roleplaying features
- **Reduced Maintenance**: Automatic pronoun handling
- **Enhanced Immersion**: Players feel more connected to their characters

## Testing Strategy

### Unit Tests
- `test_character_gender_property()` - Gender mapping functionality
- `test_pronoun_message_processing()` - Message system integration
- `test_perspective_aware_descriptions()` - Self vs other examination
- `test_clothing_pronoun_integration()` - Clothing with pronouns
- `test_longdesc_pronoun_integration()` - Longdesc with pronouns

### Integration Tests  
- **Mixed scenarios**: Characters with clothing + longdescs
- **Multi-gender testing**: Male, female, nonbinary characters
- **Complex descriptions**: Multiple clothing items with pronouns
- **Edge cases**: Missing gender, invalid values

### User Acceptance Tests
- **Character creation flow**: Set gender, examine self
- **Social interactions**: Multiple characters examining each other
- **Clothing interactions**: Wear/remove/style with pronoun messages
- **Emote integration**: Natural posing with pronoun system

## Success Criteria

### Technical Metrics
- [ ] Self-examination shows second person pronouns ("you", "your")  
- [ ] Observer examination shows correct third person pronouns ("he/she/they", "his/her/their")
- [ ] Clothing descriptions dynamically adapt to viewer perspective
- [ ] Longdesc descriptions work seamlessly with pronoun system
- [ ] Existing clothing and longdesc functionality preserved
- [ ] Gender setting works via existing `@set me/sex = <value>` commands

### Player Experience Metrics
- [ ] More immersive self-examination with "you wear..." descriptions
- [ ] Proper grammar in all character descriptions for all genders
- [ ] Seamless integration with existing look, wear, style commands  
- [ ] No breaking changes to current character examination flow
- [ ] Enhanced clothing and longdesc system without complexity

---

**Document Status**: Implementation Ready - Comprehensive deep dive with full technical specification  
**Next Phase**: Begin Phase 1 foundation implementation  
**Expected Timeline**: 2-3 weeks for complete implementation
