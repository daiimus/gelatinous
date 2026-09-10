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
from time import monotonic

from typeclasses.items import AnsweringFixture
from world.grammar import ordinal


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

        # A read-back is answered, not re-addressed (owner ruling,
        # 2026-09-06: "a bare confirm should work -- it's literally the
        # frequency for the crane"). The address gate below used to run
        # first, and no word in `_CONFIRM` is in `_ADDRESS`, so a caller
        # answering "confirmed" got silence and the read-back expired
        # unanswered 45 seconds later. The one prompt that exists for
        # safety was the one that ignored "yes" (#2472).
        #
        # Being on band 27.0 IS the addressing. The window is 45 seconds
        # and only opens after this crane asked a question, so the cost
        # is that somebody else's stray "yeah" on-band inside it will
        # confirm -- accepted deliberately over a prompt nobody can
        # answer the way people actually answer a radio.
        pending = self._pending_floor()
        # Refusal is read BEFORE confirmation, so a message carrying
        # both cancels. Moving is the irreversible half (#2624).
        refusing = pending is not None and self._is_refusal(low)
        confirming = (pending is not None and not refusing
                      and self._is_confirmation(low))

        if not confirming and not refusing \
                and not self._mentions(low, self._ADDRESS):
            return                       # band chatter, not an order

        operator = self._operator()
        if operator is None:
            # Nobody in the cab, so nobody picks up. The console does not
            # speak for itself — this world is operated by its people,
            # and an unmanned station going quiet is the consequence of
            # that, not a gap to paper over (owner ruling, 2026-08-22).
            return

        car = self._find_car()
        if car is None:
            return

        # A confirmation answers the read-back, not the parser: "yes"
        # carries no floor of its own, so it is resolved against what was
        # last offered. Decided above, before the address gate.
        if refusing:
            # Disarm, and SAY so — a read-back that is silently dropped
            # leaves the caller not knowing whether they were heard.
            self.ndb.pending = None
            self._answer("Belayed. Say the floor again when you're "
                         "ready.", speaker=operator)
            floor, _relative = self._parse_floor(low, car)
            if floor is None:
                return
            # ...unless they refused AND corrected in one breath, which
            # is how a real correction sounds: "negative, the fourth".
            # Fall through and read the new floor back.

        if confirming:
            self.ndb.pending = None
            self._run_crane(pending, car, operator)
            return

        floor, relative = self._parse_floor(low, car)
        if floor is not None:
            if relative:
                # Arithmetic gets read back before the car moves. The
                # container is a ROOM — somebody is standing in it — and
                # "down two" is exactly the order a tired operator and a
                # tired caller can mean differently (#2217).
                floor = max(self.MIN_FLOOR, min(self.MAX_FLOOR, int(floor)))
                self.ndb.pending = (floor, monotonic())
                self._answer(f"That puts her at the {ordinal(floor)}. Confirm?",
                             speaker=operator)
                return
            self.ndb.pending = None
            self._run_crane(floor, car, operator)
            return

        # addressed, clearly wants the crane moved, but no floor we could
        # read — answer rather than sit there mute. Fires on a move word
        # OR anything number-ish, so a bad-enough typo still gets a reply.
        number_ish = (bool(re.search(r"\d", low))
                      or self._fuzzy_number(low, 2) is not None)
        if (number_ish or self._mentions(low, self._INTENT)) \
                and self._cooled_down():
            self._answer("Say again — which floor? Anywhere from the "
                         "2nd to the 17th.", speaker=operator)

    #: How long a read-back stands before it goes stale. Long enough to
    #: key up and answer, short enough that a "yes" ten minutes later
    #: about something else does not move a crane.
    CONFIRM_WINDOW = 45.0

    #: What counts as "go ahead" on a work band. Deliberately narrow:
    #: anything ambiguous should fall through and be re-read rather than
    #: guessed at, because guessing moves a room with people in it.
    _CONFIRM = ("confirm", "confirmed", "affirmative", "yes", "yep", "yeah",
                "aye", "do it", "go ahead", "that's right", "thats right",
                "correct", "roger")

    def _pending_floor(self):
        """The floor last read back, if the caller could still be
        answering it."""
        pending = self.ndb.pending
        if not pending:
            return None
        floor, asked_at = pending
        if monotonic() - asked_at > self.CONFIRM_WINDOW:
            self.ndb.pending = None
            return None
        return floor

    #: What counts as "belay that". The mirror of `_CONFIRM`, and
    #: deliberately the WIDER of the two: nothing in this list moves a
    #: room with people in it, so the cost of hearing a refusal that was
    #: not meant is one repeated order, and the cost of missing one was
    #: a read-back that stayed armed for 45 seconds — so a "negative"
    #: followed by any stray "roger" on-band drove the car to the floor
    #: that had just been refused (#2624).
    #:
    #: "no" earns its place despite appearing inside phrases like "no
    #: problem, go ahead": a message carrying both is refused, which is
    #: the safe direction, and the caller repeats themselves.
    _DENY = ("negative", "belay", "cancel", "disregard", "abort",
             "stand down", "hold off", "as you were", "no", "nope",
             "wrong")

    def _is_confirmation(self, low):
        return any(re.search(rf"\b{re.escape(w)}\b", low)
                   for w in self._CONFIRM)

    def _is_refusal(self, low):
        return any(re.search(rf"\b{re.escape(w)}\b", low)
                   for w in self._DENY)

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

    @staticmethod
    def _mentions(low, words):
        """Whole-word match against a word list, tolerating a plural.

        These lists were plain substring tests, and ``"top" in "stop"``
        is True — so **"crane, stop"** parsed as a named destination,
        returned ``(MAX_FLOOR, False)``, skipped the read-back guard
        that only relative orders get, and drove the container (a room,
        with people standing in it) to the top of the mast (#2440). An
        emergency stop was the one phrase most likely to be shouted and
        the one phrase that bypassed the safety.

        The relative and numeric branches were already ``\b``-anchored;
        only these lists drifted. The optional ``s`` keeps "the cranes",
        "operators" and "docked" addressing the crane the way they
        always did.
        """
        return any(re.search(rf"\b{re.escape(w)}s?\b", low)
                   for w in words)

    def _parse_floor(self, low, car):
        """The floor an order asks for, and whether it was RELATIVE.

        Returns ``(floor, relative)`` or ``(None, False)``.

        Relative is read FIRST. "Bring her down two" used to land on the
        spelled-out-number branch and send the car to floor 2 — with
        people standing in it, because the container is a room (#2217).
        A direction word with a count is arithmetic, and arithmetic
        gets read back before anything moves; a floor called out plainly
        is unambiguous and just gets taken (owner ruling, 2026-08-23).
        """
        # RELATIVE FIRST — a direction word with an explicit count is
        # arithmetic ("up one", "down two", "up a floor"). Checked ahead
        # of everything else because "down two" otherwise matched the
        # spelled-out number and drove to floor 2. A bare "up" is still
        # chatter, so "nice weather up there" moves nothing.
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
            return cur_floor + sign * step, True

        # named destinations — these are the ones players reach for
        if self._mentions(low, ("dock", "docked", "ground", "street level",
                                "bottom", "second", "2nd", "boarding")):
            return self.MIN_FLOOR, False
        if self._mentions(low, ("top", "topmost", "highest", "the top",
                                "seventeenth", "seventeen", "17th")):
            return self.MAX_FLOOR, False
        if "queen" in low or "crossing" in low or "the level" in low:
            return self.QOC_FLOOR, False

        # an explicit floor number: digits 2..17, bare or ordinal ("12th")
        m = re.search(r"\b(1[0-7]|[2-9])(?:st|nd|rd|th)?\b", low)
        if m:
            return int(m.group(1)), False
        # or a spelled-out number
        for word, n in self._NUMBER_WORDS.items():
            if re.search(rf"\b{word}\b", low):
                return n, False
        # or a spelled-out number with a single-letter typo (the teens get
        # botched constantly: forteen, fourten, thirten, fiften, sixten)
        fuzzy = self._fuzzy_number(low, 1)
        if fuzzy is not None:
            return fuzzy, False
        return None, False

    # -- doing it --------------------------------------------------------

    def _run_crane(self, floor, car, operator):
        from evennia.utils import delay

        floor = max(self.MIN_FLOOR, min(self.MAX_FLOOR, int(floor)))
        # THE CAR CLASS OWNS THE OFFSET (#2617). `floor - 1` was one of
        # two copies of it, and the courier's end had no copy at all.
        # Taken off the CLASS rather than the instance: an instance can
        # be a mock or a differently-typed room, and a `getattr` on one
        # answers with something callable that is not this conversion.
        from typeclasses.rooms import CraneContainer
        target_z = CraneContainer.z_of(floor)
        old_z = car.db.level or 1

        if target_z == old_z:
            if self._cooled_down():
                self._answer(f"Copy. She's already sitting at the {ordinal(floor)}.",
                             speaker=operator)
            return

        rising = target_z > old_z
        # a beat of chatter, then the car actually moves
        self._answer(f"Copy, the {ordinal(floor)}. Bringing her "
                     f"{'up' if rising else 'down'} — mind the swing.",
                     speaker=operator)
        delay(2.0, self._drive, car, target_z, floor, operator)

    def _drive(self, car, target_z, floor, operator=None):
        # THE CHAIR, BEFORE THE CAR. The invariant this module opens with
        # is that "an unmanned crane must never drive itself: somebody
        # could be standing in it", and it was enforced at HEAR time
        # only. Two seconds pass between the copy and the drive; an
        # operator who stands up, is dragged out or dies inside that beat
        # has stopped being the operator, and the car moved anyway. The
        # re-read below existed and only decided who NARRATES (#2624).
        #
        # Silence rather than an announcement: the console does not speak
        # for itself, and an unmanned station going quiet is the
        # consequence of a world operated by its people (owner ruling,
        # 2026-08-22) — the same ruling `_handle` follows when nobody is
        # in the cab to take the call.
        who = self._operator() or None
        if who is None:
            from evennia.utils import logger
            logger.log_info(
                f"CRANE_STALLED: {self.key} (#{self.id}) was ordered to "
                f"the {ordinal(floor)} and the chair emptied before the "
                f"drive. The car did not move.")
            return
        car.move_to_level(target_z)
        if floor == self.QOC_FLOOR:
            self._answer(f"The {ordinal(floor)} — level with the Queen's roof. "
                         f"Step lively.", speaker=who)
        else:
            self._answer(f"Held at the {ordinal(floor)}. Watch your footing.",
                         speaker=who)
