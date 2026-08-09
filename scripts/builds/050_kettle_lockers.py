"""Build 050 — The Kettle: room type + the locker bank.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/050_kettle_lockers.py
    then a foreground reload.

Two things:
  (1) The Kettle's cells read as "interior"; retype them "bathhouse".
  (2) A LockerBank fixture in the changing room — one integrated item that
      IS the whole locker: rent (100/week), open/close, stash/retrieve, each
      gated to your sleeve; nobody sees or touches anyone else's. Forfeited
      lockers empty into a lost-property bin in the boiler room after the
      one-month grace.

Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz
from typeclasses.lockers import LockerBank
from typeclasses.items import Item


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


# ---- 1. retype the six Kettle cells -> bathhouse --------------------
KETTLE = [(-7, -11), (-8, -11), (-7, -10), (-8, -10), (-7, -9), (-8, -9)]
typed = 0
for x, y in KETTLE:
    r = at((x, y, 0))
    if r is not None:
        r.db.type = "bathhouse"
        typed += 1

# ---- 2. the lost-property bin in the boiler room --------------------
boiler = at((-8, -11, 0))
binx = next((o for o in boiler.contents if o.key == "lost-property bin"), None)
if binx is None:
    binx = create_object(Item, key="lost-property bin", location=boiler,
                         home=boiler)
    binx.aliases.add(["bin", "lost property"])
    binx.db.desc = ("A dented steel bin behind the boiler where the house "
                    "empties out lapsed lockers — other people's forgotten "
                    "lives, waiting to be claimed or sold on.")
    binx.db.integrate = True
    binx.locks.add("get:false()")
    binx.db.integration_desc = (
        "A |clost-property bin|n stands behind the boiler, heaped with the "
        "contents of lockers nobody came back for.")

# ---- 3. the locker bank in the changing room ------------------------
changing = at((-7, -10, 0))
bank = next((o for o in changing.contents if isinstance(o, LockerBank)), None)
if bank is None:
    bank = create_object(LockerBank, key="bank of lockers", location=changing,
                         home=changing)
    bank.aliases.add(["lockers", "locker bank", "locker"])
bank.db.desc = (
    "A wall of scuffed steel lockers, numbered in flaking paint, most of them "
    "shut and a few hanging open and empty. A coin slot on the end takes "
    "tokens by the week; the doors read your sleeve, so only yours opens to "
    "you.")
bank.db.forfeit_bin = binx

# a nudge in the room prose
if "lockers" not in (changing.db.desc or "").lower():
    changing.db.desc = (changing.db.desc or "").rstrip() + (
        " A wall of coin-slot lockers runs down one side for what you'd rather "
        "not take into the water.")

print(f"BUILD 050: {typed} cells -> bathhouse; bank #{bank.id} in "
      f"#{changing.id}; forfeit bin #{binx.id}.")
