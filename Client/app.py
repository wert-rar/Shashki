from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, flash
from base_sqlite import (
    check_user_exists,
    register_user,
    authenticate_user,
    get_user_by_login,
    update_user_rank,
    update_user_stats,
    create_tables,
    get_user_rang,
    insert_completed_game,
    get_user_history
)
from game import (
    get_game_status_internally,
    find_waiting_game_in_db,
    update_game_with_user_in_db,
    create_new_game_in_db,
    remove_game_in_db,
    get_or_create_ephemeral_game,
    all_games_lock,
    all_games_dict,
    update_game_status_in_db
)
import logging, subprocess, hmac, hashlib, threading, time
import itertools
import datetime

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
    "ns1": "Игра не началась из-за отсутствия хода",
    "e1": "Ошибка при запросе к серверу"
}


def get_piece_at(pieces, x, y):
    # Возвращает фигуру на заданных координатах
    for piece in pieces:
        if piece['x'] == x and piece['y'] == y:
            return piece
    return None


def can_capture(piece, pieces):
    # Определяет, может ли фигура выполнить захват
    x, y = piece['x'], piece['y']
    moves = []
    if piece.get('is_king', False):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in directions:
            opponent_found = False
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
    # Определяет, может ли фигура сделать обычный ход
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
    # Получает все возможные ходы для указанного цвета
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
    # Проверяет, может ли игрок с данным цветом сделать ход
    moves = get_possible_moves(pieces, color)
    return any(moves.values())


def check_draw(pieces):
    # Проверяет, является ли игра ничьей
    if can_player_move(pieces, 0):
        return False
    if can_player_move(pieces, 1):
        return False
    return True


def is_all_kings(pieces):
    # Проверяет, все ли фигуры являются королями
    for piece in pieces:
        if not piece.get('is_king', False):
            return False
    return True


def finalize_game(game, user_login):
    # Завершает игру и обновляет статистику игроков
    if game.status == 'w3':
        winner_color = 'w'
    elif game.status == 'b3':
        winner_color = 'b'
    elif game.status == 'n':
        winner_color = None
    elif game.status == 'ns1':
        winner_color = None
    else:
        winner_color = None

    user_color = game.user_color(user_login)
    user_is_ghost = user_login.startswith('ghost')

    if game.status == 'ns1':
        result_move = 'not_started'
        points_gained = 0
        update_game_status_in_db(game.game_id, 'completed')
        return result_move, points_gained

    if winner_color is None:
        result_move = 'draw'
        points_gained = 5 if not user_is_ghost else 0
    else:
        if winner_color == user_color:
            result_move = 'win'
            points_gained = 10 if not user_is_ghost else 0
        else:
            result_move = 'lose'
            points_gained = 0

    if not getattr(game, 'rank_updated', False):
        opponent_login = game.f_user if game.f_user != user_login else game.c_user
        opponent_is_ghost = opponent_login.startswith('ghost')

        if not user_is_ghost:
            user_rank_before = get_user_rang(user_login)

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

            user_rank_after = get_user_rang(user_login)
            user_rating_change = user_rank_after - user_rank_before

            date_end = datetime.datetime.now().isoformat()

            insert_completed_game(
                user_login=user_login,
                game_id=game.game_id,
                date_start=date_end,
                rating_before=user_rank_before,
                rating_after=user_rank_after,
                rating_change=user_rating_change,
                result=result_move
            )

        if not opponent_is_ghost:
            opponent_result_move = None
            opponent_points_gained = 0
            opponent_rank_before = get_user_rang(opponent_login)

            if result_move == 'win':
                opponent_result_move = 'lose'
                opponent_points_gained = 0
                update_user_stats(opponent_login, losses=1)
            elif result_move == 'lose':
                opponent_result_move = 'win'
                opponent_points_gained = 10
                update_user_rank(opponent_login, opponent_points_gained)
                update_user_stats(opponent_login, wins=1)
            elif result_move == 'draw':
                opponent_result_move = 'draw'
                opponent_points_gained = 5
                update_user_rank(opponent_login, opponent_points_gained)
                update_user_stats(opponent_login, draws=1)

            opponent_rank_after = get_user_rang(opponent_login)
            opponent_rating_change = opponent_rank_after - opponent_rank_before

            date_end = datetime.datetime.now().isoformat()

            insert_completed_game(
                user_login=opponent_login,
                game_id=game.game_id,
                date_start=date_end,
                rating_before=opponent_rank_before,
                rating_after=opponent_rank_after,
                rating_change=opponent_rating_change,
                result=opponent_result_move
            )

        game.rank_updated = True
        update_game_status_in_db(game.game_id, 'completed')

    return result_move, points_gained


