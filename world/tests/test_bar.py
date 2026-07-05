"""
Tests for the unified speech backbone payload and the bartender's reaction.

The backbone (world.speech) attaches a structured ``speech``/``addressed``
payload to every *hearing* listener's msg, regardless of which verb (say / to /
pose) carried the words. The bartender reacts off that single shape. These
tests pin the payload routing and the bartender's branch selection.
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import BaseEvenniaTest

import world.speech as speech
import typeclasses.bar as barmod
import typeclasses.llm_npc as llmnpc


class _Obs:
    """A minimal listener that records msg kwargs."""

    def __init__(self, name):
        self.name = name
        self.calls = []

    def msg(self, *args, **kwargs):
        self.calls.append(kwargs)

    def get_display_name(self, looker=None, **kw):
        return self.name

    last = property(lambda self: self.calls[-1] if self.calls else {})


def _room(contents):
    r = MagicMock()
    r.contents = contents
    return r


class TestDrinkNaming(BaseEvenniaTest):
    """Drink keys carry no leading article (display sites add it)."""

    def test_make_drink_strips_leading_article(self):
        from world.bar import make_drink

        d = make_drink(
            name="a mug of rotgut", desc="x", effects={}, location=self.room1
        )
        self.assertEqual(d.key, "mug of rotgut")

    def test_menu_names_are_article_free(self):
        from world.bar import HUB_AND_HOWL_MENU

        for recipe in HUB_AND_HOWL_MENU:
            self.assertFalse(
                recipe["name"].lower().startswith(("a ", "an ", "the ")),
                f"menu name {recipe['name']!r} still carries an article",
            )

    def test_aliases_still_targetable(self):
        from world.bar import make_drink

        d = make_drink(
            name="a mug of rotgut", desc="x", effects={}, location=self.room1
        )
        aliases = d.aliases.all()
        self.assertIn("rotgut", aliases)
        self.assertIn("mug", aliases)


class TestCocktailRecognition(BaseEvenniaTest):
    """The hidden classics layer: loose role-match + spirit-swap spin naming."""

    def _ing(self, role=None, spirit=None, contributions=None):
        m = MagicMock()
        m.db.role = role
        m.db.spirit = spirit
        m.db.contributions = contributions or {}
        m.db.flavour = ""
        return m

    def _negroni(self, spirit):
        return [self._ing("spirit", spirit),
                self._ing("bitter_aperitivo"),
                self._ing("sweet_vermouth")]

    def test_canonical_negroni(self):
        from world.bar import recognize_cocktail
        self.assertEqual(recognize_cocktail(self._negroni("gin")), "Negroni")

    def test_spirit_swap_spin(self):
        from world.bar import recognize_cocktail
        self.assertEqual(recognize_cocktail(self._negroni("mezcal")), "Mezcal Negroni")

    def test_colony_spirit_spin(self):
        from world.bar import recognize_cocktail
        self.assertEqual(
            recognize_cocktail(self._negroni("grain mash")), "Grain Mash Negroni"
        )

    def test_extra_garnish_ignored(self):
        from world.bar import recognize_cocktail
        ings = self._negroni("gin") + [self._ing("citrus")]
        self.assertEqual(recognize_cocktail(ings), "Negroni")

    def test_sour_family_names(self):
        from world.bar import recognize_cocktail
        sour = lambda s: [self._ing("spirit", s), self._ing("citrus"),
                          self._ing("sweetener")]
        self.assertEqual(recognize_cocktail(sour("rum")), "Daiquiri")
        self.assertEqual(recognize_cocktail(sour("whiskey")), "Whiskey Sour")
        self.assertEqual(recognize_cocktail(sour("mezcal")), "Mezcal Sour")

    def test_most_specific_template_wins(self):
        from world.bar import recognize_cocktail
        last_word = [self._ing("spirit", "gin"), self._ing("herbal_liqueur"),
                     self._ing("maraschino"), self._ing("citrus")]
        self.assertEqual(recognize_cocktail(last_word), "Last Word")

    def test_boulevardier_override(self):
        from world.bar import recognize_cocktail
        self.assertEqual(recognize_cocktail(self._negroni("whiskey")), "Boulevardier")

    def test_spiritless_classics(self):
        from world.bar import recognize_cocktail
        mimosa = [self._ing("sparkling_wine"), self._ing("orange_juice")]
        self.assertEqual(recognize_cocktail(mimosa), "Mimosa")
        spritz = [self._ing("bitter_aperitivo"), self._ing("sparkling_wine")]
        self.assertEqual(recognize_cocktail(spritz), "Spritz")

    def test_nesting_prefers_more_specific(self):
        from world.bar import recognize_cocktail
        # rum + lime + sugar = Daiquiri (sour). Add soda -> Collins. Add mint -> Mojito.
        sour = [self._ing("spirit", "rum"), self._ing("citrus"),
                self._ing("sweetener")]
        self.assertEqual(recognize_cocktail(sour), "Daiquiri")
        collins = sour + [self._ing("soda")]
        self.assertEqual(recognize_cocktail(collins), "Rum Collins")
        mojito = collins + [self._ing("mint")]
        self.assertEqual(recognize_cocktail(mojito), "Mojito")

    def test_margarita_sidecar_family(self):
        from world.bar import recognize_cocktail
        marg = [self._ing("spirit", "tequila"), self._ing("orange_liqueur"),
                self._ing("citrus")]
        self.assertEqual(recognize_cocktail(marg), "Margarita")
        sidecar = [self._ing("spirit", "brandy"), self._ing("orange_liqueur"),
                   self._ing("citrus")]
        self.assertEqual(recognize_cocktail(sidecar), "Sidecar")

    def test_no_spirit_no_match(self):
        from world.bar import recognize_cocktail
        # bitters + sweet vermouth alone fills no spirit-less skeleton either.
        self.assertIsNone(recognize_cocktail(
            [self._ing("bitters"), self._ing("sweet_vermouth")]
        ))

    def test_unrecognized_freemix(self):
        from world.bar import recognize_cocktail
        self.assertIsNone(recognize_cocktail([self._ing("spirit", "gin")]))

    def test_project_mix_caps_and_names(self):
        from world.bar import project_mix, MIX_EFFECT_CAP
        ings = [self._ing("spirit", "gin", {"alcohol": 2}),
                self._ing("bitter_aperitivo", None, {"alcohol": 1}),
                self._ing("sweet_vermouth", None, {"alcohol": 1})]
        proj = project_mix(ings)
        self.assertEqual(proj["cocktail"], "Negroni")
        self.assertEqual(proj["effects"], {"alcohol": 4})
        # Overshoot is trimmed to the safety-net cap.
        over = project_mix([self._ing("spirit", "gin", {"alcohol": 9})])
        self.assertEqual(over["effects"]["alcohol"], MIX_EFFECT_CAP)

    def test_taste_authored_for_classic(self):
        from world.bar import project_mix, COCKTAIL_TASTE
        negroni = [self._ing("spirit", "gin"), self._ing("bitter_aperitivo"),
                   self._ing("sweet_vermouth")]
        self.assertEqual(project_mix(negroni)["taste"], COCKTAIL_TASTE["Negroni"])

    def test_taste_composed_for_freemix(self):
        from world.bar import compose_taste
        g = self._ing("spirit", "gin"); g.db.flavour = "juniper-sharp botanicals"
        self.assertEqual(
            compose_taste([g], None), "It tastes of juniper-sharp botanicals."
        )
        v = self._ing("sweet_vermouth"); v.db.flavour = "sweet, herbal wine"
        self.assertEqual(
            compose_taste([g, v], None),
            "It tastes of juniper-sharp botanicals and sweet, herbal wine.",
        )

    def test_compose_has_no_semicolons(self):
        from world.bar import compose_flavour
        a = self._ing(); a.db.flavour = "alpha"
        b = self._ing(); b.db.flavour = "beta"
        c = self._ing(); c.db.flavour = "gamma"
        out = compose_flavour([a, b, c])
        self.assertNotIn(";", out)
        self.assertEqual(out, "alpha, beta, and gamma")

    def test_default_name_single_ingredient(self):
        from world.bar import default_drink_name, project_mix
        # A neat spirit is a glass of that spirit.
        gin = self._ing("spirit", "gin")
        gin.key = "bottle of gin"
        self.assertEqual(default_drink_name([gin], None), "glass of gin")
        # Two pours of the same thing is still a glass of it.
        self.assertEqual(default_drink_name([gin, gin], None), "glass of gin")
        # project_mix carries the default name.
        self.assertEqual(project_mix([gin])["name"], "glass of gin")

    def test_default_name_non_spirit_strips_vessel(self):
        from world.bar import default_drink_name
        verm = self._ing("sweet_vermouth")
        verm.key = "bottle of sweet vermouth"
        self.assertEqual(
            default_drink_name([verm], None), "glass of sweet vermouth"
        )

    def test_default_name_multi_is_house_mix(self):
        from world.bar import default_drink_name
        a = self._ing("spirit", "vodka"); a.key = "bottle of vodka"
        b = self._ing("cream"); b.key = "carton of cream"
        self.assertEqual(default_drink_name([a, b], None), "house mix")

    def test_default_name_prefers_cocktail(self):
        from world.bar import default_drink_name
        g = self._ing("spirit", "gin"); g.key = "bottle of gin"
        self.assertEqual(default_drink_name([g], "Negroni"), "Negroni")

    def test_project_mix_suggests_method(self):
        from world.bar import project_mix
        negroni = [self._ing("spirit", "gin"), self._ing("bitter_aperitivo"),
                   self._ing("sweet_vermouth")]
        self.assertEqual(project_mix(negroni)["method"], "stir")
        daiquiri = [self._ing("spirit", "rum"), self._ing("citrus"),
                    self._ing("sweetener")]
        self.assertEqual(project_mix(daiquiri)["method"], "shake")
        # Free-mix has no suggested method.
        self.assertIsNone(project_mix([self._ing("spirit", "vodka")])["method"])

    def test_catalog_covers_every_cocktail(self):
        from world.bar import INGREDIENT_CATALOG, COCKTAILS
        roles = {p.get("role") for p in INGREDIENT_CATALOG.values()}
        spirits = {p.get("spirit") for p in INGREDIENT_CATALOG.values()
                   if p.get("role") == "spirit"}
        for c in COCKTAILS:
            if c.get("spirit_keyed", True):
                self.assertIn(c["canonical"], spirits,
                              f"{c['name']}: canonical spirit not in catalog")
            for role in c["roles"]:
                self.assertIn(role, roles,
                              f"{c['name']}: role {role} has no ingredient")

    def test_make_ingredient_sets_identity(self):
        from world.bar import make_ingredient
        g = make_ingredient("mezcal", location=self.room1)
        self.assertEqual(g.db.role, "spirit")
        self.assertEqual(g.db.spirit, "mezcal")
        self.assertEqual(g.db.contributions, {"alcohol": 2})
        self.assertTrue(g.db.is_ingredient)


class TestBarMenuSave(BaseEvenniaTest):
    """The save/brand step records a free-text-named recipe to the bar menu."""

    def test_save_recipe_brands_and_keeps_base(self):
        from commands.bar_menu import _save_recipe

        bar = MagicMock()
        bar.db.menu = []
        proj = {"effects": {"alcohol": 4}, "flavour": "juniper-sharp",
                "taste": "a bittersweet Negroni", "cocktail": "Negroni"}
        r = _save_recipe(bar, "Kyoto Negroni", proj=proj, taste=None)

        self.assertEqual(r["name"], "Kyoto Negroni")
        self.assertEqual(r["base_cocktail"], "Negroni")   # remembers the family
        self.assertEqual(r["effects"], {"alcohol": 4})
        self.assertEqual(r["taste"], "a bittersweet Negroni")   # taste fallback
        self.assertIn("kyoto", r["order_keywords"])
        self.assertIn("negroni", r["order_keywords"])
        self.assertEqual(bar.db.menu[-1]["name"], "Kyoto Negroni")

    def test_custom_taste_overrides_composed(self):
        from commands.bar_menu import _save_recipe

        bar = MagicMock()
        bar.db.menu = []
        proj = {"effects": {}, "flavour": "auto flavour",
                "taste": "It tastes of auto flavour.", "cocktail": None}
        r = _save_recipe(bar, "House Pour", proj=proj, taste="silk and smoke")
        self.assertEqual(r["taste"], "silk and smoke")
        self.assertIsNone(r["base_cocktail"])


class TestBarStock(BaseEvenniaTest):
    """A bar's bottomless stock = base pantry + its menu's ingredients."""

    def test_derive_stock_from_menu(self):
        from world.bar import (derive_bar_stock, BASE_BAR_PANTRY,
                               HUB_AND_HOWL_MENU, INGREDIENT_CATALOG)
        stock = derive_bar_stock(HUB_AND_HOWL_MENU)
        for k in BASE_BAR_PANTRY:
            self.assertIn(k, stock)
        for k in ("grain_mash", "reactor_cut", "poppy_tincture", "caf"):
            self.assertIn(k, stock)
        for k in stock:
            self.assertIn(k, INGREDIENT_CATALOG)

    def test_menu_ingredients_are_catalog_keys(self):
        from world.bar import HUB_AND_HOWL_MENU, INGREDIENT_CATALOG
        for r in HUB_AND_HOWL_MENU:
            for k in r.get("ingredients", ()):
                self.assertIn(k, INGREDIENT_CATALOG,
                              f"{r['name']}: unknown ingredient {k}")


class TestOffMenuStock(BaseEvenniaTest):
    """Off-menu service: a classic the bar carries the makings for is served
    even when it isn't on the board (the bartending capability layer)."""

    _FULL = None  # filled in setUp from the catalog

    def setUp(self):
        super().setUp()
        from world.bar import INGREDIENT_CATALOG
        self._FULL = list(INGREDIENT_CATALOG)

    def test_negroni_from_full_kit(self):
        from world.bar import mix_offmenu
        r = mix_offmenu("can you do a negroni", self._FULL)
        self.assertIsNotNone(r)
        self.assertEqual(r["name"], "Negroni")
        self.assertIn("alcohol", r["effects"])      # composed from components

    def test_spirit_name_alias_pins_the_spin(self):
        from world.bar import mix_offmenu
        # 'Boulevardier' is the whiskey spin of a Negroni.
        r = mix_offmenu("a boulevardier", self._FULL)
        self.assertEqual(r["name"], "Boulevardier")

    def test_ordered_spirit_makes_a_spin(self):
        from world.bar import mix_offmenu
        r = mix_offmenu("mezcal negroni", self._FULL)
        self.assertEqual(r["name"], "Mezcal Negroni")

    def test_none_when_a_component_is_unstocked(self):
        from world.bar import mix_offmenu
        # gin + aperitivo but NO sweet vermouth -> can't build a Negroni
        self.assertIsNone(mix_offmenu("negroni", ["gin", "bitter_aperitivo"]))

    def test_none_for_unknown_drink(self):
        from world.bar import mix_offmenu
        self.assertIsNone(mix_offmenu("a glass of nanofluid", self._FULL))

    def test_colony_stock_makes_a_grimy_spin(self):
        from world.bar import mix_offmenu
        # base pantry (citrus + sweetener) + a colony spirit -> a Sour spin
        r = mix_offmenu("a sour", ["grain_mash", "lime", "sugar_syrup"])
        self.assertIsNotNone(r)
        self.assertIn("Sour", r["name"])            # 'Grain Mash Sour'

    def test_resolve_prefers_menu_over_stock(self):
        from world.bar import resolve_drink
        bar = MagicMock()
        bar.db.menu = [{"name": "Rotgut", "order_keywords": ("rotgut",)}]
        bar.db.stock = None
        recipe, off = resolve_drink("a rotgut", bar)
        self.assertFalse(off)
        self.assertEqual(recipe["name"], "Rotgut")

    def test_resolve_falls_to_offmenu_stock(self):
        from world.bar import resolve_drink
        bar = MagicMock()
        bar.db.menu = []
        bar.db.stock = self._FULL
        recipe, off = resolve_drink("negroni", bar)
        self.assertTrue(off)
        self.assertEqual(recipe["name"], "Negroni")

    def test_stockable_lists_classics_for_full_kit(self):
        from world.bar import stockable_cocktails
        names = stockable_cocktails(self._FULL)
        self.assertIn("Negroni", names)
        self.assertIn("Margarita", names)

    def test_bar_stock_derives_from_menu_when_unset(self):
        from world.bar import bar_stock, BASE_BAR_PANTRY, HUB_AND_HOWL_MENU
        bar = MagicMock()
        bar.db.stock = None
        bar.db.menu = list(HUB_AND_HOWL_MENU)
        stock = bar_stock(bar)
        for k in BASE_BAR_PANTRY:
            self.assertIn(k, stock)
        self.assertIn("grain_mash", stock)          # a menu drink's ingredient


