import time, threading
from base import SessionLocal
from models import Game as DBGame
from Client.redis_base import redis_client
import json
import random
all_games_lock = threading.Lock()
all_games_dict = {}

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

def get_db_pieces(game_id):
    board_state = redis_client.get(f"game:{game_id}:board_state")
    if board_state is not None:
        return json.loads(board_state)
    return []

def update_db_pieces(game_id, new_pieces):
    redis_client.set(f"game:{game_id}:board_state", json.dumps(new_pieces))

class Game:
    def __init__(self, f_user, c_user, game_id):
        self.f_user = f_user
        self.c_user = c_user
        self.game_id = game_id
        self.moves_count = 0
        self.current_player = "w"
        self.status = "w1"
        self.rank_updated = False
        self.must_capture_piece = None
        self.draw_offer = None
        self.draw_response = None
        self.move_history = []
        self.white_time_remaining = 30
        self.black_time_remaining = 30
        self.last_update_time = None
        self.game_started = False
        self.lock = threading.Lock()
        self.f_player_loaded = False
        self.c_player_loaded = False
        self.white_idle_time = 0
        self.black_idle_time = 0
        self.white_in_countdown = False
        self.black_in_countdown = False
        self.white_countdown_remaining = 0
        self.black_countdown_remaining = 0
        self.big_road_counter_w = 0
        self.big_road_counter_b = 0
        self.no_capture_moves = 0
        self.position_history = {}

    def update_timers(self):
        if self.last_update_time is None:
            return
        now = time.time()
        elapsed = now - self.last_update_time
        if self.status in ['w3', 'b3', 'n', 'ns1']:
            self.last_update_time = now
            return
        self.last_update_time = now

        if not self.game_started:
            if self.current_player == 'w':
                self.white_time_remaining -= elapsed
                if self.white_time_remaining <= 0:
                    self.white_time_remaining = 0
                    self.status = 'ns1'
            else:
                self.black_time_remaining -= elapsed
                if self.black_time_remaining <= 0:
                    self.black_time_remaining = 0
                    self.status = 'ns1'
            return

        if self.current_player == 'w':
            self.white_time_remaining -= elapsed
            if self.white_time_remaining <= 0:
                self.white_time_remaining = 0
                self.status = 'b3'
            self.white_idle_time += elapsed
            if not self.white_in_countdown:
                if self.white_idle_time >= 50:
                    self.white_in_countdown = True
                    self.white_countdown_remaining = 120
            else:
                self.white_countdown_remaining -= elapsed
                if self.white_countdown_remaining <= 0:
                    self.white_countdown_remaining = 0
                    self.status = 'b3'
        else:
            self.black_time_remaining -= elapsed
            if self.black_time_remaining <= 0:
                self.black_time_remaining = 0
                self.status = 'w3'
            self.black_idle_time += elapsed
            if not self.black_in_countdown:
                if self.black_idle_time >= 50:
                    self.black_in_countdown = True
                    self.black_countdown_remaining = 120
            else:
                self.black_countdown_remaining -= elapsed
                if self.black_countdown_remaining <= 0:
                    self.black_countdown_remaining = 0
                    self.status = 'w3'

    def user_color(self, user_login):
        if user_login == self.f_user:
            return 'w'
        elif user_login == self.c_user:
            return 'b'
        return None

    def update_status(self):
        if self.current_player == "w":
            self.status = "w1"
        else:
            self.status = "b1"

    def switch_turn(self):
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        self.update_status()
        self.last_update_time = time.time()
        from Client.redis_base import set_move_status
        set_move_status(self.game_id, self.status)

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"

def get_or_create_ephemeral_game(game_id):
    with all_games_lock:
        if game_id in all_games_dict:
            return all_games_dict[game_id]
        db_session = SessionLocal()
        db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
        if not db_game:
            db_session.close()
            return None
        if db_game.status == 'completed':
            db_session.close()
            return None
        f_user = db_game.f_user
        c_user = db_game.c_user
        new_game = Game(f_user, c_user, db_game.game_id)
        new_game.status = db_game.status
        all_games_dict[game_id] = new_game
        db_session.close()
        return new_game

