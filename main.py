from typing import Optional, Tuple, Iterable, Callable, List
from collections import defaultdict

import discord
import csv
from discord.ext import commands

import config

# the following characters will be stripped from the csv names when stored
# and also ignored from messages (so that they are optional)
# this is a sequence of 1-length strings
_casefold_str = " ',:-()"
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
    "The Southern Village": ("SV", 5),
    "Return to Gravehold": ("RTG", 5),
    "Dice Tower": ("P", 2),
    "Legacy (Kickstarter Exclusive)": ("P", 3),
    "The New Age (Kickstarter Exclusive)": ("P", 4),
    "Outcasts (Kickstarter Exclusive)": ("P", 5),
}

ctypes = {
    "G": "Gem", "R": "Relic", "S": "Spell", "O": "Xaxos: Outcast Ability",
    "T1": "Level 1 Treasure", "T2": "Level 2 Treasure", "T3": "Level 3 Treasure",
    "P": "Power", "M": "Minion", "A": "Attack", "C": "Curse",
    # Nemesis-specific stuff
    "T": "Strike",
}

def casefold(x: str) -> str:
    x = x.lower()
    for c in _casefold_str:
        x = x.replace(c, "")
    return x

def expand(x: str, *, prefix=False) -> str:
    x = x.replace(_newline_str, "\n")
    if prefix:
        x = x.replace(_prefix_str, config.prefix)
    return x

def load():
    player_cards.clear()
    with open("player_cards.csv", newline="") as player_file:
        content = csv.reader(player_file, dialect="excel", delimiter=";")
        for name, ctype, cost, code, special, text, flavour, starter, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            player_cards[casefold(name)].append({
                "name": name, "type": ctype, "cost": int(cost), "code": code,
                "special": expand(special, prefix=True), "text": expand(text),
                "flavour": expand(flavour), "starter": starter, "box": box,
                "deck": deck, "start": int(start), "end": int(end)
            })

    print("Player cards loaded")

    nemesis_cards.clear()
    with open("nemesis_cards.csv", newline="") as nemesis_file:
        content = csv.reader(nemesis_file, dialect="excel", delimiter=";")
        for name, ctype, tokens_hp, shield, tier, cat, code, special, discard, immediate, effect, flavour, box, deck, num in content:
            if not name or name.startswith("#"):
                continue
            nemesis_cards[casefold(name)].append({
                "name": name, "type": ctype, "tokens_hp": (int(tokens_hp) if tokens_hp else 0),
                "shield": (int(shield) if shield else 0), "tier": int(tier), "category": cat,
                "code": code, "special": expand(special, prefix=True), "discard": expand(discard),
                "immediate": expand(immediate), "effect": expand(effect), "flavour": expand(flavour),
                "box": box, "deck": deck, "number": int(num)
            })

    print("Nemesis cards loaded")

    nemesis_mats.clear()
    with open("nemesis_mats.csv", newline="") as nmats_file:
        content = csv.reader(nmats_file, dialect="excel", delimiter=";")
        for name, hp, diff, battle, unleash, setup, id_s, id_u, id_r, add_r, flavour, side, box, deck, cards in content:
            if not name or name.startswith("#"):
                continue
            nemesis_mats[casefold(name)].append({
                "name": name, "hp": int(hp), "difficulty": diff, "unleash": expand(unleash),
                "setup": expand(setup), "additional_rules": expand(add_r), "flavour": expand(flavour),
                "id_setup": id_s, "id_unleash": id_u, "id_rules": id_r,
                "side": expand(side), "box": box, "battle": int(battle),
                "deck": deck, "cards": [int(x) for x in cards.split(",")]
            })

    print("Nemesis mats loaded")

    print("Loading complete")

print("Loading content")

load()

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
        if message.content.startswith(config.prefix):
            content = message.content.lstrip(config.prefix)
            if not content:
                return
            if content.lower() in cmds:
                await super().on_message(message)
                return # these commands supersede cards

            values = get_card(content)
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
    if func.__name__ in cmds:
        raise ValueError(f"duplicate function name {func.__name__}")
    cmds[func.__name__] = func
    return bot.command()(func)

def player_card(name: str) -> List[str]:
    card = player_cards[name]
    values = []
    for c in card:
        if values: # second pass-through or more, make it different messages
            values.append(r"\NEWLINE/")
        values.extend(["```", f"{c['name']}", "", f"Type: {ctypes[c['type']]}", f"Cost: {c['cost']}", ""])
        if c['special']:
            values.append(f"** {c['special']} **")
            values.append("")
        values.append(f"{c['text']}")
        values.append("")
        if c['flavour']:
            values.append(f"{c['flavour']}")
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

def nemesis_card(name: str) -> List[str]:
    card = nemesis_cards[name]
    values = []
    for c in card:
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", f"{c['name']}", "", f"Type: {ctypes[c['type']]}"])
        if c['category'] == "B":
            values.append(f"Basic Nemesis (Tier {c['tier']})")
        elif c['category'] == "U":
            values.append(f"Upgraded Basic Nemesis (Tier {c['tier']})")
        elif c['category'] == "E":
            values.append(f"Fully-Evolved Legacy Basic Nemesis suitable as Upgraded Basic (Tier {c['tier']})")
        else: # Nemesis-specific card
            values.append(f"Nemesis card for {c['category']} (Tier {c['tier']})")
        if c['type'] == "M":
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
            values.append(f"PERSISTENT: {c['effect']}")

        else:
            values.append(f"{c['effect']}")

        values.append("")

        if c['flavour']:
            values.append(f"{c['flavour']}\n")

        values.append(f"From {c['box']} (Wave {waves[c['box']][1]})")
        if c['deck']:
            values.append(f"Deck {c['deck']}, Card {c['number']}")
        else:
            values.append(f"Card {c['number']}")

        values.append("```")

    return values

