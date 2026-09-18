"""A bowl knows how it is served (#3413).

Serve flavour used to live in two places that could not both be right.
Every counter seeded ``purchase_msg_buyer`` / ``purchase_msg_room``, and
three counters (Lin's noodle cart, the Escallier snailery, the butcher's
cart) carried authored ones -- which on a STAFFED counter could never
print: `buy` finds the keeper, hands the item over through
`shop.service.hand_over`, and returns before it ever reads them. Authored
prose, dead on arrival, on every counter somebody actually stands behind.

The owner's ruling: retire the counter's lines, and put the custom prose
on the CONSUMABLE instead -- not on the counter, not on the keeper. A
bowl of noodles is ladled whoever is ladling it, at Lin's cart or
anywhere else that bowl ends up. So the item carries `serve_line` and
`hand_over` reads it.

Only Auntie Lin's four dishes are authored that way, and the other two
counters are the reason a line-less dish is not an oversight: the
Escallier snailery is a `BarCounter`, so its dishes are served by the
bar's own craft prose and never reach `hand_over` at all, and the
butcher's five dishes cross on the cart's board gesture. Both halves of
that rule are pinned here.

That gives exactly one door for the gesture, and this module pins it
open from both sides:

    the item's own `serve_line`   ->  wins
    the counter style's gesture   ->  when the item has nothing to say
    STYLES["shelf"]["gesture"]    ->  when neither does
    a line that will not render   ->  the counter's gesture, and a log

and pins shut the three seams the change closed: the `serve_purchase`
hook the buy command used to duck-type for on the keeper, the
`purchase_msg_*` reads on the container, and the seeding of those
attributes by the two counter typeclasses.
"""

from string import Formatter
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import override_settings
from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaCommandTest

import world.prototypes as prototypes
from commands.shop import CmdBuy
from world.shop.service import STYLES, hand_over

#: The four dishes the owner authored serve prose for -- Auntie Lin's
#: cart, and nothing else. Named here rather than discovered, so DELETING
#: a line is a failure and not a silently shorter sweep. The snailery's
#: two and the butcher's five are deliberately absent: see the module
#: docstring, and `test_a_dish_with_no_line_of_its_own_...` for the
#: control that they still cross the counter properly without one.
AUTHORED_DISHES = (
    "pessoa_noodles", "pessoa_bun", "pessoa_skewer", "pessoa_tea",
)

#: The only placeholders a serve line may use -- the three `hand_over`
#: fills. A fourth (`{buyer}`, say, copied over from the retired counter
#: lines) is a KeyError in the middle of a sale, at the exact moment a
#: player is handing over money.
SERVE_FIELDS = {"item", "target", "price"}

BOARD = STYLES["board"]["gesture"]
SHELF = STYLES["shelf"]["gesture"]


class _Dish:
    """The thing crossing the counter, as `hand_over` sees it: a key and
    an attribute bag. Nothing else of an item is touched, so nothing
    else is stood up here."""

    def __init__(self, key="a bowl of hand-pulled noodles", **attrs):
        self.key = key
        self.db = SimpleNamespace(**attrs)


def _keeper(handle="the lean man"):
    """Whoever's hands it passes through. The emote is captured off
    `execute_cmd` -- a keeper acts through real commands and nothing
    else, so that IS the player-visible surface."""
    by = MagicMock()
    by._address_handle = lambda patron: handle
    return by


def _emote(by):
    return by.execute_cmd.call_args.args[0]


