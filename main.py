from typing import Optional, Tuple, Iterable, Callable, List, Dict
from collections import defaultdict

import discord
import csv
from discord.ext import commands

import config

# the following characters will be stripped from the csv names when stored
# and also ignored from messages (so that they are optional)
# this is a sequence of 1-length strings
_casefold_str = " ',:-!()"
# this character will be replaced by a newline when sent to the discord
# this is a str
_newline_str = "#"
# this character will be replaced by the prefix from the config
# this is a str
_prefix_str = "!"

VERSION = "0.1"
AUTHOR = "Anilyka Barry"
author_id = 320646088723791874

player_cards = defaultdict(list)
nemesis_cards = defaultdict(list)
player_mats = defaultdict(list)
nemesis_mats = defaultdict(list)
breach_values = defaultdict(list)
treasure_values = defaultdict(list)

content_dicts = []

def sync(d):
    def wrapper(func):
        content_dicts.append((func, d))
        return func
    return wrapper

cards_num = {} # type: Dict[str, Dict[int, Tuple[str, str]]]

waves = {
    "Aeon's End": ("AE", 1),
    "The Nameless": ("N", 1),
    "The Depths": ("D", 1),
    "War Eternal": ("W", 2),
    "The Void": ("V", 2),
    "The Outer Dark": ("O", 2),
    "Legacy": (None, 3),
    "Buried Secrets": ("BS", 3),
    "The New Age": ("NA", 4),
    "The Ancients": ("TA", 4),
    "Shattered Dreams": ("SD", 4),
    "Into the Wild": ("ITW", 4),
    "Outcasts": ("O", 5),
    "Southern Village": ("SV", 5),
    "Return to Gravehold": ("RTG", 5),
    "Dice Tower": ("P", 2),
    "Legacy (Kickstarter Exclusive)": ("P", 3),
    "The New Age (Kickstarter Exclusive)": ("P", 4),
    "Outcasts (Kickstarter Exclusive)": ("P", 5),
}

ctypes = {
    # Player cards
    "G": "Gem", "R": "Relic", "S": "Spell",
    # Nemesis cards
    "P": "Power", "M": "Minion", "A": "Attack",
    # Treasures
    "TG": "Treasured Gem", "TS": "Treasured Spell",
    "T2": "Treasure Level 2", "T3": "Treasure Level 3",
    # Outcasts content
    "O": "Xaxos: Outcast Ability", "C": "Curse",
    # Nemesis-specific types
    "N": "Corruption", "K": "Strike", "Y": "Minion-Acolyte",
}

ability_types = {
    "P": "during any player's main phase",
    "M": "during your main phase",
    "N": "during the nemesis draw phase",
    "T": "immediately after a turn order card is drawn",
    "C": "during your casting phase",
    "A": "during any ally's main phase",
    "Y": "during your casting or main phase",
    "D": "at the end of your draw phase",
}

breaches_orientation = (
    "Open",
    "Facing up",
    "Facing left",
    "Facing down",
    "Facing right",
)

# Breach opening cost formula:
# ((position-1)*number of focuses needed to open)+1
# (position*number of focuses)-number of focuses+1

def log(*x: Tuple[str], level:str="use", **kwargs) -> None:
    # probably gonna log to a file at some point
    print(*x, **kwargs)

def casefold(x: str) -> str:
    x = x.lower()
    for c in _casefold_str:
        x = x.replace(c, "")
    return x

def expand(x: str, *, flavour=False, prefix=False) -> str:
    replace_by = "\n"
    if flavour: # make newlines twice as big
        replace_by = "\n\n"
    x = x.replace(_newline_str, replace_by)
    if prefix:
        x = x.replace(_prefix_str, config.prefix)
    return x

