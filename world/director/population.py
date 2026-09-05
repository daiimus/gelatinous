"""Population — the director's census layer, first slice: the security
base and its complement.

A room designated the **security base** (``@patrol/base``, tag
``("security_base", "director")``) becomes the force's home:

* **spawn** — new secbots materialize there (and any ``@spawnmob/secbot``
  spawned elsewhere is still *posted* to the base);
* **sync** — posted units return there after assignments, which is where
  intel goes force-wide (existing completion handler);
* **respawn** — the base carries a **complement** (``db.security_complement``);
  every director heartbeat counts living posted units and, on a deficit,
  cycles ONE replacement out of the charging alcoves. Dead, wrecked, or
  deleted units simply fall out of the count — no death-hook plumbing,
  the census self-heals.

The **dispatch room** (``@patrol/dispatch``, tag ``("dispatch_room",
"director")``) is an optional split: the console and the operator live
there while spawn/sync/respawn stay at the base. Without one, dispatch
works from the base — the ear and the garage are the same room.

This is deliberately the seed of the spec's population registry (§3):
role + home + lifecycle, for one role at one base. The general registry
grows out of it.
"""

from __future__ import annotations

from random import choice, randint
from typing import Any

#: Room tag marking the security base.
BASE_TAG = "security_base"
BASE_TAG_CATEGORY = "director"

#: Room tag marking the dispatch room — where the console and the
#: operator live. Optional: without one, dispatch works from the base.
DISPATCH_TAG = "dispatch_room"


# --------------------------------------------------------------------------
# The base
# --------------------------------------------------------------------------

def get_security_base() -> Any | None:
    """The designated security-base room, or ``None``."""
    from evennia.objects.models import ObjectDB
    return ObjectDB.objects.filter(
        db_tags__db_key=BASE_TAG,
        db_tags__db_category=BASE_TAG_CATEGORY).first()


def set_security_base(room: Any, complement: int = 1) -> None:
    """Designate *room* as THE security base (single base v1 — any
    previous designation is cleared) with a standing *complement*."""
    old = get_security_base()
    if old is not None and old != room:
        old.tags.remove(BASE_TAG, category=BASE_TAG_CATEGORY)
    room.tags.add(BASE_TAG, category=BASE_TAG_CATEGORY)
    room.db.security_complement = int(complement)


def get_dispatch_room() -> Any | None:
    """The room dispatch answers from: the ``dispatch_room``-tagged room
    if one is designated, else the security base. Decouples the ear from
    the garage — units respawn at the BASE; the console and the operator
    live HERE."""
    from evennia.objects.models import ObjectDB
    room = ObjectDB.objects.filter(
        db_tags__db_key=DISPATCH_TAG,
        db_tags__db_category=BASE_TAG_CATEGORY).first()
    return room if room is not None else get_security_base()


def set_dispatch_room(room: Any) -> None:
    """Designate *room* as THE dispatch room (single room — any previous
    designation is cleared)."""
    from evennia.objects.models import ObjectDB
    old = ObjectDB.objects.filter(
        db_tags__db_key=DISPATCH_TAG,
        db_tags__db_category=BASE_TAG_CATEGORY).first()
    if old is not None and old != room:
        old.tags.remove(DISPATCH_TAG, category=BASE_TAG_CATEGORY)
    room.tags.add(DISPATCH_TAG, category=BASE_TAG_CATEGORY)


# --------------------------------------------------------------------------
# The secbot factory (shared by @spawnmob/secbot and the respawner)
# --------------------------------------------------------------------------

def factory_fit_armament(mob: Any, side: str = "right") -> None:
    """Seat the integrated shotgun module as a standalone augment organ
    (the tail pattern): the robot left the plant with it. Same backend as
    installed human chrome; ``/shotgun`` deploys via the ability layer."""
    from world.medical.core import Organ
    from world.prototypes import ROBOT_SHOTGUN_MODULE_SPEC

    def _fmt(value):
        if isinstance(value, str):
            return value.replace("{side}", side)
        if isinstance(value, dict):
            return {k: _fmt(v) for k, v in value.items()}
        return value

    spec = _fmt(dict(ROBOT_SHOTGUN_MODULE_SPEC))
    organ_name = "integrated_shotgun_module"
    state = mob.medical_state
    state.organs[organ_name] = Organ(organ_name, organ_data=spec)
    mob.save_medical_state()


