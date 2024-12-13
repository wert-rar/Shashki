from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, flash
from base import check_user_exists, register_user, authenticate_user, get_user_by_login, update_user_rank, update_user_stats, create_tables
from game import find_waiting_game, update_game_with_user, get_game_status, create_new_game
import logging, subprocess, hmac, hashlib, itertools, threading, time

current_games = {}
unstarted_games = {}
completed_games = {}

ghost_counter = itertools.count(1)
ghost_lock = threading.Lock()

logging.basicConfig(level=logging.DEBUG)

create_tables()

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
    "n": "Ничья",
    "e1": "Ошибка при запросе к серверу"
}


def get_piece_at(pieces, x, y):
    for piece in pieces:
        if piece['x'] == x and piece['y'] == y:
            return piece
    return None


def can_capture(piece, pieces):
    x, y = piece['x'], piece['y']
    moves = []
    if piece.get('is_king', False):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in directions:
            opponent_found = False
            captured_x, captured_y = None, None
            step = 1
            while True:
                curr_x = x + dx * step
                curr_y = y + dy * step
                if not (0 <= curr_x < 8 and 0 <= curr_y < 8):
                    break
                curr_piece = get_piece_at(pieces, curr_x, curr_y)
                if curr_piece:
                    if curr_piece['color'] != piece['color'] and not opponent_found:
                        opponent_found = True
                        captured_x, captured_y = curr_x, curr_y
                    else:
                        break
                elif opponent_found:
                    moves.append({'x': curr_x, 'y': curr_y})
                step += 1
    else:
        possible_directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
        for dx, dy in possible_directions:
            mid_x, mid_y = x + dx // 2, y + dy // 2
            end_x, end_y = x + dx, y + dy
            captured_piece = get_piece_at(pieces, mid_x, mid_y)
            target_pos = get_piece_at(pieces, end_x, end_y)
            if (0 <= end_x < 8 and 0 <= end_y < 8 and
                    captured_piece and captured_piece['color'] != piece['color'] and not target_pos):
                moves.append({'x': end_x, 'y': end_y})
    return moves


def can_move(piece, pieces):
    x, y = piece['x'], piece['y']
    moves = []
    if piece.get('is_king', False):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in directions:
            step = 1
            while True:
                new_x = x + dx * step
                new_y = y + dy * step
                if not (0 <= new_x < 8 and 0 <= new_y < 8):
                    break
                if not get_piece_at(pieces, new_x, new_y):
                    moves.append({'x': new_x, 'y': new_y})
                else:
                    break
                step += 1
    else:
        if piece['color'] == 0:
            directions = [(-1, -1), (1, -1)]
        else:
            directions = [(-1, 1), (1, 1)]
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < 8 and 0 <= new_y < 8 and not get_piece_at(pieces, new_x, new_y):
                moves.append({'x': new_x, 'y': new_y})
    return moves


def get_possible_moves(pieces, color, must_capture_piece=None):
    all_moves = {}
    for piece in pieces:
        if piece['color'] != color:
            continue

        if must_capture_piece and (piece['x'], piece['y']) != (must_capture_piece['x'], must_capture_piece['y']):
            continue

        capture_moves = can_capture(piece, pieces)
        if must_capture_piece:
            if capture_moves:
                all_moves[(piece['x'], piece['y'])] = capture_moves
        else:
            normal_moves = can_move(piece, pieces)
            all_moves[(piece['x'], piece['y'])] = capture_moves + normal_moves
    return all_moves


def can_player_move(pieces, color):
    moves = get_possible_moves(pieces, color)
    return any(moves.values())


def check_draw(pieces):
    if can_player_move(pieces, 0):
        return False
    if can_player_move(pieces, 1):
        return False
    app.logger.debug("Ничья: нет возможных ходов для любых фигур.")
    return True


def is_all_kings(pieces):
    for piece in pieces:
        if not piece.get('is_king', False):
            return False
    return True


