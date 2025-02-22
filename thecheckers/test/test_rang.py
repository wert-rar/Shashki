import unittest
from unittest.mock import patch
import datetime


# Заглушки для модуля base, имитирующие работу функций с базой данных
class DummyBase:
    @staticmethod
    def get_user_by_login(user):
        return {"rang": 1800}

    @staticmethod
    def update_user_rang(user, rating_change):
        pass

    @staticmethod
    def add_completed_game(user, game_id, date_end, rating_before, new_rating, rating_change, result_move):
        pass


base = DummyBase


def update_game_status_in_db(game_id, new_status):
    return

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
                date_end = datetime.datetime.now().isoformat()
                base.add_completed_game(u, game.game_id, date_end,
                                        user_old_rating, new_rating, rating_change, result_move)
        game.rank_updated = True
        update_game_status_in_db(game.game_id, 'completed')
    result_move = game.final_result_moves.get(user_login, None)
    rating_change = game.final_rating_changes.get(user_login, 0)
    if result_move in ('win', 'draw'):
        points_gained = rating_change if rating_change > 0 else 0
    else:
        points_gained = rating_change
    result = (result_move, points_gained)
    game.final_results[user_login] = result
    return result


# Класс-заглушка для объекта игры
class DummyGame:
    def __init__(self, f_user, c_user, status, game_id="game123"):
        self.f_user = f_user
        self.c_user = c_user
        self.status = status
        self.game_id = game_id
        self.big_road_counter_w = 0
        self.big_road_counter_b = 0
        self.rank_updated = False

    def user_color(self, user):
        if user == self.f_user:
            return "w"
        else:
            return "b"


# ------------------------------------- Раздел 1: Тесты для calculate_new_rating ------------------------------------- #


