from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/board")
def get_board():
    return render_template("board.html")


@app.route("/move", methods=["POST"])
def move():
    global current_player

    data = request.json("data")

    '''Movement logic'''

    current_player = "black" if current_player == "white" else "white"

    response = {"status": "ok",
                "current_player": current_player},
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