def load():
    cards_num.clear()
    for name, (prefix, wave) in waves.items():
        if prefix not in cards_num:
            cards_num[prefix] = {}

    player_cards.clear()
    with open("player_cards.csv", newline="") as player_file:
        content = csv.reader(player_file, dialect="excel", delimiter=";")
        for name, ctype, cost, code, special, text, flavour, starter, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            start = int(start)
            end = int(end)
            player_cards[casefold(name)].append({
                "name": name, "type": ctype, "cost": int(cost), "code": code,
                "special": expand(special, prefix=True), "text": expand(text),
                "flavour": expand(flavour), "starter": starter, "box": box,
                "deck": deck, "start": start, "end": end
            })
            nums = [start]
            if end and not starter:
                nums = range(start, end+1)
            elif end and starter:
                nums = [start, end]
            wave = waves[box][0]
            if not deck:
                deck = None
            if deck not in cards_num[wave]:
                cards_num[wave][deck] = {}
            for num in nums:
                cards_num[wave][deck][num] = ("P", name)

    log("Player cards loaded", level="local")

    nemesis_cards.clear()
    with open("nemesis_cards.csv", newline="") as nemesis_file:
        content = csv.reader(nemesis_file, dialect="excel", delimiter=";")
        for name, ctype, tokens_hp, shield, tier, cat, code, special, discard, immediate, effect, flavour, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            start = int(start)
            if end:
                end = int(end)
            else:
                end = 0
            nemesis_cards[casefold(name)].append({
                "name": name, "type": ctype, "tokens_hp": (int(tokens_hp) if tokens_hp else 0),
                "shield": (int(shield) if shield else 0), "tier": int(tier), "category": cat,
                "code": code, "special": expand(special, prefix=True), "discard": expand(discard),
                "immediate": expand(immediate), "effect": expand(effect), "flavour": expand(flavour),
                "box": box, "deck": deck, "start": start, "end": end
            })
            nums = [start]
            if end:
                nums = range(start, end+1)
            wave = waves[box][0]
            if not deck:
                deck = None
            if deck not in cards_num[wave]:
                cards_num[wave][deck] = {}
            for num in nums:
                cards_num[wave][deck][num] = ("N", name)

    log("Nemesis cards loaded", level="local")

    player_mats.clear()
    with open("player_mats.csv", newline="") as pmats_file:
        content = csv.reader(pmats_file, dialect="excel", delimiter=";")
        for name, title, rating, aname, charges, atype, code, ability, special, breaches, hand, deck, b1, b2, b3, b4, flavour, box in content:
            if not name or name.startswith("#"):
                continue
            adict = {"name": aname, "charges": int(charges), "type": atype, "effect": expand(ability), "code": code}
            blist = []
            for pos, breach in zip(breaches.split(","), (b1, b2, b3, b4)):
                pos = int(pos)
                if not breach: # just a regular breach
                    breach = None
                blist.append((pos, breach))
            player_mats[casefold(name)].append({
                "name": name, "title": title, "rating": rating, "ability": adict, "breaches": blist,
                "hand": hand.split(","), "deck": deck.split(","), "flavour": expand(flavour),
                "special": expand(special, prefix=True), "box": box
            })

    log("Player mats loaded", level="local")

    nemesis_mats.clear()
    with open("nemesis_mats.csv", newline="") as nmats_file:
        content = csv.reader(nmats_file, dialect="excel", delimiter=";")
        for name, hp, diff, battle, extra, unleash, setup, id_s, id_u, id_r, add_r, flavour, side, box, cards in content:
            if not name or name.startswith("#"):
                continue
            nemesis_mats[casefold(name)].append({
                "name": name, "hp": int(hp), "difficulty": diff, "unleash": expand(unleash),
                "setup": expand(setup), "additional_rules": expand(add_r), "flavour": expand(flavour),
                "extra": expand(extra), "id_setup": id_s, "id_unleash": id_u, "id_rules": id_r,
                "side": expand(side), "box": box, "battle": int(battle),
                "cards": cards.split(",")
            })

    log("Nemesis mats loaded", level="local")

    breach_values.clear()
    with open("breaches.csv", newline="") as breach_file:
        content = csv.reader(breach_file, dialect="excel", delimiter=";")
        for name, pos, focus, left, down, right, effect, mage in content:
            if not name or name.startswith("#"):
                continue
            breach_values[casefold(name)].append({
                "name": name, "position": int(pos), "focus": int(focus),
                "left": int(left), "down": int(down), "right": int(right),
                "effect": expand(effect), "mage": mage
            })

    log("Breaches loaded", level="local")

    treasure_values.clear()
    with open("treasures.csv", newline="") as treasure_file:
        content = csv.reader(treasure_file, dialect="excel", delimiter=";")
        for name, ttype, code, effect, flavour, box, deck, number in content:
            if not name or name.startswith("#"):
                continue
            treasure_values[casefold(name)].append({
                "name": name, "type": ttype, "code": code, "effect": expand(effect),
                "flavour": expand(flavour), "box": box, "deck": deck, "number": int(number)
            })
            wave = waves[box][0]
            if not deck:
                deck = None
            if deck not in cards_num[wave]:
                cards_num[wave][deck] = {}
            cards_num[wave][deck][int(number)] = ("T", name)

    log("Treasures loaded", level="local")

log("Loading content", level="local")

load()

log("Loading complete", level="local")

activity = discord.Activity(
    name=f"{config.prefix}whoami",
    application_id=0,
    url="https://github.com/Vgr255/Lexive",
    type=discord.ActivityType.playing,
    state="Studying the arcane knowledge",
)

class Lexive(commands.Bot):
    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith(config.prefix) or isinstance(message.channel, discord.DMChannel):
            content = message.content.lstrip(config.prefix)
            if not content:
                return
            if content.lower() in cmds:
                message.content = config.prefix + content
                log("CMD:", content)
                await super().on_message(message)
                return # these commands supersede cards

            values = get_card(content)
            log("REQ:", content)
            if values and values[0] is None: # too many values
                await message.channel.send(f"Ambiguous value. Possible matches: {', '.join(values[1:])}")
                return
            elif values:
                msgs = "\n".join(values).split(r"\NEWLINE/")
                for msg in msgs:
                    await message.channel.send(msg)
                return

        await super().on_message(message)

bot = Lexive(command_prefix=config.prefix, owner_id=config.owner, case_insensitive=True, activity=activity)

cmds = {}

def cmd(func: Callable) -> Callable:
    name = func.__name__.lstrip("_").replace("_", "-")
    if name in cmds:
        raise ValueError(f"duplicate function name {name}")
    cmds[name] = func
    return bot.command(name=name)(func)

