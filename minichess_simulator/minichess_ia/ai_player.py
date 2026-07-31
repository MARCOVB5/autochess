"""Compatibility import for the canonical AI implementation in core."""

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from core.ai_player import MiniChessAI as CoreMiniChessAI


class MiniChessAI(CoreMiniChessAI):
    def __init__(self, *args, model_path=None, **kwargs):
        if model_path is None:
            model_path = Path(__file__).resolve().parent / "models" / "minichess_ai_model.pkl"
        super().__init__(*args, model_path=model_path, **kwargs)


__all__ = ["MiniChessAI"]
