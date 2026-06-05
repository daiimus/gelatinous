"""Regression test for the severed-organ injury_type=None crash.

Playtest surfaced a traceback when looking at a living rat that had
been severed: ``getattr(messages, None)`` raised ``TypeError:
attribute name must be string, not 'NoneType'``.

Root cause: ``sever_character_body`` sets ``current_hp = 0`` and
``wound_stage = \"severed\"`` directly on the organ but never goes
through ``Organ.take_damage``, so ``organ.injury_type`` stays at
its init-time ``None``.

``_determine_injury_type_from_organ`` then hit
``if hasattr(organ, 'injury_type') and organ.injury_type != \"generic\"``
— ``None != \"generic\"`` evaluates True, so it returned ``None``,
which downstream ``getattr(messages, None)`` rejected.

Fix: guard the truthy check and the consumer's ``getattr`` against
non-string input.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from world.medical.wounds.longdesc_hooks import _resolve_compound_template
from world.medical.wounds.wound_descriptions import (
    _determine_injury_type_from_organ,
)


def _organ(name="tail_vertebrae", injury_type=None):
    return SimpleNamespace(
        name=name,
        injury_type=injury_type,
        conditions=[],
    )


class DetermineInjuryTypeHandlesNone(TestCase):

    def test_none_falls_through_to_default(self):
        # An organ with no recorded injury_type (severed via
        # sever_character_body, never went through take_damage) used
        # to return None; now falls through to a safe default.
        out = _determine_injury_type_from_organ(_organ(injury_type=None))
        self.assertIsNotNone(out)
        self.assertIsInstance(out, str)

    def test_generic_falls_through(self):
        # Generic was already in the fall-through path; sanity-check
        # nothing regressed.
        out = _determine_injury_type_from_organ(
            _organ(injury_type="generic")
        )
        self.assertEqual(out, "generic")

    def test_specific_injury_type_preserved(self):
        out = _determine_injury_type_from_organ(
            _organ(injury_type="cut")
        )
        self.assertEqual(out, "cut")


class ResolveCompoundTemplateHandlesNoneInjuryType(TestCase):

    def test_none_does_not_raise(self):
        # Defensive: even if a stale ``None`` injury_type slips
        # through the wound list, the renderer must not crash with
        # ``TypeError: attribute name must be string``.
        try:
            _resolve_compound_template(None, "fresh")
        except TypeError as exc:
            self.fail(
                f"_resolve_compound_template raised on None injury_type: {exc}"
            )

    def test_non_string_does_not_raise(self):
        try:
            _resolve_compound_template(123, "fresh")
        except TypeError as exc:
            self.fail(f"raised on non-string injury_type: {exc}")
