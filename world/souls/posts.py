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
keeper from their blueprint (imprint restored minus the death gap, a
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
    if _is_dead(keeper):
        return False
    room = _post_room(post)
    from world.souls import engine
    if keeper.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
        if keeper.db.soul_post is None:
            # A souled keeper with no assignment recorded still holds
            # the slot by standing in it (#2178). Without this, the
            # slot is vacant forever — the Rook sat in his own booth
            # while the sweep read the chair as dark — and `resleave`
            # mints a fresh copy every time the till can afford one.
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
            # standing somewhere else — otherwise the resleave branch
            # spins forever on a person who cannot be rebuilt (#2192).
            #
            # This is what left 14 slots permanently dark: a `resleave`
            # post took the first branch for EVERY shift, `_try_resleave`
            # bailed for want of a blueprint, and `continue` meant the
            # successor path below was never reached. Both clinics and
            # dispatch ran day-only because of it.
            bp_key = (post.db.post_blueprints or {}).get(shift) \
                or post.db.post_blueprint
            owned = bool(bp_key) and _living_body(bp_key) is None
            if owned:
                if _try_resleave(post, room, shift, slot, now):
                    # NOTHING to write back. `_install_keeper` has already
                    # re-read `post_slots`, recorded the new keeper and
                    # persisted it. Writing `slots` — this loop's snapshot,
                    # taken BEFORE the resleave — put the vacancy straight
                    # back, so a keeper who had just been installed and
                    # emoted "back at the post" left the slot reading
                    # empty (#2802).
                    return                           # one per sweep
                continue        # can't afford yet: the till keeps earning
            # Nobody's name on this shift — a stranger may claim it,
            # whatever the post's policy is for the shifts it DOES own.
            # A post with no policy at all stays dark: that is the
            # owner's undecided case, not an invitation to hire.
            if policy not in ("successor", "resleave"):
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


def _archived_keeper(bp_key):
    """The most recently archived Essential body for this blueprint,
    waiting in Limbo. Returns None when nobody is filed — a first
    death under the old rules, or a character who predates archiving."""
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


def _try_resleave(post, room, shift, slot, now) -> bool:
    """The insurance pays out (spec §P3): rebuild this SLOT's named
    keeper from their blueprint, restore the imprint MINUS the death gap
    (the last ~90 minutes never made the backup — murder stays a
    mystery), and debit the insurer's till a REAL premium paid to
    Maxwell. A till that can't afford it keeps earning — a cart can
    sell noodles toward its own keeper's resurrection."""
    from evennia.utils.search import search_object

    bp_key = (post.db.post_blueprints or {}).get(shift) \
        or post.db.post_blueprint
    if not bp_key:
        return False

    # Insurance pays out on a DEATH. If this slot's keeper is still
    # walking around, whatever made the slot read vacant is a bug in
    # the reading, and building a second body would make it permanent
    # — the original is alive, so it is never archived, so the next
    # sweep cannot restore it either and mints another copy (#2178).
    keeper = slot.get("keeper")
    if keeper is not None and keeper.pk and not _is_dead(keeper):
        return False

    # And never a second body of somebody who already exists. The slot
    # may name nobody at all — Petra's post carried her blueprint on
    # all three shifts, so day held her while swing and night each
    # built their own Petra. The slot stays dark instead, which is
    # visible (post_vacant) rather than silent.
    existing = _living_body(bp_key)
    if existing is not None:
        return False
    till = post if post.db.register is not None else post.db.post_insurer
    if till is None or int(till.db.register or 0) < RESLEAVE_PREMIUM:
        return False
    # you do not reappear behind your own counter: a new sleeve is
    # decanted at Thawn-Harrison like anyone else's, and the walk back
    # to work is the planner's problem (owner ruling 2026-08-20)
    decant = _decant_room() or room

    # ARCHIVED FIRST (#2128): Essential Personnel wait in Limbo rather
    # than being deleted, so the insurance restores the PERSON — every
    # memory, dossier, thought and habit they had — instead of building
    # a copy from their blueprint and pasting a snapshot onto it.
    # Blueprint rebuild remains the fallback for anyone who predates
    # the archive or whose record is gone.
    npc = _archived_keeper(bp_key)
    if npc is not None:
        npc.move_to(decant, quiet=True, move_hooks=False)
        # REVIVE, don't clear a phantom. This used to set
        # `db.is_dead = None` — an attribute row no object in the
        # database has ever carried, so it cleared nothing and the body
        # arrived at its post still medically dead. With the aliveness
        # test above, that would turn a permanently-held slot into a
        # permanently-churning one: revived, read dead, vacated,
        # resleeved, forever. Flesh back to factory, chrome carried
        # across — which is what a fresh sleeve IS (#2706, #526).
        from world.medical.procedures import reset_body_preserving_augments
        reset_body_preserving_augments(npc)

        # ...and out of the DEATH STATE, not just the medical one
        # (#2450). `reset_body_preserving_augments` heals the flesh;
        # it does not touch the three things `at_death` installed:
        #
        #   * `db.death_processed` — PERSISTENT, and `at_death` returns
        #     early on it forever, so the restored keeper could be shot
        #     to pieces and nothing would happen: no curtain, no corpse,
        #     no second archive. They could never die again.
        #   * DeathCmdSet as the DEFAULT cmdset (`add_default`, so it
        #     survives a reload) — help/who/quit only, `no_exits=True`.
        #     Souls act exclusively through `execute_cmd`, so the very
        #     first thing this function does after installing them —
        #     `emote is back at the post` — would be refused, and every
        #     goal after it.
        #   * `override_place = "lying motionless and deceased."`, which
        #     would render under a keeper standing at their own counter.
        #
        # `remove_death_state` is the one door that undoes all three,
        # and its only other callers are medical revival and a staff
        # `@heal` — a human with staff perms, which is not something an
        # automated resleeve can walk through.
        try:
            npc.remove_death_state()
        except Exception:  # noqa: BLE001 — a stuck cmdset must not eat the resleeve
            pass
        # The archive flag and its tag are a separate store from the
        # death state; `_archived_keeper` found this body BY being in
        # Limbo, so it is archived by construction.
        try:
            npc.unarchive_character()
        except Exception:  # noqa: BLE001
            pass
    else:
        from world.npcs.blueprints import build_npc
        try:
            npc = build_npc(bp_key, decant)
        except Exception:  # noqa: BLE001 — a broken blueprint must not loop-spawn
            return False
    npc.db.is_npc = True
    # the premium moves for real: insurer till -> Maxwell's terminal
    #
    # RE-READ the till here. Affordability is checked far above, before
    # the decant, and `build_npc` / `spawn` / `move_to` all run in
    # between — so the balance that was checked is not necessarily the
    # balance being debited. Re-checking at the point of the write costs
    # one attribute read and closes the window (#2703).
    #
    # And the credit only happens if the debit did. They were separate
    # statements, so a debit that could not be afforded would still have
    # credited Maxwell — creating tokens in a system whose header
    # describes a closed loop where money circulates rather than
    # appearing.
    balance = int(till.db.register or 0)
    if balance >= RESLEAVE_PREMIUM:
        till.db.register = balance - RESLEAVE_PREMIUM
        try:
            from world.souls import audit
            audit.coin(None, RESLEAVE_PREMIUM, "resleeve_premium",
                       other=till)
        except Exception:  # noqa: BLE001 — a log never blocks a resleeve
            pass
        provider = next((o for o in search_object("a Thawn-Harrison billing "
                                                  "terminal") if o.pk), None)
        if provider is not None:
            provider.db.register = int(provider.db.register or 0) \
                + RESLEAVE_PREMIUM

    # the imprint returns, as of the last backup — same code path a
    # player's flash clone uses, so the two can never drift
    from world import imprint as imprint_mod
    snap = (post.db.post_memory_snapshots or {}).get(shift) \
        or post.db.post_memory_snapshot
    imprint_mod.restore(npc, snap, now)

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
    (reincarnation spec §2), keyed by their shift: episodic memories,
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