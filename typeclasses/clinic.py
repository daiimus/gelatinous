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



# `Doctor` is gone (#2378). An NPC is a `LLMNpc` whose
# capabilities come from the POST it stands and the SOUL it
# carries — the typeclass says what a body IS, never what it
# can do (NPC_PLATFORM_SPEC §3, law 5).
