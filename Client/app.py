from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import random
from base import check_user_exists, \
    register_user, authenticate_user, get_user_by_login
import uuid
from game import Game, find_waiting_game, update_game_with_user, get_game_status, create_new_game

app = Flask(__name__)
app.secret_key = 'superpupersecretkey'


status_ = {
    "w1": "Ход белых",
    "b1": "Ход черных",
    "w2": "Нельзя двигать фигуру, сейчас ход белых",
    "b2": "Нельзя двигать фигуру, сейчас ход черных",
    "w3": "Победили белые",
    "b3": "Победили черные",
    "w4": "Белые продолжают ход",
    "b4": "Черные продолжают ход",
    "n": "Ничья1",
    "e1": "Ошибка при запросе к серверу"
}

current_games = {
    1: Game(1, 0, 1),
    # str(uuid.uuid4()): ['pieces', 'current_player'],
}

unstarted_games = {}


def get_piece_at(pieces,x, y):
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


def check_draw(pieces):
    for piece in pieces:
        x, y, color = piece['x'], piece['y'], piece['color']
        possible_moves = []

        for dx in [-1, 0, 1]:
            for dy in [-1, 1]:
                if abs(dx) == abs(dy) and (dx != 0 and dy != 0):
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < 8 and 0 <= new_y < 8:
                        if not get_piece_at(pieces,new_x, new_y):
                            possible_moves.append((new_x, new_y))

        if not piece.get('is_king', False):
            for dx in [-2, 0, 2]:
                for dy in [-2, 2]:
                    if abs(dx) == abs(dy) and (dx != 0 and dy != 0):
                        mid_x, mid_y = x + dx // 2, y + dy // 2
                        new_x, new_y = x + dx, y + dy
                        if 0 <= new_x < 8 and 0 <= new_y < 8:
                            middle_piece = get_piece_at(mid_x, mid_y)
                            if middle_piece and middle_piece['color'] != color and not get_piece_at(new_x, new_y):
                                possible_moves.append((new_x, new_y))
        if possible_moves:
            return False
    return True


def validate_move(new_pieces, current_player, pieces, end_turn_flag=False):
    if len(new_pieces) != len(pieces):
        return False

    moved_piece = None
    new_pos = None
    print('быстрая проверка на наличие изменений: ', new_pieces != pieces)

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
    if not moved_piece.get('is_king', False):
        if (moved_piece['color'] == 0 and moved_piece['y'] == 0) or (
                moved_piece['color'] == 1 and moved_piece['y'] == 7):
            moved_piece['is_king'] = True

    if captured and can_capture(moved_piece) and not end_turn_flag:
        print('Дополнительное взятие возможно, ход остается тем же игроком')
        return 'continue'

    if not any(piece['color'] == 0 for piece in pieces):
        print(status_['b3'])
        return "b3"
    if not any(piece['color'] == 1 for piece in pieces):
        print(status_['w3'])
        return "w3"

    if check_draw(pieces):
        print(status_['n'])
        return "n"

    current_player = 'b' if current_player == 'w' else 'w'
    return True, pieces, current_player


@app.route("/move", methods=["POST"])
def move():
    data = request.json
    new_pieces = data.get("pieces")
    game_id = data.get("game_id")
    user_id = data.get("user_id")

    game = current_games.get(game_id)

    if game is None:
        return jsonify({"error": "Invalid game ID"}), 400

    current_player, current_pieces = game.pieces_and_current_player()

    result, updated_pieces = validate_move(new_pieces, current_player, current_pieces)

    if result is True:
        # Обновляем фигуры
        game.pieces['white' if current_player == game.f_user else 'black'] = updated_pieces
        game.moves_count += 1
        current_status = f"{current_player}1"
    elif result in ["w3", "b3"]:
        current_status = result
    else:
        current_status = f"{current_player}2"

    return jsonify({"status_": current_status, "pieces": updated_pieces})


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/board")
def get_board():
    return render_template('board.html', user_id=1, game_id=1, user_color="b")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        if not check_user_exists(user_login):
            register_user(user_login, user_password)
            session['flash'] = 'Пользователь успешно зарегистрирован!'
            return redirect(url_for('login'))
        else:
            session['flash'] = 'Такой пользователь уже зарегистрирован!'

    return render_template('register.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        user = authenticate_user(user_login, user_password)

        if user:
            session['flash'] = 'Успешный вход!'
            session['user'] = user_login
            return redirect(url_for('profile', username=user_login))
        else:
            session['flash'] = 'Неправильное имя пользователя или пароль.'

    return render_template('login.html')


@app.route('/profile/<username>')
def profile(username):
    user = get_user_by_login(username)

    if user:
        total_games = user['wins'] + user['losses']
        return render_template('profile.html',
                               user_id=user['user_id'],
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

    game = find_waiting_game()

    if game:
        session['game_id'] = game.game_id
        if not game.f_user and not game.c_user:
            if random.choice([True, False]):
                update_game_with_user(game.game_id, user_login, 'white')
                session['color'] = 'white'
            else:
                update_game_with_user(game.game_id, user_login, 'black')
                session['color'] = 'black'
        elif not game.f_user:
            update_game_with_user(game.game_id, user_login, 'white')
            session['color'] = 'white'
        elif not game.c_user:
            update_game_with_user(game.game_id, user_login, 'black')
            session['color'] = 'black'
    else:
        game_id = create_new_game(user_login)
        session['game_id'] = game_id
        session['color'] = 'white'

    return render_template('waiting.html')


def check_game_status(game_id):
    if not game_id:
        return jsonify({"status": "no_game"})

    game = get_game_status(game_id)

    if game:
        return jsonify({"status": game['status']})
    else:
        return jsonify({"status": "game_not_found"})


@app.route("/update_board", methods=["POST"])
def update_board():
    data = request.json
    status = data.get("status_")
    new_pieces = data.get("pieces")
    game_id = data.get("game_id")
    print(game_id)
    game = current_games.get(game_id)

    if game is None:
        return jsonify({"error": "Invalid game ID"}), 400

    try:
        valid_update = check_game_status(game_id)

        if valid_update:
            current_player, pieces = game.pieces_and_current_player()
            return jsonify({"status_": status, "pieces": pieces})
        else:
            return jsonify({"error": "Invalid update"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
