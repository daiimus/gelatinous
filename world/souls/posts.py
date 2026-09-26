"""Posts & succession (spec §13, §3.6) — the post survives its keeper.

SHIFT SLOTS (owner rulings 2026-08-20): venues run 24/7 for a global
playerbase, staffed in EIGHT-hour shifts — day, swing, night. A post
fixture carries a SLOT per shift (`db.post_slots`); each slot holds
its own keeper, its own vacancy stamp, its own optional blueprint
(`db.post_blueprints[shift]` — the named person who owns that shift).
The counter never closes; the faces change.

The vacancy watcher rides the souls heartbeat; a dead, deleted, or
desouled slot-keeper stamps that slot vacant, and once the grace
elapses, the dead keeper's own sleeve policy decides: with one on file
they are brought back (the archived body revived, or rebuilt from their
blueprint, the imprint restored minus the death gap — `world/imprint.GAP`
owns that number), and without one the shift is nobody's and a
`successor` post offers it to the nearest unemployed soul. No candidate:
the slot stays dark and the venue limps on its other shifts — a visibly
tired counter, not a closed one. The policy is personal, bought alive at
the Thawn-Harrison terminal (`world/insurance`, #3667); a post never pays
for anyone.
"""

import time

from evennia.utils import logger
from evennia.utils.search import search_tag

POST_TAG = ("post", "souls")
SWEEP_EVERY_BEATS = 10
DEFAULT_DELAY = 6 * 3600          # vacancy grace before succession

#: What `_try_resleave` answers, and what the sweep does with it.
RESLEEVED = "resleeved"           # the person is back; the sweep is spent
HOLD = "hold"                     # transient: wait for the next sweep
SUCCESSOR = "successor"           # not coming back: the shift is nobody's


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


#: Where new sleeves wake — the same chamber the player decants into.
DECANT_ROOM = "#1989"                  # Thawn-Harrison Decantation Chamber


def _decant_room():
    from evennia.utils.search import search_object
    room = next(iter(search_object(DECANT_ROOM)), None)
    return room if room is not None and room.pk else None


def current_shift(hour=None):
    """Which shift the colony clock is on right now."""
    from world.souls.engine import SCHEDULES, _in_block

    if hour is None:
        from world.gametime import colony_now
        t = colony_now()
        hour = t.hour + t.minute / 60.0
    for shift in ("day", "swing", "night"):
        if _in_block(hour, SCHEDULES[shift]["work"]):
            return shift
    return "day"


def on_duty_keeper(post, hour=None):
    """Whoever holds the shift the clock is currently on, if anyone.

    NOT the same question as :func:`keeper_on_duty` fourteen lines down,
    despite the mirror-image name. This one ignores WHERE they are; that
    one requires them to be standing here. Code written as if they were
    interchangeable produced a branch that could never execute (#2606).

    If you are asking "can this counter serve me", you want
    :func:`any_keeper_present`. If you are asking "whose shift is it",
    you want this.
    """
    slot = (post.db.post_slots or {}).get(current_shift(hour)) or {}
    keeper = slot.get("keeper")
    return keeper if keeper is not None and keeper.pk else None


def off_duty_keepers_present(post):
    """Keepers of this post who are standing here on somebody else's
    shift — the person who can tell you they're off, and who isn't."""
    room = _post_room(post)
    now_shift = current_shift()
    out = []
    for shift, slot in (post.db.post_slots or {}).items():
        if shift == now_shift:
            continue
        keeper = slot.get("keeper")
        if keeper is not None and keeper.pk and keeper.location == room:
            out.append(keeper)
    return out


def relief_has_arrived(post) -> bool:
    """Is the CURRENT shift's keeper actually standing this counter?

    Deliberately a RAW read of `post_slots` rather than a call to
    :func:`keeper_on_duty` — that one now accepts a holdover, so asking
    it here would be circular: "am I relieved?" would answer "yes,
    by you".

    Takes the post fixture OR the room it stands in, because the souls
    engine holds `soul_post` as a room while everything here holds the
    fixture.
    """
    fixture = post
    if getattr(post, "db", None) is not None and not post.db.post_slots:
        for obj in getattr(post, "contents", ()) or ():
            if getattr(obj.db, "post_slots", None):
                fixture = obj
                break
    slots = getattr(fixture.db, "post_slots", None) or {}
    if not slots:
        return False
    room = _post_room(fixture)
    slot = slots.get(current_shift()) or {}
    keeper = slot.get("keeper")
    return bool(keeper is not None and keeper.pk and keeper.location == room)


