"""Build 108 — repair stored longdescs after the verb-agreement fix (#2150).

Fixing the catalogue only fixes people who have not been generated yet.
A longdesc is COPIED onto the character at generation, so every NPC
already walking around still carries the broken prose in
``db.longdesc`` — "she keep", "he have", "she walk".

This rewrites those stored strings onto the ``{they <verb>}`` token,
using the same substitution the catalogue got. Authored prose is
touched only where it is actually broken; a line without a bare
person-subject present-tense verb is left exactly as written.

Past tense and modals are invariant across person and stay legal, so
they are skipped.

Idempotent: a second run finds nothing to do.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/108_regrammar_stored_longdescs.py
"""

import re

from evennia.objects.models import ObjectDB

# Verbs invariant across person — safe on a bare {they}.
SAFE = {
    "could", "would", "should", "might", "must", "can", "will", "shall",
    "fell", "slept", "had", "was", "were", "did", "went", "stopped",
    "left", "kept", "spent", "lost", "found", "made", "took", "saw",
    "learned",
}

# Adverb-first phrasings cannot be fixed mechanically (the token
# conjugates its FIRST word), so they are reworded exactly as the
# catalogue was.
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
    """Return (new_text, changed)."""
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


scanned = fixed_slots = 0
people = []

for char in ObjectDB.objects.filter(db_typeclass_path__icontains="character"):
    longdescs = char.attributes.get("longdesc")
    if not isinstance(longdescs, dict) or not longdescs:
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
        char.attributes.add("longdesc", updated)
        fixed_slots += touched
        people.append(f"{char.key} (#{char.id}) — {touched}")

print(f"BUILD 108: {scanned} described characters scanned")
print(f"BUILD 108: {fixed_slots} longdesc slots repaired "
      f"across {len(people)} people")
for line in people[:25]:
    print(f"  {line}")
if len(people) > 25:
    print(f"  ... and {len(people) - 25} more")
if not fixed_slots:
    print("BUILD 108: nothing to do (already repaired)")
