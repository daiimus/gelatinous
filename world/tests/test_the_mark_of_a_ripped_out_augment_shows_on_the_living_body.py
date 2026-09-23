"""The mark of a ripped-out augment shows on the living body (#3493).

#3491 takes an augment's prose down when its chrome is harvested. The
living renderer then never visited the tail at all: it walks the species
display order plus locations that still hold a longdesc key, so a
container the medical state knows but no prose names rendered nothing --
not even the `harvested` wound the removal recorded there. The corpse
already renders it (#3379). Same gap, same fix: every container the
medical state knows joins the walk, species order first; the
standalone-wound path renders the surgery mark.
"""
from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.procedures import (
    _mark_organ_removed, _resolve_install_augment, open_incision,
)
from world.tests import test_anatomy_augments as TA


class TheMarkOfARippedOutAugmentShowsOnTheLivingBodyTest(EvenniaTest):

    def _patient_with_a_ripped_out_tail(self):
        pat = create_object("typeclasses.characters.Character", key="Patient", location=self.room1)
        pat.db.species = "human"
        open_incision(pat, "back")
        with patch("world.medical.procedures.roll_procedure", return_value={"outcome": "success"}):
            _resolve_install_augment(TA._surgeon(), pat, organ_item=TA._tail_item(), location="back")
        self.assertIn("tail", pat.longdesc, "fixture: install did not surface the tail")
        _mark_organ_removed(pat, "cybernetic_tailbone")
        self.assertNotIn("tail", pat.longdesc, "fixture: #3491 did not drop the prose")
        return pat

    def _rendered(self, pat):
        return {loc: text for loc, text in pat._get_visible_body_descriptions(looker=pat)}

    def test_the_socket_renders_where_the_tail_was(self):
        pat = self._patient_with_a_ripped_out_tail()
        rendered = self._rendered(pat)
        self.assertIn("tail", rendered, "the tail location was never visited: %r" % sorted(rendered))
        # `WOUND_DESCRIPTIONS["fresh"]` is FOUR variants chosen at random and
        # only two say "lifted free", so pinning that phrase passed about
        # half the time. What every variant states -- and what the socket
        # exists to show -- is which organ left, and from where.
        text = rendered["tail"]
        self.assertIn("tailbone", text, "the missing organ is not named: %r" % text)
        self.assertIn("tail", text, "the location is not named: %r" % text)

    def test_the_prose_is_gone(self):
        pat = self._patient_with_a_ripped_out_tail()
        self.assertNotIn("A cybernetic tail.", " ".join(self._rendered(pat).values()))

    def test_the_tail_renders_after_the_species_order(self):
        pat = self._patient_with_a_ripped_out_tail()
        order = [loc for loc, _ in pat._get_visible_body_descriptions(looker=pat)]
        self.assertEqual(order[-1], "tail")

    # --- control -----------------------------------------------------------

    def test_an_untouched_body_renders_no_extra_locations(self):
        pat = create_object("typeclasses.characters.Character", key="Whole", location=self.room1)
        pat.db.species = "human"
        self.assertNotIn("tail", self._rendered(pat))
