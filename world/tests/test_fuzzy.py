"""The fuzzy candidate facade (world/fuzzy.py) and its three consumers.

Narrow by design: LLM tool arguments resolve against small real candidate
lists. Never identity/recognition, never player-command auto-resolution.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from world.fuzzy import best_match, score


class TestScore(TestCase):
    def test_exact_and_containment(self):
        self.assertEqual(score("rotgut", "rotgut"), 1.0)
        self.assertEqual(score("Rotgut", "  rotgut "), 1.0)   # normalized
        self.assertEqual(score("rotgut", "mug of rotgut"), 0.95)
        self.assertEqual(score("a mug of rotgut", "rotgut"), 0.95)

    def test_typos_score_high_nonsense_low(self):
        self.assertGreater(score("rotgutt", "rotgut"), 0.85)
        self.assertGreater(score("bandge", "bandage"), 0.8)
        self.assertLess(score("banana", "plate carrier"), 0.5)

    def test_word_order_costs_little(self):
        self.assertGreater(score("top mesh", "mesh top"), 0.9)

    def test_empty_is_zero(self):
        self.assertEqual(score("", "rotgut"), 0.0)
        self.assertEqual(score("rotgut", ""), 0.0)


class TestBestMatch(TestCase):
    MENU = ["mug of rotgut", "reactor cut", "sweet ash tea"]

    def test_picks_the_right_candidate(self):
        hit = best_match("a mug of rotgut, please".replace(", please", ""),
                         self.MENU)
        self.assertEqual(hit[0], "mug of rotgut")

    def test_below_floor_is_none(self):
        self.assertIsNone(best_match("plasma grenade", self.MENU))

    def test_key_extraction(self):
        items = [SimpleNamespace(key="a mesh top"),
                 SimpleNamespace(key="cargo trousers")]
        hit = best_match("mesh top", items, key=lambda o: o.key)
        self.assertEqual(hit[0].key, "a mesh top")

    def test_empty_candidates(self):
        self.assertIsNone(best_match("anything", []))
        self.assertIsNone(best_match("anything", None))


class TestStyleToolResolution(TestCase):
    def test_decorated_arg_resolves_to_real_worn_key(self):
        import typeclasses.llm_npc as llmnpc
        b = MagicMock()
        top = SimpleNamespace(key="a mesh top")
        b.get_worn_items = lambda: [top]
        b.contents = [top]
        bound = llmnpc.LLMNpcMixin._handle_action_tool.__get__(
            b, llmnpc.LLMNpcMixin)
        bound("style", "take off her mesh top (unzipped)", MagicMock())
        b.execute_cmd.assert_called_once_with("remove a mesh top")


class TestPrepareDrinkResolution(TestCase):
    def test_loose_order_resolves_to_menu_name(self):
        import typeclasses.bar as barmod
        b = MagicMock()
        b.location = MagicMock()
        b._find_bar = lambda: None
        b.db.menu = [{"name": "mug of rotgut"}, {"name": "reactor cut"}]
        bound = barmod.Bartender._handle_action_tool.__get__(
            b, barmod.Bartender)
        with patch.object(barmod.LLMNpcMixin, "_handle_action_tool"):
            bound("prepare_drink", "a mug of rotgutt", MagicMock())
        b.execute_cmd.assert_called_once_with("prepare mug of rotgut")


class TestClinicTreatResolution(TestCase):
    def test_typo_supply_resolves(self):
        import typeclasses.clinic as clinic
        doc = MagicMock()
        item = MagicMock(); item.key = "gauze bandages"
        doc._draw_supply = MagicMock(return_value=item)
        patient = MagicMock()
        patient.get_display_name = lambda looker=None: "a lean man"
        bound = clinic.Doctor._treat.__get__(doc, clinic.Doctor)
        bound(patient, "bandge")       # typo: no exact, no containment
        doc._draw_supply.assert_called_once_with("GAUZE_BANDAGES")
        doc.execute_cmd.assert_called_once_with(
            "apply gauze bandages on a lean man")
