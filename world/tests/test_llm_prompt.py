"""The portable LLM prompt layer (world.llm.prompt) — backend-agnostic.

Pure functions: the OpenAI message builder (persona + tools + few-shot + turn),
the persona render, and the constrained-turn parser. No model, no Evennia.
"""

import json
from unittest import TestCase

from world.llm.prompt import (
    ARCHETYPES, BASE_TOOLS, CONTEXT_TOOLS, TOOLS, TURN_SCHEMA, _archetype,
    build_messages, parse_turn, render_persona, schema_for, tool_names,
    turn_schema,
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


class TestArchetype(TestCase):
    def test_empty_persona_defaults_to_bartender(self):
        self.assertIs(_archetype({}), ARCHETYPES["bartender"])

    def test_archetype_injects_duties_and_scopes_tools(self):
        msgs = build_messages(_PERSONA, "a man", "hi", "directed")
        sys = msgs[0]["content"]
        self.assertIn("YOUR WORK", sys)        # archetype duties block
        self.assertIn("prepare_drink", sys)    # bartender tool granted

    def test_unknown_archetype_falls_back(self):
        p = dict(_PERSONA, persona_seed=dict(_PERSONA["persona_seed"],
                                             archetype="nonesuch"))
        self.assertIs(_archetype(p), ARCHETYPES["bartender"])

    def test_archetype_fewshot_used_when_no_mes_example(self):
        # persona without its own examples borrows the archetype's banter
        p = {"persona_seed": {"name": "Rix", "archetype": "bartender"}}
        msgs = build_messages(p, "a man", "hi", "directed")
        self.assertIn("assistant", [m["role"] for m in msgs])

    def test_mapping_mes_example_is_json_safe(self):
        # DB-sourced examples arrive as a Mapping (Evennia _SaverDict), not a
        # plain dict — few_shot_messages must rebuild a json-serializable turn.
        from collections.abc import Mapping

        class FakeSaver(Mapping):  # mimics _SaverDict: a Mapping, not a dict
            def __init__(self, d): self._d = d
            def __getitem__(self, k): return self._d[k]
            def __iter__(self): return iter(self._d)
            def __len__(self): return len(self._d)

        p = {"persona_seed": {"name": "Sable", "archetype": "bartender",
             "mes_example": [FakeSaver({
                 "user": 'a patron says to you: "hi"',
                 "assistant": FakeSaver({"speech": "Hey.", "action": "nods",
                                         "tool": "none", "tool_argument": ""})})]}}
        msgs = build_messages(p, "a man", "hi", "directed")  # must not raise
        asst = next(m["content"] for m in msgs if m["role"] == "assistant")
        self.assertEqual(json.loads(asst)["speech"], "Hey.")


class TestToolScoping(TestCase):
    def setUp(self):
        # a throwaway social archetype: no job tools → BASE (look) only.
        ARCHETYPES["_test_social"] = {"duties": "You loiter.", "tools": [],
                                      "fewshot": []}
        self.addCleanup(lambda: ARCHETYPES.pop("_test_social", None))
        self.social = {"persona_seed": {"name": "Vex", "archetype": "_test_social"}}

    def test_context_tools_derived_from_registry(self):
        # read-only tools loop; the action tool (prepare_drink) is excluded.
        self.assertIn("look", CONTEXT_TOOLS)
        self.assertIn("check_stock", CONTEXT_TOOLS)
        self.assertNotIn("prepare_drink", CONTEXT_TOOLS)

    def test_base_tool_always_granted(self):
        # every archetype perceives, even one declaring no job tools.
        self.assertEqual(tool_names(self.social), list(BASE_TOOLS))
        self.assertIn("look", tool_names(self.social))

    def test_bartender_grants_its_job_tools_plus_base(self):
        names = tool_names(_PERSONA)  # bartender archetype
        self.assertEqual(names, ["look", "check_stock", "prepare_drink"])

    def test_schema_scoped_to_archetype(self):
        # the social archetype's schema can't even express prepare_drink.
        enum = schema_for(self.social)["properties"]["tool"]["enum"]
        self.assertEqual(enum, ["none", "look"])
        self.assertNotIn("prepare_drink", enum)

    def test_turn_schema_builder(self):
        self.assertEqual(turn_schema(["look"])["properties"]["tool"]["enum"],
                         ["none", "look"])

    def test_social_prompt_omits_bartender_tools(self):
        sys = build_messages(self.social, "a man", "hi", "directed")[0]["content"]
        self.assertIn("look", sys)
        self.assertNotIn("prepare_drink", sys)

    def test_parse_coerces_out_of_scope_tool(self):
        # a tool outside the archetype's grant is coerced to none.
        raw = json.dumps({"speech": "x", "action": "", "tool": "prepare_drink",
                          "tool_argument": "Negroni"})
        out = parse_turn(raw, self.social, allowed_tools=tool_names(self.social))
        self.assertEqual(out["tool"], "none")

    def test_parse_keeps_in_scope_tool(self):
        raw = json.dumps({"speech": "", "action": "", "tool": "look",
                          "tool_argument": "patron"})
        out = parse_turn(raw, self.social, allowed_tools=tool_names(self.social))
        self.assertEqual(out["tool"], "look")


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
