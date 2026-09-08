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

from world.service import SILENT, register

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
    """The clinic's pod, or None. Defensive: a location that cannot be
    enumerated simply has no pod, and a treatment must not die because
    of where somebody is standing."""
    from typeclasses.furniture import AutoDoc
    try:
        contents = list(room.contents)
    except Exception:  # noqa: BLE001
        return None
    for obj in contents:
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
    # The bottomless draw is a POST perk, so no post means no draw
    # (#2474). This read `post is not None and by.location != post`,
    # which skipped the location test entirely for anyone whose
    # `soul_post` is None — inverted-permissive for exactly the callers
    # it should be strictest about, since a post-holder standing at
    # their post is the only case the docstring sanctions.
    #
    # Checked against the world before tightening: 78 objects carry a
    # `soul_post`, the clinic keeper among them. One (`the Rook`) has
    # the attribute set to None, and is correctly refused — a sealed-
    # basement DJ has no clinic stock to draw on.
    post = getattr(by.db, "soul_post", None)
    if post is None or by.location != post:
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
    bonus when they are on the table).

    Returns True only if a treatment command was actually issued. The
    supply can be unrecognised or out of stock, and a caller that BILLS
    for this needs to know which happened (#2428)."""
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
        return False
    proto_key, verb = entry
    item = _draw(by, proto_key)
    if not item:
        return False
    target = patient.get_display_name(by)
    if verb == "inject":
        by.execute_cmd(f"inject {item.key} {target}")
    else:
        by.execute_cmd(f"apply {item.key} on {target}")
    return True


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


def _organ_slot_container(patient, cyber):
    """Where on THIS patient the organ being replaced already lives.

    Mirrors `_resolve_install`: the slot is found by `organ_name`, and
    its `container` is the place to open. Returns None when the patient
    has no such organ, which is a real answer — you cannot replace a
    heart in a body that has no heart slot.
    """
    organ_name = getattr(getattr(cyber, "db", None), "organ_name", None) \
        or getattr(cyber, "key", None)
    if not organ_name or patient is None:
        return None
    try:
        from world.medical.procedures import get_organ_snapshot
        organs = (get_organ_snapshot(patient) or {}).get("organs") or {}
    except Exception:  # noqa: BLE001 — an unreadable body has no slot
        return None
    slot = organs.get(organ_name)
    if slot is None or not hasattr(slot, "get"):
        return None
    return slot.get("container") or None


def _discard(item):
    """Undo a draw that led nowhere, so a failed request does not leave
    stock in the surgeon's pockets."""
    try:
        if item and item.pk:
            item.delete()
    except Exception:  # noqa: BLE001 — a stuck delete is not worth a crash
        pass


def build_install_chart(by, patient, what):
    """Draw the cyberware + a kit, resolve its mount point, and lay out
    the incise → install → suture chart on the patient."""
    proto_key, side = resolve_cyberware(what)
    if not proto_key or not patient:
        return None
    cyber = _draw(by, proto_key)
    if not cyber:
        return None
    # A KIT IS A REQUIREMENT, NOT A CONSUMABLE (#2474). `incise` CHECKS
    # FOR a kit; nothing spends it. `draw_supply` spawns
    # unconditionally, so every install minted a fresh one and the
    # surgeon accumulated them — nine on Jericho Black III when this was
    # filed, eight of them with consecutive object ids.
    #
    # `find_surgical_kit` is the same predicate the procedure gate uses,
    # so "do I need to draw one" and "will incise accept it" cannot
    # answer differently.
    from world.medical.utils import find_surgical_kit
    drawn_kit = None
    if find_surgical_kit(by, patient) is None:
        drawn_kit = _draw(by, "SURGICAL_KIT")
    try:
        from world.medical import charts as chart_lib
        from world.medical.procedures import resolve_augment_declaration
        decl = resolve_augment_declaration(cyber.db, side=side) or {}
        anchor = decl.get("anchor") or decl.get("container")
        if not anchor:
            # ASK THE PATIENT, not the part (#2455). A LIMB augment
            # declares where it bolts on (`augment_anchor`), but a
            # REPLACEMENT ORGAN does not and never did: its mount point
            # is wherever the organ it replaces already sits on this
            # body. That is exactly what the working door does —
            # `_resolve_install` looks `organ_name` up in the patient's
            # own organ snapshot and takes that slot's container.
            #
            # Reading only the item meant 5 of the 7 words in
            # CLINIC_CYBERWARE (heart, eye, ear, kidney, jaw) resolved
            # to None and bailed here: the NPC gave no spoken reply, no
            # surgery was laid out, and the request evaporated in
            # silence — while every attempt left a spawned cyber organ
            # in the doctor's pockets with no cleanup path. Only
            # CYBER_ARM and CYBERNETIC_TAIL carry an anchor, which is
            # why the one test of this bridge drives "cyber arm left"
            # and stayed green.
            anchor = _organ_slot_container(patient, cyber)
        if not anchor:
            # Genuinely nothing to mount it to — a body with no slot for
            # this organ. Put back everything THIS request drew rather
            # than pocketing it in silence. The kit only goes back if we
            # were the ones who drew it: a kit the surgeon already had
            # is theirs, and #2474 established a kit is a requirement
            # rather than a consumable.
            _discard(cyber)
            _discard(drawn_kit)
            return None
        # DO NOT CLOBBER SOMEBODY ELSE'S SURGERY. `save_chart` writes
        # `db.medical_chart` wholesale, while the operate menu's
        # `_add_step_to_chart` reuses an existing chart — two writers,
        # one attribute, and only one of them reads first. A surgeon
        # with an amputation and a harvest laid out on this patient
        # would find them replaced by three install steps, already
        # RUNNING, because install_cyber commences immediately (#2801).
        existing = chart_lib.get_chart(patient)
        if existing and _chart_is_live(existing):
            return None
        chart = chart_lib.new_chart(by)
        chart_lib.add_step(chart, "incise", {"location": anchor})
        # CARRY THE SIDE. It is resolved two lines up and used to build
        # the declaration, then dropped from the step — and the
        # dispatcher cannot recover it (`side = (args or {}).get("side")`
        # is None, so its `if side:` branch never runs), so the resolver
        # refuses:
        #
        #     if declaration["side_agnostic"] and not side:
        #         "mounts on either side — name one (left or right)."
        #
        # A cyber arm is side-agnostic, so that was EVERY clinic arm
        # install. And the chart is incise -> install -> suture, so the
        # incision succeeds first: the patient is opened at the anchor
        # and then left there, with the refusal addressed to the clinic
        # NPC, which has no way to supply a side (#2692).
        #
        # `CmdOperate`, the other door onto the same resolver, has always
        # passed it.
        chart_lib.add_step(chart, "install",
                           {"organ_item_key": cyber.key, "location": anchor,
                            "side": side})
        chart_lib.add_step(chart, "suture", {})
        chart_lib.save_chart(patient, chart)
        return chart
    except Exception:  # noqa: BLE001 — never crash a turn over a bad install
        return None


def _chart_is_live(chart) -> bool:
    """Is this chart somebody's work in progress rather than a spent one?

    A chart with a running or still-pending step is live. A completed or
    fully-abandoned one is just the record of the last operation and is
    safe to replace.
    """
    from world.medical import charts as chart_lib
    return any(step.get("status") in (chart_lib.PENDING, chart_lib.RUNNING)
               for step in (chart.get("steps") or ()))


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


def _diagnose(post, arg, patron, by):
    """The patient's real medical state — the clinic's `check_stock`."""
    from world.medical.utils import get_medical_status_summary
    try:
        return (get_medical_status_summary(patient_for(by, patron))
                or "nothing obviously wrong")
    except Exception:  # noqa: BLE001 — never break a turn over a read
        return "you can't get a clean read on them"


def _install_tool(post, arg, patron, by):
    """Fit chrome for real — the chart, the rolls and the outcome all
    belong to the procedure engine; the keeper just operates."""
    if arg and getattr(by, "location", None):
        install_cyber(by, patient_for(by, patron), arg)
    return None


def _treat_tool(post, arg, patron, by):
    """Draw a supply and apply it for real."""
    if arg and getattr(by, "location", None):
        treat(by, patient_for(by, patron), arg)
    return None


for _role in CLINIC_ROLES:
    register(_role, serve_at_clinic,
             aliases=("doctor", "doc", "medic", "surgeon", "ripperdoc"),
             # a doctor asked something odd stays quiet -- ON PURPOSE.
             # SILENT rather than None so the decision is on the record
             # and the startup warning stays for roles that forgot (#2824).
             fallback=SILENT,
             archetype="doctor",
             tools={"diagnose": _diagnose, "treat": _treat_tool,
                    "install": _install_tool})
