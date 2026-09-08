"""`advance` and `charge` stop being a presence oracle (#2447).

Two doors onto one decision, in the same module, that had stopped
reading the same line:

* `resolve_character_target` applies the presence gate —
  `candidates = filter_present(caller, candidates)`, under the comment
  *"Presence gate (stealth spec §7)"*. That is what `attack` uses.
* `resolve_character_in_rooms`, its cross-room sibling used by
  `advance` and `charge`, built `candidates = list(room.contents)` and
  went straight into `identity_match_characters` with no gate at all.

So `advance <guessed sdesc>` answered *"A lean man is not in combat."*
for a character the caller is Unaware of — someone absent from their
`look`. The refusal **confirmed the hidden character existed and
rendered their sdesc**, because `get_display_name` has no stealth
branch. A presence oracle built out of an error message, and generic
keywords ("man", "woman", "figure") make it workable. `attack` refuses
the same input correctly with "you cannot find".

`filter_present`'s own docstring calls itself *"the single enumeration
choke (leak-completeness discipline): every path that lists 'who is
here' for a looker filters through this."* The Phase-3 leak sweep
enumerated the swept paths and named only the sibling; the cross-room
helper was missed.

**Scope kept deliberately small.** The issue also proposed moving the
charge grapple-branch announcement after the combat-membership check.
Not done, and not needed for the leak: a hidden character no longer
matches, so that branch is never reached with one. Reordering messages
inside a live combat flow is a change to combat, and this fix is one
line in a targeting helper that touches no combat code.

Real characters rather than the mocks the neighbouring suite uses,
because the whole question is what `is_hidden_from` does with a real
`db.hidden` and a real awareness level. (Its `is not True` identity
check is also why adding the gate did not break the eight existing
mock-based cross-room tests.)
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands._identity_targeting import (
    resolve_character_in_rooms,
    resolve_character_target,
)
from world.stealth import ALERT, set_awareness


class _ScanCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.char1.location = self.room1
        # A body in the ADJACENT room — the cross-room scan is the whole
        # point of the helper under test.
        self.bystander = create_object("typeclasses.characters.Character",
                                       key="Jorge Jackson",
                                       location=self.room2)
        self.bystander.height = "tall"
        self.bystander.build = "lean"
        self.bystander.sdesc_keyword = "man"
        self.rooms = [self.room1, self.room2]

    def scan(self, phrase="man"):
        return resolve_character_in_rooms(self.char1, phrase, self.rooms)

    def hide(self, char):
        char.db.hidden = True


class TestAVisibleTargetStillResolves(_ScanCase):
    """The gate must not cost the command its actual job."""

    def test_found_across_rooms(self):
        self.assertIs(self.scan(), self.bystander)

    def test_found_in_the_callers_own_room(self):
        self.bystander.location = self.room1
        self.assertIs(self.scan(), self.bystander)

    def test_a_nonsense_phrase_still_finds_nothing(self):
        self.assertIsNone(self.scan("zephyr"))


class TestAHiddenBystanderIsNotFound(_ScanCase):
    def test_the_scan_returns_nothing(self):
        self.hide(self.bystander)
        self.assertIsNone(self.scan())

    def test_hidden_in_the_callers_own_room_too(self):
        self.hide(self.bystander)
        self.bystander.location = self.room1
        self.assertIsNone(self.scan())

    def test_the_two_doors_now_agree(self):
        """The defect in one sentence: `attack` refused and `advance`
        did not."""
        self.hide(self.bystander)
        self.bystander.location = self.room1
        self.assertIsNone(resolve_character_target(self.char1, "man"))
        self.assertIsNone(self.scan())

    def test_a_visible_body_beside_a_hidden_one_still_resolves(self):
        """The gate filters the hidden candidate, not the room."""
        self.hide(self.bystander)
        seen = create_object("typeclasses.characters.Character",
                             key="Viktor Kozlov", location=self.room2)
        seen.height = "tall"
        seen.build = "lean"
        seen.sdesc_keyword = "man"
        self.assertIs(self.scan(), seen)


class TestConcealmentIsNotInvulnerability(_ScanCase):
    """Detection is the precondition, not an exemption — an ALERT
    observer has already placed them and may target them."""

    def test_an_alert_caller_can_still_resolve_them(self):
        self.hide(self.bystander)
        set_awareness(self.char1, self.bystander, ALERT)
        self.assertIs(self.scan(), self.bystander)

    def test_and_the_sibling_agrees_there_too(self):
        self.hide(self.bystander)
        self.bystander.location = self.room1
        set_awareness(self.char1, self.bystander, ALERT)
        self.assertIs(resolve_character_target(self.char1, "man"),
                      self.bystander)


class TestStaffGetNoBackDoor(_ScanCase):
    """The sibling applies the gate BEFORE its builder fallback, so this
    one does too — matching it is the point of the fix."""

    def test_the_gate_precedes_the_builder_fallback(self):
        import inspect
        src = inspect.getsource(resolve_character_in_rooms)
        self.assertLess(src.index("filter_present"),
                        src.index("_builder_key_matches"))
