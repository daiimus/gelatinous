"""
Crowd system manager following weather system architecture.
Manages crowd level calculation and message selection.
"""

import random

class CrowdSystem:
    """
    Manages crowd levels and atmospheric descriptions.
    Integrates with room attributes, character presence, and environmental factors.
    """
    
    def __init__(self):
        # Base crowd levels for different room types. Streets carry their
        # busyness through each room's crowd_base_level (0 quiet .. 3 hotspot),
        # so 'street' itself adds nothing -- otherwise a base-1 street can never
        # read sparser than 'moderate'.
        self.room_type_modifiers = {
            'street': 0.0,
            'intersection': 1.0,
            'corner store': 0.5,
            'laundromat': 0.2,
            'courier service': 0.3,
            'cube hotel': 0.1,
            'hospital': 0.7,
            'stairway': 0.1,
            'dead-end': -0.5,  # Can reduce crowd below base
        }
        
        # Weather effects on crowd levels
        self.weather_modifiers = {
            'clear': 0.2,
            'overcast': 0.0,
            'rain': -0.5,
            'heavy_rain': -1.0,
            'torrential_rain': -1.5,
            'soft_snow': -0.3,
            'hard_snow': -0.8,
            'blizzard': -2.0,
            'fog': -0.2,
            'heavy_fog': -0.7,
            'blind_fog': -1.2,
            'windy': -0.1,
            'sandstorm': -1.8,
            'tox_rain': -1.3,
            'gray_pall': -0.4,
            'dry_thunderstorm': -0.6,
            'rainy_thunderstorm': -0.9,
            'flashstorm': -2.5,
        }
    
    def calculate_crowd_level(self, room):
        """
        Calculate total crowd level for a room based on multiple factors.
        
        Args:
            room: Room object to calculate crowd level for
            
        Returns:
            int: Final crowd level (0+)
        """
        # Start with room's base crowd level (default 0)
        # Use AttributeProperty which handles defaults automatically
        base_level = room.crowd_base_level or 0
        total_level = float(base_level)
        
        # Add room type modifier
        # Use AttributeProperty for room type
        room_type = room.type
        if room_type and room_type in self.room_type_modifiers:
            total_level += self.room_type_modifiers[room_type]
        
        # Add character-based scaling (0.5 per character, so 2 chars = +1 level)
        characters = [obj for obj in room.contents if hasattr(obj, 'has_account') and obj.has_account]
        character_bonus = len(characters) * 0.5
        total_level += character_bonus
        
        # Add weather modifier if weather system available
        try:
            from world.weather import weather_system
            current_weather = weather_system.get_current_weather()
            if current_weather in self.weather_modifiers:
                total_level += self.weather_modifiers[current_weather]
        except (ImportError, AttributeError):
            # Weather system not available, no modifier
            pass
        
        # Ensure minimum of 0
        final_level = max(0, int(round(total_level)))
        
        return final_level
    
    def get_crowd_contributions(self, room, looker):
        """
        Get crowd contributions for room atmosphere display.
        
        Args:
            room: Room object
            looker: Character looking at the room
            
        Returns:
            str: Formatted crowd description or empty string
        """
        crowd_level = self.calculate_crowd_level(room)
        
        # Check base level first - if explicitly set to 0, no crowd messages ever
        # This allows builders to disable crowd messages for specific rooms
        if room.crowd_base_level == 0:
            return ""
        
        # No message for calculated crowd level 0
        if crowd_level == 0:
            return ""
        
        # Get available crowd messages for this level
        from .crowd_messages import get_crowd_messages
        crowd_messages = get_crowd_messages(crowd_level)
        if not crowd_messages:
            return ""
        
        # Select random message from available categories, gated by the
        # looker's perceivable senses (CAPACITY_CONSUMERS spec §5): the blind
        # don't get visual crowd content, the deaf don't get the auditory din.
        from world.perception import blocked_senses
        blocked = blocked_senses(looker)
        available_categories = [
            c for c in crowd_messages.keys() if c not in blocked
        ]
        if available_categories:
            # Randomly select one category to display (following weather system pattern)
            selected_category = random.choice(available_categories)
            category_messages = crowd_messages[selected_category]
            if category_messages:
                selected_message = random.choice(category_messages)
                # Capitalise the first letter only (preserve interior caps and
                # multi-sentence lines), then ensure it ends with a period.
                formatted_message = (
                    selected_message[:1].upper() + selected_message[1:]
                )
                if not formatted_message.endswith('.'):
                    formatted_message += '.'
                # Wrap in bold white for ambient atmosphere
                return f"|w{formatted_message}|n"
        
        return ""
    
    def get_crowd_level_description(self, crowd_level):
        """
        Get human-readable description of crowd level.
        
        Args:
            crowd_level (int): Crowd level number
            
        Returns:
            str: Description of crowd level
        """
        from .crowd_messages import CROWD_INTENSITY
        intensity = CROWD_INTENSITY.get(crowd_level, 'packed')
        if intensity == 'none':
            return "empty"
        return intensity
