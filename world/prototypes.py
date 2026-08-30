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
    "prototype_key": "break_shotgun",
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
        ("worn_desc", "Electric {color}rainbow|n socks stretch up {their} thighs, the prismatic pattern shot through with bioluminescent thread. The glow pulses slowly, apparently on its own schedule"),
        ("layer", 1),  # Direct skin contact layer (underwear, thin socks)
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
        ("worn_desc", "A {color}black|n hoodie hangs loose and open off {their} shoulders, the green 'rm -rf /' across the chest lit from behind. LED thread runs data-stream patterns down the sleeves"),
        ("layer", 3),  # Regular clothing layer
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
        ("layer", 5),
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
        ("worn_desc", "A glossy fall of {color}black|n hair reaches {their} shoulders and frames the face, cut level to a blunt fringe across the brow"),
        ("layer", 1),
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
        ("worn_desc", "Honey-{color}blond|n hair falls to {their} chin in full loose layers, catching the light along the top of each one"),
        ("layer", 1),
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
        ("worn_desc", "Walnut-{color}brown|n hair falls past {their} jaw in loose waves, parted off-centre and tucked back behind one ear"),
        ("layer", 1),
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
        ("worn_desc", "Cosmetic lenses tint {their} eyes a vivid emerald, the colour saturated enough to catch attention across a room"),
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
        ("worn_desc", "A pair of {color}chrome|n mirrorshades sit across {their} eyes and give nothing back but the room, warped into a silver pane. Whatever is behind them stays behind them"),
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
        ("worn_desc", "A pair of {color}gold|n-framed aviators rest on {their} nose, the teardrop lenses smoked dark enough to hide the eyes without hiding where they are pointed"),
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
        ("worn_desc", "Faded {color}denim|n jeans sit close on {their} hips and fall straight to the boot, worn pale at the knee and seat. The indigo has given up unevenly, the way denim does"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),  # Regular clothing layer
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
                    "desc_mod": "Faded {color}denim|n jeans sit close on {their} hips with the cuffs turned up to mid-calf, leaving the ankle bare above the boot"
                }
            },
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": ""  # Use base worn_desc
                },
                "unzipped": {
                    "coverage_mod": ["-groin"],
                    "desc_mod": "Faded {color}denim|n jeans hang loose on {their} hips with the fly undone, either carelessness or a point being made"
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
        ("worn_desc", "A plain {color}white|n cotton t-shirt fits clean across {their} chest and shoulders with nothing printed on it. It is either well looked after or very recently acquired"),
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
                    "desc_mod": "A plain {color}white|n cotton t-shirt is knotted up at the hem, leaving a band of {their} midriff bare above the waistband"
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
        ("worn_desc", "Heavy {color}black leather|n combat boots come up over {their} ankles, laced with a precision that suggests it was taught rather than chosen. The toes are steel-reinforced and the soles deep-tread, built to keep footing on anything"),
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin"]),
        ("layer", 5),  # Footwear layer (doesn't conflict with pants)
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
        ("worn_desc", "A sleek {color}black|n tactical jumpsuit fits {their} body close from throat to ankle, the synthetic weave reinforced at every joint. It is built to move in rather than to stop anything"),
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
        ("worn_desc", "Durable {color}black|n tactical trousers sit heavy on {their} hips, the knees doubled and the cargo pockets flat until they are filled. The ripstop tears in a line rather than a hole"),
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
        ("worn_desc", "A practical {color}black|n tactical shirt fits close over {their} chest and arms, the shoulders reinforced where straps bite. It is cut to disappear under armour"),
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
        ("worn_desc", "A {color}tan|n plate carrier is strapped over {their} chest and back, cinched down at the shoulders and ribs. Webbing runs across every panel, waiting for whatever gets clipped to it"),
        ("layer", 2),  # Light armor layer
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
        ("worn_desc", "A {color}black|n kevlar vest sits square over {their} torso, thick with trauma plates front and back. It does not move much when {they do}"),
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
        ("worn_desc", "{color}Steel|n plate encases {their} torso and arms in overlapping segments, each one fitted and articulated to the one beside it. It moves with a sound before it moves"),
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
        ("worn_desc", "A reinforced {color}black leather|n jacket sits heavy on {their} shoulders, the hide thick enough to turn an edge and studded through with steel. It was built to be worn as much as to protect"),
        ("layer", 3),
        ("color", "black"),
        ("material", "leather"),
        ("weight", 3.2),  # Moderate weight
        
        # Style system for leather jacket
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A reinforced {color}black leather|n jacket is zipped tight to {their} throat, the studded hide closing into a shell around the torso"
                },
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A reinforced {color}black leather|n jacket hangs open off {their} shoulders, showing whatever is beneath while the studded hide still sits across the back and arms"
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
        ("worn_desc", "A {color}matte black|n tactical helmet encloses {their} skull and ears in angular composite, electronics seated flush along one side. It leaves the face open and covers everything else"),
        ("layer", 5),
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
    "prototype_key": "blood_bag",
    "key": "blood bag",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["iv", "blood", "transfusion"],
    "desc": "A sterile IV blood bag with attached tubing for emergency transfusion. Contains 500ml of universal donor blood.",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "blood_restoration"),
        # a machine takes a hydraulic charge (#2262)
        ("not_for", ["robot"]),
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
# ============================================================================
# BUTCHER CUTS (GIG_PROTOTYPE_BUTCHER_SPEC) — the Butcher's block stocks these
# as limited shop inventory when a carcass is ground (typeclasses/butcher.py);
# quantities are REAL (what suppliers brought), never infinite. Ingredient-
# grade per spec §7: edible now (eat delivery + taste), empty contributions
# slot for the future food-recipe layer.
# ============================================================================

