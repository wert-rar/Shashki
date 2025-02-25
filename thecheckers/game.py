import time
import threading
import json
import asyncio
from thecheckers.base import *
from thecheckers.models import Games as DBGame
from thecheckers.redis_base import *
from thecheckers.base import *

all_games_lock = None
all_games_dict = {}

def get_all_games_lock():
    global all_games_lock
    current_loop = asyncio.get_running_loop()
    if (all_games_lock is None) or (getattr(all_games_lock, "_loop", None) != current_loop):
        all_games_lock = asyncio.Lock()
    return all_games_lock

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
        set_move_status(self.game_id, self.status)

    def __str__(self):
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"

async def get_or_create_ephemeral_game(game_id):
    lock = get_all_games_lock()
    async with lock:
        if game_id in all_games_dict:
            return all_games_dict[game_id]
        db_game = await get_active_db_game(game_id)
        if not db_game:
            return None
        new_game = Game(db_game.f_user, db_game.c_user, db_game.game_id)
        new_game.status = db_game.status
        all_games_dict[game_id] = new_game
        return new_game


async def find_waiting_game_in_db():
    return await find_waiting_game_db()


async def update_game_with_user_in_db(game_id, user_login, color):
    updated = await update_game_with_user_db(game_id, user_login, color)
    if not updated:
        return False
    game_obj = await get_or_create_ephemeral_game(game_id)
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


async def create_new_game_in_db(user_login, forced_game_id=None):
    import json
    global pieces
    new_game_id = await create_new_game_record(user_login, forced_game_id, pieces)
    new_game = Game(f_user=user_login, c_user=None, game_id=new_game_id)
    lock = get_all_games_lock()
    async with lock:
        all_games_dict[new_game_id] = new_game
    update_db_pieces(new_game_id, pieces)
    clear_game_moves(new_game_id)
    set_move_status(new_game_id, "w1")
    return new_game_id


async def remove_game_in_db(game_id):
    await remove_game_record(game_id)
    lock = get_all_games_lock()
    async with lock:
        if game_id in all_games_dict:
            del all_games_dict[game_id]

async def get_game_status_internally(game_id):
    return await get_game_status_db(game_id)

async def update_game_status_in_db(game_id, new_status):
    await update_game_status_db(game_id, new_status)
