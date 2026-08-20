"""Build 080 — the Rook's sealed biome (recluse profile).

The studio is his whole world, so the studio satisfies his whole
profile: a Thawn-Harrison nutrient line for the body (whoever sealed
him in plumbed him in), the broadcast chair for sleep AND for the
airwaves — the colony's first parasocial soul, whose social need is
satisfied by being loved on 88.8 by people who will never see his
face. His mood now seasons every broadcast through the STATE line.
His needs are met by infrastructure, and infrastructure can break:
that is the only door out of a recluse's story, and it stays shut
until the world earns opening it.

Idempotent: fixtures/ads re-mirror; skips if already ensouled.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/080_rook_biome.py
"""

from evennia import create_object
from evennia.utils.search import search_object

from world.souls import engine, ensoul

rook = next(iter(search_object("#6034")), None)
studio = next(iter(search_object("#5283")), None)
chair = next(iter(search_object("#6035")), None)

if not (rook and rook.pk and studio and chair):
    print("BUILD 080: missing pieces; aborted")
elif rook.id in {s.id for s in engine.get_souls() if s.pk}:
    print("BUILD 080: the Rook is already ensouled; skipped")
else:
    line = next((o for o in studio.contents
                 if "nutrient line" in o.key.lower()), None)
    if line is None:
        line = create_object("typeclasses.items.Item",
                             key="a Thawn-Harrison nutrient line",
                             location=studio, home=studio)
        line.aliases.add(["line", "nutrient line", "drip"])
        line.db.desc = (
            "A medical-white feed line descending from a ceiling conduit "
            "to a wall-mounted port, its junction box wearing the "
            "Thawn-Harrison crest and a service date years out of "
            "warranty. Whoever sealed this room in also plumbed it in — "
            "the line hums faintly, warm to the touch, patient as an IV.")
        line.locks.add("get:false()")
    line.db.advertises = {"hunger": 0.9}
    line.db.dwell_pose_in = ("draws the nutrient line down and seats it "
                             "against the port at his wrist, eyes "
                             "half-lidding as the feed takes.")
    line.db.dwell_pose_out = ("unseats the line and lets it retract "
                              "ceilingward, flexing his hand like a man "
                              "waking it up.")
    line.tags.add("advertiser", category="souls")

    ads = dict(chair.db.advertises or {})
    ads["social"] = 0.8
    chair.db.advertises = ads
    chair.db.dwell_pose_in = ("keys the board, leans into the mic, and "
                              "lets the band fade under his voice — "
                              "somewhere out there, the whole colony is "
                              "listening.")
    chair.db.dwell_pose_out = ("eases off the mic and lets the house "
                               "band carry it, the ON AIR glow steady "
                               "as ever.")
    chair.tags.add("advertiser", category="souls")

    ensoul(rook, role="dj", home=studio, post=None, schedule="night",
           wage_rate=0.0, venue=None, profile="recluse")
    print(f"BUILD 080: the Rook (#{rook.id}) ensouled — recluse profile, "
          f"biome: {line.key} (hunger) + {chair.key} (the airwaves), "
          f"home = the studio")
