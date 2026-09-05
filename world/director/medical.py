"""Medical response — the rescue loop (souls spec §14, layers 2–3).

A downed, bleeding body is a RACE: report latency plus the medic's
travel time against the bleed ticks. Reports ride the same witnessed-
radio law as crime (no witness with a working set, no call — the empty
alley is free for mercy exactly as it is for murder); dispatch routes
`medical` events to the medic post's keeper through the same
assignment machinery security uses; on scene, the medic spends the
REAL supplies they carry through the real apply verb. A medic with
empty pockets, a stolen walkie, or a body nobody found are all honest
world-states, not bugs.
"""

import time
from typing import Any

from evennia.utils.utils import delay

from world.director.dispatch import WorldEvent

#: One medical report per room within this window.
REPORT_DEBOUNCE = 120.0
_RECENT: dict = {}

#: The medic's par levels — LOOSE items in inventory (the game has no
#: carried containers, deliberately). proto attr name -> count.
PAR = {"GAUZE_BANDAGES": 3, "TOURNIQUET": 2, "PAINKILLER": 2}

#: What a MECHANIC keeps on the bench. Same idea, different hands: a
#: painkiller is no use to something with no nociception, and the
#: tourniquet is here because clamping a line stops amber hydraulic
#: fluid exactly as well as it stops blood (#2262).
#:
#: Robot-specific consumables are not built yet, so this draws the
#: subset of the existing kit that a machine can actually use. When the
#: species-gated supplies land, this becomes their par list.
# The bench kit. Not the clinic's: a painkiller is no use to something
# with no nociception, and since #2262 the organic articles REFUSE a
# chassis outright, so stocking gauze here would have left the mechanic
# holding supplies that bounce off every patient she has. The
# tourniquet is on both lists because it is the one article that
# genuinely serves both -- clamping a line stops amber hydraulic fluid
# exactly as well as it stops blood.
MECHANIC_PAR = {"SEALANT_PATCH": 2, "TOURNIQUET": 2,
                "CONFORMAL_COATING": 2, "STRUT_BRACE": 1}


def restock_mechanic(npc: Any) -> int:
    """Bring the bench keeper's supplies up to par from anchored stock.

    The clinic has done this for its medic since the medical slice; the
    bench had nothing, so a mechanic stood a full shift with hands and
    no parts (#2262). Only works AT the post, same as the medic.
    """
    return _restock(npc, MECHANIC_PAR)


def _is_character(obj: Any) -> bool:
    return hasattr(obj, "get_sdesc") and hasattr(obj, "medical_state")


def find_casualty(room: Any, exclude: Any = None) -> Any:
    """The most urgent downed character in the room: unconscious/dying,
    bleeding first."""
    from world.consent import is_conscious

    best = None
    for obj in room.contents:
        if obj is exclude or not _is_character(obj) or not obj.pk:
            continue
        try:
            if is_conscious(obj):
                continue
        except Exception:  # noqa: BLE001 — unreadable body: skip
            continue
        # THE DEAD ARE NOT CASUALTIES. A body stays in the room as an
        # ordinary Character for DEATH_PROGRESSION_DURATION (90s) before
        # corpse conversion, and it passes every filter above: it is a
        # character, it has a pk, and it is certainly not conscious.
        #
        # Worse than merely being selectable — the tiebreak below is
        # unconditional, so a BLEEDING candidate always displaces a
        # non-bleeding one. A medic arriving where one victim has just
        # died bleeding and another is unconscious and not visibly
        # bleeding picked the corpse and worked on it while the person
        # who could still be saved lay beside them (#2757).
        if _is_dead(obj):
            continue
        bleeding = _is_bleeding(obj)
        if best is None or (bleeding and not best[0]):
            best = (bleeding, obj)
    return best[1] if best else None


def _is_dead(char: Any) -> bool:
    """Death is derived state — `is_dead()` is a method over
    `medical_state`, never an attribute row. Fails ALIVE for anything
    that cannot answer, because refusing to treat a LIVING
    casualty is the worse error of the two."""
    check = getattr(char, "is_dead", None)
    if not callable(check):
        return False
    try:
        return bool(check())
    except Exception:  # noqa: BLE001 — unreadable body: treat as alive
        return False


