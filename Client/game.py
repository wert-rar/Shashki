import itertools

current_player = "w"
unstarted_games = {}
current_games = {}

pieces = [
    {"color": 1, "x": 1, "y": 0, "mode": "p"},
    {"color": 1, "x": 3, "y": 0, "mode": "p"},
    {"color": 1, "x": 5, "y": 0, "mode": "p"},
    {"color": 1, "x": 7, "y": 0, "mode": "p"},
    {"color": 1, "x": 0, "y": 1, "mode": "p"},
    {"color": 1, "x": 2, "y": 1, "mode": "p"},
    {"color": 1, "x": 4, "y": 1, "mode": "p"},
    {"color": 1, "x": 6, "y": 1, "mode": "p"},
    {"color": 1, "x": 1, "y": 2, "mode": "p"},
    {"color": 1, "x": 3, "y": 2, "mode": "p"},
    {"color": 1, "x": 5, "y": 2, "mode": "p"},
    {"color": 1, "x": 7, "y": 2, "mode": "p"},
    {"color": 0, "x": 0, "y": 7, "mode": "p"},
    {"color": 0, "x": 2, "y": 7, "mode": "p"},
    {"color": 0, "x": 4, "y": 7, "mode": "p"},
    {"color": 0, "x": 6, "y": 7, "mode": "p"},
    {"color": 0, "x": 1, "y": 6, "mode": "p"},
    {"color": 0, "x": 3, "y": 6, "mode": "p"},
    {"color": 0, "x": 5, "y": 6, "mode": "p"},
    {"color": 0, "x": 7, "y": 6, "mode": "p"},
    {"color": 0, "x": 0, "y": 5, "mode": "p"},
    {"color": 0, "x": 2, "y": 5, "mode": "p"},
    {"color": 0, "x": 4, "y": 5, "mode": "p"},
    {"color": 0, "x": 6, "y": 5, "mode": "p"}
]

game_id_counter = itertools.count(2)


class Game:
    def __init__(self, f_user, c_user, game_id):
        self.f_user = f_user
        self.c_user = c_user
        self.game_id = game_id
        self.moves_count = 0
        self.pieces = [piece.copy() for piece in pieces]
        self.current_player = "w"

    def user_color(self, user_id):
        if user_id == self.f_user:
            return 'white'
        elif user_id == self.c_user:
            return 'black'
        return None

    def pieces_and_current_player(self):
        current_player = self.f_user if self.moves_count % 2 == 0 else self.c_user
        current_color = 1 if current_player == self.f_user else 0
        current_pieces = [piece for piece in self.pieces if piece["color"] == current_color]
        return current_player, current_pieces

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"


def find_waiting_game():
    for game in unstarted_games.values():
        if not game.f_user or not game.c_user:
            return game
    return None


def update_game_with_user(game_id, user_login, color):
    game = current_games.get(game_id) or unstarted_games.get(game_id)
    if not game:
        raise ValueError(f"Игра {game_id} не существует.")

    if color == 'white':
        if game.f_user is None:
            game.f_user = user_login
            if game.c_user:
                current_games[game_id] = game
                del unstarted_games[game_id]
            return True
        else:
            raise ValueError(f"В игре {game_id} уже есть белый игрок.")
    elif color == 'black':
        if game.c_user is None:
            game.c_user = user_login
            if game.f_user:
                current_games[game_id] = game
                del unstarted_games[game_id]
            return True
        else:
            raise ValueError(f"В игре {game_id} уже есть черный игрок.")
    else:
        raise ValueError("Цвет должен быть либо «белым», либо «черным».")


def create_new_game(user_login):
    game_id = next(game_id_counter)
    new_game = Game(f_user=user_login, c_user=None, game_id=game_id)
    unstarted_games[game_id] = new_game
    return game_id


def get_game_status(game_id):
    game = current_games.get(game_id) or unstarted_games.get(game_id)
    if not game:
        return None

    if game.f_user and game.c_user:
        return {'status': 'active'}
    else:
        return {'status': 'waiting'}
