"""Opinion stops being a one-way ratchet (#2436).

`react_to_attack` opened with an eligibility gate:

```python
reaction = getattr(getattr(victim, "db", None), "reaction", None)
if not reaction:
    return  # not a role-bearing NPC — none of our business
```

and the `-0.60` opinion wound sat *after* it. Its own comment claimed
the write landed "BEFORE the ladder runs, so it lands even if the
reaction itself fails" — true of the ladder, false of the gate.

`db.reaction` is written in exactly one place: the generated-civilian
ROLES table. **No blueprint sets it.** Measured live: of 78 souled
NPCs, 40 carry `db.reaction` and 38 do not — and the 38 are the NAMED
CAST (Sable, Vesper, Sully, Petra, Ottilie, Ezra, Bellows…), precisely
the characters whose WHO line reads `thoughts.opinion_of`.

Meanwhile the courtesy write (+0.08, `llm_npc.py:190`) has no such
gate and reached them fine. So for the entire named cast opinion only
ever moved UP: **thanking Sable changed her read on you, stabbing her
did not.** The strongest negative signal in the game was dropped for
exactly the characters designed to remember it.
`NPC_MEMORY_AND_IDENTITY_SPEC.md:204-205` states the write as shipped;
the code was the stale side.

The write now asks "does this victim have a memory", not "does this
victim have a scripted flee/comply/resist ladder" — soul-tag OR
reaction, so the set can only widen. All 40 current reaction-bearers
are soul-tagged, so nobody loses the write.

**Deliberately not `hasattr(db, "thoughts")`:** an opinion store
autocreates on write, so that predicate answers True for a PC and would
start stamping opinion rows onto player characters.
"""
from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from world.director.civilians import react_to_attack
from world.identity import get_apparent_uid
from world.souls import engine, thoughts


class _AttackCase(EvenniaTest):
    def npc(self, key="Sable Vane", *, souled=True, reaction=None):
        npc = create_object("typeclasses.characters.Character", key=key,
                            location=self.room1)
        npc.height, npc.build = "average", "lean"
        if souled:
            npc.tags.add(engine.SOUL_TAG[0], category=engine.SOUL_TAG[1])
        if reaction:
            npc.db.reaction = reaction
        return npc

    def opinion_keys(self, npc):
        book = thoughts._opinions(npc) or {}
        uid = get_apparent_uid(self.char1)
        return [entry[1] for entry in (book.get(uid) or [])]


class TestTheNamedCastRemembers(_AttackCase):
    """A blueprint NPC — souled, no `db.reaction`. This is the whole
    cast, and the case that was silently dropped."""

    def test_the_wound_is_recorded(self):
        sable = self.npc()
        react_to_attack(sable, self.char1)
        self.assertIn("attacked_me", self.opinion_keys(sable))

    def test_the_opinion_actually_moves_down(self):
        sable = self.npc()
        before = thoughts.opinion_of(sable, get_apparent_uid(self.char1))
        react_to_attack(sable, self.char1)
        after = thoughts.opinion_of(sable, get_apparent_uid(self.char1))
        self.assertLess(after, before)

    def test_no_scripted_ladder_is_started(self):
        """They have no role posture — the memory is all we owe."""
        sable = self.npc()
        react_to_attack(sable, self.char1)
        self.assertIsNone(getattr(sable.ndb, "reaction_stage", None))


class TestGeneratedCiviliansStillWork(_AttackCase):
    """The 40 that already worked must not lose anything."""

    def test_a_reaction_bearer_still_records_the_wound(self):
        civ = self.npc("a hauler", reaction="flee")
        react_to_attack(civ, self.char1)
        self.assertIn("attacked_me", self.opinion_keys(civ))

    def test_and_still_climbs_its_ladder(self):
        civ = self.npc("a hauler", reaction="flee")
        react_to_attack(civ, self.char1)
        self.assertIsNotNone(getattr(civ.ndb, "reaction_stage", None))

    def test_an_unsouled_reaction_bearer_keeps_the_write(self):
        """Soul-tag OR reaction — the set only widens."""
        civ = self.npc("a stranger", souled=False, reaction="comply")
        react_to_attack(civ, self.char1)
        self.assertIn("attacked_me", self.opinion_keys(civ))


class TestPlayersAreNotGivenOpinions(_AttackCase):
    """`thoughts._opinions` autocreates, so a `hasattr` predicate would
    have started writing opinion rows onto PCs."""

    def test_attacking_a_player_writes_no_opinion(self):
        self.char2.height, self.char2.build = "tall", "lean"
        react_to_attack(self.char2, self.char1)
        self.assertEqual(self.opinion_keys(self.char2), [])

    def test_a_plain_object_is_not_given_feelings(self):
        crate = create_object("typeclasses.objects.Object", key="a crate",
                              location=self.room1)
        react_to_attack(crate, self.char1)   # must not raise
        self.assertFalse(getattr(crate.db, "thoughts", None))


class TestItStillCannotBreakCombat(_AttackCase):
    def test_a_broken_opinion_store_does_not_raise(self):
        from unittest.mock import patch
        sable = self.npc()
        with patch("world.souls.thoughts.add_opinion",
                   side_effect=RuntimeError("boom")):
            react_to_attack(sable, self.char1)   # must not raise

    def test_an_attacker_with_no_identity_does_not_raise(self):
        sable = self.npc()
        react_to_attack(sable, None)             # must not raise
