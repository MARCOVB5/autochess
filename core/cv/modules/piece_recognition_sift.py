"""
Module for chess piece recognition using SIFT (Scale-Invariant Feature Transform)
"""
import cv2
import numpy as np
import os
import pickle

def keypoint_to_dict(kp):
    """Convert OpenCV KeyPoint to dictionary"""
    return {
        'pt': kp.pt,
        'size': kp.size,
        'angle': kp.angle,
        'response': kp.response,
        'octave': kp.octave,
        'class_id': kp.class_id
    }

def dict_to_keypoint(kp_dict):
    """Convert dictionary back to OpenCV KeyPoint"""
    return cv2.KeyPoint(
        x=kp_dict['pt'][0],
        y=kp_dict['pt'][1],
        size=kp_dict['size'],
        angle=kp_dict['angle'],
        response=kp_dict['response'],
        octave=kp_dict['octave'],
        class_id=kp_dict['class_id']
    )

class ChessPieceRecognizer:
    """Class for recognizing chess pieces using SIFT features"""
    
    def __init__(self, templates_dir='cv/assets/pure-assets'):
        """
        Initialize the chess piece recognizer
        
        Args:
            templates_dir: Directory containing template images of chess pieces
        """
        self.templates_dir = templates_dir
        self.templates = {}
        self.sift = cv2.SIFT_create()
        
        # instead of a fixed dict, we'll scan every .png in templates_dir
        
        # Load templates and extract SIFT features
        self._load_templates()
    
    def _load_templates(self):
        """Load template images and extract SIFT features"""
        # Check if cached features exist
        cache_file = os.path.join(self.templates_dir, 'sift_features.pkl')
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    # Convert cached data back to original format
                    self.templates = {}
                    for filename, data in cached_data.items():
                        self.templates[filename] = {
                            'keypoints': [dict_to_keypoint(kp) for kp in data['keypoints']],
                            'descriptors': data['descriptors'],
                            'type': data['type'],
                            'image': data['image']
                        }
                print(f"Loaded {len(self.templates)} cached SIFT templates")
                return
            except Exception as e:
                print(f"Error loading cached features: {e}")
        
        # Load *all* PNGs in templates_dir (and its 'augmented/' subfolder)
        all_templates = []
        for root, _, fnames in os.walk(self.templates_dir):
            for fname in fnames:
                if not fname.lower().endswith('.png'):
                    continue
                all_templates.append(os.path.join(root, fname))

        for template_path in all_templates:
            filename = os.path.basename(template_path)
            # infer piece_type from the filename prefix:
            piece_type = None
            for pt in ('king','queen','rook','pawn'):
                if filename.lower().startswith(pt):
                    piece_type = pt
                    break
            if piece_type is None:
                # skip any PNG that doesn't match our naming convention
                continue

            if not os.path.exists(template_path):
                print(f"Warning: Template {template_path} not found")
                continue
                
            # Load template image
            template = cv2.imread(template_path)
            if template is None:
                print(f"Warning: Failed to load {template_path}")
                continue
            
            # Convert to grayscale
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Detect SIFT keypoints and descriptors
            keypoints, descriptors = self.sift.detectAndCompute(gray_template, None)
            
            if keypoints and descriptors is not None:
                # Store template info (color-agnostic)
                self.templates[filename] = {
                    'keypoints': keypoints,
                    'descriptors': descriptors,
                    'type': piece_type,
                    'image': gray_template
                }
                print(f"Loaded template: {filename} ({len(keypoints)} keypoints)")
        
        # Save features to cache
        if self.templates:
            try:
                # Convert keypoints to pickleable format
                cache_data = {}
                for filename, data in self.templates.items():
                    cache_data[filename] = {
                        'keypoints': [keypoint_to_dict(kp) for kp in data['keypoints']],
                        'descriptors': data['descriptors'],
                        'type': data['type'],
                        'image': data['image']
                    }
                
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                print(f"Cached {len(self.templates)} SIFT templates to {cache_file}")
            except Exception as e:
                print(f"Error caching features: {e}")
    
    def identify_piece(self, square_img, expected_color=None):
        """
        Identify chess piece in square using SIFT
        
        Args:
            square_img: Image of a chess square containing a piece
            expected_color: Expected color of the piece ('white' or 'black'), if known
                           (not used in this implementation as templates are color-agnostic)
            
        Returns:
            dict: Information about the detected piece or None if no piece detected
        """
        if not self.templates:
            return None
        
        # Convert to grayscale for SIFT
        if len(square_img.shape) == 3:
            gray_img = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
        else:
            gray_img = square_img
        
        # Create SIFT detector
        sift = self.sift
        
        # Detect keypoints and descriptors
        keypoints, descriptors = sift.detectAndCompute(gray_img, None)
        
        if keypoints is None or len(keypoints) == 0 or descriptors is None:
            return None
        
        # Create FLANN matcher
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        best_match = None
        best_score = 0
        
        # Use all templates since we're color-agnostic
        filtered_templates = self.templates
        
        # Match against each template
        for filename, template in filtered_templates.items():
            # Skip if descriptor shapes don't match
            if descriptors.shape[1] != template['descriptors'].shape[1]:
                continue
            
            # Match descriptors using FLANN
            matches = flann.knnMatch(template['descriptors'], descriptors, k=2)
            
            # Apply ratio test as per Lowe's paper
            good_matches = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
            
            # Calculate score (normalized by template keypoints)
            score = len(good_matches) / len(template['keypoints']) if template['keypoints'] else 0
            
            # Update best match if score is better
            if score > best_score and score > 0.15:  # Threshold for minimum score
                best_score = score
                best_match = {
                    'type': template['type'],
                    'score': score,
                    'filename': filename,
                    'good_matches': len(good_matches),
                    'total_keypoints': len(template['keypoints'])
                }
        
        return best_match