def keeper_on_duty(fixture):
    """WHO is standing the shift that's actually RUNNING, or None.

    NOT :func:`on_duty_keeper` — see the note there. That one answers
    "whose shift is it" regardless of location; this one also requires
    presence.

    Two conditions, and both matter: somebody must be here, and it must
    be their shift. Presence alone used to be enough, which meant a
    proprietor who had finished her day and not yet gone home was still
    selling at midnight — she was standing there, so the counter
    answered yes.

    Note this is deliberately NOT the same question `_slot_held` asks.
    That one means "does this person still hold this job", which the
    succession sweep needs to be true around the clock, or every
    off-shift slot would read vacant and get refilled by morning.

    The object form exists because two callers need the person, not the
    fact: the `order` command has to address them, and the souls planner
    has to decide whether an order is worth the walk. Both read the
    clock through here, so neither can drift from the till's answer.
    """
    room = _post_room(fixture)
    now_shift = current_shift()
    slots = fixture.db.post_slots or {}
    for shift, slot in slots.items():
        keeper = slot.get("keeper")
        if shift != now_shift:
            continue
        if keeper is not None and keeper.pk and keeper.location == room:
            return keeper
    if slots:
        # ...or by whoever is COVERING it (#2434). A keeper does not walk
        # out mid-customer because their watch says so: they stay until
        # relieved, and eventually give up and go home. So before the
        # counter answers "closed", ask whether somebody from another
        # shift is still standing here holding it open.
        #
        # This is what keeps "the counter never closes; the faces
        # change" true across a shift boundary. Without it the ±15 min
        # personal jitter left a venue dark for up to 30 minutes three
        # times a day — the outgoing keeper gone early by their own
        # clock, the incoming not yet due by theirs.
        from world.souls.engine import on_duty, soul_hour
        from world.gametime import colony_now
        t = colony_now()
        hour_f = t.hour + t.minute / 60.0
        for shift, slot in slots.items():
            keeper = slot.get("keeper")
            if shift == now_shift or keeper is None or not keeper.pk:
                continue
            if keeper.location != room:
                continue
            if on_duty(keeper, soul_hour(keeper, hour_f)):
                return keeper
        return None
    legacy = fixture.db.post_keeper
    if legacy is not None and legacy.pk and legacy.location == room:
        return legacy
    return None


def any_keeper_present(fixture) -> bool:
    """Is the running shift being stood? The fact, from `keeper_on_duty`."""
    return keeper_on_duty(fixture) is not None


def _was_assigned(fixture, key) -> bool:
    """Was someone ever written into *key* on *fixture* -- even if they
    have since been deleted?

    Evennia reads a stored reference to a deleted object back as None,
    so `fixture.db.owner is None` cannot tell "never assigned" from
    "assigned, and that person is gone". The stored row can: a dead
    reference is still a packed tuple in `db_value`. Falls back to the
    plain `db` value for anything that is not a real Attribute row
    (test doubles), where there is no dead-reference case to see."""
    from evennia.typeclasses.attributes import Attribute
    try:
        row = fixture.attributes.get(key, return_obj=True)
    except Exception:  # noqa: BLE001 -- no handler: read the db value
        row = None
    value = row.db_value if isinstance(row, Attribute) \
        else getattr(getattr(fixture, "db", None), key, None)
    return value is not None and value != [] and value != ()


