"""Build 039 — Ossie becomes a bioroid, dressed, described, and talking.

    docker exec -i gelatinous bash -lc 'cd /usr/src/game && evennia shell' \
        < scripts/builds/039_ossie_bioroid.py
    then a foreground reload.

Owner: convert the crane operator to a bioroid — he never eats or sleeps,
he just minds the crane — with longdescs and an outfit, and wire the LLM
persona now that the crane control is proven deterministic. Follows the
build_npc path (world/npcs/blueprints.py): set species -> synthetic and
re-seed anatomy, author longdescs over the species defaults, wear the
wardrobe by layer, then persona + llm_driven. Crane orders stay hardcoded
(CraneOperator._hear_radio intercepts them before the model); the persona
only colours chatter and face-to-face. Re-run-safe.
"""
from evennia import create_object
from evennia.objects.models import ObjectDB
from world.anatomy import get_species_default_longdesc_locations
from world.medical.core import MedicalState

op = ObjectDB.objects.filter(
    db_typeclass_path="typeclasses.crane.CraneOperator").first()
assert op is not None, "Ossie (CraneOperator) not found"

# ---- 1. species: human frame, synthetic presentation ----------------
op.db.species = "synthetic_humanoid"
op.longdesc = get_species_default_longdesc_locations("synthetic_humanoid")
op._medical_state = MedicalState(op)
op.db.medical_state = op._medical_state.to_dict()

# ---- 2. identity vocab (validated set) ------------------------------
op.sex = "male"
op.height = "tall"
op.build = "heavyset"
op.hair_color = "grey"
op.hair_style = "cropped"
op.db.skintone = "pewter"
op.sdesc_keyword = "operator"

# ---- 3. authored longdescs over the synthetic defaults --------------
EYE = ("A pale, backlit iris ringed in faint amber — a focusing aperture "
       "that clicks softly when it ranges a load.")
HAND = ("A broad, blunt hand, actuator cable corded under the synthetic skin "
        "of the wrist, never quite still near the levers.")
authored = {
    "hair": ("Iron-grey hair cropped close, the recession at the temples a "
             "little too symmetrical — factory-set, not earned."),
    "face": ("A broad, weathered face, its engineered skin seamed in faint "
             "panel-lines along the jaw; the expression stays level and "
             "unhurried whatever the load is doing."),
    "left_eye": EYE, "right_eye": EYE,
    "neck": ("The throat carries the same pewter sheen, a small maker's stamp "
             "pressed into the skin just below the collar line."),
    "chest": ("A heavy engineered torso under pewter skin, panelled in neat "
              "seams — build-plate work, not gym work."),
    "left_hand": HAND, "right_hand": HAND,
}
merged = dict(op.longdesc or {})
merged.update(authored)
op.longdesc = merged

# ---- 4. the room-visible description --------------------------------
op.db.desc = (
    "A broad, heavyset crane bioroid seated at the console like it grew there "
    "— pewter-toned synthetic skin seamed in neat panels at the jaw and "
    "throat, pale backlit eyes that click faintly as they range the load. A "
    "Boiler Run hi-viz vest gone grey with dust. It watches the container "
    "through the long window more than it watches you, one blunt hand never "
    "far from the levers, and it does not seem to blink.")