def factory_fit_comms(mob: Any, side: str = "left") -> None:
    """Seat the built-in comms module (transceiver) in an ear/antenna —
    factory equipment like the riot gun. Tuned to the emergency band; the
    radio receiver reads it via world.radio.comms_organ_frequency, so the
    unit hears the net until the ear is destroyed/harvested."""
    from world.medical.core import Organ
    from world.prototypes import ROBOT_COMMS_MODULE_SPEC
    spec = {k: (v.replace("{side}", side) if isinstance(v, str) else v)
            for k, v in dict(ROBOT_COMMS_MODULE_SPEC).items()}
    state = mob.medical_state
    state.organs["comms_module"] = Organ("comms_module", organ_data=spec)
    mob.save_medical_state()


def spawn_secbot(location: Any, name: str | None = None) -> Any:
    """Build a complete security unit at *location*: robot species +
    LLMNpc brain + persona + role + factory armament, **posted to the
    security base** (or to *location* when no base is designated).
    Returns the unit."""
    from evennia import create_object
    from random import randint as _randint
    from world.anatomy import get_species_default_longdesc_locations
    from world.identity import ROBOT_FINISHES
    from world.llm.personas import SECURITY_BOT_PERSONA
    from world.medical.core import MedicalState
    from world.mob_flavor import apply_random_flavor

    # A secbot IS a security robot — the varied chassis vocabulary
    # (courier/loader/industrial, ROBOT_CHASSIS) belongs to other robots.
    # Finish still varies so units read as a fleet, not clones.
    key = name or f"a {choice(ROBOT_FINISHES)} security robot"
    mob = create_object(
        typeclass="typeclasses.llm_npc.LLMNpc",
        key=key, location=location, home=location,
    )
    # Robot species surfaces (mirrors @spawnmob's generic non-human path).
    mob.db.species = "robot"
    mob.longdesc = get_species_default_longdesc_locations("robot")
    mob._medical_state = MedicalState(mob)
    mob.db.medical_state = mob._medical_state.to_dict()
    mob.sex = "ambiguous"          # machines render neutral (they/their)
    mob.grit = _randint(1, 3)
    mob.resonance = _randint(1, 3)
    mob.intellect = _randint(1, 3)
    mob.motorics = _randint(1, 3)
    apply_random_flavor(mob)
    # Security wiring: dispatchable + voiced; deterministic layer stays
    # authoritative. Chassis renders via its robot key, not the humanoid
    # descriptor table (LLMNpc's safety-net seeds height/build).
    mob.db.is_npc = True   # the canonical NPC marker (absence = PC)
    # A voice in the MECHANICAL register of the curated vocab — the unit's
    # radio traffic ("Unit engaging — backup to ...") should read machine.
    from random import choice as _choice
    mob.db.voice_description = _choice(("clipped", "flinty", "icy"))
    mob.db.voice_ending = _choice(("monotone", "hum"))
    mob.db.role = "security"
    mob.db.llm_persona = dict(SECURITY_BOT_PERSONA)
    mob.db.llm_driven = True
    mob.height = None
    mob.build = None
    try:
        factory_fit_armament(mob)
    except Exception:  # noqa: BLE001 — an unarmed unit still functions
        pass
    try:
        factory_fit_comms(mob)   # built-in transceiver (one ear)
    except Exception:  # noqa: BLE001 — a deaf unit still patrols
        pass
    # Belong to the base: post there; adopt the base's standing beat.
    base = get_security_base()
    post = base or location
    mob.db.post = post
    beat = list(getattr(getattr(post, "db", None), "security_beat", None) or [])
    if beat:
        mob.db.patrol_beat = beat

    # Enlisted at birth, not afterwards. The units already walking were
    # ensouled by a build script and this path was not — so every unit
    # lost in the field would have cycled back out of the alcove
    # soulless, and attrition would have quietly undone the whole thing
    # one casualty at a time (#2254).
    #
    # A fresh chassis starts CLEAN: no inherited defects. Neglect has to
    # earn its quirks again on the new body, which is what a NEW unit
    # ought to mean — with the odd consequence that destroying a
    # paranoid secbot is one way to cure it.
    try:
        from world.souls import engine as souls_engine
        souls_engine.ensoul(mob, role="security", home=None, post=post,
                            schedule="always", wage_rate=0.0,
                            profile="robot")
    except Exception:  # noqa: BLE001 — an unsouled unit still patrols
        pass
    return mob


