import time, threading
from base_postgres import SessionLocal, Game as DBGame

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

        self.white_time_remaining = 30
        self.black_time_remaining = 30
        self.last_update_time = None

        self.game_started = False

        self.lock = threading.Lock()

        self.f_player_loaded = False
        self.c_player_loaded = False

    def update_timers(self):
        # Обновляет оставшееся время для текущего игрока и проверяет, не истекло ли время
        if self.last_update_time is None:
            return
        now = time.time()
        elapsed = now - self.last_update_time
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
        else:
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
        # Возвращает цвет пользователя в игре
        if user_login == self.f_user:
            return 'w'
        elif user_login == self.c_user:
            return 'b'
        return None

    def update_pieces(self, new_pieces) -> bool:
        # Обновляет позиции фигур в игре
        with self.lock:
            if len(new_pieces) != len(self.pieces):
                return False
            self.pieces = new_pieces
            return True

    def update_status(self):
        # Обновляет статус игры в зависимости от текущего игрока
        if self.current_player == "w":
            self.status = "w1"
        else:
            self.status = "b1"

    def switch_turn(self):
        # Меняет текущего игрока и обновляет статус игры
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        self.update_status()
        self.last_update_time = time.time()

    def __str__(self):
        # Возвращает строковое представление игры
        return f"Game ID: {self.game_id}, White: {self.f_user}, Black: {self.c_user}"

def get_or_create_ephemeral_game(game_id):
    # Получает существующую игру по ID или создает временную игру, если она существует в базе данных
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
        all_games_dict[game_id] = new_game
        db_session.close()
        return new_game

def find_waiting_game_in_db():
    # Ищет игру, ожидающую второго игрока, в базе данных
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(
        DBGame.status == 'unstarted',
        DBGame.c_user.is_(None)
    ).first()
    db_session.close()
    return db_game

def update_game_with_user_in_db(game_id, user_login, color):
    # Присоединяет пользователя к игре в базе данных с указанным цветом
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

    return True

def create_new_game_in_db(user_login):
    # Создает новую игру в базе данных с указанным пользователем как белыми
    import random
    db_session = SessionLocal()
    while True:
        game_id_candidate = random.randint(1, 99999999)
        exists = db_session.query(DBGame).filter(DBGame.game_id == game_id_candidate).first()
        if not exists:
            break

    new_db_game = DBGame(
        game_id=game_id_candidate,
        f_user=user_login,
        c_user=None,
        status='unstarted'
    )
    db_session.add(new_db_game)
    db_session.commit()
    db_session.close()

    new_game = Game(f_user=user_login, c_user=None, game_id=game_id_candidate)
    with all_games_lock:
        all_games_dict[game_id_candidate] = new_game

    return game_id_candidate

def remove_game_in_db(game_id):
    # Удаляет игру из базы данных, устанавливая её статус как завершённую
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
    # Получает внутренний статус игры из базы данных
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if not db_game:
        db_session.close()
        return None
    status = db_game.status
    db_session.close()
    return status

def update_game_status_in_db(game_id, new_status):
    # Обновляет статус игры в базе данных
    db_session = SessionLocal()
    db_game = db_session.query(DBGame).filter(DBGame.game_id == game_id).first()
    if db_game:
        db_game.status = new_status
        db_session.commit()
    db_session.close()
