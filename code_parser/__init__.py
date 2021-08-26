from typing import List

from code_parser.player_cards import parse_player_card, format_player_card_effect, format_player_card_special

def parse(code: str, type: str):
    if type == "P":
        return parse_player_card(code)
    return code

def format(code, type: str, name: str, ctype: str) -> List[str]:
    ret: List[str] = []
    if type == "PE":
        ret.append(format_player_card_effect(code, name, ctype))
    if type == "PS":
        ret.extend(format_player_card_special(code, name, ctype))
    d = {}
    while True:
        try:
            for i, r in enumerate(ret):
                ret[i] = r.format(**d)
        except KeyError as e:
            d[e.args[0]] = f"ERROR: Item {e.args[0]!r} was not included in format string"
        except Exception as e:
            ret[i] = f"ERROR: Malformed code string {r!r}"
            break
        else:
            break
    return ret