# --------------------------------------------------------------------------
# Complement maintenance (the respawn loop)
# --------------------------------------------------------------------------

def count_posted_secbots(base: Any) -> int:
    """Living security units posted to *base*."""
    from evennia.objects.models import ObjectDB
    n = 0
    for obj in ObjectDB.objects.filter(db_attributes__db_key="post").distinct():
        try:
            if (getattr(obj.db, "post", None) == base
                    and getattr(obj.db, "role", None) == "security"
                    and not obj.is_dead()):
                n += 1
        except Exception:  # noqa: BLE001 — a broken record doesn't count
            continue
    return n


def ensure_comms_fitted() -> int:
    """Upkeep: factory-fit the comms module into any LIVE security unit that
    never got one (units spawned before the transceiver shipped, #1009).
    Idempotent — a unit whose organs already carry the module (even a
    DESTROYED one: an EMP'd ear stays dead, we don't magically re-arm it)
    is a dict-key check, no write. Runs in-process from the heartbeat's
    at_start, so the running server's idmapper stays authoritative."""
    from evennia.objects.models import ObjectDB
    fitted = 0
    for bot in ObjectDB.objects.filter(
            db_attributes__db_key="role").distinct():
        if getattr(bot.db, "role", None) != "security":
            continue
        # Voice self-heal (same upkeep spirit): a pre-voice unit's radio
        # traffic rendered "an unfamiliar voice" — give it the mechanical
        # register its factory now ships with. Idempotent.
        if getattr(bot.db, "voice_description", None) is None:
            try:
                bot.db.voice_description = choice(("clipped", "flinty", "icy"))
                bot.db.voice_ending = choice(("monotone", "hum"))
            except Exception:  # noqa: BLE001
                pass
        state = getattr(bot, "medical_state", None)
        if state is None:
            continue
        if "comms_module" in (getattr(state, "organs", None) or {}):
            continue
        try:
            factory_fit_comms(bot)
            fitted += 1
        except Exception:  # noqa: BLE001 — one odd unit never stops the sweep
            continue
    return fitted


def ensure_base_station() -> Any | None:
    """Upkeep: the dispatch room carries its console (the
    RADIO_COMMS_SPEC §2.1 base station — the voice that acknowledges
    reports on 911MHz). Idempotent; in-process (heartbeat at_start).
    Returns the station (existing or newly installed), or None without
    a designated dispatch room or base."""
    base = get_dispatch_room()
    if base is None:
        return None
    for obj in base.contents:
        if getattr(getattr(obj, "db", None), "is_base_station", None) is True:
            # Typeclass self-heal: consoles installed before the answering
            # brain existed swap up in place (attributes preserved).
            try:
                from typeclasses.items import DispatchConsole
                if not isinstance(obj, DispatchConsole):
                    obj.swap_typeclass(
                        "typeclasses.items.DispatchConsole",
                        clean_attributes=False, run_start_hooks=None)
            except Exception:  # noqa: BLE001 — a dumb console still acks
                pass
            return obj
    try:
        from evennia.prototypes.spawner import spawn
        from world.prototypes import BASE_STATION
        station = spawn(BASE_STATION)[0]
        station.location = base
        return station
    except Exception:  # noqa: BLE001 — a mute base still dispatches
        return None


def spawn_dispatch_operator(base: Any) -> Any:
    """The human at the desk (Operator v1: Petra). Face-to-face she's a
    GM-lane NPC; ON THE AIR the console's civic lane speaks AS her — her
    voice, her register — so the far end of the radio is a person."""
    from evennia import create_object
    from world.llm.personas import DISPATCH_OPERATOR_PERSONA
    op = create_object(
        typeclass="typeclasses.llm_npc.LLMNpc",
        key="Petra", location=base, home=base,
    )
    op.height = "short"
    op.build = "lean"
    op.sex = "female"
    op.db.is_npc = True
    op.db.dispatch_operator = True
    op.db.voice_description = "smoky"
    op.db.voice_ending = "rasp"
    op.db.llm_persona = dict(DISPATCH_OPERATOR_PERSONA)
    op.db.llm_driven = True
    op.look_place = ("seated at the dispatch console, headset on, one eye "
                     "on the board.")
    # Take the actual chair when the base has one (real posture, not just
    # the placement line) — fail-open: she stands if the furniture's gone.
    try:
        op.execute_cmd("sit dispatch chair")
    except Exception:  # noqa: BLE001
        pass
    return op


