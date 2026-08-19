"""Build 079 — the Full Soul Count, Batch B: the social anchors.

The bartenders, the doctors, and the dispatcher join the economy.
Bars and clinics are static locales — 24/7, three slots each — so
every anchor takes the shift that fits their legend: Sable owns the
Helix's evening swing, Sully pours the day shift at the Hub and Howl,
and Delphine Marchetti works nights at a bar called The Last Shift,
because of course she does. Sully's till already holds 166 tokens of
previously-uncollectable bar income (#1515) — now it's his payroll.

Their blueprints attach to their shifts; open slots staff themselves
through succession. Tool seams: bartender pours resolve against the
ROOM's counter (graceful off-post), the dispatch voice is the console
not Petra, and the doctors' bottomless supply draw off-post is a
known seam noted in the issue. The Rook stays unsouled (sealed studio
needs a recluse design).

Idempotent: skips anyone already ensouled.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/079_batch_b_ensouls.py
"""

from evennia.utils.search import search_object

from world import rental
from world.souls import engine, ensoul
from world.souls.posts import register_post

DAY = 24 * 3600
ALL_SHIFTS = ("day", "swing", "night")

#: (npc, post fixture/room, role, shift, blueprint, venue ref or None)
BATCH = [
    ("#3070", "#3069", "bartender", "swing", "bartender_sable", "#3069"),
    ("#2706", "#2705", "bartender", "day", "bartender_sully", "#2705"),
    ("#5151", "#5150", "bartender", "night", "bartender_del", "#5150"),
    ("#5134", "#5130", "doctor", "day", "doctor_marta", None),
    ("#3164", "#3137", "doctor", "day", "doctor_nikolai", "#8287"),
    ("#4955", "#4963", "dispatcher", "day", "dispatch_petra", None),
]

kiosk = next(iter(search_object("#5640")), None)
souled = {s.id for s in engine.get_souls() if s.pk}

for npc_ref, fix_ref, role, shift, blueprint, venue_ref in BATCH:
    npc = next(iter(search_object(npc_ref)), None)
    fixture = next(iter(search_object(fix_ref)), None)
    if npc is None or fixture is None or not npc.pk:
        print(f"  {npc_ref}: MISSING pieces; skipped")
        continue
    if npc.id in souled:
        print(f"  {npc.key}: already ensouled; skipped")
        continue
    register_post(fixture, role=role, schedule=shift, wage_rate=0.02,
                  policy="successor", delay=3 * DAY, keeper=npc,
                  shifts=ALL_SHIFTS)
    slots = dict(fixture.db.post_slots or {})
    for s in ALL_SHIFTS:
        if s != shift and slots.get(s, {}).get("keeper") is None:
            slots[s] = {"keeper": None, "vacant_since": 1.0}
    fixture.db.post_slots = slots
    bps = dict(fixture.db.post_blueprints or {})
    bps[shift] = blueprint
    fixture.db.post_blueprints = bps
    # bars are their own tills; tag them for the tithe if untagged
    if fixture.db.register is not None:
        fixture.tags.add("till", category="souls")
    if not npc.tokens:
        npc.tokens = 10
    ok, msg = rental.assign_cube(npc, kiosk)
    home = rental.residence_of(npc)
    venue = (next(iter(search_object(venue_ref)), None)
             if venue_ref else None)
    post_room = fixture.location if fixture.location is not None else fixture
    ensoul(npc, role=role, home=home, post=post_room, schedule=shift,
           wage_rate=0.02, venue=venue)
    print(f"  {npc.key} (#{npc.id}) {role}/{shift} @ {post_room.key} "
          f"till:{venue.db.register if venue else 'treasury'} "
          f"home:{home.key if home else 'NONE'} "
          f"kiosk:{'ok' if ok else 'FAILED — ' + msg}")

print("BUILD 079: batch B ensouled")
print(f"  souls: {len([s for s in engine.get_souls() if s.pk])}")