"""Open the visual CV result for one image: python view_cv.py IMAGE."""

import argparse

import cv.main as chess_cv


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("image", help="caminho da foto que será analisada")
parser.add_argument(
    "--save",
    action="store_true",
    help="também salva a visualização na pasta output",
)
args = parser.parse_args()

result = chess_cv.detect_chess_position(
    args.image,
    visualize=True,
    save_all=args.save,
    print_before_visualization=True,
)
if not result or result.get("matriz") is None:
    raise SystemExit("Não foi possível detectar o tabuleiro nessa imagem.")
