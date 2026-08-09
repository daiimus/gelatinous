"""Build 047 — the shrine of the forgotten saint on Pessoa Street.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/047_pessoa_shrine.py
    then a foreground reload.

Make the cracked saint already described at (-6,-12) a real landmark, and
lean into the street's name: Pessoa wrote under dozens of invented selves,
so on the street of many selves the workers keep a shrine to the faceless
— a patron of the resleeved, its plinth chalked with the names people
carried before the sleeves they wear now. Enrich the room + sense layers
and add the statue as an integrated object. Data-only, re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

room = next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
             if r.destination is None and get_xyz(r) == (-6, -12, 0)), None)
assert room is not None, "Pessoa shrine cell (-6,-12,0) not found"

room.db.desc = (
    "The street opens into a communal spot, lanterns strung low overhead and "
    "the sweet reek of tallow under the industrial haze. Against the west "
    "wall leans the shrine every worker on Pessoa knows: a cracked stone "
    "saint worn faceless by weather and hands, its features rubbed to a "
    "smooth blank. The plinth and the wall behind it are layered in chalked "
    "names — dozens of them, crossed out and written over, the names people "
    "carried in the sleeves they wore before the ones they wear now. Somebody "
    "keeps the candle stubs lit.")
room.db.sense_descs = {
    "olfactory": "Tallow smoke and chalk dust, sweet under the refinery reek.",
    "auditory": "The lanterns tick in the updraft, and someone is always "
                "murmuring low at the wall.",
    "tactile": "The saint's smooth blank of a face is cold, and greasy with a "
               "thousand touches.",
    "atmospheric": "A street of many selves, keeping a shrine to the ones "
                   "nobody remembers.",
}

saint = next((o for o in room.contents if o.key == "the forgotten saint"), None)
if saint is None:
    saint = create_object("typeclasses.objects.Object",
                          key="the forgotten saint", location=room, home=room)
    saint.aliases.add(["saint", "statue", "shrine", "the saint"])
saint.db.desc = (
    "A cracked stone saint, life-sized once, now leaning where it fell "
    "against the wall. Weather and a thousand praying hands have worn its "
    "face to a smooth blank — no eyes, no mouth, nothing left to name it by. "
    "The plinth is white with overlapping chalk: names, dates, some scratched "
    "out and rewritten, the names workers carried in the sleeves they wore "
    "before this one. Candle stubs gutter in a tin dish at its feet. Whatever "
    "it was the saint of once, it is the patron of the faceless now.")
saint.db.integrate = True
saint.db.integration_desc = (
    "Against the west wall leans |wthe forgotten saint|n — a faceless stone "
    "shrine, its plinth white with chalked names, a dish of guttering candles "
    "at its feet.")
saint.locks.add("get:false()")
saint.db.get_err_msg = "The saint is stone, cracked, and heavier than guilt."

print(f"BUILD 047: shrine at #{room.id} ({get_xyz(room)}); saint #{saint.id}.")