RAT_TAIL = {
    "prototype_key": "rat_tail",
    "key": "rat tail",
    "aliases": ["tail"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A skinned rat tail, long as a forearm, coiled and tied off with "
            "butcher's twine. The classic stew base of the colony's cheaper "
            "kitchens.",
    "attrs": [
        ("drink_taste", "Gelatinous and faintly sweet, all cartilage and "
                        "slow-cooked promise — wasted eaten raw."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 1),
        ("value", 8),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

RAT_CHOPS = {
    "prototype_key": "rat_chops",
    "key": "rat chops",
    "aliases": ["chops", "chop"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Center-cut rat chops, pale and lean, trimmed square on a bone. "
            "The good cut — the one the stall signs mean when they say MEAT "
            "in capitals.",
    "attrs": [
        ("drink_taste", "Lean and springy with a mineral edge; it wants a "
                        "grill and gets teeth instead."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 1),
        ("value", 5),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

RAT_HAUNCH = {
    "prototype_key": "rat_haunch",
    "key": "rat haunch",
    "aliases": ["haunch"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A rat hindquarter, skinned and hock-tied — dense dark meat "
            "around a stout little femur. Roast weight for one.",
    "attrs": [
        ("drink_taste", "Dark, rich, and chewy, closer to game than anything "
                        "the ration lines admit exists."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 1),
        ("value", 5),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

RAT_OFFAL = {
    "prototype_key": "rat_offal",
    "key": "rat offal",
    "aliases": ["offal"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A twist of waxed paper holding the sound organs — heart, liver, "
            "kidneys — glistening and neatly sorted. Delicacy or dare, "
            "depending on the kitchen.",
    "attrs": [
        ("drink_taste", "Iron and velvet; the liver coats the tongue and the "
                        "heart pushes back."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 1),
        ("value", 5),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

GROUND_MYSTERY_MEAT = {
    "prototype_key": "ground_mystery_meat",
    "key": "ground mystery meat",
    "aliases": ["meat", "mystery meat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A dense brick of pale ground meat in a printed wrapper that says "
            "only MEAT. Whatever didn't make the cut, made this.",
    "attrs": [
        ("drink_taste", "Salt, fat, and deliberate ambiguity. It is probably "
                        "best not to chew thoughtfully."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 1),
        ("value", 2),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

# --- cooked dishes (world/food.py FOOD_RECIPES; the butcher's block sells
# these — the raw cuts above are the INGREDIENTS they consume) ---------------

RAT_TAIL_STEW = {
    "prototype_key": "rat_tail_stew",
    "key": "bowl of rat tail stew",
    "aliases": ["stew", "rat tail stew"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A dented tin bowl of dark, glossy stew, a whole rat tail coiled "
            "through it like a question mark. The colony's honest comfort "
            "food — nobody asks the rat's opinion.",
    "attrs": [
        ("drink_taste", "Rich, gelatinous, and deeply savoury — the tail gives "
                        "up everything it has, slow and complete."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 2),
        ("value", 12),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

GRILLED_RAT_CHOPS = {
    "prototype_key": "grilled_rat_chops",
    "key": "plate of grilled rat chops",
    "aliases": ["grilled chops", "chops plate"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Grill-striped rat chops on a scoured steel plate, bones frenched "
            "with more care than the venue strictly deserves.",
    "attrs": [
        ("drink_taste", "Char and clean lean meat with a mineral finish — the "
                        "good cut, treated with respect."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 2),
        ("value", 8),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

ROAST_RAT_HAUNCH = {
    "prototype_key": "roast_rat_haunch",
    "key": "roast rat haunch",
    "aliases": ["roast", "roast haunch"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A whole rat hindquarter roasted to a lacquered brown, the skin "
            "crisped and the little femur left as a handle.",
    "attrs": [
        ("drink_taste", "Dark and gamey under crackled skin — eats like a "
                        "meal that used to be somebody's whole day of hunting."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 2),
        ("value", 8),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

BUTCHERS_BREAKFAST = {
    "prototype_key": "butchers_breakfast",
    "key": "butcher's breakfast",
    "aliases": ["breakfast", "offal fry"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A shallow pan of flash-fried rat offal — heart, liver, kidneys — "
            "glistening in rendered fat with a fist of ration crackers on the "
            "side. The trade's own meal.",
    "attrs": [
        ("drink_taste", "Iron and velvet, seared fast — the liver melts, the "
                        "heart argues, the fat forgives everything."),
        ("drink_effects", {"nutrition": 6}),
        ("uses_left", 1),
        ("value", 8),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

MYSTERY_SKEWER = {
    "prototype_key": "mystery_skewer",
    "key": "mystery skewer",
    "aliases": ["skewer"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Cubes of seasoned mystery meat char-grilled on a filed-down "
            "spoke. Street food in its purest colony form: hot, cheap, and "
            "unexaminable.",
    "attrs": [
        ("drink_taste", "Salt, char, and fat — delicious precisely as long as "
                        "you keep your curiosity holstered."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 1),
        ("value", 3),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

PAINKILLER = {
    "prototype_key": "painkiller",
    "key": "painkiller",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["syringe", "morphine", "pain meds"],
    "desc": "A medical syringe containing powerful analgesic medication. Multiple doses available.",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "pain_relief"),
        # nothing in there to hurt (#2262)
        ("not_for", ["robot"]),
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
        # a machine takes a sealant patch (#2262)
        ("not_for", ["robot"]),
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
        # a machine takes a strut brace (#2262)
        ("not_for", ["robot"]),
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
                # Prosthetic-frame marker (#527/#539 standard): a severed
                # cyber tail chrome-shears (not bleeds) and reattaches
                # whole, like every other cyber limb.  Predated the
                # standard and was missing it (#571).
                "prosthetic_frame": True,
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
                "prosthetic_frame": True,
            },
            "{side}_metacarpals": {
                "container": "{side}_hand", "max_hp": 18,
                "hit_weight": "uncommon", "capacity": "manipulation",
                "contribution": "moderate", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_lattice", "inorganic": True,
                "prosthetic_frame": True,
            },
            "{side}_forearm_hardpoint": {
                "container": "{side}_arm", "max_hp": 10,
                "hit_weight": "rare", "inorganic": True,
                "hardpoint": "forearm", "prosthetic_frame": True,
            },
        }),
        ("augment_container", "{side}_arm"),
        ("augment_anchor", "{side}_arm"),
        # Templated longdesc prose (#516 review): reads as part of the
        # character, not a bare label.  `{Their}` flexes His/Her/Their
        # by the wearer's gender at render; the verb agrees with the
        # part ("arm is", "hand is"), sidestepping person-number verb
        # agreement.  `{side}` is the install-resolved literal
        # ("right"/"left") — NOT the `{arm}`/`{hand}` body-noun flex,
        # which pluralizes wrong for singular-they ("a cybernetic arms").
        ("augment_longdesc", [
            {
                "key": "{side}_arm",
                "default_desc": "{Their} {side} arm is a full cybernetic replacement, matte composite plating over an actuator column, an access panel seam running the length of the forearm.",
            },
            {
                "key": "{side}_hand",
                "default_desc": "{Their} {side} hand is articulated alloy, five-fingered and precise, the knuckle plating worn smooth.",
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
            "inorganic": True, "prosthetic_frame": True,
            "hardpoint": "forearm", "module_type": "forearm",
            "abilities": {
                "shotgun": {
                    "type": "integrated_weapon",
                    "slot": "{side}_hand",
                    "weapon_prototype": "SHOTGUN_ARM_GUN",
                    "deploy_msg": "Your {side} forearm splits along its seam and the shotgun rotates up into place — the hand folds back and away, and the barrel is just *there*, like it always was.",
                    "retract_msg": "The shotgun swings down and folds along the actuator column; plating closes over it and your fingers flex, a hand again.",
                    "deployed_longdesc": "The forearm housing has split open along its seam, a stub shotgun barrel deployed and locked where the hand should be.",
                    "deployed_longdesc_slot": "Where the {side} hand should be, the wrist tapers into a seamless firing socket — the hand has folded back and stowed along the forearm.",
                    "deploy_room": "{actor}'s forearm splits open with a snap of locking servos — a shotgun barrel rotates up out of the housing where their hand used to be.",
                    "retract_room": "{actor}'s arm-shotgun folds away into the forearm housing; plating seals and their hand reassembles, fingers flexing.",
                },
            },
        }),
    ],
}

# Targeting Processor - forearm-hardpoint module granting combat "blindsight".
# Seats into a CYBER_ARM's forearm hardpoint (like the shotgun module). /blindsight
# toggles a sonar/ranging suite that restores combat AIM with the eyes gone —
# combat-only: it does NOT restore perception (rooms/faces stay dark; that's a
# future fuller-sense upgrade). Needs a cyber arm to mount into; surgeon required.
TARGETING_PROCESSOR = {
    "key": "targeting processor",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["targeting suite", "smartlink processor", "sonar module"],
    "desc": "A forearm-hardpoint module the size of a thick deck of cards: a sensor-fusion die, a ranging emitter behind a smoked window, and a coupling collar of standard chassis gauge. Engaged, it paints the world in wireframe and firing solutions straight into your motor cortex — you shoot true with your eyes shut. It wants a slot.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "forearm"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "{side}_arm", "max_hp": 10, "hit_weight": "rare",
            "inorganic": True, "prosthetic_frame": True,
            "hardpoint": "forearm", "module_type": "forearm",
            "abilities": {
                "blindsight": {
                    "type": "blindsight",
                    "deploy_msg": "The targeting suite spins up — the world resolves into wireframe and ranging data, and your aim holds true even with your eyes shut.",
                    "retract_msg": "The targeting suite powers down; the firing solutions fade and the dark closes back in.",
                },
            },
        }),
    ],
}

# Nailz - flesh-mount natural weapon module (#526 M4)
# Implants into LIVING anatomy at either hand (flesh or chrome) —
# the host stays what it is; it just has claws in it now.  /nailz
# extends them; active claws take combat precedence over anything
# held (settled decision 2026-06-12).
# NAILZ — flesh IMPLANT (not a module): carbide claws grafted into a
# living hand, no chassis required.  The clean counterexample to the
# hardpoint modules.  Material note (#525 review): the claws are
# carbide (a rigid blade material); "monofilament" is a wire/whip and
# belongs on the cutting EDGE, not the claw body.
NAILZ = {
    "key": "Nailz",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["nailz", "claw implants", "nail implants"],
    "desc": "A sealed clinical tray of ten slender carbide blades and their spring housings, each scalpel honed to a monofilament edge and sized to seat beneath a fingernail — five per hand, both hands. The marketing name is etched on the tray lid in a typeface that has seen some court dates. Installation requires a surgeon; regret is sold separately.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "nailz"),
        ("module_mount", "flesh"),
        ("flesh_containers", ["left_hand", "right_hand"]),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "module_type": "nailz",
            "abilities": {
                "nailz": {
                    "type": "natural_weapon",
                    "weapon_prototype": "NAILZ_CLAWS",
                    "deploy_msg": "Your nails lift and part — ten carbide blades slide out from beneath them, four centimetres of monofilament edge sheathing your fingertips with a sound like scissors closing.",
                    "retract_msg": "The blades withdraw beneath your nails; your hands are just hands again, mostly.",
                    "deployed_longdesc": "Slender carbide blades jut from beneath {their} fingernails, monofilament edges catching the light.",
                    "deploy_room": "{actor}'s fingernails lift and carbide blades slide out from beneath them, catching the light.",
                    "retract_room": "{actor}'s finger-blades withdraw beneath their nails.",
                },
            },
        }),
    ],
}

# The claw weapon Nailz extends (#526 M4).  Never held — the claws
# ARE the hand; combat resolution reads it via natural-weapon
# precedence.  Reuses the tiger_claws message set.
NAILZ_CLAWS = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "carbide blades",
    "aliases": ["blades", "nailz", "nailz blades", "finger-blades"],
    "desc": "Ten slender carbide blades, extended from beneath the fingernails, each four centimetres of monofilament edge. They are not for opening letters.",
    "damage": 9,
    "locks": "get:false();drop:false();give:false()",
    "attrs": [
        ("weapon_type", "tiger_claws"),
        ("damage_type", "cut"),
        ("hands_required", 1),
        ("integrated", True),
    ],
}

# CYBER_JAW — prosthetic-jaw chassis (#525 review).  Replaces the
# flesh jaw with a chrome one (keeps talking/eating) and carries a
# "jaw" HARDPOINT for a Jawz-class module.  Installs via the
# replacement-organ path (same canonical name "jaw").  A MODULE needs
# a hardpoint, so a cyber jaw is the prerequisite for Jawz.
CYBER_JAW = {
    "key": "cybernetic jaw",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber jaw", "prosthetic jaw", "jaw unit"],
    "desc": "A full cybernetic mandible — articulated alloy and a composite chin plate, the gum line machined with an empty hardpoint behind a slide cover. It eats, it talks, and it's waiting for something to put in the slot. Surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "jaw"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "face",
            "max_hp": 14, "hit_weight": "rare",
            "capacities": ["talking", "eating"],
            "talking_contribution": "major",
            "eating_contribution": "moderate",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
            "hardpoint": "jaw",
        }),
    ],
}

# JAWZ — hardpoint module (#525 review): seats into a CYBER_JAW's jaw
# hardpoint (module = hardpoint hardware; you need the cyber jaw
# first).  Rebuilds the jaw organ to keep its talking/eating function
# while adding the bite.  /jawz bares the fangs; active fangs take
# combat precedence over a held weapon (you bit them).
JAWZ = {
    "key": "Jawz",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["jawz", "fang module", "teeth module"],
    "desc": "A surgical case of paired titanium-alloy fangs and their gum-line actuators, machined to seat into a cybernetic jaw's hardpoint. The lid carries a worn sticker — a grinning chrome skull — and a warranty void the moment it leaves the shop. Needs a cyber jaw to mount into; installation requires a surgeon.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "jaw"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "face",
            "max_hp": 14, "hit_weight": "rare",
            "capacities": ["talking", "eating"],
            "talking_contribution": "major",
            "eating_contribution": "moderate",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
            "hardpoint": "jaw", "module_type": "jaw",
            "abilities": {
                "jawz": {
                    "type": "natural_weapon",
                    "weapon_prototype": "JAWZ_FANGS",
                    "deploy_msg": "Your gums split along their seam — alloy fangs slide down over your teeth with an oily click, and your jaw sets a little wider to hold them.",
                    "retract_msg": "The fangs retract into your gum line with a wet snick; your smile is almost normal again.",
                    "deployed_longdesc": "Alloy fangs jut from {their} gum line, too long and too sharp for the mouth that holds them.",
                    "deploy_room": "{actor}'s jaw flexes and a row of alloy fangs slides down over their teeth, catching the light.",
                    "retract_room": "{actor}'s fangs retract into their gum line with a wet click.",
                },
            },
        }),
    ],
}

# The fangs Jawz bares (#525).  Never held — they ARE the bite;
# combat reads them via natural-weapon precedence.
JAWZ_FANGS = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "alloy fangs",
    "aliases": ["fangs", "jawz fangs", "teeth"],
    "desc": "Paired rows of titanium-alloy fangs, extended and locked. They were not designed with kissing in mind.",
    "damage": 8,
    "locks": "get:false();drop:false();give:false()",
    "attrs": [
        ("weapon_type", "cybernetic_teeth"),
        ("damage_type", "stab"),
        ("hands_required", 0),
        ("integrated", True),
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

# ===================================================================
# Sensory + locomotion chrome (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC)
# ===================================================================
# These restore a performance capacity the SAME way CYBER_ARM restores
# manipulation and CYBER_JAW restores talking: a capacity-bearing
# replacement organ at the CANONICAL organ name, so
# ``calculate_body_capacity`` counts it and every consumer (combat
# aim/dodge, identity recognition, perception render) sees the sense
# restored — no special-case override needed.  Eyes/ears are head
# sub-organs, so they use the single-organ (``organ_name``) path like
# CYBER_JAW (replace the destroyed flesh organ in its slot — the rest
# of the head stays put).  Legs span limb containers, so they use the
# side-agnostic ``augment_organs`` chassis path like CYBER_ARM.

# --- Optical implants → sight (combat aim, visual recognition, LOOK) ---
CYBER_LEFT_EYE = {
    "key": "cybernetic left eye",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber left eye", "left optic", "left ocular unit"],
    "desc": "A spherical optical replacement unit nested in protective foam — a machined alloy housing, a cluster lens of layered apertures, and a fan of micro-couplers trailing from the back like an optic nerve rendered in ribbon cable. The iris ring glows a faint standby amber. Mounts in a left socket; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "left_eye"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "left_eye",
            "max_hp": 10, "hit_weight": "rare",
            "capacity": "sight", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

CYBER_RIGHT_EYE = {
    "key": "cybernetic right eye",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber right eye", "right optic", "right ocular unit"],
    "desc": "A spherical optical replacement unit nested in protective foam — a machined alloy housing, a cluster lens of layered apertures, and a fan of micro-couplers trailing from the back like an optic nerve rendered in ribbon cable. The iris ring glows a faint standby amber. Mounts in a right socket; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "right_eye"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "right_eye",
            "max_hp": 10, "hit_weight": "rare",
            "capacity": "sight", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

# --- Cochlear implants → hearing (voice discernment, LOOK auditory) ---
CYBER_LEFT_EAR = {
    "key": "cybernetic left ear",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber left ear", "left cochlear unit"],
    "desc": "A cochlear replacement unit — a coiled alloy snail-shell of transducers feeding a slim pickup membrane, the whole assembly small enough to seat in a temporal bone. A standby LED winks at the base of the coupler. Mounts on the left; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "left_ear"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "left_ear",
            "max_hp": 12, "hit_weight": "rare",
            "capacity": "hearing", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

CYBER_RIGHT_EAR = {
    "key": "cybernetic right ear",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber right ear", "right cochlear unit"],
    "desc": "A cochlear replacement unit — a coiled alloy snail-shell of transducers feeding a slim pickup membrane, the whole assembly small enough to seat in a temporal bone. A standby LED winks at the base of the coupler. Mounts on the right; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "right_ear"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "right_ear",
            "max_hp": 12, "hit_weight": "rare",
            "capacity": "hearing", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

# --- Cybernetic kidney → blood_filtration (infection course, renal failure) ---
# Single-organ replacement at the canonical kidney slot (like CYBERNETIC_HEART
# in the shared chest): restores blood_filtration, which clears RenalFailure
# (§7.2) via update_vital_signs and steadies the infection course (§7.1). A
# harvested DONOR kidney installs the same way (canonical name → capacity
# auto-restores) — the modular dialysis stopgap is future.
CYBER_LEFT_KIDNEY = {
    "key": "cybernetic left kidney",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber left kidney", "left filtration unit"],
    "desc": "A bean-shaped filtration unit in a sealed perfusion cradle — a stack of micro-dialysis membranes behind a titanium shell, vascular couplers ringing the hilum like the real thing's renal artery and vein. It hums faintly even unpowered, holding pressure. Mounts on the left; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "left_kidney"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
            "capacity": "blood_filtration", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

CYBER_RIGHT_KIDNEY = {
    "key": "cybernetic right kidney",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["cyber right kidney", "right filtration unit"],
    "desc": "A bean-shaped filtration unit in a sealed perfusion cradle — a stack of micro-dialysis membranes behind a titanium shell, vascular couplers ringing the hilum like the real thing's renal artery and vein. It hums faintly even unpowered, holding pressure. Mounts on the right; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("organ_name", "right_kidney"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "abdomen", "max_hp": 15, "hit_weight": "uncommon",
            "capacity": "blood_filtration", "contribution": "major",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
        }),
    ],
}

# --- Cybernetic leg → moving (dodge, flee, movement) ---
# Side-agnostic chassis like CYBER_ARM: one prototype mounts left OR
# right, the surgeon names the side, and the canonical bone names
# ({side}_femur etc.) keep the `moving` capacity wiring intact.
CYBER_LEG = {
    "key": "cybernetic leg",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["cyber leg", "prosthetic leg", "leg unit"],
    "desc": "A full leg replacement unit in its transport cradle, hip coupling to footplate, ambidextrous mounting hardware along the seam. The shin housing is a column of linear actuators behind impact plating; the foot is a sprung alloy plate built to take a landing. Mounts over an amputated leg, either side; surgical installation required.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("augment_organs", {
            "{side}_femur": {
                "container": "{side}_thigh", "max_hp": 40,
                "hit_weight": "common", "capacity": "moving",
                "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_column", "inorganic": True,
                "prosthetic_frame": True,
            },
            "{side}_tibia": {
                "container": "{side}_shin", "max_hp": 32,
                "hit_weight": "common", "capacity": "moving",
                "contribution": "major", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_column", "inorganic": True,
                "prosthetic_frame": True,
            },
            "{side}_metatarsals": {
                "container": "{side}_foot", "max_hp": 18,
                "hit_weight": "uncommon", "capacity": "moving",
                "contribution": "minor", "can_be_destroyed": True,
                "fracture_vulnerable": True,
                "bone_type": "actuator_lattice", "inorganic": True,
                "prosthetic_frame": True,
            },
        }),
        ("augment_container", "{side}_thigh"),
        ("augment_anchor", "{side}_thigh"),
        ("augment_longdesc", [
            {
                "key": "{side}_thigh",
                "default_desc": "{Their} {side} leg is a full cybernetic replacement, a column of linear actuators behind matte impact plating, an access seam running the length of the shin.",
            },
            {
                "key": "{side}_foot",
                "default_desc": "{Their} {side} foot is a sprung alloy plate, the underside scuffed to bare metal where it takes the ground.",
                "display_after": "{side}_thigh",
            },
        ]),
        ("compatible_species", ["human"]),
    ],
}

# --- Voice modulator → voice disguise (the audio parallel to a mask) ---
# A jaw-hardpoint module (JAWZ pattern): seats into a CYBER_JAW's slot,
# rebuilds the jaw so talking/eating survive, and adds a toggleable
# `modulate` ability.  Engaging it sets `voice_modulator_active`, which
# shifts the voice signature to a different UID so listeners no longer
# recognise the voice (CAPACITY_CONSUMERS_AND_PERCEPTION_SPEC §4.2).
# Needs a cyber jaw to mount into; installation requires a surgeon.
VOICE_MODULATOR = {
    "key": "voice modulator",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["voice mod", "vox modulator", "modulator module"],
    "desc": "A flat module the size of a guitar pick, machined to seat into a cybernetic jaw's hardpoint. A lattice of resonator films and a DSP die hide under a perforated cover; the coupling collar is standard jaw gauge. Engaged, it re-synthesises every word in a voice that isn't yours. Needs a cyber jaw to mount into; installation requires a surgeon.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "jaw"),
        ("condition", "pristine"),
        ("compatible_species", ["human"]),
        ("organ_spec", {
            "container": "head", "display_location": "face",
            "max_hp": 14, "hit_weight": "rare",
            "capacities": ["talking", "eating"],
            "talking_contribution": "major",
            "eating_contribution": "moderate",
            "can_be_harvested": True, "can_be_replaced": True,
            "inorganic": True, "prosthetic_frame": True,
            "hardpoint": "jaw", "module_type": "jaw",
            "abilities": {
                "modulate": {
                    "type": "voice_modulator",
                    "deploy_msg": "The modulator hums against your jaw — your next words will leave your mouth in a stranger's voice.",
                    "retract_msg": "The modulator powers down with a faint click; your own voice settles back into your throat.",
                },
            },
        }),
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
        # a machine takes a tool roll (#2262)
        ("not_for", ["robot"]),
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
        # a machine takes a conformal coating (#2262)
        ("not_for", ["robot"]),
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


# Courier Parcel - what a rabbit runs (#2258)
#
# A deliberate McGuffin. Nobody says what is in it, including the
# people handling it, and that is the point: the parcel is a thing that
# moves through custody and can be taken off somebody, not a container
# with an inventory. Branded, because everything manufactured here is.
COURIER_PACKAGE = {
    "key": "a Longhaul bonded parcel",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["parcel", "package", "consignment", "longhaul"],
    "desc": (
        "A flat parcel in oiled grey wrap, corners taped twice over and "
        "banded across the middle with a Longhaul bonded strip. The strip "
        "is the whole product: pull it and it goes from green to a dull "
        "print-through red that cannot be put back. A consignment number "
        "is stencilled in the corner, and a countersignature runs under "
        "it in the loose hand of somebody who signs a great many of "
        "these. What is inside is the consignor's business."
    ),
    "tags": [("courier", "item_type")],
    "attrs": [
        ("courier_package", True),
    ],
}


# ---------------------------------------------------------------------
# The machine kit (#2262)
#
# A secbot is human-shaped on purpose, so the ACT of repairing one is
# the act of operating on a person -- same chart, same hit locations,
# same steps. What differs is what you put in your hands. These are the
# ordinary counterparts of the organic supplies, carrying the same
# `medical_type` so every existing code path treats them identically,
# and `serves: ["robot"]` so they do nothing for a person.
#
# Deliberately absent: a machine painkiller, sedative, oxygen or
# antiseptic. Those have no counterpart because there is nothing to
# numb, sedate, oxygenate or infect. The tourniquet has no machine
# version either, for the opposite reason -- clamping a line stops
# amber hydraulic fluid exactly as well as it stops blood, so the one
# article serves both and declares nothing.
# ---------------------------------------------------------------------

# Hydraulic Charge - the transfusion analogue
HYDRAULIC_CHARGE = {
    "key": "hydraulic charge",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["charge", "hydraulic", "fluid charge", "boiler run charge"],
    "desc": "A rigid half-litre canister of amber hydraulic fluid under pressure, the Boiler Run kettle-and-flame stamped into the shoulder. A bayonet fitting on the nose mates to a chassis reservoir port. The sight strip down one side runs from FULL to a red band somebody has worn half away with their thumb.",
    "tags": [("medical_item", "item_type"), ("inject", "delivery_method")],
    "attrs": [
        ("medical_type", "blood_restoration"),
        ("serves", ["robot"]),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 1),
        ("application_time", 1),
        ("effectiveness", {
            "bleeding": 9,
            "blood_loss": 10,
            "shock": 7,
            "organ_damage": 3,
        })
    ],
}

# Sealant Patches - the dressing analogue
SEALANT_PATCH = {
    "key": "sealant patches",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["patch", "patches", "sealant patch", "sealant patches"],
    "desc": "A folded strip of self-adhering polymer patching in a Boiler Run wrapper, scored into tear-off squares. Pressed over a split line or a breached panel it goes tacky against the fluid it is stopping, which is the whole trick of it. Five squares left on a fresh strip.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method"), ("bandage", "delivery_method")],
    "attrs": [
        ("medical_type", "wound_care"),
        ("serves", ["robot"]),
        ("uses_left", 5),
        ("max_uses", 5),
        ("stat_requirement", 0),
        ("application_time", 1),
        ("effectiveness", {
            "bleeding": 7,
            "infection": 8,
            "wound_healing": 6,
            "pain": 3,
        })
    ],
}

# Strut Brace - the splint analogue
STRUT_BRACE = {
    "key": "strut brace",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["brace", "strut", "splint brace"],
    "desc": "Two lengths of channel steel and a pair of worm-drive clamps, sized to bridge a bent actuator strut and hold it true enough to walk on. The Boiler Run plate is stamped, not printed, because a printed one would not survive the shop.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "fracture_treatment"),
        ("serves", ["robot"]),
        ("uses_left", 1),
        ("max_uses", 1),
        ("stat_requirement", 2),
        ("application_time", 2),
        ("effectiveness", {
            "fracture": 8,
            "pain": 4,
            "mobility": 6,
            "bleeding": 2,
        })
    ],
}

# Conformal Coating - the tissue-sealant analogue
CONFORMAL_COATING = {
    "key": "conformal coating",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["coating", "conformal", "potting compound"],
    "desc": "A single-dose Boiler Run ampule of grey potting compound with a fine cannula on the end. Run into a cracked component housing it wicks along the fault and cures hard in about a minute, sealing the part against fluid and dust. Useless on a closed chassis -- the panel has to be off and the component in front of you.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "organ_repair"),
        ("serves", ["robot"]),
        ("uses_left", 3),
        ("max_uses", 3),
        ("stat_requirement", 3),
        ("application_time", 2),
        ("effectiveness", {
            "organ_repair":  8,
            "infection":     7,
            "wound_healing": 5,
            "bleeding":      3,
            "pain":          1,
        })
    ],
}

# Tool Roll - the surgical-kit analogue
TOOL_ROLL = {
    "key": "tool roll",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["roll", "tools", "tool kit", "wrap"],
    "desc": "A canvas Boiler Run roll that unties flat into a row of pockets: drivers, picks, a stubby spanner, needle-nose pliers and a magnetised tray that clips to the edge so dropped screws stop being lost screws. Every handle is worn pale at the same spot.",
    "tags": [("medical_item", "item_type"), ("apply", "delivery_method")],
    "attrs": [
        ("medical_type", "surgical_treatment"),
        ("serves", ["robot"]),
        ("uses_left", 10),
        ("max_uses", 10),
        ("stat_requirement", 3),
        ("application_time", 3),
        ("effectiveness", {
            "surgery": 8,
            "organ_damage": 7,
            "fracture": 5,
            "bleeding": 4,
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
        # biology, not repair (#2262)
        ("not_for", ["robot"]),
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
        # machines don't culture biological infection (#2262)
        ("not_for", ["robot"]),
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
        # nothing in there breathing (#2262)
        ("not_for", ["robot"]),
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
        # biology, not repair (#2262)
        ("not_for", ["robot"]),
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
        # nothing in there to sedate (#2262)
        ("not_for", ["robot"]),
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
        # biology, not repair (#2262)
        ("not_for", ["robot"]),
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
        # nothing in there to hurt (#2262)
        ("not_for", ["robot"]),
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

PRE_ROLLED_JOINT = {
    "prototype_key": "pre_rolled_joint",
    "key": "Greenhaus pre-rolled joint",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["joint", "spliff"],
    "desc": "A Greenhaus-brand factory joint, machine-perfect: crimped ends, a "
            "pressed filter plug, and a seam so straight it looks printed. "
            "Uniform as ammunition — nobody's hands were involved. (One "
            "day the colony will roll its own; this is what came before.)",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "cannabis"),
        ("smoke_form", "joint"),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

ROPE_CIGAR = {
    "prototype_key": "rope_cigar",
    "key": "Old Mule rope cigar",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["cigar", "cheap cigar"],
    "desc": "An Old Mule — the short, dark cigar sold by the box to men who "
            "have stopped tasting things: dense, crooked, and dependable. "
            "Burns slow, bites hard, costs little.",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "tobacco_neutral"),
        ("smoke_form", "cigar"),
        ("uses_left", 6),
        ("max_uses", 6),
    ],
}

MACHINE_ROLLED_CIGAR = {
    "prototype_key": "machine_rolled_cigar",
    "key": "Silverband corona cigar",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["corona", "good cigar"],
    "desc": "A Silverband corona cigar in dark Noir leaf, named for its band — "
            "a strip of embossed foil pretending to a heritage the colony "
            "never had. The draw is engineered; the ash holds an inch.",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "tobacco_noir"),
        ("smoke_form", "cigar"),
        ("uses_left", 8),
        ("max_uses", 8),
    ],
}

CHEWING_TOBACCO_PLUG = {
    "prototype_key": "chewing_tobacco_plug",
    "key": "plug of Anchor chewing tobacco",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["plug", "chew", "chaw"],
    "desc": "An Anchor-brand plug of cured leaf and molasses, dense as a hockey "
            "puck and about as subtle. The working man's smoke-free vice — "
            "no flame, no ash, no witnesses.",
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
    "attrs": [
        ("drink_effects", {"tobacco_neutral": 1}),
        ("drink_taste", "Bitter leaf-juice and molasses, strong enough to "
                        "make the eyes water — spit or commit."),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

ROTGUT_BOTTLE = {
    "key": "bottle of Boiler Run rotgut",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["rotgut", "bottle", "booze"],
    "desc": "A squat bottle of Boiler Run, the colony's licensed rotgut — "
            "the label is a woodcut of a bursting boiler, which is either "
            "a warning or a promise. Smells like fuel and bad decisions, "
            "in that order.",
    "tags": [("drink", "delivery_method")],
    "attrs": [
        ("substance", "alcohol"),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

OPIUM_CIGARETTE = {
    "key": "Dead Slow opium cigarette",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["opium cigarette", "opium", "dead slow"],
    "desc": "A Dead Slow: thin paper rolled around tar-black resin, the "
            "brand mark an engine-order telegraph stamped near the tip, "
            "its needle pointed at DEAD SLOW. Heavy, sweet, and patient — "
            "it will wait as long as you can.",
    "tags": [("smoke", "delivery_method")],
    "attrs": [
        ("substance", "opium"),
        ("uses_left", 3),
        ("max_uses", 3),
    ],
}

DOUBLESHIFT_LAGER = {
    "prototype_key": "doubleshift_lager",
    "key": "can of Doubleshift lager",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["lager", "beer", "can"],
    "desc": "A ration-format can of Doubleshift, the lager brewed for the "
            "hour when one shift ends and the next hasn't started. The "
            "label shows two clock faces sharing a single hand.",
    "tags": [("drink", "delivery_method")],
    "attrs": [
        ("drink_effects", {"alcohol": 1}),
        ("drink_taste", "Thin, cold-adjacent, and honest about its job — "
                        "it tastes like knocking off work."),
        ("uses_left", 2),
        ("max_uses", 2),
    ],
}

PILGRIM_FORTIFIED = {
    "prototype_key": "pilgrim_fortified",
    "key": "bottle of Pilgrim fortified wine",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["pilgrim", "fortified wine", "wine"],
    "desc": "A screw-top bottle of Pilgrim, the fortified wine of doorways "
            "and long nights — sweet, heavy, and strong out of all "
            "proportion to its price. The label's little walking figure "
            "has been getting nowhere since the colony landed.",
    "tags": [("drink", "delivery_method")],
    "attrs": [
        ("drink_effects", {"alcohol": 1}),
        ("drink_taste", "Syrup-sweet with a burnt-raisin depth and a "
                        "finish like a warm coat you can't take off."),
        ("uses_left", 4),
        ("max_uses", 4),
    ],
}

OLD_MERIDIAN_WHISKEY = {
    "prototype_key": "old_meridian_whiskey",
    "key": "bottle of Old Meridian whiskey",
    "typeclass": "typeclasses.items.Item",
    "aliases": ["old meridian", "whiskey", "import whiskey"],
    "desc": "A sealed bottle of Old Meridian, Earth-import whiskey — or so "
            "the freight stamps insist, and nobody who can afford one asks "
            "twice. Amber as the mural in a good lobby, wax over the cork, "
            "a brand old enough to predate the colony that drinks it.",
    "tags": [("drink", "delivery_method")],
    "attrs": [
        ("drink_effects", {"alcohol": 2}),
        ("drink_taste", "Oak, smoke, and genuine caramel warmth — the real "
                        "thing, or the best counterfeit of it you will "
                        "ever gratefully not question."),
        ("uses_left", 6),
        ("max_uses", 6),
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

# Disposable lighter — finite ``uses_left``; CmdLight burns a charge per light
# and bins it when spent (vs. the infinite zippo above).
DISPOSABLE_LIGHTER = {
    "typeclass": "typeclasses.items.Item",
    "key": "disposable lighter",
    "aliases": ["lighter", "disposable", "bic"],
    "desc": (
        "A cheap translucent-plastic lighter, the kind that lives in a "
        "pocket until the flint gives out.  A sliver of fluid sloshes "
        "behind the scratched casing."
    ),
    "tags": [
        ("lighter", "item_role"),
    ],
    "attrs": [
        ("uses_left", 20),
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
    "key": "Longhaul cigarette",
    "desc": "A Longhaul — the workman's filtered cigarette, mild tobacco in "
            "white paper, the brand's little hauler logo printed at the "
            "filter. Ubiquitous as grit.",
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
    "key": "pack of Longhaul cigarettes",
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


# ===========================================================================
# Furniture (FURNITURE_AND_POSTURE) — things you sit on / lie on
# ===========================================================================

# A bar stool — sit at the bar. The Furniture typeclass defaults (sitting,
# capacity 1, "on") are exactly right, so this just dresses it.
BAR_STOOL = {
    "prototype_key": "bar_stool",
    "key": "bar stool",
    "aliases": ["stool"],
    "typeclass": "typeclasses.furniture.Furniture",
    "desc": "A battered metal stool, its vinyl seat split and patched with tape.",
    "tags": [("furniture", "category")],
}

# An AutoDoc / med-pod — lie in it to be worked on. The AutoDoc typeclass sets
# the lying posture, the "in" preposition, and the medical-apparatus marker.
AUTODOC = {
    "prototype_key": "autodoc",
    "key": "autodoc",
    "aliases": ["auto-doc", "med pod", "medpod", "stretcher", "pod"],
    "typeclass": "typeclasses.furniture.AutoDoc",
    "desc": "A scuffed white medical pod, lid hinged back over a padded trough "
            "of sensors and folded manipulator arms — a clinic's centrepiece, "
            "waiting for a body to work on.",
    "tags": [("furniture", "category"), ("medical", "category")],
}


# ===================================================================
# ROBOT MODULES (ROBOT_SPECIES_AND_MOB_SPEC)
# ===================================================================
# Robots use the SAME augment backend as human chrome (organ_spec,
# hardpoints, integrated-weapon abilities) but present it species-true:
# a robot's "cyberware" is factory equipment — modules seated in a
# frame, not chrome grafted into flesh.  The deployed weapon reuses the
# ``cybernetic_shotgun`` combat message bank (already machine-toned:
# "servos whine up to pressure", "the forearm housing locks rigid").

#: The security unit's factory armament, shared by the item prototype
#: below and the ``@spawnmob/secbot`` factory-fit (which seats it as a
#: standalone augment organ — the tail pattern — since a robot's frame
#: comes from the plant with the module already in it).
ROBOT_SHOTGUN_MODULE_SPEC = {
    "container": "{side}_arm", "max_hp": 12, "hit_weight": "rare",
    "inorganic": True, "prosthetic_frame": True,
    "hardpoint": "forearm", "module_type": "forearm",
    "abilities": {
        "shotgun": {
            "type": "integrated_weapon",
            "slot": "{side}_hand",
            "weapon_prototype": "ROBOT_ARM_GUN",
            "deploy_msg": "Your {side} forearm housing unlocks along its service seam — the manipulator folds back into its stowage recess and the riot gun rotates up and seats with a hard mechanical clack.",
            "retract_msg": "The riot gun swings down into the forearm housing; the panel seals and the manipulator redeploys, actuators cycling through their check pattern.",
            "deployed_longdesc": "The forearm housing stands open along its service seam, a stub riot-gun barrel deployed and locked where the manipulator should be.",
            "deployed_longdesc_slot": "Where the {side} manipulator should be, the wrist assembly terminates in a hardmounted firing socket — the hand has folded back into its stowage recess.",
            "deploy_room": "{actor}'s forearm housing unlocks with a clack of releasing latches — a stub riot gun rotates up out of the frame where its hand just stowed.",
            "retract_room": "{actor}'s arm-gun folds down into the forearm housing; the service panel seals and its manipulator redeploys, fingers cycling once.",
        },
    },
}

# Integrated Shotgun Module — the robot-frame counterpart of the human
# SHOTGUN_MODULE.  Same coupling standard, species-gated to robot frames;
# harvestable from a wrecked chassis and reseatable in another.
ROBOT_SHOTGUN_MODULE = {
    "key": "integrated shotgun module",
    "typeclass": "typeclasses.items.Organ",
    "aliases": ["riot module", "robot weapon module", "arm gun module"],
    "desc": "A riot shotgun in a robot-frame module format: barrel shroud, feed system, and deployment servos in a sealed unit stenciled with a municipal parts code. The coupling collar is standard chassis gauge. This is not aftermarket chrome — it left the plant as part of a security frame's bill of materials.",
    "tags": [("medical_item", "item_type"), ("augment", "item_type")],
    "attrs": [
        ("module_type", "forearm"),
        ("condition", "pristine"),
        ("compatible_species", ["robot"]),
        ("organ_spec", ROBOT_SHOTGUN_MODULE_SPEC),
    ],
}

# The integrated weapon the module deploys.  Locked + flagged integrated
# by the ability layer; carries its OWN robot-voiced combat bank
# (``world/combat/messages/robot_riot_gun.py`` — municipal-machine
# register: targeting solutions, LETHAL FORCE AUTHORIZED, casings off
# frame ports), distinct from the human chrome's ``cybernetic_shotgun``.
ROBOT_ARM_GUN = {
    "prototype_parent": "RANGED_WEAPON_BASE",
    "key": "arm-mounted riot gun",
    "aliases": ["riot gun", "arm gun"],
    "desc": "A riot shotgun hardmounted in a robot forearm — short, shrouded, and structural. The barrel shroud is load-bearing frame member; the feed system disappears into the elbow actuator housing. No grip, no trigger, no sling mount: the weapon is a subsystem, fired the way the arm is moved — by the frame that owns it.",
    "damage": 20,
    "locks": "get:false();drop:false();give:false()",
    "attrs": [
        ("weapon_type", "robot_riot_gun"),
        ("damage_type", "bullet"),
        ("hands_required", 1),
        ("integrated", True),
    ],
}


# ===================================================================
# COLONY WORKWEAR (civilian wardrobe line — clean core garments;
# dust/grime/blood are FUTURE dynamic factors from environment/injury,
# never baked into the prose)
# ===================================================================

WORK_COVERALLS = {
    "prototype_key": "WORK_COVERALLS",
    "key": "grey work coveralls",
    "aliases": ["coveralls", "jumpsuit", "overalls"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Standard-issue colony coveralls in heavy grey twill: reinforced knees and elbows, a double-stitched tool loop at the hip, and a chest patch where a shift-tag clips. The cut is boxy and the zip runs collar to crotch.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Heavy {color}grey|n twill coveralls swallow {their} frame from collar to ankle, cut boxy enough to work in and plain enough to disappear in. Reinforced patches sit at the knees and elbows, a tool loop rides one hip, and the chest patch is still blank where a shift-tag clips"),
        ("coverage", ["chest", "back", "abdomen", "groin", "left_thigh", "right_thigh", "left_shin", "right_shin", "left_arm", "right_arm"]),
        ("layer", 2),
        ("color", "grey"),
        ("material", "twill"),
        ("weight", 1.4),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {
                    "coverage_mod": ["-left_arm", "-right_arm"],
                    "desc_mod": "Heavy {color}grey|n twill coveralls swallow {their} frame from collar to ankle, the sleeves shoved past the elbow and bunched there, leaving {their} forearms bare to the work. The chest patch is still blank where a shift-tag clips",
                },
            },
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-chest"],
                    "desc_mod": "Heavy {color}grey|n twill coveralls hang off {their} shoulders unzipped to the sternum, the top half folded back to show whatever is underneath. The sleeves stay down, the knees stay doubled, and the chest patch stays blank",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal", "closure": "zipped"}),
    ],
}

MINING_HELMET = {
    "prototype_key": "MINING_HELMET",
    "key": "mining helmet",
    "aliases": ["helmet", "hardhat", "hard hat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A scuffproof composite mining helmet with a lamp bracket riveted above the brim and a chin strap gone soft with use. The lamp itself is company property and rarely survives the walk home.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}yellow|n composite mining helmet sits square on {their} head, the chin strap left hanging rather than buckled. The lamp bracket above the brow is empty, its contacts bare"),
        ("coverage", ["head"]),
        ("layer", 5),
        ("color", "yellow"),
        ("material", "composite"),
        ("weight", 0.7),
    ],
}

NECK_REBREATHER = {
    "prototype_key": "NECK_REBREATHER",
    "key": "rebreather",
    "aliases": ["mask", "breather", "respirator rig"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A half-mask rebreather on a rubberized neck strap, filters screwed in at each cheek. Worn slung at the throat, ready to pull up when the air goes bad — down-shaft, or on a bad wind day.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A half-mask rebreather hangs at {their} throat on a {color}black|n rubber strap, pushed down out of the way. Both filter ports are capped, waiting to be hauled up over the mouth when the air turns"),
        ("coverage", ["neck"]),
        ("layer", 2),
        ("color", "black"),
        ("material", "rubber"),
        ("weight", 0.6),
    ],
}

PIT_BOOTS = {
    "prototype_key": "PIT_BOOTS",
    "key": "pit boots",
    "aliases": ["boots", "work boots"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Steel-shanked pit boots laced to the shin, with a gum-rubber sole thick enough to shrug off dropped stock and hot slag alike. Heavy, honest footwear.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "{Their} feet are shod in heavy {color}brown|n pit boots, laced tight past the ankle and up the shin with a steel shank holding the arch rigid. The gum-rubber soles grip whatever the floor is doing, and the toe caps are built to take a dropped load without complaint"),
        ("coverage", ["left_foot", "right_foot"]),
        ("layer", 5),  # footwear layer — worn over trousers, never conflicts
        ("color", "brown"),
        ("material", "leather"),
        ("weight", 1.6),
    ],
}

WORK_GLOVES = {
    "prototype_key": "WORK_GLOVES",
    "key": "work gloves",
    "aliases": ["gloves"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Split-leather work gloves with reinforced palms and elastic cuffs. The kind bought by the crate and worn until the stitching gives.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Split-leather {color}tan|n work gloves cover {their} hands to the wrist, the palms doubled where a grip goes and the cuffs elasticated to keep grit out. They sit stiff until the leather warms through"),
        ("coverage", ["left_hand", "right_hand"]),
        ("layer", 5),
        ("color", "tan"),
        ("material", "leather"),
        ("weight", 0.3),
    ],
}

DUST_PONCHO = {
    "prototype_key": "DUST_PONCHO",
    "key": "canvas poncho",
    "aliases": ["poncho", "dust poncho"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A waxed-canvas poncho cut wide at the shoulder, with a drawstring hood collar and snap closures down each side. Colony streetwear for wind days.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A waxed {color}olive|n canvas poncho hangs wide off {their} shoulders with the side-snaps only half done, more shelter than garment. The wax has gone dull along the folds where it gets handled"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "olive"),
        ("material", "canvas"),
        ("weight", 1.1),
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A waxed {color}olive|n canvas poncho is snapped shut down both sides, closing {their} torso and arms into a weatherproof tent. Only the head and the boots are left out in it",
                },
                "unzipped": {"coverage_mod": [], "desc_mod": ""},
            },
        }),
        ("style_properties", {"closure": "unzipped"}),
    ],
}

HIVIS_VEST = {
    "prototype_key": "HIVIS_VEST",
    "key": "hi-vis vest",
    "aliases": ["vest", "hivis", "safety vest"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A company-issue high-visibility vest in signal orange with two reflective chest bands. The back is stencilled PROPERTY OF THE COMPANY in letters that outlast the vest.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A signal-{color}orange|n hi-vis vest hangs open over {their} chest and back, cut loose enough to go over whatever else is on. Reflective bands throw back any light that finds them, and a company stencil sits square between the shoulder blades"),
        ("coverage", ["chest", "back"]),
        ("layer", 2),  # worn OVER the jacket/coat (armor-layer precedent)
        ("color", "orange"),
        ("material", "mesh"),
        ("weight", 0.3),
    ],
}

COMPANY_WINDBREAKER = {
    "prototype_key": "COMPANY_WINDBREAKER",
    "key": "company windbreaker",
    "aliases": ["windbreaker", "jacket"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A lightweight company windbreaker in corporate blue, the logo screen-printed over the heart. Issued at orientation; worn until it isn't.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A corporate-{color}blue|n windbreaker is zipped up over {their} chest and arms, the nylon rustling at every movement. A company logo is printed small over the heart"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "blue"),
        ("material", "nylon"),
        ("weight", 0.5),
        ("style_configs", {
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-chest"],
                    "desc_mod": "A corporate-{color}blue|n windbreaker hangs open off {their} shoulders, the logo\'d panel flapping loose with each step and whatever is underneath showing down the middle",
                },
            },
        }),
        ("style_properties", {"closure": "zipped"}),
    ],
}

THERMAL_SHIRT = {
    "prototype_key": "THERMAL_SHIRT",
    "key": "thermal shirt",
    "aliases": ["thermal", "longshirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A long-sleeved thermal in waffle-knit cotton, collar stretched from being pulled on in the dark. The colony runs cold underground and colder above.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A waffle-knit {color}charcoal|n thermal sits close against {their} chest and arms, thin enough to disappear under anything worn over it. The collar has gone soft and shapeless from being hauled on and off"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 1),
        ("color", "charcoal"),
        ("material", "cotton"),
        ("weight", 0.5),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {
                    "coverage_mod": [],
                    "desc_mod": "A waffle-knit {color}charcoal|n thermal sits close against {their} chest, the sleeves shoved past the elbow and holding there on the knit alone. The collar has gone soft and shapeless from being hauled on and off",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal"}),
    ],
}

CARGO_TROUSERS = {
    "prototype_key": "CARGO_TROUSERS",
    "key": "cargo trousers",
    "aliases": ["cargos", "trousers", "pants"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Ripstop cargo trousers with bellows pockets at each thigh and a webbing belt sewn straight into the waist. Colony cut: roomy, hemmed high of the boot.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Ripstop {color}khaki|n cargo trousers hang straight from {their} hips to the ankle, roomy and entirely unremarkable. The thigh pockets bellow out where the day's carrying has been stuffed into them"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "khaki"),
        ("material", "ripstop"),
        ("weight", 0.8),
    ],
}

KNIT_CAP = {
    "prototype_key": "KNIT_CAP",
    "key": "knit cap",
    "aliases": ["cap", "beanie", "watch cap"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A ribbed knit watch cap, cuffed once. The kind of hat that lives in a coat pocket eleven months a year and on a head the twelfth.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A ribbed {color}black|n knit cap is pulled down over {their} skull, the cuff turned low enough to cover the ears. It holds its shape badly and sags at the crown"),
        # The cuff is the whole point of a watch cap, so it is a real style
        # axis: turned down it covers the ears, rolled up it does not. The
        # base coverage matches the DEFAULT state — the description said the
        # cuff covered the ears while the coverage only ever claimed the head.
        ("coverage", ["head", "left_ear", "right_ear"]),
        ("layer", 5),
        ("color", "black"),
        ("material", "wool"),
        ("weight", 0.1),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {
                    "coverage_mod": ["-left_ear", "-right_ear"],
                    "desc_mod": "A ribbed {color}black|n knit cap sits high on {their} skull with the cuff rolled up off the ears, riding the crown more than covering it",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal"}),
    ],
}

UTILITY_HARNESS = {
    "prototype_key": "UTILITY_HARNESS",
    "key": "utility harness",
    "aliases": ["harness", "rig"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A webbing utility harness hung with empty carabiners, cable loops, and a dozen pouches sized for parts, tools, and whatever fits. A scavver's second spine.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A webbing utility harness criss-crosses {their} chest and back, buckled snug enough not to swing when {they move}. Pouches and carabiners in {color}grey|n webbing hang off every strap, each one filled or clipped to something"),
        ("coverage", ["chest", "back"]),
        ("layer", 3),
        ("color", "grey"),
        ("material", "webbing"),
        ("weight", 0.9),
    ],
}

# -- timepieces ---------------------------------------------------------
#
# Time is legible in-world, through objects (world/gametime.py): a desc
# may carry {time}/{date}/{period} tokens, and per-object clock_skew /
# clock_stopped attributes let two watches in the same room disagree —
# which is the point of owning one. The stopped watch renders only
# {time}, deliberately: the moment it died stays off the record.

LONGHAUL_CHRONO = {
    "prototype_key": "LONGHAUL_CHRONO",
    "key": "crew chrono",
    "aliases": ["chrono", "watch", "wristwatch"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A Longhaul crew chrono: matte alloy case, a ridged bezel "
            "cut deep enough to turn with gloves on, lume dots that "
            "still drink the light after all these years. The face reads "
            "{time} — {date} — and it has never once been caught lying. "
            "The line issues them by the crate and collects them off the "
            "dead; one worn this smooth means somebody, somewhere, "
            "expects you.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A matte {color}gunmetal|n crew chrono rides {their} left wrist on a webbing strap, bezel scuffed from being knocked into things. The lume dots hold a faint green charge"),
        ("coverage", ["left_hand"]),
        ("layer", 1),
        ("color", "gunmetal"),
        ("material", "alloy"),
        ("weight", 0.1),
    ],
}

GILT_WRISTWATCH = {
    "prototype_key": "GILT_WRISTWATCH",
    "key": "gilt wristwatch",
    "aliases": ["wristwatch", "watch", "gilt watch"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A dress watch in gilt gone warm brass at the lugs, dial the "
            "color of old cream, indices like little knife-points. Some "
            "liner's arcade sold it a very long way from here, and the "
            "liner never came back for it. The face reads {time} with "
            "the serene confidence of an heirloom. It runs slow. It has "
            "always run slow. Everyone who ever wore it decided to "
            "forgive that.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}gilt|n dress watch sits on {their} left wrist over a cream dial and knife-point indices. The plating has worn to warm brass at every edge a sleeve touches"),
        ("coverage", ["left_hand"]),
        ("layer", 1),
        ("clock_skew", -9),
        ("color", "gilt"),
        ("material", "brass"),
        ("weight", 0.1),
    ],
}

STOPPED_WATCH = {
    "prototype_key": "STOPPED_WATCH",
    "key": "stopped watch",
    "aliases": ["watch", "wristwatch", "dead watch"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A mechanical watch older than the colony, case rubbed "
            "smooth as sea glass, crystal crazed to frost. Under the "
            "frost the hands stand at {time}, where they have stood "
            "since a morning nobody left alive can name. The crown turns "
            "without catching on anything. People wear it anyway: a "
            "watch that tells the hour something happened, forever, "
            "instead of the hour it is.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "An old {color}steel|n watch is buckled to {their} left wrist with the crystal frosted through with cracks. The hands stand perfectly still and have for some time"),
        ("coverage", ["left_hand"]),
        ("layer", 5),
        # 1970-01-02 12:17 UTC -> 04:17 colony local; only {time} renders,
        # so the date it died stays unwritten
        ("clock_stopped", 130620),
        ("color", "steel"),
        ("material", "steel"),
        ("weight", 0.1),
    ],
}

GANG_CUT = {
    "prototype_key": "GANG_CUT",
    "key": "sleeveless cut",
    "aliases": ["cut", "gang jacket", "colors"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A sleeveless heavy-canvas cut, collar torn off, back panel left bare where a set's colors get painted on. Wearing one unmarked is an invitation; wearing one marked is an allegiance.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A sleeveless {color}black|n canvas cut hangs off {their} shoulders with the arms taken off at the seam. The back panel carries a painted set of colors, worn where everyone behind {them} can read it"),
        ("coverage", ["chest", "back"]),
        ("layer", 3),
        ("color", "black"),
        ("material", "canvas"),
        ("weight", 0.7),
    ],
}

HAWKERS_APRON = {
    "prototype_key": "HAWKERS_APRON",
    "key": "hawker's apron",
    "aliases": ["apron"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A many-pocketed trade apron tied at the waist, each pouch sized to a different denomination of merchandise. The strings have been retied so many times they're mostly knot.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A many-pocketed {color}brown|n trade apron is tied off at {their} waist and hangs to the knee. Every pouch across the front sits lumpy with stock"),
        ("coverage", ["chest", "abdomen"]),
        ("layer", 4),
        ("color", "brown"),
        ("material", "canvas"),
        ("weight", 0.6),
    ],
}

COMPANY_COAT = {
    "prototype_key": "COMPANY_COAT",
    "key": "company coat",
    "aliases": ["coat", "agent coat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A knee-length coat in company charcoal, creases pressed sharp, the breast pocket exactly deep enough for a tally-book. Authority you can dry-clean.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A pressed {color}charcoal|n company coat falls from {their} shoulders to the knee without a crease out of place. A tally-book sits squared in the breast pocket"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "left_thigh", "right_thigh"]),
        ("layer", 4),
        ("color", "charcoal"),
        ("material", "wool"),
        ("weight", 1.2),
        ("style_configs", {
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A pressed {color}charcoal|n company coat worn open off the shoulders, authority at ease",
                },
            },
        }),
        ("style_properties", {"closure": "zipped"}),
    ],
}


# ===================================================================
# STREET-TIER WEAPONS (low-tier contemporary arms — the colony's back
# alleys; message banks already existed, prototypes now match)
# ===================================================================

SHIV = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "shiv",
    "aliases": ["spike"],
    "desc": "A hand-ground spike of scrap steel wound with tape for a grip. Nobody manufactures these; everybody makes them.",
    "damage": 5,
    "weapon_type": "shiv",
    "damage_type": "stab",
}

TIRE_IRON = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "tire iron",
    "aliases": ["iron", "lug wrench"],
    "desc": "A cross-ended tire iron in pitted chrome. Its second career began the night somebody realized it fit the hand better than the lug.",
    "damage": 8,
    "weapon_type": "tire_iron",
    "damage_type": "blunt",
}

BRASS_KNUCKLES = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "brass knuckles",
    "aliases": ["knuckles", "knucks"],
    "desc": "Four finger-holes and a palm bar in dull cast brass, edges worn smooth by pockets and use.",
    "damage": 6,
    "weapon_type": "brass_knuckles",
    "damage_type": "blunt",
}

