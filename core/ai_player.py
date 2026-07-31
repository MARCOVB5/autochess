import os
import pickle
import random
from copy import deepcopy
from pathlib import Path


class MiniChessAI:
    """Tabular Q-learning agent with a one-ply heuristic fallback."""

    MODEL_VERSION = 2
    PIECE_VALUES = {'p': 1.0, 'r': 5.0, 'q': 9.0, 'k': 100.0}

    def __init__(
        self,
        alpha=0.2,
        gamma=0.95,
        epsilon=0.30,
        model_path=None,
        seed=None,
        autoload=True,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.initial_epsilon = epsilon
        self.q_table = {}
        self.state_history = []
        self.games_played = 0
        self.random = random.Random(seed)
        default_model = Path(__file__).resolve().parent / 'models' / 'minichess_ai_model.pkl'
        self.model_path = str(Path(model_path) if model_path else default_model)
        if autoload:
            self.load_model()

    def get_move(self, game, training=True, pedagogical=None):
        valid_moves = game.get_all_valid_moves(game.current_player)
        if not valid_moves:
            return None

        state = game.get_state_representation()
        if pedagogical is None:
            pedagogical = training

        if pedagogical and self.games_played < 5:
            chosen_move = self._novice_move(game, valid_moves)
        elif pedagogical and self.random.random() < self.get_exploration_rate():
            chosen_move = self.random.choice(valid_moves)
        else:
            chosen_move = self._best_move(game, state, valid_moves)

        if training:
            self.state_history.append((state, chosen_move, tuple(valid_moves)))
        return chosen_move

    def _novice_move(self, game, valid_moves):
        player = game.current_player
        scored_moves = [
            (self._move_heuristic(game, move, player), move)
            for move in valid_moves
        ]
        scored_moves.sort(key=lambda item: item[0])
        weakest = [move for _, move in scored_moves[:min(3, len(scored_moves))]]
        return self.random.choice(weakest)

    def _best_move(self, game, state, valid_moves):
        player = game.current_player
        scored_moves = []
        for move in valid_moves:
            q_value = self.get_q_value(state, move)
            heuristic = self._move_heuristic(game, move, player)
            score = heuristic + (2.0 * q_value)
            scored_moves.append((score, q_value, heuristic, move))

        if self.games_played >= 15:
            safe_moves = [
                item for item in scored_moves
                if self._is_tactically_safe(game, item[3], player)
            ]
            if safe_moves:
                scored_moves = safe_moves

        best_score = max(item[0] for item in scored_moves)
        tied = [item for item in scored_moves if abs(item[0] - best_score) < 1e-9]
        return self.random.choice(tied)[3]

    @staticmethod
    def _is_tactically_safe(game, move, player):
        simulated = deepcopy(game)
        if not simulated.make_move(move):
            return False
        captured = simulated.is_king_captured()
        if captured is not None:
            return captured != player
        return not simulated.is_check(player)

    def _move_heuristic(self, game, move, player):
        simulated = deepcopy(game)
        if not simulated.make_move(move):
            return float('-inf')

        captured = simulated.is_king_captured()
        if captured is not None:
            return 10.0 if captured != player else -10.0

        score = self.evaluate_board(simulated, player) / 100.0
        if simulated.is_check(player):
            score -= 5.0
        return score

    def learn(self, game, reward):
        self.games_played += 1
        if not self.state_history:
            self.save_model()
            return

        for index in range(len(self.state_history) - 1, -1, -1):
            state, action, _ = self.state_history[index]
            current_q = self.get_q_value(state, action)

            if index == len(self.state_history) - 1:
                target = reward
            else:
                next_state, _, next_moves = self.state_history[index + 1]
                next_q = max(
                    (self.get_q_value(next_state, move) for move in next_moves),
                    default=0.0,
                )
                target = self.gamma * next_q

            updated_q = current_q + self.alpha * (target - current_q)
            self.q_table.setdefault(state, {})[self.action_to_key(action)] = updated_q

        self.state_history = []
        self.epsilon = self.get_exploration_rate()
        if self.games_played % 10 == 0:
            self.save_model()

    def get_exploration_rate(self):
        if self.games_played < 5:
            return 1.0
        if self.games_played < 15:
            return 0.55
        return 0.0

    def adjust_learning_parameters(self):
        self.epsilon = self.get_exploration_rate()

    def get_q_value(self, state, action):
        return self.q_table.get(state, {}).get(self.action_to_key(action), 0.0)

    @staticmethod
    def action_to_key(action):
        origin, destination = action
        return (origin[0], origin[1], destination[0], destination[1])

    def save_model(self):
        model_path = Path(self.model_path)
        try:
            model_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'version': self.MODEL_VERSION,
                'q_table': self.q_table,
                'games_played': self.games_played,
                'alpha': self.alpha,
                'gamma': self.gamma,
                'epsilon': self.epsilon,
                'initial_epsilon': self.initial_epsilon,
            }
            temporary_path = model_path.with_suffix(model_path.suffix + '.tmp')
            with temporary_path.open('wb') as model_file:
                pickle.dump(data, model_file)
            os.replace(temporary_path, model_path)
            return True
        except (OSError, pickle.PickleError):
            return False

    def load_model(self):
        model_path = Path(self.model_path)
        if not model_path.exists():
            return False
        try:
            with model_path.open('rb') as model_file:
                data = pickle.load(model_file)
            if data.get('version') != self.MODEL_VERSION:
                return False
            self.q_table = data.get('q_table', {})
            self.games_played = int(data.get('games_played', 0))
            self.alpha = float(data.get('alpha', self.alpha))
            self.gamma = float(data.get('gamma', self.gamma))
            self.initial_epsilon = float(
                data.get('initial_epsilon', data.get('epsilon', self.initial_epsilon))
            )
            self.epsilon = self.get_exploration_rate()
            return True
        except (OSError, EOFError, ValueError, TypeError, pickle.PickleError):
            self.q_table = {}
            self.games_played = 0
            return False

    def reset_model(self):
        self.q_table = {}
        self.games_played = 0
        self.epsilon = self.initial_epsilon
        self.state_history = []
        try:
            Path(self.model_path).unlink(missing_ok=True)
        except OSError:
            pass

    def force_phase(self, phase):
        phase_games = {1: 0, 2: 5, 3: 15}
        if phase not in phase_games:
            raise ValueError("phase must be 1, 2, or 3")
        self.games_played = phase_games[phase]
        self.adjust_learning_parameters()

    def get_strength_description(self):
        if self.games_played < 5:
            return "Iniciante"
        if self.games_played < 15:
            return "Aprendendo"
        return "Experiente"

    def evaluate_board(self, game, player):
        captured = game.is_king_captured()
        if captured is not None:
            return 1000.0 if captured != player else -1000.0

        score = 0.0
        opponent = 'b' if player == 'w' else 'w'
        for row in game.board:
            for piece in row:
                if piece == '.':
                    continue
                value = self.PIECE_VALUES[piece.lower()]
                score += value if game.get_piece_color(piece) == player else -value

        if game.is_check(opponent):
            score += 2.0
        if game.is_check(player):
            score -= 2.0

        return score
