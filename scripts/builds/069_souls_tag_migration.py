"""Build 069 — tag migration for the souls query-hygiene pass (P3).

Tags are the indexed lookup path; attribute-key joins and typeclass
icontains scans are not. This tags what already exists:

 * every object carrying `db.advertises` -> ("advertiser", souls)
 * every ShopContainer -> ("till", souls) — new ones self-tag at
   creation from now on (typeclasses/shopkeeper.py)

Idempotent: tags.add is a no-op when present.

Run: docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
         < scripts/builds/069_souls_tag_migration.py
"""

from evennia.objects.models import ObjectDB

from typeclasses.shopkeeper import ShopContainer

ads = 0
for obj in ObjectDB.objects.filter(db_attributes__db_key="advertises"):
    if obj.db.advertises:
        obj.tags.add("advertiser", category="souls")
        ads += 1
        print(f"  advertiser: {obj.key} (#{obj.id})")

tills = 0
for counter in ShopContainer.objects.all():
    if counter.pk:
        counter.tags.add("till", category="souls")
        tills += 1
        print(f"  till: {counter.key} (#{counter.id})")

print(f"BUILD 069: tagged {ads} advertisers, {tills} tills")
