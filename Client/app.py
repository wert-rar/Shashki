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


@app.route("/")
def home():
    return "Hello World!"


@app.route("/board")
def get_board():
    return render_template('board.html')


@app.route("/move", methods=["POST"])
def move():
    global current_player, pieces

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"status_": "e1", "pieces": pieces})

    new_pieces = data.get("pieces", pieces)

    if not new_pieces or not isinstance(new_pieces, list):
        current_status = "e1"
    else:
        # Вася ТРАХАЕТ Алёну ??????
        white_pieces = [p for p in pieces if p["color"] == 1]
        black_pieces = [p for p in pieces if p["color"] == 0]

        if (current_player == "w1" or current_player == "w4") and any(
                p not in white_pieces for p in new_pieces if p["color"] == 1):
            current_status = "w2"
        elif (current_player == "b1" or current_player == "b4") and any(
                p not in black_pieces for p in new_pieces if p["color"] == 0):
            current_status = "b2"
        else:
            captured = len(new_pieces) != len(pieces)
            pieces = new_pieces

            if all(p["color"] == 1 for p in pieces):
                current_status = "w3"
            elif all(p["color"] == 0 for p in pieces):
                current_status = "b3"
            else:
                if captured:
                    current_status = "w4" if (current_player == "w1" or current_player == "w4") else "b4"
                else:
                    current_status = "b1" if (current_player == "w1" or current_player == "w4") else "w1"

                current_player = current_status

    response = {
        "status_": current_status,
        "pieces": pieces
    }

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)