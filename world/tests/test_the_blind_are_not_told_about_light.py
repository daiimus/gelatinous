"""Sight-only weather prose lives in the bucket that can be gated (#2734).

`atmospheric` is never perception-gated -- that is its documented
contract (`CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC`: *"olfactory /
tactile / atmospheric never gated"*). Sight-only lines were authored
into it anyway:

    clear_dawn / midday / dusk / night
        "hard light throws the street's grime into relief"

so a blind character standing outdoors was told that hard light threw
the grime into relief.

AND THE COMPENSATION MADE IT WORSE. `weather_system` gives a looker
missing a sense one EXTRA line from the buckets that remain -- a kind
intent that inverts here:

    sighted   5 senses, 2 lines drawn   -> P(atmospheric) 40%
    blind     4 senses, 3 lines drawn   -> P(atmospheric) 75%

The player who cannot see drew the un-gated bucket nearly twice as
often, and that bucket was where the sight-only prose lived. The
mechanism built to compensate for blindness concentrated the leak.

Fixed by RE-CATEGORISING, not by gating `atmospheric`: the lines are
visual prose that was filed in the wrong bucket, and the bucket's
contract is correct. 17 moved into their own pool's `visual` list,
where the existing filter already drops them for a looker who cannot
see.

ONE FALSE POSITIVE WAS LEFT ALONE, and it is why this was not done by
regex: "the light wet leaves the street muted and soft" -- `light` there
is light RAIN, not illumination. Every candidate was read before moving.

Erring toward moving is the safe direction: a line wrongly moved means a
blind character misses some flavour, while a line wrongly kept means
they are told about shadows.
"""
import re

from evennia.utils.test_resources import EvenniaTest

# WEATHER_POOLS, not WEATHER_MESSAGES: the pools carrying the per-sense
# buckets are the former. The first version read the latter, found zero
# pools, and its control failed rather than letting an empty sweep pass
# as a clean result.
from world.weather.weather_messages import WEATHER_POOLS

#: Words that cannot be perceived without sight.
SIGHT = re.compile(
    r"\b(hard light|lamplight|glare|glow|glows|glowing|shadow|shadows|"
    r"gleam|gleams|glint|glints|shine|shines|shining|silhouette|"
    r"colour|color|grey|gray|looks|you can see|haloes)\b", re.I)

#: Read and kept deliberately -- `light` here is light RAIN.
ALLOWED = ("the light wet leaves the street muted and soft",)


class TestAtmosphericIsSenseNeutral(EvenniaTest):

    def _atmospheric(self):
        for weather, pool in WEATHER_POOLS.items():
            if not isinstance(pool, dict):
                continue
            for line in pool.get("atmospheric", []) or []:
                yield weather, line

    def test_the_sweep_reads_real_pools(self):
        """Control: an empty sweep would pass while checking nothing."""
        self.assertTrue(list(self._atmospheric()))

    def test_the_pattern_catches_what_it_is_for(self):
        """Control: and that the matcher fires on the known offender."""
        self.assertTrue(
            SIGHT.search("hard light throws the street's grime into relief"))

    def test_no_atmospheric_line_needs_eyes(self):
        offenders = [f"{w}: {line}" for w, line in self._atmospheric()
                     if SIGHT.search(line) and line not in ALLOWED]
        self.assertEqual(
            offenders, [],
            "sight-only prose in the un-gated bucket — move it to "
            "'visual' in the same pool:\n" + "\n".join(offenders))

    def test_the_visual_bucket_still_has_content(self):
        """Control: the moves must not have emptied a pool's atmospheric
        list into visual wholesale."""
        thin = [w for w, pool in WEATHER_POOLS.items()
                if isinstance(pool, dict) and pool.get("atmospheric") == []]
        self.assertEqual(thin, [], f"emptied atmospheric pools: {thin}")
