"""The posts watcher — NPC reincarnation (NPC_POSTS_AND_REINCARNATION_SPEC §P2).

A **post** is a staffed workplace (the food cart; later the bars, clinics,
counters). The blueprint registry is the single source of truth — each
blueprint's ``post`` dict names its fixture, policy, and delay; there is no
in-game registration (owner's standing rule: no ad-hoc builder commands).

Each director heartbeat, ``maintain_posts()`` sweeps every registered post:

* keeper present → nothing to do (clearing any stale vacancy state);
* keeper gone (dead NPCs are deleted, #1022) → stamp the vacancy and swap the
  fixture to its vacant ``integration_desc`` — the room tells the story;
* vacancy older than the policy delay (and no live combat at the post) →
  reincarnate: ``resleave`` rebuilds the SAME person from the blueprint;
  ``successor`` seats a STRANGER (``build_successor``) with an empty book.

The post persists through death by design: stock, till, and prices are the
cart's property, not the keeper's (owner-decided). Memory snapshot/restore
for re-sleeve is §P3 — the snapshot must be taken at death-time (the object
is deleted before this sweep can see it), which needs the death-side hook.
"""

import time

from evennia.utils.search import search_object


def _resolve(dbref):
    hits = search_object(dbref)
    return hits[0] if hits else None


def _keeper_present(fixture):
    keeper = fixture.db.post_keeper
    return bool(keeper and keeper.pk
                and keeper.location == fixture.location)


def _combat_at(room):
    from world.director.security import _in_combat
    return any(_in_combat(obj) for obj in room.contents
               if hasattr(obj, "is_typeclass")
               and obj.is_typeclass("typeclasses.characters.Character",
                                    exact=False))


def snapshot_keeper_memory(npc):
    """§P3, the death-side half: called from the death machinery JUST BEFORE
    a dead NPC object is deleted. If the deceased kept a registered post,
    their dossiers + episodic memory are copied onto the POST — the estate
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


def maintain_posts(now=None):
    """One sweep over every blueprint-registered post. Never raises — the
    heartbeat guards it, but each post is also isolated so one broken post
    can't stall the others."""
    from world.npcs.blueprints import BLUEPRINTS
    now = now if now is not None else time.time()
    for key, bp in BLUEPRINTS.items():
        post = bp.get("post") or {}
        if not post.get("fixture") or post.get("policy") not in (
                "resleave", "successor"):
            continue
        try:
            _sweep_post(key, bp, post, now)
        except Exception:  # noqa: BLE001 — one post must not stall the sweep
            pass


def _sweep_post(blueprint_key, bp, post, now):
    fixture = _resolve(post["fixture"])
    if not fixture or not fixture.location:
        return
    # Partition (reconciliation 2.3): a fixture registered with the
    # SOULS post system is owned by its watcher — a living resident
    # claims it or the resleave policy pays out. Racing this sweep
    # against that one on a different clock seats a stranger and a
    # neighbor at the same counter.
    if fixture.tags.get("post", category="souls"):
        return
    room = fixture.location

    if _keeper_present(fixture):
        if fixture.db.post_vacant_since:
            _restore_desc(fixture)
            fixture.db.post_vacant_since = None
        return

    if not fixture.db.post_vacant_since:
        # the moment the watcher notices: stamp it, shutter the fixture
        fixture.db.post_vacant_since = now
        if post.get("vacant_desc"):
            if fixture.db.post_active_desc is None:
                fixture.db.post_active_desc = fixture.db.integration_desc
            fixture.db.integration_desc = post["vacant_desc"]
        return

    if now - float(fixture.db.post_vacant_since) < post["delay_hours"] * 3600:
        return
    if _combat_at(room):
        return   # never seat anyone into a live firefight

    from world.npcs.blueprints import build_npc, build_successor
    if post["policy"] == "resleave":
        npc = build_npc(blueprint_key, room)
        # continuity of self is what the insurance pays for: the death-time
        # snapshot comes back with them, then is consumed
        snapshot = fixture.db.post_memory_snapshot
        if snapshot:
            npc.db.llm_dossiers = dict(snapshot.get("dossiers") or {})
            npc.db.llm_memories = list(snapshot.get("memories") or [])
            fixture.db.post_memory_snapshot = None
        arrival = post.get(
            "arrival_resleave",
            "{mob} is back at their post, moving like the absence never "
            "happened.")
    else:
        npc = build_successor(blueprint_key, room)
        arrival = post.get(
            "arrival_successor",
            "{mob} steps up and takes over the post like it was always "
            "theirs.")

    fixture.db.post_keeper = npc
    fixture.db.post_vacant_since = None
    _restore_desc(fixture)

    from world.identity_utils import msg_room_identity
    msg_room_identity(location=room, template=arrival,
                      char_refs={"mob": npc})


def _restore_desc(fixture):
    if fixture.db.post_active_desc is not None:
        fixture.db.integration_desc = fixture.db.post_active_desc
        fixture.db.post_active_desc = None