HEAVY_CHAIN = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "heavy chain",
    "aliases": ["chain"],
    "desc": "A meter of galvanized cargo chain with the last link ground open. Loud to carry, louder to use.",
    "damage": 7,
    "weapon_type": "chain",
    "damage_type": "blunt",
}

BOX_CUTTER = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "box cutter",
    "aliases": ["cutter", "razor knife"],
    "desc": "A workaday box cutter with a thumb-slide and a fresh segment snapped forward. A tool, mostly.",
    "damage": 5,
    "weapon_type": "box_cutter",
    "damage_type": "cut",
}

CROWBAR = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "crowbar",
    "aliases": ["prybar", "pry bar"],
    "desc": "A flat-ended crowbar in chipped red enamel. Opens crates, doors, and arguments.",
    "damage": 9,
    "weapon_type": "crowbar",
    "damage_type": "blunt",
}

PIPE_WRENCH = {
    "prototype_parent": "MELEE_WEAPON_BASE",
    "key": "pipe wrench",
    "aliases": ["wrench"],
    "desc": "A foot and a half of drop-forged pipe wrench, jaw rusted open at a permanent two inches. Still a tool; increasingly an argument.",
    "damage": 8,
    "weapon_type": "pipe_wrench",
    "damage_type": "blunt",
}


