"""Service at a clinic — the third shape (#2352).

A bar is SERVED FROM and a shop is SOLD FROM; a clinic is WORKED ON. The
patient is not always the person talking (whoever is on the AutoDoc
outranks them), nothing changes hands, and the act is a surgery chart
rather than a purchase. Same registry, different shape.

Ported off the `Doctor` typeclass so the competence belongs to the post.
The clinic had no live gap when this was written — both doctor posts
were held by `Doctor` keepers — but every other 24/7 venue in the colony
was dark two thirds of the time for exactly this reason, and the
blueprint table cannot stop naming role typeclasses until the last
venue stops depending on one (#2352).

Only EXPLICIT requests run here. Diagnosis-driven treatment still flows
to the voice, because the need is in the sim rather than in the words.
"""

import re

from evennia.utils import delay

from world.service import register

#: Roles that work on people. `medic` runs `policy=successor` with no
#: blueprint, so a generic soul takes that post the moment it falls
#: vacant — it is the one most likely to need this.
CLINIC_ROLES = ("doctor", "medic")


#: item wants — ``apply`` for dressings/splints, ``inject`` for fluids).
CLINIC_SUPPLIES = {
    "bandage": ("GAUZE_BANDAGES", "apply"),
    "gauze": ("GAUZE_BANDAGES", "apply"),
    "dressing": ("GAUZE_BANDAGES", "apply"),
    "painkiller": ("PAINKILLER", "inject"),
    "morphine": ("PAINKILLER", "inject"),
    "pain": ("PAINKILLER", "inject"),
    "blood": ("BLOOD_BAG", "inject"),
    "transfusion": ("BLOOD_BAG", "inject"),
    "stim": ("STIMPAK", "inject"),
    "stimpak": ("STIMPAK", "inject"),
    "splint": ("SPLINT", "apply"),
}

#: Cyberware the clinic can fit, keyed by the word the doctor names. ``{S}`` is
#: filled with the side for left/right organs; ``side_agnostic`` chassis (the arm)
#: take a single prototype and a side passed to the augment declaration instead.
CLINIC_CYBERWARE = {
    "arm": ("CYBER_ARM", True),
    "eye": ("CYBER_{S}_EYE", False),
    "ear": ("CYBER_{S}_EAR", False),
    "kidney": ("CYBER_{S}_KIDNEY", False),
    "jaw": ("CYBER_JAW", False),
    "heart": ("CYBERNETIC_HEART", False),
    "tail": ("CYBERNETIC_TAIL", False),
}

#: Deterministic medical-request vocab (parity with the bartender's order parser,
#: #1235): an EXPLICIT patient request for a procedure runs for real instead of
#: riding the model's flaky treat/install roll. The sim-DRIVEN treatment a doctor
#: decides from a diagnosis still flows to the LLM — that need is in the sim, not
#: the words, so it can't be parsed away.
CYBER_WORDS = ("arm", "eye", "ear", "kidney", "jaw", "heart", "tail")
SUPPLY_WORDS = ("painkiller", "morphine", "bandage", "gauze", "dressing", "blood",
                "transfusion", "stim", "stimpak", "splint", "pain")
#: chrome qualifiers on a body part → an install request ("chrome arm", "cyber eye")
CHROME_QUALIFIERS = ("cyber", "chrome", "bionic", "prosthetic", "mechanical")
#: verbs that mark an install request even without a chrome word ("replace my arm")
INSTALL_CUES = ("install", "fit me", "fit a", "put in", "wire me", "chrome me",
                "replace my", "swap in", "swap out", "give me a new",
                "i want a new", "hook me up with", "put a")
#: verbs that mark a supply request ("gimme a painkiller", "something for the pain")
TREAT_CUES = ("gimme", "give me", "i need", "i want", "hit me with", "hook me up",
              "can i get", "shoot me", "get me", "i could use", "something for")

def find_autodoc(room):
    """The clinic's pod, or None."""
    from typeclasses.clinic import AutoDoc
    if room is None:
        return None
    for obj in room.contents:
        if isinstance(obj, AutoDoc):
            return obj
    return None


def patient_for(by, patron):
    """Who the keeper works on: whoever is lying on the AutoDoc if
    anyone is, else whoever is talking to them."""
    pod = find_autodoc(getattr(by, "location", None))
    if pod:
        occupants = pod.occupants()
        if occupants:
            return occupants[0]
    return patron


def parse_medical_request(speech):
    """('install', speech) | ('treat', speech) | None.

    Conservative — a question or a bare symptom ("my arm hurts") is NOT
    a request: an install needs a cyberware part AND a chrome word or
    install verb; a treat needs a supply word AND a request cue."""
    low = " ".join((speech or "").lower().split())
    if not low or "?" in low:
        return None
    words = re.findall(r"[a-z]+", low)   # whole words, punctuation stripped
    if any(w in words for w in CYBER_WORDS) and (
            any(q in low for q in CHROME_QUALIFIERS)
            or any(c in low for c in INSTALL_CUES)):
        return ("install", speech)
    if (any(w in low for w in SUPPLY_WORDS)
            and any(c in low for c in TREAT_CUES)):
        return ("treat", speech)
    return None


