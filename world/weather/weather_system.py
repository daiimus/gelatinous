"""
Core Weather System

Manages global weather state and provides weather descriptions for rooms.
Designed to be easily expandable for regional weather systems.
"""

import random
from evennia.utils import logger
from .weather_messages import WEATHER_MESSAGES, WEATHER_INTENSITY
from .time_system import get_current_time_period


class WeatherSystem:
    """
    Global weather management system.
    
    Handles current weather state and provides atmospheric descriptions
    for outdoor rooms based on weather conditions and time of day.
    """
    
    def __init__(self):
        """Initialize weather system with default conditions."""
        self.current_weather = "clear"
        self.weather_region = "default"  # Future: support multiple regions
        
    def get_weather_contributions(self, room, looker):
        """
        Get weather contributions for a room's atmosphere.
        
        Args:
            room: The room to get weather for
            looker: Character looking at the room (for sensory filtering)
            
        Returns:
            str: Weather description for the room, or empty string if not applicable
        """
        # Only apply weather to outdoor rooms
        if not getattr(room, 'outside', False):
            return ""
            
        # Get current time period
        time_period = get_current_time_period()
        
        # Get available sensory messages
        weather_key = f"{self.current_weather}_{time_period}"
        sensory_messages = self.get_sensory_messages(weather_key, looker)
        
        if not sensory_messages:
            return ""

        # Compensatory enrichment (CAPACITY_CONSUMERS spec §5): a looker missing
        # a sense gets a little more texture from the senses that remain.
        from world.perception import has_reduced_perception
        count = 3 if has_reduced_perception(looker) else 2
        selected_messages = self.select_weather_messages(sensory_messages, count)
        
        if not selected_messages:
            return ""
            
        # Format messages with proper capitalization and punctuation
        formatted_messages = []
        for message in selected_messages:
            # Capitalize first letter and ensure period at end
            formatted_message = message.strip()
            if formatted_message:
                formatted_message = formatted_message[0].upper() + formatted_message[1:]
                if not formatted_message.endswith('.'):
                    formatted_message += '.'
                formatted_messages.append(formatted_message)
        
        if not formatted_messages:
            return ""
            
        # Combine messages with space separator and wrap in bold white
        combined = " ".join(formatted_messages)
        return f"|w{combined}|n"
        
    def get_sensory_messages(self, weather_key, looker):
        """
        Get available sensory messages based on player capabilities.
        
        Args:
            weather_key: Weather and time combination key
            looker: Character to check sensory capabilities for
            
        Returns:
            list: Available sensory messages for this character
        """
        # Get message pool for current weather/time
        region_messages = WEATHER_MESSAGES.get(self.weather_region, {})
        weather_messages = region_messages.get(weather_key, {})
        
        if not weather_messages:
            # Fallback: try just weather type without time
            weather_messages = region_messages.get(self.current_weather, {})
            
        if not weather_messages:
            return []

        # Filter by the looker's perceivable senses (CAPACITY_CONSUMERS spec §5):
        # a blind looker gets no *visual* weather (rain they can't see) but still
        # the auditory/olfactory channels; a deaf looker loses the auditory ones.
        from world.perception import blocked_senses
        blocked = blocked_senses(looker)

        available_messages = []
        for sense, messages in weather_messages.items():
            if messages and sense not in blocked:
                available_messages.extend(messages)

        return available_messages
        
    def select_weather_messages(self, available_messages, count=2):
        """
        Select weather messages from available pool.
        
        Args:
            available_messages: List of available messages
            count: Number of messages to select
            
        Returns:
            list: Selected messages
        """
        if not available_messages:
            return []
            
        # Select up to 'count' random messages
        selection_count = min(count, len(available_messages))
        return random.sample(available_messages, selection_count)
        
    def set_weather(self, weather_type):
        """
        Change current weather state.
        
        Args:
            weather_type: New weather type from WEATHER_INTENSITY keys
        """
        if weather_type in WEATHER_INTENSITY:
            self.current_weather = weather_type
            logger.log_info(f"Weather changed to: {weather_type}")
        else:
            logger.log_warn(f"Unknown weather type: {weather_type}")
            
    def get_current_weather(self):
        """Get current weather state."""
        return self.current_weather
        
    def get_weather_intensity(self):
        """Get current weather intensity level."""
        return WEATHER_INTENSITY.get(self.current_weather, 'mild')