@sync(player_cards)
def player_card(name: str) -> List[str]:
    card = player_cards[name]
    values = []
    for c in card:
        if values: # second pass-through or more, make it different messages
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], "", f"Type: {ctypes[c['type']]}", f"Cost: {c['cost']}", ""])
        if c['special']:
            values.append(f"** {c['special']} **")
            values.append("")
        values.append(c['text'])
        values.append("")
        if c['flavour']:
            values.append(c['flavour'])
            values.append("")
        if c['starter']:
            values.append(f"Starter card for {c['starter']}")
            values.append("")
        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")

        prefix = waves[c['box']][0]
        if prefix is None:
            prefix = c['deck']
        elif c['deck']:
            prefix += f"-{c['deck']}-"

        if c['starter'] and c['end']:
            values.append(f"Cards {prefix}{c['start']} and {prefix}{c['end']}")
        elif c['end']:
            values.append(f"Cards {prefix}{c['start']}-{prefix}{c['end']}")
        else:
            values.append(f"Card {prefix}{c['start']}")

        values.append("```")

    return values

@sync(nemesis_cards)
def nemesis_card(name: str) -> List[str]:
    card = nemesis_cards[name]
    values = []
    for c in card:
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], "", f"Type: {ctypes[c['type']]}"])
        if c['category'] == "B":
            values.append(f"Basic Nemesis (Tier {c['tier']})")
        elif c['category'] == "U":
            values.append(f"Upgraded Basic Nemesis (Tier {c['tier']})")
        elif c['category'] == "E":
            values.append(f"Fully-Evolved Legacy Basic Nemesis suitable as Upgraded Basic (Tier {c['tier']})")
        else: # Nemesis-specific card
            values.append(f"Nemesis card for {c['category']} (Tier {c['tier']})")
        if c['type'] in ("M", "Y"):
            hp = c['tokens_hp']
            if not hp:
                hp = "*"
            values.append(f"Health: {hp}")
            if c['shield']:
                values.append(f"Shield tokens: {c['shield']}")

        values.append("")

        if c['special']:
            values.append(f"** {c['special']} **\n")

        if c['immediate']:
            values.append(f"IMMEDIATELY: {c['immediate']}\n")

        if c['type'] == "P":
            if c['discard']:
                values.append(f"TO DISCARD: {c['discard']}\n")
            values.append(f"POWER {c['tokens_hp']}: {c['effect']}")

        elif c['type'] == "M":
            if c['effect']: # not all minions have a Persistent effect
                values.append(f"PERSISTENT: {c['effect']}")

        elif c['type'] == "Y":
            values.append(f"BLOOD MAGIC: {c['effect']}")

        else:
            values.append(c['effect'])

        if c['effect']:
            values.append("")

        if c['flavour']:
            values.append(f"{c['flavour']}\n")

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        prefix = waves[c['box']][0]
        if c['deck']:
            prefix = f"{prefix}-{c['deck']}-"
        if c['end']:
            values.append(f"Cards {prefix}{c['start']}-{prefix}{c['end']}")
        else:
            values.append(f"Card {prefix}{c['start']}")

        values.append("```")

    return values

@sync(player_mats)
def player_mat(name: str) -> List[str]:
    mat = player_mats[name]
    values = []
    for c in mat:
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], c['title'], f"Complexity rating: {c['rating']}", "", "Starting breach positions:", ""])

        bconv = ("I", "II", "III", "IV")
        for x in range(4):
            pos, special = c['breaches'][x]
            if pos == 9: # no breach
                values.append(f"(No breach {bconv[x]})")
                continue
            if special is None:
                special = f"Breach {bconv[x]}"
            values.append(f"{config.prefix}{special} - {breaches_orientation[pos]}")

        values.append("")
        wave = waves[c['box']][0]
        hand = []
        deck = []
        for orig, new in zip((c["hand"], c["deck"]), (hand, deck)):
            for x in orig:
                if x.isdigit():
                    x = cards_num[wave][None][int(x)][1]
                elif x[0].isdigit() and x[1].isalpha() and x[2:].isdigit():
                    x = cards_num[wave][x[:2]][int(x[2:])][1]
                elif x[:3] == "END" and x[3:].isdigit():
                    x = cards_num[wave]["END"][int(x[3:])][1]
                elif x == "C":
                    x = "Crystal"
                elif x == "S":
                    x = "Spark"
                else:
                    x = f"ERROR: Unrecognized card {x}"
                new.append(x)
        hand_readable = []
        deck_readable = []
        for orig, new in zip((hand, deck), (hand_readable, deck_readable)):
            for x in orig:
                num = 0
                if new and new[-1][3:] == x:
                    num = int(new[-1][0])
                    del new[-1]
                num += 1
                x = f"{num}x {x}"
                new.append(x)

        values.append(f"Starting hand: {', '.join(hand_readable)}")
        values.append(f"Starting deck: {', '.join(deck_readable)}")
        values.append("")

        values.append(f"Ability: {c['ability']['name']}")
        values.append(f"Charges needed: {c['ability']['charges']}")
        values.append(f"Activate {ability_types[c['ability']['type']]}:")
        values.append(c['ability']['effect'])
        values.append("")

        if c['special']:
            values.append(c['special'])
            values.append("")

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        values.append("```")

        if c['flavour']:
            values.append(r"\NEWLINE/```")
            values.append(c['flavour'])
            values.append("```")

    return values

