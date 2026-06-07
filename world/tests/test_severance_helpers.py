"""Unit tests for ``world.medical.severance``.

This module owns the single sources of truth for sutured-stump shape
(``normalize_sutured_stumps``) and cut-point computation
(``compute_cut_points`` / ``compute_severed_containers``).  The wound
renderer, the operate picker, and the runtime suture verb all read
through these helpers, so the round-trip cases need pinning here
rather than scattered across the consumer tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase


class _FakeOrgan:
    def __init__(self, container, *, wound_stage=None, current_hp=10,
                 max_hp=10):
        self.container = container
        self.wound_stage = wound_stage
        self.current_hp = current_hp
        self.max_hp = max_hp


class _FakeMedical:
    def __init__(self, organs):
        self.organs = organs


def _target(organs, *, species="human", sutured_stumps=None):
    target = SimpleNamespace()
    target.medical_state = _FakeMedical(organs)
    target.db = SimpleNamespace(
        species=species, sutured_stumps=sutured_stumps,
    )
    return target


# ---------------------------------------------------------------------
# normalize_sutured_stumps
# ---------------------------------------------------------------------


class NormalizeSuturedStumps(TestCase):

    def test_none_returns_empty_dict(self):
        from world.medical.severance import normalize_sutured_stumps
        target = _target({})
        self.assertEqual(normalize_sutured_stumps(target), {})

    def test_dict_shape_returned_as_fresh_copy(self):
        # The returned dict should be a copy — callers mutate without
        # touching the stored Attribute.
        from world.medical.severance import normalize_sutured_stumps
        original = {"head": "success"}
        target = _target({}, sutured_stumps=original)
        out = normalize_sutured_stumps(target)
        self.assertEqual(out, original)
        out["head"] = "failure"
        self.assertEqual(original["head"], "success")

    def test_legacy_list_shape_maps_to_success_outcomes(self):
        # Pre-outcome storage was a flat list — each entry imports as
        # ``"success"`` so the renderer picks the clean variant set,
        # matching what the older code path produced.
        from world.medical.severance import normalize_sutured_stumps
        target = _target({}, sutured_stumps=["head", "left_arm"])
        self.assertEqual(
            normalize_sutured_stumps(target),
            {"head": "success", "left_arm": "success"},
        )

    def test_missing_db_handled(self):
        from world.medical.severance import normalize_sutured_stumps
        target = SimpleNamespace()  # no .db at all
        self.assertEqual(normalize_sutured_stumps(target), {})


# ---------------------------------------------------------------------
# compute_severed_containers
# ---------------------------------------------------------------------


class ComputeSeveredContainers(TestCase):

    def test_includes_only_severed_zero_hp_organs(self):
        from world.medical.severance import compute_severed_containers
        target = _target({
            "brain": _FakeOrgan("head", wound_stage="severed", current_hp=0),
            "heart": _FakeOrgan("chest"),  # intact
            "left_eye": _FakeOrgan("head", wound_stage="severed",
                                    current_hp=0),
        })
        self.assertEqual(
            compute_severed_containers(target), {"head"},
        )

    def test_severed_stage_with_positive_hp_excluded(self):
        # Defensive guard: only count organs that are *actually* zeroed.
        from world.medical.severance import compute_severed_containers
        target = _target({
            "brain": _FakeOrgan("head", wound_stage="severed", current_hp=3),
        })
        self.assertEqual(compute_severed_containers(target), set())

    def test_no_medical_state_returns_empty(self):
        from world.medical.severance import compute_severed_containers
        target = SimpleNamespace(
            medical_state=None,
            db=SimpleNamespace(species="human"),
        )
        self.assertEqual(compute_severed_containers(target), set())

    def test_corpse_shaped_target_reads_wounds_at_death(self):
        # Corpses have empty live ``medical_state.organs`` post-death.
        # The helper falls back to ``wounds_at_death`` and treats any
        # ``injury_type="severed"`` entry as a stump container.  Lets
        # the suture verb detect post-death stumps so corpse stumps
        # can progress to ``treated_<outcome>`` prose.
        from world.medical.severance import compute_severed_containers
        target = SimpleNamespace()
        target.medical_state = SimpleNamespace(organs={})  # empty
        target.db = SimpleNamespace(
            species="human",
            wounds_at_death=[
                {"injury_type": "severed", "location": "head",
                 "stage": "fresh"},
                {"injury_type": "bullet", "location": "chest",
                 "stage": "old"},  # not a stump
                {"injury_type": "severed", "location": "left_arm",
                 "stage": "old"},
            ],
        )
        self.assertEqual(
            compute_severed_containers(target),
            {"head", "left_arm"},
        )

    def test_living_path_wins_when_organs_populated(self):
        # When both surfaces have data (test setup or transitional
        # state), the live ``medical_state.organs`` path takes
        # precedence — that's the source of truth for living targets.
        from world.medical.severance import compute_severed_containers
        target = SimpleNamespace()
        target.medical_state = SimpleNamespace(organs={
            "brain": _FakeOrgan("head", wound_stage="severed",
                                  current_hp=0),
        })
        target.db = SimpleNamespace(
            species="human",
            wounds_at_death=[
                {"injury_type": "severed", "location": "left_arm",
                 "stage": "old"},
            ],
        )
        # Live path wins — only "head" returned.
        self.assertEqual(
            compute_severed_containers(target), {"head"},
        )


# ---------------------------------------------------------------------
# compute_cut_points
# ---------------------------------------------------------------------


class ComputeCutPoints(TestCase):

    def test_head_cluster_collapses_to_head(self):
        # Decapitation: brain (container=head) + cervical_spine
        # (container=neck) both severed.  Cut points should be just
        # ``{"head"}`` — the neck collapses into the head cluster.
        from world.medical.severance import compute_cut_points
        target = _target({
            "brain": _FakeOrgan("head", wound_stage="severed", current_hp=0),
            "cervical_spine": _FakeOrgan("neck", wound_stage="severed",
                                          current_hp=0),
        })
        self.assertEqual(compute_cut_points(target), {"head"})

    def test_limb_chain_collapses_to_root(self):
        # Thigh amputation: chain organs at thigh + shin + foot all
        # severed.  Cut points should be just ``{"left_thigh"}``.
        from world.medical.severance import compute_cut_points
        target = _target({
            "left_femur": _FakeOrgan("left_thigh", wound_stage="severed",
                                       current_hp=0),
            "left_tibia": _FakeOrgan("left_shin", wound_stage="severed",
                                       current_hp=0),
            "left_metatarsals": _FakeOrgan("left_foot",
                                             wound_stage="severed",
                                             current_hp=0),
        })
        self.assertEqual(compute_cut_points(target), {"left_thigh"})

    def test_solo_severance_renders_as_cut_point(self):
        # Single-container severance (e.g. a forearm cut where the
        # downstream hand happens not to also be severed) — the lone
        # severed container IS the cut point.
        from world.medical.severance import compute_cut_points
        target = _target({
            "left_humerus": _FakeOrgan("left_arm", wound_stage="severed",
                                         current_hp=0),
        })
        self.assertEqual(compute_cut_points(target), {"left_arm"})

    def test_multiple_severances_each_emit_a_cut_point(self):
        # Two unrelated severances — head and a leg — should both
        # appear, each collapsed to one entry.
        from world.medical.severance import compute_cut_points
        target = _target({
            "brain": _FakeOrgan("head", wound_stage="severed", current_hp=0),
            "left_femur": _FakeOrgan("left_thigh", wound_stage="severed",
                                       current_hp=0),
            "left_tibia": _FakeOrgan("left_shin", wound_stage="severed",
                                       current_hp=0),
        })
        self.assertEqual(
            compute_cut_points(target), {"head", "left_thigh"},
        )

    def test_empty_when_nothing_severed(self):
        from world.medical.severance import compute_cut_points
        target = _target({
            "heart": _FakeOrgan("chest"),
        })
        self.assertEqual(compute_cut_points(target), set())

    def test_rat_species_uses_rat_cluster_set(self):
        # Sanity: species lookup feeds the cluster set.  Rat-specific
        # cluster includes ``snout`` / ``fur``; verify a snout-
        # container severance also collapses into ``head``.
        from world.medical.severance import compute_cut_points
        target = _target(
            {
                "brain": _FakeOrgan("head", wound_stage="severed",
                                      current_hp=0),
                # cervical_spine is in container "neck" for rats too;
                # we don't need a snout-container organ to verify the
                # collapse, since the cluster set drives suppression
                # regardless of which peer triggers it.
                "cervical_spine": _FakeOrgan("neck",
                                               wound_stage="severed",
                                               current_hp=0),
            },
            species="rat",
        )
        self.assertEqual(compute_cut_points(target), {"head"})