def ensure_dispatch_operator() -> Any | None:
    """Upkeep (heartbeat at_start): the dispatch room has someone at the
    desk.
    Idempotent. A DEAD operator is a vacancy and the desk staffs itself
    again — the same rule every other post follows, and the dispatch
    fixture already carries `post_policy = resleave` like the bars do
    (owner ruling, 2026-09-05). An operator who is merely ELSEWHERE is
    not a vacancy: she is a person who walked off, and hiring a second
    body of her is how three Petras happened (#2181).

    Absence is still SILENCE while it lasts: with nobody at the desk the
    console answers nothing at all, because the colony is operated by
    its people and an unmanned emergency line is the setting rather than
    a hole in it (owner ruling, 2026-08-22).

    The docstring previously said a dead operator was NOT auto-hired,
    which contradicted both the post policy on the same fixture and
    `test_a_dead_operator_does_not_block_rehiring`. The code did neither
    thing on purpose — its liveness filter read `obj.db.is_dead`, an
    attribute no object carries, so it was always true and dead
    operators counted as staff (#2762)."""
    base = get_dispatch_room()
    if base is None:
        return None
    for obj in base.contents:
        if getattr(getattr(obj, "db", None), "dispatch_operator", None) is True:
            return obj
    # `is_dead()` — the METHOD. `obj.db.is_dead` is an attribute row no
    # object in the world has ever carried, so the old spelling was
    # always true and never filtered anybody; the same file already gets
    # this right 22 lines down. Same misread as #2706.
    #
    # An operator who exists but is STANDING SOMEWHERE ELSE is not a
    # vacancy to fill — she is a person who walked off, and hiring a
    # second body of her is how three Petras happened (#2181). The
    # empty desk answers in the console's automation voice, which is
    # what this function's own docstring says absence should sound
    # like, and her planner can walk her back.
    from evennia.objects.models import ObjectDB
    existing = [
        obj for obj in ObjectDB.objects.filter(
            db_attributes__db_key="dispatch_operator")
        if obj.pk and obj.db.dispatch_operator is True
        and not obj.is_dead()
    ]
    if existing:
        return None
    try:
        op = spawn_dispatch_operator(base)
        op.execute_cmd("emote settles into the chair at the dispatch "
                       "console and pulls the headset on.")
        return op
    except Exception:  # noqa: BLE001 — an empty desk still automates
        return None


def get_dispatch_operator() -> Any | None:
    """The LIVE operator at the desk, or None (dead, unconscious, absent,
    kidnapped = the automation answers — a difference players can hear)."""
    base = get_dispatch_room()
    if base is None:
        return None

    # WHO HOLDS THE CHAIR, not who the spawner flagged. This asked
    # `db.dispatch_operator is True`, an attribute exactly ONE object in
    # the database carries — the day keeper. The desk is rostered across
    # all three shifts (day Petra, swing Kiro, night Ines), so for two
    # shifts out of three this returned None no matter who was sitting
    # there, and the automation answered. By the docstring's own framing
    # that is "a difference players can hear": two-thirds of every day,
    # the colony had no dispatcher by definition (#2710).
    #
    # `keeper_on_duty` is the post machinery the shops, bar and clinic
    # gates already use, and it answers the state question this
    # docstring describes: somebody is here AND it is their shift. The
    # dispatch room IS the post fixture, so it can be asked directly.
    operator = None
    try:
        from world.souls.posts import keeper_on_duty
        operator = keeper_on_duty(base)
    except Exception:  # noqa: BLE001 — fall through to the legacy flag
        operator = None

    if operator is None:
        # Legacy fallback: a body explicitly flagged and standing here.
        # Kept so a post with no slots configured still works, and so
        # this strictly WIDENS who can qualify rather than trading one
        # narrow test for another.
        for obj in base.contents:
            if getattr(getattr(obj, "db", None),
                       "dispatch_operator", None) is True:
                operator = obj
                break
    if operator is None:
        return None

    try:
        if operator.is_dead() or operator.is_unconscious():
            return None
    except Exception:  # noqa: BLE001 — no medical read, assume working
        pass
    return operator