@sync(nemesis_mats)
def nemesis_mat(name: str) -> List[str]:
    mat = nemesis_mats[name]
    values = []
    for c in mat:
        if values:
            values.append(r"\NEWLINE/")
        hp = c['hp']
        if not hp:
            hp = "*"
        values.extend(["```", f"{c['name']}", f"Health: {hp}", f"Difficulty rating: {c['difficulty']}", f"Battle: {c['battle']}", 
                       "", "SETUP:", c['setup'], "", "UNLEASH:", c['unleash'], "", "* INCREASED DIFFICULTY *"])
        if c['id_setup']:
            values.append(f"SETUP: {c['id_setup']}")
        if c['id_unleash']:
            values.append(f"UNLEASH: {c['id_unleash']}")
        if c['id_rules']:
            values.append(f"RULES: {c['id_rules']}")

        values.extend(["", "* ADDITIONAL RULES *", f"{c['additional_rules']}", ""])

        if c['extra']:
            values.extend(["Additional expedition rules:", c['extra'], ""])

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        values.append("")

        largest = 0
        box = cards_num[waves[c['box']][0]]

        cards = []
        for x in c["cards"]:
            if x.isdigit():
                deck = None
                num = int(x)
            elif x[0].isdigit() and x[1].isalpha() and x[2:].isdigit(): # regular non-Legacy stuff
                deck = x[:2]
                num = int(x[2:])
            else: # Legacy stuff
                for d in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "END"):
                    if x.startswith(d) and x[len(d):].isdigit():
                        deck = d
                        num = int(x[len(d):])

            ctype, card = box[deck][num]

            if ctype == "N":
                content = nemesis_cards[casefold(card)][0]
                cards.append((f"(Tier {content['tier']} {{0}}) {card}", ctypes[content['type']]))
            elif ctype == "P":
                content = player_cards[casefold(card)][0]
                cards.append((f"({content['cost']}-Cost {{0}}) {card}", ctypes[content['type']]))
            largest = max(largest, len(ctypes[content["type"]]))

        cards = [text.format(t.ljust(largest)) for text, t in cards]

        values.append("Cards used with this nemesis:")
        values.extend(cards)

        values.append(f"```\\NEWLINE/```\n{c['flavour']}```")

        if c['side']: # side mat
            values.append(r"\NEWLINE/```")
            values.append(f"{c['side']}```")

    return values

@sync(breach_values)
def get_breach(name: str) -> List[str]:
    b = breach_values[name]
    values = []
    for c in b:
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], f"Position: {c['position']}", ""])
        if c['focus']:
            values.append(f"Focus cost: {c['focus']}")
            values.append(f"Opening cost from UP   : {c['focus']}")
        if c['left']:
            values.append(f"Opening cost from LEFT : {c['left']}")
        if c['down']:
            values.append(f"Opening cost from DOWN : {c['down']}")
        if c['right']:
            values.append(f"Opening cost from RIGHT: {c['right']}")
        if c['focus']:
            values.append("")

        if c['effect']:
            values.append(c['effect'])

        if c['mage']:
            values.append("") # if we have a mage, there is an effect
            # [0] is "wrong", but technically mages should never overlap because if they do they have suffixes
            values.append(f"Used with {c['mage']} (From {player_mats[casefold(c['mage'])][0]['box']})")

        values.append("```")

    return values

@sync(treasure_values)
def get_treasure(name: str) -> List[str]:
    t = treasure_values[name]
    values = []
    for c in t:
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], f"Type: {ctypes[c['type']]}", "", c['effect'], ""])

        if c['flavour']:
            values.append(c['flavour'])
            values.append("")

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        prefix = waves[c['box']][0]
        if c['deck']:
            prefix = f"{prefix}-{c['deck']}-"
        values.append(f"Card {prefix}{c['number']}")
        values.append("```")

    return values

def get_card(name: str) -> Optional[List[str]]:
    mention = None # Optional
    if "<@!" in name and ">" in name: # mentioning someone else
        index = name.index("<@!")
        name, mention = name[:index], name[index:]
    for x in ("@", "#"): # ignore what's after
        if x in name:
            name = name[:name.index(x)]
    arg = casefold(name)
    possible = set()
    for func, mapping in content_dicts:
        possible.update(mapping.keys())
    matches = complete_match(arg, possible)
    values = []
    if len(matches) > config.max_dupe:
        values.append(None)
        for x in matches:
            for func, d in content_dicts:
                if x in d:
                    for n in d[x]:
                        if n["name"] not in values:
                            values.append(n["name"])

        return values
    for x in matches:
        for func, mapping in content_dicts:
            if x in mapping:
                values.append(func(x))

    if not values:
        return None

    ret = []
    if mention is not None:
        ret.append(mention)
    for x in values:
        if ret:
            ret.append(r"\NEWLINE/")
        ret.extend(x)

    return ret

def complete_match(string: str, matches: Iterable) -> list:
    possible_matches = set()
    for possible in matches:
        if string == possible:
            return [string]
        if possible.startswith(string):
            possible_matches.add(possible)
    return sorted(possible_matches)

