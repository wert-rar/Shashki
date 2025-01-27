import os
import re
import sqlite3
import logging, subprocess, hmac, hashlib, threading, time
import itertools
import secrets

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from datetime import timedelta, datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, flash, make_response
from flask_wtf.csrf import CSRFProtect

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
    get_user_history,
    add_remember_token,
    get_user_by_remember_token,
    delete_remember_token,
    delete_all_remember_tokens,
    connect_db
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

from base_postgres import (
    SessionLocal,
    GameMove,
    init_db,
    send_friend_request_db,
    get_incoming_friend_requests_db,
    respond_friend_request_db,
    get_friends_db,
    remove_friend_db
)

ghost_counter = itertools.count(1)
ghost_lock = threading.Lock()
logging.basicConfig(level=logging.DEBUG)
create_tables()
app = Flask(__name__)
app.secret_key = 'superpupersecretkey'
csrf = CSRFProtect(app)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'avatars')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)

limiter.init_app(app)


def is_valid_username(username):
    return re.fullmatch(r'[A-Za-z0-9]{3,15}', username) is not None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    return True

def is_all_kings(pieces):
    for piece in pieces:
        if not piece.get('is_king', False):
            return False
    return True

def get_game_moves_from_db(game_id):
    db_session = SessionLocal()
    moves = db_session.query(GameMove).filter_by(game_id=game_id).order_by(GameMove.move_id).all()
    move_list = []
    for m in moves:
        move_list.append({
            "player": m.player,
            "from": {"x": m.from_x, "y": m.from_y},
            "to": {"x": m.to_x, "y": m.to_y},
            "captured": m.captured_piece,
            "promotion": m.promotion
        })
    db_session.close()
    return move_list