def is_bound(fixture) -> bool:
    """Is this counter somebody's job -- or was it ever?

    UNBOUND is the vending tier: no shifts, nobody posted, nobody owns
    it, and whoever is standing there serves. BOUND means the job system
    (or a hand-set owner/staff allowlist) decides, and a bound counter
    with nobody valid present reads CLOSED -- the state a vacant shift
    already produces ("commerce pauses, property remains").

    The one question, asked by the till, the shop, the planner, the job
    lookup and the order path (#3573). Five inline copies had drifted,
    and every one read a DELETED keeper, owner or staff member as "never
    assigned" -- so a counter whose person was gone fell to the vending
    tier and anyone present could work it and empty the register (the
    #2921 regression). A reference that was ever set keeps the counter
    bound, dead or not.

    `owner`/`staff` are the legacy bar allowlist; see #3648 for why
    future player ownership is not grown from them."""
    if getattr(getattr(fixture, "db", None), "post_slots", None):
        return True
    return any(_was_assigned(fixture, key) for key in ("post_keeper", "owner", "staff"))


def _is_dead(obj) -> bool:
    """Death is DERIVED state — `is_dead()` is a method over
    `medical_state`, and every other consumer in the codebase calls it
    as one.

    This module read `obj.db.is_dead` in three places: an attribute row
    that ZERO objects in the database carry, so `not obj.db.is_dead` was
    always True and none of the three guards ever fired. The only
    non-test write to it was a line clearing something never set
    (#2706).

    Fails ALIVE for anything without the method — a fixture, a non-
    character — because reading a mock as a corpse would vacate posts
    that are actually staffed.
    """
    check = getattr(obj, "is_dead", None)
    if not callable(check):
        return False
    try:
        return bool(check())
    except Exception:  # noqa: BLE001 — an unreadable body is not a dead one
        return False


def _slot_held(post, shift, slot) -> bool:
    """Is this slot's keeper alive and still on this post?

    A keeper holds it by assignment — their post and shift must still
    match, so a soul who quits or is reassigned frees the slot.

    **A post keeper is a soul.** That is now an invariant rather than a
    hope. This used to carry a third branch letting an UNSOULED cast
    member hold a slot by presence, because Vesper worked her chaise
    without a needs engine and reading her slot as vacant would have the
    insurance resleeve a second Vesper while the first stood there
    (#2132). She was the only body it was ever for, and she has a soul
    now (#2362) — so an unsouled keeper is a build error, and a slot it
    holds correctly reads vacant and gets filled by somebody who can
    actually do the work.
    """
    keeper = slot.get("keeper")
    if keeper is None or not keeper.pk:
        return False
    # A DEAD keeper does not hold a post. `pk` is not the test: Essential
    # personnel are ARCHIVED to Limbo rather than deleted (#2128), which
    # is deliberate and good — the insurance restores the person instead
    # of rebuilding a copy — but it means a named keeper's corpse keeps a
    # truthy pk, its soul tag (desoul() has no callers) and its
    # `soul_post` (never cleared on death). None of the three changes
    # when they die, so the slot read HELD forever: no vacancy stamp, no
    # post_vacant signal, no succession, no resleeve, and the counter
    # reporting closed with nothing to say why. Every blueprinted keeper
    # is one death away from it (#2706).
    if _is_dead(keeper) or getattr(keeper, "is_archived", False):
        return False
    room = _post_room(post)
    from world.souls import engine
    if keeper.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
        if keeper.db.soul_post is None:
            # A souled keeper with no assignment recorded still holds
            # the slot by standing in it (#2178). Without this, the
            # slot is vacant forever — the Rook sat in his own booth
            # while the sweep read the chair as dark — and the return
            # would mint a fresh copy of a person who is standing there.
            # This is the same argument #2132 made for unsouled cast,
            # applied to the branch it missed.
            return keeper.location == room
        return (keeper.db.soul_post == room
                and (keeper.db.soul_schedule or "day") == shift)
    return False


