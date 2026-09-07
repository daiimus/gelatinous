"""Clear wreck prose from a structure that is intact (#2558).

`mend_structure` restored the stashed sensory layer only `if
db.intact_sensory:`. A structure with no authored
`sensory_contributions` stashes `None`, so the restore was skipped —
while the wreck text had been installed unconditionally and `db.intact`
was set back to `True`. The mast ends up intact and relaying, reading as
wrecked, with no way back: mending again does nothing, because it is
already "intact".

Live: **#5641, the AWE Sentinel-9 repeater mast** — `intact=True`, and
its only sensory line is *"A wrecked antenna mast lists against its cut
guy lines…"*.

The stash is empty, so there is nothing to restore. This CLEARS the
false line rather than inventing a replacement: the structure then
renders with no sensory layer, like the derelict repeater (#6935),
which is neutral where the wreck text is wrong. Authoring branded prose
for it belongs with #2559, not with a data repair.
"""
from evennia.objects.models import ObjectDB
from evennia.utils.dbserialize import deserialize

from commands.CmdBreach import WRECKED_SENSORY

wreck = dict(WRECKED_SENSORY)
fixed = 0
for obj in ObjectDB.objects.all():
    if not obj.attributes.has("intact"):
        continue
    if obj.attributes.get("intact") is not True:
        continue          # genuinely wrecked; the prose is correct
    sens = dict(deserialize(obj.attributes.get("sensory_contributions")) or {})
    if sens != wreck:
        continue
    obj.attributes.add("sensory_contributions", {})
    obj.attributes.remove("intact_sensory")
    obj.attributes.remove("intact_desc")
    fixed += 1
    print(f"  cleared wreck prose from #{obj.id} {obj.key!r}")

print(f"repaired: {fixed}")

remaining = [
    o.id for o in ObjectDB.objects.all()
    if o.attributes.has("intact")
    and o.attributes.get("intact") is True
    and dict(deserialize(o.attributes.get("sensory_contributions")) or {})
    == wreck
]
print(f"intact-but-reading-wrecked remaining: {len(remaining)}")
