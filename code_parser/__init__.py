from code_parser.player_cards import parse_player_card, format_player_card_effect, format_player_card_special

def parse(code: str, type: str):
    if type == "P":
        return parse_player_card(code)
    return code

def format(code, type: str, name: str, ctype: str) -> str:
    ret = ""
    if type == "PE":
        ret = format_player_card_effect(code, name, ctype)
    if type == "PS":
        ret = format_player_card_special(code, name, ctype)
    d = {}
    while True:
        try:
            ret = ret.format(**d)
        except KeyError as e:
            d[e.args[0]] = f"ERROR: Item {e.args[0]!r} was not included in format string"
        except Exception as e:
            ret = f"ERROR: Malformed code string {ret!r}"
            break
        else:
            break
    return ret