def player_mat(name: str) -> List[str]:
    return ["Not implemented"]

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
                       "", f"SETUP: {c['setup']}", "", f"UNLEASH: {c['unleash']}", "", "* INCREASED DIFFICULTY *"])
        if c['id_setup']:
            values.append(f"SETUP: {c['id_setup']}")
        if c['id_unleash']:
            values.append(f"UNLEASH: {c['id_unleash']}")
        if c['id_rules']:
            values.append(f"RULES: {c['id_rules']}")

        values.extend(["", "* ADDITIONAL RULES *", f"{c['additional_rules']}", ""])

        values.extend([f"From {c['box']} (Wave {waves[c['box']][1]})"])

        if c['deck']:
            values.append(f"Cards used with this nemesis: Deck {c['deck']}, Cards {', '.join(str(x) for x in c['cards'])}")
        else:
            values.append(f"Cards used with this nemesis: {', '.join(c['cards'])}")

        values.append(f"```\\NEWLINE/```\n{c['flavour']}```")

        if c['side']: # side mat
            values.append(r"\NEWLINE/```")
            values.append(f"{c['side']}```")

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
    matches = complete_match(arg, player_cards.keys() | nemesis_cards.keys() | player_mats.keys() | nemesis_mats.keys())
    values = []
    if len(matches) > config.max_dupe:
        values.append(None)
        for x in matches:
            for d in (player_cards, nemesis_cards, player_mats, nemesis_mats):
                if x in d:
                    for n in d[x]:
                        if n["name"] not in values:
                            values.append(n["name"])

        return values
    for x in matches:
        if x in player_cards:
            values.append(player_card(x))
        if x in nemesis_cards:
            values.append(nemesis_card(x))
        if x in player_mats:
            values.append(player_mat(x))
        if x in nemesis_mats:
            values.append(nemesis_mat(x))

    if not values:
        return None

    ret = []
    for x in values:
        if ret:
            ret.append(r"\NEWLINE/")
        ret.extend(x)

    if mention is not None:
        ret.insert(0, mention)
    return ret

def complete_match(string: str, matches: Iterable) -> list:
    possible_matches = set()
    for possible in matches:
        if string == possible:
            return [string]
        if possible.startswith(string):
            possible_matches.add(possible)
    return sorted(possible_matches)

@cmd
async def info(ctx, *args):
    values = get_card("".join(args))
    if values and values[0] is None: # too many values
        to_send = f"Ambiguous value. Possible matches: {', '.join(values[1:])}"
    elif not args:
        to_send = "No argument provided."
    elif not values:
        to_send = f"No content found matching {' '.join(args)}"
    else:
        to_send = "\n".join(values)

    for msg in to_send.split(r"\NEWLINE/"):
        await ctx.send(msg)

#@cmd
async def search(ctx, *arg):
    to_search = " ".join(arg).lower()
    possible = set()
    for pcard in player_cards:
        pass # todo

@cmd
async def link(ctx):
    await ctx.send("```Two spells with Link may be prepped to the same breach.```")

@cmd
async def silence(ctx):
    await ctx.send("```When a minion is silenced, place a silence token on it. "+
    "During the next nemesis turn, remove this token and ignore the persistent "+
    "effect of that minion. You may not silence a minion that has a silence "+
    "token on it. Silence does not prevent minion effects written on the card "+
    "that are not after the Persistent keyword.```")

@cmd
async def echo(ctx):
    await ctx.send("```When you cast a spell with Echo, resolve that Cast effect twice. " +
    "Any additional effects granted for casting the spell are added to both resolutions of the spell. " +
    "For example, you cast a spell with Echo that has a Cast effect of \"Deal 2 damage\". " +
    "That spell was prepped to a breach that has the following two effects: \"Deals +1 damage\" " +
    "and \"Gravehold gains 1 life\". You will resolve the following: \"Deal 3 damage. Gravehold gains 1 life\" " +
    "then \"Deal 3 damage. Gravehold gains 1 life\"```")

@cmd
async def wandering(ctx):
    await ctx.send("```Some minions have Wandering. This means that all damage dealt to them " +
    "by abilities and cards is reduced to 1. However, during any player's main phase, that "+
    "player may spend aether ($) to deal an equal amount of damage to minions of this type.```")

@cmd
async def reload(ctx):
    if await ctx.bot.is_owner(ctx.author):
        print("\nReloading content")
        load()
        await ctx.send("Reloaded data.")

@cmd
async def whoami(ctx):
    author = AUTHOR
    aid = ctx.bot.get_user(author_id)
    mention = ""
    if aid is not None:
        author += f" ({aid.mention})"
        mention = f" You may also ask or tell {aid.mention} directly."
    await ctx.send(f"I am Lexive v{VERSION} and I was created by {author}. " +
    "My code is available at <https://github.com/Vgr255/Lexive> where you can submit pull requests " +
    f"and bug reports.{mention}" +
    "\nI am a utility bot for all Aeon's End content. You can ask me about any card by doing " +
    f"`{config.prefix}<card name>` in any channel on this server. I also know " +
    "about some unique mechanics, and autocomplete is supported for cards. "+
    "Legacy-specific content is not currently implemented and will arrive in v0.2")

print("Bot loaded. Starting")

bot.run(config.token)
