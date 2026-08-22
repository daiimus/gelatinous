"""Build 109 — finish the repair build 108 only half did (#2176).

Build 108 selected its targets with

    ObjectDB.objects.filter(db_typeclass_path__icontains="character")

which reads as "every character" and is not. The people in this game
are `LLMNpc`, `Shopkeeper`, `Bartender`, `Doctor` — none of whose
typeclass paths contain the word "character". So the grammar repair
reached 74 bodies and skipped 70 others, including most of the named
cast and every live civilian.

This selects on the thing that actually defines a body: ownership of a
`longdesc` attribute in the `appearance` category. Typeclass is not
consulted at all, so a future people-typeclass cannot be missed the
same way.

Same substitution as 108: bare `{they}` + a present-tense verb becomes
the `{they <verb>}` token, which agrees with the person. Past tense
and modals are invariant and are left alone. Authored prose is touched
only where it is actually broken.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/109_regrammar_every_body.py
"""

import re
from collections.abc import Mapping

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute

SAFE = {
    "could", "would", "should", "might", "must", "can", "will", "shall",
    "fell", "slept", "had", "was", "were", "did", "went", "stopped",
    "left", "kept", "spent", "lost", "found", "made", "took", "saw",
    "learned",
}

MANUAL = {
    "as though {they} usually wear something across half of it":
        "as though {they wear} something across half of it most days",
    "a tic {they} no longer notice":
        "a tic {they have} stopped noticing",
    "the shape of words {they} aren't speaking":
        "the shape of words {they are} not speaking",
}

BRACED = re.compile(r"\{([Tt]hey)\}\s+\{(\w+)\}")
BARE = re.compile(r"\{([Tt]hey)\}\s+([A-Za-z']+)")


def repair(text):
    if not text or "{" not in text:
        return text, False
    original = text
    for before, after in MANUAL.items():
        text = text.replace(before, after)
    text = BRACED.sub(r"{\1 \2}", text)

    def _bare(match):
        pronoun, word = match.group(1), match.group(2)
        if word.lower() in SAFE:
            return match.group(0)
        return "{%s %s}" % (pronoun, word)

    text = BARE.sub(_bare, text)
    return text, text != original


# Every object owning a longdesc, whatever its typeclass.
owner_ids = set(
    Attribute.objects.filter(
        db_key="longdesc", db_category="appearance"
    ).values_list("objectdb__id", flat=True)
)
owner_ids.discard(None)

scanned = fixed = 0
people = []
for obj_id in sorted(owner_ids):
    try:
        body = ObjectDB.objects.get(id=obj_id)
    except ObjectDB.DoesNotExist:
        continue
    longdescs = body.attributes.get("longdesc", category="appearance")
    if not isinstance(longdescs, Mapping) or not longdescs:
        continue
    scanned += 1
    updated = dict(longdescs)
    touched = 0
    for location, text in longdescs.items():
        new_text, changed = repair(str(text) if text else "")
        if changed:
            updated[location] = new_text
            touched += 1
    if touched:
        body.attributes.add("longdesc", updated, category="appearance")
        fixed += touched
        tc = (body.db_typeclass_path or "").split(".")[-1]
        people.append(f"{body.key} (#{body.id}, {tc}) — {touched}")

print(f"BUILD 109: {len(owner_ids)} bodies own a longdesc; "
      f"{scanned} carried one to check")
print(f"BUILD 109: {fixed} slots repaired across {len(people)} bodies")
for line in people[:40]:
    print(f"  {line}")
if len(people) > 40:
    print(f"  ... and {len(people) - 40} more")
if not fixed:
    print("BUILD 109: nothing to do (already repaired)")
