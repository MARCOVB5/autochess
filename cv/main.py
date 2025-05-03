import cv2
import numpy as np

def createPattern(img):
    # Convert to HSV
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define yellow color range
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    
    # Define green color range
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([90, 255, 255])
    
    # Create masks for both colors
    mask_yellow = cv2.inRange(imgHSV, lower_yellow, upper_yellow)
    mask_green = cv2.inRange(imgHSV, lower_green, upper_green)
    
    # Combine the masks
    combined_mask = cv2.bitwise_or(mask_yellow, mask_green)
    
    # Apply morphological operations to improve the mask
    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    
    # Apply combined mask to the original image
    imgResult = cv2.bitwise_and(img, img, mask=combined_mask)
    
    # Edge detect on masked image
    imgCanny = cv2.Canny(imgResult, 100, 500)
    
    # Dilate edges to make them more visible
    kernel = np.ones((2, 2), np.uint8)
    imgCanny = cv2.dilate(imgCanny, kernel, iterations=1)
    
    return imgCanny, combined_mask

def enhanceSymbols(roi, piece_color):
    """Enhance the symbols on chess pieces using image processing techniques"""
    # Increase contrast
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    enhanced_roi = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(enhanced_roi, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Different threshold parameters based on piece color
    if piece_color == "Black":
        # For black pieces with white background, we're looking for dark symbols on light background
        threshold = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY_INV, 11, 4)
    else:
        # For white pieces with black background, we're looking for light symbols on dark background
        threshold = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 4)
    
    # Apply morphological operations to enhance the symbols
    kernel = np.ones((2, 2), np.uint8)
    enhanced = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
    enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_OPEN, kernel)
    
    # Further dilate the symbols to make them more visible
    enhanced = cv2.dilate(enhanced, kernel, iterations=1)
    
    return enhanced

