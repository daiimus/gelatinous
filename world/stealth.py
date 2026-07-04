"""Stealth & detection — the contest engine and graded awareness store.

STEALTH_AND_DETECTION_SPEC Phases 1–2 (+ the passive tier): ``hide`` /
``sneak`` / ``search`` resolved as an opposed **Motorics (hider) vs
Resonance (searcher)** contest, recorded as **per-observer graded
awareness** (Unaware → Suspicious → Searching → Alert/Detected).

Three contest tiers, weakest to strongest:

* **passive** — free, runs when an observer enters a room or looks around;
  penalized and rate-limited (look-spam is not a search). A perceptive
  observer still inherently spots a terrible hider.
* **hide-time** — everyone watching when you try to vanish gets an unmodified
  contest; those who win keep track of you (you read as *lurking*, §4).
* **active search** — an action, with a bonus; the deliberate counter.

Awareness keys on the target's **apparent uid** (identity spec): you can be
made as a *presence* without being *identified* — a mask still protects the
name. Environmental modifiers (light, cover/LoS, crowd) land with the
coordinate integration; v1 is the flat tier spread below.
"""

import time
from random import randint

# Awareness levels (spec §4).
UNAWARE, SUSPICIOUS, SEARCHING, ALERT = 0, 1, 2, 3

ACTIVE_SEARCH_BONUS = 4      # deliberate searching beats a glance
SNEAK_PENALTY = 3            # hiding on the move is harder than from cover
PASSIVE_SUSPICION_MARGIN = 3  # passive near-miss => "you sense something"
PASSIVE_COOLDOWN = 60.0      # seconds between free passive rolls per target
AWARENESS_DECAY = 300.0      # seconds per level of decay once contact is lost


def _stat(char, name):
    try:
        return int(getattr(char, name, 1) or 1)
    except Exception:  # noqa: BLE001
        return 1


def _target_key(target):
    """Awareness keys on apparent identity — presence ≠ name."""
    try:
        from world.identity import get_apparent_uid
        return get_apparent_uid(target) or f"#{target.id}"
    except Exception:  # noqa: BLE001
        return f"#{getattr(target, 'id', id(target))}"


def _records(observer) -> dict:
    from evennia.utils.dbserialize import deserialize
    db = getattr(observer, "db", None)
    data = deserialize(getattr(db, "awareness", None))
    return data if isinstance(data, dict) else {}


