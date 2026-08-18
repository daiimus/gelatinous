"""Build 071 — a ground-floor fleet cradle in the Constabulary Lobby.

The dispatch console (build 070's charge advertiser) sits upstairs
behind an elevator NPCs can't operate — every cradle run stalled
loudly at the lift (travel now faults, but the battery stays dead).
Security units charge at STREET level: a branded fleet cradle in the
lobby advertises charge/maintenance where the pathfinder can actually
deliver a walker.

Idempotent: skips if a cradle already stands in the lobby.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/071_constab_fleet_cradle.py
"""

from evennia import create_object
from evennia.utils.search import search_object

lobby = next((r for r in search_object("Colonial Constabulary Lobby")
              if r.destination is None), None)
if lobby is None:
    print("BUILD 071: NO LOBBY FOUND — nothing built")
else:
    cradle = next((o for o in lobby.contents
                   if "fleet cradle" in o.key.lower()), None)
    if cradle is None:
        cradle = create_object("typeclasses.items.Item",
                               key="a Boiler Run fleet cradle",
                               location=lobby, home=lobby)
        cradle.aliases.add(["cradle", "fleet cradle", "charger"])
        cradle.db.desc = (
            "A waist-high Boiler Run charging frame bolted to the lobby "
            "floor, contact rails polished bright by chassis after "
            "chassis. A fat conduit climbs the wall behind it, and the "
            "status strip along its lip idles a slow, patient amber. "
            "BOILER RUN — FLEET POWER, stamped where a kneeling unit "
            "would read it.")
        cradle.locks.add("get:false()")
    ads = dict(cradle.db.advertises or {})
    ads["charge"] = 0.9
    ads["maintenance"] = 0.6
    cradle.db.advertises = ads
    cradle.tags.add("advertiser", category="souls")
    print(f"BUILD 071: {cradle.key} (#{cradle.id}) @ {lobby.key} "
          f"ads={dict(cradle.db.advertises)}")
