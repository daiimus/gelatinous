"""
Time System

Manages game time and provides current time period for weather system.
Designed to be easily expandable for calendar systems and time-based events.
"""



# Time periods for weather variation (12 granular periods)
TIME_PERIODS = [
    'dawn',           # 5-6 AM
    'early_morning',  # 6-8 AM  
    'late_morning',   # 8-11 AM
    'midday',         # 11 AM-1 PM
    'early_afternoon',# 1-4 PM
    'late_afternoon', # 4-6 PM
    'dusk',           # 6-7 PM
    'early_evening',  # 7-9 PM
    'late_evening',   # 9-11 PM
    'night',          # 11 PM-1 AM
    'late_night',     # 1-3 AM
    'pre_dawn'        # 3-5 AM
]

# Hour ranges for each time period (24-hour format)
TIME_RANGES = {
    'dawn': (5, 6),
    'early_morning': (6, 8),
    'late_morning': (8, 11),
    'midday': (11, 13),
    'early_afternoon': (13, 16),
    'late_afternoon': (16, 18),
    'dusk': (18, 19),
    'early_evening': (19, 21),
    'late_evening': (21, 23),
    'night': (23, 1),
    'late_night': (1, 3),
    'pre_dawn': (3, 5)
}


class TimeSystem:
    """
    Manages game time and time-based calculations.
    
    Provides current time period for weather system and other
    time-dependent game mechanics.
    """
    
    def __init__(self):
        """Initialize time system."""
        pass
        
    def get_current_hour(self):
        """
        Get current game hour (0-23).
        
        Returns:
            int: Current hour in 24-hour format
        """
        # Delegates to the colony clock. This used to call time.localtime(),
        # which is the CONTAINER's clock — UTC — so "night" ran eight hours
        # away from the colony's own night, and weather, director broadcasts
        # and the admin readout all inherited the error.
        from world.gametime import colony_hour
        return colony_hour()
        
    def get_current_time_period(self):
        """
        Get current time period for weather system.
        
        Returns:
            str: Current time period from TIME_PERIODS
        """
        hour = self.get_current_hour()
        
        for period, (start, end) in TIME_RANGES.items():
            if start <= end:
                # Normal range (e.g., 6-8)
                if start <= hour < end:
                    return period
            else:
                # Wrap around midnight (e.g., 23-1)
                if hour >= start or hour < end:
                    return period
                    
        # Fallback
        return 'midday'


# Global convenience function
def get_current_time_period():
    """
    Convenience function to get current time period.
    
    Returns:
        str: Current time period
    """
    return TimeSystem().get_current_time_period()


def spoken_period(period):
    """A TIME_PERIODS key as something a voice can say.

    The keys are identifiers -- ``late_evening`` -- and were being
    interpolated straight into broadcast prose, so the station said "It
    is late_evening in the colony" for 18 hours of every 24 (#2785).

    De-underscored rather than hand-mapped, deliberately: every one of
    the twelve reads correctly that way ("late evening", "pre dawn"), and
    a lookup table would silently fall back to the raw key the first time
    somebody adds a period -- which is the exact failure being fixed.
    """
    if not period:
        return period
    return str(period).replace("_", " ")
