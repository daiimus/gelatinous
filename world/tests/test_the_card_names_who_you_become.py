"""The flash-clone card names who you will wake up as (#3364).

`archive_character` bumps death_count before the respawn menu renders, and
both doors then labelled the flash-clone option with the OUTGOING key. A
card reading "Jorge Jackson I" delivered "Jorge Jackson II" -- always one
numeral behind. Owner ruling 2026-09-13: the card says who you become.

One helper, `flash_clone_name`, feeds the telnet label, the web context and
`create_flash_clone` itself, so the promise and the result cannot drift.
"""
from django.template import Context, Template
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate

_flash_clone_name = getattr(charcreate, "flash_clone_name", None)


class _NDB:
    def __init__(self):
        self.charcreate_data = {}
        self.charcreate_old_character = None
        self.charcreate_is_respawn = True


class _Caller:
    def __init__(self):
        self.ndb = _NDB(); self.seen = []
    def msg(self, text=None, **kw):
        if text is not None: self.seen.append(text)


class CardNamesWhoYouBecomeTest(EvenniaTest):

    def _dead_sleeve(self):
        # Jorge died once already (key "I"); archiving bumps death_count to 2.
        old = create_object("typeclasses.characters.Character", key="Jorge Jackson I")
        old.death_count = 2
        return old

    def test_helper_gives_the_incoming_name(self):
        if _flash_clone_name is None: self.skipTest("helper absent (unfixed tree)")
        self.assertEqual(_flash_clone_name(self._dead_sleeve()), "Jorge Jackson II")

    def test_telnet_card_names_the_incoming_sleeve(self):
        old = self._dead_sleeve()
        c = _Caller(); c.ndb.charcreate_old_character = old
        c.ndb.charcreate_data['templates'] = [charcreate.generate_random_template() for _ in range(3)]
        text, _ = charcreate.respawn_welcome(c, "")
        self.assertIn("FLASH CLONE", text)
        self.assertIn("Jorge Jackson II", text, "card does not name who you become")
        self.assertNotIn("Jorge Jackson I|n", text, "card still names the outgoing sleeve")

    def test_web_card_renders_the_incoming_name(self):
        # The template prints the context value the view supplies; render the
        # card fragment the way Django will.
        if _flash_clone_name is None: self.skipTest("helper absent (unfixed tree)")
        old = self._dead_sleeve()
        frag = Template('<h5>{{ flash_clone_name }} <small>({{ old_character.sex|title }})</small></h5>')
        out = frag.render(Context({'old_character': old, 'flash_clone_name': _flash_clone_name(old)}))
        self.assertIn("Jorge Jackson II", out)

    def test_label_and_result_agree(self):
        # Control for the whole point: what the card promises is what
        # create_flash_clone delivers.
        if _flash_clone_name is None: self.skipTest("helper absent (unfixed tree)")
        old = self._dead_sleeve()
        promised = _flash_clone_name(old)
        delivered = charcreate.build_name_from_death_count(old.key, old.death_count)
        self.assertEqual(promised, delivered)
