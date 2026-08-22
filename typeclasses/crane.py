"""The Boiler Run crane — the console that answers band 27.0.

The competence used to live on the OPERATOR: `CraneOperator` was an
LLMNpc whose `_hear_radio` override *was* the crane. That meant the
crane answered Ossie and nobody else, ever — a relief operator taking
the chair would have sat there mute while the hoist ignored the band,
and the post could never accept a successor (#2216).

It lives on the console now, like dispatch. The chair grants the job;
the job does not grant the chair.

The container itself is `typeclasses.rooms.CraneContainer` — one
MOVING ROOM, which is why an unmanned crane must never drive itself:
somebody could be standing in it.
"""

import re

from typeclasses.items import AnsweringFixture


class CraneConsole(AnsweringFixture):
    """The cab console. Hears the work band, drives the container."""

    #: The Boiler Run work band. Callers tune here to reach the cab.
    CRANE_BAND = "27.0"

    #: house floor -> the container's z is (floor - 1); travel is 2..17.
    MIN_FLOOR = 2
    MAX_FLOOR = 17
    QOC_FLOOR = 13          # level with the Queen of Cups rack roof

    _NUMBER_WORDS = {
        # cardinals
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17,
        # ordinals — how people actually name a floor
        "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
        "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
        "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
        "sixteenth": 16, "seventeenth": 17,
    }

    #: Words that mark a transmission as a crane ORDER (vs a plain hail),
    #: so an addressed call the parser can't pin down gets a "say again"
    #: instead of silence.
    _INTENT = ("floor", "deck", "take", "bring", "send", "raise", "lower",
               "move", "drop", "hoist", "level", "up", "down", "top", "dock")

    #: A transmission only counts as a crane order if it ADDRESSES the crane
    #: — so ordinary band chatter that happens to contain "up" or "second"
    #: never drives the hoist (the same discipline dispatch uses: name the
    #: unit or it doesn't answer).
    _ADDRESS = ("operator", "ossie", "trelane", "crane", "container",
                "hoist", "boiler run", "the box", "the car", "the can")

    # -- the AnsweringFixture contract -----------------------------------

    def _on_our_band(self, kwargs):
        from world.radio import same_band

        return same_band(kwargs.get("radio_frequency"), self.CRANE_BAND)

    def _operator(self):
        """Whoever is on shift here — the console IS the post, so it can
        ask itself. Present and alive, or nobody."""
        try:
            from world.souls.posts import on_duty_keeper

            keeper = on_duty_keeper(self)
            if keeper is None or not keeper.pk:
                return None
            if keeper.location is not self.location:
                return None
            if keeper.is_dead() or keeper.is_unconscious():
                return None
            return keeper
        except Exception:  # noqa: BLE001 — an unmanned cab is a real answer
            return None

    def _handle(self, speech, speaker, kwargs):
        low = speech.lower()
        if not any(a in low for a in self._ADDRESS):
            return                       # band chatter, not an order

        operator = self._operator()
        if operator is None:
            # An empty cab does NOT drive itself — the container is a
            # room and somebody may be standing in it. But it answers,
            # because silence reads as a broken radio and this is a
            # closed shift. Absence is audible, and informative.
            if self._cooled_down():
                self._answer("Cab's dark — no operator on shift. "
                             "Try again on the day watch.")
            return

        car = self._find_car()
        if car is None:
            return

        floor = self._parse_floor(low, car)
        if floor is not None:
            self._run_crane(floor, car, operator)
            return

        # addressed, clearly wants the crane moved, but no floor we could
        # read — answer rather than sit there mute. Fires on a move word
        # OR anything number-ish, so a bad-enough typo still gets a reply.
        number_ish = (bool(re.search(r"\d", low))
                      or self._fuzzy_number(low, 2) is not None)
        if (number_ish or any(w in low for w in self._INTENT)) \
                and self._cooled_down():
            self._answer("Say again — which floor? Anywhere from the "
                         "2nd to the 17th.", speaker=operator)

    # -- finding the car -------------------------------------------------

    def _find_car(self):
        from evennia.objects.models import ObjectDB
        return ObjectDB.objects.filter(
            db_typeclass_path="typeclasses.rooms.CraneContainer").first()

    # -- typo tolerance --------------------------------------------------

    @staticmethod
    def _lev(a, b):
        """Levenshtein distance, capped — we only care about <= 2."""
        if a == b:
            return 0
        if abs(len(a) - len(b)) > 2:
            return 9
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[-1] + 1,
                               prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    def _fuzzy_number(self, low, max_dist):
        """The floor a misspelled number word points at, within max_dist —
        only longish tokens against longish number words (so short function
        words like 'for' can't masquerade as 'four'), and only when one
        number wins outright (ambiguous typo -> None, ask instead)."""
        best_n, best_d, ambiguous = None, max_dist + 1, False
        for tok in re.findall(r"[a-z]+", low):
            if len(tok) < 5:
                continue
            for word, n in self._NUMBER_WORDS.items():
                if len(word) < 6:
                    continue
                d = self._lev(tok, word)
                if d < best_d:
                    best_n, best_d, ambiguous = n, d, False
                elif d == best_d and n != best_n:
                    ambiguous = True
        if best_n is not None and best_d <= max_dist and not ambiguous:
            return best_n
        return None

    # -- reading the order -----------------------------------------------

    def _parse_floor(self, low, car):
        """Pull a target floor (2..17) out of a transmission, or None if it
        isn't a crane order at all."""
        # named destinations first — these are the ones players reach for
        if any(w in low for w in ("dock", "docked", "ground", "street level",
                                  "bottom", "second", "2nd", "boarding")):
            return self.MIN_FLOOR
        if any(w in low for w in ("top", "topmost", "highest", "the top",
                                  "seventeenth", "seventeen", "17th")):
            return self.MAX_FLOOR
        if "queen" in low or "crossing" in low or "the level" in low:
            return self.QOC_FLOOR

        # an explicit floor number: digits 2..17, bare or ordinal ("12th")
        m = re.search(r"\b(1[0-7]|[2-9])(?:st|nd|rd|th)?\b", low)
        if m:
            return int(m.group(1))
        # or a spelled-out number
        for word, n in self._NUMBER_WORDS.items():
            if re.search(rf"\b{word}\b", low):
                return n
        # or a spelled-out number with a single-letter typo (the teens get
        # botched constantly: forteen, fourten, thirten, fiften, sixten)
        fuzzy = self._fuzzy_number(low, 1)
        if fuzzy is not None:
            return fuzzy

        # relative nudges — only a direction word with an EXPLICIT count
        # ("up one", "down two", "up a floor"); a bare "up" is chatter, not
        # an order, so "nice weather up there" moves nothing.
        rel = re.search(
            r"\b(up|raise|lift|higher|down|lower|drop)\b\s+(?:by\s+)?"
            r"(a floor|a level|one|two|three|\d+)", low)
        if rel:
            token = rel.group(2)
            step = {"a floor": 1, "a level": 1, "one": 1,
                    "two": 2, "three": 3}.get(token)
            if step is None:
                step = int(token)
            cur_floor = (car.db.level or 1) + 1
            sign = 1 if rel.group(1) in ("up", "raise", "lift", "higher") else -1
            return cur_floor + sign * step
        return None

    # -- doing it --------------------------------------------------------

    def _run_crane(self, floor, car, operator):
        from evennia.utils import delay

        floor = max(self.MIN_FLOOR, min(self.MAX_FLOOR, int(floor)))
        target_z = floor - 1
        old_z = car.db.level or 1

        if target_z == old_z:
            if self._cooled_down():
                self._answer(f"Copy. She's already sitting at the {floor}th.",
                             speaker=operator)
            return

        rising = target_z > old_z
        # a beat of chatter, then the car actually moves
        self._answer(f"Copy, the {floor}th. Bringing her "
                     f"{'up' if rising else 'down'} — mind the swing.",
                     speaker=operator)
        delay(2.0, self._drive, car, target_z, floor, operator)

    def _drive(self, car, target_z, floor, operator=None):
        car.move_to_level(target_z)
        # re-read the chair: an operator who left (or was dropped) between
        # the copy and the landing does not narrate the landing
        who = self._operator() or None
        if floor == self.QOC_FLOOR:
            self._answer(f"The {floor}th — level with the Queen's roof. "
                         f"Step lively.", speaker=who)
        else:
            self._answer(f"Held at the {floor}th. Watch your footing.",
                         speaker=who)
