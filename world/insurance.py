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

A record may be PERPETUAL (owner ruling 2026-09-25, for staff and play
testing). It is taken like any other, so two returns racing for it still
get one body and one refusal, and once the return is verified the caller
re-issues it in the NEW body's name (`renew_perpetual`): a flash clone is
a new object with a new id, and a record left pointing at the dead body
would pay for exactly one death. A forfeit (Q5) or a staff revoke removes
it; the terminal also replaces a dead holder's leftover when a living body
of the lineage buys (`buy_policy`), as for any record.

Every take and forfeit is a compare-and-delete on the ROW that was read
(by pk), never a delete by key: a re-issued standing record lives under the
same key, and a door holding a stale read must not consume it.

The doors ask one question, `flash_clone_refusal`, and the gate inside
`create_flash_clone` asks the same one plus "is the body still on the
table", so the card and the refusal can never disagree.
"""
import time
from typing import Any, Optional

from django.db import IntegrityError

from world.access import sleeve_uid_of

#: What a policy costs, in tokens. Zero for now: the economy is not
#: balanced (owner ruling 2026-09-25); the act of buying stays.
POLICY_PRICE = 0

_KEY = "sleeve_policy:"

#: The one reply both respawn doors give; here so the terminal's status
#: line and the doors never drift.
NO_POLICY = "No sleeve policy on file."
NOT_A_DEATH = "That sleeve was shelved, not killed; a policy pays for a death."
STILL_ON_THE_TABLE = "That sleeve is still on the table."
PERPETUAL_NOTE = "standing: a return re-issues it"


class PolicyRefused(Exception):
    """A return the record does not pay for. Raised by the clone gate;
    both respawn doors catch it and show its text, nothing else."""


def key_for(uid: str) -> str:
    return f"{_KEY}{uid}"


def policy_for(uid: Optional[str]) -> Optional[dict]:
    """The record on file for *uid*, or None."""
    return _row_for(uid)[1]


def _row_for(uid: Optional[str]) -> tuple[Any, Optional[dict]]:
    """The store row and its record for *uid*, or ``(None, None)``. The
    row's pk is what a take deletes by."""
    if not uid:
        return None, None
    from collections.abc import Mapping
    from evennia.server.models import ServerConfig
    row = ServerConfig.objects.filter(db_key=key_for(uid)).first()
    if row is None:
        return None, None
    # A pickled dict comes back as Evennia's _SaverDict, a Mapping that is
    # NOT a dict subclass; an isinstance(dict) test read every row as empty.
    stored = row.value
    return row, (dict(stored) if isinstance(stored, Mapping) else None)


def _delete_row(row: Any) -> bool:
    """Compare-and-delete: the one row that was read, by pk. False when it
    was already taken (or replaced) by another door."""
    from evennia.server.models import ServerConfig
    deleted, _ = ServerConfig.objects.filter(pk=row.pk).delete()
    return deleted == 1


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

    row, existing = _row_for(uid)
    if existing:
        if existing.get("buyer_dbref") == char.id:
            if existing.get("perpetual"):
                return False, f"Your policy is already on file ({PERPETUAL_NOTE})."
            return False, "Your policy is already on file."
        holder = _body(existing.get("buyer_dbref"))
        if holder is not None and _alive_and_in_service(holder):
            return False, ("The reader flags your signature: a policy is "
                           "on file for another sleeve.")
        _delete_row(row)                    # an older body's leftover, the row read

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
    the DELETE of the row that was read returns 1 exactly once, so two
    returns racing for one record get one body and one clean refusal, and
    a stale read can never consume a record re-issued under the same key.
    Returns the record taken, or None. The caller restores it with
    :func:`restore_policy` if the build that follows fails, and re-issues
    a perpetual one with :func:`renew_perpetual` once the return is
    verified."""
    row, rec = _row_for(uid)
    if not rec or rec.get("buyer_dbref") != body_id:
        return None
    return rec if _delete_row(row) else None


def restore_policy(record: dict) -> bool:
    """Put a taken record back (a return that failed after the take).
    False when somebody already re-bought under that uid."""
    return _insert(dict(record))


def renew_perpetual(record: dict, new_body: Any) -> bool:
    """A verified return on a PERPETUAL record: re-issue it in the new
    body's name, so the next death is covered too. An ordinary record is
    spent and nothing happens. False when the re-issue lost to a purchase
    on the same uid (the new body is then covered by that purchase)."""
    if not record.get("perpetual"):
        return False
    fresh = dict(record)
    fresh.update({
        "buyer_key": str(getattr(new_body, "key", "")),
        "buyer_dbref": new_body.id,
        "account_id": getattr(getattr(new_body, "account", None), "id", None),
        "renewed_at": time.time(),
    })
    return _insert(fresh)


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


def void_policy(uid: Optional[str]) -> bool:
    """Drop whatever is on file for *uid*, whoever bought it. Returns
    whether a record was removed."""
    if not uid:
        return False
    from evennia.server.models import ServerConfig
    deleted, _ = ServerConfig.objects.filter(db_key=key_for(uid)).delete()
    return deleted == 1


def forfeit_policy(dead_body: Any) -> bool:
    """The person starts fresh after an insured death (Q5): the dead
    body's OWN record goes, standing or not, so no orphaned row can revive
    an abandoned self later. A record another body of the lineage holds
    is left alone. Returns whether a record was removed."""
    row, rec = _row_for(sleeve_uid_of(dead_body))
    if not rec or rec.get("buyer_dbref") != getattr(dead_body, "id", None):
        return False
    return _delete_row(row)


def flash_clone_refusal(old_body: Any) -> Optional[str]:
    """Why *old_body* cannot be flash-cloned, or None when it can. The
    one question both respawn doors ask before offering the card, and the
    gate asks again before the take. A policy pays for a DEATH (ruling
    Q3): the body must be archived with reason "death"; a shelved body
    never comes back this way. Then the record must be this body's own."""
    try:
        if not old_body.is_archived or old_body.db.archived_reason != "death":
            return NOT_A_DEATH
    except AttributeError:
        return NO_POLICY
    if not covers(old_body):
        return NO_POLICY
    return None


