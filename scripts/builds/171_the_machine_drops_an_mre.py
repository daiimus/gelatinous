"""Build 171 — the cigarette machine drops an MRE (#3806).

Owner, 2026-11-13: "Let's make a MRE."

The mechanics shipped dormant in #3804: a soul may carry one ration,
eats it when no meal is worth the walk, and goes for another on an idle
beat. Nothing in the world was a ration or sold one. This puts the one
source in: the battered cigarette machine on Bhavani Corridor, which
every soul that eats bought food lives within the planner's range of
(read from the live database, 2026-11-13).

On the one object, #3174, and nothing else:

1. `longhaul_mre` joins its wares at 0, the price its other wares carry.
2. It advertises `ration` and takes the `advertiser` tag the planner
   finds advertisers by. It does NOT advertise `hunger`: a machine is
   where a pocket is filled, not a place to eat.
3. One sentence is added to its description, so that what it sells can
   be read off it.

What follows in play, by itself: each soul that eats bought food, on an
idle beat with no ration in its pocket, walks to Bhavani Corridor, buys
one and puts it away. That is one MRE a soul, once, and one more each
time one is eaten.

The machine is named by dbref AND checked against its key and class
before anything is written; a mismatch aborts with nothing changed. The
prototype must be loaded (reload after the merge, then run this): if it
is not, the build aborts with nothing changed. Idempotent: each step
reads before it writes and says what it found. DRY_RUN=True prints the
plan and writes nothing.

Run IN-GAME (idmapper):
    @py exec(open('/usr/src/game/scripts/builds/171_the_machine_drops_an_mre.py').read(), {'print': self.msg})
"""

from evennia.prototypes.prototypes import search_prototype
from evennia.utils.search import search_object

from typeclasses.shopkeeper import ShopContainer
from world.souls import actions, constants

DRY_RUN = False

MACHINE = 3174
MACHINE_KEY = "battered cigarette machine"
WARE = "longhaul_mre"
PRICE = 0
#: what the planner scores a source by, over distance; the range other
#: advertisers use (a kitchen 0.8 to 0.9). With one source in the world
#: it decides nothing yet.
ADVERT_VALUE = 0.8
#: the description as it stood on 2026-11-13; anything else is left alone
DESC_WAS = (
    "A dented, graffiti-tagged cigarette machine bolted to the wall, its "
    "backlit panel flickering between a few stubborn brands. A coin slot "
    "and a row of scratched pull-knobs promise a hit of tar to anyone with "
    "tokens to spare.")
DESC_ADDS = (
    " The last knob in the row has lost its brand card to a strip of tape "
    "lettered MRE, and what drops from that chute is flat, tan and stamped "
    "Longhaul.")

tag = f"BUILD 171{' (dry run)' if DRY_RUN else ''}:"


def build():
    found = [o for o in search_object(f"#{MACHINE}") if o.pk]
    machine = found[0] if found else None
    if (machine is None or machine.key != MACHINE_KEY
            or not isinstance(machine, ShopContainer)):
        print(f"{tag} #{MACHINE} is not the {MACHINE_KEY} "
              f"(found {machine!r}); ABORTED, nothing changed")
        return
    if not search_prototype(WARE):
        print(f"{tag} prototype {WARE!r} is not loaded (reload first); "
              f"ABORTED, nothing changed")
        return

    wares = dict(machine.db.prototype_inventory or {})
    if WARE in wares:
        print(f"{tag} already stocks {WARE} at {wares[WARE]}; left as is")
    else:
        # the shelf's own door for a new ware; no quantity, so the
        # machine stays infinite like its other wares
        if not DRY_RUN and not machine.add_prototype(WARE, price=PRICE):
            print(f"{tag} the machine refused {WARE}; ABORTED at step 1")
            return
        print(f"{tag} stocks {WARE} at {PRICE} beside {sorted(wares)}")

    ads = dict(machine.db.advertises or {})
    if ads.get(constants.RATION_ADVERT):
        print(f"{tag} already advertises {ads}; left as is")
    else:
        ads[constants.RATION_ADVERT] = ADVERT_VALUE
        if not DRY_RUN:
            machine.db.advertises = ads
        print(f"{tag} advertises {ads}")
    # advertisers are found by an INDEXED TAG, never by the attribute
    if machine.tags.has("advertiser", category="souls"):
        print(f"{tag} already tagged as an advertiser")
    else:
        if not DRY_RUN:
            machine.tags.add("advertiser", category="souls")
        print(f"{tag} tagged as an advertiser")

    desc = machine.db.desc or ""
    if DESC_ADDS.strip() in desc:
        print(f"{tag} description already names the MRE; left as is")
    elif desc != DESC_WAS:
        print(f"{tag} description is not the one this build knows; "
              f"left as is, look at it: {desc!r}")
    else:
        if not DRY_RUN:
            machine.db.desc = DESC_WAS + DESC_ADDS
        print(f"{tag} description now ends:{DESC_ADDS}")

    if DRY_RUN:
        return
    # read back the way the planner reads it
    actions._ad_cache["at"] = 0.0
    print(f"{tag} the planner reads its rations as "
          f"{actions._ration_wares(machine)}, "
          f"open={actions._counter_open(machine)}, "
          f"listed={machine in actions._advertiser_objs()}")


build()
