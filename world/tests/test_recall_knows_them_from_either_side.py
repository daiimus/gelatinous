"""`Also known as` reads the same from either face (#2651).

`get_linked_aliases` walked `linked_to` FORWARD only, which is right for
`walk_linked_chain`'s own job — the unmasking path points a new
presentation back at the one it replaced, so walking from the face in
front of you reaches their history.

But identity is symmetric and recall must be too. If you knew somebody
as A, met them again as B (B -> A) and then looked at A, a forward walk
from A reached nothing, and what they told you as B was unrecallable
purely because of which face you happened to be looking at.

`linked_family` was written to close exactly this (#2410). It had one
caller — the LLM NPC path — and the player's own `recall` never got it.
"""
from evennia.utils.test_resources import EvenniaTest

from world.identity import get_linked_aliases


def _memory():
    """A knew them as "Fen", then met the same body presenting as "Wick",
    and the unmask pointed WICK at FEN."""
    return {
        "uid-fen": {"assigned_name": "Fen"},
        "uid-wick": {"assigned_name": "Wick", "linked_to": "uid-fen"},
    }


class TestEitherFaceGivesTheSameAnswer(EvenniaTest):

    def test_the_forward_direction_still_works(self):
        """Control: the direction that always worked. If the walk were
        simply broken, the symmetric assertion below would pass for the
        wrong reason."""
        self.assertEqual(get_linked_aliases(_memory(), "uid-wick"), ["Fen"])

    def test_and_so_does_the_backward_one(self):
        self.assertEqual(
            get_linked_aliases(_memory(), "uid-fen"), ["Wick"],
            "looking at the older face forgot the newer one")

    def test_a_stranger_has_no_aliases(self):
        """Control: it must not be answering 'everyone' now."""
        memory = _memory()
        memory["uid-stranger"] = {"assigned_name": "Nobody"}
        self.assertEqual(get_linked_aliases(memory, "uid-stranger"), [])
        self.assertNotIn("Nobody", get_linked_aliases(memory, "uid-fen"))

    def test_a_three_link_family_closes_from_the_middle(self):
        memory = {
            "a": {"assigned_name": "Aay"},
            "b": {"assigned_name": "Bee", "linked_to": "a"},
            "c": {"assigned_name": "Cee", "linked_to": "b"},
        }
        self.assertEqual(sorted(get_linked_aliases(memory, "b")),
                         ["Aay", "Cee"])

    def test_the_order_is_the_order_you_met_them(self):
        """`linked_family` returns a SET, whose iteration order is
        arbitrary and not stable across restarts. Ordering by the
        observer's own memory is deterministic and is the order a
        person would say the names in."""
        memory = {
            "first": {"assigned_name": "First"},
            "second": {"assigned_name": "Second", "linked_to": "first"},
            "third": {"assigned_name": "Third", "linked_to": "second"},
        }
        self.assertEqual(get_linked_aliases(memory, "second"),
                         ["First", "Third"])

    def test_a_blank_name_is_omitted(self):
        memory = _memory()
        memory["uid-wick"]["assigned_name"] = "   "
        self.assertEqual(get_linked_aliases(memory, "uid-fen"), [])

    def test_an_unknown_uid_is_empty(self):
        self.assertEqual(get_linked_aliases(_memory(), "uid-nothing"), [])

    def test_a_cycle_does_not_hang(self):
        memory = {
            "a": {"assigned_name": "Aay", "linked_to": "b"},
            "b": {"assigned_name": "Bee", "linked_to": "a"},
        }
        self.assertEqual(get_linked_aliases(memory, "a"), ["Bee"])
