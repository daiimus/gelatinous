"""Build 112 — Ossie works a shift, and the cab is a post (#2214).

Ossie has been standing in the crane cab permanently: no soul, no
home, no schedule, and — the part that matters — no POST, so nothing
in the world knows the cab is a job somebody holds.

Ensouling him naively would have been worse than leaving him. He
transmits through a SEATED base station (`active_transmit_radio`:
worn radio -> held radio -> seated console), and he carries no radio.
Standing up is going off the air, and band 27.0 is how the colony
drives a crane whose container is a MOVING ROOM. A hunger tick at the
wrong moment strands whoever is riding it.

So: the cab is a registered post with a DAY shift, and off-shift the
band simply does not answer. That is what a real crane does, and it
gives "call back at six" as texture rather than a bug.

Deliberately NOT a `successor` post. The crane parsing lives in the
`CraneOperator` typeclass, not in the post — a stranger promoted into
the chair would be a plain LLMNpc and the crane would ignore them.
Policy stays unset, which the sweep reads as "the owner has not
decided" and leaves dark rather than hiring somebody who cannot drive.

Relief operators on swing and night are a content decision (two more
named bioroids, or none), and are left to the owner.

Ossie is a synth, so `profile_name()` gives him the synth dials
automatically — 16h to hunger, 24h to rest — which means he leaves the
chair about half as often as a human would.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/112_ossie_works_a_shift.py
"""

from evennia.utils.search import search_object

from world import rental
from world.souls import engine, posts as posts_mod

OSSIE = "#7401"

ossie = next(iter(search_object(OSSIE)), None)
if ossie is None or not ossie.pk:
    print("BUILD 112: Ossie not found; aborted")
else:
    cab = ossie.location
    console = next(
        (o for o in (cab.contents if cab else [])
         if getattr(o.db, "is_base_station", None) is True), None)
    chair = next(
        (o for o in (cab.contents if cab else [])
         if "chair" in (o.key or "").lower()), None)

    if cab is None or console is None:
        print("BUILD 112: cab or console missing; aborted")
    elif ossie.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
        print("BUILD 112: Ossie already has a soul; skipped")
    else:
        # A home he can actually walk to — the Queen of Cups is the
        # tower the crane docks level with at floor 13.
        home = rental.residence_of(ossie)
        if home is None:
            terminal = next(
                (o for o in search_object("rental terminal")
                 if o.pk and o.location
                 and "Queen of Cups" in o.location.key), None)
            if terminal is not None:
                try:
                    rental.assign_cube(ossie, terminal)
                    home = rental.residence_of(ossie)
                except Exception as err:      # noqa: BLE001
                    print(f"BUILD 112: no cube for him ({err})")

        ossie.db.is_npc = True
        ossie.db.essential = True          # authored, not disposable

        engine.ensoul(ossie, role="crane_operator", home=home,
                      post=cab, schedule="day", wage_rate=0.02,
                      venue=console)

        # The cab becomes a POST — one shift, no policy. Off-shift the
        # band goes unanswered, which is the honest behaviour.
        posts_mod.register_post(
            console, role="crane_operator", schedule="day",
            wage_rate=0.02, policy=None, keeper=ossie, shifts=("day",))

        print(f"BUILD 112: {ossie.key} ensouled — day shift at "
              f"{cab.key}, home {home.key if home else 'none'}")
        print(f"BUILD 112: {console.key} registered as a post "
              f"(day only, policy unset)")
        if chair is not None:
            print(f"BUILD 112: he transmits from {chair.key}; off-shift "
                  f"band 27.0 does not answer")