def draw_supply(by, proto_key):
    """Spawn a clinic supply into the keeper's hands (bottomless stock).

    Anchored = bottomless, field = finite (souls spec §14): the
    bottomless draw only works AT the post — a doctor met off-duty at a
    bar treats with whatever is actually in their pockets, like anyone
    else."""
    post = getattr(by.db, "soul_post", None)
    if post is not None and by.location != post:
        return None
    try:
        from evennia.prototypes.spawner import spawn
        from world import prototypes
        proto = getattr(prototypes, proto_key, None)
        if not proto:
            return None
        item = spawn(proto)[0]
        item.move_to(by, quiet=True, move_hooks=False)
        return item
    except Exception:  # noqa: BLE001 — a failed draw must not break the turn
        return None


def _draw(by, proto_key):
    """Draw a supply, preferring the keeper's own method when they have
    one. That override seam is what a `Doctor` and its tests rely on;
    a plain post-holder falls through to the module default."""
    own = getattr(by, "_draw_supply", None)
    if callable(own):
        return own(proto_key)
    return draw_supply(by, proto_key)


def treat(by, patient, what):
    """Pick the supply named, draw it from stock, and ``apply``/``inject``
    it on the patient — the command runs the sim treatment (+ the AutoDoc
    bonus when they are on the table)."""
    key = (what or "").strip().lower()
    entry = CLINIC_SUPPLIES.get(key)
    if not entry:  # loose: any supply word inside the phrase
        entry = next((v for k, v in CLINIC_SUPPLIES.items() if k in key), None)
    if not entry:  # fuzzy: "pain killer", "bandge"
        try:
            from world.fuzzy import best_match
            hit = best_match(key, list(CLINIC_SUPPLIES))
            if hit:
                entry = CLINIC_SUPPLIES[hit[0]]
        except Exception:  # noqa: BLE001 — resolution is best-effort
            entry = None
    if not entry or not patient:
        return
    proto_key, verb = entry
    item = _draw(by, proto_key)
    if not item:
        return
    target = patient.get_display_name(by)
    if verb == "inject":
        by.execute_cmd(f"inject {item.key} {target}")
    else:
        by.execute_cmd(f"apply {item.key} on {target}")


def resolve_cyberware(what):
    """Parse an ``install`` argument into a (prototype_key, side) pair."""
    low = (what or "").lower()
    side = "right" if "right" in low else ("left" if "left" in low else None)
    for keyword, (template, side_agnostic) in CLINIC_CYBERWARE.items():
        if re.search(rf"\b{keyword}\b", low):  # whole word ('ear' != 'heart')
            if "{S}" in template:
                return template.replace("{S}", (side or "left").upper()), None
            if side_agnostic:
                return template, (side or "right")
            return template, None
    return None, None


def build_install_chart(by, patient, what):
    """Draw the cyberware + a kit, resolve its mount point, and lay out
    the incise → install → suture chart on the patient."""
    proto_key, side = resolve_cyberware(what)
    if not proto_key or not patient:
        return None
    cyber = _draw(by, proto_key)
    if not cyber:
        return None
    _draw(by, "SURGICAL_KIT")   # incise checks for a kit on the surgeon
    try:
        from world.medical import charts as chart_lib
        from world.medical.procedures import resolve_augment_declaration
        decl = resolve_augment_declaration(cyber.db, side=side) or {}
        anchor = decl.get("anchor") or decl.get("container")
        if not anchor:
            return None
        chart = chart_lib.new_chart(by)
        chart_lib.add_step(chart, "incise", {"location": anchor})
        chart_lib.add_step(chart, "install",
                           {"organ_item_key": cyber.key, "location": anchor})
        chart_lib.add_step(chart, "suture", {})
        chart_lib.save_chart(patient, chart)
        return chart
    except Exception:  # noqa: BLE001 — never crash a turn over a bad install
        return None


def install_cyber(by, patient, what):
    """Fit cyberware: build the real surgery chart and commence it. The
    procedure engine owns the rolls and the outcome (+ the AutoDoc
    bonus); the keeper just operates."""
    if build_install_chart(by, patient, what):
        from world.medical import charts as chart_lib
        try:
            chart_lib.commence_chart(patient, by)
        except Exception:  # noqa: BLE001 — surgery must not break the turn
            pass


def serve_at_clinic(post, speech, patron, by, addressed=False):
    """Run an explicit procedure request. True if claimed.

    Unlike a board or a shelf, an ADDRESSED line earns no leniency here:
    a doctor acting on a half-heard request is worse than one who asks
    again. Both doors go through the same conservative parse.
    """
    req = parse_medical_request(speech)
    if req is None:
        return False
    kind, arg = req
    patient = patient_for(by, patron)
    runner = install_cyber if kind == "install" else treat
    delay(1.5, runner, by, patient, arg)
    return True


for _role in CLINIC_ROLES:
    register(_role, serve_at_clinic)
