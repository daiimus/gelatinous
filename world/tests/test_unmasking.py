"""Tests for the unmasking-moments broadcast pipeline.

Covers the engine added in PR 3:

* :class:`world.identity.apply_signature_change` — context manager that
  detects UID transitions and dispatches :func:`_broadcast_unmasking`.
* :func:`_broadcast_unmasking` — the 4-cell A/B/C/D matrix that updates
  in-room observers' recognition memory.
* :func:`_collect_unmasking_observers` — same-room, conscious, has-memory
  filter.
* :func:`walk_linked_chain` / :func:`get_linked_aliases` — chain
  traversal helpers (with cycle and max-hops defenses).

These tests exercise the engine directly without going through CmdSets;
wiring tests live alongside the relevant command/mixin modules.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from world.identity import (
    _broadcast_unmasking,
    _broadcast_unmask_with_action,
    _build_link_entry,
    _collect_unmasking_observers,
    _LINKED_CHAIN_MAX_HOPS,
    _send_unmasking_message,
    apply_signature_change,
    get_linked_aliases,
    walk_linked_chain,
)
from world.tests._identity_helpers import make_recognition_entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeRoom:
    """Minimal stand-in for a location with ``contents`` and a ``key``."""

    def __init__(self, key: str = "Test Room") -> None:
        self.key = key
        self.contents: list = []


class _FakeObserver:
    """Stand-in for an in-room character that can observe an unmasking.

    Mirrors the duck-typed surface read by
    :func:`_collect_unmasking_observers` (``recognition_memory``,
    ``is_unconscious``, ``location``) and the broadcast pipeline
    (``recognition_memory`` writeback).
    """

    def __init__(
        self,
        *,
        key: str = "Observer",
        location: _FakeRoom | None = None,
        recognition_memory: dict | None = None,
        unconscious: bool = False,
        is_unconscious_raises: bool = False,
    ) -> None:
        self.key = key
        self.location = location
        self.recognition_memory = (
            recognition_memory if recognition_memory is not None else {}
        )
        self._unconscious = unconscious
        self._is_unconscious_raises = is_unconscious_raises
        self.messages: list[str] = []
        if location is not None:
            location.contents.append(self)

    def is_unconscious(self) -> bool:
        if self._is_unconscious_raises:
            raise AttributeError("simulated broken medical surface")
        return self._unconscious

    def msg(self, text: str = "", **kwargs) -> None:
        # Capture for assertions; ignore kwargs (type, etc.).
        del kwargs
        self.messages.append(text)


class _FakeTarget:
    """The character whose Apparent UID transitions.

    Implements just enough surface for the broadcast pipeline:
    ``location``, ``get_sdesc``, ``key``.
    """

    def __init__(
        self,
        *,
        key: str = "Jorge",
        location: _FakeRoom | None = None,
        sdesc: str = "a tall lean man",
    ) -> None:
        self.key = key
        self.location = location
        self._sdesc = sdesc
        if location is not None:
            location.contents.append(self)

    def get_sdesc(self) -> str:
        return self._sdesc


class _FakeNonCharacter:
    """An item-like object in the room: no ``recognition_memory`` attr."""

    def __init__(self, location: _FakeRoom) -> None:
        self.key = "rock"
        location.contents.append(self)


# ---------------------------------------------------------------------------
# _collect_unmasking_observers
# ---------------------------------------------------------------------------


class TestCollectUnmaskingObservers(TestCase):
    """Eligibility filter for in-room observers."""

    def test_returns_empty_when_target_has_no_location(self) -> None:
        target = _FakeTarget(location=None)
        self.assertEqual(_collect_unmasking_observers(target), [])

    def test_excludes_self(self) -> None:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        target.recognition_memory = {}  # self has memory too
        self.assertEqual(_collect_unmasking_observers(target), [])

    def test_excludes_objects_without_recognition_memory(self) -> None:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        _FakeNonCharacter(room)
        self.assertEqual(_collect_unmasking_observers(target), [])

    def test_excludes_unconscious_observers(self) -> None:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        awake = _FakeObserver(location=room, key="awake")
        _FakeObserver(location=room, key="asleep", unconscious=True)
        observers = _collect_unmasking_observers(target)
        self.assertEqual(observers, [awake])

    def test_treats_broken_is_unconscious_as_conscious(self) -> None:
        """A raising ``is_unconscious`` must not nuke the broadcast."""
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        broken = _FakeObserver(
            location=room, key="broken", is_unconscious_raises=True
        )
        observers = _collect_unmasking_observers(target)
        self.assertEqual(observers, [broken])

    def test_returns_multiple_in_iteration_order(self) -> None:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        a = _FakeObserver(location=room, key="a")
        b = _FakeObserver(location=room, key="b")
        c = _FakeObserver(location=room, key="c")
        self.assertEqual(_collect_unmasking_observers(target), [a, b, c])


# ---------------------------------------------------------------------------
# _broadcast_unmasking — 4-cell matrix
# ---------------------------------------------------------------------------


class TestBroadcastUnmaskingShortCircuits(TestCase):
    """Pre-matrix bailouts: ``None`` UIDs and unchanged UIDs."""

    def _setup_observer_with_known(self, old_uid: str) -> _FakeObserver:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        observer = _FakeObserver(
            location=room,
            recognition_memory={
                old_uid: make_recognition_entry(assigned_name="Jorge")
            },
        )
        self.target = target
        return observer

    def test_none_old_uid_short_circuits(self) -> None:
        observer = self._setup_observer_with_known("uid-old")
        before = dict(observer.recognition_memory)
        _broadcast_unmasking(self.target, None, "uid-new")
        self.assertEqual(observer.recognition_memory, before)

    def test_none_new_uid_short_circuits(self) -> None:
        observer = self._setup_observer_with_known("uid-old")
        before = dict(observer.recognition_memory)
        _broadcast_unmasking(self.target, "uid-old", None)
        self.assertEqual(observer.recognition_memory, before)

    def test_unchanged_uid_short_circuits(self) -> None:
        observer = self._setup_observer_with_known("uid-same")
        before_entry = dict(observer.recognition_memory["uid-same"])
        _broadcast_unmasking(self.target, "uid-same", "uid-same")
        self.assertEqual(
            observer.recognition_memory["uid-same"], before_entry
        )


class TestBroadcastCellA(TestCase):
    """Observer knew neither old nor new UID — no-op."""

    def test_strangers_remain_strangers(self) -> None:
        room = _FakeRoom()
        target = _FakeTarget(location=room)
        observer = _FakeObserver(location=room, recognition_memory={})
        _broadcast_unmasking(target, "uid-old", "uid-new")
        self.assertEqual(observer.recognition_memory, {})


class TestBroadcastCellB(TestCase):
    """Observer knew old only — mark lost, auto-create linked new entry."""

    def setUp(self) -> None:
        self.room = _FakeRoom("Alley")
        self.target = _FakeTarget(location=self.room, sdesc="a hooded figure")
        self.observer = _FakeObserver(
            location=self.room,
            recognition_memory={
                "uid-old": make_recognition_entry(
                    assigned_name="Jorge",
                    sdesc_at_first_encounter="a tall lean man",
                )
            },
        )

    def test_old_entry_marked_lost_contact(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertTrue(
            self.observer.recognition_memory["uid-old"]["lost_contact"]
        )

    def test_new_entry_created_with_link_back(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        new_entry = self.observer.recognition_memory["uid-new"]
        self.assertEqual(new_entry["linked_to"], "uid-old")
        self.assertEqual(new_entry["assigned_name"], "")
        self.assertEqual(new_entry["sdesc_at_last_encounter"], "a hooded figure")
        self.assertEqual(new_entry["location_first_seen"], "Alley")

    def test_assigned_name_on_old_preserved(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-old"]["assigned_name"],
            "Jorge",
        )

    def test_old_entry_backfills_real_sleeve_uid(self) -> None:
        """Lazy backfill on cell B's old entry.

        Mirrors the contract in cells C and D: any entry touched by
        the unmasking pipeline gets ``real_sleeve_uid`` populated
        from the live target when missing.  This keeps legacy
        entries from staying pierce-ineligible forever after their
        owner walks through a disguise transition.
        """
        self.target.sleeve_uid = "sleeve-jorge"
        # Pre-condition: old entry has no real_sleeve_uid (legacy).
        self.observer.recognition_memory["uid-old"].pop(
            "real_sleeve_uid", None
        )
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-old"]["real_sleeve_uid"],
            "sleeve-jorge",
        )

    def test_old_entry_preserves_existing_real_sleeve_uid(self) -> None:
        """Backfill must not overwrite a non-None value."""
        self.target.sleeve_uid = "sleeve-jorge"
        self.observer.recognition_memory["uid-old"]["real_sleeve_uid"] = (
            "sleeve-original"
        )
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-old"]["real_sleeve_uid"],
            "sleeve-original",
        )


class TestBroadcastCellC(TestCase):
    """Observer knew new only — refresh, no link."""

    def setUp(self) -> None:
        self.room = _FakeRoom("Bar")
        self.target = _FakeTarget(location=self.room, sdesc="a tall lean man")
        self.observer = _FakeObserver(
            location=self.room,
            recognition_memory={
                "uid-new": make_recognition_entry(
                    assigned_name="Jorge",
                    location_first_seen="Plaza",
                    location_last_seen="Plaza",
                    lost_contact=True,
                )
            },
        )

    def test_lost_contact_cleared(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertFalse(
            self.observer.recognition_memory["uid-new"]["lost_contact"]
        )

    def test_last_seen_refreshed(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        entry = self.observer.recognition_memory["uid-new"]
        self.assertEqual(entry["location_last_seen"], "Bar")
        self.assertEqual(entry["sdesc_at_last_encounter"], "a tall lean man")

    def test_no_link_formed(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertIsNone(
            self.observer.recognition_memory["uid-new"]["linked_to"]
        )

    def test_old_uid_not_added(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertNotIn("uid-old", self.observer.recognition_memory)


class TestBroadcastCellD(TestCase):
    """Observer knew both — link new→old, refresh new, mark old lost."""

    def setUp(self) -> None:
        self.room = _FakeRoom("Dock")
        self.target = _FakeTarget(location=self.room, sdesc="a hooded figure")
        self.observer = _FakeObserver(
            location=self.room,
            recognition_memory={
                "uid-old": make_recognition_entry(assigned_name="Jorge"),
                "uid-new": make_recognition_entry(
                    assigned_name="The Hood",
                    lost_contact=True,
                ),
            },
        )

    def test_both_assigned_names_preserved(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-old"]["assigned_name"],
            "Jorge",
        )
        self.assertEqual(
            self.observer.recognition_memory["uid-new"]["assigned_name"],
            "The Hood",
        )

    def test_old_marked_lost_new_refreshed(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertTrue(
            self.observer.recognition_memory["uid-old"]["lost_contact"]
        )
        self.assertFalse(
            self.observer.recognition_memory["uid-new"]["lost_contact"]
        )

    def test_link_set_when_absent(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-new"]["linked_to"],
            "uid-old",
        )

    def test_existing_link_not_overwritten(self) -> None:
        self.observer.recognition_memory["uid-new"]["linked_to"] = "uid-other"
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(
            self.observer.recognition_memory["uid-new"]["linked_to"],
            "uid-other",
        )


# ---------------------------------------------------------------------------
# _send_unmasking_message — per-cell narrative prose
# ---------------------------------------------------------------------------


class TestUnmaskingMessageCellA(TestCase):
    """Cell A never reaches the hook; the matrix short-circuits upstream.

    These tests guard the broader broadcast: when neither presentation
    is in memory, no message reaches the observer at all.
    """

    def test_stranger_observer_receives_no_message(self) -> None:
        room = _FakeRoom("Plaza")
        target = _FakeTarget(location=room, sdesc="a hooded figure")
        observer = _FakeObserver(location=room)  # empty memory
        _broadcast_unmasking(target, "uid-old", "uid-new")
        self.assertEqual(observer.messages, [])


class TestUnmaskingMessageCellB(TestCase):
    """Cell B (knew old only) — recognition-gained prose."""

    def setUp(self) -> None:
        self.room = _FakeRoom("Alley")
        self.target = _FakeTarget(
            location=self.room, sdesc="a hooded figure"
        )
        self.observer = _FakeObserver(
            location=self.room,
            recognition_memory={
                "uid-old": make_recognition_entry(
                    assigned_name="Jorge",
                    sdesc_at_last_encounter="a tall lean man",
                )
            },
        )

    def test_message_uses_assigned_name_for_old_presentation(self) -> None:
        # When the observer has named the old presentation, the
        # transition message reads with that name rather than the
        # bare sdesc — the observer knew who was standing there.
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(len(self.observer.messages), 1)
        msg = self.observer.messages[0]
        self.assertIn("a hooded figure", msg)
        self.assertIn("Jorge", msg)
        self.assertIn("steps into view", msg)
        # Bare-sdesc form for the old side suppressed when name is set.
        self.assertNotIn("a tall lean man", msg)

    def test_message_falls_back_to_sdesc_when_no_assigned_name(self) -> None:
        # When the observer hasn't named the old presentation, the
        # bare sdesc is used as before.
        self.observer.recognition_memory["uid-old"]["assigned_name"] = ""
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        msg = self.observer.messages[0]
        self.assertIn("a tall lean man", msg)
        self.assertIn("a hooded figure", msg)
        self.assertNotIn("Jorge", msg)
        self.assertIn("steps into view", msg)

    def test_missing_old_sdesc_suppresses_message(self) -> None:
        # Defensive path: a malformed memory entry without the snapshot
        # should not produce broken prose.
        self.observer.recognition_memory["uid-old"][
            "sdesc_at_last_encounter"
        ] = ""
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(self.observer.messages, [])


class TestUnmaskingMessageCellC(TestCase):
    """Cell C is silent per design — observer already knew the new face."""

    def test_no_message_emitted(self) -> None:
        room = _FakeRoom("Bar")
        target = _FakeTarget(location=room, sdesc="a tall lean man")
        observer = _FakeObserver(
            location=room,
            recognition_memory={
                "uid-new": make_recognition_entry(assigned_name="Jorge")
            },
        )
        _broadcast_unmasking(target, "uid-old", "uid-new")
        # Bookkeeping must still have fired (refresh), but no prose.
        self.assertEqual(observer.messages, [])
        self.assertEqual(
            observer.recognition_memory["uid-new"]["sdesc_at_last_encounter"],
            "a tall lean man",
        )


class TestUnmaskingMessageCellD(TestCase):
    """Cell D (knew both) — verbose link-discovered prose."""

    def setUp(self) -> None:
        self.room = _FakeRoom("Dock")
        self.target = _FakeTarget(
            location=self.room, sdesc="a hooded figure"
        )
        self.observer = _FakeObserver(
            location=self.room,
            recognition_memory={
                "uid-old": make_recognition_entry(
                    assigned_name="Jorge",
                    sdesc_at_last_encounter="a tall lean man",
                ),
                "uid-new": make_recognition_entry(
                    assigned_name="The Hood",
                    sdesc_at_last_encounter="a hooded figure",
                ),
            },
        )

    def test_message_names_both_presentations(self) -> None:
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        self.assertEqual(len(self.observer.messages), 1)
        msg = self.observer.messages[0]
        self.assertIn("a tall lean man", msg)
        self.assertIn("a hooded figure", msg)
        self.assertIn("Jorge", msg)
        self.assertIn("The Hood", msg)
        self.assertIn("are the same person", msg)

    def test_message_surfaces_only_side_with_assigned_name(self) -> None:
        # Realistic playtest scenario: observer remembered the bare
        # face (named) and watched the disguise go on (creating an
        # auto-linked entry with no name).  The realize message
        # should still surface the known name rather than collapsing
        # both sides to bare sdescs.
        self.observer.recognition_memory["uid-new"]["assigned_name"] = ""
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        msg = self.observer.messages[0]
        self.assertIn("a tall lean man", msg)
        self.assertIn("a hooded figure", msg)
        self.assertIn("who you call Jorge", msg)
        # New side has no name — its phrase stays the bare sdesc.
        self.assertNotIn("who you call The Hood", msg)
        self.assertIn("are the same person", msg)

    def test_message_omits_who_you_call_when_neither_side_named(self) -> None:
        # Pathological case — both auto-linked entries with no name.
        # The message collapses to bare sdescs on both sides.
        self.observer.recognition_memory["uid-old"]["assigned_name"] = ""
        self.observer.recognition_memory["uid-new"]["assigned_name"] = ""
        _broadcast_unmasking(self.target, "uid-old", "uid-new")
        msg = self.observer.messages[0]
        self.assertIn("a tall lean man", msg)
        self.assertIn("a hooded figure", msg)
        self.assertNotIn("who you call", msg)
        self.assertIn("are the same person", msg)


class TestUnmaskingMessageObserverFiltering(TestCase):
    """The eligibility filter governs who can receive a message at all."""

    def test_unconscious_observer_receives_no_message(self) -> None:
        room = _FakeRoom("Vault")
        target = _FakeTarget(location=room, sdesc="a hooded figure")
        observer = _FakeObserver(
            location=room,
            unconscious=True,
            recognition_memory={
                "uid-old": make_recognition_entry(
                    assigned_name="Jorge",
                    sdesc_at_last_encounter="a tall lean man",
                )
            },
        )
        _broadcast_unmasking(target, "uid-old", "uid-new")
        self.assertEqual(observer.messages, [])

    def test_subject_does_not_message_themselves(self) -> None:
        # The collector excludes ``char`` from observers; ensure no
        # message reaches the subject even if they have a memory dict.
        room = _FakeRoom("Mirror")
        target = _FakeTarget(location=room, sdesc="a hooded figure")
        # Bolt a memory dict onto the target so the collector would
        # otherwise consider them — the same-as-char filter must drop.
        target.recognition_memory = {
            "uid-old": make_recognition_entry(
                assigned_name="Self",
                sdesc_at_last_encounter="a tall lean man",
            )
        }
        target.messages = []  # type: ignore[attr-defined]

        def _msg(text: str = "", **kwargs) -> None:
            del kwargs
            target.messages.append(text)  # type: ignore[attr-defined]

        target.msg = _msg  # type: ignore[attr-defined]
        _broadcast_unmasking(target, "uid-old", "uid-new")
        self.assertEqual(target.messages, [])  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# apply_signature_change context manager
# ---------------------------------------------------------------------------


class TestApplySignatureChange(TestCase):
    """Context manager dispatch correctness."""

    def test_no_broadcast_when_uid_unchanged(self) -> None:
        target = _FakeTarget(location=_FakeRoom())
        with patch(
            "world.identity.get_apparent_uid", side_effect=["uid-x", "uid-x"]
        ), patch("world.identity._broadcast_unmasking") as bc:
            with apply_signature_change(target, source="test"):
                pass
        bc.assert_called_once_with(target, "uid-x", "uid-x", source="test")

    def test_broadcast_called_with_old_and_new(self) -> None:
        target = _FakeTarget(location=_FakeRoom())
        with patch(
            "world.identity.get_apparent_uid",
            side_effect=["uid-old", "uid-new"],
        ), patch("world.identity._broadcast_unmasking") as bc:
            with apply_signature_change(target, source="wear:hood"):
                pass
        bc.assert_called_once_with(
            target, "uid-old", "uid-new", source="wear:hood"
        )

    def test_exception_suppresses_broadcast(self) -> None:
        target = _FakeTarget(location=_FakeRoom())
        with patch(
            "world.identity.get_apparent_uid",
            side_effect=["uid-old", "uid-new"],
        ), patch("world.identity._broadcast_unmasking") as bc:
            with self.assertRaises(RuntimeError):
                with apply_signature_change(target):
                    raise RuntimeError("mutation failed")
        bc.assert_not_called()


# ---------------------------------------------------------------------------
# walk_linked_chain / get_linked_aliases
# ---------------------------------------------------------------------------


class TestWalkLinkedChain(TestCase):
    """Chain traversal with cycle and max-hops defenses."""

    def test_missing_start_returns_empty(self) -> None:
        self.assertEqual(walk_linked_chain({}, "uid-missing"), [])

    def test_single_entry_returns_just_self(self) -> None:
        memory = {"uid-1": make_recognition_entry(linked_to=None)}
        self.assertEqual(walk_linked_chain(memory, "uid-1"), ["uid-1"])

    def test_multi_link_walk(self) -> None:
        memory = {
            "uid-3": make_recognition_entry(linked_to="uid-2"),
            "uid-2": make_recognition_entry(linked_to="uid-1"),
            "uid-1": make_recognition_entry(linked_to=None),
        }
        self.assertEqual(
            walk_linked_chain(memory, "uid-3"),
            ["uid-3", "uid-2", "uid-1"],
        )

    def test_cycle_terminates(self) -> None:
        memory = {
            "uid-a": make_recognition_entry(linked_to="uid-b"),
            "uid-b": make_recognition_entry(linked_to="uid-a"),
        }
        chain = walk_linked_chain(memory, "uid-a")
        self.assertEqual(chain, ["uid-a", "uid-b"])

    def test_max_hops_caps_walk(self) -> None:
        memory = {}
        for i in range(_LINKED_CHAIN_MAX_HOPS + 10):
            memory[f"uid-{i}"] = make_recognition_entry(
                linked_to=f"uid-{i + 1}"
            )
        # Last entry: dangling pointer to a uid not in memory — ensures
        # walk terminates by max_hops, not by missing-link fallthrough.
        chain = walk_linked_chain(memory, "uid-0")
        self.assertEqual(len(chain), _LINKED_CHAIN_MAX_HOPS)

    def test_dangling_link_terminates_silently(self) -> None:
        memory = {
            "uid-1": make_recognition_entry(linked_to="uid-missing"),
        }
        self.assertEqual(walk_linked_chain(memory, "uid-1"), ["uid-1"])


class TestGetLinkedAliases(TestCase):
    """Chain-derived alias names for ``Also known as`` rendering."""

    def test_no_chain_returns_empty(self) -> None:
        memory = {"uid-1": make_recognition_entry(assigned_name="Jorge")}
        self.assertEqual(get_linked_aliases(memory, "uid-1"), [])

    def test_excludes_starting_entry_name(self) -> None:
        memory = {
            "uid-2": make_recognition_entry(
                assigned_name="The Hood", linked_to="uid-1"
            ),
            "uid-1": make_recognition_entry(assigned_name="Jorge"),
        }
        # Starting from uid-2 (named "The Hood"), we should see Jorge but
        # not "The Hood" itself.
        self.assertEqual(get_linked_aliases(memory, "uid-2"), ["Jorge"])

    def test_skips_blank_assigned_names(self) -> None:
        memory = {
            "uid-3": make_recognition_entry(
                assigned_name="Outer", linked_to="uid-2"
            ),
            "uid-2": make_recognition_entry(
                assigned_name="", linked_to="uid-1"
            ),
            "uid-1": make_recognition_entry(assigned_name="Inner"),
        }
        self.assertEqual(get_linked_aliases(memory, "uid-3"), ["Inner"])


# ---------------------------------------------------------------------------
# _build_link_entry
# ---------------------------------------------------------------------------


class TestBuildLinkEntry(TestCase):
    """Auto-created link-entry shape parity with ``make_recognition_entry``."""

    def test_required_fields_present(self) -> None:
        target = _FakeTarget(sdesc="a hooded figure")
        observer = _FakeObserver()
        entry = _build_link_entry(
            target=target,
            observer=observer,
            linked_to="uid-prev",
            now_iso="2025-01-02T03:04:05",
            location_name="Alley",
        )
        for field in (
            "assigned_name",
            "first_seen",
            "last_seen",
            "times_seen",
            "location_first_seen",
            "location_last_seen",
            "sdesc_at_first_encounter",
            "sdesc_at_last_encounter",
            "lost_contact",
            "linked_to",
        ):
            self.assertIn(field, entry, f"missing field: {field}")

    def test_assigned_name_starts_blank(self) -> None:
        target = _FakeTarget(sdesc="a hooded figure")
        observer = _FakeObserver()
        entry = _build_link_entry(
            target=target,
            observer=observer,
            linked_to=None,
            now_iso="2025-01-02T03:04:05",
            location_name="Alley",
        )
        self.assertEqual(entry["assigned_name"], "")

    def test_linked_to_passed_through(self) -> None:
        target = _FakeTarget(sdesc="a hooded figure")
        observer = _FakeObserver()
        entry = _build_link_entry(
            target=target,
            observer=observer,
            linked_to="uid-prev",
            now_iso="2025-01-02T03:04:05",
            location_name="Alley",
        )
        self.assertEqual(entry["linked_to"], "uid-prev")


# ---------------------------------------------------------------------------
# Wiring tests — confirm apply_signature_change is invoked at each site
# ---------------------------------------------------------------------------


class _WiringMixinHost:
    """Minimal host for :class:`ClothingMixin` exercising wear/remove only.

    The mixin reads ``self.worn_items`` (dict mapping location → list of
    items) and ``self.hands`` (dict mapping hand → held item).  We don't
    need an Evennia Character — just the duck-typed surface.
    """

    def __init__(self) -> None:
        self.worn_items: dict = {}
        self.hands: dict = {}
        self.location = None  # broadcast no-ops when no location


class _WiringFakeItem:
    """Wearable item stand-in for clothing-mixin wiring tests."""

    def __init__(
        self,
        *,
        disguise_essential: bool,
        layer: int = 2,
        coverage: tuple[str, ...] = ("torso",),
        key: str = "fake-garment",
    ) -> None:
        self.disguise_essential = disguise_essential
        self.layer = layer
        self._coverage = coverage
        self.key = key
        self.location = None

    def is_wearable(self) -> bool:
        return True

    def get_current_coverage(self) -> tuple[str, ...]:
        return self._coverage

    def move_to(self, *_args, **_kwargs) -> None:
        return None


class TestClothingMixinWiring(TestCase):
    """``wear_item`` / ``remove_item`` invoke broadcast only for essentials."""

    def _build_host_with_item(self, item: _WiringFakeItem):
        from typeclasses.clothing_mixin import ClothingMixin

        class _Host(_WiringMixinHost, ClothingMixin):
            pass

        host = _Host()
        item.location = host  # treat as in inventory
        return host

    def test_wear_essential_invokes_broadcast(self) -> None:
        item = _WiringFakeItem(disguise_essential=True, key="balaclava")
        host = self._build_host_with_item(item)
        with patch(
            "world.identity.get_apparent_uid",
            side_effect=["uid-bare", "uid-masked"],
        ), patch("world.identity._broadcast_unmasking") as bc:
            ok, _msg = host.wear_item(item)
        self.assertTrue(ok)
        bc.assert_called_once()

    def test_wear_non_essential_skips_broadcast(self) -> None:
        item = _WiringFakeItem(disguise_essential=False, key="shirt")
        host = self._build_host_with_item(item)
        with patch("world.identity._broadcast_unmasking") as bc:
            ok, _msg = host.wear_item(item)
        self.assertTrue(ok)
        bc.assert_not_called()

    def test_remove_essential_invokes_broadcast(self) -> None:
        item = _WiringFakeItem(disguise_essential=True, key="balaclava")
        host = self._build_host_with_item(item)
        host.wear_item(item)  # establish worn state without patches
        with patch(
            "world.identity.get_apparent_uid",
            side_effect=["uid-masked", "uid-bare"],
        ), patch("world.identity._broadcast_unmasking") as bc:
            ok, _msg = host.remove_item(item)
        self.assertTrue(ok)
        bc.assert_called_once()

    def test_remove_non_essential_skips_broadcast(self) -> None:
        item = _WiringFakeItem(disguise_essential=False, key="shirt")
        host = self._build_host_with_item(item)
        host.wear_item(item)
        with patch("world.identity._broadcast_unmasking") as bc:
            ok, _msg = host.remove_item(item)
        self.assertTrue(ok)
        bc.assert_not_called()


class TestOverrideHelperWiring(TestCase):
    """``_clear_all_overrides`` runs the mutation inside the context manager."""

    def test_clear_all_overrides_uses_context_manager(self) -> None:
        from commands.CmdCharacter import _clear_all_overrides

        class _DB:
            height_override = "tall"
            build_override = "lean"
            keyword_override = "hood"
            active_persona = "Bandit"

        class _Caller:
            db = _DB()
            location = None

        caller = _Caller()
        with patch(
            "world.identity.get_apparent_uid",
            side_effect=["uid-disguised", "uid-real"],
        ), patch("world.identity._broadcast_unmasking") as bc:
            _clear_all_overrides(caller)

        # All four axes wiped.
        self.assertIsNone(caller.db.height_override)
        self.assertIsNone(caller.db.build_override)
        self.assertIsNone(caller.db.keyword_override)
        self.assertIsNone(caller.db.active_persona)
        bc.assert_called_once()


# ---------------------------------------------------------------------------
# _broadcast_unmask_with_action — combined "action + reveal" path
# ---------------------------------------------------------------------------


class TestBroadcastUnmaskWithAction(TestCase):
    """The combined-message path emits one line per observer:
    action emote + reveal suffix keyed on the observer's memory."""

    def _build_scene(
        self, *,
        observer_memory: dict | None = None,
        target_sdesc: str = "a wiry masked ninja in a white cotton t-shirt",
    ):
        room = _FakeRoom("Tolliver Row")
        target = _FakeTarget(location=room, sdesc=target_sdesc)
        observer = _FakeObserver(
            location=room, recognition_memory=observer_memory or {},
        )
        return room, target, observer

    def _call(self, target, observer, *, old_uid, new_uid):
        # The action_template uses a snapshot for the actor — observers
        # see the pre-mutation sdesc rendered through the snapshot.
        pre_resolved = {
            "actor": {observer: "a wiry masked ninja in a white cotton t-shirt"},
        }
        _broadcast_unmask_with_action(
            target, old_uid, new_uid,
            action_template="{actor} removes a black balaclava.",
            action_char_refs={"actor": target},
            action_pre_resolved_refs=pre_resolved,
            action_exclude=[],
        )

    def test_cell_d_named_new_uid_combines_action_and_reveal(self) -> None:
        memory = {
            "uid-masked": make_recognition_entry(
                assigned_name="",
                sdesc_at_last_encounter=(
                    "a wiry masked ninja in a white cotton t-shirt"
                ),
            ),
            "uid-bare": make_recognition_entry(
                assigned_name="Drek Drivel",
                sdesc_at_last_encounter="a wiry ninja wielding a chainsaw",
            ),
        }
        _, target, observer = self._build_scene(observer_memory=memory)
        self._call(target, observer, old_uid="uid-masked", new_uid="uid-bare")
        self.assertEqual(len(observer.messages), 1)
        msg = observer.messages[0]
        self.assertIn("removes a black balaclava", msg)
        self.assertIn(
            "revealing they are none other than Drek Drivel", msg,
        )
        self.assertTrue(msg.endswith("."), msg)

    def test_cell_c_named_new_uid_combines_action_and_reveal(self) -> None:
        # Cell C: observer only knew the bare presentation.  Same
        # reveal as cell D from the observer's POV.
        memory = {
            "uid-bare": make_recognition_entry(
                assigned_name="Drek Drivel",
                sdesc_at_last_encounter="a wiry ninja wielding a chainsaw",
            ),
        }
        _, target, observer = self._build_scene(observer_memory=memory)
        self._call(target, observer, old_uid="uid-masked", new_uid="uid-bare")
        msg = observer.messages[0]
        self.assertIn("revealing they are none other than Drek Drivel", msg)

    def test_cell_a_stranger_gets_action_only(self) -> None:
        # No memory for either UID.
        _, target, observer = self._build_scene(observer_memory={})
        self._call(target, observer, old_uid="uid-masked", new_uid="uid-bare")
        msg = observer.messages[0]
        self.assertIn("removes a black balaclava", msg)
        self.assertNotIn("revealing", msg)

    def test_cell_d_no_assigned_name_omits_reveal_suffix(self) -> None:
        # Observer auto-linked both presentations but named neither —
        # combined path drops the linkage prose (per the "one message"
        # contract); the action emote stands alone.
        memory = {
            "uid-masked": make_recognition_entry(
                assigned_name="",
                sdesc_at_last_encounter="a wiry masked ninja",
            ),
            "uid-bare": make_recognition_entry(
                assigned_name="",
                sdesc_at_last_encounter="a wiry ninja",
            ),
        }
        _, target, observer = self._build_scene(observer_memory=memory)
        self._call(target, observer, old_uid="uid-masked", new_uid="uid-bare")
        msg = observer.messages[0]
        self.assertIn("removes a black balaclava", msg)
        self.assertNotIn("revealing", msg)

    def test_actor_excluded(self) -> None:
        _, target, observer = self._build_scene(observer_memory={})
        # Add target as an "observer" via action_exclude.
        _broadcast_unmask_with_action(
            target, "uid-old", "uid-new",
            action_template="{actor} removes balaclava.",
            action_char_refs={"actor": target},
            action_pre_resolved_refs={},
            action_exclude=[observer],
        )
        self.assertEqual(observer.messages, [])

    def test_no_op_when_uids_unchanged(self) -> None:
        _, target, observer = self._build_scene(observer_memory={})
        _broadcast_unmask_with_action(
            target, "uid-x", "uid-x",
            action_template="{actor} removes balaclava.",
            action_char_refs={"actor": target},
            action_pre_resolved_refs={},
            action_exclude=[],
        )
        self.assertEqual(observer.messages, [])
