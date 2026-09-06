"""Build 149 — recover the bleeder identity on 326 blood incidents (#2420).

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/149_backfill_blood_sleeve_uids.py
    then a foreground reload.

`sleeve_uid` is an `AttributeProperty(category="identity")`, so
`character.db.sleeve_uid` reads a DIFFERENT ROW and is always None on a
Character. `MedicalScript` recorded every bleeding incident through that
`.db` read, so all 326 incidents in the world carry `sleeve_uid=None` and
not one carries a real UID. The forensic source-count then fell into its
legacy branch and de-duplicated on the raw character key instead of the
body-identity axis -- two bleeders sharing a key read as one source.

THE EVIDENCE IS NOT LOST. The same code captured a `signature` tuple two
lines later through `get_identity_signature`, which reads the PROPERTY
correctly -- and `signature[0]` is documented as "the character's real
`sleeve_uid`". All 326 incidents carry a signature. So the dedicated
field can be recovered exactly rather than guessed: this copies
`signature[0]` into `sleeve_uid` and invents nothing.

An incident with no signature, or a signature whose first element is
falsy, is LEFT ALONE and counted. A forensic record is evidence; a
plausible value filled into it would be worse than an empty one.

Re-run-safe: an incident that already has a `sleeve_uid` is skipped.
"""
from evennia.objects.models import ObjectDB


def main():
    pools = [o for o in ObjectDB.objects.all()
             if o.attributes.get("is_blood_pool")]
    print(f"BUILD 149: {len(pools)} blood pools")

    seen = filled = already = unrecoverable = 0
    for pool in pools:
        incidents = pool.attributes.get("bleeding_incidents") or []
        rebuilt = []
        changed = False
        for inc in incidents:
            entry = dict(inc)
            seen += 1
            if entry.get("sleeve_uid"):
                already += 1
                rebuilt.append(entry)
                continue
            sig = entry.get("signature")
            uid = None
            try:
                uid = sig[0] if sig else None
            except (TypeError, IndexError, KeyError):
                uid = None
            if uid:
                entry["sleeve_uid"] = uid
                filled += 1
                changed = True
            else:
                unrecoverable += 1
            rebuilt.append(entry)
        if changed:
            pool.attributes.add("bleeding_incidents", rebuilt)
            print(f"BUILD 149:   #{pool.id} {pool.key[:26]:26} "
                  f"{len(incidents)} incidents updated")

    print(f"BUILD 149: {seen} incidents seen, {filled} recovered, "
          f"{already} already had one, {unrecoverable} left empty")

    still = 0
    for pool in ObjectDB.objects.all():
        if not pool.attributes.get("is_blood_pool"):
            continue
        for inc in (pool.attributes.get("bleeding_incidents") or []):
            if not inc.get("sleeve_uid"):
                still += 1
    print(f"BUILD 149: incidents still without a bleeder: {still}")


main()
