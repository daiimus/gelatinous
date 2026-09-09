"""A social emote that is REFUSED must not blow your cover (#3049).

The rule is #2530's and the comment in `_make_social_cmd` states it
outright:

    AFTER the argument checks above and before any broadcast, matching
    #2530: a refused command must not blow your cover for an action
    that never happened. The solo form needs no arguments, so the only
    refusal ahead of it is the no-location guard.

That last sentence is true of the SOLO form only. `break_stealth` sits
above two more refusals that the TARGETED form runs into:

    if targeted_template is None:      # `sigh` has no targeted form
        caller.msg(f"Usage: {keyword}")
        return
    target = caller.search(args)
    if not target:
        return

So a hider who typed `wave` at something that is not there emerged from
concealment for a wave the room never saw. The comment describes the
invariant the code directly beneath it breaks.

Both directions are asserted here. A test that only checked the
refusals would pass just as well if `break_stealth` were deleted
outright, which would be a much worse bug -- so the successful forms
are pinned too.

Drives the generated command CLASSES directly rather than
`execute_cmd`. The first version of this file used `execute_cmd` and
every assertion was vacuous: `SOCIAL_COMMANDS` are registered on the
real `CharacterCmdSet`, which `EvenniaCommandTest` does not load, so
nothing ran, `hidden` stayed True and the two refusal tests "passed"
while the two success tests failed. The bug was confirmed in the
running game instead, where `wave xyzzynotathing` printed "You abandon
any pretense of hiding." and then "Could not find 'xyzzynotathing'."
"""
from evennia.utils.test_resources import EvenniaCommandTest

from world.emote_templates import SOCIAL_COMMANDS


def _social(keyword):
    """The generated command class for one keyword."""
    for cls in SOCIAL_COMMANDS:
        if cls.key == keyword:
            return cls()
    raise AssertionError(f"no social command {keyword!r}")


class TestARefusalDoesNotUncoverYou(EvenniaCommandTest):

    def setUp(self):
        super().setUp()
        self.char1.db.hidden = True

    def _hidden(self):
        return self.char1.db.hidden is True

    def test_a_social_with_no_targeted_form_refuses_and_keeps_cover(self):
        """`sigh` has no targeted template -- this is the Usage refusal."""
        self.call(_social("sigh"), "at nobody")
        self.assertTrue(self._hidden(),
                        "a usage refusal emerged the hider")

    def test_waving_at_something_that_is_not_there_keeps_cover(self):
        """The failed-search refusal."""
        self.call(_social("wave"), "xyzzynotathing")
        self.assertTrue(self._hidden(),
                        "a failed target search emerged the hider")


class TestASocialThatActuallyHappensStillUncoversYou(EvenniaCommandTest):
    """The other half. Without these, deleting `break_stealth` passes."""

    def setUp(self):
        super().setUp()
        self.char1.db.hidden = True

    def test_a_solo_pose_breaks_stealth(self):
        self.call(_social("wave"), "")
        self.assertIsNot(self.char1.db.hidden, True,
                         "a pose the room watched left the actor hidden")

    def test_a_targeted_pose_at_a_real_target_breaks_stealth(self):
        self.call(_social("wave"), self.char2.key)
        self.assertIsNot(self.char1.db.hidden, True,
                         "a pose the room watched left the actor hidden")
