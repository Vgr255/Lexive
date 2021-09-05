from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple, Optional, Union

import config

_parse_list = List[List[Tuple[str, str]]]
_extra_list = List[Tuple[str, str]]
_range_tuple = Tuple[Optional[int], Optional[int]]
_data_dict = Dict[str, Union[bool, None, str, _range_tuple]]

_definitions: Dict[str, _ActionBase] = {}

def register(prefix: str):
    def inner(cls: _ActionBase):
        _definitions[prefix] = cls
        return cls
    return inner

def get_data_dict() -> _data_dict:
    ret = {
        "source": None,
        "location": None,
        "auto_cast": False,
        "cost": (None, None),
        "charges": (None, None),
        "life": (None, None),
        "specific": "",
    }
    ret.update((v, False) for v in _data_values.values())
    return ret

_data_values: Dict[str, str] = {
    "C": "cast",
    "D": "divided",
    "H": "optional",
    "I": "conditional",
    "N": "nemesis_tier",
    "O": "opened",
    "W": "no_discard",
}

class AppendType(Enum):
    NoAppend = ""
    Concat = "{} {}"
    And = "{} and {}"
    AndThen = "{} and then {}"

class CardLocation(Enum):
    InHand = "{a_card} in hand"
    InSelfDiscard = "{a_card} in your discard pile"
    HandOrSelfDiscard = "{a_card} in your hand or discard pile"
    HandOrAnyDiscard = "{a_card} in hand or on top of any player's discard pile"
    TopAnyDiscard = "{top_card} of any player's discard pile"

_source_values: Dict[str, str] = {
    "A": "any player",
    "B": "any ally",
    "C": "self",
    "D": "each ally",
}

_location_values: Dict[str, CardLocation] = {
    "E": CardLocation.InHand,
    "F": CardLocation.InSelfDiscard,
    "G": CardLocation.HandOrSelfDiscard,
    "H": CardLocation.HandOrAnyDiscard,
    "I": CardLocation.TopAnyDiscard,
}

