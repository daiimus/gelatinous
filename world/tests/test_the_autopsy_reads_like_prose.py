"""An autopsy renders prose, not template tokens (#2659).

`_render_wound_lines` holds the corpse and called the wound renderer
without passing it, so two things that depend on the body never ran: the
pronoun substitution and the species routing.

    get_wound_description(injury_type="cut", location="face",
                          severity="Severe", stage="destroyed",
                          organ=None, character=None)

    -> '|R{Their}  is split open, the flesh cleaved through and weeping.|n'

TWO FAULTS IN THAT ONE LINE, and the issue attributes the second to the
wrong token. The literal `{Their}` is the missing character. The doubled
space is not the location — it is `{organ}`.

`DESTROYED_BY_LOCATION` overlays are keyed by LOCATION and their prose
says "{their} {organ}", because at a sensory surface the organ IS the
thing at that location. A wound snapshot for a face carries no organ, so
`{organ}` rendered empty:

    'A cleaving cut has bisected their , leaving a deep ragged gash.'

An empty token is never the right answer there — every template using
`{organ}` is describing something, and when no organ was named, the
location is what that something is.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.medical.wounds import get_wound_description


class TestThePronounIsSubstituted(EvenniaTest):

    def body(self, species="human"):
        who = create_object("typeclasses.characters.Character",
                            key="the deceased", location=self.room1)
        who.db.species = species
        return who

    def test_no_raw_token_survives(self):
        text = get_wound_description(
            injury_type="cut", location="face", severity="Severe",
            stage="destroyed", organ=None, character=self.body())
        for token in ("{Their}", "{their}", "{organ}", "{location}",
                      "{severity}"):
            self.assertNotIn(token, text, text)

    def test_without_a_body_the_token_survives(self):
        """Control: the renderer really does depend on the character —
        so passing it is what fixed the autopsy, not luck elsewhere."""
        text = get_wound_description(
            injury_type="cut", location="face", severity="Severe",
            stage="destroyed", organ=None, character=None)
        self.assertIn("{", text)


class TestTheOrganTokenFallsBackToTheLocation(EvenniaTest):

    def body(self):
        who = create_object("typeclasses.characters.Character",
                            key="the deceased", location=self.room1)
        who.db.species = "human"
        return who

    def test_a_location_overlay_names_the_location(self):
        text = get_wound_description(
            injury_type="cut", location="face", severity="Severe",
            stage="destroyed", organ=None, character=self.body())
        self.assertIn("face", text, text)

    def test_no_empty_gap_is_left(self):
        """The visible symptom: 'bisected their , leaving'."""
        for _ in range(12):
            text = get_wound_description(
                injury_type="cut", location="face", severity="Severe",
                stage="destroyed", organ=None, character=self.body())
            self.assertNotIn(" ,", text, text)
            self.assertNotIn("  ", text, text)

    def test_a_named_organ_still_wins(self):
        """Control: the fallback must not overwrite a real organ."""
        text = get_wound_description(
            injury_type="cut", location="face", severity="Severe",
            stage="destroyed", organ="left_eye", character=self.body())
        self.assertIn("left eye", text, text)


class TestTheSpeciesRoutes(EvenniaTest):
    """The other half of passing the body: a robot does not bleed, and a
    species with a registered pack renders ALL its wound prose from it,
    so human flesh vocabulary can never leak onto the wrong chassis."""

    def body(self, species):
        who = create_object("typeclasses.characters.Character",
                            key="the deceased", location=self.room1)
        who.db.species = species
        return who

    def test_a_species_with_a_pack_uses_it(self):
        from world.medical.wounds import messages
        for species in ("robot", "synth", "synthetic_humanoid"):
            if messages.species_pack(self.body(species)) is None:
                continue
            human = get_wound_description(
                injury_type="cut", location="chest", severity="Severe",
                stage="fresh", organ=None, character=self.body("human"))
            other = get_wound_description(
                injury_type="cut", location="chest", severity="Severe",
                stage="fresh", organ=None, character=self.body(species))
            self.assertNotEqual(
                human, other,
                f"{species} rendered the same prose as a human")
            return
        self.skipTest("no species pack registered in this tree")


class TestTheAutopsyPassesTheBody(EvenniaTest):

    def test_the_call_site_passes_character(self):
        """Structural, because the section only renders for a corpse
        carrying a `wounds_at_death` snapshot and building one here
        would test the fixture rather than the omission."""
        import inspect

        from world import forensics
        source = inspect.getsource(forensics._render_wound_lines)
        self.assertIn("character=corpse", source,
                      "the renderer is still called without the body")
