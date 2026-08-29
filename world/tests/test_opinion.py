"""Opinion — the same feeling, pointed at a person (#2388).

An NPC's read on someone used to be a free-text string the MODEL wrote
through the `feel` tool, which the game then stored and read back. That is
platform law 4 running backwards: souls decide, the LLM voices, and no
mechanic may exist only behind a model turn. The docstring on the old
setter even promised trust/consent would consult it one day — which would
have made a real mechanic depend on a model's word choice.

Opinion is the engine's answer now: the clamped, half-life-decayed sum of
what a person actually DID, derived on read exactly like mood. The voice is
handed the result.

Nothing gates on it yet, on purpose — see NPC_TRAITS_SPEC §12. These tests
pin the SHAPE, not tuned numbers.
"""
import time
from unittest import mock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import thoughts


class TestOpinionIsDerived(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def test_a_stranger_is_neutral(self):
        self.assertEqual(thoughts.opinion_of(self.soul, "nobody"), 0.0)
        self.assertEqual(thoughts.opinion_band(0.0), "neutral")

    def test_kindness_and_violence_move_it_opposite_ways(self):
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.30)
        thoughts.add_opinion(self.soul, "u2", "attacked_me", -0.60)
        self.assertGreater(thoughts.opinion_of(self.soul, "u1"), 0)
        self.assertLess(thoughts.opinion_of(self.soul, "u2"), 0)

    def test_it_is_per_person_not_global(self):
        """The whole point. A soul can like one person and loathe another."""
        thoughts.add_opinion(self.soul, "friend", "was_civil", 0.50)
        thoughts.add_opinion(self.soul, "enemy", "attacked_me", -0.70)
        self.assertEqual(thoughts.opinion_band(
            thoughts.opinion_of(self.soul, "friend")), "warm")
        self.assertEqual(thoughts.opinion_band(
            thoughts.opinion_of(self.soul, "enemy")), "hostile")

    def test_no_attribute_holds_the_score(self):
        """Zero-write law: the log is stored, the FEELING is derived. A cached
        score is a second source of truth that can drift from its reasons."""
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.30)
        stored = repr(self.soul.db.soul_opinions)
        self.assertNotIn("0.3'", stored.replace('"', "'"))  # no score field
        self.assertIn("was_civil", stored)                  # the REASON is

    def test_it_decays(self):
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.50)
        now = time.time()
        fresh = thoughts.opinion_of(self.soul, "u1", now=now)
        later = thoughts.opinion_of(
            self.soul, "u1", now=now + thoughts.HALFLIFE_SECONDS)
        self.assertAlmostEqual(later, fresh / 2, places=2)

    def test_a_wound_outlasts_an_ordinary_slight(self):
        """Violence should follow you around longer than rudeness."""
        thoughts.add_opinion(self.soul, "rude", "was_rude", -0.60)
        thoughts.add_opinion(self.soul, "thug", "attacked_me", -0.60,
                             wound=True)
        far = time.time() + thoughts.HALFLIFE_SECONDS * 4
        self.assertLess(thoughts.opinion_of(self.soul, "thug", now=far),
                        thoughts.opinion_of(self.soul, "rude", now=far))

    def test_it_is_clamped(self):
        for _ in range(30):
            thoughts.add_opinion(self.soul, "u1", f"k{_}", 1.0)
        self.assertLessEqual(thoughts.opinion_of(self.soul, "u1"), 1.0)