def finalize_game(game, user_login):
    if game.status == 'w3':
        winner_color = 'w'
    elif game.status == 'b3':
        winner_color = 'b'
    elif game.status == 'n':
        winner_color = None
    else:
        winner_color = None

    user_color = game.user_color(user_login)

    if winner_color is None:
        result_move = 'draw'
        points_gained = 5
    else:
        if winner_color == user_color:
            result_move = 'win'
            points_gained = 10
        else:
            result_move = 'lose'
            points_gained = 0

    if not getattr(game, 'rank_updated', False):
        opponent_login = game.f_user if game.f_user != user_login else game.c_user
        user_is_ghost = user_login.startswith('ghost')
        opponent_is_ghost = opponent_login.startswith('ghost')

        if not user_is_ghost:
            if result_move == 'win':
                update_user_rank(user_login, points_gained)
                update_user_stats(user_login, wins=1)
                if not opponent_is_ghost:
                    update_user_stats(opponent_login, losses=1)
            elif result_move == 'lose':
                update_user_stats(user_login, losses=1)
            elif result_move == 'draw':
                update_user_rank(user_login, points_gained)
                if not opponent_is_ghost:
                    update_user_rank(opponent_login, points_gained)
                update_user_stats(user_login, draws=1)
                if not opponent_is_ghost:
                    update_user_stats(opponent_login, draws=1)

        game.rank_updated = True

    remove_game(game.game_id)
    session.pop('game_id', None)
    session.pop('color', None)

    return result_move, points_gained


def validate_move(selected_piece, new_pos, current_player, pieces, game):
    x, y = selected_piece['x'], selected_piece['y']
    dest_x, dest_y = new_pos['x'], new_pos['y']
    color = 0 if current_player == 'w' else 1

    if game.must_capture_piece:
        valid_moves = get_possible_moves(pieces, color, must_capture_piece=game.must_capture_piece)
    else:
        valid_moves = get_possible_moves(pieces, color)

    piece_moves = valid_moves.get((x, y), [])

    if not any(move['x'] == dest_x and move['y'] == dest_y for move in piece_moves):
        return {'move_result': 'invalid'}

    new_pieces = [piece.copy() for piece in pieces]

    captured = False
    captured_pieces = []
    moved_piece = None

    if abs(dest_x - x) > 1:
        dx = 1 if dest_x > x else -1
        dy = 1 if dest_y > y else -1
        current_x, current_y = x + dx, y + dy
        while current_x != dest_x and current_y != dest_y:
            piece_at_square = get_piece_at(new_pieces, current_x, current_y)
            if piece_at_square and piece_at_square['color'] != selected_piece['color']:
                new_pieces.remove(piece_at_square)
                captured = True
                captured_pieces.append({'x': current_x, 'y': current_y})
                break
            elif piece_at_square:
                break
            current_x += dx
            current_y += dy

    promotion_occurred = False

    for piece in new_pieces:
        if piece['x'] == x and piece['y'] == y:
            piece['x'] = dest_x
            piece['y'] = dest_y
            moved_piece = piece
            if not piece.get('is_king', False):
                if (piece['color'] == 0 and piece['y'] == 0) or (
                        piece['color'] == 1 and piece['y'] == 7):
                    piece['is_king'] = True
                    piece['mode'] = 'k'
                    promotion_occurred = True
            break

    if captured:
        capture_moves = can_capture(moved_piece, new_pieces)
        if capture_moves:
            game.must_capture_piece = moved_piece.copy()
            return {
                'move_result': 'continue_capture',
                'new_pieces': new_pieces,
                'captured': True,
                'captured_pieces': captured_pieces,
                'multiple_capture': True
            }
        else:
            game.must_capture_piece = None
    else:
        game.must_capture_piece = None

    return {
        'move_result': 'valid',
        'new_pieces': new_pieces,
        'captured': captured,
        'captured_pieces': captured_pieces,
        'multiple_capture': False,
        'promotion': promotion_occurred
    }


