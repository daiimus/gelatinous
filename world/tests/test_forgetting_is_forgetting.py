"""Forgetting is forgetting (#3825).

Owner, 2026-11-14, on a `forget` that blanked a name and kept the
entry: "If the game still uses it - it doesn't seem like they've been
actually forgotten. What if someones memory is blanked out by a machine
or a bioroid hacked."

`forget` used to do two wrong things.

* It kept the entry. The name was blanked and everything else stayed:
  the links, the seen-count, the game's tag for the true body. Naming
  the look again set the name back on the same entry, so the old "Also
  known as" returned and familiarity carried on.
* It cleared by true body. Forgetting somebody by name blanked every
  named voice of the same body and dropped every won see-through of
  it, whatever the observer had called them and whether or not they
  had ever connected them.

Now `world.identity.erase_look` erases the entry and what the observer
connected to it, and nothing else. The one thing kept is a LOST
see-through, which is not memory but the rule that a lost roll cannot
be bought again (`test_a_lost_see_through_is_for_good`).
"""
from types import SimpleNamespace
from unittest import TestCase

from evennia.prototypes.spawner import spawn

from world import identity
from world import voice as voice_mod
from world.identity import get_apparent_uid, get_linked_aliases
from world.tests.test_an_eyewitness_keeps_the_name import (
    LOST, WON, _MaskCase, resolve_assigned_name)


def _erase(observer, uid):
    """Fetched late so this module still LOADS against the unfixed
    tree: a loader error is not evidence."""
    erase = getattr(identity, "erase_look", None)
    assert erase is not None, "world.identity.erase_look is missing"
    return erase(observer, uid)


def _observer(memory, voices=None, verdicts=None):
    return SimpleNamespace(
        recognition_memory=memory,
        voice_memory=voices if voices is not None else {},
        db=SimpleNamespace(disguise_pierce_cache=verdicts,
                           voice_discern_cache=None))


class TestTheEntryGoes(TestCase):

    def test_nothing_of_it_is_left(self):
        memory = {"face": {"assigned_name": "Alder", "times_seen": 4,
                           "real_sleeve_uid": "sleeve-a"}}
        self.assertEqual(_erase(_observer(memory), "face"), "Alder")
        self.assertEqual(memory, {})

    def test_a_look_that_is_not_there_is_not_an_error(self):
        memory = {"face": {"assigned_name": "Alder"}}
        self.assertEqual(_erase(_observer(memory), "nobody"), "")
        self.assertIn("face", memory)

    def test_two_names_joined_only_through_it_stand_alone(self):
        """It used to be kept as the bridge, so forgetting the middle
        name changed nothing about the other two."""
        memory = {
            "face": {"assigned_name": "Bruce"},
            "mask": {"assigned_name": "Batman", "linked_to": "face",
                     "witnessed_from": "face"},
            "helm": {"assigned_name": "Knight", "linked_to": "mask",
                     "witnessed_from": "mask"},
        }
        _erase(_observer(memory), "mask")
        self.assertNotIn("mask", memory)
        self.assertEqual(get_linked_aliases(memory, "face"), [])
        self.assertEqual(get_linked_aliases(memory, "helm"), [])
        self.assertIsNone(memory["helm"]["linked_to"])
        self.assertIsNone(memory["helm"]["witnessed_from"])
        self.assertEqual(resolve_assigned_name(memory, "face")[0], "Bruce")
        self.assertEqual(resolve_assigned_name(memory, "helm")[0], "Knight")

    def test_a_look_known_only_through_it_goes_with_it(self):
        memory = {
            "face": {"assigned_name": "Tamsin"},
            "mask": {"assigned_name": "", "witnessed_from": "face",
                     "linked_to": "face", "real_sleeve_uid": "sleeve-t"},
            "hood": {"assigned_name": "", "linked_to": "mask"},
        }
        _erase(_observer(memory), "face")
        self.assertEqual(memory, {})

    def test_a_look_another_name_still_reaches_stays(self):
        """Bruce, the masked look watched to come from him, and a third
        look named Bat that was watched to come from the mask. Forget
        Bat: the masked look is still Bruce's."""
        memory = {
            "face": {"assigned_name": "Bruce"},
            "mask": {"assigned_name": "", "witnessed_from": "face",
                     "linked_to": "face"},
            "wig": {"assigned_name": "Bat", "linked_to": "mask"},
        }
        _erase(_observer(memory), "wig")
        self.assertIn("mask", memory)
        self.assertEqual(resolve_assigned_name(memory, "mask")[0], "Bruce")

    def test_a_look_the_observer_has_read_papers_about_stays(self):
        """Review round one. A wanted poster told the observer something
        about the masked look. That did not come through the name being
        forgotten, and reading the poster again would not bring it back."""
        papers = [{"name": "The Ghost", "issuer": "colony"}]
        memory = {
            "face": {"assigned_name": "Tamsin"},
            "mask": {"assigned_name": "", "witnessed_from": "face",
                     "linked_to": "face", "attested": papers},
        }
        _erase(_observer(memory), "face")
        self.assertEqual(list(memory), ["mask"])
        self.assertEqual(memory["mask"]["attested"], papers)
        self.assertIsNone(memory["mask"]["witnessed_from"])
        self.assertIsNone(memory["mask"]["linked_to"])

    def test_an_unnamed_entry_that_had_nothing_to_do_with_it_stays(self):
        """Memories written before this change hold blank entries. They
        are not swept up by forgetting somebody else."""
        memory = {
            "face": {"assigned_name": "Alder"},
            "old": {"assigned_name": "", "real_sleeve_uid": "sleeve-x"},
        }
        _erase(_observer(memory), "face")
        self.assertEqual(list(memory), ["old"])


