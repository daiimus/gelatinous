"""Build 064 — Cistern No. 1 gets its belly: hatch + Inside the Tank.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/064_cistern_one_interior.py
    then a foreground reload.

Owner: every cistern follows the No. 3 design — a hatch on the lid into
an off-grid interior — because the future water system wants hackable /
repairable / sabotageable pumps IN each tank, and the rooms should be
waiting for them. The runt keeps its proportions (no ladder-cage rooms
at one storey; the stall ladder already reaches the lid): this adds
only the hatch and the drum interior, with a dormant pump housing
seeded in the desc as the future fixture's socket. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

ROOM_TC = "typeclasses.rooms.Room"
EXIT_TC = "typeclasses.exits.Exit"
ALIAS = {"in": ["hatch", "enter"], "out": ["o", "exit"]}

INTERIOR_DESC = (
    "Inside the runt. No. 1's drum is shallow and old — the hatch-light "
    "lands on maybe a hand's depth of standing water over a sediment the "
    "colour of tea, ring-marked up the walls where better years stood "
    "deeper. In the centre squats the pump housing, a cold iron toad of "
    "a machine, its breaker box shut, its gauge needle asleep on the pin. "
    "GH-1 is stencilled on the casing beside an inspection tally that "
    "stopped years ago. The rivets tick as the day's heat leaves.")


def by_key(key):
    return next((r for r in ObjectDB.objects.filter(db_key=key)
                 if r.destination is None), None)


def link(loc, dest, key):
    if loc is None or dest is None or any(e.key == key for e in loc.exits):
        return 0
    create_object(EXIT_TC, key=key, aliases=ALIAS.get(key, []),
                  location=loc, destination=dest)
    return 1


c1 = by_key("Greenhaus Cistern No. 1 - Tank Top")
inside = by_key("Greenhaus Cistern No. 1 - Inside the Tank")
made = 0
if inside is None:
    inside = create_object(ROOM_TC,
                           key="Greenhaus Cistern No. 1 - Inside the Tank")
    made += 1
inside.db.desc = INTERIOR_DESC
inside.db.type = "interior"
inside.db.outside = False

exits = link(c1, inside, "in")
exits += link(inside, c1, "out")

# the lid desc names the hatch
c1.db.desc = ("The lid of Greenhaus Cistern No. 1 — the sole survivor of "
              "the numbered set on this block, a squat riveted drum on "
              "splayed legs over the corner off Braddock. The deck plate "
              "is dished with age and slick where the fill valve weeps; "
              "the numeral is repainted annually by someone who clearly "
              "hates ladders. A service hatch sits off-centre in the "
              "plate, its wheel stiff with verdigris. The ladder drops "
              "among the avionics stalls at the alley's south end. East "
              "and northeast, across the lane's air, the Fungary's "
              "first-level rails wait for the committed.")

print(f"BUILD 064: Cistern No. 1 interior — {made} room, {exits} exits "
      f"(in/out via the lid hatch). Pump socket seeded, awaiting the "
      f"water system.")
