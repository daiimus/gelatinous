"""Whoever watches a mask go on goes on knowing who is under it, and a
name the room shows can be typed (#3811).

Owner, 2026-11-13, after remembering somebody and having them put on a
ski mask: *"There name still appear but I could not reference it with
look."* And, asked whether somebody who watches a person they know put
on a mask goes on knowing them: *"Yes, and it's specific to that
person. We already have code for this, I believe. It's our 'Scooby
doo' system."*

The unmasking hook had recorded it all along: an eyewitness gets an
entry for the new look with no name and a link back to the look they
have a name for. `recall` read the link. The name on screen and the
name that could be typed did not, so an eyewitness fell through to the
see-through roll, and what they saw was a matter of dice.

Real commands throughout (`remember`, `wear`, `remove`, `look`,
`forget`, `recall`, a dot-pose), on fresh bodies, with the real ski
mask. The dice are stood in for only to choose a branch, or to prove
that none are thrown.

What is pinned:

* the eyewitness keeps the name, everywhere, with no roll, and the same
  the other way round when a mask comes off somebody known only masked;
* somebody who walked in on the mask and saw through it can type the
  name the room shows them, and typing never rolls;
* the controls: a bystander with no name for anybody learns nothing,
  and a mask that holds against somebody who walked in gives no name.
"""
import re
from unittest import mock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import get_apparent_uid

MASKED = "a gaunt masked man in a wool ski mask"
ROLL = "world.combat.dice.opposed_roll"
WON, LOST = (20, 1, True), (1, 20, False)


def plain(text):
    return re.sub(r"\|[a-zA-Z0-9/\[\]#=]+?|\x1b\[[0-9;]*m", "", text)


class _MaskCase(EvenniaTest):
    """A viewer, somebody they call Tamsin, and a ski mask.

    Fresh bodies with no account: `execute_cmd` on the harness's own
    `char1` (an account and no session) never completes without a
    reactor, and prints and writes nothing."""

    def setUp(self):
        super().setUp()
        self.viewer = self.body("Viewer", "short", "stocky", "woman")
        self.them = self.body("Target", "tall", "lean", "man")
        mask = spawn("SKI_MASK")[0]
        mask.move_to(self.them, quiet=True)
        self.heard = {}
        self.listen(self.viewer)
        self.do("remember man as Tamsin")

    def body(self, key, height, build, keyword, where=None):
        char = create_object(Character, key=key,
                             location=where or self.room1)
        char.sleeve_uid = f"sleeve-{key.lower()}"
        char.height, char.build, char.sdesc_keyword = height, build, keyword
        char.recognition_memory = {}
        char.db.disguise_pierce_cache = None
        return char

    def listen(self, who):
        lines = self.heard.setdefault(who, [])

        def hear(text=None, **kwargs):
            if isinstance(text, (tuple, list)):
                text = text[0]
            if text:
                lines.append(plain(str(text)))

        who.msg = hear

    def do(self, command, who=None):
        """What *who* (the viewer) is told when they type *command*."""
        who = who or self.viewer
        self.heard[who].clear()
        who.execute_cmd(command)
        return "\n".join(self.heard[who])

    def they(self, command):
        """What the VIEWER is told when the other one types *command*."""
        self.heard[self.viewer].clear()
        self.them.execute_cmd(command)
        return "\n".join(self.heard[self.viewer])

    def roster(self, who=None):
        """The line of the room that lists who is standing there."""
        return next((line for line in self.do("look", who).splitlines()
                     if "standing here" in line), "")

    def first(self, text):
        return (text.splitlines() or [""])[0]

    def no_dice(self):
        """Fail the test if anything rolls."""
        patch = mock.patch(ROLL, side_effect=AssertionError("a roll was made"))
        patch.start()
        self.addCleanup(patch.stop)

    def dice(self, result):
        patch = mock.patch(ROLL, return_value=result)
        rolled = patch.start()
        self.addCleanup(patch.stop)
        return rolled


class TestTheEyewitness(_MaskCase):
    """The mask goes on in front of the viewer."""

    def setUp(self):
        super().setUp()
        self.no_dice()
        self.saw = self.they("wear ski mask")

    def test_they_watched_tamsin_do_it(self):
        self.assertEqual(self.saw, "Tamsin puts on a wool ski mask.")

    def test_the_room_still_names_them(self):
        self.assertIn("Tamsin", self.roster())
        self.assertNotIn("masked man", self.roster())

    def test_the_name_can_be_typed(self):
        self.assertEqual(self.first(self.do("look tamsin")),
                         f"Tamsin ({MASKED})")

    def test_and_so_can_the_description(self):
        self.assertEqual(self.first(self.do("look man")),
                         f"Tamsin ({MASKED})")

    def test_a_pose_can_be_aimed_at_the_name(self):
        self.assertEqual(self.do(".wave at tamsin"), "You wave at Tamsin.")

    def test_recall_says_who_it_is_once(self):
        told = self.do("recall man")
        self.assertIn("You know them as: Tamsin", told)
        self.assertNotIn("don't have a name", told)
        self.assertNotIn("Also known as", told)

    def test_a_name_given_to_the_masked_look_wins(self):
        self.do("remember tamsin as Ghost")
        self.assertIn("Ghost", self.roster())
        self.assertNotIn("Tamsin", self.roster())
        self.assertEqual(self.first(self.do("look ghost")),
                         f"Ghost ({MASKED})")

    def test_forgetting_them_forgets_them(self):
        """The name is on the look they watched it come from, and that
        is the only name there is to take away."""
        self.assertIn("You forget the name 'Tamsin'", self.do("forget tamsin"))
        self.assertNotIn("Tamsin", self.roster())
        self.assertEqual(self.do("look tamsin"), "Could not find 'tamsin'.")

    def test_taking_it_off_again_reveals_nothing_new(self):
        told = self.they("remove ski mask")
        self.assertEqual(told, "Tamsin removes a wool ski mask.")
        self.assertIn("Tamsin", self.roster())

    def test_on_off_and_on_again(self):
        """The two looks end up linked at each other. The name still
        comes out, and nothing is said about a loop."""
        self.they("remove ski mask")
        with mock.patch("evennia.utils.logger.log_warn") as warned:
            self.they("wear ski mask")
            self.assertIn("Tamsin", self.roster())
            self.assertEqual(self.first(self.do("look tamsin")),
                             f"Tamsin ({MASKED})")
        warned.assert_not_called()

    def test_it_holds_when_they_walk_out_and_back(self):
        self.viewer.move_to(self.room2, quiet=True)
        self.viewer.move_to(self.room1, quiet=True)
        self.assertIn("Tamsin", self.roster())


