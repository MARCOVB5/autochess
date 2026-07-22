import cv2
import numpy as np


def _sample_lightness(lab_img, mask):
    """Return mean L channel value inside mask."""
    if mask is None or not np.any(mask):
        return None
    return float(np.mean(lab_img[:, :, 0][mask > 0]))


def _background_lightness(lab_img, exclude_mask=None):
    """Estimate square background lightness from edges/corners."""
    h, w = lab_img.shape[:2]
    margin = max(2, h // 14)
    bg_mask = np.zeros((h, w), dtype=np.uint8)
    bg_mask[margin:h-margin, 0:margin] = 255
    bg_mask[margin:h-margin, w-margin:w] = 255
    bg_mask[0:margin, margin:w-margin] = 255
    bg_mask[h-margin:h, margin:w-margin] = 255
    if exclude_mask is not None:
        bg_mask = cv2.bitwise_and(bg_mask, cv2.bitwise_not(exclude_mask))
    return _sample_lightness(lab_img, bg_mask)


def _detect_disk_hough(gray_img):
    """Hough circle transform for coin-style pieces."""
    blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
    side = min(gray_img.shape[:2])
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=side // 2,
        param1=50,
        param2=30,
        minRadius=side // 7,
        maxRadius=side // 2,
    )
    if circles is not None and len(circles) > 0:
        circle = np.uint16(np.around(circles))[0][0]
        return tuple(circle)
    return None


def _detect_disk_segmentation(gray_img, lab_img):
    """
    Fallback when Hough fails: segment pixels that differ from the square
    background and fit a circle to the largest blob.
    """
    h, w = gray_img.shape[:2]
    side = min(h, w)
    bg_l = _background_lightness(lab_img)
    if bg_l is None:
        return None

    l = lab_img[:, :, 0].astype(np.float32)
    diff = np.abs(l - bg_l)
    binary = (diff > 20).astype(np.uint8) * 255

    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    center = (w // 2, h // 2)
    best = None
    best_score = float('inf')

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (side // 6) ** 2:
            continue
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        if radius <= 0 or radius > side // 1.9:
            continue
        circ_area = np.pi * radius * radius
        solidity = area / circ_area
        if solidity < 0.6:
            continue
        dist_to_center = np.hypot(x - center[0], y - center[1])
        score = dist_to_center * 1.5 + abs(radius - side // 3.5) * 2
        if score < best_score:
            best_score = score
            best = (int(x), int(y), int(radius))

    return best


def piece_detection(square_img):
    """
    Detect a coin-style chess piece in a board square and determine its color.

    Physical pieces are circular disks where the disk background is the opposite
    color of the piece symbol:
      - White piece  -> dark disk with light symbol
      - Black piece  -> light disk with dark symbol

    The primary method compares the inner symbol region to the outer disk ring.
    A disk-vs-background check is used as fallback and sanity check.

    Returns:
        (contains_piece, piece_color)
        piece_color is 'white', 'black', or None.
    """
    if square_img is None or square_img.size == 0:
        return False, None

    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(square_img, cv2.COLOR_BGR2LAB)

    circle = _detect_disk_hough(gray)
    if circle is None:
        circle = _detect_disk_segmentation(gray, lab)

    if circle is None:
        return False, None

    cx, cy, radius = circle
    h, w = gray.shape[:2]

    Y, X = np.ogrid[:h, :w]
    disk_mask = (((X - cx) ** 2 + (Y - cy) ** 2) <= radius ** 2).astype(np.uint8) * 255

    inner_r = int(radius * 0.7)
    inner_mask = (((X - cx) ** 2 + (Y - cy) ** 2) <= inner_r ** 2).astype(np.uint8) * 255
    outer_mask = cv2.bitwise_and(disk_mask, cv2.bitwise_not(inner_mask))

    inner_l = _sample_lightness(lab, inner_mask)
    outer_l = _sample_lightness(lab, outer_mask)
    disk_l = _sample_lightness(lab, disk_mask)
    bg_l = _background_lightness(lab, disk_mask)

    if inner_l is None or outer_l is None or disk_l is None or bg_l is None:
        return False, None

    inner_outer_diff = abs(inner_l - outer_l)
    disk_bg_diff = abs(disk_l - bg_l)

    # Primary decision: inner (symbol) vs outer (disk background)
    if inner_outer_diff >= 8:
        if inner_l < outer_l:
            piece_color = 'black'
        else:
            piece_color = 'white'
    elif disk_bg_diff >= 12:
        # Fallback: disk color vs square background, piece is opposite
        if disk_l < bg_l:
            piece_color = 'white'
        else:
            piece_color = 'black'
    else:
        return False, None

    return True, piece_color
