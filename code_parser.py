from typing import List, Dict, Tuple

import config

_parse_list = List[Tuple[str, str]]
_extra_dict = Dict[str, str]

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
            if action == "A":
                form.append(f"gain {value}$")
            if action == "B":
                form.append(f"gain {value} additional $")
            if action == "C":
                form.append(f"gain {value} charges")
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
                form.append(f"Gravehold gains {value} health")
            if action == "H":
                form.append("cast a spell in hand")
            if action == "L":
                form.append(f"{{source}} gains {value} life")
            if action == "O":
                form.append(f"Xaxos: Outcast gains {value} charge{'s' if int(value) > 1 else ''}")
            if action == "P":
                form.append("cast {target} prepped spell{plural1}")
            if action == "S":
                form.append(f"{config.prefix}Silence a minion")
            if action == "X":
                form.append("destroy {card}")

            # modifiers to the previous entry
            if action == "&":
                x = form.pop(-1)
                if value.isdigit():
                    form.append(f"{x} that costs {value}")
                if value == "A":
                    form.append(x.format(source="any player", target="any player's", card="any card", plural1="", plural2=""))
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
                if value == "W":
                    form.append(f"{x} without discarding it")
                if value == "Y":
                    form.append(x.format(source="you", target="one of your", card="this", plural1="s", plural2="es"))

        text.append(" ".join(f"{x[0].upper()}{x[1:]}." for x in form))

    return "\n".join(text)

def as_special(code: _extra_dict) -> Tuple[str, str]:
    """Return a formatted text of the card's special conditions."""
    return '', ''













_code_pattern = r"""

(
    ([a-zA-Z]+)
)
(
    =([a-zA-Z0-9: ]+)
)?
(
    (
        [,/]
    )
    (
        ([a-zA-Z]+)
    )
    (
        =([a-zA-Z0-9: ]+)
    )?
)*
(;
    (
        ([a-zA-Z]+)
    )
    (
        =([a-zA-Z0-9: ]+)
    )?
)*
"""
