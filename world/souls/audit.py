"""The souls audit log — what the colony did, kept (#2318).

Three surfaces recorded soul behaviour before this and none of them
remembered:

* the WSIS bus decays on a half-life, by design -- it answers "how is
  the colony RIGHT NOW" and its own docstring says the picture is
  "always 'lately', never 'ever'"
* ``soul_faults`` keeps the last FIVE per soul, so a soul that fails
  two hundred times shows you five
* ``server.log`` hears from souls exactly once, on population arrival

So there was no way to ask whether last week was worse than this week,
which route keeps failing, or whether anybody ever buys clothes. Every
soul bug found today -- a courier who started one run and finished
none, five souls failing to path to a padlocked shutter for hours --
was found by a human happening to look.

This is the other half of the pair, and deliberately NOT part of WSIS.
The bus is a live index built on decayed weights and its cheapness is
its premise. Analysis wants the opposite: undecayed, timestamped,
append-only facts. Emit to both at the same call site, the way combat
already does, and neither compromises the other.

Five event kinds, one line each:

    goal   a soul chose something to do
    fault  a job broke, and why
    done   a job finished
    coin   money moved
    life   somebody arrived, died, resleeved, or inherited a post

Format is ``kind key=value ...`` -- greppable with no parser, parseable
with a trivial one. Values never contain spaces, so a field is always
one token.
"""
import logging
import logging.handlers
import os

from django.conf import settings

AUDIT_FILENAME = "souls_audit.log"

#: Per-process logger cache, mirroring `world.combat.debug`.
_LOGGER: list = []


def _under_test() -> bool:
    """True when a test runner owns this process.

    Both audit logs write to ``settings.LOG_DIR``, which the test
    settings do not override -- so every suite run appended its
    fixtures and mock exceptions to the PRODUCTION logs. Found by
    reading this one and seeing `who=Char#6 at=Room
    reason=radio_work_crashed:_boom`: `Char`, `Room` and `boom` are a
    test fixture and a mock, not a colonist and an accident (#2328).

    `combat_audit.log` had it far worse -- 6542 MagicMock references in
    401MB -- because it has been running for months.

    Detected by the DATABASE, not by argv: Django's test runner swaps
    in a `test_`-prefixed database, and that is true no matter how the
    suite was invoked.
    """
    import sys
    # The runner itself. `evennia test ...` is how the suite is always
    # invoked here, and this is true before any database exists.
    if "test" in sys.argv[:3]:
        return True
    try:
        from django.db import connection
        name = str(connection.settings_dict.get("NAME") or "")
    except Exception:  # noqa: BLE001 — if we cannot tell, keep logging
        return False
    # Django swaps in a throwaway database. Evennia's is IN-MEMORY --
    # `file:memorydb_default?mode=memory&cache=shared` -- not the
    # `test_`-prefixed file the docs describe, which is why the first
    # version of this check let six more lines through and had to be
    # measured rather than assumed.
    import os
    return ("memory" in name
            or os.path.basename(name).startswith("test_"))


def _logger():
    """The stdlib logger writing ``souls_audit.log``.

    Thread-safe (logging locks per handler), rotation-safe (rollover
    happens under that lock) and reactor-friendly: the handler buffers
    through the OS page cache, so a write is microseconds. Same
    discipline as `combat_audit.log`, whose rotation settings this
    follows so the two age out together.
    """
    if _LOGGER:
        return _LOGGER[0]
    log = logging.getLogger("gelatinous.souls_audit")
    if not log.handlers:
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(settings.LOG_DIR, AUDIT_FILENAME),
            maxBytes=max(1000, getattr(settings, "CHANNEL_LOG_ROTATE_SIZE",
                                       10_000_000)),
            backupCount=100, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [-] %(message)s", datefmt="%y-%m-%d %H:%M:%S"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    _LOGGER.append(log)
    return log


def _tok(value) -> str:
    """One field, one token. Spaces become underscores so a line can be
    split on whitespace forever, and an empty value is still a token."""
    if value is None:
        return "-"
    return str(value).replace(" ", "_").replace("=", "-") or "-"


def _who(soul) -> str:
    """A soul as a stable identifier: key and dbref together, because
    keys repeat across resleeves and dbrefs do not."""
    if soul is None:
        return "-"
    return f"{_tok(getattr(soul, 'key', '?'))}#{getattr(soul, 'id', 0) or 0}"


def record(kind: str, soul=None, **fields) -> None:
    """Write one audit line. Never raises -- observation must not be
    able to break the thing it observes."""
    if _under_test():
        return          # never append test fixtures to the real log
    try:
        parts = [kind, f"who={_who(soul)}"]
        if soul is not None:
            db = getattr(soul, "db", None)
            role = getattr(db, "soul_role", None)
            if role:
                parts.append(f"role={_tok(role)}")
            where = getattr(soul, "location", None)
            parts.append(f"at={_tok(getattr(where, 'key', None))}")
        for key, value in fields.items():
            parts.append(f"{key}={_tok(value)}")
        _logger().info(" ".join(parts))
    except Exception:  # noqa: BLE001 — a log that can break a beat is
        pass                                        # worse than no log


# --- the five kinds -------------------------------------------------

def goal(soul, goal_name, band=None, hour=None):
    """A soul chose something to do."""
    record("goal", soul, goal=goal_name, band=band,
           hour=None if hour is None else round(float(hour), 1))


def fault(soul, goal_name, reason):
    """A job broke. The single most useful line in the file: it is what
    would have said 'Wren has started one run and finished none'."""
    record("fault", soul, goal=goal_name, reason=reason)


def done(soul, goal_name):
    """A job finished. Paired with `goal`, this is the completion rate
    for every kind of work in the colony."""
    record("done", soul, goal=goal_name)


def coin(soul, amount, why, other=None):
    """Money moved. Wages, purchases, fees, till deltas -- the record
    that answers whether the economy circulates or merely accrues."""
    record("coin", soul, amount=amount, why=why, other=_who(other)
           if other is not None else None)


def life(soul, event, detail=None):
    """Arrival, death, resleeve, succession. The population's history."""
    record("life", soul, event=event, detail=detail)
