from thecheckers import base
from thecheckers.game import update_game_status_in_db
from thecheckers.redis_base import clear_move_status


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
            if (0 <= end_x < 8 and 0 <= end_y < 8 and captured_piece and
                    captured_piece['color'] != piece['color'] and not target_pos):
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
    capture_exists = any(can_capture(piece, pieces) for piece in pieces if piece['color'] == color)
    for piece in pieces:
        if piece['color'] != color:
            continue
        if must_capture_piece and (piece['x'], piece['y']) != (must_capture_piece['x'], must_capture_piece['y']):
            continue
        capture_moves = can_capture(piece, pieces)
        if capture_exists:
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
    return not (can_player_move(pieces, 0) or can_player_move(pieces, 1))


def is_all_kings(pieces):
    return all(piece.get('is_king', False) for piece in pieces)


def calculate_new_rating(rating, opponent_rating, result, base_K=20):
    diff = opponent_rating - rating
    if diff > 0:
        if diff < 150:
            win_multiplier = 1.0
            loss_multiplier = 1.0
        elif diff < 300:
            win_multiplier = 1.5
            loss_multiplier = 0.5
        elif diff < 550:
            win_multiplier = 2.0
            loss_multiplier = 0.4
        else:
            win_multiplier = 3.0
            loss_multiplier = 0.3
    elif diff < 0:
        adiff = -diff
        if adiff < 150:
            win_multiplier = 1.0
            loss_multiplier = 1.0
        elif adiff < 300:
            win_multiplier = 0.5
            loss_multiplier = 1.5
        elif adiff < 550:
            win_multiplier = 0.4
            loss_multiplier = 2.0
        else:
            win_multiplier = 0.3
            loss_multiplier = 3.0
    else:
        win_multiplier = 1.0
        loss_multiplier = 1.0

    expected_score = 1 / (1 + 10 ** ((opponent_rating - rating) / 400))
    if result == 1.0:
        multiplier = win_multiplier
    elif result == 0.0:
        multiplier = loss_multiplier
    else:
        multiplier = 1.0

    rating_change = base_K * multiplier * (result - expected_score)
    if result == 1.0 and rating_change < 1:
        rating_change = 1
    elif result == 0.0 and rating_change > -1:
        rating_change = -1
    if result == 0.5:
        if rating_change > 5:
            rating_change = 5
        elif rating_change < -5:
            rating_change = -5

    new_rating = rating + rating_change
    return round(new_rating)


def finalize_game(game, user_login):
    if not hasattr(game, 'final_results'):
        game.final_results = {}
    if user_login in game.final_results:
        return game.final_results[user_login]
    if not hasattr(game, 'final_rating_changes'):
        game.final_rating_changes = {}
        game.final_result_moves = {}
        if not hasattr(game, 'initial_ratings'):
            game.initial_ratings = {}
            for u in [game.f_user, game.c_user]:
                if u and (not u.startswith('ghost')):
                    user_data = base.get_user_by_login(u)
                    game.initial_ratings[u] = user_data["rang"]
                else:
                    game.initial_ratings[u] = 0
        if game.status == 'w3':
            winner_color = 'w'
        elif game.status == 'b3':
            winner_color = 'b'
        elif game.status == 'n':
            winner_color = None
        else:
            winner_color = None
        for u in [game.f_user, game.c_user]:
            if not u:
                continue
            user_is_ghost = u.startswith('ghost')
            user_old_rating = game.initial_ratings.get(u, 0)
            opp = game.f_user if u == game.c_user else game.c_user
            opponent_old_rating = game.initial_ratings.get(opp, 0) if opp else 0
            user_color = game.user_color(u)
            if game.status == 'n':
                result_move = 'draw'
                user_score = 0.5
            else:
                if winner_color == user_color:
                    result_move = 'win'
                    user_score = 1.0
                else:
                    result_move = 'lose'
                    user_score = 0.0
            if (not user_is_ghost) and opp and opp.startswith('ghost'):
                if result_move == 'win':
                    rating_change = 20
                elif result_move == 'lose':
                    rating_change = -20
                else:
                    rating_change = 0
                new_rating = user_old_rating + rating_change
            else:
                new_rating = calculate_new_rating(user_old_rating, opponent_old_rating, user_score, base_K=20)
                new_rating = max(0, new_rating)
                rating_change = new_rating - user_old_rating
            game.final_rating_changes[u] = rating_change
            game.final_result_moves[u] = result_move
            if not user_is_ghost:
                base.update_user_rang(u, rating_change)
                import datetime
                date_end = datetime.datetime.now().isoformat()
                base.add_completed_game(u, game.game_id, date_end, user_old_rating, new_rating, rating_change, result_move)
        game.rank_updated = True
        update_game_status_in_db(game.game_id, 'completed')
        clear_move_status(game.game_id)
        if not hasattr(game, 'persisted'):
            base.persist_game_data(game.game_id)
            game.persisted = True
    result_move = game.final_result_moves.get(user_login, None)
    rating_change = game.final_rating_changes.get(user_login, 0)
    if result_move in ('win', 'draw'):
        points_gained = rating_change if rating_change > 0 else 0
    else:
        points_gained = rating_change
    result = (result_move, points_gained)
    game.final_results[user_login] = result
    return result

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
        for step in range(1, abs(dest_x - x)):
            current_x = x + dx * step
            current_y = y + dy * step
            piece_at_square = get_piece_at(new_pieces, current_x, current_y)
            if piece_at_square:
                if piece_at_square['color'] != selected_piece['color']:
                    new_pieces.remove(piece_at_square)
                    captured = True
                    captured_pieces.append({'x': current_x, 'y': current_y})
                break
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
                'multiple_capture': True,
                'next_capture_piece': moved_piece.copy(),
                'promotion': promotion_occurred
            }
    game.must_capture_piece = None
    return {
        'move_result': 'valid',
        'new_pieces': new_pieces,
        'captured': captured,
        'captured_pieces': captured_pieces,
        'multiple_capture': False,
        'promotion': promotion_occurred
    }


