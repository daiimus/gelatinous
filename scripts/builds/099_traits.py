"""Build 099 — give the colony personalities (#2134).

The cast get the traits the owner red-penned; everyone else rolls two
or three, exclusion-safe. From this point two broke lawless souls are
no longer interchangeable knives: one of them may be Soft-Handed, and
will go to bed hungry rather than rob, right up until starving
changes her mind.

Idempotent: never overwrites traits already set.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/099_traits.py
"""

from world.souls import engine
from world.souls import traits as traits_mod

CAST = {
    "Bellows": ["rivet_tight", "plate_nerved"],
    "Sable Vane": ["antenna_up", "dry_circuit"],
    "Sully": ["rustgut", "open_valve"],
    "Delphine Marchetti": ["dark_adapted", "faraday_souled"],
    "Auntie Lin": ["shift_hound", "rivet_tight"],
    "Ottilie Krug": ["ration_burner", "shift_hound"],
    "Nikolai Kasparov": ["greenhaus_handed", "plate_nerved"],
    "Marta Okoye": ["greenhaus_handed", "dark_adapted"],
    "Petra": ["plate_nerved", "dark_adapted"],
    "Ezra Vantomme": ["rivet_tight", "grudge_etched"],
    "the Rook": ["wire_loved"],
}

authored = rolled = kept = 0
for soul in engine.get_souls():
    if not soul.pk:
        continue
    if soul.db.soul_traits:
        kept += 1
        continue
    if traits_mod.registry_for(soul) is traits_mod.DEFECTS:
        soul.db.soul_traits = []      # machines EARN theirs; see #2136
        continue
    if soul.key in CAST:
        soul.db.soul_traits = list(CAST[soul.key])
        authored += 1
    else:
        soul.db.soul_traits = list(traits_mod.roll())
        rolled += 1

print(f"BUILD 099: {authored} authored, {rolled} rolled, {kept} already set")
for soul in sorted(engine.get_souls(), key=lambda s: s.key):
    if not soul.pk:
        continue
    ab, re_ = traits_mod.ethos(soul)
    line = ", ".join(traits_mod.labels(soul)) or "—"
    tail = ""
    if ab:
        tail += f"  abhors {'/'.join(sorted(ab))}"
    if re_:
        tail += f"  relishes {'/'.join(sorted(re_))}"
    print(f"    {soul.key:<28}{line}{tail}")
