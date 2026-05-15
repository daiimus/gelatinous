"""
End-to-end integration tests for the disguise-piercing pipeline.

Unlike the rest of the identity test suite — which composes mocks for
speed and isolation — this module spins up real Evennia ``Character``
instances and exercises the production
:meth:`typeclasses.characters.Character.get_display_name` pipeline.

The goal is to catch integration bugs that mocks paper over:

* ``Character.get_display_name`` actually calling
  :func:`world.identity.attempt_display_pierce` with the real
  ``recognition_memory`` attribute.
* :func:`attempt_disguise_pierce` reading and writing the real
  ``db.disguise_pierce_cache`` attribute on a saved typeclass.
* :func:`get_apparent_uid` returning a *different* hash when an
  override is set on a real character, so the cache key actually
  changes when the disguise changes.
* The reverse-lookup index (``real_sleeve_uid``) holding up across a
  real :meth:`AttributeProperty` round-trip.

Run via::

    evennia test world.tests.test_pierce_integration
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import Character
from world.identity import (
    DISGUISE_PIERCE_VECTOR_PENALTY,
    get_apparent_uid,
)


class TestPierceIntegrationEndToEnd(EvenniaTest):
    """Drive the pierce pipeline through real Character typeclasses."""

    character_typeclass = Character

    def setUp(self) -> None:
        super().setUp()
        # EvenniaTest creates self.char1 / self.char2 of self.character_typeclass.
        # We need stable, predictable sleeve_uids and a known starting
        # state for recognition_memory.
        self.observer = self.char1
        self.target = self.char2
        self.observer.sleeve_uid = "sleeve-observer-001"
        self.target.sleeve_uid = "sleeve-target-002"
        # recognition_memory has autocreate=True so it exists already;
        # reset to a known empty dict to avoid pollution across tests.
        self.observer.recognition_memory = {}
        # Clear any pre-existing pierce cache.
        self.observer.db.disguise_pierce_cache = None
        # Give the target a real silhouette so get_sdesc() renders an
        # actual sdesc instead of falling back to self.key (which would
        # mask name-leak vs sdesc-fallback in the pierce-fail path).
        self.target.height = "tall"
        self.target.build = "lean"
        self.target.sdesc_keyword = "man"

    # ------------------------------------------------------------------
    # Recognition path (no disguise)
    # ------------------------------------------------------------------

    def test_assigned_name_used_when_observer_remembers(self) -> None:
        """When observer has the target's *current* Apparent UID in
        ``recognition_memory``, ``get_display_name`` returns the
        assigned name without invoking the pierce roll.
        """
        apparent_uid = get_apparent_uid(self.target)
        self.assertIsNotNone(apparent_uid)
        self.observer.recognition_memory = {
            apparent_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 3,
            }
        }
        name = self.target.get_display_name(looker=self.observer)
        self.assertEqual(name, "Jorge")

    def test_self_lookup_returns_real_key(self) -> None:
        """A character looking at themselves always sees their own
        ``self.key`` regardless of memory or disguise state.
        """
        name = self.target.get_display_name(looker=self.target)
        self.assertEqual(name, self.target.key)

    # ------------------------------------------------------------------
    # Pierce path — bare-face memory + presentation shift
    # ------------------------------------------------------------------

    def test_pierce_succeeds_surfaces_bare_assigned_name(self) -> None:
        """Observer remembers the bare sleeve under one Apparent UID;
        target then puts on a height override (new Apparent UID).  With
        the opposed roll forced to succeed, ``get_display_name``
        surfaces the bare entry's ``assigned_name``.
        """
        # Bare-face entry: keyed on a *different* UID than the
        # disguised presentation we'll generate below.
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 5,
            }
        }
        # Apply a disguise override so target's current Apparent UID
        # shifts away from anything in memory.
        self.target.db.height_override = "tall"
        disguised_uid = get_apparent_uid(self.target)
        self.assertNotEqual(disguised_uid, bare_uid)

        # Force the opposed roll to favour the observer.
        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(100, 1, 99),
        ):
            name = self.target.get_display_name(looker=self.observer)

        self.assertEqual(name, "Jorge")

    def test_pierce_fails_falls_back_to_articled_sdesc(self) -> None:
        """When the opposed roll favours the target, the observer sees
        the indefinite-articled sdesc — no leak of the bare name.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 1,
            }
        }
        self.target.db.height_override = "tall"

        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(1, 100, -99),
        ):
            name = self.target.get_display_name(looker=self.observer)

        # Should not be the assigned name.
        self.assertNotEqual(name, "Jorge")
        # And should not be the target's real key (no leak via self.key).
        self.assertNotEqual(name, self.target.key)

    # ------------------------------------------------------------------
    # Cache contract — real db.disguise_pierce_cache round-trip
    # ------------------------------------------------------------------

    def test_pierce_result_cached_on_observer_db(self) -> None:
        """After one resolved pierce attempt, the result is persisted
        to ``observer.db.disguise_pierce_cache`` keyed on
        ``(target.dbref, apparent_uid)``.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 5,
            }
        }
        self.target.db.height_override = "tall"
        disguised_uid = get_apparent_uid(self.target)

        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(100, 1, 99),
        ):
            self.target.get_display_name(looker=self.observer)

        cache = self.observer.db.disguise_pierce_cache
        self.assertIsNotNone(cache)
        key = (self.target.dbref, disguised_uid)
        self.assertIn(key, cache)
        self.assertTrue(cache[key])

    def test_cached_result_skips_reroll(self) -> None:
        """A cached pierce result is honoured — even an opposed roll
        that would otherwise fail is not consulted again.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 5,
            }
        }
        self.target.db.height_override = "tall"
        disguised_uid = get_apparent_uid(self.target)

        # Pre-seed cache with a TRUE result for the current disguise.
        self.observer.db.disguise_pierce_cache = {
            (self.target.dbref, disguised_uid): True
        }

        # Roll would *fail* if consulted — but the cache should win.
        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(1, 100, -99),
        ) as roll:
            name = self.target.get_display_name(looker=self.observer)

        self.assertEqual(name, "Jorge")
        roll.assert_not_called()

    def test_disguise_change_invalidates_old_cache_entry(self) -> None:
        """A new disguise produces a new Apparent UID, which is a
        different cache key — the old failure does not carry over.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 5,
            }
        }
        # First disguise: a height override.
        self.target.db.height_override = "tall"
        first_uid = get_apparent_uid(self.target)

        # Pre-seed FAIL for the first disguise.
        self.observer.db.disguise_pierce_cache = {
            (self.target.dbref, first_uid): False
        }

        # Switch to a different disguise (new override value -> new UID).
        self.target.db.height_override = None
        self.target.db.build_override = "slight"
        second_uid = get_apparent_uid(self.target)
        self.assertNotEqual(first_uid, second_uid)

        # Fresh roll succeeds for the new disguise.
        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(100, 1, 99),
        ):
            name = self.target.get_display_name(looker=self.observer)

        self.assertEqual(name, "Jorge")
        cache = self.observer.db.disguise_pierce_cache
        self.assertFalse(cache[(self.target.dbref, first_uid)])
        self.assertTrue(cache[(self.target.dbref, second_uid)])

    # ------------------------------------------------------------------
    # Reverse-lookup index contract on real AttributeProperty
    # ------------------------------------------------------------------

    def test_pierce_skipped_when_no_bare_face_in_memory(self) -> None:
        """No reverse-lookup match -> no pierce attempt -> sdesc."""
        # Memory exists but contains entries for *other* sleeves only.
        self.observer.recognition_memory = {
            "uid-someone-else": {
                "assigned_name": "Maria",
                "real_sleeve_uid": "sleeve-different-999",
                "times_seen": 5,
            }
        }
        self.target.db.height_override = "tall"

        # Roll should never be called.
        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(100, 1, 99),
        ) as roll:
            name = self.target.get_display_name(looker=self.observer)

        roll.assert_not_called()
        self.assertNotEqual(name, "Maria")

    def test_pierce_skipped_when_bare_entry_has_no_assigned_name(self) -> None:
        """Reverse-lookup matches but the candidate entry has an empty
        ``assigned_name`` (observer saw the sleeve but never named it);
        pierce is not attempted because there is nothing to surface.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "",  # never named
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 5,
            }
        }
        self.target.db.height_override = "tall"

        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(100, 1, 99),
        ) as roll:
            self.target.get_display_name(looker=self.observer)

        roll.assert_not_called()

    # ------------------------------------------------------------------
    # Disguise vector counting — real attribute access path
    # ------------------------------------------------------------------

    def test_disguise_vector_penalty_uses_real_db_overrides(self) -> None:
        """``_count_disguise_vectors`` reads real ``db.*_override``
        attributes; verify the penalty actually scales with vectors by
        constructing a roll that succeeds with one vector but fails
        with three.
        """
        bare_uid = "uid-bare-face"
        self.observer.recognition_memory = {
            bare_uid: {
                "assigned_name": "Jorge",
                "real_sleeve_uid": self.target.sleeve_uid,
                "times_seen": 0,  # no familiarity bonus
            }
        }
        # Single vector: height_override only.
        self.target.db.height_override = "tall"

        # Pick a margin that beats the 1-vector penalty but not 3.
        # success := (obs + fam) > (tgt + penalty)
        # 1 vector  -> penalty = 1 * VECTOR_PENALTY
        # 3 vectors -> penalty = 3 * VECTOR_PENALTY
        # Roll obs=10, tgt=10 -> needs (10 + 0) > (10 + penalty)
        # → fails always with VECTOR_PENALTY >= 0.  Use obs=20, tgt=10.
        margin = DISGUISE_PIERCE_VECTOR_PENALTY * 2  # comfortably beats 1
        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(10 + margin, 10, margin),
        ):
            name = self.target.get_display_name(looker=self.observer)
        self.assertEqual(name, "Jorge")

        # Now stack three vectors — penalty triples and the roll fails.
        # Clear the cached True from the previous pierce on this UID.
        self.observer.db.disguise_pierce_cache = None
        self.target.db.build_override = "slight"
        self.target.db.keyword_override = "man"

        with patch(
            "world.combat.dice.opposed_roll",
            return_value=(10 + margin, 10, margin),
        ):
            name = self.target.get_display_name(looker=self.observer)
        self.assertNotEqual(name, "Jorge")
