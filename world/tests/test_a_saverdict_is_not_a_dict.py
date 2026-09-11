"""An organ-bound condition survives a reload.

Regression pin for #2679.  `Organ.from_dict` restored persisted
conditions behind `isinstance(entry, dict)`.

Evennia wraps a persisted container in `_SaverDict`, which is **not a
`dict` subclass**, so that test was `False` for every entry that had
actually been through the database — and the `elif isinstance(entry,
MedicalCondition)` did not catch it either, because a loaded entry is a
mapping, not a live object.  Both arms missed, and the loop's stated
intent ("skip anything that doesn't recognise as one of those shapes")
turned the miss into a silent drop.

So an organ-bound condition did not survive a reload.  Measured
end-to-end on a real character before the fix::

    organ-bound conditions before save : 1
    persisted entry type               : _SaverDict
    isinstance(entry, dict)            : False
    organ conditions AFTER load        : 0

The state-level path in `MedicalState.from_dict` was never affected —
it calls the factory with no `isinstance` guard at all, which is why
state conditions persisted and organ-bound ones vanished.

ARMED, not firing: zero organ-bound conditions are persisted anywhere in
the world today, because conditions are written through
`MedicalState.add_condition`.  It fires the first time anything puts one
on an organ.

The shim is the one `world/medical/diagnose.py` and
`world/medical/severance.py` already use for this exact trap —
`hasattr(x, "get")` rather than `isinstance(x, dict)`.
"""

from __future__ import annotations

from unittest import TestCase

from world.medical.core import Organ
from world.medical.conditions import MedicalCondition


class _SaverLike:
    """A mapping that is NOT a dict subclass — `_SaverDict`'s shape."""

    def __init__(self, data):
        self._data = dict(data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]


def _condition_payload():
    return MedicalCondition(
        condition_type="infection", location="chest", severity=3,
    ).to_dict()


def _organ_snapshot(conditions):
    return {"name": "heart", "current_hp": 10, "max_hp": 10,
            "conditions": conditions}


class TestASaverDictIsNotADict(TestCase):

    def test_a_saver_wrapped_condition_is_restored(self):
        """The defect: not a dict subclass, so it was dropped."""
        organ = Organ.from_dict(
            _organ_snapshot([_SaverLike(_condition_payload())]))
        self.assertEqual(len(organ.conditions), 1)
        self.assertEqual(organ.conditions[0].condition_type, "infection")

    def test_a_saver_wrapped_snapshot_is_restored(self):
        """The whole snapshot is wrapped too, not just the entries."""
        organ = Organ.from_dict(
            _SaverLike(_organ_snapshot([_SaverLike(_condition_payload())])))
        self.assertEqual(len(organ.conditions), 1)

    # -- controls: the other two shapes must still work --------------

    def test_a_plain_dict_is_still_restored(self):
        organ = Organ.from_dict(_organ_snapshot([_condition_payload()]))
        self.assertEqual(len(organ.conditions), 1)

    def test_a_live_condition_object_passes_through(self):
        """Pre-#307 snapshots pickled the object itself. It must not go
        to the factory — the concrete check comes first."""
        live = MedicalCondition(
            condition_type="bleeding", location="chest", severity=2)
        organ = Organ.from_dict(_organ_snapshot([live]))
        self.assertEqual(len(organ.conditions), 1)
        self.assertIs(organ.conditions[0], live)

    def test_an_unrecognised_entry_is_still_skipped(self):
        """The loop's forward-compat intent survives: a shape that is
        neither a condition nor a mapping is dropped, not crashed on."""
        organ = Organ.from_dict(_organ_snapshot(["nonsense", 42, None]))
        self.assertEqual(organ.conditions, [])

    def test_no_conditions_is_not_an_error(self):
        organ = Organ.from_dict(_organ_snapshot([]))
        self.assertEqual(organ.conditions, [])
