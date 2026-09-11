"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().
     - sessions - session-handler. Use session.get() to see all sessions connected, if any
     - options - option-handler. Defaults are taken from settings.OPTIONS_ACCOUNT_DEFAULT
     - characters - handler for listing the account's playable characters

    * Helper methods (check autodocs for full updated listing)

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(searchdata, return_puppet=False, search_object=False, typeclass=None,
                      nofound_string=None, multimatch_string=None, use_nicks=True,
                      quiet=False, **kwargs)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs)
     - check_permstring(permstring)
     - get_cmdsets(caller, current, **kwargs)
     - get_cmdset_providers()
     - uses_screenreader(session=None)
     - get_display_name(looker, **kwargs)
     - get_extra_display_name_info(looker, **kwargs)
     - disconnect_session_from_account()
     - puppet_object(session, obj)
     - unpuppet_object(session)
     - unpuppet_all()
     - get_puppet(session)
     - get_all_puppets()
     - is_banned(**kwargs)
     - get_username_validators(validator_config=settings.AUTH_USERNAME_VALIDATORS)
     - authenticate(username, password, ip="", **kwargs)
     - normalize_username(username)
     - validate_username(username)
     - validate_password(password, account=None)
     - set_password(password, **kwargs)
     - get_character_slots()
     - get_available_character_slots()
     - create_character(*args, **kwargs)
     - create(*args, **kwargs)
     - delete(*args, **kwargs)
     - channel_msg(message, channel, senders=None, **kwargs)
     - idle_time()
     - connection_time()

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_first_save()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_password_change(**kwargs)
     - at_first_login()
     - at_pre_login()
     - at_post_login(session=None)
     - at_failed_login(session, **kwargs)
     - at_disconnect(reason=None, **kwargs)
     - at_post_disconnect(**kwargs)
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()
     - at_look(target=None, session=None, **kwargs)
     - at_post_create_character(character, **kwargs)
     - at_post_add_character(char)
     - at_post_remove_character(char)
     - at_pre_channel_msg(message, channel, senders=None, **kwargs)
     - at_post_chnnel_msg(message, channel, senders=None, **kwargs)

    """

    def _sleeves_split(self):
        """Split this account's characters into (active, archived) using the
        ``archived`` tag index (spec §9 step 3) — ONE database query for the
        whole split instead of a ``db.archived`` attribute read per character
        (accounts accumulate archived sleeves forever; actives are capped by
        MAX_NR_CHARACTERS). Order of ``self.characters`` is preserved.

        Self-healing: the few tag-active sleeves are verified against the
        legacy ``db.archived`` attribute — a True without the tag (pre-index
        sleeve, stray staff @py) is healed into the index on the spot, so an
        archived husk can never read as active (at_post_login auto-puppets
        actives)."""
        chars = [c for c in self.characters if c]
        if not chars:
            return [], []
        from evennia.objects.models import ObjectDB
        archived_ids = set(ObjectDB.objects.filter(
            id__in=[c.id for c in chars],
            db_tags__db_key="archived",
            db_tags__db_category="sleeve",
        ).values_list("id", flat=True))
        active, archived = [], []
        for char in chars:
            if char.id in archived_ids:
                archived.append(char)
            elif char.db.archived is True:      # legacy flag, no tag: heal
                char.tags.add("archived", category="sleeve")
                archived.append(char)
            else:
                active.append(char)
        return active, archived

    @property
    def active_sleeves(self):
        """This account's non-archived characters (tag-indexed, one query)."""
        return self._sleeves_split()[0]

    @property
    def archived_sleeves(self):
        """This account's archived sleeves (tag-indexed, one query)."""
        return self._sleeves_split()[1]

    def check_available_slots(self, **kwargs):
        """
        Override Evennia's default to exclude archived characters from slot count.
        
        Helper method used to determine if an account can create additional characters
        using the character slot system. Archived characters don't count toward the limit.

        Returns:
            str (optional): An error message regarding the status of slots. If present, this
               will halt character creation. If not, character creation can proceed.
        """
        from django.conf import settings

        # Get max allowed characters
        max_slots = settings.MAX_NR_CHARACTERS
        if max_slots is None:
            # No limit
            return None

        # Count only active (non-archived) characters
        active_count = len(self.active_sleeves)

        # Check if we have slots available
        available_slots = max(0, max_slots - active_count)
        
        if available_slots <= 0:
            if not (self.is_superuser or self.check_permstring("Developer")):
                plural = "" if max_slots == 1 else "s"
                return f"You may only have a maximum of {max_slots} character{plural}."
        
        return None

    @property
    def at_character_limit(self):
        """
        Check if account has reached the maximum character limit.
        
        Note: This does NOT bypass for superusers anymore. The limit applies to everyone
        for menu display purposes. Character creation itself may still allow bypass.
        
        Returns:
            bool: True if at max characters, False otherwise.
        """
        from django.conf import settings
        
        max_slots = settings.MAX_NR_CHARACTERS
        if max_slots is None:
            return False

        # Count active (non-archived) characters via the tag index
        return len(self.active_sleeves) >= max_slots

    def respawn_candidate(self):
        """The archived sleeve this account may respawn from, or None.

        `db.last_character` is written by the death path and was read
        RAW by the telnet login while the web view validated it first
        (#2615). Whatever sat there -- a living sleeve, a deleted one,
        one transferred to another account -- was handed to the respawn
        flow as the character being replaced.

        One door now. Both callers ask this, and it CLEARS a reference
        that does not qualify, so a stale value is repaired on the way
        past rather than left for the next login to trip over.

        Returns:
            The archived character, or None (having cleared the
            attribute when the reference was alive or broken).
        """
        old = self.db.last_character
        if not old:
            return None
        try:
            _ = old.key                  # a deleted sleeve raises here
            if old.is_archived:
                return old
        except (AttributeError, TypeError):
            self.db.last_character = None
            return None
        # Alive: they are not a respawn candidate, and the stale
        # pointer would misreport the next death.
        self.db.last_character = None
        return None

    def at_post_login(self, session=None, **kwargs):
        """
        Called after successful login, handles character detection and auto-puppeting.
        
        We override the default entirely because we have custom logic for:
        - Auto-puppeting single characters
        - Starting character creation for new accounts
        - Handling archived characters

        Overriding the PUPPETING is the reason; overriding the rest was
        an accident (#2613). Evennia's default does three things before
        it puppets — restore saved protocol flags, send the ``logged_in``
        OOB message, and post *"|G{key} connected|n"* to the connect
        channel — and replacing the method wholesale dropped all three.
        `at_disconnect` is NOT overridden, so its matching red line still
        posts: MudInfo held **2,847 disconnects and zero connects**, in
        the channel whose job is telling staff who is on.

        Done here rather than via `super()` deliberately: the default
        ends by auto-puppeting, and calling it would run that a second
        time alongside the custom logic below.
        """
        # -- the non-puppeting preamble of Evennia's default (#2613) --
        protocol_flags = self.attributes.get("_saved_protocol_flags", {})
        if session and protocol_flags:
            session.update_flags(**protocol_flags)
        if session:
            session.msg(logged_in={})
        try:
            self._send_to_connect_channel(f"|G{self.key} connected|n")
        except Exception:  # noqa: BLE001 — an announcement never blocks a login
            from evennia.utils import logger
            logger.log_trace(
                f"connect-channel announcement failed for {self.key}")

        # Split the account's sleeves on the tag index — one query, and the
        # archived list is reused below for the last_character restore.
        active_chars, archived_sleeves = self._sleeves_split()

        # A DECANT ALREADY IN PROGRESS IS NOT RESTARTED (#2625).
        #
        # `at_post_login` runs for EVERY session (MULTISESSION_MODE=1),
        # and with zero sleeves it used to start chargen
        # unconditionally. `EvMenu.__init__` closes any existing menu on
        # the same caller, so a second tab tore down the first one:
        # `_charcreate_exit_callback` then saw zero actives and
        # disconnected the original session with "Sleeve decantation
        # incomplete", while `start_character_creation` reset
        # `ndb.charcreate_data` and discarded everything already typed.
        #
        # Ten fields in on the web client, open a second tab, lose the
        # lot. The second session is told where the decant is instead.
        if not active_chars and getattr(self.ndb, "_evmenu", None):
            self.msg(
                "|yYou're already decanting a sleeve in another "
                "session.|n Finish there, or disconnect it and "
                "reconnect here."
            )
            return

        # CRITICAL: Only start character creation if there are ZERO active characters
        if not active_chars:
            # No active characters - start character creation
            # Import here to avoid circular imports
            try:
                from commands.charcreate import start_character_creation
                
                # Restore last_character if it's missing but we have archived characters
                # This handles cases where last_character was cleared or lost
                if not self.db.last_character and archived_sleeves:
                    # Most recently archived sleeve (tag-indexed split above)
                    self.db.last_character = max(
                        archived_sleeves,
                        key=lambda c: c.db.archived_date or 0)
                
                # Check if they have a last_character (from death or manual archival)
                # If so, use respawn flow with flash clone + template options
                # Validated, not read raw (#2615) — the same check the
                # web respawn view makes, so the two doors cannot
                # disagree about what is respawnable.
                old_character = self.respawn_candidate()
                is_respawn = old_character is not None
                
                start_character_creation(self, is_respawn=is_respawn, old_character=old_character)
            except ImportError as e:
                # Graceful fallback if charcreate not available yet
                self.msg("|rCharacter creation system not available. Please contact an admin.|n")
        elif len(active_chars) == 1:
            # Exactly one active character - auto-puppet for convenience
            if session:
                self.puppet_object(session, active_chars[0])
            else:
                # No session means we can't auto-puppet - this shouldn't happen
                self.msg("|yAuto-puppet failed: No session. Use 'ic' to connect.|n")
        else:
            # Multiple active sleeves — show the selection screen.
            #
            # This was `pass`, under a comment reading "the default OOC
            # behavior will handle this". The default is
            # `DefaultAccount.at_post_login`'s multi-character branch —
            # which THIS METHOD REPLACES, deliberately without calling
            # `super()` (see the docstring above, #2613). So nothing
            # handled it: an account with two or more active sleeves
            # logged in to silence. No list, no prompt, and no hint that
            # `ic <name>` was the way out, since the only place that was
            # written down was the comment (#2614).
            #
            # Scoped to `active_chars` rather than the default's
            # `self.characters`: archived sleeves are dead and must not
            # appear in a picker that implies they can be puppeted.
            self.msg(
                self.at_look(target=active_chars, session=session),
                session=session,
            )


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
