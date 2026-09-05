"""Biometric access grants — everything is a file (verticality §2.2).

No keys, no codes, no cards: a lock reads the presenter's SLEEVE (the
identity spine's ``sleeve_uid``) and checks it against its **grant
file** — a list of ``{"sleeve": uid, "until": epoch-or-None,
"issued_by": name}`` entries stored as honest attributes on the lock
until decking makes them hackable. The attack surface is forgery, not
theft: present someone else's biometrics.

Consumers: ``DoorExit.access_grants`` (typeclasses/doors.py) and the
elevator's per-floor ``db.floor_locks`` (typeclasses/elevator.py).
"""

from __future__ import annotations

import time
from typing import Any, Optional


def sleeve_uid_of(char: Any) -> Optional[str]:
    """The presenter's biometric — the sleeve's canonical uid."""
    try:
        return getattr(char, "sleeve_uid", None)
    except Exception:  # noqa: BLE001 — a broken identity reads as no-match
        return None


def make_grant(char: Any, issued_by: Any = None,
               until: Optional[float] = None) -> dict:
    """A grant-file entry for *char*'s sleeve (§2.2 record shape)."""
    return {
        "sleeve": sleeve_uid_of(char),
        # `is None`, not falsy. An expiry of 0 is a real instant --
        # the epoch, or a duration that has already elapsed -- and
        # coercing it to None mints a PERMANENT grant out of one that
        # should already be dead (#2690).
        "until": None if until is None else float(until),
        "issued_by": str(issued_by) if issued_by else None,
    }


def is_granted(char: Any, grants: Any) -> bool:
    """Does *char*'s sleeve match a live entry in *grants*?

    Fail-closed: no sleeve, no grants, malformed entries, expired
    entries — all read as not granted. One bad record never grants
    (or blocks) the rest.
    """
    uid = sleeve_uid_of(char)
    if not uid or not grants:
        return False
    now = time.time()
    for entry in grants:
        try:
            if entry.get("sleeve") != uid:
                continue
            until = entry.get("until")
            # Same distinction on the read side, where the mistake was
            # made independently: `None` and `0` are both falsy, so a
            # stored zero skipped the expiry test entirely and granted
            # access forever. Fixing only the writer would have left
            # this reading any zero already on disk as permanent.
            #
            # This is the one ambiguity in the function that failed
            # OPEN, in a module whose docstring commits to the opposite
            # -- and it failed open on the value that most obviously
            # means "not valid" (#2690).
            if until is not None and now > float(until):
                continue
            return True
        except Exception:  # noqa: BLE001
            continue
    return False
