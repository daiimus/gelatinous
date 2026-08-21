"""Build 093 — the paper is provisional (#2118).

Wearing the Thawn-Harrison issue now reads as decent-but-not-dressed:
it satisfies modesty, so nobody walks the street bare, but it leaves
a soft pressure that gets replaced on the soul's own time — never
instead of a shift. Marks the already-spawned issue garments.

Idempotent.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/093_provisional_issue.py
"""

from evennia.objects.models import ObjectDB

marked = 0
for obj in ObjectDB.objects.filter(db_key__icontains="Thawn-Harrison"):
    if not obj.attributes.get("coverage") or obj.attributes.get("provisional"):
        continue
    obj.attributes.add("provisional", True)
    marked += 1
print(f"BUILD 093: {marked} issue garments marked provisional")
