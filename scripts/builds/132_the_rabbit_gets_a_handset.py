"""Build 132 — Wren gets a handset (#2301).

She can now ask the crane for a level, but only through a real radio:
`call_the_crane` finds a carried transceiver, switches it on, tunes it
to 27.0 and keys the REAL transmit verb. No back door — the console
hears her exactly as it hears a player, and Ossie can refuse, be
absent, or ask her to confirm.

Without a handset in her hands that whole path is a no-op, which is
the correct failure (she cannot shout at a crane) but a silent one.
This puts the radio in her hands.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/132_the_rabbit_gets_a_handset.py
"""

from evennia.prototypes.spawner import spawn

from world import prototypes
from world.radio import is_radio
from world.souls import posts as posts_mod

wren = posts_mod._living_body("rabbit_wren")
if wren is None:
    print("BUILD 132: no rabbit; aborted")
    raise SystemExit

handset = next((o for o in wren.contents if is_radio(o)), None)
if handset is None:
    handset = spawn(prototypes.WALKIE_TALKIE)[0]
    handset.move_to(wren, quiet=True, move_hooks=False)
    print(f"BUILD 132: {wren.key} issued {handset.key} #{handset.id}")
else:
    print(f"BUILD 132: {wren.key} already carries {handset.key}")

handset.db.radio_on = True
handset.db.frequency = "27.0"          # the crane band, kept ready
print(f"BUILD 132: on={handset.db.radio_on} freq={handset.db.frequency}")

# What she'd ask for from where she is standing right now.
from world.director import courier
want = courier.crane_level_wanted(wren)
print(f"BUILD 132: standing in {wren.location.key}, she wants the box at "
      f"{want if want is not None else 'nothing — not at the crane'}")
print(f"BUILD 132: crane band is {courier.CRANE_BAND}")
