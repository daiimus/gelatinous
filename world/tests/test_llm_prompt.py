"""The portable LLM prompt layer (world.llm.prompt) — backend-agnostic.

Pure functions: the OpenAI-style message builder, the persona render, and the
reply parser. No model, no Evennia, no network — these travel with the repo so the
inference backend stays swappable.
"""

from unittest import TestCase

from world.llm.prompt import build_messages, parse_reply, render_persona

_PERSONA = {
    "sdesc": "a lithe woman",
    "skintone": "olive",
    "voice": "speaking Common, in a silken purr",
    "location": {"name": "the Helix Lounge"},
    "persona_seed": {
        "name": "Sable",
        "manner": "sly, watchful",
        "wants": "to read everyone who sits down",
        "boundaries": "won't discuss the owner's debts",
    },
}


class TestBuildMessages(TestCase):
    def test_openai_message_shape(self):
        msgs = build_messages(_PERSONA, "a lean man", "rough night?", "directed")
        self.assertEqual([m["role"] for m in msgs], ["system", "user"])
        self.assertIn("Sable", msgs[0]["content"])
        self.assertIn("sly, watchful", msgs[0]["content"])
        self.assertIn("a lean man", msgs[1]["content"])
        self.assertIn("rough night?", msgs[1]["content"])

    def test_directed_vs_ambient_framing(self):
        directed = build_messages(_PERSONA, "a man", "hi", "directed")
        ambient = build_messages(_PERSONA, "a man", "hi", "ambient")
        self.assertIn("says to you", directed[1]["content"])
        self.assertIn("overhear", ambient[1]["content"].lower())
        # ambient charter tells the model it may decline
        self.assertIn("OVERHEARD", ambient[0]["content"])
        self.assertNotIn("OVERHEARD", directed[0]["content"])

    def test_render_persona_is_defensive(self):
        # a near-empty persona still renders without raising
        self.assertIn("the bartender", render_persona({}))


class TestParseReply(TestCase):
    def test_speech_and_action_split(self):
        raw = '*Sable smirks.* "What\'s it to ya?"'
        out = parse_reply(raw, _PERSONA)
        self.assertEqual(out["speech"], "What's it to ya?")
        # leading self-reference stripped (the game prepends the name via pose)
        self.assertEqual(out["action"], "smirks.")

    def test_speech_only(self):
        out = parse_reply('"Just a sec."', _PERSONA)
        self.assertEqual(out["speech"], "Just a sec.")
        self.assertIsNone(out["action"])

    def test_no_markers_treated_as_speech(self):
        out = parse_reply("rough night, huh", _PERSONA)
        self.assertEqual(out["speech"], "rough night, huh")

    def test_ooc_dropped_to_null(self):
        out = parse_reply("As an AI, I can't roleplay that.", _PERSONA)
        self.assertEqual(out, {"speech": None, "action": None})

    def test_empty_is_null(self):
        self.assertEqual(parse_reply("", _PERSONA), {"speech": None, "action": None})

    def test_pass_sentinel_is_null(self):
        for raw in ("PASS", "pass", '"PASS"', "PASS.", "*PASS*"):
            self.assertEqual(
                parse_reply(raw, _PERSONA), {"speech": None, "action": None}, raw
            )

    def test_decline_narration_is_null(self):
        # ambient decline narrated as prose (no quotes) → silence, not a spoken line
        out = parse_reply("Sable does not react to the comment.", _PERSONA)
        self.assertEqual(out, {"speech": None, "action": None})

    def test_quoted_line_with_decline_word_still_speaks(self):
        # a real quoted line that merely contains a decline word still renders
        out = parse_reply('"No response from the docks, last I heard."', _PERSONA)
        self.assertEqual(out["speech"], "No response from the docks, last I heard.")
