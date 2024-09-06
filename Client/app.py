from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from game import Game
import sqlite3

app = Flask(__name__)
app.secret_key = 'superpupersecretkey'

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
        pass
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

    moved_piece['x'] = new_pos['x']
    moved_piece['y'] = new_pos['y']

    current_player = 'b' if current_player == 'w' else 'w'
    return True


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        con = sqlite3.connect("../DataBase.db")
        cur = con.cursor()

        cur.execute("SELECT login FROM player WHERE login = ?", (user_login,))
        if cur.fetchone() is None:
            # Если пользователя нет, добавляем его в базу данных
            cur.execute("INSERT INTO player (login, password, rang) VALUES (?, ?, ?)", (user_login, user_password, 0))
            con.commit()
            session['flash'] = 'Пользователь успешно зарегистрирован!'
            con.close()
            # Перенаправляем на страницу входа
            return redirect(url_for('login'))
        else:
            session['flash'] = 'Такой пользователь уже зарегистрирован!'

        con.close()

    return render_template('register.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        con = sqlite3.connect("../DataBase.db")
        cur = con.cursor()

        cur.execute("SELECT * FROM player WHERE login = ? AND password = ?", (user_login, user_password))
        user = cur.fetchone()

        if user:
            session['flash'] = 'Успешный вход!'
            session['user'] = user_login
            return redirect(url_for('profile', username=user_login))
        else:
            session['flash'] = 'Неправильное имя пользователя или пароль.'

        con.close()

    return render_template('login.html')

def get_db_connection():
    conn = sqlite3.connect('../DataBase.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/profile/<username>')
def profile(username):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM player WHERE login = ?", (username,))
    user = cur.fetchone()

    conn.close()

    if user:
        total_games = user['wins'] + user['losses']
        return render_template('profile.html',
                               user_id=user['id'],
                               user_login=user['login'],
                               rang=user['rang'],
                               total_games=total_games,
                               wins=user['wins'],
                               losses=user['losses'])
    else:
        return 'Пользователь не найден', 404

@app.route("/logout")
def logout():
    session.pop('user', None)
    session['flash'] = 'Вы вышли из системы.'
    return redirect(url_for('home'))


@app.route('/start_game')
def start_game():
    user_login = session.get('user')
    if not user_login:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM game WHERE status = 'waiting'")
    game = cur.fetchone()

    if game:
        session['game_id'] = game['id']
        cur.execute("UPDATE game SET status = 'active' WHERE id = ?", (game['id'],))
        cur.execute("INSERT INTO game_user (game_id, user_login) VALUES (?, ?)", (game['id'], user_login))
        conn.commit()
    else:
        cur.execute("INSERT INTO game (status) VALUES ('waiting')")
        game_id = cur.lastrowid
        session['game_id'] = game_id
        cur.execute("INSERT INTO game_user (game_id, user_login) VALUES (?, ?)", (game_id, user_login))
        conn.commit()

    conn.close()
    return render_template('waiting.html')

app.route('/check_game_status')
def check_game_status():
    game_id = session.get('game_id')
    if not game_id:
        return jsonify({"status": "no_game"})

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM game WHERE id = ?", (game_id,))
    game = cur.fetchone()
    conn.close()

    if not game:
        return jsonify({"status": "no_game"})

    return jsonify({"status": game['status'], "game_id": game_id, "user_id": session.get('user')})


@app.route('/board/<int:game_id>/<user_id>')
def get_board(game_id, user_id):
    if session.get('game_id') != game_id or session.get('user') != user_id:
        return redirect(url_for('home'))
    return render_template('board.html', game_id=game_id, user_id=user_id)


@app.route('/make_move', methods=['POST'])
def make_move():
    user_id = session.get('user')
    game_id = session.get('game_id')

    if not user_id or not game_id:
        return jsonify({"status": "error", "message": "Invalid session"})

    data = request.json
    move = data.get('move')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM game_user WHERE game_id = ? AND user_login = ?", (game_id, user_id))
    if not cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "User not in game"})

    cur.execute("INSERT INTO moves (game_id, user_login, move) VALUES (?, ?, ?)", (game_id, user_id, move))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})


@app.route('/get_moves')
def get_moves():
    game_id = session.get('game_id')
    if not game_id:
        return jsonify({"status": "error", "message": "No game in session"})

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_login, move FROM moves WHERE game_id = ?", (game_id,))
    moves = cur.fetchall()
    conn.close()

    return jsonify([{"user": move["user_login"], "move": move["move"]} for move in moves])




if __name__ == "__main__":
    app.run(debug=True)
