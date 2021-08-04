from typing import Optional, Tuple, Iterable, List, Dict
from collections import defaultdict

import argparse
import discord
import random as _random
import csv
import os
from discord.ext import commands

import config
from code_parser import parse, as_text, as_special

# the following characters will be stripped from the csv names when stored
# and also ignored from messages (so that they are optional)
# this is a sequence of 1-length strings
_casefold_str = " ',:-!()[]"
# this character will be replaced by a newline when sent to the discord
# this is a str
_newline_str = "#"
# this character will be replaced by the prefix from the config
# this is a str
_prefix_str = "!"

VERSION = "0.3"
AUTHOR = "Anilyka Barry"
author_id = 320646088723791874

assets = {}
mechanics = {}
waves = {}
cards_num = {} # type: Dict[str, Dict[int, Tuple[str, str]]]
ctypes = {}
ability_types = {}
player_cards = defaultdict(list)
nemesis_cards = defaultdict(list)
player_mats = defaultdict(list)
nemesis_mats = defaultdict(list)
breach_values = defaultdict(list)
treasure_values = defaultdict(list)

content_dicts = []
cmds = {}

def sync(d):
    def wrapper(func):
        content_dicts.append((func, d))
        return func
    return wrapper

def command(name=None):
    def wrapper(func):
        nonlocal name
        if name is None:
            name = func.__name__
        cmds[name] = func
        return func
    return wrapper

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

class _open:
    """Wrapper class to get around weird encoding shenanigans."""

    def __init__(self, filename):
        self.filename = filename
        self.file = None

    def __enter__(self):
        self.file = open(self.filename, "rb")
        return self

    def __exit__(self, exc, exc_type, exc_value):
        self.file.close()

    def __iter__(self):
        return self

    def __next__(self):
        value = self.file.readline()
        if not value:
            raise StopIteration
        if value.startswith(b"\xef\xbb\xbf"):
            value = value.lstrip(b"\xef\xbb\xbf")
        value = value.rstrip()
        return value.decode("utf-8")

def log(*x: str, level:str="use", **kwargs) -> None:
    # probably gonna log to a file at some point
    print(*x, **kwargs)

def casefold(x: str) -> str:
    x = x.lower()
    for c in _casefold_str:
        x = x.replace(c, "")
    return x

def expand(x: str, *, flavour=False, prefix=False) -> str:
    if x.startswith(">>>"):
        x = x[3:]
    replace_by = "\n"
    if flavour: # make newlines twice as big
        replace_by = "\n\n"
    x = x.replace(_newline_str, replace_by)
    if prefix:
        x = x.replace(_prefix_str, config.prefix)
    return x

