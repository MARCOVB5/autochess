"""Evaluate the black MiniChess agent against a seeded random opponent."""

import argparse
import random
import time
from collections import Counter

from ai_player import MiniChessAI
from minichess import MiniChess


def evaluate(ai, games, seed=10_000, max_plies=100, pedagogical=False):
    rng = random.Random(seed)
    results = Counter()
    started_at = time.perf_counter()

    for _ in range(games):
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
                move = ai.get_move(
                    game,
                    training=False,
                    pedagogical=pedagogical,
                )
            if move is None or not game.make_move(move):
                raise RuntimeError(f"invalid move selected: {move}")

        result = game.get_result()
        if result == -1:
            results["black"] += 1
        elif result == 1:
            results["white"] += 1
        else:
            results["draw"] += 1

    return results, time.perf_counter() - started_at


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--model", default=None)
    parser.add_argument("--seed", type=int, default=10_000)
    parser.add_argument("--max-plies", type=int, default=100)
    parser.add_argument(
        "--pedagogical",
        action="store_true",
        help="evaluate the visible behavior for the current learning stage",
    )
    args = parser.parse_args()

    ai = MiniChessAI(model_path=args.model, seed=args.seed)
    results, elapsed = evaluate(
        ai,
        args.games,
        args.seed,
        args.max_plies,
        args.pedagogical,
    )
    print(
        f"games={args.games} black={results['black']} "
        f"white={results['white']} draws={results['draw']}"
    )
    print(
        f"model_games={ai.games_played} q_states={len(ai.q_table)} "
        f"elapsed={elapsed:.3f}s"
    )


if __name__ == "__main__":
    main()
