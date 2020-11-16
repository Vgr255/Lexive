from typing import Optional, Tuple, Iterable, Callable, List
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

def log(*x: Tuple[str], level:str="use") -> None:
    # probably gonna log to a file at some point
    print(*x)

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

    log("Player cards loaded", level="local")

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

    log("Nemesis cards loaded", level="local")

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

    log("Nemesis mats loaded", level="local")

    log("Loading complete", level="local")

log("Loading content", level="local")

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
    """Wrapper for unique argless commands."""
    if func.__name__ in cmds:
        raise ValueError(f"duplicate function name {func.__name__}")
    async def wrapper(ctx):
        log(f"CMD: {func.__name__}")
        return await func(ctx)

    cmds[func.__name__] = wrapper
    return bot.command(name=func.__name__)(wrapper)

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
        prefix = waves[c['box']][0]
        if c['deck']:
            prefix = f"{prefix}-{c['deck']}-"
        values.append(f"Card {prefix}{c['number']}")

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
            values.append(f"Cards used with this nemesis: {', '.join(str(x) for x in c['cards'])}")

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

@bot.command()
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
    "then \"Deal 3 damage. Gravehold gains 1 life\". Additionally, both instances of damage may be " +
    "directed to different targets.```")

@cmd
async def wandering(ctx):
    await ctx.send("```Some minions have Wandering. This means that all damage dealt to them " +
    "by abilities and cards is reduced to 1. However, during any player's main phase, that "+
    "player may spend aether ($) to deal an equal amount of damage to minions of this type.```")

@cmd
async def dual(ctx):
    await ctx.send("```This spell must be prepped to two adjacent breaches so that this touches both breaches. " +
    "This fully occupies both breaches. If one or both of these breaches have an additional effect, " +
    "such as additional damage of gaining life, then the spell prepped to these breaches gains the " +
    "additional effect(s) of all of the breaches it is prepped to.```")

@cmd
async def attach(ctx):
    await ctx.send("```Some relics allow you to Attach them to a breach. When you attach " +
    "a relic to a breach, place that relic underneath that breach token. You cannot " +
    "a relic to a breach that already has a relic attached to it. Attached relics are " +
    "not discarded at the end of the turn. If an attached relic is discarded, it is " +
    "placed in the discard pile of the player whose breach it was attached to. " +
    "If a breach with a relic attached to it is destroyed, the attached relic " +
    "is discarded. If an effect does not otherwise allow for it, you may not " +
    "choose to discard an attached relic (for example to make room for a " +
    "better-suited relic).```")

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
async def order(ctx):
    await ctx.send("""```
Resolution order of spell-casting

Step 1: Move the spell to its new destination, as indicated by the following, in order:

Here, "applicable" refers to effects written on the spell being cast, or on the \
spell which casts this spell, or on the gem or relic which casts this spell, \
or to a relic attached to a breach from where the spell is cast.

- The spell remains in place, if applicable. Move to Step 2.
  * Any spell that remains in place may be cast again as part of the same \
casting phase or another player's main phase.
- The spell moves to anywhere that is not a player's hand, discard, or the \
supply, if applicable. Move to Step 2.
- The spell moves to any player's hand, if applicable. Move to Step 2.
  * For purposes of tracking and resolution of card effects, the spell entering \
the player's hand is considered a new spell.
- The spell returns to the supply, if applicable and possible. Move to Step 2.
- The spell is discarded to any player's discard pile, if applicable. Move to Step 2.
- The spell is discarded to the discard pile of the mage who had the spell prepped.
```""")

    await ctx.send("""```
Step 2: Resolve the cast effects of the spell, as indicated by the following, in order:

- Resolve the cast effects from top to bottom, in the written order.
- If the spell natively deals damage (with an effect similar to "Deal 1 Damage"), all \
effects that add damage (with an effect similar to "On Cast: Deal +1 Damage") to \
the spell resolution are added. This includes bonus damage from an opened breach \
that the spell is prepped to, an attached relic to a breach this spell was prepped \
to, or a gem, relic, or spell which casts this spell, and includes breaches that \
were opened by the same spell, as long as the effect which opens the breach is \
listed before the damage effect on the card. This also includes damage that the \
spell itself gains for fulfilling certain conditions.
  * Additional damage cannot stack multiple times per instance of damage. This \
means that damage gained from the spell itself does NOT gain bonus damage from a \
breach it is prepped to, a relic attached to a breach it is prepped to, or a gem, \
relic, or spell which casts this spell.
- If the spell deals multiple instances of damage, additional damage is applied \
separately for each instance of damage.
- If the spell says to repeat the Cast effects, return to the beginning of Step 2.
- If the spell does not natively deal damage (without an effect similar to "Deal \
1 Damage"), but is affected by one or multiple effects that add damage (as \
described above), calculate the total additional damage and deal it as one \
instance to a target.
- If the spell benefits from additional effects which do not deal damage, such as \
gaining aether or life, resolve those effects now.
```""")

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
    content = """* Known issues *

- Starter cards do not currently have their proper card number;
- Treasures are not implemented yet;
- Nemeses and mages are not all in yet (they will be added gradually);
- Some cards with identical names will send a similar message multiple times;
- Legacy specific content is not currently implemented;
- Upgraded player cards (Lost, Mazra, Razra) are not currently implemented.

""" + mention

    await ctx.send(content)

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

@bot.command() # for the meme
async def ae6(ctx):
    await ctx.send("Someday, hopefully.")

print("Bot loaded. Starting")

bot.run(config.token)
