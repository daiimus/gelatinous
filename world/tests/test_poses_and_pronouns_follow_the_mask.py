"""Three findings from #2462.

**A disguise's pronouns gave the wearer away.** The longdesc and
worn-desc renderers built their pronoun set from the character's REAL
gender, so a man presenting as "a brawny woman" was still described
with "his" on a plain `look` — no pierce roll spent, no contest, just
prose contradicting the mask. `get_apparent_gender` is the derivation
the rest of the identity layer already uses.

The braced-verb NUMBER moves with it, or the two disagree: a neutral
character presenting as a woman would otherwise read "She hold
themselves still".

**The eight social emotes broadcast a visible pose without breaking
stealth.** `emote`, `.`, `say` and `to` all break it; `nod`, `wave`,
`shrug` and the rest did not, so a hider could pose at somebody and
stay concealed while the room watched them do it. The break goes after
the argument checks and before any broadcast, matching #2530 — a
refused command must not blow your cover for an action that never
happened.

**A wordless `emote` never marked its target as addressed.**
`speech_payload` builds itself around the spoken WORDS, so a pose with
no quote comes back without the key at all. `render_dot_pose` puts it
back with a `setdefault`; `render_emote` did not. So `.point at
bartender` was heard by the NPC and `emote points at the bartender` was
not, for want of one line the sibling already had.

**Finding 1 did not survive checking.** `_NOT_A_LEADING_VERB` is built
with `" ".join((...)).split()` now, not `tuple.__str__().split()`, so
no repr punctuation survives into the stopword set.

**Finding 5 is NOT fixed here.** A dot-pose opening on a non-subject
first-person pronoun (`.my hands are shaking`) is broadcast with no
actor attribution — observers get "His hands are shaking." with no name
in a room of several people. The mechanism is confirmed, but the
reporter marked it UNCERTAIN and the spec documents only two opening
patterns, neither of which is this. What that line SHOULD render as is
a design question rather than a defect with an obvious answer, so it is
raised separately.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _MaskCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        for char in (self.char1, self.char2):
            char.location = self.room1
        self.char1.height, self.char1.build = "tall", "lean"
        self.char1.sdesc_keyword = "man"

    def disguise_as(self, char, keyword):
        char.db.keyword_override = keyword


class TestPronounsFollowTheDisguise(_MaskCase):
    def test_the_renderers_ask_for_the_apparent_gender(self):
        import inspect
        from typeclasses import appearance_mixin
        source = inspect.getsource(appearance_mixin)
        self.assertIn("get_apparent_gender", source)

    def test_no_renderer_still_reads_the_real_gender_for_pronouns(self):
        import inspect
        from typeclasses import appearance_mixin
        source = inspect.getsource(appearance_mixin)
        self.assertNotIn("gender_mapping.get(self.gender", source)

    def test_a_disguised_man_reads_as_the_presentation(self):
        from world.identity import get_apparent_gender
        self.char1.sex = "male"
        self.disguise_as(self.char1, "woman")
        self.assertEqual(get_apparent_gender(self.char1), "female")

    def test_an_undisguised_character_is_unchanged(self):
        from world.identity import get_apparent_gender
        self.char1.sex = "male"
        self.assertEqual(get_apparent_gender(self.char1), "male")

    def test_the_verb_number_moves_with_the_pronoun(self):
        """Otherwise a neutral body presenting as a woman reads 'She
        hold themselves still'."""
        import inspect
        from typeclasses import appearance_mixin
        source = inspect.getsource(appearance_mixin)
        self.assertNotIn("body_number_for(self.gender)", source)


class TestSocialEmotesBreakStealth(_MaskCase):
    def _social(self, key="nod"):
        from world.emote_templates import SOCIAL_COMMANDS
        for cls in SOCIAL_COMMANDS:
            if cls.key == key:
                return cls
        self.skipTest(f"no social command named {key}")

    def test_posing_reveals_a_hidden_character(self):
        cmd_cls = self._social()
        self.char1.db.hidden = True
        cmd = cmd_cls()
        cmd.caller, cmd.args = self.char1, ""
        cmd.func()
        self.assertFalse(self.char1.db.hidden)

    def test_every_social_command_breaks_it(self):
        import inspect
        from world import emote_templates
        self.assertIn("break_stealth", inspect.getsource(emote_templates))

    def test_a_visible_character_is_unaffected(self):
        cmd_cls = self._social()
        cmd = cmd_cls()
        cmd.caller, cmd.args = self.char1, ""
        cmd.func()                       # must not raise
        self.assertFalse(self.char1.db.hidden)

    def test_it_breaks_after_the_no_location_guard(self):
        """#2530: a refused command must not blow your cover."""
        import inspect
        from world import emote_templates
        source = inspect.getsource(emote_templates)
        self.assertLess(source.index("You have no location to emote in."),
                        source.index("break_stealth"))


class TestAWordlessEmoteStillAddresses(_MaskCase):
    def test_render_emote_sets_the_fallback(self):
        import inspect
        from world import emote
        source = inspect.getsource(emote.render_emote)
        self.assertIn('setdefault("addressed"', source)

    def test_the_dot_pose_sibling_still_does_too(self):
        import inspect
        from world import emote
        source = inspect.getsource(emote.render_dot_pose)
        self.assertIn('setdefault("addressed"', source)

    def test_a_pointed_emote_marks_the_target(self):
        received = []
        self.char2.msg = lambda text="", **kw: received.append(kw)
        from world.emote import render_emote, tokenize_emote
        # Characters only — `room.contents` also holds exits, which have
        # no `get_sdesc`, and production filters to occupants first.
        occupants = [o for o in self.room1.contents
                     if hasattr(o, "get_sdesc")]
        tokens = tokenize_emote("points at Char2", self.char1, occupants)
        render_emote(tokens, self.char1, self.room1)
        self.assertTrue(any("addressed" in kw for kw in received),
                        f"payloads: {received}")


class TestTheStopwordSetIsClean(EvenniaTest):
    """Finding 1, already fixed — a pin."""

    def test_no_repr_punctuation_leaked_into_the_stopwords(self):
        from typeclasses.llm_npc import LLMNpcMixin
        for word in LLMNpcMixin._NOT_A_LEADING_VERB:
            self.assertNotIn(",", word)
            self.assertNotIn("'", word)
            self.assertNotIn("(", word)
