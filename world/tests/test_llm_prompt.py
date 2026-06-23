"""The portable LLM prompt layer (world.llm.prompt) — backend-agnostic.

Pure functions: the OpenAI message builder (persona + tools + few-shot + turn),
the persona render, and the constrained-turn parser. No model, no Evennia.
"""

import json
from unittest import TestCase

from world.llm.prompt import (
    TURN_SCHEMA, build_messages, parse_turn, render_persona,
)

_PERSONA = {
    "sdesc": "a lithe woman",
    "voice": "a silken purr",
    "location": {"name": "the Helix Lounge"},
    "menu": ["Negroni", "Martini"],
    "persona_seed": {
        "name": "Sable",
        "description": "the bartender at the Helix Lounge.",
        "personality": "sly, watchful",
        "mes_example": [
            {"user": 'a patron says to you: "busy?"',
             "assistant": {"speech": "Define busy.", "action": "polishes a glass",
                           "tool": "none", "tool_argument": ""}},
        ],
    },
}


class TestBuildMessages(TestCase):
    def test_system_has_tools_schema_and_persona(self):
        msgs = build_messages(_PERSONA, "a lean man", "rough night?", "directed")
        sys = msgs[0]["content"]
        self.assertIn("Sable", sys)
        self.assertIn("speech", sys)        # schema fields explained
        self.assertIn("prepare_drink", sys)  # tools listed
        self.assertIn("look", sys)
        self.assertIn("Negroni", sys)        # menu

    def test_fewshot_is_json_and_turn_last(self):
        msgs = build_messages(_PERSONA, "a man", "hi", "directed")
        self.assertIn("assistant", [m["role"] for m in msgs])
        # the few-shot assistant content is the JSON schema, not prose
        asst = next(m["content"] for m in msgs if m["role"] == "assistant")
        self.assertEqual(json.loads(asst)["speech"], "Define busy.")
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertIn("hi", msgs[-1]["content"])

    def test_perception_grounds_turn(self):
        msgs = build_messages(_PERSONA, "a man", "hi", "directed",
                              perception="a stocky droog in a white shirt")
        self.assertIn("a stocky droog in a white shirt", msgs[-1]["content"])

    def test_ambient_framing(self):
        d = build_messages(_PERSONA, "a man", "hi", "directed")
        a = build_messages(_PERSONA, "a man", "hi", "ambient")
        self.assertIn("says to you", d[-1]["content"])
        self.assertIn("overhear", a[-1]["content"].lower())
        self.assertIn("OVERHEARD", a[0]["content"])

    def test_render_persona_defensive(self):
        self.assertIn("the bartender", render_persona({}))


class TestParseTurn(TestCase):
    def _t(self, **kw):
        base = {"speech": "", "action": "", "tool": "none", "tool_argument": ""}
        base.update(kw)
        return json.dumps(base)

    def test_json_turn_with_tool(self):
        out = parse_turn(self._t(speech="Coming up.", action="grabs a glass",
                                 tool="prepare_drink", tool_argument="Negroni"),
                         _PERSONA)
        self.assertEqual(out["speech"], "Coming up.")
        self.assertEqual(out["action"], "grabs a glass")
        self.assertEqual(out["tool"], "prepare_drink")
        self.assertEqual(out["tool_argument"], "Negroni")

    def test_self_lead_stripped(self):
        out = parse_turn(self._t(speech="hi", action="Sable smirks"), _PERSONA)
        self.assertEqual(out["action"], "smirks")

    def test_pov_leak_action_dropped(self):
        out = parse_turn(self._t(speech="hey", action="your eyes meet his"),
                         _PERSONA)
        self.assertIsNone(out["action"])
        self.assertEqual(out["speech"], "hey")

    def test_empty_is_null(self):
        out = parse_turn(self._t(), _PERSONA)
        self.assertIsNone(out["speech"])
        self.assertIsNone(out["action"])
        self.assertEqual(out["tool"], "none")

    def test_unknown_tool_coerced_to_none(self):
        out = parse_turn(self._t(speech="x", tool="frobnicate"), _PERSONA)
        self.assertEqual(out["tool"], "none")

    def test_ooc_speech_dropped(self):
        out = parse_turn(self._t(speech="As an AI I can't do that"), _PERSONA)
        self.assertIsNone(out["speech"])

    def test_prose_fallback(self):
        out = parse_turn('*smirks* "what now?"', _PERSONA)
        self.assertEqual(out["speech"], "what now?")
        self.assertEqual(out["action"], "smirks")
        self.assertEqual(out["tool"], "none")

    def test_schema_tool_enum(self):
        self.assertEqual(TURN_SCHEMA["properties"]["tool"]["enum"],
                         ["none", "look", "check_stock", "prepare_drink"])
