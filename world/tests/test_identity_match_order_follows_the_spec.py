"""Assigned names resolve before sdescs, per spec (#2820).

`identity_match_characters` said two contradictory things twelve lines
apart:

    Resolution order (per the spec):
      1. Assigned names ...
      2. Sdescs ...
    ...
    Returns: ... ordered as they appear in *candidates*.

and the code implements the first: two passes over `candidates`,
concatenated, so candidate order is preserved WITHIN each bucket and
destroyed BETWEEN them.

#2820 read the `Returns:` line as the contract and proposed making the
code match it. The spec says otherwise. IDENTITY_RECOGNITION_SPEC,
"Targeting Priority":

    2. **Assigned names** -- Check the player's recognition memory ...
    3. **sdescs** -- Match against visible characters' sdescs ...
    4. **Ordinals** -- "2nd tall man" uses the existing ordinal system

Assigned names are step 2, sdescs step 3, and ordinals step 4 applied to
the result. So the buckets ARE the contract and the `Returns:` sentence
was the error. Fixed there; pinned here, because the ordering is
load-bearing for every targeting command and nothing tested it.

THE CONSEQUENCE IS REAL AND IS NOT A DEFECT. An ordinal indexes the
priority order, not the order the player can see: with two men present
and one remembered by name, the remembered one is always `1.man`. That
is what the spec asks for. Whether it is what the game WANTS is a design
question for the owner, and is recorded on the issue rather than
answered by changing the code.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.search import identity_match_characters


class TestPriorityOrder(EvenniaTest):

    def setUp(self):
        super().setUp()
        self.searcher = self.char1
        self.searcher.location = self.room1
        self.people = []
        for key in ("First", "Second"):
            who = create_object("typeclasses.characters.Character",
                                key=key, location=self.room1)
            who.height = "tall"
            who.build = "lean"
            who.sdesc_keyword = "man"
            self.people.append(who)

    def _remember(self, who, name):
        """Write the recognition entry directly, keyed on the target's
        APPARENT UID -- which is how the store is keyed, and what
        `_match_assigned_name` reads. There is no `assign_name` helper;
        the first version of this test imported one that does not exist
        and raised ImportError, which is an ERROR and proves nothing."""
        from world.identity import get_apparent_uid
        memory = dict(self.searcher.recognition_memory or {})
        memory[get_apparent_uid(who)] = {"assigned_name": name}
        self.searcher.recognition_memory = memory

    def test_both_match_by_sdesc_in_candidate_order(self):
        """Control: with nobody remembered, the buckets cannot reorder
        anything and candidate order is what comes back."""
        got = identity_match_characters(self.searcher, "man", self.people)
        self.assertEqual(got, self.people)

    def test_a_remembered_person_comes_first(self):
        """Even when they are SECOND in candidate order."""
        self._remember(self.people[1], "man")
        got = identity_match_characters(self.searcher, "man", self.people)
        self.assertEqual(got[0], self.people[1],
                         "an assigned-name match did not resolve first")

    def test_the_ordinal_indexes_that_order(self):
        """The consequence, pinned so it cannot change silently."""
        self._remember(self.people[1], "man")
        got = identity_match_characters(self.searcher, "2.man", self.people)
        self.assertEqual(got, [self.people[0]])
