from Lexive.code_parser.player_cards import format_player_card_special
from code_parser.player_cards import parse_player_card, format_player_card_effect, format_player_card_special

def parse(code: str, type: str):
    if type == "P":
        return parse_player_card(code)
    return code

def format(code, type: str) -> str:
    if type == "PE":
        return format_player_card_effect(code)
    if type == "PS":
        return format_player_card_special(code)
    return ""
