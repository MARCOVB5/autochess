"""
Módulo para detecção de padrões do tabuleiro de xadrez 4x4
"""
import cv2
import numpy as np
import os
from .piece_detection import piece_detection
from .piece_recognition_sift import identify_piece_sift

# Variável global para armazenar a imagem de referência do tabuleiro vazio
empty_board_reference = None
empty_board_squares = None

def detect_board_corners(img):
    """
    Detecta os quatro cantos do tabuleiro 4x4 verde-amarelo.
    
    Args:
        img: Imagem original
        
    Returns:
        corners: Array numpy com as coordenadas dos 4 cantos do tabuleiro
        mask: Máscara binária do tabuleiro
    """
    # Converter para HSV para detecção de cor
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Definir intervalos para cores verde e amarelo
    yellow_lower = np.array([15, 70, 70])
    yellow_upper = np.array([45, 255, 255])
    
    green_lower = np.array([40, 40, 40])
    green_upper = np.array([90, 255, 255])
    
    # Criar máscaras para cores
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Combinar máscaras
    combined_mask = cv2.bitwise_or(yellow_mask, green_mask)
    
    # Aplicar operações morfológicas para melhorar a máscara
    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar para encontrar o contorno do tabuleiro (maior área)
    if not contours:
        return None, combined_mask
        
    # Ordenar contornos por área (decrescente)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    board_contour = contours[0]
    
    # Verificar se o contorno tem área mínima
    min_area = 10000  # Ajustar conforme necessário
    if cv2.contourArea(board_contour) < min_area:
        return None, combined_mask
    
    # Aproximar o contorno para obter os cantos
    peri = cv2.arcLength(board_contour, True)
    approx = cv2.approxPolyDP(board_contour, 0.02 * peri, True)
    
    # Tentar extrair exatamente 4 cantos
    if len(approx) < 4:
        # Caso não consiga encontrar 4 cantos diretamente, usar convex hull
        hull = cv2.convexHull(board_contour)
        approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
    
    # Reduzir para 4 pontos se tiver mais
    if len(approx) > 4:
        # Calcular centroide
        M = cv2.moments(approx)
        cx = int(M['m10']/M['m00']) if M['m00'] != 0 else 0
        cy = int(M['m01']/M['m00']) if M['m00'] != 0 else 0
        center = (cx, cy)
        
        # Calcular os 4 pontos mais distantes do centro em cada quadrante
        points = []
        for point in approx.reshape(-1, 2):
            # Determinar o quadrante (0: superior-esquerdo, 1: superior-direito, 
            # 2: inferior-direito, 3: inferior-esquerdo)
            quadrant = 0
            if point[0] >= center[0] and point[1] < center[1]:
                quadrant = 1
            elif point[0] >= center[0] and point[1] >= center[1]:
                quadrant = 2
            elif point[0] < center[0] and point[1] >= center[1]:
                quadrant = 3
                
            # Calcular distância ao centro
            dist = np.sqrt((point[0] - center[0])**2 + (point[1] - center[1])**2)
            points.append((dist, point, quadrant))
        
        # Agrupar por quadrante
        quadrant_points = [[] for _ in range(4)]
        for dist, point, quad in points:
            quadrant_points[quad].append((dist, point))
            
        # Pegar o ponto mais distante em cada quadrante
        corners = np.zeros((4, 2), dtype=np.float32)
        for q in range(4):
            if quadrant_points[q]:
                # Pegar o ponto mais distante neste quadrante
                quadrant_points[q].sort(reverse=True)
                corners[q] = quadrant_points[q][0][1]
            else:
                # Se não tiver pontos neste quadrante, estimar com base nos outros
                if q == 0:  # Superior-esquerdo
                    corners[q] = np.array([0, 0])
                elif q == 1:  # Superior-direito
                    corners[q] = np.array([img.shape[1], 0])
                elif q == 2:  # Inferior-direito
                    corners[q] = np.array([img.shape[1], img.shape[0]])
                else:  # Inferior-esquerdo
                    corners[q] = np.array([0, img.shape[0]])
    else:
        # Se tiver 4 pontos, ordenar em sentido horário
        corners = order_points(approx.reshape(-1, 2))
    
    return corners, combined_mask