def slot_is_taken(post, shift, by=None) -> bool:
    """Is this SHIFT's slot already held by somebody other than *by*?

    The question the claim step must ask, and asks through `_slot_held`
    so it is the same reading the succession sweep uses. The claim used
    to check `post_keeper` — the legacy SINGLE mirror, which cannot tell
    one shift from another — and additionally required the holder to be
    standing there. Souls leave their post constantly (a band-1 need
    outranks duty), so a keeper who stepped out to eat was displaced by
    the next candidate offered the same slot, and the pair of them ended
    up believing they held it (#2371).
    """
    slot = (post.db.post_slots or {}).get(shift) or {}
    keeper = slot.get("keeper")
    if keeper is None or not keeper.pk or keeper is by:
        return False
    return _slot_held(post, shift, slot)


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
        if soul.db.soul_post is not None:
            continue
        if engine.is_pinned(soul):
            continue                     # frozen in time: never a candidate (#3507)
        # leisure never blocks a job offer — a soul out socializing or
        # idling takes the call (only survival-band work is sacred);
        # the old any-job exclusion left the unemployed perpetually
        # "busy" at the bar while twenty shifts went begging
        goal = (soul.db.soul_job or {}).get("goal")
        if goal in ("hunger", "safety", "claim", "treat"):
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
                    slot.pop("dead_uid", None)
                    slot.pop("dead_id", None)
                    slot.pop("return_failures", None)
                    dirty = True
                continue
            if slot.get("vacant_since") is None:
                slot["vacant_since"] = now           # newly dark
                try:
                    from world import wsis
                    wsis.emit("post_vacant", _post_room(post),
                              note=f"{post.key} [{shift}]")
                except Exception:  # noqa: BLE001
                    pass
                # Who died here. Stamped now, before the reference can
                # read back as None: the sleeve policy that may bring
                # them back names this body (#3667).
                keeper = slot.get("keeper")
                if keeper is not None and keeper.pk:
                    slot["dead_uid"] = getattr(keeper, "sleeve_uid", None)
                    slot["dead_id"] = keeper.id
                if slot.get("keeper") is not None \
                        and not (slot["keeper"] and slot["keeper"].pk):
                    slot["keeper"] = None
                dirty = True
                continue
            # `is None`, not `or`. A builder asking for NO delay --
            # re-staff the moment the slot goes dark -- wrote 0, which
            # is falsy, so `or DEFAULT_DELAY` silently gave them the
            # LONGEST delay instead, with no error and nothing in the
            # log (#3093). Same shape as #2877's expiry-of-zero.
            #
            # Censused before changing: 19 posts carry a delay
            # (259200 x10, 21600 x5, 86400 x2, 600 x2) and NONE is 0, so
            # this changes no live cadence -- it stops the next builder
            # who types 0 from getting six hours.
            authored = post.db.post_delay
            ripe_after = (DEFAULT_DELAY if authored is None
                          else int(authored))
            if now - float(slot["vacant_since"]) < ripe_after:
                continue
            room = _post_room(post)
            if any(_in_combat(o) for o in room.contents
                   if hasattr(o, "ndb")):
                continue                             # never over a fight
            policy = post.db.post_policy
            # Does THIS shift have a name on it? A blueprint names a
            # person, and a person works one shift. So a shift is owned
            # only if its blueprint's namesake is not already alive and
            # standing somewhere else — otherwise the return branch
            # spins forever on a person who cannot be rebuilt (#2192).
            #
            # This is what left 14 slots permanently dark: a `resleave`
            # post took the first branch for EVERY shift, `_try_resleave`
            # bailed for want of a blueprint, and `continue` meant the
            # successor path below was never reached. Both clinics and
            # dispatch ran day-only because of it.
            bp_key = (post.db.post_blueprints or {}).get(shift)
            owned = bool(bp_key) and _living_body(bp_key) is None
            if owned:
                outcome = _try_resleave(post, room, shift, slot, now)
                if outcome == RESLEEVED:
                    # NOTHING to write back. `_install_keeper` has already
                    # re-read `post_slots`, recorded the new keeper and
                    # persisted it. Writing `slots` — this loop's snapshot,
                    # taken BEFORE the resleave — put the vacancy straight
                    # back, so a keeper who had just been installed and
                    # emoted "back at the post" left the slot reading
                    # empty (#2802).
                    return                           # one per sweep
                if outcome == HOLD:
                    continue        # transient: the next sweep asks again
                # SUCCESSOR: the dead keeper is not coming back (no
                # sleeve policy in their name, #3667). The shift is
                # nobody's now, so it is offered below like any other.
                # Before this it hit `continue`, and a shift whose
                # return could never succeed stayed dark forever
                # (#3565).
                _disown_shift(post, shift)
            # Nobody's name on this shift — a stranger may claim it.
            # A post with no policy at all stays dark: that is the
            # owner's undecided case, not an invitation to hire.
            if policy != "successor":
                continue
            candidates = _eligible_candidates(room)
            if not candidates:
                continue                             # the slot stays dark
            # Offer DOWN THE LIST, and only spend the sweep on a real
            # hire. `_offer` refuses a post the soul cannot walk to
            # (#2332) -- a good rule that this caller did not know
            # about, because it offered to the nearest candidate only
            # and then returned whether or not anybody took it.
            #
            # Both orderings are deterministic (`_eligible_candidates`
            # sorts on `(distance, id)`, `get_posts()` is a tag search),
            # so the next sweep made the same offer to the same sealed-in
            # soul and burned itself again -- forever, and taking every
            # later dark post down with it. Measured at the time: 3 of
            # 19 posts had a nearest candidate who could not reach them,
            # one of them the Rook, who is exactly the soul #2332 was
            # written about and who cannot leave his basement.
            if not any(_offer(soul, post, room, shift)
                       for soul in candidates):
                continue                # nobody could take it; try the next
            if dirty:
                post.db.post_slots = slots
            return                                   # one per sweep
        if dirty:
            post.db.post_slots = slots


