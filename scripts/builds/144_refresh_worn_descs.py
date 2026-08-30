"""Build 144 — push the rewritten worn descriptions onto items already in play.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/144_refresh_worn_descs.py
    then a foreground reload.

`worn_desc` is STAMPED onto an object when it spawns. Rewriting a prototype
changes nothing that already exists, so after #2400/#2402/#2404 the live world
held 436 garments still carrying the old caption text and 22 carrying the new —
the 22 being ones respawned by hand during testing. Every garment on an NPC or
a shop shelf was untouched.

SAFETY: this only overwrites an attribute that still EXACTLY matches what the
prototype said before the rewrite. Anything else — a builder's hand-authored
description, an item customised in play — differs from the old text and is left
alone. The old text is read out of git rather than guessed, so "unchanged since
spawn" is a fact rather than an assumption.

Re-run-safe: a second run finds nothing left matching the old text.
"""
from evennia.objects.models import ObjectDB

#: Historical prototype files, staged through the bind mount by the operator:
#:
#:     git show 0fca3bf6:world/prototypes.py > game/.mudlogs/old_protos2.py
#:     git show 454ea4e1:world/prototypes.py > game/.mudlogs/old_protos.py
#:
#: TWO generations, not one. Objects in the world predate different fixes: some
#: were spawned before #2396 tokenised the literal `their`, others between that
#: and the rewrite. Checking a single baseline mislabelled the older ones as
#: hand-customised and would have left 7 of them stale forever. (There is no
#: git inside the container, hence files rather than `git show` in-process.)
GENERATIONS = (
    "/usr/src/game/.mudlogs/old_protos2.py",   # pre-#2396
    "/usr/src/game/.mudlogs/old_protos.py",    # pre-#2400
    "/usr/src/game/.mudlogs/old_protos3.py",   # pre-{they move} fix
)


def _load(path):
    ns: dict = {}
    exec(compile(open(path).read(), "<old_prototypes>", "exec"), ns)
    return ns


old_gens = [_load(p) for p in GENERATIONS]

from world import prototypes as new_mod  # noqa: E402


def _attrs(proto):
    return dict(proto.get("attrs") or []) if isinstance(proto, dict) else {}


# ---- 2. walk everything that came from a prototype ----------------------
updated_desc = 0
updated_styles = 0
skipped_custom = 0
already_current = 0

for obj in ObjectDB.objects.all():
    if obj.attributes.get("worn_desc") is None:
        continue
    tags = [t.db_key for t in obj.tags.all(return_objs=True)
            if t.db_category == "from_prototype"]
    if not tags:
        continue
    key = tags[0].upper()
    new_proto = getattr(new_mod, key, None)
    if not isinstance(new_proto, dict):
        continue
    new_a = _attrs(new_proto)
    olds = [_attrs(g[key]) for g in old_gens if isinstance(g.get(key), dict)]

    # --- worn_desc ---
    new_wd = new_a.get("worn_desc")
    known_old = {o.get("worn_desc") for o in olds}
    known_old.discard(None)
    known_old.discard(new_wd)
    if new_wd is not None and known_old:
        current = obj.attributes.get("worn_desc")
        if current == new_wd:
            already_current += 1
        elif current in known_old:
            obj.attributes.add("worn_desc", new_wd)
            updated_desc += 1
        else:
            skipped_custom += 1

    # --- style_configs (the per-state desc_mods were rewritten too) ---
    from evennia.utils.dbserialize import deserialize
    new_sc = new_a.get("style_configs")
    old_scs = [o.get("style_configs") for o in olds]
    old_scs = [x for x in old_scs if x is not None and x != new_sc]
    if new_sc is not None and old_scs:
        current = deserialize(obj.attributes.get("style_configs"))
        if any(current == x for x in old_scs):
            obj.attributes.add("style_configs", new_sc)
            updated_styles += 1

print(f"worn_desc updated     : {updated_desc}")
print(f"style_configs updated : {updated_styles}")
print(f"already current       : {already_current}")
print(f"left alone (customised): {skipped_custom}")
