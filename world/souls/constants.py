"""Tunable numbers for how a soul chooses what to eat (#3804).

Owner, 2026-11-13, approving the design these numbers drive: "That makes
sense and can likely live in our constant logic. We can implement now
and leave it open for future review."

EVERY MAGNITUDE HERE IS PROVISIONAL. No system in the colony has had its
balance pass, and these were picked to make the shape right rather than
the amounts: a ration is worse than a meal, a long walk is not worth an
ordinary one, and better food is worth going further for. The review is
#3805. Change the numbers here and nowhere else.

Read through the module (`constants.FOOD_QUALITY_DEFAULT`), never by
`from ... import NAME`, so a number changed here is the number used.
"""

# ------------------------------------------------------------- quality

#: The quality of a food that declares none (`db.food_quality` on the
#: item, `food_quality` among a prototype's attrs). The scale is open at
#: both ends, so it can grow with the kitchens: 5 is an ordinary hot
#: meal. Every dish in the game sits here until it is given a number.
FOOD_QUALITY_DEFAULT = 5.0

#: The attribute a food carries its quality on.
FOOD_QUALITY_ATTR = "food_quality"

# ---------------------------------------------------------------- walk

#: What one room of walking costs, in quality points. A meal is worth
#: its quality minus this for every room on the way; a ration in the
#: pocket is worth its quality, having no way to go. The owner's test:
#: nobody deep in a mine walks 40+ rooms to a restaurant past the ration
#: in their own pocket. At 0.1 an ordinary meal (5) stops being worth
#: the walk over a ration (2) at 30 rooms, and a quality-7 one at 50.
FOOD_WALK_COST_PER_ROOM = 0.1

# -------------------------------------------------------------- ration

#: The tag (key, category) that marks a food as a RATION: the one kind
#: of food allowed to wait in a pocket. Everything else a soul carries
#: is eaten before anything is bought, which is the rule that ended the
#: hoard (#3793), and a ration is the single exemption from it.
RATION_TAG = ("ration", "food_class")

#: How many rations a soul carries. It restocks only below this.
RATION_CARRY_MAX = 1

#: What a restock point advertises (`db.advertises`). Deliberately not
#: `hunger`: a machine is where a pocket is filled, not a place to eat.
#: Advertising hunger would let a machine next door beat a kitchen
#: across town on value over distance, and the colony would live on
#: bars.
RATION_ADVERT = "ration"

#: How long a soul remembers being told "there is no route to a ration
#: from this room". Range, opening and price are asked on every idle
#: think because they cost nothing; the route costs a pathfind, so a NO
#: is remembered for this long, room by room (a soul on a beat is idle
#: at every stop of it). A yes is never remembered: it is acted on in
#: the same think.
RATION_ROUTE_RECHECK_SECONDS = 900

# ---------------------------------------------------------------- mood

#: The `ate_well` thought for a finished meal of default quality. The
#: lift scales in proportion to quality, so better food is felt and a
#: ration is felt less.
ATE_WELL_VALENCE = 0.15

#: The most one meal can lift a mood, however good.
ATE_WELL_VALENCE_MAX = 0.30