@bot.command()
async def info(ctx, *args):
    arg = "".join(args)
    if not arg:
        await ctx.send("No argument provided.")
        return
    if not arg.isalpha() and arg.isalnum(): # has numbers and no special characters
        await ctx.send(f"Number detected. Did you want `{config.prefix}card` instead?")
        return
    values = get_card(arg)
    if values and values[0] is None: # too many values
        to_send = f"Ambiguous value. Possible matches: {', '.join(values[1:])}"
    elif not values:
        to_send = f"No content found matching {' '.join(args)}"
    else:
        to_send = "\n".join(values)

    for msg in to_send.split(r"\NEWLINE/"):
        await ctx.send(msg)

@bot.command()
async def card(ctx, *args):
    arg = casefold("".join(args)).upper()
    if arg.isdigit():
        await ctx.send("No prefix supplied.")
        return
    index = 0
    for i, x in enumerate(arg):
        if x.isdigit():
            index = i
            break
    if not index:
        await ctx.send(f"No number found. Did you want `{config.prefix}info` instead?")
        return
    prefix, num = arg[:index], arg[index:]
    deck = None
    if ("I" in prefix or prefix == "V") and "T" not in prefix: # Legacy and not Into the Wild
        deck = prefix
        prefix = None
    if not num.isdigit(): # probably has a deck in it, like 1a
        if num[0].isdigit() and num[1].isalpha() and num[2:].isdigit():
            deck, num = num[:2], num[2:]
    if prefix not in cards_num:
        await ctx.send(f"Prefix {prefix} is unrecognized")
        return
    values = cards_num[prefix]
    # this is a hack
    if deck and len(deck) == 2 and deck[1] in "ABCD":
        deck = deck[0] + deck[1].lower()
    if deck not in values:
        await ctx.send(f"Deck {deck} not recognized")
        return
    num = int(num)
    if num not in values[deck]:
        await ctx.send(f"Card {num} is unknown")
        return

    ctype, name = values[deck][num]
    if ctype == "P":
        ctype = "Player card"
    elif ctype == "N":
        ctype = "Nemesis card"
    elif ctype == "T":
        ctype = "Treasure card"
    else:
        ctype = "Unknown card type"

    await ctx.send(f"{name} ({ctype})")

# unique mechanics begin

@cmd
async def adjacent(ctx):
    await ctx.send("```\nSome spells may refer to adjacent breaches. Breaches are " +
    "adjacent to the one or two breaches directly next to them physically. As such, " +
    "I is adjacent to II, II is adjacent to I and III, III is adjacent to II and IV, " +
    "and IV is adjacent to III.\n```")

@cmd
async def aether(ctx):
    await ctx.send("```\nAether ($) can be gained during a player's turn by playing gems, " +
    "relics, by casting spells, or by using their or another player's ability, if " +
    "applicable. Aether may be gained even if it is not spent. Any aether gained on " +
    "a turn that is not spent is lost. Aether does not accumulate over turns, nor " +
    "can it be given to other players.\n```")

@cmd
async def ally(ctx):
    await ctx.send("```\nAn ally refers to any player other than you. If you are playing " +
    "true solo with one mage, you are your own ally.\n```")

@cmd
async def attach(ctx):
    await ctx.send("```\nSome relics allow you to Attach them to a breach. When you attach " +
    "a relic to a breach, place that relic underneath that breach token. You cannot " +
    "attach a relic to a breach that already has a relic attached to it. Attached relics " +
    "are not discarded at the end of the turn. If an attached relic is discarded, it is " +
    "placed in the discard pile of the player whose breach it was attached to. " +
    "If a breach with a relic attached to it is destroyed, the attached relic " +
    "is discarded. If an effect does not otherwise allow for it, you may not " +
    "choose to discard an attached relic (for example to make room for a " +
    "better-suited relic).\n```")

@cmd
async def attack(ctx):
    await ctx.send("```\nAttack cards are one of three types of nemesis cards. When " +
    "an attack card is drawn, their effect is resolved immediately and then discarded " +
    "in the nemesis discard pile.\n```")

@cmd
async def banish(ctx):
    await ctx.send("```\nWhen a card is banished, place it in the banished section of the game box. " +
    "Banished cards will not be used again during the current campaign or expedition. During an " +
    "expedition, if you lose a battle, you may reorganize your market using the most-recently " +
    "banished market cards.\n```")

@cmd
async def barracks(ctx):
    await ctx.send("```\nBetween games, the Barracks is where players store all of the content " +
    "they have access to for the current expedition. This includes player cards, player mats, " +
    "and treasures, including those not currently being used in any given battle.\n```")

@cmd
async def charge(ctx):
    await ctx.send("```\nEvery mage (with the exception of the starting mages in Legacy) " +
    "possesses an ability written on their mat, with space for 4 to 6 charge tokens under it. " +
    "During any player's main phase, that player may spend 2$ to gain a charge. " +
    "They cannot choose to pay aether to give charges to their allies. When a player " +
    "gains a charge, they take a charge token and place it on their player mat, beneath " +
    "the ability description. No player may have more charges than their ability " +
    "requires (4, 5, or 6). When a player has all of their charges, they may use their " +
    "ability at the appropriate time -- the phase in which it can be used is written " +
    "just below the ability name; this is typically during that same player's main phase. " +
    "When using their ability, the mage first loses all of their charges, and then " +
    "resolves the effect.\n```")

