"""
Prototypes

A prototype is a simple way to create individualized instances of a
given typeclass. It is dictionary with specific key names.

For example, you might have a Sword typeclass that implements everything a
Sword would need to do. The only difference between different individual Swords
would be their key, description and some Attributes. The Prototype system
allows to create a range of such Swords with only minor variations. Prototypes
can also inherit and combine together to form entire hierarchies (such as
giving all Sabres and all Broadswords some common properties). Note that bigger
variations, such as custom commands or functionality belong in a hierarchy of
typeclasses instead.

A prototype can either be a dictionary placed into a global variable in a
python module (a 'module-prototype') or stored in the database as a dict on a
special Script (a db-prototype). The former can be created just by adding dicts
to modules Evennia looks at for prototypes, the latter is easiest created
in-game via the `olc` command/menu.

Prototypes are read and used to create new objects with the `spawn` command
or directly via `evennia.spawn` or the full path `evennia.prototypes.spawner.spawn`.

A prototype dictionary have the following keywords:

Possible keywords are:
- `prototype_key` - the name of the prototype. This is required for db-prototypes,
  for module-prototypes, the global variable name of the dict is used instead
- `prototype_parent` - string pointing to parent prototype if any. Prototype inherits
  in a similar way as classes, with children overriding values in their parents.
- `key` - string, the main object identifier.
- `typeclass` - string, if not set, will use `settings.BASE_OBJECT_TYPECLASS`.
- `location` - this should be a valid object or #dbref.
- `home` - valid object or #dbref.
- `destination` - only valid for exits (object or #dbref).
- `permissions` - string or list of permission strings.
- `locks` - a lock-string to use for the spawned object.
- `aliases` - string or list of strings.
- `attrs` - Attributes, expressed as a list of tuples on the form `(attrname, value)`,
  `(attrname, value, category)`, or `(attrname, value, category, locks)`. If using one
   of the shorter forms, defaults are used for the rest.
- `tags` - Tags, as a list of tuples `(tag,)`, `(tag, category)` or `(tag, category, data)`.
-  Any other keywords are interpreted as Attributes with no category or lock.
   These will internally be added to `attrs` (equivalent to `(attrname, value)`.

See the `spawn` command and `evennia.prototypes.spawner.spawn` for more info.

"""

# =============================================================================
# EXPLOSIVE PROTOTYPES FOR THROW COMMAND TESTING
# =============================================================================

# Base explosive prototype with common properties
EXPLOSIVE_BASE = {
    "typeclass": "typeclasses.items.Item",
    "desc": "A military-grade explosive device with a pin-pull mechanism.",
    "is_explosive": True,
    "requires_pin": True,
    "pin_pulled": False,
    "chain_trigger": True,
    "dud_chance": 0.05,  # 5% chance to fail
    "damage_type": "laceration",  # Fragmentation/shrapnel wounds
    "scanned_by_detonator": None,  # Remote detonator tracking
}

# Standard fragmentation grenade
FRAG_GRENADE = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "HDG M67 fragmentation grenade",
    "aliases": ["grenade", "frag", "m67", "hdg grenade", "frag grenade"],
    "desc": "A Helios Defense Group M67 fragmentation grenade - the standard-issue antipersonnel explosive used by military forces across human space. The body is a sphere of notched steel designed to fragment into hundreds of lethal shards upon detonation, encased in an olive drab coating. A spoon-style safety lever is held down by a pin that must be pulled to arm the fuse. Once the pin is pulled and the spoon released, you have approximately 8 seconds before detonation - enough time to throw it, not enough time to reconsider. The M67's blast radius extends fifteen meters, with the fragmentation pattern deadly within five. HDG has manufactured this design unchanged for over a century because some problems require the same solution regardless of the era: aggressive, indiscriminate violence delivered by a sphere you can hold in your hand.",
    "fuse_time": 8,
    "blast_damage": 25,
}

# Shorter fuse tactical grenade
TACTICAL_GRENADE = {
    "prototype_parent": "EXPLOSIVE_BASE", 
    "key": "tactical grenade",
    "aliases": ["tac grenade", "tactical"],
    "desc": "A tactical grenade with a shorter 5-second fuse for close-quarters combat.",
    "fuse_time": 5,
    "blast_damage": 20,
    "dud_chance": 0.02,  # More reliable
}

# High-damage demo charge
DEMO_CHARGE = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "HDG DX-15 demolition charge", 
    "aliases": ["charge", "demo", "dx-15", "dx15", "hdg demo", "demo charge", "c4"],
    "desc": "A Helios Defense Group DX-15 demolition charge - military-grade plastic explosive in a standardized one-kilogram block. The putty-like compound is stable enough to survive drops, fire, and even small-arms fire, but detonates with devastating force when triggered by the integrated electric blasting cap. The tan-colored explosive can be molded to fit against structural weak points, and the adhesive backing ensures it stays exactly where you place it. A digital timer/detonator is embedded in the block, offering settings from 10 seconds to 24 hours - though combat engineers rarely use anything longer than the minimum. When absolute structural destruction is required, whether it's breaching reinforced doors, collapsing tunnels, or eliminating hardened positions, the DX-15 delivers predictable, overwhelming force. HDG's technical documentation carefully avoids mentioning that this is the same compound used in shaped charges, improvised devices, and enough war crimes to fill a database.",
    "fuse_time": 10,
    "blast_damage": 40,
    "dud_chance": 0.01,  # Very reliable
}

# Flashbang (non-lethal)
FLASHBANG = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "flashbang",
    "aliases": ["flash", "stun grenade"],
    "desc": "A non-lethal stun grenade that produces a blinding flash and deafening bang.",
    "fuse_time": 6,
    "blast_damage": 5,  # Minimal damage, mainly stunning
    "dud_chance": 0.10,  # 10% dud chance
    "damage_type": "blunt",  # Concussion/pressure wave damage
}

# Smoke grenade (minimal damage)
SMOKE_GRENADE = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "smoke grenade",
    "aliases": ["smoke"],
    "desc": "A smoke grenade that creates a thick concealing cloud. Minimal explosive force.",
    "fuse_time": 4,
    "blast_damage": 2,  # Very low damage
    "dud_chance": 0.15,  # Higher dud chance
    "damage_type": "burn",  # Chemical irritation from smoke
}

# =============================================================================
# STICKY GRENADE PROTOTYPE (magnetic adhesion system)
# =============================================================================

# SPDR M9 - Spider-class magnetic adhesion grenade (repurposed mining tech)
STICKY_GRENADE = {
    "prototype_parent": "EXPLOSIVE_BASE",
    "key": "SPDR M9 grenade",
    "aliases": ["spdr", "spider grenade", "m9", "sticky grenade", "sticky"],
    "desc": "A SPDR M9 'Spider' - originally designed for breaching and clearing metallic ore deposits in asteroid mining operations. A compact black sphere bristling with eight telescoping articulated legs that extend on deployment. The moment it's thrown, tiny servos activate and the legs begin seeking ferrous metal surfaces with the single-minded purpose of industrial demolition equipment. Once proximity is achieved, powerful electromagnets pulse through the leg tips, causing them to skitter and latch onto the target with frightening precision. The magnetic adhesion is so strong that removing the stuck surface is the only way to separate yourself from the device. A soft blue LED pulses faster as detonation approaches. What was once a tool for breaking apart ore-rich asteroids has found a darker purpose in combat scenarios.",
    "fuse_time": 10,  # Longer fuse for tactical use
    "blast_damage": 30,
    "dud_chance": 0.02,  # Industrial reliability standards
    "damage_type": "laceration",
    # Sticky grenade specific attributes
    "is_sticky": True,
    "magnetic_strength": 8,  # 0-10 scale, determines stick threshold (mining-grade electromagnets)
    "stuck_to_armor": None,  # Reference to armor it's stuck to (runtime)
    "stuck_to_location": None,  # Body location where it's stuck (runtime)
}

# =============================================================================
# REMOTE DETONATOR PROTOTYPE
# =============================================================================

REMOTE_DETONATOR = {
    "key": "VECTOR UEM-3 detonator",
    "aliases": ["vector", "uem3", "uem-3", "detonator", "remote", "trigger"],
    "typeclass": "typeclasses.items.RemoteDetonator",
    "desc": "A VECTOR UEM-3 (Universal Explosive Module, Series 3) - a compact military-grade remote detonator with a matte black finish and angular, utilitarian design. Its digital display shows scanned explosive device signatures in crisp amber text. The device can store up to 20 explosive signatures simultaneously and trigger them remotely with surgical precision. A prominent red safety cover protects the main detonation switch, while smaller buttons below handle scanning and memory management. The VECTOR logo is subtly embossed on the casing, along with the serial number and dire warnings about unauthorized use.",
    "tags": [
        ("item", "general"),
        ("tool", "category"),
    ],
    "attrs": [
        ("scanned_explosives", []),  # List of explosive dbrefs
        ("max_capacity", 20),        # Maximum capacity
        ("device_type", "remote_detonator"),
    ]
}

# =============================================================================
# MELEE WEAPON PROTOTYPES (for grenade deflection testing)
# =============================================================================

# Base melee weapon
MELEE_WEAPON_BASE = {
    "prototype_key": "melee_weapon_base",
    "key": "melee weapon",
    "typeclass": "typeclasses.items.Item",
    "desc": "A weapon designed for close combat.",
    "tags": [
        ("weapon", "type"),
        ("melee", "category"),
        ("item", "general")
    ],
    "attrs": [
        ("is_ranged", False),  # Explicitly melee (though this is the default)
    ]
}

# Sword (standard deflection)
SWORD = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "sword",
    "aliases": ["blade"],
    "desc": "A well-balanced sword. Good for both combat and deflecting projectiles.",
    "damage": 10,
    "weapon_type": "long_sword",  # Using existing message type
    "damage_type": "cut",  # Medical system injury type
    "can_sever": True,  # Edged: can sever limbs from a corpse (PR #190)
}

# Baseball bat (enhanced deflection)
BASEBALL_BAT = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "baseball bat",
    "aliases": ["bat"],
    "desc": "A wooden baseball bat. Perfect for batting away incoming objects!",
    "damage": 8,
    "deflection_bonus": 0.30,  # +6 to deflection threshold (0.30 * 20)
    "weapon_type": "baseball_bat",  # Using existing message type
    "damage_type": "blunt",  # Medical system injury type
}

# Staff (good deflection)
STAFF = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "staff",
    "aliases": ["quarterstaff", "bo"],
    "desc": "A long wooden staff. Its reach makes it excellent for deflecting projectiles.",
    "damage": 7,
    "deflection_bonus": 0.10,  # +2 to deflection threshold (0.10 * 20)
    "weapon_type": "staff",  # Using existing message type
    "damage_type": "blunt",  # Medical system injury type
}

# Tennis Racket (excellent deflection!)
TENNIS_RACKET = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "tennis racket",
    "aliases": ["racket", "racquet"],
    "desc": "A professional tennis racket with tight strings and a lightweight frame. Perfect for returning serves... and grenades!",
    "damage": 5,  # Lower damage but amazing deflection
    "deflection_bonus": 0.50,  # +10 to deflection threshold (0.50 * 20) - BEST deflection weapon!
    "weapon_type": "tennis_racket",
    "damage_type": "blunt",  # Medical system injury type
    "hands": 1,
}

# Katana (legendary weapon of the samurai soul)
KATANA = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "katana",
    "aliases": ["sword", "blade", "japanese sword", "nihonto", "samurai sword"],
    "desc": "A legendary nihonto katana forged by a master swordsmith in the ancient traditions of the samurai. The curved, single-edged blade bears the distinctive hamon temper line like frozen lightning captured in tamahagane steel. Its razor-sharp ha (cutting edge) whispers promises of iai-jutsu and the Way of the Sword, while the sacred geometry of its curvature channels the very essence of bushido. The ray-skin wrapped tsuka handle, bound with silk ito in traditional diamond patterns, fits perfectly in the hand as if forged for your soul alone. This is not merely a weapon—it is the steel incarnation of honor, discipline, and the indomitable spirit of the warrior. To wield it is to walk the path of the samurai, where each cut carries the weight of a thousand generations of swordmasters. The blade seems to hum with latent spiritual energy, as if it remembers every duel, every moment of perfect technique, every drop of blood spilled in service to the code. In the right hands, this katana transcends mere metal to become an extension of one's very being—the soul made manifest in folded steel.",
    "damage": 14,
    "deflection_bonus": 0.25,  # +5 to deflection threshold (excellent for parrying)
    "weapon_type": "katana",  # Using existing katana message type
    "damage_type": "cut",  # Medical system injury type
    "can_sever": True,  # Edged: can sever limbs from a corpse (PR #190)
}

# Dagger (poor deflection)
DAGGER = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "dagger",
    "aliases": ["knife"],
    "desc": "A small, sharp dagger. Not ideal for deflecting larger objects.",
    "damage": 6,
    "deflection_bonus": -0.05,  # -1 to deflection threshold (penalty)
    "weapon_type": "knife",  # Using existing message type
    "damage_type": "stab",  # Medical system injury type
    "can_sever": True,  # Edged: can sever limbs from a corpse (PR #190)
}

# Tessen (iron war fan)
FIGHTING_FAN = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "fighting fan",
    "aliases": ["tessen", "iron fan", "fighting fan", "battle fan"],
    "desc": "A tessen war fan - deceptively elegant with its iron ribs concealed beneath decorative lacquer and silk panels. What appears to be a courtly accessory unfolds into a bladed weapon, each metal spine sharpened along its edge. The hinged ribs lock into position with a practiced snap, transforming ornament into armament. Favored by those who understood that the deadliest weapons are the ones your opponent doesn't see coming.",
    "damage": 7,
    "deflection_bonus": 0.15,  # +3 to deflection threshold (good defensive weapon)
    "weapon_type": "tessen",
    "damage_type": "cut",  # Medical system injury type
    "can_sever": True,  # Edged: can sever limbs from a corpse (PR #190)
}

