from app import pieces

class Game:
    def __init__(self, f_user, c_user, game_id):
        self.f_user = f_user
        self.c_user = c_user
        self.game_id = game_id
        self.moves_count = 0
        self.pieces = pieces

    def user_color(self, user_id):
        if user_id == self.f_user:
            return 'white'
        elif user_id == self.c_user:
            return 'black'
        return None

    def pieces_and_current_player(self):
        current_player = self.f_user if self.moves_count % 2 == 0 else self.c_user
        current_color = 'white' if current_player == self.f_user else 'black'
        current_pieces = self.pieces[current_color]
        return current_player, current_pieces

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"