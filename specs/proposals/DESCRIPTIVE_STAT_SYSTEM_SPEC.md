# Descriptive Stat System Specification

Each G.R.I.M. stat (Grit, Resonance, Intellect, Motorics) is shown on the `@stats` / `score` sheet and the web character page as a word, not a number. The 0–150 scale is cut into 26 alphabetical tiers, A to Z, and each stat has its own 26-word vocabulary. Tiers A to Y each cover six points; Z is exactly 0. Stats are still stored and used as numbers; the words are a display layer only.

## Tiers

| Tier | Range | Note |
|---|---|---|
| A | 145–150 | Apex tier |
| B | 139–144 | |
| C | 133–138 | |
| D | 127–132 | |
| E | 121–126 | |
| F | 115–120 | |
| G | 109–114 | |
| H | 103–108 | |
| I | 97–102 | |
| J | 91–96 | |
| K | 85–90 | |
| L | 79–84 | |
| M | 73–78 | |
| N | 67–72 | |
| O | 61–66 | |
| P | 55–60 | |
| Q | 49–54 | |
| R | 43–48 | |
| S | 37–42 | |
| T | 31–36 | |
| U | 25–30 | |
| V | 19–24 | |
| W | 13–18 | |
| X | 7–12 | |
| Y | 1–6 | Near-zero tier |
| Z | 0 | Zero tier |

## Who sees what

- **Players.** The `@stats` / `score` sheet and the web character page show only the descriptive word.
- **Character creation**, in game and on the web, shows and takes the exact numbers: the player shares out 300 points, 1–150 per stat. 📋 UNBUILT (no issue, not decided): descriptors in character creation.
- **Staff.** Staff running `@stats/numeric` see the word plus the exact number, e.g. `Granite (112)`. No help file or command shows the tier range. 📋 UNBUILT (no issue, not decided): tier ranges in help files.
- **Other characters' sheets.** Staff (Builder or above, not quelled) can read another character's sheet with `@stats <target>`, adding `/numeric` for exact values. Anyone else who names a target is told "You can only check your own evaluation."
- **Universal application.** All Character typeclass entities (PCs, NPCs, mobs) use this system.
- **Thematic consistency.** Each stat has its own vocabulary that reflects its nature.

## The `@stats` sheet

The `@stats` sheet is a 48-column boxed "PSYCHOPHYSICAL EVALUATION REPORT" listing one stat per row. The staff `/numeric` view shows the word plus the exact value — `Grit: Granite (112)` — never the tier range. The `@stats` help text is the `CmdStats` docstring, which names the A–Z tier system but does not carry a per-stat range table.

The same box carries a "Ratings:" block for skills. The skill system is `world/manifest.py`: fourteen ratings, with `letter_for()` giving the same A–Z tiers on the same 0–150 scale. The sheet lists at most six ratings, highest first (`rated_skills`), each as its A–Z letter from `letter_for`; staff using `/numeric` also see the number in brackets. A character with no ratings gets "(no ratings on file)". Per-skill word lists are not built. See [`SKILLS_AND_DESIGNATION_SPEC.md`](SKILLS_AND_DESIGNATION_SPEC.md) and #2082.

## Stat Progressions

### GRIT (Physical Toughness & Endurance)

Grit represents physical resilience, pain tolerance, and the ability to endure hardship.

- **A (145-150)**: Apex - Legendary physical resilience
- **B (139-144)**: Bulletproof - Extreme damage resistance
- **C (133-138)**: Concrete - Nearly unbreakable toughness
- **D (127-132)**: Durable - Exceptional physical resilience
- **E (121-126)**: Enduring - Superior stamina and toughness
- **F (115-120)**: Fortified - Well-hardened constitution
- **G (109-114)**: Granite - Rock-solid physical foundation
- **H (103-108)**: Hardy - Robust and resilient
- **I (97-102)**: Iron-willed - Strong determination and endurance
- **J (91-96)**: Juggernaut - Unstoppable physical momentum
- **K (85-90)**: Keen - Sharp physical awareness and endurance
- **L (79-84)**: Lasting - Good sustained endurance
- **M (73-78)**: Moderate - Average physical resilience
- **N (67-72)**: Normal - Typical toughness levels
- **O (61-66)**: Ordinary - Standard physical endurance
- **P (55-60)**: Passable - Adequate but unremarkable
- **Q (49-54)**: Questionable - Below-average resilience
- **R (43-48)**: Rough - Poor physical condition
- **S (37-42)**: Soft - Weak physical constitution
- **T (31-36)**: Tender - Easily damaged or exhausted
- **U (25-30)**: Unstable - Very poor physical state
- **V (19-24)**: Vulnerable - Extremely fragile condition
- **W (13-18)**: Weak - Severely compromised toughness
- **X (7-12)**: Xerotic - Dried out, withered resilience
- **Y (1-6)**: Yielding - Virtually no resistance left
- **Z (0)**: Zero - Complete physical breakdown

