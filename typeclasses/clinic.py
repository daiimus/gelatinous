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

from evennia.utils import delay

from typeclasses.characters import Character
from typeclasses.furniture import AutoDoc
from typeclasses.llm_npc import LLMNpcMixin

#: What a clinic stocks (bottomless), keyed by the loose word the doctor picks
#: (the ``treat`` tool argument) → (medical-item prototype, the delivery verb the
# The clinic's vocabulary and its service moved to `world/clinic.py`
# (#2352) so the competence belongs to the POST — see world/service.py.
# Re-exported here because tests and tools read them off this module.
from world.clinic import (            # noqa: E402,F401
    CLINIC_CYBERWARE,
    CLINIC_SUPPLIES,
    CHROME_QUALIFIERS,
    CYBER_WORDS,
    INSTALL_CUES,
    SUPPLY_WORDS,
    TREAT_CUES,
)



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

    # --- deterministic medical requests (reliability lever) --------------
    # The intercept moved to the generic one in `LLMNpcMixin`, and the
    # procedures to `world/clinic.py`, so whoever stands the post can run
    # them (#2352). These remain as named delegates.

    def _parse_medical_request(self, speech):
        from world.clinic import parse_medical_request
        return parse_medical_request(speech)

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
        from world.clinic import treat
        return treat(self, patient, what)

    def _resolve_cyberware(self, what):
        from world.clinic import resolve_cyberware
        return resolve_cyberware(what)

    def _install_cyber(self, patient, what):
        from world.clinic import install_cyber
        return install_cyber(self, patient, what)

    def _build_install_chart(self, patient, what):
        from world.clinic import build_install_chart
        return build_install_chart(self, patient, what)

    def _draw_supply(self, proto_key):
        from world.clinic import draw_supply
        return draw_supply(self, proto_key)
