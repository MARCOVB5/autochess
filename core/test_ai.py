import tempfile
import unittest
from pathlib import Path

from ai_player import MiniChessAI
from minichess import MiniChess


class MiniChessRulesTest(unittest.TestCase):
    def test_white_cannot_expose_its_king(self):
        game = MiniChess()
        game.board = [
            ['r', '.', '.', 'k'],
            ['.', '.', '.', '.'],
            ['R', '.', '.', '.'],
            ['K', '.', '.', '.'],
        ]
        game.king_positions = {'w': (3, 0), 'b': (0, 3)}
        game.current_player = 'w'

        self.assertNotIn((2, 1), game.get_valid_moves((2, 0)))

    def test_ignore_check_rule_applies_to_both_players(self):
        game = MiniChess(ignore_check_rule=True)
        game.board = [
            ['k', '.', '.', 'r'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', 'R'],
            ['.', '.', '.', 'K'],
        ]
        game.king_positions = {'w': (3, 3), 'b': (0, 0)}
        game.current_player = 'w'
        self.assertIn((2, 2), game.get_valid_moves((2, 3)))

        game.board = [
            ['k', '.', '.', 'K'],
            ['r', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['R', '.', '.', '.'],
        ]
        game.king_positions = {'w': (0, 3), 'b': (0, 0)}
        game.current_player = 'b'
        self.assertIn((1, 1), game.get_valid_moves((1, 0)))

    def test_check_does_not_end_pedagogical_game(self):
        game = MiniChess(ignore_check_rule=True)
        game.board = [
            ['k', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['r', '.', '.', '.'],
            ['K', '.', '.', '.'],
        ]
        game.king_positions = {'w': (3, 0), 'b': (0, 0)}
        game.current_player = 'w'

        self.assertTrue(game.is_check('w'))
        self.assertFalse(game.is_checkmate())
        self.assertFalse(game.is_game_over())


class MiniChessAITest(unittest.TestCase):
    def make_ai(self, **kwargs):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        model_path = Path(temporary_directory.name) / "model.pkl"
        return MiniChessAI(model_path=model_path, autoload=False, seed=1, **kwargs)

    def test_q_value_influences_policy(self):
        game = MiniChess()
        game.current_player = 'b'
        ai = self.make_ai(epsilon=0.0)
        state = game.get_state_representation()
        moves = game.get_all_valid_moves('b')
        preferred = moves[-1]
        ai.q_table[state] = {
            ai.action_to_key(move): -1.0 for move in moves
        }
        ai.q_table[state][ai.action_to_key(preferred)] = 10.0

        self.assertEqual(preferred, ai.get_move(game, training=False))

    def test_visible_progression_changes_behavior(self):
        game = MiniChess(ignore_check_rule=True)
        game.board = [
            ['k', '.', '.', '.'],
            ['r', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['K', '.', '.', '.'],
        ]
        game.king_positions = {'w': (3, 0), 'b': (0, 0)}
        game.current_player = 'b'
        ai = self.make_ai(epsilon=0.0)
        king_capture = ((1, 0), (3, 0))

        novice_move = ai.get_move(
            game,
            training=False,
            pedagogical=True,
        )
        self.assertNotEqual(king_capture, novice_move)

        ai.games_played = 15
        experienced_move = ai.get_move(
            game,
            training=False,
            pedagogical=False,
        )
        self.assertEqual(king_capture, experienced_move)

    def test_experienced_ai_answers_an_immediate_king_threat(self):
        game = MiniChess(ignore_check_rule=True)
        game.board = [
            ['k', '.', '.', '.'],
            ['.', 'r', '.', '.'],
            ['.', '.', '.', '.'],
            ['R', '.', '.', 'K'],
        ]
        game.king_positions = {'w': (3, 3), 'b': (0, 0)}
        game.current_player = 'b'
        ai = self.make_ai()
        ai.games_played = 20
        unsafe_move = ((1, 1), (1, 3))
        state = game.get_state_representation()
        ai.q_table[state] = {
            ai.action_to_key(unsafe_move): 100.0,
        }

        self.assertTrue(game.is_check('b'))
        move = ai.get_move(game, training=False, pedagogical=True)
        game.make_move(move)
        self.assertFalse(game.is_check('b'))
        self.assertEqual(0.0, ai.get_exploration_rate())

    def test_terminal_reward_updates_entire_episode(self):
        ai = self.make_ai(alpha=1.0, gamma=0.5, epsilon=0.0)
        state_one = ("state-one", "b")
        state_two = ("state-two", "b")
        move_one = ((0, 0), (1, 0))
        move_two = ((1, 0), (2, 0))
        ai.state_history = [
            (state_one, move_one, (move_one,)),
            (state_two, move_two, (move_two,)),
        ]

        ai.learn(None, 1.0)

        self.assertEqual(1.0, ai.get_q_value(state_two, move_two))
        self.assertEqual(0.5, ai.get_q_value(state_one, move_one))

    def test_model_path_is_independent_from_working_directory(self):
        ai = MiniChessAI(autoload=False)
        expected = Path(__file__).resolve().parent / "models" / "minichess_ai_model.pkl"
        self.assertEqual(expected, Path(ai.model_path))


if __name__ == "__main__":
    unittest.main()