class Context:
    def __init__(self, actions: List[_ActionBase], card_name: str, card_type: str, data: _data_dict, contexts: List[Context]):

        # FIXME: move source/target/etc. to be per-token rather than per-context
        # (this will require moving all of the &=* tokens outside of Context)
        self.actions = actions
        self.card_name = card_name
        self.card_type = card_type

        # we are storing a list of all the contexts of this card
        # (this is the whole code if there is no OR in it)
        # sometimes, we need to look ahead (or back) and we can use this
        # 'self in self.contexts' is always true
        # this is mutable, so we want to keep the original around
        self.contexts = contexts

        self.source: Optional[str] = data["source"]
        self.location: Optional[CardLocation] = data["location"]

        self.cost: _range_tuple = data["cost"]
        self.charges: _range_tuple = data["charges"]
        self.life: _range_tuple = data["life"]

        self.specific: str = data["specific"]

        self.cast: bool = data["cast"]
        self.auto_cast: bool = data["auto_cast"]
        self.divided: bool = data["divided"]
        self.optional: bool = data["optional"]
        self.conditional: bool = data["conditional"]
        self.nemesis_tier: bool = data["nemesis_tier"]
        self.opened: bool = data["opened"]
        self.no_discard: bool = data["no_discard"]

    def format(self, *, auto_format: bool) -> str:
        final: List[str] = []
        for action in self.actions:
            value = action.format(context=self)
            if action.append_type != AppendType.NoAppend:
                prev = final.pop(-1)
                value = action.append_type.value.format(prev, value)
            final.append(value)

        ret = " ".join(final)
        if self.cost != (None, None):
            if self.cost[0] is None:
                ret = f"{ret} that costs {self.cost[1]}$ or less"
            elif self.cost[1] is None:
                ret = f"{ret} that costs {self.cost[0]}$ or more"
            else:
                ret = f"{ret} that costs {self.cost[0]}$"
        if self.charges != (None, None):
            if self.source == "self":
                pronoun = "you"
            else:
                pronoun = "they"
            if self.charges[0] is None:
                ret = f"if {pronoun} have {self.charges[1]} charges or less, {ret}"
            elif self.charges[1] is None:
                ret = f"if {pronoun} have at least {self.charges[0]} charges, {ret}"
            else:
                ret = f"if {pronoun} have between {self.charges[0]} and {self.charges[1]} charges, {ret}"
        if self.life != (None, None):
            if self.source == "self":
                pronoun = "you"
            else:
                pronoun = "they"
            if self.life[0] == self.life[1]:
                if self.life[0] == 0:
                    ret = f"if {pronoun} are exhausted, {ret}"
                else:
                    ret = f"if {pronoun} have {self.life[0]} life, {ret}"
            elif self.life[0] == 0:
                ret = f"if {pronoun} have {self.life[1]} life or less, {ret}"
            elif self.life[1] == 99:
                ret = f"if {pronoun} have {self.life[0]} life or more, {ret}"
            else:
                ret = f"if {pronoun} have between {self.life[0]} and {self.life[1]} life, {ret}"

        if self.specific:
            values = []
            if "C" in self.specific:
                values.append("gain cards")
            if "G" in self.specific:
                values.append("gain a gem")
            if "R" in self.specific:
                if not values:
                    values.append("gain")
                else:
                    values.append("or")
                values.append("a relic")
            if "S" in self.specific:
                if not values:
                    values.append("gain")
                else:
                    values.append("or")
                values.append("a spell")

            if "F" in self.specific or "O" in self.specific:
                if "F" in self.specific:
                    values.append("focus")
                if "O" in self.specific:
                    if "F" in self.specific:
                        values.append("or")
                    values.append("open")
                if "IV" in self.specific:
                    values.append("your IV breach")
                elif "III" in self.specific:
                    values.append("your III breach")
                elif "II" in self.specific:
                    values.append("your II breach")
                elif "I" in self.specific:
                    values.append("your I breach")
                else:
                    values.append("a breach")

            ret = f"{ret} that can only be used to {' '.join(values)}"

        if self.optional:
            if self.source == "self":
                ret = f"you may {ret}"
            else:
                ret = f"{self.source} may {ret}"
        if self.divided:
            ret = f"{ret} divided however you choose to the nemesis and any number of minions"
        if self.conditional:
            if self.source == "self":
                ret = f"if you do, {ret}"
            else:
                ret = f"if they do, {ret}"
        if self.nemesis_tier:
            ret = f"if the nemesis tier is 2 or higher, {ret}"
        if self.opened:
            # TODO: Add rule clarification for this, somewhere
            ret = f"if all of your breaches are opened, {ret}"
        if self.no_discard:
            ret = f"{ret} without discarding it"

        if auto_format:
            ret = f"{ret[0].upper()}{ret[1:]}."
            if self.auto_cast or self.cast:
                ret = f"Cast: {ret}"
        elif self.cast:
            ret = f"Cast: {ret}"

        return ret

class _ActionBase:
    support_additional = False
    support_exclusive = False
    support_negative = False
    support_range = False

    convert_integer = False
    has_value = True

    def __init__(self, value: str, append_type: AppendType):
        self.append_type = append_type
        if not self.has_value:
            return
        self.additional = False
        self.exclusive = False
        self.negative = False
        if self.support_additional and value[0] == "+":
            self.additional = True
            value = value[1:]
        if self.support_exclusive and value[0] == "!":
            self.exclusive = True
            value = value[1:]
        if self.support_negative and value[0] == "-":
            self.negative = True
            value = value[1:]
        if self.support_range:
            if "-" in value:
                begin, _, end = value.partition("-")
                self.lower = int(begin)
                self.upper = int(end)
            else:
                self.lower = self.upper = int(value)

        if self.convert_integer:
            value = int(value)
        self.value = value

    def format(self, context: Context) -> str:
        """Base formatting function. The return value should be lowercase and not have a trailing period."""
        return f"{self.__class__.__name__} does not support formatting."

