"""Who dispatch can see, and who a medic should treat (#2756, #2757).

#2756 — two attributes name a medic. `notice_casualty` accepts EITHER
`db.soul_role` or `db.role`; dispatch accepted only `role`, and not as a
late comparison but in the QUERYSET (`db_attributes__db_key="role"`), so
a soul carrying only `soul_role` was never in the candidate set at all.
Measured live: 3 medics by `soul_role`, 1 also carrying `role` — two of
the colony's three were invisible to dispatch.

#2757 — neither `find_casualty` nor `treat_casualty` checked whether the
casualty was dead. A body stays in the room as an ordinary Character for
DEATH_PROGRESSION_DURATION (90s) before corpse conversion, and passes
every filter: it is a character, it has a pk, and it is certainly not
conscious. The bleeding tiebreak is unconditional, so a bleeding corpse
DISPLACED a living unconscious victim.
"""
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from world.director import medical
from world.director.dispatch import _npcs_with_roles


class TestDispatchSeesEveryMedic(EvenniaCommandTest):
    def _medic(self, key, **attrs):
        npc = create_object("typeclasses.characters.Character", key=key,
                            location=self.room1)
        for k, v in attrs.items():
            npc.attributes.add(k, v)
        return npc

    def test_a_medic_named_by_soul_role_is_found(self):
        npc = self._medic("SoulMedic", soul_role="medic")
        self.assertIn(npc, _npcs_with_roles({"medic"}))

    def test_a_medic_named_by_role_is_still_found(self):
        """The pin: the attribute that already worked must keep working."""
        npc = self._medic("RoleMedic", role="medic")
        self.assertIn(npc, _npcs_with_roles({"medic"}))

    def test_a_medic_carrying_both_appears_once(self):
        """`.distinct()` matters now that two keys can match one object."""
        npc = self._medic("BothMedic", role="medic", soul_role="medic")
        found = [o for o in _npcs_with_roles({"medic"}) if o == npc]
        self.assertEqual(len(found), 1)

    def test_a_different_role_is_not_swept_in(self):
        self._medic("Barkeep", soul_role="bartender")
        self.assertEqual(
            [o.key for o in _npcs_with_roles({"medic"})], [])

    def test_an_object_that_is_not_a_character_is_excluded(self):
        item = create_object("typeclasses.items.Item", key="a role badge",
                             location=self.room1)
        item.attributes.add("role", "medic")
        self.assertNotIn(item, _npcs_with_roles({"medic"}))


class TestTheDeadAreNotCasualties(EvenniaCommandTest):
    def _downed(self, key, bleeding=False, dead=False):
        char = create_object("typeclasses.characters.Character", key=key,
                             location=self.room1)
        char._test_bleeding = bleeding
        char._test_dead = dead
        return char

    def _find(self):
        def bleeding(c):
            return getattr(c, "_test_bleeding", False)

        def dead(c):
            return getattr(c, "_test_dead", False)

        with mock.patch.object(medical, "_is_bleeding", side_effect=bleeding), \
             mock.patch.object(medical, "_is_dead", side_effect=dead), \
             mock.patch("world.consent.is_conscious", return_value=False):
            return medical.find_casualty(self.room1)

    def setUp(self):
        super().setUp()
        for obj in list(self.room1.contents):
            if obj in (self.char1, self.char2):
                obj.location = self.room2

    def test_a_bleeding_corpse_does_not_outrank_a_living_victim(self):
        """The exact reported shape: one just died bleeding, one is
        unconscious and not visibly bleeding."""
        self._downed("TheDead", bleeding=True, dead=True)
        alive = self._downed("TheLiving", bleeding=False, dead=False)
        self.assertIs(self._find(), alive)

    def test_a_dead_body_is_not_selected_even_when_alone(self):
        self._downed("TheDead", bleeding=True, dead=True)
        self.assertIsNone(self._find())

    def test_a_bleeding_living_victim_still_wins(self):
        """The pin: triage must keep preferring the bleeding casualty."""
        self._downed("Quiet", bleeding=False, dead=False)
        bleeder = self._downed("Bleeder", bleeding=True, dead=False)
        self.assertIs(self._find(), bleeder)

    def test_a_lone_living_victim_is_still_found(self):
        alive = self._downed("TheLiving", bleeding=False, dead=False)
        self.assertIs(self._find(), alive)


class TestTheDeathPredicate(EvenniaCommandTest):
    def test_a_living_character_is_not_dead(self):
        self.assertFalse(medical._is_dead(self.char1))

    def test_a_dead_character_is_dead(self):
        with mock.patch.object(type(self.char1), "is_dead",
                               return_value=True):
            self.assertTrue(medical._is_dead(self.char1))

    def test_an_unreadable_body_reads_alive(self):
        """Fails ALIVE: refusing to treat a living casualty is the worse
        error of the two."""
        boom = mock.MagicMock()
        boom.is_dead.side_effect = RuntimeError("no medical state")
        self.assertFalse(medical._is_dead(boom))
