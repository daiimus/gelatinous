"""Build 138 — ensoul the ambient crowd (#2362).

The population merge. Forty `LLMNpc` civilians drift the streets on
director patrol beats with personas and no interior: no needs, no post,
no wage, never hungry, never tired, never paid. They are scenery that
talks.

STAGED ON PURPOSE. Run it repeatedly with a small LIMIT and watch the
souls audit log between runs. Forty new bodies dropped into the band
tree at once would be forty new fault sources with no way to tell which
one caused what; five at a time, the log stays readable and a bad
interaction is obvious while it is still small.

Each civilian gets:
  * a real cube through the real kiosk (`rental.assign_cube`) — `rest`
    returns None with no home, and a soul that cannot plan rest faults
    every night forever
  * `soul_home` from the tenancy that produced, so the door grant and
    the soul agree about where they live
  * their existing director `role` carried across as `soul_role`, so a
    ganger stays a ganger

They KEEP their patrol beat. `routines.is_patrol_idle` already yields to
`soul_job`, so patrol becomes the idle filler it was always documented
as rather than a second driver fighting for the body.

Idempotent: an already-ensouled civilian is skipped, and a civilian who
already holds a residence is not re-housed.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/138_ensoul_the_crowd.py
"""

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object

from typeclasses.characters import Character
from world import rental
from world.souls import engine

#: How many to ensoul per run. Small on purpose — see the module docstring.
LIMIT = 5

#: The kiosks, in the order we fill them. Spread rather than stacking the
#: whole crowd into one tower: a colony where every drifter lives in the
#: Brackett is a colony with one neighbourhood.
KIOSK_DBREFS = ("#5640", "#5068", "#7132")   # Brackett, Queen of Cups, Halcyon


def _kiosks():
    out = []
    for ref in KIOSK_DBREFS:
        k = next(iter(search_object(ref)), None)
        if k is not None and k.pk and k.db.cubes:
            out.append(k)
    return out


def _crowd():
    """Unsouled ambient civilians, oldest first so runs are repeatable."""
    out = []
    for obj in ObjectDB.objects.all():
        try:
            if not isinstance(obj, Character):
                continue
        except Exception:  # noqa: BLE001
            continue
        if obj.db_account_id:
            continue
        if not obj.tags.get("civilian", category="director"):
            continue
        if obj.tags.get(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1]):
            continue
        if obj.location is None:
            continue
        out.append(obj)
    return sorted(out, key=lambda o: o.id)


kiosks = _kiosks()
if not kiosks:
    print("BUILD 138: no rental kiosk found — nothing done.")
else:
    crowd = _crowd()
    print(f"BUILD 138: {len(crowd)} unsouled civilians standing; "
          f"taking {min(LIMIT, len(crowd))}.")
    housed = ensouled = skipped = 0
    for index, npc in enumerate(crowd[:LIMIT]):
        home = rental.residence_of(npc)
        if home is None:
            kiosk = kiosks[index % len(kiosks)]
            ok, msg = rental.assign_cube(npc, kiosk)
            if not ok:
                print(f"BUILD 138: {npc.key[:22]:22} NO CUBE — {msg}")
                skipped += 1
                continue
            home = rental.residence_of(npc)
            housed += 1
        if home is None:
            print(f"BUILD 138: {npc.key[:22]:22} cube claimed but no "
                  f"residence resolved — skipped")
            skipped += 1
            continue
        # Their director role IS their role; a ganger who becomes a
        # "resident" the moment they get an interior would be a
        # different person.
        role = str(npc.db.role or "resident")
        engine.ensoul(npc, role=role, home=home, post=None,
                      schedule="day", wage_rate=0.0)
        ensouled += 1
        print(f"BUILD 138: {npc.key[:22]:22} role={role:<10} "
              f"home={home.key}")

    print(f"BUILD 138: ensouled={ensouled} housed={housed} "
          f"skipped={skipped}; {len(crowd) - ensouled} still to go.")
    print("BUILD 138: watch souls_audit.log before the next run.")
