import os

import logging, subprocess, hmac, hashlib, time
import secrets

from datetime import timedelta, datetime, timezone

from flask import g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, flash, make_response
from flask_wtf.csrf import CSRFProtect


from game import (
    get_game_status_internally,
    find_waiting_game_in_db,
    update_game_with_user_in_db,
    remove_game_in_db,
    get_or_create_ephemeral_game,
    all_games_lock,
    all_games_dict,
    get_db_pieces,
    update_db_pieces,
    create_new_game_in_db
)
import base

import utils
import game_engine

logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)
app.secret_key = 'superpupersecretkey'
csrf = CSRFProtect(app)

app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
limiter.init_app(app)


app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'avatars')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)




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

@app.route("/")
def home():
    user_login = session.get('user')
    user_is_registered = False
    if user_login and not user_login.startswith('ghost'):
        user = base.get_user_by_login(user_login)
        if user:
            user_is_registered = True
    return render_template('home.html', user_is_registered=user_is_registered)

@app.route('/board/<int:game_id>/<user_login>')
@csrf.exempt
def get_board(game_id, user_login):
    if session.get('user') != user_login:
        abort(403)
    game = get_or_create_ephemeral_game(game_id)
    if not game:
        abort(404)
    user_color = 'w' if user_login == game.f_user else 'b' if user_login == game.c_user else None
    if not user_color:
        abort(403)
    opponent_login = game.c_user if user_login == game.f_user else game.f_user
    is_ghost = user_login.startswith('ghost')
    user = base.get_user_by_login(user_login)
    if is_ghost:
        user_avatar_url = '/static/avatars/default_avatar.jpg'
    else:
        avatar_filename = user['avatar_filename']
        if avatar_filename:
            user_avatar_url = url_for('static', filename='avatars/' + avatar_filename)
        else:
            user_avatar_url = '/static/avatars/default_avatar.jpg'
    opponent = base.get_user_by_login(opponent_login)
    if opponent and (not opponent_login.startswith('ghost')) and opponent['avatar_filename']:
        opponent_avatar_url = url_for('static', filename='avatars/' + opponent['avatar_filename'])
    else:
        opponent_avatar_url = '/static/avatars/default_avatar.jpg'
    return render_template(
        'board.html',
        user_login=user_login,
        game_id=game_id,
        user_color=user_color,
        opponent_login=opponent_login,
        f_user=game.f_user,
        c_user=game.c_user,
        is_ghost=is_ghost,
        user_avatar_url=user_avatar_url,
        opponent_avatar_url=opponent_avatar_url
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']
        if not utils.is_valid_username(user_login):
            flash('Имя пользователя может содержать только латинские буквы и цифры (3-15 символов)', 'error')
            return redirect(url_for('register'))
        if user_login.lower().startswith('ghost'):
            flash('Имя пользователя не может начинаться с "ghost"', 'error')
            return redirect(url_for('register'))
        if not base.check_user_exists(user_login):
            base.register_user(user_login, user_password)
            flash('Регистрация прошла успешно!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь уже существует', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')
def find_active_game(user_login):
    with all_games_lock:
        for g_id, g_obj in all_games_dict.items():
            if g_obj.f_user == user_login or g_obj.c_user == user_login:
                if g_obj.status not in ['w3', 'b3', 'n', 'ns1']:
                    return g_obj
    return None

@app.errorhandler(429)
def ratelimit_error():
    flash("Слишком много запросов. Попробуйте позже.", "error")
    return render_template("login.html"), 429

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("7 per minute")
def login():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']
        remember = 'remember_me' in request.form
        if not utils.is_valid_username(user_login):
            flash('Имя пользователя может содержать только латинские буквы и цифры (3-15 символов)', 'error')
            return redirect(url_for('register'))
        user = base.authenticate_user(user_login, user_password)
        if user:
            session['user'] = user_login
            flash('Вход выполнен', 'success')
            if remember:
                session.permanent = True
                token = secrets.token_urlsafe(64)
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)
                if base.add_remember_token(user_login, token, expires_at):
                    resp = make_response(redirect(url_for('home')))
                    resp.set_cookie('remember_token', token, expires=expires_at, httponly=True, secure=True, samesite='Lax')
                    return resp
                else:
                    flash('Не удалось сохранить токен для запоминания', 'error')
                    return redirect(url_for('login'))
            else:
                session.permanent = False
                return redirect(url_for('home'))
        else:
            flash('Неверные данные для входа', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/profile/<username>')
def profile(username):
    if not utils.is_valid_username(username):
        abort(404)
    if username.startswith('ghost'):
        abort(403)
    user_row = base.get_user_by_login(username)
    if user_row:
        user = dict(user_row)
        user_history = base.get_user_history(username)
        wins = 0
        losses = 0
        draws = 0
        for game in user_history:
            if game['result'] == 'win':
                wins += 1
            elif game['result'] == 'lose':
                losses += 1
            else:
                draws += 1
        total_games = wins + losses + draws
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
        avatar_filename = user['avatar_filename']
        if avatar_filename:
            user_avatar_url = url_for('static', filename='avatars/' + avatar_filename)
        else:
            user_avatar_url = '/static/avatars/default_avatar.jpg'
        return render_template(
            'profile.html',
            profile_user_login=user['login'],
            rang=user['rang'],
            total_games=total_games,
            wins=wins,
            losses=losses,
            draws=draws,
            is_own_profile=is_own_profile,
            in_game=in_game,
            game_id=game_id,
            current_user_login=current_user,
            user_history=user_history,
            user_avatar_url=user_avatar_url
        )
    else:
        abort(404)

@app.route("/logout")
def logout():
    user_login = session.pop('user', None)
    session.pop('game_id', None)
    session.pop('color', None)
    flash('Вы вышли из аккаунта', 'info')
    token = request.cookies.get('remember_token')
    if token:
        base.delete_remember_token(token)
    resp = make_response(redirect(url_for('home')))
    resp.delete_cookie('remember_token')
    if user_login:
        base.delete_all_remember_tokens(user_login)
    return resp

@app.errorhandler(404)
def page_not_found():
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden():
    return render_template('403.html'), 403

@app.route('/trigger_error')
def trigger_error():
    abort(500)

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Ошибка 500: {e}")
    return render_template('500.html'), 500

@app.route('/start_game')
@csrf.exempt
def start_game():
    user_login = utils.ensure_user()

    game_id = session.get('game_id')
    if game_id:
        try:
            game_id_int = int(game_id)
        except (ValueError, TypeError):
            session.pop('game_id', None)
            session.pop('color', None)
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
                    session['search_start_time'] = time.time()
                    return render_template('waiting.html', game_id=new_game_id, user_login=user_login)
                else:
                    flash('Не удалось начать новую игру.', 'error')
                    return redirect(url_for('home'))
            else:
                if game.f_user and game.c_user:
                    return redirect(url_for('get_board', game_id=game_id_int, user_login=user_login))
                else:
                    session['search_start_time'] = time.time()
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
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('home'))

    game_id_new = create_new_game_in_db(user_login)
    if not game_id_new:
        flash('Не удалось создать игру.', 'error')
        return redirect(url_for('home'))
    session['game_id'] = game_id_new
    session['color'] = 'w'
    session['search_start_time'] = time.time()
    g_obj = get_or_create_ephemeral_game(session['game_id'])
    if g_obj and g_obj.f_user and g_obj.c_user:
        return redirect(url_for('get_board', game_id=session['game_id'], user_login=user_login))
    else:
        return render_template('waiting.html', game_id=session.get('game_id'), user_login=user_login)

@app.route("/check_game_status", methods=["GET"])
@csrf.exempt
def check_game_status_route():
    game_id = session.get('game_id')
    user_login = session.get('user')
    if not game_id:
        return jsonify({"status": "no_game"}), 200
    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"status": "invalid_game_id"}), 400
    search_start_time = session.get('search_start_time')
    if search_start_time:
        elapsed = time.time() - search_start_time
        if elapsed >= 600:
            return jsonify({"status": "timeout"}), 200
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
@csrf.exempt
def move():
    def finalize_and_respond(game, user_login, game_id_int):
        result_move, points_gained = game_engine.finalize_game(game, user_login)
        response_data = {
            "status_": game.status,
            "pieces": get_db_pieces(game_id_int),
            "move_history": base.get_game_moves_from_db(game_id_int),
            "result": result_move,
            "points_gained": points_gained,
            "white_countdown": int(game.white_countdown_remaining),
            "black_countdown": int(game.black_countdown_remaining)
        }
        return jsonify(response_data)

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
        game.update_timers()
        p = get_db_pieces(game_id_int)
        result = game_engine.validate_move(
            selected_piece,
            new_pos,
            current_player,
            p,
            game
        )

        if result['move_result'] == 'invalid':
            return jsonify({"error": "Invalid move"}), 400
        updated_pieces = result['new_pieces']
        update_db_pieces(game_id_int, updated_pieces)
        move_record = {
            'player': game.f_user if current_player == 'w' else game.c_user,
            'from': {'x': selected_piece['x'], 'y': selected_piece['y']},
            'to': {'x': new_pos['x'], 'y': new_pos['y']},
            'captured': result['captured'],
            'captured_pieces': result.get('captured_pieces', []),
            'promotion': result.get('promotion', False)
        }
        if not game.game_started:
            game.game_started = True
            game.white_time_remaining = 900
            game.black_time_remaining = 900
            game.last_update_time = time.time()
        if user_color == 'w':
            game.white_idle_time = 0
            game.white_in_countdown = False
            game.white_countdown_remaining = 0
        else:
            game.black_idle_time = 0
            game.black_in_countdown = False
            game.black_countdown_remaining = 0
        game.last_update_time = time.time()
        game.update_timers()

        game.move_history.append(move_record)
        base.add_move(game_id_int, move_record)
        if game.status in ['w3', 'b3', 'n', 'ns1']:
            return finalize_and_respond(game, user_login, game_id_int)
        if result['move_result'] == 'continue_capture':
            game.status = f"{current_player}4"
            game.must_capture_piece = result['next_capture_piece']
            return jsonify({
                "status_": game.status,
                "pieces": get_db_pieces(game_id_int),
                "move_history": base.get_game_moves_from_db(game_id_int),
                "multiple_capture": True,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
            })
        elif result['move_result'] == 'valid':
            game.moves_count += 1
            game.must_capture_piece = None
            game.switch_turn()
        else:
            return jsonify({"error": "Invalid move"}), 400
        p = get_db_pieces(game_id_int)
        if game_engine.is_all_kings(p):
            game.status = "n"
            return finalize_and_respond(game, user_login, game_id_int)
        if game_engine.check_draw(p):
            game.status = "n"
            return finalize_and_respond(game, user_login, game_id_int)
        opponent_color = 'b' if current_player == 'w' else 'w'
        opponent_pieces = [x for x in p if x['color'] == (0 if opponent_color == 'w' else 1)]
        if not opponent_pieces:
            game.status = f"{current_player}3"
            return finalize_and_respond(game, user_login, game_id_int)
        if not game_engine.can_player_move(p, 0 if opponent_color == 'w' else 1):
            game.status = "n"
            return finalize_and_respond(game, user_login, game_id_int)
        return jsonify({
            "status_": game.status,
            "pieces": get_db_pieces(game_id_int),
            "move_history": base.get_game_moves_from_db(game_id_int),
            "white_countdown": int(game.white_countdown_remaining),
            "black_countdown": int(game.black_countdown_remaining)
        })

