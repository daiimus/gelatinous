"""Build 085 — restore the cast the split-brain cost us (#2098).

Two post systems disagreed about which fixture owns a post. The
legacy watcher rebuilt the doctors from blueprints WITHOUT souls
(only the souls watcher ensouls), so Maxwell and Kaspar have been
staffed by mannequins — nobody treated bleeding, and four of the
last five deaths were blood loss. Sable and Delphine fell the other
way: their fixtures ARE souls-owned, so the blueprint watcher stood
down, and the souls watcher had no unemployed candidate to hire —
they simply stayed dead.

This repairs the damage using the real machinery (build_npc,
snapshot restore, _install_keeper) and NO insurance premium: this
is a bug repair, not an in-fiction resleeve.

Idempotent: already-souled keepers are skipped.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/085_restore_the_cast.py
"""

import time

from evennia.utils.search import search_object

from world.souls import engine
from world.souls.posts import _install_keeper, _post_room, RESLEAVE_GAP

now = time.time()


def _restore_estate(npc, post, shift):
    """Give back what the estate kept, minus the death gap."""
    snap = (post.db.post_memory_snapshots or {}).get(shift) \
        or post.db.post_memory_snapshot
    if not snap:
        return 0
    died = float(snap.get("died_at") or now)
    cutoff = died - RESLEAVE_GAP
    mems = [r for r in (snap.get("memories") or [])
            if float(r.get("created", 0) or 0) < cutoff]
    npc.db.llm_memories = mems
    npc.db.llm_dossiers = dict(snap.get("dossiers") or {})
    npc.db.soul_thoughts = [t for t in (snap.get("thoughts") or [])
                            if float(t[0]) < cutoff]
    return len(mems)


# (post dbref, shift, existing body dbref or None, blueprint key)
CAST = [
    ("#3137", "day", "#8378", "doctor_nikolai"),    # Maxwell OR
    ("#5130", "day", "#8394", "doctor_marta"),      # Kaspar UC
    ("#3069", "swing", None, "bartender_sable"),    # Helix Lounge
    ("#5150", "night", None, "bartender_del"),      # The Last Shift
]

for post_ref, shift, body_ref, bp_key in CAST:
    post = next(iter(search_object(post_ref)), None)
    if post is None or not post.pk:
        print(f"BUILD 085: post {post_ref} missing; skipped")
        continue
    room = _post_room(post)
    npc = next(iter(search_object(body_ref)), None) if body_ref else None

    if npc is not None and npc.tags.get(engine.SOUL_TAG[0],
                                        category=engine.SOUL_TAG[1]):
        print(f"BUILD 085: {npc.key} already souled; skipped")
        continue

    if npc is None:
        from world.npcs.blueprints import build_npc
        npc = build_npc(bp_key, room)
        npc.db.is_npc = True
        origin = "rebuilt from blueprint"
    else:
        origin = "existing body ensouled"

    mems = _restore_estate(npc, post, shift)
    _install_keeper(npc, post, room, shift)
    print(f"BUILD 085: {npc.key} #{npc.id} — {origin}, {mems} memories "
          f"restored, {shift} shift at {room.key}")

print("BUILD 085: the cast is back on the floor")
