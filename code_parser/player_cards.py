from typing import List, Dict, Tuple

import config

_parse_list = List[Tuple[str, str]]
_extra_dict = Dict[str, str]

def _int_internal(x: str, word):
    # FIXME: plural3 messes with "any X may"
    lower = 0
    upper = 0
    if "-" in x:
        begin, _, end = x.partition("-")
        if begin.isdigit() and end.isdigit():
            lower = int(begin)
            upper = int(end)
        else:
            return f"ERROR: Malformed range {x}"
    else:
        lower = upper = int(x)
    if lower == upper:
        if lower == 1:
            return f"{word}{{plural3}} {{a_card}} {{place}}"
        return f"{word}{{plural3}} {lower} cards {{place}}"

    if lower == 0:
        return f"{word}{{plural3}} up to {upper} cards {{place}}"
    return f"{word}{{plural3}} from {lower} to {upper} cards {{place}}"

def parse_player_card(code: str) -> Tuple[_parse_list, _extra_dict]:
    values = []
    extra = {}
    sub, *rest = code.split(";")
    if sub:
        for segment in sub.split("/"):
            d = []
            for part in segment.split(","):
                key, _, value = part.partition("=")
                d.append((key, value))
            values.append(d)
    for x in rest:
        key, _, value = x.partition("=")
        extra[key] = value
    return values, extra