class TestTheItemsOwnLineWins(TestCase):
    """(a)/(b)/(c) -- the whole precedence rule, at the one function both
    doors reach."""

    LADLE = ("ladles {item} up out of the broth pot and passes it across "
             "to {target}, {price} into the tin.")

    def test_a_dish_is_served_in_its_own_words(self):
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(serve_line=self.LADLE), 6, BOARD)
        self.assertEqual(
            _emote(by),
            "emote ladles a bowl of hand-pulled noodles up out of the "
            "broth pot and passes it across to the lean man, 6 into the "
            "tin.")

    def test_and_the_counters_gesture_is_not_used(self):
        """The control. Without it "the line printed" is also true of a
        version that prints BOTH, or the wrong one first."""
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(serve_line=self.LADLE), 6, BOARD)
        self.assertNotIn("on the board", _emote(by))
        self.assertNotIn("from the shelf", _emote(by))

    def test_the_placeholders_are_filled_from_the_sale(self):
        """`{item}` takes its article, `{target}` is the handle THIS
        keeper addresses the buyer by (not their name, which a stranger
        has not been told), `{price}` is what was paid."""
        by = _keeper(handle="the woman in the grease-black apron")
        hand_over(by, MagicMock(), _Dish(key="a jar of pickled snails",
                                        serve_line=self.LADLE), 5, BOARD)
        emote = _emote(by)
        self.assertIn("a jar of pickled snails", emote)
        self.assertIn("the woman in the grease-black apron", emote)
        self.assertIn("5 into the tin", emote)
        self.assertNotIn("{", emote)

    def test_a_dish_with_nothing_to_say_is_served_the_counters_way(self):
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(), 6, BOARD)
        self.assertEqual(
            _emote(by),
            "emote sets a bowl of hand-pulled noodles on the board and "
            "sweeps 6 into the till.")

    def test_and_with_no_counter_style_either_the_shelf_default(self):
        """`CmdBuy`'s keeper branch passes no style at all -- a typed
        `buy` at a plain shelf lands here."""
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(), 6)
        self.assertEqual(
            _emote(by),
            "emote plucks a bowl of hand-pulled noodles from the shelf, "
            "presses it into the lean man's hand, and sweeps 6 into the "
            "till.")

    def test_an_empty_serve_line_is_not_a_line(self):
        """A builder clearing the attribute leaves `""` behind as often
        as `None`. An empty gesture would emote nothing at all -- the
        item would cross the counter in silence."""
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(serve_line=""), 6, BOARD)
        self.assertEqual(
            _emote(by),
            "emote sets a bowl of hand-pulled noodles on the board and "
            "sweeps 6 into the till.")

    def test_and_neither_is_a_blank_one(self):
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(serve_line="   \n"), 6, BOARD)
        self.assertIn("on the board", _emote(by))

    def test_an_empty_line_with_no_style_still_reaches_the_shelf_default(self):
        by = _keeper()
        hand_over(by, MagicMock(), _Dish(serve_line=""), 6)
        self.assertIn("presses it into the lean man's hand", _emote(by))


class TestAMalformedLineIsNotAFailedSale(TestCase):
    """A line that will not render is a CONTENT bug, and content bugs do
    not get to happen in the middle of a sale.

    `{buyer}` is the realistic one: it is what the retired counter lines
    used, so anyone copying old prose onto a new dish writes it by
    reflex. The buyer has already paid and already holds the thing by the
    time `hand_over` speaks, so the only honest failure mode is to print
    the counter's own gesture and tell the log which dish to fix.
    """

    #: the retired counter lines' placeholder, on an item line
    WRONG_FIELD = "hands {item} to {buyer} for {price}."
    #: and a plain typo -- an unclosed brace is a ValueError, not a KeyError
    STRAY_BRACE = "hands {item} to {target} {"

    def _hand_over(self, line, gesture=SHELF):
        by = _keeper()
        with patch("evennia.utils.logger.log_warn") as warned:
            hand_over(by, MagicMock(), _Dish(serve_line=line), 6, gesture)
        return _emote(by), warned

    def test_an_unfillable_placeholder_falls_back_to_the_counter(self):
        emote, _ = self._hand_over(self.WRONG_FIELD)
        self.assertIn("plucks a bowl of hand-pulled noodles from the shelf",
                      emote)
        self.assertIn("presses it into the lean man's hand", emote)
        self.assertNotIn("{buyer}", emote)
        self.assertNotIn("{", emote)

    def test_and_it_says_in_the_log_which_dish_to_fix(self):
        """Silently swallowing it would leave authored prose that never
        prints and nobody ever hears about -- the exact shape of the
        defect this whole module exists to close."""
        _, warned = self._hand_over(self.WRONG_FIELD)
        warned.assert_called_once()
        self.assertIn("a bowl of hand-pulled noodles",
                      warned.call_args.args[0])

    def test_a_stray_brace_takes_the_same_door(self):
        emote, warned = self._hand_over(self.STRAY_BRACE)
        self.assertIn("plucks a bowl of hand-pulled noodles from the shelf",
                      emote)
        self.assertNotIn("{", emote)
        warned.assert_called_once()
        self.assertIn("a bowl of hand-pulled noodles",
                      warned.call_args.args[0])

    def test_the_counters_own_style_is_what_prints_not_the_shelf_default(self):
        """The control on the fallback: it is the gesture THIS counter
        passed, so a cart's sale does not suddenly read like a shop's."""
        emote, _ = self._hand_over(self.WRONG_FIELD, gesture=BOARD)
        self.assertEqual(
            emote,
            "emote sets a bowl of hand-pulled noodles on the board and "
            "sweeps 6 into the till.")

    def test_a_line_that_renders_is_not_logged_at_all(self):
        """And the instrument control: the warning is raised BY the
        malformed line, not by every sale."""
        by = _keeper()
        with patch("evennia.utils.logger.log_warn") as warned:
            hand_over(by, MagicMock(),
                      _Dish(serve_line="hands {item} to {target} for "
                                       "{price}."), 6, SHELF)
        self.assertIn("hands a bowl of hand-pulled noodles to the lean man",
                      _emote(by))
        warned.assert_not_called()


