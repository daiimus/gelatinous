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
        active_count = 0
        for char in self.characters:
            if char.db.archived:
                continue
            active_count += 1
        
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
        
        # Count active (non-archived) characters - defensive coding
        active_count = 0
        for char in self.characters:
            if not char or not hasattr(char, 'db'):
                continue
            if char.db.archived:
                continue
            active_count += 1
        
        return active_count >= max_slots

    def at_post_login(self, session=None, **kwargs):
        """
        Called after successful login, handles character detection and auto-puppeting.
        
        We override the default entirely because we have custom logic for:
        - Auto-puppeting single characters
        - Starting character creation for new accounts
        - Handling archived characters
        """
        # Use Evennia's account.characters (the _playable_characters list) - this is the authoritative source
        all_characters = self.characters.all()
        
        # Filter for active (non-archived) characters
        # Be defensive: only treat explicitly archived=True as archived
        active_chars = []
        for char in all_characters:
            # Only exclude if explicitly archived
            if char.db.archived is True:
                continue
            active_chars.append(char)
        
        # CRITICAL: Only start character creation if there are ZERO active characters
        if len(active_chars) == 0:
            # No active characters - start character creation
            # Import here to avoid circular imports
            try:
                from commands.charcreate import start_character_creation
                
                # Restore last_character if it's missing but we have archived characters
                # This handles cases where last_character was cleared or lost
                if not self.db.last_character:
                    # Find most recently archived character
                    archived_chars = []
                    for char in all_characters:
                        if char.db.archived is True:
                            archived_date = char.db.archived_date or 0
                            archived_chars.append((archived_date, char))
                    
                    # Sort by archive date (most recent first) and use the newest
                    if archived_chars:
                        archived_chars.sort(reverse=True, key=lambda x: x[0])
                        self.db.last_character = archived_chars[0][1]
                
                # Check if they have a last_character (from death or manual archival)
                # If so, use respawn flow with flash clone + template options
                is_respawn = bool(self.db.last_character)
                old_character = self.db.last_character if is_respawn else None
                
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
            # Multiple active characters - let user choose with 'ic <name>'
            # The default OOC behavior will handle this
            pass


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
