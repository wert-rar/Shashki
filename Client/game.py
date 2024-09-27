import uuid
current_player = "w"
unstarted_games = {}
current_games = (1, 0, 1)

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


class Game:
    def __init__(self, f_user, c_user, game_id):
        self.f_user = f_user
        self.c_user = c_user
        self.game_id = game_id
        self.moves_count = 0
        self.pieces = pieces
        self.current_player = "w"

    def user_color(self, user_id):
        if user_id == self.f_user:
            return 'white'
        elif user_id == self.c_user:
            return 'black'
        return None

    def pieces_and_current_player(self):
        self.current_player = self.f_user if self.moves_count % 2 == 0 else self.c_user
        current_color = 'white' if current_player == self.f_user else 'black'
        current_pieces = self.pieces[current_color]
        return current_player, current_pieces

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"


def find_waiting_game():
    for game_id, game in unstarted_games.items():
        if not game.f_user or not game.c_user:
            return game
    return None


def update_game_with_user(game_id, user_login, color):
    if game_id in unstarted_games:
        game = unstarted_games[game_id]
        if color == 'white':
            if game.f_user is None:
                game.f_user = user_login
                return True
            else:
                raise ValueError(f"В игре {game_id} уже есть белый игрок.")
        elif color == 'black':
            if game.c_user is None:
                game.c_user = user_login
                return True
            else:
                raise ValueError(f"В игре {game_id} уже есть черный игрок.")
        else:
             raise ValueError("Цвет должен быть либо «белым», либо «черным».")
    else:
        raise ValueError(f"Игра {game_id} не существует.")


def create_new_game(user_login):
    game_id = current_games
    new_game = Game(f_user=user_login, c_user=None, game_id=game_id)
    unstarted_games[game_id] = new_game
    return game_id


def get_game_status(game_id):
    if game_id in current_games:
        game = current_games[game_id]
    elif game_id in unstarted_games:
        game = unstarted_games[game_id]
    else:
        return None

    if game.f_user and game.c_user:
        return {'status': 'ready'}
    else:
        return {'status': 'waiting'}