class TestTheVoiceLearnedWithTheLook(TestCase):
    """A voice is named in one place, `remember` on somebody in front of
    you, and its entry records the look it was named with."""

    FACE = {"assigned_name": "Alder", "real_sleeve_uid": "sleeve-a"}

    def forget_the_face(self, voices, face=None):
        memory = {"face": dict(face or self.FACE)}
        _erase(_observer(memory, voices), "face")
        return voices

    def test_the_voice_named_with_the_look_goes(self):
        voices = self.forget_the_face({
            "v": {"assigned_name": "Alder", "named_with": "face",
                  "real_sleeve_uid": "sleeve-a"}})
        self.assertEqual(voices, {})

    def test_it_goes_whatever_papers_have_since_called_the_face(self):
        """Review round one, and #2652 again: named "Big J" in person,
        the face renamed "Jorge Ruiz" from his papers, then forgotten.
        Matching names left "Big J" naming him on the radio."""
        voices = self.forget_the_face(
            {"v": {"assigned_name": "Big J", "named_with": "face",
                   "real_sleeve_uid": "sleeve-a"}},
            face={"assigned_name": "Jorge Ruiz",
                  "real_sleeve_uid": "sleeve-a"})
        self.assertEqual(voices, {})

    def test_the_same_voice_named_again_with_another_look_stays(self):
        """The owner's question about the example: name him Alder
        bare-faced, then name the same man masked, as Ghost. The one
        voice is Ghost's now. Forgetting Alder leaves it."""
        voices = self.forget_the_face({
            "v": {"assigned_name": "Ghost", "named_with": "mask",
                  "real_sleeve_uid": "sleeve-a", "times_heard": 2}})
        self.assertEqual(voices["v"]["assigned_name"], "Ghost")
        self.assertEqual(voices["v"]["times_heard"], 2)

    def test_somebody_else_under_the_same_name_keeps_their_voice(self):
        """Review round one: papers can give two faces one name."""
        voices = self.forget_the_face({
            "v": {"assigned_name": "Alder", "named_with": "other-face",
                  "real_sleeve_uid": "sleeve-b"}})
        self.assertIn("v", voices)

    def test_an_older_entry_goes_by_its_name(self):
        """No record of the look it was named with."""
        voices = self.forget_the_face({
            "same": {"assigned_name": "alder", "real_sleeve_uid": "sleeve-a"},
            "no-body": {"assigned_name": "Alder", "real_sleeve_uid": None},
            "other-name": {"assigned_name": "Ghost",
                           "real_sleeve_uid": "sleeve-a"},
            "other-body": {"assigned_name": "Alder",
                           "real_sleeve_uid": "sleeve-b"},
        })
        self.assertEqual(sorted(voices), ["other-body", "other-name"])

    def test_the_voice_helper_reports_what_it_erased(self):
        erase = getattr(voice_mod, "erase_voices_named", None)
        self.assertIsNotNone(erase, "world.voice.erase_voices_named is missing")
        voices = {"a": {"assigned_name": "Alder"},
                  "b": {"assigned_name": "ALDER"},
                  "c": {"assigned_name": "Wren"}}
        observer = _observer({}, voices)
        self.assertEqual(erase(observer, "alder"), 2)
        self.assertEqual(erase(observer, "Alder"), 0)
        self.assertEqual(erase(observer, ""), 0)
        self.assertEqual(erase(observer, None), 0)

    def test_remember_records_the_look(self):
        """The writer: `remember` hands the voice the look it is naming."""
        import inspect
        from commands import CmdCharacter
        self.assertIn("look_uid=apparent_uid",
                      inspect.getsource(CmdCharacter))
        heard = SimpleNamespace(voice_memory={}, db=SimpleNamespace())
        with_voice = SimpleNamespace(sleeve_uid="sleeve-a")
        from unittest import mock
        with mock.patch.object(voice_mod, "can_hear", return_value=True), \
                mock.patch.object(voice_mod, "get_apparent_voice_uid",
                                  return_value="v"), \
                mock.patch.object(voice_mod, "voice_phrase",
                                  return_value="a low voice"):
            voice_mod.remember_voice(heard, with_voice, "Alder",
                                     look_uid="face")
        self.assertEqual(heard.voice_memory["v"]["named_with"], "face")