def _is_bleeding(char: Any) -> bool:
    conds = (getattr(char.db, "medical_state", None) or {}).get(
        "conditions") or []
    return any("bleed" in str((c.get("type") if isinstance(c, dict) else c)
                              or "").lower() for c in conds)


def report_medical(location: Any, casualty: Any = None) -> bool:
    """Someone is down: roll the crowd witness and put it on the air.
    Same debounce, same witness-with-a-radio law as report_crime."""
    from world.director.witness import (WITNESS_REPORT_DELAY, spawn_witness,
                                        witness_report)

    if location is None:
        return False
    key = (location, "medical")
    now = time.monotonic()
    last = _RECENT.get(key)
    if last is not None and (now - last) < REPORT_DEBOUNCE:
        return False
    _RECENT[key] = now
    witness = spawn_witness(location)
    if witness is None:
        return False                # nobody around: the alley stays silent
    event = WorldEvent(type="medical", location=location, severity=1,
                       source=None, payload={})
    delay(WITNESS_REPORT_DELAY, witness_report, witness, event)
    return True


def _is_unit(obj: Any) -> bool:
    """A security unit: the force's own, as opposed to a colonist."""
    db = getattr(obj, "db", None)
    return (getattr(db, "role", None) == "security"
            and getattr(db, "species", None) == "robot")


def recover_casualty(soul: Any, casualty: Any) -> bool:
    """A unit takes a downed unit home. True if it took the errand.

    Deliberately narrow: only a UNIT recovers, and only a UNIT is
    recovered. A secbot does not sling a bleeding colonist over its
    shoulder -- that is the medic's job, and the radio report the
    caller already makes is the right response to a person.
    """
    if not _is_unit(soul) or not _is_unit(casualty):
        return False
    if casualty is soul or soul.db.soul_recovering:
        return False
    # somebody already has it
    #
    # `is_grappled(combat_handler, character)` takes TWO arguments. This
    # passed one, so every call raised TypeError — and the except below
    # returned False, which is the same thing the success branch
    # returns. The function could therefore never return anything but
    # False: a medic has NEVER started a casualty recovery. Nine days
    # and 54,000 log lines show `goal=recover` elected zero times
    # (#2712).
    #
    # `world/consent.py:64` is the one correct call in the repo and
    # shows the shape: find the handler first.
    #
    # The except is narrowed to the failure it was written for — an
    # unreadable hold — so the next programming error here surfaces
    # instead of becoming a permanent policy. This is the second
    # instance in the audit of a blanket except hiding an arity
    # mismatch (#2668 is the other).
    try:
        from world.combat.grappling import is_grappled
        from world.combat.utils import find_character_handler
        handler = find_character_handler(casualty)
        if handler and is_grappled(handler, casualty):
            return False
    except TypeError:
        raise                        # a call-shape bug is not a policy
    except Exception:  # noqa: BLE001 — unreadable hold: leave it be
        return False
    from world.souls import actions
    soul.db.soul_recovering = casualty.id
    job = actions.plan_for(soul, "recover")
    if job is None:
        soul.db.soul_recovering = None
        return False
    soul.db.soul_job = job
    try:
        from world.director.security import _cmd
        _cmd(soul, f"xmit Unit {getattr(soul, 'id', 0) or 0} — "
                   f"{getattr(soul.location, 'key', 'this location')}. "
                   f"Unit {getattr(casualty, 'id', 0) or 0} down. "
                   f"Recovering.")
    except Exception:  # noqa: BLE001 — flavour never blocks the errand
        pass
    return True


def notice_casualty(soul: Any, room: Any) -> None:
    """A soul thinking in a room with a downed body acts on it: a MEDIC
    treats it on the spot — nobody radios dispatch about the body at
    their own feet — anyone else raises the alarm through the
    witnessed-radio law (debounced; the thought only lands when a
    report actually went up)."""
    casualty = find_casualty(room, exclude=soul)
    if casualty is None:
        return
    if getattr(soul.db, "soul_role", None) == "medic" \
            or getattr(soul.db, "role", None) == "medic":
        treat_casualty(soul, casualty)
        return
    # THE FORCE RECOVERS ITS OWN (owner ruling 2026-08-24). A unit that
    # comes upon a downed unit doesn't radio about it -- it picks it up
    # and walks it home. Same shape as the medic branch above: role
    # decides what finding a body MEANS (#2282).
    if recover_casualty(soul, casualty):
        return
    if report_medical(room, casualty):
        try:
            from world.souls import thoughts
            thoughts.add_thought(soul, "saw_someone_down", -0.15,
                                 f"someone was down and bleeding at "
                                 f"{room.key}")
        except Exception:  # noqa: BLE001 — the report matters more
            pass