class TestCalculateNewRating(unittest.TestCase):
    # Для diff < 150 (например, diff = 50)
    def test_diff_less_150_win(self):
        new_rating = calculate_new_rating(1800, 1850, 1.0)
        print("Раздел 1.1: diff < 150, победа: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating > 1800)

    def test_diff_less_150_loss(self):
        new_rating = calculate_new_rating(1800, 1850, 0.0)
        print("Раздел 1.2: diff < 150, поражение: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating < 1800)

    # Для diff от 150 до 300 (например, diff = 200)
    def test_diff_150_300_win(self):
        new_rating = calculate_new_rating(1800, 2000, 1.0)
        print("Раздел 1.3: diff 150-300, победа: начальный рейтинг 1800, новый =", new_rating)
        self.assertEqual(new_rating, 1823)

    def test_diff_150_300_loss(self):
        new_rating = calculate_new_rating(1800, 2000, 0.0)
        print("Раздел 1.4: diff 150-300, поражение: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating < 1800)

    # Для diff от 300 до 550 (например, diff = 400)
    def test_diff_300_550_win(self):
        new_rating = calculate_new_rating(1800, 2200, 1.0)
        print("Раздел 1.5: diff 300-550, победа: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating > 1800)

    def test_diff_300_550_loss(self):
        new_rating = calculate_new_rating(1800, 2200, 0.0)
        print("Раздел 1.6: diff 300-550, поражение: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating < 1800)

    # Для diff >= 550 (например, diff = 600)
    def test_diff_ge_550_win(self):
        new_rating = calculate_new_rating(1800, 2400, 1.0)
        print("Раздел 1.7: diff >= 550, победа: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating > 1800)

    def test_diff_ge_550_loss(self):
        new_rating = calculate_new_rating(1800, 2400, 0.0)
        print("Раздел 1.8: diff >= 550, поражение: начальный рейтинг 1800, новый =", new_rating)
        self.assertTrue(new_rating < 1800)

    def test_draw_positive(self):
        new_rating = calculate_new_rating(1800, 2400, 0.5)
        change = new_rating - 1800
        print("Раздел 1.9: ничья (андердог): изменение =", change)
        self.assertTrue(change <= 5)

    def test_draw_negative(self):
        new_rating = calculate_new_rating(2400, 1800, 0.5)
        change = new_rating - 2400
        print("Раздел 1.10: ничья (фаворит): изменение =", change)
        self.assertTrue(change >= -5)


# ----------------------------------------  Раздел 2: Тесты для finalize_game  --------------------------------------- #


class TestFinalizeGame(unittest.TestCase):
    @patch(__name__ + '.update_game_status_in_db')
    @patch.object(base, 'add_completed_game')
    @patch.object(base, 'update_user_rang')
    @patch.object(base, 'get_user_by_login')
    def test_finalize_game_draw(self, mock_get_user_by_login, mock_update_user_rang,
                                mock_add_completed_game, mock_update_game_status_in_db):
        print("\nРаздел 2.1: finalize_game для ничьей")
        mock_get_user_by_login.side_effect = lambda user: {"rang": 1800}
        game = DummyGame("user1", "user2", "n")
        result = finalize_game(game, "user1")
        print("Результат для user1:", result)
        self.assertEqual(result, ("draw", 0))
        result_cached = finalize_game(game, "user1")
        self.assertEqual(result_cached, ("draw", 0))
        mock_update_user_rang.assert_any_call("user1", unittest.mock.ANY)
        mock_update_user_rang.assert_any_call("user2", unittest.mock.ANY)
        mock_update_game_status_in_db.assert_called_with(game.game_id, 'completed')
        self.assertTrue(mock_add_completed_game.called)

    @patch(__name__ + '.update_game_status_in_db')
    @patch.object(base, 'add_completed_game')
    @patch.object(base, 'update_user_rang')
    @patch.object(base, 'get_user_by_login')
    def test_finalize_game_white_win(self, mock_get_user_by_login, mock_update_game_status_in_db):
        print("\nРаздел 2.2: finalize_game для выигрыша белых")

        def get_user_data(user):
            if user == "user1":
                return {"rang": 1800}
            elif user == "user2":
                return {"rang": 1900}
            return {"rang": 0}

        mock_get_user_by_login.side_effect = get_user_data
        game = DummyGame("user1", "user2", "w3")
        result_user1 = finalize_game(game, "user1")
        result_user2 = finalize_game(game, "user2")
        print("Результат для user1:", result_user1, "| начальный рейтинг 1800 -> новый =", 1800 + result_user1[1])
        print("Результат для user2:", result_user2, "| начальный рейтинг 1900 -> новый =", 1900 + result_user2[1])
        self.assertEqual(result_user1, ("win", 13))
        self.assertEqual(result_user2, ("lose", -13))
        mock_update_game_status_in_db.assert_called_with(game.game_id, 'completed')

    @patch(__name__ + '.update_game_status_in_db')
    @patch.object(base, 'add_completed_game')
    @patch.object(base, 'update_user_rang')
    @patch.object(base, 'get_user_by_login')
    def test_finalize_game_ghost_opponent(self, mock_get_user_by_login, mock_update_game_status_in_db):
        print("\nРаздел 2.3: finalize_game с ghost-противником")

        def get_user_data(user):
            if user == "user1":
                return {"rang": 1800}
            return {"rang": 0}

        mock_get_user_by_login.side_effect = get_user_data
        game = DummyGame("user1", "ghost123", "w3")
        result_user1 = finalize_game(game, "user1")
        result_ghost = finalize_game(game, "ghost123")
        print("Результат для user1:", result_user1)
        print("Результат для ghost123:", result_ghost)
        self.assertEqual(result_user1, ("win", 20))
        self.assertEqual(result_ghost, ("lose", 0))
        mock_update_game_status_in_db.assert_called_with(game.game_id, 'completed')


# -------------------------------------- Раздел 3: Дополнительные симуляции игр -------------------------------------- #


def run_simulations():
    print("\n------------------------------ Раздел 3.1: Победа user1 (белые) ------------------------------")
    print("Сценарий 1: 'user1' (10) выигрывает против 'user2' (1000)")
    game1 = DummyGame("user1", "user2", "w3", game_id="game_test_001")
    game1.initial_ratings = {"user1": 10, "user2": 1000}
    result_user1_game1 = finalize_game(game1, "user1")
    result_user2_game1 = finalize_game(game1, "user2")
    print(f"Для user1: начальный = 10, изменение = {result_user1_game1[1]}, итог = {10 + result_user1_game1[1]}")
    print(f"Для user2: начальный = 1000, изменение = {result_user2_game1[1]}, итог = {1000 + result_user2_game1[1]}")

    print("\nСценарий 2: 'user1' (50) выигрывает против 'user2' (800)")
    game1A = DummyGame("user1", "user2", "w3", game_id="game_test_001A")
    game1A.initial_ratings = {"user1": 50, "user2": 800}
    result_user1_game1A = finalize_game(game1A, "user1")
    result_user2_game1A = finalize_game(game1A, "user2")
    print(f"Для user1: начальный = 50, изменение = {result_user1_game1A[1]}, итог = {50 + result_user1_game1A[1]}")
    print(f"Для user2: начальный = 800, изменение = {result_user2_game1A[1]}, итог = {800 + result_user2_game1A[1]}")

    print("\nСценарий 3: 'user1' (300) выигрывает против 'user2' (1000)")
    game1B = DummyGame("user1", "user2", "w3", game_id="game_test_001B")
    game1B.initial_ratings = {"user1": 300, "user2": 1000}
    result_user1_game1B = finalize_game(game1B, "user1")
    result_user2_game1B = finalize_game(game1B, "user2")
    print(f"Для user1: начальный = 300, изменение = {result_user1_game1B[1]}, итог = {300 + result_user1_game1B[1]}")
    print(f"Для user2: начальный = 1000, изменение = {result_user2_game1B[1]}, итог = {1000 + result_user2_game1B[1]}")


# -------------------------------------------------------------------------------------------------------------------- #


    print("\n------------------------------ Раздел 3.2: Победа user2 (чёрные) ------------------------------")
    print("Сценарий 1: 'user2' (1000) выигрывает против 'user1' (10)")
    game2 = DummyGame("user1", "user2", "b3", game_id="game_test_002")
    game2.initial_ratings = {"user1": 10, "user2": 1000}
    result_user1_game2 = finalize_game(game2, "user1")
    result_user2_game2 = finalize_game(game2, "user2")
    print(f"Для user1: начальный = 10, изменение = {result_user1_game2[1]}, итог = {10 + result_user1_game2[1]}")
    print(f"Для user2: начальный = 1000, изменение = {result_user2_game2[1]}, итог = {1000 + result_user2_game2[1]}")

    print("\nСценарий 2: 'user2' (800) выигрывает против 'user1' (100)")
    game2A = DummyGame("user1", "user2", "b3", game_id="game_test_002A")
    game2A.initial_ratings = {"user1": 100, "user2": 800}
    result_user1_game2A = finalize_game(game2A, "user1")
    result_user2_game2A = finalize_game(game2A, "user2")
    print(f"Для user1: начальный = 100, изменение = {result_user1_game2A[1]}, итог = {100 + result_user1_game2A[1]}")
    print(f"Для user2: начальный = 800, изменение = {result_user2_game2A[1]}, итог = {800 + result_user2_game2A[1]}")

    print("\nСценарий 3: 'user2' (1200) выигрывает против 'user1' (200)")
    game2B = DummyGame("user1", "user2", "b3", game_id="game_test_002B")
    game2B.initial_ratings = {"user1": 200, "user2": 1200}
    result_user1_game2B = finalize_game(game2B, "user1")
    result_user2_game2B = finalize_game(game2B, "user2")
    print(f"Для user1: начальный = 200, изменение = {result_user1_game2B[1]}, итог = {200 + result_user1_game2B[1]}")
    print(f"Для user2: начальный = 1200, изменение = {result_user2_game2B[1]}, итог = {1200 + result_user2_game2B[1]}")


# -------------------------------------------------------------------------------------------------------------------- #


    print("\n------------------------------ Раздел 3.3: Ничья ------------------------------")
    print("Сценарий 1: ничья, начальный рейтинг 500 для обоих")
    game3 = DummyGame("user1", "user2", "n", game_id="game_test_003")
    game3.initial_ratings = {"user1": 500, "user2": 500}
    result_user1_game3 = finalize_game(game3, "user1")
    result_user2_game3 = finalize_game(game3, "user2")
    print(f"Для user1: начальный = 500, изменение = {result_user1_game3[1]}, итог = {500 + result_user1_game3[1]}")
    print(f"Для user2: начальный = 500, изменение = {result_user2_game3[1]}, итог = {500 + result_user2_game3[1]}")

    print("\nСценарий 2: ничья, начальный рейтинг 1200 для обоих")
    game3A = DummyGame("user1", "user2", "n", game_id="game_test_003A")
    game3A.initial_ratings = {"user1": 1200, "user2": 1200}
    result_user1_game3A = finalize_game(game3A, "user1")
    result_user2_game3A = finalize_game(game3A, "user2")
    print(f"Для user1: начальный = 1200, изменение = {result_user1_game3A[1]}, итог = {1200 + result_user1_game3A[1]}")
    print(f"Для user2: начальный = 1200, изменение = {result_user2_game3A[1]}, итог = {1200 + result_user2_game3A[1]}")

    print("\nСценарий 3: ничья, начальный рейтинг 2000 для user1 и 1800 для user2")
    game3B = DummyGame("user1", "user2", "n", game_id="game_test_003B")
    game3B.initial_ratings = {"user1": 2000, "user2": 1800}
    result_user1_game3B = finalize_game(game3B, "user1")
    result_user2_game3B = finalize_game(game3B, "user2")
    print(f"Для user1: начальный = 2000, изменение = {result_user1_game3B[1]}, итог = {2000 + result_user1_game3B[1]}")
    print(f"Для user2: начальный = 1800, изменение = {result_user2_game3B[1]}, итог = {1800 + result_user2_game3B[1]}")


# -------------------------------------------------------------------------------------------------------------------- #


    print("\n------------------------------ Раздел 3.4: Игра с ghost ------------------------------")
    print("Сценарий 1: 'user1' (800) против ghost (0)")
    game4 = DummyGame("user1", "ghost123", "w3", game_id="game_test_004")
    game4.initial_ratings = {"user1": 800, "ghost123": 0}
    result_user1_game4 = finalize_game(game4, "user1")
    result_ghost_game4 = finalize_game(game4, "ghost123")
    print(f"Для user1: начальный = 800, изменение = {result_user1_game4[1]}, итог = {800 + result_user1_game4[1]}")
    print(f"Для ghost123: начальный = 0, изменение = {result_ghost_game4[1]}, итог = {0 + result_ghost_game4[1]}")

    print("\nСценарий 2: 'user1' (1000) против ghost (0)")
    game4A = DummyGame("user1", "ghost123", "w3", game_id="game_test_004A")
    game4A.initial_ratings = {"user1": 1000, "ghost123": 0}
    result_user1_game4A = finalize_game(game4A, "user1")
    result_ghost_game4A = finalize_game(game4A, "ghost123")
    print(f"Для user1: начальный = 1000, изменение = {result_user1_game4A[1]}, итог = {1000 + result_user1_game4A[1]}")
    print(f"Для ghost123: начальный = 0, изменение = {result_ghost_game4A[1]}, итог = {0 + result_ghost_game4A[1]}")

    print("\nСценарий 3: 'user1' (300) против ghost (0)")
    game4B = DummyGame("user1", "ghost123", "w3", game_id="game_test_004B")
    game4B.initial_ratings = {"user1": 300, "ghost123": 0}
    result_user1_game4B = finalize_game(game4B, "user1")
    result_ghost_game4B = finalize_game(game4B, "ghost123")
    print(f"Для user1: начальный = 300, изменение = {result_user1_game4B[1]}, итог = {300 + result_user1_game4B[1]}")
    print(f"Для ghost123: начальный = 0, изменение = {result_ghost_game4B[1]}, итог = {0 + result_ghost_game4B[1]}")


# -------------------------------------------------------------------------------------------------------------------- #


    print("\n------------------------------ Раздел 3.5: Плохая игра (неверный статус) ------------------------------")
    print("Сценарий 1: 'user1' и 'user2' (1000) играют с статусом 'invalid'")
    game5 = DummyGame("user1", "user2", "invalid", game_id="game_test_005")
    game5.initial_ratings = {"user1": 1000, "user2": 1000}
    result_user1_game5 = finalize_game(game5, "user1")
    result_user2_game5 = finalize_game(game5, "user2")
    print(f"Для user1: начальный = 1000, изменение = {result_user1_game5[1]}, итог = {1000 + result_user1_game5[1]}")
    print(f"Для user2: начальный = 1000, изменение = {result_user2_game5[1]}, итог = {1000 + result_user2_game5[1]}")
    print("Примечание: При неизвестном статусе игра трактуется как поражение для обеих сторон.")

    print("\nСценарий 2: 'user1' (800) и 'user2' (1200) играют с статусом 'invalid'")
    game5A = DummyGame("user1", "user2", "invalid", game_id="game_test_005A")
    game5A.initial_ratings = {"user1": 800, "user2": 1200}
    result_user1_game5A = finalize_game(game5A, "user1")
    result_user2_game5A = finalize_game(game5A, "user2")
    print(f"Для user1: начальный = 800, изменение = {result_user1_game5A[1]}, итог = {800 + result_user1_game5A[1]}")
    print(f"Для user2: начальный = 1200, изменение = {result_user2_game5A[1]}, итог = {1200 + result_user2_game5A[1]}")

    print("\nСценарий 3: 'user1' (2000) и 'user2' (1800) играют с статусом 'invalid'")
    game5B = DummyGame("user1", "user2", "invalid", game_id="game_test_005B")
    game5B.initial_ratings = {"user1": 2000, "user2": 1800}
    result_user1_game5B = finalize_game(game5B, "user1")
    result_user2_game5B = finalize_game(game5B, "user2")
    print(f"Для user1: начальный = 2000, изменение = {result_user1_game5B[1]}, итог = {2000 + result_user1_game5B[1]}")
    print(f"Для user2: начальный = 1800, изменение = {result_user2_game5B[1]}, итог = {1800 + result_user2_game5B[1]}")
    print("Примечание: При неизвестном статусе игра трактуется как поражение для обеих сторон.")


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(TestCalculateNewRating))
    runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(TestFinalizeGame))

    run_simulations()