# ===================================================================
# STREET FASHION + COMPANION LINE (style_configs give the nuance:
# zip/unzip closures, rollup adjustments — same machinery as DEV_HOODIE)
# ===================================================================

SYNTHWEAVE_SHEATH = {
    "prototype_key": "SYNTHWEAVE_SHEATH",
    "key": "synthweave sheath dress",
    "aliases": ["dress", "sheath"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A fitted sheath dress in liquid-black synthweave, cut to the knee with a side-zip from hip to hem. The fabric carries a faint pearlescent sheen and never wrinkles — engineered, like its usual wearers, to look effortless.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A liquid-{color}black|n synthweave sheath is fitted down {their} body from shoulder to knee, close enough to show the line of them. The pearlescent sheen shifts and slides as {they move}"),
        ("coverage", ["chest", "back", "abdomen", "groin", "left_thigh", "right_thigh"]),
        ("layer", 2),
        ("color", "black"),
        ("material", "synthweave"),
        ("weight", 0.4),
        ("style_configs", {
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-left_thigh"],
                    "desc_mod": "A liquid-{color}black|n synthweave sheath is fitted down {their} body from shoulder to knee with the side-zip run open from hip to hem. The slit bares one thigh with every stride",
                },
            },
        }),
        ("style_properties", {"closure": "zipped"}),
    ],
}

