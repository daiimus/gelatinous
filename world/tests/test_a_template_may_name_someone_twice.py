"""Capitalisation is decided per OCCURRENCE, not per placeholder.

Regression pin for #2641.  `msg_room_identity` picked a single "first
placeholder" by minimum position, decided sentence-start-ness for that
one, and then substituted it with an unbounded `str.replace`.  Two
defects fell out, and both were about what an author may safely write:

* **Every occurrence was capitalised.**  `str.replace` takes no count,
  so a verdict reached about one occurrence applied to all of them --
  `"{actor} draws, and {actor} fires."` rendered *"A lanky man draws,
  and A lanky man fires."*  A repeated reference could not be written
  correctly at all.
* **Only one placeholder could ever be capitalised.**  A later one
  opening a sentence was never considered --
  `"{actor} steps back. {target} does not."` rendered its second name
  lowercase, though the guard immediately above reasons about `.!?` as
  sentence terminators, so an author reading it would expect otherwise.

Filed latent, and verified latent before the rewrite: 482
template-shaped string literals across the repo, 193 direct call sites,
and **zero** trip either shape today.  This removes a constraint on the
255 call sites' future templates rather than fixing a live symptom --
which is why the controls below matter as much as the two new cases.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from world.identity_utils import msg_room_identity


class _Sessions:
    def count(self):
        return 1


class _Observer:
    def __init__(self):
        self.sessions = _Sessions()
        self.received = []

    def msg(self, text=None, **kwargs):
        self.received.append(text)


class _Room:
    def __init__(self, contents):
        self.contents = contents


def _char(name, counter=None):
    c = MagicMock()
    def _display(looker=None, **kw):
        if counter is not None:
            counter.append(name)
        return name
    c.get_display_name = _display
    return c


def _render(template, refs):
    obs = _Observer()
    room = _Room([obs])
    msg_room_identity(location=room, template=template, char_refs=refs)
    return obs.received[0]


ACTOR = "a lanky man"
TARGET = "a scarred woman"


class TestATemplateMayNameSomeoneTwice(TestCase):

    # -- defect 1: the unbounded replace -----------------------------

    def test_a_repeated_name_is_capitalised_only_where_it_opens(self):
        self.assertEqual(
            _render("{actor} draws, and {actor} fires.",
                    {"actor": _char(ACTOR)}),
            "A lanky man draws, and a lanky man fires.",
        )

    def test_a_repeated_name_mid_sentence_is_never_capitalised(self):
        self.assertEqual(
            _render("The crowd watches {actor}, and {actor} knows it.",
                    {"actor": _char(ACTOR)}),
            "The crowd watches a lanky man, and a lanky man knows it.",
        )

    # -- defect 2: the later sentence start --------------------------

    def test_a_second_placeholder_opening_a_sentence_is_capitalised(self):
        self.assertEqual(
            _render("{actor} steps back. {target} does not.",
                    {"actor": _char(ACTOR), "target": _char(TARGET)}),
            "A lanky man steps back. A scarred woman does not.",
        )

    def test_every_terminator_opens_a_sentence(self):
        for mark in (".", "!", "?"):
            with self.subTest(mark):
                self.assertEqual(
                    _render("{actor} stops" + mark + " {target} does not.",
                            {"actor": _char(ACTOR), "target": _char(TARGET)}),
                    "A lanky man stops" + mark + " A scarred woman does not.",
                )

    # -- controls: everything that must NOT change -------------------

    def test_a_mid_sentence_placeholder_stays_lowercase(self):
        """The guard the original pass existed to enforce."""
        self.assertEqual(
            _render("techs peel {actor} out of the gel.",
                    {"actor": _char(ACTOR)}),
            "techs peel a lanky man out of the gel.",
        )

    def test_a_leading_colour_code_is_not_prose(self):
        """Markup before a placeholder must not block capitalisation."""
        self.assertEqual(
            _render("|g{actor} grapples {target}!",
                    {"actor": _char(ACTOR), "target": _char(TARGET)}),
            "|gA lanky man grapples a scarred woman!",
        )

    def test_the_ordinary_two_name_template_is_unchanged(self):
        self.assertEqual(
            _render("{actor} attacks {target} with a knife!",
                    {"actor": _char(ACTOR), "target": _char(TARGET)}),
            "A lanky man attacks a scarred woman with a knife!",
        )

    def test_a_foreign_placeholder_passes_through_untouched(self):
        """`{item}` belongs to another consumer and is not a char_ref."""
        self.assertEqual(
            _render("{actor} disarms {target}, and {item} falls.",
                    {"actor": _char(ACTOR), "target": _char(TARGET)}),
            "A lanky man disarms a scarred woman, and {item} falls.",
        )

    def test_a_template_with_no_placeholders_is_passed_through(self):
        self.assertEqual(
            _render("The lights flicker.", {"actor": _char(ACTOR)}),
            "The lights flicker.",
        )

    # -- the expensive call must not be paid twice -------------------

    def test_a_repeated_name_resolves_once_per_observer(self):
        """`get_display_name` is the priciest call on this path."""
        calls: list[str] = []
        _render("{actor} draws, and {actor} fires.",
                {"actor": _char(ACTOR, calls)})
        self.assertEqual(len(calls), 1)

    # -- the session gate is untouched -------------------------------

    def test_a_sessionless_observer_receives_nothing(self):
        obs = _Observer()
        obs.sessions = None
        msg_room_identity(location=_Room([obs]), template="{actor} nods.",
                          char_refs={"actor": _char(ACTOR)})
        self.assertEqual(obs.received, [])
