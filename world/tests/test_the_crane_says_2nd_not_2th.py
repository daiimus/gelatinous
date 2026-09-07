"""The mast's two lowest floors have names (#2472, #2446).

Both the crane's radio voice and the container's own prose wrote
``f"the {floor}th"`` unconditionally. The Boiler Run mast runs from the
2nd to the 17th, so the two lowest floors announced themselves as
**"the 2th"** and **"the 3th"** — including in the read-back that asks a
caller to confirm a move while people are standing in the car.

Seven sites, two files. `#2446` reported it for
`CraneContainer.move_to_level`; `#2472` found the same defect in the
console's read-back. A fix touching only `rooms.py` would have left the
radio voice still saying "the 3th", which is why both are done together
and why the arithmetic now lives in one place.

`ordinal` is in `world/grammar.py` beside the rest of the language
machinery rather than in either caller — it is the kind of thing a third
site will want. The teens are the whole difficulty: 11, 12 and 13 take
`th` despite ending in 1, 2 and 3.

**Left open deliberately:** #2472's main finding, that a bare
"confirmed" never reaches the confirmation branch because the address
gate returns first. That one is a design question — whether the crane
should accept an unaddressed "yes" inside the read-back window — and is
asked rather than answered.
"""
from evennia.utils.test_resources import EvenniaTest


def ordinal(n):
    """Imported lazily inside the helper so this module still LOADS
    against the unfixed tree — otherwise every test in it errors on a
    missing import and the source-pinning tests below prove nothing."""
    from world.grammar import ordinal as _ordinal
    return _ordinal(n)


class TestTheSuffix(EvenniaTest):
    def test_the_two_that_were_wrong(self):
        self.assertEqual((ordinal(2), ordinal(3)), ("2nd", "3rd"))

    def test_the_rest_of_the_mast(self):
        self.assertEqual([ordinal(n) for n in range(4, 18)],
                         ["4th", "5th", "6th", "7th", "8th", "9th", "10th",
                          "11th", "12th", "13th", "14th", "15th", "16th",
                          "17th"])

    def test_the_teens_are_not_st_nd_rd(self):
        """11/12/13 end in 1/2/3 and still take `th`."""
        self.assertEqual([ordinal(n) for n in (11, 12, 13)],
                         ["11th", "12th", "13th"])

    def test_it_keeps_counting_past_the_mast(self):
        self.assertEqual([ordinal(n) for n in (21, 22, 23, 101, 111)],
                         ["21st", "22nd", "23rd", "101st", "111th"])

    def test_one(self):
        self.assertEqual(ordinal(1), "1st")


class TestNoSourceStillSaysNth(EvenniaTest):
    """Pinned against the file, because this defect's whole nature is a
    hard-coded suffix that reads fine until you look at floor 2."""

    def _source(self, relpath):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return (root / relpath).read_text(errors="ignore")

    def test_the_console_has_no_hard_coded_suffix(self):
        self.assertNotIn("}th", self._source("typeclasses/crane.py"))

    def test_the_container_has_no_hard_coded_suffix(self):
        self.assertNotIn("}th", self._source("typeclasses/rooms.py"))


class TestTheVoiceReadsRight(EvenniaTest):
    """Through the strings the console actually speaks."""

    def test_the_read_back_at_the_second(self):
        floor = 2
        self.assertEqual(f"That puts her at the {ordinal(floor)}. Confirm?",
                         "That puts her at the 2nd. Confirm?")

    def test_the_copy_at_the_third(self):
        floor = 3
        self.assertEqual(f"Copy, the {ordinal(floor)}. Bringing her up",
                         "Copy, the 3rd. Bringing her up")

    def test_the_landing_at_the_seventeenth(self):
        floor = 17
        self.assertEqual(f"Held at the {ordinal(floor)}. Watch your footing.",
                         "Held at the 17th. Watch your footing.")

    def test_the_container_prose_at_the_second(self):
        z = 1
        self.assertEqual(f"settles at the {ordinal(z + 1)} floor.",
                         "settles at the 2nd floor.")