class TestForgettingInPlay(_MaskCase):
    """Real commands on fresh bodies. The viewer calls the bare face
    Tamsin (the harness does that)."""

    def setUp(self):
        super().setUp()
        self.rolled = self.dice(LOST)

    def bare(self):
        return dict(self.viewer.recognition_memory).get(
            get_apparent_uid(self.them))

    def test_the_entry_is_gone_from_memory(self):
        self.assertIsNotNone(self.bare())
        self.assertIn("forget the name", self.do("forget tamsin"))
        self.assertIsNone(self.bare())

    def test_naming_them_again_starts_from_nothing(self):
        """Familiarity is the seen-count. It used to carry on."""
        self.do("remember man as Tamsin")
        self.do("remember man as Tamsin")
        self.assertEqual(self.bare()["times_seen"], 3)
        self.do("forget tamsin")
        self.do("remember man as Jane")
        self.assertEqual(self.bare()["times_seen"], 1)

    def test_the_old_link_does_not_come_back(self):
        """Name the mask he was watched to put on, forget that name,
        name the mask again. It used to be the same entry, so `recall`
        read "Also known as: Tamsin" again at once."""
        self.they("wear ski mask")
        self.do("remember tamsin as Ghost")
        self.assertIn("Also known as: Tamsin", self.do("recall ghost"))
        self.do("forget ghost")
        self.assertIn("gaunt masked man", self.roster())
        self.do("remember gaunt masked man as Shade")
        said = self.do("recall shade")
        self.assertIn("You remember them as: Shade", said)
        self.assertNotIn("Also known as", said)
        self.assertNotIn("Tamsin", said)


class TestAWonSeeThroughStandsOnAName(_MaskCase):
    """Three looks of one man: his face (Tamsin), hooded, and masked.
    The viewer saw through the hood and the mask to Tamsin, and gave
    the hooded look a name of its own. Forgetting THAT name is not
    forgetting Tamsin."""

    def setUp(self):
        super().setUp()
        self.rolled = self.dice(WON)
        hood = spawn("HOODIE_HOOD_UP")[0]
        hood.move_to(self.them, quiet=True)
        self.unseen("wear hood")
        self.assertIn("Tamsin", self.roster())
        self.do("remember tamsin as Hood")
        self.unseen("remove hood")
        self.unseen("wear ski mask")
        self.assertIn("Tamsin", self.roster())

    def unseen(self, command):
        self.them.move_to(self.room2, quiet=True, move_hooks=False)
        self.them.execute_cmd(command)
        self.them.move_to(self.room1, quiet=True, move_hooks=False)

    def won(self):
        cache = dict(self.viewer.db.disguise_pierce_cache or {})
        return sorted(look for (_dbref, look), verdict in cache.items()
                      if verdict)

    def test_the_setup_is_two_won_see_throughs(self):
        self.assertEqual(len(self.won()), 2)

    def test_forgetting_the_other_name_keeps_both(self):
        """Every won see-through of the same body used to go."""
        before = self.won()
        self.assertIn("forget the name", self.do("forget hood"))
        self.assertEqual(self.won(), before)
        self.assertIn("Tamsin", self.roster())

    def test_forgetting_the_name_they_stand_on_takes_them(self):
        self.assertIn("forget the name", self.do("forget tamsin"))
        self.assertEqual(self.won(), [])
