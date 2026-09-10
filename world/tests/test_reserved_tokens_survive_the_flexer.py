"""`{color}` reaches the layer that owns it (#2722).

The longdesc flexer promised twice -- in the module header and in the
function's own Returns block -- that a token matching neither the
pronoun table nor the flex vocabulary is "left literal so an upstream
layer (corpse skintone / `{color}`) can still claim them".

It did the opposite. Executed against the real module:

    '{Their} {color}coat is torn.'  ->  'His colorscoat is torn.'
    'A {s} mark.'                   ->  'A ses mark.'

The braces are eaten, the word is run through the verb conjugator, and
the result is jammed against whatever follows. No error.

`{color}` is not hypothetical: 109 prototype values use it (plus 41
`{side}`), resolved by the GARMENT renderer and, for corpses, resolved
BEFORE this flexer runs -- which is the only thing keeping it safe
today. An author who follows the docstring and writes `{color}` in a
body-part description gets `colorscoat`.

FIXED AS A RESERVED LIST, not as "leave every unknown token literal",
which is what the docstrings promised and what the issue proposed.
There is no verb vocabulary to check against -- `flex_verb` conjugates
whatever it is handed -- so "unknown" cannot be distinguished from "a
verb nobody listed", and the live census of 2,254 longdesc entries shows
real authored verbs riding that exact path (`{are}` 258, `{carry}` 78).
Leaving unknown tokens literal would silently stop flexing every verb
not on some list: a worse failure, and a much bigger one.

Latent today -- the same census found no unknown token in any live
body-part description -- so this protects the next author rather than
repairing existing prose.
"""
from evennia.utils.test_resources import EvenniaTest

from world.anatomy.longdesc_tokens import _flex_body_tokens


class TestReservedTokens(EvenniaTest):

    def test_a_verb_is_still_flexed(self):
        """Control: the fall-through this does NOT change. 258 live
        entries depend on it."""
        self.assertEqual(_flex_body_tokens("They {are} torn.", "singular"),
                         "They is torn.")

    def test_a_body_noun_is_still_flexed(self):
        """Control: the noun path is untouched too."""
        got = _flex_body_tokens("Their {eyes} are pale.", "singular")
        self.assertIn("eye", got)
        self.assertNotIn("{", got)

    def test_color_survives_for_the_layer_that_owns_it(self):
        got = _flex_body_tokens("Their {color}coat is torn.", "singular")
        self.assertIn("{color}", got)
        self.assertNotIn("colorscoat", got)

    def test_side_survives_too(self):
        got = _flex_body_tokens("A scar on the {side} panel.", "singular")
        self.assertIn("{side}", got)

    def test_a_multi_word_token_is_still_literal(self):
        """Control: the one literal path that already worked."""
        got = _flex_body_tokens("A {future substitution} here.", "singular")
        self.assertIn("{future substitution}", got)