def order_points(pts):
    """
    Ordena os pontos em sentido horário: superior-esquerdo, superior-direito,
    inferior-direito, inferior-esquerdo.
    
    Args:
        pts: Array de 4 pontos [x, y]
        
    Returns:
        Pontos ordenados como np.float32
    """
    # Inicializar array ordenado
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # A soma das coordenadas x e y
    s = pts.sum(axis=1)
    # Superior-esquerdo: menor soma
    rect[0] = pts[np.argmin(s)]
    # Inferior-direito: maior soma
    rect[2] = pts[np.argmax(s)]
    
    # A diferença entre as coordenadas x e y
    diff = np.diff(pts, axis=1)
    # Superior-direito: menor diferença
    rect[1] = pts[np.argmin(diff)]
    # Inferior-esquerdo: maior diferença
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
    # Pontos de destino (quadrado de tamanho fixo)
    dst = np.array([
        [0, 0],
        [size-1, 0],
        [size-1, size-1],
        [0, size-1]
    ], dtype=np.float32)
    
    # Calcular matriz de transformação
    M = cv2.getPerspectiveTransform(corners, dst)
    
    # Aplicar transformação
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
            # Calcular coordenadas do quadrado
            x = col * square_width
            y = row * square_height
            
            # Extrair região de interesse
            square_img = warped_board[y:y+square_height, x:x+square_width]
            
            # Determinar se é quadrado verde ou amarelo pelo padrão de xadrez
            is_yellow = (row + col) % 2 == 0
            
            # Informações do quadrado
            squares.append({
                'image': square_img.copy(),
                'coords': (x, y, square_width, square_height),
                'position': (row, col),
                'board_coords': f"{chr(65+col)}{rows-row}",  # Exemplo: A1, B4, etc.
                'color': 'yellow' if is_yellow else 'green'
            })
    
    return squares

