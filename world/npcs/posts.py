"""Blueprint-side helpers for the cast.

This module ONCE carried a second post watcher, sweeping
blueprint-registered fixtures and rebuilding named NPCs on its own
clock. It disagreed with world/souls/posts.py about which fixture
owned a post — the doctors were registered on their autodocs here
and on their treatment rooms there — so both systems acted, and the
bodies this one rebuilt were never ensouled. Maxwell and Kaspar
stood staffed by mannequins while the colony bled out (#2132).

There is one registry now: world/souls/posts.py. What remains here
is the imprint snapshot the death path still calls.
"""


import time

from evennia.utils.search import search_object


def _resolve(dbref):
    hits = search_object(dbref)
    return hits[0] if hits else None


def snapshot_keeper_memory(npc):
    """§P3, the death-side half: called from the death machinery JUST BEFORE
    a dead NPC object is deleted. If the deceased kept a registered post,
    their dossiers + episodic memory are copied onto the POST — the imprint
    the policy disposes of: ``resleave`` restores it (insurance covers the
    self), ``successor`` never reads it (the empty book is the point; the
    snapshot stays as GM-readable archaeology). Never raises — death must
    not be blockable by bookkeeping."""
    try:
        from evennia.utils.dbserialize import deserialize
        from world.npcs.blueprints import BLUEPRINTS
        for key, bp in BLUEPRINTS.items():
            post = (bp.get("post") or {})
            if not post.get("fixture"):
                continue
            fixture = _resolve(post["fixture"])
            if not fixture or fixture.db.post_keeper != npc:
                continue
            fixture.db.post_memory_snapshot = {
                "keeper": npc.key,
                "taken": time.time(),
                "dossiers": deserialize(npc.db.llm_dossiers) or {},
                "memories": deserialize(npc.db.llm_memories) or [],
            }
            return
    except Exception:  # noqa: BLE001 — never block a death on bookkeeping
        pass