def _carried(npc: Any, proto_attr: str) -> list:
    """Loose carried items matching a supply prototype's key."""
    from world import prototypes
    proto = getattr(prototypes, proto_attr, None)
    want = (proto or {}).get("key", "").lower()
    if not want:
        return []
    return [o for o in npc.contents
            if o.pk and o.key.lower() == want and not o.destination]


def _restock(npc: Any, par: dict) -> int:
    """Draw *par* levels of loose supplies from anchored stock, at post."""
    from evennia.prototypes.spawner import spawn

    from world import prototypes
    if npc.location is None or npc.location != npc.db.soul_post:
        return 0
    drawn = 0
    for proto_attr, want in par.items():
        short = want - len(_carried(npc, proto_attr))
        proto = getattr(prototypes, proto_attr, None)
        if not proto or short <= 0:
            continue
        for _ in range(short):
            try:
                item = spawn(proto)[0]
                item.move_to(npc, quiet=True, move_hooks=False)
                drawn += 1
            except Exception:  # noqa: BLE001 — a failed draw skips
                break
    return drawn


def restock_medic(npc: Any) -> int:
    """Bring the medic's loose supplies up to par from the clinic's
    anchored bottomless stock. Only works AT their post (the clinic) —
    the field is finite by design."""
    from evennia.prototypes.spawner import spawn

    from world import prototypes
    if npc.location is None or npc.location != npc.db.soul_post:
        return 0
    drawn = 0
    for proto_attr, par in PAR.items():
        short = par - len(_carried(npc, proto_attr))
        proto = getattr(prototypes, proto_attr, None)
        if not proto or short <= 0:
            continue
        for _ in range(short):
            try:
                item = spawn(proto)[0]
                item.move_to(npc, quiet=True, move_hooks=False)
                drawn += 1
            except Exception:  # noqa: BLE001 — a failed draw skips
                break
    return drawn


def treat_casualty(npc: Any, casualty: Any) -> int:
    """Kneel and work: spend real carried supplies through the real
    apply verb. Tourniquet stops the bleed, gauze dresses the wounds —
    whatever's in the pockets. Returns supplies used. Debounced per
    casualty so one patient isn't gauze-bombed every think."""
    import time as _time

    from world.director.security import _target_token

    last = getattr(npc.ndb, "last_treated", None) or {}
    if _time.time() - last.get(casualty.id, 0) < 300:
        return 0
    last[casualty.id] = _time.time()
    npc.ndb.last_treated = last

    npc.execute_cmd("emote drops to a knee beside the casualty, hands "
                    "already moving.")
    token = _target_token(casualty)
    used = 0
    if _is_bleeding(casualty):
        for item in _carried(npc, "TOURNIQUET")[:1]:
            npc.execute_cmd(f"apply {item.key} on {token}")
            used += 1
    for item in _carried(npc, "GAUZE_BANDAGES")[:2]:
        npc.execute_cmd(f"apply {item.key} on {token}")
        used += 1
    if used == 0:
        npc.execute_cmd("emote comes up empty — pockets bare when it "
                        "mattered.")
    try:
        from world.souls import thoughts
        thoughts.add_thought(npc, "worked_a_scene",
                             0.10 if used else -0.30,
                             f"worked a casualty at {npc.location.key}"
                             + ("" if used else " with empty pockets"))
    except Exception:  # noqa: BLE001
        pass
    return used


def medic_arrival(npc: Any, assignment: Any) -> None:
    """On-scene behavior for ``role == "medic"``: find the casualty and
    treat them; stand down if nobody's there."""
    from world.director.assignment import resolve

    casualty = find_casualty(npc.location, exclude=npc)
    if casualty is None:
        npc.execute_cmd("emote scans the scene, finds nobody down, and "
                        "straightens up slowly.")
    else:
        treat_casualty(npc, casualty)
    resolve(npc)


def register() -> None:
    from world.director.assignment import register_arrival_handler
    register_arrival_handler("medic", medic_arrival)


register()
