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

    for new_piece in new_pieces:
        old_piece = get_piece_at(new_piece['x'], new_piece['y'])
        if old_piece and old_piece != new_piece:
            if moved_piece:
                return False
            moved_piece = old_piece
            new_pos = new_piece

    if not moved_piece:
        return False

    dx = new_pos['x'] - moved_piece['x']
    dy = new_pos['y'] - moved_piece['y']

    if abs(dx) != 1 or abs(dy) != 1:
        return False

    if (current_player == "w1" and dy != 1) or (current_player == "b1" and dy != -1):
        return False

    if get_piece_at(new_pos['x'], new_pos['y']):
        return False

    if (current_player == "w1" and moved_piece['color'] != 1) or (current_player == "b1" and moved_piece['color'] != 0):
        return False

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

    if not new_pieces:
        return jsonify({"status": "e1", "message": status_["e1"]})

    if validate_move(new_pieces):
        pieces = new_pieces
        current_player = "b1" if current_player == "w1" else "w1"
        return jsonify({"status": current_player, "message": status_[current_player]})
    else:
        return jsonify({"status": f"{current_player[0]}2", "message": status_[f"{current_player[0]}2"]})


if __name__ == "__main__":
    app.run(debug=True)