def validate_move(selected_piece, new_pos, current_player, pieces, game):
    # Валидирует ход игрока
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
                if (piece['color'] == 0 and piece['y'] == 0) or (piece['color'] == 1 and piece['y'] == 7):
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
                'captured': captured,
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


@app.route("/")
def home():
    # Отображает домашнюю страницу
    user_login = session.get('user')
    user_is_registered = False
    if user_login and not user_login.startswith('ghost'):
        user = get_user_by_login(user_login)
        if user:
            user_is_registered = True
    return render_template('home.html', user_is_registered=user_is_registered)


@app.route('/board/<int:game_id>/<user_login>')
def get_board(game_id, user_login):
    # Отображает игровую доску для указанной игры и пользователя
    game = get_or_create_ephemeral_game(game_id)
    if not game:
        abort(404)

    user_color = 'w' if user_login == game.f_user else 'b' if user_login == game.c_user else None
    if not user_color:
        abort(403)

    opponent_login = game.c_user if user_login == game.f_user else game.f_user
    is_ghost = user_login.startswith('ghost')

    return render_template(
        'board.html',
        user_login=user_login,
        game_id=game_id,
        user_color=user_color,
        opponent_login=opponent_login,
        f_user=game.f_user,
        c_user=game.c_user,
        is_ghost=is_ghost
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    # Обрабатывает регистрацию нового пользователя
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


def find_active_game(user_login):
    # Находит активную игру для пользователя
    with all_games_lock:
        for g_id, g_obj in all_games_dict.items():
            if g_obj.f_user == user_login or g_obj.c_user == user_login:
                if g_obj.status not in ['w3', 'b3', 'n', 'ns1']:
                    return g_obj
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    # Обрабатывает вход пользователя в систему
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']

        user = authenticate_user(user_login, user_password)
        if user:
            session['user'] = user_login
            game = find_active_game(user_login)
            if game:
                session['game_id'] = game.game_id
                session['color'] = game.user_color(user_login)
            flash('Успешный вход!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Неправильное имя пользователя или пароль.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/profile/<username>')
def profile(username):
    # Отображает профиль указанного пользователя
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
                game = all_games_dict.get(game_id_int)
                if game and current_user in [game.f_user, game.c_user]:
                    if game.f_user and game.c_user and game.status not in ['w3', 'b3', 'n', 'ns1']:
                        in_game = True
                        game_id = game_id_int
            except (ValueError, TypeError):
                in_game = False

        user_history = get_user_history(username)

        return render_template(
            'profile.html',
            profile_user_login=user['login'],
            rang=user['rang'],
            total_games=total_games,
            wins=user['wins'],
            losses=user['losses'],
            draws=user['draws'],
            is_own_profile=is_own_profile,
            in_game=in_game,
            game_id=game_id,
            current_user_login=current_user,
            user_history=user_history
        )
    else:
        abort(404)


@app.route("/logout")
def logout():
    # Обрабатывает выход пользователя из системы
    session.pop('user', None)
    session.pop('game_id', None)
    session.pop('color', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('home'))


@app.errorhandler(404)
def page_not_found(e):
    # Обрабатывает ошибку 404
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    # Обрабатывает ошибку 403
    return render_template('403.html'), 403


@app.route('/trigger_error')
def trigger_error():
    # Триггерит ошибку 500 для тестирования
    abort(500)


@app.errorhandler(500)
def internal_server_error(e):
    # Обрабатывает ошибку 500
    app.logger.error(f"Ошибка 500: {e}")
    return render_template('500.html'), 500


@app.route('/start_game')
def start_game():
    # Инициирует начало новой игры или присоединение к существующей
    user_login = session.get('user')
    if not user_login:
        with ghost_lock:
            ghost_num = next(ghost_counter)
            ghost_username = f"ghost{ghost_num}"
        session['user'] = ghost_username
        session['is_ghost'] = True
        user_login = ghost_username
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

        game = all_games_dict.get(game_id_int)
        if game and user_login in [game.f_user, game.c_user]:
            if game.status in ['w3', 'b3', 'n', 'ns1']:
                session.pop('game_id', None)
                session.pop('color', None)
                new_game_id = create_new_game_in_db(user_login)
                if new_game_id:
                    session['game_id'] = new_game_id
                    session['color'] = 'w'
                    return render_template('waiting.html', game_id=new_game_id, user_login=user_login)
                else:
                    flash('Не удалось начать новую игру.', 'error')
                    return redirect(url_for('home'))
            else:
                if game.f_user and game.c_user:
                    return redirect(url_for('get_board', game_id=game_id_int, user_login=user_login))
                else:
                    return render_template('waiting.html', game_id=game_id_int, user_login=user_login)

    waiting_game = find_waiting_game_in_db()
    if waiting_game:
        color = 'w' if not waiting_game.f_user else 'b'
        try:
            updated = update_game_with_user_in_db(waiting_game.game_id, user_login, color)
            if updated:
                session['game_id'] = waiting_game.game_id
                session['color'] = color
                return redirect(url_for('get_board', game_id=waiting_game.game_id, user_login=user_login))
            else:
                pass
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('home'))

    game_id_new = create_new_game_in_db(user_login)
    if not game_id_new:
        flash('Не удалось создать игру.', 'error')
        return redirect(url_for('home'))
    session['game_id'] = game_id_new
    session['color'] = 'w'

    g = get_or_create_ephemeral_game(session['game_id'])
    if g and g.f_user and g.c_user:
        return redirect(url_for('get_board', game_id=session['game_id'], user_login=user_login))
    else:
        return render_template('waiting.html', game_id=session.get('game_id'), user_login=user_login)