# Chainsaw (devastating damage, no deflection)
CHAINSAW = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "chainsaw",
    "aliases": ["saw", "power saw"],
    "desc": "A gas-powered chainsaw with razor-sharp teeth. The engine sputters and growls, hungry for violence. Its mechanical brutality leaves no room for finesse.",
    "damage": 25,  # Extremely high damage
    "deflection_bonus": -0.50,  # -10 to deflection threshold (major penalty - chainsaws are terrible for defense)
    "weapon_type": "chainsaw",  # Using our newly converted message type
    "damage_type": "laceration",  # Medical system injury type
    "can_sever": True,  # Edged: can sever limbs from a corpse (PR #190)
}

# =============================================================================
# THROWING WEAPON PROTOTYPES
# =============================================================================

# Base throwing weapon
THROWING_WEAPON_BASE = {
    "prototype_key": "throwing_weapon_base",
    "key": "throwing weapon",
    "typeclass": "typeclasses.items.Item",
    "desc": "A weapon designed for throwing.",
    "tags": [
        ("weapon", "type"),
        ("throwing", "category"),
        ("item", "general")
    ],
    "attrs": [
        ("is_ranged", True),  # Throwing weapons are ranged weapons
        ("is_explosive", False),
        ("is_throwing_weapon", True),  # Dedicated throwing weapon - uses attack command
    ]
}

# Throwing knife
THROWING_KNIFE = {
    "prototype_parent": "THROWING_WEAPON_BASE",
    "key": "throwing knife",
    "aliases": ["knife", "blade"],
    "desc": "A balanced knife designed for throwing. Sharp and deadly.",
    "damage": 8,
    "attrs": [
        ("weapon_type", "throwing_knife"),
        ("damage_type", "stab"),  # Medical system injury type
    ]
}

# Throwing axe
THROWING_AXE = {
    "prototype_parent": "THROWING_WEAPON_BASE", 
    "key": "throwing axe",
    "aliases": ["axe", "hatchet"],
    "desc": "A heavy axe perfect for throwing. Deals significant damage on impact.",
    "damage": 12,
    "attrs": [
        ("weapon_type", "throwing_axe"),
        ("damage_type", "cut"),  # Medical system injury type
    ]
}

# Shuriken
SHURIKEN = {
    "prototype_parent": "THROWING_WEAPON_BASE",
    "key": "shuriken",
    "aliases": ["star", "ninja star"],
    "desc": "A traditional throwing star. Light and precise.",
    "damage": 6,
    "attrs": [
        ("weapon_type", "shuriken"),
        ("damage_type", "laceration"),  # Medical system injury type
    ]
}

# =============================================================================
# RANGED WEAPON PROTOTYPES (firearms and projectile weapons)
# =============================================================================

# Base ranged weapon
RANGED_WEAPON_BASE = {
    "prototype_key": "ranged_weapon_base",
    "key": "ranged weapon",
    "typeclass": "typeclasses.items.Item",
    "desc": "A weapon designed for ranged combat.",
    "tags": [
        ("weapon", "type"),
        ("ranged", "category"),
        ("item", "general")
    ],
    "attrs": [
        ("is_ranged", True),  # Ranged weapons
        ("hands_required", 2),  # Most firearms require two hands
        ("deflection_bonus", 0.0),  # Base deflection capability
    ]
}

# Light pistol (existing message type)
LIGHT_PISTOL = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "PAM Model 6 pistol",
    "aliases": ["pistol", "model 6", "m6", "pam pistol", "pam m6", "handgun", "9mm"],
    "desc": "A Pioneer Arms Manufacturing Model 6 pistol in 6mm - the ubiquitous sidearm of frontier colonies across human space. The polymer frame keeps weight down while the slide is precision-machined steel with a corrosion-resistant finish that stands up to harsh planetary environments. Fixed three-dot sights are robust and simple, requiring no batteries or adjustment. The trigger is heavy but predictable, designed for reliability over refinement. No frills, no unnecessary features - just a working person's pistol that starts every time and keeps running through dust, mud, and neglect. You'll find Model 9s in the holsters of security guards, cargo haulers, and frontier marshals across a thousand worlds. It's not the best pistol ever made, but it might be the most common.",
    "damage": 12,
    "attrs": [
        ("weapon_type", "light_pistol"),
        ("damage_type", "bullet"),  # Medical system injury type
        ("hands_required", 1),  # Pistols can be fired one-handed
    ]
}

# Heavy pistol (existing message type) 
HEAVY_PISTOL = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "HDG M88 tactical pistol",
    "aliases": ["M88", "m88", "hdg pistol", "tactical pistol", "heavy pistol", "magnum"],
    "desc": "A Helios Defense Group M88 tactical pistol chambered in 10mm caseless - maintaining ammunition commonality across HDG's entire product line. Unlike the compact VP9 or battle rifle M4RA, the M88 is built as a dedicated sidearm with refined ergonomics. The slide is machined from stainless steel with aggressive forward serrations and a loaded chamber indicator. The polymer frame features interchangeable backstraps and an integrated accessory rail. The match-grade barrel extends slightly beyond the slide, housed in a subtle compensator that controls muzzle rise during rapid fire. Night sights come standard, and the trigger breaks clean at four pounds. While the 10mm caseless round is somewhat overpowered for a pistol platform, the M88's robust construction handles it without complaint - and when you need a sidearm that hits like a rifle, HDG delivers.",
    "damage": 18,
    "attrs": [
        ("weapon_type", "heavy_pistol"),
        ("damage_type", "bullet"),  # Medical system injury type
        ("hands_required", 1),  # Can be fired one-handed but difficult
    ]
}

# Pump-action shotgun (existing message type)
PUMP_SHOTGUN = {
    "prototype_parent": "RANGED_WEAPON_BASE", 
    "key": "PAM Defender shotgun",
    "aliases": ["shotgun", "pump", "defender", "pam shotgun", "scattergun"],
    "desc": "A Pioneer Arms Manufacturing Defender pump-action shotgun in 12-gauge - found in homesteads, outposts, and frontier settlements galaxy-wide. The action is smooth and forgiving, designed to cycle even with cheap ammunition or light hand loads. The barrel is chrome-lined and the receiver is a single piece of investment-cast steel that could probably survive re-entry. Wood furniture shows honest wear, and the corn-cob forend fits hands in work gloves as easily as bare skin. An extended magazine tube holds seven shells, and the distinctive *chk-chk* of the pump is a sound that says 'property defended' in any language. Whether it's hostile wildlife, claim jumpers, or something worse in the dark, the Defender has protected three generations of colonists.",
    "damage": 20,
    "attrs": [
        ("weapon_type", "pump-action_shotgun"),
        ("damage_type", "bullet"),  # Medical system injury type
    ]
}

# Break-action shotgun (existing message type)
BREAK_SHOTGUN = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "PAM Reaper shotgun", 
    "aliases": ["reaper", "double-barrel", "coach gun", "pam reaper", "break shotgun", "boomstick"],
    "desc": "A Pioneer Arms Manufacturing Reaper - the double-barrel 12-gauge that earned its name in blood across a hundred frontier wars. The design is over four centuries old and hasn't needed improvement since. Two barrels, two triggers, two shells - everything else is just luxury. The barrels are chromed and the action is precisely fitted, breaking open with a satisfying mechanical *clack* and ejecting spent shells with authority. Checkered walnut stock and forend show the patina of hard use and generational transfer. At close range, both barrels fired simultaneously will stop anything that walks, crawls, or flies - and the Reaper has proven it against claim jumpers, pirates, hostile fauna, and things with too many limbs to count. When colonists need a last line of defense, they reach for the Reaper. The name isn't marketing - it's a reputation earned in the dirt.",
    "damage": 25,
    "attrs": [
        ("weapon_type", "break-action_shotgun"),
        ("damage_type", "bullet"),  # Medical system injury type
    ]
}

# Bolt-action rifle (existing message type)
BOLT_RIFLE = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "PAM Pathfinder rifle",
    "aliases": ["rifle", "pathfinder", "pam rifle", "bolt-action", "bolt rifle"],
    "desc": "A Pioneer Arms Manufacturing Pathfinder bolt-action rifle chambered in 7.62x51mm - the working rifle of choice for frontier scouts, hunters, and anyone who needs to reach out past the fence line. The action is a controlled-feed design that's smooth as glass and utterly reliable. The barrel is free-floated and cold-hammer-forged, capable of sub-MOA accuracy with quality ammunition. The synthetic stock is textured for grip and impervious to weather, while the steel receiver wears a matte finish that won't glare in harsh sunlight. A detachable box magazine holds five rounds, and the trigger adjusts from two to four pounds. Whether you're harvesting local fauna, defending livestock from predators, or putting down threats at distance, the Pathfinder delivers first-shot hits when it counts.",
    "damage": 22,
    "attrs": [
        ("weapon_type", "bolt-action_rifle"),
        ("damage_type", "bullet"),  # Medical system injury type
    ]
}

# Anti-material rifle (existing message type)  
ANTI_MATERIAL_RIFLE = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "HDG M82A3 anti-material rifle",
    "aliases": ["AMR", "M82A3", "anti-material rifle", "m82a3", "hdg amr"],
    "desc": "A Helios Defense Group M82A3 anti-material rifle chambered in 12.7x99mm. This massive weapon features a fluted bull barrel with an integrated muzzle brake that redirects gases upward to reduce felt recoil. The upper receiver is machined from a single billet of aircraft-grade aluminum, with a full-length Picatinny rail mounting a variable-power optic. A heavy-duty bipod clamps to the reinforced front rail section, and the buttstock incorporates a hydraulic recoil buffer and adjustable cheek rest. The entire system weighs nearly thirty pounds unloaded, and the carrying handle suggests HDG knows this weapon spends more time being transported than fired. Built to eliminate light vehicles, hardened positions, and targets at extreme range.",
    "damage": 35,
    "attrs": [
        ("weapon_type", "anti-material_rifle"),
        ("damage_type", "bullet"),  # Medical system injury type
        ("hands_required", 2),  # Requires bipod/support
    ]
}

# Assault rifle (if you have assault rifle messages)
ASSAULT_RIFLE = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "HDG M4RA pulse rifle", 
    "aliases": ["rifle", "M4RA", "pulse rifle", "pulse", "m4ra", "hdg"],
    "desc": "A Helios Defense Group M4RA pulse rifle chambered in 10mm caseless. The weapon's distinctive profile features a long barrel shroud with integrated electronic ammunition counter displaying in crisp amber numerals. The receiver is matte black composite with aggressive texturing, while the skeletal stock telescopes for compact carry. A charging handle protrudes from the right side of the upper receiver, and the trigger guard has been enlarged for gloved operation. The foregrip is ribbed polymer with heat-dissipation vents running along its length. Rail systems run along the top and sides of the handguard, currently mounting only iron sights but capable of accepting various optics and accessories. The whole assembly has the brutal, utilitarian aesthetic of military hardware designed for reliability under the worst possible conditions.",
    "damage": 15,
    "attrs": [
        ("weapon_type", "assault_rifle"),  # May need to create message file
        ("damage_type", "bullet"),  # Medical system injury type
    ]
}

# SMG/Submachine gun
SMG = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "HDG VP9 submachine gun",
    "aliases": ["SMG", "VP9", "vp9", "hdg smg", "submachine gun", "machine pistol"],
    "desc": "A Helios Defense Group VP9 submachine gun in 10mm caseless - the same ammunition as the M4RA rifle, allowing for simplified logistics in the field. The weapon is built around a compact bullpup design that keeps overall length minimal while maintaining a full-length barrel for accuracy. The polymer chassis is reinforced with internal steel rails, and the top-mounted charging handle can be swapped for left or right-hand operation. A folding vertical foregrip provides control during full-auto bursts, while the collapsible wire stock locks into three positions. The fire selector offers semi-auto, three-round burst, and full-auto modes. Compact, reliable, and sharing ammunition with half of HDG's product line - the VP9 excels in close-quarters engagements.",
    "damage": 10,
    "attrs": [
        ("weapon_type", "smg"),  # May need to create message file
        ("damage_type", "bullet"),  # Medical system injury type
        ("hands_required", 1),  # Can be fired one-handed
    ]
}

# =============================================================================
# UTILITY OBJECT PROTOTYPES (for non-combat throwing)
# =============================================================================

# Keys for testing utility throws
KEYRING = {
    "key": "keyring",
    "aliases": ["keys", "ring"],
    "desc": "A ring of various keys. Useful for testing throwing mechanics.",
    "typeclass": "typeclasses.objects.Object",
}

# Rock for testing
ROCK = {
    "key": "rock",
    "aliases": ["stone"],
    "desc": "A smooth throwing rock. Perfect for testing directional throws.",
    "typeclass": "typeclasses.objects.Object",
}

# Bottle for testing
BOTTLE = {
    "key": "bottle",
    "aliases": ["glass bottle"],
    "desc": "An empty glass bottle. Makes a satisfying crash when thrown.",
    "typeclass": "typeclasses.objects.Object",
}

# =============================================================================
# GRAFFITI SYSTEM PROTOTYPES
# =============================================================================

# Base spray paint can
SPRAYPAINT_CAN = {
    "prototype_key": "spraypaint_can",
    "key": "can of",
    "aliases": ["can", "paint", "spray", "spraycan", "spraypaint"],
    "typeclass": "typeclasses.items.SprayCanItem", 
    "desc": "A can of spraypaint with a red nozzle. It feels heavy with paint.",
    "attrs": [
        ("aerosol_level", 256),
        ("max_aerosol", 256),
        ("current_color", "red"),
        ("aerosol_contents", "spraypaint"),
        ("damage", 2),
        ("weapon_type", "spraycan"),
        ("damage_type", "burn"),  # Medical system injury type - chemical burn
        ("hands_required", 1)
    ],
    "tags": [
        ("graffiti", "type"),
        ("spray_can", "category"),
        ("item", "general")
    ]
}

