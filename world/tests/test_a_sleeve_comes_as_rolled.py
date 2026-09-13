"""A template sleeve is decanted with the sex it was rolled with (#3358).

Telnet's `respawn_confirm_template` used to prompt for biological sex and
route the answer into `respawn_finalize_template`, which passed it to
`create_character_from_template` -- overwriting `template['sex']`. The
web door never did: it passes the rolled value. Since the template draws
the first name from the bank keyed to the rolled sex, the telnet override
produced a sleeve named from one bank whose sex said the other.

Owner ruling A: telnet matches the web. The confirm node shows the rolled
sex and offers only decant/back; finalize reads `template['sex']`.
"""
from evennia.utils.test_resources import EvenniaTest

from commands import charcreate


class _Caller:
    class _NDB:
        def __init__(self): self.charcreate_data = {}
    def __init__(self):
        self.ndb = _Caller._NDB(); self.seen = []
    def msg(self, text=None, **kw):
        if text is not None: self.seen.append(text)


def _template(sex="female"):
    return {'first_name': 'Ilse', 'last_name': 'Varga', 'name': 'Ilse Varga',
            'sex': sex, 'grit': 75, 'resonance': 75, 'intellect': 75, 'motorics': 75}


class SleeveComesAsRolledTest(EvenniaTest):

    def test_confirm_node_offers_no_sex_choice(self):
        c = _Caller(); c.ndb.charcreate_data['templates'] = [_template()]
        text, options = charcreate.respawn_confirm_template(c, "", template_idx=0)
        keys = {k for o in options for k in (o["key"] if isinstance(o["key"], tuple) else (o["key"],))}
        self.assertNotIn("1", keys, "a numbered sex menu is still offered")
        self.assertNotIn("Select biological sex", text)
        self.assertIn("Female", text, "the rolled sex is not shown to the player")

    def test_confirm_node_routes_to_finalize_without_a_sex_kwarg(self):
        c = _Caller(); c.ndb.charcreate_data['templates'] = [_template()]
        _, options = charcreate.respawn_confirm_template(c, "", template_idx=0)
        gotos = [o["goto"] for o in options]
        self.assertIn("respawn_finalize_template", gotos)
        for g in gotos:
            if isinstance(g, tuple):
                self.assertNotIn("sex", g[1], "a sex override is still routed to finalize")

    def test_finalize_uses_the_rolled_sex(self):
        # Drive finalize and capture what it hands to the creator.
        captured = {}
        real = charcreate.create_character_from_template
        def spy(account, template, sex="ambiguous"):
            captured['sex'] = sex
            raise RuntimeError("stop here")   # do not build a body in this test
        charcreate.create_character_from_template = spy
        try:
            c = _Caller(); c.ndb.charcreate_data['selected_template'] = _template("female")
            try:
                charcreate.respawn_finalize_template(c, "", sex="male")   # the old override
            except RuntimeError:
                pass
        finally:
            charcreate.create_character_from_template = real
        self.assertEqual(captured.get('sex'), "female",
                         "finalize passed %r; the rolled sex was overridden" % captured.get('sex'))
