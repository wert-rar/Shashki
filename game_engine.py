import datetime

from Client import base
from Client.game import remove_game_in_db, update_game_status_in_db


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
            if 0 <= end_x < 8 and 0 <= end_y < 8 and captured_piece and captured_piece['color'] != piece['color'] and not target_pos:
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
                user_rank_before = base.get_user_by_login(user_login)["rang"]
                date_end = datetime.datetime.now().isoformat()
                base.add_completed_game(user_login, game.game_id, date_end, user_rank_before, user_rank_before, 0, result_move)
            opponent_login = game.f_user if game.f_user != user_login else game.c_user
            if opponent_login and not opponent_login.startswith('ghost'):
                opp_rank_before = base.get_user_by_login(opponent_login)["rang"]
                date_end = datetime.datetime.now().isoformat()
                base.add_completed_game(opponent_login, game.game_id, date_end, opp_rank_before, opp_rank_before, 0, result_move)
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
            user_rank_before = base.get_user_by_login(user_login)["rang"]
            if result_move == 'win':
                base.update_user_rang(user_login, points_gained)
                base.update_user_stats(user_login, wins=1)
                if not opponent_is_ghost:
                    base.update_user_stats(opponent_login, losses=1)
            elif result_move == 'lose':
                base.update_user_stats(user_login, losses=1)
            elif result_move == 'draw':
                base.update_user_rang(user_login, points_gained)
                if not opponent_is_ghost:
                    base.update_user_rang(opponent_login, points_gained)
                base.update_user_stats(user_login, draws=1)
                if not opponent_is_ghost:
                    base.update_user_stats(opponent_login, draws=1)
            user_rank_after = base.get_user_by_login(user_login)["rang"]
            user_rating_change = user_rank_after - user_rank_before
            date_end = datetime.datetime.now().isoformat()
            base.add_completed_game(user_login, game.game_id, date_end, user_rank_before, user_rank_after, user_rating_change, result_move)
        if not opponent_is_ghost:
            opponent_rank_before = base.get_user_by_login(opponent_login)["rang"]
            if result_move == 'win':
                opponent_result_move = 'lose'
                base.update_user_stats(opponent_login, losses=1)
            elif result_move == 'lose':
                opponent_result_move = 'win'
                opponent_points_gained = 10
                base.update_user_rang(opponent_login, opponent_points_gained)
                base.update_user_stats(opponent_login, wins=1)
            elif result_move == 'draw':
                opponent_result_move = 'draw'
                opponent_points_gained = 5
                base.update_user_rang(opponent_login, opponent_points_gained)
                base.update_user_stats(opponent_login, draws=1)
            else:
                opponent_result_move = None
            if opponent_result_move is not None:
                opponent_rank_after = base.get_user_by_login(opponent_login)["rang"]
                opponent_rating_change = opponent_rank_after - opponent_rank_before
                date_end = datetime.datetime.now().isoformat()
                base.add_completed_game(opponent_login, game.game_id, date_end, opponent_rank_before, opponent_rank_after, opponent_rating_change, opponent_result_move)
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
