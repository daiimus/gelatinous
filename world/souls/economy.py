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


def get_treasury():
    existing = ScriptDB.objects.filter(db_key=TREASURY_KEY).first()
    if existing:
        return existing
    script = create_script(key=TREASURY_KEY, persistent=True, autostart=False)
    script.db.balance = 0
    return script


def balance():
    return int(get_treasury().db.balance or 0)


def pay_wage(soul):
    """Convert accrued wage_owed into real tokens at shift end.

    Owner rule: venue posts are paid out of their own till
    (`soul.db.soul_venue.db.register`); non-venue posts draw colony
    treasury. Partial payment when the source is short — a drought is a
    visible state (`@soul` shows the unpaid balance), not a crash.
    """
    owed_f = float(soul.db.soul_wage_owed or 0.0)
    owed = int(owed_f)               # whole tokens payable now
    if owed <= 0:
        return 0
    venue = soul.db.soul_venue
    if venue is not None:
        avail = int(venue.db.register or 0)
        paid = min(owed, avail)
        if paid > 0:
            venue.db.register = avail - paid
    else:
        treasury = get_treasury()
        avail = int(treasury.db.balance or 0)
        paid = min(owed, avail)
        if paid > 0:
            treasury.db.balance = avail - paid
    if paid > 0:
        soul.tokens = (soul.tokens or 0) + paid
    # the fractional remainder stays owed — sub-token accrual is never
    # discarded across paydays
    soul.db.soul_wage_owed = owed_f - paid
    return paid


def run_tithe():
    """Sweep a fraction of every venue register back to the treasury."""
    from typeclasses.shopkeeper import ShopContainer
    from evennia.objects.models import ObjectDB

    treasury = get_treasury()
    swept = 0
    for obj in ObjectDB.objects.filter(
            db_typeclass_path__icontains="shopkeeper"):
        if not isinstance(obj, ShopContainer):
            continue
        register = int(obj.db.register or 0)
        cut = int(register * TITHE_FRACTION)
        if cut > 0:
            obj.db.register = register - cut
            swept += cut
    if swept:
        treasury.db.balance = int(treasury.db.balance or 0) + swept
    return swept
