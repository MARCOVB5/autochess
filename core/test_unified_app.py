import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from ai_player import MiniChessAI
from button_reader import parse_button_command
from minichess import MiniChess
from unified_app import AutoChessApp, BOARD_RECT


class PhysicalButtonReaderTest(unittest.TestCase):
    def test_button_protocol(self):
        self.assertEqual("0", parse_button_command("BUTTON_0"))
        self.assertEqual("2", parse_button_command("BUTTON_2"))
        self.assertIsNone(parse_button_command("BUTTON_9"))
        self.assertIsNone(parse_button_command("Arduino pronto"))


class UnifiedAppTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.app = AutoChessApp(simulate=True)
        self.app.controller.ai_player = MiniChessAI(
            model_path=Path(self.temporary_directory.name) / "model.pkl",
            autoload=False,
            seed=1,
        )
        self.app.controller.chess_game = MiniChess(ignore_check_rule=True)

    def tearDown(self):
        self.app.close()
        self.temporary_directory.cleanup()

    def test_simulated_human_and_ai_turn(self):
        square_size = BOARD_RECT.width // 4

        def center(row, col):
            return (
                BOARD_RECT.x + col * square_size + square_size // 2,
                BOARD_RECT.y + row * square_size + square_size // 2,
            )

        self.app._handle_simulated_board_click(center(2, 0))
        self.assertIn((1, 1), self.app.valid_moves)
        self.app._handle_simulated_board_click(center(1, 1))

        deadline = time.time() + 2
        while self.app.busy and time.time() < deadline:
            self.app._handle_background_events()
            time.sleep(0.01)

        self.assertFalse(self.app.busy)
        self.assertEqual("w", self.app.game.current_player)
        self.assertIsNotNone(self.app.last_move)

    def test_status_text_is_clipped_to_panel(self):
        text = "mensagem muito longa " * 30
        fitted = self.app._fit_text(text, self.app.small_font, 560)
        self.assertLessEqual(self.app.small_font.size(fitted)[0], 560)
        self.assertTrue(fitted.endswith("…"))


if __name__ == "__main__":
    unittest.main()
