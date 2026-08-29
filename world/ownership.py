"""Who owns a body — the question to answer before deleting one.

**`db_account_id` is not ownership.** It is set only while a character
is actively PUPPETED, so every logged-out player character in the game
reads as ownerless by that field. Filtering on it to mean "this is not
a player's body" is wrong, it is quiet, and it is destructive: this
codebase has already lost player characters that way, and it has a
one-time repair command (`@fixchar`) that exists because ownership was
recorded three different ways over the project's life.

So there are three signals, and a body is a player's if ANY of them
says so:

1. ``db_account_id`` — currently puppeted. Present only while online.
2. ``account.db._playable_characters`` — the canonical modern record,
   and the only one that survives logout. 56 characters are claimed
   this way in a colony where 23 accounts exist.
3. the ``puppet:`` lock naming an account id — how LEGACY characters
   were bound before `account.create_character()`, per `@fixchar`.

Ask :func:`is_player_owned` before deleting, archiving, re-typing or
mass-editing any Character. It is cheap, and the failure it prevents is
not recoverable.
"""

import re

#: A puppet lock that names a specific account — `pid(7)`, `id(7)`.
_PUPPET_ACCOUNT = re.compile(r"\bp?id\((\d+)\)")


def owning_accounts(obj):
    """Every account with a claim on *obj*, by any of the three signals.

    Returns a list of ``(account_key, how)`` pairs — `how` names which
    signal fired, because "who owns this" and "why do we think so" are
    both needed when the answer is surprising.
    """
    claims = []
    if obj is None or not getattr(obj, "pk", None):
        return claims

    account_id = getattr(obj, "db_account_id", None)
    if account_id:
        claims.append((str(account_id), "puppeted"))

    try:
        from evennia.accounts.models import AccountDB
        for acct in AccountDB.objects.all():
            for char in (acct.db._playable_characters or []):
                if char is not None and getattr(char, "pk", None) == obj.pk:
                    claims.append((acct.key, "playable_characters"))
    except Exception:  # noqa: BLE001 — an unreadable account is not a licence
        claims.append(("<unreadable>", "account-scan-failed"))

    try:
        for clause in str(obj.locks).split(";"):
            if not clause.startswith("puppet:"):
                continue
            found = _PUPPET_ACCOUNT.search(clause)
            if found:
                claims.append((found.group(1), "puppet-lock"))
    except Exception:  # noqa: BLE001
        pass

    return claims


def is_player_owned(obj) -> bool:
    """Does any account have a claim on this body?

    Fails CLOSED: an account list that cannot be read counts as a claim,
    because the cost of a false "nobody owns this" is somebody's
    character and the cost of a false "somebody does" is a body left
    standing.
    """
    return bool(owning_accounts(obj))
