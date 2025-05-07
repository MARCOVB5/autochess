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

def visualize_piece_detection(square_img):
    """
    Creates a visualization of the piece detection process.
    
    Args:
        square_img: Image of the square containing the piece
        
    Returns:
        Visualization image showing detection steps
    """
    # Run the enhanced piece detection
    contains_piece, piece_color, piece_type, piece_info = enhance_piece_detection(square_img)
    
    # Create a visualization image
    h, w = square_img.shape[:2]
    viz = np.zeros((h, w*2, 3), dtype=np.uint8)
    
    # Original image on the left
    viz[:, :w] = square_img.copy()
    
    # Detection visualization on the right
    detection_viz = square_img.copy()
    
    if contains_piece and 'circle' in piece_info:
        # Draw the detected circle
        center_x, center_y, radius = piece_info['circle']
        cv2.circle(detection_viz, (center_x, center_y), radius, (0, 255, 0), 2)
        
        # Draw inner circle (used for analysis)
        inner_radius = int(radius * 0.7)
        cv2.circle(detection_viz, (center_x, center_y), inner_radius, (255, 0, 0), 1)
        
        # Add text for piece information
        color_text = piece_color.capitalize() if piece_color else "Unknown"
        type_text = piece_type.capitalize() if piece_type else "Unknown"
        
        cv2.putText(detection_viz, f"{color_text} {type_text}", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Add confidence if available
        if 'type_confidence' in piece_info:
            conf_text = f"Conf: {piece_info['type_confidence']:.2f}"
            cv2.putText(detection_viz, conf_text, 
                       (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    else:
        cv2.putText(detection_viz, "No piece detected", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    # Add detection visualization to the right side
    viz[:, w:] = detection_viz
    
    return viz

def integrate_with_pattern_detection(squares):
    """
    Integrates the improved piece detection with the existing pattern detection code.
    This function should be called in the original process_board_image function.
    
    Args:
        squares: List of square dictionaries from split_board_into_squares
        
    Returns:
        Updated squares with improved piece detection
    """
    for square in squares:
        # Run enhanced piece detection
        contains_piece, piece_color, piece_type, piece_info = improved_detect_piece_in_square(
            square['image'], square['position']
        )
        
        # Update square information
        square['contains_piece'] = contains_piece
        square['piece_color'] = piece_color
        square['piece_type'] = piece_type
        square['piece_info'].update(piece_info)
    
    return squares

# Function to be added to the main pattern_detection.py file
def process_board_image_improved(img):
    """
    Enhanced version of process_board_image that uses the improved piece detection.
    
    Args:
        img: Original image of the board
        
    Returns:
        warped_board: Board with corrected perspective
        squares: List of information for each square
        board_corners: Coordinates of the board corners
    """
    # Import the original functions from pattern_detection
    from pattern_detection import detect_board_corners, warp_board_perspective, split_board_into_squares
    
    # Detect board corners
    corners, board_mask = detect_board_corners(img)
    
    if corners is None:
        return None, [], None
    
    # Apply perspective transformation
    warped_board, transform_matrix = warp_board_perspective(img, corners)
    
    # Split into 16 squares (4x4)
    squares = split_board_into_squares(warped_board)
    
    # Use improved piece detection
    squares = integrate_with_pattern_detection(squares)
    
    return warped_board, squares, corners

def visualize_board_and_pieces_improved(img, warped_board, squares, corners=None):
    """
    Enhanced visualization of the board and pieces with piece type information.
    
    Args:
        img: Original image
        warped_board: Board with corrected perspective
        squares: List of square information
        corners: Coordinates of the board corners
        
    Returns:
        Image with visualization
    """
    # Import the original function from pattern_detection
    from pattern_detection import visualize_board_and_pieces
    
    # Get the basic visualization
    basic_viz = visualize_board_and_pieces(img, warped_board, squares, corners)
    
    # Create an enhanced version with piece type information
    board_viz = warped_board.copy()
    
    # Draw grid and pieces with type information
    for square in squares:
        x, y, w, h = square['coords']
        color = square['color']
        contains_piece = square['contains_piece']
        piece_color = square['piece_color']
        piece_type = square.get('piece_type', 'unknown')
        
        # Define border color
        if color == 'yellow':
            border_color = (0, 255, 255)  # Yellow in BGR
        else:
            border_color = (0, 255, 0)    # Green in BGR
        
        # Draw square border
        cv2.rectangle(board_viz, (x, y), (x+w, y+h), border_color, 2)
        
        # Draw coordinate
        cv2.putText(board_viz, square['board_coords'], 
                   (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # If contains piece, draw with type information
        if contains_piece:
            # Center of the square
            center_x = x + w // 2
            center_y = y + h // 2
            radius = min(w, h) // 3
            
            # Set confidence
            confidence = square.get('piece_info', {}).get('type_confidence', 0)
            
            # Draw circle with the piece color
            if piece_color == 'white':
                cv2.circle(board_viz, (center_x, center_y), radius, (255, 255, 255), -1)
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 0), 2)  # Black border
                
                # Add type indicator
                type_symbol = piece_type[0].upper() if piece_type else "?"
                cv2.putText(board_viz, type_symbol, (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Add confidence
                if confidence > 0:
                    conf_text = f"{confidence:.2f}"
                    cv2.putText(board_viz, conf_text, (center_x-15, center_y+radius+15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                
            elif piece_color == 'black':
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 0), -1)
                cv2.circle(board_viz, (center_x, center_y), radius, (255, 255, 255), 2)  # White border
                
                # Add type indicator
                type_symbol = piece_type[0].upper() if piece_type else "?"
                cv2.putText(board_viz, type_symbol, (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Add confidence
                if confidence > 0:
                    conf_text = f"{confidence:.2f}"
                    cv2.putText(board_viz, conf_text, (center_x-15, center_y+radius+15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            else:
                # Piece detected but color undetermined
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 255), -1)
                cv2.putText(board_viz, "?", (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Create statistics panel
    yellow_count = sum(1 for s in squares if s['color'] == 'yellow')
    green_count = sum(1 for s in squares if s['color'] == 'green')
    pieces_count = sum(1 for s in squares if s['contains_piece'])
    white_pieces = sum(1 for s in squares if s['piece_color'] == 'white')
    black_pieces = sum(1 for s in squares if s['piece_color'] == 'black')
    
    # Count by piece type
    kings = sum(1 for s in squares if s.get('piece_type') == 'king')
    queens = sum(1 for s in squares if s.get('piece_type') == 'queen')
    pawns = sum(1 for s in squares if s.get('piece_type') == 'pawn')
    towers = sum(1 for s in squares if s.get('piece_type') == 'tower')
    unknown_type = pieces_count - kings - queens - pawns - towers
    
    h, w = warped_board.shape[:2]
    stats_img = np.ones((150, w, 3), dtype=np.uint8) * 240
    
    cv2.putText(stats_img, f"Squares: {len(squares)} (Y:{yellow_count}, G:{green_count})", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(stats_img, f"Pieces: {pieces_count} (B:{black_pieces}, W:{white_pieces})", 
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(stats_img, f"Types: K:{kings}, Q:{queens}, P:{pawns}, T:{towers}, ?:{unknown_type}", 
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Legend
    cv2.putText(stats_img, "K=King, Q=Queen, P=Pawn, T=Tower, ?=Unknown", 
               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Combine visualization of the board with statistics
    enhanced_viz = np.vstack((board_viz, stats_img))
    
    return enhanced_viz, basic_viz
