import unittest

class DummyGame:
    def __init__(self):
        self.status = "w1"
        self.big_road_counter_w = 0
        self.big_road_counter_b = 0

def check_and_update_big_road(game, pieces, current_player, captured):
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

class TestBigRoadRule(unittest.TestCase):
    def setUp(self):
        self.pieces = [
            {"color": 0, "x": 2, "y": 3, "mode": "k", "is_king": True},
            {"color": 0, "x": 4, "y": 3, "mode": "k", "is_king": True},
            {"color": 0, "x": 6, "y": 3, "mode": "k", "is_king": True},
            {"color": 1, "x": 5, "y": 2, "mode": "k", "is_king": True}
        ]
        self.game = DummyGame()
        self.current_player = 'w'

    def test_big_road_counter_without_capture(self):
        for move in range(16):
            check_and_update_big_road(self.game, self.pieces, self.current_player, captured=False)
            self.assertEqual(self.game.big_road_counter_w, move + 1)
            if move < 14:
                self.assertEqual(self.game.status, "w1")
        self.assertEqual(self.game.status, "b3")

    def test_reset_counter_after_capture(self):
        for move in range(5):
            check_and_update_big_road(self.game, self.pieces, self.current_player, captured=False)
        self.assertEqual(self.game.big_road_counter_w, 5)
        check_and_update_big_road(self.game, self.pieces, self.current_player, captured=True)
        self.assertEqual(self.game.big_road_counter_w, 0)
        self.assertEqual(self.game.status, "w1")

if __name__ == '__main__':
    unittest.main()
