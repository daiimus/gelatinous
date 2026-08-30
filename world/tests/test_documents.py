"""Documents vouch for faces, through perception (#2408).

A document is read by LOOKING at it. There is no `show` verb and there should
not be one: handing someone a photo, setting it on a bar, and holding it up
are all expressions of look, and an obscure verb per case is a hazard for
players (owner ruling 2026-08-29). One hook — `Document.return_appearance` —
serves every route.

What a document proves is per-observer KNOWLEDGE, never global truth. A
`verified_name` as a property of a person would collapse the disguise layer
the moment it existed.

Authority and protocol are separate axes. A colony document with a broken seal
is high authority and worthless; a club card with a valid chip is low
authority and perfectly genuine — and may honestly attest an ALIAS.
"""
from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from world import identity


class _Papers(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        # real Characters — the base harness ships DefaultCharacters, which
        # have no recognition_memory
        self.observer = create_object("typeclasses.characters.Character",
                                      key="observer", location=self.room1)
        self.other = create_object("typeclasses.characters.Character",
                                   key="other", location=self.room1)
        self.subject = create_object("typeclasses.characters.Character",
                                     key="subject", location=self.room1)
        self.subject.sleeve_uid = "sleeve-subject-1"
        self.uid = identity.get_apparent_uid(self.subject)
        self.doc = create_object("typeclasses.items.Document",
                                 key="registry card", location=self.room1)
        self.doc.attributes.add("depicts_uid", self.uid)
        self.doc.attributes.add("attested_name", "Robert Paulson")
        self.doc.attributes.add("issuer", "Colony Registry")
        self.doc.attributes.add("authority", "colony")
        self.doc.attributes.add("protocol", "pressed seal")
        self.doc.attributes.add("protocol_ok", True)

    def _know_the_face(self, name="Billy"):
        mem = self.observer.recognition_memory or {}
        mem[self.uid] = {"assigned_name": name, "attested": [],
                         "times_seen": 1}
        self.observer.recognition_memory = mem


class TestReadingIsTheMechanic(_Papers):

    def test_looking_at_it_files_what_it_proves(self):
        self._know_the_face()
        self.doc.return_appearance(self.observer)
        self.assertEqual(identity.official_name(self.observer, self.uid),
                         "Robert Paulson")

    def test_it_does_not_overwrite_what_you_call_them(self):
        """Papers are a separate column. What you CALL someone stays your
        choice — the owner's ruling that address is the NPC's decision."""
        self._know_the_face("Billy")
        self.doc.return_appearance(self.observer)
        entry = (self.observer.recognition_memory or {})[self.uid]
        self.assertEqual(entry["assigned_name"], "Billy")

    def test_a_face_you_have_never_seen_is_not_filed_by_looking(self):
        """Reading papers about a stranger tells you a name, not a face.
        Committing the face takes the deliberate act — `remember`."""
        self.doc.return_appearance(self.observer)
        self.assertNotIn(self.uid, self.observer.recognition_memory or {})

    def test_reading_never_raises_on_a_blank_document(self):
        blank = create_object("typeclasses.items.Document", key="blank",
                              location=self.room1)
        blank.return_appearance(self.observer)      # must not raise


class TestAuthorityAndProtocol(_Papers):

    def test_a_broken_seal_proves_nothing(self):
        """High authority, failed protocol. The document is genuine-looking
        and worthless — which is what forgery will attack later."""
        self._know_the_face()
        self.doc.attributes.add("protocol_ok", False)
        self.doc.return_appearance(self.observer)
        self.assertIsNone(identity.official_name(self.observer, self.uid))
        self.assertTrue(identity.attestations(self.observer, self.uid))

    def test_a_club_card_is_genuine_but_not_official(self):
        """The owner's case: documents may honestly pass an ALIAS."""
        self._know_the_face()
        self.doc.attributes.add("authority", "commercial")
        self.doc.attributes.add("attested_name", "Blade")
        self.doc.return_appearance(self.observer)
        self.assertIsNone(identity.official_name(self.observer, self.uid))
        self.assertEqual(identity.attestations(self.observer, self.uid)[0]["name"],
                         "Blade")

    def test_attestations_rank_by_authority(self):
        self._know_the_face()
        identity.attest(self.observer, self.uid, "Blade", issuer="Helix",
                        authority="commercial")
        identity.attest(self.observer, self.uid, "Robert Paulson",
                        issuer="Registry", authority="colony")
        self.assertEqual(
            identity.attestations(self.observer, self.uid)[0]["name"],
            "Robert Paulson")

    def test_re_attesting_refreshes_rather_than_stacks(self):
        self._know_the_face()
        for _ in range(4):
            identity.attest(self.observer, self.uid, "Robert Paulson",
                            issuer="Registry", authority="colony")
        self.assertEqual(len(identity.attestations(self.observer, self.uid)), 1)


class TestItIsKnowledgeNotTruth(_Papers):

    def test_two_observers_can_hold_different_records(self):
        """The disguise layer depends on this. What a document proves is only
        ever 'somebody could show me this'."""
        self._know_the_face()
        self.doc.return_appearance(self.observer)
        self.assertEqual(identity.official_name(self.observer, self.uid),
                         "Robert Paulson")
        self.assertIsNone(identity.official_name(self.other, self.uid))

    def test_papers_on_an_unknown_face_are_refused(self):
        self.assertFalse(identity.attest(self.observer, "nobody-uid", "X",
                                         issuer="Registry"))