class _ChargePulseBase(_ActionBase):
    support_additional = True
    support_negative = True
    convert_integer = True

    word = "<undefined>"

    def format(self, context: Context) -> str:
        add = ""
        if self.additional:
            add = "an additional "
        if context.optional or context.source == "self":
            if self.value == 1 and self.negative:
                if self.additional:
                    return f"lose an additional {self.word}"
                return f"lose a {self.word}"
            s = "lose" if self.negative else "gain"
            return f"{s} {add}{self.value} {self.word}{'s' if self.value > 1 else ''}"
        if self.value == 1 and self.negative:
            return f"{context.source} loses a {self.word}"
        s = "loses" if self.negative else "gains"
        return f"{context.source} {s} {add}{self.value} {self.word}{'s' if self.value > 1 else ''}"

class _DiscardDestroyBase(_ActionBase):
    support_range = True
    word = "<undefined>"

    def format(self, context: Context) -> str:
        form = []
        if context.optional or context.source == "self":
            form.append(self.word)
        else:
            form.append(f"{context.source} {self.word}s")

        if self.lower == self.upper:
            if self.lower == 1:
                a_card = "a card"
                top_card = "the top card"
            else:
                a_card = f"{self.lower} cards"
                top_card = f"the top {self.lower} cards"

        elif self.lower == 0:
            a_card = f"up to {self.upper} cards"
            top_card = f"up to {self.upper} cards on top"

        else:
            a_card = f"between {self.lower} and {self.upper} cards"
            top_card = f"between {self.lower} and {self.upper} cards on top"

        form.append(context.location.value.format(a_card=a_card, top_card=top_card))

        return " ".join(form)

@register("A")
class AetherGain(_ActionBase):
    support_additional = True
    convert_integer = True

    def format(self, context: Context) -> str:
        if self.additional:
            return f"gain an additional {self.value}$"
        return f"gain {self.value}$"

@register("B")
class CastPrepped(_ActionBase):
    has_value = False

    def format(self, context: Context) -> str:
        if context.source == "self":
            return "cast one of your prepped spells"
        return f"cast {context.source}'s prepped spell"

@register("C")
class ChargeGain(_ChargePulseBase):
    word = "charge"

@register("D")
class DamageDeal(_ActionBase):
    support_additional = True
    convert_integer = True

    def format(self, context: Context) -> str:
        add = ""
        if self.additional:
            add = " additional"
        return f"deal {self.value}{add} damage"

@register("F")
class FocusBreach(_ActionBase):
    def __init__(self, value: str, append_type: AppendType):
        super().__init__(value, append_type)
        breach, _, count = value.partition("+")
        self.breach = int(breach) if breach else None
        self.count = int(count) if count else 1

    def format(self, context: Context) -> str:
        count = ""
        if self.count == 2:
            count = " twice"
        elif self.count == 3:
            count = " three times"
        elif self.count == 4:
            count = " four times"

        if self.breach is None:
            if context.source == "self":
                return f"focus one of your breaches{count}"
            return f"focus {context.source}'s closed breach{count}"

        if self.breach == 0:
            if context.source == "self":
                return f"focus your closed breach with the lowest focus cost{count}"
            return f"focus {context.source}'s closed breach with the lowest focus cost{count}"

        a = (None, "I", "II", "III", "IV")
        if context.source == "self":
            return f"focus your {a[self.breach]} breach{count}"
        return f"focus {context.source}'s {a[self.breach]} breach{count}"

@register("G")
class GraveholdHealth(_ActionBase):
    support_additional = True
    support_negative = True
    convert_integer = True

    def format(self, context: Context) -> str:
        a = "an additional " if self.additional else ""
        if self.negative:
            return f"Gravehold suffers {a}{self.value} damage"
        return f"Gravehold gains {a}{self.value} life"

@register("H")
class CastFromHand(_ActionBase):
    has_value = False

    def format(self, context: Context) -> str:
        return "cast a spell in hand"

@register("I")
class DiscardFromHand(_DiscardDestroyBase):
    word = "discard"

@register("J")
class DrawCards(_ActionBase):
    support_additional = True
    convert_integer = True

    def format(self, context: Context) -> str:
        if context.optional or context.source == "self":
            draw = "draw"
        else:
            draw = f"{context.source} draws"

        if self.value == 1:
            if not self.additional:
                count = "a card"
            else:
                count = "an additional card"
        else:
            if not self.additional:
                count = f"{self.value} cards"
            else:
                count = f"an additional {self.value} cards"

        return f"{draw} {count}"

