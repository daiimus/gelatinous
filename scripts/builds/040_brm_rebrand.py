"""Build 040 — rebrand the crane: Boiler Run Mechanics (BRM), model S-2.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/040_brm_rebrand.py
    then a foreground reload.

Owner: the maker is Boiler Run Mechanics (BRM); the crane is the S-2,
"Stationary Model 2". Mast decks take the short tag "BRM S-2 Crane -
Mast (Deck #)"; the cab takes the full "Boiler Run Mechanics S-2 Crane -
Operator Cab". Carry the brand through the descriptions, the console, the
vest, Ossie's persona, and the channel signage so nothing still reads
plain "Boiler Run". Data-only, re-run-safe (brand expansion collapses any
prior run first, so it never doubles).
"""
from evennia.objects.models import ObjectDB
from world.spatial import get_xyz


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.destination is None and get_xyz(r) == xyz), None)


def rb(s):
    """Boiler Run -> Boiler Run Mechanics, idempotently (collapse then
    expand, so re-runs never stack 'Mechanics Mechanics')."""
    if not s:
        return s
    s = s.replace("Boiler Run Mechanics", "Boiler Run")
    s = s.replace("BOILER RUN MECHANICS", "BOILER RUN")
    s = s.replace("Boiler Run", "Boiler Run Mechanics")
    s = s.replace("BOILER RUN", "BOILER RUN MECHANICS")
    return s


n = 0

# ---- 1. mast decks: short tag "BRM S-2 Crane - Mast (Deck #)" --------
for z in range(1, 17):
    r = at((-1, -19, z))
    if r is None:
        continue
    if "Boiler Run Crane" in r.key:
        r.key = r.key.replace("Boiler Run Crane", "BRM S-2 Crane")
    r.db.desc = rb(r.db.desc)
    n += 1

# ---- 2. the cab: full brand -----------------------------------------
cab = at((-1, -19, 17))
cab.key = "Boiler Run Mechanics S-2 Crane - Operator Cab"
cab.db.desc = rb(cab.db.desc)

# ---- 3. the ground descs (S-2 on the tower-crane mention) -----------
base = at((-1, -19, 0))
if base and base.db.desc:
    d = rb(base.db.desc)
    d = d.replace("Boiler Run Mechanics tower crane",
                  "Boiler Run Mechanics S-2 tower crane")
    base.db.desc = d
for xyz in ((-1, -18, 0), (-1, -17, 0)):
    r = at(xyz)
    if r and r.db.desc:
        r.db.desc = rb(r.db.desc)

# ---- 4. the console: rebrand + a model data plate -------------------
console = next((o for o in cab.contents
                if getattr(o.db, "is_base_station", None) is True), None)
if console is not None:
    if "Boiler Run crane console" in console.key:
        console.key = "Boiler Run Mechanics crane console"
    console.db.desc = rb(console.db.desc)
    if "Stationary Model 2" not in (console.db.desc or ""):
        console.db.desc = ((console.db.desc or "").rstrip()
                           + " A data plate reads BRM S-2 — Stationary Model 2.")
    console.db.integration_desc = rb(console.db.integration_desc)

# ---- 5. Ossie: desc, vest, persona ----------------------------------
op = next((o for o in cab.contents
           if o.typeclass_path == "typeclasses.crane.CraneOperator"), None)
if op is not None:
    op.db.desc = rb(op.db.desc)
    vest = next((o for o in op.contents if "hi-viz" in o.key.lower()), None)
    if vest is not None:
        if "Boiler Run hi-viz" in vest.key:
            vest.key = "Boiler Run Mechanics hi-viz vest"
        vest.db.desc = rb(vest.db.desc)
        vest.db.worn_desc = rb(vest.db.worn_desc)
    persona = dict(op.db.llm_persona or {})
    for k in ("description", "personality", "manner", "wants", "boundaries",
              "scenario"):
        if persona.get(k):
            persona[k] = rb(persona[k])
    op.db.llm_persona = persona

print(f"BUILD 040: {n} mast decks -> BRM S-2; cab={cab.key!r}; "
      f"console={console.key if console else '?'!r}; brand carried through "
      f"descs/vest/persona.")
