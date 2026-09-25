"""Sleeve insurance — a personal policy, bought alive, spent by a return.

The intro framework (SLEEVE_INSURANCE_SPEC, #3667). A policy is an
off-body record held by Thawn-Harrison, one per sleeve uid, keyed to the
DNA sample the lobby terminal takes: `sleeve_uid_of(presser)`, the same
biometric the lockers and the rental board key on. Off-body because the
body is deleted or archived at death; one per uid because a lineage
shares its uid (a flash clone copies it, `imprint.restore` writes it back),
so stacking records would stack lives.

Storage is one `ServerConfig` row per uid (`sleeve_policy:<uid>`, 50
chars in a 64-char unique key). Not a GLOBAL_SCRIPTS entry: Evennia
recreates a managed global script whenever its settings entry changes,
which is how the WSIS ring nearly lost its history (#2672). Not on the
terminal: a re-run build or a deleted machine would wipe every policy
(the #3565 class). The unique key is what makes a purchase and a take
atomic: a duplicate INSERT fails, and a DELETE returns 1 exactly once.

Slice A ships the record and the terminal and makes a flash clone SPEND
the record. Nothing yet REQUIRES one (Slice C), and no NPC goes to buy
(Slice B).
"""
import time
from typing import Any, Optional

from django.db import IntegrityError

from world.access import sleeve_uid_of

#: What a policy costs, in tokens. Zero for now: the economy is not
#: balanced (owner ruling 2026-09-25); the act of buying stays.
POLICY_PRICE = 0

_KEY = "sleeve_policy:"

#: The one reply both respawn doors will give in Slice C; here so the
#: terminal's status line and the doors never drift.
NO_POLICY = "No sleeve policy on file."


def key_for(uid: str) -> str:
    return f"{_KEY}{uid}"


def policy_for(uid: Optional[str]) -> Optional[dict]:
    """The record on file for *uid*, or None."""
    if not uid:
        return None
    from collections.abc import Mapping
    from evennia.server.models import ServerConfig
    # A pickled dict comes back as Evennia's _SaverDict, a Mapping that is
    # NOT a dict subclass; an isinstance(dict) test read every row as empty.
    stored = ServerConfig.objects.conf(key_for(uid), default=None)
    return dict(stored) if isinstance(stored, Mapping) else None


def covers(char: Any) -> bool:
    """Can *char* redeem a policy: one on file for their uid, bought by
    this body. A record bought by another body of the lineage (an older
    husk) does not cover them."""
    rec = policy_for(sleeve_uid_of(char))
    return bool(rec) and rec.get("buyer_dbref") == getattr(char, "id", None)


def _is_presentable(char: Any) -> Optional[str]:
    """Why *char* cannot give a sample right now, or None if they can."""
    try:
        if char.is_dead():
            return "The reader passes over you and registers no vital signs."
        if char.scripts.get("death_progression"):
            return "The reader passes over you and registers no vital signs."
        if char.is_archived:                # a property on Character
            return "The reader finds a sleeve signature that is not in service."
        if char.is_unconscious():
            return "The reader waits for a conscious subject."
    except AttributeError:
        return "The reader finds nothing it can sample."
    return None