@register("K")
class DestroyCards(_DiscardDestroyBase):
    word = "destroy"

@register("L")
class GainLife(_ActionBase):
    support_additional = True
    support_negative = True
    convert_integer = True

    def format(self, context: Context) -> str:
        add = ""
        if self.additional:
            add = "an additional "
        if self.negative:
            if context.optional or context.source == "self":
                return f"suffer {add}{self.value} damage"
            return f"{context.source} suffers {add}{self.value} damage"

        if context.source == "self":
            return f"gain {add}{self.value} life"
        return f"{context.source} gains {add}{self.value} life"

@register("M")
class PlayCountName(_ActionBase):
    support_exclusive = True
    convert_integer = True

    def format(self, context: Context) -> str:
        neg = ""
        if self.exclusive:
            neg = "not "
        s = f"{self.value}th"
        if self.value == 1:
            s = "first"
        if self.value == 2:
            s = "second"
        if self.value == 3:
            s = "third"
        return f"if this is {neg}the {s} {context.card_name} you have {'cast' if 'S' in context.card_type else 'played'} this turn,"

@register("N")
class PlayCountTime(_ActionBase):
    support_exclusive = True
    convert_integer = True

    def format(self, context: Context) -> str:
        neg = ""
        if self.exclusive:
            neg = "not "
        s = f"{self.value}th"
        if self.value == 1:
            s = "first"
        if self.value == 2:
            s = "second"
        if self.value == 3:
            s = "third"
        return f"if this is {neg}the {s} time you have {'cast' if 'S' in context.card_type else 'played'} {context.card_name} this turn,"

@register("O")
class XaxosCharges(_ActionBase):
    support_additional = True
    convert_integer = True

    def format(self, context: Context) -> str:
        add = ""
        if self.additional:
            add = "an additional "
        return f"Xaxos: Outcast gains {add}{self.value} charge{'s' if self.value > 1 else ''}"

@register("P")
class PulseTokens(_ChargePulseBase):
    word = "pulse token"

@register("Q")
class DiscardPrepped(_ActionBase):
    support_range = True

    def format(self, context: Context) -> str:
        if self.lower == self.upper:
            if self.lower == 1:
                return "discard a prepped spell"
            return f"discard {self.lower} prepped spells"

        if self.lower == 0:
            return f"discard up to {self.upper} prepped spells"

        return f"discard between {self.lower} and {self.upper} prepped spells"

@register("R")
class DestroyPrepped(_ActionBase):
    support_range = True

    def format(self, context: Context) -> str:
        if self.lower == self.upper:
            if self.lower == 1:
                return "destroy a prepped spell"
            return f"destroy {self.lower} prepped spells"

        if self.lower == 0:
            return f"destroy up to {self.upper} prepped spells"

        return f"destroy between {self.lower} and {self.upper} prepped spells"

@register("S")
class SilenceMinion(_ActionBase):
    has_value = False

    def format(self, context: Context) -> str:
        return f"{config.prefix}Silence a minion"

@register("X")
class DestroyThis(_ActionBase):
    has_value = False

    def format(self, context: Context) -> str:
        return "destroy this"

@register("Z")
class AllyFocus(_ActionBase):
    def __init__(self, value: str, append_type: AppendType):
        super().__init__(value, append_type)
        breach, _, count = value.partition("+")
        self.breach = int(breach) if breach else None
        self.count = int(count) if count else 1

    def format(self, context: Context) -> str:
        count = ""
        if self.count == 2:
            count = " twice"
        elif self.count == 3:
            count = " three times"
        elif self.count == 4:
            count = " four times"

        if self.breach is None:
            return f"{context.source} focuses one of their closed breaches{count}"

        if self.breach == 0:
            return f"{context.source} focuses their closed breach with the lowest focus cost{count}"

        a = (None, "I", "II", "III", "IV")
        return f"{context.source} focuses their {a[self.breach]} breach{count}"