# Solvent can for cleaning graffiti
SOLVENT_CAN = {
    "prototype_key": "solvent_can",
    "key": "can of",
    "aliases": ["solvent", "cleaner", "cleaning_can", "can"],
    "typeclass": "typeclasses.items.SolventCanItem",
    "desc": "A can of solvent for cleaning graffiti. It feels heavy with solvent.", 
    "attrs": [
        ("aerosol_level", 256),
        ("max_aerosol", 256),
        ("aerosol_contents", "solvent"),
        ("damage", 2),
        ("weapon_type", "spraycan"), 
        ("damage_type", "burn"),  # Medical system injury type - chemical burn
        ("hands_required", 1)
    ],
    "tags": [
        ("graffiti", "type"),
        ("solvent_can", "category"),
        ("item", "general")
    ]
}

# =============================================================================
# CLOTHING SYSTEM PROTOTYPES
# =============================================================================
"""
Clothing System Implementation Notes:

Phase 1 & 2 COMPLETE: Core infrastructure with dynamic styling and appearance integration
- Attribute-based clothing detection (coverage, layer, worn_desc)
- Multi-property styling system (adjustable + closure combinations)
- Coverage-based visibility masking of longdesc locations
- Inventory integration showing style states

LAYERING SYSTEM:
Layer 0: Direct skin contact (underwear, thin socks)
Layer 1: Base clothing (t-shirts, tactical undergarments)
Layer 2: Regular clothing (jeans, hoodies, regular shirts)
Layer 3: Footwear (boots, shoes - doesn't conflict with pants)
Layer 4: Light armor (plate carriers, kevlar vests)
Layer 5: Heavy armor (future: full plate, power armor)
Layer 6: Outer layers (future: coats, cloaks, ponchos)

FUTURE EXPANSION POSSIBILITIES:
- Phase 3: Advanced layer conflict resolution, staff targeting commands
- Material Physics: Durability, weather resistance, cleaning requirements
- Fashion Systems: NPC reactions based on clothing combinations/appropriateness
- Condition Tracking: Wear states, stains, damage affecting appearance/stats
- Social Mechanics: Dress codes, cultural clothing significance
- Seasonal Systems: Temperature comfort, weather protection
- Economic Integration: Clothing value, fashion trends affecting prices
- Magical Clothing: Enchantments, transformation items, stat bonuses

Current prototypes are proof-of-concept focusing on core mechanics.
"""

# Epic coder socks with dynamic styling capabilities
CODER_SOCKS = {
    "prototype_key": "CODER_SOCKS",
    "key": "rainbow coding socks",
    "aliases": ["socks", "coding socks", "rainbow socks"],
    "typeclass": "typeclasses.items.Item",
    "desc": "These magnificent thigh-high socks feature a gradient rainbow pattern with tiny pixelated hearts and coffee cups. The fabric shimmers with an almost magical quality, and they seem to pulse gently with RGB lighting effects. Every serious coder knows these provide +10 to programming ability.",
    "attrs": [
        # Basic clothing attributes
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin", "left_thigh", "right_thigh"]),
        ("worn_desc", "Electric {color}rainbow|n coding socks stretching up {their} thighs, {their} prismatic patterns pulsing with soft bioluminescent threads that seem to respond to neural activity"),
        ("layer", 0),  # Direct skin contact layer (underwear, thin socks)
        ("color", "bright_magenta"),
        ("material", "synthetic"),
        ("weight", 0.2),  # Very light
        
        # Style configuration for incredible transformation power
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "rolled": {
                    "coverage_mod": ["-left_thigh", "-right_thigh"],  # Rolled down to knee-high
                    "desc_mod": "Electric {color}rainbow|n coding socks bunched down around {their} knees, {their} compressed RGB fibers creating intense aurora-like cascades that paint the calves in shifting spectral light"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "Electric {color}rainbow|n coding socks stretching up {their} thighs, {their} LED matrices blazing at maximum intensity like fiber-optic constellations mapping the topology of pure computational ecstasy"
                },
                "unzipped": {
                    "coverage_mod": [],
                    "desc_mod": "Electric {color}rainbow|n coding socks stretching up {their} thighs, {their} bioluminescent patterns dimmed to a gentle ambient pulse that whispers of late-night debugging sessions and caffeine dreams"
                }
            }
        }),
        
        # Initial style state - full power mode!
        ("style_properties", {
            "adjustable": "normal",  # Full thigh-high
            "closure": "zipped"      # LEDs on full blast
        })
        
        # Future: combat stats for style-based intimidation, coder stat bonuses
        # Future tags: material properties, rarity systems, specialty gear recognition
    ],
    # Future: tags for NPC coder recognition, RGB lighting systems, legendary item mechanics  
    # "tags": [("clothing", "type"), ("socks", "category"), ("coder_gear", "specialty")]
}

# Stylish developer hoodie with hood functionality
DEV_HOODIE = {
    "prototype_key": "DEV_HOODIE", 
    "key": "black developer hoodie",
    "aliases": ["hoodie", "dev hoodie", "black hoodie"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A jet-black hoodie with 'rm -rf /' printed in small, ominous green text on the chest. The fabric is impossibly soft, and the hood seems designed to cast perfect dramatic shadows. Tiny LED threads are woven throughout, creating a subtle matrix-like pattern when activated.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("worn_desc", "A menacing {color}black|n developer hoodie draped loose and open, the cryptic green 'rm -rf /' text glowing with malevolent promise while embedded LED threads create subtle data-stream patterns across {their} fabric"),
        ("layer", 2),  # Regular clothing layer
        ("color", "black"),
        ("material", "cotton"),
        ("weight", 1.8),  # Moderate weight
        
        # Advanced styling - hood and LED modes
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""
                },
                "rolled": {
                    "coverage_mod": ["+head"],  # Hood up adds head coverage
                    "desc_mod": "A menacing {color}black|n developer hoodie with the hood pulled up like digital shadow incarnate, casting {their} face into mysterious darkness while green command-line text pulses ominously across {their} chest like a hacker's heartbeat"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A menacing {color}black|n developer hoodie zipped tight against the digital cold, LED matrix patterns cascading across the fabric like endless streams of compiled consciousness while 'rm -rf /' glows with quiet menace"
                },
                "unzipped": {
                    "coverage_mod": ["-chest"],  # Unzipped shows what's underneath
                    "desc_mod": "A menacing {color}black|n developer hoodie hanging open in calculated carelessness, revealing whatever lies beneath while {their} forbidden command-line incantation pulses with green malevolence against the darkness"
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal",    # Hood down initially  
            "closure": "unzipped"      # Casual mode
        })
        
        # Future: intimidation mechanics, focus bonuses, developer culture systems
        # Future tags: LED features, professional gear, meeting avoidance mechanics
    ],
    # Future: tags for developer NPC interactions, LED systems, professional contexts
    # "tags": [("clothing", "type"), ("hoodie", "category"), ("developer_gear", "specialty")]
}

# Canonical disguise item — the foundational red-flag head-covering.
# Demonstrates the full Phase 3 disguise surface in one prototype:
#   * is_disguise_item       → marks it as belonging to the disguise taxonomy
#   * disguise_essential     → contributes to the identity signature when worn
#   * disguise_type_id       → the per-type hash key (multiple balaclavas are
#                              indistinguishable; swapping one for another of
#                              the same type does NOT shift Apparent UID)
#   * disguise_adjective     → "masked" red-flag prefix in observer sdescs
#   * worn_sdesc_short       → brief noun phrase used in the distinguishing-
#                              feature clause (solo-disguise carve-out)
#   * coverage                → body locations the item hides; "hair" in the
#                              coverage list suppresses the hair fallback in
#                              the distinguishing-feature chain (replaces the
#                              legacy ``covers_hair`` boolean — see #176)
BALACLAVA = {
    "prototype_key": "BALACLAVA",
    "key": "black balaclava",
    "aliases": ["balaclava", "ski mask", "mask"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A heavy knit balaclava in matte black, woven tight enough to swallow detail. Only a narrow eye-slit interrupts the seamless coverage; the wearer's features collapse into shadow, and even hair colour is hidden by the snug pull of the fabric.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["hair", "head"]),
        ("worn_desc", "A snug {color}black|n balaclava pulled tight over {their} head, devouring features and hair alike behind a narrow eye-slit"),
        ("layer", 2),  # Regular clothing layer
        ("color", "black"),
        ("material", "wool"),
        ("weight", 0.2),

        # Disguise surface — see specs/IDENTITY_RECOGNITION_SPEC.md
        # §"Disguise Items" and §"Disguise Adjective".
        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "balaclava"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "black balaclava"),
    ],
}

# =========================================================================
# Disguise Catalog — Phase 3.5
# =========================================================================
#
# See specs/IDENTITY_RECOGNITION_SPEC.md §"Disguise Item Taxonomy".
#
# Two classes of disguise items:
#
# Class A — Visibly-obfuscating: carry a non-empty ``disguise_adjective``
#   that is injected into the wearer's sdesc as a red-flag prefix
#   ("masked", "hooded"). Observers see the disguise itself.
#
# Class B — Silent obfuscators: carry ``disguise_adjective=""`` so they
#   shift the Apparent UID without announcing themselves in the sdesc.
#   Wigs, contacts, and sunglasses fall here — disguise works precisely
#   because it does not call attention to itself.
#
# Both classes share ``is_disguise_item=True`` and
# ``disguise_essential=True``; the per-type ``disguise_type_id`` ensures
# same-type swaps (BALACLAVA ↔ SKI_MASK) do not shift the Apparent UID
# while cross-type swaps do.

# --- Class A: Visibly-obfuscating ----------------------------------------

# A second balaclava variant; shares ``disguise_type_id="balaclava"`` so
# swapping a BALACLAVA for a SKI_MASK is invisible to observers.
#
# disguise_type_id rationale: "balaclava" — shared with BALACLAVA.
# Both items fully obscure head and hair through dense knit; the
# narrow eye-slit / cut-outs read the same at observer distance.
# Swap-equivalent for Apparent UID purposes.
SKI_MASK = {
    "prototype_key": "SKI_MASK",
    "key": "wool ski mask",
    "aliases": ["ski mask", "mask", "balaclava"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A pull-on ski mask of coarse charcoal wool with three cut-outs — two for the eyes and one for the mouth — leaving everything between in featureless shadow. The weave is dense enough to obscure hair colour and jawline alike.",
    "attrs": [
        ("coverage", ["hair", "head", "face"]),
        ("worn_desc", "A coarse {color}charcoal|n ski mask drawn tight over {their} head, three ragged cut-outs the only break in featureless wool"),
        ("layer", 2),
        ("color", "charcoal"),
        ("material", "wool"),
        ("weight", 0.2),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "balaclava"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "wool ski mask"),
    ],
}

# Pale-blue surgical mask — covers nose and mouth, leaves eyes and hair
# untouched.
#
# disguise_type_id rationale: "face_mask" — deliberately distinct
# from RESPIRATOR's "respirator". The flat pleated profile reads
# completely differently from a bulky filtered respirator; collapsing
# them would let an observer who knows the wearer in a surgical mask
# fail to react to the same wearer in a gas mask. See
# test_disguise_prototypes.test_surgical_mask_and_respirator_distinct.
SURGICAL_MASK = {
    "prototype_key": "SURGICAL_MASK",
    "key": "pale-blue surgical mask",
    "aliases": ["surgical mask", "mask", "medical mask"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A standard pleated surgical mask in pale clinic-blue, looped over the ears with thin elastic. The pleats expand to cover nose, mouth and chin, leaving only the eyes and brow exposed.",
    "attrs": [
        ("coverage", ["face"]),
        ("worn_desc", "A pleated {color}pale-blue|n surgical mask hooked over {their} ears, smothering nose and mouth in clinical fabric"),
        ("layer", 2),
        ("color", "pale-blue"),
        ("material", "polypropylene"),
        ("weight", 0.05),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "face_mask"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "surgical mask"),
    ],
}

# Industrial half-face respirator — heavy rubber and twin filter cans.
#
# disguise_type_id rationale: "respirator" — deliberately distinct
# from SURGICAL_MASK's "face_mask". The twin filter cans and rubber
# harness create an unmistakable silhouette; not swap-equivalent
# with any other face-covering. See
# test_disguise_prototypes.test_surgical_mask_and_respirator_distinct.
RESPIRATOR = {
    "prototype_key": "RESPIRATOR",
    "key": "industrial respirator",
    "aliases": ["respirator", "gas mask", "mask"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A bulky half-face respirator moulded from matte-black rubber, twin filter cans jutting from the cheeks like stubby tusks. The harness straps cinch tight across the back of the skull and around the crown.",
    "attrs": [
        ("coverage", ["face"]),
        ("worn_desc", "A bulky {color}black|n industrial respirator strapped to {their} face, twin filter cans jutting like stubby tusks"),
        ("layer", 2),
        ("color", "black"),
        ("material", "rubber"),
        ("weight", 0.6),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "respirator"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "industrial respirator"),
    ],
}

# Slim domino mask — covers the eyes only, classic costume-party shape.
#
# disguise_type_id rationale: "domino_mask" — sole occupant of this
# slot; the satin upper-face cut is structurally unlike any other
# face-covering in the catalog.
DOMINO_MASK = {
    "prototype_key": "DOMINO_MASK",
    "key": "black domino mask",
    "aliases": ["domino mask", "mask", "eye mask"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A slim domino mask cut from black satin, shaped to cover the brow and the upper cheeks while leaving the lower face entirely free. A thin elastic loops behind the head; two almond-shaped slits frame the eyes.",
    "attrs": [
        ("coverage", ["left_eye", "right_eye"]),
        ("worn_desc", "A slim {color}black|n satin domino mask hugging the upper half of {their} face, two almond slits framing {their} eyes"),
        ("layer", 2),
        ("color", "black"),
        ("material", "satin"),
        ("weight", 0.05),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "domino_mask"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "domino mask"),
    ],
}