@cmd
async def curse(ctx):
    await ctx.send("```\nOutcasts introduces the Curse deck. This is a deck of cards that is " +
    "placed faceup near the nemesis deck. Cards in the nemesis deck may refer to cards in " +
    "the Curse deck. When a player is told to gain a card from the Curse deck, they search " +
    "for that specific card and then gain it. The Curse deck is not a supply pile. When " +
    "a card from the Curse deck is destroyed, do not return it to the Curse deck.\n```")

@cmd
async def degrade(ctx):
    await ctx.send("```\nWhen a nemesis card forces a player to degrade a card, that player must " +
    "first destroy a card that costs 2$ or more. Then, that player MAY gain a card of the same " +
    "type from any supply pile which costs less than the cost of the destroyed card and place it " +
    "into their hand. If a player cannot degrade a card, that player suffers 2 damage.\n```")

@cmd
async def destroy(ctx):
    await ctx.send("```\nCards which are destroyed are permanently removed from the game and are " +
    "not used or interacted with in any way once they are destroyed. Destroyed cards do not return " +
    f"to the supply. Unlike {config.prefix}banish, a destroyed card returns to its supply pile or " +
    "player hand or deck at the end of each game.\n```")

@cmd
async def dual(ctx):
    await ctx.send("```\nSome spells must be prepped to two adjacent breaches so that this touches both breaches. " +
    "This fully occupies both breaches. If one or both of these breaches have an additional effect, " +
    "such as additional damage of gaining life, then the spell prepped to these breaches gains the " +
    "additional effect(s) of all of the breaches it is prepped to.\n```")

@cmd
async def echo(ctx):
    await ctx.send("```\nWhen you cast a spell with Echo, resolve that Cast effect twice. " +
    "Any additional effects granted for casting the spell are added to both resolutions of the spell. " +
    "For example, you cast a spell with Echo that has a Cast effect of \"Deal 2 damage\". " +
    "That spell was prepped to a breach that has the following two effects: \"Deals +1 damage\" " +
    "and \"Gravehold gains 1 life\". You will resolve the following: \"Deal 3 damage. Gravehold gains 1 life\" " +
    "then \"Deal 3 damage. Gravehold gains 1 life\". Additionally, both instances of damage may be " +
    "directed to different targets.\n```")

@cmd
async def exhaust(ctx):
    await ctx.send("```\nIf a player's life is reduced to 0, that player is exhausted. " +
    "When a player becomes exhausted, resolve the following effects in order:\n" +
    "1 - Resolve the nemesis's Unleash effect twice. If a player becomes exhausted " +
    "during the nemesis Unleash effect, finish resolving the Unleash effect before that " +
    "player resolves the effects of becoming exhausted.\n" +
    "2 - The exhausted player destroys one of their breaches, discarding any spell " +
    "prepped in that breach, or relic attached to the breach. Destroyed breaches " +
    "can be returned to the box -- there is no way to regain a destroyed breach. " +
    "The remaining breaches stay in their current positions.\n" +
    "3 - The exhausted player discards all of their charge tokens.\n" +
    "The exhausted player continues to participate in the game as usual with the " +
    "following exceptions:\n" +
    "- Exhausted players cannot gain life.\n" +
    "- When an effect deals damage to the player with the lowest life, it always " +
    "deals that damage to the non-exhausted player with the lowest current life.\n" +
    "- When an exhausted player suffers damage, instead deal twice that amount of " +
    "damage to Gravehold. This includes excess damage when a player initially " +
    "becomes exhausted.\n" +
    "If all players become exhausted, the game ends immediately and the players " +
    "lose. If you are playing solo with one mage, you do not lose the game when you " +
    "are exhausted. Instead, you lose the game when Gravehold has 0 life.\n```")

@cmd
async def focus(ctx):
    await ctx.send("""```
* Focusing a breach *
- You can focus one of your closed breaches by paying the focus cost shown near \
the center of that breach token.
- When you focus a breach, rotate the breach token 90° clockwise. You may prep a \
spell to the focused breach this turn.
- Breaches may be focused any number of times per turn. Any number of breaches may \
be focused per turn. You may focus a breach without prepping a spell to it.
- A Breach that has been rotated to that the yellow quadrant is at the top can be \
opened by an effect that would otherwise focus this breach.

Some effects allow players to focus another mage's breach. \
You may not focus another mage's breach by spending aether.

* Opening a breach *
- You can open one of your closed breaches by paying the open cost currently indicated \
on the top of that breach token. The open cost decreases each time you focus the breach.
- When you open a breach, flip the breach to the opened side. Opened breaches stay \
opened for the rest of the game. A spell can be prepped to a breach on the \
turn that breach is opened and any subsequent turn.
```""")

@cmd
async def gem(ctx):
    await ctx.send("```\nGems are the primary way of gaining aether ($). Spending aether " +
    "is how you gain new cards, focus and open breaches, gain charges, and a few " +
    "other things. Each gem supply pile contains 7 cards.\n```")