@app.route("/update_board", methods=["POST"])
@csrf.exempt
def update_board():
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
        return jsonify({"error": "Invalid game ID"}), 400
    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Invalid game ID"}), 400
    user_color = game.user_color(user_login)
    game.update_timers()
    response_data = {
        "status_": game.status,
        "pieces": get_db_pieces(game_id_int),
        "white_time": max(round(game.white_time_remaining), 0),
        "black_time": max(round(game.black_time_remaining), 0),
        "move_history": base.get_game_moves_from_db(game_id_int),
        "white_countdown": int(game.white_countdown_remaining),
        "black_countdown": int(game.black_countdown_remaining)
    }
    if game.draw_offer:
        response_data["draw_offer"] = game.draw_offer
    if game.draw_response:
        if game.draw_response['to'] == user_color:
            response_data['draw_response'] = game.draw_response['response']
            game.draw_response = None
    if game.status in ['w3', 'b3', 'n', 'ns1']:
        result_move, points_gained = game_engine.finalize_game(game, user_login)
        response_data['points_gained'] = points_gained
        response_data['result'] = result_move
    return jsonify(response_data)

@app.route("/give_up", methods=["POST"])
@csrf.exempt
def give_up_route():
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

        result_move, points_gained = game_engine.finalize_game(game, user_login)

        updated_pieces = get_db_pieces(game.game_id)

        response = {
            "status_": game.status,
            "pieces": updated_pieces,
            "result": result_move,
            "points_gained": points_gained
        }
        return jsonify(response), 200
    except Exception as e:
        app.logger.error(f"Ошибка при сдаче: {str(e)}")
        return jsonify({"error": "Произошла ошибка при сдаче."}), 500