def remove_game(game_id):
    if game_id in current_games:
        completed_games[game_id] = current_games.pop(game_id)
        app.logger.debug(f"Игра {game_id} перемещена из current_games в completed_games.")
    elif game_id in unstarted_games:
        completed_games[game_id] = unstarted_games.pop(game_id)
        app.logger.debug(f"Игра {game_id} перемещена из unstarted_games в completed_games.")


@app.route("/")
def home():
    user_login = session.get('user')
    user_is_registered = False
    if user_login and not user_login.startswith('ghost'):
        user = get_user_by_login(user_login)
        if user:
            user_is_registered = True
    return render_template('home.html', user_is_registered=user_is_registered)


@app.route('/board/<int:game_id>/<user_login>')
def get_board(game_id, user_login):
    app.logger.debug(f"Game ID received: {game_id}")
    game = current_games.get(game_id) or completed_games.get(game_id) or unstarted_games.get(game_id)
    if not game:
        abort(404)

    user_color = 'w' if user_login == game.f_user else 'b' if user_login == game.c_user else None
    if not user_color:
        abort(403)

    opponent_login = game.c_user if user_login == game.f_user else game.f_user

    return render_template(
        'board.html',
        user_login=user_login,
        game_id=game_id,
        user_color=user_color,
        opponent_login=opponent_login,
        f_user=game.f_user,
        c_user=game.c_user
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        if user_login.lower().startswith('ghost'):
            flash('Невозможно использовать имя, начинающееся с ghost.', 'error')
            return redirect(url_for('register'))

        if not check_user_exists(user_login):
            register_user(user_login, user_password)
            flash('Пользователь успешно зарегистрирован!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Такой пользователь уже зарегистрирован!', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        user = authenticate_user(user_login, user_password)

        if user:
            session['user'] = user_login
            flash('Успешный вход!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Неправильное имя пользователя или пароль.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/profile/<username>')
def profile(username):
    user = get_user_by_login(username)
    if username.startswith('ghost'):
        abort(403)
    if user:
        total_games = user['wins'] + user['losses'] + user['draws']

        current_user = session.get('user')
        is_own_profile = (username == current_user)
        in_game = False
        game_id = None

        if current_user and session.get('game_id'):
            try:
                game_id_int = int(session.get('game_id'))
                game = current_games.get(game_id_int) or completed_games.get(game_id_int) or unstarted_games.get(game_id_int)
                if game and current_user in [game.f_user, game.c_user]:
                    if game.f_user and game.c_user and game.status not in ['w3', 'b3', 'n']:
                        in_game = True
                        game_id = game_id_int
                    else:
                        in_game = False
            except (ValueError, TypeError):
                app.logger.warning(f"Некорректный game_id в сессии: {session.get('game_id')}")
                in_game = False

        return render_template('profile.html',
                               profile_user_login=user['login'],
                               rang=user['rang'],
                               total_games=total_games,
                               wins=user['wins'],
                               losses=user['losses'],
                               draws=user['draws'],
                               is_own_profile=is_own_profile,
                               in_game=in_game,
                               game_id=game_id,
                               current_user_login=current_user)
    else:
        abort(404)


@app.route("/logout")
def logout():
    session.pop('user', None)
    session.pop('game_id', None)
    session.pop('color', None)
    session['flash'] = 'Вы вышли из системы.'
    return redirect(url_for('home'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.route('/trigger_error')
def trigger_error():
    abort(500)


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Ошибка 500: {e}")
    return render_template('500.html'), 500


@app.route('/start_game')
def start_game():
    user_login = session.get('user')
    if not user_login:
        with ghost_lock:
            ghost_num = next(ghost_counter)
            ghost_username = f"ghost{ghost_num}"
        session['user'] = ghost_username
        session['is_ghost'] = True
    elif user_login.startswith('ghost'):
        session['is_ghost'] = True
    else:
        session['is_ghost'] = False

    game_id = session.get('game_id')
    if game_id:
        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            session.pop('game_id', None)
            session.pop('color', None)
            app.logger.warning(f"Некорректный game_id в сессии: {game_id}")
            game_id_int = None

        game = current_games.get(game_id_int) or completed_games.get(game_id_int) or unstarted_games.get(game_id_int) if game_id_int else None
        if game and user_login in [game.f_user, game.c_user]:
            if game.status in ['w3', 'b3', 'n']:
                session.pop('game_id', None)
                session.pop('color', None)

                new_game_id = create_new_game(user_login, unstarted_games, current_games)
                if new_game_id:
                    session['game_id'] = new_game_id
                    session['color'] = 'w'
                    app.logger.debug(f"New game created after finished game: {new_game_id} for {user_login}")
                    return render_template('waiting.html', game_id=new_game_id, user_login=user_login)
                else:
                    session['flash'] = 'Не удалось начать новую игру.'
                    return redirect(url_for('home'))
            else:
                if game.f_user and game.c_user:
                    return redirect(url_for('get_board', game_id=game_id_int, user_login=user_login))
                else:
                    return render_template('waiting.html', game_id=game_id_int, user_login=user_login)

    game = find_waiting_game(unstarted_games)

    if game:
        color = 'w' if not game.f_user else 'b'
        try:
            updated = update_game_with_user(game.game_id, user_login, color, current_games, unstarted_games)
            if not updated:
                new_game_id = create_new_game(user_login, unstarted_games, current_games)
                if new_game_id:
                    session['game_id'] = new_game_id
                    session['color'] = 'w'
                    app.logger.debug(f"New game created after failed join: {new_game_id} for {user_login}")
                    return render_template('waiting.html', game_id=new_game_id, user_login=user_login)
                else:
                    session['flash'] = 'Не удалось создать или присоединиться к игре.'
                    return redirect(url_for('home'))
            session['game_id'] = game.game_id
            session['color'] = color
        except ValueError as e:
            session['flash'] = str(e)
            return redirect(url_for('home'))
    else:
        game_id = create_new_game(user_login, unstarted_games, current_games)
        if not game_id:
            session['flash'] = 'Не удалось создать игру.'
            return redirect(url_for('home'))
        session['game_id'] = game_id
        session['color'] = 'w'

    app.logger.debug(f"Game created or joined: {session['game_id']} by {user_login} with color {session['color']}")

    game = current_games.get(session['game_id']) or unstarted_games.get(session['game_id'])
    if game and game.f_user and game.c_user:
        return redirect(url_for('get_board', game_id=session['game_id'], user_login=user_login))
    else:
        return render_template('waiting.html', game_id=session.get('game_id'), user_login=user_login)


@app.route("/check_game_status", methods=["GET"])
def check_game_status_route():
    game_id = session.get('game_id')
    user_login = session.get('user')

    if not game_id:
        return jsonify({"status": "no_game"}), 404

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        app.logger.warning(f"Некорректный game_id в check_game_status: {game_id}")
        return jsonify({"status": "invalid_game_id"}), 400

    game = current_games.get(game_id_int) or completed_games.get(game_id_int) or unstarted_games.get(game_id_int)
    if not game:
        return jsonify({"status": "game_not_found"}), 404

    if game.status in ['w3', 'b3', 'n']:
        response = {
            'status': game.status,
            'current_user': user_login,
            'game_id': game_id_int
        }
    else:
        response = get_game_status(game_id_int, current_games, unstarted_games)
        if response['status'] == 'active':
            response['current_user'] = user_login
            response['game_id'] = game_id_int
        elif response['status'] == 'waiting':
            response['current_user'] = user_login
            response['game_id'] = game_id_int
        else:
            response['current_user'] = user_login
            response['game_id'] = game_id_int

    return jsonify(response)


@app.route("/move", methods=["POST"])
def move():
    data = request.json
    selected_piece = data.get("selected_piece")
    new_pos = data.get("new_pos")
    game_id = data.get("game_id")
    user_login = session.get('user')

    if not game_id:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int)
    if not game:
        return jsonify({"error": "Invalid game ID"}), 400
    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        logging.debug(f"User {user_login} attempted to move, but it's {current_player}'s turn.")
        return jsonify({"error": "Not your turn"}), 403

    with game.lock:
        result = validate_move(selected_piece, new_pos, current_player, game.pieces, game)
        logging.debug(f"Validate move result: {result}")

        if result['move_result'] == 'invalid':
            return jsonify({"error": "Invalid move"}), 400

        move_record = {
            'player': game.f_user if current_player == 'w' else game.c_user,
            'from': {'x': selected_piece['x'], 'y': selected_piece['y']},
            'to': {'x': new_pos['x'], 'y': new_pos['y']},
            'captured': result['captured'],
            'captured_pieces': result.get('captured_pieces', []),
            'promotion': result.get('promotion', False)
        }
        game.move_history.append(move_record)

        game.update_timers()

        if game.status in ['w3', 'b3', 'n']:
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": game.status,
                "pieces": game.pieces,
                "white_time": max(int(game.white_time_remaining), 0),
                "black_time": max(int(game.black_time_remaining), 0),
                "move_history": game.move_history,
                "result": result_move,
                "points_gained": points_gained
            }
            return jsonify(response_data)

        if result['move_result'] == 'continue_capture':
            game.pieces = result['new_pieces']
            game.status = f"{current_player}4"
            return jsonify({"status_": game.status, "pieces": game.pieces, "move_history": game.move_history, "multiple_capture": True})
        elif result['move_result'] == 'valid':
            game.pieces = result['new_pieces']
            game.moves_count += 1
            game.switch_turn()
        else:
            return jsonify({"error": "Invalid move"}), 400

        if is_all_kings(game.pieces):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {"status_": "n", "pieces": game.pieces, "move_history": game.move_history,
                             "result": result_move, "points_gained": points_gained}
            return jsonify(response_data)

        if check_draw(game.pieces):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {"status_": "n", "pieces": game.pieces, "move_history": game.move_history,
                             "result": result_move, "points_gained": points_gained}
            return jsonify(response_data)

        opponent_color = 'b' if current_player == 'w' else 'w'
        opponent_pieces = [p for p in game.pieces if p['color'] == (0 if opponent_color == 'w' else 1)]

        if not opponent_pieces:
            game.status = f"{current_player}3"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {"status_": game.status, "pieces": game.pieces, "move_history": game.move_history,
                             "result": result_move, "points_gained": points_gained}
            return jsonify(response_data)

        if not can_player_move(game.pieces, 0 if opponent_color == 'w' else 1):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {"status_": "n", "pieces": game.pieces, "move_history": game.move_history,
                             "result": result_move, "points_gained": points_gained}
            return jsonify(response_data)

        return jsonify({"status_": game.status, "pieces": game.pieces, "move_history": game.move_history})


@app.route("/update_board", methods=["POST"])
def update_board():
    try:
        if not request.is_json:
            return jsonify({"error": "Request data must be in JSON format"}), 400

        data = request.get_json()
        game_id = data.get("game_id")
        user_login = session.get('user')

        if game_id is None:
            return jsonify({"error": "Game ID is required"}), 400

        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            app.logger.warning(f"Некорректный game_id: {game_id}")
            return jsonify({"error": "Invalid game ID"}), 400

        game = current_games.get(game_id_int) or completed_games.get(game_id_int) or unstarted_games.get(game_id_int)
        if not game:
            return jsonify({"error": "Invalid game ID"}), 400

        user_color = game.user_color(user_login)
        game.update_timers()

        response_data = {
            "status_": game.status,
            "pieces": game.pieces,
            "white_time": max(int(game.white_time_remaining), 0),
            "black_time": max(int(game.black_time_remaining), 0),
            "move_history": game.move_history
        }

        if game.draw_offer:
            response_data["draw_offer"] = game.draw_offer

        if game.draw_response:
            if game.draw_response['to'] == user_color:
                response_data['draw_response'] = game.draw_response['response']
                game.draw_response = None

        if game.status in ['w3', 'b3', 'n']:
            result_move, points_gained = finalize_game(game, user_login)
            response_data['points_gained'] = points_gained
            response_data['result'] = result_move

        return jsonify(response_data)
    except Exception as e:
        app.logger.error(f"Exception in update_board: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/give_up", methods=["POST"])
def give_up_route():
    try:
        data = request.get_json()
        game_id = data.get("game_id")
        user_login = data.get("user_login")

        if not game_id or not user_login:
            return jsonify({"error": "Недостаточно данных для сдачи"}), 400

        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid game ID"}), 400

        game = current_games.get(game_id_int) or unstarted_games.get(game_id_int)
        if not game:
            return jsonify({"error": "Игра не найдена"}), 404

        if user_login not in [game.f_user, game.c_user]:
            abort(403)

        user_color = 'w' if user_login == game.f_user else 'b'

        if user_color == 'w':
            game.status = 'b3'
        else:
            game.status = 'w3'

        result_move, points_gained = finalize_game(game, user_login)
        response = {
            "status_": game.status,
            "pieces": game.pieces,
            "result": result_move,
            "points_gained": points_gained
        }

        return jsonify(response), 200

    except Exception as e:
        app.logger.error(f"Ошибка при сдаче: {str(e)}")
        return jsonify({"error": "Произошла ошибка при сдаче."}), 500


@app.route('/leave_game', methods=['POST'])
def leave_game():
    game_id = session.get('game_id')
    user_login = session.get('user')

    if not game_id or not user_login:
        return jsonify({"error": "No game to leave"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int) or unstarted_games.get(game_id_int)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    if game.f_user == user_login:
        game.f_user = None
    elif game.c_user == user_login:
        game.c_user = None
    else:
        abort(403)

    if game.f_user is None and game.c_user is None:
        remove_game(game_id_int)

    session.pop('game_id', None)
    session.pop('color', None)
    session['flash'] = 'Вы покинули игру.'
    return jsonify({"message": "Left the game successfully"}), 200


@app.route("/offer_draw", methods=["POST"])
def offer_draw():
    data = request.json
    game_id = data.get("game_id")
    user_login = session.get('user')

    if game_id is None:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int) or unstarted_games.get(game_id_int)
    if not game:
        return jsonify({"error": "Игра не найдена"}), 404

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    user_color = 'w' if user_login == game.f_user else 'b'

    if game.draw_offer:
        return jsonify({"error": "Партия уже на рассмотрении"}), 400

    game.draw_offer = user_color
    app.logger.debug(f"Пользователь {user_login} предложил ничью в игре {game_id_int}")

    return jsonify({"message": "Предложение ничьей отправлено"}), 200


@app.route("/respond_draw", methods=["POST"])
def respond_draw_route():
    data = request.json
    game_id = data.get("game_id")
    user_login = session.get('user')
    response = data.get("response")

    if game_id is None:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int) or unstarted_games.get(game_id_int)
    if not game:
        return jsonify({"error": "Игра не найдена"}), 404

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    user_color = 'w' if user_login == game.f_user else 'b'

    if not game.draw_offer:
        return jsonify({"error": "Нет активных предложений ничьей"}), 400

    if game.draw_offer == user_color:
        return jsonify({"error": "Вы уже предложили ничью"}), 400

    if response == "accept":
        game.status = "n"
        game.draw_response = {'response': 'accept', 'to': game.draw_offer}
        app.logger.debug(f"Пользователь {user_login} принял ничью в игре {game_id_int}")
        game.draw_offer = None
    elif response == "decline":
        game.draw_response = {'response': 'decline', 'to': game.draw_offer}
        app.logger.debug(f"Пользователь {user_login} отклонил ничью в игре {game_id_int}")
        game.draw_offer = None
    else:
        return jsonify({"error": "Неверный ответ"}), 400

    if game.status == "n":
        result_move, points_gained = finalize_game(game, user_login)
        response_data = {
            "status_": game.status,
            "pieces": game.pieces,
            "result": result_move,
            "points_gained": points_gained
        }
        return jsonify(response_data), 200

    return jsonify({"status_": game.status, "pieces": game.pieces}), 200


@app.route("/get_possible_moves", methods=["POST"])
def get_possible_moves_route():
    data = request.json
    selected_piece = data.get("selected_piece")
    game_id = data.get("game_id")
    user_login = session.get('user')

    if game_id is None:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int)
    if game is None:
        game = completed_games.get(game_id_int)
        if game is None:
            return jsonify({"error": "Invalid game ID"}), 400
        else:
            return jsonify({"error": "Game has already ended"}), 400

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        logging.debug(f"User {user_login} attempted to get moves, but it's {current_player}'s turn.")
        return jsonify({"error": "Not your turn"}), 403

    x, y = selected_piece['x'], selected_piece['y']
    color = 0 if current_player == 'w' else 1
    moves = []

    if game.must_capture_piece:
        if (x, y) == (game.must_capture_piece['x'], game.must_capture_piece['y']):
            valid_moves = get_possible_moves(game.pieces, color, must_capture_piece=game.must_capture_piece)
            moves = valid_moves.get((x, y), [])
    else:
        valid_moves = get_possible_moves(game.pieces, color)
        moves = valid_moves.get((x, y), [])

    return jsonify({"moves": moves})


