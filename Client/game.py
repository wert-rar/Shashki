from base import get_pieces_and_current_player, get_user_color as imported_get_user_color

def pieces_and_current_player(game_id):
    return get_pieces_and_current_player(game_id)

def user_color(game_id, user_id):
    return imported_get_user_color(game_id, user_id)