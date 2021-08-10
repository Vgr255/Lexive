from code_parser.player_cards import parse_player_card, format_player_card_effect, format_player_card_special

def parse(code: str, type: str):
    if type == "P":
        return parse_player_card(code)
    return code

def format(code, type: str, name: str, ctype: str) -> str:
    if type == "PE":
        return format_player_card_effect(code, name, ctype)
    if type == "PS":
        return format_player_card_special(code, name, ctype)
    return ""
