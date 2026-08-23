"""Build 118 — collapse duplicate memories, and forget one lie (#2242).

Two kinds of damage, both from appending memories without ever asking
whether the NPC already had them.

**Duplicates.** A soul stuck in a retrying travel fault stored the same
sentence every time it failed. The dispatcher held 29 byte-identical
copies of "nothing to eat I could reach or afford" inside a per-subject
cap of 30 — so prune spent its whole budget on one line and genuinely
forgot everything else to keep it. Collapsing them to one record keeps
the memory and returns the budget; the survivor carries the combined
`uses` count, because a thing that happened thirty times IS strongly
remembered.

**A fabrication that became canon.** An NPC's own reply is stored as a
memory, retrieved by similarity, and handed back to the model as
context. The dispatcher invented a suspect description — "white male
inside welfare gate. Browsing casual clothing." — and from then on the
same call retrieved her own invention and she recited it, storing the
recitation each time. The register forbidding invention could not win
against her own memory of having invented it.

Code-side dedup (`memory.remember`) stops both going forward. This
clears what is already written.

Idempotent. Reports per-NPC so the scale of the spam is visible.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/118_forget_the_spam_and_the_lie.py
"""

from evennia.objects.models import ObjectDB

#: Text that is a KNOWN fabrication rather than a memory — forgotten
#: outright, not merged. Kept narrow and literal on purpose: this
#: deletes an NPC's recollection, and guessing is worse than leaving it.
LIES = ("white male inside welfare gate",)


def _norm(text):
    return " ".join(str(text or "").split())


holders = [o for o in ObjectDB.objects.filter(
    db_attributes__db_key="llm_memories").distinct()]
print(f"BUILD 118: {len(holders)} NPCs carry memories")

for npc in holders:
    recs = list(npc.db.llm_memories or [])
    if not recs:
        continue
    merged, seen, forgotten = [], {}, 0
    for rec in recs:
        text = _norm(rec.get("text"))
        if any(lie in text for lie in LIES):
            forgotten += 1
            continue
        key = (rec.get("subject", ""), text)
        first = seen.get(key)
        if first is None:
            seen[key] = rec
            merged.append(rec)
            continue
        # the same memory, recalled again — strengthen it, don't clone it
        first["uses"] = first.get("uses", 0) + rec.get("uses", 0) + 1
        first["last_seen"] = max(first.get("last_seen", 0) or 0,
                                 rec.get("last_seen", 0) or 0)

    if len(merged) == len(recs) and not forgotten:
        continue
    npc.db.llm_memories = merged
    print(f"BUILD 118: {npc.key} #{npc.id}: {len(recs)} -> {len(merged)} "
          f"({len(recs) - len(merged) - forgotten} duplicates collapsed"
          f"{f', {forgotten} fabrication(s) forgotten' if forgotten else ''})")

print("BUILD 118: done")