@app.route('/api/profile/<username>', methods=['GET'])
def api_profile(username):
    if username.startswith('ghost'):
        return jsonify({"error": "Профиль не доступен"}), 403
    user = get_user_by_login(username)
    if user:
        return jsonify({
            "user_login": user['login'],
            "rang": user['rang'],
            "wins": user['wins'],
            "losses": user['losses'],
            "draws": user['draws'],
            "total_games": user['wins'] + user['losses'] + user['draws']
        })
    else:
        return jsonify({"error": "Пользователь не найден"}), 404


@app.route('/hook', methods=['POST'])
def webhook():
    payload = request.data
    signature = request.headers.get('X-Hub-Signature-256', '')
    SECRET = b'superpupersecretkey'

    if not signature.startswith('sha256='):
        return "Invalid signature header", 400

    sha_name, signature_hash = signature.split('=')
    computed_hash = hmac.new(SECRET, payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature_hash, computed_hash):
        return "Invalid secret", 403

    try:
        output = subprocess.check_output(
            ["git", "-C", "/home/j/j0mutyp2/thesashki.ru", "pull", "origin", "main"],
            stderr=subprocess.STDOUT
        )
        return "OK: " + output.decode('utf-8'), 200
    except subprocess.CalledProcessError as e:
        return "Git pull failed:\n" + e.output.decode('utf-8'), 500

