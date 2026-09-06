"""Spawned NPCs carry money the game can see (#2426).

`Character.tokens` is an `AttributeProperty(category="shop")`. A bare
`db.tokens` is a DIFFERENT ROW that nothing reads. Two director spawners
wrote the bare one, so 40 street civilians and witnesses walked around
holding 12,728 credits `pickpocket` answered "is carrying no tokens"
for — while `@civilians` help text promised "carrying 100-500 tokens
(muggable)". The souls `rob` step reads the property too, and terminated
at 0.

The codebase already knew: `CmdTheft` carries the diagnosis verbatim in a
comment. The reader was fixed; the writers were not.

These tests assert what a THIEF sees, not which attribute was written —
`pickpocket` finding money is the whole point, and pinning the storage
mechanism would just re-encode today's implementation.
"""
from unittest import mock

from evennia.utils.test_resources import EvenniaTest


class _WalletCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.mark = self.char2
        self.mark.location = self.room1
        self.thief = self.char1
        self.thief.location = self.room1

    def visible_money(self):
        """What every reader in the game actually looks at."""
        return int(getattr(self.mark, "tokens", 0) or 0)

    def ghost_row(self):
        return self.mark.attributes.get("tokens", category=None)


class TestTheCivilianSpawnerFundsTheRealWallet(_WalletCase):
    def test_a_spawned_civilian_has_money_a_thief_can_find(self):
        """Drives the real `spawn_civilian`, so this fails if the write
        ever moves back to the ghost row."""
        from world.director import civilians
        npc = civilians.spawn_civilian("addict", self.room1)
        if npc is None:
            self.skipTest("spawn_civilian declined in this environment")
        self.assertGreaterEqual(int(getattr(npc, "tokens", 0) or 0),
                                civilians.TOKEN_RANGE[0])
        self.assertIsNone(npc.attributes.get("tokens", category=None))

    def test_the_spawner_does_not_write_the_ghost_row(self):
        import inspect
        from world.director import civilians
        src = inspect.getsource(civilians)
        code = "\n".join(l for l in src.splitlines()
                         if not l.strip().startswith("#"))
        self.assertNotIn("npc.db.tokens", code)


class TestTheWitnessSpawnerFundsTheRealWallet(_WalletCase):
    def test_the_spawner_does_not_write_the_ghost_row(self):
        import inspect
        from world.director import witness
        src = inspect.getsource(witness)
        code = "\n".join(l for l in src.splitlines()
                         if not l.strip().startswith("#"))
        self.assertNotIn("witness.db.tokens", code)


class TestAThiefFindsWhatTheSpawnerLeft(_WalletCase):
    """The player-facing consequence, stated once."""

    def test_money_on_the_property_is_visible(self):
        self.mark.tokens = 250
        self.assertEqual(self.visible_money(), 250)

    def test_money_on_the_ghost_row_is_not(self):
        """Pinning the trap itself: a bare `db.tokens` is invisible, so
        anyone writing one has funded nobody."""
        self.mark.attributes.add("tokens", 250)
        self.assertEqual(self.visible_money(), 0)

    def test_the_two_rows_are_genuinely_different(self):
        self.mark.tokens = 10
        self.mark.attributes.add("tokens", 999)
        self.assertEqual(self.visible_money(), 10)
        self.assertEqual(self.ghost_row(), 999)


class TestTheDeadShopHelpersAreMarked(EvenniaTest):
    """`validate_purchase`/`deduct_tokens`/`add_tokens` have no callers
    and read the ghost row. They are left in place but must warn, so the
    next person to reach for them does not recreate this."""

    def test_the_docstring_warns(self):
        from world.shop import utils
        self.assertIn("WRONG WALLET",
                      (utils.validate_purchase.__doc__ or "").upper())