MESH_TOP = {
    "prototype_key": "MESH_TOP",
    "key": "mesh top",
    "aliases": ["mesh", "sheer top"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A long-sleeved top of fine industrial mesh, more suggestion than fabric. Colony street fashion at its most honest: it keeps off exactly nothing.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A fine {color}smoke|n-grey mesh top clings over {their} chest and arms, the weave open enough to read as shadow rather than fabric. It sits closer to a suggestion than a garment"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 1),
        ("color", "smoke"),
        ("material", "mesh"),
        ("weight", 0.1),
    ],
}

CROPPED_JACKET = {
    "prototype_key": "CROPPED_JACKET",
    "key": "cropped jacket",
    "aliases": ["crop jacket"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A cropped moto-cut jacket in dyed synth-leather, hem stopping at the ribs, with an off-center zip and a collar built to be worn up.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A cropped {color}oxblood|n synth-leather jacket sits high on {their} torso and stops at the ribs, the collar turned up. The zip catches whatever light the room has"),
        ("coverage", ["chest", "back", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "oxblood"),
        ("material", "synth-leather"),
        ("weight", 0.9),
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "A cropped {color}oxblood|n synth-leather jacket is zipped to {their} throat and stops at the ribs, the collar standing up like a closed door",
                },
                "unzipped": {
                    "coverage_mod": ["-chest"],
                    "desc_mod": "A cropped {color}oxblood|n synth-leather jacket hangs open off {their} shoulders, ending at the ribs and framing whatever is worn beneath it",
                },
            },
        }),
        ("style_properties", {"closure": "unzipped"}),
    ],
}