class TestSnacks(BaseEvenniaTest):
    """Free bar snacks (§10): keyword match + room resolution."""

    def test_match_snack(self):
        from world.bar import match_snack, DEFAULT_BAR_SNACKS

        self.assertEqual(
            match_snack("grab some brine pods", DEFAULT_BAR_SNACKS)["name"],
            "brine pods",
        )
        self.assertEqual(
            match_snack("jerky", DEFAULT_BAR_SNACKS)["name"], "synth-jerky"
        )
        self.assertIsNone(match_snack("a wrench", DEFAULT_BAR_SNACKS))
        self.assertIsNone(match_snack("", DEFAULT_BAR_SNACKS))

    def test_find_room_bar_snack_strips_from_clause(self):
        from world.bar import find_room_bar_snack, DEFAULT_BAR_SNACKS

        bar = MagicMock()
        bar.is_bartender = lambda c: True  # duck-typed as a bar
        bar.db.snacks = DEFAULT_BAR_SNACKS
        room = MagicMock()
        room.contents = [bar]

        found = find_room_bar_snack(room, "crackers from the hull-slab bar")
        self.assertIsNotNone(found)
        self.assertIs(found[0], bar)
        self.assertEqual(found[1]["name"], "ration crackers")

    def test_find_room_bar_snack_no_bar(self):
        from world.bar import find_room_bar_snack, DEFAULT_BAR_SNACKS

        not_a_bar = MagicMock(spec=[])  # no is_bartender
        room = MagicMock()
        room.contents = [not_a_bar]
        self.assertIsNone(find_room_bar_snack(room, "brine pods"))