def check_and_update_big_road(game, pieces, current_player, captured):
    """
    Если в окончательной стадии партии один участник имеет не менее трёх дамок (при этом у него может быть ещё и простые шашки),
    а у соперника всего одна шашка (которая является дамкой),
    то считается, что установлен принцип "большой дороги".

    Если с момента установления такого соотношения сил игрок (текущий ходящий)
    не совершает взятие дамки соперника (captured == False) в течение 15 своих ходов,
    то его позиция считается недостаточно «конвертированной» – игра завершается присуждением победы сопернику.

    Для белых (current_player == 'w'):
      - если количество дамок у белых (count_white) >= 3,
      - а у чёрных всего одна шашка (total_black == 1, и эта шашка – дамка),
    то если в ходе не произошло взятия, увеличивается счетчик big_road_counter_w.
    При достижении 15, статус игры устанавливается как 'b3' (победа чёрных).

    Аналогично для чёрных.
    """
    count_white = sum(1 for p in pieces if p['color'] == 0 and p.get('is_king', False))
    total_white = sum(1 for p in pieces if p['color'] == 0)
    count_black = sum(1 for p in pieces if p['color'] == 1 and p.get('is_king', False))
    total_black = sum(1 for p in pieces if p['color'] == 1)
    if current_player == 'w':
        if count_white >= 3 and total_black == 1 and count_black == 1:
            if not captured:
                game.big_road_counter_w += 1
            else:
                game.big_road_counter_w = 0
            if game.big_road_counter_w >= 15:
                game.status = 'b3'
        else:
            game.big_road_counter_w = 0
    elif current_player == 'b':
        if count_black >= 3 and total_white == 1 and count_white == 1:
            if not captured:
                game.big_road_counter_b += 1
            else:
                game.big_road_counter_b = 0
            if game.big_road_counter_b >= 15:
                game.status = 'w3'
        else:
            game.big_road_counter_b = 0


def compute_position_signature(pieces, current_player):
    """
    Вычисляет строковую сигнатуру для текущего положения:
    — сортируем шашки по x, y и режиму (обычная или дамка),
    — объединяем информацию о каждой шашке и добавляем сторону, которая ходит.
    """
    sorted_pieces = sorted(pieces, key=lambda p: (p['x'], p['y'], p.get('mode', 'p')))
    rep = ",".join(f"{p['color']}-{p['x']}-{p['y']}-{p.get('mode', 'p')}" for p in sorted_pieces)
    rep += f":{current_player}"
    return rep
