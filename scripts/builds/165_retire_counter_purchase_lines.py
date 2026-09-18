"""Retire the counters' authored purchase lines (#3413).

Every counter type seeded ``purchase_msg_buyer`` / ``purchase_msg_room``,
and three counters (Lin's noodle cart, the Escallier snailery counter,
the butcher's cart) carried authored ones. On a staffed counter they
could never print: the buy command hands the item over through the
keeper and returns before reading them. Serve flavour now lives on the
ITEM (``serve_line`` on the dish prototypes) and the attributes are
retired from the code, so strip them from the live objects too.

Run once:
    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' < scripts/builds/165_retire_counter_purchase_lines.py

DEFAULTS TO A CENSUS. Set PURGE = True to write. Idempotent: an object
without the attributes is left alone.
"""
from evennia.objects.models import ObjectDB

PURGE = False

ATTRS = ("purchase_msg_buyer", "purchase_msg_room")
carriers = [
    obj for obj in ObjectDB.objects.filter(db_attributes__db_key__in=list(ATTRS)).distinct()
    if any(obj.attributes.has(a) for a in ATTRS)
]
print(f"BUILD 165 census: {len(carriers)} objects carry a retired purchase line: "
      f"{[(o.key, o.id) for o in carriers]}")
if PURGE:
    for obj in carriers:
        for attr in ATTRS:
            if obj.attributes.has(attr):
                obj.attributes.remove(attr)
    print(f"BUILD 165: stripped {len(carriers)} objects")
else:
    print("BUILD 165: census only (PURGE = False)")