@override_settings(PROTOTYPE_MODULES=["world.prototypes"])
class TestARealDishSpawnedOffARealPrototype(BaseEvenniaTest):
    """The chain the authored prose actually travels: `attrs` on the
    prototype -> `db.serve_line` on the spawned object -> the emote.

    Tested with a real spawn because that middle step is the one a typo
    in the attrs tuple breaks, and a hand-built stand-in would never
    notice."""

    def _spawn(self, proto_key):
        from evennia.prototypes.spawner import spawn
        item = spawn(proto_key)[0]
        item.location = self.room1
        return item

    def test_the_prototype_attr_lands_on_the_object(self):
        self.assertEqual(
            self._spawn("pessoa_noodles").db.serve_line,
            "ladles {item} up out of the broth pot and passes it across "
            "to {target}, {price} into the till.")

    def test_and_the_bowl_is_ladled_when_it_is_handed_over(self):
        by = _keeper()
        hand_over(by, self.char1, self._spawn("pessoa_noodles"), 6, SHELF)
        self.assertEqual(
            _emote(by),
            "emote ladles a bowl of hand-pulled noodles up out of the "
            "broth pot and passes it across to the lean man, 6 into the "
            "till.")

    def test_a_bun_is_tonged_and_a_skewer_comes_off_the_cart(self):
        """Two more of Lin's four, so the pin is on the CONTENT reaching
        the emote and not on one lucky prototype."""
        by = _keeper()
        hand_over(by, self.char1, self._spawn("pessoa_bun"), 4, SHELF)
        self.assertIn("tongs a steamed bun into a paper twist", _emote(by))
        by = _keeper()
        hand_over(by, self.char1, self._spawn("pessoa_skewer"), 3, SHELF)
        self.assertIn("picks a charred skewer off the cart's edge",
                      _emote(by))

    def test_a_dish_with_no_line_of_its_own_takes_the_counters_gesture(self):
        """The other half of the rule, on a REAL dish rather than a
        stand-in. Only Lin's four are authored; the snailery's skewer is
        a dish in every other respect and carries nothing, so it must
        cross the counter on the counter's own words.

        Both facts are asserted together on purpose: "it used the shelf
        gesture" would also be true of a dish whose line was read and
        silently dropped, which is a different bug wearing this one's
        output."""
        skewer = self._spawn("snail_skewer")
        self.assertIsNone(skewer.db.serve_line)
        by = _keeper()
        hand_over(by, self.char1, skewer, 3, SHELF)
        self.assertEqual(
            _emote(by),
            "emote plucks a grilled snail skewer from the shelf, presses "
            "it into the lean man's hand, and sweeps 3 into the till.")

    def test_an_ordinary_item_still_falls_to_the_counter(self):
        """The control on the whole feature: only dishes carry a line,
        and everything else on every shelf must serve exactly as before."""
        by = _keeper()
        hand_over(by, self.char1, self._spawn("cigarette_pack_noir"), 6,
                  SHELF)
        self.assertIn("plucks", _emote(by))
        self.assertIn("presses it into the lean man's hand", _emote(by))


