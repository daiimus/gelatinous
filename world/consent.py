"""Trust & consent — the third-party action gate.

Implements TRUST_AND_CONSENT_SPEC Phase 1: one shared answer to "may this
actor do this class of thing to that target?" so third-party commands stop
inventing one-off gates.

The core stance (spec §1): a target can refuse an invasive third-party
action only when it can CONTEST — conscious AND unrestrained. Otherwise the
action lands freely (the existing unconscious/dead gate, generalized to
include restraint). The conscious-and-unwilling path is opened by TRUST,
granted per action class and keyed to the actor's *perceived identity*
(``get_apparent_uid`` — trusting "batman" is not trusting "bruce wayne";
spec §2).

Consumers call :func:`check_consent`; the ``trust``/``distrust`` commands
(``commands/CmdTrust.py``) manage the grants.
"""

from evennia.utils.dbserialize import deserialize

#: The grantable action classes (spec §3). A class maps to a set of gated
#: commands; Phase 1 wires the ``dress`` (third-party clothing) and ``heal``
#: (all-medical, deliberately blanket) consumers. ``escort``/``grab``/
#: ``search`` grants are storable now, consumed by later phases.
ACTION_CLASSES = ("dress", "escort", "grab", "heal", "search")


# --------------------------------------------------------------------------
# The contest predicate (spec §1)
# --------------------------------------------------------------------------

def is_conscious(target) -> bool:
    """Whether the target is provably awake. A target with no readable
    medical state is treated as conscious — we only take the free-action
    path when helplessness is affirmative, matching the conservative
    polarity of the old per-command gates."""
    medical_state = getattr(target, "medical_state", None)
    if medical_state is None:
        return True
    try:
        if callable(medical_state.is_dead) and medical_state.is_dead():
            return False
        if (callable(medical_state.is_unconscious)
                and medical_state.is_unconscious()):
            return False
    except Exception:  # noqa: BLE001 — unreadable state = assume awake
        return True
    return True


def is_restrained(target) -> bool:
    """The shared restraint predicate (spec §7.3): a grapple OR a restraint
    device. Devices are furniture with ``db.restraining``; live AutoDocs
    predate that flag, so a medical lie-in pod counts too (the healing pod
    is the spec's canonical restraint device — no live backfill needed)."""
    # Grapple (world/combat/grappling.py state).
    try:
        from world.combat.constants import NDB_COMBAT_HANDLER
        from world.combat.grappling import is_grappled
        handler = getattr(target.ndb, NDB_COMBAT_HANDLER, None)
        if handler and is_grappled(handler, target):
            return True
    except Exception:  # noqa: BLE001 — no combat state = not grappled
        pass
    # Restraint device (furniture the target occupies).
    try:
        furniture = target.db.furniture
        if furniture is not None:
            if getattr(furniture.db, "restraining", False):
                return True
            if (getattr(furniture.db, "is_medical", False)
                    and "lying" in (furniture.db.postures or ())):
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def can_contest(target) -> bool:
    """Spec §1: ``is_conscious(target) and not is_restrained(target)``."""
    return is_conscious(target) and not is_restrained(target)


# --------------------------------------------------------------------------
# Grants (spec §2 storage: on the grantor, keyed by apparent uid)
# --------------------------------------------------------------------------

def get_grants(grantor) -> dict:
    """The grantor's grants as a plain dict:
    ``{apparent_uid: {"classes": [..], "label": "<snapshot>"}}``.
    Defensive: a non-character "grantor" (a rock someone targeted)
    simply holds no grants."""
    db = getattr(grantor, "db", None)
    return deserialize(getattr(db, "consent_grants", None)) or {}


def grant_trust(grantor, actor, action_class) -> list:
    """Grant ``action_class`` (or ``"all"``) to ``actor``'s CURRENT apparent
    identity. Returns the actor's stored class list after the grant. The
    display-label snapshot is refreshed each grant (spec §5 fallback)."""
    from world.identity import get_apparent_uid
    uid = get_apparent_uid(actor)
    if not uid:
        return []
    grants = get_grants(grantor)
    entry = dict(grants.get(uid) or {})
    classes = list(entry.get("classes") or [])
    wanted = list(ACTION_CLASSES) if action_class == "all" else [action_class]
    for cls in wanted:
        if cls in ACTION_CLASSES and cls not in classes:
            classes.append(cls)
    entry["classes"] = classes
    try:
        entry["label"] = actor.get_display_name(grantor)
    except Exception:  # noqa: BLE001
        entry["label"] = entry.get("label") or getattr(actor, "key", "someone")
    grants[uid] = entry
    grantor.db.consent_grants = grants
    return classes


def revoke_trust(grantor, uid, action_class=None) -> bool:
    """Revoke one class (or, with ``action_class=None``, every grant) held
    by ``uid``. Returns True if anything was removed."""
    grants = get_grants(grantor)
    entry = grants.get(uid)
    if not entry:
        return False
    if action_class is None:
        del grants[uid]
        grantor.db.consent_grants = grants
        return True
    classes = list(entry.get("classes") or [])
    if action_class not in classes:
        return False
    classes.remove(action_class)
    if classes:
        entry = dict(entry)
        entry["classes"] = classes
        grants[uid] = entry
    else:
        del grants[uid]
    grantor.db.consent_grants = grants
    return True


def wipe_trust(grantor) -> int:
    """``distrust all`` — wipe every grant. Returns how many were held."""
    n = len(get_grants(grantor))
    grantor.db.consent_grants = {}
    return n


def grant_display_name(grantor, uid, entry=None) -> str:
    """How the grantor PERCEIVES a stored grant-holder (spec §5): their
    recognition name for that uid if they still know one, else the label
    snapshotted at grant time."""
    try:
        memory = deserialize(grantor.recognition_memory) or {}
        assigned = (memory.get(uid) or {}).get("assigned_name")
        if assigned:
            return assigned
    except Exception:  # noqa: BLE001
        pass
    entry = entry or get_grants(grantor).get(uid) or {}
    return entry.get("label") or "someone"


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

def has_trust(target, actor, action_class) -> bool:
    """Whether ``target`` currently trusts ``actor``'s apparent identity
    with ``action_class``. A disguise change or re-sleeve shifts the
    actor's uid and the grant silently stops matching (spec §2)."""
    try:
        from world.identity import get_apparent_uid
        uid = get_apparent_uid(actor)
    except Exception:  # noqa: BLE001
        return False
    if not uid:
        return False
    entry = get_grants(target).get(uid)
    return bool(entry and action_class in (entry.get("classes") or ()))


def check_consent(actor, target, action_class) -> bool:
    """THE gate. True when ``actor`` may perform an ``action_class`` action
    on ``target``: self-action, a target that cannot contest (unconscious /
    dead / restrained — the free path), or pre-granted trust."""
    if actor is target:
        return True
    if not can_contest(target):
        return True
    return has_trust(target, actor, action_class)