@app.route("/start_singleplayer")
def start_singleplayer():
    user_login = session.get('user')
    if not user_login:
        with ghost_lock:
            ghost_num = next(ghost_counter)
            ghost_username = f"ghost{ghost_num}"
        session['user'] = ghost_username
        session['is_ghost'] = True
    else:
        session['is_ghost'] = False
    return redirect(url_for('singleplayer', username=session['user']))

@app.route("/singleplayer/<username>")
def singleplayer(username):
    is_ghost = session.get('is_ghost', False)
    return render_template("singleplayer.html", username=username, is_ghost=is_ghost)

@app.route('/player_loaded', methods=['POST'])
def player_loaded():
    data = request.json
    game_id = data.get('game_id')
    user_login = session.get('user')

    if not game_id or not user_login:
        return jsonify({"error": "Game ID and user login are required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = current_games.get(game_id_int) or unstarted_games.get(game_id_int)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    if user_login == game.f_user:
        game.f_player_loaded = True
    elif user_login == game.c_user:
        game.c_player_loaded = True
    else:
        return jsonify({"error": "User not part of the game"}), 403

    if game.f_player_loaded and game.c_player_loaded and game.last_update_time is None:
        game.last_update_time = time.time()

    return jsonify({"message": "Player loaded status updated"}), 200


if __name__ == "__main__":
    app.run(debug=True)
