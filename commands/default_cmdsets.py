"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""


from evennia import default_cmds, CmdSet
from commands import CmdCharacter
from commands import CmdInventory
from commands import CmdAdmin
from commands import CmdClothing
from commands import CmdMedical
from commands import CmdConsumption
from commands import CmdMedicalItems
from commands.CmdSpawnMob import CmdSpawnMob
from commands.CmdBug import CmdBug
from commands.CmdAdmin import CmdHeal, CmdPeace, CmdTestDeathCurtain, CmdWeather, CmdResetMedical, CmdMedicalAudit, CmdTestDeath, CmdTestUnconscious
from commands.CmdFixCharacterOwnership import CmdFixCharacterOwnership
from commands.combat.cmdset_combat import CombatCmdSet
from commands.combat.special_actions import CmdAim, CmdGrapple
from commands.CmdThrow import CmdThrow, CmdPull, CmdCatch
from commands.CmdExplosives import (
    CmdRig, CmdDefuse, CmdScan, CmdDetonate, CmdDetonateList,
    CmdClearDetonator,
)
from commands.CmdGraffiti import CmdGraffiti, CmdPress
from commands.CmdCharacter import CmdLongdesc, CmdSkintone
from commands.CmdCharacter import CmdShortdesc, CmdAssign
from commands.CmdCommunication import CmdSay, CmdWhisper, CmdEmote, CmdDotPose
from commands.CmdArmor import CmdArmor, CmdArmorRepair, CmdSlot, CmdUnslot
from commands.shop import CmdBuy


class UnconsciousCmdSet(CmdSet):
    """
    Command set for unconscious characters.
    Only allows minimal OOC commands - no perception, movement, or actions.
    """
    key = "unconscious_cmdset"
    priority = 0  # Same as normal CharacterCmdSet since this replaces it entirely
    no_exits = True  # Prevent exit traversal when unconscious
    
    def at_cmdset_creation(self):
        """
        Add only commands that unconscious characters should be able to use.
        Unconscious = no perception, no movement, no actions.
        """
        # Essential OOC commands only
        self.add(default_cmds.CmdHelp())      # Always allow help
        self.add(default_cmds.CmdWho())       # OOC player information
        self.add(default_cmds.CmdTime())      # OOC time information
        
        # System commands
        self.add(default_cmds.CmdQuit())      # Can always quit
        
        # Staff commands (will be filtered by permissions anyway)
        self.add(default_cmds.CmdPy())        # Staff debugging
        self.add(default_cmds.CmdReload())    # Staff server management
        
        # NO look, NO movement, NO actions when unconscious


class DeathCmdSet(CmdSet):
    """
    Command set for dead characters.
    Only allows minimal OOC commands - no perception, no movement, no actions.
    """
    key = "death_cmdset"
    priority = 0  # Same as normal CharacterCmdSet since this replaces it entirely
    no_exits = True  # Prevent exit traversal when dead
    
    def at_cmdset_creation(self):
        """
        Add only commands that dead characters should be able to use.
        Dead = no perception, no movement, no actions, minimal OOC only.
        """
        # Very minimal set - OOC information only
        self.add(default_cmds.CmdHelp())      # Always allow help
        self.add(default_cmds.CmdWho())       # OOC player information
        self.add(default_cmds.CmdQuit())      # Can always quit
        
        # Staff commands (will be filtered by permissions anyway)
        self.add(default_cmds.CmdPy())        # Staff debugging
        self.add(default_cmds.CmdReload())    # Staff server management
        
        # NO look, NO time, NO movement, NO actions when dead


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        # Add individual character commands
        self.add(CmdCharacter.CmdStats)
        self.add(CmdSpawnMob())
        self.add(CmdAdmin.CmdHeal())
        self.add(CmdAdmin.CmdPeace())
        self.add(CmdAdmin.CmdTestDeathCurtain())
        self.add(CmdWeather())
        
        # Add character ownership fix command
        self.add(CmdFixCharacterOwnership())
        
        # Add bug reporting command
        self.add(CmdBug())
        
        # Add aim command for ranged combat preparation
        self.add(CmdAim())
        
        # Add grapple command for initiating grappling combat
        self.add(CmdGrapple())
        
        # Add the entire combat command set
        self.add(CombatCmdSet)
        
        # Add inventory commands
        self.add(CmdInventory.CmdWield())
        self.add(CmdInventory.CmdUnwield())
        self.add(CmdInventory.CmdFreeHands())
        self.add(CmdInventory.CmdInventory())
        self.add(CmdInventory.CmdDrop())
        self.add(CmdInventory.CmdGet())
        self.add(CmdInventory.CmdGive())
        
        # Add wrest command (non-combat item snatching)
        self.add(CmdInventory.CmdWrest())
        
        # Add frisk command (search characters/corpses)
        self.add(CmdInventory.CmdFrisk())
        
        # Add throw/grenade system commands
        self.add(CmdThrow())
        self.add(CmdPull())
        self.add(CmdCatch())
        self.add(CmdRig())
        self.add(CmdDefuse())
        
        # Add remote detonator commands
        self.add(CmdScan())
        self.add(CmdDetonate())
        self.add(CmdDetonateList())
        self.add(CmdClearDetonator())
        
        # Add character placement commands
        self.add(CmdCharacter.CmdLookPlace())
        self.add(CmdCharacter.CmdTempPlace())
        
        # Add graffiti system commands
        self.add(CmdGraffiti())
        self.add(CmdPress())
        
        # Add longdesc system command
        self.add(CmdLongdesc())
        
        # Add skintone system command
        self.add(CmdSkintone())
        
        # Add identity system commands
        self.add(CmdShortdesc())
        self.add(CmdAssign())

        # Add identity-aware communication commands (override Evennia defaults)
        self.add(CmdSay())
        self.add(CmdWhisper())
        self.add(CmdEmote())
        self.add(CmdDotPose())
        
        # Add clothing system commands
        self.add(CmdClothing.CmdWear())
        self.add(CmdClothing.CmdRemove())
        self.add(CmdClothing.CmdRollUp())
        self.add(CmdClothing.CmdZip())
        
        # Add armor system commands
        self.add(CmdArmor())
        self.add(CmdArmorRepair())
        self.add(CmdSlot())
        self.add(CmdUnslot())
        
        # Add medical system commands
        self.add(CmdMedical.CmdMedical())
        self.add(CmdMedical.CmdDamageTest())
        self.add(CmdMedical.CmdMedicalInfo())
        
        # Add medical administration commands
        self.add(CmdResetMedical())
        self.add(CmdMedicalAudit())
        
        # Add medical state testing commands (using real medical system)
        self.add(CmdTestDeath())
        self.add(CmdTestUnconscious())
        
        # Add consumption method commands
        self.add(CmdConsumption.CmdInject())
        self.add(CmdConsumption.CmdApply())
        self.add(CmdConsumption.CmdBandage())
        self.add(CmdConsumption.CmdEat())
        self.add(CmdConsumption.CmdDrink())
        self.add(CmdConsumption.CmdInhale())
        self.add(CmdConsumption.CmdSmoke())
        
        # Add medical item management commands
        self.add(CmdMedicalItems.CmdListMedItems())
        self.add(CmdMedicalItems.CmdMedItemInfo())
        self.add(CmdMedicalItems.CmdRefillMedItem())
        
        # Add shop commands
        self.add(CmdBuy())

class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #

