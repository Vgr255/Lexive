from typing import Optional, Tuple, Iterable, Callable, List

import discord
import csv
from discord.ext import commands

import config

VERSION = "0.1"
AUTHOR = "Anilyka Barry"
author_id = 320646088723791874

player_cards = {}
nemesis_cards = {}
player_mats = {}
nemesis_mats = {}

waves = {
    "Aeon's End": 1,
    "The Nameless": 1,
    "The Depths": 1,
    "War Eternal": 2,
    "The Void": 2,
    "The Outer Dark": 2,
    "Legacy": 3,
    "Buried Secrets": 3,
    "The New Age": 4,
    "The Ancients": 4,
    "Shattered Dreams": 4,
    "Into the Wild": 4,
    "Outcasts": 5,
    "The Southern Village": 5,
    "Return to Gravehold": 5,
    "Dice Tower": 2,
    "Legacy (Kickstarter Exclusive)": 3,
    "The New Age (Kickstarter Exclusive)": 4,
    "Outcasts (Kickstarter Exclusive)": 5,
}

ctypes = {
    "G": "Gem", "R": "Relic", "S": "Spell", "O": "Xaxos: Outcast Ability",
    "T1": "Level 1 Treasure", "T2": "Level 2 Treasure", "T3": "Level 3 Treasure",
    "P": "Power", "M": "Minion", "A": "Attack", "C": "Curse",
    # Nemesis-specific stuff
    "T": "Strike"
}

def load():
    player_cards.clear()
    with open("player_cards.csv", newline="") as player_file:
        content = csv.reader(player_file, dialect="excel", delimiter=";")
        for name, ctype, cost, code, special, text, flavour, starter, box, deck, start, end in content:
            if not name or name.startswith("#"):
                continue
            special = special.replace("#", "\n").replace("!", config.prefix)
            text = text.replace("#", "\n")
            flavour = flavour.replace("#", "\n")
            casefolded_name = name.lower().replace(" ", "").replace("'", "").replace(",", "")
            if casefolded_name in player_cards:
                raise ValueError(f"duplicate value {casefolded_name}")
            player_cards[casefolded_name] = {
                "name": name, "type": ctype, "cost": int(cost), "code": code,
                "special": special, "text": text, "flavour": flavour,
                "starter": starter, "box": box, "deck": deck, "start": int(start), "end": int(end)
            }

    print("Player cards loaded")

    nemesis_cards.clear()
    with open("nemesis_cards.csv", newline="") as nemesis_file:
        content = csv.reader(nemesis_file, dialect="excel", delimiter=";")
        for name, ctype, tokens_hp, shield, tier, cat, code, special, discard, immediate, effect, flavour, box, deck, num in content:
            if not name or name.startswith("#"):
                continue
            special = special.replace("#", "\n").replace("!", config.prefix)
            effect = effect.replace("#", "\n")
            flavour = flavour.replace("#", "\n")
            casefolded_name = name.lower().replace(" ", "").replace("'", "").replace(",", "").replace("-", "")
            if casefolded_name in nemesis_cards:
                raise ValueError(f"duplicate value {casefolded_name}")
            nemesis_cards[casefolded_name] = {
                "name": name, "type": ctype, "tokens_hp": (int(tokens_hp) if tokens_hp else 0),
                "shield": (int(shield) if shield else 0), "tier": int(tier), "category": cat,
                "code": code, "special": special, "discard": discard, "immediate": immediate,
                "effect": effect, "flavour": flavour, "box": box, "deck": deck, "number": int(num)
            }

    print("Nemesis cards loaded")

    nemesis_mats.clear()
    with open("nemesis_mats.csv", newline="") as nmats_file:
        content = csv.reader(nmats_file, dialect="excel", delimiter=";")
        for name, hp, diff, battle, unleash, setup, id_s, id_u, id_r, add_r, flavour, side, box, deck, cards in content:
            if not name or name.startswith("#"):
                continue
            setup = setup.replace("#", "\n")
            unleash = unleash.replace("#", "\n")
            add_r = add_r.replace("#", "\n")
            flavour = flavour.replace("#", "\n")
            side = side.replace("#", "\n")
            casefolded_name = name.lower().replace(" ", "").replace("'", "").replace(",", "")
            if casefolded_name in nemesis_mats:
                raise ValueError(f"duplicate value {casefolded_name}")
            nemesis_mats[casefolded_name] = {
                "name": name, "hp": int(hp), "difficulty": diff, "unleash": unleash,
                "setup": setup, "additional_rules": add_r, "flavour": flavour,
                "id_setup": id_s, "id_unleash": id_u, "id_rules": id_r,
                "side": side, "box": box, "battle": int(battle),
                "deck": deck, "cards": cards.split(",")
            }

    print("Nemesis mats loaded")

    assert (not player_cards.keys() & nemesis_cards.keys()), "player & nemesis cards"
    assert (not player_cards.keys() & player_mats.keys()), "player cards & mats"
    assert (not nemesis_cards.keys() & player_mats.keys()), "nemesis cards & player mats"
    assert (not nemesis_cards.keys() & nemesis_mats.keys()), "nemesis cards & mats"

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

            values, possible = get_card(content)
            if possible == 1:
                msgs = "\n".join(values).split(r"\NEWLINE/")
                for msg in msgs:
                    await message.channel.send(msg)
                return
            elif possible > 1:
                await message.channel.send(f"Ambiguous value. Possible matches: {', '.join(values)}")
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
    c = player_cards[name]
    values = ["```", f"{c['name']}", "", f"Type: {ctypes[c['type']]}", f"Cost: {c['cost']}", ""]
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
    values.append(f"From {c['box']} (Wave {waves[c['box']]})")

    if c['deck']:
        values.append(f"Deck {c['deck']}, {c['start']}-{c['end']}")
    else:
        values.append(f"{c['start']}-{c['end']}")

    values.append("```")

    return values

