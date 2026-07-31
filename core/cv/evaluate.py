"""Evaluate the board recognizer against independently annotated positions."""

import argparse
import contextlib
import io
import json
import os
import time

from cv.main import detect_chess_position


def _flatten(rows):
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ValueError("each annotation must contain four strings of length four")
    return "".join(rows)


def evaluate(annotations_path, images_dir):
    with open(annotations_path, encoding="utf-8") as annotations_file:
        annotations = json.load(annotations_file)

    totals = {
        "images": len(annotations),
        "boards_detected": 0,
        "exact_positions": 0,
        "squares": 0,
        "square_correct": 0,
        "occupancy_correct": 0,
        "color_correct": 0,
        "type_correct": 0,
    }
    elapsed = 0.0

    for filename, expected_rows in annotations.items():
        expected = _flatten(expected_rows)
        image_path = os.path.join(images_dir, filename)
        started = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            result = detect_chess_position(image_path, visualize=False)
        elapsed += time.perf_counter() - started

        if not result or result.get("matriz") is None:
            print(f"FAIL {filename}: board not detected")
            continue

        totals["boards_detected"] += 1
        predicted = _flatten(["".join(row) for row in result["matriz"]])
        totals["exact_positions"] += predicted == expected

        for wanted, got in zip(expected, predicted):
            totals["squares"] += 1
            totals["square_correct"] += wanted == got
            totals["occupancy_correct"] += (wanted == ".") == (got == ".")
            if wanted != "." and got != ".":
                totals["color_correct"] += wanted.isupper() == got.isupper()
                totals["type_correct"] += wanted.lower() == got.lower()

        status = "OK" if predicted == expected else "MISS"
        print(f"{status:4} {filename}: expected={expected} predicted={predicted}")

    squares = totals["squares"] or 1
    detected = totals["boards_detected"] or 1
    print(
        "\n"
        f"boards: {totals['boards_detected']}/{totals['images']}\n"
        f"exact positions: {totals['exact_positions']}/{detected}\n"
        f"square accuracy: {totals['square_correct']}/{squares} "
        f"({100 * totals['square_correct'] / squares:.1f}%)\n"
        f"occupancy accuracy: {totals['occupancy_correct']}/{squares} "
        f"({100 * totals['occupancy_correct'] / squares:.1f}%)\n"
        f"elapsed: {elapsed:.2f}s ({elapsed / detected:.2f}s/image)"
    )
    return 0 if totals["exact_positions"] == totals["images"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", help="JSON mapping image names to four board rows")
    parser.add_argument("images_dir", help="directory containing the annotated images")
    args = parser.parse_args()
    return evaluate(args.annotations, args.images_dir)


if __name__ == "__main__":
    raise SystemExit(main())
