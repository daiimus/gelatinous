"""Build 102 — the pot gets its proper name (#2144).

`kuro` alone is the adjective "black" — a bowl of black, which meant
nothing. The dish is now kuro-nikomi: nikomi being the simmering
itself, and motsu-nikomi (offal stew, built from the cuts nobody would
buy) being the lineage the yard's pot actually belongs to.

"Stew" stays in the name on purpose. Players will not know kuro or
nikomi; they will know stew.

Deliberately noodle-free. Miso-nikomi udon is the famous version, but
noodles cost money and Auntie Lin sells those a few minutes up the
same street — so the free bowl is the one with nothing to chew in it,
and the missing noodles are the poverty, visible in the bowl.

Renames any already-spawned bowls too.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/102_kuro_rename.py
"""

from evennia.objects.models import ObjectDB

NEW_KEY = "a bowl of kuro-nikomi stew"
ALIASES = ["kuro", "nikomi", "kuro-nikomi", "stew", "broth", "bowl", "soup"]

renamed = 0
for bowl in ObjectDB.objects.filter(db_key="a bowl of kuro"):
    bowl.key = NEW_KEY
    bowl.aliases.clear()
    bowl.aliases.add(ALIASES)
    renamed += 1

print(f"BUILD 102: {renamed} bowls renamed; the counter serves "
      f"{NEW_KEY!r} (noodle-free by design)")