class TestTheCaps(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def test_two_people_can_both_be_generous(self):
        """The bug the shared log would have had: STACK_CAP dedupes on key,
        so A's 'was_civil' would evict B's."""
        for uid in ("a", "b", "c"):
            thoughts.add_opinion(self.soul, uid, "was_civil", 0.30)
        for uid in ("a", "b", "c"):
            self.assertGreater(thoughts.opinion_of(self.soul, uid), 0,
                               f"{uid} lost their entry")

    def test_one_person_repeating_themselves_is_capped(self):
        for _ in range(10):
            thoughts.add_opinion(self.soul, "u1", "was_civil", 0.10)
        entries = (self.soul.db.soul_opinions or {}).get("u1") or []
        self.assertLessEqual(len(entries), thoughts.OPINION_STACK_CAP)

    def test_the_acquaintance_book_is_bounded(self):
        for i in range(thoughts.ACQUAINTANCE_CAP + 10):
            thoughts.add_opinion(self.soul, f"u{i}", "was_civil", 0.10)
        self.assertLessEqual(len(self.soul.db.soul_opinions or {}),
                             thoughts.ACQUAINTANCE_CAP)

    def test_eviction_forgets_the_least_recently_felt_about(self):
        thoughts.add_opinion(self.soul, "old_friend", "was_civil", 0.10)
        for i in range(thoughts.ACQUAINTANCE_CAP + 5):
            thoughts.add_opinion(self.soul, f"u{i}", "was_civil", 0.10)
        self.assertNotIn("old_friend", self.soul.db.soul_opinions or {})

    def test_mood_is_not_crowded_out_by_sociability(self):
        """Why opinion got its own store: a bartender who meets a dozen
        patrons must not evict her own payday and hunger to make room."""
        thoughts.add_thought(self.soul, "payday", 0.25, "got paid")
        for i in range(30):
            thoughts.add_opinion(self.soul, f"patron{i}", "was_civil", 0.05)
        keys = [k for _t, k, _v, _n in (self.soul.db.soul_thoughts or [])]
        self.assertIn("payday", keys)


class TestMoodCoupling(BaseEvenniaTest):
    """Owner ruling 2026-08-29: a personal slight dents the DAY too, at
    reduced weight. Being robbed at knifepoint should not leave you
    'bright'."""

    def setUp(self):
        super().setUp()
        self.soul = self.char1

    def test_a_personal_event_also_moves_mood(self):
        before = thoughts.mood(self.soul)
        thoughts.add_opinion(self.soul, "thug", "attacked_me", -0.80)
        self.assertLess(thoughts.mood(self.soul), before)

    def test_but_less_than_it_moves_opinion(self):
        thoughts.add_opinion(self.soul, "thug", "attacked_me", -0.80)
        self.assertLess(abs(thoughts.mood(self.soul)),
                        abs(thoughts.opinion_of(self.soul, "thug")))

    def test_mood_share_zero_keeps_it_strictly_personal(self):
        thoughts.add_opinion(self.soul, "u1", "was_civil", 0.50,
                             mood_share=0)
        self.assertEqual(thoughts.mood(self.soul), 0.0)
        self.assertGreater(thoughts.opinion_of(self.soul, "u1"), 0)


class TestTheModelNoLongerAuthorsIt(BaseEvenniaTest):

    def test_the_feel_tool_is_gone(self):
        """Law 4: no mechanic may exist only behind a model turn. `feel` let
        the model WRITE a state the game stored and read back."""
        from world.llm.prompt import BASE_TOOLS, TOOLS
        self.assertNotIn("feel", TOOLS)
        self.assertNotIn("feel", BASE_TOOLS)

    def test_no_few_shot_example_still_calls_it(self):
        """A removed tool that examples still demonstrate is the schema and
        the training signal disagreeing — the model would emit a tool the
        router silently drops."""
        import inspect

        from world.llm import prompt
        src = inspect.getsource(prompt)
        self.assertNotIn('"tool": "feel"', src)

    def test_the_setter_is_gone(self):
        from typeclasses.llm_npc import LLMNpcMixin
        self.assertFalse(hasattr(LLMNpcMixin, "_set_valence"))


class TestTheVoiceIsHandedTheAnswer(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="npc", location=self.room1)

    def test_the_who_line_reports_the_engines_read(self):
        thoughts.add_opinion(self.npc, "u1", "attacked_me", -0.70,
                             note="they put hands on me")
        line = self.npc._relationship_line("u1", None)
        self.assertIsNotNone(line)
        self.assertIn("hostile", line)

    def test_it_cites_the_reason(self):
        """So the voice narrates the engine's grievance instead of inventing
        a different one."""
        thoughts.add_opinion(self.npc, "u1", "attacked_me", -0.70,
                             note="they put hands on me")
        self.assertIn("they put hands on me",
                      self.npc._relationship_line("u1", None))

    def test_a_clean_stranger_still_gets_no_line(self):
        self.assertIsNone(self.npc._relationship_line("nobody", None))

    def test_a_stale_model_written_valence_is_ignored(self):
        """Old dossiers still carry the strings `feel` wrote. They are inert
        now — the read comes from the event log or it doesn't come at all."""
        self.npc.db.llm_dossiers = {"u1": {"aliases": [],
                                           "valence": "smitten"}}
        self.assertIsNone(self.npc._relationship_line("u1", None))


class TestTheProducers(BaseEvenniaTest):

    def setUp(self):
        super().setUp()
        self.npc = create_object("typeclasses.llm_npc.LLMNpc",
                                 key="npc", location=self.room1)

    def test_courtesy_is_recorded(self):
        with mock.patch.object(self.npc, "_memory_subject",
                               return_value="u1"):
            self.npc._note_courtesy(self.char2)
        self.assertGreater(thoughts.opinion_of(self.npc, "u1"), 0)

    def test_being_thanked_by_nobody_is_not_recorded(self):
        self.npc._note_courtesy(None)
        self.assertFalse(self.npc.db.soul_opinions)

    def test_a_feeling_never_breaks_a_reply(self):
        """Fail-open: an NPC whose feelings raise must still answer."""
        with mock.patch("world.souls.thoughts.add_opinion",
                        side_effect=RuntimeError("boom")):
            self.npc._note_courtesy(self.char2)      # must not raise

    def test_violence_is_recorded_against_the_attacker(self):
        """The other producer: `react_to_attack` is the deterministic hook
        where a victim and a named attacker are both in hand."""
        from world.director import civilians
        self.npc.db.reaction = "flee"
        with mock.patch("world.identity.get_apparent_uid",
                        return_value="thug"), \
                mock.patch.object(self.npc, "execute_cmd"):
            civilians.react_to_attack(self.npc, self.char2)
        self.assertLess(thoughts.opinion_of(self.npc, "thug"), 0)
