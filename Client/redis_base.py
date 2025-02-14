import redis
import json

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)


def create_game_in_redis(game_id, f_user, c_user, board_state, status="unstarted"):
    key = f"game:{game_id}"
    game_data = {
        "f_user": f_user if f_user is not None else "",
        "c_user": c_user if c_user is not None else "",
        "board_state": board_state if board_state is not None else "",
        "status": status if status is not None else ""
    }
    redis_client.hset(key, mapping=game_data)


def update_game_status(game_id, new_status):
    """
    Обновляет статус игры.
    :param game_id: Идентификатор игры
    :param new_status: Новый статус (например, "Ход черных")
    """
    key = f"game:{game_id}"
    redis_client.hset(key, "status", new_status)


def get_game_data(game_id):
    """
    Получает данные игры из Redis.
    :param game_id: Идентификатор игры
    :return: Словарь с данными игры
    """
    key = f"game:{game_id}"
    data = redis_client.hgetall(key)
    return {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}


def add_move(game_id, move):
    """
    Добавляет новый ход в список ходов игры.
    :param game_id: Идентификатор игры
    :param move: Словарь с информацией о ходе (например, {"player": "user1", "from": {"x":0, "y":0}, "to": {"x":1, "y":1}})
    """
    key = f"game:{game_id}:moves"
    move_json = json.dumps(move)
    redis_client.rpush(key, move_json)


def get_game_moves(game_id):
    """
    Получает список ходов игры.
    :param game_id: Идентификатор игры
    :return: Список ходов (каждый ход – словарь)
    """
    key = f"game:{game_id}:moves"
    moves = redis_client.lrange(key, 0, -1)
    return [json.loads(move.decode('utf-8')) for move in moves]


if __name__ == "__main__":
    create_game_in_redis(game_id=1, f_user="user1", c_user="user2", board_state="initial_state", status="Ход белых")