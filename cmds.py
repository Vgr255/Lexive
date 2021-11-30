import argparse
import random
import os

from typing import List, Tuple, Optional, Iterable

import discord
from discord.ext.commands.context import Context

from loader import (
    casefold,
    load,
    mechanics,
    player_cards,
    player_mats,
    nemesis_cards,
    nemesis_mats,
    waves,
    treasure_values,
    cards_num,
    ctypes,
    assets,
)

_owner_cmds = ("eval", "reload")

import config

cmds = {}
content_dicts = []

def command(name=None):
    def wrapper(func):
        nonlocal name
        if name is None:
            name = func.__name__
        cmds[name] = func
        return func
    return wrapper

def get_card(guild, name: str) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    guild: int = guild.id if guild is not None else 0
    mention = None # Optional
    if "<@!" in name and ">" in name: # mentioning someone else
        index = name.index("<@!")
        name, mention = name[:index], name[index:]
    for x in ("@", "#"): # ignore what's after
        if x in name:
            name = name[:name.index(x)]
    ass = []
    arg = casefold(name)
    possible = set()
    for func, mapping in content_dicts:
        possible.update(mapping.keys())
    matches = complete_match(arg, possible)
    values = []
    if len(matches) > config.max_dupes:
        values.append(None)
        for x in matches:
            for func, d in content_dicts:
                if x in d:
                    for n in d[x]:
                        if n["name"] not in values:
                            values.append(n["name"])

        return values, ass
    for x in matches:
        for func, mapping in content_dicts:
            if x in mapping:
                ret = func(guild, x)
                if ret:
                    values.append(ret)
        if x in assets:
            ass.append(assets[x])

    if not values:
        return None, ass

    ret = []
    if mention is not None:
        ret.append(mention)
    for x in values:
        if ret:
            ret.append(r"\NEWLINE/")
        ret.extend(x)

    return ret, ass

def complete_match(string: str, matches: Iterable[str]) -> list:
    possible_matches = set()
    for possible in matches:
        if string == possible:
            return [string]
        if possible.startswith(string) or string in possible:
            possible_matches.add(possible)
    return sorted(possible_matches)

# Create the randomizer and its parser

class ArgParser(argparse.ArgumentParser):
    def print_usage(self, file=None) -> None:
        super().print_usage(HelperFile())
    def print_help(self, file=None):
        super().print_help(HelperFile())
    def exit(self, status=0, message=None):
        raise RuntimeError(message)

class HelperFile:
    def write(self, content):
        raise RuntimeError(f"```\n{content}\n```")

_randomizer_args = ArgParser(prog="random", description="Generate a random market, mages and nemesis", add_help=False)

_randomizer_args.add_argument("--help", "-h", action="help", default=argparse.SUPPRESS, help="Prints this help message")

_randomizer_args.add_argument("--player-count", "-p", type=int, default=2, choices=range(1, 5), help="How many mages are going to play")

_randomizer_args.add_argument("--gem-count", "-g", type=int, default=3, choices=range(10), help="How many gems to include in the market")
_randomizer_args.add_argument("--force-cheap-gem", "-c", action="store_true", help="If set and --gem-count > 0, forces at least one gem costing at most 3")
_randomizer_args.add_argument("--relic-count", "-r", type=int, default=2, choices=range(10), help="How many relics to include in the market")
_randomizer_args.add_argument("--spell-count", "-s", type=int, default=4, choices=range(10), help="How many spells to include in the market")

_randomizer_args.add_argument("--lowest-difficulty", "-d", type=int, default=1, choices=range(11), help="The lowest nemesis difficulty to allow")
_randomizer_args.add_argument("--highest-difficulty", "-D", type=int, default=10, choices=range(11), help="The highest nemesis difficulty to allow")

_randomizer_args.add_argument("--minimum-rating", "-m", type=int, default=1, choices=range(11), help="The minimum mage complexity rating to allow")
_randomizer_args.add_argument("--maximum-rating", "-M", type=int, default=10, choices=range(11), help="The maximum complexity rating to allow")

#_randomizer_args.add_argument("--expedition", "-e", action="store_true", help="If set, will generate an expedition of length specified in --expedition-length")
#_randomizer_args.add_argument("--expedition-length", "-E", type=int, default=4, choices=range(1, 9), help="How many battles the expedition should be")

#_randomizer_args.add_argument("--boxes", "-b", action="extend", default=waves, choices=waves, help="From which boxes should the content be pulled")

