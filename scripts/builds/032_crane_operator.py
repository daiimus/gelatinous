"""Build 032 — the crane operator and the cab console (P3).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/032_crane_operator.py
    then a foreground reload.

Puts Ossie Trelane in the operator's cab with a Boiler Run base-station
console tuned to the work band (27.0). Callers key up on 27.0 and ask
for a floor; Ossie runs the container there and answers on the air. The
crane order is deterministic (CraneOperator._hear_radio); the LLM is off
for now. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz

BAND = "27.0"


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def in_room(room, key):
    return next((o for o in room.contents if o.key == key), None)


cab = at((-1, -18, 17))
assert cab is not None, "operator's cab missing at (-1,-18,17)"

# ---- the console: a powered base station on the work band ------------
console = in_room(cab, "Boiler Run crane console")
if console is None:
    console = create_object("typeclasses.items.Radio",
                            key="Boiler Run crane console", location=cab)
    console.aliases.add(["console", "crane console", "radio", "base station"])
    console.db.desc = (
        "A bolted-down Boiler Run control console — a bank of worn levers, a "
        "load gauge with a cracked face, and a fixed transceiver whose "
        "display glows a steady 27.0. This is the voice that runs the "
        "container.")
    console.locks.add("get:false()")
console.db.is_radio = True
console.db.is_base_station = True
console.db.is_npc = True             # radio loop-guard: brains observe, never chain
console.db.radio_on = True
console.db.frequency = BAND

# ---- the chair: so the operator is 'seated at' the console -----------
chair = in_room(cab, "operator's chair")
if chair is None:
    chair = create_object("typeclasses.furniture.Furniture",
                          key="operator's chair", location=cab)
    chair.db.desc = ("A cracked vinyl chair on a pedestal, bolted to the cab "
                     "floor so it doesn't slide when the mast sways.")

# ---- Ossie Trelane, the operator ------------------------------------
op = in_room(cab, "Ossie Trelane")
if op is None:
    op = create_object("typeclasses.crane.CraneOperator", key="Ossie Trelane",
                       location=cab)
    op.aliases.add(["ossie", "operator", "crane operator", "trelane"])
op.db.desc = (
    "A broad, weathered crane operator in a Boiler Run hi-viz vest gone grey "
    "with dust, seated at the console like they've grown into it. They watch "
    "the load through the long window more than they watch you, one hand "
    "never far from the levers.")
op.db.is_npc = True
op.db.llm_driven = False              # deterministic crane control; LLM off for now
op.db.voice_description = "gravelly, unhurried"
op.db.voice_ending = "and signs off with a click of the handset"
# seat them at the console
op.db.furniture = chair
op.db.posture = "sitting"

# ---- point callers at the band --------------------------------------
if "27.0" not in (cab.db.desc or ""):
    cab.db.desc = (cab.db.desc or "").rstrip() + (
        " A grease-pencil scrawl by the window reads: CRANE CONTROL — "
        "BOILER RUN WORK CHANNEL 27.0.")
hoard = at((-1, -19, 0))
if hoard is not None and "27.0" not in (hoard.db.desc or ""):
    hoard.db.desc = (hoard.db.desc or "").rstrip() + (
        " A faded sign wired to the fence: DELIVERIES — RAISE THE OPERATOR ON "
        "27.0.")

print(f"BUILD 032: operator #{op.id} seated at chair #{chair.id}, "
      f"console #{console.id} on {console.db.frequency} "
      f"(on={console.db.radio_on}, base={console.db.is_base_station}).")
