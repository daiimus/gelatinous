"""The Boiler Run crane operator — radio control of the container car.

The operator sits in the cab at the top of the mast with a base-station
console tuned to the work band. A caller keys up on that band and asks
for a floor; the operator runs the container there (the P2 seam,
``CraneContainer.move_to_level``) and keys back a confirmation.

The crane order is DETERMINISTIC — it does not depend on the LLM being
up, because a hoist answering "take it to twelve" shouldn't hinge on a
warm model. Anything that ISN'T a crane order falls through to the LLM
persona (when enabled) for flavour, exactly the ``_handle_directed_speech``
/ radio split the brain was built around.
"""
import re

from typeclasses.llm_npc import LLMNpc


class CraneOperator(LLMNpc):
    """An LLM-capable NPC whose radio ear is wired to the crane first."""

    #: The Boiler Run work band. Callers tune here to reach the cab.
    CRANE_BAND = "27.0"

    #: house floor -> the container's z is (floor - 1); travel is 2..17.
    MIN_FLOOR = 2
    MAX_FLOOR = 17
    QOC_FLOOR = 13          # level with the Queen of Cups rack roof

    _NUMBER_WORDS = {
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17,
    }

    # -- finding the car -------------------------------------------------
    def _find_car(self):
        from evennia.objects.models import ObjectDB
        return ObjectDB.objects.filter(
            db_typeclass_path="typeclasses.rooms.CraneContainer").first()

    # -- reading the order -----------------------------------------------
    def _parse_floor(self, speech, car):
        """Pull a target floor (2..17) out of a transmission, or None if it
        isn't a crane order at all."""
        low = speech.lower()

        # named destinations first — these are the ones players will reach for
        if any(w in low for w in ("dock", "docked", "ground", "street level",
                                  "bottom", "second", "2nd", "boarding")):
            return self.MIN_FLOOR
        if any(w in low for w in ("top", "topmost", "highest", "the top",
                                  "seventeenth", "seventeen", "17th")):
            return self.MAX_FLOOR
        if "queen" in low or "crossing" in low or "the level" in low:
            return self.QOC_FLOOR

        # an explicit floor number: digits 2..17
        m = re.search(r"\b(1[0-7]|[2-9])\b", low)
        if m:
            return int(m.group(1))
        # or a spelled-out number
        for word, n in self._NUMBER_WORDS.items():
            if re.search(rf"\b{word}\b", low):
                return n

        # relative nudges (only when clearly a movement word, not chatter)
        cur_floor = (car.db.level or 1) + 1
        if re.search(r"\b(up|raise|higher|lift)\b", low):
            return cur_floor + 1
        if re.search(r"\b(down|lower|drop)\b", low):
            return cur_floor - 1
        return None

    # -- radio ear: crane order first, persona second --------------------
    def _hear_radio(self, speech, speaker, kwargs):
        from world.radio import same_band

        if (speech and not self._is_npc_speaker(speaker)
                and same_band(kwargs.get("radio_frequency"), self.CRANE_BAND)):
            car = self._find_car()
            if car is not None:
                floor = self._parse_floor(speech, car)
                if floor is not None:
                    self._run_crane(floor, speaker, car)
                    return
        # not a crane order — let the LLM brain handle it (if enabled)
        super()._hear_radio(speech, speaker, kwargs)

    # -- doing it --------------------------------------------------------
    def _run_crane(self, floor, caller, car):
        from evennia.utils import delay

        floor = max(self.MIN_FLOOR, min(self.MAX_FLOOR, int(floor)))
        target_z = floor - 1
        old_z = car.db.level or 1

        if target_z == old_z:
            self._reply(f"Copy. She's already sitting at the {floor}th.")
            return

        rising = target_z > old_z
        # a beat of chatter, then the car actually moves
        self._reply(f"Copy, the {floor}th. Bringing her "
                    f"{'up' if rising else 'down'} — mind the swing.")
        delay(2.0, self._drive, car, target_z, floor)

    def _drive(self, car, target_z, floor):
        car.move_to_level(target_z)
        if floor == self.QOC_FLOOR:
            self._reply(f"The {floor}th — level with the Queen's roof. "
                        f"Step lively.")
        else:
            self._reply(f"Held at the {floor}th. Watch your footing.")

    def _reply(self, message):
        """Key the cab console and answer on the band."""
        from world.radio import active_transmit_radio, transmit, transmit_organ
        device = active_transmit_radio(self)
        if device is not None:
            transmit(self, message, device=device)
        else:
            transmit_organ(self, message)