def _disown_shift(post, shift):
    """The shift's name comes off: nobody's blueprint owns it now."""
    bps = dict(post.db.post_blueprints or {})
    if bps.pop(shift, None) is not None or not bps:
        post.db.post_blueprints = bps


def _archived_body(bp_key):
    """The most recently archived Essential body for this blueprint,
    waiting in Limbo, or None. Identity is NOT settled here: a blueprint
    names a role's namesake, and the sleeve policy that brings a person
    back names the exact body that bought it (#3667), so the record is
    the identity check, made by `_try_resleave`."""
    from evennia.objects.models import ObjectDB

    candidates = [
        obj for obj in ObjectDB.objects.filter(db_location__isnull=False)
        if obj.db.essential and obj.db.blueprint_key == bp_key
        and obj.db.is_npc and obj.location
        and obj.location.id == 2                     # Evennia's Limbo
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda o: o.id)


def _living_body(bp_key):
    """A living NPC already built from this blueprint, anywhere.

    A blueprint names a PERSON — `doctor_marta` is Marta Okoye — so
    there must never be two of them walking around. Petra's post had
    the same blueprint on all three shifts, and the insurance duly
    built her a body per shift (#2178).
    """
    from evennia.objects.models import ObjectDB

    for obj in ObjectDB.objects.filter(
            db_attributes__db_key="blueprint_key"):
        if (obj.pk and obj.db.blueprint_key == bp_key
                and obj.db.is_npc and not _is_dead(obj)
                and obj.location is not None
                and obj.location.id != 2):        # not archived in Limbo
            return obj
    return None


def _dying(body) -> bool:
    """Dead, but still revivable on the table: the death progression is
    running, or death completed and the body is not yet archived (a
    wedged or stalled progression). Its policy must not be spent, and
    the shift must not be given away (#3667)."""
    try:
        if body.scripts.get("death_progression"):
            return True
        return bool(body.db.death_processed) and not body.is_archived
    except AttributeError:
        return False


def _slot_body(slot):
    """The body this slot's death is about: the keeper reference while
    it still resolves, else the id stamped when the slot went dark.
    None when the body is gone (deleted) or was never stamped."""
    from evennia.utils.search import search_object

    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk:
        return keeper
    if slot.get("dead_id"):
        hit = search_object(f"#{slot['dead_id']}")
        return hit[0] if hit and hit[0].pk else None
    return None


def _dead_keeper(post, shift, slot, bp_key):
    """The ARCHIVED body of the person who died on this shift, or None.

    The slot's own body first (an archived Essential body keeps its pk,
    and the stamp names it once the reference is gone). Only a slot that
    went dark before the stamp existed falls back to the newest archived
    body built as this blueprint. Whichever is found must be this
    blueprint's namesake, archived; the sleeve policy then has to name
    that exact body.
    """
    found = _slot_body(slot)
    if found is None and not slot.get("dead_id"):
        found = _archived_body(bp_key)          # pre-stamp vacancy only
    if found is None or not found.pk:
        return None
    if found.db.blueprint_key != bp_key or not found.is_archived:
        return None
    return found