@app.route('/leave_game', methods=['POST'])
@csrf.exempt
def leave_game():
    game_id = session.get('game_id')
    user_login = session.get('user')
    if not game_id or not user_login:
        return jsonify({"error": "Нет активной игры или пользователя"}), 400
    try:
        game_id_int = int(game_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Некорректный ID игры"}), 400
    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Игра не найдена"}), 404
    if game.f_user == user_login:
        game.f_user = None
    elif game.c_user == user_login:
        game.c_user = None
    else:
        return jsonify({"error": "Пользователь не участвует в игре"}), 403
    if game.status == 'unstarted':
        remove_game_in_db(game_id_int)
        session.pop('game_id', None)
        session.pop('color', None)
        session.pop('search_start_time', None)
        flash('Поиск игры отменен и игра удалена.', 'info')
        return jsonify({"message": "Покинул игру и игра была удалена"}), 200
    if (game.f_user is None) and (game.c_user is None):
        remove_game_in_db(game_id_int)
    session.pop('game_id', None)
    session.pop('color', None)
    session.pop('search_start_time', None)
    return jsonify({"message": "Покинул игру успешно"}), 200

@app.route("/offer_draw", methods=["POST"])
@csrf.exempt
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
    game = get_or_create_ephemeral_game(game_id_int)
    if not game:
        return jsonify({"error": "Игра не найдена"}), 404
    if user_login not in [game.f_user, game.c_user]:
        abort(403)
    user_color = 'w' if user_login == game.f_user else 'b'
    if game.draw_offer:
        return jsonify({"error": "Партия уже на рассмотрении"}), 400
    game.draw_offer = user_color
    return jsonify({"message": "Предложение ничьей отправлено"}), 200

@app.route("/respond_draw", methods=["POST"])
@csrf.exempt
def respond_draw_route():
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
        game.draw_offer = None
    elif resp == "decline":
        game.draw_response = {'response': 'decline', 'to': game.draw_offer}
        game.draw_offer = None
    else:
        return jsonify({"error": "Неверный ответ"}), 400
    if game.status == "n":
        updated_pieces = get_db_pieces(game.game_id)
        response_data = {
            "status_": game.status,
            "pieces": updated_pieces
        }
        return jsonify(response_data), 200
    else:
        updated_pieces = get_db_pieces(game.game_id)
        return jsonify({"status_": game.status, "pieces": updated_pieces}), 200

@app.route("/get_possible_moves", methods=["POST"])
@csrf.exempt
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

    game = get_or_create_ephemeral_game(game_id_int)
    if game is None:
        return jsonify({"error": "Invalid game ID"}), 400

    if user_login not in [game.f_user, game.c_user]:
        abort(403)

    current_player = game.current_player
    user_color = game.user_color(user_login)

    if user_color != current_player:
        return jsonify({"moves": []}), 200

    p = get_db_pieces(game_id_int)
    if not selected_piece or 'x' not in selected_piece or 'y' not in selected_piece:
        return jsonify({"error": "Invalid piece coordinates"}), 400

    x, y = selected_piece['x'], selected_piece['y']
    color = 0 if current_player == 'w' else 1
    moves = []

    if game.must_capture_piece:
        if (x, y) == (game.must_capture_piece['x'], game.must_capture_piece['y']):
            valid_moves = game_engine.get_possible_moves(p, color, must_capture_piece=game.must_capture_piece)
            moves = valid_moves.get((x, y), [])
    else:
        valid_moves = game_engine.get_possible_moves(p, color)
        moves = valid_moves.get((x, y), [])

    return jsonify({"moves": moves})

@app.route('/api/profile/<username>', methods=['GET'])
@csrf.exempt
def api_profile(username):
    if not utils.is_valid_username(username):
        return jsonify({"error": "Неверный пользователь"}), 404
    if username.startswith('ghost'):
        return jsonify({"error": "Профиль не доступен"}), 403
    user = base.get_user_by_login(username)
    if user:
        return jsonify({
            "user_login": user["login"],
            "rang": user["rang"],
            "wins": user["wins"],
            "losses": user["losses"],
            "draws": user["draws"],
            "total_games": user["wins"] + user["losses"] + user["draws"]
        })
    else:
        return jsonify({"error": "Пользователь не найден"}), 404

@app.route('/hook', methods=['POST'])
@csrf.exempt
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

@app.route("/singleplayer_easy/<username>")
@csrf.exempt
def singleplayer_easy(username):
    if not utils.is_valid_username(username) and not username.startswith('ghost'):
        abort(404)
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_easy.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/singleplayer_medium/<username>")
@csrf.exempt
def singleplayer_medium(username):
    if not utils.is_valid_username(username) and not username.startswith('ghost'):
        abort(404)
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_medium.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/singleplayer_hard/<username>")
@csrf.exempt
def singleplayer_hard(username):
    if not utils.is_valid_username(username) and not username.startswith('ghost'):
        abort(404)
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_hard.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/start_singleplayer", methods=["GET", "POST"])
@csrf.exempt
def start_singleplayer():
    if request.method == "POST":
        difficulty = request.form.get("difficulty")
        color = request.form.get("color")
        user_login = utils.ensure_user()
        if difficulty not in ["easy", "medium", "hard"]:
            flash('Неизвестная сложность', 'error')
            return redirect(url_for('home'))
        return redirect(url_for(f'singleplayer_{difficulty}', username=user_login, color=color))
    else:
        return redirect(url_for('home'))

@app.route('/player_loaded', methods=['POST'])
@csrf.exempt
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

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    logging.debug("Начало загрузки аватарки")
    user_login, user = utils.get_valid_user(session, base)
    if 'avatar' not in request.files:
        flash('Нет файла для загрузки', 'error')
        logging.warning("Файл не найден в запросе")
        return redirect(url_for('profile', username=user_login))
    file = request.files['avatar']
    safe_filename, error = utils.process_and_save_avatar(file, user_login, app.config['UPLOAD_FOLDER'], ALLOWED_EXTENSIONS)
    if error:
        flash(error, 'error')
        return redirect(url_for('profile', username=user_login))
    utils.remove_old_avatar(user.get("avatar_filename"), safe_filename, app.config['UPLOAD_FOLDER'])
    base.update_user_avatar(user_login, safe_filename)
    flash('Аватар успешно обновлен!', 'success')
    logging.info("Аватар успешно обновлен для пользователя")
    return redirect(url_for('profile', username=user_login))


@app.route('/delete_avatar', methods=['POST'])
@csrf.exempt
def delete_avatar():
    if 'user' not in session:
        abort(403)
    user_login = session['user']
    user = base.get_user_by_login(user_login)
    if not user or user_login.startswith('ghost'):
        abort(403)
    avatar_filename = user["avatar_filename"]
    if avatar_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        base.update_user_avatar(user_login, None)
    else:
        flash('У вас уже дефолтный аватар', 'info')
    return redirect(url_for('profile', username=user_login))

@app.route("/send_friend_request", methods=["POST"])
@csrf.exempt
def send_friend_request():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    data = request.get_json()
    friend_username = data.get("friend_username")
    sender = session.get("user")
    if not friend_username:
        return jsonify({"error": "Не указан получатель"}), 400
    if friend_username == sender:
        return jsonify({"error": "Нельзя добавить себя в друзья"}), 400
    user_row = base.get_user_by_login(friend_username)
    if not user_row:
        return jsonify({"error": "Пользователь не найден"}), 404
    status = base.send_friend_request_db(sender, friend_username)

    status_messages = {
        "sent": ({"message": "Запрос успешно отправлен"}, 200),
        "already_sent": ({"message": "Вы уже отправили запрос этому пользователю"}, 200),
        "receiver_already_sent": ({"message": "Этот пользователь уже отправил вам запрос в друзья"}, 200),
        "already_friends": ({"message": "Вы уже друзья"}, 200),
        "sent_again": ({"message": "Запрос успешно отправлен"}, 200),
        "self_request": ({"error": "Нельзя добавить себя в друзья"}, 400),
    }

    # Получаем сообщение и статус из словаря или возвращаем ошибку по умолчанию
    message, status_code = status_messages.get(status, ({"error": "Не удалось отправить запрос"}, 500))
    return jsonify(message), status_code

@app.route("/respond_friend_request", methods=["POST"])
@csrf.exempt
def respond_friend_request():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    data = request.get_json()
    sender_username = data.get("sender_username")
    response = data.get("response")
    receiver = session.get("user")
    if not sender_username or response not in ["accept", "decline"]:
        return jsonify({"error": "Некорректные данные"}), 400
    updated = base.respond_friend_request_db(sender_username, receiver, response)
    if not updated:
        return jsonify({"error": "Нет запроса от данного пользователя"}), 400
    if response == "accept":
        message = f"Пользователь {sender_username} теперь ваш друг"
    else:
        message = f"Запрос от {sender_username} отклонён"
    return jsonify({"message": message}), 200

@app.route("/get_friend_requests", methods=["GET"])
@csrf.exempt
def get_friend_requests():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    receiver = session.get("user")
    requests_list = base.get_incoming_friend_requests_db(receiver)
    return jsonify({"requests": requests_list}), 200

@app.route("/get_notifications", methods=["GET"])
@csrf.exempt
def get_notifications():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    receiver = session.get("user")
    requests_list = base.get_incoming_friend_requests_db(receiver)
    return jsonify({"notifications": requests_list}), 200

@app.route("/get_friends", methods=["GET"])
@csrf.exempt
def get_friends():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    current_user = session.get("user")
    user_friends = base.get_friends_db(current_user)
    return jsonify({"friends": user_friends}), 200

@app.route("/remove_friend", methods=["POST"])
@csrf.exempt
def remove_friend():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    data = request.get_json()
    friend_username = data.get("friend_username")
    current_user = session.get("user")
    if not friend_username:
        return jsonify({"error": "Не указан друг"}), 400
    success = base.remove_friend_db(current_user, friend_username)
    if not success:
        return jsonify({"error": "Пользователь не является вашим другом или не найден"}), 400
    return jsonify({"message": f"Пользователь {friend_username} удалён из друзей"}), 200

@app.route("/search_users")
@csrf.exempt
def search_users():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"results": []})

    current_user = session.get('user')
    results = base.search_users(query, exclude_user=current_user, limit=10)
    return jsonify({"results": results})

