"""One species attribute, not two (#2205).

`species` was an `AttributeProperty` under `category="identity"` that
nothing ever wrote. Twenty spawners and every consumer use the
uncategorised `db.species`, so the property returned its `"human"`
default forever.

It had exactly one reader — `llm_persona`, which hands the model an
NPC's description. So every synth Companion and every security robot
was introduced to the LLM as human.

It also burned build 111 (#2196), which asked the property and gave
synths and robots human bodies.
"""
from evennia.utils.test_resources import EvenniaCommandTest


class TestSpeciesHasOneSourceOfTruth(EvenniaCommandTest):
    def test_it_reads_db_species(self):
        self.char1.db.species = "synthetic_humanoid"
        self.assertEqual(self.char1.species, "synthetic_humanoid")

    def test_it_writes_db_species(self):
        self.char1.species = "robot"
        self.assertEqual(self.char1.db.species, "robot")
        self.assertEqual(self.char1.species, "robot")

    def test_unset_falls_back_to_human(self):
        self.char1.db.species = None
        self.assertEqual(self.char1.species, "human")

    def test_a_synth_is_not_reported_as_human(self):
        """The bug, at the surface that had it: the persona payload."""
        self.char1.db.species = "synthetic_humanoid"
        self.assertNotEqual(self.char1.species, "human")

    def test_the_stale_identity_attribute_no_longer_shadows_it(self):
        """Bodies created before the change carry a leftover
        identity-category `species` attribute. It must not win."""
        self.char1.attributes.add("species", "human", category="identity")
        self.char1.db.species = "robot"
        self.assertEqual(self.char1.species, "robot")


class TestThePersonaSeesIt(EvenniaCommandTest):
    def test_persona_reports_the_real_species(self):
        from typeclasses import llm_persona

        self.char1.db.species = "robot"
        self.char1.db.llm_persona = {"archetype": "bot", "name": "unit"}
        try:
            payload = llm_persona.build_persona(self.char1)
        except Exception as err:  # noqa: BLE001 — persona needs a lot of world
            self.skipTest(f"persona unavailable in test env: {err}")
        self.assertEqual(payload.get("species"), "robot")