def _identify_piece_template(square_img, templates_dir='cv/assets/pure-assets', expected_color=None):
    """
    Identify a chess piece by grayscale template matching against the base
    piece silhouettes. White pieces (light symbol on dark disk) are inverted
    before matching so the symbol aligns with the dark template shape.

    Returns:
        tuple: (piece_type, confidence) or (None, 0)
    """
    piece_names = ['king', 'queen', 'rook', 'pawn']
    templates = {}
    for name in piece_names:
        path = os.path.join(templates_dir, f"{name}.png")
        if not os.path.exists(path):
            continue
        templ = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if templ is not None:
            templates[name] = templ

    if not templates:
        return None, 0

    if len(square_img.shape) == 3:
        gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = square_img

    # White pieces have a light symbol on a dark disk. The templates are dark
    # silhouettes on a light background, so invert white-piece squares.
    if expected_color == 'white':
        gray = cv2.bitwise_not(gray)

    best_type = None
    best_score = 0.55  # minimum acceptable template match score

    for name, templ in templates.items():
        h_t, w_t = templ.shape
        local_best = 0
        for scale in np.arange(0.25, 1.05, 0.05):
            resized = cv2.resize(templ, (0, 0), fx=scale, fy=scale)
            if resized.shape[0] > gray.shape[0] or resized.shape[1] > gray.shape[1]:
                continue
            if resized.shape[0] < 8 or resized.shape[1] < 8:
                continue
            res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > local_best:
                local_best = max_val
        if local_best > best_score:
            best_score = local_best
            best_type = name

    return best_type, best_score


