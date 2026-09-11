"""The post owns the board, on shift and off.

Regression pin for #2623. The persona builder fell back to the BODY's
`db.menu` when the NPC stood no post, while the job tools that act on
the menu -- `_check_stock`, `_prepare_drink` -- read the post's
exclusively.

So an off-shift bartender's prompt listed drinks the tools would then
refuse to check or pour: the model offering something the game will not
serve. `llm_persona.py` states the rule itself -- "off shift it resolves
to None and they are simply themselves again" -- and the archetype
follows it; the menu did not, because a stale `db.menu` on the body
survives the shift end.

Live when fixed: Sully (#2706) and Sable Vane (#8403) both carry one.
They are now inert rather than contradictory.

The dead branch went with it. The fallback reached for `_find_bar`,
which has had no definition since #2378, so `getattr` returned None and
it collapsed to the body's menu every time.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from typeclasses.llm_persona import build_persona


def _npc(post_menu=None, body_menu=None):
    """A mock keeper whose `_find_bar` is genuinely absent.

    Setting it to None matters. A bare `MagicMock` answers `_find_bar`
    with another mock — callable, whose `.db.menu` is a mock that
    iterates EMPTY — so the unfixed code never reached the body's menu
    and this test passed against it, proving nothing. `_find_bar` has
    had no definition since #2378, so None is also the real shape.
    """
    npc = MagicMock()
    npc._find_bar = None
    npc.db.menu = body_menu
    return npc


def _post(menu):
    post = MagicMock()
    post.db.menu = menu
    return post


BOARD = [{"name": "mug of rotgut"}, {"name": "cup of channel fog"}]


def _menu_of(npc, post):
    with patch("world.service.post_for", return_value=post):
        try:
            return build_persona(npc).get("menu")
        except Exception:
            # The builder touches a lot of surfaces; only the menu is
            # under test, so a mock gap elsewhere must not mask it.
            raise


class TestOneBoardOnShiftAndOff(TestCase):

    def test_off_shift_there_is_no_menu(self):
        """The defect: the body's stale board was offered instead."""
        npc = _npc(body_menu=BOARD)
        self.assertIsNone(_menu_of(npc, post=None))

    def test_on_shift_the_post_supplies_it(self):
        """The control — a builder that always returned None would pass
        the test above."""
        npc = _npc(body_menu=None)
        self.assertEqual(
            _menu_of(npc, post=_post(BOARD)),
            ["mug of rotgut", "cup of channel fog"],
        )

    def test_the_post_wins_over_a_stale_body_menu(self):
        npc = _npc(body_menu=[{"name": "ghost drink"}])
        self.assertEqual(
            _menu_of(npc, post=_post(BOARD)),
            ["mug of rotgut", "cup of channel fog"],
        )

    def test_an_empty_post_board_is_no_menu(self):
        npc = _npc(body_menu=BOARD)
        self.assertIsNone(_menu_of(npc, post=_post([])))