def finalize_game(game, user_login):
    if not game.c_user:
        remove_game_in_db(game.game_id)
        return None, 0
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
        if not getattr(game, 'rank_updated', False):
            update_game_status_in_db(game.game_id, 'completed')
            if not user_is_ghost:
                user_rank_before = get_user_rang(user_login)
                date_end = datetime.now().isoformat()
                insert_completed_game(
                    user_login=user_login,
                    game_id=game.game_id,
                    date_start=date_end,
                    rating_before=user_rank_before,
                    rating_after=user_rank_before,
                    rating_change=0,
                    result=result_move
                )
            opponent_login = game.f_user if game.f_user != user_login else game.c_user
            if opponent_login and not opponent_login.startswith('ghost'):
                opp_rank_before = get_user_rang(opponent_login)
                date_end = datetime.now().isoformat()
                insert_completed_game(
                    user_login=opponent_login,
                    game_id=game.game_id,
                    date_start=date_end,
                    rating_before=opp_rank_before,
                    rating_after=opp_rank_before,
                    rating_change=0,
                    result=result_move
                )
            game.rank_updated = True
        return result_move, points_gained
    if winner_color is None and game.status == 'n':
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
            date_end = datetime.now().isoformat()
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
            else:
                opponent_result_move = None
                opponent_points_gained = 0
            if opponent_result_move is not None:
                opponent_rank_after = get_user_rang(opponent_login)
                opponent_rating_change = opponent_rank_after - opponent_rank_before
                date_end = datetime.now().isoformat()
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
    user_login = session.get('user')
    user_is_registered = False
    if user_login and not user_login.startswith('ghost'):
        user = get_user_by_login(user_login)
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
    user = get_user_by_login(user_login)
    if is_ghost:
        user_avatar_url = '/static/avatars/default_avatar.jpg'
    else:
        avatar_filename = user['avatar_filename']
        if avatar_filename:
            user_avatar_url = url_for('static', filename='avatars/' + avatar_filename)
        else:
            user_avatar_url = '/static/avatars/default_avatar.jpg'
    opponent = get_user_by_login(opponent_login)
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
        if not is_valid_username(user_login):
            flash('Имя пользователя может содержать только латинские буквы и цифры (3-15 символов)', 'error')
            return redirect(url_for('register'))
        if user_login.lower().startswith('ghost'):
            flash('Имя пользователя не может начинаться с "ghost"', 'error')
            return redirect(url_for('register'))
        if not check_user_exists(user_login):
            register_user(user_login, user_password)
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
def ratelimit_error(e):
    flash("Слишком много запросов. Попробуйте позже.", "error")
    return render_template("login.html"), 429

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        user_login = request.form['login']
        user_password = request.form['password']
        remember = 'remember_me' in request.form

        if not is_valid_username(user_login):
            flash('Имя пользователя может содержать только латинские буквы и цифры (3-15 символов)', 'error')
            return redirect(url_for('register'))

        user = authenticate_user(user_login, user_password)
        if user:
            session['user'] = user_login
            flash('Вход выполнен', 'success')

            if remember:
                session.permanent = True
                token = secrets.token_urlsafe(64)
                expires_at = datetime.utcnow() + timedelta(days=30)
                if add_remember_token(user_login, token, expires_at):
                    resp = make_response(redirect(url_for('home')))
                    resp.set_cookie(
                        'remember_token',
                        token,
                        expires=expires_at,
                        httponly=True,
                        secure=True,
                        samesite='Lax'
                    )
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
    user_row = get_user_by_login(username)
    if username.startswith('ghost'):
        abort(403)
    if user_row:
        user = dict(user_row)
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
            wins=user['wins'],
            losses=user['losses'],
            draws=user['draws'],
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
        delete_remember_token(token)

    resp = make_response(redirect(url_for('home')))
    resp.delete_cookie('remember_token')

    if user_login:
        delete_all_remember_tokens(user_login)

    return resp

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
@csrf.exempt
def start_game():
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
    g = get_or_create_ephemeral_game(session['game_id'])
    if g and g.f_user and g.c_user:
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
        app.logger.warning(f"Некорректный game_id в check_game_status: {game_id}")
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
        db_session = SessionLocal()
        new_move = GameMove(
            game_id=game_id_int,
            player=move_record['player'],
            from_x=move_record['from']['x'],
            from_y=move_record['from']['y'],
            to_x=move_record['to']['x'],
            to_y=move_record['to']['y'],
            captured_piece=move_record['captured'],
            promotion=move_record['promotion']
        )
        db_session.add(new_move)
        db_session.commit()
        db_session.close()
        if game.status in ['w3', 'b3', 'n', 'ns1']:
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": game.status,
                "pieces": game.pieces,
                "white_time": max(round(game.white_time_remaining), 0),
                "black_time": max(round(game.black_time_remaining), 0),
                "move_history": get_game_moves_from_db(game_id_int),
                "result": result_move,
                "points_gained": points_gained,
                "white_countdown": round(game.white_countdown_remaining),
                "black_countdown": round(game.black_countdown_remaining)
            }
            return jsonify(response_data)
        if result['move_result'] == 'continue_capture':
            game.pieces = result['new_pieces']
            game.status = f"{current_player}4"
            return jsonify({
                "status_": game.status,
                "pieces": game.pieces,
                "move_history": get_game_moves_from_db(game_id_int),
                "multiple_capture": True,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
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
            response_data = {
                "status_": "n",
                "pieces": game.pieces,
                "move_history": get_game_moves_from_db(game_id_int),
                "result": result_move,
                "points_gained": points_gained,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
            }
            return jsonify(response_data)
        if check_draw(game.pieces):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": "n",
                "pieces": game.pieces,
                "move_history": get_game_moves_from_db(game_id_int),
                "result": result_move,
                "points_gained": points_gained,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
            }
            return jsonify(response_data)
        opponent_color = 'b' if current_player == 'w' else 'w'
        opponent_pieces = [p for p in game.pieces if p['color'] == (0 if opponent_color == 'w' else 1)]
        if not opponent_pieces:
            game.status = f"{current_player}3"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": game.status,
                "pieces": game.pieces,
                "move_history": get_game_moves_from_db(game_id_int),
                "result": result_move,
                "points_gained": points_gained,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
            }
            return jsonify(response_data)
        if not can_player_move(game.pieces, 0 if opponent_color == 'w' else 1):
            game.status = "n"
            result_move, points_gained = finalize_game(game, user_login)
            response_data = {
                "status_": "n",
                "pieces": game.pieces,
                "move_history": get_game_moves_from_db(game_id_int),
                "result": result_move,
                "points_gained": points_gained,
                "white_countdown": int(game.white_countdown_remaining),
                "black_countdown": int(game.black_countdown_remaining)
            }
            return jsonify(response_data)
        return jsonify({
            "status_": game.status,
            "pieces": game.pieces,
            "move_history": get_game_moves_from_db(game_id_int),
            "white_countdown": int(game.white_countdown_remaining),
            "black_countdown": int(game.black_countdown_remaining)
        })

