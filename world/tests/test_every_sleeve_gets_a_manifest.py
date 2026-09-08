"""Players get a manifest, and it belongs to the person (#3033).

Owner ruling, 2026-09-08: *"Give players one."*

The roll lived inside a single telnet menu node —
`respawn_finalize_template` — rather than in any shared creation path.
So it never ran for a first character by any door, and only ran for a
template respawn through that one menu. Measured live before the fix:
**0 of 57 PC sleeves had a designation**, telnet-created ones included,
while every souled NPC had one. `score` printed "Designation: NONE ON
FILE" and "(no ratings on file)" to every player in the game, and
`first_char_finalize` printed `MANIFEST: NO RECORD` to every new one.

`world.manifest.ensure_manifest` is now the single stamp, called from
all four creation doors: template respawn, flash clone, telnet first
character, and the website. The bespoke roll in the menu node is gone —
it was the only place it happened, which is exactly why nobody had one.

**The record belongs to the PERSON, not the body.** A designation is a
service record; resleeving does not issue you a new one. So a flash
clone INHERITS from the body it replaces rather than rolling again.
Live, one player's lineage runs to thirty-three sleeves under a single
`db.stack_id` — without inheritance that would read as thirty-three
different careers. (`stack_id` is the person; `sleeve_uid` is the body.)

It is idempotent because it is both the creation path and the backfill:
a character who already has a designation is left exactly alone.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.manifest import ROLLABLE, ROLLABLE_RANKS


def ensure_manifest(char, inherit_from=None):
    """Called through a wrapper so this module still LOADS against the
    unfixed tree. A module-scope import of a function that does not
    exist yet turns the whole file into a loader error, and a loader
    error is not evidence — `TestEveryDoorStamps` below has to actually
    RUN before the fix to show that three of the four doors were
    silent."""
    from world import manifest
    return manifest.ensure_manifest(char, inherit_from=inherit_from)


class _ManifestCase(EvenniaTest):
    def blank(self, key="a body"):
        char = create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)
        char.db.designation = None
        char.db.skills = None
        return char


class TestTheStamp(_ManifestCase):
    def test_a_blank_character_gets_a_designation(self):
        char = self.blank()
        self.assertTrue(ensure_manifest(char))
        self.assertTrue(char.db.designation)

    def test_it_gets_skills_too(self):
        char = self.blank()
        ensure_manifest(char)
        self.assertTrue(char.db.skills)

    def test_the_designation_is_well_formed(self):
        char = self.blank()
        ensure_manifest(char)
        d = char.db.designation
        self.assertIn(d["dept"], ROLLABLE)
        self.assertIn(d["rank"], ROLLABLE_RANKS)
        self.assertTrue(d["vessel"])

    def test_command_stays_empty(self):
        """Reserved — its story arrives as artifacts, not officers."""
        for _ in range(60):
            char = self.blank()
            ensure_manifest(char)
            self.assertNotEqual(char.db.designation["dept"], "command")
            self.assertNotEqual(char.db.designation["rank"], "commander")


class TestItIsIdempotent(_ManifestCase):
    """It is the creation path AND the backfill, so running it twice
    must never re-roll somebody's career."""

    def test_a_second_call_writes_nothing(self):
        char = self.blank()
        ensure_manifest(char)
        self.assertFalse(ensure_manifest(char))

    def test_the_record_is_unchanged(self):
        char = self.blank()
        ensure_manifest(char)
        before = dict(char.db.designation)
        ensure_manifest(char)
        self.assertEqual(dict(char.db.designation), before)

    def test_skills_survive_a_second_call(self):
        char = self.blank()
        ensure_manifest(char)
        before = dict(char.db.skills)
        ensure_manifest(char)
        self.assertEqual(dict(char.db.skills), before)


class TestTheRecordFollowsThePerson(_ManifestCase):
    def test_a_clone_inherits_the_designation(self):
        old = self.blank("the dead one")
        ensure_manifest(old)
        new = self.blank("the clone")
        ensure_manifest(new, inherit_from=old)
        self.assertEqual(dict(new.db.designation), dict(old.db.designation))

    def test_a_clone_inherits_the_skills(self):
        old = self.blank("the dead one")
        ensure_manifest(old)
        new = self.blank("the clone")
        ensure_manifest(new, inherit_from=old)
        self.assertEqual(dict(new.db.skills), dict(old.db.skills))

    def test_a_clone_of_a_blank_body_still_gets_one(self):
        """Inheriting from someone with no record must not leave the
        clone blank — that is how the gap propagates."""
        old = self.blank("the dead one")
        new = self.blank("the clone")
        ensure_manifest(new, inherit_from=old)
        self.assertTrue(new.db.designation)

    def test_a_fresh_person_does_not_inherit(self):
        a = self.blank("one")
        ensure_manifest(a)
        b = self.blank("two")
        ensure_manifest(b)
        # Different people: nothing was copied. (They may coincide by
        # chance, so assert the CALL did not link them, not that the
        # rolls differ.)
        self.assertTrue(b.db.designation)


class TestEveryDoorStamps(EvenniaTest):
    """The defect was placement, not logic — the roll existed and sat in
    one menu node. Pin all four doors."""

    def _source(self, obj):
        import inspect
        return inspect.getsource(obj)

    def test_the_template_respawn_helper(self):
        from commands.charcreate import create_character_from_template
        self.assertIn("ensure_manifest", self._source(create_character_from_template))

    def test_the_flash_clone(self):
        from commands.charcreate import create_flash_clone
        self.assertIn("ensure_manifest", self._source(create_flash_clone))

    def test_the_telnet_first_character(self):
        from commands.charcreate import first_char_finalize
        self.assertIn("ensure_manifest", self._source(first_char_finalize))

    def test_the_website(self):
        from web.website.views import characters
        self.assertIn("ensure_manifest", self._source(characters))

    def test_the_menu_node_no_longer_rolls_it_itself(self):
        """It was the only place it happened. If it still rolls, the
        stamp has not actually moved."""
        from commands.charcreate import respawn_finalize_template
        self.assertNotIn("roll_designation", self._source(respawn_finalize_template))


class TestScoreStopsSayingNoneOnFile(_ManifestCase):
    def test_a_stamped_character_has_a_designation_line(self):
        from world.manifest import designation_line
        char = self.blank()
        ensure_manifest(char)
        line = designation_line(char)
        self.assertTrue(line)
        self.assertNotIn("NONE ON FILE", str(line).upper())

    def test_a_stamped_character_has_rated_skills(self):
        from world.manifest import rated_skills
        char = self.blank()
        ensure_manifest(char)
        self.assertTrue(rated_skills(char))
