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

from world import gametime
from django.conf import settings
from evennia import utils


#: The login frame's width in visible columns.
#:
#: `NEW_PLAYER_EXPERIENCE_SPEC` §3 fixes 66 columns for the post-menu
#: blocks, and the closing bar already matched it. The three TOP bars
#: were 67, so the frame did not close: the bottom edge sat one column
#: left of the top edge, on the first screen every player sees (#2752).
FRAME_WIDTH = 66

#: The shade the frame is drawn in, and the block at each end.
_SHADE = "\u2592"
_EDGE = "\u2588"

#: How much of the header row is spent before the title.
_INSET = 9


def _rule():
    """A closed bar exactly `FRAME_WIDTH` columns wide."""
    return _EDGE + _SHADE * (FRAME_WIDTH - 2) + _EDGE


def _titled_rule(markup, visible):
    """A bar with a title inset, padded from the title's VISIBLE length.

    The trailing shade run used to be a literal. It measured correctly
    only because `len("Gelatinous Monster") + len("6.1.0")` happened to
    land right — rename the server or bump Evennia and the header row
    goes crooked. `markup` and `visible` are built from the same parts
    by the caller so they cannot describe different strings.
    """
    for inset in (_INSET, 1):
        lead = _EDGE + _SHADE * inset + " "
        fill = FRAME_WIDTH - len(lead) - len(visible) - 2
        if fill >= 1:
            return f"{lead}{markup} " + _SHADE * fill + _EDGE

    # Longer than the frame even with no inset. Keep the FRAME and trim
    # the title: a bar that closes matters more than a name in full, and
    # the alternative is the row growing past every other row again.
    # The colour goes with it, because `markup` cannot be cut safely —
    # a slice can land in the middle of a `|g` and print the code.
    title = visible[:FRAME_WIDTH - 6]
    return (_EDGE + _SHADE + " " + title + " "
            + _SHADE * (FRAME_WIDTH - 5 - len(title)) + _EDGE)


def connection_screen():
    """
    Dynamic connection screen that adjusts based on settings.
    """
    # Build the create command line based on registration setting
    if settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
        create_line = "__ Create  : |wcreate <email@address.com> <password>|n\n\nUse your email address to connect or create a new account."
    else:
        create_line = "__ Create  : |rAccount creation disabled|n\n\nUse your email address to connect to your existing account."
    
    version = utils.get_evennia_version("short")
    rule = _rule()
    header = _titled_rule(
        f"|g{settings.SERVERNAME} SYSTEM|n :::: SIGNAL {version}|b",
        f"{settings.SERVERNAME} SYSTEM :::: SIGNAL {version}",
    )

    return f"""

|b{rule}
{header}
{rule}|n

[ WARNING: Signal instability detected. ]
[ Color bars desaturated. ]
[ Anomalous resonance detected at 7.8Hz. ] 

YEAR: {gametime.tst_now().year} (ENDLESS BROADCAST)
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

|b{rule}|n
"""
