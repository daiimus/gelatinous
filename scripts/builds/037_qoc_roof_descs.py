"""Build 037 — descriptions for the Queen of Cups rack roof.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/037_qoc_roof_descs.py
    then a foreground reload.

Six roof cells at z12 were blank. Fill them in the house voice (the
cube-hotel-as-server-farm, the drop always present, the two crossings
that meet up here) with visual + sense layers, matching the already-
written Northwest tile and Lobby Roof. Data-only, re-run-safe.

Layout (north = +y):
                WEST(-3)      CENTER(-2)     EAST(-1)
  NORTH(-14)                  Rooftop 7287
        (-15)  NW 7282        N 7284         NE 7286
  SOUTH(-16)   SW 7281        S 7283         SE 7285  -> crane container
NW carries the fallen mast to the Halcyon; SE is the crane crossing;
Rooftop has the hatch down into the building.
"""
from evennia.objects.models import ObjectDB

DESCS = {
    7281: {  # Rack Roof Southwest
        "desc": (
            "The southwest corner of the Queen's rack roof — the top of the "
            "cube stack, boxed in by condenser units and a low parapet gone "
            "soft with salt. West past the corner, the fallen repeater mast "
            "leaves for the Halcyon; south and far below, Kaspar Street and "
            "the crane's dig. The whole rack breathes warm air up through the "
            "grating underfoot."),
        "sense": {
            "auditory": "A hundred cubes' worth of fans, a low continuous roar "
                        "you stop hearing.",
            "olfactory": "Warm exhaust — soap, sleep, machine oil — cut with "
                         "cold street air over the parapet.",
            "tactile": "Grating warm underfoot; the parapet's paint flakes off "
                       "under a hand.",
            "atmospheric": "The corner where two crossings almost meet, and the "
                           "ground is a very long way down."}},
    7283: {  # Rack Roof South
        "desc": (
            "The south run of the rack roof, a lane of deck plate between the "
            "cube stack's vents and the south parapet. Condensate lines sweat "
            "along the plate and dive through it; past the lip is the drop to "
            "Kaspar Street and the Boiler Run crane working its lot. The stack "
            "hums under your boots like a server farm that rents beds."),
        "sense": {
            "auditory": "Fans and the tick of dripping condensate; far below, "
                        "the clank of the crane.",
            "olfactory": "Warm laundry-and-noodles exhaust, damp concrete "
                         "rising from the street.",
            "tactile": "A slick condensate film on the plate; the parapet cold "
                       "and gritty.",
            "atmospheric": "A hot roof over a thousand rented sleeps, the city "
                           "laid out past the rail."}},
    7284: {  # Rack Roof North (the crossroads)
        "desc": (
            "The middle of the rack roof, where the deck's lanes cross — north "
            "to the rooftop hatch, and out to every corner of the stack. HVAC "
            "housings and a lashed-down clutter of aerials and drying laundry "
            "someone has claimed. From here the whole cube-rack spreads out, a "
            "field of warm steel boxes exhaling the building's breath."),
        "sense": {
            "auditory": "The massed fans close on every side; a line of washing "
                        "snapping in the wind.",
            "olfactory": "Detergent, hot dust, the faint ozone tang of the "
                         "aerials.",
            "tactile": "Warm housings; guy-lines drawn taut across the walkway.",
            "atmospheric": "The crossroads of the roof — every way off the "
                           "Queen starts here."}},
    7285: {  # Rack Roof Southeast (the crane crossing)
        "desc": (
            "The southeast corner of the rack roof, and the near end of the "
            "crane crossing. South across the gap the Boiler Run tower crane "
            "holds its container out on the jib; when the operator swings it "
            "level with this deck it's a short step onto the box — and a long "
            "fall when it isn't. East, the parapet gives onto the drop over "
            "South Marlowe. Boot-scuffs on the plate say plenty of people have "
            "made the jump."),
        "sense": {
            "auditory": "The rack's roar, and out over the gap the groan of "
                        "crane cable.",
            "olfactory": "Warm exhaust off the stack, diesel drifting up from "
                         "the lot.",
            "tactile": "Gritty deck plate; the rail worn bright where hands "
                       "grip before the jump.",
            "atmospheric": "The launch point. The container is either there or "
                           "it isn't."}},
    7286: {  # Rack Roof Northeast
        "desc": (
            "The northeast corner of the rack roof, a quieter angle of the deck "
            "— the fans a little muffled behind the housings, the parapet "
            "looking east and north over the drop. Somebody has dragged up a "
            "milk-crate seat and a windbreak of pallet wood against the rail: a "
            "good place to watch the street and not be watched."),
        "sense": {
            "auditory": "The fans, dulled here; wind worrying the pallet-wood "
                        "windbreak.",
            "olfactory": "Cold air winning out over the rack's warmth this high "
                         "up.",
            "tactile": "The milk crate's cracked plastic; the rail cold and "
                       "flaking.",
            "atmospheric": "The corner people climb to be alone, twelve storeys "
                           "up."}},
    7287: {  # Rooftop (the crown, hatch down)
        "desc": (
            "The true crown of the Queen of Cups, north of the rack — a small "
            "open deck around the stair-head hatch that drops back down into "
            "the eleventh level. Marine-painted plate, a guardrail, a weathered "
            "brand plate reading QUEEN OF CUPS. South and below, the cube-rack "
            "falls away in warm terraced steel; ahead, the rooflines of the "
            "colony and a great deal of empty air."),
        "sense": {
            "auditory": "The hatch breathes stairwell echo and lift machinery; "
                        "wind past the rail.",
            "olfactory": "Stairwell warmth — carpet, bodies, oil — meeting cold "
                         "roof air.",
            "tactile": "The hatch coaming smooth with use; the guardrail slick.",
            "atmospheric": "The top of the Queen — the only cell up here with a "
                           "way back inside."}},
}

n = 0
for rid, data in DESCS.items():
    r = ObjectDB.objects.filter(id=rid).first()
    if r is None:
        print(f"  WARN: #{rid} missing")
        continue
    r.db.desc = data["desc"]
    r.db.sense_descs = data["sense"]
    n += 1

print(f"BUILD 037: {n} Queen of Cups roof cells described.")
