"""The closed-loop colony economy (owner verdicts: REAL, no minting).

One treasury, seeded once by build script. Wages for non-venue shifts
draw from it; the return path is the SUPPLY TITHE — every venue till
(`ShopContainer.db.register`) periodically pays a fraction back to the
colony for its restocks (bottomless stock was never free; it is
wholesale). Treasury -> wages -> spending -> tills -> tithe -> treasury.
If the treasury runs dry, wages stop and the `@soul` economy line shows
it — drought is a visible state, not a crash.
"""

from evennia.scripts.models import ScriptDB
from evennia.utils.create import create_script

TREASURY_KEY = "colony_treasury"
TITHE_FRACTION = 0.25          # of each till's register, per tithe pass

_TREASURY = None               # in-process memo; refreshed on a dead ref


def get_treasury():
    global _TREASURY
    if _TREASURY is not None and _TREASURY.pk:
        return _TREASURY
    existing = ScriptDB.objects.filter(db_key=TREASURY_KEY).first()
    if existing:
        _TREASURY = existing
        return existing
    script = create_script(key=TREASURY_KEY, persistent=True, autostart=False)
    script.db.balance = 0
    _TREASURY = script
    return script


def balance():
    return int(get_treasury().db.balance or 0)


def pay_wage(soul):
    """Convert accrued wage_owed into real tokens at shift end.

    Owner rule: venue posts are paid out of their own till
    (`soul.db.soul_venue.db.register`); non-venue posts draw colony
    treasury. Partial payment when the source is short — a drought is a
    visible state (`@soul` shows the unpaid balance), not a crash.

    A venue with NO till is the third case, and it is not a dry one. It
    used to fall into the venue branch, read `int(None or 0)` as zero,
    pay nothing, and never reach the `else` that would have gone to the
    treasury — so the wage accrued forever. Ossie Trelane had banked
    140.56 tokens against a crane console that has no `register`
    attribute at all, with the treasury solvent at 1,150 (#2693).

    It stayed invisible because a missing till and an empty one are
    indistinguishable downstream: both show as an unpaid balance on
    `@soul`, so the display meant to make a drought visible is exactly
    what disguised it.

    A control surface is not a counter. If a venue should fund its own
    posts, give it a register; absent one, the colony pays.
    """
    # fold any un-checkpointed ndb accrual in before paying out
    pending = float(soul.ndb.soul_wage_pending or 0.0)
    if pending:
        soul.ndb.soul_wage_pending = 0.0
    owed_f = float(soul.db.soul_wage_owed or 0.0) + pending
    owed = int(owed_f)               # whole tokens payable now
    if owed <= 0:
        if pending:
            soul.db.soul_wage_owed = owed_f   # folded fraction stays owed
        return 0
    venue = soul.db.soul_venue
    # `has("register")` — not truthiness. An empty till is a real,
    # documented state; a MISSING one means this fixture was never a
    # place wages come out of.
    has_till = False
    if venue is not None:
        try:
            has_till = venue.attributes.has("register")
        except Exception:  # noqa: BLE001 — unreadable venue: treasury pays
            has_till = False
    if has_till:
        avail = int(venue.db.register or 0)
        # `max(0, ...)` — a NEGATIVE till must not become negative pay.
        # `min(owed, avail)` with a negative `avail` gives a negative
        # `paid`; both money writes below are guarded by `paid > 0` and
        # correctly do nothing, but the final
        # `soul.db.soul_wage_owed = owed_f - paid` is NOT guarded, so a
        # negative `paid` ADDED to the debt. The keeper of an overdrawn
        # venue would accrue phantom debt equal to the overdraft every
        # payday, compounding, while never being paid (#2703).
        paid = max(0, min(owed, avail))
        if paid > 0:
            venue.db.register = avail - paid
    else:
        treasury = get_treasury()
        avail = int(treasury.db.balance or 0)
        paid = max(0, min(owed, avail))   # same guard on the other source
        if paid > 0:
            treasury.db.balance = avail - paid
    if paid > 0:
        soul.tokens = (soul.tokens or 0) + paid
        from world.souls import audit
        audit.coin(soul, paid, "wage")
    # the fractional remainder stays owed — sub-token accrual is never
    # discarded across paydays
    soul.db.soul_wage_owed = owed_f - paid
    return paid


def run_tithe():
    """Sweep a fraction of every venue register back to the treasury.
    Tills are found by tag (indexed) — ShopContainer tags itself at
    creation and build 069 tagged the pre-existing ones."""
    from evennia.utils.search import search_tag

    treasury = get_treasury()
    swept = 0
    for obj in search_tag("till", category="souls"):
        if not obj or not obj.pk:
            continue
        register = int(obj.db.register or 0)
        cut = int(register * TITHE_FRACTION)
        if cut > 0:
            obj.db.register = register - cut
            swept += cut
    if swept:
        treasury.db.balance = int(treasury.db.balance or 0) + swept
    return swept