### RESONANCE (Social Connection & Empathy)

Resonance represents social awareness, empathy, and the ability to connect with others.

- **A (145-150)**: Attuned - Perfect social synchronization
- **B (139-144)**: Bonded - Deep emotional connections
- **C (133-138)**: Charismatic - Naturally magnetic presence
- **D (127-132)**: Dynamic - Energetic social engagement
- **E (121-126)**: Empathetic - Exceptional emotional understanding
- **F (115-120)**: Fluid - Smooth social interactions
- **G (109-114)**: Gracious - Naturally diplomatic and kind
- **H (103-108)**: Harmonious - Well-balanced social skills
- **I (97-102)**: Intuitive - Strong social instincts
- **J (91-96)**: Jovial - Naturally uplifting presence
- **K (85-90)**: Kind - Genuine warmth and consideration
- **L (79-84)**: Likeable - Generally pleasant company
- **M (73-78)**: Moderate - Average social capabilities
- **N (67-72)**: Natural - Standard social functioning
- **O (61-66)**: Open - Reasonably approachable
- **P (55-60)**: Polite - Basic social courtesies
- **Q (49-54)**: Quiet - Limited social engagement
- **R (43-48)**: Reserved - Withdrawn from others
- **S (37-42)**: Stiff - Awkward social interactions
- **T (31-36)**: Tense - Uncomfortable social presence
- **U (25-30)**: Uncomfortable - Poor social ease
- **V (19-24)**: Vacant - Emotionally disconnected
- **W (13-18)**: Withdrawn - Severely isolated
- **X (7-12)**: Xenophobic - Fear and hatred of others
- **Y (1-6)**: Yearning - Desperately lonely
- **Z (0)**: Zero - Complete social isolation

### INTELLECT (Reasoning & Knowledge)

Intellect represents analytical thinking, problem-solving, and accumulated knowledge.

- **A (145-150)**: Absolute - Perfect cognitive clarity
- **B (139-144)**: Brilliant - Exceptional intellectual capability
- **C (133-138)**: Calculating - Precise analytical mind
- **D (127-132)**: Discerning - Sharp judgment and insight
- **E (121-126)**: Enlightened - Superior understanding
- **F (115-120)**: Focused - Clear, concentrated thinking
- **G (109-114)**: Gifted - Naturally talented intellect
- **H (103-108)**: Heightened - Enhanced mental acuity
- **I (97-102)**: Incisive - Sharp, penetrating analysis
- **J (91-96)**: Judicious - Wise decision-making
- **K (85-90)**: Knowledgeable - Well-informed understanding
- **L (79-84)**: Logical - Sound reasoning abilities
- **M (73-78)**: Methodical - Systematic thinking approach
- **N (67-72)**: Normal - Standard cognitive function
- **O (61-66)**: Observant - Good attention to detail
- **P (55-60)**: Practical - Basic problem-solving skills
- **Q (49-54)**: Questioning - Uncertain mental clarity
- **R (43-48)**: Rough - Poor cognitive processing
- **S (37-42)**: Slow - Sluggish mental responses
- **T (31-36)**: Troubled - Confused thinking patterns
- **U (25-30)**: Unclear - Muddled thought processes
- **V (19-24)**: Vacant - Empty mental state
- **W (13-18)**: Wandering - Severely unfocused mind
- **X (7-12)**: Xeric - Barren, desert-like cognition
- **Y (1-6)**: Yearning - Grasping for basic understanding
- **Z (0)**: Zero - Complete cognitive shutdown

### MOTORICS (Physical Coordination & Dexterity)

Motorics represents fine motor control, hand-eye coordination, and physical grace.

- **A (145-150)**: Artful - Perfect physical expression
- **B (139-144)**: Balletic - Graceful, flowing movement
- **C (133-138)**: Coordinated - Exceptional body control
- **D (127-132)**: Dexterous - Skilled hand-eye coordination
- **E (121-126)**: Elegant - Refined physical grace
- **F (115-120)**: Fluid - Smooth, natural movement
- **G (109-114)**: Graceful - Naturally beautiful motion
- **H (103-108)**: Harmonized - Well-balanced coordination
- **I (97-102)**: Intuitive - Natural movement instincts
- **J (91-96)**: Jaunty - Confident, sprightly movement
- **K (85-90)**: Kinetic - Good physical energy and control
- **L (79-84)**: Limber - Flexible and responsive
- **M (73-78)**: Mobile - Standard movement capabilities
- **N (67-72)**: Nimble - Reasonably quick and agile
- **O (61-66)**: Ordinary - Average physical coordination
- **P (55-60)**: Passable - Adequate but unremarkable
- **Q (49-54)**: Questionable - Uncertain coordination
- **R (43-48)**: Rigid - Stiff, uncomfortable movement
- **S (37-42)**: Stilted - Awkward physical expression
- **T (31-36)**: Trembling - Unsteady motor control
- **U (25-30)**: Unsteady - Poor physical stability
- **V (19-24)**: Vacant - Disconnected from body
- **W (13-18)**: Wobbly - Severely impaired coordination
- **X (7-12)**: Xyloid - Wooden, stiff motor function
- **Y (1-6)**: Yielding - Barely controllable movement
- **Z (0)**: Zero - Complete motor shutdown