class TestSpeechPayloadRouting(BaseEvenniaTest):
    """broadcast_speech attaches speech/addressed only to hearing listeners."""

    def setUp(self):
        super().setUp()
        self.speaker = _Obs("a lean man")
        self.target = _Obs("a tall woman")
        self.bystander = _Obs("a short man")
        self.room = _room([self.speaker, self.target, self.bystander])

    def _patch_perception(self, hear=True, see=True):
        # Backbone reads can_hear/can_see + attribution; stub them flat.
        return [
            patch.object(speech, "can_hear", lambda o: hear),
            patch.object(speech, "can_see", lambda o: see),
            patch.object(speech, "resolve_speaker_attribution",
                         lambda s, o: "a lean man"),
            patch.object(speech, "visible_voice_flavor", lambda s: None),
        ]

    def _run(self, **kw):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in self._patch_perception(**kw.pop("perc", {})):
                stack.enter_context(p)
            speech.broadcast_speech(self.speaker, "hi", self.room, **kw)

    def test_say_not_addressed(self):
        self._run()
        self.assertEqual(self.target.last.get("speech"), "hi")
        self.assertFalse(self.target.last.get("addressed"))
        self.assertFalse(self.bystander.last.get("addressed"))

    def test_to_marks_only_target_addressed(self):
        self._run(target=self.target)
        self.assertTrue(self.target.last.get("addressed"))
        self.assertEqual(self.bystander.last.get("speech"), "hi")
        self.assertFalse(self.bystander.last.get("addressed"))

    def test_deaf_listener_gets_no_words(self):
        self._run(perc={"hear": False, "see": True})
        # Deaf-but-sighted still receives a line, but no speech payload.
        self.assertIsNone(self.target.last.get("speech"))
        self.assertNotIn("addressed", self.target.last)

    def test_no_channel_skipped(self):
        self._run(perc={"hear": False, "see": False})
        self.assertEqual(self.target.calls, [])


