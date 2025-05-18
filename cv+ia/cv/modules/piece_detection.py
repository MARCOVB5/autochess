import cv2
import numpy as np

def piece_detection(square_img):
    """
    Enhances the piece detection by applying image processing techniques 
    specifically designed for the "coin" style pieces.
    
    Args:
        square_img: Image of the square to be analyzed
        
    Returns:
        contains_piece: Boolean indicating if piece is present
        piece_color: Color of the piece ('white', 'black', or None)
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
        return False, None
    
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
    
    return True, piece_color
