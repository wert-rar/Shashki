import itertools, random, time, threading

games_lock = threading.Lock()

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
        self.status = "w1"
        self.rank_updated = False
        self.must_capture_piece = None
        self.draw_offer = None
        self.draw_response = None
        self.move_history = []

        self.white_time_remaining = 900
        self.black_time_remaining = 900
        self.last_update_time = None

        self.lock = threading.Lock()

        self.f_player_loaded = False
        self.c_player_loaded = False

    def update_timers(self):
        if self.last_update_time is None:
            return

        now = time.time()
        elapsed = now - self.last_update_time
        self.last_update_time = now

        if self.current_player == 'w':
            self.white_time_remaining -= elapsed
            if self.white_time_remaining <= 0:
                self.white_time_remaining = 0
                self.status = 'b3'
        else:
            self.black_time_remaining -= elapsed
            if self.black_time_remaining <= 0:
                self.black_time_remaining = 0
                self.status = 'w3'

    def user_color(self, user_login):
        if user_login == self.f_user:
            return 'w'
        elif user_login == self.c_user:
            return 'b'
        return None

    def update_pieces(self, new_pieces) -> bool:
        with self.lock:
            if len(new_pieces) != len(self.pieces):
                return False
            self.pieces = new_pieces
            return True

    def update_status(self):
        if self.current_player == "w":
            self.status = "w1"
        else:
            self.status = "b1"

    def switch_turn(self):
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        self.update_status()
        self.last_update_time = time.time()

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"


def find_waiting_game(unstarted_games):
    for game in unstarted_games.values():
        if not game.f_user or not game.c_user:
            return game
    return None


def update_game_with_user(game_id, user_login, color, current_games, unstarted_games):
    with games_lock:
        game = current_games.get(game_id) or unstarted_games.get(game_id)
        if not game:
            return False

        if user_login in [game.f_user, game.c_user]:
            return False

        if color == 'w':
            if game.f_user is None:
                game.f_user = user_login
                if game.c_user:
                    current_games[game_id] = game
                    del unstarted_games[game_id]
                return True
            else:
                return False
        elif color == 'b':
            if game.c_user is None:
                game.c_user = user_login
                if game.f_user:
                    current_games[game_id] = game
                    del unstarted_games[game_id]
                return True
            else:
                return False
        else:
            return False


def create_new_game(user_login, unstarted_games, current_games):
    with games_lock:
        game_id = random.randint(1, 99999999)
        while game_id in current_games or game_id in unstarted_games:
            game_id = random.randint(1, 99999999)
        new_game = Game(f_user=user_login, c_user=None, game_id=game_id)
        unstarted_games[game_id] = new_game
    return game_id


def get_game_status(game_id, current_games, unstarted_games):
    game = current_games.get(game_id) or unstarted_games.get(game_id)
    if not game:
        return None

    if game.f_user and game.c_user:
        return {'status': 'active'}
    elif game.f_user or game.c_user:
        return {'status': 'waiting'}
    else:
        return {'status': 'no_players'}