@cmd
async def link(ctx):
    await ctx.send("```\nSome spells have the Link ability. You may prep two spells " +
    "with Link to the same breach. When you cast one of these spells, you do not " +
    "have to cast any other spell prepped in this breach.\n```")

@cmd
async def minion(ctx):
    await ctx.send("```\nMinions are one of three types of nemesis cards. When a " +
    "minion is drawn, it is put into play with their starting life. If a minion " +
    "has a number of shield tokens on its card, it gains that many shield tokens. " +
    "When a minion enters play, immediately resolve its \"IMMEDIATELY:\" effect, " +
    "if applicable. Do not resolve its \"PERSISTENT:\" effect this turn. When " +
    "the nemesis takes its turn, resolve each minion's \"PERSISTENT:\" effect " +
    "in order from oldest to newest. When the life of a minion reaches 0, it " +
    "is immediatedly discarded.\n```")

@cmd
async def _or(ctx):
    await ctx.send("```\nWhen a card gives two options separated by an \"OR\", you may " +
    "choose either option. If you cannot fully resolve one of the options, you must " +
    "choose an effect which you can fully resolve. If you cannot fully resolve either " +
    "effect, you must choose the one which you can resolve the most.\n```")

@cmd
async def order(ctx):
    await ctx.send("""**- Resolution order of spell-casting -**
```
Step 1: Move the spell to its new destination, as indicated by the following, \
with each step taking precedence over the ones below:

Once you find a matching condition, move to Step 2.

Here, "applicable" refers to effects written on the spell being cast, or on the \
spell which casts this spell, or on the gem or relic which casts this spell, \
or to a relic attached to a breach from where the spell is cast.

1.1   - The spell is destroyed and removed from play, if applicable.
1.2   - The spell remains in place, if applicable.
1.2.1 - Any spell that remains in place may be cast again as part of the same \
casting phase or another player's main phase.
1.3   - The spell moves to anywhere that is not a player's hand, discard, or the \
supply, if applicable.
1.4   - The spell moves to any player's hand, if applicable.
1.4.1 - For purposes of tracking and resolution of card effects, the spell entering \
the player's hand is considered a new spell.
1.5   - The spell returns to the supply, if applicable and possible.
1.6   - The spell is discarded to any player's discard pile, if applicable.
1.7   - The spell is discarded to the discard pile of the mage who had the spell prepped.
```""")

    await ctx.send("""```
Step 2: Resolve the cast effects of the spell, as indicated by the following, in order:

2.1   - Resolve the cast effects from top to bottom, in the written order. Win or \
loss conditions trigger as soon as their conditions are met, if relevant.
2.2   - If the spell natively deals damage (with an effect similar to "Deal 1 Damage"), all \
effects that add damage (with an effect similar to "On Cast: Deal +1 Damage") to \
the spell resolution are added. This includes bonus damage from an opened breach \
that the spell is prepped to, an attached relic to a breach this spell was prepped \
to, or a gem, relic, or spell which casts this spell, and includes breaches that \
were opened by the same spell, as long as the effect which opens the breach is \
listed before the damage effect on the card. This also includes damage that the \
spell itself gains for fulfilling certain conditions.
2.2.1 - Additional damage cannot stack multiple times per instance of damage. This \
means that damage gained from the spell itself does NOT gain bonus damage from a \
breach it is prepped to, a relic attached to a breach it is prepped to, or a gem, \
relic, or spell which casts this spell.
2.2.2 - If the spell deals multiple instances of damage, additional damage is applied \
separately for each instance of damage.
2.3   - If the spell does not natively deal damage (without an effect similar to "Deal \
1 Damage"), but is affected by one or multiple effects that add damage (as \
described above), calculate the total additional damage and deal it as one \
instance to a target.
2.4   - If the spell benefits from additional effects which do not deal damage, such as \
gaining aether or life, resolve those effects now.
2.5   - If the spell says to repeat the Cast effects, repeat Steps 2.2 to 2.4 once.
```""")

@cmd
async def power(ctx):
    await ctx.send("```\nPower cards are one of three types of nemesis cards. All " +
    "power cards have \"POWER: N\" on them. When a power card enters play, place " +
    "N power tokens on it. If it has an \"IMMEDIATELY:\" effect, resolve that now. " +
    "Unless discarded, power cards stay in play for N nemesis turns before resolving. " +
    "During the nemesis main phase, remove 1 power token from each power card in play, " +
    "from oldest to newest. When a power card has no power tokens left, resolve its " +
    "effect and then discard it. Only resolve a power card's \"POWER: N\" effect " +
    "when the last power token is removed. Some power cards also have a \"TO DISCARD:\" " +
    "text on them. This represents something that must be done (typically spending aether) " +
    "during any player's main phase to discard the power card. When resolving a " +
    "\"TO DISCARD:\" effect, the player must fully resolve the entire effect. " +
    "If a power card is discarded this way, its effect is not resolved.\n```")

@cmd
async def pulse(ctx):
    await ctx.send("```\nPulse tokens are used with certain player cards from Legacy, " +
    "starting in deck V and later, as well as some cards from the Buried Secrets " +
    "expansion. Cards may make a player gain or lose Pulse tokens as part of their " +
    "effects. Each player may not have more than 5 Pulse token at any time - any " +
    "Pulse tokens gained beyong 5 are lost. Pulse tokens are carried over from " +
    "turn to turn.\n```")