def identify_piece_sift(square_img, templates_dir='cv/assets/pure-assets', expected_color=None):
    """
    Wrapper function to identify chess piece using SIFT and template matching.

    Args:
        square_img: Image of a chess square containing a piece
        templates_dir: Directory containing template images
        expected_color: Expected color of the piece ('white' or 'black'), if known

    Returns:
        tuple: (piece_type, sift_color, confidence)
    """
    # Create a singleton instance of ChessPieceRecognizer
    if not hasattr(identify_piece_sift, 'recognizer'):
        identify_piece_sift.recognizer = ChessPieceRecognizer(templates_dir)

    # SIFT path
    result = identify_piece_sift.recognizer.identify_piece(square_img, expected_color)

    # If white piece is expected or no good match was found, try with inverted image
    if (expected_color == 'white' or (result is None or result['score'] < 0.25)) and len(square_img.shape) == 3:
        inverted_img = cv2.bitwise_not(square_img)
        inverted_result = identify_piece_sift.recognizer.identify_piece(inverted_img, expected_color)
        if inverted_result and (result is None or inverted_result['score'] > result['score']):
            result = inverted_result

    sift_type = result['type'] if result else None
    sift_score = result['score'] if result else 0

    # Template matching path
    template_type, template_score = _identify_piece_template(
        square_img, templates_dir=templates_dir, expected_color=expected_color
    )

    # Return the method with the higher confidence
    if template_type and template_score >= sift_score:
        return template_type, expected_color, template_score

    if sift_type:
        return sift_type, expected_color, sift_score

    return None, None, 0

def visualize_sift_match(square_img, templates_dir='cv/assets/pure-assets', expected_color=None):
    """
    Visualize SIFT matches for debugging
    
    Args:
        square_img: Image of a chess square containing a piece
        templates_dir: Directory containing template images
        expected_color: Expected color of the piece ('white' or 'black'), if known
                       (not used in this implementation as templates are color-agnostic)
        
    Returns:
        Image with SIFT matches visualization
    """
    # Create a singleton instance of ChessPieceRecognizer
    if not hasattr(visualize_sift_match, 'recognizer'):
        visualize_sift_match.recognizer = ChessPieceRecognizer(templates_dir)
    
    # Convert to grayscale for SIFT
    if len(square_img.shape) == 3:
        gray_img = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    else:
        gray_img = square_img
    
    # Detect keypoints and descriptors
    sift = visualize_sift_match.recognizer.sift
    keypoints, descriptors = sift.detectAndCompute(gray_img, None)
    
    if keypoints is None or len(keypoints) == 0 or descriptors is None:
        return square_img
    
    # Create FLANN matcher
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    
    recognizer = visualize_sift_match.recognizer
    
    # Use all templates since we're color-agnostic
    filtered_templates = recognizer.templates
    
    best_match = None
    best_score = 0
    best_template = None
    best_good_matches = []
    
    # Match against each template
    for filename, template in filtered_templates.items():
        # Skip if descriptor shapes don't match
        if descriptors.shape[1] != template['descriptors'].shape[1]:
            continue
        
        # Match descriptors using FLANN
        matches = flann.knnMatch(template['descriptors'], descriptors, k=2)
        
        # Apply ratio test as per Lowe's paper
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
        
        # Calculate score (normalized by template keypoints)
        score = len(good_matches) / len(template['keypoints']) if template['keypoints'] else 0
        
        # Update best match if score is better
        if score > best_score and score > 0.15:  # Threshold for minimum score
            best_score = score
            best_match = {
                'type': template['type'],
                'score': score,
                'filename': filename
            }
            best_template = template['image']
            best_good_matches = good_matches
    
    if best_match and best_template is not None:
        # Draw matches
        img_matches = cv2.drawMatches(
            best_template, recognizer.templates[best_match['filename']]['keypoints'],
            gray_img, keypoints,
            best_good_matches, None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
        )
        
        # Add info text
        cv2.putText(
            img_matches, 
            f"{best_match['type']}: {best_score:.2f}", 
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )
        
        return img_matches
    
    # Draw keypoints if no match
    img_keypoints = cv2.drawKeypoints(
        gray_img, keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
    )
    cv2.putText(
        img_keypoints,
        f"No match found ({len(keypoints)} keypoints)",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
    )
    
    return img_keypoints
