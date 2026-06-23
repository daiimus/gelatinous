"""The portable LLM prompt layer (world.llm.prompt) — backend-agnostic.

Pure functions: the OpenAI message builder (card persona + few-shot + grounded
turn), the persona render, and the reply parser. No model, no Evennia, no network.
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
        "description": "the bartender at the Helix Lounge.",
        "personality": "sly, watchful, unhurried",
        "scenario": "tending a slow night behind the bar",
        "mes_example": [
            {"user": 'a patron says to you: "busy?"',
             "assistant": '*polishes a glass.* "Define busy."'},
        ],
    },
}


class TestBuildMessages(TestCase):
    def test_system_fewshot_turn_order(self):
        msgs = build_messages(_PERSONA, "a lean man", "rough night?", "directed")
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertIn("assistant", [m["role"] for m in msgs])  # few-shot present
        self.assertIn("Sable", msgs[0]["content"])
        self.assertIn("sly, watchful", msgs[0]["content"])
        self.assertIn("rough night?", msgs[-1]["content"])

    def test_fewshot_uses_card_examples(self):
        joined = " ".join(m["content"] for m in
                          build_messages(_PERSONA, "a man", "hi", "directed"))
        self.assertIn("Define busy.", joined)  # from mes_example

    def test_perception_grounds_and_forbids_invention(self):
        msgs = build_messages(_PERSONA, "a man", "hi", "directed",
                              perception="a stocky droog in a white t-shirt")
        self.assertIn("a stocky droog in a white t-shirt", msgs[-1]["content"])
        self.assertIn("PERCEPTION", msgs[-1]["content"])
        sys = msgs[0]["content"].lower()
        self.assertIn("invent", sys)  # charter forbids inventing appearance

    def test_directed_vs_ambient_framing(self):
        directed = build_messages(_PERSONA, "a man", "hi", "directed")
        ambient = build_messages(_PERSONA, "a man", "hi", "ambient")
        self.assertIn("says to you", directed[-1]["content"])
        self.assertIn("overhear", ambient[-1]["content"].lower())
        self.assertIn("PASS", ambient[0]["content"])

    def test_backcompat_old_manner_keys(self):
        old = {"persona_seed": {"name": "X", "manner": "gruff",
                                "wants": "quiet", "boundaries": "discuss debts"}}
        self.assertIn("gruff", render_persona(old))

    def test_render_persona_is_defensive(self):
        self.assertIn("the bartender", render_persona({}))


class TestParseReply(TestCase):
    def test_clean_format_split(self):
        out = parse_reply('*Sable smirks.* "What\'s it to ya?"', _PERSONA)
        self.assertEqual(out["speech"], "What's it to ya?")
        self.assertEqual(out["action"], "smirks.")

    def test_prose_narration_becomes_pose(self):
        raw = 'Sable\'s eyes flick to the door. "We\'re closing soon," she says.'
        out = parse_reply(raw, _PERSONA)
        self.assertEqual(out["speech"], "We're closing soon,")
        self.assertIsNotNone(out["action"])
        self.assertIn("eyes flick to the door", out["action"])
        self.assertFalse(out["action"].lower().startswith("sable"))

    def test_pov_leak_action_dropped(self):
        out = parse_reply('*your eyes meet his.* "Hey."', _PERSONA)
        self.assertEqual(out["speech"], "Hey.")
        self.assertIsNone(out["action"])

    def test_speech_only(self):
        out = parse_reply('"Just a sec."', _PERSONA)
        self.assertEqual(out["speech"], "Just a sec.")
        self.assertIsNone(out["action"])

    def test_no_markers_treated_as_speech(self):
        self.assertEqual(parse_reply("rough night, huh", _PERSONA)["speech"],
                         "rough night, huh")

    def test_ooc_dropped_to_null(self):
        out = parse_reply("As an AI, I can't roleplay that.", _PERSONA)
        self.assertEqual(out, {"speech": None, "action": None})

    def test_empty_is_null(self):
        self.assertEqual(parse_reply("", _PERSONA), {"speech": None, "action": None})

    def test_pass_sentinel_is_null(self):
        for raw in ("PASS", "pass", '"PASS"', "PASS.", "*PASS*"):
            self.assertEqual(parse_reply(raw, _PERSONA),
                             {"speech": None, "action": None}, raw)

    def test_decline_narration_is_null(self):
        out = parse_reply("Sable does not react to the comment.", _PERSONA)
        self.assertEqual(out, {"speech": None, "action": None})

    def test_quoted_line_with_decline_word_still_speaks(self):
        out = parse_reply('"No response from the docks, last I heard."', _PERSONA)
        self.assertEqual(out["speech"], "No response from the docks, last I heard.")