_randomizer_args.add_argument("--verbose", "-v", action="count", default=0, help="Turn on verbose output (up to -vvv)")

def _isin(code: str, *items: str) -> bool:
    """Temporary hack until the parser is functional."""
    for item in items:
        if f"{item}=" in code:
            return True
    return False

@command("random")
async def random_cmd(ctx: Context, *args):
    # TODO: Add expedition support
    try:
        namespace = _randomizer_args.parse_args(args)
    except (argparse.ArgumentError, RuntimeError) as e:
        await ctx.send(str(e))
        return

    verbose = namespace.verbose

    # TODO: Allow users to add and select which boxes they have (probably a SQL db or something)

    if verbose >= 1:
        await ctx.send(f"Settings: {namespace}")

    message = ["Random battle:", ""]

    # TODO: Add box handling (and make sure that there's enough mages/markets/etc.)
    boxes = list(waves)
    message.append("Using ALL released content (currently not configurable, will be in the future)")
    message.append("")

    nemesis = None
    count = 0
    while nemesis is None:
        count += 1
        if count == 1000:
            await ctx.send("Could not find a matching nemesis")
            return
        values = random.choice(list(nemesis_mats.values()))
        value = random.choice(values)
        if verbose >= 2:
            await ctx.send(f"Checking {value['name']}")
        if not (namespace.lowest_difficulty <= value["difficulty"] <= namespace.highest_difficulty):
            if verbose >= 3:
                await ctx.send("Difficulty doesn't match")
            continue
        if "NOEXP" in value["code"]:
            continue
        if value["box"] not in boxes:
            if verbose >= 3:
                await ctx.send("Box doesn't match")
            continue
        nemesis = value

    message.append(f"Fighting {nemesis['name']} (difficulty {nemesis['difficulty']})")

    mages = []
    count = 0
    while len(mages) < namespace.player_count:
        count += 1
        if count == 1000:
            await ctx.send("Could not find enough mages")
            return
        values = random.choice(list(player_mats.values()))
        value = random.choice(values)
        if value in mages:
            if verbose >= 3:
                await ctx.send(f"Found {value['name']} but already in, skipping")
            continue
        if verbose >= 2:
            await ctx.send(f"Checking {value['name']}")
        if not (namespace.minimum_rating <= value["rating"] <= namespace.maximum_rating):
            if verbose >= 3:
                await ctx.send("Complexity rating doesn't match")
            continue
        if value["box"] not in boxes:
            if verbose >= 3:
                await ctx.send("Box doesn't match")
            continue

        mages.append(value)

    message.append(f"Using mages {', '.join(m['name'] for m in mages)}")

    # Note: this block below checks the code column in a very hacky way
    # This is going to be improved when the parser is complete

    gems = []
    relics = []
    spells = []
    count = 0
    while len(gems) < namespace.gem_count or len(relics) < namespace.relic_count or len(spells) < namespace.spell_count:
        count += 1
        if count == 5000:
            await ctx.send("Could not find enough market cards")
            return
        for value in random.choice(list(player_cards.values())):
            if value["type"] == "G":
                if not gems and namespace.force_cheap_gem and value["cost"] > 3:
                    continue
                if len(gems) >= namespace.gem_count:
                    continue
                if value["starter"]:
                    continue
                if _isin(value["code"], "T", "U", "N"):
                    continue
                if value not in gems:
                    gems.append(value)
            if value["type"] == "R":
                if len(relics) >= namespace.relic_count:
                    continue
                if value["starter"]:
                    continue
                if _isin(value["code"], "T", "U", "N"):
                    continue
                if value not in relics:
                    relics.append(value)
            if value["type"] == "S":
                if len(spells) >= namespace.spell_count:
                    continue
                if value["starter"]:
                    continue
                if _isin(value["code"], "T", "U", "N"):
                    continue
                if value not in spells:
                    spells.append(value)

    gems.sort(key=lambda x: x["cost"])
    relics.sort(key=lambda x: x["cost"])
    spells.sort(key=lambda x: x["cost"])

    for name, container in (("gems", gems), ("relics", relics), ("spells", spells)):
        message.append("")
        message.append(f"Market {name}:")
        message.extend([f"{value['name']} (from {value['box']}, {value['cost']}-cost)" for value in container])

    await ctx.send("\n".join(message))

