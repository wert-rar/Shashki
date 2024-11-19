from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import random
from base import check_user_exists, \
    register_user, authenticate_user, get_user_by_login
from game import Game, find_waiting_game, update_game_with_user, get_game_status, create_new_game
import logging

current_games = {}
unstarted_games = {}

logging.basicConfig(level=logging.DEBUG)
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


def get_piece_at(pieces, x, y):
    for piece in pieces:
        if piece['x'] == x and piece['y'] == y:
            return piece
    return None


def can_capture(piece, pieces):
    x, y = piece['x'], piece['y']
    possible_directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
    for dx, dy in possible_directions:
        mid_x, mid_y = x + dx // 2, y + dy // 2
        end_x, end_y = x + dx, y + dy
        captured_piece = get_piece_at(pieces, mid_x, mid_y)
        target_pos = get_piece_at(pieces, end_x, end_y)
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
                        if not get_piece_at(pieces, new_x, new_y):
                            possible_moves.append((new_x, new_y))

        if not piece.get('is_king', False):
            for dx in [-2, 0, 2]:
                for dy in [-2, 2]:
                    if abs(dx) == abs(dy) and (dx != 0 and dy != 0):
                        mid_x, mid_y = x + dx // 2, y + dy // 2
                        new_x, new_y = x + dx, y + dy
                        if 0 <= new_x < 8 and 0 <= new_y < 8:
                            middle_piece = get_piece_at(pieces, mid_x, mid_y)
                            if middle_piece and middle_piece['color'] != color and not get_piece_at(pieces, new_x,
                                                                                                    new_y):
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

    if (current_player == "w" and moved_piece['color'] != 0) or (
            current_player == "b" and moved_piece['color'] != 1):
        return False

    if get_piece_at(pieces, new_pos['x'], new_pos['y']):
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
                piece_at_pos = get_piece_at(pieces, moved_piece['x'] + i * step_x, moved_piece['y'] + i * step_y)
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
            captured_piece = get_piece_at(pieces, mid_x, mid_y)
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

    if captured and can_capture(moved_piece, pieces) and not end_turn_flag:
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

    print(f'Текущий игрок: {current_player}')
    print(f'Фигуры до хода: {pieces}')
    print(f'Фигуры после хода: {new_pieces}')

    return True, pieces, current_player


@app.route("/")
def home():
    return render_template('home.html')


@app.route('/board/<int:game_id>/<user_login>')
def get_board(game_id, user_login):
    app.logger.debug(f"Game ID received: {game_id}")
    game = current_games.get(game_id)
    if not game:
        return jsonify({"error": "Invalid game ID"}), 404

    user_color = 'w' if user_login == game.f_user else 'b' if user_login == game.c_user else None
    if not user_color:
        return jsonify({"error": "User not part of this game"}), 403

    return render_template(
        'board.html',
        user_login=user_login,
        game_id=game_id,
        user_color=user_color,
        f_user=game.f_user,
        c_user=game.c_user
    )


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
            return redirect(url_for('home'))
        else:
            session['flash'] = 'Неправильное имя пользователя или пароль.'

    return render_template('login.html')


@app.route('/profile/<username>')
def profile(username):
    user = get_user_by_login(username)

    if user:
        total_games = user['wins'] + user['losses']
        return render_template('profile.html',
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
    session.pop('game_id', None)
    session['flash'] = 'Вы вышли из системы.'
    return redirect(url_for('home'))


@app.route('/start_game')
def start_game():
    user_login = session.get('user')
    if not user_login:
        return redirect(url_for('login'))

    game = find_waiting_game(unstarted_games)

    if game:
        color = 'w' if not game.f_user else 'b'
        try:
            update_game_with_user(game.game_id, user_login, color, current_games, unstarted_games)
            session['game_id'] = game.game_id
            session['color'] = color
        except ValueError as e:
            session['flash'] = str(e)
            return redirect(url_for('profile', username=user_login))
    else:
        game_id = create_new_game(user_login, unstarted_games, current_games)
        session['game_id'] = game_id
        session['color'] = 'w'

    app.logger.debug(f"Game created or joined: {session['game_id']} by {user_login} with color {session['color']}")

    return render_template('waiting.html', game_id=session.get('game_id'), user_login=user_login)


@app.route("/check_game_status", methods=["GET"])
def check_game_status_route():
    game_id = session.get('game_id')
    user_login = session.get('user')
    logging.debug(f"Checking game status, game_id: {game_id}, user_login: {user_login}")

    if not game_id:
        return jsonify({"status": "no_game"}), 404

    game_status = get_game_status(game_id, current_games, unstarted_games)
    if game_status:
        return jsonify(game_status)
    else:
        return jsonify({"status": "game_not_found"}), 404


@app.route("/move", methods=["POST"])
def move():
    data = request.json
    new_pieces = data.get("pieces")
    game_id = int(data.get("game_id"))
    user_login = session.get('user')

    game = current_games.get(game_id)

    if game is None:
        return jsonify({"error": "Invalid game ID"}), 400
    if user_login not in [game.f_user, game.c_user]:
        return jsonify({"error": "Invalid user ID"}), 403

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        logging.debug(f"User {user_login} attempted to move, but it's {current_player}'s turn.")
        return jsonify({"error": "Not your turn"}), 403

    result = validate_move(new_pieces, current_player, game.pieces)
    logging.debug(f"Validate move result: {result}")

    if isinstance(result, tuple):
        move_result, updated_pieces, new_current_player = result
    else:
        move_result = result

    if move_result is True:
        game.pieces = updated_pieces
        game.moves_count += 1
        game.switch_turn()
    elif move_result in ["w3", "b3", "n"]:
        game.pieces = updated_pieces
    elif move_result == 'continue':
        game.pieces = updated_pieces
    else:
        return jsonify({"error": "Invalid move"}), 400

    return jsonify({"status_": game.status, "pieces": game.pieces})


@app.route("/update_board", methods=["POST"])
def update_board():
    try:
        if not request.is_json:
            return jsonify({"error": "Request data must be in JSON format"}), 400

        data = request.get_json()
        game_id = data.get("game_id")

        game = current_games.get(int(game_id))
        if game is None:
            return jsonify({"error": "Invalid game ID"}), 400
        return jsonify({"status_": game.status, "pieces": game.pieces})
    except Exception as e:
        print("Exception:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/leave_game', methods=['POST'])
def leave_game():
    game_id = session.get('game_id')
    user_login = session.get('user')

    if not game_id or not user_login:
        return jsonify({"error": "No game to leave"}), 400

    game = current_games.get(game_id) or unstarted_games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    if game.f_user == user_login:
        game.f_user = None
    elif game.c_user == user_login:
        game.c_user = None
    else:
        return jsonify({"error": "User not part of the game"}), 400

    if game_id in current_games:
        if not game.f_user and not game.c_user:
            unstarted_games[game_id] = game
            del current_games[game_id]

    session.pop('game_id', None)
    session.pop('color', None)
    session['flash'] = 'Вы покинули игру.'
    return jsonify({"message": "Left the game successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True)
