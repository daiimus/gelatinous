# SHOP SYSTEM SPECIFICATION

The shop system lets characters buy items with tokens (₮). A shop is a physical container object, a `ShopContainer` (shelf, counter, rack, machine), that holds prototype keys and prices rather than objects, and spawns the item when it is bought. A counter can be bound to an NPC post: then a keeper on shift must be standing at it, and that keeper hands the item over in person. An unbound counter sells with nobody there. Shops are buy-only. Marketplaces with selling and haggling (Phase 2) and player-owned shops (Phase 3+) are described under "Unbuilt".

## The three tiers (owner ruling 2026-09-13)

> **Owner ruling 2026-09-13 -- three tiers (#3375 superseded).** Live today: (1) **Bars** are talk-only -- you speak to the tender (the bar's `order` is speech with the targeting done); they are not shop containers and `buy` cannot address them. (2) **Stores** (`ShopContainer`, shelf-styled; post-bound ones like Kaspar Pawn, Cinder & Leaf, Lin's noodle cart, and unbound self-service ones like Ramirez, the Armory, Gaia's, Community Thrift) keep the typed `buy`; a manned store also serves you when you speak to the keeper. The owner is **hesitant** to make stores talk-only -- "a bit alien for a MUD" -- so both doors stay there for now. (3) **Vending machines** (e.g. the battered cigarette machine, an unbound `ShopContainer`) are self-serve only. **Carts** (`FoodCart`, board-styled) move to the **bar model**: you talk to whoever is working the cart; `buy` is refused before any coin moves (`TAKES_BUY = False`). Principle 9 below ("no attendance check") describes the unbound tier only; post-bound fixtures are closed when nobody is on shift.

An unbound counter is called "the vending tier" (in `world/service.py` and `world/bar.py`). The five unstaffed vending-tier fixtures are the Ramirez counter, the Armory crates, Gaia's shelving, the cigarette machine and the Community Thrift rail. They are the only fixtures that self-serve.

## Design Philosophy

1. **Container-Based Architecture**: ShopContainers are standalone objects that manage their own inventory and pricing. No room configuration needed.
2. **Prototype Inventory**: Items stored as prototype keys, spawned on purchase to prevent database bloat.
3. **Holographic Merchants**: NPCs protected via `validate_attack_target()` method and AttributeProperties (`is_merchant`, `is_holographic`).
4. **Infinite Inventory Mode**: Shops operate in infinite mode by default - items never run out.
5. **AttributeProperty Currency**: All characters have `tokens` AttributeProperty (autocreate, default 0).
6. **Customizable Messaging**: Serve flavour lives on the item (`serve_line`, placeholders `{item}`, `{target}`, `{price}`). The self-service lines at an unmanned counter are fixed text.
7. **Data-Driven Display**: Can names derived from `aerosol_contents` attribute - extensible for future dynamic items.
8. **Buy-Only**: Fixed shops only support purchasing. Selling is Phase 2 with haggling.
9. **Self-Service Shops**: Merchants are decorative/atmospheric. Shops function without merchant presence (no attendance check). This holds for unbound counters only (see the ruling above).
10. **Builder-Friendly**: Simple @py commands to set up shops.
11. **Traditional Commands**: No EvMenu. At a store or vending machine, players use `buy <item> from <container>` and `look <container>`. At a manned store they can also say what they want to the keeper. At a cart, speaking is the only way (owner ruling 2026-09-13, above).

## ShopContainer

`ShopContainer` (`typeclasses/shopkeeper.py`) is a physical container that manages a prototype-based inventory, in infinite stock mode by default.

### Attributes

Set by `at_object_creation`:

| attribute | shape / default | meaning |
|---|---|---|
| `db.prototype_inventory` | `{prototype_key: price}` | what is sold, and for how much |
| `db.item_inventory` | `{prototype_key: quantity}` | stock, used only when stock is limited |
| `db.is_infinite` | `True` | infinite stock |
| `db.markup_percent` | `0` | markup used when `add_prototype` derives a price |
| `db.shop_name` | `"Shop"` | stored, but read by nothing: the `{shop}` token in the unmanned-shelf room line is the container's own display name, and the browse listing has no header |
| `db.container_type` | `"shelf"` | container type |

`at_object_creation` also adds the tag `till` (category `souls`), the index the souls tithe sweep reads.

Read, but never set at creation, so `None` on a plain shelf. This is why an unbound counter vends freely:

| attribute | meaning |
|---|---|
| `db.register` | the till; credited by the price on every sale when not `None` |
| `db.post_slots` | post binding, per shift |
| `db.post_keeper` | legacy single-keeper mirror |
| `db.post_closed_msg` | the refusal line when nobody is minding the counter |
| `db.owner`, `db.staff` | legacy bar allowlist; also binds |

A counter is bound if `post_slots` is set, or if `post_keeper`, `owner` or `staff` was ever assigned, even to someone since deleted (`world.souls.posts.is_bound`). A bound counter with nobody valid present is closed.

### Methods

- `add_prototype(prototype_key, price=None, quantity=None)` adds an item. With no price, the price is `calculate_shop_price` of the prototype's `value` attribute (default 10, through `get_prototype_value(prototype, "value", 10)`) and `markup_percent`. With a quantity, the shop switches to limited stock: `is_infinite` becomes `False` and `item_inventory` is filled. If the prototype does not exist, it does not raise: it logs "Prototype 'X' not found" and returns `False`.
- `remove_prototype(prototype_key)` drops an item from both inventories.
- `get_price(prototype_key)` returns the price.
- `is_in_stock(prototype_key)` checks availability: always True in infinite mode; with limited stock it gates on `item_inventory`.
- `purchase_item(buyer, prototype_key)` runs the sale (below).
- `get_display_name_for_prototype(prototype_key, prototype)` returns the display name (see "Item names").
- `get_browse_display(viewer)` builds the inventory listing as numbered `[001]`-style lines. It stores the number→prototype map on the **viewer's** `ndb.shop_number_map`, keyed to this container, so `buy 002 from shelf` works and one looker's numbering can never renumber another's. If the map lived on the container, a stock change between two looks could hand a buyer the wrong dish (#2470; the reasoning is in the comment in `get_browse_display`).
- `return_appearance(looker)` shows the inventory on look.
- `_off_shift_deflection(buyer)`: when a post-bound counter has no on-duty keeper but one of its OWN off-shift keepers is standing there, that keeper says so out loud and names whoever holds the shift, and that line becomes the refusal the buyer sees.

The limited stock mode is what the food cart runs on entirely.

### Purchase flow (`purchase_item`)

1. If the counter is bound to a post and no keeper on shift is present, refuse. `any_keeper_present` is `keeper_on_duty(fixture) is not None`: present AND on shift (#2146). One of the counter's own off-shift keepers who is present says why (`_off_shift_deflection`); otherwise the refusal is `db.post_closed_msg`, or the default "Nobody's minding the counter…" line. So a post-bound counter refuses sales while its keeper is dead or absent.
2. Refuse if the item is not sold here ("That item isn't sold here."), or is out of stock ("That item is out of stock.").
3. Refuse if the buyer has fewer tokens than the price ("You need N₮ more to afford that.").
4. Spawn the item, move it to the buyer, and put it in a free hand if there is one (`FoodCart.purchase_item`, `typeclasses/butcher.py`, overrides this to set the dish back on its board). If the spawn fails the buyer reads "The item couldn't be retrieved. Contact an admin." or "Something went wrong. Contact an admin."
5. Deduct the tokens (`buyer.tokens -= price`) and record the payment in the souls coin audit as a `purchase` (#2698).
6. Break the buyer's hiding (`break_stealth`, #3763).
7. Credit `db.register` when the counter keeps one.
8. Decrement `item_inventory` when stock is limited.
9. Return `(True, item)`.

### Hands

A bought item is moved to the buyer quietly, then wielded into the first free hand. Hand placement is best-effort: when both hands are full the item stays in inventory, with no message. `FoodCart.purchase_item` puts the dish back on the cart's board instead.

### Buying breaks hiding

Every completed sale breaks the buyer's stealth, whether by the typed `buy` or a spoken order. Owner, 2026-10-24, #3763: "You have to come out of hiding if you're buying something". The break happens inside `purchase_item`, so both doors agree.

## Currency

`Character.tokens` (`typeclasses/characters.py`) is an `AttributeProperty(0, category="shop", autocreate=True)`. Every character has it, new or existing, defaulting to 0, with no initialisation in `at_object_creation`; it persists across restarts. It is read and written directly: `char.tokens = 100`, `char.tokens -= 50`.

Helpers in `world/shop/utils.py`:

- `format_currency(amount)` gives `"150₮"`, and `"0₮"` for a free item.
- `parse_currency(text)` reads `"50"`, `"50₮"`, `"50 tokens"`, `"50 ticks"`, `"50 tabs"`, `"50 kennys"` (singular forms too) as 50, and returns `None` when the text is not a number.
- `get_prototype_value(prototype, attr_name, default=None)` returns the raw value of `attr_name` from a prototype's `attrs` list, or `default`. No int conversion.
- `calculate_shop_price(base_value, markup_percent=0)` returns the base value plus `markup_percent` of it. `add_prototype` uses it when no price is given.

Do not use `validate_purchase`, `deduct_tokens` or `add_tokens` in the same module: nothing calls them, and they read and write `db.tokens`, which no part of the game reads. The wallet is the `Character.tokens` property (category `"shop"`).

### Currency lore

The **Token (₮)** is standard colonial scrip used throughout Gelatinous. Street slang includes "ticks," "tabs," and "kennys." `parse_currency` accepts all three as input; display always uses the ₮ symbol.

- **"Tabs"** - From "running a tab," implies debt and company store economics
- **"Kennys"** - Origin unknown, possibly from a famous debtor or colonial administrator

Example NPC dialogue:

```
"That medkit? 150 ticks, no haggling."
"I need at least 30 tabs for this junk."
"You got the kennys for it, or you just window shopping?"
```

## Item names and pricing

`get_display_name_for_prototype` returns `"can of <aerosol_contents>"` when the prototype carries an `aerosol_contents` attribute, and otherwise the prototype's `key`. Display names are data-driven, with no hardcoded item names.

The can prototypes' keys are the shown names, "can of spraypaint" and "can of solvent" (#3783), so the core search finds a can by what the player sees. `get_display_name_for_prototype` still builds the same string from `aerosol_contents`.

Any prototype in `world/prototypes.py` can be sold. Pricing uses a prototype's `value` attribute when it carries one. `SPRAYPAINT_CAN` (typeclass `typeclasses.items.SprayCanItem`) carries none, so `add_prototype("SPRAYPAINT_CAN")` with no explicit price prices it at **10**. The solvent can is `SOLVENT_CAN`; there is no `SPRAY_SOLVENT` prototype, and no machete prototype of any casing.

## Holographic merchants

### Flags

`Character` (`typeclasses/characters.py`) carries `is_merchant` and `is_holographic`, both `AttributeProperty(False, category="shop", autocreate=True)`.

### Combat protection

`Character.validate_attack_target()` takes no arguments. It returns `None` when the character can be attacked, or an error string when it cannot (`is_holographic` is True: "A holographic merchant cannot be attacked - target validation failed"). It sends no messages itself, and the attacker never sees that string.

`CmdAttack.func` (`commands/combat/core_actions.py`), after resolving the target, calls `target.validate_attack_target()`. If that returns an error and the target is holographic:

- the attacker reads `|yYour attack passes through <them>'s holographic form with a shimmer of static.|n`, where `<them>` comes from `get_display_name_safe(target, caller)`, so it renders through the attacker's own recognition and never prints the raw key;
- each observer reads, through `msg_room_identity`, "<actor>'s attack passes through <target>'s flickering projection.";
- the attack stops before the combat handler is involved.

Any other error gives "You cannot attack <name>."

### Prototypes

`HOLOGRAPHIC_MERCHANT` (`world/prototypes.py`) has no `prototype_parent`:

```python
HOLOGRAPHIC_MERCHANT = {
    "key": "holographic merchant",
    "typeclass": "typeclasses.characters.Character",
    "desc": "A shimmering holographic projection of a merchant. ...",
    "attrs": [
        ("is_merchant", True),
        ("is_holographic", True, "shop"),
        ("merchant_greeting", "Welcome to the shop. Browse my wares."),
    ],
    "locks": "get:false();puppet:false()",
}
```

The `"shop"` category on `is_holographic` is required: `Character.is_holographic` is an `AttributeProperty(category="shop")`, and the combat guard reads that property, so a flag stored without the category is not seen and the hologram can be swung at (#3130). Write it `("is_holographic", True, "shop")`, never as a two-tuple.

Specific merchants inherit from `HOLOGRAPHIC_MERCHANT`:

- `ARMORY_MERCHANT` - Gunther the Armorer (weapons and armor)
- `GENERAL_MERCHANT` - Sal the Supplier (general supplies)
- `MEDIC_MERCHANT` - Dr. Voss (medical supplies)
- `CORNERSTORE_MERCHANT` - Juan Sanchez (general goods)

Spawn one with `@spawn CORNERSTORE_MERCHANT`; it inherits the categorised flag. There is no `BASE_NPC` prototype.

The holographic merchant prototypes are decoration: they stand no post, and no sale depends on them. The keepers who actually sell are NPCs standing a post (`world.souls.posts`; see `NPC_POSTS_AND_REINCARNATION_SPEC.md`), with the selling competence registered per role in `world/shop/service.py`.

## The buy command

`CmdBuy` (`commands/shop.py`, in `CharacterCmdSet`, `commands/default_cmdsets.py`).

### Syntax

```
buy <item> from <container>
buy spraypaint from shop
buy can of spraypaint from shop
buy solvent from shop
```

`purchase` is an alias. `buy 002 from shelf` (also `2`, `#2` or `#002`) buys by the number in your own last look at that counter. Only the last " from " splits the item from the container, so `buy letter from mother from shelf` works.

### Flow

1. Refuse if the buyer is channeling (`refuse_if_channeling`, #3376).
2. Parse `buy <item> from <container>`; find the container in the room and verify it is a `ShopContainer`.
3. Refuse if the fixture does not take the typed door (`TAKES_BUY = False`: `FoodCart` follows the bar model, #3375). The refusal names the keeper if one is working it.
4. `container._find_prototype_key(item_name)`: the buyer's own `[001]` numbering, then an exact or fuzzy display-name match (using `get_display_name_for_prototype`, so cans match). A fuzzy match is the search term inside the display name, or the display name inside the search term.
5. `container.purchase_item(caller, prototype_key)` spawns the item, deducts tokens, credits the till and places the item. Hand placement happens inside `purchase_item`, or the fixture's override lands it on the counter or board.
6. **Manned counter.** `_find_keeper` finds the post's on-duty keeper (`world.souls.posts.keeper_on_duty`), who must be in the buyer's room. The buyer is told `You pay <price>.` and the keeper emotes the handover through `world.shop.service.hand_over(keeper, caller, item, price)`: the item's `serve_line` if it has one, else the shelf gesture (see "Serve flavour"). The command then returns: no self-service lines, and no `_notify_merchant`, whose "bought <item> off the shelf" notice would contradict the keeper's own emote (and, for an LLM keeper, write that contradiction into the observation buffer their next turn reads).
7. **Unmanned shelf.** The two fixed self-service lines, which cannot be overridden: `"You purchase {item} for {price}."` to the buyer, and `"{buyer} purchases {item} from {shop}."` to the room through `msg_room_identity` (per-observer, so `{buyer}` resolves to whatever each onlooker recognises). Then `_notify_merchant()`.

A manned counter is never self-service. The two branches are exhaustive: with a keeper on duty in the room the handover is emoted and the command returns; only the no-keeper branch prints the self-service lines. With no keeper on duty, a post-bound counter has already refused the sale in `purchase_item`, so the self-service branch runs only at unbound counters.

## 8. Serve flavour: `serve_line` on the item

### Addendum (2026-09-18) — the counter's purchase lines are retired (#3413)

**Owner ruling, #3413, 2026-09-18:** *"custom serve messages are awesome, but should probably live on the food/drink/consumable not the counter"*, and, on the counter attributes themselves, *"retirement makes sense. We should standardize"*.

Serve flavour was first written onto the counter, as two authored attributes, `purchase_msg_buyer` and `purchase_msg_room`. The ruling above retired them in favour of one optional line on the item. Nothing seeds, authors or reads them (build 165, `scripts/builds/165_retire_counter_purchase_lines.py`, strips them from existing objects; it is idempotent and safe to re-run).

**Why the counter is the wrong place.** The counter's lines could never print on a staffed counter: with a keeper on duty the command emotes the handover and returns, and with nobody on duty a post-bound counter refuses the sale, on or off shift. And the same bowl is ladled the same way whoever is standing there, while one counter sells four different dishes.

### The standard (one door for serve flavour)

1. A manned counter is never self-service. The sale ends in `world.shop.service.hand_over(by, patron, item, price, gesture=None)`, which emotes in the KEEPER's voice.
2. `hand_over` prefers, in order:
   - the item's own **`serve_line`** (an authored non-empty string on `item.db.serve_line`),
   - else the `gesture` the caller passed: the counter STYLE's gesture from `STYLES` in `world/shop/service.py` (`shelf` presses it into your hand and sweeps the price into the till; `board` "sets {item} on the board and sweeps {price} into the till"),
   - else `STYLES["shelf"]["gesture"]`.
3. A consumable prototype may carry **ONE optional `serve_line`**. That is the whole customisation surface. There is no per-keeper `serve_purchase` hook: `CmdBuy` never consults one, and no keeper defines one (a test in `world/tests/test_a_bowl_knows_how_it_is_served.py` holds this shut). Serve flavour comes from exactly one place.

### Both doors reach it

| door | call | gesture passed |
|---|---|---|
| typed `buy … from …` at a manned counter (`commands/shop.py`) | `hand_over(keeper, caller, item, price)` | none → shelf default |
| spoken order at a shelf-styled counter (`serve_from_shelf` → `_fulfil_from_shelf`) | `hand_over(by, patron, item, price, STYLES["shelf"]["gesture"])` | shelf |
| spoken order at a board-styled cart (`serve_from_board_cart`) | same, with `STYLES["board"]["gesture"]` | board |

In all three the item's `serve_line` wins when it has one.

### Writing a `serve_line`

It is an **emote**, in the keeper's voice, run as `emote <line>`. So it starts mid-sentence, after the actor's name, and never names the keeper; the emote supplies the name.

```python
("serve_line", "ladles {item} up out of the broth pot and passes it across "
               "to {target}, {price} into the till."),
```

```python
# Same thing on a live object (owner's example):
@py dish.db.serve_line = "ladles {item} up and passes it across to {target}, {price} into the tin."
```

Placeholders, exactly three, supplied by `hand_over`:

- `{item}`: `with_article(item.key)` ("a bowl of noodles")
- `{target}`: the keeper's own address handle for the buyer (perceived identity: "the tall woman", a known name); falls back to `"the customer"`
- `{price}`: the **bare integer** token count. It is NOT run through `format_currency`, so there is no `₮` glyph: write "`{price} into the tin`", not a line where a naked number has to stand on its own.

Two cautions:

- Any OTHER `{placeholder}`, or a stray brace, fails to render, but this is caught. `hand_over` wraps the `.format()` in `try/except (KeyError, IndexError, ValueError)`, so a malformed line never raises after the buyer has paid. The counter style's gesture prints in its place, and the failure is logged once per sale with `logger.log_warn` ("shop: serve_line on … could not be rendered"), which lands in the container log. The sale always completes; the authored prose is lost silently unless you read the log. Stick to the three.
- Only a non-empty string counts as authored; anything else falls through to the style gesture.

### Which items carry a line

**Four dishes carry lines** (`world/prototypes.py`): `pessoa_noodles`, `pessoa_bun`, `pessoa_skewer`, `pessoa_tea`, all four Auntie Lin's, sold over her shelf-styled `ShopContainer`. Nothing else carries one, and the two obvious candidates deliberately do not:

- The **Escallier snailery is not a shop counter**. Build 137 (#2342) turned counter #8119 into a `typeclasses.bar.BarCounter` with no prototype inventory; `snail_skewer`, `snail_jar` and the kuro are plated off the bar's board using the `craft` strings in `SNAILERY_MENU` (`scripts/builds/137_the_snailery_serves.py`). That path never reaches `hand_over`, so a `serve_line` there would be dead prose. Those dishes carry none.
- The **butcher's five dishes** (`world.food.FOOD_RECIPES`: `rat_tail_stew`, `grilled_rat_chops`, `roast_rat_haunch`, `butchers_breakfast`, `mystery_skewer`) carry none either. The board style's gesture already says exactly what a board line would say, so all five take it, and the cart speaks with one voice instead of some dishes sounding different from the rest.

Everything else on every shelf serves with the counter style's gesture, which is the default by design: a `serve_line` is for a thing with a distinctive handover, not for stock.

**Bar drinks and plated bar dishes are not affected.** The bar's serve path (`world/bar.py` `serve_from_board` → the recipe's `craft` string) does not go through `hand_over`, so a `serve_line` has no effect there. No prototype is served by both paths, so none has to keep two voices in step. See `BARS_AND_RECIPES_SPEC.md` §7.2.

**Self-service lines are not customisable.** The unmanned-shelf branch prints fixed text (`"You purchase {item} for {price}."` / `"{buyer} purchases {item} from {shop}."`). A vending-tier shelf has nobody to have a manner, so there is nothing to author.

**Typed `buy` at a board-styled counter.** `CmdBuy`'s keeper branch passes no style. What that means for a line-less item at a board-styled counter is open; see "Not decided".

## Keepers and spoken orders

(#1293–#1298, #2350/#2378.)

- **Whoever stands the counter sells.** Spoken orders resolve deterministically against the counter's real shelf and run `purchase_item`. The selling code is keyed by `post_role` in `world/shop/service.py` (`serve_from_shelf` / `match_from_shelf`, registered for the shelf roles through `world/service.py`). The model (an LLM keeper) supplies voice and memory, never prices.
- **Keeper-served buy.** A manned counter is never self-service: the `buy` command routes the handover through the keeper's serve emote (see "The buy command").
- **No keeper, no commerce.** A post-bound counter refuses sales while its keeper is dead or absent; unbound counters vend freely, which IS the vending-machine tier by construction.
- **Shelf grounding.** The persona card (`world/llm/prompt.py` `render_persona`) carries the counter's complete stock and token prices, with anti-invention and no-haggling clauses, and "never narrate a sale or a handover yourself". Keeper personality comes from souls and blueprints (`world/npcs/blueprints.py`).
- **Hand delivery and tills.** See the purchase flow above.
- **No selling to shops.** Sell/pawn (P3) explicitly rejected, 2026-07-25 (#1293–#1298): "not ready for a pawn economy."

At an unmanned shelf, `_notify_merchant` tells a merchant in the room that the buyer "bought <item> off the shelf"; for an LLM keeper the notice goes into the observation buffer their next turn reads.

## Builder workflow

### Setting up a shop

```
@create/drop shop:typeclasses.shopkeeper.ShopContainer
@desc shop = A well-stocked shop shelf displaying various items.
@py shop.db.shop_name = "Juan's Corner Market"
@py shop.db.container_type = "shelf"
```

`shop_name` is stored but read by nothing (see "Attributes").

### Adding items

```
@py shop.add_prototype("SPRAYPAINT_CAN", 50)
@py shop.add_prototype("SOLVENT_CAN", 30)
@py shop.add_prototype("FRAG_GRENADE", 200)
@py shop.db.prototype_inventory
```

Use real prototype keys. `add_prototype` does not raise on a key that is not a prototype: it logs and returns `False`, and the shop is built without that item, in silence. The live general shelf, `GENERAL_SHELF` (`world/prototypes.py`), stocks `"SPRAYPAINT_CAN": 25, "SOLVENT_CAN": 30`. Pass a quantity (`add_prototype(key, price, quantity=N)`) for limited stock.

### Giving a dish its own serve line (optional)

On the prototype (preferred; every spawn gets it):

```python
("serve_line", "ladles {item} up and passes it across to {target}, {price} into the tin."),
```

Or on a single live object:

```
@py dish = me.search("bowl of noodles")
@py dish.db.serve_line = "ladles {item} up and passes it across to {target}, {price} into the tin."
```

Placeholders: `{item}` `{target}` `{price}`, and only those three. It is an emote in the keeper's voice, so it follows their name and never spells it. `{price}` is the bare number, no ₮. Never put serve flavour on the shop.

### Spawning a holographic merchant (optional)

```
@spawn CORNERSTORE_MERCHANT
```

The merchant is invulnerable to attacks. A hand-written spawn dict must spell the flag `("is_holographic", True, "shop")`; there is no `BASE_NPC` prototype to parent from.

### Tokens

```
@py me.tokens = 500
@py me.tokens
@py me.tokens += 500
@py me.tokens -= 100
@py me.tokens >= 50
```

### Testing a shop

```
look shop
buy spraypaint from shop
buy can of spraypaint from shop
buy solvent from shop
@spawn HOLOGRAPHIC_MERCHANT
attack merchant
```

The attack passes through with the shimmer-of-static line under "Combat protection", rendered through the attacker's own recognition.

## Unbuilt

Everything below is design that was never built. The original design is kept for reference and potential future development; where it disagrees with the rules above, the rules above are the game.

### Merchant attendance (overturned intention)

The original design made shops self-service with merchants as decoration, and gated attendance on a room-level `allows_unmanned_sales` flag. Instead a post-bound counter refuses every sale while no keeper stands the running shift (#2146, `ShopContainer.purchase_item`), and only unbound counters are self-service (owner ruling 2026-09-13, above).

### Merchant template system — 📋 UNBUILT

The game uses ordinary Evennia prototypes (`HOLOGRAPHIC_MERCHANT` and its children) instead. The design: a `MerchantTemplate` is a reusable blueprint for spawning shop NPCs, holding appearance (name, description, gender), personality (greeting, farewell, combat taunt), G.R.I.M. stats for future haggling (defaults grit 1, resonance 1, intellect 2 — merchants tend to be clever — motorics 1) and an `is_holographic` flag. A template also records which room the merchant works in. Defaults: name "Generic Merchant", description "A merchant stands here.", gender neutral, greeting "Welcome to my shop!", farewell "Come back soon!", combat taunt "You'll regret that!" (none of the example templates overrides the taunt). It solves respawning (a dead merchant is replaced by an identical one, narratively "the same person") and consistency (several shops share an archetype). The flow:

1. A builder creates a template (for example "weapons_dealer").
2. The room stores the template key in its shop config.
3. The room spawns a regular Character from the template, with merchant flags.
4. When that character dies, the room waits 5 minutes and spawns a new one from the same template.

Example templates: **Jaxxon Vale** (weapons dealer, male, "A grizzled weapons dealer with cybernetic eyes and scarred hands.", greeting "Looking for something with stopping power?", farewell "Stay dangerous out there."); **Mira Chen** (general store, female, resonance 2, "A friendly shopkeeper with a warm smile and quick wit.", "Welcome! Looking for supplies?", "Come back anytime!"); **Forge-Pattern Delta** (armor smith, holographic and so invulnerable, neutral, "A holographic construct resembling a heavily armored smith. Pixels flicker at the edges.", "PROTECTION PROTOCOLS AVAILABLE.", "STAY SHIELDED.").

### Room-based shops — 📋 UNBUILT

The design made the room itself the shop: all shop data on the room, merchants just Characters standing there who could be killed, swapped or absent. Its benefits: the shop persists when the merchant is dead, several merchants can work it, player shops need no merchant, merchants swap for events or day/night, no merchant subclasses. `setup_as_shop` would store a `shop_config` holding the prototype list, an `upsell_factor` (default 1.2; a room that is not a shop reports 1.0), the merchant template, `merchant_respawn_delay` (default 300 s, 5 minutes), the current merchant, `allows_unmanned_sales` (default False), `shop_name` (default "<room> Shop") and `greeting` (default "Welcome!"), and tag the room `shop` (category `shop_system`). On merchant death the room clears the reference, schedules the respawn and tells the room "<merchant> has fallen! Another will arrive in N minutes...".

### Character merchant flags and respawn — 📋 UNBUILT

The design stored `is_merchant`, `shop_room` and `template_key` on the character; on death a merchant would notify its shop room to handle the respawn. A holographic merchant attacked would show a crackle-of-static line to the attacker ("Your attack passes through <merchant>'s holographic form with a crackle of static!"), tell the room "<attacker>'s attack disrupts <merchant>'s projection, causing visible glitches.", and answer the attacker with one random line:

- "Violence is so... analog. Can I interest you in a purchase instead?"
- "I'm incorporeal. You're wasting your energy."
- "My projection is backed up. This is futile."
- "Cute. Now, about those prices..."

The design's `validate_attack_target(attacker)` returned a `(can_attack, message)` pair. Do not add that form or its CmdAttack block: `CmdAttack.func` already calls `validate_attack_target()` with no arguments, as described under "Combat protection".

### Original shop container — 📋 UNBUILT

The design's container held a list of prototype keys rather than a price map, priced each item at `int(base value × the room's upsell factor)` (the look shows 1.2 when the room is not a shop; a purchase there is refused), and refused a sale in a room that is not a shop ("This container is not in a functioning shop."). Its look showed an "Items for sale:" table (Item, Price, Description cut to 50 characters), "The <type> is empty." when empty, and "Use buy <item> from <container> to purchase.". It matched by exact key or alias, then by partial key. Refusals: "'<item>' is not available in the <container>."; "You need <price> but only have <balance>."; "Item spawning failed. Contact an administrator." or "Purchase error: <error>" when the spawn fails. The item went to the right hand, then the left; a character without hands got "<item> goes to your inventory." On success: "You buy <item> for <price>."; with both hands full the item went to inventory with "Your hands are full. <item> goes to your inventory." (The game's container is the one under "ShopContainer"; its full-hands case prints nothing.) Builder example: a `weapons_shelf` with `container_type` "weapons rack".

### Vending machine — 📋 UNBUILT (not decided)

No `VendingMachine` class exists. Today a vending machine is an unbound `ShopContainer` (owner ruling 2026-09-13 at the top of this document), for example the battered cigarette machine, looked at and bought from like any shelf. Buying by slot code (`A1`) is 📋 UNBUILT (not decided).

The design: a specialised ShopContainer that runs with no merchant, like a real vending machine: insert money, press button, get item. For street corners with basic supplies (bandages, stimpaks), safe zones with emergency gear, high-tech kiosks, places where a merchant is impractical. Its default description is "An automated vending machine with a digital display." and its container type "vending machine".

- Slots (A1, B2, C3 …) map to prototype keys (`slot_inventory`).
- Price is base value × `price_multiplier`, rounded down to a whole token (default 1.5: a BANDAGE worth 10 sells for 15).
- Stock is unlimited by default (`unlimited_stock`); with limited stock each slot has a quantity (`stock_quantities`).
- A machine can be out of order (`is_operational`); its message defaults to "** OUT OF ORDER - CONTACT MAINTENANCE **", and a look then shows only that.
- Optional `brand_name` and `interface_color` theme the display.
- Look shows a table of Slot, Item, Price, Stock (∞, a number, or SOLD OUT), slots sorted, a missing prototype shown as ERROR, and "Use buy <slot> from <machine> (e.g., 'buy A1 from machine')".
- A purchase takes a slot code (tried first, any case) or an exact item name (any case). Checks run in this order: operational, slot/name, stock, funds; the item is spawned before the tokens are taken, and limited stock is decremented after. Refusals: the out-of-order message; "'<item>' is not available in this machine."; "Slot <slot> is sold out."; "Item not found in database." (prototype missing); "Insufficient funds. Need <price>, have <tokens>."; "Vending error. Contact an administrator." or "Vending error: <error>" when the spawn fails. On success: "You insert <price>. <item> drops from slot <slot>."
- `restock_slot(slot, quantity)` adds stock ("Slot <slot> restocked: <old> → <new>"; "Slot <slot> does not exist."; "Machine has unlimited stock - restocking not needed.").
- `set_operational(on, message=None)` switches the machine; the room reads "<machine> hums back to life." or "<machine> displays: <message>".

Example machines: a medical machine "MediCorp AutoVend" (red; BANDAGE, PAINKILLER, BLOOD_BAG, SPLINT, STIMPAK; limited stock 10/15/5/8/3; multiplier 1.3); an ammo dispenser "ArmaStock 3000" (yellow; PISTOL_AMMO, RIFLE_AMMO, SHOTGUN_SHELLS, FRAG_GRENADE; unlimited; multiplier 2.0, expensive but convenient); a snack machine "Snack-O-Matic" (cyan; ENERGY_BAR, PROTEIN_SHAKE, SODA, CHIPS, CANDY; multiplier 1.1).

### Original buy command — 📋 UNBUILT

The design's `buy` (help category Economy) also took a bare `buy <item>` and searched every shop container in the room ("There are no shops here."; "'<item>' is not for sale here."). With no item it answered "Usage: buy <item> [from <container>]"; a named source that is not a shop container gave "<container> is not a shop container." A vending machine bypassed all shop checks. Otherwise it required the room to be a shop ("You need to be in a shop to buy items.") and, unless the shop allowed unmanned sales, a merchant in the room ("The shop appears to be closed. No merchant is present."). The room read "<buyer> purchases <item> from the <container>.". `buy_from_room` and `get_prototype_by_name` have no code. The game's command is the one under "The buy command".

### Error handling and limits — 📋 UNBUILT (not decided)

None of these constants or validation helpers exist, nor do `Room.spawn_merchant`, `can_afford` or `ShopContainer.at_object_delete`. The refusals a buyer reads today are those in the purchase flow above.

| constant | value | meaning |
|---|---|---|
| `MAX_SINGLE_PURCHASE` | 1000000 | maximum credits in a single transaction |
| `MIN_ITEM_VALUE` | 1 | minimum item value (can't be worthless) |
| `MAX_STACK_SIZE` | 999 | maximum stackable item quantity |
| `MAX_CONTAINERS_PER_SHOP` | 20 | prevent container spam |
| `MAX_ITEMS_PER_CONTAINER` | 100 | prevent prototype list bloat |
| `MIN_UPSELL_FACTOR` | 0.01 | can't sell for less than 1% of value |
| `MAX_UPSELL_FACTOR` | 100.0 | can't charge more than 100× value |
| `MIN_RESPAWN_DELAY` | 60 | minimum seconds before respawn (1 minute) |
| `MAX_RESPAWN_DELAY` | 86400 | maximum seconds before respawn (24 hours) |
| `DEFAULT_RESPAWN_DELAY` | 300 | default respawn delay (5 minutes) |
| `MAX_VENDING_SLOTS` | 100 | maximum slots in a vending machine (A1-J10) |

Error cases the design handles:

- **Invalid prototype key**: the buyer reads "Error: Item prototype '<key>' not found. Please report this to staff." and the error is logged.
- **Corrupted merchant template**: no template configured, or an invalid one, logs a warning or error and spawns nothing.
- **Several merchants in one shop**: log a warning, keep the first, delete the duplicates.
- **Insufficient credits**: "You can't afford that. You need <price> but only have <credits>."
- **Item won't fit in hands**: put it in the first empty hand, else inventory with "Your hands are full. <item> is in your inventory."
- **Container deleted while the shop is active**: log a warning; the shop keeps working with its other containers.
- **Merchant death during a transaction**: a sell with the merchant absent leaves the item on the counter. (For `buy`, a post-bound counter refuses the sale unless a keeper on the running shift is present; an unbound counter sells with nobody there.)
- **Holographic merchant attack**: as under "Combat protection".
- **Validation**: a shop config needs a `shop_name`, an upsell factor and respawn delay within the limits above; a container's prototype list may hold at most 100 keys, each a real prototype.

### Phase 2: marketplaces — 📋 UNBUILT (#302)

No `CmdSell`, `CmdHaggle` or `MarketplaceRoom` exists.

- **Procedural mazes**: marketplace rooms that reconfigure on timers (`reconfigure_interval`, 1 hour), managed by a `MarketplaceMaze` that generates layouts and anchors them.
- **Grid integration**: marketplaces auto-connect to key anchor points on the main grid (`anchor_point`). Each room belongs to a zone (for example `central_bazaar`) and lists the vendor templates that can spawn there and the item prototypes available.
- **Vendor spawning** in marketplace zones.
- **Haggling** for both buying AND selling: `haggle <item> from <vendor>`, `haggle <price> for <item> from <vendor>`, an opposed roll of Intellect against the vendor's Intellect (`base_haggle_difficulty` 15, an Intellect check).
- **Dynamic pricing**: supply/demand based on database queries and rarity. Prototype `value` attributes feed this future dynamic pricing.
- **Selling, marketplace-only**: `sell <item>`, `sell <item> to <vendor>`, with haggling based on Intellect. Fixed shops stay buy-only: selling belongs with the haggling mechanics and dynamic pricing.
- **Browse**: `browse` explores stalls and vendors; `browse <category>` searches for item types. All shop commands still work once you find a stall.

### Phase 3+ — 📋 UNBUILT

1. **Player-owned shops**: lease systems, revenue collection
2. **Economic simulation**: supply/demand tracking, price volatility
3. **Crafting**: crafting commissions; merchants craft custom items
4. **Broker systems**
5. **Shop upgrades**: expand inventory, improve prices
6. **Shop events**: sales, limited-time items
7. **Black market**: illegal items with risk mechanics
8. **Reputation system**: discounts for loyal customers
9. **Auction houses**: timed bidding on rare items

## Not decided

- **Typed `buy` at a board-styled counter** (open). `CmdBuy`'s keeper branch passes no style, so an item with **no** `serve_line`, bought with the typed command at a **board-styled** counter, would be handed over with the SHELF gesture, while the same keeper serving the same dish by spoken order uses the BOARD gesture. Nothing masks it: every dish on the only board-styled counter is line-less, and Lin's four lines sit on a shelf-styled counter, where the command's default and the post's style are the same anyway. It stays latent only because the only board-styled role is `butcher`, whose counter is a `FoodCart` with `TAKES_BUY = False`, so the typed door is refused there before any coin moves (#3375). It becomes reachable the moment a board-styled keeper stands a plain `ShopContainer`. The fix, when it is wanted, is for `CmdBuy` to read the keeper's post style rather than defaulting.
- Whether to build a slot-code vending machine, and the error-handling limits, are also not decided; see "Vending machine" and "Error handling and limits" under Unbuilt.

## Related documents

- `NPC_POSTS_AND_REINCARNATION_SPEC.md`: posts, shifts and the keepers who stand counters.
- `BARS_AND_RECIPES_SPEC.md` §7.2: the bar's serve path and `craft` prose.

Code: `typeclasses/shopkeeper.py` (`ShopContainer`), `typeclasses/butcher.py` (`FoodCart`), `commands/shop.py` (`CmdBuy`), `world/shop/service.py` (`hand_over`, `STYLES`, spoken-order selling), `world/shop/utils.py` (currency helpers), `world/souls/posts.py` (`is_bound`, `keeper_on_duty`, `any_keeper_present`), `typeclasses/characters.py` (`tokens`, `is_merchant`, `is_holographic`, `validate_attack_target`), `world/prototypes.py` (merchant and item prototypes).
