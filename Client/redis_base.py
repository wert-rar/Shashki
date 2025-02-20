import redis
import json

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)

def create_game_in_redis(game_id, f_user, c_user, board_state, status="unstarted", move_status="w1"):
    key = f"game:{game_id}"
    game_data = {
        "f_user": f_user or "",             # Поле f_user – первый игрок
        "c_user": c_user or "",             # Поле c_user – второй игрок
        "board_state": board_state or "",   # Поле board_state – состояние доски
        "status": status or "",             # Поле status – статус игры
        "move_status": move_status or ""    # Поле move_status - статус ходов игроков
    }
    redis_client.hset(key, mapping=game_data)

# Обновляет значение поля "status" для указанной игры
def update_game_status(game_id, new_status):
    key = f"game:{game_id}"
    redis_client.hset(key, "status", new_status)

def set_move_status(game_id, move_status):
    key = f"game:{game_id}"
    redis_client.hset(key, "move_status", move_status)

def get_move_status(game_id):
    key = f"game:{game_id}"
    status = redis_client.hget(key, "move_status")
    return status.decode('utf-8') if status else None

# Возвращает словарь с полями: f_user, c_user, board_state и status
def get_game_data(game_id):
    key = f"game:{game_id}"
    data = redis_client.hgetall(key)
    return {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

# Ходы сохраняются в Redis в виде списка под ключом "game:<game_id>:moves"
def add_move(game_id, move):
    key = f"game:{game_id}:moves"
    redis_client.rpush(key, json.dumps(move))

# Функция для получения списка ходов игры
def get_game_moves(game_id):
    key = f"game:{game_id}:moves"
    moves = redis_client.lrange(key, 0, -1)
    return [json.loads(move.decode('utf-8')) for move in moves]

#Функция для очистки статуса хода игрока
def clear_move_status(game_id):
    key = f"game:{game_id}"
    redis_client.hdel(key, "move_status")