@app.route("/update_board", methods=["POST"])
@csrf.exempt
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
            return jsonify({"error": "Invalid game ID"}), 400
        game = get_or_create_ephemeral_game(game_id_int)
        if not game:
            return jsonify({"error": "Invalid game ID"}), 400
        user_color = game.user_color(user_login)
        game.update_timers()
        response_data = {
            "status_": game.status,
            "pieces": game.pieces,
            "white_time": max(round(game.white_time_remaining), 0),
            "black_time": max(round(game.black_time_remaining), 0),
            "move_history": get_game_moves_from_db(game_id_int),
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
            result_move, points_gained = finalize_game(game, user_login)
            response_data['points_gained'] = points_gained
            response_data['result'] = result_move
        return jsonify(response_data)
    except Exception as e:
        app.logger.error(f"Exception in update_board: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
@csrf.exempt
def api_profile(username):
    if username.startswith('ghost'):
        return jsonify({"error": "Профиль не доступен"}), 403
    user = get_user_by_login(username)
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
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_easy.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/singleplayer_medium/<username>")
@csrf.exempt
def singleplayer_medium(username):
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_medium.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/singleplayer_hard/<username>")
@csrf.exempt
def singleplayer_hard(username):
    is_ghost = session.get('is_ghost', False)
    user_color = request.args.get('color', 'w')
    return render_template("singleplayer_hard.html", username=username, is_ghost=is_ghost, user_color=user_color)

@app.route("/start_singleplayer", methods=["GET", "POST"])
@csrf.exempt
def start_singleplayer():
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
    if 'user' not in session:
        abort(403)
    user_login = session['user']
    user = get_user_by_login(user_login)
    if not user or user_login.startswith('ghost'):
        abort(403)
    if 'avatar' not in request.files:
        flash('Нет файла для загрузки', 'error')
        return redirect(url_for('profile', username=user_login))
    file = request.files['avatar']
    if file.filename == '':
        flash('Вы не выбрали файл', 'error')
        return redirect(url_for('profile', username=user_login))
    if file and allowed_file(file.filename):
        _, ext = os.path.splitext(file.filename)
        new_filename = f"{user_login}{ext.lower()}"
        from base_sqlite import update_user_avatar
        old_avatar = user["avatar_filename"]
        if old_avatar and old_avatar != new_filename:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        safe_filename = secure_filename(new_filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(save_path)
        update_user_avatar(user_login, safe_filename)
    else:
        flash('Недопустимый файл', 'error')
    return redirect(url_for('profile', username=user_login))

@app.route('/delete_avatar', methods=['POST'])
@csrf.exempt
def delete_avatar():
    if 'user' not in session:
        abort(403)
    user_login = session['user']
    user = get_user_by_login(user_login)
    if not user or user_login.startswith('ghost'):
        abort(403)
    avatar_filename = user["avatar_filename"]
    if avatar_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        from base_sqlite import update_user_avatar
        update_user_avatar(user_login, None)
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

    user_row = get_user_by_login(friend_username)
    if not user_row:
        return jsonify({"error": "Пользователь не найден"}), 404

    status = send_friend_request_db(sender, friend_username)

    if status == "sent":
        return jsonify({"message": "Запрос успешно отправлен"}), 200
    elif status == "already_sent":
        return jsonify({"message": "Вы уже отправили запрос этому пользователю"}), 200
    elif status == "receiver_already_sent":
        return jsonify({"message": "Этот пользователь уже отправил вам запрос в друзья"}), 200
    elif status == "already_friends":
        return jsonify({"message": "Вы уже друзья"}), 200
    elif status == "sent_again":
        return jsonify({"message": "Запрос успешно отправлен"}), 200
    elif status == "self_request":
        return jsonify({"error": "Нельзя добавить себя в друзья"}), 400
    else:
        return jsonify({"error": "Не удалось отправить запрос"}), 500


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
    updated = respond_friend_request_db(sender_username, receiver, response)
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
    requests_list = get_incoming_friend_requests_db(receiver)
    return jsonify({"requests": requests_list}), 200


@app.route("/get_notifications", methods=["GET"])
@csrf.exempt
def get_notifications():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    receiver = session.get("user")
    requests_list = get_incoming_friend_requests_db(receiver)
    return jsonify({"notifications": requests_list}), 200


@app.route("/get_friends", methods=["GET"])
@csrf.exempt
def get_friends():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    current_user = session.get("user")
    user_friends = get_friends_db(current_user)
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
    success = remove_friend_db(current_user, friend_username)
    if not success:
        return jsonify({"error": "Пользователь не является вашим другом или не найден"}), 400
    return jsonify({"message": f"Пользователь {friend_username} удалён из друзей"}), 200

@app.route("/search_users")
@csrf.exempt
def search_users():
    from base_sqlite import connect_db
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"results": []})

    current_user = session.get('user')

    con = connect_db()
    cur = con.cursor()

    if current_user:
        cur.execute(
            "SELECT login FROM player WHERE login LIKE ? AND login != ? COLLATE NOCASE LIMIT 10",
            (query + '%', current_user)
        )
    else:
        cur.execute(
            "SELECT login FROM player WHERE login LIKE ? COLLATE NOCASE LIMIT 10",
            (query + '%',)
        )

    rows = cur.fetchall()
    con.close()
    results = [row["login"] for row in rows]
    return jsonify({"results": results})

@app.before_request
def load_user_from_remember_token():
    if 'user' not in session:
        token = request.cookies.get('remember_token')
        if token:
            user_login = get_user_by_remember_token(token)
            if user_login:
                session['user'] = user_login
                session.permanent = True
                new_token = secrets.token_urlsafe(64)
                new_expires_at = datetime.utcnow() + timedelta(days=30)
                if add_remember_token(user_login, new_token, new_expires_at):
                    delete_remember_token(token)
                    resp = make_response()
                    resp.set_cookie(
                        'remember_token',
                        new_token,
                        expires=new_expires_at,
                        httponly=True,
                        secure=True,
                        samesite='Lax'
                    )
                    from flask import g
                    g.new_remember_token = new_token
                    g.new_expires_at = new_expires_at
@app.after_request
def set_new_remember_token(response):
    from flask import g
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
def get_top_players():
    try:
        con = connect_db()
        cur = con.cursor()
        cur.execute("""
            SELECT login, rang, avatar_filename
            FROM player
            ORDER BY rang DESC
            LIMIT 3
        """)
        rows = cur.fetchall()
        con.close()
        top_players = []
        for row in rows:
            avatar_url = url_for('static', filename='avatars/' + row["avatar_filename"]) if row["avatar_filename"] else url_for('static', filename='avatars/default_avatar.jpg')
            top_players.append({
                "login": row["login"],
                "rang": row["rang"],
                "avatar_url": avatar_url
            })
        return jsonify({"top_players": top_players}), 200
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении топ игроков: {e}")
        return jsonify({"error": "Не удалось получить топ игроков"}), 500

@app.route("/invite_game", methods=["POST"])
@csrf.exempt
def invite_game():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403

    data = request.get_json()
    friend_username = data.get("friend_username")
    sender = session["user"]
    if not friend_username:
        return jsonify({"error": "Не указан пользователь"}), 400

    from game import create_new_game_in_db
    new_game_id = create_new_game_in_db(sender)
    if not new_game_id:
        return jsonify({"error": "Не удалось создать игру"}), 500

    session["game_id"] = new_game_id
    session["color"] = "w"

    from base_postgres import send_game_invite_db_with_gameid
    status = send_game_invite_db_with_gameid(sender, friend_username, new_game_id)
    if status == "self_invite":
        return jsonify({"error": "Нельзя пригласить самого себя"}), 400
    elif status == "already_sent":
        return jsonify({"message": "Уже отправлено приглашение", "game_id": new_game_id}), 200
    elif status == "reverse_already_sent":
        return jsonify({"message": "Пользователь уже отправил вам приглашение", "game_id": new_game_id}), 200
    elif status == "sent":
        return jsonify({
            "message": f"Приглашение отправлено! (номер игры {new_game_id})",
            "game_id": new_game_id
        }), 200
    else:
        return jsonify({"error": "Неизвестная ошибка"}), 500

@app.route("/get_game_invites", methods=["GET"])
@csrf.exempt
def get_game_invites():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    receiver = session["user"]
    from base_postgres import get_incoming_game_invites_db
    invites = get_incoming_game_invites_db(receiver)
    return jsonify({"invites": invites}), 200

@app.route("/respond_game_invite", methods=["POST"])
@csrf.exempt
def respond_game_invite():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 403
    data = request.get_json()
    sender_username = data.get("sender_username")
    response = data.get("response")
    receiver = session["user"]
    if not sender_username or response not in ["accept","decline"]:
        return jsonify({"error":"Неверные данные"}),400
    from base_postgres import respond_game_invite_db
    success, the_game_id = respond_game_invite_db(sender_username, receiver, response)
    if not success:
        return jsonify({"error":"Приглашение не найдено"}),400
    if response == "accept" and the_game_id:
        session["game_id"] = the_game_id
        session["color"] = "b"
        return jsonify({"message":"Приглашение принято","game_id":the_game_id}),200
    else:
        return jsonify({"message":"Операция выполнена"}),200

if __name__ == "__main__":
    app.run(debug=True)
