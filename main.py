from typing import List

import discord
import os
from discord.ext import commands

import config
from code_parser import format
from cmds import cmds, get_card, complete_match, card_, content_dicts, command
from loader import (
    log,
    casefold,
    load,
    mechanics,
    player_cards,
    player_mats,
    ctypes,
    waves,
    nemesis_mats,
    nemesis_cards,
    cards_num,
    ability_types,
    breach_values,
    treasure_values,
)

VERSION = "0.3"
AUTHOR = "Anilyka Barry"
author_id = 320646088723791874

def sync(d):
    def wrapper(func):
        content_dicts.append((func, d))
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
            try:
                log("REQ:", content)
                value = content.split()
                matches = complete_match(value[0], cmds)
                if len(matches) == 1:
                    await cmds[matches[0]](ctx, *value[1:])
                    return

                values, asset = get_card(ctx.guild, content)
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
            except Exception as e:
                if hasattr(config, "server") and hasattr(config, "channel"):
                    await report(ctx, f"[Automatic reporting]\n{e}")
                raise

            await super().on_message(message)

bot = Lexive(command_prefix=config.prefix, owner_id=config.owner, case_insensitive=True, activity=activity, intents=discord.Intents.all())

@bot.command("report") # not a regular @command because we don't want autocomplete for this one
async def report_cmd(ctx, *args):
    if not hasattr(config, "server") or not hasattr(config, "channel"):
        ctx.send("Automatic issue reporting is not enabled")
        return
    await report(ctx, f"Reported by {ctx.message.author} in {ctx.message.guild} ({ctx.message.channel}):\n" + " ".join(args))
    await ctx.send("Issue reported, thank you!")

async def report(ctx, message):
    for guild in ctx.bot.guilds:
        if guild.id == config.server:
            chan = guild.get_channel(config.channel)
            await chan.send(message)

@command()
async def whoami(ctx, *args):
    author = AUTHOR
    aid = ctx.bot.get_user(author_id)
    mention = ""
    if aid is not None:
        author += f" ({aid.mention})"
        mention = f" You may also ask or tell {aid.mention} directly."
    await ctx.send(f"I am Lexive v{VERSION} and I was created by {author}. " +
    "My code is available at <https://github.com/Vgr255/Lexive> where you can submit " +
    f"pull requests and bug reports.{mention} You may use `{config.prefix}report <issue>` " +
    "to report an issue directly to the developers." +
    "\nI am a utility bot for all Aeon's End content. You can ask me about anything by doing " +
    f"`{config.prefix}<name>` in any channel on this server, or in private message with me. " +
    "I also know about some unique mechanics, and autocomplete is supported. Type " +
    f"`{config.prefix}issues` for a list of known issues, and `{config.prefix}unique` " +
    "for a list of unique mechanics I know about. You may search the content for a specific " +
    f"word or phrase using `{config.prefix}search <word>`. I also have a randomizer, which you " +
    f"can use with `{config.prefix}random`. See `{config.prefix}random --help` for help on " +
    "customizing the randomizer to your liking. You may see all of the commands I know of with " +
    f"`{config.prefix}commands`." + "\nArt by Amaple")

@sync(mechanics)
def unique_handler(guild, name: str) -> List[str]:
    # there is no support for guild-specific mechanic currently
    mechanic = mechanics[name][0]["content"]
    values = []
    if len(mechanic) == 1: # most common occurence
        values.append("```")
        values.append(mechanic[0].rstrip("\n").format(prefix=config.prefix))
        values.append("```")

    else: # manually go through
        class _card_internal:
            def __getitem__(self, item):
                return card_(item)
        def preformat(x: str) -> str:
            return x.format(prefix=config.prefix, newline="", card=_card_internal())

        is_title = False
        is_continue = False
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
            if current == "CONTINUE":
                is_continue = True
                continue
            if current == "NEXT":
                values.append(r"\NEWLINE/")
                continue
            if is_title:
                values.append(preformat(current))
                is_title = False
                continue
            if continuing:
                values.append(preformat(current))
                continue

            if values and not is_continue:
                values.append(r"\NEWLINE/")
            values.append("```")
            values.append(preformat(current))
            continuing = True
            is_continue = False

        if continuing:
            values.append("```")

    return values