class TestPosePayload(BaseEvenniaTest):
    """A pose's embedded quote rides the same rails; refs count as addressed."""

    def test_pose_speech_payload_addressed(self):
        from world.emote import SpeechToken, CharRefToken, render_dot_pose

        actor = _Obs("a lean man")
        target = _Obs("a tall woman")
        room = _room([actor, target])
        tokens = [CharRefToken(target, "woman"),
                  SpeechToken("Let me get some rotgut.", actor)]

        with patch.object(speech, "can_hear", lambda o: True):
            with patch("world.emote.render_for_observer", lambda t, a, o: "rendered"):
                render_dot_pose(tokens, actor, room)

        self.assertEqual(target.last.get("speech"), "Let me get some rotgut.")
        self.assertTrue(target.last.get("addressed"))


class TestBarStaffAccess(BaseEvenniaTest):
    """Staff (Builder+) can work/manage any bar; ownership still gates others."""

    def _bar(self, owner=None, staff=None):
        b = MagicMock()
        b.db.owner = owner
        b.db.staff = staff or []
        b._is_staff = barmod.BarCounter._is_staff  # real staticmethod
        return b

    def _char(self, is_staff=False):
        c = MagicMock()
        c.locks.check_lockstring = lambda obj, lockstr: is_staff
        return c

    def _is_bartender(self, bar, char):
        return barmod.BarCounter.is_bartender(bar, char)

    def test_staff_can_work_owned_bar(self):
        bar = self._bar(owner=object())  # owned by someone else
        self.assertTrue(self._is_bartender(bar, self._char(is_staff=True)))

    def test_non_staff_blocked_on_owned_bar(self):
        bar = self._bar(owner=object())
        self.assertFalse(self._is_bartender(bar, self._char(is_staff=False)))

    def test_owner_allowed(self):
        owner = self._char(is_staff=False)
        bar = self._bar(owner=owner)
        self.assertTrue(self._is_bartender(bar, owner))

    def test_unowned_allows_anyone(self):
        bar = self._bar()
        self.assertTrue(self._is_bartender(bar, self._char(is_staff=False)))

    def test_staff_check_failure_is_safe(self):
        bar = self._bar(owner=object())
        char = MagicMock()
        char.locks.check_lockstring.side_effect = RuntimeError("boom")
        # A lock-check hiccup must not crash; it just denies non-owners.
        self.assertFalse(self._is_bartender(bar, char))


