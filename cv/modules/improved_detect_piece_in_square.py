"""
Enhancement module for detecting and classifying chess pieces on a 4x4 board
"""
import cv2
import numpy as np
import os

def identify_piece_type(square_img, piece_color):
    """
    Identifies the type of chess piece (king, queen, pawn, tower/rook) using shape analysis.
    
    Args:
        square_img: Image of the square containing the piece
        piece_color: Color of the piece ('white' or 'black')
        
    Returns:
        piece_type: String indicating the piece type ('king', 'queen', 'pawn', 'tower')
        confidence: Confidence score of the classification
    """
    # Convert to grayscale
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding based on piece color
    # For white pieces, we look for dark features on light background
    # For black pieces, we look for light features on dark background
    if piece_color == 'white':
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    else:
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    
    # Apply morphological operations to clean up the image
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    # Find contours of the piece symbol
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # If no contours found, return unknown
    if not contours:
        return "unknown", 0.0
    
    # Get the largest contour (should be the piece symbol)
    contour = max(contours, key=cv2.contourArea)
    
    # Calculate contour features
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    
    # If area is too small, not a valid piece
    if area < 20:
        return "unknown", 0.0
    
    # Calculate circularity
    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
    
    # Calculate bounding rectangle
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    
    # Calculate the convex hull and its area
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0
    
    # Calculate the minimum enclosing circle
    (x, y), radius = cv2.minEnclosingCircle(contour)
    
    # Calculate the extent (ratio of contour area to bounding rect area)
    extent = float(area) / (w * h) if w * h > 0 else 0
    
    # Calculate moments and Hu moments for shape recognition
    moments = cv2.moments(contour)
    hu_moments = cv2.HuMoments(moments).flatten()
    
    # Feature-based classification
    # These thresholds may need to be adjusted based on your specific pieces
    
    # King: Usually has a cross on top, more complex shape
    # Queen: Often has a crown-like shape
    # Pawn: Simple, compact shape
    # Tower/Rook: Usually has a blocky, castle-like shape
    
    # Decision tree based on shape features
    confidence = 0.6  # Base confidence
    
    if aspect_ratio > 0.8 and aspect_ratio < 1.2:
        # More square-like shapes (possible Tower or King)
        if extent > 0.7:
            piece_type = "tower"  # Tower/Rook is more filled/solid
            confidence = 0.75
        else:
            piece_type = "king"  # King is less filled due to cross
            confidence = 0.7
    elif aspect_ratio >= 1.2:
        # Wider than tall (possible Queen)
        piece_type = "queen"
        confidence = 0.65
    else:
        # Taller than wide (likely Pawn)
        piece_type = "pawn"
        confidence = 0.75
    
    # Additional checks based on Hu moments
    # This is a simplified approach; in a real system, you might use a trained classifier
    # Hu[0] is a measure of spread - lower values mean more spread out shape
    if hu_moments[0] < 0.2:  # Spread out shape
        if aspect_ratio < 1.0:
            piece_type = "queen"  # Queen often has a spread-out crown
            confidence = 0.8
    elif hu_moments[0] > 0.4:  # Compact shape
        piece_type = "pawn"  # Pawns are typically compact
        confidence = 0.75
    
    return piece_type, confidence

