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
from unittest import TestCase, mock

from evennia import create_object
from evennia.prototypes.spawner import spawn
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import get_apparent_uid
from world.tests.test_identity_bearer_mixin import _FakeBearer, _FakeLooker

def resolve_assigned_name(memory, uid):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree: a module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence."""
    from world import identity
    return identity.resolve_assigned_name(memory, uid)


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

    def test_the_entry_says_what_they_watched_it_come_from(self):
        """What the name is read through: `linked_to` alone is not
        evidence that anybody watched anything."""
        memory = dict(self.viewer.recognition_memory)
        entry = memory[get_apparent_uid(self.them)]
        self.assertEqual(entry["assigned_name"], "")
        self.assertEqual(
            memory[entry["witnessed_from"]]["assigned_name"], "Tamsin")

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

    def hood_up(self):
        """A second change, in front of the viewer: a hood over the
        mask. What the viewer is told."""
        hood = spawn("HOODIE_HOOD_UP")[0]
        hood.move_to(self.them, quiet=True)
        return self.they("wear hood")

    def test_a_viewer_who_saw_through_watches_the_next_change(self):
        """They hold no entry for the masked look: seeing through
        writes a verdict and nothing else. The hook read them as a
        stranger, told them "Tamsin puts on a drawn hood", and then
        rolled afresh for the hooded figure."""
        rolled = self.walk_in(WON)
        self.assertEqual(self.hood_up(), "Tamsin puts on a drawn hood.")
        self.assertIn("Tamsin", self.roster())
        self.assertIn("Tamsin (", self.first(self.do("look tamsin")))
        self.assertEqual(rolled.call_count, 1, "rolled for the new look")

    def test_a_viewer_the_mask_held_against_learns_nothing_from_it(self):
        """The control: they never knew who it was, and watching a
        stranger pull a hood up names nobody."""
        self.walk_in(LOST)
        self.assertNotIn("Tamsin", self.hood_up())
        self.assertNotIn("Tamsin", self.roster())
        self.assertEqual(self.do("look tamsin"), "Could not find 'tamsin'.")

    def test_typing_a_name_never_rolls(self):
        """In the room and not yet looked, so nothing is decided, and
        trying names must not decide it: that would be fishing for who
        is under the mask."""
        self.no_dice()
        self.viewer.move_to(self.room1, quiet=True, move_hooks=False)
        self.assertEqual(self.viewer.search("tamsin", quiet=True), [])
        self.assertIsNone(self.viewer.db.disguise_pierce_cache)

    def test_a_pose_never_rolls_either(self):
        """The pose resolver builds a handle for everybody in the room
        before it matches anything. It asked for the display name, so
        it rolled, and a pose could land on a name `look` had just said
        was not there."""
        self.no_dice()
        self.viewer.move_to(self.room1, quiet=True, move_hooks=False)
        self.assertEqual(self.do(".wave at tamsin"), "You wave at tamsin.")
        self.assertIsNone(self.viewer.db.disguise_pierce_cache)

    def test_forgetting_a_name_seen_through_to(self):
        self.walk_in(WON)
        self.assertIn("You forget the name 'Tamsin'", self.do("forget tamsin"))
        self.assertNotIn("Tamsin", self.roster())

    def test_forgetting_takes_the_verdict_with_it(self):
        """The look that was seen through has no memory entry, so its
        verdict was never found to clear: remember the face again and
        the masked figure was named at once, with no roll."""
        self.walk_in(WON)
        self.do("forget tamsin")
        self.assertEqual(dict(self.viewer.db.disguise_pierce_cache or {}), {})

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


class TestForgettingAMaskYouNamed(_MaskCase):
    """After `forget`, the look that carried the name names nobody.

    The viewer watched the mask go on and then gave the masked figure a
    name of its own. Forgetting that name must not leave the figure
    answering to the face's name through the link, under a message that
    says they will now appear as their description. (From there the
    viewer is where anybody is who did not watch: the mask holds unless
    they see through it, so the dice are set against them here.)"""

    def setUp(self):
        super().setUp()
        self.dice(LOST)
        self.they("wear ski mask")
        self.do("remember tamsin as Ghost")
        self.told = self.do("forget ghost")

    def test_it_says_what_then_happens(self):
        self.assertIn("You forget the name 'Ghost'", self.told)
        self.assertIn("appear as their description", self.told)

    def test_and_that_is_what_happens(self):
        self.assertIn("gaunt masked man", self.roster())
        self.assertNotIn("Tamsin", self.roster())
        self.assertNotIn("Ghost", self.roster())
        self.assertEqual(self.do("look tamsin"), "Could not find 'tamsin'.")

    def test_the_face_keeps_its_own_name(self):
        """Forgetting "Batman" leaves "Bruce" alone."""
        told = self.they("remove ski mask")
        self.assertEqual(
            told, "A gaunt masked man in a wool ski mask removes a wool "
                  "ski mask, revealing they are none other than Tamsin.")
        self.assertIn("Tamsin", self.roster())


class TestForgettingSomebodyWhoHasLeft(_MaskCase):
    """`forget` has a second door, for a name typed when nobody by it
    is in the room. It has to take the same thing away."""

    def setUp(self):
        super().setUp()
        self.dice(LOST)
        self.they("wear ski mask")
        self.do("remember tamsin as Ghost")
        self.them.move_to(self.room2, quiet=True, move_hooks=False)
        self.told = self.do("forget ghost")
        self.them.move_to(self.room1, quiet=True, move_hooks=False)

    def test_the_name_is_forgotten(self):
        self.assertIn("You forget the name 'Ghost'", self.told)

    def test_and_they_come_back_a_stranger(self):
        """Cleared of its name alone, the masked look still recorded
        the face it was watched to come from, and answered to that."""
        self.assertIn("gaunt masked man", self.roster())
        self.assertNotIn("Tamsin", self.roster())
        self.assertNotIn("Ghost", self.roster())


class TestATwoWordName(_MaskCase):
    """A pose may be aimed at one word of a name, and that has to be
    the same name a typed target answers to."""

    def setUp(self):
        super().setUp()
        self.do("remember man as Whimsical Wendy")

    def test_an_eyewitness_aims_at_one_word_of_it(self):
        self.no_dice()
        self.they("wear ski mask")
        self.assertEqual(self.do(".wave at wendy"),
                         "You wave at Whimsical Wendy.")

    def test_and_so_does_somebody_who_saw_through(self):
        self.viewer.move_to(self.room2, quiet=True, move_hooks=False)
        self.them.execute_cmd("wear ski mask")
        self.dice(WON)
        self.viewer.move_to(self.room1, quiet=True)
        self.assertEqual(self.do(".wave at wendy"),
                         "You wave at Whimsical Wendy.")
        self.assertEqual(self.first(self.do("look wendy")),
                         f"Whimsical Wendy ({MASKED})")


class TestTheWalk(TestCase):
    """`resolve_assigned_name` on bare memories: no bodies needed."""

    def named(self, memory, uid):
        with mock.patch("evennia.utils.logger.log_warn") as warned:
            found = resolve_assigned_name(memory, uid)
        warned.assert_not_called()
        return found

    def test_a_look_with_its_own_name(self):
        memory = {"mask": {"assigned_name": "Ghost", "linked_to": "face"},
                  "face": {"assigned_name": "Tamsin"}}
        self.assertEqual(self.named(memory, "mask"), ("Ghost", "mask"))

    def watched(self, linked_to):
        """An entry as the unmasking hook writes it for an eyewitness."""
        return {"assigned_name": "", "linked_to": linked_to,
                "witnessed_from": linked_to}

    def test_the_look_it_was_seen_to_come_from(self):
        memory = {"mask": self.watched("face"),
                  "face": {"assigned_name": "Tamsin"}}
        self.assertEqual(self.named(memory, "mask"), ("Tamsin", "face"))

    def test_a_link_nobody_watched_being_made_is_not_followed(self):
        """The control on the mark. This is every nameless, linked
        entry from before the change: a look `forget` cleared on the
        old code (which left the link), and a look named on a guess by
        `remember` (which links two looks of one body without asking
        whether the caller saw through) and then forgotten. Following
        these would have named them all on the day this loaded."""
        memory = {"mask": {"assigned_name": "", "linked_to": "face"},
                  "face": {"assigned_name": "Tamsin"}}
        self.assertEqual(self.named(memory, "mask"), (None, None))
        memory["mask"]["witnessed_from"] = None
        self.assertEqual(self.named(memory, "mask"), (None, None))

    def test_the_nearest_name_and_no_further(self):
        memory = {"c": self.watched("b"),
                  "b": {"assigned_name": "Near", "linked_to": "a"},
                  "a": {"assigned_name": "Far"}}
        self.assertEqual(self.named(memory, "c"), ("Near", "b"))

    def test_it_does_not_pass_through_a_look_they_did_not_watch(self):
        memory = {"c": self.watched("b"),
                  "b": {"assigned_name": "", "linked_to": "a"},
                  "a": {"assigned_name": "Far"}}
        self.assertEqual(self.named(memory, "c"), (None, None))

    def test_two_nameless_looks_linked_at_each_other(self):
        """Nothing here stops the walk but the walk itself."""
        memory = {"mask": self.watched("face"),
                  "face": self.watched("mask")}
        self.assertEqual(self.named(memory, "mask"), (None, None))
        self.assertEqual(self.named(memory, "face"), (None, None))

    def test_a_look_linked_at_itself(self):
        memory = {"mask": self.watched("mask")}
        self.assertEqual(self.named(memory, "mask"), (None, None))

    def test_a_chain_too_long_to_be_real(self):
        memory = {f"u{i}": self.watched(f"u{i + 1}") for i in range(500)}
        memory["u500"] = {"assigned_name": "Too far"}
        self.assertEqual(self.named(memory, "u0"), (None, None))

    def test_a_link_to_an_entry_that_is_gone(self):
        memory = {"mask": self.watched("gone")}
        self.assertEqual(self.named(memory, "mask"), (None, None))

    def test_a_look_the_observer_has_no_entry_for(self):
        """The control: this is everybody who did not watch."""
        memory = {"face": {"assigned_name": "Tamsin"}}
        self.assertEqual(self.named(memory, "mask"), (None, None))
        self.assertEqual(self.named({}, "mask"), (None, None))
        self.assertEqual(self.named(None, "mask"), (None, None))


class TestOtherSurfaces(TestCase):
    """The same question is asked of a body on the floor and of a trust
    grant, by uid, and they read the name by hand too."""

    WATCHED = {"face": {"assigned_name": "Tamsin"},
               "mask": {"assigned_name": "", "linked_to": "face",
                        "witnessed_from": "face"}}

    def corpse_name(self, memory):
        bearer = _FakeBearer(apparent_uid="mask")
        with mock.patch("world.identity.get_apparent_uid_for_decay",
                        return_value="mask"), \
                mock.patch("world.identity.get_apparent_uid",
                           return_value="mask"):
            return bearer.get_display_name(_FakeLooker(memory=memory))

    def test_an_eyewitness_still_knows_the_body(self):
        """Named while they stood, and anonymous the moment they fell:
        the masked look's own name is blank for whoever watched the
        mask go on."""
        self.assertEqual(self.corpse_name(self.WATCHED),
                         "fresh bearer (Tamsin)")

    def test_a_masked_body_nobody_watched_is_nobody(self):
        """The control."""
        self.assertEqual(
            self.corpse_name({"face": {"assigned_name": "Tamsin"},
                              "mask": {"assigned_name": "",
                                       "linked_to": "face"}}),
            "fresh bearer")

    def test_a_body_too_far_gone_to_know_by_eye(self):
        """The second pass: decay has taken the face, a forensic read
        recovers the look they died in, and that look is one the
        caller watched arrive."""
        bearer = _FakeBearer(stage="moderate", decay_label="moderate thing",
                             apparent_uid="mask")
        with mock.patch("world.identity.get_apparent_uid_for_decay",
                        return_value="degraded"), \
                mock.patch("world.identity.get_apparent_uid",
                           return_value="mask"), \
                mock.patch("typeclasses.identity_bearer.IdentityBearerMixin"
                           "._attempt_forensic_recognition",
                           return_value=True):
            self.assertEqual(
                bearer.get_display_name(_FakeLooker(memory=self.WATCHED)),
                "moderate thing (Tamsin)")

    def test_a_grant_is_shown_by_the_name_held_for_that_look(self):
        from world.consent import grant_display_name
        grantor = _FakeLooker(memory=self.WATCHED)
        self.assertEqual(
            grant_display_name(grantor, "mask", entry={"label": "a man"}),
            "Tamsin")


class TestWhatForgetLeavesAlone(TestCase):
    """`forget` takes the name and the mark, and leaves the link: the
    forgotten look may be all that joins two names the caller kept."""

    def setUp(self):
        from commands.CmdCharacter import _forget_entry
        self.memory = {
            "face": {"assigned_name": "Bruce"},
            "mask": {"assigned_name": "Batman", "linked_to": "face",
                     "witnessed_from": "face"},
            "helm": {"assigned_name": "Knight", "linked_to": "mask",
                     "witnessed_from": "mask"},
        }
        _forget_entry(self.memory, "mask")

    def test_the_forgotten_look_names_nobody(self):
        self.assertEqual(resolve_assigned_name(self.memory, "mask"),
                         (None, None))

    def test_the_names_on_either_side_still_go_together(self):
        from world.identity import get_linked_aliases
        self.assertEqual(get_linked_aliases(self.memory, "face"), ["Knight"])
        self.assertEqual(get_linked_aliases(self.memory, "helm"), ["Bruce"])

    def test_and_each_keeps_its_own(self):
        self.assertEqual(resolve_assigned_name(self.memory, "face")[0],
                         "Bruce")
        self.assertEqual(resolve_assigned_name(self.memory, "helm")[0],
                         "Knight")

    def test_watching_them_change_back_into_it_cuts_nothing(self):
        """The helm comes off in front of the caller, and the forgotten
        look arrives again (cell D). It is known again, by the name of
        the look it was just watched to come from, and its link is as
        it was: rewriting it here left "Bruce" joined to nobody."""
        from world.identity import _witness_known_look, get_linked_aliases
        _witness_known_look(self.memory, "mask", "helm")
        self.assertEqual(self.memory["mask"]["linked_to"], "face")
        self.assertEqual(resolve_assigned_name(self.memory, "mask"),
                         ("Knight", "helm"))
        self.assertEqual(get_linked_aliases(self.memory, "face"), ["Knight"])
        self.assertEqual(get_linked_aliases(self.memory, "helm"), ["Bruce"])

    def test_a_named_look_arriving_is_treated_as_it_always_was(self):
        """The control: cell D on an entry with its own name sets a
        missing link and nothing else."""
        from world.identity import _witness_known_look
        memory = {"a": {"assigned_name": "Ghost", "linked_to": "x"},
                  "b": {"assigned_name": "Ghost", "linked_to": None}}
        _witness_known_look(memory, "a", "y")
        self.assertEqual(memory["a"],
                         {"assigned_name": "Ghost", "linked_to": "x"})
        _witness_known_look(memory, "b", "y")
        self.assertEqual(memory["b"],
                         {"assigned_name": "Ghost", "linked_to": "y"})


class TestAThirdLook(TestCase):
    """Mask on, hood up, hood down, all in front of one viewer. The
    masked look arrives a second time, from the hood, which was itself
    watched to come from the mask."""

    def setUp(self):
        self.memory = {
            "face": {"assigned_name": "Tamsin"},
            "mask": {"assigned_name": "", "linked_to": "face",
                     "witnessed_from": "face"},
            "hood": {"assigned_name": "", "linked_to": "mask",
                     "witnessed_from": "mask"},
        }

    def test_the_mask_still_leads_to_the_face(self):
        """Recording the hood here pointed the two at each other and
        cut the face off: an eyewitness to every change, sent to the
        roll."""
        from world.identity import _witness_known_look
        _witness_known_look(self.memory, "mask", "hood")
        self.assertEqual(self.memory["mask"]["witnessed_from"], "face")
        self.assertEqual(resolve_assigned_name(self.memory, "mask"),
                         ("Tamsin", "face"))
        self.assertEqual(resolve_assigned_name(self.memory, "hood"),
                         ("Tamsin", "face"))

    def test_a_look_that_reaches_no_name_takes_the_new_one(self):
        """The control: the same arrival when the mask was forgotten.
        It leads nowhere, so what was just watched is recorded."""
        from world.identity import _witness_known_look
        self.memory["mask"]["witnessed_from"] = None
        self.memory["hood"]["assigned_name"] = "Hood"
        _witness_known_look(self.memory, "mask", "hood")
        self.assertEqual(resolve_assigned_name(self.memory, "mask"),
                         ("Hood", "hood"))


class TestWhoeverPutsTheMaskOn(_MaskCase):
    """`dress <somebody> in <a mask>`: the dresser is not sent the
    room's line, because the command gives them one of their own. They
    still watched."""

    def setUp(self):
        super().setUp()
        self.no_dice()
        mask = next(o for o in self.them.contents)
        self.heard[self.viewer].clear()
        self.them.wear_item(
            mask,
            action_template="{actor} dresses {target} in a wool ski mask.",
            action_char_refs={"actor": self.viewer, "target": self.them},
            action_pre_resolved_refs={},
            action_exclude=[self.viewer, self.them])

    def test_they_are_not_sent_the_rooms_line(self):
        self.assertEqual(self.heard[self.viewer], [])

    def test_and_go_on_knowing_them(self):
        self.assertIn("Tamsin", self.roster())
        self.assertEqual(self.first(self.do("look tamsin")),
                         f"Tamsin ({MASKED})")


class TestAMemoryFromBeforeThisChange(_MaskCase):
    """Live memories already hold nameless, linked entries with no
    record of what, if anything, was watched. They are not read for a
    name. Watching the change again records it."""

    def setUp(self):
        super().setUp()
        self.dice(LOST)
        self.they("wear ski mask")
        memory = self.viewer.recognition_memory
        del memory[get_apparent_uid(self.them)]["witnessed_from"]
        self.viewer.recognition_memory = memory
        self.viewer.db.disguise_pierce_cache = None

    def test_it_is_where_it_was_the_roll(self):
        self.assertIn("gaunt masked man", self.roster())
        self.assertNotIn("Tamsin", self.roster())
        self.assertEqual(self.do("look tamsin"), "Could not find 'tamsin'.")

    def test_watching_it_happen_again_is_watching(self):
        self.they("remove ski mask")
        self.they("wear ski mask")
        self.assertIn("Tamsin", self.roster())
        self.assertEqual(self.first(self.do("look tamsin")),
                         f"Tamsin ({MASKED})")


class TestSeeingThroughALookYouForgot(_MaskCase):
    """`forget` leaves a blank entry for the look. If the viewer then
    sees through it, the room names the person, and `recall` has to
    read out that person: it looked no further than the blank entry."""

    def setUp(self):
        super().setUp()
        self.dice(WON)
        self.they("wear ski mask")
        self.do("remember tamsin as Ghost")
        self.do("forget ghost")

    def test_the_room_names_who_they_saw_through_to(self):
        self.assertIn("Tamsin", self.roster())

    def test_and_recall_reads_out_the_same_person(self):
        self.roster()
        self.assertIn("You remember them as: Tamsin", self.do("recall man"))
        self.assertIn("You remember them as: Tamsin",
                      self.do("recall tamsin"))