def template_match_piece(square_img, templates_dir='./assets/pure-assets'):
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
    
    # Lista de possíveis templates
    template_files = {
        #'white': ['white-king.png', 'white-queen.png', 'white-rook.png', 'white-pawn.png'],
        #'black': ['black-king.png', 'black-queen.png', 'black-rook.png', 'black-pawn.png']
        ['king.png', 'queen.png', 'rook.png', 'pawn.png']
    }
    
    best_match = None
    best_score = -1
    best_color = None
    
    # Pré-processar a imagem do quadrado
    gray = cv2.cvtColor(square_img, cv2.COLOR_BGR2GRAY)
    
    for color, templates in template_files.items():
        for template_file in templates:
            template_path = os.path.join(templates_dir, template_file)
            
            if not os.path.exists(template_path):
                continue
                
            # Carregar e redimensionar o template
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            
            if template is None:
                continue
                
            # Redimensionar para vários tamanhos para tentar combinar
            for scale in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                resized_template = cv2.resize(template, (0, 0), fx=scale, fy=scale)
                
                # Verificar se o template é menor que a imagem
                if resized_template.shape[0] > gray.shape[0] or resized_template.shape[1] > gray.shape[1]:
                    continue
                
                # Aplicar template matching
                result = cv2.matchTemplate(gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = template_file
                    best_color = color
    
    # Retornar o melhor match se a pontuação for alta o suficiente
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
    
    # Detectar cantos do tabuleiro
    corners, board_mask = detect_board_corners(img)
    
    if corners is None:
        return None, [], None
    
    # Aplicar transformação de perspectiva
    warped_board, transform_matrix = warp_board_perspective(img, corners)
    
    # Dividir em 16 quadrados (4x4)
    squares = split_board_into_squares(warped_board)
    
    # Para cada quadrado, verificar se tem peça
    for square in squares:
        # Detectar peça usando subtração de fundo e classificar por HSV
        contains_piece, piece_color = piece_detection(square['image'])
        # Atualizar informações da peça
        square['contains_piece'] = contains_piece
        square['piece_color'] = piece_color
        
        # Se a peça foi detectada, tentar identificar seu tipo usando SIFT
        if contains_piece:
            # Usar a cor detectada como dica para o reconhecimento SIFT
            piece_type, sift_color, confidence = identify_piece_sift(
                square['image'], 
                templates_dir='./assets/pure-assets',
                expected_color=piece_color
            )
            
            # Criar dicionário de informações da peça se não existir
            if 'piece_info' not in square:
                square['piece_info'] = {}
                
            # Armazenar resultados do SIFT
            square['piece_info']['type'] = piece_type
            square['piece_info']['sift_confidence'] = confidence
            
            # Se o SIFT identificou uma cor com alta confiança, atualizar piece_color
            if sift_color and confidence > 0.3 and (piece_color is None or confidence > 0.6):
                square['piece_color'] = sift_color
            
            # Se ainda não conseguimos classificar a peça, tentar template matching como fallback
            if piece_color is None and (piece_type is None or confidence < 0.3):
                # Tentar template matching para confirmar a cor
                template_color, template_confidence = template_match_piece(square['image'])
                
                # Armazenar informações de template matching
                square['template_match'] = {
                    'color': template_color,
                    'confidence': template_confidence
                }
                
                # Se o template matching tiver boa confiança, usar sua classificação
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
    # Criar cópia da imagem original para desenhar
    original_viz = img.copy()
    
    # Desenhar os cantos do tabuleiro na imagem original, se disponíveis
    if corners is not None:
        for i, corner in enumerate(corners):
            x, y = corner
            cv2.circle(original_viz, (int(x), int(y)), 10, (0, 0, 255), -1)
            cv2.putText(original_viz, str(i), (int(x)+10, int(y)+10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Criar visualização do tabuleiro corrigido
    board_viz = warped_board.copy()
    
    # Desenhar grade e peças
    for square in squares:
        x, y, w, h = square['coords']
        color = square['color']
        contains_piece = square['contains_piece']
        piece_color = square['piece_color']
        
        # Definir cor da borda do quadrado
        if color == 'yellow':
            border_color = (0, 255, 255)  # Amarelo em BGR
        else:
            border_color = (0, 255, 0)    # Verde em BGR
        
        # Desenhar borda do quadrado
        cv2.rectangle(board_viz, (x, y), (x+w, y+h), border_color, 2)
        
        # Desenhar coordenada do quadrado
        cv2.putText(board_viz, square['board_coords'], 
                   (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Se contém peça, desenhar círculo com a cor correspondente
        if contains_piece:
            # Centro do quadrado
            center_x = x + w // 2
            center_y = y + h // 2
            radius = min(w, h) // 3
            
            # Obter tipo de peça se disponível
            piece_type = None
            if 'piece_info' in square and 'type' in square['piece_info']:
                piece_type = square['piece_info']['type']
            
            # Verificar se foi usado template matching com alta confiança
            used_template = False
            template_confidence = 0
            
            if 'template_match' in square and square['template_match']['color'] is not None:
                template_confidence = square['template_match']['confidence']
                if template_confidence > 0.6:
                    used_template = True
            
            # Desenhar círculo com borda mais destacada se usou template
            thickness = 2 if not used_template else 3
            
            if piece_color == 'white':
                cv2.circle(board_viz, (center_x, center_y), radius, (255, 255, 255), -1)
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 0), thickness)  # Borda preta
                
                # Adicionar indicador de tipo
                text = "W"
                if piece_type:
                    # Usar primeira letra do tipo de peça
                    text = piece_type[0].upper()
                
                cv2.putText(board_viz, text, (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Adicionar confiança do SIFT se disponível
                if piece_type and 'sift_confidence' in square['piece_info']:
                    conf_text = f"{square['piece_info']['sift_confidence']:.2f}"
                    cv2.putText(board_viz, conf_text, (center_x-15, center_y+radius+15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                
            elif piece_color == 'black':
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 0), -1)
                cv2.circle(board_viz, (center_x, center_y), radius, (255, 255, 255), thickness)  # Borda branca
                
                # Adicionar indicador de tipo
                text = "B"
                if piece_type:
                    # Usar primeira letra do tipo de peça
                    text = piece_type[0].upper()
                
                cv2.putText(board_viz, text, (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Adicionar confiança do SIFT se disponível
                if piece_type and 'sift_confidence' in square['piece_info']:
                    conf_text = f"{square['piece_info']['sift_confidence']:.2f}"
                    cv2.putText(board_viz, conf_text, (center_x-15, center_y+radius+15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            else:
                # Peça detectada mas cor indeterminada
                cv2.circle(board_viz, (center_x, center_y), radius, (0, 0, 255), -1)
                cv2.putText(board_viz, "?", (center_x-10, center_y+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Criar painel de estatísticas
    yellow_count = sum(1 for s in squares if s['color'] == 'yellow')
    green_count = sum(1 for s in squares if s['color'] == 'green')
    pieces_count = sum(1 for s in squares if s['contains_piece'])
    white_pieces = sum(1 for s in squares if s['piece_color'] == 'white')
    black_pieces = sum(1 for s in squares if s['piece_color'] == 'black')
    unclassified = pieces_count - white_pieces - black_pieces

    # Contar tipos de peças
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
    
    # Legenda
    cv2.putText(stats_img, "P=Peão, R=Torre, Q=Rainha, K=Rei, ?=Indeterminado", 
               (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Combinar visualização do tabuleiro com estatísticas
    board_with_stats = np.vstack((board_viz, stats_img))
    
    # Redimensionar imagem original para mesma altura
    h_combined = board_with_stats.shape[0]
    w_original = original_viz.shape[1]
    h_original = original_viz.shape[0]
    
    # Calcular nova largura mantendo a proporção
    w_resized = int(w_original * (h_combined / h_original))
    
    # Redimensionar imagem original
    original_resized = cv2.resize(original_viz, (w_resized, h_combined))
    
    # Combinar as duas visualizações lado a lado
    final_viz = np.hstack((original_resized, board_with_stats))
    
    return final_viz
