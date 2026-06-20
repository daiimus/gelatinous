"""
Condition-driven appearance symptoms — the body's state, legible at a glance
(CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §7.3).

A character's medical state tints their rendered skintone: the sick one *looks*
sick, no ``diagnose`` required — a RipperDoc reads you across the room. Symptoms
come from two places, unified here:

* **Capacity / vitals driven** — built in: ``cyanosis`` (failing ``breathing`` →
  oxygen-starved blue), ``pallor`` (blood loss → drained).
* **Condition driven** — any ``MedicalCondition`` may expose an
  ``appearance_symptom()`` returning a symptom keyword (e.g. RenalFailure →
  ``uremic``). This is the cross-cutting hook §7.3 promises; conditions become
  first-class visible signals other systems can read.

The dominant symptom (by clinical priority) wins and overrides the base skintone
in the longdesc render. Fail-open: anything unreadable yields no tint, so look
never breaks.
"""

from __future__ import annotations

from typing import Any

#: Symptom keyword → xterm256 colour code (matches SKINTONE_PALETTE's ``|RGB``).
SYMPTOM_TINTS = {
    "cyanosis": "|115",   # oxygen-starved — dusky blue
    "pallor":   "|444",   # blood-drained — ashen grey
    "uremic":   "|431",   # renal failure — sallow grey-yellow
    "jaundice": "|551",   # hepatic — yellow
}

#: Most clinically dominant first — first present wins.
_SYMPTOM_PRIORITY = ("cyanosis", "pallor", "uremic", "jaundice")

# Built-in capacity/vitals thresholds. Tunable.
CYANOSIS_BREATHING_THRESHOLD = 0.5   # failing lungs can't oxygenate
PALLOR_BLOOD_THRESHOLD = 95.0        # % of normal blood volume (death ~85)


def _capacity(state, name):
    calc = getattr(state, "calculate_body_capacity", None)
    if not callable(calc):
        return None
    try:
        value = calc(name)
    except Exception:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return value


def get_active_symptom(character: Any) -> str | None:
    """Return the dominant visible symptom keyword for *character*, or ``None``."""
    state = getattr(character, "medical_state", None)
    if state is None:
        return None

    present: set[str] = set()

    # Condition-driven symptoms (the §7.3 hook).
    for cond in getattr(state, "conditions", None) or []:
        getter = getattr(cond, "appearance_symptom", None)
        if not callable(getter):
            continue
        try:
            symptom = getter()
        except Exception:
            symptom = None
        if symptom:
            present.add(symptom)

    # Built-in capacity / vitals symptoms.
    breathing = _capacity(state, "breathing")
    if breathing is not None and breathing < CYANOSIS_BREATHING_THRESHOLD:
        present.add("cyanosis")

    blood = getattr(state, "blood_level", None)
    if isinstance(blood, (int, float)) and not isinstance(blood, bool) \
            and blood < PALLOR_BLOOD_THRESHOLD:
        present.add("pallor")

    for symptom in _SYMPTOM_PRIORITY:
        if symptom in present:
            return symptom
    # An unranked condition-driven symptom still shows if it's the only one.
    return next(iter(present), None)


def get_appearance_tint(character: Any) -> str | None:
    """Colour code for *character*'s dominant symptom, or ``None`` for no tint."""
    try:
        symptom = get_active_symptom(character)
    except Exception:
        return None
    return SYMPTOM_TINTS.get(symptom) if symptom else None
