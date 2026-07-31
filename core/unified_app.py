"""Painel unificado do AutoChess para interface, CV, IA, CNC e botões."""

import argparse
import ast
import queue
import threading

import cv2
import pygame

import hardware_config as hardware
from button_reader import PhysicalButtonReader, drain_events
from main import OptimizedGameController, is_valid_move_format
from minichess import MiniChess


WINDOW_SIZE = (1440, 820)
BOARD_RECT = pygame.Rect(40, 120, 560, 560)
CV_RECT = pygame.Rect(640, 120, 760, 570)
ACTION_BUTTONS = {
    "0": pygame.Rect(640, 720, 230, 58),
    "1": pygame.Rect(885, 720, 230, 58),
    "2": pygame.Rect(1130, 720, 230, 58),
}
COLORS = {
    "background": (238, 241, 245),
    "panel": (255, 255, 255),
    "text": (31, 41, 55),
    "muted": (100, 116, 139),
    "light_square": (239, 217, 181),
    "dark_square": (181, 136, 99),
    "selected": (250, 204, 21),
    "valid": (34, 197, 94),
    "danger": (239, 68, 68),
    "primary": (37, 99, 235),
    "secondary": (71, 85, 105),
}
PIECE_LABELS = {
    "p": "P",
    "r": "T",
    "q": "D",
    "k": "R",
    "P": "P",
    "R": "T",
    "Q": "D",
    "K": "R",
}