def load():
    assets.clear()
    for filename in os.listdir("assets"):
        assets[casefold(filename.split(".")[0])] = filename

    log("Assets indexed", level="local")

    mechanics.clear()
    for filename in os.listdir("unique"):
        if not filename.endswith(".lexive"):
            continue
        with open(os.path.join("unique", filename), "rt") as unique_file:
            mechanics[filename[:-7]] = unique_file.readlines()

    log("Mechanics loaded", level="local")

    waves.clear()
    cards_num.clear()
    with _open("boxes.csv") as boxes_file:
        content = csv.reader(boxes_file, dialect="excel")
        for prefix, name, wave in content:
            if not name or prefix.startswith("#"):
                continue
            if not prefix:
                prefix = None
            wave = int(wave)
            waves[name] = (prefix, wave)
            cards_num[prefix] = {}

    log("Waves loaded", level="local")

    ctypes.clear()
    with _open("card_types.csv") as types_file:
        content = csv.reader(types_file, dialect="excel")
        for prefix, name in content:
            if not prefix or prefix.startswith("#"):
                continue
            ctypes[prefix] = name

    log("Prefixes loaded", level="local")

    ability_types.clear()
    with _open("mage_ability_types.csv") as ability_file:
        content = csv.reader(ability_file, dialect="excel")
        for shorthand, long in content:
            if not shorthand or shorthand.startswith("#"):
                continue
            ability_types[shorthand] = long

    log("Ability types loaded", level="local")

    player_cards.clear()
    with _open("player_cards.csv") as player_file:
        content = csv.reader(player_file, dialect="excel")
        for name, ctype, cost, code, special, text, flavour, starter, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            start = int(start)
            end = int(end)
            player_cards[casefold(name)].append({
                "name": name, "type": ctype, "cost": int(cost), "code": parse(code),
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
    with _open("nemesis_cards.csv") as nemesis_file:
        content = csv.reader(nemesis_file, dialect="excel")
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
                "code": parse(code), "special": expand(special, prefix=True), "discard": expand(discard),
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
    with _open("player_mats.csv") as pmats_file:
        content = csv.reader(pmats_file, dialect="excel")
        for name, title, rating, aname, charges, atype, code, ability, special, breaches, hand, deck, b1, b2, b3, b4, flavour, box in content:
            if not name or name.startswith("#"):
                continue
            if not charges:
                charges = 0
            if not rating:
                rating = 0
            adict = {"name": aname, "charges": int(charges), "type": atype, "effect": expand(ability), "code": parse(code)}
            blist = []
            for pos, breach in zip(breaches.split(","), (b1, b2, b3, b4)):
                pos = int(pos) if pos else 0
                if not breach: # just a regular breach
                    breach = None
                blist.append((pos, breach))
            player_mats[casefold(name)].append({
                "name": name, "title": title, "rating": int(rating), "ability": adict, "breaches": blist,
                "hand": hand.split(","), "deck": deck.split(","), "flavour": expand(flavour),
                "special": expand(special, prefix=True), "box": box
            })

    log("Player mats loaded", level="local")

    nemesis_mats.clear()
    with _open("nemesis_mats.csv") as nmats_file:
        content = csv.reader(nmats_file, dialect="excel")
        for name, hp, diff, battle, code, extra, unleash, setup, id_s, id_u, id_r, add_r, flavour, side, box, cards in content:
            if not name or name.startswith("#"):
                continue
            nemesis_mats[casefold(name)].append({
                "name": name, "hp": int(hp), "difficulty": int(diff), "unleash": expand(unleash),
                "setup": expand(setup), "additional_rules": expand(add_r), "flavour": expand(flavour),
                "code": parse(code), "extra": expand(extra), "id_setup": id_s, "id_unleash": id_u,
                "id_rules": id_r, "side": expand(side), "box": box, "battle": int(battle),
                "cards": cards.split(",")
            })

    log("Nemesis mats loaded", level="local")

    breach_values.clear()
    with _open("breaches.csv") as breach_file:
        content = csv.reader(breach_file, dialect="excel")
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
    with _open("treasures.csv") as treasure_file:
        content = csv.reader(treasure_file, dialect="excel")
        for name, ttype, code, effect, flavour, box, deck, number in content:
            if not name or name.startswith("#"):
                continue
            treasure_values[casefold(name)].append({
                "name": name, "type": ttype, "code": parse(code), "effect": expand(effect),
                "flavour": expand(flavour), "box": box, "deck": deck, "number": int(number)
            })
            wave = waves[box][0]
            pvalue = "T"
            if ttype == "O":
                pvalue = "O"
            if not deck:
                deck = None
            if deck not in cards_num[wave]:
                cards_num[wave][deck] = {}
            cards_num[wave][deck][int(number)] = (pvalue, name)

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
    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        if message.content.startswith(config.prefix) or isinstance(message.channel, discord.DMChannel):
            content = message.content.lstrip(config.prefix)
            if not content:
                return

            ctx = await self.get_context(message)
            value = content.split()
            matches = complete_match(value[0], cmds)
            if len(matches) == 1:
                await cmds[matches[0]](ctx, *value[1:])
                return

            values, asset = get_card(content)
            log("REQ:", content)
            if values and values[0] is None: # too many values
                await ctx.send(f"Ambiguous value. Possible matches: {', '.join(values[1:])}")
                return
            elif values:
                msgs = "\n".join(values).split(r"\NEWLINE/")
                for msg in msgs:
                    await ctx.send(msg)
                for ass in asset:
                    with open(os.path.join("assets", ass), mode="rb") as a:
                        await ctx.send(file=discord.File(a))
                return

        await super().on_message(message)

bot = Lexive(command_prefix=config.prefix, owner_id=config.owner, case_insensitive=True, activity=activity)

@sync(mechanics)
def unique_handler(name: str) -> List[str]:
    mechanic = mechanics[name]
    values = []
    if len(mechanic) == 1: # most common occurence
        values.append("```")
        values.append(mechanic[0].rstrip("\n").format(prefix=config.prefix))
        values.append("```")

    else: # manually go through
        class _card_internal:
            def __getitem__(self, item):
                return _card(item)
        def preformat(x: str) -> str:
            return x.format(prefix=config.prefix, newline="", card=_card_internal())

        is_title = False
        continuing = False
        for current in mechanic:
            current = current.rstrip("\n")
            if not current:
                if continuing:
                    values.append("```")
                    continuing = False
                continue
            if current == "TITLE":
                is_title = True
                continue
            if is_title:
                values.append(preformat(current))
                is_title = False
                continue
            if continuing:
                values.append(preformat(current))
                continue

            if values:
                values.append(r"\NEWLINE/")
            values.append("```")
            values.append(preformat(current))
            continuing = True

        if continuing:
            values.append("```")

    return values

@sync(player_cards)
def player_card(name: str) -> List[str]:
    card = player_cards[name]
    values = []
    for c in card:
        text_code, special_code = c['code']
        before, after = as_special(special_code)
        if values: # second pass-through or more, make it different messages
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], "", f"Type: {ctypes[c['type']]}", f"Cost: {c['cost']}", ""])
        if c['special'] or before:
            if before:
                values.append(f"** {before} **")
            else:
                values.append(f"** {c['special']} **")
            values.append("")
        if text_code:
            values.append(as_text(text_code).format(name=c['name']))
        else:
            values.append(c['text'])
        values.append("")
        if after:
            values.append(after)
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
        if c['type'].startswith("M"):
            hp = c['tokens_hp']
            if not hp:
                hp = "*"
            values.append(f"Health: {hp}")
            if c['shield']:
                shields = c['shield']
                if shields == -1:
                    shields = "*"
                values.append(f"Shield tokens: {shields}")

        values.append("")

        if c['special']:
            values.append(f"** {c['special']} **\n")

        if c['immediate']:
            values.append(f"IMMEDIATELY: {c['immediate']}\n")

        if c['type'] == "P":
            if c['discard']:
                values.append(f"TO DISCARD: {c['discard']}\n")
            values.append(f"POWER {c['tokens_hp']}: {c['effect']}")

        elif c['type'] == "MA":
            values.append(f"BLOOD MAGIC: {c['effect']}")

        elif c['type'].startswith("M"):
            if c['effect']: # not all minions have a Persistent effect
                values.append(f"PERSISTENT: {c['effect']}")

        else:
            values.append(c['effect'])

        if c['effect']:
            values.append("")

        if c['flavour']:
            values.append(f"{c['flavour']}\n")

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        prefix = waves[c['box']][0]
        if not prefix:
            if c['deck']:
                prefix = f"{c['deck']}-"
            else:
                prefix = ""
        elif c['deck']:
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
                       "", "SETUP:", c['setup'], "", "UNLEASH:", c['unleash'], ""])

        if c['id_setup'] or c['id_unleash'] or c['id_rules']:
            values.append("* INCREASED DIFFICULTY *")
            if c['id_setup']:
                values.append(f"SETUP: {c['id_setup']}")
            if c['id_unleash']:
                values.append(f"UNLEASH: {c['id_unleash']}")
            if c['id_rules']:
                values.append(f"RULES: {c['id_rules']}")
            values.append("")

        values.extend(["* ADDITIONAL RULES *", f"{c['additional_rules']}", ""])

        if c['extra']:
            values.extend(["Additional expedition rules:", c['extra'], ""])

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        values.append("")

        largest = 0
        box = cards_num[waves[c['box']][0]]

        cards = []
        for x in c["cards"]:
            if x.isdigit() and x[0] in box:
                deck = x[0]
                num = int(x[1:])
            elif x.isdigit():
                deck = None
                num = int(x)
            elif x[0].isdigit() and x[1].isalpha() and x[2:].isdigit(): # regular non-Legacy stuff
                deck = x[:2]
                num = int(x[2:])
            else: # Legacy stuff
                for d in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "END"):
                    if x.upper().startswith(d) and x[len(d):].isdigit():
                        deck = d
                        num = int(x[len(d):])
                        break
                else:
                    raise ValueError(f"Unknown card {x} for {name}")

            ctype, card = box[deck][num]

            if ctype == "N":
                content = nemesis_cards[casefold(card)][0]
                cards.append((f"(Tier {content['tier']} {{0}}) {card}", ctypes[content['type']]))
            elif ctype == "P":
                content = player_cards[casefold(card)][0]
                cards.append((f"({content['cost']}-Cost {{0}}) {card}", ctypes[content['type']]))
            largest = max(largest, len(ctypes[content["type"]]))

        cards = [text.format(t.ljust(largest)) for text, t in cards]

        values.append(r"```\NEWLINE/```")
        values.append("Cards used with this nemesis:\n")
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

