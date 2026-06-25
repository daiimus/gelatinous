"""The `think` command — private interiority as a thoughtbubble.

For now only the actor and any Builder+ in the room perceive a thought; a plain
observer hears nothing. The thinker's name resolves per-observer (the emote
machinery), and the format is the MUSH bubble `Name thinks . o O ( ... )`.
"""

from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world.emote import render_think


def _char(location, key="C"):
    return create_object("typeclasses.characters.Character", key=key,
                         location=location)


class TestRenderThink(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object("typeclasses.rooms.Room", key="room")
        self.thinker = _char(self.room, key="Bob")
        self.thinker.height, self.thinker.build = "tall", "lean"
        self.thinker.sdesc_keyword = "man"

    def _spy(self, char, is_builder):
        """Replace .msg with a recorder and stub the perm check."""
        char.msg = MagicMock()
        char.check_permstring = MagicMock(return_value=is_builder)
        return char.msg

    def test_actor_sees_own_thought(self):
        spy = self._spy(self.thinker, is_builder=False)
        render_think(self.thinker, "these are my thoughts.", self.room)
        spy.assert_called_once_with(
            "You think . o O ( these are my thoughts. )")

    def test_builder_in_room_hears_it_by_perceived_name(self):
        watcher = _char(self.room, key="Staff")
        spy = self._spy(watcher, is_builder=True)
        self._spy(self.thinker, is_builder=False)   # silence actor recorder
        render_think(self.thinker, "secret plan.", self.room)
        # Watcher doesn't know Bob -> sees his sdesc, capitalized, in the bubble.
        (msg,), _ = spy.call_args
        self.assertTrue(msg.endswith("thinks . o O ( secret plan. )"), msg)
        self.assertIn("man", msg.lower())          # by description, not "Bob"
        self.assertNotIn("Bob", msg)

    def test_non_builder_hears_nothing(self):
        bystander = _char(self.room, key="Rando")
        spy = self._spy(bystander, is_builder=False)
        self._spy(self.thinker, is_builder=False)
        render_think(self.thinker, "private.", self.room)
        spy.assert_not_called()