## Technical Implementation

### Code Integration

- `STAT_DESCRIPTORS` in `world/combat/constants.py` holds all four vocabularies. Each tier is keyed on its **maximum** value (`150: "Apex", 144: "Bulletproof", 138: "Concrete", ...`). The ranges themselves are held separately in `STAT_TIER_RANGES` in the same file.
- `get_stat_descriptor(stat_name, numeric_value)` in `commands/CmdCharacter.py` turns a number into its word.
- `get_stat_range(descriptor_word, stat_name)` in the same file returns the `(min_value, max_value)` range for a word.
- `get_stat_tier_info` in the same file also returns the tier letter.
- `CmdStats` (`@stats` / `score`) renders the sheet; `web/website/views/characters.py` renders the same descriptors on the web character page.

### Backward Compatibility

- Stats are stored as numbers, unchanged.
- All combat calculations use the numeric values.
- Only the display layer shows descriptive words.
- Staff switch between descriptive and numeric views with `/numeric`.

### Proposed Display Formats

📋 UNBUILT: the formats below are proposed. The game does not render them; the live sheet is the one described under "The `@stats` sheet" above.

**Character Sheet Display** (two stats per row):
```
GRIT: Granite        RESONANCE: Harmonious
INTELLECT: Logical   MOTORICS: Fluid
```

**Admin/Debug Display** (word, tier range and exact value):
```
GRIT: Granite (109-114, actual: 112)
RESONANCE: Harmonious (103-108, actual: 105)
```

**Help File Content** (per-stat range table):
```
@stats - Character Statistics

Your character's capabilities are measured in four core areas:

GRIT (Physical Toughness): From Apex (145-150) to Zero (0)
RESONANCE (Social Connection): From Attuned (145-150) to Zero (0)
INTELLECT (Reasoning): From Absolute (145-150) to Zero (0)
MOTORICS (Coordination): From Artful (145-150) to Zero (0)

Descriptors A to Y each cover six points; Z is exactly 0.
```

## Design Rationale

The aim is a more immersive, narrative-focused character progression system that keeps full compatibility with existing combat and character mechanics.

### Alphabetical Organization
- **Intuitive**: A-Z progression is universally understood
- **Memorable**: Easier to remember relative power levels
- **Elegant**: Clean, systematic organization

### Six-Point Ranges
- **Meaningful Differences**: Each tier represents noticeable capability difference
- **Granular Enough**: 26 tiers provide sufficient progression granularity
- **Round Numbers**: Clean mathematical progression

### Thematic Vocabularies
- **Immersive**: Reinforces the gritty, realistic tone
- **Distinctive**: Each stat has its own personality through word choice
- **Progressive**: Words clearly indicate relative capability levels

### Universal Application
- **Consistency**: All entities use same descriptive system
- **Simplicity**: Single system to learn and understand
- **Scalability**: Easy to add new content using existing framework

## Unbuilt

Besides the two items under "Who sees what" (descriptors in character creation; tier ranges in help files), the proposed display formats above, and per-skill word lists (see `SKILLS_AND_DESIGNATION_SPEC.md`):

### Potential Enhancements
- Colored tier displays (green for high, red for low) 📋 UNBUILT (no issue, not decided)
- Detailed tier descriptions in help files 📋 UNBUILT (no issue, not decided)
- Stat comparison tools using descriptive words 📋 UNBUILT (no issue, not decided)
- Integration with character generation system 📋 UNBUILT (no issue, not decided)
- Narrative text generation based on stat descriptors 📋 UNBUILT (no issue, not decided)

### Customization Options
- Server-configurable descriptor word sets 📋 UNBUILT (no issue, not decided)
- Language localization support 📋 UNBUILT (no issue, not decided)
- Theme-specific vocabulary variations 📋 UNBUILT (no issue, not decided)
- Player preference for numeric vs. descriptive display 📋 UNBUILT (no issue, not decided)

## Not decided

- Are the range-style admin view and the help-file per-stat range table still wanted, or should they be dropped from the proposed display formats?

## Related documents

- [`SKILLS_AND_DESIGNATION_SPEC.md`](SKILLS_AND_DESIGNATION_SPEC.md) — the skill ratings that share the A–Z scale (#2082).
