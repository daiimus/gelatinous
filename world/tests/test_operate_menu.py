"""EvMenu node tests for the operate menu.

Each node function in ``commands.CmdOperate`` follows the EvMenu
contract: ``(caller, raw_string, **kwargs) -> (text, options)``.  The
nodes are pure functions over the caller's ``ndb`` scratch state and
the target's medical / chart state — easy to test in isolation with
plain-Python stubs, no Evennia session machinery required.

Coverage here focuses on:

* **The suture location picker** — the node with the most bug history
  (PRs #424, #425, #426, #427).  Each historical bug becomes a
  regression test so future picker work has a safety net.
* **Routing dispatchers** (``_process_top_choice``,
  ``_process_verb_choice``) — small but load-bearing.  Cheap to test
  and they're the input edge of the entire menu.

This file is the seed for menu-node coverage in general; as
inconsistencies surface during design / style standardisation, drop
the regression test here.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase


# ---------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------


def _make_organ(container, *, wound_stage=None, current_hp=10, max_hp=10):
    return SimpleNamespace(
        container=container,
        wound_stage=wound_stage,
        current_hp=current_hp,
        max_hp=max_hp,
    )


def _make_target(*, species="human", organs=None, surgical_state=None,
                  medical_chart=None, sutured_stumps=None,
                  location_covered=False):
    """Build a stub target supporting every read the suture picker does.

    ``organs`` is a ``{name: _make_organ(...)}`` map.
    ``surgical_state`` is the live ``{"incisions": ..., "active_procedure": ...}``
    dict or ``None`` (lazy-init by the procedure helpers).
    ``medical_chart`` is the chart dict (with ``steps``) or ``None``.
    ``sutured_stumps`` is the dict / legacy list / ``None``.
    """
    target = SimpleNamespace()
    target.medical_state = SimpleNamespace(organs=organs or {})
    target.db = SimpleNamespace(
        species=species,
        surgical_state=surgical_state,
        medical_chart=medical_chart,
        sutured_stumps=sutured_stumps,
    )
    target.is_location_covered = lambda loc: location_covered
    return target


def _make_caller(target=None):
    """Build a caller stub.  ``msg`` calls accumulate on ``msg_log``."""
    caller = SimpleNamespace()
    caller.ndb = SimpleNamespace()
    if target is not None:
        caller.ndb._operate_target = target
    caller.msg_log = []
    caller.msg = lambda *a, **k: caller.msg_log.append(a[0] if a else None)
    return caller


# ---------------------------------------------------------------------
# Suture location picker
# ---------------------------------------------------------------------


class SutureLocationPicker(TestCase):
    """``_node_suture_location`` — the node with the most bug history.

    Each test below maps to a real regression we hit on the playtest
    server during the surgery work.  Together they pin the picker's
    three input sources (open incisions, planned chart steps,
    medical-state stumps) and the cluster + chain collapse rules.
    """

    def _picker_values(self, caller):
        # The ``"all"`` row is index 0; real picker options start at 1.
        return [val for _label, val in caller.ndb._operate_pickable[1:]]

    def _picker_labels(self, caller):
        return [label for label, _val in caller.ndb._operate_pickable[1:]]

    # -- Source: empty state -----------------------------------------

    def test_empty_state_shows_empty_branch(self):
        from commands.CmdOperate import _node_suture_location
        target = _make_target()
        caller = _make_caller(target)
        text, _opts = _node_suture_location(caller, "")
        self.assertIn("No incisions currently open", text)

    # -- Source: open incisions --------------------------------------

    def test_open_incision_listed(self):
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            surgical_state={
                "incisions": {"chest": {"opened_at": 1.0}},
                "active_procedure": None,
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["chest"])
        self.assertIn("(open)", self._picker_labels(caller)[0])

    # -- Source: planned chart steps ---------------------------------

    def test_pending_amputate_step_listed_as_planned(self):
        # PR #424 regression: chart-author flow needs to see the
        # cut point a pending amputate step will leave open, even
        # before the step runs.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            medical_chart={
                "steps": [{
                    "verb": "amputate",
                    "args": {"location": "head"},
                    "status": "pending",
                }],
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["head"])
        self.assertIn("(planned)", self._picker_labels(caller)[0])

    def test_done_amputate_step_does_not_appear_as_planned(self):
        # PR #424 follow-up: a DONE amputate step's location is
        # already an open incision (the runtime opened it) — so we
        # don't double-list it as "planned" too.  The open_incisions
        # source covers it.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            medical_chart={
                "steps": [{
                    "verb": "amputate",
                    "args": {"location": "head"},
                    "status": "done",
                }],
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        # No state → no picker, empty branch.
        self.assertIn("No incisions currently open",
                      _node_suture_location(caller, "")[0])

    # -- Source: severed-organ stumps --------------------------------

    def test_severed_stump_listed(self):
        # PR #424: combat-driven amputation leaves the body with
        # severed organs but no incision (pre-#428) or chart step.
        # The picker must consult the medical state as a third
        # source.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            organs={
                "left_humerus": _make_organ("left_arm",
                                              wound_stage="severed",
                                              current_hp=0),
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["left_arm"])
        self.assertIn("(stump)", self._picker_labels(caller)[0])

    # -- Source combination ------------------------------------------

    def test_combined_sources_combine_tags(self):
        # PR #428: post-fix the chart amputate also marks the cut
        # point as a severed organ, so the picker should reflect
        # BOTH signals — ``(open + stump)``, not separate entries.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            surgical_state={
                "incisions": {"head": {"opened_at": 1.0}},
                "active_procedure": None,
            },
            organs={
                "brain": _make_organ("head", wound_stage="severed",
                                       current_hp=0),
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["head"])
        label = self._picker_labels(caller)[0]
        self.assertIn("(open + stump)", label)

    # -- Cluster collapse: head ---------------------------------------

    def test_head_cluster_collapses_to_head_only(self):
        # PR #426 regression: decapitation marks the brain (head)
        # AND the cervical spine (neck) severed.  The picker MUST
        # show one entry — "head" — and NOT a separate "neck (stump)"
        # option.  Mirrors the wound renderer's cluster collapse
        # so the surgeon doesn't see two "what to suture" options
        # for what's anatomically one cut.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            organs={
                "brain": _make_organ("head", wound_stage="severed",
                                       current_hp=0),
                "cervical_spine": _make_organ("neck",
                                                wound_stage="severed",
                                                current_hp=0),
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["head"])

    # -- Cluster collapse: limb chain --------------------------------

    def test_limb_chain_collapses_to_root(self):
        # Same idea as the head cluster: thigh amputation chains
        # through shin + foot, picker shows the chain root only.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            organs={
                "left_femur": _make_organ("left_thigh",
                                            wound_stage="severed",
                                            current_hp=0),
                "left_tibia": _make_organ("left_shin",
                                            wound_stage="severed",
                                            current_hp=0),
                "left_metatarsals": _make_organ("left_foot",
                                                  wound_stage="severed",
                                                  current_hp=0),
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        self.assertEqual(self._picker_values(caller), ["left_thigh"])

    # -- Suture state filtering --------------------------------------

    def test_already_sutured_stump_excluded(self):
        # PR #423: a stump that's already been sutured shouldn't
        # re-appear in the picker.  Otherwise repeated suture verbs
        # could double-record outcomes.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            organs={
                "left_humerus": _make_organ("left_arm",
                                              wound_stage="severed",
                                              current_hp=0),
            },
            sutured_stumps={"left_arm": "success"},
        )
        caller = _make_caller(target)
        text, _opts = _node_suture_location(caller, "")
        self.assertIn("No incisions currently open", text)

    def test_legacy_list_shape_sutured_stumps_filtered(self):
        # PR #426 / #427: backward compat for the pre-outcome
        # list-shape storage of sutured_stumps.  Reads the same.
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            organs={
                "left_humerus": _make_organ("left_arm",
                                              wound_stage="severed",
                                              current_hp=0),
            },
            sutured_stumps=["left_arm"],  # legacy list
        )
        caller = _make_caller(target)
        text, _opts = _node_suture_location(caller, "")
        self.assertIn("No incisions currently open", text)

    # -- Always-present "all" --------------------------------------

    def test_all_option_present_when_locations_exist(self):
        from commands.CmdOperate import _node_suture_location
        target = _make_target(
            surgical_state={
                "incisions": {"chest": {"opened_at": 1.0}},
                "active_procedure": None,
            },
        )
        caller = _make_caller(target)
        _node_suture_location(caller, "")
        # First entry is "all" with value "all open incisions" — the
        # sentinel ``_process_suture_location`` checks against to
        # build a no-location step.
        first_label, first_val = caller.ndb._operate_pickable[0]
        self.assertEqual(first_val, "all open incisions")
        self.assertIn("all", first_label)


# ---------------------------------------------------------------------
# Top-level navigation routing
# ---------------------------------------------------------------------


class TopChoiceRouting(TestCase):
    """``_process_top_choice`` — numeric + ``x`` dispatcher off the
    main operate panel.  Tiny but load-bearing: any drift here breaks
    every menu workflow."""

    def _process(self, raw_string):
        from commands.CmdOperate import _process_top_choice
        caller = _make_caller()
        return _process_top_choice(caller, raw_string), caller

    def test_choice_1_routes_to_add_verb(self):
        result, _ = self._process("1")
        self.assertEqual(result, "node_add_verb")

    def test_choice_2_routes_to_edit_chart(self):
        result, _ = self._process("2")
        self.assertEqual(result, "node_edit_chart")

    def test_choice_3_routes_to_commence(self):
        result, _ = self._process("3")
        self.assertEqual(result, "node_commence")

    def test_choice_4_routes_to_save_exit(self):
        result, _ = self._process("4")
        self.assertEqual(result, "node_save_exit")

    def test_choice_5_routes_to_discard_confirm(self):
        result, _ = self._process("5")
        self.assertEqual(result, "node_discard_confirm")

    def test_x_routes_to_exit(self):
        result, _ = self._process("x")
        self.assertEqual(result, "node_exit")

    def test_exit_keyword_routes_to_exit(self):
        result, _ = self._process("exit")
        self.assertEqual(result, "node_exit")

    def test_empty_input_re_renders_top(self):
        # ``None`` return is EvMenu's "stay here, redisplay" signal.
        result, _ = self._process("")
        self.assertIsNone(result)

    def test_invalid_choice_messages_and_redisplays(self):
        result, caller = self._process("9")
        self.assertIsNone(result)
        self.assertEqual(len(caller.msg_log), 1)
        self.assertIn("Invalid option", caller.msg_log[0])


# ---------------------------------------------------------------------
# Verb selection routing
# ---------------------------------------------------------------------


class VerbChoiceRouting(TestCase):
    """``_process_verb_choice`` — picks a procedure verb and routes
    to its location/organ picker.  Accepts numeric + keyword.
    """

    def _process(self, raw_string):
        from commands.CmdOperate import _process_verb_choice
        caller = _make_caller()
        return _process_verb_choice(caller, raw_string), caller

    def test_choice_1_routes_to_incise_location(self):
        result, _ = self._process("1")
        self.assertEqual(result, "node_incise_location")

    def test_choice_2_routes_to_harvest_organ(self):
        result, _ = self._process("2")
        self.assertEqual(result, "node_harvest_organ")

    def test_choice_3_routes_to_install_organ(self):
        result, _ = self._process("3")
        self.assertEqual(result, "node_install_organ")

    def test_choice_4_routes_to_suture_location(self):
        result, _ = self._process("4")
        self.assertEqual(result, "node_suture_location")

    def test_choice_5_routes_to_amputate_location(self):
        result, _ = self._process("5")
        self.assertEqual(result, "node_amputate_location")

    def test_x_returns_to_top(self):
        result, _ = self._process("x")
        self.assertEqual(result, "node_top")

    def test_cancel_keyword_returns_to_top(self):
        result, _ = self._process("cancel")
        self.assertEqual(result, "node_top")

    def test_verb_keyword_synonyms(self):
        # Each verb name as a typed keyword routes the same as its
        # number.  Lets surgeons type "suture" instead of "4".
        for keyword, node in (
            ("incise", "node_incise_location"),
            ("harvest", "node_harvest_organ"),
            ("install", "node_install_organ"),
            ("suture", "node_suture_location"),
            ("amputate", "node_amputate_location"),
        ):
            with self.subTest(keyword=keyword):
                result, _ = self._process(keyword)
                self.assertEqual(result, node)

    def test_invalid_choice_messages_and_redisplays(self):
        result, caller = self._process("9")
        self.assertIsNone(result)
        self.assertEqual(len(caller.msg_log), 1)
        self.assertIn("Pick 1-5", caller.msg_log[0])

    def test_verb_choice_persists_pending_verb(self):
        # Side effect: the picker uses ``caller.ndb._operate_pending_verb``
        # to remember which verb's location picker we're inside.
        result, caller = self._process("4")
        self.assertEqual(result, "node_suture_location")
        self.assertEqual(caller.ndb._operate_pending_verb, "suture")


# ---------------------------------------------------------------------
# Install location helper
# ---------------------------------------------------------------------


def _make_donor(*, organ_name=None, source_species=None,
                 compatible_species=None,
                 target_container=None, target_display_locations=None,
                 key="harvested heart"):
    """Build a donor-item stub for the install picker."""
    donor = SimpleNamespace(key=key)
    donor.db = SimpleNamespace(
        organ_name=organ_name,
        source_species=source_species,
        compatible_species=compatible_species,
        target_container=target_container,
        target_display_locations=target_display_locations,
    )
    return donor


class ListInstallLocations(TestCase):
    """``_list_install_locations`` — the helper that turns
    ``"every body region"`` (broken old picker) into the slot(s)
    where the specific donor can actually go.  Two paths converge:
    biological (lookup by organ_name in species spec) and cyberware
    (item-declared overrides).  Cross-species refusal sits in front
    of both."""

    # -- Biological path ---------------------------------------------

    def test_biological_heart_occupied_when_slot_intact(self):
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest", current_hp=15),
        })
        donor = _make_donor(organ_name="heart", source_species="human",
                             compatible_species=["human"])
        self.assertEqual(
            _list_install_locations(target, donor),
            [("chest", "occupied")],
        )

    def test_biological_heart_empty_when_slot_harvested(self):
        # Heart's been harvested (current_hp=0) → slot is empty,
        # ready for a fresh donor.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest", current_hp=0),
        })
        donor = _make_donor(organ_name="heart", source_species="human",
                             compatible_species=["human"])
        self.assertEqual(
            _list_install_locations(target, donor),
            [("chest", "empty")],
        )

    def test_biological_eye_picks_display_location(self):
        # Eyes have container="head" but display_location="left_eye"
        # — the display surface is the install target, not the bulk
        # container.  Same rule the wound renderer follows.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "left_eye": _make_organ("head", current_hp=0),
        })
        target.medical_state.organs["left_eye"].display_location = "left_eye"
        donor = _make_donor(organ_name="left_eye", source_species="human",
                             compatible_species=["human"])
        result = _list_install_locations(target, donor)
        self.assertEqual([loc for loc, _tag in result], ["left_eye"])

    # -- Cross-species gate ------------------------------------------

    def test_cross_species_donor_refused(self):
        # Rat heart in a human → empty list (picker shows refusal).
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest"),
        })
        donor = _make_donor(organ_name="heart", source_species="rat",
                             compatible_species=["rat"])
        self.assertEqual(_list_install_locations(target, donor), [])

    def test_legacy_donor_falls_back_to_source_species(self):
        # Items harvested before ``compatible_species`` was added
        # carry only ``source_species``.  The helper synthesises the
        # list so cross-species refusal still works for legacy data.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest", current_hp=0),
        })
        donor = _make_donor(organ_name="heart", source_species="rat",
                             compatible_species=None)  # legacy
        self.assertEqual(_list_install_locations(target, donor), [])

    def test_legacy_donor_same_species_passes(self):
        # Same fallback — but when source species matches target,
        # the install proceeds.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest", current_hp=0),
        })
        donor = _make_donor(organ_name="heart", source_species="human",
                             compatible_species=None)  # legacy
        self.assertEqual(
            _list_install_locations(target, donor),
            [("chest", "empty")],
        )

    # -- Cyberware path ----------------------------------------------

    def test_cyberware_with_target_display_locations(self):
        # Cybernetic eye declares both eye sockets as valid targets.
        # Picker should offer both — surgeon chooses which side.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={})
        donor = _make_donor(
            key="cybernetic eye v2",
            organ_name=None,  # cyberware needn't match species spec
            compatible_species=["human", "rat", "lizard"],
            target_display_locations=["left_eye", "right_eye"],
        )
        result = _list_install_locations(target, donor)
        self.assertEqual(
            sorted([loc for loc, _tag in result]),
            ["left_eye", "right_eye"],
        )

    def test_cyberware_compatible_with_multiple_species(self):
        # Same cybernetic eye lands on a rat just fine.
        from commands.CmdOperate import _list_install_locations
        target_rat = _make_target(species="rat", organs={})
        donor = _make_donor(
            key="cybernetic eye v2",
            organ_name=None,
            compatible_species=["human", "rat"],
            target_display_locations=["left_eye", "right_eye"],
        )
        result = _list_install_locations(target_rat, donor)
        self.assertEqual(len(result), 2)

    def test_cyberware_refused_for_uncompatible_species(self):
        from commands.CmdOperate import _list_install_locations
        target_lizard = _make_target(species="lizard", organs={})
        donor = _make_donor(
            key="cybernetic eye v2",
            organ_name=None,
            compatible_species=["human", "rat"],
            target_display_locations=["left_eye", "right_eye"],
        )
        self.assertEqual(_list_install_locations(target_lizard, donor), [])

    def test_cyberware_with_target_container_only(self):
        # Simpler cyberware — bulk slot replacement.  Just container,
        # no per-side display_location list.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={
            "heart": _make_organ("chest", current_hp=0),
        })
        donor = _make_donor(
            key="artificial heart",
            organ_name=None,
            compatible_species=["human"],
            target_container="chest",
        )
        result = _list_install_locations(target, donor)
        self.assertEqual([loc for loc, _tag in result], ["chest"])

    # -- No-go cases --------------------------------------------------

    def test_unknown_organ_name_returns_empty(self):
        # Donor's organ_name doesn't exist in the target species'
        # spec — no install target, picker refuses cleanly.
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={})
        donor = _make_donor(
            organ_name="quantum_synapse",  # made up
            source_species="human",
            compatible_species=["human"],
        )
        self.assertEqual(_list_install_locations(target, donor), [])

    def test_donor_with_no_organ_name_or_overrides_returns_empty(self):
        from commands.CmdOperate import _list_install_locations
        target = _make_target(species="human", organs={})
        donor = _make_donor(
            organ_name=None,
            compatible_species=["human"],
        )
        self.assertEqual(_list_install_locations(target, donor), [])
