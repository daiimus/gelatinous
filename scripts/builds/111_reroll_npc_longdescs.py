"""Build 111 — re-roll generated NPC longdescs onto the curated catalogue.

The catalogue was curated (#2167), tagged by build (#2169), and
expanded across human, synth and robot (#2171, #2173). None of that
reaches anybody already standing in a room: a longdesc is COPIED onto
the body when it is generated, so the existing cast still wears the
old template prose — forty-two ways of saying "{Their} {thighs}
{bear}" — and none of it is build-matched, so a heavyset civilian can
still be described as thin.

This re-rolls them. Rules:

* **NPCs only.** `db.is_npc` gates it. Players keep their bodies.
* **Generated prose only.** A slot is rewritten only if its current
  text appears in the catalogue — the one shipping now, or the one in
  git before the curation began. Anything else is somebody's writing
  and is left exactly alone. That is what protects the named cast:
  Sable's feline amber eyes, Delphine's weathered face, Kasparov's
  hollow cheeks were all hand-written and none of them match.
* **Build-aware.** Selection goes through `random_longdesc(...,
  build=)`, so tagged lines only reach bodies they fit.
* **Species-aware.** Rats, robots and synths draw their own tables.

Idempotent in the sense that matters: running twice re-rolls again
(the prose is random), but it will never consume authored text, and it
never touches a slot it did not recognise.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/111_reroll_npc_longdescs.py
"""

import ast
import glob
import os
from collections.abc import Mapping

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute

from world import mob_flavor
from world.anatomy import get_species_pair_keys

#: Where the pre-curation catalogue was staged for comparison. Absent
#: on a normal run — then only the CURRENT catalogue is recognised,
#: which is the conservative direction (fewer rewrites, never more).
LEGACY_DIR = "/tmp/oldcat"


def _flatten(table):
    out = set()
    for entries in (table or {}).values():
        if isinstance(entries, dict):
            entries = [ln for v in entries.values() for ln in v]
        for entry in entries or ():
            out.add(entry[1] if isinstance(entry, tuple) else entry)
    return out


def _known_lines():
    """Every line the game has ever generated, current and pre-curation."""
    known = set()
    for table in mob_flavor._LONGDESCS_BY_SPECIES.values():
        known |= _flatten(table)
    for path in sorted(glob.glob(os.path.join(LEGACY_DIR, "*.py"))):
        try:
            tree = ast.parse(open(path).read())
        except Exception:  # noqa: BLE001 — a bad staged file is not fatal
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(value, dict):
                known |= _flatten(value)
            elif isinstance(value, list):
                known |= {v for v in value if isinstance(v, str)}
    return known


KNOWN = _known_lines()
print(f"BUILD 111: {len(KNOWN)} catalogue lines recognised as generated")

owner_ids = set(
    Attribute.objects.filter(
        db_key="longdesc", db_category="appearance"
    ).values_list("objectdb__id", flat=True)
)
owner_ids.discard(None)

bodies = rerolled = authored_kept = 0
touched = []

for obj_id in sorted(owner_ids):
    try:
        body = ObjectDB.objects.get(id=obj_id)
    except ObjectDB.DoesNotExist:
        continue
    if not body.attributes.get("is_npc"):
        continue
    longdescs = body.attributes.get("longdesc", category="appearance")
    if not isinstance(longdescs, Mapping) or not longdescs:
        continue

    bodies += 1
    # db.species (UNCATEGORISED) is the real one — every consumer reads
    # it (`apply_random_flavor`, `_get_visible_body_descriptions`). The
    # categorised `species` AttributeProperty is never written and always
    # returns its "human" default, which is how synths and robots got
    # human bodies on the first run (#2196).
    species = body.db.species or "human"
    sex = getattr(body, "sex", None)
    build = getattr(body, "build", None)
    updated = dict(longdescs)

    # Paired locations re-roll TOGETHER so left and right keep matching.
    pair_of = {}
    for pair_key, (left, right) in get_species_pair_keys(species).items():
        pair_of[left] = pair_key
        pair_of[right] = pair_key

    drawn = {}
    changed = 0
    for location, text in longdescs.items():
        text = str(text or "")
        if not text:
            continue
        if text not in KNOWN:
            authored_kept += 1
            continue
        slot = pair_of.get(location, location)
        if slot not in drawn:
            line = mob_flavor.random_longdesc(
                slot, species, sex=sex, build=build)
            drawn[slot] = line
        line = drawn[slot]
        if line and line != text:
            updated[location] = line
            changed += 1

    if changed:
        body.attributes.add("longdesc", updated, category="appearance")
        rerolled += changed
        touched.append(f"{body.key} (#{body.id}, {species}/{build}) "
                       f"— {changed}")

print(f"BUILD 111: {bodies} NPC bodies scanned")
print(f"BUILD 111: {rerolled} slots re-rolled across {len(touched)} bodies")
print(f"BUILD 111: {authored_kept} authored slots left untouched")
for line in touched[:30]:
    print(f"  {line}")
if len(touched) > 30:
    print(f"  ... and {len(touched) - 30} more")
if not rerolled:
    print("BUILD 111: nothing to do")