HEELED_BOOTS = {
    "prototype_key": "HEELED_BOOTS",
    "key": "heeled boots",
    "aliases": ["heels"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Knee-high boots in polished synth-leather on a sculpted heel — high enough to announce every step on ferrocrete, stable enough to run in if the night turns.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Knee-high {color}black|n heeled boots run up {their} shins and stop just under the knee, polished to a street-lamp shine. The heel announces every step a moment before {they arrive}"),
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin"]),
        ("layer", 5),  # footwear layer — worn over trousers, never conflicts
        ("color", "black"),
        ("material", "synth-leather"),
        ("weight", 1.0),
    ],
}

SYNTH_COLLAR = {
    "prototype_key": "SYNTH_COLLAR",
    "key": "sleek collar",
    "aliases": ["collar", "choker"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A slim collar of brushed alloy on a synthweave band, closed with a magnetic clasp. On some necks it's jewelry; on a synth's, it reads uncomfortably like a maker's mark.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A slim brushed-{color}silver|n collar sits close around {their} throat, narrow enough to read as jewellery until it catches the light. The clasp winks with each turn of the head"),
        ("coverage", ["neck"]),
        ("layer", 1),
        ("color", "silver"),
        ("material", "alloy"),
        ("weight", 0.1),
    ],
}

LONG_COAT = {
    "prototype_key": "LONG_COAT",
    "key": "long coat",
    "aliases": ["duster", "coat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "An ankle-length coat in heavy stormcloth, collar wide enough to hide in, cut to move like weather. The colony's most democratic garment: everyone from companions to gun-hands wears one eventually.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "An ankle-length {color}charcoal|n stormcloth coat falls from {their} shoulders to the ankle and moves like low weather around {them}"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 4),  # over-everything duster — clears knee-high boots at the shins
        ("color", "charcoal"),
        ("material", "stormcloth"),
        ("weight", 1.8),
        ("style_configs", {
            "closure": {
                "zipped": {
                    "coverage_mod": [],
                    "desc_mod": "An ankle-length {color}charcoal|n stormcloth coat is fastened to {their} collar and closed the whole way down, a moving column of weather",
                },
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "An ankle-length {color}charcoal|n stormcloth coat hangs open off {their} shoulders, billowing back from whatever is underneath it",
                },
            },
        }),
        ("style_properties", {"closure": "unzipped"}),
    ],
}

BOMBER_JACKET = {
    "prototype_key": "BOMBER_JACKET",
    "key": "bomber jacket",
    "aliases": ["bomber"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A nylon bomber with ribbed cuffs and a two-way zip, the shoulders patched with the ghost-stitching of insignia long since cut off.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}forest|n-green nylon bomber sits short on {their} waist with the cuffs ribbed tight. Ghost-stitching marks the sleeve where patches used to live"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "forest"),
        ("material", "nylon"),
        ("weight", 0.8),
        ("style_configs", {
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-chest"],
                    "desc_mod": "A {color}forest|n-green nylon bomber hangs open off {their} shoulders, the ribbed hem swinging loose at the waist",
                },
            },
        }),
        ("style_properties", {"closure": "zipped"}),
    ],
}

FLANNEL_SHIRT = {
    "prototype_key": "FLANNEL_SHIRT",
    "key": "flannel shirt",
    "aliases": ["flannel"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A brushed-flannel work shirt in a red-black check, buttons mismatched from a decade of replacements. Sleeves made to be rolled.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}red|n-black check flannel hangs soft on {their} shoulders, washed thin enough to drape. The buttons down the front no longer match each other"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 1),
        ("color", "red"),
        ("material", "flannel"),
        ("weight", 0.6),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {
                    "coverage_mod": [],
                    "desc_mod": "A {color}red|n-black check flannel hangs soft on {their} shoulders with the sleeves turned past the elbow, leaving {their} forearms bare for work",
                },
            },
            "closure": {
                "zipped": {"coverage_mod": [], "desc_mod": ""},
                "unzipped": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A {color}red|n-black check flannel hangs open off {their} shoulders with the tails loose, showing whatever is worn beneath it",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal", "closure": "zipped"}),
    ],
}

TANK_TOP = {
    "prototype_key": "TANK_TOP",
    "key": "ribbed tank top",
    "aliases": ["tank", "tank top"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A ribbed cotton tank in colony white — which is to say, grey. Cut close, holds its shape, asks nothing.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A ribbed {color}grey|n-white tank is cut close over {their} chest and leaves the shoulders entirely bare. The knit has stretched slack at the armholes"),
        ("coverage", ["chest", "back", "abdomen"]),
        ("layer", 1),
        ("color", "grey"),
        ("material", "cotton"),
        ("weight", 0.2),
    ],
}

SLIT_SKIRT = {
    "prototype_key": "SLIT_SKIRT",
    "key": "slit skirt",
    "aliases": ["skirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A long bias-cut skirt in matte synthetic, slit high on one side. Moves like smoke; stops traffic like a wall.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A long matte-{color}black|n skirt falls to {their} ankle with a slit run high up one side. It bares a stripe of thigh with every second step"),
        ("coverage", ["groin", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "black"),
        ("material", "synthetic"),
        ("weight", 0.4),
    ],
}

LEATHER_TROUSERS = {
    "prototype_key": "LEATHER_TROUSERS",
    "key": "leather trousers",
    "aliases": ["leathers"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Close-cut trousers in matte synth-leather, seams double-stitched, knees pre-scuffed by the factory or the street — impossible to say which.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Close-cut matte-{color}black|n synth-leather trousers fit down {their} legs with no give in them at all. Light catches along the seams and nowhere else"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "black"),
        ("material", "synth-leather"),
        ("weight", 0.9),
    ],
}

HIGH_TOPS = {
    "prototype_key": "HIGH_TOPS",
    "key": "high-top sneakers",
    "aliases": ["sneakers", "high-tops", "hightops"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Canvas high-tops re-soled at least once, laces replaced with paracord. Street standard: quiet, quick, and dry enough.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Scuffed {color}white|n canvas high-tops come up over {their} ankles, laced with paracord in place of whatever came with them. The canvas has gone grey at the toe"),
        ("coverage", ["left_foot", "right_foot"]),
        ("layer", 5),  # footwear layer — worn over trousers, never conflicts
        ("color", "white"),
        ("material", "canvas"),
        ("weight", 0.6),
    ],
}


# ==========================================================================
# COMM DEVICES (RADIO_COMMS_SPEC Phase 1)
# ==========================================================================

WALKIE_TALKIE = {
    "prototype_key": "WALKIE_TALKIE",
    "typeclass": "typeclasses.items.Radio",
    "key": "AWE Magpie-01 radio",
    "aliases": ["walkie", "walkie-talkie", "radio", "handset", "magpie",
                "magpie-01", "awe"],
    "desc": ("A knock-around AWE Magpie-01 — a handheld transceiver in scuffed "
             "high-impact plastic, its stubby antenna taped at the base and a "
             "rubberised push-to-talk worn pale by a thousand thumbs. The "
             "Ashford Wireless & Electric wordmark and its little etched magpie "
             "have half-rubbed off the casing — the same mark you'd find on a "
             "cheap hotplate — and a small monochrome display sits above the "
             "dial."),
    "attrs": [
        ("is_radio", True),
        ("radio_on", False),
        ("frequency", None),
    ],
}


#: The security base's fixed transceiver (RADIO_COMMS_SPEC §2.1: "base
#: station") — the voice of dispatch. A powered, 911MHz-locked console that
#: acknowledges reports on the air (deterministic template lines, no LLM).
#: PHYSICAL: switch it off or wreck it and dispatch goes silent. The is_npc
#: marker is the radio loop-guard (LLM units observe its traffic, never
#: reply-chain on it).
BASE_STATION = {
    "prototype_key": "BASE_STATION",
    "typeclass": "typeclasses.items.DispatchConsole",
    "key": "a dispatch console",
    "aliases": ["console", "station", "base station", "dispatch"],
    "desc": ("A hard-wired dispatch console bolted to the wall, all worn "
             "toggles and a fat coiled mic on a hook. A band readout burns "
             "steady at 911MHz; the cooling fan never quite stops."),
    "locks": "get:false()",
    "attrs": [
        ("is_radio", True),
        ("radio_on", True),
        ("frequency", "911MHz"),
        ("is_base_station", True),
        ("is_npc", True),
        ("voice_description", "clipped"),
        ("voice_ending", "monotone"),
    ],
}


#: District radio infrastructure, TWO-OBJECT STANDARD (the Constabulary /
#: QoC pattern): the MAST is pure structure — ``db.intact`` +
#: ``db.breachable`` are the ``sabotage``/``repair`` seam — while the
#: CABINET below is the actual base-station Radio, linked via
#: ``cabinet.db.antenna = <mast>`` at spawn. Intact antenna = mast-tier
#: reach (colony-wide relay); wrecked = the cabinet still hums at
#: handheld range. Site the mast HIGH; the cabinet can live floors away
#: (the Brackett's is in the basement — head-end fiction, standard verbs).
REPEATER_MAST = {
    "prototype_key": "REPEATER_MAST",
    "typeclass": "typeclasses.items.Item",
    "key": "AWE Sentinel-9 repeater mast",
    "aliases": ["mast", "repeater", "sentinel", "sentinel-9"],
    "desc": ("A lattice-steel repeater mast in Ashford Wireless & Electric "
             "grey, guyed to the deck at three points and crowned with a "
             "folded-dipole array that creaks when the wind changes its "
             "mind. A service plate at its base carries the stencilled AWE "
             "magpie, and a conduit as thick as a wrist dives straight "
             "down into the building's bones."),
    "locks": "get:false()",
    "attrs": [
        ("intact", True),
        ("breachable", True),
        ("get_err_msg", "It is guyed, bolted, and taller than your ambition."),
    ],
}


#: The band on a shelf: a fixed venue set. The GRILLE rule does the
#: work — a powered radio fans its band to the whole room it sits in,
#: so one of these behind a counter puts the Birdhouse in everyone's
#: ears, keeper and patrons alike. Anyone can ``tune`` it (the mischief
#: seam); it is bolted against walking off.
AWE_SHELF_RADIO = {
    "prototype_key": "AWE_SHELF_RADIO",
    "typeclass": "typeclasses.items.Radio",
    "key": "AWE Fireside-12 shelf radio",
    "aliases": ["radio", "shelf radio", "fireside", "set"],
    "desc": ("An AWE Fireside-12: a shoebox of scuffed bakelite and brass "
             "grille-cloth, the etched magpie riding the corner of the "
             "dial plate. The tuner's had one favourite spot long enough "
             "to wear a pale arc in the dial."),
    "locks": "get:false()",
    "attrs": [
        ("is_radio", True),
        ("radio_on", True),
        ("frequency", "88.8MHz"),
        ("integration_priority", 9),   # after the venue's primary fixture
        ("get_err_msg", "It is screwed down against exactly this idea."),
    ],
}