@command()
async def random(ctx, *args):
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
        values = _random.choice(list(nemesis_mats.values()))
        value = _random.choice(values)
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
        values = _random.choice(list(player_mats.values()))
        value = _random.choice(values)
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
        for value in _random.choice(list(player_cards.values())):
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

def get_card(name: str) -> Tuple[Optional[List[str]], Optional[List[str]]]:
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
                values.append(func(x))
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

def complete_match(string: str, matches: Iterable) -> list:
    possible_matches = set()
    for possible in matches:
        if string == possible:
            return [string]
        if possible.startswith(string):
            possible_matches.add(possible)
    return sorted(possible_matches)

@command()
async def info(ctx, *args):
    arg = "".join(args)
    if not arg:
        await ctx.send("No argument provided.")
        return
    if not arg.isalpha() and arg.isalnum(): # has numbers and no special characters
        await ctx.send(f"Number detected. Did you want `{config.prefix}card` instead?")
        return
    values, asset = get_card(arg)
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
async def card(ctx, *args):
    await ctx.send(_card(casefold("".join(args)).upper(), detailed=True))

def _card(arg: str, *, detailed=False) -> str:
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
async def box(ctx, *args):
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
    c = {"P": player_cards, "N": nemesis_cards, "T": treasure_values}

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
                if count >= 1800:
                    result.append("```\\NEWLINE/```")
                    count = 3
                result.append(f"- {card} ({ctypes[d['type']]}) ({num})")
                count += len(result[-1])

    result.append("```")

    for line in "\n".join(result).split("\\NEWLINE/"):
        await ctx.send(line)

