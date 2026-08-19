"""Posts & succession (spec §13, §3.6) — the post survives its keeper.

SHIFT SLOTS (owner rulings 2026-08-20): venues run 24/7 for a global
playerbase, staffed in EIGHT-hour shifts — day, swing, night. A post
fixture carries a SLOT per shift (`db.post_slots`); each slot holds
its own keeper, its own vacancy stamp, its own optional blueprint
(`db.post_blueprints[shift]` — the named person who owns that shift).
The counter never closes; the faces change.

The vacancy watcher rides the souls heartbeat; a dead, deleted, or
desouled slot-keeper stamps that slot vacant, and once the grace
elapses the policy fills it: `resleave` rebuilds the slot's named
keeper from their blueprint (estate restored minus the death gap, a
real premium debited), `successor` offers the slot to the nearest
unemployed soul. No candidate: the slot stays dark and the venue limps
on its other shifts — a visibly tired counter, not a closed one.
"""

import time

from evennia.utils.search import search_tag

POST_TAG = ("post", "souls")
SWEEP_EVERY_BEATS = 10
DEFAULT_DELAY = 6 * 3600          # vacancy grace before succession
RESLEAVE_PREMIUM = 40             # what the insurer's till pays Maxwell
RESLEAVE_GAP = 5400               # the last ~90min never made the backup


def register_post(fixture, role, schedule="day", wage_rate=0.02,
                  policy="successor", delay=DEFAULT_DELAY, keeper=None,
                  shifts=None):
    """Make *fixture* (counter or room) an administrative post.

    `shifts` is the tuple of shift slots this post staffs (default: the
    single `schedule` given — roomed posts like the caretaker may be
    one-shift; 24/7 venues register all three). `keeper` holds the
    `schedule` slot."""
    fixture.db.post_role = role
    fixture.db.post_wage_rate = float(wage_rate)
    fixture.db.post_policy = policy
    fixture.db.post_delay = int(delay)
    slots = dict(fixture.db.post_slots or {})
    for shift in (shifts or (schedule,)):
        slots.setdefault(shift, {"keeper": None, "vacant_since": None})
    if keeper is not None:
        slots[schedule] = {"keeper": keeper, "vacant_since": None}
        fixture.db.post_keeper = keeper       # legacy mirror (shop gate)
    fixture.db.post_slots = slots
    fixture.tags.add(POST_TAG[0], category=POST_TAG[1])
    return fixture


def get_posts():
    return [p for p in search_tag(POST_TAG[0], category=POST_TAG[1]) if p]


def _post_room(post):
    return post.location if post.location is not None else post


def any_keeper_present(fixture) -> bool:
    """Is ANY shift-holder physically at the fixture? (The 24/7 shop
    gate: whoever's shift it is should be standing there; presence is
    what opens the counter, whoever's face it is.)"""
    room = _post_room(fixture)
    for slot in (fixture.db.post_slots or {}).values():
        keeper = slot.get("keeper")
        if keeper is not None and keeper.pk and keeper.location == room:
            return True
    legacy = fixture.db.post_keeper
    return bool(legacy is not None and legacy.pk
                and legacy.location == room)


def _slot_held(post, shift, slot) -> bool:
    """Is this slot's keeper alive, souled, and still on this post?"""
    keeper = slot.get("keeper")
    if keeper is None or not keeper.pk:
        return False
    room = _post_room(post)
    return (keeper.db.soul_post == room
            and (keeper.db.soul_schedule or "day") == shift)


def _eligible_candidates(room):
    """Unemployed souls, nearest first — human-shaped, idle, alive."""
    from world.souls import engine
    from world.souls import needs as needs_mod
    from world.spatial import get_xyz

    origin = get_xyz(room)
    out = []
    for soul in engine.get_souls():
        if not soul.pk or soul.location is None:
            continue
        if soul.db.soul_post is not None or soul.db.soul_job:
            continue
        if needs_mod.profile_name(soul) == "robot":
            continue
        pos = get_xyz(soul.location)
        dist = (max(abs(origin[0] - pos[0]), abs(origin[1] - pos[1]))
                if origin and pos else 999)
        out.append((dist, soul.id, soul))
    out.sort()
    return [s for _, _, s in out]


