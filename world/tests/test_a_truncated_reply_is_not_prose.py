"""A cut-off JSON reply is still JSON, not prose.

Regression pin for #2729. A truncated model response fails
`json.loads` and used to fall straight into `_parse_prose` -- which
pulls QUOTED RUNS out as dialogue. In a cut-off object the first quoted
runs are the SCHEMA'S OWN KEY NAMES, so:

    '{"speech": "Evening. What can I get y'
      -> speech: 'speech'
      -> action: '{: Evening. What can I get y'

The NPC said the word "speech" out loud and posed as JSON punctuation.
Measured at ~9% of 2,458 logged turns -- including the Rook broadcasting
"speech" on air.

`_salvage_json` recovers the fields from a cut-off object, and returns
None for anything not JSON-shaped so genuine prose still reaches the
prose parser (the few-shot and fallback paths depend on it).
"""

from unittest import TestCase

from world.llm.prompt import parse_turn

PERSONA = {"persona_seed": {"name": "Sully"}}


class TestATruncatedReplyIsNotProse(TestCase):

    def _turn(self, raw):
        return parse_turn(raw, PERSONA)

    def test_a_cut_off_speech_keeps_its_words(self):
        t = self._turn('{"speech": "Evening. What can I get y')
        self.assertEqual(t.get("speech"), "Evening. What can I get y")

    def test_the_key_name_is_never_spoken(self):
        for raw in ('{"speech": "Evening. What can I get y',
                    '{"speech": "Evening.", "action": "wipes the bar", "thou'):
            with self.subTest(raw[:30]):
                said = (self._turn(raw).get("speech") or "")
                self.assertFalse(said.startswith("speech"), said)
                self.assertNotIn("action", said)

    def test_json_punctuation_is_never_posed(self):
        t = self._turn('{"speech": "Evening.", "action": "wipes the bar", "thou')
        self.assertEqual(t.get("action"), "wipes the bar")
        self.assertNotIn("{", t.get("action") or "")

    # -- controls ----------------------------------------------------

    def test_whole_json_is_unaffected(self):
        t = self._turn(
            '{"speech": "Long day.", "action": "nods", "thought": "tired"}')
        self.assertEqual(t.get("speech"), "Long day.")
        self.assertEqual(t.get("action"), "nods")

    def test_genuine_prose_still_reaches_the_prose_parser(self):
        """The few-shot and fallback paths depend on it."""
        t = self._turn('He nods. "Evening."')
        self.assertEqual(t.get("speech"), "Evening.")
        self.assertIn("nods", t.get("action") or "")

    def test_a_non_json_string_is_not_salvaged(self):
        import world.llm.prompt as mod

        # Bound off the module so an unfixed tree reports the MISSING
        # salvage as a named failure rather than an ImportError.
        salvage = getattr(mod, "_salvage_json", None)
        self.assertIsNotNone(
            salvage, "world.llm.prompt._salvage_json is missing, so a "
                     "truncated reply still falls into the prose parser")
        self.assertIsNone(salvage('He nods. "Evening."'))
        self.assertIsNone(salvage(""))
