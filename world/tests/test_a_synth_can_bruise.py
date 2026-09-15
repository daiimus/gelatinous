"""A species wound pack answers by injury type (#owner 2026-09-14).

The synth and robot packs were keyed by healing stage alone, so a blow,
a bullet and a blade all rendered the same cobalt cut. A pack may now
carry ``BY_INJURY`` (and ``COMPOUND_BY_INJURY``); the lookup prefers it
and falls back to the stage-only table, so an unauthored injury type
never leaks human flesh prose.
"""
from types import SimpleNamespace
from unittest import TestCase, mock

from world.medical.wounds import messages
from world.medical.wounds.longdesc_hooks import _resolve_compound_template
from world.medical.wounds.wound_descriptions import get_wound_description


def _char(species):
    return SimpleNamespace(species=species, db=SimpleNamespace(species=species, skintone=None))


class _FakePack:
    WOUND_DESCRIPTIONS = {"fresh": ["|Ba {severity} STAGEONLY on the {location}|n"],
                          "treated": ["{skintone}a {severity} STAGEONLY-treated on the {location}|n"]}
    BY_INJURY = {"blunt": {"fresh": ["|Ba {severity} BLUNTLINE on the {location}|n"]}}
    COMPOUND_DESCRIPTIONS = {"fresh": ["|Ba {severity} STAGEONLY-compound on the {location}|n"]}
    COMPOUND_BY_INJURY = {"blunt": {"fresh": ["|Ba {severity} BLUNT-compound on the {location}|n"]}}


class ASynthCanBruiseTest(TestCase):

    def setUp(self):
        self._p = mock.patch.dict(messages.SPECIES_PACKS, {"fakespecies": _FakePack})
        self._p.start(); self.addCleanup(self._p.stop)
        self.c = _char("fakespecies")

    def test_an_authored_injury_type_uses_its_own_lines(self):
        for _ in range(8):
            self.assertIn("BLUNTLINE", get_wound_description("blunt", "left_arm", "Moderate", "fresh", character=self.c))

    def test_an_unauthored_stage_falls_back_within_the_pack(self):
        # blunt has no 'treated' entry: the stage-only table answers, never human prose
        self.assertIn("STAGEONLY-treated", get_wound_description("blunt", "left_arm", "Moderate", "treated", character=self.c))

    def test_an_unauthored_injury_type_falls_back_to_the_stage_table(self):
        self.assertIn("STAGEONLY", get_wound_description("stab", "left_arm", "Moderate", "fresh", character=self.c))

    def test_compound_prefers_the_injury_table(self):
        self.assertIn("BLUNT-compound", _resolve_compound_template("blunt", "fresh", self.c))
        self.assertIn("STAGEONLY-compound", _resolve_compound_template("stab", "fresh", self.c))

    def test_a_human_still_reads_the_per_injury_modules(self):
        seen = " ".join(get_wound_description("blunt", "left_arm", "Moderate", "fresh", character=_char("human")) for _ in range(20)).lower()
        self.assertTrue(any(w in seen for w in ("bruis", "crush", "bludgeon", "impact")), seen[:200])
        self.assertNotIn("BLUNTLINE", seen)
