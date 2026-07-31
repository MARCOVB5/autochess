"""
Módulo para detecção de padrões do tabuleiro de xadrez 4x4
"""
import cv2
import numpy as np
import os
from .piece_detection import piece_detection
from .piece_recognition_sift import identify_piece_sift

empty_board_reference = None
empty_board_squares = None

def _quadrilateral_score(approx_quad, img_shape):
    """
    Score a quadrilateral candidate for being the actual board.
    Returns a higher score for square-ish, centered, large-enough regions.
    """
    pts = approx_quad.reshape(-1, 2).astype(np.float32)
    if len(pts) != 4:
        return -1.0

    side_lengths = [
        np.linalg.norm(pts[i] - pts[(i + 1) % 4])
        for i in range(4)
    ]
    if min(side_lengths) <= 0:
        return -1.0

    xs, ys = pts[:, 0], pts[:, 1]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    if width <= 0 or height <= 0:
        return -1.0
    aspect = max(width, height) / min(width, height)

    area = cv2.contourArea(pts)
    img_area = img_shape[0] * img_shape[1]
    area_ratio = area / img_area

    if aspect > 1.6 or area_ratio < 0.05 or area_ratio > 0.98:
        return -1.0

    score = area_ratio * (1.0 / aspect)
    return score


def detect_board_corners(img, _cleanup_size=5):
    """
    Detecta os quatro cantos do tabuleiro 4x4 verde-amarelo.
    
    Args:
        img: Imagem original
        
    Returns:
        corners: Array numpy com as coordenadas dos 4 cantos do tabuleiro
        mask: Máscara binária do tabuleiro
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    yellow_lower = np.array([15, 70, 70])
    yellow_upper = np.array([45, 255, 255])
    
    green_lower = np.array([40, 40, 40])
    green_upper = np.array([90, 255, 255])
    
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    
    combined_mask = cv2.bitwise_or(yellow_mask, green_mask)
    
    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    cleanup_kernel = np.ones((_cleanup_size, _cleanup_size), np.uint8)
    combined_mask = cv2.morphologyEx(
        combined_mask, cv2.MORPH_OPEN, cleanup_kernel
    )
    
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, combined_mask
    
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    best_corners = None
    best_score = -1.0
    
    for contour in contours:
        if cv2.contourArea(contour) < 10000:
            continue
        
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        if len(approx) < 4:
            hull = cv2.convexHull(contour)
            approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
        
        candidate = approx.reshape(-1, 2).astype(np.float32)
        if len(candidate) < 4:
            continue
        
        if len(candidate) > 4:
            M = cv2.moments(candidate)
            cx = int(M['m10']/M['m00']) if M['m00'] != 0 else img.shape[1] // 2
            cy = int(M['m01']/M['m00']) if M['m00'] != 0 else img.shape[0] // 2
            center = np.array([cx, cy])
            
            quadrant_points = [[] for _ in range(4)]
            for point in candidate:
                x, y = point
                quadrant = 0
                if x >= center[0] and y < center[1]:
                    quadrant = 1
                elif x >= center[0] and y >= center[1]:
                    quadrant = 2
                elif x < center[0] and y >= center[1]:
                    quadrant = 3
                dist = np.linalg.norm(point - center)
                quadrant_points[quadrant].append((dist, point))
            
            reduced = np.zeros((4, 2), dtype=np.float32)
            valid = True
            for q in range(4):
                if quadrant_points[q]:
                    quadrant_points[q].sort(reverse=True, key=lambda x: x[0])
                    reduced[q] = quadrant_points[q][0][1]
                else:
                    valid = False
                    break
            
            if not valid:
                continue
            candidate = reduced
        
        score = _quadrilateral_score(candidate, img.shape)
        if score > best_score:
            best_score = score
            best_corners = order_points(candidate)

        # Cabos podem deformar um vértice; o retângulo mínimo é o fallback.
        rect_candidate = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.float32)
        rect_score = _quadrilateral_score(rect_candidate, img.shape)
        if rect_score > best_score:
            best_score = rect_score
            best_corners = order_points(rect_candidate)
    
    if best_corners is None:
        return None, combined_mask

    margin = min(img.shape[:2]) * 0.01
    near_boundary = any(
        x <= margin or y <= margin
        or x >= img.shape[1] - margin or y >= img.shape[0] - margin
        for x, y in best_corners
    )
    # Um canto na borda costuma indicar que a máscara grudou no mecanismo.
    if near_boundary and _cleanup_size == 5:
        return detect_board_corners(img, _cleanup_size=13)
    
    return best_corners, combined_mask

def order_points(pts):
    """
    Ordena os pontos em sentido horário: superior-esquerdo, superior-direito,
    inferior-direito, inferior-esquerdo.
    
    Args:
        pts: Array de 4 pontos [x, y]
        
    Returns:
        Pontos ordenados como np.float32
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def warp_board_perspective(img, corners, size=800):
    """
    Aplica uma transformação de perspectiva para obter uma visão de cima do tabuleiro.
    
    Args:
        img: Imagem original
        corners: Coordenadas dos 4 cantos do tabuleiro
        size: Tamanho do quadrado resultante
        
    Returns:
        Imagem transformada do tabuleiro (visão de cima)
    """
    dst = np.array([
        [0, 0],
        [size-1, 0],
        [size-1, size-1],
        [0, size-1]
    ], dtype=np.float32)
    
    M = cv2.getPerspectiveTransform(corners, dst)
    
    warped = cv2.warpPerspective(img, M, (size, size))
    
    return warped, M

