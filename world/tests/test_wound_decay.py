"""Wound status must survive a reload, and must not be shared (#2783).

A wound decays on a three-day half-life instead of six hours. Which keys
count was held in a MODULE-LEVEL set that `wound=True` added to — so it
died with the process, and a stored `attacked_me` silently fell back to
the ordinary half-life after any reload. Being module-level it was also
shared: the first soul to record a key made it a wound for every soul in
the process.

Only `against_my_nature` is hardcoded, and that is why it never showed —
the one key that survived a reload was the one that never needed to.
"""

from __future__ import annotations

from evennia.utils.test_resources import BaseEvenniaTest

from world.souls import thoughts


class TestWoundStatusIsPerSoulAndPersisted(BaseEvenniaTest):
    def test_a_wound_is_recorded_on_the_soul(self):
        thoughts.add_thought(self.char1, "attacked_me", -0.6,
                             "they put hands on me", wound=True)
        self.assertIn("attacked_me",
                      set(self.char1.db.soul_wound_keys or ()))

    def test_it_survives_losing_the_module_state(self):
        thoughts.add_thought(self.char1, "attacked_me", -0.6, "x", wound=True)
        # what a reload does: the module set is back to its baseline
        self.assertNotIn("attacked_me", thoughts.WOUND_KEYS)
        self.assertIn("attacked_me", thoughts._wound_keys(self.char1))

    def test_one_soul_s_wound_is_not_another_s(self):
        thoughts.add_thought(self.char1, "attacked_me", -0.6, "x", wound=True)
        self.assertNotIn("attacked_me", thoughts._wound_keys(self.char2))

    def test_a_wound_decays_slower_than_an_ordinary_thought(self):
        thoughts.add_thought(self.char1, "attacked_me", -0.6, "x", wound=True)
        day = 24 * 3600
        wounded = thoughts._weight("attacked_me", day, self.char1)
        ordinary = thoughts._weight("ate_well", day, self.char1)
        self.assertGreater(wounded, ordinary)

    def test_the_baseline_key_still_works_without_a_soul(self):
        self.assertGreater(thoughts._weight("against_my_nature", 24 * 3600),
                           thoughts._weight("ate_well", 24 * 3600))