class AutoChessApp:
    def __init__(
        self,
        simulate=False,
        use_camera=True,
        use_cnc=True,
        use_buttons=True,
        cv_image=None,
    ):
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("AutoChess")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("dejavusans", 24)
        self.small_font = pygame.font.SysFont("dejavusans", 18)
        self.large_font = pygame.font.SysFont("dejavusans", 34, bold=True)
        self.piece_font = pygame.font.SysFont("dejavusans", 42, bold=True)

        self.simulate = simulate
        self.use_camera = use_camera and not simulate
        self.use_cnc = use_cnc and not simulate
        self.use_buttons = use_buttons and not simulate
        self.cv_image = cv_image
        self.events = queue.Queue()
        self.controller = OptimizedGameController()
        self.button_reader = PhysicalButtonReader(self.events)
        self.running = True
        self.busy = False
        self.selected_square = None
        self.valid_moves = []
        self.last_cv_surface = None
        self.last_move = None
        self.status = "Inicializando..."
        self.game_over = False
        self.model_changed = False

    @property
    def game(self):
        return self.controller.chess_game

    @property
    def ai(self):
        return self.controller.ai_player

    def initialize(self):
        try:
            initialized = self.controller.initialize_game_resources(
                use_cnc=self.use_cnc,
                use_camera=self.use_camera,
            )
            if not initialized:
                raise RuntimeError("Falha ao inicializar os recursos do jogo.")

            if self.use_buttons:
                if self.button_reader.start():
                    button_status = f"botões em {self.button_reader.port}"
                else:
                    button_status = "botões desativados"
            else:
                button_status = "botões desativados"

            mode = "simulação" if self.simulate else "hardware"
            self.status = f"Pronto — modo {mode}; {button_status}."
            if self.cv_image:
                result = self.controller.vision_system.detect_chess_position_optimized(
                    self.cv_image,
                    include_visualization=True,
                )
                visualization = result.get("visualization") if result else None
                if visualization is not None:
                    self.last_cv_surface = self._cv_to_surface(visualization)
                    self.status = f"Imagem processada: {self.cv_image}"
                else:
                    self.status = f"Não foi possível processar: {self.cv_image}"
        except Exception as error:
            self.status = f"Inicialização incompleta: {error}"
            if self.controller.ai_player is None:
                self.controller.ai_player = self._new_ai()
            if self.controller.chess_game is None:
                self.controller.chess_game = MiniChess(ignore_check_rule=True)

    @staticmethod
    def _new_ai():
        from ai_player import MiniChessAI
        return MiniChessAI()

    def run(self):
        self.initialize()
        while self.running:
            self._handle_pygame_events()
            self._handle_background_events()
            self._draw()
            self.clock.tick(30)
        self.close()

    def _handle_pygame_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                elif event.unicode in {"0", "1", "2"}:
                    self.handle_command(event.unicode)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for command, rect in ACTION_BUTTONS.items():
                    if rect.collidepoint(event.pos):
                        self.handle_command(command)
                        return
                if self.simulate and not self.busy:
                    self._handle_simulated_board_click(event.pos)

    def _handle_background_events(self):
        for event_type, payload in drain_events(self.events):
            if event_type == "button":
                self.handle_command(payload)
            elif event_type == "human_done":
                self.busy = False
                success, message, move, visualization = payload
                self.status = message
                if visualization is not None:
                    self.last_cv_surface = self._cv_to_surface(visualization)
                if success:
                    self.last_move = move
                    self._after_move()
            elif event_type == "ai_done":
                self.busy = False
                success, message, move = payload
                self.status = message
                if success:
                    self.last_move = move
                    self._after_move(start_ai=False)
                elif move is None:
                    result = self.game.get_result()
                    if result is not None:
                        self._finish_game(result)
            elif event_type == "button_log":
                self.status = f"Arduino: {payload}"
            elif event_type == "error":
                self.busy = False
                self.status = payload

    def handle_command(self, command):
        if self.busy:
            return
        if command == "0":
            if self.simulate:
                self.status = "Faça a jogada das brancas no tabuleiro da tela."
            elif not self.use_camera:
                self.status = "A câmera está desativada."
            elif self.game.current_player != "w":
                self.status = "Aguarde a jogada da IA."
            else:
                self.busy = True
                self.status = "Capturando e processando o tabuleiro..."
                threading.Thread(target=self._capture_human_move, daemon=True).start()
        elif command == "1":
            self._new_game()
        elif command == "2":
            self.ai.reset_model()
            self.model_changed = False
            self._new_game()
            self.status = "Aprendizado apagado. Nova partida iniciada."

    def _capture_human_move(self):
        try:
            move_text = self.controller.capture_and_detect_move_optimized(
                include_visualization=True,
            )
            visualization = self.controller.vision_system.last_visualization
            if not is_valid_move_format(move_text):
                self.events.put((
                    "human_done",
                    (False, "Não foi possível identificar uma jogada válida.", None, visualization),
                ))
                return
            move = ast.literal_eval(move_text)
            origin, destination = move
            if destination not in self.game.get_valid_moves(origin):
                self.events.put((
                    "human_done",
                    (False, f"Jogada detectada não é válida: {move}.", move, visualization),
                ))
                return
            self.game.make_move(move)
            self.events.put((
                "human_done",
                (True, f"Jogada humana: {origin} → {destination}", move, visualization),
            ))
        except Exception as error:
            self.events.put(("error", f"Erro ao processar a câmera: {error}"))

    def _handle_simulated_board_click(self, position):
        if self.game_over or self.game.current_player != "w":
            return
        square = self._screen_to_square(position)
        if square is None:
            return
        row, col = square
        piece = self.game.board[row][col]
        if self.selected_square and square in self.valid_moves:
            move = (self.selected_square, square)
            self.game.make_move(move)
            self.last_move = move
            self.selected_square = None
            self.valid_moves = []
            self.status = f"Jogada humana: {move[0]} → {move[1]}"
            self._after_move()
        elif piece != "." and self.game.get_piece_color(piece) == "w":
            self.selected_square = square
            self.valid_moves = self.game.get_valid_moves(square)
        else:
            self.selected_square = None
            self.valid_moves = []

    def _after_move(self, start_ai=True):
        result = self.game.get_result()
        if result is not None:
            self._finish_game(result)
            return
        if start_ai and self.game.current_player == "b":
            self.busy = True
            self.status = "IA está escolhendo a jogada..."
            threading.Thread(target=self._execute_ai_move, daemon=True).start()

    def _execute_ai_move(self):
        try:
            move = self.ai.get_move(self.game)
            if move is None:
                self.events.put(("ai_done", (False, "A IA não possui jogadas.", None)))
                return
            destination = move[1]
            captured = self.game.board[destination[0]][destination[1]] != "."
            if self.use_cnc:
                if not self.controller.controller.control_moves(move, captured):
                    self.events.put((
                        "ai_done",
                        (False, "A CNC não confirmou o movimento.", move),
                    ))
                    return
            self.game.make_move(move)
            self.events.put((
                "ai_done",
                (True, f"Jogada da IA: {move[0]} → {move[1]}", move),
            ))
        except Exception as error:
            self.events.put(("error", f"Erro na jogada da IA: {error}"))

    def _finish_game(self, result):
        self.game_over = True
        reward = -float(result)
        self.ai.learn(self.game, reward)
        self.model_changed = True
        if result == 1:
            self.status = "Fim de jogo — você venceu."
        elif result == -1:
            self.status = "Fim de jogo — a IA venceu."
        else:
            self.status = "Fim de jogo — empate."

    def _new_game(self):
        self.controller.chess_game = MiniChess(ignore_check_rule=True)
        self.selected_square = None
        self.valid_moves = []
        self.last_move = None
        self.game_over = False
        self.busy = False
        self.status = "Nova partida iniciada."

    def _screen_to_square(self, position):
        if not BOARD_RECT.collidepoint(position):
            return None
        square_size = BOARD_RECT.width // 4
        col = (position[0] - BOARD_RECT.x) // square_size
        row = (position[1] - BOARD_RECT.y) // square_size
        return int(row), int(col)

    def _draw(self):
        self.screen.fill(COLORS["background"])
        title = self.large_font.render("AutoChess", True, COLORS["text"])
        self.screen.blit(title, (40, 32))
        mode_text = "SIMULAÇÃO" if self.simulate else "ROBÔ"
        mode = self.small_font.render(mode_text, True, COLORS["primary"])
        self.screen.blit(mode, (250, 45))
        board_heading = self.font.render("Tabuleiro da partida", True, COLORS["text"])
        cv_heading = self.font.render("Visão computacional", True, COLORS["text"])
        self.screen.blit(board_heading, (40, 82))
        self.screen.blit(cv_heading, (640, 82))

        self._draw_board_panel()
        self._draw_cv_panel()
        self._draw_status()
        self._draw_buttons()
        pygame.display.flip()

    def _draw_board_panel(self):
        pygame.draw.rect(self.screen, COLORS["panel"], BOARD_RECT.inflate(20, 20))
        square_size = BOARD_RECT.width // 4
        king_in_check = None
        if self.game.is_check(self.game.current_player):
            king_in_check = self.game.king_positions[self.game.current_player]

        for row in range(4):
            for col in range(4):
                rect = pygame.Rect(
                    BOARD_RECT.x + col * square_size,
                    BOARD_RECT.y + row * square_size,
                    square_size,
                    square_size,
                )
                color = (
                    COLORS["light_square"]
                    if (row + col) % 2 == 0
                    else COLORS["dark_square"]
                )
                if self.selected_square == (row, col):
                    color = COLORS["selected"]
                elif king_in_check == (row, col):
                    color = COLORS["danger"]
                pygame.draw.rect(self.screen, color, rect)
                if (row, col) in self.valid_moves:
                    pygame.draw.circle(
                        self.screen,
                        COLORS["valid"],
                        rect.center,
                        11,
                    )

                piece = self.game.board[row][col]
                if piece != ".":
                    self._draw_piece(piece, rect.center, square_size)

        pygame.draw.rect(self.screen, COLORS["text"], BOARD_RECT, 2)

    def _draw_piece(self, piece, center, square_size):
        is_white = piece.isupper()
        fill = (245, 245, 245) if is_white else (30, 41, 55)
        outline = (30, 41, 55) if is_white else (245, 245, 245)
        radius = int(square_size * 0.31)
        pygame.draw.circle(self.screen, fill, center, radius)
        pygame.draw.circle(self.screen, outline, center, radius, 3)
        label = self.piece_font.render(
            PIECE_LABELS[piece],
            True,
            outline,
        )
        self.screen.blit(label, label.get_rect(center=center))

    def _draw_cv_panel(self):
        pygame.draw.rect(self.screen, COLORS["panel"], CV_RECT)
        if self.last_cv_surface:
            image = self._fit_surface(self.last_cv_surface, CV_RECT.size)
            rect = image.get_rect(center=CV_RECT.center)
            self.screen.blit(image, rect)
        else:
            heading = self.font.render(
                "A última captura do CV aparecerá aqui",
                True,
                COLORS["muted"],
            )
            self.screen.blit(heading, heading.get_rect(center=CV_RECT.center))
        pygame.draw.rect(self.screen, (203, 213, 225), CV_RECT, 2)

    def _draw_status(self):
        turn = "Brancas" if self.game.current_player == "w" else "IA"
        info = f"Vez: {turn}  •  Partidas da IA: {self.ai.games_played}"
        info_surface = self.small_font.render(info, True, COLORS["muted"])
        self.screen.blit(info_surface, (40, 700))
        status_text = self._fit_text(self.status, self.small_font, 560)
        status_surface = self.small_font.render(
            status_text,
            True,
            COLORS["text"],
        )
        self.screen.blit(status_surface, (40, 735))

    def _draw_buttons(self):
        labels = {
            "0": "Ler tabuleiro",
            "1": "Nova partida",
            "2": "Resetar IA",
        }
        for command, rect in ACTION_BUTTONS.items():
            color = (
                COLORS["primary"]
                if command == "0"
                else COLORS["secondary"]
            )
            if self.busy:
                color = (148, 163, 184)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            text = self.font.render(
                f"{command}  {labels[command]}",
                True,
                (255, 255, 255),
            )
            self.screen.blit(text, text.get_rect(center=rect.center))

    @staticmethod
    def _fit_surface(surface, target_size):
        width, height = surface.get_size()
        scale = min(target_size[0] / width, target_size[1] / height)
        size = max(1, int(width * scale)), max(1, int(height * scale))
        return pygame.transform.smoothscale(surface, size)

    @staticmethod
    def _fit_text(text, font, max_width):
        if font.size(text)[0] <= max_width:
            return text
        shortened = text
        while shortened and font.size(shortened + "…")[0] > max_width:
            shortened = shortened[:-1]
        return shortened.rstrip() + "…"

    @staticmethod
    def _cv_to_surface(image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return pygame.image.frombuffer(
            rgb.tobytes(),
            (rgb.shape[1], rgb.shape[0]),
            "RGB",
        ).copy()

    def close(self):
        self.button_reader.close()
        self.controller.cleanup_resources(save_ai_model=self.model_changed)
        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="executa interface, jogo e IA sem câmera, CNC ou botões",
    )
    parser.add_argument("--no-camera", action="store_true")
    parser.add_argument("--no-cnc", action="store_true")
    parser.add_argument("--no-buttons", action="store_true")
    parser.add_argument(
        "--cv-image",
        help="processa uma imagem e mostra o resultado no painel de CV",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = AutoChessApp(
        simulate=args.simulate,
        use_camera=not args.no_camera,
        use_cnc=not args.no_cnc,
        use_buttons=not args.no_buttons,
        cv_image=args.cv_image,
    )
    app.run()


if __name__ == "__main__":
    main()