@command()
async def info(ctx: Context, *args):
    arg = "".join(args)
    if not arg:
        await ctx.send("No argument provided.")
        return
    if not arg.isalpha() and arg.isalnum(): # has numbers and no special characters
        await ctx.send(f"Number detected. Did you want `{config.prefix}card` instead?")
        return
    values, asset = get_card(ctx.guild, arg)
    if values and values[0] is None: # too many values
        to_send = f"Ambiguous value. Possible matches: {', '.join(values[1:])}"
    elif not values:
        to_send = f"No content found matching {' '.join(args)}"
    else:
        to_send = "\n".join(values)

    for msg in to_send.split(r"\NEWLINE/"):
        await ctx.send(msg)
    for ass in asset:
        with open(os.path.join("assets", ass), mode="rb") as a:
            await ctx.send(file=discord.File(a))

@command()
async def card(ctx: Context, *args):
    await ctx.send(card_(casefold("".join(args)).upper(), detailed=True))

def card_(arg: str, *, detailed=False) -> str:
    if arg.isdigit():
        return "No prefix supplied."
    index = 0
    for i, x in enumerate(arg):
        if x.isdigit():
            index = i
            break
    if not index:
        return f"No number found. Did you want `{config.prefix}info` instead?"
    prefix, num = arg[:index], arg[index:]
    deck = None
    if ("I" in prefix or prefix == "V") and "T" not in prefix: # Legacy and not Into the Wild
        deck = prefix
        prefix = None
    if not num.isdigit(): # probably has a deck in it, like 1a
        if num[0].isdigit() and num[1].isalpha() and num[2:].isdigit():
            deck, num = num[:2], num[2:]
    if prefix not in cards_num:
        return f"Prefix {prefix} is unrecognized"
    values = cards_num[prefix]
    # this is a hack
    if deck and len(deck) == 2 and deck[1] in "ABCD":
        deck = deck[0] + deck[1].lower()
    if deck not in values:
        return f"Deck {deck} not recognized"
    num = int(num)
    if num not in values[deck]:
        return f"Card {num} is unknown"

    ctype, name = values[deck][num]
    if not detailed:
        return name

    if ctype == "P":
        ctype = "Player card"
    elif ctype == "N":
        ctype = "Nemesis card"
    elif ctype == "T":
        ctype = "Treasure card"
    elif ctype == "O":
        ctype = "Xaxos: Outcast Ability"
    else:
        ctype = "Unknown card type"

    return f"{name} ({ctype})"

@command()
async def box(ctx: Context, *args):
    arg = "".join(args)
    arg = casefold(arg)
    mapping = {casefold(x): x for x in waves}
    values = complete_match(arg, mapping)
    if len(values) > 1:
        await ctx.send(f"Ambiguous value. Possible matches: {', '.join(values)}")
        return
    if not values:
        await ctx.send("No match found")
        return

    box = mapping[values[0]]
    prefix = waves[box][0]
    
    result = ["```", f"Cards from {box}:", ""]
    count = len(" ".join(result))
    c = {"P": player_cards, "N": nemesis_cards, "T": treasure_values, "O": treasure_values}

    for deck in cards_num[prefix]:
        if count >= 1800:
            result.append("```\\NEWLINE/```")
            count = 3
        if deck:
            result.extend([f"```\\NEWLINE/```", f"Deck: {deck}", ""])
            count = len(deck) + 12
        for num, (ctype, card) in cards_num[prefix][deck].items():
            if count >= 1800:
                result.append("```\\NEWLINE/```")
                count = 3
            ind = c[ctype][casefold(card)]
            for d in ind:
                if d['box'] != box:
                    continue
                if count >= 1800:
                    result.append("```\\NEWLINE/```")
                    count = 3
                result.append(f"- {card} ({ctypes[d['type']]}) ({num})")
                count += len(result[-1])

    result.append("```")

    for line in "\n".join(result).split("\\NEWLINE/"):
        await ctx.send(line)