def enhance_piece_detection(square_img):
    """
    Enhances the piece detection by applying image processing techniques 
    specifically designed for the "coin" style pieces.
    
    Args:
        square_img: Image of the square to be analyzed
        
    Returns:
        contains_piece: Boolean indicating if piece is present
        piece_color: Color of the piece ('white', 'black', or None)
        piece_type: Type of the piece ('king', 'queen', 'pawn', 'tower', or None)
        piece_info: Dictionary with additional information
    """
    # Initial info dictionary
    piece_info = {}
    
    # Convert to different color spaces for analysis
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(square_img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(square_img, cv2.COLOR_BGR2LAB)
    
    # Blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detect circles using Hough Circle Transform
    # This is good for detecting the coin-shaped pieces
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=square_img.shape[0]//2,
        param1=50,
        param2=30,
        minRadius=square_img.shape[0]//6,
        maxRadius=square_img.shape[0]//2
    )
    
    # Check if any circles were found
    contains_piece = circles is not None
    
    if not contains_piece:
        return False, None, None, piece_info
    
    # Get the largest circle (should be the piece)
    circle = np.uint16(np.around(circles))[0][0]
    center_x, center_y, radius = circle
    
    # Create a mask for the circle
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.circle(mask, (center_x, center_y), radius, 255, -1)
    
    # Extract the piece region
    piece_region = cv2.bitwise_and(square_img, square_img, mask=mask)
    
    # Create inner and outer masks to analyze the coin background and piece symbol
    inner_radius = int(radius * 0.7)  # Inner 70% for the piece symbol
    outer_radius = radius
    
    inner_mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.circle(inner_mask, (center_x, center_y), inner_radius, 255, -1)
    
    outer_mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.circle(outer_mask, (center_x, center_y), outer_radius, 255, -1)
    cv2.circle(outer_mask, (center_x, center_y), inner_radius, 0, -1)  # Subtract inner circle
    
    # Extract inner and outer regions
    inner_region = cv2.bitwise_and(square_img, square_img, mask=inner_mask)
    outer_region = cv2.bitwise_and(square_img, square_img, mask=outer_mask)
    
    # Analyze color distribution in inner and outer regions
    # We'll use LAB color space which is good for color differences
    inner_lab = cv2.cvtColor(inner_region, cv2.COLOR_BGR2LAB)
    outer_lab = cv2.cvtColor(outer_region, cv2.COLOR_BGR2LAB)
    
    # Calculate average L (lightness) for inner and outer regions
    inner_l = np.mean(inner_lab[:,:,0][inner_mask > 0])
    outer_l = np.mean(outer_lab[:,:,0][outer_mask > 0])
    
    # Store color metrics in piece_info
    piece_info.update({
        'inner_l': inner_l,
        'outer_l': outer_l,
        'circle': (center_x, center_y, radius)
    })
    
    # Determine piece color based on contrast between inner and outer regions
    # For the coin-style pieces:
    # - Black piece has white background (outer is lighter than inner)
    # - White piece has black background (inner is lighter than outer)
    L_DIFF_THRESHOLD = 15  # Minimum difference in lightness to determine contrast
    
    if abs(inner_l - outer_l) < L_DIFF_THRESHOLD:
        # Not enough contrast, could be an empty square or noise
        return False, None, None, piece_info
    
    # Determine piece color based on which region is darker
    if inner_l < outer_l:
        # Inner region darker than outer
        piece_color = 'black'  # Black piece on white background
    else:
        # Outer region darker than inner
        piece_color = 'white'  # White piece on black background
    
    # Store determination method
    piece_info['color_determination'] = f"{'Black' if piece_color == 'black' else 'White'} piece detected: inner_l={inner_l:.1f}, outer_l={outer_l:.1f}"
    
    # Now identify the piece type
    piece_type, confidence = identify_piece_type(piece_region, piece_color)
    piece_info['type_confidence'] = confidence
    
    return True, piece_color, piece_type, piece_info

def improved_detect_piece_in_square(square_img, square_position=None):
    """
    An improved version of detect_piece_in_square that incorporates enhanced detection
    and also identifies the piece type.
    
    Args:
        square_img: Image of the square individual
        square_position: Position (row, column) of the square on the board
        
    Returns:
        contains_piece: Boolean indicating presence of piece
        piece_color: 'white', 'black' or None
        piece_type: 'king', 'queen', 'pawn', 'tower' or None
        piece_info: Dictionary with additional information about the piece
    """
    # Use the enhanced detection method
    contains_piece, piece_color, piece_type, piece_info = enhance_piece_detection(square_img)
    
    # If no piece detected, return early
    if not contains_piece:
        return False, None, None, piece_info
    
    # If a piece is detected but we're not confident in the type, try template matching
    if piece_type == "unknown" or piece_info.get('type_confidence', 0) < 0.6:
        # Template matching could be implemented here
        pass
    
    return contains_piece, piece_color, piece_type, piece_info



