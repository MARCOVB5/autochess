"""Train the black MiniChess agent against a seeded random opponent."""

import argparse
import random
from collections import Counter

from ai_player import MiniChessAI
from minichess import MiniChess


def play_training_game(ai, rng, max_plies):
    game = MiniChess(ignore_check_rule=True)
    for _ in range(max_plies):
        if game.is_game_over():
            break
        moves = game.get_all_valid_moves(game.current_player)
        if not moves:
            break
        if game.current_player == 'w':
            move = rng.choice(moves)
        else:
            move = ai.get_move(game, training=True)
        if move is None or not game.make_move(move):
            raise RuntimeError(f"invalid move selected: {move}")

    result = game.get_result()
    reward = -float(result) if result is not None else 0.0
    ai.learn(game, reward)
    if reward > 0:
        return "black"
    if reward < 0:
        return "white"
    return "draw"


def train(games, model_path=None, seed=0, max_plies=100):
    rng = random.Random(seed)
    ai = MiniChessAI(model_path=model_path, seed=seed)
    results = Counter()
    for _ in range(games):
        results[play_training_game(ai, rng, max_plies)] += 1
    ai.save_model()
    return ai, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--model", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-plies", type=int, default=100)
    args = parser.parse_args()

    ai, results = train(
        games=args.games,
        model_path=args.model,
        seed=args.seed,
        max_plies=args.max_plies,
    )
    states = len(ai.q_table)
    actions = sum(len(values) for values in ai.q_table.values())
    print(
        f"games={args.games} black={results['black']} "
        f"white={results['white']} draws={results['draw']}"
    )
    print(
        f"q_states={states} q_actions={actions} "
        f"epsilon={ai.get_exploration_rate():.3f} model={ai.model_path}"
    )


if __name__ == "__main__":
    main()
