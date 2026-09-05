"""Bleeding detection must read the field, not stringify the object.

It worked by ACCIDENT, through two faults that cancelled out (#2701):

    bleeding = any("bleed" in str((c.get("type") if isinstance(c, dict)
                                   else c) or "").lower() ...)

There is no `type` key on a stored condition -- the fields are
`condition_type`, `severity`, `location` and so on -- so that branch
would return None. It was never taken, because stored conditions are
`_SaverDict`, which is NOT a dict subclass, so `isinstance` failed and
the `else c` branch stringified the WHOLE condition. The substring then
hit `condition_type='minor_bleeding'` and the answer came out right.

THE TRAP: the recommended `_SaverDict` cleanup in #2679 -- duck-type or
deserialize so isinstance checks stop failing -- would have routed this
into the `type` branch, returned None, and SILENTLY stopped detecting
bleeding, dropping 0.35 of pressure from every bleeding soul.

Verified on the live database before and after: 23 bodies carry
conditions and the old and new expressions agree on every one.
"""
from unittest import TestCase

from world.souls import needs as needs_mod
from world.souls.needs import health_pressure

_is_bleeding_condition = getattr(needs_mod, "_is_bleeding_condition", None)


class _SaverLike:
    """Dict-LIKE without being a dict — the shape that made the old
    expression work by accident. `_SaverDict` is not a dict subclass."""

    def __init__(self, **fields):
        self._f = dict(fields)

    def get(self, key, default=None):
        return self._f.get(key, default)

    def keys(self):
        return self._f.keys()

    def __str__(self):
        return str(self._f)


class _Soul:
    def __init__(self, conditions):
        self.db = type("db", (), {"medical_state": {"conditions": conditions}})()


def _old_expression(conds):
    """The expression this replaced, reproduced verbatim so the trap can
    be demonstrated rather than described."""
    return any("bleed" in str((c.get("type") if isinstance(c, dict)
                               else c) or "").lower()
               for c in conds)


class TestTheTrapIsReal(TestCase):
    """Runs against ANY build, because it tests the old expression
    directly rather than the module. This is the whole reason working
    code was changed."""

    def test_the_old_expression_worked_on_saverdict_shapes(self):
        cond = _SaverLike(condition_type="minor_bleeding")
        self.assertTrue(_old_expression([cond]),
                        "the accident is misdescribed")

    def test_the_old_expression_BREAKS_on_a_real_dict(self):
        """What #2679's `_SaverDict` cleanup would have produced. The
        `type` key does not exist, so the isinstance branch returns None
        and bleeding stops being detected -- silently, dropping 0.35 of
        pressure from every bleeding soul."""
        self.assertFalse(
            _old_expression([{"condition_type": "minor_bleeding"}]),
            "the trap does not reproduce; re-check before trusting this")

    def test_the_old_expression_matched_unrelated_fields(self):
        """It searched the whole serialized condition, not a field."""
        cond = _SaverLike(condition_type="pain", notes="stopped bleeding")
        self.assertTrue(_old_expression([cond]))


class TestItReadsTheRealField(TestCase):
    def test_a_bleeding_condition_is_detected(self):
        cond = _SaverLike(condition_type="minor_bleeding", severity=2)
        self.assertTrue(_is_bleeding_condition(cond))

    def test_a_non_bleeding_condition_is_not(self):
        for ctype in ("pain", "infection", "addiction",
                      "consciousness_suppression"):
            with self.subTest(ctype=ctype):
                self.assertFalse(
                    _is_bleeding_condition(_SaverLike(condition_type=ctype)))

    def test_it_survives_the_saverdict_cleanup(self):
        """THE POINT. A REAL dict — what #2679's cleanup would produce —
        must still be detected. The old expression would have read the
        nonexistent `type` key here and returned None."""
        self.assertTrue(_is_bleeding_condition(
            {"condition_type": "minor_bleeding", "severity": 2}))

    def test_it_does_not_match_an_unrelated_field(self):
        """The substring ran over the WHOLE serialized condition, so any
        future field whose name or value contained 'bleed' triggered
        it."""
        cond = _SaverLike(condition_type="pain",
                          location="bleeder_valve", notes="stopped bleeding")
        self.assertFalse(_is_bleeding_condition(cond))

    def test_something_that_is_not_condition_shaped_is_not_bleeding(self):
        for junk in (None, "minor_bleeding", 42, object()):
            with self.subTest(junk=junk):
                self.assertFalse(_is_bleeding_condition(junk))


class TestThePressureIsUnchanged(TestCase):
    """Behaviour-identical on every shape the live world holds — the
    point of the change is the trap, not the answer."""

    def _p(self, *ctypes):
        return health_pressure(_Soul(
            [_SaverLike(condition_type=c) for c in ctypes]))

    def test_a_bleeding_body_carries_the_bleed_term(self):
        self.assertAlmostEqual(self._p("minor_bleeding"), 0.12 + 0.35,
                               places=3)

    def test_a_non_bleeding_body_does_not(self):
        self.assertAlmostEqual(self._p("pain"), 0.12, places=3)

    def test_it_still_caps_at_one(self):
        self.assertEqual(self._p(*(["pain"] * 12)), 1.0)

    def test_a_body_with_no_conditions_is_zero(self):
        self.assertEqual(health_pressure(_Soul([])), 0.0)

    def test_an_unreadable_body_reads_as_well(self):
        broken = type("x", (), {"db": type("db", (), {})()})()
        self.assertEqual(health_pressure(broken), 0.0)