class _BuyAtACounter(EvenniaCommandTest):
    """A shelf with one LINED dish on it and a buyer with money.

    Driven through the real `buy` command: the defect this change closed
    was in WHICH BRANCH reads what, so calling the helpers directly would
    prove nothing about the door a player walks through.

    The dish is one of Lin's four, because these tests turn on an
    authored line reaching the room; a dish without one would pass the
    emote assertions off the shelf gesture and prove nothing.
    """

    def setUp(self):
        super().setUp()
        self.counter = create_object("typeclasses.shopkeeper.ShopContainer",
                                     key="counter", location=self.room1)
        self.counter.db.prototype_inventory = {"pessoa_noodles": 6}
        self.counter.db.is_infinite = True
        self.keeper = create_object("typeclasses.llm_npc.LLMNpc",
                                    key="Testkeeper", location=self.room1)
        self.char1.location = self.room1
        self.char1.tokens = 500

    def _buy(self, keeper):
        with patch("world.souls.posts.keeper_on_duty", return_value=keeper):
            return self.call(CmdBuy(), "noodles from counter")


class TestTheKeeperIsNotAskedHowToServe(_BuyAtACounter):
    """(d) -- the keeper-side hook is gone.

    `CmdBuy` used to duck-type: `serve = getattr(keeper, "serve_purchase",
    None)`, call it if callable, and only otherwise reach `hand_over`.
    That is a second door onto the same gesture, openable per-NPC, and
    the ruling closed it -- the ITEM decides, not whoever is holding it.
    A keeper still carrying the attribute (a stale soul blueprint, an
    old build script) must simply be ignored.
    """

    def test_a_keeper_carrying_the_old_hook_is_never_consulted(self):
        self.keeper.serve_purchase = MagicMock()
        with patch("world.shop.service.hand_over") as handed:
            self._buy(self.keeper)
        self.keeper.serve_purchase.assert_not_called()
        handed.assert_called_once()

    def test_the_hand_over_is_the_sale_itself(self):
        """And it is passed NO gesture, so the item's line (or the shelf
        default) is what decides -- the whole point of one door."""
        with patch("world.shop.service.hand_over") as handed:
            out = self._buy(self.keeper)
        args, kwargs = handed.call_args
        self.assertIs(args[0], self.keeper)
        self.assertIs(args[1], self.char1)
        self.assertEqual(args[3], 6)                  # the price paid
        self.assertEqual(len(args), 4)                # no style gesture
        self.assertEqual(kwargs, {})
        self.assertIn("You pay", out)

    def test_and_the_bowl_crosses_the_counter_in_its_own_words(self):
        """Unpatched, all the way to the emote the room reads."""
        with patch.object(type(self.keeper), "execute_cmd") as ran:
            self._buy(self.keeper)
        emotes = [call.args[0] for call in ran.call_args_list
                  if call.args and str(call.args[0]).startswith("emote ")]
        self.assertTrue(emotes, f"the keeper emoted nothing: "
                               f"{ran.call_args_list}")
        self.assertIn("ladles a bowl of hand-pulled noodles up out of the "
                      "broth pot", emotes[-1])
        self.assertIn("6 into the till", emotes[-1])
        self.assertNotIn("from the shelf", emotes[-1])


class TestAnUnmannedShelfIsPlainSelfService(_BuyAtACounter):
    """(e) -- the container's authored lines are not read any more.

    The counter is given both retired attributes here ON PURPOSE: live
    objects still carry them until build 165 sweeps them, and a sweep is
    not what makes this correct. The code must ignore them.
    """

    def setUp(self):
        super().setUp()
        self.counter.db.purchase_msg_buyer = "AUTHORED BUYER LINE {item}."
        self.counter.db.purchase_msg_room = "AUTHORED ROOM LINE {buyer}."

    def test_the_bait_is_really_on_the_counter(self):
        """The instrument control for the two tests below: they read as
        "the authored line did not print", which is also true of a
        counter that never carried one."""
        self.assertEqual(self.counter.db.purchase_msg_buyer,
                         "AUTHORED BUYER LINE {item}.")
        self.assertEqual(self.counter.db.purchase_msg_room,
                         "AUTHORED ROOM LINE {buyer}.")

    def test_the_buyer_reads_the_fixed_line(self):
        out = self._buy(None)
        self.assertIn("You purchase a bowl of hand-pulled noodles for 6", out)
        self.assertNotIn("AUTHORED", out)

    def test_the_room_reads_the_fixed_line_too(self):
        """Room broadcasts never reach a test observer (they are session
        -gated), so the template is read where it is handed to the
        identity renderer."""
        with patch("commands.shop.msg_room_identity") as told:
            self._buy(None)
        template = told.call_args.kwargs["template"]
        self.assertIn("purchases", template)
        self.assertNotIn("AUTHORED", template)

    def test_a_manned_sale_prints_neither_of_them(self):
        """The other half of the same guarantee: served in person, the
        self-service lines do not print at all."""
        out = self._buy(self.keeper)
        self.assertNotIn("You purchase", out)
        self.assertNotIn("AUTHORED", out)