# Bandana worn outlaw-style across the lower face.
#
# disguise_type_id rationale: "face_bandana" — sole occupant. Knotted
# cloth across the lower face reads distinctly from a pleated
# medical mask or a moulded respirator; the loose triangle hangs and
# moves with the wearer in a way none of the other items do.
FACE_BANDANA = {
    "prototype_key": "FACE_BANDANA",
    "key": "red face bandana",
    "aliases": ["bandana", "face bandana", "kerchief"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A square of red cotton bandana, knotted outlaw-style across the lower face. The triangle of cloth covers nose, mouth and chin; the knot bunches behind the ears at the nape.",
    "attrs": [
        ("coverage", ["face"]),
        ("worn_desc", "A {color}red|n cotton bandana knotted outlaw-style across the lower half of {their} face"),
        ("layer", 2),
        ("color", "red"),
        ("material", "cotton"),
        ("weight", 0.1),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "face_bandana"),
        ("disguise_adjective", "masked"),
        ("worn_sdesc_short", "face bandana"),
    ],
}

# A standalone hood worn raised — separate from the DEV_HOODIE garment so
# the disguise hook can fire on a discrete wear/remove cycle without
# requiring a full hoodie style transition.
#
# disguise_type_id rationale: "hood" — sole occupant. A drawn hood
# casts shadow rather than obscuring with fabric directly; the
# silhouette is unmistakably "hooded" rather than "masked" and
# triggers a distinct disguise_adjective.
HOODIE_HOOD_UP = {
    "prototype_key": "HOODIE_HOOD_UP",
    "key": "drawn hood",
    "aliases": ["hood", "drawn hood"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A loose dark-grey hood, deep enough to swallow most of the wearer's face in shadow when raised. The drawstrings hang loose against the chest, and the lining is unbleached cotton softened by long use.",
    "attrs": [
        ("coverage", ["hair", "head"]),
        ("worn_desc", "A loose {color}dark-grey|n hood drawn forward over {their} head, casting {their} face into shadow"),
        ("layer", 3),
        ("color", "dark-grey"),
        ("material", "cotton"),
        ("weight", 0.3),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "hood"),
        ("disguise_adjective", "hooded"),
        ("worn_sdesc_short", "drawn hood"),
    ],
}

# --- Class B: Silent obfuscators -----------------------------------------
#
# These items shift the wearer's Apparent UID — making them unrecognisable
# to observers who only know the bare-faced form — but contribute no
# adjective to the rendered sdesc.  See PR #129 for the wig precedent.

BLACK_WIG = {
    "prototype_key": "BLACK_WIG",
    "key": "black wig",
    "aliases": ["wig", "black wig"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A shoulder-length wig of glossy jet-black synthetic hair, cut to a blunt fringe. The mesh cap is fine enough to pass for a natural hairline at conversational distance.",
    "attrs": [
        ("coverage", ["hair", "head"]),
        ("worn_desc", "A glossy {color}black|n shoulder-length wig with a blunt fringe"),
        ("layer", 2),
        ("color", "black"),
        ("material", "synthetic"),
        ("weight", 0.15),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        # disguise_type_id rationale: "wig" — shared across all three
        # wig prototypes (BLACK_WIG, BLOND_WIG, BROWN_WIG). All wigs
        # read as "wearing a wig" at observer distance; the color is
        # appearance (skintone-style flavour), not an identity-class
        # distinction. Swapping one wig for another of a different
        # colour does NOT shift the Apparent UID — but going from
        # bare-headed to wigged DOES (the disguise_essential flag is
        # what flips the signature, not the per-colour type id).
        ("disguise_type_id", "wig"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "black wig"),
    ],
}

# disguise_type_id rationale: "wig" — shared with BLACK_WIG and
# BROWN_WIG. See BLACK_WIG above for the full rationale on why colour
# is flavour rather than an identity-class distinction.
BLOND_WIG = {
    "prototype_key": "BLOND_WIG",
    "key": "blond wig",
    "aliases": ["wig", "blond wig", "blonde wig"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A chin-length blond wig in honey-gold synthetic fibre, layered for volume. The cap is mesh-lined and the parting has been hand-stitched to mimic a real scalp.",
    "attrs": [
        ("coverage", ["hair", "head"]),
        ("worn_desc", "A honey-{color}blond|n chin-length wig layered for volume"),
        ("layer", 2),
        ("color", "gold"),
        ("material", "synthetic"),
        ("weight", 0.15),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "wig"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "blond wig"),
    ],
}

# disguise_type_id rationale: "wig" — shared with BLACK_WIG and
# BLOND_WIG. See BLACK_WIG above for the full rationale.
BROWN_WIG = {
    "prototype_key": "BROWN_WIG",
    "key": "brown wig",
    "aliases": ["wig", "brown wig"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A mid-length brown wig in walnut-toned synthetic fibre, parted off-centre. The cap is a soft stretch mesh and the ends have been heat-set into a loose wave.",
    "attrs": [
        ("coverage", ["hair", "head"]),
        ("worn_desc", "A walnut-{color}brown|n mid-length wig parted off-centre with loose waves"),
        ("layer", 2),
        ("color", "brown"),
        ("material", "synthetic"),
        ("weight", 0.15),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "wig"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "brown wig"),
    ],
}

# Cosmetic contact lenses — change apparent eye colour silently.
#
# disguise_type_id rationale: "contacts" — sole occupant. Contacts sit
# on the eye itself and read only as eye colour to observers; they are
# silent (no adjective, no distinguishing-feature clause) and there is
# no second contact-class prototype to collapse with. A future tinted-
# lens variant in a different colour would still share "contacts" —
# colour is flavour, not an identity-class distinction (same precedent
# as the three wigs sharing "wig").
COLORED_CONTACTS = {
    "prototype_key": "COLORED_CONTACTS",
    "key": "colored contact lenses",
    "aliases": ["contacts", "lenses", "contact lenses"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A blister-pack pair of cosmetic contact lenses in vivid emerald green. The pigment ring covers the iris completely; pupils show through unaltered.",
    "attrs": [
        ("coverage", ["left_eye", "right_eye"]),
        ("worn_desc", "Cosmetic contact lenses tinting {their} eyes vivid emerald"),
        ("layer", 1),
        ("color", "emerald"),
        ("material", "hydrogel"),
        ("weight", 0.01),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "contacts"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "colored contacts"),
        # Sub-visible: contacts sit on the eye — observers register eye
        # colour, not "in colored contacts."  Excluded from the
        # distinguishing-feature clause while remaining in the disguise
        # / Apparent UID system (swap detection, recognition memory).
        ("disguise_silent_feature", True),
    ],
}

# Mirrorshade aviators — opaque chrome lenses, classic shape.
#
# disguise_type_id rationale: "mirrorshades" — deliberately distinct
# from AVIATOR_SUNGLASSES ("sunglasses"). The mirrored chrome finish
# is unmistakable at observer distance: lenses read as a reflective
# silver pane rather than tinted glass. An observer who has memorised
# a target in mirrorshades would not be fooled into thinking they had
# swapped to gold-framed smoke-tint aviators (or vice versa). Both
# share the aviator silhouette, but the lens finish is the salient
# identity feature, not the frame shape. Compare with SURGICAL_MASK
# vs RESPIRATOR: same principle — silhouette overlap is not enough to
# collapse the type id when the visible signature differs sharply.
MIRRORSHADES = {
    "prototype_key": "MIRRORSHADES",
    "key": "chrome mirrorshades",
    "aliases": ["mirrorshades", "shades", "sunglasses", "glasses"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A pair of mirrorshade aviators with a chrome-coated finish so dense the lenses throw back the room as a warped silver pane. The frames are thin gunmetal wire, the bridge a single arched bar.",
    "attrs": [
        ("coverage", ["left_eye", "right_eye"]),
        ("worn_desc", "A pair of {color}chrome|n mirrorshades reflecting the room as a warped silver pane"),
        ("layer", 2),
        ("color", "chrome"),
        ("material", "metal"),
        ("weight", 0.08),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "mirrorshades"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "mirrorshades"),
    ],
}

# disguise_type_id rationale: "sunglasses" — deliberately distinct
# from MIRRORSHADES ("mirrorshades"). Smoke-tinted teardrop lenses in
# a gold wire frame read as conventional sunglasses; the eyes are
# obscured but the lenses are not reflective. See MIRRORSHADES above
# for the full rationale on why lens finish (not frame silhouette)
# governs eyewear type identity.
AVIATOR_SUNGLASSES = {
    "prototype_key": "AVIATOR_SUNGLASSES",
    "key": "aviator sunglasses",
    "aliases": ["aviators", "sunglasses", "glasses", "shades"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A pair of aviator sunglasses with teardrop-shaped smoke-tinted lenses and a thin gold frame. The lenses are dark enough to obscure the eyes but translucent enough to read intent through.",
    "attrs": [
        ("coverage", ["left_eye", "right_eye"]),
        ("worn_desc", "A pair of {color}gold|n-framed aviator sunglasses with teardrop smoke-tinted lenses"),
        ("layer", 2),
        ("color", "gold"),
        ("material", "metal"),
        ("weight", 0.08),

        ("is_disguise_item", True),
        ("disguise_essential", True),
        ("disguise_type_id", "sunglasses"),
        ("disguise_adjective", ""),
        ("worn_sdesc_short", "aviator sunglasses"),
    ],
}

# Classic blue jeans with functional styling
BLUE_JEANS = {
    "prototype_key": "BLUE_JEANS",
    "key": "blue jeans",
    "aliases": ["jeans", "pants", "denim"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A classic pair of medium-wash blue jeans with a comfortable fit. The denim is soft from years of wear, with subtle fading at the knees and pockets. Five-pocket styling with sturdy copper rivets at stress points.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Battle-tested {color}denim|n jeans that cling to {their} form with urban authority, {their} faded indigo surface scarred by countless encounters with concrete and circumstance"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 2),  # Regular clothing layer
        ("color", "blue"),
        ("material", "denim"),
        ("weight", 1.5),  # Moderate weight
        
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "rolled": {
                    "coverage_mod": ["-left_shin", "-right_shin"],
                    "desc_mod": "Battle-tested {color}denim|n jeans with cuffs deliberately rolled up to mid-calf in street-smart defiance, exposing {their} scarred ankles and the promise of swift movement when the situation demands it"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "unzipped": {
                    "coverage_mod": ["-groin"],
                    "desc_mod": "Battle-tested {color}denim|n jeans hanging loose with dangerous nonchalance, {their} undone fly creating a calculated statement of rebellion against the oppressive tyranny of proper dress codes"
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal",
            "closure": "zipped"
        })
        
        # Future: durability/wear system, comfort affects stats, style bonuses
        # Future tags: material properties, fashion categories, condition tracking
    ],
    # Future: tags for material physics, fashion systems, NPC reactions
    # "tags": [("clothing", "type"), ("pants", "category"), ("denim", "material")]
}

# Simple cotton t-shirt 
COTTON_TSHIRT = {
    "prototype_key": "COTTON_TSHIRT",
    "key": "white cotton t-shirt",
    "aliases": ["shirt", "t-shirt", "tshirt", "tee"],
    "typeclass": "typeclasses.items.Item", 
    "desc": "A simple white cotton t-shirt with a classic crew neck. The fabric is soft and breathable, perfect for everyday wear. The shoulders and hem show the clean lines of quality construction.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A deceptively simple {color}white|n cotton t-shirt that seems to absorb and reflect the ambient light of {their} urban environment, its clean lines and perfect fit suggesting either careful maintenance or recent acquisition"),
        ("coverage", ["chest", "back", "abdomen"]),
        ("layer", 1),  # Base clothing layer (worn under hoodies/jackets)
        ("color", "white"),
        ("material", "cotton"),
        ("weight", 0.4),  # Light weight
        
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "rolled": {
                    "coverage_mod": ["-abdomen"],
                    "desc_mod": "A deceptively simple {color}white|n cotton t-shirt deliberately rolled up at the hem to expose {their} midriff, the casual gesture somehow managing to convey both vulnerability and confident defiance of conventional modesty"
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal"
        })
        
        # Future: fabric physics, stain resistance, NPC fashion reactions  
        # Future tags: material breathability, wash cycles, social contexts
    ],
    # Future: tags for clothing care systems, fashion mechanics, NPC interactions
    # "tags": [("clothing", "type"), ("shirt", "category"), ("cotton", "material")]
}

# Tactical leather combat boots with lacing
COMBAT_BOOTS = {
    "prototype_key": "COMBAT_BOOTS",
    "key": "black leather combat boots",
    "aliases": ["boots", "combat boots", "leather boots"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Heavy-duty black leather combat boots with steel-reinforced toes and deep tread soles. The leather is scuffed from use but well-maintained, with military-style speed lacing running up to mid-calf. Perfect for urban warfare or intimidating accountants.",
    
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Imposing {color}black leather|n combat boots laced with military precision, {their} steel-reinforced toes and deep-tread soles speaking of {their} owner's serious intent while weathered leather tells stories of urban warfare and late-night foot chases"),
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin"]),
        ("layer", 3),  # Footwear layer (doesn't conflict with pants)
        ("color", "black"),
        ("material", "leather"),
        
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc (laced tight)
                },
                "unzipped": {
                    "coverage_mod": ["-left_shin", "-right_shin"],
                    "desc_mod": "Imposing {color}black leather|n combat boots with speed-laces hanging in deliberate disarray, {their} unlaced tongues flopping open to reveal glimpses of tactical readiness beneath the facade of casual indifference"
                }
            }
        }),
        
        ("style_properties", {
            "closure": "zipped"  # Laced tight by default
        })
        
        # Future: armor rating, movement speed modifiers, intimidation bonuses
        # Future tags: leather durability, tactical gear, weather resistance
    ],
    # Future: tags for combat systems, material physics, professional contexts  
    # "tags": [("clothing", "type"), ("boots", "category"), ("leather", "material")]
}


# =============================================================================
# ARMOR PROTOTYPES (CLOTHING WITH ARMOR ATTRIBUTES)
# =============================================================================

