from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import random
import  Client.game as game

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
    "n" : "Ничья1",
    "e1": "Ошибка при запросе к серверу"
}

def get_piece_at(x, y):
    for piece in pieces:
        if piece['x'] == x and piece['y'] == y:
            return piece
    return None


def can_capture(piece):
    x, y = piece['x'], piece['y']
    possible_directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
    for dx, dy in possible_directions:
        mid_x, mid_y = x + dx // 2, y + dy // 2
        end_x, end_y = x + dx, y + dy
        captured_piece = get_piece_at(mid_x, mid_y)
        target_pos = get_piece_at(end_x, end_y)
        if (0 <= end_x < 8 and 0 <= end_y < 8 and
            captured_piece and captured_piece['color'] != piece['color'] and not target_pos):
            return True
    return False


def validate_move(new_pieces,current_player,pieces, end_turn_flag=False):

    if len(new_pieces) != len(pieces):
        return False

    moved_piece = None
    new_pos = None
    print('быстрая проверка на наличие изменений: ', new_pieces != pieces)

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
    captured = False

    if moved_piece.get('is_king', False):
        if abs_dx == abs_dy:
            step_x = dx // abs_dx
            step_y = dy // abs_dy
            captured_pieces = []
            for i in range(1, abs_dx):
                piece_at_pos = get_piece_at(moved_piece['x'] + i * step_x, moved_piece['y'] + i * step_y)
                if piece_at_pos:
                    if piece_at_pos['color'] == moved_piece['color']:
                        print('Путь блокирован')
                        return False
                    else:
                        captured_pieces.append(piece_at_pos)
            if len(captured_pieces) > 1:
                print('Путь блокирован более чем одной фигурой')
                return False
            elif captured_pieces:
                pieces.remove(captured_pieces[0])
                captured = True
        else:
            print('Дамка должна двигаться по диагонали')
            return False
    else:
        if abs_dx == 1 and abs_dy == 1:
            if (moved_piece['color'] == 0 and dy == -1) or (moved_piece['color'] == 1 and dy == 1):
                # Разрешенный ход
                pass
            else:
                print('Обычные пешки не могут ходить назад')
                return False
        elif abs_dx == 2 and abs_dy == 2:
            mid_x = (moved_piece['x'] + new_pos['x']) // 2
            mid_y = (moved_piece['y'] + new_pos['y']) // 2
            captured_piece = get_piece_at(mid_x, mid_y)
            if not captured_piece or captured_piece['color'] == moved_piece['color']:
                print('Невозможно съесть фигуру')
                return False
            pieces.remove(captured_piece)
            captured = True
        else:
            print('Ошибка с дистанцией')
            return False

    moved_piece['x'] = new_pos['x']
    moved_piece['y'] = new_pos['y']
    # Проверка на коронацию
    if not moved_piece.get('is_king', False):
        if (moved_piece['color'] == 0 and moved_piece['y'] == 0) or (
                moved_piece['color'] == 1 and moved_piece['y'] == 7):
            moved_piece['is_king'] = True

    if captured and can_capture(moved_piece) and not end_turn_flag:
        print('Дополнительное взятие возможно, ход остается тем же игроком')
        return 'continue'

    # Проверка на победу
    if not any(piece['color'] == 0 for piece in pieces):
        print(status_['b3'])
        return "b3"
    if not any(piece['color'] == 1 for piece in pieces):
        print(status_['w3'])
        return "w3"

    current_player = 'b' if current_player == 'w' else 'w'
    return True,pieces,current_player

@app.route("/move", methods=["POST"])
def move():
    global pieces, current_player
    new_pieces = request.json.get("pieces")
    game_id = request.json.get("game_id")
    user_id = request.json.get("user_id")

    pieces,current_player = game.pieces_and_current_player(game_id)

    result,pieces,current_player = validate_move(new_pieces,current_player,pieces)

    if result is True:
        current_status = f"{current_player}1"
    elif result == "w3" or result == "b3":
        current_status = result
    else:
        current_status = f"{current_player}2"
    return jsonify({"status_": current_status, "pieces": pieces})


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/board")
def get_board():
    return render_template('board.html')


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

    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM game WHERE status = 'waiting' AND (white_user IS NULL OR black_user IS NULL)")
        game = cur.fetchone()

        if game:
            session['game_id'] = game['id']
            if not game['white_user'] and not game['black_user']:
                if random.choice([True, False]):
                    cur.execute("UPDATE game SET white_user = ?, status = 'active' WHERE id = ?", (user_login, game['id']))
                    session['color'] = 'white'
                else:
                    cur.execute("UPDATE game SET black_user = ?, status = 'active' WHERE id = ?", (user_login, game['id']))
                    session['color'] = 'black'
            elif not game['white_user']:
                cur.execute("UPDATE game SET white_user = ?, status = 'active' WHERE id = ?", (user_login, game['id']))
                session['color'] = 'white'
            elif not game['black_user']:
                cur.execute("UPDATE game SET black_user = ?, status = 'active' WHERE id = ?", (user_login, game['id']))
                session['color'] = 'black'
        else:
            cur.execute("INSERT INTO game (status, white_user, black_user) VALUES ('waiting', ?, NULL)", (user_login,))
            game_id = cur.lastrowid
            session['game_id'] = game_id
            session['color'] = 'white'

        conn.commit()

        return render_template('waiting.html')



@app.route('/check_game_status')
def check_game_status():
    game_id = session.get('game_id')
    if not game_id:
        return jsonify({"status": "no_game"})

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM game WHERE id = ?", (game_id,))
        game = cur.fetchone()

    if not game:
        return jsonify({"status": "no_game"})

    if game['status'] == 'finished':
        session.pop('game_id', None)
        return jsonify({"status": "finished"})

    return jsonify({"status": game['status']})

if __name__ == "__main__":
    app.run(debug=True)