#: A return that keeps failing is not transient. After this many failed
#: attempts on one vacancy the shift falls to a successor and the record
#: stays unspent (the spec's rule for a permanent failure).
RETURN_ATTEMPTS = 3


def _return_failed(slot, post, shift, record, restore_policy):
    """Book a failed attempt: the record goes back; HOLD until the
    attempts run out, then SUCCESSOR."""
    restore_policy(record)
    slots = dict(post.db.post_slots or {})
    live = dict(slots.get(shift) or slot)
    live["return_failures"] = int(live.get("return_failures") or 0) + 1
    slots[shift] = live
    post.db.post_slots = slots
    return HOLD if live["return_failures"] < RETURN_ATTEMPTS else SUCCESSOR


def _try_resleave(post, room, shift, slot, now) -> str:
    """Bring this SLOT's dead keeper back, if their sleeve policy pays.

    The policy is personal (`world/insurance`, #3667): bought alive at
    the Thawn-Harrison terminal, keyed to the body that bought it, spent
    by the return. So the payout is keyed to the PERSON who died, never
    to the post: the archived body is revived (every memory, dossier,
    thought and habit they had, from their own imprint), or, for a
    keeper who was never archived, a body is rebuilt from the blueprint
    and the shift's snapshot restored, but only when that snapshot is
    this namesake's own.

    Answers RESLEEVED (the person is back), HOLD (transient: a keeper
    who is alive, still dying, or whose return failed and may be
    retried), or SUCCESSOR (nobody is coming back: no policy, a blueprint
    that cannot build, or RETURN_ATTEMPTS failures). The take happens
    BEFORE the body is built, and is put back on any failure; a failed
    revive puts the body back exactly as it was, dead and archived.
    """
    bp_key = (post.db.post_blueprints or {}).get(shift)
    if not bp_key:
        return SUCCESSOR

    # A return happens on a DEATH. If this slot's keeper is still
    # walking around, whatever made the slot read vacant is a bug in
    # the reading, and building a second body would make it permanent
    # — the original is alive, so it is never archived, so the next
    # sweep cannot restore it either and mints another copy (#2178).
    body = _slot_body(slot)
    if body is not None and not _is_dead(body) and not body.is_archived:
        return HOLD
    # Dead but not yet archived: still on the table, or a wedged death
    # the boot sweep will finish. Never rely on the 90 s timing.
    if body is not None and not body.is_archived and _dying(body):
        return HOLD

    # And never a second body of somebody who already exists. The slot
    # may name nobody at all — Petra's post carried her blueprint on
    # all three shifts, so day held her while swing and night each
    # built their own Petra. The slot stays dark instead, which is
    # visible (post_vacant) rather than silent.
    if _living_body(bp_key) is not None:
        return HOLD

    from world import imprint as imprint_mod
    from world.insurance import restore_policy, take_policy

    # you do not reappear behind your own counter: a new sleeve is
    # decanted at Thawn-Harrison like anyone else's, and the walk back
    # to work is the planner's problem (owner ruling 2026-08-20)
    decant = _decant_room() or room

    # ARCHIVED FIRST (#2128): Essential Personnel wait in Limbo rather
    # than being deleted, so the return restores the PERSON — every
    # memory, dossier, thought and habit they had — instead of building
    # a copy from their blueprint and pasting a snapshot onto it.
    npc = _dead_keeper(post, shift, slot, bp_key)
    if npc is not None:
        if _dying(npc):
            return HOLD
        record = take_policy(npc.sleeve_uid, npc.id)
        if record is None:
            return SUCCESSOR
        snap = npc.db.imprint                 # their own, taken at death
        was_at = npc.location
        try:
            npc.save_medical_state()          # the dead body, as it lies
        except AttributeError:
            pass
        old_medical = npc.db.medical_state    # ...serialised, for the undo
        try:
            npc.move_to(decant, quiet=True, move_hooks=False)
            # REVIVE, don't clear a phantom. Flesh back to factory,
            # chrome carried across — which is what a fresh sleeve IS
            # (#2706, #526).
            from world.medical.procedures import reset_body_preserving_augments
            reset_body_preserving_augments(npc)
            # ...and out of the DEATH STATE, not just the medical one
            # (#2450): `db.death_processed` (persistent; `at_death`
            # returns early on it forever), the DeathCmdSet as the
            # DEFAULT cmdset (help/who/quit only), and the
            # `override_place` of a corpse. `remove_death_state` is the
            # one door that undoes all three.
            npc.remove_death_state()
            # The archive flag and its tag are a separate store from the
            # death state; this body was found BY being archived.
            npc.unarchive_character()
            npc.db.is_npc = True
            try:
                imprint_mod.restore(npc, snap, now)
            except Exception:  # noqa: BLE001 — a torn memory is not a failed return
                logger.log_trace(f"resleeve: imprint restore failed for {npc.key}")
            _install_keeper(npc, post, room, shift)
            revived = (not _is_dead(npc) and not npc.is_archived
                       and npc.location == decant
                       and (post.db.post_slots or {}).get(shift, {})
                       .get("keeper") == npc)
        except Exception:  # noqa: BLE001 — a failed return must not eat the policy
            logger.log_trace(f"resleeve: return of {npc.key} failed")
            revived = False
        if not revived:
            # Back EXACTLY as it was: dead, and archived. Never delete
            # (the body is the person's only copy) and never
            # `archive_character` (that bumps death_count). The medical
            # reset and `remove_death_state` are undone by hand, or the
            # body would sit alive in Limbo reading as a held slot.
            try:
                npc.move_to(was_at or _limbo() or npc.location, quiet=True,
                            move_hooks=False)
                if old_medical is not None:
                    npc.db.medical_state = old_medical
                    if hasattr(npc, "_medical_state"):
                        delattr(npc, "_medical_state")
                npc.db.death_processed = True
                npc.db.archived = True
                npc.tags.add("archived", category="sleeve")
            except Exception:  # noqa: BLE001
                logger.log_trace(f"resleeve: undo for {npc.key} failed")
            return _return_failed(slot, post, shift, record, restore_policy)
    else:
        # Rebuild from the blueprint: only for THIS namesake's own
        # snapshot. The shift's snapshot belongs to whoever last died on
        # the shift, a hired successor included, so it must name this
        # blueprint and, where the slot was stamped, the body that was
        # stamped (#3667).
        snap = (post.db.post_memory_snapshots or {}).get(shift)
        if (not snap or snap.get("blueprint_key") != bp_key
                or not snap.get("dbref") or not snap.get("sleeve_uid")):
            return SUCCESSOR
        if slot.get("dead_id") and snap.get("dbref") != slot.get("dead_id"):
            return SUCCESSOR
        record = take_policy(snap.get("sleeve_uid"), snap.get("dbref"))
        if record is None:
            return SUCCESSOR
        from world.npcs.blueprints import build_npc
        try:
            npc = build_npc(bp_key, decant)
        except Exception:  # noqa: BLE001 — a broken blueprint must not loop-spawn
            restore_policy(record)
            return SUCCESSOR               # a build that raises never will
        try:
            npc.db.is_npc = True
            # the imprint returns, as of the last backup — same code path
            # a player's flash clone uses, so the two can never drift
            try:
                imprint_mod.restore(npc, snap, now)
            except Exception:  # noqa: BLE001 — a torn memory is not a failed return
                logger.log_trace(f"resleeve: imprint restore failed for {npc.key}")
            _install_keeper(npc, post, room, shift)
            built = (not _is_dead(npc) and npc.location == decant
                     and (post.db.post_slots or {}).get(shift, {})
                     .get("keeper") == npc)
        except Exception:  # noqa: BLE001
            logger.log_trace(f"resleeve: install of rebuilt {bp_key} failed")
            built = False
        if not built:
            try:
                npc.delete()                # a fresh body, nobody's only copy
            except Exception:  # noqa: BLE001
                pass
            return _return_failed(slot, post, shift, record, restore_policy)

    from world.souls import audit, thoughts as thoughts_mod
    try:
        audit.life(npc, "resleeved", bp_key)
    except Exception:  # noqa: BLE001 — a log never blocks a return
        pass
    thoughts_mod.add_thought(
        npc, "resleeved", -0.50,
        "woke in a new sleeve; the last hours before the dark are "
        "simply gone")
    npc.execute_cmd("emote is back at the post, moving like the week "
                    "never happened.")
    return RESLEEVED