def nemesis_card(name: str) -> List[str]:
    c = nemesis_cards[name]
    values = ["```", f"{c['name']}", "", f"Type: {ctypes[c['type']]}"]
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

    values.append(f"From {c['box']} (Wave {waves[c['box']]})")
    if c['deck']:
        values.append(f"Deck {c['deck']}, Card {c['number']}")
    else:
        values.append(f"Card {c['number']}")

    values.append("```")

    return values

def player_mat(name: str) -> List[str]:
    return ["Not implemented"]

def nemesis_mat(name: str) -> List[str]:
    c = nemesis_mats[name]
    hp = c['hp']
    if not hp:
        hp = "*"
    values = ["```", f"{c['name']}", f"Health: {hp}", f"Difficulty rating: {c['difficulty']}", f"Battle: {c['battle']}", 
              "", f"SETUP: {c['setup']}", "", f"UNLEASH: {c['unleash']}", "", "* INCREASED DIFFICULTY *"]
    if c['id_setup']:
        values.append(f"SETUP: {c['id_setup']}")
    if c['id_unleash']:
        values.append(f"UNLEASH: {c['id_unleash']}")
    if c['id_rules']:
        values.append(f"RULES: {c['id_rules']}")

    values.extend(["", "* ADDITIONAL RULES *", f"{c['additional_rules']}", ""])

    values.extend([f"From {c['box']} (Wave {waves[c['box']]})"])

    if c['deck']:
        values.append(f"Cards used with this nemesis: Deck {c['deck']}, Cards {', '.join(c['cards'])}")
    else:
        values.append(f"Cards used with this nemesis: {', '.join(c['cards'])}")

    values.append(f"```\\NEWLINE/```\n{c['flavour']}```")

    if c['side']: # side mat
        values.append(r"\NEWLINE/```")
        values.append(f"{c['side']}```")

    return values

def get_card(name: str) -> Tuple[Optional[list], int]:
    mention = None # Optional
    if "<@!" in name and ">" in name: # mentioning someone else
        index = name.index("<@!")
        name, mention = name[:index], name[index:]
    for x in ("@", "#"): # ignore what's after
        if x in name:
            name = name[:name.index(x)]
    arg = name.lower().replace(" ", "").replace("'", "").replace(",", "").replace("-", "")
    matches = complete_match(arg, player_cards.keys() | nemesis_cards.keys() | player_mats.keys() | nemesis_mats.keys())
    if len(matches) == 1:
        if matches[0] in player_cards:
            values = player_card(matches[0])
        elif matches[0] in nemesis_cards:
            values = nemesis_card(matches[0])
        elif matches[0] in player_mats:
            values = player_mat(matches[0])
        elif matches[0] in nemesis_mats:
            values = nemesis_mat(matches[0])
        if mention is not None:
            values.insert(0, mention)
        return values, 1
    elif len(matches) > 1:
        values = []
        for x in matches:
            if x in player_cards:
                values.append(player_cards[x]["name"])
            elif x in nemesis_cards:
                values.append(nemesis_cards[x]["name"])
        return values, len(matches)
    return None, 0

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
    values, possible = get_card("".join(args))
    if possible == 1:
        to_send = "\n".join(values)
    elif not args:
        to_send = "No argument provided."
    elif possible > 1:
        to_send = f"Ambiguous value. Possible matches: {', '.join(values)}"
    else:
        to_send = f"No content found matching {' '.join(args)}"

    for msg in to_send.split(r"\NEWLINE/"):
      await ctx.send(msg)

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
    "For example, you cast a spell with Echo that has a Cast effect if \"Deal 2 damage\". " +
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
