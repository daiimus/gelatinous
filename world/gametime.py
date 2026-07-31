"""
The colony clock — canonical time for Domino's Gambit.

Single source of truth. Anything that needs the hour, the date, or a
timestamp asks here; nothing else should call ``time.localtime()``, because
the container runs UTC and the colony does not.

THREE FACTS, and they are all the spec:

1. **Time runs 1:1 with real time.** No acceleration. An hour is an hour.
   ``TIME_FACTOR = 1.0`` in settings backs this up for Evennia's own
   ``gametime`` helpers.

2. **The colony sits at a fixed UTC-8, and does not observe DST.** It matches
   the owner's winter clock exactly and drifts an hour in summer. That is
   deliberate: a stranded colony has no reason to shift its clocks twice a
   year, and no authority left to tell it to.

3. **The year is real year + 1200.** Today is 3226. Terran Standard Time is
   the Earth calendar the wider network still runs on, and the colony keeps
   it.

   The offset is 1200 rather than a rounder 1000 for one reason: the
   Gregorian calendar repeats on a **400-year cycle**, so only multiples of
   400 preserve the day of the week. +1000 would have kept the month and day
   but silently shifted every weekday, which breaks the moment anything is
   scheduled — a Friday night at the bar that is not Friday for the people
   playing. 1200 keeps month, day AND weekday, so a real date and its TST
   date are the same day in every sense.

Locally, people count from the landing instead: **CY** (Colony Year), zero at
3165 TST. Anything institutional is dated TST; anything the colony wrote
itself tends to be CY. That split is free texture — use it.
"""

from datetime import datetime, timedelta, timezone
import time

# -- the three constants above, in code ---------------------------------

#: Colony offset from UTC. Fixed. No daylight saving, ever.
COLONY_UTC_OFFSET = timedelta(hours=-8)

#: Terran Standard Time is the real calendar, plus this many years.
#: MUST stay a multiple of 400 or weekdays stop matching real ones —
#: see the module docstring, and test_weekday_alignment_depends_on_the_offset.
TST_YEAR_OFFSET = 1200

#: TST year the colony made planetfall — CY 0.
FOUNDING_YEAR_TST = 3165

COLONY_TZ = timezone(COLONY_UTC_OFFSET, name="TST-8")


# -- the clock ----------------------------------------------------------

def _real_utc():
    """Real wall-clock UTC. The one place we read the host clock."""
    return datetime.now(timezone.utc)


def _shift_year(moment):
    """
    Move a datetime forward by the TST offset.

    Uses ``replace`` rather than arithmetic so the month, day, hour and
    weekday are preserved exactly. Feb 29 is the one date that cannot
    survive a year shift onto a non-leap year, so it lands on Mar 1 — the
    alternative (Feb 28) would silently repeat a date.
    """
    try:
        return moment.replace(year=moment.year + TST_YEAR_OFFSET)
    except ValueError:
        return moment.replace(month=3, day=1, year=moment.year + TST_YEAR_OFFSET)


def tst_now():
    """Terran Standard Time — the network's clock. UTC, shifted."""
    return _shift_year(_real_utc())


def colony_now():
    """
    Local time in the colony: TST at a fixed UTC-8.

    This is what a character experiences — what "evening" means, when the
    market opens, whether it is dark.
    """
    return _shift_year(_real_utc().astimezone(COLONY_TZ))


def colony_hour():
    """Current colony hour, 0-23. The hour every other system should use."""
    return colony_now().hour


def colony_year():
    """
    Years since planetfall — CY. Currently 61.

    Returns the *local* reckoning, not TST.
    """
    return tst_now().year - FOUNDING_YEAR_TST


# -- timestamps ---------------------------------------------------------

def stamp():
    """
    A timestamp for storage: real POSIX seconds, UTC.

    Deliberately NOT shifted and NOT localised. Stored time should be a
    plain monotonic number so durations are subtraction and nothing depends
    on a timezone that might change. Shift it on the way out, for display,
    with :func:`format_stamp`.
    """
    return time.time()


def since(stamped, now=None):
    """Seconds elapsed since a :func:`stamp`. Negative clamps to zero."""
    if stamped is None:
        return None
    return max(0.0, (now if now is not None else time.time()) - stamped)


def format_stamp(stamped, with_time=True):
    """Render a stored stamp in colony local time, TST calendar."""
    if stamped is None:
        return "unrecorded"
    moment = _shift_year(
        datetime.fromtimestamp(stamped, timezone.utc).astimezone(COLONY_TZ)
    )
    return moment.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")


def format_now():
    """The current colony time, both reckonings, for display."""
    moment = colony_now()
    return f"{moment.strftime('%Y-%m-%d %H:%M')} TST  (CY {colony_year()})"