def sweep(now=None):
    """One vacancy pass over every SLOT of every post: stamp the newly
    dark, fill the grace-elapsed. One succession per sweep, never over
    a live fight."""
    from world.director.security import _in_combat

    now = now if now is not None else time.time()
    for post in get_posts():
        slots = dict(post.db.post_slots or {})
        if not slots and post.db.post_keeper is not None:
            # legacy single-keeper post: adopt into the slot model
            shift = "day"
            slots = {shift: {"keeper": post.db.post_keeper,
                             "vacant_since": post.db.post_vacant_since}}
            post.db.post_slots = slots
        dirty = False
        for shift, slot in slots.items():
            if _slot_held(post, shift, slot):
                if slot.get("vacant_since") is not None:
                    slot["vacant_since"] = None      # re-manned
                    dirty = True
                continue
            if slot.get("vacant_since") is None:
                slot["vacant_since"] = now           # newly dark
                if slot.get("keeper") is not None \
                        and not (slot["keeper"] and slot["keeper"].pk):
                    slot["keeper"] = None
                dirty = True
                continue
            if now - float(slot["vacant_since"]) < int(
                    post.db.post_delay or DEFAULT_DELAY):
                continue
            room = _post_room(post)
            if any(_in_combat(o) for o in room.contents
                   if hasattr(o, "ndb")):
                continue                             # never over a fight
            policy = post.db.post_policy
            if policy == "resleave" or (
                    (post.db.post_blueprints or {}).get(shift)):
                if _try_resleave(post, room, shift, slot, now):
                    post.db.post_slots = slots
                    return                           # one per sweep
                continue        # can't afford yet: the till keeps earning
            if policy != "successor":
                continue
            candidates = _eligible_candidates(room)
            if not candidates:
                continue                             # the slot stays dark
            _offer(candidates[0], post, room, shift)
            if dirty:
                post.db.post_slots = slots
            return                                   # one per sweep
        if dirty:
            post.db.post_slots = slots


def _try_resleave(post, room, shift, slot, now) -> bool:
    """The insurance pays out (spec §P3): rebuild this SLOT's named
    keeper from their blueprint, restore the estate MINUS the death gap
    (the last ~90 minutes never made the backup — murder stays a
    mystery), and debit the insurer's till a REAL premium paid to
    Maxwell. A till that can't afford it keeps earning — a cart can
    sell noodles toward its own keeper's resurrection."""
    from evennia.utils.search import search_object

    bp_key = (post.db.post_blueprints or {}).get(shift) \
        or post.db.post_blueprint
    if not bp_key:
        return False
    till = post if post.db.register is not None else post.db.post_insurer
    if till is None or int(till.db.register or 0) < RESLEAVE_PREMIUM:
        return False
    from world.npcs.blueprints import build_npc
    try:
        npc = build_npc(bp_key, room)
    except Exception:  # noqa: BLE001 — a broken blueprint must not loop-spawn
        return False
    npc.db.is_npc = True
    # the premium moves for real: insurer till -> Maxwell's terminal
    till.db.register = int(till.db.register or 0) - RESLEAVE_PREMIUM
    provider = next((o for o in search_object("a Thawn-Harrison billing "
                                              "terminal") if o.pk), None)
    if provider is not None:
        provider.db.register = int(provider.db.register or 0) \
            + RESLEAVE_PREMIUM

    # the estate returns, minus the gap
    snap = (post.db.post_memory_snapshots or {}).get(shift) \
        or post.db.post_memory_snapshot
    if snap:
        died = float(snap.get("died_at") or now)
        cutoff = died - RESLEAVE_GAP
        npc.db.llm_memories = [
            r for r in (snap.get("memories") or [])
            if float(r.get("created", 0) or 0) < cutoff]
        npc.db.llm_dossiers = dict(snap.get("dossiers") or {})
        npc.db.soul_thoughts = [
            t for t in (snap.get("thoughts") or [])
            if float(t[0]) < cutoff]

    _install_keeper(npc, post, room, shift)
    from world.souls import thoughts as thoughts_mod
    thoughts_mod.add_thought(
        npc, "resleeved", -0.50,
        "woke in a new sleeve; the last hours before the dark are "
        "simply gone")
    npc.execute_cmd("emote is back at the post, moving like the week "
                    "never happened.")
    return True


