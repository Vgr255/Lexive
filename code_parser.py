from typing import List, Dict, Tuple

import config

_parse_list = List[Tuple[str, str]]
_extra_dict = Dict[str, str]

def _int_internal(x, word, place):
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
            return f"{word} a card in {place}"
        return f"{word} {lower} cards in {place}"

    if lower == 0:
        return f"{word} up to {upper} cards in {place}"
    return f"{word} from {lower} to {upper} cards in {place}"

def parse(code: str) -> Tuple[_parse_list, _extra_dict]:
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

def as_text(code: _parse_list) -> str:
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
                form.append(f"gain {value}$")
            if action == "B":
                form.append(f"gain {value} additional $")
            if action == "C":
                form.append(f"gain {value} charge{'s' if int(value) > 1 else ''}")
            if action == "D":
                if form: # might be part of something like "do X, if you do, deal Y damage"
                    form.append(f"deal {value} damage")
                else: # but if it's not, we can assume it has a Cast: prefix, and doesn't need &=C
                    form.append(f"Cast: Deal {value} damage")
            if action == "E":
                form.append(f"deal {value} additional damage")
            if action == "F":
                form.append("focus {target} closed breach{plural2}")
            if action == "G":
                form.append(f"Gravehold gains {value} life")
            if action == "H":
                form.append("cast a spell in hand")
            if action == "I":
                form.append(_int_internal(value, "discard", "hand"))
            if action == "J":
                if value == "1":
                    form.append("{source} draw{plural3} a card")
                else:
                    form.append(f"{{source}} draw{{plural3}} {value} cards")
            if action == "K":
                form.append(_int_internal(value, "destroy", "hand"))
            if action == "L":
                form.append(f"{{source}} gains {value} life")
            if action == "N":
                s = f"{value}th"
                if value == "1":
                    s = "first"
                if value == "2":
                    s = "second"
                if value == "3":
                    s = "third"
                form.append(f"if this is the {s} time you have played {{name}} this turn,")
            if action == "O":
                form.append(f"Xaxos: Outcast gains {value} charge{'s' if int(value) > 1 else ''}")
            if action == "P":
                form.append("cast {target} prepped spell{plural1}")
            if action == "R":
                form.append(f"{{source}} gain{{plural3}} {value} charge{'s' if int(value) > 1 else ''}")
            if action == "S":
                form.append(f"{config.prefix}Silence a minion")
            if action == "X":
                form.append("destroy {card}")
            if action == "Z":
                form.append("focus {targ_sing} closed breach with the lowest focus cost")

            # modifiers to the previous entry
            if action == "&":
                x = form.pop(-1)
                if value.isdigit():
                    form.append(f"{x} that costs {value}")
                if value == "A":
                    form.append(x.format(
                        source="any player",
                        target="any player's",
                        targ_sing="any player's",
                        card="any card",
                        plural1="",
                        plural2="",
                        plural3="s",
                        ))
                if value == "B":
                    form.append(x.format(
                        source="any ally",
                        target="any ally's",
                        targ_sing="any ally's",
                        card="a card you played this turn",
                        plural1="",
                        plural2="",
                        plural3="s",
                        ))
                if value == "C":
                    form.append(f"Cast: {x[0].upper()}{x[1:]}")
                if value == "H":
                    form.append(f"{{source}} may {x}")
                if value == "I":
                    form.append(f"If you do, {x}")
                if value == "L":
                    form.append(f"{x} or less")
                if value == "M":
                    form.append(f"{x} or more")
                if value == "O":
                    form.append(f"if all your breaches are opened, {x}")
                if value == "T":
                    form.append("that can only be used to")
                if value == "W":
                    form.append(f"{x} without discarding it")
                if value == "Y":
                    form.append(x.format(
                        source="you",
                        target="one of your",
                        targ_sing="your",
                        card="this",
                        plural1="s",
                        plural2="es",
                        plural3="",
                        ))

            if action == "%": # further modifiers
                x = form.pop(-1)
                values = []
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

            if to_append:
                a = form.pop(-1)
                b = form.pop(-1)
                form.append(f"{b} {a}")

        text.append(" ".join(f"{x[0].upper()}{x[1:]}." for x in form))

    return "\n".join(text)

def as_special(code: _extra_dict) -> Tuple[str, str]:
    """Return a formatted text of the card's special conditions."""
    return '', ''
