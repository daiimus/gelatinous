"""`help aim` describes what aiming does, and promises nothing it doesn't (#3355).

The docstring told players aiming was "potentially granting bonuses to
subsequent ranged attacks". The to-hit roll (world/combat/attack.py) never
reads the aim state -- a player spent a round aiming for accuracy that
never came. Owner ruling 2026-09-13: withdraw the promise; aim is a
positioning tool. The help now names the real effects: the lock, the
flee-punish, the visible tell, cross-room fire, and how aim ends.

The docstring IS the in-game help text, so asserting on it is asserting
on what the player reads.
"""
from evennia.utils.test_resources import EvenniaTest

from commands.combat.special_actions import CmdAim


class HelpAimTest(EvenniaTest):

    def test_no_accuracy_promise(self):
        doc = (CmdAim.__doc__ or "").lower()
        self.assertNotIn("granting bonus", doc, "help aim still promises a bonus")
        self.assertNotIn("bonuses to subsequent", doc)
        # It should say the opposite, plainly.
        self.assertIn("does not improve your accuracy", doc)

    def test_names_the_real_effects(self):
        doc = (CmdAim.__doc__ or "").lower()
        for phrase in ("locks them in place", "flee", "free attack",
                       "through that exit", "ranged weapon", "aim stop"):
            self.assertIn(phrase, doc, "help aim does not mention %r" % phrase)

    def test_says_when_aim_ends(self):
        doc = (CmdAim.__doc__ or "").lower()
        self.assertIn("holds through combat", doc)
        self.assertIn("when you move", doc)