def parse_player_card(code: str) -> Tuple[_parse_list, _extra_list]:
    values = []
    extra = []
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
        extra.append((key, value))
    return values, extra

def itemize(code: _parse_list, name: str, ctype: str) -> List[List[Context]]:
    result: List[List[Context]] = []
    for d in code:
        form: List[Context] = []
        actions: List[_ActionBase] = []
        data = get_data_dict()
        for key, value in d:
            a = tuple(AppendType)
            c = key.count("&", 0, len(a) - 1)
            key = key.lstrip("&") if key != "&" else key
            atype = a[c]

            if actions and atype == AppendType.NoAppend and key.isalpha(): # store existing context
                ctx = Context(actions, name, ctype, data, form)
                form.append(ctx)
                # create new variables for the next sentence
                actions = []
                data = get_data_dict()

            if key in _definitions:
                if key == "D" and not actions and not form and "S" in ctype:
                    data["auto_cast"] = True
                actions.append(_definitions[key](value, atype))

            elif key == "&":
                if value in _data_values:
                    data[_data_values[value]] = True
                elif value[0].isdigit() and len(value) <= 2:
                    if len(value) == 1:
                        data["cost"] = (int(value), int(value))
                    elif value[1] == "-":
                        data["cost"] = (None, int(value[0]))
                    elif value[1] == "+":
                        data["cost"] = (int(value[0]), None)
                elif value[0] == "+":
                    data["charges"] = (int(value[1]), None)
                elif value[0] == "-":
                    data["charges"] = (None, int(value[1]))
                elif "-" in value:
                    lower, _, upper = value.partition("-")
                    data["life"] = (int(lower), int(upper))

            elif key == "%":
                data["specific"] = value

            elif key == "$": # target
                if value in _source_values:
                    data["source"] = _source_values[value]
                if value in _location_values:
                    data["location"] = _location_values[value]

        ctx = Context(actions, name, ctype, data, form)
        form.append(ctx)

        result.append(form)

    return result

def format_player_card_effect(code: _parse_list, name: str, ctype: str, *, auto_format=True) -> str:
    """Return a formatted text of the card effect."""
    text = []
    contexts = itemize(code, name, ctype)
    for ctx_list in contexts:
        if text:
            text.append("OR")
        form = []
        for ctx in ctx_list:
            form.append(ctx.format(auto_format=auto_format))
        text.append(" ".join(form))

    return "\n".join(text)

def format_player_card_special(code: _extra_list, name: str, ctype: str) -> Tuple[str, str]:
    """Return a formatted text of the card's special conditions."""
    before = []
    after = []
    for key, value in code:
        if key == "C":
            before.append("This spell may be prepped to a closed breach without focusing it.")
        elif key == "D":
            before.append(f"{config.prefix}Dual")
        elif key == "E":
            before.append(f"{config.prefix}Echo")
        elif key == "G":
            before.append("When you gain this,")
        elif key == "L":
            before.append(f"{config.prefix}Link")
        elif key == "N":
            before.append(f"Use this only when playing with {value}.")
        elif key == "P":
            before.append("While prepped,")
        elif key == "T":
            after.append(f"Card type: {value}")
        elif key == "U":
            before.append(f"Use this card only when playing with {value}.")
        elif key == "&":
            x = before.pop(-1)
            if value == "C":
                before.append(f"{x} at the end of your casting phase,")
            elif value == "G":
                before.append(f"{x} when you gain a card,")
            elif value == "M":
                before.append(f"{x} once per turn during your main phase,")
            else:
                before.append(f"ERROR: Unrecognized modifier {value}\nText: {x}")
        elif key == "?":
            x = before.pop(-1)
            content = []
            for step in value.split("/"):
                internal = []
                for c in step.split(","):
                    a, _, b = c.partition(":")
                    internal.append((a, b))
                content.append(internal)
            text = format_player_card_effect(content, name, ctype, auto_format=False)
            before.append(f"{x} {text}.")

        else:
            before.append(f"ERROR: Unrecognized token {key}={value}")

    return "\n".join(before), "\n".join(after)