#: The Sentinel's head-end: the base-station Radio the mast serves.
#: Standard radio grammar only — ``toggle``/``tune``; its display renders
#: dynamically (band when powered, dark when not).
REPEATER_CABINET = {
    "prototype_key": "REPEATER_CABINET",
    "typeclass": "typeclasses.items.Radio",
    "key": "AWE head-end cabinet",
    "aliases": ["cabinet", "head-end", "headend"],
    "desc": ("A steel equipment cabinet in Ashford Wireless & Electric "
             "grey, bolted to the wall with its service door ajar on a "
             "rack of patient, humming boards. A conduit as thick as a "
             "wrist climbs from its crown into the riser and doesn't come "
             "back down."),
    "locks": "get:false()",
    "attrs": [
        ("is_radio", True),
        ("radio_on", True),
        ("frequency", "911MHz"),
        ("is_base_station", True),
        ("get_err_msg", "It is conduit-fed and bolted to the wall."),
    ],
}


#: The security unit's built-in transceiver (RADIO_COMMS_SPEC §2.1): a comms
#: module seated in an ear/antenna, factory-fit like the riot gun. Carries
#: the radio metadata the receiver reads (`radio_frequency`); intact + on-band
#: = the unit hears the net. Destroy/harvest the ear (medical hit-location)
#: and the bot goes deaf — the EMP/mute seam, for free.
ROBOT_COMMS_MODULE_SPEC = {
    "container": "{side}_ear", "max_hp": 6, "hit_weight": "rare",
    "inorganic": True, "prosthetic_frame": True,
    "radio_frequency": "911MHz",   # the emergency band (world.radio)
    "longdesc": ("Where the {side} ear should be, a mesh-grilled comms pod "
                 "sits flush to the chassis, a stub antenna folded along the "
                 "skull line."),
}


# ---------------------------------------------------------------------------
# WARDROBE EXPANSION (2026-07-12) — registers the catalog lacked: corpo,
# medical, weather-sealed, agri/service, domestic, formal. Cut to dress the
# NPC population the new districts imply (dome growers, market vendors,
# tenants, office workers). Same conventions as the rest of the wardrobe:
# layer 1 base / 2 garment / 3 over / 4 outer, style_configs where a
# garment honestly has states.
# ---------------------------------------------------------------------------

CORPO_BLAZER = {
    "prototype_key": "CORPO_BLAZER",
    "key": "corporate blazer",
    "aliases": ["blazer", "jacket"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A structured blazer in company-neutral slate, shoulders built to a silhouette some brand manual specified. The lapel carries a stitched loop where an affiliation pin clips — empty, which says something too.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A structured {color}slate|n blazer squares off {their} shoulders in a cut that costs more than it looks like it does. The lapel pin loop sits conspicuously empty"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 3),
        ("color", "slate"),
        ("material", "wool blend"),
        ("weight", 0.9),
        ("style_configs", {
            "closure": {
                "buttoned": {"coverage_mod": [], "desc_mod": ""},
                "open": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A structured {color}slate|n blazer hangs open off {their} shoulders, the shape of it going slack. It is corporate formality at the end of a long shift",
                },
            },
        }),
        ("style_properties", {"closure": "buttoned"}),
    ],
}

DRESS_SHIRT = {
    "prototype_key": "DRESS_SHIRT",
    "key": "pressed dress shirt",
    "aliases": ["shirt", "dress shirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A dress shirt in recycled-fiber white, pressed to creases you could file paper under. The collar is the kind that leaves a mark by end of shift.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A pressed {color}white|n dress shirt is buttoned to {their} throat, the collar sharp enough to leave a mark on the skin under it"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm"]),
        ("layer", 1),
        ("color", "white"),
        ("material", "recycled fiber"),
        ("weight", 0.3),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "rolled": {
                    "coverage_mod": ["-left_arm", "-right_arm"],
                    "desc_mod": "A pressed {color}white|n dress shirt sits open at {their} collar with the sleeves turned back to the forearm. It is formality making concessions",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal"}),
    ],
}

DRESS_TROUSERS = {
    "prototype_key": "DRESS_TROUSERS",
    "key": "creased trousers",
    "aliases": ["trousers", "slacks"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Office trousers with a crease that survived the commute, in a grey engineered to match every blazer the company ever issued.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Creased {color}grey|n office trousers fall clean from {their} hips to the shoe, holding their line against a colony that ruins everything else"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "grey"),
        ("material", "wool blend"),
        ("weight", 0.5),
    ],
}

PENCIL_SKIRT = {
    "prototype_key": "PENCIL_SKIRT",
    "key": "pencil skirt",
    "aliases": ["skirt"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A knee-length pencil skirt in charcoal, cut narrow and lined — office armor of the type that predates the colony and will outlast it.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A narrow {color}charcoal|n pencil skirt fits close over {their} hips and stops exactly at the knee. It permits a short stride and nothing else"),
        ("coverage", ["groin", "left_thigh", "right_thigh"]),
        ("layer", 1),
        ("color", "charcoal"),
        ("material", "wool blend"),
        ("weight", 0.4),
    ],
}

OXFORD_SHOES = {
    "prototype_key": "OXFORD_SHOES",
    "key": "polished oxfords",
    "aliases": ["oxfords", "shoes"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Lace-up oxfords polished to a corporate shine that the street grating is actively working to undo.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Polished {color}black|n oxfords sit narrow on {their} feet, laced flat and buffed to a shine. They are fighting a losing war with the grating"),
        ("coverage", ["left_foot", "right_foot"]),
        ("layer", 5),
        ("color", "black"),
        ("material", "leather"),
        ("weight", 0.8),
    ],
}

NECKTIE = {
    "prototype_key": "NECKTIE",
    "key": "corporate necktie",
    "aliases": ["tie", "necktie"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A necktie in muted company stripes, knotted by muscle memory. On this colony it reads less as fashion than as allegiance.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A striped {color}company-blue|n necktie is knotted tight at {their} throat and squared under the collar, allegiance worn where it can be checked"),
        ("coverage", ["neck"]),
        ("layer", 5),
        ("color", "company-blue"),
        ("material", "synthetic silk"),
        ("weight", 0.1),
        ("style_configs", {
            "adjustable": {
                "normal": {"coverage_mod": [], "desc_mod": ""},
                "loosened": {
                    "coverage_mod": [],
                    "desc_mod": "A striped {color}company-blue|n necktie hangs loose at {their} throat with the knot dragged down and the top button gone. The day has stopped pretending",
                },
            },
        }),
        ("style_properties", {"adjustable": "normal"}),
    ],
}

MEDICAL_SCRUBS = {
    "prototype_key": "MEDICAL_SCRUBS",
    "key": "surgical scrubs",
    "aliases": ["scrubs"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Two-piece scrubs in clinical teal, autoclave-faded, the breast pocket permanently sprung from carried instruments.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Autoclave-faded {color}teal|n scrubs hang loose on {their} frame, cut for moving fast and washing hot. The breast pocket is sprung from years of instruments riding in it"),
        ("coverage", ["chest", "back", "abdomen", "groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 4),
        ("color", "teal"),
        ("material", "cotton blend"),
        ("weight", 0.5),
    ],
}

LAB_COAT = {
    "prototype_key": "LAB_COAT",
    "key": "white lab coat",
    "aliases": ["lab coat", "coat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A knee-length lab coat, white where it matters and stained honestly where it doesn't, a row of pens clipped to the breast pocket in descending order of function.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}white|n lab coat hangs open to the knee off {their} shoulders, honestly stained and not apologised for. Pens are racked in the breast pocket in a row"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "left_thigh", "right_thigh"]),
        ("layer", 5),  # OUTER than scrubs (4): a coat goes on over
                       # them, and dressing runs inner->outer, so at the
                       # same layer one of the two silently fails to
                       # wear — which is what a clinic aide did (#2381),
        ("color", "white"),
        ("material", "poly-cotton"),
        ("weight", 0.7),
        ("style_configs", {
            "closure": {
                "buttoned": {"coverage_mod": [], "desc_mod": ""},
                "open": {
                    "coverage_mod": ["-chest", "-abdomen"],
                    "desc_mod": "A {color}white|n lab coat swings loose around {their} legs as {they move}, unbuttoned and trailing like the tail end of a thought",
                },
            },
        }),
        ("style_properties", {"closure": "open"}),
    ],
}

SEALED_SLICKER = {
    "prototype_key": "SEALED_SLICKER",
    "key": "tox-sealed slicker",
    "aliases": ["slicker", "raincoat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A hooded slicker in safety amber, seams heat-welded and cuffs gasketed — rated for tox rain, which on this colony is not a hypothetical. The hood's clear visor strip has gone the yellow of old resin.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A heat-welded {color}amber|n slicker seals {their} body from throat to shin, gasketed tight at the cuffs. It is built for rain that should not be allowed near skin"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "left_thigh", "right_thigh"]),
        ("layer", 3),
        ("color", "amber"),
        ("material", "welded polymer"),
        ("weight", 1.2),
        ("style_configs", {
            "adjustable": {
                "hood_down": {"coverage_mod": [], "desc_mod": ""},
                "hood_up": {
                    "coverage_mod": ["+head"],
                    "desc_mod": "A heat-welded {color}amber|n slicker seals {their} body from throat to shin with the hood drawn up and cinched. The face is reduced to a strip behind yellowed visor plastic",
                },
            },
        }),
        ("style_properties", {"adjustable": "hood_down"}),
    ],
}

GROWERS_APRON = {
    "prototype_key": "GROWERS_APRON",
    "key": "grower's rubber apron",
    "aliases": ["apron"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A heavy rubber apron stained the particular green-brown of nutrient work, its front pocket sprouting shears, ties, and a moisture probe. Smells like the inside of an agridome because it has never been anywhere else.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A nutrient-stained {color}green-brown|n rubber apron covers {them} from chest to shin, tied off behind the back. Tools sprout from the front pocket at every angle"),
        ("coverage", ["chest", "abdomen", "groin"]),
        ("layer", 4),
        ("color", "green-brown"),
        ("material", "rubber"),
        ("weight", 1.0),
    ],
}

RUBBER_WADERS = {
    "prototype_key": "RUBBER_WADERS",
    "key": "rubber waders",
    "aliases": ["waders", "boots"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Thigh-high rubber waders, patched at the left knee with something that used to be a different color. For standing in what the colony's floors collect.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Thigh-high {color}black|n rubber waders swallow {their} legs to the hip, patched in more than one place. They are made for standing in whatever collects at the bottom of things"),
        ("coverage", ["left_foot", "right_foot", "left_shin", "right_shin", "left_thigh", "right_thigh"]),
        ("layer", 5),
        ("color", "black"),
        ("material", "rubber"),
        ("weight", 1.6),
    ],
}

SHOWER_SANDALS = {
    "prototype_key": "SHOWER_SANDALS",
    "key": "shower sandals",
    "aliases": ["sandals", "slides"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Molded plastic slides in a faded orange, the tread long gone. The unofficial uniform of every cube-hotel corridor in the colony.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Faded {color}orange|n shower sandals hang off {their} feet by a single moulded strap. They slap the floor with every step and announce {them} down a corridor"),
        ("coverage", ["left_foot", "right_foot"]),
        ("layer", 5),
        ("color", "orange"),
        ("material", "molded plastic"),
        ("weight", 0.2),
    ],
}

HOUSE_ROBE = {
    "prototype_key": "HOUSE_ROBE",
    "key": "quilted house robe",
    "aliases": ["robe"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A quilted robe washed to an ambiguous mauve, belt tied in the permanent knot of someone who has stopped performing for the corridor.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A quilted {color}mauve|n house robe hangs off {their} shoulders to the shin, the belt tied in what is clearly its permanent knot. It is the uniform of being off duty from everything"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "left_thigh", "right_thigh"]),
        ("layer", 4),
        ("color", "mauve"),
        ("material", "quilted synthetic"),
        ("weight", 0.8),
    ],
}

HEAD_WRAP = {
    "prototype_key": "HEAD_WRAP",
    "key": "printed head wrap",
    "aliases": ["wrap", "headwrap"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A meter of printed cloth wrapped and tucked with practiced architecture, its pattern faded from a market bolt that sold out years ago.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A printed {color}ochre|n head wrap is wound over {their} hair and tucked with practised architecture, no end left loose. It has been done the same way a thousand times"),
        ("coverage", ["head"]),
        ("layer", 5),
        ("color", "ochre"),
        ("material", "printed cotton"),
        ("weight", 0.1),
    ],
}

EVENING_SUIT = {
    "prototype_key": "EVENING_SUIT",
    "key": "midnight evening suit",
    "aliases": ["suit", "evening suit"],
    "typeclass": "typeclasses.items.Item",
    "desc": "An evening suit in true midnight, cut close and unbranded — the kind of formality that costs more for what it doesn't say. Colony dust does not stick to it, which is its own small miracle.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}midnight|n evening suit is cut close to {their} frame, unbranded and precise about it. The cloth takes the room's light and gives very little of it back"),
        ("coverage", ["chest", "back", "abdomen", "left_arm", "right_arm", "groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "midnight"),
        ("material", "wool-silk"),
        ("weight", 1.1),
    ],
}

