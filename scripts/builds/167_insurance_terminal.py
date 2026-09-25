"""Build 167 — the sleeve-policy terminal in the Thawn-Harrison lobby (#3667).

Sleeve insurance is a personal policy bought alive, at this machine: it
takes the presser's sample and puts a record on file in their name
(`world.insurance`, one `ServerConfig` row per sleeve uid). `press insure
on terminal` buys; `press terminal` reads the status back. The record
lives off the machine, so this box can be rebuilt without losing cover.

Idempotent: skips if a terminal is already installed in the lobby.

Run IN-GAME (the server's cache must see the new object; an external
`evennia shell` would need a reload afterwards):
    @py exec(open('/usr/src/game/scripts/builds/167_insurance_terminal.py').read(), {'print': self.msg})
"""

from evennia import create_object
from evennia.utils.search import search_object

LOBBY = "#1986"        # Thawn-Harrison Cryogenics - Lobby

room = next(iter(search_object(LOBBY)), None)
if room is None or not room.pk or "Lobby" not in room.key:
    print(f"BUILD 167: lobby {LOBBY} missing or not the lobby; aborted")
else:
    existing = next((o for o in room.contents
                     if o.is_typeclass("typeclasses.terminals.InsuranceTerminal",
                                       exact=False)), None)
    if existing is not None:
        # Re-run repair: the index tag Slice B's planner looks up, for a
        # terminal built before at_object_creation added it.
        if not existing.tags.has("insurance_terminal", category="machines"):
            existing.tags.add("insurance_terminal", category="machines")
            print(f"BUILD 167: terminal #{existing.id} tagged")
        if existing.attributes.has("insurance_terminal"):
            existing.attributes.remove("insurance_terminal")   # retired flag
        print(f"BUILD 167: terminal #{existing.id} already installed; skipped")
    else:
        term = create_object("typeclasses.terminals.InsuranceTerminal",
                             key="a Thawn-Harrison policy terminal",
                             location=room, home=room)
        term.db.desc = (
            "A desk-mounted terminal in Thawn-Harrison off-white, its "
            "sample reader a recessed oval worn grey at the rim by "
            "thousands of thumbs. The screen cycles one line: SLEEVE "
            "POLICY — PRESS INSURE TO SAMPLE AND FILE. A smaller plate "
            "beneath it reads: A POLICY COVERS ONE RETURN. RENEW AFTER "
            "DECANT.")
        term.db.integrate = True
        term.db.integration_priority = 6
        term.db.integration_desc = (
            "A policy terminal sits at the end of the main desk, its "
            "sample reader glowing a patient amber.")
        print(f"BUILD 167: terminal #{term.id} installed in {room.key}")