def split_board_into_squares(warped_board, rows=4, cols=4):
    """
    Divide o tabuleiro em quadrados individuais.
    
    Args:
        warped_board: Imagem do tabuleiro com perspectiva corrigida
        rows: Número de linhas do tabuleiro
        cols: Número de colunas do tabuleiro
        
    Returns:
        Lista de dicionários contendo informações de cada quadrado
    """
    height, width = warped_board.shape[:2]
    square_height = height // rows
    square_width = width // cols
    
    squares = []
    
    for row in range(rows):
        for col in range(cols):
            x = col * square_width
            y = row * square_height
            
            square_img = warped_board[y:y+square_height, x:x+square_width]
            
            is_yellow = (row + col) % 2 == 0
            
            squares.append({
                'image': square_img.copy(),
                'coords': (x, y, square_width, square_height),
                'position': (row, col),
                'board_coords': f"{chr(65+col)}{rows-row}",  # Exemplo: A1, B4, etc.
                'color': 'yellow' if is_yellow else 'green'
            })
    
    return squares

def template_match_piece(square_img, templates_dir='./cv/assets/pure-assets'):
    """
    Utiliza template matching para identificar o tipo e cor da peça.
    
    Args:
        square_img: Imagem do quadrado contendo a peça
        templates_dir: Diretório contendo as imagens de template
        
    Returns:
        match_color: 'white' ou 'black' baseado no melhor match
        confidence: Valor de confiança do match
    """
    if not os.path.exists(templates_dir):
        return None, 0
    
    template_files = {'unknown': ['king.png', 'queen.png', 'rook.png', 'pawn.png']}
    
    best_match = None
    best_score = -1
    best_color = None
    
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    
    for color, templates in template_files.items():
        for template_file in templates:
            template_path = os.path.join(templates_dir, template_file)
            
            if not os.path.exists(template_path):
                continue
                
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            
            if template is None:
                continue
                
            for scale in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                resized_template = cv2.resize(template, (0, 0), fx=scale, fy=scale)
                
                if resized_template.shape[0] > gray.shape[0] or resized_template.shape[1] > gray.shape[1]:
                    continue
                
                result = cv2.matchTemplate(gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = template_file
                    best_color = color
    
    if best_score > 0.5:
        return best_color, best_score
    
    return None, best_score

def process_board_image(img):
    """
    Processa uma imagem do tabuleiro 4x4, detecta os cantos, aplica transformação
    de perspectiva, divide em 16 quadrados e identifica peças.
    
    Args:
        img: Imagem original do tabuleiro
        
    Returns:
        warped_board: Tabuleiro com perspectiva corrigida
        squares: Lista de informações de cada quadrado
        board_corners: Coordenadas dos cantos do tabuleiro
    """
    global empty_board_reference
    
    corners, board_mask = detect_board_corners(img)
    
    if corners is None:
        return None, [], None
    
    warped_board, transform_matrix = warp_board_perspective(img, corners)
    
    squares = split_board_into_squares(warped_board)
    
    for square in squares:
        contains_piece, piece_color = piece_detection(square['image'])
        square['contains_piece'] = contains_piece
        square['piece_color'] = piece_color
        
        if contains_piece:
            piece_type, sift_color, confidence = identify_piece_sift(
                square['image'], 
                templates_dir='./cv/assets/pure-assets',
                expected_color=piece_color
            )
            
            if 'piece_info' not in square:
                square['piece_info'] = {}
                
            square['piece_info']['type'] = piece_type
            square['piece_info']['sift_confidence'] = confidence
            
            if sift_color and confidence > 0.3 and (piece_color is None or confidence > 0.6):
                square['piece_color'] = sift_color
            
            if piece_color is None and (piece_type is None or confidence < 0.3):
                template_color, template_confidence = template_match_piece(square['image'])
                
                square['template_match'] = {
                    'color': template_color,
                    'confidence': template_confidence
                }
                
                if template_color and template_confidence > 0.6:
                    square['piece_color'] = template_color
                    square['piece_info']['template_confidence'] = template_confidence
    
    return warped_board, squares, corners

def visualize_board_and_pieces(img, warped_board, squares, corners=None):
    """
    Cria uma visualização do tabuleiro e das peças detectadas.
    
    Args:
        img: Imagem original
        warped_board: Tabuleiro com perspectiva corrigida
        squares: Lista de informações dos quadrados
        corners: Coordenadas dos cantos do tabuleiro
        
    Returns:
        Imagem com a visualização
    """
    original_viz = img.copy()
    
    if corners is not None:
        corner_names = ("TL", "TR", "BR", "BL")
        polygon = np.round(corners).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(original_viz, [polygon], True, (0, 0, 255), 5)
        for corner_name, corner in zip(corner_names, corners):
            x, y = corner
            cv2.circle(original_viz, (int(x), int(y)), 10, (0, 0, 255), -1)
            cv2.putText(original_viz, corner_name, (int(x)+12, int(y)+12),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    board_viz = warped_board.copy()
    
    for square in squares:
        x, y, w, h = square['coords']
        color = square['color']
        contains_piece = square['contains_piece']
        piece_color = square['piece_color']
        
        if color == 'yellow':
            border_color = (0, 255, 255)  # Amarelo em BGR
        else:
            border_color = (0, 255, 0)    # Verde em BGR
        
        cv2.rectangle(board_viz, (x, y), (x+w, y+h), border_color, 2)
        
        cv2.putText(board_viz, square['board_coords'], 
                   (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        if contains_piece:
            center_x = x + w // 2
            center_y = y + h // 2
            radius = min(w, h) // 3
            
            piece_type = None
            if 'piece_info' in square and 'type' in square['piece_info']:
                piece_type = square['piece_info']['type']
            
            confidence = square.get('piece_info', {}).get('sift_confidence', 0)
            if piece_color == 'white':
                marker_color = (255, 255, 255)
                text = piece_type[0].upper() if piece_type else "?"
            elif piece_color == 'black':
                marker_color = (0, 0, 0)
                text = piece_type[0].lower() if piece_type else "?"
            else:
                marker_color = (0, 0, 255)
                text = "?"

            cv2.circle(board_viz, (center_x, center_y), radius, marker_color, 4)
            piece_names = {
                'pawn': 'PEAO',
                'rook': 'TORRE',
                'queen': 'RAINHA',
                'king': 'REI',
            }
            color_name = (
                'BRANCA' if piece_color == 'white'
                else 'PRETA' if piece_color == 'black'
                else '?'
            )
            type_name = piece_names.get(piece_type, '?')
            label = f"{square['board_coords']} {type_name} {color_name}"
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2
            )
            label_y = y + 48
            cv2.rectangle(
                board_viz,
                (x + 4, y + 26),
                (min(x + w - 4, x + label_w + 12), label_y + 8),
                (30, 30, 30),
                -1,
            )
            cv2.putText(
                board_viz, label, (x + 8, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2
            )

            outline_color = (
                (0, 0, 0) if marker_color == (255, 255, 255)
                else (255, 255, 255)
            )
            cv2.putText(
                board_viz, text, (center_x - 22, center_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, outline_color, 9
            )
            cv2.putText(
                board_viz, text, (center_x - 22, center_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, marker_color, 4
            )
            cv2.putText(
                board_viz, f"{confidence:.0%}",
                (x + 8, y + h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
            )
    
    yellow_count = sum(1 for s in squares if s['color'] == 'yellow')
    green_count = sum(1 for s in squares if s['color'] == 'green')
    pieces_count = sum(1 for s in squares if s['contains_piece'])
    white_pieces = sum(1 for s in squares if s['piece_color'] == 'white')
    black_pieces = sum(1 for s in squares if s['piece_color'] == 'black')
    unclassified = pieces_count - white_pieces - black_pieces

    pawn_count = sum(1 for s in squares if s['contains_piece'] and 'piece_info' in s and s['piece_info'].get('type') == 'pawn')
    rook_count = sum(1 for s in squares if s['contains_piece'] and 'piece_info' in s and s['piece_info'].get('type') == 'rook')
    queen_count = sum(1 for s in squares if s['contains_piece'] and 'piece_info' in s and s['piece_info'].get('type') == 'queen')
    king_count = sum(1 for s in squares if s['contains_piece'] and 'piece_info' in s and s['piece_info'].get('type') == 'king')
    unknown_type = pieces_count - pawn_count - rook_count - queen_count - king_count
    
    h, w = warped_board.shape[:2]
    stats_img = np.ones((120, w, 3), dtype=np.uint8) * 240
    
    cv2.putText(stats_img, f"Quadrados: {len(squares)} (Y:{yellow_count}, G:{green_count})", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(stats_img, f"Peças: {pieces_count} (B:{black_pieces}, W:{white_pieces}, ?:{unclassified})", 
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(stats_img, f"Tipos: P:{pawn_count}, R:{rook_count}, Q:{queen_count}, K:{king_count}, ?:{unknown_type}", 
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    cv2.putText(stats_img, "P=Peão, R=Torre, Q=Rainha, K=Rei, ?=Indeterminado", 
               (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    board_with_stats = np.vstack((board_viz, stats_img))
    
    h_combined = board_with_stats.shape[0]
    w_original = original_viz.shape[1]
    h_original = original_viz.shape[0]
    
    w_resized = int(w_original * (h_combined / h_original))
    
    original_resized = cv2.resize(original_viz, (w_resized, h_combined))
    
    final_viz = np.hstack((original_resized, board_with_stats))
    
    return final_viz
