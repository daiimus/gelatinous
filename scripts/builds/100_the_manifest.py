"""Build 100 — everyone gets a berth on the dead chart (#2138).

The cast take the designations the owner red-penned; everyone else
rolls one. Nobody is Command, and nobody is a Commander — both are
reserved, and Command is meant to stay empty. Its story, if it ever
arrives, arrives as ship logs and personal effects rather than as an
officer.

Vesper is skipped on purpose: synthetics were never on a manifest,
and that absence is its own kind of record.

Idempotent: never overwrites a designation already on file.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/100_the_manifest.py
"""

from world import manifest as manifest_mod
from world.souls import engine

CAST = {
    "Nikolai Kasparov": ("medical", "officer"),      # watched the sleepers
    "Marta Okoye": ("medical", "chief"),
    "Petra": ("signals", "chief"),                   # dispatch is the old watch
    "the Rook": ("signals", "officer"),              # the voice of the ship
    "Ossie": ("engineering", "specialist"),
    "Ezra Vantomme": ("logistics", "chief"),         # a pawn counter is a hold
    "Bellows": ("logistics", "specialist"),
    "Sully": ("engineering", "crewman"),             # hull-rated hands
    "Sable Vane": ("life_systems", "crewman"),       # stewarding, near enough
    "Auntie Lin": ("life_systems", "crewman"),       # galley rating
    "Ottilie Krug": ("life_systems", "specialist"),  # galley track
    "Delphine Marchetti": ("signals", "crewman"),    # night watch, then and now
}

authored = rolled = kept = skipped = 0
for soul in engine.get_souls():
    if not soul.pk:
        continue
    if soul.db.designation:
        kept += 1
        continue
    if (soul.db.species or "").lower().startswith("synth") \
            or soul.key == "Vesper":
        skipped += 1
        continue
    if soul.key in CAST:
        dept, rank = CAST[soul.key]
        soul.db.designation = manifest_mod.roll_designation(dept=dept,
                                                            rank=rank)
        authored += 1
    else:
        soul.db.designation = manifest_mod.roll_designation()
        rolled += 1
    soul.db.skills = manifest_mod.seed_skills(soul.db.designation)

print(f"BUILD 100: {authored} authored, {rolled} rolled, {kept} on file, "
      f"{skipped} never listed")
for soul in sorted(engine.get_souls(), key=lambda s: s.key):
    if not soul.pk or not soul.db.designation:
        continue
    rated = ", ".join(
        f"{lbl} [{manifest_mod.letter_for(v)}]"
        for lbl, v in manifest_mod.rated_skills(soul)[:3])
    print(f"    {soul.key:<26}{manifest_mod.designation_line(soul)}")
    print(f"    {'':<26}{rated}")
