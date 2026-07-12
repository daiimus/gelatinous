"""The blood-token contract (2026-07-12): weapon and severance prose
never hardcodes blood colour — templates say {blood}/{Blood} and the
renderers resolve the TARGET's species fluid (human crimson, synth
cobalt, robot amber). These tests keep the sweep true forever."""

import glob
import re
import string
from unittest import TestCase
from unittest.mock import MagicMock

#: Non-blood reds the sweep deliberately spared (sights, painted steel).
_ALLOWED_RED = re.compile(
    r"red[- ]hot|red\s+(dot|bead|laser|light|glow|led|beam|button|switch|"
    r"lens|eye[s]?\b)|glowing\s+red|infrared|dull red of the (axe|blade|"
    r"head)|red(dened|dish|ness)", re.I)

#: Every format field the two renderers supply.
_SUPPLIED = {
    "attacker_name", "target_name", "attacker", "target", "item_name",
    "item", "phase", "hit_location", "damage", "blood", "Blood",
}


def _message_files():
    files = glob.glob("world/combat/messages/*.py")
    files += glob.glob("world/combat/messages/severance/*.py")
    return [f for f in files if not f.endswith("__init__.py")]


class TestNoHardcodedBlood(TestCase):
    def test_no_bare_blood_colour_words(self):
        offenders = []
        for path in _message_files():
            text = open(path).read()
            for m in re.finditer(r"\b(crimson|scarlet|red)\b", text, re.I):
                ctx = text[max(0, m.start() - 12):m.end() + 14]
                if not _ALLOWED_RED.search(ctx):
                    offenders.append(f"{path}: ...{ctx!r}...")
        self.assertEqual(offenders[:8], [], f"{len(offenders)} hardcoded")


class TestTemplatesFormatCleanly(TestCase):
    def test_every_template_field_is_supplied(self):
        import ast
        fmt = string.Formatter()
        offenders = []
        for path in _message_files():
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)):
                    continue
                template = node.value
                if "{" not in template:
                    continue
                try:
                    fields = {f for _, f, _, _ in fmt.parse(template) if f}
                except ValueError:
                    continue      # not a format template (stray braces)
                bad = {f.split(".")[0].split("[")[0] for f in fields}
                # docstrings use prose braces ("{a, b, c}") — only
                # identifier-shaped fields are real format slots
                bad = {f for f in bad if f.isidentifier()}
                bad -= _SUPPLIED
                if bad:
                    offenders.append(f"{path}: {sorted(bad)} in "
                                     f"{template[:60]!r}")
        self.assertEqual(offenders[:8], [], f"{len(offenders)} bad fields")


class TestRenderersResolveSpecies(TestCase):
    def _target(self, species):
        target = MagicMock()
        target.db.species = species
        target.key = "someone"
        return target

    def test_combat_message_bleeds_target_species(self):
        from world.combat.messages import get_combat_message
        # chainsaw hit prose is dense with {blood} after the sweep
        msgs = get_combat_message("chainsaw", "hit",
                                  target=self._target("synthetic_humanoid"),
                                  hit_location="chest", damage=5)
        joined = " ".join(str(v) for v in msgs.values())
        self.assertNotIn("(Error", joined)
        self.assertNotIn("{blood}", joined)

    def test_severance_bleeds_target_species(self):
        from world.combat.messages.severance import get_severance_message
        msgs = get_severance_message("left_arm", "cut",
                                     target=self._target("robot"))
        joined = " ".join(str(v) for v in msgs.values()
                          if isinstance(v, str))
        self.assertNotIn("(Error", joined)
        self.assertNotIn("{blood}", joined)
