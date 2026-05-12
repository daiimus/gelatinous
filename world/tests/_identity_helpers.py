"""
Shared identity-test helpers.

Centralises the derivation of recognition_memory dict keys and the
shape of recognition_memory entries so the 7 identity-adjacent test
modules (``test_identity_commands``, ``test_emote``, ``test_emote_templates``,
``test_identity_search``, ``test_communication``, ``test_character_identity``,
``test_identity``) stay aligned with the production engine in
``world/identity.py``.

Two reasons to import from here instead of seeding literal UIDs:

1. **Schema stability.**  When the identity signature gains new inputs
   (e.g. PR-C wires equipped essential disguise items), every test
   re-derives its expected key automatically.

2. **Mock hygiene.**  ``MagicMock(spec=Character)`` auto-creates truthy
   stand-ins for ``char.db.height_override`` etc., which silently
   poisons the signature.  :func:`prepare_mock_for_apparent_uid` clears
   those axes to ``None`` so the derived UID is a deterministic function
   of ``sleeve_uid`` alone (until PR-C adds essential items).
"""

from __future__ import annotations

from typing import Any

from world.identity import get_apparent_uid


def prepare_mock_for_apparent_uid(char: Any) -> None:
    """Zero out ``db.*_override`` axes on a mock character.

    ``MagicMock`` returns a fresh ``MagicMock`` for any attribute
    access, including ``char.db.height_override``.  Those non-``None``
    sentinels feed directly into :func:`world.identity.get_identity_signature`
    and produce wildly different Apparent UIDs than the production
    engine would compute for an undisguised character.

    Call this once per test character that participates in recognition
    lookups; safe to call multiple times.
    """
    char.db.height_override = None
    char.db.build_override = None
    char.db.keyword_override = None


def apparent_uid_for(char: Any) -> str:
    """Return the Apparent UID for *char*, asserting it is non-``None``.

    Wraps :func:`world.identity.get_apparent_uid` so test fixtures fail
    loudly (rather than silently storing a ``None`` key) when a mock
    character is missing its ``sleeve_uid``.
    """
    prepare_mock_for_apparent_uid(char)
    uid = get_apparent_uid(char)
    if uid is None:
        raise AssertionError(
            f"apparent_uid_for({char!r}) returned None; mock is missing "
            f"sleeve_uid."
        )
    return uid


def make_recognition_entry(
    *,
    assigned_name: str = "",
    sdesc_at_first_encounter: str = "a tall lean man",
    sdesc_at_last_encounter: str | None = None,
    location_first_seen: str = "Test Room",
    location_last_seen: str | None = None,
    first_seen: str = "2025-01-01T00:00:00",
    last_seen: str | None = None,
    times_seen: int = 1,
    lost_contact: bool = False,
) -> dict:
    """Build a recognition_memory entry dict matching the production schema.

    Defaults mirror what :meth:`commands.CmdCharacter.CmdRemember._remember_target`
    writes for a fresh first-meet, including the ``lost_contact`` field
    introduced by the disguise engine PR.  Tests that need a particular
    field shape pass the relevant kwargs; everything else takes a
    sensible default.
    """
    return {
        "assigned_name": assigned_name,
        "sdesc_at_first_encounter": sdesc_at_first_encounter,
        "sdesc_at_last_encounter": (
            sdesc_at_last_encounter
            if sdesc_at_last_encounter is not None
            else sdesc_at_first_encounter
        ),
        "location_first_seen": location_first_seen,
        "location_last_seen": (
            location_last_seen
            if location_last_seen is not None
            else location_first_seen
        ),
        "first_seen": first_seen,
        "last_seen": last_seen if last_seen is not None else first_seen,
        "times_seen": times_seen,
        "lost_contact": lost_contact,
    }