def grant_perpetual(char: Any, granted_by: Any = None) -> tuple[bool, str]:
    """Staff: a standing policy for *char*, in this body's name, that a
    return re-issues instead of spending (owner ruling 2026-09-25: play
    testing, staff). Replaces the lineage's record when its holder can no
    longer use it. A dead, archived body may be granted one: that is how
    staff bring back a playtester who died uninsured. Refused: a body with
    no sleeve signature (nothing could ever match it); a SHELVED body (a
    policy pays for a death only, so the grant could never pay); and an
    older husk whose lineage's record is held by a body that is alive, dying,
    or dead and still able to redeem it (the grant would strip that body's
    cover for a record no door can ever reach, since the doors only ever
    offer the newest dead body)."""
    uid = sleeve_uid_of(char)
    if not uid:
        return False, "That body has no sleeve signature to insure."
    try:
        shelved = char.is_archived and char.db.archived_reason != "death"
    except AttributeError:
        shelved = False
    if shelved:
        return False, (f"{char.key} was shelved, not killed; no policy can bring a "
                       f"shelved sleeve back. Grant it on the body in service.")
    row, existing = _row_for(uid)
    if existing and existing.get("buyer_dbref") != char.id:
        holder = _body(existing.get("buyer_dbref"))
        if holder is not None and _holder_still_counts(holder):
            return False, (f"That signature's policy is held by {holder.key} "
                           f"(#{holder.id}), whose return it still pays for; "
                           f"grant it there.")
    if row is not None:
        _delete_row(row)
    record = {
        "uid": uid,
        "bought_at": time.time(),
        "buyer_key": str(getattr(char, "key", "")),
        "buyer_dbref": char.id,
        "blueprint_key": char.attributes.get("blueprint_key"),
        "account_id": getattr(getattr(char, "account", None), "id", None),
        "perpetual": True,
        "granted_by": str(getattr(granted_by, "key", granted_by or "")),
    }
    if not _insert(record):
        return False, "A policy landed on that signature at the same moment; try again."
    return True, f"{char.key} holds a standing sleeve policy ({PERPETUAL_NOTE})."


def revoke_perpetual(char: Any) -> tuple[bool, str]:
    """Staff: take a standing policy away, from the body that holds it.
    Leaves an ordinary policy alone (that is the player's own purchase,
    not staff's to remove here), and refuses to act through an older husk
    of the lineage, so the message always names the body that lost it."""
    uid = sleeve_uid_of(char)
    row, rec = _row_for(uid)
    if not rec:
        return False, f"{char.key} holds no sleeve policy."
    if rec.get("buyer_dbref") != char.id:
        holder = _body(rec.get("buyer_dbref"))
        who = f"{holder.key} (#{holder.id})" if holder is not None else f"body #{rec.get('buyer_dbref')}"
        return False, f"That signature's policy is held by {who}; revoke it there."
    if not rec.get("perpetual"):
        return False, (f"{char.key}'s policy is an ordinary purchase, not a "
                       f"standing one; it is spent by a return, not revoked.")
    if not _delete_row(row):
        return False, (f"{char.key}'s policy changed hands as you spoke (a return "
                       f"re-issued it); read @insure/status and try again.")
    return True, f"{char.key}'s standing sleeve policy is revoked."


def status_line(char: Any) -> str:
    """What the terminal reads back for *char*."""
    uid = sleeve_uid_of(char)
    if uid is None:
        return "The reader finds no sleeve signature to look up."
    rec = policy_for(uid)
    if not rec:
        return NO_POLICY
    if rec.get("buyer_dbref") == char.id:
        if rec.get("perpetual"):
            return (f"A Thawn-Harrison sleeve policy is on file in your name "
                    f"({PERPETUAL_NOTE}).")
        return "A Thawn-Harrison sleeve policy is on file in your name."
    return ("A policy is on file for your signature, held by another "
            "sleeve.")


def envelope_line(char: Any) -> str:
    """The sleeve envelope's POLICY line, printed at every decant so the
    player knows where they stand BEFORE it matters: every character
    starts uninsured, and an uninsured death is permanent."""
    rec = policy_for(sleeve_uid_of(char))
    if rec and rec.get("buyer_dbref") == getattr(char, "id", None):
        if rec.get("perpetual"):
            return "SLEEVE POLICY: STANDING"
        return "SLEEVE POLICY: ON FILE"
    return "SLEEVE POLICY: NONE ON FILE · POLICY TERMINAL IN LOBBY"


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


def _holder_still_counts(holder: Any) -> bool:
    """Can the body holding a record still use it: alive and in service,
    dying (the death path will archive it as a death), or dead-archived
    and able to redeem at the doors. Only a shelved body or a superseded
    husk fails this, and only their record may be replaced through another
    body of the lineage."""
    if _alive_and_in_service(holder):
        return True
    try:
        if holder.scripts.get("death_progression"):
            return True
        if holder.db.death_processed and not holder.is_archived:
            return True
    except AttributeError:
        return False
    return flash_clone_refusal(holder) is None