def get_awareness(observer, target) -> int:
    """The observer's current awareness of ``target``, with lazy time decay
    (one level per AWARENESS_DECAY seconds since last contact)."""
    rec = _records(observer).get(_target_key(target))
    if not rec:
        return UNAWARE
    level = int(rec.get("level", UNAWARE))
    elapsed = max(0.0, time.time() - float(rec.get("t", 0)))
    return max(UNAWARE, level - int(elapsed // AWARENESS_DECAY))


def set_awareness(observer, target, level, *, roll_stamp=False):
    """Record awareness (only non-default records are stored — spec §12
    bounding). ``roll_stamp`` also marks a passive-roll timestamp. A
    SUSPICIOUS+ record stamps the target's LAST-KNOWN ROOM — the hunt's
    destination (spec §5)."""
    records = _records(observer)
    key = _target_key(target)
    rec = dict(records.get(key) or {})
    now = time.time()
    if level <= UNAWARE and not roll_stamp:
        records.pop(key, None)
    else:
        rec["level"] = int(level)
        rec["t"] = now
        if roll_stamp:
            rec["t_roll"] = now
        if level >= SUSPICIOUS:
            room = getattr(target, "location", None)
            room_id = getattr(room, "id", None)
            if room_id is not None:
                rec["last_room"] = room_id
        records[key] = rec
    observer.db.awareness = records


def seed_awareness(observer, target_key, level, last_room_id=None):
    """Write an awareness record BY KEY — alert propagation between NPCs
    (spec §5) hands a colleague the target's key and last-known room
    without ever holding the target object."""
    records = _records(observer)
    if level <= UNAWARE:
        records.pop(target_key, None)
    else:
        rec = dict(records.get(target_key) or {})
        rec["level"] = max(int(level), int(rec.get("level", UNAWARE)))
        rec["t"] = time.time()
        if last_room_id is not None:
            rec["last_room"] = last_room_id
        records[target_key] = rec
    observer.db.awareness = records


def hunt_records(observer) -> list:
    """The observer's decayed awareness records for the hunt:
    ``[(target_key, level, last_room_id, t)]``, strongest first."""
    now = time.time()
    out = []
    for key, rec in _records(observer).items():
        level = int(rec.get("level", UNAWARE))
        elapsed = max(0.0, now - float(rec.get("t", 0)))
        level = max(UNAWARE, level - int(elapsed // AWARENESS_DECAY))
        if level > UNAWARE:
            out.append((key, level, rec.get("last_room"),
                        float(rec.get("t", 0))))
    out.sort(key=lambda r: (-r[1], -r[3]))
    return out


def _passive_ready(observer, target) -> bool:
    rec = _records(observer).get(_target_key(target)) or {}
    return time.time() - float(rec.get("t_roll", 0)) >= PASSIVE_COOLDOWN


def crowd_hider_bonus(room) -> int:
    """Blending in: crowd density is concealment (spec §3.2). A hotspot
    throng is worth up to +3 to the hider; an empty street gives nothing.
    First environmental modifier to land — light/cover ride the
    coordinate integration later."""
    try:
        from world.crowd import crowd_system
        level = int(crowd_system.calculate_crowd_level(room) or 0)
        return max(0, min(level, 3))
    except Exception:  # noqa: BLE001 — no crowd system, no bonus
        return 0


def contest(hider, observer, *, hider_bonus=0, observer_bonus=0) -> int:
    """One opposed roll. Positive margin = the OBSERVER wins (spots them);
    zero or negative = the hider holds. Hider leans Motorics, observer
    Resonance (spec §3.1 working direction). The hider's room's crowd
    density always helps them — blending in is real at every tier."""
    hider_bonus += crowd_hider_bonus(getattr(hider, "location", None))
    hide_total = randint(1, 20) + _stat(hider, "motorics") + hider_bonus
    seek_total = randint(1, 20) + _stat(observer, "resonance") + observer_bonus
    return seek_total - hide_total


def _watchers(room, hider):
    """Who could contest a hide attempt: present characters with working
    sight (the visual layer; blind observers don't watch you vanish)."""
    from world.perception import can_see
    out = []
    for obj in (room.contents if room else []):
        if obj is hider or not hasattr(obj, "get_sdesc"):
            continue
        try:
            if can_see(obj):
                out.append(obj)
        except Exception:  # noqa: BLE001
            out.append(obj)
    return out


def attempt_hide(hider, *, sneak=False) -> list:
    """Try to slip out of sight. Everyone watching gets an unmodified
    contest: winners keep track (Detected — you read as lurking to them),
    losers lose you (Unaware). Returns the observers who kept track."""
    room = hider.location
    hider.db.hidden = True
    bonus = -SNEAK_PENALTY if sneak else 0
    kept = []
    for observer in _watchers(room, hider):
        if contest(hider, observer, hider_bonus=bonus) > 0:
            set_awareness(observer, hider, ALERT, roll_stamp=True)
            kept.append(observer)
        else:
            set_awareness(observer, hider, UNAWARE, roll_stamp=True)
    return kept


def passive_check(observer, hider) -> int:
    """The free glance — entering a room or looking around. Penalized (the
    active-search bonus is withheld) and rate-limited per target so
    look-spam never equals searching; repeat looks reuse the standing
    result until the cooldown passes or the hider re-rolls.

    Returns the observer's (possibly updated) awareness level. A clear win
    spots them outright; a near miss leaves that prickling feeling."""
    current = get_awareness(observer, hider)
    if current >= ALERT:
        return current
    if not _passive_ready(observer, hider):
        return current
    margin = contest(hider, observer)
    if margin > 0:
        set_awareness(observer, hider, ALERT, roll_stamp=True)
        return ALERT
    if margin > -PASSIVE_SUSPICION_MARGIN and current < SUSPICIOUS:
        set_awareness(observer, hider, SUSPICIOUS, roll_stamp=True)
        return SUSPICIOUS
    set_awareness(observer, hider, current, roll_stamp=True)
    return current


def active_search(searcher, room=None) -> tuple:
    """The deliberate counter: one action, rolls (with the search bonus)
    against every hidden character and stashed object here. Returns
    (found_characters, found_objects)."""
    room = room or searcher.location
    found_chars, found_objs = [], []
    for obj in (room.contents if room else []):
        if obj is searcher:
            continue
        if getattr(obj.db, "hidden", False) is not True:
            continue
        if hasattr(obj, "get_sdesc"):
            if contest(obj, searcher, observer_bonus=ACTIVE_SEARCH_BONUS) > 0:
                set_awareness(searcher, obj, ALERT, roll_stamp=True)
                found_chars.append(obj)
        else:
            stash_roll = int(getattr(obj.db, "stash_roll", 10) or 10)
            if randint(1, 20) + _stat(searcher, "resonance") \
                    + ACTIVE_SEARCH_BONUS > stash_roll:
                obj.db.hidden = False   # objects reveal for everyone
                found_objs.append(obj)
    return found_chars, found_objs


def break_stealth(char, *, quiet=False):
    """Acting loudly (speaking, attacking, walking off openly) drops the
    hidden state and makes everyone present fully aware (spec §6.4 —
    per-room here; alert propagation is the hunt phase's job). Strict
    ``is True``: the state is only ever written as a literal, and test
    doubles with auto-attributes must not read as hidden.

    Non-quiet breaks add the EMERGENCE beat: observers who couldn't see
    the character get "…emerges from concealment." *before* whatever gave
    them away renders, so a voice never just materializes mid-sentence.
    Trackers (who've been watching them lurk) get no redundant line.
    Quiet is for callers that narrate the moment themselves (unhide) or
    where emergence reads wrong (collapsing unconscious, movement)."""
    if getattr(getattr(char, "db", None), "hidden", False) is not True:
        return False
    room = char.location
    emergence = []
    if not quiet:
        emergence = [obs for obs in (room.contents if room else [])
                     if obs is not char and hasattr(obs, "get_sdesc")
                     and is_hidden_from(char, obs)]
    char.db.hidden = False
    for observer in (room.contents if room else []):
        if observer is char or not hasattr(observer, "get_sdesc"):
            continue
        set_awareness(observer, char, ALERT)
    if not quiet:
        char.msg("You abandon any pretense of hiding.")
        from world.grammar import capitalize_first
        for observer in emergence:
            try:
                observer.msg(
                    f"{capitalize_first(char.get_display_name(observer))} "
                    f"emerges from concealment."
                )
            except Exception:  # noqa: BLE001 — narration is best-effort
                pass
    return True


def is_hidden_from(target, looker) -> bool:
    """The display gate: hidden AND the looker is not yet aware enough to
    place them. Suspicious knows *a* presence, not who/where — still
    filtered from the room roster (the cue renders instead)."""
    if getattr(getattr(target, "db", None), "hidden", False) is not True:
        return False
    return get_awareness(looker, target) < ALERT
