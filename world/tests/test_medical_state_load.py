"""Medical-state load re-entrance (the Jorge loop).

Restoring a persisted ticker condition runs ``start_condition``, whose
``start_medical_script`` reads ``character.medical_state``. When that
read happens DURING a property-triggered load — before the freshly
built state is installed — the property re-triggers the load: mutual
recursion to ``RecursionError``, every ticker condition shed on every
rebuild, and an audit-log flood (45k lines for one NPC) whose queued
writes died on Evennia's log-handle reset race as ``NoneType: None``.

The fix: ``from_dict`` no longer starts tickers; ``load_medical_state``
installs the state FIRST, then restarts them.
"""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch


def _pain(severity=1):
    return {"condition_type": "pain", "severity": severity}


def _persisted(*conditions):
    return {"organs": {}, "conditions": list(conditions),
            "blood_level": 100.0, "pain_level": 0.0, "consciousness": 1.0}


class _Char:
    """Mimics the Character.medical_state property contract exactly:
    the lazy load fires on read, and the state only lands on
    ``_medical_state`` when the loader assigns it."""

    def __init__(self, data):
        self.db = SimpleNamespace(medical_state=data, archived=False)
        self.key = "Jorge"
        self.scripts = MagicMock()

    @property
    def medical_state(self):
        if not hasattr(self, "_medical_state") or self._medical_state is None:
            from world.medical.utils import load_medical_state
            load_medical_state(self)
        return self._medical_state

    @medical_state.setter
    def medical_state(self, value):
        self._medical_state = value


class TestLoadReentrance(TestCase):
    def test_ticker_restart_reads_the_installed_state(self):
        # start_medical_script reads character.medical_state — the
        # exact re-entrant read that recursed. It must now see the
        # already-installed state, not re-trigger the load.
        char = _Char(_persisted(_pain()))
        seen = []
        with patch("world.medical.script.start_medical_script",
                   side_effect=lambda c: seen.append(c.medical_state)
                   ) as starter, \
                patch("world.combat.debug.get_splattercast",
                      return_value=MagicMock()):
            state = char.medical_state    # would RecursionError pre-fix
        self.assertEqual(len(state.conditions), 1)
        starter.assert_called_once()
        self.assertIs(seen[0], state)     # the SAME installed state

    def test_conditions_survive_the_rebuild(self):
        # The loop's damage was shed conditions: every rebuild lost the
        # tickers to the caught RecursionError. All must survive now.
        char = _Char(_persisted(_pain(1), _pain(3)))
        with patch("world.medical.script.start_medical_script"), \
                patch("world.combat.debug.get_splattercast",
                      return_value=MagicMock()):
            state = char.medical_state
        self.assertEqual(
            [c.severity for c in state.conditions], [1, 3])

    def test_archived_characters_restore_without_tickers(self):
        char = _Char(_persisted(_pain()))
        char.db.archived = True
        with patch("world.medical.script.start_medical_script") as starter:
            state = char.medical_state
        self.assertEqual(len(state.conditions), 1)   # data intact
        starter.assert_not_called()                  # but no ticker

    def test_one_bad_ticker_start_never_sheds_the_rest(self):
        char = _Char(_persisted(_pain(1), _pain(2)))
        cast = MagicMock()
        with patch("world.medical.script.start_medical_script",
                   side_effect=[RuntimeError("bad script"), MagicMock()]), \
                patch("world.combat.debug.get_splattercast",
                      return_value=cast):
            state = char.medical_state
        self.assertEqual(len(state.conditions), 2)   # nothing shed
