from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

current_player = "w1"

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
    for piece, new_piece in zip(pieces, new_pieces):
    # если положение фигур не изменилось то значит ни одна фигура не сдвинута
        if new_pieces == pieces:
            print('Нет двинутых фигур')
            return False
    # иначе ищем подвинутую фигуру
    for piece, new_piece in zip(pieces,new_pieces):
        if piece['x'] != new_piece['x'] or piece['y'] != new_piece['y']:
            print(f'сдвинута фигура! c {piece} на {new_piece}')
            moved_piece = piece
            new_pos = new_piece
            break

    if moved_piece is None:
        print('Нет двинутых фигур')
        return False

    if (current_player[0] == "w" and moved_piece['color'] == 1) or (current_player[0] == "b" and moved_piece['color'] == 0):
        if (current_player[0] == "w" and moved_piece['color'] == 1) or (current_player[0] == "b" and moved_piece['color'] == 0):
            print('не тот цвет')
            return False

    dx = new_pos['x'] - moved_piece['x']
    dy = new_pos['y'] - moved_piece['y']

    if abs(dx) != 1 or abs(dy) != 1:
        print('ошибка с дистанцией')
        return False

    if get_piece_at(new_pos['x'], new_pos['y']):
        print('поле занято')
        return False
    print('сработало верно')
    return True


@app.route("/")
def home():
    return "Hello World!"


@app.route("/board")
def get_board():
    return render_template('board.html')


@app.route("/move", methods=["POST"])
def move():
    global pieces, current_player

    new_pieces = request.json.get("pieces")
    print('validate move :', validate_move(new_pieces))
    if validate_move(new_pieces):
        pieces = new_pieces
        current_player = "w1" if current_player not in ["w1","w2"] else "b1"
        return jsonify({"status_": current_player, "pieces": pieces})
    else:
        return jsonify({"status_": f"{current_player[0]}2", "pieces": pieces})


if __name__ == "__main__":
    app.run(debug=True)
