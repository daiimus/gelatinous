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