@command()
async def unique(ctx):
    await ctx.send("```\nThe unique mechanics that I know about are as follow. " +
    f"You may prefix them with {config.prefix} to ask me about them.\n- " +
    "\n- ".join(mechanics) + "\n```")

@command()
async def reload(ctx):
    if await ctx.bot.is_owner(ctx.author):
        print("\nReloading content")
        load()
        await ctx.send("Reloaded data.")

@command()
async def issues(ctx):
    aid = ctx.bot.get_user(author_id)
    mention = ""
    if aid is not None:
        mention = f"Report all other issues to {aid.mention}."
    content = """* Known issues and to-do list *

- Entwined Amethyst will send a similar message twice;
- Not all Legacy-specific content is implemented;
- !card doesn't return a block of text yet.

""" + mention

    await ctx.send(content)

@command()
async def github(ctx):
    await ctx.send("https://github.com/Vgr255/Lexive")

@command("eval")
async def eval_(ctx, *args):
    if await ctx.bot.is_owner(ctx.author):
        await ctx.send(eval(" ".join(args)))

@command()
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
    "for a list of unique mechanics I know about.\nArt by Amaple")

@command()
async def faq(ctx):
    await ctx.send("https://www.querki.net/u/aefaq/aeons-end-faq")

@command()
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

print("Bot loaded. Starting")

bot.run(config.token)
