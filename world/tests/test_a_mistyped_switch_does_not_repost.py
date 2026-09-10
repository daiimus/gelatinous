"""A mistyped @patrol switch does not silently re-post the NPC (#2565).

`@patrol` dispatches on a chain of membership tests with no `else`:

    if "base" in switches: ...
    if "dispatch" in switches: ...
    if "status" in switches: ...

so anything unmatched continued into the BARE form at the bottom of
`func` — post this NPC to wherever the builder happens to be standing,
overwriting `db.post`. `@patrol/Status bob` printed no status, gave no
warning, and moved bob's post.

Two separate faults had to be fixed, and neither is enough alone:

* no `switch_options`, so `MuxCommand` did not validate switches at all
  and `/stat` matched nothing;
* `MuxCommand` compares switches case-SENSITIVELY even when they ARE
  declared, so `/Status` is dropped as an extra switch and
  `self.switches` comes back empty — indistinguishable in `func` from
  the bare form.

The tests drive the command CLASS through `self.call`. `execute_cmd`
under `EvenniaCommandTest` does not load the character cmdset, so a
command driven that way never runs and every refusal assertion passes
for the wrong reason.
"""
from evennia.utils.test_resources import EvenniaCommandTest

from commands.CmdPatrol import CmdPatrol


class TestAMistypedSwitchDoesNotRepost(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.permissions.add("Developers")
        self.char2.key = "bob"
        self.char2.db.post = self.room2
        self.char1.location = self.room1

    def post(self):
        return self.char2.db.post

    def test_the_bare_form_still_posts(self):
        """Control: the destructive default is REACHABLE, so a test
        showing it was not reached is measuring something."""
        self.call(CmdPatrol(), "bob")
        self.assertIs(self.post(), self.room1)

    def test_a_miscased_switch_does_not_repost(self):
        self.call(CmdPatrol(), "/Status bob")
        self.assertIs(self.post(), self.room2,
                      "a mistyped switch moved the NPC's post")

    def test_a_nonsense_switch_does_not_repost(self):
        self.call(CmdPatrol(), "/wibble bob")
        self.assertIs(self.post(), self.room2)

    def test_a_nonsense_switch_says_so(self):
        out = self.call(CmdPatrol(), "/wibble bob")
        self.assertIn("switch", out.lower())

    def test_a_miscased_switch_does_what_was_meant(self):
        """`/Status` should REPORT, not merely refuse.

        Asserts on `Heartbeat:`, which only the status branch prints.
        "bob appears in the output" is true of the destructive default
        too, so it would pass against the unfixed code."""
        out = self.call(CmdPatrol(), "/Status bob")
        self.assertIn("Heartbeat:", out)
        self.assertNotIn("unrecognised", out.lower())

    def test_an_abbreviation_reports_too(self):
        out = self.call(CmdPatrol(), "/stat bob")
        self.assertIn("Heartbeat:", out)

    def test_an_abbreviated_switch_resolves(self):
        """What declaring the options buys: `/stat` is `/status`."""
        out = self.call(CmdPatrol(), "/stat bob")
        self.assertIs(self.post(), self.room2)
        self.assertNotIn("unrecognised", out.lower())

    def test_a_real_switch_still_works(self):
        self.call(CmdPatrol(), "/clear bob")
        self.assertIs(self.post(), self.room2,
                      "/clear takes them off patrol but KEEPS the post")
