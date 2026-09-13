"""A rejected name re-displays the prompt, it does not close the menu (#3357).

The two first-character name nodes are EvMenu **node functions**. On bad
input they returned a bare `None` under a comment saying "re-display
current node". EvMenu does the opposite: a node function that yields no
options is "done", so the menu CLOSES -- which fires
`_charcreate_exit_callback`, and for a first-time account (no active
sleeve) that DISCONNECTS the session with "Sleeve decantation
incomplete." So a new player who fat-fingered their name was kicked and
their progress discarded.

This test pins the RETURN VALUE, not just that validation fires. #2550's
test exercised `validate_name` alone, so the suite stayed green while the
node kept returning None -- the exact gap that let this survive. A node
that re-displays returns a `(text, options)` tuple; a node that closes
returns None. That is the whole difference, and it is what we assert.

Runs against the node functions directly: under `evennia test` there is
no reactor, so driving the menu through `execute_cmd` would hang rather
than step (the #3211 lesson). The node contract -- bad input yields a
re-display tuple, good input yields the next node's tuple -- is exactly
what EvMenu consumes, so testing it is testing the behaviour.
"""
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate

_first = getattr(charcreate, "first_char_name_first", None)
_last = getattr(charcreate, "first_char_name_last", None)


class _Caller:
    """Minimal stand-in: the nodes touch only .ndb.charcreate_data and .msg."""
    class _NDB:
        def __init__(self):
            self.charcreate_data = {}

    def __init__(self):
        self.ndb = _Caller._NDB()
        self.seen = []

    def msg(self, text=None, **kw):
        if text is not None:
            self.seen.append(text)


def _is_redisplay(ret):
    # EvMenu: a (text, options) tuple re-displays; a bare None closes.
    return isinstance(ret, tuple) and len(ret) >= 2


class RejectedNameRedisplaysTest(EvenniaTest):

    def test_nodes_exist(self):
        self.assertIsNotNone(_first, "first_char_name_first is missing")
        self.assertIsNotNone(_last, "first_char_name_last is missing")

    # --- the defect: bad input must NOT close the menu -------------------

    def test_first_name_too_short_redisplays(self):
        c = _Caller()
        ret = _first(c, "A")
        self.assertTrue(_is_redisplay(ret),
                        "a too-short first name returned %r (None closes the "
                        "menu and disconnects the player)" % (ret,))
        self.assertTrue(c.seen, "no error was shown to the player")

    def test_first_name_bad_charset_redisplays(self):
        c = _Caller()
        self.assertTrue(_is_redisplay(_first(c, "J0hn")),
                        "a first name with a digit closed the menu")

    def test_last_name_too_short_redisplays(self):
        c = _Caller()
        c.ndb.charcreate_data['first_name'] = 'John'
        self.assertTrue(_is_redisplay(_last(c, "D")),
                        "a too-short last name closed the menu")

    def test_last_name_bad_charset_redisplays(self):
        c = _Caller()
        c.ndb.charcreate_data['first_name'] = 'John'
        self.assertTrue(_is_redisplay(_last(c, "Dix9")),
                        "a last name with a digit closed the menu")

    # --- control: good input still advances, never closes ----------------

    def test_good_first_name_advances(self):
        # Returns the NEXT node's (text, options) -- also a tuple, never
        # None. Proves the fix did not turn advancement into a close.
        c = _Caller()
        ret = _first(c, "John")
        self.assertTrue(_is_redisplay(ret),
                        "a valid first name did not advance (%r)" % (ret,))
        self.assertEqual(c.ndb.charcreate_data.get('first_name'), 'John')

    def test_good_last_name_advances(self):
        c = _Caller()
        c.ndb.charcreate_data['first_name'] = 'John'
        ret = _last(c, "Smith")
        self.assertTrue(_is_redisplay(ret),
                        "a valid last name did not advance (%r)" % (ret,))
        self.assertEqual(c.ndb.charcreate_data.get('last_name'), 'Smith')