def find_waiting_game_in_db():
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(
        DBGame.status == 'unstarted',
        DBGame.c_user.is_(None),
        DBGame.f_user.isnot(None)
    ).order_by(DBGame.game_id.asc()).first()
    db_session.close()
    return db_game


def update_game_with_user_in_db(game_id, user_login, color):
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if not db_game:
        db_session.close()
        return False
    if db_game.f_user == user_login or db_game.c_user == user_login:
        db_session.close()
        return False
    if color == 'w':
        if db_game.f_user is None:
            db_game.f_user = user_login
            if db_game.c_user:
                db_game.status = 'current'
        else:
            db_session.close()
            return False
    elif color == 'b':
        if db_game.c_user is None:
            db_game.c_user = user_login
            if db_game.f_user:
                db_game.status = 'current'
        else:
            db_session.close()
            return False
    else:
        db_session.close()
        return False
    db_session.commit()
    db_session.close()

    game_obj = get_or_create_ephemeral_game(game_id)
    if game_obj:
        with game_obj.lock:
            if color == 'w':
                game_obj.f_user = user_login
            else:
                game_obj.c_user = user_login
            if game_obj.f_user and game_obj.c_user:
                game_obj.status = 'w1'
                game_obj.current_player = 'w'
    return True

def create_new_game_in_db(user_login, forced_game_id=None):
    import random, json
    db_session = SessionLocal()
    try:
        if forced_game_id is not None:
            existing_game = db_session.query(DBGame).filter(DBGame.game_id == forced_game_id).first()
            if not existing_game:
                new_db_game = DBGame(
                    game_id=forced_game_id,
                    f_user=user_login,
                    c_user=None,
                    status='unstarted',
                    board_state=json.dumps(pieces)
                )
                db_session.add(new_db_game)
                db_session.commit()
                new_game = Game(f_user=user_login, c_user=None, game_id=forced_game_id)
                with all_games_lock:
                    all_games_dict[forced_game_id] = new_game
                redis_client.set(f"game:{forced_game_id}:board_state", json.dumps(pieces))
                redis_client.delete(f"game:{forced_game_id}:moves")
                from Client.redis_base import set_move_status
                set_move_status(forced_game_id, "w1")
                db_session.close()
                return forced_game_id
            else:
                db_session.close()
                return existing_game.game_id
        while True:
            game_id_candidate = random.randint(1, 99999999)
            exists = db_session.query(DBGame).filter(DBGame.game_id == game_id_candidate).first()
            if not exists:
                break
        new_db_game = DBGame(
            game_id=game_id_candidate,
            f_user=user_login,
            c_user=None,
            status='unstarted',
            board_state=json.dumps(pieces)
        )
        db_session.add(new_db_game)
        db_session.commit()
        new_game = Game(f_user=user_login, c_user=None, game_id=game_id_candidate)
        with all_games_lock:
            all_games_dict[game_id_candidate] = new_game
        redis_client.set(f"game:{game_id_candidate}:board_state", json.dumps(pieces))
        redis_client.delete(f"game:{game_id_candidate}:moves")
        from Client.redis_base import set_move_status
        set_move_status(game_id_candidate, "w1")
        db_session.close()
        return game_id_candidate
    except:
        db_session.close()
        raise

def remove_game_in_db(game_id):
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if db_game:
        db_game.status = 'completed'
        db_session.commit()
    db_session.close()
    with all_games_lock:
        if game_id in all_games_dict:
            del all_games_dict[game_id]

def get_game_status_internally(game_id):
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if not db_game:
        db_session.close()
        return None
    status = db_game.status
    db_session.close()
    return status

def update_game_status_in_db(game_id, new_status):
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if db_game:
        db_game.status = new_status
        db_session.commit()
    db_session.close()
