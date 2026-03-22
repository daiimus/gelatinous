"""
One-time admin command to repair legacy character ownership.

This fixes characters created with the old broken manual method by properly
establishing Evennia's internal ownership relationships using the account's
internal _add_character method.

This command will be obsolete once all legacy characters are fixed.
"""

from evennia import Command
from evennia.utils.search import search_object


class CmdFixCharacterOwnership(Command):
    """
    ONE-TIME FIX for legacy character ownership.
    
    Usage:
        @fixchar <character name>
        @fixchar all
        @fixchar undo
    
    This repairs characters created before we switched to account.create_character()
    by using Evennia's internal character tracking methods.
    
    Legacy characters were created with manual setup and don't appear in
    account.characters. This command fixes that by checking the character's
    puppet lock for your account ID.
    
    Use 'all' to fix all characters that have your account ID in their puppet lock.
    Use 'undo' to remove ALL characters from your account.characters list (emergency cleanup).
    """
    
    key = "@fixchar"
    locks = "cmd:pperm(Admin)"
    help_category = "Admin"
    
    def func(self):
        caller = self.caller
        
        # Get the account - caller might be a Character, we need the Account
        if hasattr(caller, 'account'):
            account = caller.account
        else:
            account = caller
        
        if not self.args:
            caller.msg("Usage: @fixchar <character name> or @fixchar all or @fixchar undo")
            return
        
        if self.args.strip().lower() == "undo":
            # EMERGENCY: Clear the entire _playable_characters list
            caller.msg("|rWARNING: This will remove ALL characters from your account.characters list!|n")
            all_chars = account.characters.all()
            caller.msg(f"|rRemoving {len(all_chars)} character(s)...|n")
            for char in list(all_chars):  # Make a copy to avoid modifying while iterating
                account.characters.remove(char)
                caller.msg(f"|yRemoved:|n {char.key} (#{char.id})")
            caller.msg("|gUndo complete. Your account.characters list is now empty.|n")
            return
        
        if self.args.strip().lower() == "all":
            # Fix all characters that have the correct puppet lock for this account
            from typeclasses.characters import Character
            all_chars = Character.objects.all()
            
            fixed_count = 0
            for char in all_chars:
                # Check if character's locks specifically reference this account's ID
                # This prevents admins from accidentally claiming all characters
                puppet_lock = char.locks.get("puppet")
                if puppet_lock and f"pid({account.id})" in puppet_lock:
                    # Character has a lock for this specific account, but may not be in characters list
                    if char not in account.characters:
                        try:
                            account.characters.add(char)
                            fixed_count += 1
                            caller.msg(f"|gFixed:|n {char.key} (#{char.id})")
                        except Exception as e:
                            caller.msg(f"|rError fixing {char.key}:|n {e}")
            
            if fixed_count == 0:
                caller.msg("|yNo characters needed fixing.|n")
            else:
                caller.msg(f"|gFixed {fixed_count} character(s).|n")
            
            # Show verification
            all_playable = account.characters.all()
            caller.msg(f"|yaccount.characters now returns {len(all_playable)} character(s):|n")
            for char in all_playable:
                caller.msg(f"  - {char.key} (#{char.id})")
            
        else:
            # Fix specific character
            char_name = self.args.strip()
            results = search_object(char_name, typeclass="typeclasses.characters.Character")
            
            if not results:
                caller.msg(f"|rNo character found with name '{char_name}'.|n")
                return
            
            if len(results) > 1:
                caller.msg(f"|rMultiple matches:|n")
                for char in results:
                    caller.msg(f"  - {char.key} (#{char.id})")
                caller.msg("|yPlease be more specific.|n")
                return
            
            char = results[0]
            
            # Check puppet access
            if not char.access(account, "puppet"):
                caller.msg(f"|rYou don't have permission to puppet {char.key}.|n")
                return
            
            # Check if already tracked
            if char in account.characters:
                caller.msg(f"|y{char.key} is already in account.characters list.|n")
                return
            
            # Use Evennia's CharactersHandler to properly add the character
            try:
                account.characters.add(char)
                caller.msg(f"|gFixed {char.key} - added to playable characters.|n")
            except Exception as e:
                caller.msg(f"|rError fixing {char.key}:|n {e}")
                return
            
            # Verify
            all_playable = account.characters.all()
            caller.msg(f"|yaccount.characters now returns {len(all_playable)} character(s):|n")
            for char in all_playable:
                caller.msg(f"  - {char.key} (#{char.id})")