# =============================================================================
# TACTICAL UNIFORM BASE LAYERS (Light Protection)
# =============================================================================

# Tactical Jumpsuit - Base layer with minimal protection
TACTICAL_JUMPSUIT = {
    "key": "tactical jumpsuit",
    "aliases": ["jumpsuit", "coveralls", "tactical suit"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A form-fitting tactical jumpsuit made from reinforced synthetic weave. Provides minimal protection while maintaining maximum mobility and comfort.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen", "groin", "left_arm", "right_arm", "left_thigh", "right_thigh", "left_shin", "right_shin", "left_foot", "right_foot"]),
        ("worn_desc", "A sleek {color}black|n tactical jumpsuit that hugs their form like a second skin, its reinforced synthetic weave providing minimal protection while prioritizing mobility and tactical flexibility"),
        ("layer", 1),  # Base clothing layer (worn under armor)
        ("color", "black"),
        ("material", "synthetic"),
        ("weight", 1.8),  # Lightweight
        
        # Minimal armor
        ("armor_rating", 1),
        ("armor_type", "synthetic"),
        ("armor_durability", 20),
        ("max_armor_durability", 20),
        ("base_armor_rating", 1),
        
        # Sticky grenade properties (synthetic fabric - no metal)
        ("metal_level", 0),      # No metal content
        ("magnetic_level", 0),   # No magnetic response
    ],
}

# Tactical Pants - Alternative to jumpsuit
TACTICAL_PANTS = {
    "key": "tactical pants",
    "aliases": ["pants", "tactical trousers", "combat pants"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Heavy-duty tactical pants with reinforced knees and multiple cargo pockets. Made from ripstop fabric with minimal ballistic protection.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("worn_desc", "Durable {color}black|n tactical pants with reinforced knees and cargo pockets, their ripstop fabric providing minimal protection while maintaining tactical functionality"),
        ("layer", 1),  # Base clothing layer (worn under armor)
        ("color", "black"),
        ("material", "synthetic"),
        ("weight", 1.2),
        
        # Minimal armor
        ("armor_rating", 1),
        ("armor_type", "synthetic"),
        ("armor_durability", 20),
        ("max_armor_durability", 20),
        ("base_armor_rating", 1),
        
        # Sticky grenade properties (synthetic fabric - no metal)
        ("metal_level", 0),      # No metal content
        ("magnetic_level", 0),   # No magnetic response
    ],
}

# Tactical Shirt - Upper body base layer
TACTICAL_SHIRT = {
    "key": "tactical shirt",
    "aliases": ["shirt", "tactical tee", "combat shirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A tactical shirt with moisture-wicking fabric and reinforced shoulders. Designed to be worn under armor systems.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("worn_desc", "A practical {color}black|n tactical shirt with moisture-wicking fabric, its reinforced shoulders and minimal protection designed to serve as a foundation for armor systems"),
        ("layer", 1),  # Base clothing layer (worn under armor)
        ("color", "black"),
        ("material", "synthetic"),
        ("weight", 0.8),
        
        # Minimal armor
        ("armor_rating", 1),
        ("armor_type", "synthetic"),
        ("armor_durability", 20),
        ("max_armor_durability", 20),
        ("base_armor_rating", 1),
        
        # Sticky grenade properties (synthetic fabric - no metal)
        ("metal_level", 0),      # No metal content
        ("magnetic_level", 0),   # No magnetic response
    ],
}

# =============================================================================
# MODULAR PLATE CARRIER SYSTEM
# =============================================================================

# Basic Plate Carrier - Modular platform
PLATE_CARRIER = {
    "key": "plate carrier",
    "aliases": ["carrier", "vest", "tactical vest"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A modular plate carrier system with front and back plate pockets, side plate slots, and tactical webbing. Designed to accept ballistic plates for customizable protection levels.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen"]),
        ("worn_desc", "A professional {color}tan|n plate carrier with tactical webbing and modular plate pockets, its adjustable straps and MOLLE system creating a foundation for serious ballistic protection"),
        ("layer", 4),  # Light armor layer
        ("color", "tan"),
        ("material", "nylon"),
        ("weight", 2.5),  # Just the carrier itself
        
        # Base protection (carrier only)
        ("armor_rating", 2),        # Minimal protection without plates
        ("armor_type", "synthetic"), # Basic synthetic protection
        ("armor_durability", 40),
        ("max_armor_durability", 40),
        ("base_armor_rating", 2),
        
        # Plate carrier system
        ("is_plate_carrier", True),
        ("plate_slots", ["front", "back", "left_side", "right_side"]),
        ("installed_plates", {}),   # Empty initially
        ("plate_slot_coverage", {
            "front": ["chest"],
            "back": ["back"],
            "left_side": ["abdomen"],
            "right_side": ["abdomen"]
        }),
        
        # Style system for tactical adjustments
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {"coverage_mod": ["-abdomen"], "desc_mod": "A professional {color}tan|n plate carrier with the lower section rolled up for improved mobility, its tactical webbing still providing modular attachment points"}
            }
        }),
        ("style_properties", {"adjustable": "normal"}),
        
        # Sticky grenade properties (nylon carrier - minimal metal from buckles/clips)
        ("metal_level", 1),      # Minimal metal (buckles, clips)
        ("magnetic_level", 1),   # Minimal magnetic (some steel hardware)
    ],
}

# =============================================================================
# ARMOR PLATES (For Plate Carriers)
# Universal fit - trade protection for weight/durability
# =============================================================================

# Lightweight Plate - Mobility focused
LIGHTWEIGHT_PLATE = {
    "key": "lightweight plate",
    "aliases": ["light plate", "mobility plate", "composite plate"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A lightweight composite armor plate prioritizing mobility. Sacrifices some protection for reduced weight, ideal for fast response scenarios.",
    "attrs": [
        # Not worn directly - installed in carriers
        ("coverage", []),
        ("layer", 0),  # Not a clothing layer
        ("weight", 1.8),  # Lightest option
        ("material", "composite"),
        
        # Plate properties
        ("is_armor_plate", True),
        ("plate_class", "lightweight"),  # Instead of size
        ("armor_rating", 5),        # Lower protection
        ("armor_type", "composite"),
        ("armor_durability", 100),  # Lower durability
        ("max_armor_durability", 100),
        ("base_armor_rating", 5),
        
        # Sticky grenade properties (composite - some metal, non-magnetic)
        ("metal_level", 4),      # Some metal content (aluminum backing)
        ("magnetic_level", 0),   # Non-magnetic (aluminum/composite)
    ],
}

# Standard Plate - Balanced protection
STANDARD_PLATE = {
    "key": "standard plate",
    "aliases": ["plate", "ballistic plate", "armor plate", "ceramic plate"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A standard ballistic plate made from advanced ceramic composite. Offers excellent protection against rifle rounds while maintaining reasonable weight.",
    "attrs": [
        # Not worn directly - installed in carriers
        ("coverage", []),
        ("layer", 0),  # Not a clothing layer
        ("weight", 3.2),  # Balanced weight
        ("material", "ceramic"),
        
        # Plate properties
        ("is_armor_plate", True),
        ("plate_class", "standard"),  # Instead of size
        ("armor_rating", 7),        # Good protection
        ("armor_type", "ceramic"),
        ("armor_durability", 140),
        ("max_armor_durability", 140),
        ("base_armor_rating", 7),
        
        # Sticky grenade properties (ceramic with steel backing)
        ("metal_level", 6),      # Moderate metal (steel backing plate)
        ("magnetic_level", 5),   # Moderate magnetic (steel backing)
    ],
}

# Reinforced Plate - Maximum protection
REINFORCED_PLATE = {
    "key": "reinforced plate",
    "aliases": ["heavy plate", "steel plate", "assault plate"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A heavy reinforced steel ballistic plate offering maximum protection. Significantly heavier than alternatives but nearly indestructible in combat scenarios.",
    "attrs": [
        ("coverage", []),
        ("layer", 0),
        ("weight", 8.5),  # Heaviest option
        ("material", "steel"),
        
        ("is_armor_plate", True),
        ("plate_class", "reinforced"),  # Instead of size
        ("armor_rating", 9),        # Maximum protection
        ("armor_type", "steel"),
        ("armor_durability", 180),  # Highest durability
        ("max_armor_durability", 180),
        ("base_armor_rating", 9),
        
        # Sticky grenade properties (solid steel plate - HIGHLY magnetic)
        ("metal_level", 10),     # Maximum metal content (solid steel)
        ("magnetic_level", 10),  # Maximum magnetic (ferrous steel)
    ],
}

# High-Performance Trauma Plate - Specialist option
CERAMIC_PLATES = {
    "key": "trauma plate",
    "aliases": ["ceramic plate", "trauma insert", "ceramic insert"],
    "typeclass": "typeclasses.items.Item",
    "desc": "An advanced ceramic trauma plate using cutting-edge materials. Extremely effective against high-velocity rounds but brittle - shatters after absorbing significant damage.",
    "attrs": [
        # Not worn directly - installed in carriers
        ("coverage", []),
        ("layer", 0),  # Not a clothing layer
        ("weight", 4.0),  # Heavy ceramic
        ("material", "ceramic"),
        
        # Plate properties
        ("is_armor_plate", True),
        ("plate_class", "trauma"),  # Specialist class
        ("armor_rating", 10),       # Maximum protection
        ("armor_type", "ceramic"),  # Excellent vs bullets, degrades quickly
        ("armor_durability", 50),   # Low durability - shatters after absorbing damage
        ("max_armor_durability", 50),
        ("base_armor_rating", 10),
        
        # Sticky grenade properties (advanced ceramic - minimal magnetic)
        ("metal_level", 3),      # Minimal metal (titanium backing)
        ("magnetic_level", 0),   # Non-magnetic (ceramic/titanium)
    ],
}

# =============================================================================
# LEGACY ARMOR (Updated with Weight)
# =============================================================================

# Base prototype for armor items (avoids inheriting weapon tags)
ARMOR_BASE = {
    "prototype_key": "armor_base",
    "key": "armor",
    "typeclass": "typeclasses.items.Item",
    "desc": "A piece of protective armor.",
    "tags": [
        ("armor", "type"),
        ("item", "general")
    ],
}

# Tactical Kevlar Vest - Excellent bullet protection
KEVLAR_VEST = {
    "prototype_parent": "ARMOR_BASE",
    "key": "kevlar vest",
    "aliases": ["vest", "body armor", "bulletproof vest"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A lightweight tactical kevlar vest with trauma plates. Designed to stop bullets while maintaining mobility.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen"]),
        ("worn_desc", "A professional {color}black|n kevlar vest with trauma plates, its tactical webbing and ballistic panels speaking of serious protection against projectile threats"),
        ("layer", 4),  # Light armor layer
        ("color", "black"),
        ("material", "kevlar"),
        ("weight", 4.5),  # Moderate weight
        
        # Armor attributes
        ("armor_rating", 8),        # High armor rating
        ("armor_type", "kevlar"),   # Excellent vs bullets, poor vs stabs
        ("armor_durability", 160),  # Rating * 20
        ("max_armor_durability", 160),
        ("base_armor_rating", 8),
        
        # Combat stats
        ("deflection_bonus", -0.05),  # Slight penalty to deflection (bulky)
        
        # Sticky grenade properties (kevlar with steel trauma plates)
        ("metal_level", 7),      # High metal (embedded steel plates)
        ("magnetic_level", 6),   # High magnetic (steel trauma plates)
    ],
}

# =============================================================================
# BEE HIVE ARMORED COVERALL - Swarm-Themed Tactical Armor
# =============================================================================

BEE_HIVE_COVERALL = {
    "key": "HIVE-MIND Mark VII coverall",
    "aliases": ["hive coverall", "bee armor", "hive-mind", "swarm suit", "bee suit"],
    "typeclass": "typeclasses.items.Item",
    "desc": (
        "A HIVE-MIND Mark VII tactical coverall that defies conventional armor design philosophy with its revolutionary bio-mimetic approach. "
        "The entire surface is covered in thousands of hexagonal ceramic composite cells arranged in a perfect honeycomb lattice, each cell "
        "independently articulated on microscopic servo-actuators that create a constantly shifting, organic movement across the armor's surface. "
        "The base color is a deep amber-gold that seems to glow from within, overlaid with bold black striping patterns that flow across the torso, "
        "arms, and legs in asymmetric warning coloration that triggers primal recognition responses in observers.\n\n"
        "Embedded bioluminescent fibers pulse gently beneath the hexagonal cells, creating the illusion of thousands of worker bees moving just "
        "beneath the surface—an effect that becomes more pronounced in low light, where the entire suit seems to writhe with insectile life. "
        "The collar area features raised ridges that mimic the segmented thorax of a bee, while the back incorporates subtle wing-like panels "
        "that serve both aesthetic and heat-dissipation purposes.\n\n"
        "Most unsettling are the micro-speakers distributed throughout the suit's surface, which emit a constant low-frequency buzz that can be "
        "felt in the bones more than heard—a psychological warfare tool that triggers instinctive flight responses in those nearby. The manufacturer's "
        "documentation suggests this 'harmonic resonance system' was inspired by defensive bee swarm behavior, creating an auditory territoriality "
        "field that makes opponents unconsciously maintain distance.\n\n"
        "The armor's smart-material construction allows the hexagonal cells to lock rigid on impact, distributing force across the entire lattice "
        "structure like a hive distributing the workload among workers. Each cell can also independently adjust its angle to deflect incoming "
        "projectiles, creating a surface that seems to flow and redirect attacks rather than simply absorb them. The overall effect is of wearing "
        "a living colony—beautiful, alien, and deeply disturbing in its implication that the wearer has merged with the swarm."
    ),
    "attrs": [
        # Clothing attributes - full body coverage like jumpsuit
        ("coverage", ["chest", "back", "abdomen", "groin", "left_arm", "right_arm", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("worn_desc", (
            "A mesmerizing HIVE-MIND Mark VII coverall coating {their} form in thousands of articulating hexagonal amber-and-black cells "
            "that ripple and shift like a living bee colony, the constant low-frequency buzz emanating from its surface making the air "
            "itself seem to vibrate with barely-contained aggression while bioluminescent patterns pulse beneath the honeycomb lattice "
            "like worker bees moving through dark corridors"
        )),
        ("layer", 4),  # Light armor layer (same as plate carrier/kevlar)
        ("color", "amber"),  # Amber-gold primary color
        ("material", "ceramic_composite"),  # Advanced materials
        ("weight", 6.8),  # Heavier than kevlar, lighter than steel plate
        
        # Armor attributes - excellent distributed protection
        ("armor_rating", 7),        # Very good protection (between kevlar and steel)
        ("armor_type", "ceramic"),  # Ceramic composite - excellent vs projectiles
        ("armor_durability", 140),  # Rating * 20
        ("max_armor_durability", 140),
        ("base_armor_rating", 7),
        
        # Combat stats - the hexagonal lattice has interesting properties
        ("deflection_bonus", 0.15),  # +3 to deflection (cells redirect impacts!)
        
        # Sticky grenade properties (ceramic composite with minimal metal framework)
        ("metal_level", 3),      # Low metal (internal framework only)
        ("magnetic_level", 0),   # Non-magnetic (ceramic/titanium construction)
        
        # Style system for bee armor
        ("style_configs", {
            "adjustable": {
                "normal": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "rolled": {
                    "coverage_mod": ["-left_shin", "-right_shin"],
                    "desc_mod": (
                        "A mesmerizing HIVE-MIND Mark VII coverall with lower sections rolled up to expose {their} calves, "
                        "the exposed hexagonal cells at the roll line still pulsing with bioluminescent patterns as if "
                        "the hive extends beyond what's visible, worker bees still toiling in phantom corridors"
                    )
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc - sealed and buzzing
                },
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": (
                        "A mesmerizing HIVE-MIND Mark VII coverall hanging partially open to reveal {their} torso beneath, "
                        "the separated hexagonal cells along the zipper line reorganizing themselves in real-time like "
                        "a hive adapting to structural damage, their golden bioluminescence dimmed but still pulsing "
                        "with patient, insectile purpose"
                    )
                }
            }
        }),
        
        ("style_properties", {
            "adjustable": "normal",
            "closure": "zipped"  # Fully sealed for maximum swarm effect
        })
    ],
}

# Steel Plate Armor - Medieval style, excellent all-around protection
PLATE_MAIL = {
    "prototype_parent": "ARMOR_BASE",
    "key": "plate mail",
    "aliases": ["steel plate mail", "steel plate armor", "plate armor", "steel armor"],
    "typeclass": "typeclasses.items.Item", 
    "desc": "Heavy steel plate armor forged in overlapping segments. Provides excellent protection but restricts movement significantly.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("worn_desc", "Imposing {color}steel|n plate armor that encases their torso and arms in overlapping metal segments, each piece precisely fitted and articulated for maximum protection while maintaining combat mobility"),
        ("layer", 5),  # Heavy armor layer (over plate carriers and other armor)
        ("color", "bright_white"),  # Polished steel
        ("material", "steel"),
        ("weight", 25.0),  # Very heavy
        
        # Armor attributes
        ("armor_rating", 10),       # Maximum armor rating
        ("armor_type", "steel"),    # Excellent vs everything except fire/chemicals
        ("armor_durability", 200),  # Rating * 20
        ("max_armor_durability", 200),
        ("base_armor_rating", 10),
        
        # Combat penalties
        ("deflection_bonus", -0.15),  # Significant deflection penalty (very bulky)
        
        # Sticky grenade properties (solid steel plate armor - MAXIMUM)
        ("metal_level", 10),     # Maximum metal (solid steel plates)
        ("magnetic_level", 10),  # Maximum magnetic (ferrous steel)
    ],
}

# Leather Jacket - Light armor, good vs cuts
ARMORED_LEATHER_JACKET = {
    "prototype_parent": "ARMOR_BASE",
    "key": "armored leather jacket",
    "aliases": ["jacket", "leather armor", "biker jacket"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A heavy leather jacket reinforced with steel studs and padding. Provides moderate protection while maintaining style.",
    "attrs": [
        # Clothing attributes  
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("worn_desc", "A reinforced {color}black leather|n jacket studded with steel reinforcements, its thick hide and metal accents providing street-smart protection without sacrificing the rebellious aesthetic of urban warfare"),
        ("layer", 2),
        ("color", "black"),
        ("material", "leather"),
        ("weight", 3.2),  # Moderate weight
        
        # Style system for leather jacket
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A reinforced {color}black leather|n jacket zipped tight and studded with steel reinforcements, its thick hide creating a defensive shell around their torso"
                },
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A reinforced {color}black leather|n jacket hanging open to reveal whatever lies beneath, steel studs and thick hide still providing partial protection to their back and arms"
                }
            }
        }),
        ("style_properties", {"closure": "zipped"}),
        
        # Armor attributes
        ("armor_rating", 5),        # Moderate armor rating
        ("armor_type", "leather"),  # Good vs cuts, poor vs bullets
        ("armor_durability", 100),  # Rating * 20
        ("max_armor_durability", 100),
        ("base_armor_rating", 5),
        
        # Combat stats
        ("deflection_bonus", 0.05),  # Slight deflection bonus (flexible)
        
        # Sticky grenade properties (leather with decorative studs)
        ("metal_level", 2),      # Minimal metal (some decorative studs)
        ("magnetic_level", 1),   # Minimal magnetic (small steel studs)
    ],
}

