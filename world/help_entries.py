"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "tokens",
        "aliases": ["token", "braces"],
        "category": "Character",
        "text": """
            |cDescription Tokens|n

            Tokens are words wrapped in |w{braces}|n inside a description. When
            the description is shown, each token is replaced with the right word
            for the viewer and the situation. Any text that is |wnot|n in braces
            is shown exactly as written, so you only need tokens where something
            must change.

            There are two kinds of tokens: |wpronoun tokens|n and
            |wnumber-flexible tokens|n.

            # subtopics

            ## pronouns

            Pronoun tokens adapt to your character's gender and to whoever is
            looking. Use the lowercase form mid-sentence and the capitalized
            form at the start of a sentence.

                |w{they}|n / |w{They}|n         - subject  (he, she, they, you)
                |w{them}|n / |w{Them}|n         - object   (him, her, them, you)
                |w{their}|n / |w{Their}|n       - possessive (his, her, their, your)
                |w{theirs}|n / |w{Theirs}|n     - possessive absolute
                |w{themself}|n / |w{themselves}|n - reflexive

            A viewer looking at someone else sees third-person pronouns matching
            that character's gender; the character themself sees "you/your".

            Example:

                a long scar runs down {their} cheek

                others see -> a long scar runs down her cheek
                you see    -> a long scar runs down your cheek

            ## number

            Number-flexible tokens let a single description read naturally
            whether a body part is paired (both present) or a lone survivor
            (one lost). The token flexes between plural and singular to match.

            Brace the |wbody-part noun|n and any |wverb|n that must agree with
            it:

                deep brown {eyes} that {accent} {their} skin

                both present -> deep brown eyes that accent their skin
                one present  -> a deep brown eye that accents their skin

            The recognised part nouns are the symmetric pairs: eye, ear, arm,
            hand, thigh, shin, foot. A single braced word that is |wnot|n one of
            these is treated as a verb and conjugated to match.

            |wArticles:|n brace |w{an eye}|n (or |w{a hand}|n) to let the
            article appear only in the singular form and drop in the plural.
            The article re-agrees a/an automatically.

            Caveat: if you put an adjective between the article and the noun,
            omit the article from the brace and write it plainly, so the plural
            stays clean. Prefer:

                {eyes} of pale jade        not   {an eyes} of pale jade

            ## verbatim

            Braces are entirely optional. A description with no tokens is shown
            verbatim, exactly as you typed it. Use tokens only where the wording
            must change for the viewer (pronouns) or for missing body parts
            (number). Anything the resolver does not recognise is left on screen
            literally with its braces intact, so a typo like |w{thier}|n is easy
            to spot in the preview rather than silently vanishing.

            See also: |whelp @longdesc|n.
        """,
    },
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
]