def buy_policy(char: Any, terminal: Any = None) -> tuple[bool, str]:
    """The terminal transaction. Returns ``(ok, message)``.

    The sample is the presser's own uid: never a held object (a corpse
    and a severed head carry the uid too). One record per uid: a second
    press by the same body is "already on file"; a record whose buyer is
    a dead or archived body of the same lineage is void and replaced, so
    a return that did not spend it can never strand the living body; a
    record held by another LIVE body of the lineage is refused.
    """
    uid = sleeve_uid_of(char)
    if not uid:
        return False, ("The reader passes over you and finds no sleeve "
                       "signature to sample.")
    why_not = _is_presentable(char)
    if why_not:
        return False, why_not

    existing = policy_for(uid)
    if existing:
        if existing.get("buyer_dbref") == char.id:
            return False, "Your policy is already on file."
        holder = _body(existing.get("buyer_dbref"))
        if holder is not None and _alive_and_in_service(holder):
            return False, ("The reader flags your signature: a policy is "
                           "on file for another sleeve.")
        void_policy(uid)                    # an older body's leftover

    if POLICY_PRICE > 0:
        have = int(getattr(char, "tokens", 0) or 0)
        if have < POLICY_PRICE:
            return False, (f"The terminal quotes {POLICY_PRICE} tokens. "
                           f"You have {have}.")

    record = {
        "uid": uid,
        "bought_at": time.time(),
        "buyer_key": str(getattr(char, "key", "")),
        "buyer_dbref": char.id,
        "blueprint_key": char.attributes.get("blueprint_key"),
        "account_id": getattr(getattr(char, "account", None), "id", None),
    }
    if not _insert(record):
        return False, "Your policy is already on file."

    if POLICY_PRICE > 0:
        from world.souls import audit
        char.tokens = int(char.tokens or 0) - POLICY_PRICE
        if terminal is not None and terminal.attributes.has("register"):
            terminal.db.register = int(terminal.db.register or 0) + POLICY_PRICE
        audit.coin(char, POLICY_PRICE, "sleeve_policy", other=terminal)

    return True, ("The reader takes its sample. A Thawn-Harrison sleeve "
                  "policy is on file in your name.")


def take_policy(uid: Optional[str], body_id: Optional[int]) -> Optional[dict]:
    """Spend the policy for *uid*, but only if *body_id* bought it. Atomic:
    the DELETE returns 1 exactly once, so two returns racing for one
    record get one body and one clean refusal. Returns the record taken,
    or None. The caller restores it with :func:`restore_policy` if the
    build that follows fails."""
    rec = policy_for(uid)
    if not rec or rec.get("buyer_dbref") != body_id:
        return None
    from evennia.server.models import ServerConfig
    deleted, _ = ServerConfig.objects.filter(db_key=key_for(uid)).delete()
    return rec if deleted == 1 else None


def restore_policy(record: dict) -> bool:
    """Put a taken record back (a return that failed after the take).
    False when somebody already re-bought under that uid."""
    return _insert(dict(record))


def _insert(record: dict) -> bool:
    """The one INSERT. `ServerConfig.value`'s setter saves on assignment,
    so the row is built with the pickled value and saved inside the try:
    a duplicate key raises here, and nowhere else. False = already on
    file."""
    from evennia.server.models import ServerConfig
    from evennia.utils.dbserialize import to_pickle
    row = ServerConfig(db_key=key_for(record["uid"]), db_value=to_pickle(record))
    try:
        row.save()
    except IntegrityError:
        return False
    return True


def spend_policy(uid: Optional[str], body_id: Optional[int]) -> bool:
    """A return has happened for *body_id*: its own record is spent. A
    record held by another body of the lineage is left alone (the living
    body's cover must survive an older husk being cloned; a dead
    holder's leftover is replaced at the terminal by `buy_policy`)."""
    return take_policy(uid, body_id) is not None


def void_policy(uid: Optional[str]) -> bool:
    """Drop whatever is on file for *uid*, whoever bought it. A return
    spends it (flash clone, resleeve); a fresh start after an insured
    death forfeits it (Slice C). Returns whether a record was removed."""
    if not uid:
        return False
    from evennia.server.models import ServerConfig
    deleted, _ = ServerConfig.objects.filter(db_key=key_for(uid)).delete()
    return deleted == 1


def status_line(char: Any) -> str:
    """What the terminal reads back for *char*."""
    uid = sleeve_uid_of(char)
    if uid is None:
        return "The reader finds no sleeve signature to look up."
    rec = policy_for(uid)
    if not rec:
        return NO_POLICY
    if rec.get("buyer_dbref") == char.id:
        return "A Thawn-Harrison sleeve policy is on file in your name."
    return ("A policy is on file for your signature, held by another "
            "sleeve.")


def _body(dbref: Optional[int]) -> Any:
    if not dbref:
        return None
    from evennia.utils.search import search_object
    found = search_object(f"#{dbref}")
    return found[0] if found else None


def _alive_and_in_service(body: Any) -> bool:
    try:
        return not body.is_dead() and not body.is_archived
    except AttributeError:
        return False
