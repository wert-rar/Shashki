import unittest


def compute_position_signature(pieces, current_player):
    sorted_pieces = sorted(pieces, key=lambda p: (p['x'], p['y'], p.get('mode', 'p')))
    rep = ",".join(f"{p['color']}-{p['x']}-{p['y']}-{p.get('mode','p')}" for p in sorted_pieces)
    rep += f":{current_player}"
    return rep


class DummyGame:
    def __init__(self):
        self.status = "w1"
        self.position_history = {}


class TestThreefoldRepetition(unittest.TestCase):
    def setUp(self):
        self.pieces = [
            {"color": 0, "x": 2, "y": 3, "mode": "k", "is_king": True},
            {"color": 0, "x": 4, "y": 3, "mode": "k", "is_king": True},
            {"color": 0, "x": 6, "y": 3, "mode": "k", "is_king": True},
            {"color": 0, "x": 0, "y": 3, "mode": "k", "is_king": True},
            {"color": 1, "x": 5, "y": 2, "mode": "k", "is_king": True}
        ]
        self.game = DummyGame()
        self.current_player = 'w'

    def test_compute_signature_consistency(self):
        sig1 = compute_position_signature(self.pieces, self.current_player)
        sig2 = compute_position_signature(self.pieces, self.current_player)
        self.assertEqual(sig1, sig2)

    def test_threefold_repetition_trigger(self):
        sig = compute_position_signature(self.pieces, self.current_player)
        for _ in range(3):
            self.game.position_history[sig] = self.game.position_history.get(sig, 0) + 1
        self.assertGreaterEqual(self.game.position_history[sig], 3)

    def test_repetition_draw_decision(self):
        sig = compute_position_signature(self.pieces, self.current_player)
        self.game.position_history[sig] = 2
        self.game.position_history[sig] += 1
        if self.game.position_history[sig] >= 3:
            self.game.status = "n"
        self.assertEqual(self.game.status, "n")


if __name__ == '__main__':
    unittest.main()
