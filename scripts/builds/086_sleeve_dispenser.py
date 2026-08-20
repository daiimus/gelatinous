"""Build 086 — the decant issue dispenser (#2100).

Everyone wakes at Thawn-Harrison with nothing. This bolts a jumpsuit-
and-slipper dispenser to the Decantation Chamber wall: `press dispenser`
pays out one of each, into free hands or onto the floor. PCs and
resleeved NPCs use the identical machine.

Idempotent: skips if a dispenser is already installed.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/086_sleeve_dispenser.py
"""

from evennia import create_object
from evennia.utils.search import search_object

CHAMBER = "#1989"        # Thawn-Harrison Cryogenics - Decantation Chamber

room = next(iter(search_object(CHAMBER)), None)
if room is None or not room.pk:
    print("BUILD 086: decantation chamber missing; aborted")
else:
    existing = next((o for o in room.contents
                     if o.is_typeclass("typeclasses.terminals.SleeveDispenser",
                                       exact=False)), None)
    if existing is not None:
        print(f"BUILD 086: dispenser #{existing.id} already installed; skipped")
    else:
        disp = create_object("typeclasses.terminals.SleeveDispenser",
                             key="a Thawn-Harrison issue dispenser",
                             location=room, home=room)
        disp.db.desc = (
            "A wall-mounted dispenser in the same clinical off-white as "
            "everything else in the chamber, its output tray worn "
            "smooth by decades of hands. A yellow decal reads ISSUE: "
            "ONE SUIT, ONE PAIR — PRESS FOR SERVICE, and beneath it, "
            "scratched into the paint by somebody who had time to "
            "think about it: WELCOME BACK.")
        disp.db.integrate = True
        disp.db.integration_priority = 6
        disp.db.integration_desc = (
            "An issue dispenser is bolted to the wall beside the tables, "
            "its tray worn smooth.")
        print(f"BUILD 086: dispenser #{disp.id} installed in {room.key}")