# Combat Helmet - Head protection (skull/crown only, face exposed)
COMBAT_HELMET = {
    "prototype_parent": "ARMOR_BASE",
    "key": "combat helmet",
    "aliases": ["helmet", "tactical helmet"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A military-grade combat helmet with ballistic protection for the skull. The open-face design provides excellent visibility and hearing while protecting the crown and sides of the head.",
    "attrs": [
        # Clothing attributes
        ("coverage", ["head", "left_ear", "right_ear"]),  # Protects skull and ears, but face/eyes/jaw exposed
        ("worn_desc", "A menacing {color}matte black|n tactical helmet with ballistic protection, its angular design and integrated electronics creating an intimidating visage of military precision"),
        ("layer", 2),
        ("color", "black"),
        ("material", "kevlar"),
        ("weight", 1.8),  # Light weight
        
        # Armor attributes
        ("armor_rating", 7),        # High head protection
        ("armor_type", "kevlar"),   # Good vs bullets
        ("armor_durability", 20),   # Moderate durability
        ("max_armor_durability", 20),
        ("base_armor_rating", 7),
        
        # Sticky grenade properties (kevlar with composite shell)
        ("metal_level", 3),      # Low metal (mounting hardware)
        ("magnetic_level", 2),   # Low magnetic (minimal steel clips)
    ],
}

# =============================================================================  
# REPAIR TOOL PROTOTYPES (FOR ARMOR MAINTENANCE)
# =============================================================================

# Sewing Kit - Best for leather armor
SEWING_KIT = {
    "key": "sewing kit",
    "aliases": ["kit", "needles", "thread"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A comprehensive sewing kit with heavy-duty needles, reinforced thread, and leather patches. Perfect for repairing fabric and leather armor.",
    "attrs": [
        ("repair_tool_type", "sewing_kit"),
        ("tool_durability", 25),
        ("max_tool_durability", 25),
    ],
}

# Metalworking Tools - Best for steel armor  
METALWORK_TOOLS = {
    "key": "metalworking tools",
    "aliases": ["tools", "hammer", "anvil", "metalwork"],
    "typeclass": "typeclasses.items.Item", 
    "desc": "A set of metalworking tools including a small anvil, hammer, tongs, and files. Essential for repairing steel and metal armor components.",
    "attrs": [
        ("repair_tool_type", "metalwork_tools"),
        ("tool_durability", 30),
        ("max_tool_durability", 30),
    ],
}

# Ballistic Repair Kit - Best for kevlar
BALLISTIC_REPAIR_KIT = {
    "key": "ballistic repair kit",
    "aliases": ["ballistic kit", "kevlar kit", "fiber kit"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A specialized kit for repairing ballistic armor, containing aramid fibers, ballistic gel, and precision tools for working with advanced protective materials.",
    "attrs": [
        ("repair_tool_type", "ballistic_repair_kit"),
        ("tool_durability", 15),  # Specialized but fragile
        ("max_tool_durability", 15),
    ],
}

# Ceramic Repair Compound - Best for ceramic plates
CERAMIC_REPAIR_COMPOUND = {
    "key": "ceramic repair compound",
    "aliases": ["compound", "ceramic paste", "armor compound"],
    "typeclass": "typeclasses.items.Item",
    "desc": "An advanced ceramic repair compound that can restore cracked trauma plates. Requires precise application and technical expertise to use effectively.",
    "attrs": [
        ("repair_tool_type", "ceramic_repair_compound"),
        ("tool_durability", 8),   # Very specialized, limited uses
        ("max_tool_durability", 8),
    ],
}

# Generic Tool Kit - Moderate for all armor types
GENERIC_TOOL_KIT = {
    "key": "tool kit",
    "aliases": ["tools", "repair kit", "general tools"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A general-purpose tool kit with basic implements for field repairs. Not specialized for any particular material, but versatile enough for emergency fixes.",
    "attrs": [
        ("repair_tool_type", "generic_tools"),
        ("tool_durability", 20),
        ("max_tool_durability", 20),
    ],
}

# Workshop Bench - For full repairs (location-based)
ARMOR_WORKBENCH = {
    "key": "armor workbench", 
    "aliases": ["workbench", "bench", "workshop"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A professional armor repair workbench equipped with specialized tools, proper lighting, and workspace for comprehensive armor restoration. Enables full repair capabilities.",
    "attrs": [
        ("repair_tool_type", "workshop_bench"),
        ("tool_durability", 1000),  # Extremely durable, permanent installation
        ("max_tool_durability", 1000),
        ("workshop_tool", True),    # Special flag for full repairs
    ],
}

# =============================================================================
# MEDICAL ITEM PROTOTYPES
# =============================================================================

# IV Blood Bag - Emergency blood transfusion
BLOOD_BAG = {
    "key": "blood bag",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["iv", "blood", "transfusion"],
    "desc": "A sterile IV blood bag with attached tubing for emergency transfusion. Contains 500ml of universal donor blood.",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "blood_restoration"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 1),
        ("application_time", 1),
        ("effectiveness", {
            "bleeding": 9,        # Excellent for severe bleeding
            "blood_loss": 10,     # Perfect for blood restoration
            "shock": 7,          # Good for shock treatment
            "organ_damage": 3,   # Limited help for organs
        })
    ],
}

# Injectable Painkiller - Multi-dose pain management
PAINKILLER = {
    "key": "painkiller",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["syringe", "morphine", "pain meds"],
    "desc": "A medical syringe containing powerful analgesic medication. Multiple doses available.",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "pain_relief"),
        ("uses_left", 3),
        ("max_uses", 3),
        ("stat_requirement", 0),
        ("application_time", 1),
        ("effectiveness", {
            "pain": 9,           # Excellent pain relief
            "shock": 6,          # Moderate shock treatment
            "bleeding": 2,       # Minimal bleeding help
            "fracture": 4,       # Some fracture pain relief
        })
    ],
}

# Gauze Bandages - Multi-use wound dressing
GAUZE_BANDAGES = {
    "key": "gauze bandages",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["gauze", "bandages", "dressing"],
    "desc": "Sterile gauze bandages for wound dressing and bleeding control. Multiple applications available.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method"), ("bandage", "delivery_method")],
    "attrs": [
        ("medical_type", "wound_care"),
        ("uses_left", 5),
        ("max_uses", 5),
        ("stat_requirement", 0),
        ("application_time", 1),
        ("effectiveness", {
            "bleeding": 7,       # Very good bleeding control
            "infection": 8,      # Excellent infection prevention  
            "wound_healing": 6,  # Good wound protection
            "pain": 3,           # Minimal pain relief
        })
    ],
}

# Medical Splint - Single-use bone stabilization
SPLINT = {
    "key": "medical splint",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["splint", "brace"],
    "desc": "A universal medical splint that adapts to immobilize fractured appendages. Works on arms, legs, tentacles, wings, and other limbs.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "fracture_treatment"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 2),
        ("application_time", 2),
        ("effectiveness", {
            "fracture": 8,       # Excellent fracture stabilization
            "pain": 4,           # Some pain relief
            "mobility": 6,       # Restores some movement
            "bleeding": 2,       # Minimal bleeding help
        })
    ],
}

# Tourniquet - Reusable limb bleeding control (#509)
TOURNIQUET = {
    "key": "tourniquet",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["tq", "strap"],
    "desc": "A windlass-and-strap tourniquet for clamping off catastrophic limb bleeding. Stops any bleed it can reach cold — but nothing heals under it, and the wound reopens the moment it comes off without proper treatment. Limbs only.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "tourniquet"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 0),
        ("application_time", 1),
    ],
}

# Cybernetic Tail - first anatomy augment (ANATOMY_AUGMENTS_SPEC, #511)
CYBERNETIC_TAIL = {
    "key": "cybernetic tail",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["cybertail", "tail unit"],
    "desc": "A segmented cybernetic tail, coiled in its mounting cradle. Articulated alloy vertebrae taper to a prehensile tip; the mount plate at the base is machined to bolt against a human thoracolumbar spine. Surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        # Anatomy carried on the item (spec §3.3).  The organ spec is
        # complete — augments have no species-table entry, so this
        # dict IS the anatomy.  Bone-typed: splints brace a bent
        # actuator column the same way they brace a femur.
        ("augment_organs", {
            "cybernetic_tailbone": {
                "container": "tail", "max_hp": 25, "hit_weight": "common",
                "can_be_destroyed": True,
                "fracture_vulnerable": True, "bone_type": "actuator_column",
                "severable_container": True,
                "grasping": True,
                "inorganic": True,
            },
        }),
        ("augment_container", "tail"),
        ("augment_anchor", "back"),
        ("augment_longdesc", {
            "key": "tail",
            "default_desc": "A segmented cybernetic tail sways at the base of the spine, alloy vertebrae clicking softly when it moves.",
            "display_after": "back",
        }),
        # The established cyberware species gate (the same field
        # harvest provenance sets) — synth expansion is editing this
        # list, no code.
        ("compatible_species", ["human"]),
    ],
}

