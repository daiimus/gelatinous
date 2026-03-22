"""
Appearance Mixin

Provides the longdesc appearance system, body description rendering,
paragraph formatting, pronoun resolution, and the main ``return_appearance``
hook used by Evennia's ``look`` command for Character objects.

Extracted from typeclasses/characters.py in Phase 4 refactoring.
"""


class AppearanceMixin:
    """
    Mixin class providing appearance and longdesc methods.

    Methods:
        get_longdesc_appearance: Build character's longdesc appearance string.
        _get_visible_body_descriptions: Get visible descriptions integrating
            clothing with the longdesc system.
        _format_longdescs_with_paragraphs: Smart paragraph-break formatter.
        _get_anatomical_region: Determine anatomical region for a location.
        has_location: Check if character has a specific body location.
        get_available_locations: Get all body locations this character has.
        set_longdesc: Set a longdesc for a specific location.
        get_longdesc: Get longdesc for a specific location.
        return_appearance: Main appearance rendering (Evennia hook for look).
        _process_description_variables: Process template variables for
            perspective-aware text.
        _get_pronoun: Get specific pronoun based on gender and type.

    Cross-cutting concerns:
        - Calls ``self._build_clothing_coverage_map()`` from ClothingMixin.
        - Reads ``self.longdesc``, ``self.worn_items`` AttributeProperties.
        - Reads ``self.hands`` via ``self.attributes.get()``.
        - Reads ``self.gender`` property from Character core.
    """

    def get_longdesc_appearance(self, looker=None, **kwargs):
        """
        Builds and returns the character's longdesc appearance.

        Args:
            looker: Character doing the looking (optional).
            **kwargs: Additional parameters.

        Returns:
            str: Formatted appearance with base description + longdescs.
        """
        # Get base description
        base_desc = self.db.desc or ""

        # Get visible body descriptions (longdesc + clothing integration)
        visible_body_descriptions = self._get_visible_body_descriptions(looker)

        if not visible_body_descriptions:
            return base_desc

        # Combine with smart paragraph formatting
        formatted_body_descriptions = self._format_longdescs_with_paragraphs(
            visible_body_descriptions
        )

        # Combine base description with body descriptions
        if base_desc:
            return f"{base_desc}\n\n{formatted_body_descriptions}"
        else:
            return formatted_body_descriptions

    def _get_visible_body_descriptions(self, looker=None):
        """
        Get all visible descriptions, integrating clothing with existing
        longdesc system.

        Args:
            looker: Character looking (for future permission checks).

        Returns:
            list: List of (location, description) tuples in anatomical order.
        """
        from world.combat.constants import ANATOMICAL_DISPLAY_ORDER

        descriptions = []
        coverage_map = self._build_clothing_coverage_map()
        longdescs = self.longdesc or {}

        # Track which clothing items we've already added to avoid duplicates
        added_clothing_items = set()

        # Process in anatomical order
        for location in ANATOMICAL_DISPLAY_ORDER:
            if location in coverage_map:
                # Location covered by clothing - use outermost item's current worn_desc
                clothing_item = coverage_map[location]

                # Only add each clothing item once, regardless of how many
                # locations it covers
                if clothing_item not in added_clothing_items:
                    # Use new method with $pron() processing and color integration
                    desc = clothing_item.get_current_worn_desc_with_perspective(
                        looker, self
                    )
                    if desc:
                        descriptions.append((location, desc))
                        added_clothing_items.add(clothing_item)
            else:
                # Location not covered - use character's longdesc if set with
                # template variable processing
                if location in longdescs and longdescs[location]:
                    # Longdesc should have skintone applied
                    processed_desc = self._process_description_variables(
                        longdescs[location], looker,
                        force_third_person=True, apply_skintone=True,
                    )

                    # Add wounds to this location if any exist
                    try:
                        from world.medical.wounds import append_wounds_to_longdesc
                        processed_desc = append_wounds_to_longdesc(
                            processed_desc, self, location, looker
                        )
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

                    descriptions.append((location, processed_desc))
                else:
                    # No longdesc for this location, but check for standalone wounds
                    try:
                        from world.medical.wounds import get_character_wounds
                        wounds = get_character_wounds(self)
                        location_wounds = [
                            w for w in wounds if w['location'] == location
                        ]

                        if location_wounds:
                            # Create standalone wound description for this location
                            from world.medical.wounds import get_wound_description
                            wound = location_wounds[0]
                            wound_desc = get_wound_description(
                                injury_type=wound['injury_type'],
                                location=wound['location'],
                                severity=wound['severity'],
                                stage=wound['stage'],
                                organ=wound.get('organ'),
                                character=self,
                            )
                            descriptions.append((location, wound_desc))
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

        # Add any extended anatomy not in default order (clothing or longdesc)
        all_locations = set(longdescs.keys()) | set(coverage_map.keys())
        for location in all_locations:
            if location not in ANATOMICAL_DISPLAY_ORDER:
                if location in coverage_map:
                    # Extended location with clothing
                    clothing_item = coverage_map[location]
                    if clothing_item not in added_clothing_items:
                        desc = clothing_item.get_current_worn_desc_with_perspective(
                            looker, self
                        )
                        if desc:
                            descriptions.append((location, desc))
                            added_clothing_items.add(clothing_item)
                elif location in longdescs and longdescs[location]:
                    # Extended location with longdesc - apply template variable
                    # processing and skintone
                    processed_desc = self._process_description_variables(
                        longdescs[location], looker,
                        force_third_person=True, apply_skintone=True,
                    )

                    # Add wounds to this extended location if any exist
                    try:
                        from world.medical.wounds import append_wounds_to_longdesc
                        processed_desc = append_wounds_to_longdesc(
                            processed_desc, self, location, looker
                        )
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

                    descriptions.append((location, processed_desc))
                else:
                    # No longdesc for extended location, but check for
                    # standalone wounds
                    try:
                        from world.medical.wounds import get_character_wounds
                        wounds = get_character_wounds(self)
                        location_wounds = [
                            w for w in wounds if w['location'] == location
                        ]

                        if location_wounds:
                            from world.medical.wounds import get_wound_description
                            wound = location_wounds[0]
                            wound_desc = get_wound_description(
                                injury_type=wound['injury_type'],
                                location=wound['location'],
                                severity=wound['severity'],
                                stage=wound['stage'],
                                organ=wound.get('organ'),
                                character=self,
                            )
                            descriptions.append((location, wound_desc))
                    except ImportError:
                        # Wound system not available, continue without wounds
                        pass

        return descriptions

    def _format_longdescs_with_paragraphs(self, longdesc_list):
        """
        Formats longdesc descriptions with smart paragraph breaks.

        Args:
            longdesc_list: List of (location, description) tuples.

        Returns:
            str: Formatted description with paragraph breaks.
        """
        from world.combat.constants import (
            PARAGRAPH_BREAK_THRESHOLD,
            ANATOMICAL_REGIONS,
            REGION_BREAK_PRIORITY,
        )

        if not longdesc_list:
            return ""

        paragraphs = []
        current_paragraph = []
        current_char_count = 0
        current_region = None

        for location, description in longdesc_list:
            # Determine which anatomical region this location belongs to
            location_region = self._get_anatomical_region(location)

            # Check if we should break for a new paragraph
            should_break = False

            if (REGION_BREAK_PRIORITY and current_region and
                    location_region != current_region):
                # Region changed - check if we should break
                if current_char_count >= PARAGRAPH_BREAK_THRESHOLD * 0.7:
                    should_break = True
            elif current_char_count + len(description) > PARAGRAPH_BREAK_THRESHOLD:
                # Would exceed threshold - break now
                should_break = True

            if should_break and current_paragraph:
                # Finish current paragraph and start new one
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
                current_char_count = 0

            # Add description to current paragraph
            current_paragraph.append(description)
            current_char_count += len(description) + 1  # +1 for space
            current_region = location_region

        # Add final paragraph
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))

        return "\n\n".join(paragraphs)

    def _get_anatomical_region(self, location):
        """
        Determines which anatomical region a location belongs to.

        Args:
            location: Body location string.

        Returns:
            str: Region name or 'extended' for non-standard anatomy.
        """
        from world.combat.constants import ANATOMICAL_REGIONS

        for region_name, locations in ANATOMICAL_REGIONS.items():
            if location in locations:
                return region_name
        return "extended"

    def has_location(self, location):
        """
        Checks if this character has a specific body location.

        Args:
            location: Body location to check.

        Returns:
            bool: True if character has this location.
        """
        longdescs = self.longdesc or {}
        return location in longdescs

    def get_available_locations(self):
        """
        Gets list of all body locations this character has.

        Returns:
            list: List of available body location names.
        """
        longdescs = self.longdesc or {}
        return list(longdescs.keys())

    def set_longdesc(self, location, description):
        """
        Sets a longdesc for a specific location.

        Args:
            location: Body location.
            description: Description text (None to clear).

        Returns:
            bool: True if successful, False if location invalid.
        """
        if not self.has_location(location):
            return False

        longdescs = self.longdesc or {}
        longdescs[location] = description
        self.longdesc = longdescs
        return True

    def get_longdesc(self, location):
        """
        Gets longdesc for a specific location.

        Args:
            location: Body location.

        Returns:
            str or None: Description text or None if unset/invalid.
        """
        if not self.has_location(location):
            return None

        longdescs = self.longdesc or {}
        return longdescs.get(location)

    def return_appearance(self, looker, **kwargs):
        """
        Called when someone looks at this character.

        Returns a clean character appearance with name, description,
        longdesc+clothing, and wielded items.

        Args:
            looker: Character doing the looking.
            **kwargs: Additional parameters.

        Returns:
            str: Complete character appearance in clean format.
        """
        # Build appearance components
        parts = []

        # 1. Character name (header) + main description (no blank line between)
        name_and_desc = [self.get_display_name(looker)]
        if self.db.desc:
            # Initial description should NOT have skintone applied
            processed_desc = self._process_description_variables(
                self.db.desc, looker,
                force_third_person=True, apply_skintone=False,
            )
            name_and_desc.append(processed_desc)

        parts.append('\n'.join(name_and_desc))

        # 2. Longdesc + clothing integration (uses automatic paragraph parsing)
        if self.longdesc is None:
            try:
                from world.combat.constants import DEFAULT_LONGDESC_LOCATIONS
                self.longdesc = DEFAULT_LONGDESC_LOCATIONS.copy()
            except ImportError:
                pass

        visible_body_descriptions = self._get_visible_body_descriptions(looker)
        if visible_body_descriptions:
            formatted_body_descriptions = self._format_longdescs_with_paragraphs(
                visible_body_descriptions
            )
            parts.append(formatted_body_descriptions)

        # 3. Wielded items section (using hands system)
        hands = (
            self.attributes.get('hands', category='equipment')
            or {'left': None, 'right': None}
        )
        wielded_items = [item for item in hands.values() if item is not None]

        if wielded_items:
            wielded_names = [obj.get_display_name(looker) for obj in wielded_items]
            if len(wielded_names) == 1:
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding a "
                    f"{wielded_names[0]}."
                )
            elif len(wielded_names) == 2:
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding a "
                    f"{wielded_names[0]} and a {wielded_names[1]}."
                )
            else:
                # Multiple items: "a item1, a item2, and a item3"
                wielded_with_articles = [f"a {name}" for name in wielded_names]
                wielded_text = (
                    f"{self.get_display_name(looker)} is holding "
                    f"{', '.join(wielded_with_articles[:-1])}, and "
                    f"{wielded_with_articles[-1]}."
                )
            parts.append(wielded_text)
        else:
            # Show explicitly when hands are empty
            parts.append(f"{self.get_display_name(looker)} is holding nothing.")

        # 4. Staff-only comprehensive inventory (with explicit admin messaging)
        if looker.check_permstring("Builder"):
            all_contents = [obj for obj in self.contents if obj.location == self]
            if all_contents:
                content_names = [
                    f"{obj.get_display_name(looker)} [{obj.dbref}]"
                    for obj in all_contents
                ]
                parts.append(
                    f"|wWith your administrative visibility, you see:|n "
                    f"{', '.join(content_names)}"
                )

        # Join all parts with appropriate spacing (blank lines between sections)
        return '\n\n'.join(parts)

    def _process_description_variables(
        self, desc, looker, force_third_person=False, apply_skintone=False
    ):
        """
        Process template variables in descriptions for perspective-aware text.

        Uses simple template variables like {their}, {they}, {name} similar
        to {color}.

        Args:
            desc (str): Description text with potential template variables.
            looker (Character): Who is looking at this character.
            force_third_person (bool): If True, always use 3rd person pronouns.
            apply_skintone (bool): If True, apply skintone coloring
                (for longdescs only).

        Returns:
            str: Description with variables substituted.
        """
        if not desc or not looker:
            return desc

        # Map of available template variables based on perspective
        is_self = (looker == self) and not force_third_person

        # Get pronoun information for this character
        gender_mapping = {
            'male': 'male',
            'female': 'female',
            'neutral': 'plural',
            'nonbinary': 'plural',
            'other': 'plural',
        }

        character_gender = gender_mapping.get(self.gender, 'plural')

        # Simple template variable mapping (like {color})
        variables = {
            # Most common - possessive pronouns (lowercase)
            'their': (
                'your' if is_self
                else self._get_pronoun('possessive', character_gender)
            ),
            # Subject and object pronouns (lowercase)
            'they': (
                'you' if is_self
                else self._get_pronoun('subject', character_gender)
            ),
            'them': (
                'you' if is_self
                else self._get_pronoun('object', character_gender)
            ),
            # Possessive absolute and reflexive (less common, lowercase)
            'theirs': (
                'yours' if is_self
                else self._get_pronoun('possessive_absolute', character_gender)
            ),
            'themselves': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            'themself': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            # Capitalized versions for sentence starts
            'Their': (
                'Your' if is_self
                else self._get_pronoun(
                    'possessive', character_gender
                ).capitalize()
            ),
            'They': (
                'You' if is_self
                else self._get_pronoun('subject', character_gender).capitalize()
            ),
            'Them': (
                'You' if is_self
                else self._get_pronoun('object', character_gender).capitalize()
            ),
            'Theirs': (
                'Yours' if is_self
                else self._get_pronoun(
                    'possessive_absolute', character_gender
                ).capitalize()
            ),
            'Themselves': (
                'Yourself' if is_self
                else self._get_pronoun(
                    'reflexive', character_gender
                ).capitalize()
            ),
            'Themself': (
                'Yourself' if is_self
                else self._get_pronoun(
                    'reflexive', character_gender
                ).capitalize()
            ),
            # Character names
            'name': 'you' if is_self else self.get_display_name(looker),
            "name's": (
                'your' if is_self
                else f"{self.get_display_name(looker)}'s"
            ),
            # Legacy support for existing verbose names (can be removed later)
            'observer_pronoun_possessive': (
                'your' if is_self
                else self._get_pronoun('possessive', character_gender)
            ),
            'observer_pronoun_subject': (
                'you' if is_self
                else self._get_pronoun('subject', character_gender)
            ),
            'observer_pronoun_object': (
                'you' if is_self
                else self._get_pronoun('object', character_gender)
            ),
            'observer_pronoun_possessive_absolute': (
                'yours' if is_self
                else self._get_pronoun('possessive_absolute', character_gender)
            ),
            'observer_pronoun_reflexive': (
                'yourself' if is_self
                else self._get_pronoun('reflexive', character_gender)
            ),
            'observer_character_name': (
                'you' if is_self
                else self.get_display_name(looker)
            ),
            'observer_character_name_possessive': (
                'your' if is_self
                else f"{self.get_display_name(looker)}'s"
            ),
        }

        # Substitute all variables in the description
        try:
            processed_desc = desc.format(**variables)
        except (KeyError, ValueError) as e:
            # If there are template errors, use original description and log
            processed_desc = desc
            print(f"Template processing error in _process_description_variables: {e}")
            print(f"Description: {desc[:100]}...")
            print(f"Variables available: {list(variables.keys())}")

        # Apply skintone coloring only if requested (for longdescs only)
        if apply_skintone:
            skintone = self.db.skintone
            if skintone:
                from world.combat.constants import SKINTONE_PALETTE
                color_code = SKINTONE_PALETTE.get(skintone)
                if color_code:
                    # Wrap the entire processed description in the skintone color
                    # Reset color at end to prevent bleeding
                    processed_desc = f"{color_code}{processed_desc}|n"

        return processed_desc

    def _get_pronoun(self, pronoun_type, gender):
        """
        Get specific pronoun based on gender and type.

        Args:
            pronoun_type (str): Type of pronoun
                (subject, object, possessive, etc.)
            gender (str): Gender identifier (male, female, plural).

        Returns:
            str: Appropriate pronoun.
        """
        pronouns = {
            'male': {
                'subject': 'he',
                'object': 'him',
                'possessive': 'his',
                'possessive_absolute': 'his',
                'reflexive': 'himself',
            },
            'female': {
                'subject': 'she',
                'object': 'her',
                'possessive': 'her',
                'possessive_absolute': 'hers',
                'reflexive': 'herself',
            },
            'plural': {  # Used for they/them, nonbinary, neutral, other
                'subject': 'they',
                'object': 'them',
                'possessive': 'their',
                'possessive_absolute': 'theirs',
                'reflexive': 'themselves',
            },
        }

        return pronouns.get(gender, pronouns['plural']).get(pronoun_type, 'they')