class TestEveryAuthoredDishKnowsHowItIsServed(TestCase):
    """(f) -- the four lines, read straight out of `world.prototypes`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.by_key = {}
        for value in vars(prototypes).values():
            if isinstance(value, dict) and value.get("prototype_key"):
                cls.by_key[value["prototype_key"]] = value

    def _serve_line(self, proto_key):
        proto = self.by_key.get(proto_key)
        self.assertIsNotNone(proto, f"no prototype named {proto_key}")
        attrs = {row[0]: row[1] for row in (proto.get("attrs") or ())}
        line = attrs.get("serve_line")
        self.assertTrue(line, f"{proto_key} carries no serve_line")
        return line

    def test_every_dish_carries_one(self):
        for proto_key in AUTHORED_DISHES:
            self.assertIsInstance(self._serve_line(proto_key), str)

    def test_it_uses_only_the_placeholders_the_sale_can_fill(self):
        for proto_key in AUTHORED_DISHES:
            line = self._serve_line(proto_key)
            fields = {name for _, name, _, _ in Formatter().parse(line)
                      if name}
            self.assertLessEqual(fields, SERVE_FIELDS, proto_key)
            # a serve line that names neither the thing nor the person is
            # not a serve line
            self.assertIn("item", fields, proto_key)
            self.assertIn("target", fields, proto_key)

    def test_it_comes_out_with_no_holes_in_it(self):
        for proto_key in AUTHORED_DISHES:
            served = self._serve_line(proto_key).format(
                item="a bowl of hand-pulled noodles",
                target="the lean man", price=6)
            self.assertNotIn("{", served, proto_key)
            self.assertNotIn("}", served, proto_key)

    def test_it_reads_in_the_emote_voice(self):
        """`hand_over` prefixes the NPC, so the line continues a sentence
        that has already named them: "Auntie Lin ladles...". A capital,
        or a subject of its own, and the emote reads double."""
        for proto_key in AUTHORED_DISHES:
            line = self._serve_line(proto_key)
            first = line.split()[0].strip("'")
            self.assertTrue(first[:1].islower(),
                            f"{proto_key}: {line!r} does not open in the "
                            f"emote voice")
            self.assertNotIn(first, {"the", "a", "an", "he", "she", "they",
                                     "it", "you", "i", "and", "then"},
                             f"{proto_key}: {line!r} opens on {first!r}, "
                             f"not a verb")
            self.assertTrue(line.rstrip().endswith("."), proto_key)


class TestNoCounterSeedsRetiredPurchaseLines(BaseEvenniaTest):
    """(g) -- and nothing puts them back on new objects."""

    def _fresh(self, typeclass, key):
        return create_object(typeclass, key=key, location=self.room1)

    def test_a_new_shop_container_carries_neither(self):
        counter = self._fresh("typeclasses.shopkeeper.ShopContainer",
                              "new counter")
        self.assertFalse(counter.attributes.has("purchase_msg_buyer"))
        self.assertFalse(counter.attributes.has("purchase_msg_room"))

    def test_a_new_food_cart_carries_neither(self):
        cart = self._fresh("typeclasses.butcher.FoodCart", "new cart")
        self.assertFalse(cart.attributes.has("purchase_msg_buyer"))
        self.assertFalse(cart.attributes.has("purchase_msg_room"))

    def test_the_rest_of_the_seeding_is_untouched(self):
        """The control: `at_object_creation` still runs and still seeds
        everything else, so "no purchase lines" is not passing because
        the whole hook broke."""
        counter = self._fresh("typeclasses.shopkeeper.ShopContainer",
                              "control counter")
        self.assertEqual(counter.db.container_type, "shelf")
        self.assertTrue(counter.db.is_infinite)
        cart = self._fresh("typeclasses.butcher.FoodCart", "control cart")
        self.assertEqual(cart.db.container_type, "cart")
        self.assertEqual(cart.db.register, 0)