# Cybernetic Heart - first spec-carrying replacement organ (#526 M1)
# Installs into the canonical "heart" slot via the standard
# replacement path (incise chest -> install -> suture).  Same organ
# NAME so the blood_pumping capacity wiring is untouched; the SPEC
# makes it chrome — inorganic (no bleed, no sepsis), sturdier than
# meat.
CYBERNETIC_HEART = {
    "key": "cybernetic heart",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber heart", "pump unit"],
    "desc": "A fist-sized cardiac replacement unit, its impeller housing machined from surgical alloy and its mounting collar ringed with vascular couplers. It does one thing, forever, without being asked.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "heart"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "chest", "max_hp": 20, "hit_weight": "uncommon",
            "vital": True, "capacity": "blood_pumping",
            "contribution": "total",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True,
        }),
    ],
}

# Cybernetic Arm - side-agnostic limb chassis (#526 M2/M3)
# One prototype mounts left OR right: the surgeon names the side and
# every {side} template resolves from it.  Organs keep CANONICAL
# names ({side}_humerus etc.) so capacity wiring survives — the SPEC
# makes them chrome.  The forearm hardpoint is an empty module slot:
# weapons/tools seat into it via `install <module> in <target>`.
CYBER_ARM = {
    "key": "cybernetic arm",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["cyber arm", "prosthetic arm", "arm unit"],
    "desc": "A full arm replacement unit in its transport cradle, shoulder coupling to fingertips, ambidextrous mounting hardware along the seam. The forearm housing carries an empty modular hardpoint behind an access panel — the chassis is honest work; what goes in the slot is the owner's business. Mounts over an amputated arm, either side; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("augment_organs", {
            "{side}_humerus": {
                "container": "{side}_arm", "max_hp": 30,
                "hit_weight": "common", "capacity": "manipulation",
                "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_column", "inorganic": True,
            },
            "{side}_metacarpals": {
                "container": "{side}_hand", "max_hp": 18,
                "hit_weight": "uncommon", "capacity": "manipulation",
                "contribution": "moderate", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_lattice", "inorganic": True,
            },
            "{side}_forearm_hardpoint": {
                "container": "{side}_arm", "max_hp": 10,
                "hit_weight": "rare", "inorganic": True,
                "hardpoint": "forearm",
            },
        }),
        ("augment_container", "{side}_arm"),
        ("augment_anchor", "{side}_arm"),
        ("augment_longdesc", [
            {
                "key": "{side}_arm",
                "default_desc": "A full cybernetic arm, matte composite plating over an actuator column, an access panel seam running the length of the forearm.",
            },
            {
                "key": "{side}_hand",
                "default_desc": "An articulated alloy hand, five-fingered and precise, the knuckle plating worn smooth.",
                "display_after": "{side}_arm",
            },
        ]),
        ("compatible_species", ["human"]),
    ],
}

# Shotgun Module - forearm hardpoint weapon (#526 M3)
# Seats into any free forearm hardpoint, either side — it inherits
# its side from the slot.  Harvest recovers it from a limb or corpse
# as this same item.
SHOTGUN_MODULE = {
    "key": "shotgun module",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["arm shotgun module", "weapon module"],
    "desc": "A combat shotgun folded into a forearm-hardpoint form factor: barrel shroud, feed system, and deployment servos packed into a unit the size of a forearm bone. The coupling collar is standard chassis gauge. It wants a slot.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "forearm"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "{side}_arm", "max_hp": 12, "hit_weight": "rare",
            "inorganic": True,
            "hardpoint": "forearm", "module_type": "forearm",
            "abilities": {
                "shotgun": {
                    "type": "integrated_weapon",
                    "slot": "{side}_hand",
                    "weapon_prototype": "SHOTGUN_ARM_GUN",
                    "deploy_msg": "Your {side} forearm splits along its seam and the shotgun rotates up into place — the hand folds back and away, and the barrel is just *there*, like it always was.",
                    "retract_msg": "The shotgun swings down and folds along the actuator column; plating closes over it and your fingers flex, a hand again.",
                    "deploy_room": "{actor}'s forearm splits open with a snap of locking servos — a shotgun barrel rotates up out of the housing where their hand used to be.",
                    "retract_room": "{actor}'s arm-shotgun folds away into the forearm housing; plating seals and their hand reassembles, fingers flexing.",
                },
            },
        }),
    ],
}

# The integrated weapon the shotgun arm deploys (#516).  Spawned
# lazily on first /shotgun; locked + flagged integrated by the
# ability layer regardless of what's declared here.
SHOTGUN_ARM_GUN = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "arm-mounted shotgun",
    "aliases": ["arm shotgun", "armgun"],
    "desc": "A combat shotgun built into a cybernetic forearm — short, shrouded, and inseparable from the arm that carries it. The barrel shroud doubles as the forearm's structural plating, and the feed system disappears somewhere into the elbow. There is no stock, no grip, no sling mount: the weapon is the limb.",
    "damage": 20,
    "locks": "get:false();drop:false();give:false()",
    "attrs": [
        ("weapon_type", "cybernetic_shotgun"),
        ("damage_type", "bullet"),  # Medical system injury type
        ("hands_required", 1),      # It IS the hand
        ("integrated", True),
    ],
}

# Surgical Kit - Advanced multi-use medical tools
SURGICAL_KIT = {
    "key": "surgical kit",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["surgery", "medical kit", "scalpel"],
    "desc": "A comprehensive surgical kit containing scalpels, sutures, clamps, and other advanced medical tools. Requires significant medical training.",
    "tags": [("medical_item", "item_type")],
    "attrs": [
        ("medical_type", "surgical_treatment"),
        ("uses_left", 10),
        ("max_uses", 10),
        ("stat_requirement", 3),
        ("application_time", 3),
        ("effectiveness", {
            "organ_damage": 10,  # Perfect for internal injuries
            "internal_bleeding": 9, # Excellent for internal bleeding
            "complex_wounds": 8, # Very good for complex injuries
            "infection": 7,      # Good sterile procedures
            "pain": 5,           # Moderate pain management
        })
    ],
}

# Surgical Sealant (#307, PR-D) - In-procedure organ repair compound.
# Single-dose ampule of biocompatible tissue sealant.  Applied
# directly to damaged organ tissue during open surgical procedures
# to bond and seal lacerations.  Inert and useless on closed skin —
# the system tolerates the application per the substance-tolerance
# principle, but the ``organ_repair`` effect only lands when the
# wound's container has an open incision.  Apply via:
#
#     apply surgical sealant on bob's chest
#
# during an incise → harvest/install → suture procedure to repair
# the damaged organ inside.
SURGICAL_SEALANT = {
    "key": "surgical sealant",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["sealant", "tissue sealant", "bioseal"],
    "desc": "A single-dose ampule of biocompatible tissue sealant. Applied directly to damaged organ tissue during open procedures to bond and seal lacerations. Inert on closed skin; requires an active surgical field to do anything meaningful.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "organ_repair"),
        ("uses_left", 3),
        ("max_uses", 3),
        ("stat_requirement", 3),
        ("application_time", 2),
        ("effectiveness", {
            "organ_repair":  8,  # Headline: instant HP refund on success
            "infection":     7,  # Sterile bond reduces post-op infection
            "wound_healing": 5,  # Modest slow-tick contribution
            "bleeding":      3,  # Some bond-mediated bleeding control
            "pain":          1,  # Negligible
        })
    ],
}

# Emergency Stimpak - Rapid healing injection
STIMPAK = {
    "key": "stimpak",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["stim", "healing injection"],
    "desc": "An emergency medical stimulant that accelerates natural healing processes. Single-use auto-injector.",
    "tags": [("medical_item", "item_type")],
    "attrs": [
        ("medical_type", "healing_acceleration"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 1),
        ("application_time", 1),
        ("effectiveness", {
            "wound_healing": 8,  # Excellent healing boost
            "bleeding": 6,       # Good bleeding control
            "pain": 7,           # Very good pain relief
            "organ_damage": 4,   # Limited organ help
            "fatigue": 9,        # Excellent energy restoration
        })
    ],
}

# Antiseptic Spray - Infection prevention
ANTISEPTIC = {
    "key": "antiseptic spray",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["antiseptic", "disinfectant", "spray"],
    "desc": "Medical-grade antiseptic spray for wound cleaning and infection prevention. Multiple applications per bottle.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "antiseptic"),
        ("uses_left", 8),
        ("max_uses", 8),
        ("stat_requirement", 0),
        ("application_time", 1),
        ("effectiveness", {
            "infection": 9,      # Excellent infection prevention
            "wound_healing": 5,  # Moderate healing assistance
            "bleeding": 3,       # Minimal bleeding help
            "pain": 2,           # Slight pain relief
        })
    ],
}

# ===================================================================
# PHASE 2.5: INHALATION & SMOKING MEDICAL ITEMS
# ===================================================================

OXYGEN_TANK = {
    "key": "oxygen tank",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["oxygen", "o2", "tank"],
    "desc": "Portable oxygen tank with breathing mask. Essential for respiratory emergencies and consciousness recovery.",
    "tags": [("medical_item", "item_type"), ("inhale", "delivery_method")],
    "attrs": [
        ("medical_type", "oxygen"),
        ("uses_left", 10),
        ("max_uses", 10),
        ("stat_requirement", 0),
        ("application_time", 1),
        ("effectiveness", {
            "consciousness": 9,      # Excellent consciousness boost
            "breathing_difficulty": 8, # Great respiratory help
            "suffocation": 10,       # Perfect suffocation treatment
        })
    ],
}

STIMPAK_INHALER = {
    "key": "stimpak inhaler",
    "typeclass": "typeclasses.items.Item", 
    "aliases": ["inhaler", "stimpak vapor", "medical inhaler"],
    "desc": "Pressurized inhaler containing vaporized stimpak for rapid respiratory absorption. Single use only.",
    "tags": [("medical_item", "item_type"), ("inhale", "delivery_method")],
    "attrs": [
        ("medical_type", "vapor"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 1),
        ("application_time", 2),
        ("effectiveness", {
            "pain": 7,           # Good pain relief
            "blood_loss": 6,     # Moderate blood restoration
            "breathing_difficulty": 5, # Some respiratory help
        })
    ],
}

ANESTHETIC_GAS = {
    "key": "anesthetic gas",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["anesthetic", "knockout gas", "medical gas"],
    "desc": "Medical anesthetic gas canister. Reduces pain but may cause drowsiness. Use with caution.",
    "tags": [("medical_item", "item_type"), ("inhale", "delivery_method")],
    "attrs": [
        ("medical_type", "anesthetic"),
        ("uses_left", 5),
        ("max_uses", 5),
        ("stat_requirement", 2),
        ("application_time", 2),
        ("effectiveness", {
            "pain": 9,           # Excellent pain relief
            "consciousness": -2,  # Reduces consciousness (side effect)
        })
    ],
}

MEDICINAL_HERB = {
    "key": "medicinal herb",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["herb", "healing herb", "dried herb"],
    "desc": "Dried medicinal herb that can be smoked for natural pain relief and calming effects. Organic treatment option.",
    "tags": [("medical_item", "item_type"), ("smoke", "delivery_method")],
    "attrs": [
        ("medical_type", "herb"),
        ("uses_left", 3),
        ("max_uses", 3),
        ("stat_requirement", 0),
        ("application_time", 3),
        ("effectiveness", {
            "pain": 6,           # Good natural pain relief
            "stress": 7,         # Excellent stress relief
            "anxiety": 6,        # Good anxiety reduction
        })
    ],
}

PAIN_RELIEF_CIGARETTE = {
    "key": "pain relief cigarette",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["med cigarette", "medical cigarette", "pain cigarette"],
    "desc": "Specially formulated cigarette infused with mild pain-relieving compounds. For medicinal use only.",
    "tags": [("medical_item", "item_type"), ("smoke", "delivery_method")],
    "attrs": [
        ("medical_type", "cigarette"),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 0),
        ("application_time", 4),
        ("effectiveness", {
            "pain": 4,           # Mild pain relief
            "stress": 3,         # Minor stress relief
        })
    ],
}

# =============================================================================
# RECREATIONAL SUBSTANCE PROTOTYPES (#487)
# =============================================================================
# Substance pharmacology lives in world/substances/registry.py; these
# items just carry the substance id + delivery tag (spec §1/§2).

HAND_ROLLED_JOINT = {
    "key": "hand-rolled joint",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["joint", "spliff"],
    "desc": "A crooked hand-rolled joint, packed with sweet-smelling "
            "resinous flower. The paper crackles when squeezed.",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "cannabis"),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

ROTGUT_BOTTLE = {
    "key": "bottle of rotgut",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["rotgut", "bottle", "booze"],
    "desc": "An unlabeled glass bottle of harsh colonial liquor. It "
            "smells like fuel and bad decisions, in that order.",
    "tags": [("drink", "delivery_method")],
    "attrs": [
        ("substance", "alcohol"),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

OPIUM_CIGARETTE = {
    "key": "tar-black opium cigarette",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["opium cigarette", "opium", "tar cigarette"],
    "desc": "A thin cigarette rolled around tar-black resin. Heavy, "
            "sweet, and patient — it will wait as long as you can.",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "opium"),
        ("uses_left", 3),
        ("max_uses", 3),
    ],
}

GUTTERVENOM_SYRINGE = {
    "key": "syringe of guttervenom",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["guttervenom", "venom syringe", "toxin"],
    "desc": "A scratched autoinjector filled with murky, iridescent "
            "fluid. The label has been deliberately scraped off.",
    "tags": [("inject", "delivery_method")],
    "attrs": [
        ("substance", "guttervenom"),
        ("uses_left", 1),
        ("max_uses", 1),
    ],
}

