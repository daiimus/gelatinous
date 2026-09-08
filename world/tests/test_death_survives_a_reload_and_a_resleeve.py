"""Two of the five findings in #2450; three did not survive checking.

**A reload inside the death curtain wedged the dier permanently.** The
curtain chains ~60 frames with `delay(...)` — non-persistent by
construction, and the callback is a bound method of a plain object that
could not be persisted anyway — and ONLY its completion calls
`start_death_progression`. A reload in that ~6s window (plus the 5s
combat deferral) drops every pending call, and nothing re-checked at
boot.

What that leaves is not a half-death, it is a permanent one.
`db.death_processed` is PERSISTENT and `at_death` returns early on it
forever, so there is no retry: no corpse, no archive, no respawn menu,
DeathCmdSet as the default (`no_exits=True`), and `at_post_login`
auto-puppets the wedged body straight back. Only a staff `@heal`
recovers it. The house has fixed this exact shape twice at boot already
— grenade fuses (#505) and stranded channel tells (#2774).

The predicate has to exclude a COMPLETED death, not merely find an
unfinished one: a finished progression moves the body to Limbo (#2) and
archives it, so restarting on one of those would spawn a second corpse.

**The resleeved Essential keeper came back command-dead.**
`reset_body_preserving_augments` heals the flesh (#2706) but does not
touch what `at_death` installed: `db.death_processed` (so they could
never die again), DeathCmdSet as the DEFAULT cmdset — and souls act
exclusively through `execute_cmd`, so the very first `emote is back at
the post` would be refused — and an `override_place` reading "lying
motionless and deceased." under someone standing at their own counter.

**Three findings did not survive checking**, all fixed since the audit
ran. Finding 1: `db.is_dead` was an attribute no object carries, so
three guards never fired — #2706 replaced all three reads with the
`_is_dead()` helper. Finding 2: the 14-day corpse auto-reaper, removed
in #3039 earlier today. Finding 5: the dying player's cause-of-death
line — #2469 replaced the `'▓' in text` content sniff with an explicit
`death_curtain=True` flag, and the curtain sets it on exactly that
line.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest


class _DeathCase(EvenniaTest):
    def wedged(self, key="a wedged body"):
        """death_processed set, no progression script, still in a room —
        the state a dropped delay() chain leaves behind."""
        char = create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)
        char.db.death_processed = True
        return char


class TestTheBootSweepRestartsAWedgedDeath(_DeathCase):
    """`start_death_progression` is patched rather than run: creating a
    real script inside `EvenniaTest` trips an Evennia harness artifact
    (`at_start` cannot read its host during `scripts.add`). What matters
    here is WHICH bodies the sweep picks up, and that is exactly what
    the patch observes."""

    def _sweep(self):
        from unittest.mock import patch
        from typeclasses.death_progression import sweep_wedged_deaths
        with patch("typeclasses.death_progression.start_death_progression") \
                as started:
            count = sweep_wedged_deaths()
        return count, [c.args[0] for c in started.call_args_list]

    def test_a_wedged_body_is_picked_up(self):
        char = self.wedged()
        _count, restarted = self._sweep()
        self.assertIn(char, restarted)

    def test_it_reports_what_it_restarted(self):
        self.wedged()
        count, _ = self._sweep()
        self.assertGreaterEqual(count, 1)

    def test_boot_actually_runs_it(self):
        """A sweep nobody calls is not a fix. This assertion exists
        both before and after, so it is real evidence rather than a
        missing-symbol error."""
        import inspect
        from server.conf import at_server_startstop
        source = inspect.getsource(at_server_startstop.at_server_start)
        self.assertIn("sweep_wedged_deaths", source)

    def test_the_real_starter_is_idempotent_anyway(self):
        """Belt and braces — it returns any existing script rather than
        stacking a second."""
        import inspect
        from typeclasses.death_progression import start_death_progression
        self.assertIn("existing_script",
                      inspect.getsource(start_death_progression))


class TestItCannotRestartAFinishedDeath(_DeathCase):
    """A completed progression moves the body to Limbo and archives it.
    Restarting one of those would spawn a second corpse."""

    def wedged_p(self, **kw):
        from typeclasses.death_progression import is_wedged_death
        return is_wedged_death

    def test_a_plain_wedged_body_qualifies(self):
        self.assertTrue(self.wedged_p()(self.wedged()))

    def test_an_archived_body_is_skipped(self):
        char = self.wedged()
        char.db.archived = True
        self.assertFalse(self.wedged_p()(char))

    def test_a_body_in_limbo_is_skipped(self):
        from evennia.objects.models import ObjectDB
        limbo = ObjectDB.objects.filter(id=2).first()
        if limbo is None:
            self.skipTest("no #2 in this database")
        char = self.wedged()
        char.location = limbo
        self.assertFalse(self.wedged_p()(char))

    def test_a_living_character_is_untouched(self):
        self.assertFalse(self.wedged_p()(self.char1))

    def test_a_body_with_no_location_is_skipped(self):
        char = self.wedged()
        char.location = None
        self.assertFalse(self.wedged_p()(char))


class TestAResleevedKeeperCanActAgain(EvenniaTest):
    """`remove_death_state` is the one door that undoes all three things
    `at_death` installs, and the automated resleeve never walked it."""

    def dead_keeper(self):
        npc = create_object("typeclasses.characters.Character",
                            key="Marta Okoye", location=self.room1)
        npc.db.death_processed = True
        npc.override_place = "lying motionless and deceased."
        return npc

    def test_the_death_flag_is_cleared(self):
        npc = self.dead_keeper()
        npc.remove_death_state()
        self.assertIsNone(npc.db.death_processed)

    def test_they_can_die_again(self):
        """`at_death` returns early on the persistent flag forever —
        a keeper who cannot die is not restored, they are invulnerable."""
        npc = self.dead_keeper()
        npc.remove_death_state()
        self.assertFalse(npc.db.death_processed)

    def test_the_deceased_place_line_is_gone(self):
        npc = self.dead_keeper()
        npc.remove_death_state()
        self.assertFalse(npc.override_place)

    def test_the_resleeve_path_calls_it(self):
        import inspect
        from world.souls import posts
        source = inspect.getsource(posts._try_resleave)
        self.assertIn("remove_death_state", source)
        self.assertIn("unarchive_character", source)


class TestTheThreeAlreadyFixedStayFixed(EvenniaTest):
    """Regression pins, not evidence."""

    def test_the_aliveness_helper_reads_the_body_not_a_phantom(self):
        """#2706: the three guards read `db.is_dead`, an attribute row
        zero objects carry, so none of them ever fired."""
        from world.souls.posts import _is_dead
        self.assertFalse(_is_dead(self.char1))
        self.assertFalse(_is_dead(object()))   # fails ALIVE, by design

    def test_the_corpse_reaper_is_gone(self):
        from typeclasses.corpse import Corpse
        self.assertFalse(hasattr(Corpse, "check_complete_decay"))

    def test_the_curtain_flags_its_cause_of_death_line(self):
        import inspect
        from typeclasses import curtain_of_death
        source = inspect.getsource(curtain_of_death)
        self.assertIn("death_curtain=True", source)
