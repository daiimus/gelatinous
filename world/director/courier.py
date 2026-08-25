"""The rabbit — packages across the colony (#2258).

A courier is the one job that exercises everything at once: pathfinding,
verticality, `route_taste`, the crane, tills, and the shift clock. That
is the point of her. She is a WORKING INSTRUMENT — when a new route,
a piece of parkour gear or a bit of cyberware lands, she is the NPC who
proves it works by using it all day.

The loop, per the owner (2026-08-24):

    wait at Kaspar  →  take a package  →  cross the city
                    →  hand it to an employee  →  collect on delivery
                    →  come home and wait for the next run

Three rulings shape it:

* **Payment is 1 token.** Testing scale, deliberately. She runs all
  shift; at a realistic fee she would strip every till in the colony
  inside a day.
* **She delivers to a PERSON**, so a run only targets a counter with
  somebody standing at it. Destinations therefore change as shifts
  rotate, which is free variety nobody has to author.
* **If the till is dry the delivery still lands** and is logged unpaid.
  Eight of the colony's ten tills held zero the day this was written,
  so subsidising her would have hidden that. Instead she measures it:
  an unpaid run emits the `till_empty` signal the intelligence bus
  already understands.
"""
from typing import Any

#: Testing scale. See the module docstring before raising this.
FEE = 1

#: Where the register lives on a counter (the butcher's till loop, #2233).
REGISTER = "register"


def _counter_in(room: Any):
    """The till-bearing counter in *room*, or None."""
    for obj in getattr(room, "contents", None) or ():
        if obj.attributes.has(REGISTER) and obj.destination is None:
            return obj
    return None


def _keeper_in(room: Any, exclude=None):
    """The person on duty in *room* right now, or None.

    Asks the POST who holds the running shift rather than scanning the
    room and interrogating each body — `on_duty_keeper` is the
    primitive that already knows, and it is the same one the succession
    sweep trusts.

    Then checks they are actually STANDING here. Being rostered and
    being present are different questions, and a package can only be
    handed to the second kind.
    """
    from world.souls import posts as posts_mod
    for post in list(getattr(room, "contents", None) or ()) + [room]:
        if post is exclude or getattr(post, "destination", None) is not None:
            continue
        if not getattr(getattr(post, "db", None), "post_slots", None):
            continue
        try:
            keeper = posts_mod.on_duty_keeper(post)
        except Exception:  # noqa: BLE001 — unreadable roster: skip it
            continue
        if keeper is None or keeper is exclude or not keeper.pk:
            continue
        if keeper.location is not room:
            continue          # rostered but not here — nobody to hand it to
        try:
            if keeper.is_dead():
                continue
        except Exception:  # noqa: BLE001
            pass
        return keeper
    return None


def runnable_destinations(soul: Any) -> list:
    """Every ``(room, counter, keeper)`` a run could target right now.

    Excludes the courier's own post — carrying a package across the
    room is not a run.
    """
    from evennia.objects.models import ObjectDB
    out = []
    home = getattr(soul.db, "soul_post", None)
    home_room = home if getattr(home, "contents", None) is not None \
        else getattr(home, "location", None)
    for counter in ObjectDB.objects.filter(
            db_attributes__db_key=REGISTER).distinct():
        room = counter.location
        if room is None or room is home_room:
            continue
        keeper = _keeper_in(room, exclude=soul)
        if keeper is None:
            continue
        out.append((room, counter, keeper))
    return out


def hand_over(soul: Any, counter: Any, package: Any = None) -> dict:
    """Give the package over and take the fee. Returns a small report.

    Order matters: the package changes hands FIRST. A courier who
    refuses to release a parcel because the till is short is a
    different, worse character — and the whole point of letting the
    delivery land unpaid is that the debt becomes visible instead of
    the errand failing.
    """
    out = {"delivered": False, "paid": 0, "short": False}
    room = counter.location if counter is not None else None
    keeper = _keeper_in(room, exclude=soul) if room else None

    if package is not None and package.pk:
        target = keeper if keeper is not None else counter
        try:
            package.move_to(target, quiet=True, move_hooks=False)
            out["delivered"] = True
        except Exception:  # noqa: BLE001 — a stuck parcel is not a crash
            pass

    till = int(counter.attributes.get(REGISTER, 0) or 0)
    if till >= FEE:
        counter.attributes.add(REGISTER, till - FEE)
        soul.tokens = (soul.tokens or 0) + FEE
        out["paid"] = FEE
    else:
        out["short"] = True
        # The colony saying it cannot pay for its own errands. The bus
        # already knows this signal; nothing else had to be invented.
        try:
            from world import wsis
            wsis.emit("till_empty", room, note=getattr(counter, "key", ""))
        except Exception:  # noqa: BLE001 — observation never blocks work
            pass
    return out


# ---------------------------------------------------------------------
# The crane (#2301)
#
# The Longhaul container is a moving room: it docks level with the
# Kaspar Urgent Care roof at level 2 (the boarding point) and reaches
# the Queen of Cups rack roof at level 12. Both ends are ROOFTOPS, so
# the only souls it is any use to are the ones who walk roofs -- which
# in this colony is currently one person.
#
# She does not operate it. She ASKS, on band 27.0, and the console
# answers in Ossie's voice or does not. That is the whole point: an NPC
# changing the world so that it can path through it, using the same
# radio a player would key.
# ---------------------------------------------------------------------

CRANE_BAND = "27.0"


def _crane_car(soul):
    """The crane container, if this soul is somewhere it matters."""
    from typeclasses.rooms import CraneContainer
    here = getattr(soul, "location", None)
    if isinstance(here, CraneContainer):
        return here, "aboard"
    # standing at the dock: the car's boarding roof
    from evennia.objects.models import ObjectDB
    for room in ObjectDB.objects.all():
        if not isinstance(room, CraneContainer):
            continue
        dock = room._room_at(room.UC_ROOF)
        if dock is not None and dock is here:
            return room, "dock"
        break
    return None, None


def crane_level_wanted(soul):
    """The level she needs the car at, or None if she needs nothing.

    Deliberately inferred from WHERE SHE IS STANDING rather than from
    route introspection:

    * on the boarding roof with the car elsewhere — she wants it down;
      nobody stands on that roof for the view.
    * aboard, below the Queen's level — she wants it up; the only
      reason to board is to cross at the top.
    """
    car, where = _crane_car(soul)
    if car is None:
        return None
    level = int(getattr(car.db, "level", car.MIN_Z) or car.MIN_Z)
    if where == "dock":
        return None if level == car.MIN_Z else car.MIN_Z
    if where == "aboard":
        return None if level == car.QOC_Z else car.QOC_Z
    return None


def call_the_crane(soul, level) -> bool:
    """Key the handset and ask for a level. True if she transmitted.

    Uses the REAL verb on a REAL carried radio, so the console hears it
    exactly as it hears a player — no back door, and the operator can
    refuse, be absent, or ask her to confirm.
    """
    from world.radio import is_radio
    handset = next((o for o in soul.contents if is_radio(o)), None)
    if handset is None:
        return False
    if not handset.attributes.get("radio_on"):
        soul.execute_cmd(f"toggle {handset.key} on")
    if str(handset.attributes.get("frequency") or "") != CRANE_BAND:
        soul.execute_cmd(f"tune {handset.key} to {CRANE_BAND}")
    soul.execute_cmd(f"xmit Ossie, Rabbit. Bring the box to {level}.")
    return True