@app.route("/check_game_status", methods=["GET"])
def check_game_status_route():
    # Проверяет текущий статус игры
    game_id = session.get('game_id')
    user_login = session.get('user')

    if not game_id:
        return jsonify({"status": "no_game"}), 200

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        app.logger.warning(f"Некорректный game_id в check_game_status: {game_id}")
        return jsonify({"status": "invalid_game_id"}), 400

    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"status": "game_not_found"}), 404

    if game.status in ['w3', 'b3', 'n', 'ns1']:
        response = {
            'status': game.status,
            'current_user': user_login,
            'game_id': game_id_int
        }
    else:
        db_status = get_game_status_internally(game_id_int)
        if db_status == 'current':
            response = {
                'status': 'active',
                'current_user': user_login,
                'game_id': game_id_int
            }
        elif db_status == 'unstarted':
            response = {
                'status': 'waiting',
                'current_user': user_login,
                'game_id': game_id_int
            }
        elif db_status == 'completed':
            response = {
                'status': 'completed',
                'current_user': user_login,
                'game_id': game_id_int
            }
        else:
            response = {
                'status': 'game_not_found',
                'current_user': user_login,
                'game_id': game_id_int
            }

    return jsonify(response)


@app.route("/move", methods=["POST"])
def move():
    # Обрабатывает ход пользователя
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

    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Invalid game ID"}), 400

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        return jsonify({"error": "Not your turn"}), 403

    with game.lock:
        result = validate_move(selected_piece, new_pos, current_player, game.pieces, game)
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

        if not game.game_started:
            game.game_started = True
            game.white_time_remaining = 900
            game.black_time_remaining = 900
            game.last_update_time = time.time()

        game.update_timers()

        if game.status in ['w3', 'b3', 'n', 'ns1']:
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
            return jsonify({
                "status_": game.status,
                "pieces": game.pieces,
                "move_history": game.move_history,
                "multiple_capture": True
            })
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
            response_data = {
                "status_": game.status,
                "pieces": game.pieces,
                "move_history": game.move_history,
                "result": result_move,
                "points_gained": points_gained
            }
            return jsonify(response_data)

        if not can_player_move(game.pieces, 0 if opponent_color == 'w' else 1):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": "n",
                "pieces": game.pieces,
                "move_history": game.move_history,
                "result": result_move,
                "points_gained": points_gained
            }
            return jsonify(response_data)

        return jsonify({"status_": game.status, "pieces": game.pieces, "move_history": game.move_history})


@app.route("/update_board", methods=["POST"])
def update_board():
    # Обновляет состояние доски на основе данных с сервера
    try:
        if not request.is_json:
            app.logger.debug("Запрос не является JSON.")
            return jsonify({"error": "Request data must be in JSON format"}), 400

        data = request.get_json()
        app.logger.debug(f"Полученные данные: {data}")

        game_id = data.get("game_id")
        user_login = session.get('user')

        if game_id is None:
            app.logger.debug("Необходимо поле game_id.")
            return jsonify({"error": "Game ID is required"}), 400

        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            app.logger.warning(f"Некорректный game_id: {game_id}")
            return jsonify({"error": "Invalid game ID"}), 400

        game = get_or_create_ephemeral_game(game_id_int)
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

        if game.status in ['w3', 'b3', 'n', 'ns1']:
            result_move, points_gained = finalize_game(game, user_login)
            response_data['points_gained'] = points_gained
            response_data['result'] = result_move

        return jsonify(response_data)
    except Exception as e:
        app.logger.error(f"Exception in update_board: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/give_up", methods=["POST"])