@app.before_request
def load_user_from_remember_token():
    if 'user' not in session:
        token = request.cookies.get('remember_token')
        if token:
            user_login = base.get_user_by_remember_token(token)
            if user_login:
                session['user'] = user_login
                session.permanent = True
                new_token = secrets.token_urlsafe(64)
                new_expires_at = datetime.now() + timedelta(days=30)
                if base.add_remember_token(user_login, new_token, new_expires_at):
                    base.delete_remember_token(token)
                    g.new_remember_token = new_token
                    g.new_expires_at = new_expires_at

@app.after_request
def set_new_remember_token(response):
    if hasattr(g, 'new_remember_token') and g.new_remember_token:
        response.set_cookie(
            'remember_token',
            g.new_remember_token,
            expires=g.new_expires_at,
            httponly=True,
            secure=True,
            samesite='Lax'
        )
    return response

@app.route("/get_top_players", methods=["GET"])
@csrf.exempt
def get_top_players_route():
    try:
        top_players_data = base.get_top_players(limit=3)
        top_players = []
        for player in top_players_data:
            avatar_filename = player["avatar_filename"]
            if avatar_filename:
                avatar_url = url_for('static', filename='avatars/' + avatar_filename)
            else:
                avatar_url = url_for('static', filename='avatars/default_avatar.jpg')
            top_players.append({
                "login": player["login"],
                "rang": player["rang"],
                "avatar_url": avatar_url
            })
        return jsonify({"top_players": top_players}), 200
    except Exception as e:
        logging.error(f"Ошибка при обработке топ игроков: {e}")
        return jsonify({"error": "Не удалось получить топ игроков"}), 500


if __name__ == "__main__":
    app.run(debug=True)
