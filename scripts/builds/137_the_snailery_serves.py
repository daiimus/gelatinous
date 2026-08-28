"""Build 137 — the Snailery becomes a restaurant (#2342).

Escallier Snailery is a sit-down snail house: tanks, a yard, a grill-pan
that has known ten thousand snails, and ESCARGOT FOR ALL burned into the
counter's edge. It has been serving like a vending machine -- `buy
snail_skewer from the shell counter`, the item pressed into your hand
off a shelf, nobody taking an order.

That wasn't a mistake in the build. The shop model was the only model
the souls layer could use, and the bar model couldn't hand over food.
#2342 fixed both, so now the venue can be what it is:

  * the shell counter becomes a BarCounter with a BOARD -- the three
    snail dishes, at the prices the shelf already charged. No number
    moves. Kuro stays free, because the free pot is the creed.
  * its shelf is removed. One venue, one door: you order, Nonna plates
    it, it lands on the zinc and you pick it up.
  * all three shift keepers -- Nonna (day), Pia (swing), Tobias (night)
    -- become Bartenders, because the serve path is a Bartender method.
    The counter runs 24/7 and every shift has to be able to take an
    order, not just the one the owner happens to be watching.
  * the two real bars start ADVERTISING, so souls can find them. They
    have been invisible to NPC life since they were built.

Typeclass swaps here keep attributes and do NOT run start hooks on the
PEOPLE -- a Character's creation hook rebuilds a body, and these three
have lived in theirs. The counter is a fixture and does run its hook
(it needs the cmdset and the stools); everything the hook resets is put
back afterwards.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/137_the_snailery_serves.py
"""

from evennia.objects.models import ObjectDB

COUNTER_ID = 8119

#: The board. Prices are the shelf's, carried over untouched: the skewer
#: was 3, the jar 5, the kuro free. Keyword order matters -- `match_recipe`
#: takes the first entry whose keyword appears in what was said, and a
#: soul asks with the FIRST keyword, so each of those is unambiguous.
SNAILERY_MENU = [
    {
        "name": "bowl of kuro-nikomi",
        "order_keywords": ("kuro", "nikomi", "stew", "broth", "soup"),
        "proto": "snail_kuro",
        "price": 0,
        "craft": "ladles the black stew up out of the pot",
    },
    {
        "name": "grilled snail skewer",
        "order_keywords": ("skewer", "escargot", "grilled"),
        "proto": "snail_skewer",
        "price": 3,
        "craft": "lays six on the grill-pan until the shells hiss, then "
                 "threads them onto a wire",
    },
    {
        "name": "jar of pickled snails",
        "order_keywords": ("jar", "pickled", "pickles"),
        "proto": "snail_jar",
        "price": 5,
        "craft": "lifts a jar down off the shelf and wipes the brine off "
                 "the lid",
    },
]

#: What a bar serves, so souls can smell it from the street. Weighted
#: below the dedicated vice counter at Cinder & Leaf (0.9): a bar is
#: where you drink, a shop is where you go when you mean it.
BAR_ADVERTISERS = {
    "the hull-slab bar": {"vice": 0.8},
    "the backlit bar": {"vice": 0.8},
}


def _swap(obj, path, run_hooks=None):
    """Swap typeclass, keeping every attribute. Returns True if moved."""
    if obj.db_typeclass_path == path:
        return False
    obj.swap_typeclass(path, clean_attributes=False,
                       run_start_hooks=run_hooks)
    return True


# --- the counter ----------------------------------------------------------
counter = ObjectDB.objects.get(id=COUNTER_ID)
keep = {
    "desc": counter.db.desc,
    "register": int(counter.db.register or 0),
    "advertises": counter.db.advertises,
    "post_slots": counter.db.post_slots,
    "post_keeper": counter.db.post_keeper,
}
# The fixture DOES run its creation hook: it needs the bar cmdset (that's
# where `order` and `menu` live) and the stools. The hook then blanks the
# board, swaps in a bar's free nibbles and writes a "salvaged bar" line
# over the description -- all restored below.
if _swap(counter, "typeclasses.bar.BarCounter", run_hooks="at_object_creation"):
    print(f"BUILD 137: {counter.key} is a counter you order at")
else:
    print(f"BUILD 137: {counter.key} already converted")

counter.db.menu = SNAILERY_MENU
counter.db.snacks = []              # no brine pods in a snail yard
counter.db.prototype_inventory = None    # one venue, one door
counter.db.item_inventory = None
counter.db.is_infinite = None
counter.db.integration_fallback = None   # the desc already does this work
for attr, value in keep.items():
    if value is not None:
        setattr(counter.db, attr, value)
counter.db.integrate = True

# --- the people who work it ----------------------------------------------
for slot, entry in sorted((counter.db.post_slots or {}).items()):
    keeper = entry.get("keeper")
    if keeper is None:
        print(f"BUILD 137: {slot} shift is dark -- nobody to convert")
        continue
    moved = _swap(keeper, "typeclasses.bar.Bartender")
    keeper.db.is_bartender_npc = True
    print(f"BUILD 137: {slot:6} {keeper.key:18} "
          f"{'-> Bartender' if moved else 'already a Bartender'}")

# --- the bars nobody could find ------------------------------------------
for key, advertises in BAR_ADVERTISERS.items():
    for bar in ObjectDB.objects.filter(db_key=key):
        bar.db.advertises = advertises
        # advertisers are found by an INDEXED TAG, never by the attribute
        # (hardening spec law #3 -- the attribute join is uncached)
        bar.tags.add("advertiser", category="souls")
        where = bar.location.key if bar.location else "nowhere"
        print(f"BUILD 137: {bar.key} ({where}) now advertises {advertises}")

print("BUILD 137: done")