@command()
async def search(ctx: Context, *args):
    arg = " ".join(args).lower()
    final = []
    guild = ctx.guild.id
    for mapping, attrs in (
        (player_cards, ("text", "special", "flavour")),
        (nemesis_cards, ("effect", "special", "immediate", "discard", "flavour")),
        (player_mats, ("special", "title", "flavour", "ability:name", "ability:effect")),
        (nemesis_mats, ("unleash", "id_unleash", "setup", "id_setup", "extra", "side", "additional_rules", "id_rules", "flavour")),
        (treasure_values, ("effect", "flavour")),
    ):

        for content in mapping.values():
            for inner in content:
                if inner['guild'] != 0 and inner['guild'] != guild:
                    # cannot be used in this guild
                    continue
                for attr in attrs:
                    name, _, second = attr.partition(":")
                    c = inner[name]
                    if second:
                        c = c[second]
                    if arg in c.lower():
                        final.append(inner)

    if final:
        await ctx.send(f"Found the following content for pattern `{arg}`:")
        l = 0
        msg = []
        for x in final:
            if l >= 1800:
                await ctx.send("\n".join(msg))
                msg.clear()
                l = 0
            msg.append(f"- {x['name']}")
            l += len(x["name"]) + 2
        if msg:
            await ctx.send("\n".join(msg))
    else:
        await ctx.send(f"Could not find anything matching pattern `{arg}`.")

@command()
async def unique(ctx: Context, *args):
    await ctx.send("```\nThe unique mechanics that I know about are as follow. " +
    f"You may prefix them with {config.prefix} to ask me about them.\n- " +
    "\n- ".join(mechanics) + "\n```")

@command()
async def reload(ctx: Context, *args):
    if await ctx.bot.is_owner(ctx.author):
        print("\nReloading content")
        load()
        await ctx.send("Reloaded data.")

@command()
async def issues(ctx: Context, *args):
    content = f"""* Known issues and to-do list *

- Entwined Amethyst will send a similar message twice;
- Not all Legacy-specific content is implemented;
- !card doesn't return a block of text yet.

Report all other issues using `{config.prefix}report <issue>`

"""

    await ctx.send(content)

@command()
async def github(ctx: Context, *args):
    await ctx.send("https://github.com/Vgr255/Lexive")

@command("eval")
async def eval_(ctx: Context, *args):
    if await ctx.bot.is_owner(ctx.author):
        await ctx.send(eval(" ".join(args)))

@command()
async def faq(ctx: Context, *args):
    await ctx.send("https://www.querki.net/u/aefaq/aeons-end-faq")

@command()
async def wiki(ctx: Context, *args):
    await ctx.send("https://aeonsend.fandom.com/")

@command("commands")
async def commands_cmd(ctx: Context, *args):
    msg = list(cmds)
    for c in _owner_cmds:
        if c in msg:
            msg.remove(c)
    msg.sort()
    await ctx.send("```\nCommands:\n- " + "\n- ".join(msg) + "```")

#@command()
# No longer used, keeping for posterity
async def outcasts(ctx: Context, *args):
    await ctx.send("""Known issues with the first Outcasts printing (from the Kickstarter):

- Ilya's Deck: Stop Deck 1b contains the wrong starter cards for Ilya. Her starting hand and \
deck should both include two Sparks. The final two cards of the End deck are Sparks and can \
be used without spoiling any other content. IBC has confirmed this was an error. The missing \
cards will be provided to backers of the AE6 Kickstarter, and there will be a TBD alternate \
method of getting replacement cards for Outcast backers that don't plan to back AE6. \
IBC has provided Print and Play Sparks as a short term solution.
- Envelope 1b is mislabeled. It should read Envelope 1d. IBC has confirmed this was an error.
- The battle 3 nemesis has inconsistent special rules between the nemesis mat and its reminder \
card. Nick Little has confirmed that the Nemesis mat is correct. IBC has provided a Print and \
Play replacement as a short term solution.""")

    await ctx.send("""There have been a few typos identified in the rulebook:
- In the contents list on page 2, it should state that 40 life tokens with value 1 are included rather than 35.
- In the contents list on page 3, it should state that 10 stop decks are included rather than 11.
- In the contents list on page 3, it should state that 24 card dividers are included rather than 39.
- In the player setup graphic on page 9, the incorrect order is shown for Kel's starting deck. \
The Crystals should be on the top of her deck, and the Trulite of Energy should be on the bottom.

There are no card dividers for the Xaxos: Outcast abilities and the Curse decks. IBC has provided \
a Print and Play alternative, and have stated that they may include them in a future Kickstarter.

Wave 4 expansion "The Ancients"'s punchboard for Mazra's Research breach and Qu's Form token \
is not pre-punched. This affects all content printed alongside Outcasts's Kickstarter. IBC \
is working on reprinting them and sending them out to all backers.

Thread: <https://boardgamegeek.com/thread/2499061/outcasts-errata> (maintained by Will)

""")
