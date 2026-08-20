"""Build 081 — the nutrient line serves for real (#2074).

Hunger is pharmacology now: food carries a nutrition substance and the
eat command moves the eater's meter — one consumption path for players
and NPCs. This build:

1. Converts the Rook's nutrient line from dwell-scenery to a SERVING
   FIXTURE (``db.snacks`` + authored serve messaging): any character in
   the studio can ``eat feed`` and hit the same membrane, gates, and
   pharmacology the Rook does. The retired dwell poses come off.
2. Stamps nutrition onto already-spawned food stock — prototype changes
   don't retro-apply, and a soul that eats a pre-#2074 skewer would
   fault "didn't nourish".

Idempotent: re-stamps are no-ops, the sweep skips items already fed.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/081_line_serves.py
"""

from evennia.utils.search import search_object, search_tag

STUDIO_ID = "#5283"

# key(lower) -> nutrition doses per bite, mirroring world/prototypes.py
NUTRITION_BY_KEY = {
    "rat tail": 2, "rat chops": 2, "rat haunch": 2, "rat offal": 2,
    "ground mystery meat": 2,
    "bowl of rat tail stew": 3, "plate of grilled rat chops": 3,
    "roast rat haunch": 3, "butcher's breakfast": 6, "mystery skewer": 3,
    "a bowl of hand-pulled noodles": 2, "a steamed bun": 2,
    "a grilled snail skewer": 3, "a jar of pickled snails": 1,
    "a charred skewer": 3,
}

studio = next(iter(search_object(STUDIO_ID)), None)
line = next((o for o in (studio.contents if studio else ())
             if "nutrient line" in o.key.lower()), None)

if line is None:
    print("BUILD 081: nutrient line not found; aborted")
else:
    line.db.snacks = [{
        "name": "nutrient feed",
        "order_keywords": ("feed", "nutrient", "nutrients", "line"),
        "effects": {"nutrition": 4},
        "taste": ("Warm, faintly sweet nothing — the texture of settled "
                  "custard, the aftertaste of vitamins doing their job."),
        "msg_self": ("You draw the nutrient line down and seat it against "
                     "the port at your wrist; the feed takes with a soft "
                     "click and a spreading warmth."),
        "msg_room": ("{actor} draws the nutrient line down and seats it "
                     "against a wrist port; the junction box ticks as the "
                     "feed cycles."),
    }]
    # retired: the dwell path — feeding goes through the real eat verb now
    line.attributes.remove("dwell_pose_in")
    line.attributes.remove("dwell_pose_out")
    print(f"BUILD 081: {line.key} now serves (eat feed, nutrition 4/serve)")

stamped = skipped = 0
for obj in search_tag("eat", category="delivery_method"):
    if not obj or not obj.pk:
        continue
    doses = NUTRITION_BY_KEY.get((obj.key or "").lower())
    if doses is None:
        skipped += 1
        continue
    effects = obj.db.drink_effects
    if effects is not None and not effects.get("nutrition"):
        effects = dict(effects)
        effects["nutrition"] = doses
        obj.db.drink_effects = effects
        stamped += 1
print(f"BUILD 081: live stock — {stamped} items fed, "
      f"{skipped} eat-tagged non-food left alone")