def get_base_station() -> Any | None:
    """The dispatch room's live, powered console, or None (no room, no
    console, console off/broken = dispatch has no voice — the physical
    gate: sabotage the console and the net goes quiet)."""
    from world.radio import is_powered, is_radio
    base = get_dispatch_room()
    if base is None:
        return None
    for obj in base.contents:
        if (getattr(getattr(obj, "db", None), "is_base_station", None) is True
                and is_radio(obj) and is_powered(obj)):
            antenna = getattr(obj.db, "antenna", None)
            if antenna is not None and getattr(
                    getattr(antenna, "db", None), "intact", None) is not True:
                return None   # mast down = dispatch has no voice
            return obj
    return None


def maintain_security_complement() -> Any | None:
    """One heartbeat of the respawn loop: if living posted units fall
    short of the base's complement, cycle ONE replacement out of the
    alcoves (one per tick — losses are made good at machine-logistics
    pace, not instantly). Returns the new unit or ``None``."""
    base = get_security_base()
    if base is None:
        return None
    complement = int(getattr(base.db, "security_complement", None) or 0)
    if complement <= 0 or count_posted_secbots(base) >= complement:
        return None
    unit = spawn_secbot(base)
    try:
        unit.execute_cmd(
            "emote cycles out of a charging alcove, status lights "
            "climbing to green.")
    except Exception:  # noqa: BLE001
        pass
    return unit


# ---------------------------------------------------------------------------
# Civilian population
# ---------------------------------------------------------------------------
# Secbots have had a respawn loop since the security slice shipped; civilians
# never did. They were spawned by hand (`@civilians/populate`) and every one
# that died stayed dead, so the streets drained monotonically and the only
# cure was a builder remembering to top them up.
#
# This is the same shape as maintain_security_complement: ONE per heartbeat,
# so a massacre is made good over minutes rather than instantly, and the
# colony never appears to teleport a crowd into a room someone is standing in.

#: Ceiling on the ambient civilian population. Not a target to rush to — the
#: loop trickles toward it. Override in settings as CIVILIAN_POOL_MAX.
CIVILIAN_POOL_DEFAULT = 40


def civilian_pool_max() -> int:
    """The ceiling, from settings if set, else :data:`CIVILIAN_POOL_DEFAULT`."""
    from django.conf import settings
    try:
        return max(0, int(getattr(settings, "CIVILIAN_POOL_MAX",
                                  CIVILIAN_POOL_DEFAULT)))
    except (TypeError, ValueError):
        return CIVILIAN_POOL_DEFAULT


def living_civilians() -> list:
    """Every civilian currently on the grid."""
    from evennia.utils.search import search_tag
    return [npc for npc in search_tag("civilian", category="director") if npc]


def _spawnable_rooms() -> list:
    """
    Where a civilian may appear.

    Two rules, both about not being seen to pop into existence:
    somewhere with a reason to have people (`crowd_base_level > 0`), and
    nowhere a player is standing.
    """
    from world.spatial.coordinates import all_coordinate_rooms
    rooms = []
    for room in all_coordinate_rooms():
        if "Room" not in getattr(room, "typeclass_path", ""):
            continue
        if getattr(room.db, "is_sky_room", False):
            continue
        if not (getattr(room, "crowd_base_level", 0) or 0):
            continue
        if any(getattr(o, "has_account", False) for o in room.contents):
            continue
        rooms.append(room)
    return rooms


def maintain_civilian_population():
    """
    One heartbeat of the civilian respawn loop.

    Spawns at most ONE civilian, and only while the living population is
    under :func:`civilian_pool_max`. Returns the new civilian or ``None``.
    """
    from random import choice

    ceiling = civilian_pool_max()
    if ceiling <= 0:
        return None
    if len(living_civilians()) >= ceiling:
        return None

    rooms = _spawnable_rooms()
    if not rooms:
        return None

    from world.director.civilians import CIVILIAN_ROLES, spawn_civilian
    return spawn_civilian(choice(sorted(CIVILIAN_ROLES)), choice(rooms))