# =============================================================================
# SHOP MERCHANT PROTOTYPES
# =============================================================================

# Base merchant template - holographic shopkeeper
HOLOGRAPHIC_MERCHANT = {
    "key": "holographic merchant",
    "typeclass": "typeclasses.characters.Character",
    "desc": "A shimmering holographic projection of a merchant. The figure flickers slightly, clearly not real.",
    "attrs": [
        ("is_merchant", True),
        ("is_holographic", True),
        ("merchant_greeting", "Welcome to the shop. Browse my wares."),
    ],
    "locks": "get:false();puppet:false()",
}

# Example armory merchant
ARMORY_MERCHANT = {
    "prototype_parent": "HOLOGRAPHIC_MERCHANT",
    "key": "Gunther the Armorer",
    "desc": "A burly holographic figure in tactical gear, arms crossed. The projection glitches occasionally, revealing the emitter underneath.",
    "attrs": [
        ("merchant_greeting", "Need weapons? You've come to the right place."),
        ("merchant_specialty", "weapons and armor"),
    ],
}

# Example general goods merchant
GENERAL_MERCHANT = {
    "prototype_parent": "HOLOGRAPHIC_MERCHANT",
    "key": "Sal the Supplier",
    "desc": "A friendly-looking holographic merchant with a wide smile. The projection flickers blue-green.",
    "attrs": [
        ("merchant_greeting", "Everything you need, right here!"),
        ("merchant_specialty", "general supplies"),
    ],
}

# Example medical supplies merchant
MEDIC_MERCHANT = {
    "prototype_parent": "HOLOGRAPHIC_MERCHANT",
    "key": "Dr. Voss",
    "desc": "A stern holographic figure in a white coat, clipboard in hand. The projection is sharp and professional.",
    "attrs": [
        ("merchant_greeting", "Medical supplies. No prescriptions required."),
        ("merchant_specialty", "medical supplies"),
    ],
}

# Example corner store merchant
CORNERSTORE_MERCHANT = {
    "prototype_parent": "HOLOGRAPHIC_MERCHANT",
    "key": "Juan Sanchez",
    "desc": "A flamboyant holographic merchant with wild hair and an elaborate mustache. His garish outfit shifts between purple and gold as the projection flickers. He gestures dramatically even in stillness.",
    "attrs": [
        ("merchant_greeting", "Welcome, my friend! I have everything you need - and some things you don't!"),
        ("merchant_specialty", "general goods"),
    ],
}

# =============================================================================
# SHOP CONTAINER PROTOTYPES
# =============================================================================

# Base shop container template
SHOP_CONTAINER_BASE = {
    "prototype_key": "shop_container_base",
    "typeclass": "typeclasses.shopkeeper.ShopContainer",
    "locks": "get:false();puppet:false()",
    "attrs": [
        ("is_infinite", True),
        ("markup_percent", 0),
        ("shop_name", "Shop"),
        ("container_type", "shelf"),
        ("prototype_inventory", {}),
        ("item_inventory", {}),
    ],
}

# Weapons shop shelf
WEAPONS_SHELF = {
    "prototype_parent": "shop_container_base",
    "key": "weapons rack",
    "desc": "A sturdy metal weapons rack displaying various implements of violence. Everything from blades to firearms.",
    "attrs": [
        ("shop_name", "Armory"),
        ("container_type", "rack"),
        ("markup_percent", 15),  # 15% markup on weapons
        ("prototype_inventory", {
            "KATANA": 500,
            "SWORD": 250,
            "DAGGER": 80,
            "CHAINSAW": 800,
            "STAFF": 150,
            "BASEBALL_BAT": 60,
            "TENNIS_RACKET": 120,
        }),
    ],
}

# Explosives shop crate
EXPLOSIVES_CRATE = {
    "prototype_parent": "shop_container_base",
    "key": "reinforced crate",
    "desc": "A heavily reinforced military crate with warning labels. Contains various explosive devices - handle with extreme care.",
    "attrs": [
        ("shop_name", "Demolitions Supply"),
        ("container_type", "crate"),
        ("markup_percent", 25),  # 25% markup on dangerous goods
        ("prototype_inventory", {
            "FRAG_GRENADE": 150,
            "TACTICAL_GRENADE": 200,
            "DEMO_CHARGE": 500,
            "FLASHBANG": 100,
            "SMOKE_GRENADE": 75,
            "STICKY_GRENADE": 300,
            "REMOTE_DETONATOR": 250,
        }),
    ],
}

# Armor shop display
ARMOR_DISPLAY = {
    "prototype_parent": "shop_container_base",
    "key": "armor display",
    "desc": "A professional display stand showcasing various protective gear and tactical equipment.",
    "attrs": [
        ("shop_name", "Tactical Outfitters"),
        ("container_type", "display"),
        ("markup_percent", 20),  # 20% markup on armor
        ("prototype_inventory", {
            "KEVLAR_VEST": 800,
            "PLATE_CARRIER": 600,
            "PLATE_MAIL": 1500,
            "ARMORED_LEATHER_JACKET": 400,
            "COMBAT_HELMET": 350,
            "LIGHTWEIGHT_PLATE": 200,
            "STANDARD_PLATE": 350,
            "REINFORCED_PLATE": 600,
            "CERAMIC_PLATES": 500,
            "BEE_HIVE_COVERALL": 1200,  # Premium exotic armor
        }),
    ],
}

# Clothing shop rack
CLOTHING_RACK = {
    "prototype_parent": "shop_container_base",
    "key": "clothing rack",
    "desc": "A sleek chrome clothing rack displaying various garments from tactical to casual wear.",
    "attrs": [
        ("shop_name", "Street Fashion"),
        ("container_type", "rack"),
        ("markup_percent", 10),  # 10% markup on clothing
        ("prototype_inventory", {
            "CODER_SOCKS": 50,
            "DEV_HOODIE": 80,
            "BLUE_JEANS": 60,
            "COTTON_TSHIRT": 25,
            "COMBAT_BOOTS": 120,
            "TACTICAL_JUMPSUIT": 150,
            "TACTICAL_PANTS": 70,
            "TACTICAL_SHIRT": 50,
        }),
        # Integration settings - embeds shop in room description
        ("integrate", True),
        ("integration_desc", "A sleek chrome clothing rack displays various street fashion items, from coding socks to tactical gear."),
        ("integration_priority", 2),
    ],
}

# Medical supplies cabinet
MEDICAL_CABINET = {
    "prototype_parent": "shop_container_base",
    "key": "medical supply cabinet",
    "desc": "A sterile white medical cabinet with glass doors. Stocked with various emergency medical supplies.",
    "attrs": [
        ("shop_name", "Medical Supplies"),
        ("container_type", "cabinet"),
        ("markup_percent", 30),  # 30% markup on medical (premium)
        ("prototype_inventory", {
            "BLOOD_BAG": 200,
            "PAINKILLER": 80,
            "GAUZE_BANDAGES": 30,
            "SPLINT": 100,
            "SURGICAL_KIT": 500,
            "STIMPAK": 150,
            "ANTISEPTIC": 40,
            "OXYGEN_TANK": 250,
            "STIMPAK_INHALER": 120,
            "ANESTHETIC_GAS": 180,
            "MEDICINAL_HERB": 60,
            "PAIN_RELIEF_CIGARETTE": 20,
        }),
    ],
}

# General goods shelf
GENERAL_SHELF = {
    "prototype_parent": "shop_container_base",
    "key": "general goods shelf",
    "desc": "A well-stocked shelf with a variety of useful items and miscellaneous supplies.",
    "attrs": [
        ("shop_name", "General Store"),
        ("container_type", "shelf"),
        ("markup_percent", 5),  # 5% markup on general goods
        ("prototype_inventory", {
            "SPRAYPAINT_CAN": 25,
            "SOLVENT_CAN": 30,
            "KEYRING": 10,
            "ROCK": 1,
            "BOTTLE": 5,
            "SEWING_KIT": 50,
            "METALWORK_TOOLS": 150,
            "BALLISTIC_REPAIR_KIT": 100,
            "CERAMIC_REPAIR_COMPOUND": 200,
            "GENERIC_TOOL_KIT": 75,
        }),
    ],
}

# Ranged weapons locker
FIREARMS_LOCKER = {
    "prototype_parent": "shop_container_base",
    "key": "firearms locker",
    "desc": "A secure firearms locker with reinforced steel construction. Contains various ranged weapons under lock and key.",
    "attrs": [
        ("shop_name", "Gun Shop"),
        ("container_type", "locker"),
        ("markup_percent", 20),  # 20% markup on firearms
        ("prototype_inventory", {
            "LIGHT_PISTOL": 300,
            "PUMP_SHOTGUN": 500,
            "BOLT_RIFLE": 800,
            "ANTI_MATERIAL_RIFLE": 2500,
            "ASSAULT_RIFLE": 900,
            "SMG": 600,
            "THROWING_KNIFE": 40,
            "THROWING_AXE": 60,
            "SHURIKEN": 25,
        }),
    ],
}

# Limited stock example - corner store cooler
CORNER_STORE_COOLER = {
    "prototype_parent": "shop_container_base",
    "key": "refrigerated cooler",
    "desc": "A humming refrigerated cooler with glass doors. The stock looks somewhat limited.",
    "attrs": [
        ("shop_name", "Juan's Corner Store"),
        ("container_type", "cooler"),
        ("markup_percent", 50),  # 50% markup - corner store convenience tax!
        ("is_infinite", False),  # Limited stock!
        ("prototype_inventory", {
            "BLOOD_BAG": 500,      # Expensive emergency supply
            "STIMPAK": 350,        # Premium healing
            "PAINKILLER": 150,     # Pain relief
        }),
        ("item_inventory", {
            "BLOOD_BAG": 2,        # Only 2 in stock
            "STIMPAK": 5,          # Only 5 in stock
            "PAINKILLER": 3,       # Only 3 in stock
        }),
    ],
}



# =============================================================================
# SMOKE SYSTEM PROTOTYPES (issue #454)
# =============================================================================
#
# Brand drives which flavor bank ``smoke`` picks from
# (see ``world/smoke.py``).  ``CIGARETTE_BASE`` carries the role tag
# so the ``light`` / ``smoke`` / ``snuff`` commands recognise it; the
# branded subclasses just override ``brand``.  Packs are containers
# that auto-spawn ``capacity`` cigarettes at creation, brand-matched.


# Lighter — zippo-style infinite-use for v1.  ``item_role:lighter``
# tag is how ``CmdLight`` finds it in the actor's hands.
ZIPPO_LIGHTER = {
    "typeclass": "typeclasses.items.Item",
    "key": "zippo lighter",
    "aliases": ["lighter", "zippo"],
    "desc": (
        "A weather-beaten Zippo with a steady, reliable flame.  "
        "The hinge clicks open with a satisfying snap; the wick "
        "catches on the first strike more often than not."
    ),
    "tags": [
        ("lighter", "item_role"),
    ],
}


# Base cigarette.  Branded subtypes override ``brand``.
CIGARETTE_BASE = {
    "typeclass": "typeclasses.items.Item",
    "key": "cigarette",
    "aliases": ["cig", "smoke"],
    "desc": "A slim, hand-rolled cigarette.",
    "attrs": [
        ("substance", "tobacco_neutral"),
        ("uses_left", 6),
        ("max_uses", 6),
    ],
    "tags": [
        # Delivery-method classification (#456) — what verbs apply
        # to this item.  Joints, cigars, pipes will share this tag.
        ("smoke", "delivery_method"),
    ],
}

CIGARETTE_NEUTRAL = {
    "prototype_parent": "CIGARETTE_BASE",
    "key": "cigarette",
    "desc": "A standard filtered cigarette, mild tobacco wrapped in white paper.",
    "attrs": [
        ("substance", "tobacco_neutral"),
    ],
}

CIGARETTE_NOIR = {
    "prototype_parent": "CIGARETTE_BASE",
    "key": "Noir cigarette",
    "aliases": ["noir cig", "noir", "cig", "smoke"],
    "desc": (
        "An unfiltered cigarette in dark paper, the brand stamp on "
        "the side faded to near-illegible.  Smells of something "
        "older than tobacco."
    ),
    "attrs": [
        ("substance", "tobacco_noir"),
    ],
}


# Pack — auto-spawns ``capacity`` cigarettes of ``cigarette_prototype``
# at creation, stamping each with the pack's ``substance``.
CIGARETTE_PACK_BASE = {
    "typeclass": "typeclasses.smoke.CigarettePack",
    "key": "pack of cigarettes",
    "aliases": ["pack", "cigarettes"],
    "desc": "A cardboard pack of cigarettes.",
    "attrs": [
        ("substance", "tobacco_neutral"),
        ("capacity", 10),
        ("cigarette_prototype", "CIGARETTE_NEUTRAL"),
    ],
}

CIGARETTE_PACK_NEUTRAL = {
    "prototype_parent": "CIGARETTE_PACK_BASE",
    "key": "pack of cigarettes",
    "desc": (
        "A cardboard pack of filtered cigarettes.  The brand "
        "lettering is generic block print, no logo, no flourish."
    ),
    "attrs": [
        ("substance", "tobacco_neutral"),
        ("cigarette_prototype", "CIGARETTE_NEUTRAL"),
    ],
}

CIGARETTE_PACK_NOIR = {
    "prototype_parent": "CIGARETTE_PACK_BASE",
    "key": "pack of Noir cigarettes",
    "aliases": ["pack", "noir pack", "cigarettes"],
    "desc": (
        "A matte black pack with the brand name 'NOIR' embossed in "
        "tarnished silver.  Heavier than it looks."
    ),
    "attrs": [
        ("substance", "tobacco_noir"),
        ("cigarette_prototype", "CIGARETTE_NOIR"),
    ],
}