def detectChessPieces(img, mask):
    # Create a copy of the original image for drawing
    result_img = img.copy()
    # Create an all-black background for symbols-only visualization (4th panel)
    symbols_only = np.zeros_like(img)
    
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours to find circular pieces
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Filter by area to avoid small noise
        if area > 500:
            # Calculate circularity
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Circular objects have circularity close to 1
                if circularity > 0.5:
                    # Draw contour
                    cv2.drawContours(result_img, [cnt], -1, (0, 255, 0), 2)
                    
                    # Get center and radius for the circular piece
                    (x, y), radius = cv2.minEnclosingCircle(cnt)
                    center = (int(x), int(y))
                    radius = int(radius)
                    
                    # Get bounding rectangle (for ROI extraction)
                    x, y, w, h = cv2.boundingRect(cnt)
                    
                    # Ensure valid region (not too close to borders)
                    if (x > 0 and y > 0 and x+w < img.shape[1] and y+h < img.shape[0]):
                        # Get the region of interest (the chess piece)
                        roi = img[y:y+h, x:x+w]
                        
                        # Skip if ROI is too small
                        if roi.shape[0] < 20 or roi.shape[1] < 20:
                            continue
                        
                        # Check for dark/light piece (based on the region inside the contour)
                        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                        avg_value = np.mean(hsv_roi[:,:,2])
                        
                        if avg_value > 100:  # Bright piece (likely black piece with white background)
                            piece_color = "Black"
                            text_color = (0, 0, 0)
                            symbol_color = [0, 0, 255]  # Red
                        else:  # Dark piece (likely white piece with black background)
                            piece_color = "White"
                            text_color = (255, 255, 255)
                            symbol_color = [255, 0, 0]  # Blue
                        
                        # Enhance the symbols on the piece based on its color
                        enhanced_roi = enhanceSymbols(roi, piece_color)
                        
                        # Create a mask for the piece based on its contour
                        piece_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                        cv2.drawContours(piece_mask, [cnt], -1, 255, -1)
                        
                        # Place the enhanced ROI into the result image
                        if enhanced_roi.shape[0] > 0 and enhanced_roi.shape[1] > 0:
                            # Create a colored version of the enhanced ROI
                            color_mask = np.zeros_like(roi)
                            
                            # Highlight the detected symbols with color
                            color_mask[enhanced_roi > 50] = symbol_color
                            
                            # Create highlight mask with more visibility
                            highlight_mask = np.zeros_like(roi)
                            highlight_mask[enhanced_roi > 50] = [255, 255, 255]
                            
                            # Apply the highlight mask with higher contrast
                            result_roi = result_img[y:y+h, x:x+w]
                            result_roi = cv2.addWeighted(result_roi, 0.7, highlight_mask, 0.7, 0)
                            
                            # Then apply the colored symbols
                            result_roi = cv2.addWeighted(result_roi, 0.7, color_mask, 0.9, 0)
                            
                            # Update the result image
                            result_img[y:y+h, x:x+w] = result_roi
                            
                            # Also create a visualization for the symbols-only image (4th panel)
                            cv2.circle(symbols_only, center, radius+5, (50, 50, 50), -1)  # Dark circle background
                            symbols_roi = symbols_only[y:y+h, x:x+w]
                            symbol_highlight = np.zeros_like(roi)
                            
                            # Use bright colors for the symbols based on piece color
                            if piece_color == "Black":
                                symbol_highlight[enhanced_roi > 50] = [255, 0, 0]  # Blue for black pieces
                            else:
                                symbol_highlight[enhanced_roi > 50] = [0, 255, 255]  # Yellow for white pieces
                                
                            # Apply to the symbols-only visualization
                            symbols_roi = cv2.addWeighted(symbols_roi, 0.1, symbol_highlight, 0.9, 0)
                            symbols_only[y:y+h, x:x+w] = symbols_roi
                            
                            # Draw a small version of the symbol next to the piece label
                            symbol_viz = np.zeros_like(roi)
                            symbol_viz[enhanced_roi > 50] = symbol_color
                            
                            symbol_size = min(40, w, h)
                            if symbol_size > 20:
                                small_symbol = cv2.resize(symbol_viz, (symbol_size, symbol_size))
                                symbol_x = max(0, x - symbol_size - 5)
                                symbol_y = max(0, y - 5)
                                
                                # Make sure we don't exceed image boundaries
                                if (symbol_y + symbol_size < img.shape[0] and 
                                    symbol_x + symbol_size < img.shape[1]):
                                    result_img[symbol_y:symbol_y+symbol_size, 
                                              symbol_x:symbol_x+symbol_size] = small_symbol
                        
                        # Label the piece
                        cv2.putText(result_img, piece_color, (x, y-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
    
    return result_img, symbols_only

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Could not open webcam")
        return
    print("✅ Webcam opened. Press 'q' to quit, 's' to save current frame.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        # Process frame
        edges, mask = createPattern(frame)
        
        # Detect chess pieces
        piece_detection, symbols_only = detectChessPieces(frame, mask)

        # Create a 2x2 grid display (resize each to half size for better viewing)
        h, w = frame.shape[:2]
        h_half, w_half = h//2, w//2
        
        # Resize the images to fit the grid
        frame_small = cv2.resize(frame, (w_half, h_half))
        edges_small = cv2.resize(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), (w_half, h_half))
        piece_detection_small = cv2.resize(piece_detection, (w_half, h_half))
        symbols_only_small = cv2.resize(symbols_only, (w_half, h_half))
        
        # Create the grid display
        top_row = np.hstack((frame_small, edges_small))
        bottom_row = np.hstack((piece_detection_small, symbols_only_small))
        combined = np.vstack((top_row, bottom_row))
        
        # Add labels to each quadrant
        cv2.putText(combined, "Original", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Edges", (w_half+10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Piece Detection", (10, h_half+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Symbols Only", (w_half+10, h_half+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Chess Piece Detection", combined)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save current frame when 's' is pressed
            cv2.imwrite("chess_detection.jpg", combined)
            print("✅ Saved current frame as chess_detection.jpg")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
