from typing import Dict, Tuple
from collections import defaultdict
import csv
import os

from code_parser import parse

import config

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

assets = {}
waves = {}
cards_num = {} # type: Dict[str, Dict[int, Tuple[str, str]]]
ctypes = {}
ability_types = {}
mechanics = defaultdict(list)
player_cards = defaultdict(list)
nemesis_cards = defaultdict(list)
player_mats = defaultdict(list)
nemesis_mats = defaultdict(list)
breach_values = defaultdict(list)
treasure_values = defaultdict(list)

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

def load_boxes(relpath):
    file = "boxes.csv"
    if relpath is None:
        waves.clear()
        cards_num.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as boxes_file:
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

def load_ctypes(relpath):
    file = "card_types.csv"
    if relpath is None:
        ctypes.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as types_file:
        content = csv.reader(types_file, dialect="excel")
        for prefix, name in content:
            if not prefix or prefix.startswith("#"):
                continue
            ctypes[prefix] = name

    log("Prefixes loaded", level="local")

def load_atypes(relpath):
    file = "mage_ability_types.csv"
    if relpath is None:
        ability_types.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as ability_file:
        content = csv.reader(ability_file, dialect="excel")
        for shorthand, long in content:
            if not shorthand or shorthand.startswith("#"):
                continue
            ability_types[shorthand] = long

    log("Ability types loaded", level="local")

def load_meta(relpath=None):
    if relpath is None:
        log("Loading global metadata:", level="local")
        assets.clear()
        for filename in os.listdir("assets"):
            assets[casefold(filename.split(".")[0])] = filename

        log("Assets indexed", level="local")
    else:
        log(f"\nLoading guild-specific metadata for {relpath}:", level="local")

    load_boxes(relpath)
    load_ctypes(relpath)
    load_atypes(relpath)

def load_unique():
    mechanics.clear()
    for filename in os.listdir("unique"):
        if not filename.endswith(".lexive"):
            continue
        with open(os.path.join("unique", filename), "rt") as unique_file:
            mechanics[filename[:-7]].append({"name": filename[:-7], "content": unique_file.readlines()})

    log("Mechanics loaded", level="local")

def load_pcards(relpath=None):
    file = "player_cards.csv"
    if relpath is None:
        player_cards.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as player_file:
        content = csv.reader(player_file, dialect="excel")
        for name, ctype, cost, code, special, text, flavour, starter, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            start = int(start)
            end = int(end)
            player_cards[casefold(name)].append({
                "name": name, "type": ctype, "cost": int(cost), "code": parse(code, "P"),
                "special": expand(special, prefix=True), "text": expand(text),
                "flavour": expand(flavour), "starter": starter, "box": box,
                "deck": deck, "start": start, "end": end, "guild": int(relpath) if relpath else 0
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

def load_ncards(relpath=None):
    file = "nemesis_cards.csv"
    if relpath is None:
        nemesis_cards.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as nemesis_file:
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
                "code": parse(code, "N"), "special": expand(special, prefix=True), "discard": expand(discard),
                "immediate": expand(immediate), "effect": expand(effect), "flavour": expand(flavour),
                "box": box, "deck": deck, "start": start, "end": end, "guild": int(relpath) if relpath else 0
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

def load_pmats(relpath=None):
    file = "player_mats.csv"
    if relpath is None:
        player_mats.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as pmats_file:
        content = csv.reader(pmats_file, dialect="excel")
        for name, title, rating, aname, charges, atype, code, ability, special, breaches, hand, deck, b1, b2, b3, b4, flavour, box in content:
            if not name or name.startswith("#"):
                continue
            if not charges:
                charges = 0
            if not rating:
                rating = 0
            adict = {"name": aname, "charges": int(charges), "type": atype, "effect": expand(ability), "code": parse(code, "A")}
            blist = []
            for pos, breach in zip(breaches.split(","), (b1, b2, b3, b4)):
                pos = int(pos) if pos else 0
                if not breach: # just a regular breach
                    breach = None
                blist.append((pos, breach))
            player_mats[casefold(name)].append({
                "name": name, "title": title, "rating": int(rating), "ability": adict, "breaches": blist,
                "hand": hand.split(","), "deck": deck.split(","), "flavour": expand(flavour),
                "special": expand(special, prefix=True), "box": box, "guild": int(relpath) if relpath else 0
            })

    log("Player mats loaded", level="local")

def load_nmats(relpath=None):
    file = "nemesis_mats.csv"
    if relpath is None:
        nemesis_mats.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as nmats_file:
        content = csv.reader(nmats_file, dialect="excel")
        for name, hp, diff, battle, code, extra, unleash, setup, id_s, id_u, id_r, add_r, flavour, side, box, cards in content:
            if not name or name.startswith("#"):
                continue
            nemesis_mats[casefold(name)].append({
                "name": name, "hp": int(hp), "difficulty": int(diff), "unleash": expand(unleash),
                "setup": expand(setup), "additional_rules": expand(add_r), "flavour": expand(flavour),
                "code": parse(code, "M"), "extra": expand(extra), "id_setup": id_s, "id_unleash": id_u,
                "id_rules": id_r, "side": expand(side), "box": box, "battle": int(battle),
                "cards": cards.split(","), "guild": int(relpath) if relpath else 0
            })

    log("Nemesis mats loaded", level="local")

def load_breaches(relpath=None):
    file = "breaches.csv"
    if relpath is None:
        breach_values.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as breach_file:
        content = csv.reader(breach_file, dialect="excel")
        for name, pos, focus, left, down, right, effect, mage in content:
            if not name or name.startswith("#"):
                continue
            breach_values[casefold(name)].append({
                "name": name, "position": int(pos), "focus": int(focus),
                "left": int(left), "down": int(down), "right": int(right),
                "effect": expand(effect), "mage": mage, "guild": int(relpath) if relpath else 0
            })

    log("Breaches loaded", level="local")

def load_treasures(relpath=None):
    file = "treasures.csv"
    if relpath is None:
        treasure_values.clear()
    else:
        file = os.path.join("guilds", relpath, file)
        if not os.path.isfile(file):
            return
    with _open(file) as treasure_file:
        content = csv.reader(treasure_file, dialect="excel")
        for name, ttype, code, effect, flavour, box, deck, number in content:
            if not name or name.startswith("#"):
                continue
            treasure_values[casefold(name)].append({
                "name": name, "type": ttype, "code": parse(code, "T"), "effect": expand(effect),
                "flavour": expand(flavour), "box": box, "deck": deck, "number": int(number),
                "guild": int(relpath) if relpath else 0
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

def load():
    load_meta()
    load_unique()
    load_pcards()
    load_ncards()
    load_pmats()
    load_nmats()
    load_breaches()
    load_treasures()

    for folder in os.listdir("guilds"):
        if folder.isdigit():
            load_meta(folder)
            load_pcards(folder)
            load_ncards(folder)
            load_pmats(folder)
            load_nmats(folder)
            load_breaches(folder)
            load_treasures(folder)