def _limbo():
    from evennia.utils.search import search_object
    hit = search_object("#2")
    return hit[0] if hit else None


def _install_keeper(npc, post, room, shift):
    """Bind a keeper into a slot: housing, soul, slot record, legacy
    mirror, venue wages only where a till actually exists."""
    # REFUSE a non-post. This function writes a complete, valid-looking
    # slot record onto whatever it is handed, and build 117 handed it
    # the dispatch CONSOLE -- so the room kept the real slots while the
    # console grew a rival set with different keepers, and the build
    # printed success (#2259).
    #
    # Two objects claiming to be the same post is not a state anything
    # downstream can reason about, so it is refused at the seam rather
    # than papered over at every reader.
    if not post.tags.get(POST_TAG[0], category=POST_TAG[1]):
        raise ValueError(
            f"{post} is not a registered post -- call register_post() "
            f"first, or pass the object that actually carries the tag"
        )
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


def _imprint_of(character, now):
    """The imprint record — see `world/imprint.py`, which players resleeve
    through too. Kept as a thin alias so this module's callers read the
    same as they did before the extraction."""
    from world import imprint

    return imprint.capture(character, now)


def snapshot_imprint(character) -> bool:
    """At death, a slot-keeper's memories become the post's property
    (reincarnation spec §2), keyed by their shift (the record names the
    keeper's blueprint and body, so a rebuild restores only its own): episodic memories,
    dossiers, thoughts, and the people they knew by face and by voice,
    copied onto the fixture BEFORE the corpse machinery deletes the
    body — kept whether or not anyone ever pays to restore them."""
    import time as _time

    for post in get_posts():
        for shift, slot in (post.db.post_slots or {}).items():
            if slot.get("keeper") != character:
                continue
            snaps = dict(post.db.post_memory_snapshots or {})
            snaps[shift] = _imprint_of(character, _time.time())
            post.db.post_memory_snapshots = snaps
            return True
        if post.db.post_keeper == character:     # legacy fallback
            post.db.post_memory_snapshot = _imprint_of(
                character, _time.time())
            return True
    return False