@sync(player_cards)
def player_card(guild, name: str) -> List[str]:
    card = player_cards[name]
    values = []
    for c in card:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
        text_code, special_code = c['code']
        before, after = format(special_code, "PS", c['name'], c['type'])
        if values: # second pass-through or more, make it different messages
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], "", f"Type: {ctypes[c['type']]}", f"Cost: {c['cost']}", ""])
        if c['special'] or before:
            if before:
                values.append(f"** {before} **")
                if before != c['special']:
                    values.append("Autogenerated content above does not match printed content:")
                    values.append(f"** {c['special']} **")
            else:
                values.append(f"** {c['special']} **")
            values.append("")
        if text_code:
            content = format(text_code, "PE", c['name'], c['type'])[0]
            values.append(content)
            if content != c['text']:
                values.append("Autogenerated content above does not match printed content:")
                values.append(c['text'])
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
def nemesis_card(guild, name: str) -> List[str]:
    card = nemesis_cards[name]
    values = []
    for c in card:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
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
def player_mat(guild, name: str) -> List[str]:
    x: str
    mat = player_mats[name]
    values = []
    for c in mat:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
        if values:
            values.append(r"\NEWLINE/")
        values.extend(["```", c['name'], c['title'], f"Complexity rating: {c['rating']}", "", "Starting breach positions:", ""])

        bconv = ("I", "II", "III", "IV")
        for i in range(4):
            pos, special = c['breaches'][i]
            if pos == 9: # no breach
                values.append(f"(No breach {bconv[i]})")
                continue
            if special is None:
                special = f"Breach {bconv[i]}"
            values.append(f"{config.prefix}{special} - {breaches_orientation[pos]}")

        values.append("")
        wave = waves[c['box']][0]
        hand = []
        deck = []
        for orig, new in zip((c["hand"], c["deck"]), (hand, deck)):
            for x in orig:
                if x.count("-") == 2:
                    wave, x = x.split("-", 1)
                    x = x.replace("-", "")
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
def nemesis_mat(guild, name: str) -> List[str]:
    mat = nemesis_mats[name]
    values = []
    for c in mat:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
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
            elif x.isdigit(): # Cards that have nothing but a number.
                deck = None
                num = int(x)
            elif x[0].isdigit() and x[1].isalpha() and x[2:].isdigit(): # regular non-Legacy stuff, like "2a19", i.e. x[0] is "2", x[1] is "a" and the rest is "19"
                deck = x[:2]
                num = int(x[2:])
            # Legacy of Gravehold specific cases are handled below because LoG is the first wave where the deck name doesn't necessarily
            # start with a digit like 1c or 2a, so the above case handles some, but not most of those decks.
            elif x[0].isalpha():
                if x[1].isalpha():
                    if x[2].isalpha():
                        # 3 alphas means END deck
                        deck = x[:3]
                        num = int(x[3:])
                    elif x[2].isdigit():
                        # 2 alphas means most regular decks, e.g. BS
                        deck = x[:2]
                        num = int(x[2:])
                elif x[1].isdigit():
                    # 1 alpha means E, i.e. the event deck.
                    deck = x[0]
                    num = int(x[1:])
            else: # Legacy stuff
                for d in ("Ic", "II", "III", "IV", "V", "VI", "VII", "VIII", "END"):
                    if x.startswith(d) and x[len(d):].isdigit():
                        deck = d
                        num = int(x[len(d):])
                        break
                else:
                    raise ValueError(f"Unknown card {x} for {name}")

            ctype, card = box[deck][num]

            if ctype == "N":
                content = nemesis_cards[casefold(card)][0]
                cards.append((f"(Tier {content['tier']} {{0}}) {card}",
                ctypes[content['type']]))
            elif ctype == "P":
                content = player_cards[casefold(card)][0]
                cards.append((f"({content['cost']}-Cost {{0}}) {card}",
                ctypes[content['type']]))
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
def get_breach(guild, name: str) -> List[str]:
    b = breach_values[name]
    values = []
    for c in b:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
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
def get_treasure(guild, name: str) -> List[str]:
    t = treasure_values[name]
    values = []
    for c in t:
        if c['guild'] != 0 and guild != c['guild']:
            # this card can only be used in a specific guild, and this isn't it
            continue
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

if __name__ == "__main__":
    print("\nBot loaded. Starting")

    bot.run(config.token)
