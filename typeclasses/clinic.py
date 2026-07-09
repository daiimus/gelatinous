"""The clinic — a Doctor NPC and the medical-supply layer over the AutoDoc.

The medical analogue of the bar: a Doctor (LLM-driven NPC) works a patient lying
on an AutoDoc (the apparatus), diagnoses them, and treats them by drawing from
the clinic's bottomless supplies and applying them through the REAL medical
commands (``apply`` / ``inject``) — the sim owns the outcome, the AutoDoc adds its
treatment bonus (``world.medical.utils.treatment_station``). Built to
HEALTH_AND_SUBSTANCE_SYSTEM_SPEC.md (G.R.I.M. treatment, diagnosis).

This is the brain + job hooks only; the persona's ``archetype`` ('doctor', in
``world/llm/prompt``) is the role. Opt in per-NPC via ``db.llm_driven``.
"""

from typeclasses.characters import Character
from typeclasses.furniture import AutoDoc
from typeclasses.llm_npc import LLMNpcMixin

#: What a clinic stocks (bottomless), keyed by the loose word the doctor picks
#: (the ``treat`` tool argument) → (medical-item prototype, the delivery verb the
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


class Doctor(LLMNpcMixin, Character):
    """An LLM-driven clinic doctor — the medical analogue of ``Bartender``."""

    def at_object_creation(self):
        super().at_object_creation()
        # Identity safety-net (parity with LLMNpc): always render through sdesc.
        if not self.height:
            self.height = "average"
        if not self.build:
            self.build = "average"
        self.db.llm_driven = False
        self.db.is_medic_npc = True   # loop-guard marker (cf. is_bartender_npc)

    # --- targeting: the patient on the table -----------------------------
    def _find_autodoc(self):
        if not self.location:
            return None
        for obj in self.location.contents:
            if isinstance(obj, AutoDoc):
                return obj
        return None

    def _patient(self, patron):
        """Who the doctor works on: the patient lying on the clinic's AutoDoc if
        there is one, else just whoever's talking to them."""
        pod = self._find_autodoc()
        if pod:
            occupants = pod.occupants()
            if occupants:
                return occupants[0]
        return patron

    def _name_aliases(self):
        return ["doctor", "doc", "medic", "surgeon", "ripperdoc"]

    # --- tool routing over the shared LLM brain --------------------------
    def _run_context_tool(self, tool, arg, patron):
        """``diagnose`` reads the patient's real medical state (the clinic's
        ``check_stock`` analogue). ``look`` stays the mixin's."""
        if tool == "diagnose":
            from world.medical.utils import get_medical_status_summary
            try:
                return (get_medical_status_summary(self._patient(patron))
                        or "nothing obviously wrong")
            except Exception:  # noqa: BLE001 — never break a turn over a read
                return "you can't get a clean read on them"
        return super()._run_context_tool(tool, arg, patron)

    def _handle_action_tool(self, tool, arg, patron):
        """``treat`` draws a clinic supply and applies it for real; the rest
        (``remember``/``feel``) delegate to the mixin."""
        if tool == "treat" and arg and self.location:
            self._treat(self._patient(patron), arg)
            return
        if tool == "install" and arg and self.location:
            self._install_cyber(self._patient(patron), arg)
            return
        LLMNpcMixin._handle_action_tool(self, tool, arg, patron)

    # --- treatment: draw a supply, run the REAL command ------------------
    def _treat(self, patient, what):
        """Pick the supply the doctor named, draw it from clinic stock, and
        ``apply``/``inject`` it on the patient — the command runs the sim
        treatment (+ AutoDoc bonus when they're on the table)."""
        key = (what or "").strip().lower()
        entry = CLINIC_SUPPLIES.get(key)
        if not entry:  # loose: any supply word inside the phrase
            entry = next((v for k, v in CLINIC_SUPPLIES.items() if k in key), None)
        if not entry:  # fuzzy: "pain killer", "bandge" (world.fuzzy facade)
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
        item = self._draw_supply(proto_key)
        if not item:
            return
        target = patient.get_display_name(self)
        if verb == "inject":
            self.execute_cmd(f"inject {item.key} {target}")
        else:
            self.execute_cmd(f"apply {item.key} on {target}")

    # --- cyberware install: run the real surgery chart ------------------
    def _resolve_cyberware(self, what):
        """Parse the doctor's ``install`` argument into a (prototype_key, side)
        pair. ``side`` is the value passed to the augment declaration (only
        side-agnostic chassis like the arm need it; L/R organs pick a prototype)."""
        import re
        low = (what or "").lower()
        side = "right" if "right" in low else ("left" if "left" in low else None)
        for keyword, (template, side_agnostic) in CLINIC_CYBERWARE.items():
            if re.search(rf"\b{keyword}\b", low):   # whole word (so 'ear' != 'heart')
                if "{S}" in template:
                    return template.replace("{S}", (side or "left").upper()), None
                if side_agnostic:
                    return template, (side or "right")
                return template, None
        return None, None

    def _install_cyber(self, patient, what):
        """Fit cyberware on the patient: build the real surgery chart
        (incise → install → suture) and commence it. The procedure engine owns
        the skill rolls + outcome (+ the AutoDoc bonus); the doctor just operates."""
        chart = self._build_install_chart(patient, what)
        if chart:
            from world.medical import charts as chart_lib
            try:
                chart_lib.commence_chart(patient, self)
            except Exception:  # noqa: BLE001 — surgery must not break the turn
                pass

    def _build_install_chart(self, patient, what):
        """Draw the cyberware + a kit, resolve its mount point, and lay out the
        incise → install → suture chart on the patient. Returns the chart or
        ``None`` if the cyberware can't be resolved."""
        proto_key, side = self._resolve_cyberware(what)
        if not proto_key or not patient:
            return None
        cyber = self._draw_supply(proto_key)
        if not cyber:
            return None
        self._draw_supply("SURGICAL_KIT")   # incise checks for a kit on the surgeon
        try:
            from world.medical import charts as chart_lib
            from world.medical.procedures import resolve_augment_declaration
            decl = resolve_augment_declaration(cyber.db, side=side) or {}
            anchor = decl.get("anchor") or decl.get("container")
            if not anchor:
                return None
            chart = chart_lib.new_chart(self)
            chart_lib.add_step(chart, "incise", {"location": anchor})
            chart_lib.add_step(chart, "install",
                               {"organ_item_key": cyber.key, "location": anchor})
            chart_lib.add_step(chart, "suture", {})
            chart_lib.save_chart(patient, chart)
            return chart
        except Exception:  # noqa: BLE001 — never crash a turn over a bad install
            return None

    def _draw_supply(self, proto_key):
        """Spawn a clinic supply item into the doctor's hands (bottomless stock).
        Returns the item or ``None`` on any failure."""
        try:
            from evennia.prototypes.spawner import spawn
            from world import prototypes
            proto = getattr(prototypes, proto_key, None)
            if not proto:
                return None
            item = spawn(proto)[0]
            item.move_to(self, quiet=True, move_hooks=False)
            return item
        except Exception:  # noqa: BLE001 — a failed draw must not break the turn
            return None