class TestSomebodyWhoNeverKnewThem(_MaskCase):
    """The control, in a class of its own so that it reads the same on
    the unfixed tree: a second person stands there and watches the mask
    go on, with no name for anybody. (The dice are allowed here, and
    set against the viewer: before the fix the viewer's own look
    rolled, and that is not what this class is about.)"""

    def setUp(self):
        super().setUp()
        self.dice(LOST)
        self.stranger = self.body("Stranger", "average", "average", "woman")
        self.listen(self.stranger)
        self.heard[self.stranger].clear()
        self.them.execute_cmd("wear ski mask")

    def test_they_are_told_what_a_stranger_is_told(self):
        self.assertEqual(self.heard[self.stranger],
                         ["A gaunt man puts on a wool ski mask."])

    def test_and_see_a_stranger(self):
        self.assertIn("gaunt masked man", self.roster(self.stranger))
        self.assertNotIn("Tamsin", self.roster(self.stranger))

    def test_and_the_viewers_name_for_them_finds_nobody(self):
        self.assertEqual(self.do("look tamsin", self.stranger),
                         "Could not find 'tamsin'.")
        self.assertEqual(dict(self.stranger.recognition_memory), {})


class TestTheMaskComesOffSomebodyKnownOnlyMasked(_MaskCase):
    """The same rule the other way round: the viewer has a name for the
    masked figure and has never seen the face."""

    def setUp(self):
        super().setUp()
        self.do("forget tamsin")
        self.them.execute_cmd("wear ski mask")
        self.do("remember man as Ghost")
        self.no_dice()
        self.saw = self.they("remove ski mask")

    def test_they_watched_ghost_do_it(self):
        self.assertEqual(self.saw, "Ghost removes a wool ski mask.")

    def test_the_face_keeps_the_name(self):
        self.assertIn("Ghost", self.roster())
        self.assertEqual(self.first(self.do("look ghost")),
                         "Ghost (a gaunt man)")


class TestWalkingInOnTheMask(_MaskCase):
    """The viewer is out of the room when the mask goes on. This is what
    the see-through roll is for, and it is unchanged; what changes is
    that a name it has put on screen can be typed.

    Arriving in a room looks at it, so the roll is made on the way in:
    the dice are set before the viewer walks."""

    def setUp(self):
        super().setUp()
        self.viewer.move_to(self.room2, quiet=True, move_hooks=False)
        self.them.execute_cmd("wear ski mask")

    def walk_in(self, result):
        rolled = self.dice(result)
        self.viewer.move_to(self.room1, quiet=True)
        return rolled

    def test_a_name_seen_through_to_can_be_typed(self):
        self.walk_in(WON)
        self.assertIn("Tamsin", self.roster())
        self.assertEqual(self.first(self.do("look tamsin")),
                         f"Tamsin ({MASKED})")
        self.assertEqual(self.do(".wave at tamsin"), "You wave at Tamsin.")

    def test_it_was_rolled_once_and_by_looking(self):
        rolled = self.walk_in(WON)
        self.roster()
        self.do("look tamsin")
        self.do("look man")
        self.roster()
        self.assertEqual(rolled.call_count, 1)

    def test_typing_a_name_never_rolls(self):
        """In the room and not yet looked, so nothing is decided, and
        trying names must not decide it: that would be fishing for who
        is under the mask."""
        self.no_dice()
        self.viewer.move_to(self.room1, quiet=True, move_hooks=False)
        self.assertEqual(self.viewer.search("tamsin", quiet=True), [])
        self.assertIsNone(self.viewer.db.disguise_pierce_cache)

    def test_forgetting_a_name_seen_through_to(self):
        self.walk_in(WON)
        self.assertIn("You forget the name 'Tamsin'", self.do("forget tamsin"))
        self.assertNotIn("Tamsin", self.roster())

    def test_recall_reads_out_who_they_saw_through_to(self):
        self.walk_in(WON)
        self.assertIn("You remember them as: Tamsin", self.do("recall tamsin"))
        self.assertIn("You remember them as: Tamsin", self.do("recall man"))

    def test_a_mask_that_holds_gives_no_name(self):
        """The control: the roll goes the mask's way."""
        self.walk_in(LOST)
        self.assertIn("gaunt masked man", self.roster())
        self.assertNotIn("Tamsin", self.roster())
        self.assertEqual(self.do("look tamsin"), "Could not find 'tamsin'.")
        self.assertEqual(self.first(self.do("look man")), MASKED)
        self.assertEqual(self.do("recall man"),
                         "You don't recognize that person.")

    def test_and_the_viewer_has_no_entry_for_the_look(self):
        """The control on the rule itself: only watching writes the
        link, so only a watcher gets the name without a roll."""
        self.walk_in(LOST)
        self.assertNotIn(get_apparent_uid(self.them),
                         dict(self.viewer.recognition_memory))