def _install_keeper(npc, post, room, shift):
    """Bind a keeper into a slot: housing, soul, slot record, legacy
    mirror, venue wages only where a till actually exists."""
    from evennia.utils.search import search_object

    try:
        from world import rental
        kiosk = next(iter(search_object("#5640")), None)
        if kiosk is not None:
            rental.assign_cube(npc, kiosk)
        home = rental.residence_of(npc)
    except Exception:  # noqa: BLE001 — homeless but employed beats neither
        home = None
    from world.souls import engine
    engine.ensoul(npc, role=post.db.post_role or "worker", home=home,
                  post=room, schedule=shift,
                  wage_rate=float(post.db.post_wage_rate or 0.02),
                  venue=post if post.db.register is not None else None)
    slots = dict(post.db.post_slots or {})
    slots[shift] = {"keeper": npc, "vacant_since": None}
    post.db.post_slots = slots
    post.db.post_keeper = npc             # legacy mirror (shop gate et al)


def snapshot_estate(character) -> bool:
    """At death, a slot-keeper's memories become the post's property
    (reincarnation spec §2), keyed by their shift: episodic memories,
    dossiers, and thoughts copied onto the fixture BEFORE the corpse
    machinery deletes the body — kept whether or not anyone ever pays
    to restore them."""
    import time as _time

    from evennia.utils.dbserialize import deserialize

    for post in get_posts():
        for shift, slot in (post.db.post_slots or {}).items():
            if slot.get("keeper") != character:
                continue
            snaps = dict(post.db.post_memory_snapshots or {})
            snaps[shift] = {
                "name": character.key,
                "died_at": _time.time(),
                "memories": deserialize(character.db.llm_memories) or [],
                "dossiers": deserialize(character.db.llm_dossiers) or {},
                "thoughts": deserialize(character.db.soul_thoughts) or [],
            }
            post.db.post_memory_snapshots = snaps
            return True
        if post.db.post_keeper == character:     # legacy fallback
            post.db.post_memory_snapshot = {
                "name": character.key,
                "died_at": _time.time(),
                "memories": deserialize(character.db.llm_memories) or [],
                "dossiers": deserialize(character.db.llm_dossiers) or {},
                "thoughts": deserialize(character.db.soul_thoughts) or [],
            }
            return True
    return False


def _offer(soul, post, room, shift):
    """Hand the claim job: walk there for real, then take the shift.
    Goal is "claim", NOT "duty" — the shift-release logic clears duty
    jobs outside work hours, which ate every after-hours job offer
    (you take the job tonight; you start when your shift comes)."""
    soul.db.soul_job = {
        "goal": "claim", "band": 2, "at": 0,
        "steps": [
            {"do": "travel", "room": room.id},
            {"do": "claim", "post": post.id, "shift": shift},
        ],
    }


def do_claim(soul, post, shift="day"):
    """The claim step's business: bind soul to the slot (jobs.py calls)."""
    from world.souls import thoughts

    room = _post_room(post)
    soul.db.soul_post = room
    soul.db.soul_role = post.db.post_role or "worker"
    soul.db.soul_schedule = shift
    soul.db.soul_wage_rate = float(post.db.post_wage_rate or 0.02)
    # only a real till pays wages from itself; till-less fixtures are
    # treasury posts
    soul.db.soul_venue = post if post.db.register is not None else None
    slots = dict(post.db.post_slots or {})
    slots[shift] = {"keeper": soul, "vacant_since": None}
    post.db.post_slots = slots
    post.db.post_keeper = soul            # legacy mirror
    post.db.post_vacant_since = None
    thoughts.add_thought(soul, "new_job", 0.30,
                         f"picked up the {shift}-shift "
                         f"{soul.db.soul_role} work at {room.key}")