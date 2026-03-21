# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings
from evennia import utils


def connection_screen():
    """
    Dynamic connection screen that adjusts based on settings.
    """
    # Build the create command line based on registration setting
    if settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
        create_line = "__ Create  : |wcreate <email@address.com> <password>|n\n\nUse your email address to connect or create a new account."
    else:
        create_line = "__ Create  : |rAccount creation disabled|n\n\nUse your email address to connect to your existing account."
    
    return f"""

|b█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒█
█▒▒▒▒▒▒▒▒▒ |g{settings.SERVERNAME} SYSTEM |n :::: SIGNAL {utils.get_evennia_version("short")} |b▒▒▒▒▒▒▒▒▒▒█
█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒█|n

[ WARNING: Signal instability detected. ]
[ Color bars desaturated. ]
[ Anomalous resonance detected at 7.8Hz. ] 

YEAR: 198|u█|n (ENDLESS BROADCAST)
LOCATION: PARTS UNKNOWN
 
>> Streets: Flowing.
>> Airwaves: Distorted.
>> Flesh: Grainy.
>> Memory: OFFLINE.

__ Connect : |wconnect <email@address.com> <password>|n
{create_line}
Character creation happens after login.
Enter |whelp|n for more info. |wlook|n will re-show this screen.

|w>>> END OF TE▒T PATTERN. BROADCAST WI▒L NOT RESUME WITHOUT PROMPT.|n

|b█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒█|n
"""