def format_player_card_effect(code: _parse_list) -> str:
    """Return a formatted text of the card effect."""
    text = []
    for d in code:
        if text:
            text.append("OR")
        form: List[str] = []
        for action, value in d:
            to_append = False
            if len(action) > 1 and action.startswith("&"):
                to_append = True
                action = action[1:]
            if action == "A":
                add = ""
                if value[0] == "+":
                    add = "an additional "
                    value = value[1:]
                form.append(f"gain {add}{value}$")
            elif action == "C":
                if value == "1":
                    form.append("gain a charge")
                elif value.isdigit():
                    form.append(f"gain {value} charges")
                elif value == "-1":
                    form.append("lose a charge")
                else:
                    form.append(f"lose {value[1:]} charges")
            elif action == "D":
                add = ""
                if value[0] == "+":
                    add = " additional"
                    value = value[1:]
                if form: # might be part of something like "do X, if you do, deal Y damage"
                    form.append(f"deal {value}{add} damage")
                else: # but if it's not, we can assume it has a Cast: prefix, and doesn't need &=C
                    form.append(f"Cast: Deal {value}{add} damage")
            elif action == "F":
                br, _, c = value.partition("+")
                if c:
                    if c == "2":
                        c = " twice"
                    elif c == "3":
                        c = " three times"
                    else:
                        c = f" {c} times"
                if not br:
                    form.append("focus {target} closed breach{plural2}{c}")
                elif br == "0":
                    form.append("focus {targ_sing} closed breach with the lowest focus cost{c}")
                else:
                    a = {"1": "I", "2": "II", "3": "III", "4": "IV"}
                    form.append(f"focus {{target}} {a[br]} breach{c}")
            elif action == "G":
                form.append(f"Gravehold gains {value} life")
            elif action == "H":
                form.append("cast a spell in hand")
            elif action == "I":
                form.append(_int_internal(value, "discard"))
            elif action == "J":
                if value == "1":
                    form.append("{maybe_source}draw{plural3} a card")
                else:
                    form.append(f"{{maybe_source}}draw{{plural3}} {value} cards")
            elif action == "K":
                form.append(_int_internal(value, "destroy"))
            elif action == "L":
                form.append(f"{{maybe_source}}gain{{plural3}} {value} life")
            elif action == "N":
                s = f"{value}th"
                if value == "1":
                    s = "first"
                if value == "2":
                    s = "second"
                if value == "3":
                    s = "third"
                form.append(f"if this is the {s} time you have played {{name}} this turn,")
            elif action == "O":
                form.append(f"Xaxos: Outcast gains {value} charge{'s' if int(value) > 1 else ''}")
            elif action == "P":
                form.append("cast {target} prepped spell{plural1}")
            elif action == "Q":
                if value == "1":
                    form.append("discard a prepped spell")
                else:
                    form.append(f"discard {value} prepped spells")
            elif action == "R":
                form.append(f"{{source}} gain{{plural3}} {value} charge{'s' if int(value) > 1 else ''}")
            elif action == "S":
                form.append(f"{config.prefix}Silence a minion")
            elif action == "X":
                form.append("destroy {card}")
            elif action == "Z":
                br, _, c = value.partition("+")
                if c:
                    if c == "2":
                        c = " twice"
                    else:
                        c = f" {c} times"
                if not value:
                    form.append("{source} focuses one of their closed breaches{c}")
                elif value == "0":
                    form.append("{source} focuses their closed breach with the lowest focus cost{c}")
                else:
                    a = {"1": "I", "2": "II", "3": "III", "4": "IV"}
                    form.append(f"{{source}} focuses their {a[br]} breach{c}")

            # modifiers to the previous entry
            elif action == "&":
                x = form.pop(-1)
                if value.isdigit():
                    form.append(f"{x} that costs {value}")
                elif value[0] == "+":
                    value = value[1:]
                    form.append(f"if {{pronoun}} have at least {value} charges, {x}")
                elif value[0] == "-":
                    value = value[1:]
                    form.append(f"if {{pronoun}} have {value} charges or less, {x}")
                elif "-" in value:
                    lower, _, upper = value.partition("-")
                    if lower == upper:
                        if lower == "0":
                            form.append(f"if {{pronoun}} are exhausted, {x}")
                        else:
                            form.append(f"if {{pronoun}} have {lower} life, {x}")
                    elif lower == "0":
                        form.append(f"if {{pronoun}} have {upper} life or less, {x}")
                    elif upper == "0":
                        form.append(f"if {{pronoun}} have {lower} life or more, {x}")
                    else:
                        form.append(f"if {{pronoun}} have from {lower} to {upper} life, {x}")
                elif value == "C":
                    form.append(f"Cast: {x[0].upper()}{x[1:]}")
                elif value == "D":
                    form.append("divided however you choose to the nemesis and any number of minions")
                elif value == "H":
                    form.append(f"{{source}} may {x}")
                elif value == "I":
                    form.append(f"If {{pronoun}} do, {x}")
                elif value == "L":
                    form.append(f"{x} or less")
                elif value == "M":
                    form.append(f"{x} or more")
                elif value == "N":
                    form.append(f"if the nemesis tier is 2 or higher, {x}")
                elif value == "O":
                    form.append(f"if all your breaches are opened, {x}")
                elif value == "T":
                    form.append("that can only be used to")
                elif value == "W":
                    form.append(f"{x} without discarding it")
                else:
                    form.append(f"ERROR: Unrecognized param {value}\nText: {x}")

            elif action == "%": # further modifiers to &=T
                x = form.pop(-1)
                values = []
                if "C" in value:
                    values.append("gain cards")
                if "G" in value:
                    values.append("gain a gem")
                if "R" in value:
                    if not values:
                        values.append("gain")
                    else:
                        values.append("or")
                    values.append("a relic")
                if "S" in value:
                    if not values:
                        values.append("gain")
                    else:
                        values.append("or")
                    values.append("a spell")

                if "F" in value or "O" in value:
                    if "F" in value:
                        values.append("focus")
                    if "O" in value:
                        if "F" in value:
                            values.append("or")
                        values.append("open")
                    if "IV" in value:
                        values.append("your IV breach")
                    elif "III" in value:
                        values.append("your III breach")
                    elif "II" in value:
                        values.append("your II breach")
                    elif "I" in value:
                        values.append("your I breach")
                    else:
                        values.append("a breach")

                form.append(f"{x} {' '.join(values)}")

            elif action == "$": # target modifiers
                # todo: remove the load on individual values and split further
                x = form.pop(-1)
                if value == "A":
                    form.append(x.format(
                        source="any player",
                        maybe_source="any player ",
                        pronoun="they",
                        target="any player's",
                        targ_sing="any player's",
                        card="any card",
                        plural1="",
                        plural2="",
                        plural3="s",
                        a_card="{a_card}",
                        place="{place}",
                        ))
                elif value == "B":
                    form.append(x.format(
                        source="any ally",
                        maybe_source="any ally ",
                        pronoun="they",
                        target="any ally's",
                        targ_sing="any ally's",
                        card="a card you played this turn",
                        plural1="",
                        plural2="",
                        plural3="s",
                        a_card="{a_card}",
                        place="{place}",
                        ))
                elif value == "C":
                    form.append(x.format(
                        source="you",
                        maybe_source="",
                        pronoun="you",
                        target="one of your",
                        targ_sing="your",
                        card="this",
                        plural1="s",
                        plural2="es",
                        plural3="",
                        a_card="{a_card}",
                        place="{place}",
                        ))
                elif value == "D":
                    form.append(x.format(
                        source="each ally",
                        maybe_source="each ally ",
                        pronoun="they",
                        target="each ally's",
                        targ_sing="each ally's",
                        card="any card",
                        plural1="",
                        plural2="",
                        plural3="s",
                        a_card="{a_card}",
                        place="{place}",
                    ))
                elif value == "E":
                    form.append(x.format(place1="in hand", place2=""))
                elif value == "F":
                    form.append(x.format(place1="in your discard pile", place2="of your discard pile"))
                elif value == "G":
                    form.append(x.format(place1="in your hand or discard pile", place2=""))
                elif value == "H":
                    form.append(x.format(place1="in hand or on top of any player's discard pile", place2=""))
                elif value == "I":
                    form.append(x.format(place1="on the top of any player's discard pile", place2="of any player's discard pile"))
                elif value == "J":
                    form.append(x.format(a_card="a card", place="{place1}"))
                elif value == "K":
                    form.append(x.format(a_card="the top card", place="{place2}"))
                else:
                    form.append(f"ERROR: Unrecognized target modifier {value}\nText: {x}")

            else:
                form.append(f"ERROR: Unrecognized token {action}={value}")

            if to_append:
                a = form.pop(-1)
                b = form.pop(-1)
                form.append(f"{b} {a}")

        text.append(" ".join(f"{x[0].upper()}{x[1:]}." for x in form))

    return "\n".join(text)

def format_player_card_special(code: _extra_dict) -> Tuple[str, str]:
    """Return a formatted text of the card's special conditions."""
    before = []
    after = []
    for key, value in code.items():
        if key == "D":
            before.append(f"{config.prefix}Dual")
        elif key == "E":
            before.append(f"{config.prefix}Echo")
        elif key == "L":
            before.append(f"{config.prefix}Link")
        elif key == "N":
            before.append(f"Use this only when fighting against {value}.")
        elif key == "T":
            after.append(f"Card type: {value}")
        elif key == "U":
            before.append(f"Use this card only when playing with {value}.")
        else:
            before.append(f"ERROR: Unrecognized token {key}={value}")
    return "\n".join(before), "\n".join(after)

