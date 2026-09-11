"""Both respawn doors validate `last_character` the same way.

Regression pin for #2615. The web view checked that the stored sleeve
was actually archived -- clearing the attribute if it was alive or the
reference was broken -- and the telnet login read it RAW:

    is_respawn = bool(self.db.last_character)

So whatever sat there was handed to the respawn flow as the character
being replaced: a living sleeve, a deleted one, one transferred to
another account. The web door was hardened for exactly this; the telnet
door, which is the one most players use, was not.

Latent -- a stale value needs an unusual sequence -- but two doors
disagreeing about validation is the defect.

`Account.respawn_candidate()` is now the one door. It CLEARS a
reference that does not qualify, so a stale pointer is repaired on the
way past rather than left for the next login.
"""

from unittest import TestCase
from unittest.mock import MagicMock

from typeclasses.accounts import Account


def _account(last):
    acc = MagicMock()
    acc.db.last_character = last
    acc.respawn_candidate = Account.respawn_candidate.__get__(acc, Account)
    return acc


class _Broken:
    """A deleted sleeve: touching `.key` raises, as Evennia's does."""

    def __bool__(self):
        return True

    @property
    def key(self):
        raise AttributeError("deleted")


def _sleeve(archived=True, broken=False):
    # A plain object, not `PropertyMock` on `type(mock)` — that sets the
    # attribute on the shared MagicMock CLASS and leaks into every other
    # mock in the process.
    if broken:
        return _Broken()
    ch = MagicMock()
    ch.key = "Corpse"
    ch.is_archived = archived
    return ch


class TestOneDoorOntoTheLastCharacter(TestCase):

    def test_an_archived_sleeve_is_a_candidate(self):
        sleeve = _sleeve(archived=True)
        acc = _account(sleeve)
        self.assertIs(acc.respawn_candidate(), sleeve)
        self.assertIs(acc.db.last_character, sleeve)   # not cleared

    def test_a_living_sleeve_is_refused_and_cleared(self):
        acc = _account(_sleeve(archived=False))
        self.assertIsNone(acc.respawn_candidate())
        self.assertIsNone(acc.db.last_character)

    def test_a_broken_reference_is_refused_and_cleared(self):
        acc = _account(_sleeve(broken=True))
        self.assertIsNone(acc.respawn_candidate())
        self.assertIsNone(acc.db.last_character)

    def test_no_last_character_is_not_an_error(self):
        acc = _account(None)
        self.assertIsNone(acc.respawn_candidate())

    def test_both_doors_call_it(self):
        """The point of the change: one validator, two callers."""
        import inspect
        from web.website.views import characters as web

        self.assertIn("respawn_candidate",
                      inspect.getsource(Account.at_post_login))
        self.assertIn("respawn_candidate", inspect.getsource(web))