def _can_reach(soul, room) -> bool:
    """Can this soul actually walk there, as itself?"""
    here = getattr(soul, "location", None)
    if here is None or room is None:
        return False
    if here is room:
        return True
    try:
        from world.spatial.pathfind import find_path
        return bool(find_path(here, room, traverser=soul))
    except Exception:  # noqa: BLE001 — an unroutable question is a no
        return False


def _offer(soul, post, room, shift):
    """Hand the claim job: walk there for real, then take the shift.
    Goal is "claim", NOT "duty" — the shift-release logic clears duty
    jobs outside work hours, which ate every after-hours job offer
    (you take the job tonight; you start when your shift comes).

    Refuses a job the soul cannot REACH. The Rook was offered the
    Helix Lounge from inside his sealed basement studio -- a recluse
    with no exits, by design -- and re-took the offer every three
    minutes forever, because nothing asked whether he could walk there
    (#2331). `_advertisers` learned this already; the job market had
    not.

    Returns True if the soul took the job. The caller spends its one
    hire per sweep on this call, so it has to be able to tell a hire
    from a refusal -- when it could not, a single unroutable neighbour
    ended the sweep and starved every other dark post in the colony.
    """
    if not _can_reach(soul, room):
        return False
    soul.db.soul_job = {
        "goal": "claim", "band": 2, "at": 0,
        "steps": [
            {"do": "travel", "room": room.id},
            {"do": "claim", "post": post.id, "shift": shift},
        ],
    }
    return True


def do_claim(soul, post, shift="day"):
    """The claim step's business: bind soul to the slot (jobs.py calls)."""
    from world.souls import thoughts

    room = _post_room(post)
    soul.db.soul_post = room
    soul.db.soul_role = post.db.post_role or "worker"
    soul.db.soul_schedule = shift
    rate = post.db.post_wage_rate
    soul.db.soul_wage_rate = 0.02 if rate is None else float(rate)
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