class TestBartenderReaction(BaseEvenniaTest):
    """at_msg_receive routes the unified payload to ack / order / nothing."""

    def _bartender(self):
        b = MagicMock()
        b._is_gratitude = barmod.Bartender._is_gratitude  # real staticmethod
        b._acknowledge = MagicMock()
        # at_msg_receive (mixin) defers to this real bartender hook for the
        # gratitude/order intercept before the LLM layer.
        b._handle_directed_speech = (
            barmod.Bartender._handle_directed_speech.__get__(b, barmod.Bartender))
        return b

    def _call(self, b, speaker, **payload):
        return barmod.Bartender.at_msg_receive(
            b, text=None, from_obj=speaker, **payload
        )

    def test_addressed_order_fulfils(self):
        b = self._bartender()
        speaker = object()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, speaker, speech="a rotgut please", addressed=True)
        mock_delay.assert_called_once()
        b._acknowledge.assert_not_called()

    def test_unaddressed_speech_does_nothing(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech="a rotgut please", addressed=False)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()

    def test_gratitude_acks_even_if_addressed(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech="much obliged", addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_called_once()

    def test_no_speech_payload_ignored(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, object(), speech=None, addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()

    def test_own_speech_ignored(self):
        b = self._bartender()
        with patch.object(barmod, "delay") as mock_delay:
            # from_obj is the bartender itself
            self._call(b, b, speech="thanks", addressed=True)
        mock_delay.assert_not_called()
        b._acknowledge.assert_not_called()


class TestBartenderLLMRouting(BaseEvenniaTest):
    """The gated LLM conversational layer: directed/ambient routing, payload,
    cooldown, loop-guard, fail-safe. Orders + gratitude paths stay untouched."""

    _REAL = (
        "_classify_speech", "_is_npc_speaker", "_is_engaged_with",
        "_mentions_self", "_name_aliases",
        "_handle_directed_speech", "_try_llm_reply",
        "_render_llm_reply", "_resolve_second_person",
        "_llm_fallback", "_llm_silent",
    )

    def _bartender(self, llm_driven=True, location="room"):
        b = MagicMock()
        b.key = "Sable"
        b.sdesc_keyword = "catgirl"
        b.db.llm_driven = llm_driven
        b.db.is_bartender_npc = True
        b.ndb.last_llm = 0
        b.ndb.llm_engaged_until = None    # no conversation hold by default
        b.location = location
        b._is_gratitude = barmod.Bartender._is_gratitude  # real staticmethod
        for name in self._REAL:
            bound = getattr(barmod.Bartender, name).__get__(b, barmod.Bartender)
            setattr(b, name, bound)
        # default: not alone (so ambient stays ambient); override per test
        b._is_alone_with = lambda speaker: False
        # real _resolve_second_person needs a concrete handle
        b._address_handle = lambda t: "a lean man"
        # default: no long-term memories → _try_llm_reply skips the embed round-
        # trip and goes straight to generation (Phase 2; override per test)
        b._load_memories = lambda: []
        return b

    def _speaker(self, location="room", name="a lean man"):
        s = MagicMock()
        s.db.is_bartender_npc = False
        s.db.llm_driven = False
        s.db.is_npc = False               # auto-mock truthiness reads as NPC
        s.location = location
        s.get_display_name = lambda looker=None, **kw: name
        return s

    def _call(self, b, speaker, **payload):
        return barmod.Bartender.at_msg_receive(
            b, text=None, from_obj=speaker, **payload
        )

    # --- routing through at_msg_receive ---

    def test_directed_name_routes_directed(self):
        b, spk = self._bartender(), self._speaker()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as mock_delay:
            self._call(b, spk, speech="hey sable, busy?", addressed=False)
        mock_delay.assert_called_once()
        self.assertIn("directed", mock_delay.call_args.args)

    def test_ambient_routes_ambient(self):
        b, spk = self._bartender(), self._speaker()
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as mock_delay:
            self._call(b, spk, speech="this place is dead tonight", addressed=False)
        mock_delay.assert_called_once()
        self.assertIn("ambient", mock_delay.call_args.args)

    def test_disabled_routes_nothing(self):
        b, spk = self._bartender(), self._speaker()
        with patch.object(llmnpc, "llm_enabled", return_value=False), \
                patch.object(llmnpc, "delay") as mock_delay:
            self._call(b, spk, speech="hey sable", addressed=False)
        mock_delay.assert_not_called()

    def test_loop_guard_ignores_npc_speaker(self):
        b, npc = self._bartender(), self._speaker()
        npc.db.is_bartender_npc = True
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as mock_delay:
            self._call(b, npc, speech="rough night sable", addressed=False)
        mock_delay.assert_not_called()

    def test_solo_room_routes_directed(self):
        # alone with the speaker → a plain (un-named) line is plainly for her
        b, spk = self._bartender(), self._speaker()
        b._is_alone_with = lambda speaker: True
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as mock_delay:
            self._call(b, spk, speech="this drink is watered down", addressed=False)
        mock_delay.assert_called_once()
        self.assertIn("directed", mock_delay.call_args.args)

    def test_is_alone_with_detects_other_characters(self):
        from typeclasses.characters import Character
        b = self._bartender()
        b._is_alone_with = barmod.Bartender._is_alone_with.__get__(
            b, barmod.Bartender)
        spk = MagicMock(spec=Character)
        room = MagicMock()
        b.location = room
        room.contents = [b, spk]
        self.assertTrue(b._is_alone_with(spk))
        room.contents = [b, spk, MagicMock(spec=Character)]
        self.assertFalse(b._is_alone_with(spk))

    def test_addressed_still_routes_to_order(self):
        b, spk = self._bartender(), self._speaker()
        # the addressed→order delay fires in the bartender hook (bar module),
        # before the LLM layer is even consulted.
        with patch.object(barmod, "delay") as mock_delay:
            self._call(b, spk, speech="a rotgut", addressed=True)
        mock_delay.assert_called_once()
        # the addressed branch targets _fulfil_order, not the LLM layer
        self.assertIs(mock_delay.call_args.args[1], b._fulfil_order)

    # --- _try_llm_reply gating + payload ---

    def test_try_llm_reply_starts_agentic_round(self):
        b, patron = self._bartender(), self._speaker(name="a wiry courier")
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "build_persona", return_value={"x": 1}), \
                patch.object(llmnpc, "build_messages", return_value=["m"]) as bm:
            taken = b._try_llm_reply("rough night?", patron, "directed")
        self.assertTrue(taken)
        bm.assert_called_once()
        b._agentic_round.assert_called_once()      # the loop is kicked off
        args = b._agentic_round.call_args.args
        self.assertEqual(args[0], ["m"])           # messages
        self.assertEqual(args[3], "rough night?")  # line

    def test_try_llm_reply_gated_off(self):
        b, patron = self._bartender(llm_driven=False), self._speaker()
        taken = b._try_llm_reply("hi", patron, "directed")
        self.assertFalse(taken)
        b._agentic_round.assert_not_called()

    def test_try_llm_reply_cooldown_is_silent(self):
        from time import monotonic
        b, patron = self._bartender(), self._speaker()
        b.ndb.last_llm = monotonic()  # just replied
        with patch.object(llmnpc, "llm_enabled", return_value=True):
            taken = b._try_llm_reply("hi", patron, "directed")
        self.assertTrue(taken)         # handled-by-silence, no scripted fallback
        b._agentic_round.assert_not_called()

    # --- order-path fallback, render, fail-safe ---

    def test_order_no_recipe_llm_off_curt_line(self):
        b, patron = self._bartender(llm_driven=False), self._speaker()
        b._find_bar = lambda: None
        b.db.menu = []
        with patch.object(barmod, "match_recipe", return_value=None):
            barmod.Bartender._fulfil_order(b, "a unicorn tear", patron)
        b.execute_cmd.assert_any_call("say Don't serve that here.")

    def test_render_unified_pose(self):
        # action + speech -> ONE third-person `emote` with the line woven in as a
        # quote, fired through the REAL emote command (execute_cmd).
        b = self._bartender()
        b._render_llm_reply("What's it to ya?", "wipes down the slab")
        b.execute_cmd.assert_called_once_with(
            'emote wipes down the slab, "What\'s it to ya?"')

    def test_render_action_only(self):
        b = self._bartender()
        b.execute_cmd.reset_mock()
        b._render_llm_reply(None, "polishes a glass")
        b.execute_cmd.assert_called_once_with("emote polishes a glass")

    def test_render_thought_goes_to_think(self):
        # The private interiority channel routes to the REAL `think` command.
        b = self._bartender()
        b.execute_cmd.reset_mock()
        b._render_llm_reply(None, None, "He's lying to me.")
        b.execute_cmd.assert_called_once_with("think He's lying to me.")

    def test_render_action_and_thought(self):
        b = self._bartender()
        b.execute_cmd.reset_mock()
        b._render_llm_reply(None, "wipes the bar", "Trouble walking in.")
        b.execute_cmd.assert_any_call("emote wipes the bar")
        b.execute_cmd.assert_any_call("think Trouble walking in.")

    def test_render_speech_only(self):
        b = self._bartender()
        b.execute_cmd.reset_mock()
        b._render_llm_reply("just a sec", None)
        b.execute_cmd.assert_called_once_with("say just a sec")

    # --- room presence: roster + enter/leave awareness ---

    def _bind(self, b, *names):
        for name in names:
            setattr(b, name,
                    getattr(barmod.Bartender, name).__get__(b, barmod.Bartender))

    def test_present_others_excludes_self_and_speaker(self):
        # The roster is who ELSE is here, by the name this NPC perceives them by.
        b = self._bartender()
        self._bind(b, "_present_others")
        b._address_handle = lambda t: t.get_display_name(b)
        patron = self._speaker(name="a lean man")
        other = self._speaker(name="a tall woman")
        loc = MagicMock(); loc.contents = [b, patron, other]
        b.location = loc
        self.assertEqual(b._present_others(patron), ["a tall woman"])

    def test_notice_arrival_buffers_and_reacts(self):
        b = self._bartender()
        self._bind(b, "notice_presence_change", "_observe_action",
                   "_is_npc_speaker")
        b.ndb.action_buffer = []
        mover = self._speaker(name="a tall woman")
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.notice_presence_change(mover, entered=True)
        self.assertTrue(any("arrives" in e for e in b.ndb.action_buffer))
        d.assert_called_once()
        self.assertEqual(d.call_args.args[4], "arrival")  # gated arrival reaction

    def test_notice_departure_buffers_no_reaction(self):
        b = self._bartender()
        self._bind(b, "notice_presence_change", "_observe_action",
                   "_is_npc_speaker")
        b.ndb.action_buffer = []
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.notice_presence_change(self._speaker(name="a tall woman"),
                                     entered=False)
        self.assertTrue(any("leaves" in e for e in b.ndb.action_buffer))
        d.assert_not_called()  # a departure is observe-only

    def test_notice_npc_arrival_no_reaction(self):
        # Another NPC walking in is logged but never provokes a reply (loop guard)
        b = self._bartender()
        self._bind(b, "notice_presence_change", "_observe_action",
                   "_is_npc_speaker")
        b.ndb.action_buffer = []
        npc = self._speaker(name="another tender"); npc.db.llm_driven = True
        with patch.object(llmnpc, "llm_enabled", return_value=True), \
                patch.object(llmnpc, "delay") as d:
            b.notice_presence_change(npc, entered=True)
        d.assert_not_called()

    def test_llm_fallback_curt_line(self):
        b = self._bartender()
        b._llm_fallback()
        b.execute_cmd.assert_called_once_with("say Don't serve that here.")

    def _bind_memory(self, b):
        b._hist_key = barmod.Bartender._hist_key            # staticmethods
        b._reconstruct_reply = barmod.Bartender._reconstruct_reply
        for name in ("_recent_history", "_remember_turn"):
            setattr(b, name,
                    getattr(barmod.Bartender, name).__get__(b, barmod.Bartender))

    def test_short_term_memory_roundtrip(self):
        b = self._bartender()
        self._bind_memory(b)
        patron = self._speaker(); patron.id = 42
        b.ndb.llm_history = {}
        self.assertEqual(b._recent_history(patron), [])
        b._remember_turn(patron, "hey", "a man", "evening", "wipes the bar")
        hist = b._recent_history(patron)
        self.assertEqual(len(hist), 1)
        self.assertIn("hey", hist[0]["user"])
        self.assertEqual(hist[0]["assistant"], '*wipes the bar* "evening"')

    def test_memory_caps_at_limit(self):
        b = self._bartender()
        self._bind_memory(b)
        patron = self._speaker(); patron.id = 7
        b.ndb.llm_history = {}
        for i in range(llmnpc.LLM_HISTORY_TURNS + 4):
            b._remember_turn(patron, f"l{i}", "a man", f"r{i}", "nods")
        self.assertEqual(len(b._recent_history(patron)), llmnpc.LLM_HISTORY_TURNS)

    def test_memory_is_per_interlocutor(self):
        b = self._bartender()
        self._bind_memory(b)
        b.ndb.llm_history = {}
        p1 = self._speaker(); p1.id = 1
        p2 = self._speaker(); p2.id = 2
        b._remember_turn(p1, "to one", "a man", "hi one", "nods")
        self.assertEqual(len(b._recent_history(p1)), 1)
        self.assertEqual(b._recent_history(p2), [])  # separate conversation

    # --- the agentic tool loop ---

    def _bind_loop(self, b):
        b._hist_key = barmod.Bartender._hist_key
        b._reconstruct_reply = barmod.Bartender._reconstruct_reply
        for name in ("_on_turn", "_run_context_tool", "_render_llm_reply",
                     "_handle_action_tool", "_remember_turn", "_recent_history"):
            setattr(b, name,
                    getattr(barmod.Bartender, name).__get__(b, barmod.Bartender))
        b.ndb.llm_history = {}

    def test_on_turn_context_tool_loops(self):
        b = self._bartender(); self._bind_loop(b)
        patron = self._speaker(); patron.id = 5
        b._run_context_tool = lambda tool, arg, p: "a stocky droog"
        turn = {"speech": None, "action": None, "tool": "look",
                "tool_argument": "patron"}
        with patch.object(llmnpc, "parse_turn", return_value=turn):
            b._on_turn(["m"], {}, patron, "hi", "a man", lambda: None, 0, None, "{}")
        b._agentic_round.assert_called_once()           # looped to gather context
        b.execute_cmd.assert_not_called()               # no terminal render yet

    def test_on_turn_action_tool_runs_real_command(self):
        b = self._bartender(); self._bind_loop(b)
        patron = self._speaker(); patron.id = 6
        turn = {"speech": "Coming up", "action": "grabs a glass", "thought": None,
                "tool": "prepare_drink", "tool_argument": "Negroni"}
        with patch.object(llmnpc, "parse_turn", return_value=turn):
            b._on_turn(["m"], {}, patron, "a negroni", "a man", lambda: None, 0, None, "{}")
        b.execute_cmd.assert_any_call("prepare Negroni")  # the REAL command
        b._agentic_round.assert_not_called()              # terminal, no loop

    def test_on_turn_terminal_renders(self):
        # Terminal turn: action+speech go out as ONE third-person `emote` through
        # the real emote command (execute_cmd), the line woven in as a quote.
        b = self._bartender(); self._bind_loop(b)
        patron = self._speaker(); patron.id = 8
        turn = {"speech": "hey", "action": "nods", "thought": None,
                "tool": "none", "tool_argument": ""}
        with patch.object(llmnpc, "parse_turn", return_value=turn):
            b._on_turn(["m"], {}, patron, "hi", "a man", lambda: None, 0, None, "{}")
        b.execute_cmd.assert_any_call('emote nods, "hey"')

    def test_run_context_tool_look_and_stock(self):
        b = self._bartender()
        b._perceive = lambda patron: "a wiry courier, scarred jaw"
        patron = self._speaker()
        # look is the shared mixin tool (Bartender delegates to it via super)
        self.assertIn("wiry courier",
                      llmnpc.LLMNpcMixin._run_context_tool(b, "look", "patron", patron))
        # check_stock is the bartender's own extension
        b._run_context_tool = barmod.Bartender._run_context_tool.__get__(
            b, barmod.Bartender)
        b._find_bar = lambda: None
        b.db.menu = [{"name": "Negroni"}, {"name": "Martini"}]
        self.assertIn("Negroni", b._run_context_tool("check_stock", "", patron))

    def test_mentions_self(self):
        b = self._bartender()
        self.assertTrue(b._mentions_self("hey sable"))
        self.assertTrue(b._mentions_self("yo bartender"))
        self.assertTrue(b._mentions_self("nice catgirl ears"))
        self.assertFalse(b._mentions_self("this whole place is dead"))
