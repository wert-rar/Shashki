from flask import Flask, render_template, request, jsonify
from game import Game

app = Flask(__name__)

current_player = "w"

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

status_ = {
    "w1": "Ход белых",
    "b1": "Ход черных",
    "w2": "Нельзя двигать фигуру, сейчас ход белых",
    "b2": "Нельзя двигать фигуру, сейчас ход черных",
    "w3": "Победили белые",
    "b3": "Победили черные",
    "w4": "Белые продолжают ход",
    "b4": "Черные продолжают ход",
    "e1": "Ошибка при запросе к серверу"
}

def get_piece_at(x, y):
    for piece in pieces:
        if piece['x'] == x and piece['y'] == y:
            return piece
    return None


def validate_move(new_pieces):
    global pieces, current_player

    if len(new_pieces) != len(pieces):
        return False

    moved_piece = None
    new_pos = None
    print('быстрая проверка на наличие изменений: ', not (new_pieces == pieces))

    # иначе ищем подвинутую фигуру
    for piece, new_piece in zip(pieces, new_pieces):
        if piece['x'] != new_piece['x'] or piece['y'] != new_piece['y']:
            print(f'сдвинута фигура! c {piece} на {new_piece}')
            moved_piece = piece
            new_pos = new_piece
            break

    if moved_piece is None:
        return False

    if (current_player == "w" and moved_piece['color'] == 1) or (
            current_player == "b" and moved_piece['color'] == 0):
        return False

    # Проверка на занятость клетки
    if get_piece_at(new_pos['x'], new_pos['y']):
        print('Поле занято')
        return False

    dx = new_pos['x'] - moved_piece['x']
    dy = new_pos['y'] - moved_piece['y']
    abs_dx = abs(dx)
    abs_dy = abs(dy)

    if abs_dx == 1 and abs_dy == 1:
        pass  # Проверка на занятость уже выполнена ранее
    elif abs_dx == 2 and abs_dy == 2:
        mid_x = (moved_piece['x'] + new_pos['x']) // 2
        mid_y = (moved_piece['y'] + new_pos['y']) // 2
        captured_piece = get_piece_at(mid_x, mid_y)
        if not captured_piece or captured_piece['color'] == moved_piece['color']:
            print('Невозможно съесть фигуру')
            return False
        pieces.remove(captured_piece)
    else:
        print('Ошибка с дистанцией')
        return False

    # Обновляем позицию сдвинутой фигуры
    moved_piece['x'] = new_pos['x']
    moved_piece['y'] = new_pos['y']

    # Меняем очередь игрока после успешного хода
    current_player = 'b' if current_player == 'w' else 'w'
    return True


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/board")
def get_board():
    return render_template('board.html')


@app.route("/move", methods=["POST"])
def move():
    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400
    player_id = data.get("player_id")
    game_id = data.get("game_id")
    move = data.get("move")

    # Проверяем, что все необходимые данные переданы
    if not all([player_id, game_id, move]):
        return jsonify({"error": "Player ID, Game ID, and Move are required"}), 400

    # Ищем соответствующую игру
    game = next((g for g in Game.get_current_games() if g.game_id == game_id), None)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    # Проверка принадлежности игроку
    if player_id not in [game.f_user, game.c_user]:
        return jsonify({"error": "Invalid player"}), 403

    # Обработка хода
    success, message = game.make_move(player_id, move)
    if not success:
        return jsonify({"error": message}), 400

    # Возвращаем обновлённое состояние игры
    return jsonify({
        "message": message,
        "game_id": game.game_id,
        "player_id": player_id,
        "move": move,
        #можно будет возвращать актуальное состояние доски
    })


#Создаёт новую игру и добавляет её в список не начатых игр.
@app.route("/create_game", methods=["POST"])
def create_game():
    # Создаем новую игру без пользователей, добавляем в список не начатых игр.
    new_game = Game()
    return jsonify({"message": "Game created", "game_id": new_game.game_id})


#Пользователь присоединяется к текущей не начатой игре или создаёт новую.
@app.route("/join_game", methods=["POST"])
def join_game():
    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    game = Game.search_game(user_id)
    return jsonify({"message": "Joined game", "game_id": game.game_id, "f_user": game.f_user, "c_user": game.c_user})


#Конкретная игра завершается и удаляется из текущего списка игр.
@app.route("/end_game/<int:game_id>", methods=["POST"])
def end_game(game_id):
    Game.end_game(game_id)
    return jsonify({"message": f"Game {game_id} has ended"})


#Возвращает информацию о конкретной игре (кто является игроками и статус).
@app.route("/game_status/<int:game_id>", methods=["GET"])
def game_status(game_id):
    game = next((g for g in Game.current_games if g.game_id == game_id), None)
    if game:
        return jsonify({"game_id": game.game_id, "f_user": game.f_user, "c_user": game.c_user, "status": "in progress"})
    else:
        return jsonify({"error": "Game not found"}), 404


#Возвращает состояние доски для указанного игрока в игре.
@app.route("/display_board/<int:game_id>/<int:player_id>", methods=["GET"])
def display_board(game_id, player_id):
    game = next((g for g in Game.current_games if g.game_id == game_id), None)
    if game:
        board_state = game.display_board(player_id)
        return jsonify({"board": board_state})
    else:
        return jsonify({"error": "Game not found"}), 404



if __name__ == "__main__":
    app.run(debug=True)
