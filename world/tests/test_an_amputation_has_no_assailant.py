"""A severance with no attacker still narrates, and reads correctly.

Regression pin for #2753. `observer_char_refs` passed `attacker`
straight through, and off the combat path it is None -- it comes from
`ndb._last_damage_attacker`, which only the attack path sets. The
template's `{actor}` is live by then, so a chart-driven amputation meant
`None.get_display_name(...)` and a fall back to the legacy beat.

Three of the function's four outputs already guarded the same absence
("someone" / "Someone"); this was the one that did not.

A STAND-IN rather than a literal, because `{actor}` appears both leading
a sentence and mid-sentence across the templates. It renders lowercase,
so the broadcast layer capitalises it exactly where it opens one
(#2641):

    Someone's saw parts a gaunt man's arm.
    Bone parts under someone's saw, and a gaunt man screams.
"""

from unittest import TestCase
from unittest.mock import MagicMock

from world.combat.messages.severance import get_severance_message


def _target():
    t = MagicMock()
    t.key = "Patient"
    t.get_display_name = lambda looker=None, **k: "a gaunt man"
    return t


def _message(attacker):
    item = MagicMock()
    item.key = "bone saw"
    return get_severance_message(attacker=attacker, target=_target(),
                                 item=item, location="left_arm",
                                 is_cybernetic=False)


class TestAnAmputationHasNoAssailant(TestCase):

    def test_an_absent_attacker_yields_a_usable_ref(self):
        refs = _message(None)["observer_char_refs"]
        self.assertIsNotNone(refs["actor"])
        self.assertEqual(refs["actor"].get_display_name(None), "someone")

    def test_the_stand_in_is_lowercase(self):
        """So the broadcast layer can capitalise it by POSITION; a
        baked-in literal could not be right in both places.

        Bound off the module, not imported — an import of a name the
        unfixed tree lacks makes this whole FILE error, which destroys
        every control in it.
        """
        import world.combat.messages.severance as mod

        someone = getattr(mod, "_SOMEONE", None)
        self.assertIsNotNone(
            someone, "there is no stand-in for an absent attacker")
        self.assertEqual(someone.get_display_name(None), "someone")

    def test_the_target_is_still_identity_resolved(self):
        refs = _message(None)["observer_char_refs"]
        self.assertEqual(
            refs["target_char"].get_display_name(None), "a gaunt man")

    def test_a_real_attacker_is_passed_through(self):
        """The control — the stand-in must not replace a real one."""
        attacker = MagicMock()
        attacker.key = "Surgeon"
        refs = _message(attacker)["observer_char_refs"]
        self.assertIs(refs["actor"], attacker)
