"""The "all units, respond" answerer must be someone on the net.

Regression pin for #2656.  The single-answerer election took every
LLM-driven receiver that got words and picked the lowest dbref.  Two
tests, neither of which asked whether the candidate was actually on the
frequency: `receivers` is the grille fan-out, so membership meant "a
person in a room that contains a powered radio", not "a unit on the net".

So standing near somebody else's handset put you in the running, and
dbref order then decided who answered for the colony.

The fix reuses the flag the module already maintains for exactly this
distinction.  `own` means the traffic came to YOU -- you carry the
handset, it is your comms organ, or you are a duty console listening to
itself -- and the render below the election already chooses between
"Your radio" and "A radio nearby" off it.  No new predicate, and no
role list to adjudicate.

Measured live across every band before and after:

    911MHz  security robot #3258 (comms organ)   -> unchanged, correct
    27.0    Petra #4955, dispatcher, no radio    -> Wren #9084, courier,
                                                    carrying a radio
    88.8    Ezra Vantomme #5161, carries a radio -> unchanged
    447     no candidates                        -> no candidates

Two corrections to the issue, both from re-measuring: it reported the
911MHz winner as a WORKER in a dispatch office, which no longer
reproduces, and it stated that no LLM-driven NPC in the colony carries a
radio.  Two do -- Wren and Ezra Vantomme -- which is why the honest fix
is to prefer the people genuinely on the net rather than, as the issue
expected, to empty the pool.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from world import radio
from world.radio import transmit


class _Room:
    """A real list for `contents` — `_grille_audience` is isinstance-typed."""

    def __init__(self):
        self.contents = []


class _Person:
    """A person at a grille: perceivable, addressable, with a dbref."""

    def __init__(self, dbref, room, *, llm=True):
        self.id = dbref
        self.location = room
        self.hands = {}
        self.contents = []
        self.msg = MagicMock()
        self.db = MagicMock()
        self.db.llm_driven = llm
        room.contents.append(self)

    # `_perceives` duck-types a person by these.
    def get_sdesc(self):
        return "a figure"

    medical_state = object()


def _handset(owner, freq="27.0"):
    r = MagicMock()
    r.db.is_radio = True
    r.db.radio_on = True
    r.db.frequency = freq
    r.location = owner          # carried -> owner is the holder
    del r._maybe_answer         # not a duty console
    return r


def _speaker():
    c = MagicMock()
    c.get_worn_items = lambda: []
    c.hands = {}
    c.contents = []
    return c


def _elected_of(radios, speaker_device):
    """Run a real transmit and report who was flagged as the answerer."""
    speaker = _speaker()
    speaker_device.location = speaker
    with patch.object(radio, "_all_powered_radios",
                      return_value=[speaker_device] + radios), \
            patch.object(radio, "_comms_bots_on", return_value=[]), \
            patch.object(radio, "_log_to_channel"), \
            patch("world.perception.can_hear", return_value=True), \
            patch("world.voice.attempt_voice_discern", return_value=None), \
            patch("world.voice.get_voice_description", return_value="flat"), \
            patch("world.voice.voice_phrase", return_value=None):
        transmit(speaker, "all units, respond", speaker_device)
    return None


class TestTheAnswererIsOnTheNet(TestCase):

    def _run(self, room, radios):
        speaker_device = _handset(_speaker())
        _elected_of(radios, speaker_device)
        out = {}
        for person in room.contents:
            calls = [c for c in person.msg.call_args_list
                     if "radio_elected" in (c.kwargs or {})]
            if calls:
                out[person.id] = calls[-1].kwargs["radio_elected"]
        return out

    # -- the defect ------------------------------------------------

    def test_a_bystander_does_not_answer_for_the_carrier(self):
        """Lower dbref, no radio, same room. Must not be elected."""
        room = _Room()
        bystander = _Person(10, room)      # lower dbref, carries nothing
        carrier = _Person(20, room)        # higher dbref, carries the radio
        handset = _handset(carrier)

        verdicts = self._run(room, [handset])

        self.assertIs(verdicts.get(carrier.id), True,
                      "the unit actually holding the radio must answer")
        self.assertIs(verdicts.get(bystander.id), False,
                      "a bystander at someone else's grille was elected "
                      "purely for having the lower dbref")

    def test_a_room_of_bystanders_elects_nobody(self):
        """A radio on the floor belongs to no one — nobody answers."""
        room = _Room()
        a, b = _Person(10, room), _Person(20, room)
        loose = MagicMock()
        loose.db.is_radio = True
        loose.db.radio_on = True
        loose.db.frequency = "27.0"
        loose.location = room              # on the floor: holder is the room
        del loose._maybe_answer

        verdicts = self._run(room, [loose])

        self.assertEqual(set(verdicts.values()), {False},
                         "nobody is on this net, so nobody should answer")
        self.assertEqual(sorted(verdicts), [a.id, b.id])

    # -- controls --------------------------------------------------

    def test_the_lowest_dbref_carrier_still_wins(self):
        """Determinism survives: dbref remains the tie-break."""
        room = _Room()
        low, high = _Person(10, room), _Person(30, room)
        verdicts = self._run(room, [_handset(low), _handset(high)])
        self.assertIs(verdicts.get(low.id), True)
        self.assertIs(verdicts.get(high.id), False)

    def test_exactly_one_unit_is_ever_elected(self):
        room = _Room()
        carriers = [_Person(n, room) for n in (10, 20, 30)]
        verdicts = self._run(room, [_handset(c) for c in carriers])
        self.assertEqual(sorted(verdicts.values()).count(True), 1)

    def test_a_non_llm_carrier_is_not_elected(self):
        """A player carrying a radio is not the colony's answering machine."""
        room = _Room()
        player = _Person(10, room, llm=False)
        npc = _Person(20, room)
        verdicts = self._run(room, [_handset(player), _handset(npc)])
        self.assertIs(verdicts.get(npc.id), True)
        self.assertIs(verdicts.get(player.id), False)

    # -- the render half of the same flag --------------------------

    def test_a_carrier_is_told_it_is_their_own_radio(self):
        """`own` also picks "Your radio" over "A radio nearby".

        Same sticky-`own` fix, seen from the other side: a carrier
        collected first at somebody else's grille was told the traffic
        came from a radio NEARBY, about words coming out of a handset on
        their own belt. Rendered on the deaf branch, where the phrase
        is reachable without a reception failure.
        """
        room = _Room()
        neighbour = _Person(10, room)      # collected first, lower dbref
        carrier = _Person(20, room)

        speaker_device = _handset(_speaker())
        speaker = _speaker()
        speaker_device.location = speaker
        with patch.object(radio, "_all_powered_radios",
                          return_value=[speaker_device,
                                        _handset(neighbour),
                                        _handset(carrier)]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=False):
            transmit(speaker, "all units, respond", speaker_device)

        line = carrier.msg.call_args_list[-1].args[0]
        self.assertIn("Your radio", line)
        self.assertNotIn("A radio nearby", line)

    def test_a_true_bystander_is_still_told_it_is_nearby(self):
        """The control: sticky-`own` must not make everyone an owner."""
        room = _Room()
        bystander = _Person(10, room)
        carrier = _Person(20, room)

        speaker_device = _handset(_speaker())
        speaker = _speaker()
        speaker_device.location = speaker
        with patch.object(radio, "_all_powered_radios",
                          return_value=[speaker_device, _handset(carrier)]), \
                patch.object(radio, "_comms_bots_on", return_value=[]), \
                patch.object(radio, "_log_to_channel"), \
                patch("world.perception.can_hear", return_value=False):
            transmit(speaker, "all units, respond", speaker_device)

        self.assertIn("A radio nearby",
                      bystander.msg.call_args_list[-1].args[0])
        self.assertIn("Your radio",
                      carrier.msg.call_args_list[-1].args[0])
