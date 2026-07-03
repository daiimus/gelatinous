"""Tests for the security-unit LLM persona: the archetype spine, the
stock seed, and the rendered prompt."""

from __future__ import annotations

from unittest import TestCase

from world.llm.personas import SECURITY_BOT_PERSONA
from world.llm.prompt import ARCHETYPES, build_messages


class TestSecurityArchetype(TestCase):
    def test_registered_with_required_keys(self):
        self.assertIn("security", ARCHETYPES)
        arch = ARCHETYPES["security"]
        for key in ("duties", "length", "tools", "fewshot"):
            self.assertIn(key, arch)
        # combat/detain stays deterministic; `release` (end a chat) is the
        # one conversational action it owns.
        self.assertEqual(arch["tools"], ["release"])

    def test_fewshot_is_machine_register(self):
        shots = ARCHETYPES["security"]["fewshot"]
        self.assertTrue(shots)
        joined = str(shots).lower()
        self.assertIn("restricted", joined)
        self.assertIn("optics", joined)


class TestSecuritySeed(TestCase):
    def test_seed_selects_security_archetype(self):
        self.assertEqual(SECURITY_BOT_PERSONA["archetype"], "security")
        for key in ("name", "description", "personality", "manner",
                    "wants", "boundaries", "scenario"):
            self.assertTrue(SECURITY_BOT_PERSONA.get(key), key)

    def test_system_prompt_speaks_machine(self):
        persona = {
            "sdesc": "a battered sentry robot",
            "persona_seed": dict(SECURITY_BOT_PERSONA),
        }
        messages = build_messages(persona, "a citizen", "what happened here?",
                                  "directed")
        system = messages[0]["content"].lower()
        # the archetype's duties + length made it into the charter
        self.assertIn("security unit", system)
        self.assertIn("clipped", system)
        self.assertIn("restricted", system)
        # the seed's card made it in
        self.assertIn("municipal", system)
        # and it doesn't inherit the bartender's job
        self.assertNotIn("tend this bar", system)