# ---- 5. the outfit (worn by layer: base first) ----------------------
WARDROBE = [
    {"key": "grey work henley", "aliases": ["henley", "shirt"],
     "desc": ("A heavy grey henley, sleeves shoved to the elbow, the weave "
              "gone thin and soft where it rubs a lever all shift."),
     "worn_desc": "a heavy grey henley, sleeves shoved to the elbow",
     "coverage": ["chest", "back", "left_arm", "right_arm"],
     "layer": 1, "color": "grey", "material": "cotton", "weight": 0.4,
     "category": "clothing"},
    {"key": "heavy canvas work trousers", "aliases": ["trousers", "pants"],
     "desc": ("Heavy canvas work trousers, knees double-stitched and grey "
              "with dust, a folding rule still in the thigh pocket."),
     "worn_desc": "heavy canvas work trousers, knees double-stitched",
     "coverage": ["groin", "left_thigh", "right_thigh", "left_shin",
                  "right_shin"],
     "layer": 1, "color": "tan", "material": "canvas", "weight": 0.6,
     "category": "clothing"},
    {"key": "steel-toed boots", "aliases": ["boots"],
     "desc": ("Scuffed steel-toed work boots, the leather cracked white "
              "across the flex, the toecaps worn back to bright metal."),
     "worn_desc": "scuffed steel-toed boots, toecaps worn to bright metal",
     "coverage": ["left_foot", "right_foot"],
     "layer": 1, "color": "brown", "material": "leather", "weight": 0.9,
     "category": "clothing"},
    {"key": "fingerless grip gloves", "aliases": ["gloves"],
     "desc": ("Fingerless gloves with tacky rubberised palms, the grip worn "
              "smooth in the exact shape of a lever."),
     "worn_desc": "fingerless gloves with rubberised palms",
     "coverage": ["left_hand", "right_hand"],
     "layer": 1, "color": "black", "material": "leather", "weight": 0.1,
     "category": "clothing"},
    {"key": "Boiler Run hi-viz vest",
     "aliases": ["vest", "hi-viz", "hi-vis", "hivis"],
     "desc": ("A high-visibility safety vest in faded Boiler Run amber, "
              "reflective strips crazed and peeling, BOILER RUN stencilled "
              "across the back over a hard-hat logo. Grey with rock dust."),
     "worn_desc": "a faded amber Boiler Run hi-viz vest, strips peeling",
     "coverage": ["chest", "back"],
     "layer": 2, "color": "amber", "material": "polyester", "weight": 0.3,
     "category": "clothing"},
]
worn = 0
already = {o.key for o in op.contents}
for gspec in sorted(WARDROBE, key=lambda g: int(g.get("layer", 1))):
    if gspec["key"] in already:
        continue
    garment = create_object("typeclasses.items.Item", key=gspec["key"],
                            aliases=gspec.get("aliases"), location=op, home=op)
    for attr in ("desc", "worn_desc", "coverage", "layer", "color",
                 "material", "weight", "category"):
        if gspec.get(attr) is not None:
            garment.attributes.add(attr, gspec[attr])
    op.wear_item(garment)
    worn += 1

# ---- 6. the bioroid persona (crane control stays deterministic) -----
op.db.llm_persona = {
    "archetype": "colonist",
    "name": "Ossie Trelane",
    "description": (
        "A heavyset crane bioroid in a dust-grey Boiler Run hi-viz vest, "
        "pewter synthetic skin seamed at the jaw, pale backlit eyes that "
        "range the load and rarely blink."),
    "personality": (
        "A Boiler Run crane bioroid, and he'll say so if you ask — no "
        "pretence of being anything else. Tireless in the literal sense: he "
        "does not eat, does not sleep, has not left the cab since the mast "
        "went up. Laconic, dry, patient past anything human. Treats the "
        "container as 'her' — the one thing he minds. Safety is a fixed "
        "subroutine; a rushed lift is how people become paperwork."),
    "manner": (
        "clipped radio brevity with an even synthetic calm under it; calls "
        "the container 'her' and callers 'chief'; ends with a click of the "
        "handset; gives a dry line where another man would use ten"),
    "wants": (
        "a load that swings true, nobody stepping off onto air, and the lot "
        "finished someday so he knows what he was for"),
    "boundaries": (
        "rush a lift he reads as unsafe; leave the cab; pretend to appetites "
        "he does not have; claim knowledge past his own steel and the band"),
    "scenario": (
        "Up in the Boiler Run crane cab over the Marlowe Lot, minding the "
        "container by radio on 27.0 — has, without a break, since the crane "
        "was raised. Callers key up for a floor; between lifts it is dead air "
        "and wind."),
}
op.db.llm_driven = True

print(f"BUILD 039: Ossie #{op.id} species={op.db.species} skintone={op.db.skintone} "
      f"worn+{worn} llm_driven={op.db.llm_driven} persona={op.db.llm_persona['name']!r}")
