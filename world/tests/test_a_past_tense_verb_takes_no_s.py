"""`.went north` does not render as "wents" (#2642).

`conjugate_third_person` consulted its irregular table only against the
RAW input, then handed everything else to a normalise-and-append-s
pipeline. The table holds nine forms, all be/do/have, so every other
irregular verb in English came back with an -s stapled on:

    'am'   -> 'ares'      'went' -> 'wents'
    'said' -> 'saids'     'ate'  -> 'ates'

Reachable from both doors. `world/emote.py` conjugates every verb token
for observers, and `typeclasses/llm_npc.py` runs generated prose through
the same function — its `endswith(("s", "ing", "ed"))` filter catches
regular past tense and misses every irregular one, because `said` ends
in d, `went` in t and `ate` in e.

**The actor's own view is unaffected**, since the emote renderer uses
`token.base_form` untouched for the actor. So the player who typed it
sees correct English and the room sees the mangled version, which is
why it could ship unnoticed.

Two distinct causes, two fixes:

* `am` is the one `be` form the table forgot. It normalises toward
  `are`, and the table was never re-consulted after normalisation
  despite the docstring promising it "takes absolute precedence" and is
  "keyed by any form".
* Irregular past tense is invariant across person and number — "she
  went", "she said" — so it needs conjugating exactly as much as a
  modal does, which is not at all.
"""
from evennia.utils.test_resources import EvenniaTest

from world import grammar as grammar_mod
from world.grammar import conjugate_third_person

#: Read off the module with an EMPTY default rather than imported by
#: name: a missing table makes this file fail to LOAD against the
#: unfixed tree, and a test that never runs is not a control. Empty is
#: also the unfixed reality, so the exclusion-rule assertions below stay
#: true there while the behavioural ones fail — which is the claim.
IRREGULAR_PAST = getattr(grammar_mod, "IRREGULAR_PAST", frozenset())

#: Forms that are BOTH past and present tense, or another verb's base.
#: None of these may be in the past table: adding one breaks the
#: ordinary present-tense pose, which is a far more common line than
#: the past-tense one it would fix.
AMBIGUOUS = ("read", "set", "put", "cut", "hit", "let", "cost", "hurt",
             "shut", "spread", "bet", "quit", "shed", "saw", "lay",
             "bore", "ground", "wound", "found")


class TestTheReportedCases(EvenniaTest):

    def test_the_be_form_the_table_forgot(self):
        self.assertEqual(conjugate_third_person("am"), "is")

    def test_irregular_past_passes_through(self):
        for verb in ("went", "said", "ate", "took", "gave", "knew",
                     "ran", "stood", "brought"):
            self.assertEqual(conjugate_third_person(verb), verb)


class TestThePresentTenseStillConjugates(EvenniaTest):
    """Controls. Every one of these is the ordinary case, and a fix that
    stopped conjugating them would be worse than the defect."""

    def test_the_four_rules_still_fire(self):
        self.assertEqual(conjugate_third_person("lean"), "leans")
        self.assertEqual(conjugate_third_person("catch"), "catches")
        self.assertEqual(conjugate_third_person("try"), "tries")
        self.assertEqual(conjugate_third_person("go"), "goes")

    def test_a_true_base_ending_in_s_is_not_normalised_away(self):
        self.assertEqual(conjugate_third_person("pass"), "passes")
        self.assertEqual(conjugate_third_person("cross"), "crosses")

    def test_an_already_conjugated_form_is_idempotent(self):
        self.assertEqual(conjugate_third_person("stands"), "stands")

    def test_modals_and_the_table_are_untouched(self):
        for verb, want in (("can", "can"), ("could", "could"),
                           ("is", "is"), ("was", "was"), ("has", "has"),
                           ("does", "does")):
            self.assertEqual(conjugate_third_person(verb), want)


class TestTheExclusionRuleHolds(EvenniaTest):
    """The list's own rule, pinned — it matters more than the entries.
    A form that is also a present-tense verb must never be in it."""

    def test_no_ambiguous_form_is_listed(self):
        listed = [w for w in AMBIGUOUS if w in IRREGULAR_PAST]
        self.assertEqual(
            listed, [],
            "these are present tense too; listing them breaks the "
            "ordinary pose")

    def test_and_they_still_conjugate(self):
        for verb in ("set", "put", "cut", "read", "saw", "lay", "wound"):
            self.assertEqual(conjugate_third_person(verb), verb + "s",
                             verb)


class TestCapitalisationSurvives(EvenniaTest):

    def test_a_past_form_keeps_its_case(self):
        self.assertEqual(conjugate_third_person("Went"), "Went")

    def test_a_normalised_table_hit_keeps_its_case(self):
        self.assertEqual(conjugate_third_person("Am"), "Is")

    def test_and_an_ordinary_verb_does(self):
        self.assertEqual(conjugate_third_person("Stand"), "Stands")
