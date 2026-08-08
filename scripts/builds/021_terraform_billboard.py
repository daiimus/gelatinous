"""Build 021 — the dead-terraform holo-billboard (Brackett<->Halcyon perch).

    evennia shell < scripts/builds/021_terraform_billboard.py
    then foreground reload.

Owner: replace the awkward knight's-move jump with a billboard stepping
stone. The Kaspar Gap air cell (-8,-16,12) becomes a WALKABLE catwalk
behind a truss-mounted holo-billboard bolted to the Brackett's east
flank — still projecting a colonization-era PSA for a green world that
never came. Turns the one bent leap into a clean two-cell walk:
  Brackett #6963 (-9,-16) <-walk-> Board catwalk (-8,-16)
    <-walk-> Halcyon Sun Deck (-7,-15)
The old jump edges are removed; a `billboard` sprite + an examinable
projector object carry the dead promise. (Static precursor to the
broadcast/display layer.)
"""
from evennia import create_object
from evennia.objects.models import ObjectDB

EXIT_TC = "typeclasses.exits.Exit"
ITEM_TC = "typeclasses.items.Item"


def at(xyz):
    return next((r for r in ObjectDB.objects.filter(db_attributes__db_key="xyz")
                 if r.db.xyz == xyz and r.destination is None), None)


board = ObjectDB.objects.filter(id=7133).first()        # the Kaspar Gap air
sun = ObjectDB.objects.filter(db_key="The Halcyon - Sun Deck").first()
gar = ObjectDB.objects.filter(id=6963).first()          # Brackett North Corner
assert board and sun and gar, "missing crossing rooms"

# ---- the air cell becomes a walkable billboard catwalk ---------------
board.key = "The Terraform Board"
board.db.type = "rooftop"
board.db.outside = True
board.db.is_ground = True
board.db.is_sky_room = False
board.db.atlas_skin = "billboard"
board.db.desc = (
    "A maintenance catwalk behind a colonization-era holo-billboard, "
    "bolted to the Brackett's east flank and hung out over Kaspar "
    "Street. The projector still runs, faithful as a headstone: a green "
    "world turns in the air over the slum, and under it the promise — "
    "DOMINO'S GAMBIT · A GREEN WORLD BY 3181 — a date forty-five years "
    "dead. You cross behind the light, from the Brackett's roof toward "
    "the Halcyon's deck.")
board.db.sense_descs = {
    "auditory": "The projector hums a flat carrier; the catwalk grating "
                "rings under a boot.",
    "olfactory": "Hot dust off the emitter, cold wind off the drop.",
    "tactile": "The green light passes through you and casts nothing.",
    "atmospheric": "A future nobody got, still lit, still lying."}

# ---- drop the old jump edges (this cell was their sky_room) ----------
for room in (sun, gar):
    for e in list(room.exits):
        if e.attributes.get("is_edge") and e.destination == board:
            e.delete()

# ---- walkable exits: #6963 <-> board <-> Halcyon deck ----------------
PAIRS = [(gar, board, "east", "e"), (board, gar, "west", "w"),
         (board, sun, "northeast", "ne"), (sun, board, "southwest", "sw")]
for loc, dest, key, alias in PAIRS:
    if not any(x.key == key for x in loc.exits):
        create_object(EXIT_TC, key=key, aliases=[alias], location=loc,
                      destination=dest)

# ---- the projector object (examinable, carries the ad) ---------------
proj = next((o for o in board.contents if o.key == "holo-billboard"), None)
if proj is None:
    proj = create_object(ITEM_TC, key="holo-billboard", location=board)
proj.db.desc = (
    "A truss-mounted holographic billboard in faded Domino's Gambit "
    "livery, its emitter still throwing a slow green globe into the air. "
    "The caption cycles, sun-bleached and certain: A GREEN WORLD BY "
    "3181. Someone has keyed a single word under it, years ago: SOON.")
proj.db.integrate = True
proj.db.integration_desc = (
    "A |gholo-billboard|n hangs over the street, projecting a green "
    "world that never arrived.")
proj.db.get_err_msg = "The billboard is bolted to the truss, out over the drop."
proj.db.weight = 0.5

print(f"BUILD 021: Kaspar Gap -> walkable holo-billboard catwalk "
      f"{board.db.xyz}; jump edges removed; crossing now a 2-cell walk.")
