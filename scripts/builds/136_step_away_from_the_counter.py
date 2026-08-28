"""Build 136 — clear placements stranded by the old volatile marker (#2339).

`placed_by_shift` used to live on `ndb`, which dies on reload, while
`db.temp_place` does not. So every soul placed at a counter before the
marker was made persistent carries a placement line nothing can clear:
Ezra Vantomme standing in the Snailery yard "behind the steel counter"
-- a counter in Kaspar Pawn & Salvage -- and Wren, a courier, wearing
the same line.

The fix makes future placements clearable. It cannot clear these,
because the flag granting permission was never written for them.

This is the migration, and it is deliberately conservative: a soul's
placement is only touched when it DIFFERS from the one their blueprint
authored. Blueprint text is the character's own ("waiting by the
counter with a parcel under one arm"); anything else was put there by
a shift. Souls with no blueprint entry are left alone entirely.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/136_step_away_from_the_counter.py
"""

from world.npcs.blueprints import BLUEPRINTS
from world.souls import posts as posts_mod
from world.souls.engine import get_souls

authored = {}
for key, bp in BLUEPRINTS.items():
    body = posts_mod._living_body(key)
    if body is not None:
        authored[body.id] = bp.get("temp_place")

cleared = kept = unknown = adopted = 0
for soul in get_souls():
    place = soul.db.temp_place or ""
    if not place:
        continue
    if soul.id not in authored:
        # No blueprint to compare against -- but if the line is one the
        # SHIFT system itself generates for this soul's post, it is
        # ours and the reconciler should own it from here.
        from world.souls.jobs import _post_placement
        if place == (_post_placement(soul) or ""):
            soul.db.placed_by_shift = True
            print(f"BUILD 136: adopting {soul.key[:20]:20} {place[:40]!r}")
            adopted += 1
        else:
            unknown += 1
        continue
    if place == (authored[soul.id] or ""):
        kept += 1
        continue                       # the character's own line
    from world.souls.jobs import _post_placement
    if place == (_post_placement(soul) or ""):
        # they are standing where this line belongs: adopt, do not strip
        soul.db.placed_by_shift = True
        adopted += 1
        continue
    print(f"BUILD 136: clearing {soul.key[:20]:20} {place[:44]!r}")
    soul.db.temp_place = ""
    soul.db.placed_by_shift = False
    cleared += 1

print(f"BUILD 136: cleared={cleared} kept_authored={kept} "
      f"adopted_for_reconciler={adopted} left_alone={unknown}")

# Prove the yard reads right afterwards.
from evennia.objects.models import ObjectDB
yard = [r for r in ObjectDB.objects.all()
        if r.key == "Escallier Snailery - Yard" and r.destination is None]
if yard:
    yard = yard[0]
    c = [o for o in yard.contents if o.attributes.has("post_slots")]
    on_duty = posts_mod.on_duty_keeper(c[0]) if c else None
    print(f"BUILD 136: on duty at the Snailery: {on_duty}")
    for o in yard.contents:
        if not hasattr(o, "medical_state") or o.destination:
            continue
        print(f"BUILD 136:   {o.key[:20]:20} {(o.db.temp_place or '')[:44]!r}")
