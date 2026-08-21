"""Build 098 — one post registry (#2132).

Two watchers disagreed about what a post is, and that disagreement
killed the colony: the legacy blueprint sweep kept rebuilding doctors
at fixtures the souls registry didn't own, WITHOUT souls, so Maxwell
and Kaspar were staffed by mannequins while people bled out.

The souls registry has since converged on nine of the eleven — it
already holds each cast member's blueprint against the right shift.
This registers the two the legacy sweep uniquely protected, so that
watcher can be retired without losing anyone:

  * the Rook — postless by design (a recluse works from a sealed
    room), so her broadcast chair becomes a post held by nobody but
    her. Resleeve-only: no stranger is ever seated at that board.
  * Vesper — the Helix VIP chaise, same arrangement.

Also states each post's policy explicitly. It had been left at the
default `successor` everywhere, and the sweep only reached the
resleeve path because a registered blueprint quietly overrode it —
correct behaviour reached by accident, which is the kind of thing
that stops being correct when someone edits it.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/098_one_post_registry.py
"""

from evennia.utils.search import search_object

from world.souls import engine
from world.souls.posts import get_posts, register_post

# blueprint -> (fixture dbref, role, shift) for the two the souls
# registry never covered
UNCOVERED = (
    ("dj_rook", "#6035", "dj", "night"),          # her broadcast chair
    ("companion_vesper", "#5278", "companion", "swing"),   # the VIP chaise
)

for bp_key, ref, role, shift in UNCOVERED:
    fixture = next(iter(search_object(ref)), None)
    if fixture is None or not fixture.pk:
        print(f"BUILD 098: {ref} missing; {bp_key} left uncovered")
        continue
    # the holder may not be souled — Vesper works her chaise without a
    # needs engine — so look through every character, not just souls
    from evennia.objects.models import ObjectDB
    from world.npcs.blueprints import BLUEPRINTS
    want = BLUEPRINTS[bp_key]["name"]
    holder = next((s for s in engine.get_souls()
                   if s.pk and s.db.blueprint_key == bp_key), None)
    if holder is None:
        holder = ObjectDB.objects.filter(db_key=want).first()
    if holder is not None:
        holder.db.essential = True          # archived, never deleted
        holder.db.blueprint_key = bp_key
    register_post(fixture, role=role, schedule=shift, wage_rate=0.0,
                  policy="resleave", keeper=holder, shifts=(shift,))
    bps = dict(fixture.db.post_blueprints or {})
    bps[shift] = bp_key
    fixture.db.post_blueprints = bps
    # her own till would be the wrong idea; the treasury covers her
    fixture.db.post_insurer = fixture.db.post_insurer or None
    print(f"BUILD 098: {fixture.key} #{fixture.id} is now {bp_key}'s post "
          f"({shift}, resleave-only, keeper={holder.key if holder else None})")

# say the policy out loud everywhere rather than relying on the
# blueprint override
stated = 0
for post in get_posts():
    bps = post.db.post_blueprints or {}
    want = "resleave" if bps else "successor"
    if post.db.post_policy != want:
        post.db.post_policy = want
        stated += 1
print(f"BUILD 098: {stated} posts had their policy stated explicitly")