SILK_SLIP_DRESS = {
    "prototype_key": "SILK_SLIP_DRESS",
    "key": "silk slip dress",
    "aliases": ["slip", "dress"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A bias-cut slip dress in real silk — or synthesis close enough to require touching, which is the point. It moves half a beat behind its wearer, like a rumor.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A bias-cut {color}oyster|n silk slip skims {their} body and hangs off two thin straps. The fabric moves half a beat behind {them} and settles late"),
        ("coverage", ["chest", "abdomen", "groin", "left_thigh", "right_thigh"]),
        ("layer", 1),
        ("color", "oyster"),
        ("material", "silk"),
        ("weight", 0.2),
    ],
}

LONG_SCARF = {
    "prototype_key": "LONG_SCARF",
    "key": "long knit scarf",
    "aliases": ["scarf"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Two meters of knit scarf in a rust that flatters nobody and warms everybody, wound twice and still trailing.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A {color}rust|n knit scarf is wound twice around {their} throat and still has length left over, both ends trailing down the front"),
        ("coverage", ["neck"]),
        ("layer", 5),
        ("color", "rust"),
        ("material", "knit synthetic"),
        ("weight", 0.3),
    ],
}

WIDE_BRIM_HAT = {
    "prototype_key": "WIDE_BRIM_HAT",
    "key": "wide-brimmed hat",
    "aliases": ["hat"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A wide-brimmed hat in oiled canvas, shaped by weather into something between agriculture and myth. Keeps the processor glare off and opinions in.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A weather-shaped {color}oiled-tan|n hat sits low on {their} head, the wide brim pulled down against the glare. The oil in the felt has gone dark where it gets handled"),
        ("coverage", ["head"]),
        ("layer", 5),
        ("color", "oiled-tan"),
        ("material", "oiled canvas"),
        ("weight", 0.4),
    ],
}

THERMAL_LEGGINGS = {
    "prototype_key": "THERMAL_LEGGINGS",
    "key": "thermal leggings",
    "aliases": ["leggings"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Ribbed thermal leggings in expedition black, the base layer of everyone who works where the colony's heating doesn't reach.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "Ribbed {color}black|n thermal leggings fit tight down {their} legs, thin and unglamorous. They are the honest base layer of cold work"),
        ("coverage", ["groin", "left_thigh", "right_thigh", "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "black"),
        ("material", "ribbed thermal"),
        ("weight", 0.3),
    ],
}


# --- Pessoa Street: Auntie Lin's noodle cart wares (build 048) -------------
# Handmade worker food — the branding rule's handmade exception. Eaten/drunk
# through the consumption system (same shape as the butcher's dishes).

PESSOA_NOODLES = {
    "prototype_key": "pessoa_noodles",
    "key": "a bowl of hand-pulled noodles",
    "aliases": ["noodles", "bowl of noodles", "noodle"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A steel bowl of hand-pulled wheat noodles in a dark, oily broth, "
            "scattered with scallion ash and a slick of chili oil. The broth "
            "has been going so long nobody remembers starting it.",
    "attrs": [
        ("drink_taste", "Deep, salty, faintly scorched — the broth of a "
                        "thousand shifts, and it sticks to your ribs like one."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 3),
        ("value", 6),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

PESSOA_BUN = {
    "prototype_key": "pessoa_bun",
    "key": "a steamed bun",
    "aliases": ["bun", "steamed bun", "pork bun"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A pale, pleated bun the size of a fist, steam-soft and heavy in "
            "the hand, its underside stuck to a square of waxed paper. "
            "Whatever's inside is dark, sweet, and generously salted.",
    "attrs": [
        ("drink_taste", "Cloud-soft dough over a hot, savoury-sweet filling — "
                        "a whole meal you can eat one-handed on the walk."),
        ("drink_effects", {"nutrition": 2}),
        ("uses_left", 2),
        ("value", 4),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

SNAIL_SKEWER = {
    "prototype_key": "snail_skewer",
    "key": "a grilled snail skewer",
    "aliases": ["snails", "snail skewer", "escargot"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Six fat snails off the Escallier boards, grilled in their own "
            "butter-fat with crushed garlic-weed and a squeeze of something "
            "sour, threaded on a wire skewer with the shells still hissing.",
    "attrs": [
        ("drink_taste", "Rich, dark, and faintly of the good kind of damp — "
                        "the colony's humblest luxury, six bites long."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 1),
        ("value", 3),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

SNAIL_JAR = {
    "prototype_key": "snail_jar",
    "key": "a jar of pickled snails",
    "aliases": ["jar", "pickled snails"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A stout glass jar of shelled snails in cloudy brine, peppercorns "
            "and a coil of dried chili drifting among them. The lid is "
            "stamped by hand: ESCARGOT FOR ALL.",
    "attrs": [
        ("drink_taste", "Sharp brine, then the meat — dense, cold, and "
                        "somehow honest. Keeps for a shift year."),
        ("drink_effects", {"nutrition": 1}),
        ("uses_left", 4),
        ("value", 5),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

PESSOA_SKEWER = {
    "prototype_key": "pessoa_skewer",
    "key": "a charred skewer",
    "aliases": ["skewer", "stick"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Cubes of something dark grilled onto a splintered bamboo stick, "
            "brushed with the same chili oil as everything on the cart and "
            "dusted with a rust-coloured spice.",
    "attrs": [
        ("drink_taste", "Char, fat, and a spice that builds — gone in four "
                        "bites and worth every one."),
        ("drink_effects", {"nutrition": 3}),
        ("uses_left", 1),
        ("value", 3),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

PESSOA_TEA = {
    "prototype_key": "pessoa_tea",
    "key": "a cup of smoked tea",
    "aliases": ["tea", "cup of tea", "cha"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A dented enamel cup of tea steeped so dark and smoke-cured it "
            "could pass for broth, cut with a spoonful of condensed something "
            "gone to the bottom.",
    "attrs": [
        ("drink_taste", "Smoke, tannin, and a cloying sweetness — scalding "
                        "enough to remind you you're alive on a cold shift."),
        ("drink_effects", {}),
        ("uses_left", 3),
        ("value", 2),
    ],
    "tags": [("drink", "delivery_method"), ("drink", "item_type")],
}

# ---------------------------------------------------------------------------
# THAWN-HARRISON DECANT ISSUE — what the dispenser gives a fresh sleeve.
# Deliberately the cheapest dignity the colony can extend: paper-weight,
# one size, stamped with the brand that grew you.
# ---------------------------------------------------------------------------

DECANT_JUMPSUIT = {
    "prototype_key": "decant_jumpsuit",
    "key": "Thawn-Harrison decant jumpsuit",
    "aliases": ["jumpsuit", "decant jumpsuit", "coverall", "suit"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A disposable one-piece in clinical off-white, seams "
            "heat-welded rather than stitched and the fabric barely "
            "heavier than paper. THAWN-HARRISON CRYOGENICS is stamped "
            "across the back in yellow, along with a size (ONE) and a "
            "line of small print explaining that this garment is "
            "provided as a courtesy and is not rated for weather.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A papery {color}off-white|n decant jumpsuit, "
                      "THAWN-HARRISON stamped across the back in yellow "
                      "— the courtesy garment of somebody who woke up "
                      "today"),
        ("coverage", ["chest", "back", "abdomen", "groin", "left_arm",
                      "right_arm", "left_thigh", "right_thigh",
                      "left_shin", "right_shin"]),
        ("layer", 1),
        ("color", "off-white"),
        ("material", "paper-weave"),
        ("weight", 0.3),
        ("value", 0),
        # issue clothing: decent, not dressed (#2118), and paper-thin —
        # it tears coming off, so free suits never stockpile (#2120)
        ("provisional", True),
        ("single_use", True),
    ],
    "tags": [("clothing", "item_type")],
}

DECANT_SLIPPERS = {
    "prototype_key": "decant_slippers",
    "key": "pair of Thawn-Harrison slippers",
    "aliases": ["slippers", "decant slippers", "shoes"],
    "typeclass": "typeclasses.items.Item",
    "desc": "Two flat soles of pressed grey fibre with elasticated "
            "uppers, the kind of footwear that exists to get a person "
            "from a table to a door. The left one is stamped L, the "
            "right one is also stamped L.",
    "attrs": [
        ("category", "clothing"),
        ("worn_desc", "A pair of flat {color}grey|n decant slippers, "
                      "pressed fibre gone soft at the edges"),
        ("coverage", ["left_foot", "right_foot"]),
        ("layer", 5),
        ("color", "grey"),
        ("material", "pressed fibre"),
        ("weight", 0.2),
        ("value", 0),
        # issue clothing: decent, not dressed (#2118), and paper-thin —
        # it tears coming off, so free suits never stockpile (#2120)
        ("provisional", True),
        ("single_use", True),
    ],
    "tags": [("clothing", "item_type")],
}

# ---------------------------------------------------------------------------
# KURO — the snailery's free pot. Not charity: the shells, the trimmings and
# the ones too small to sell, boiled down to a black stock that costs the
# yard nothing to give away. The gate has read ESCARGOT FOR ALL since before
# anybody working there was decanted; this is the sign taken literally.
# ---------------------------------------------------------------------------

SNAIL_KURO = {
    "prototype_key": "snail_kuro",
    "key": "a bowl of kuro-nikomi stew",
    "aliases": ["kuro", "nikomi", "kuro-nikomi", "stew", "broth", "bowl",
                "soup"],
    "typeclass": "typeclasses.items.Item",
    "desc": "A chipped bowl of stew so dark it reads black until the light "
            "catches the oil on top and turns it bronze. Shell stock, hours "
            "of it, thickened with whatever the beds gave up and cut with "
            "something sharp and fermented. Three or four small snails have "
            "been let down into it whole. There are no noodles in it — "
            "noodles cost money, and Auntie Lin sells those a few minutes "
            "up the street. It is thin, it is very hot, and it costs "
            "nothing.",
    "attrs": [
        ("drink_taste", "Deep, dark and mineral, with a sour edge that "
                        "arrives late — the taste of a thing made from what "
                        "was left over, and made well. You finish it still "
                        "wanting something to chew."),
        ("drink_effects", {"nutrition": 1}),
        ("uses_left", 3),
        ("max_uses", 3),
        ("value", 0),
    ],
    "tags": [("eat", "delivery_method"), ("food", "item_type")],
}

# ===================================================================
# DOCUMENTS — paper that vouches for a face (#2408)
#
# A document is spawned ABOUT somebody: `depicts_uid` is set at creation to
# the apparent uid it portrays. These prototypes are the blanks.
# ===================================================================

SLEEVE_ID = {
    "prototype_key": "SLEEVE_ID",
    "key": "Thawn-Harrison sleeve card",
    "aliases": ["card", "id", "sleeve card", "identification"],
    "typeclass": "typeclasses.items.Document",
    "desc": "A stiff polymer card in Thawn-Harrison off-white, a decant portrait "
            "laser-etched into one corner and the registry line printed beneath "
            "it. A holographic seal runs across the face; tilted to the light it "
            "resolves into the company mark and a batch number.",
    "attrs": [
        ("category", "document"),
        ("issuer", "Thawn-Harrison Cryogenics"),
        ("authority", "corporate"),
        ("protocol", "holographic seal"),
        ("protocol_ok", True),
        ("weight", 0.02),
    ],
}

COLONY_ID = {
    "prototype_key": "COLONY_ID",
    "key": "colony registry card",
    "aliases": ["card", "registry card", "id", "papers"],
    "typeclass": "typeclasses.items.Document",
    "desc": "A worn registry card, the colony seal pressed into the laminate and "
            "gone soft at the corners from a decade in a pocket. The photograph "
            "has faded toward grey but the registry line is still crisp.",
    "attrs": [
        ("category", "document"),
        ("issuer", "Domino's Gambit Colony Registry"),
        ("authority", "colony"),
        ("protocol", "pressed colony seal"),
        ("protocol_ok", True),
        ("weight", 0.02),
    ],
}

WANTED_NOTICE = {
    "prototype_key": "WANTED_NOTICE",
    "key": "constabulary notice",
    "aliases": ["notice", "poster", "wanted", "bolo"],
    "typeclass": "typeclasses.items.Document",
    "desc": "A printed constabulary notice, the face reproduced coarse enough to "
            "have come off a camera rather than a sitting. The registry name runs "
            "under it in block capitals, above a countersignature and a case "
            "number.",
    "attrs": [
        ("category", "document"),
        ("issuer", "Colony Constabulary"),
        ("authority", "colony"),
        ("protocol", "countersigned case number"),
        ("protocol_ok", True),
        ("weight", 0.01),
    ],
}

CLUB_CARD = {
    "prototype_key": "CLUB_CARD",
    "key": "Helix membership card",
    "aliases": ["card", "membership", "helix card"],
    "typeclass": "typeclasses.items.Document",
    "desc": "A slim black card with the Helix mark foiled along one edge and a "
            "contact chip seated flush in the corner. The name on it is the one "
            "the house uses, which is not necessarily the one on anybody's "
            "papers.",
    "attrs": [
        ("category", "document"),
        ("issuer", "Helix Lounge"),
        ("authority", "commercial"),
        ("protocol", "contact chip"),
        ("protocol_ok", True),
        ("weight", 0.01),
    ],
}