@cmd
async def relic(ctx):
    await ctx.send("```\nRelics have a wide variety of effects and are resolved " +
    "as soon as they are played. Each relic supply pile contains 5 cards.\n```")

@cmd
async def revealing(ctx):
    await ctx.send("```\nWhenever you reveal a card from the top of any deck, return it " +
    "to the top of that deck. If you reveal more than one card, return them in any " +
    "order you choose, unless the effect states otherwise.\n```")

@cmd
async def shield(ctx):
    await ctx.send("```\nShield tokens are used with certain minions from Legacy, " +
    "starting in deck III and later, as well as some minions from the Buried " +
    "Secrets expansion. The number of shield tokens a minion starts with is " +
    "indicated by a number on the left of the card. When a minion with at least " +
    "one shield token is dealt any amount of damage, remove a single shield " +
    "token from the minion, instead of removing any life tokens. Remove only one " +
    "shield token each time an instance of damage is dealt to the minion, " +
    "regardless of the amount of damage that would otherwise be dealt.\n```")

@cmd
async def silence(ctx):
    await ctx.send("```\nWhen a minion is silenced, place a silence token on it. " +
    "During the next nemesis turn, remove this token and ignore the persistent " +
    "effect of that minion. You may not silence a minion that has a silence " +
    "token on it. Silence does not prevent minion effects written on the card " +
    "that are not after the Persistent keyword.\n```")

@cmd
async def spell(ctx):
    await ctx.send("```\nSpells are the primary source of damage to the nemesis and its " +
    "minions. They must be prepped to a breach on a turn in order to be cast on a " +
    "later turn. Some spells have a \"While prepped\" effect, which can only be used " +
    "once per turn. Each spell supply pile contains 5 cards.\n```")

@cmd
async def tier(ctx):
    await ctx.send("```\nSome effects refer to the nemesis tier. The nemesis tier is the " +
    "highest number in the tier section (at the bottom right) of any nemesis card in the " +
    "nemesis discard pile or in play. This is typically the tier of the last card drawn " +
    "from the nemesis deck.\n```")

@cmd
async def todiscard(ctx):
    await ctx.send("```\nSome nemesis power cards have a \"TO DISCARD:\" effect on them. " +
    "During a player's main phase, that player may resolve the text following \"TO DISCARD:\" " +
    "to discard that power card from play. If a player discards a power card this way, " +
    "that power has no effect.\n```")

@cmd
async def unleash(ctx):
    await ctx.send("```\nEach nemesis has a unique Unleash ability written on their mat, " +
    "which may be modified if playing with the Increased Difficulty rules. When a " +
    "nemesis card uses the Unleash keyword, refer to the effect listed on the nemesis mat.\n```")

@cmd
async def wandering(ctx):
    await ctx.send("```\nSome minions have Wandering. This means that all damage dealt to them " +
    "by abilities and cards is reduced to 1. However, during any player's main phase, that " +
    "player may spend aether ($) to deal an equal amount of damage to minions of this type.\n```")

# unique mechanics end

@bot.command()
async def unique(ctx):
    await ctx.send("```The unique mechanics that I know about are as follow. " +
    f"You may prefix them with {config.prefix} to ask me about them.\n- " +
    "\n- ".join(cmds) + "\n```")

@bot.command()
async def reload(ctx):
    if await ctx.bot.is_owner(ctx.author):
        print("\nReloading content")
        load()
        await ctx.send("Reloaded data.")

@bot.command()
async def issues(ctx):
    aid = ctx.bot.get_user(author_id)
    mention = ""
    if aid is not None:
        mention = f"Report all other issues to {aid.mention}."
    content = """* Known issues and to-do list *

- Nemeses are not all in yet (they will be added gradually);
- Entwined Amethyst will send a similar message twice;
- Not all Legacy-specific content is implemented;
- !card doesn't return a block of text yet.

""" + mention

    await ctx.send(content)

@bot.command()
async def github(ctx):
    await ctx.send("https://github.com/Vgr255/Lexive")

@bot.command()
async def whoami(ctx):
    author = AUTHOR
    aid = ctx.bot.get_user(author_id)
    mention = ""
    if aid is not None:
        author += f" ({aid.mention})"
        mention = f" You may also ask or tell {aid.mention} directly."
    await ctx.send(f"I am Lexive v{VERSION} and I was created by {author}. " +
    "My code is available at <https://github.com/Vgr255/Lexive> where you can submit " +
    f"pull requests and bug reports.{mention}" +
    "\nI am a utility bot for all Aeon's End content. You can ask me about anything by doing " +
    f"`{config.prefix}<name>` in any channel on this server, or in private message with me. " +
    "I also know about some unique mechanics, and autocomplete is supported. Type " +
    f"`{config.prefix}issues` for a list of known issues, and `{config.prefix}unique` " +
    "for a list of unique mechanics I know about.")

@bot.command()
async def faq(ctx):
    await ctx.send("https://www.querki.net/u/aefaq/aeons-end-faq")

@bot.command()
async def outcasts(ctx):
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
Play replacement as a short term solution.

There have been a few typos identified in the rulebook:
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

print("Bot loaded. Starting")

bot.run(config.token)