def give_up_route():
    # Обрабатывает сдачу пользователя
    try:
        data = request.json
        game_id = data.get("game_id")
        user_login = data.get("user_login")

        if not game_id or not user_login:
            return jsonify({"error": "Недостаточно данных для сдачи"}), 400

        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid game ID"}), 400

        game = get_or_create_ephemeral_game(game_id_int)
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
    # Обрабатывает выход пользователя из игры
    game_id = session.get('game_id')
    user_login = session.get('user')

    if not game_id or not user_login:
        return jsonify({"error": "No game to leave"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    if game.f_user == user_login:
        game.f_user = None
    elif game.c_user == user_login:
        game.c_user = None
    else:
        return jsonify({"error": "User is not in the game"}), 403

    if (game.f_user is None) and (game.c_user is None):
        remove_game_in_db(game_id_int)

    session.pop('game_id', None)
    session.pop('color', None)
    return jsonify({"message": "Left the game successfully"}), 200


@app.route("/offer_draw", methods=["POST"])
def offer_draw():
    # Обрабатывает предложение ничьей
    data = request.json
    game_id = data.get("game_id")
    user_login = session.get('user')

    if game_id is None:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = get_or_create_ephemeral_game(game_id_int)
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
    # Обрабатывает ответ на предложение ничьей
    data = request.json
    game_id = data.get("game_id")
    user_login = session.get('user')
    resp = data.get("response")

    if game_id is None:
        return jsonify({"error": "Game ID is required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Игра не найдена"}), 404

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    user_color = 'w' if user_login == game.f_user else 'b'

    if not game.draw_offer:
        return jsonify({"error": "Нет активных предложений ничьей"}), 400

    if game.draw_offer == user_color:
        return jsonify({"error": "Вы уже предложили ничью"}), 400

    if resp == "accept":
        game.status = "n"
        game.draw_response = {'response': 'accept', 'to': game.draw_offer}
        app.logger.debug(f"Пользователь {user_login} принял ничью в игре {game_id_int}")
        game.draw_offer = None
    elif resp == "decline":
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
    # Возвращает возможные ходы для выбранной фигуры
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

    game = get_or_create_ephemeral_game(game_id_int)
    if game is None:
        return jsonify({"error": "Invalid game ID"}), 400

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        logging.debug(f"User {user_login} attempted to get moves, but it's {current_player}'s turn. Возвращаем пустой список.")
        return jsonify({"moves": []}), 200

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
    # Возвращает информацию о профиле пользователя в формате JSON
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
    # Обрабатывает вебхук для автоматического обновления репозитория
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


@app.route("/singleplayer_easy/<username>")
def singleplayer_easy(username):
    # Отображает страницу легкого уровня одиночной игры
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_easy.html", username=username, is_ghost=is_ghost, user_color=user_color)


@app.route("/singleplayer_medium/<username>")
def singleplayer_medium(username):
    # Отображает страницу среднего уровня одиночной игры
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_medium.html", username=username, is_ghost=is_ghost, user_color=user_color)


@app.route("/singleplayer_hard/<username>")
def singleplayer_hard(username):
    # Отображает страницу сложного уровня одиночной игры
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_hard.html", username=username, is_ghost=is_ghost, user_color=user_color)


@app.route("/start_singleplayer", methods=["GET", "POST"])
def start_singleplayer():
    # Инициирует одиночную игру с выбранным уровнем сложности
    if request.method == "POST":
        difficulty = request.form.get("difficulty")
        color = request.form.get("color")
        user_login = session.get('user')

        if not user_login:
            with ghost_lock:
                ghost_num = next(ghost_counter)
                ghost_username = f"ghost{ghost_num}"
            session['user'] = ghost_username
            session['is_ghost'] = True
        else:
            session['is_ghost'] = False

        if difficulty not in ["easy", "medium", "hard"]:
            flash('Неизвестная сложность', 'error')
            return redirect(url_for('home'))

        return redirect(url_for(f'singleplayer_{difficulty}', username=session['user'], color=color))
    else:
        return redirect(url_for('home'))


@app.route('/player_loaded', methods=['POST'])
def player_loaded():
    # Отмечает, что игрок загрузил игровую доску
    data = request.json
    game_id = data.get('game_id')
    user_login = session.get('user')

    if not game_id or not user_login:
        return jsonify({"error": "Game ID and user login are required"}), 400

    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game ID"}), 400

    game = get_or_create_ephemeral_game(game_id_int)
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


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


if __name__ == "__main__":
    app.run(debug=True)
