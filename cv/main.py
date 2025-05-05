import cv2
import numpy as np
import argparse
import os

def createPattern(img, yellow_range=None, green_range=None):
    """
    Cria um padrão para detectar o tabuleiro de xadrez e as peças.
    Retorna as bordas e uma máscara combinada.
    """
    # Fazer uma cópia da imagem original
    img_display = img.copy()
    
    # Convert to HSV for better color detection
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define yellow color range
    if yellow_range is None:
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([35, 255, 255])
    else:
        lower_yellow, upper_yellow = yellow_range
    
    # Define green color range
    if green_range is None:
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([90, 255, 255])
    else:
        lower_green, upper_green = green_range
    
    # Create masks for both colors
    mask_yellow = cv2.inRange(imgHSV, lower_yellow, upper_yellow)
    mask_green = cv2.inRange(imgHSV, lower_green, upper_green)
    
    # Combine the masks for board squares
    board_mask = cv2.bitwise_or(mask_yellow, mask_green)
    
    # Apply morphological operations to improve the mask
    kernel = np.ones((5, 5), np.uint8)
    board_mask = cv2.morphologyEx(board_mask, cv2.MORPH_CLOSE, kernel)
    board_mask = cv2.morphologyEx(board_mask, cv2.MORPH_OPEN, kernel)
    
    # Método melhorado para detectar as peças
    # 1. Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Aplicar blur para reduzir ruído
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # 3. Aplicar limiarização adaptativa para destacar as peças
    # Usar limiarização adaptativa para lidar melhor com iluminação variável
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # 4. Aplicar operações morfológicas para melhorar a máscara
    kernel_morph = np.ones((3, 3), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_morph, iterations=2)
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_morph, iterations=1)
    
    # 5. Encontrar contornos na imagem processada
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 6. Criar máscara para peças circulares
    pieces_mask = np.zeros_like(gray)
    
    # 7. Filtrar apenas contornos potencialmente circulares
    valid_contours = []
    min_area = 500  # Área mínima para filtrar ruído
    max_area = 10000  # Área máxima para evitar detecções erradas
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Filtrar por área
        if min_area < area < max_area:
            # Calcular circularidade
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Objetos circulares têm circularidade próxima a 1
                if circularity > 0.5:
                    # Adicionar à lista de contornos válidos
                    valid_contours.append(cnt)
                    # Desenhar na máscara
                    cv2.drawContours(pieces_mask, [cnt], -1, 255, -1)
    
    # 8. Caso não detecte peças suficientes, tentar abordagem alternativa
    if len(valid_contours) < 10:  # Esperamos 16 peças
        print(f"⚠️ Detectadas apenas {len(valid_contours)} peças, tentando método alternativo...")
        
        # Usar detecção de círculos Hough Circle
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                  param1=50, param2=30, minRadius=15, maxRadius=50)
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            print(f"✅ Método Hough Circle detectou {len(circles[0])} círculos")
            
            # Limpar a máscara anterior
            pieces_mask = np.zeros_like(gray)
            
            # Desenhar círculos na máscara
            for circle in circles[0, :]:
                center = (circle[0], circle[1])
                radius = circle[2]
                
                # Desenhar círculo preenchido na máscara
                cv2.circle(pieces_mask, center, radius, 255, -1)
                
                # Desenhar círculo na imagem de visualização
                cv2.circle(img_display, center, radius, (0, 255, 0), 2)
    
    # Edge detect do tabuleiro para visualização
    board_result = cv2.bitwise_and(img, img, mask=board_mask)
    imgCanny = cv2.Canny(board_result, 100, 500)
    kernel = np.ones((2, 2), np.uint8)
    imgCanny = cv2.dilate(imgCanny, kernel, iterations=1)
    
    return imgCanny, pieces_mask, img_display, board_mask

def detectBoardAndSquares(img, board_mask):
    """
    Detecta o tabuleiro de xadrez, aplica transformação de perspectiva e divide em 16 quadrantes.
    
    Args:
        img: Imagem original
        board_mask: Máscara do tabuleiro (quadrados verdes e amarelos)
    
    Returns:
        warped_board: Imagem do tabuleiro com perspectiva corrigida
        squares: Lista de 16 ROIs (4x4) representando cada casa do tabuleiro
        M: Matriz de transformação usada
        board_corners: Coordenadas dos 4 cantos do tabuleiro
    """
    # Encontrar contornos do tabuleiro na máscara
    contours, _ = cv2.findContours(board_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar para encontrar o contorno do tabuleiro (o maior contorno)
    board_contour = max(contours, key=cv2.contourArea) if contours else None
    
    if board_contour is None:
        print("❌ Falha ao detectar o tabuleiro")
        return None, [], None, []
    
    # Aproximar o contorno do tabuleiro para um polígono
    epsilon = 0.02 * cv2.arcLength(board_contour, True)
    approx = cv2.approxPolyDP(board_contour, epsilon, True)
    
    # Verificar se o polígono tem 4 vértices (aproximação de um quadrilátero)
    if len(approx) != 4:
        # Se não encontrou exatamente 4 cantos, tentar encontrar os 4 cantos do retângulo delimitador
        x, y, w, h = cv2.boundingRect(board_contour)
        approx = np.array([
            [x, y],
            [x + w, y],
            [x + w, y + h],
            [x, y + h]
        ], dtype=np.float32).reshape(-1, 1, 2)
    
    # Ordenar os pontos para garantir consistência [top-left, top-right, bottom-right, bottom-left]
    approx = approx.reshape(4, 2)
    
    # Calcular o centro de massa
    center = np.mean(approx, axis=0)
    
    # Ordenar os pontos baseado na posição relativa ao centro
    ordered_points = []
    for pt in approx:
        # Classificar baseado no quadrante em relação ao centro
        if pt[0] < center[0] and pt[1] < center[1]:
            ordered_points.append((0, pt))  # top-left
        elif pt[0] > center[0] and pt[1] < center[1]:
            ordered_points.append((1, pt))  # top-right
        elif pt[0] > center[0] and pt[1] > center[1]:
            ordered_points.append((2, pt))  # bottom-right
        else:
            ordered_points.append((3, pt))  # bottom-left
    
    # Ordenar pelos índices e extrair os pontos
    ordered_points.sort(key=lambda x: x[0])
    src_points = np.array([pt[1] for pt in ordered_points], dtype=np.float32)
    
    # Definir as dimensões do tabuleiro transformado (um quadrado para manter a proporção)
    board_size = 400  # tamanho em pixels do tabuleiro transformado
    dst_points = np.array([
        [0, 0],
        [board_size, 0],
        [board_size, board_size],
        [0, board_size]
    ], dtype=np.float32)
    
    # Calcular a matriz de transformação de perspectiva
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    
    # Aplicar a transformação de perspectiva
    warped_board = cv2.warpPerspective(img, M, (board_size, board_size))
    
    # Dividir o tabuleiro em 16 quadrantes (4x4)
    square_size = board_size // 4
    squares = []
    for row in range(4):
        for col in range(4):
            # Extrair o quadrante
            x1 = col * square_size
            y1 = row * square_size
            square_roi = warped_board[y1:y1 + square_size, x1:x1 + square_size]
            squares.append((square_roi, (row, col), (x1, y1, square_size, square_size)))
    
    return warped_board, squares, M, src_points

def analyzeSquare(square_roi, templates):
    """
    Analisa um quadrante do tabuleiro e verifica se há peça e identifica seu tipo/cor.
    
    Args:
        square_roi: Imagem do quadrante do tabuleiro
        templates: Dicionário de templates para identificação de peças
    
    Returns:
        has_piece: Booleano indicando se o quadrante contém uma peça
        piece_color: Cor da peça ('White', 'Black' ou None)
        piece_type: Tipo da peça (King, Queen, Tower, Pawn, Unknown ou None)
        confidence: Nível de confiança na identificação
    """
    # Converter para HSV para análise de cor
    hsv_roi = cv2.cvtColor(square_roi, cv2.COLOR_BGR2HSV)
    
    # Criar uma máscara circular para analisar apenas o centro do quadrante
    h, w = square_roi.shape[:2]
    center_x, center_y = w // 2, h // 2
    radius = min(w, h) // 3  # Um terço da largura/altura
    
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (center_x, center_y), radius, 255, -1)
    
    # Extrair região central do quadrante
    masked_roi = cv2.bitwise_and(square_roi, square_roi, mask=mask)
    
    # Converter para escala de cinza para análise de presença
    gray = cv2.cvtColor(masked_roi, cv2.COLOR_BGR2GRAY)
    
    # Contar pixels não-zero na região central
    non_zero_pixels = cv2.countNonZero(gray)
    
    # Verificar se há peça (baseado na quantidade de pixels não-zero)
    piece_threshold = (radius ** 2) * 0.3  # 30% da área do círculo
    has_piece = non_zero_pixels > piece_threshold
    
    if not has_piece:
        return False, None, None, 0.0
    
    # Redimensionar o quadrante para tamanho padrão para análise
    standard_size = (64, 64)
    resized_roi = cv2.resize(square_roi, standard_size)
    
    # Identificar a cor da peça
    piece_color, text_color, symbol_color, avg_value, debug_info = identify_piece_color(resized_roi, mask)
    
    # Identificar o tipo da peça
    piece_type, confidence = identify_piece_type_template_matching(resized_roi, piece_color, mask, templates)
    
    return True, piece_color, piece_type, confidence

def processChessboard(img, templates):
    """
    Processa o tabuleiro de xadrez usando a abordagem de quadrantes fixos.
    
    Args:
        img: Imagem original do tabuleiro
        templates: Dicionário de templates para identificação de peças
    
    Returns:
        result_img: Imagem original com anotações
        warped_annotated: Tabuleiro com perspectiva corrigida e anotações
        board_state: Matriz 4x4 com o estado do tabuleiro (peças em cada posição)
    """
    # Processar a imagem para obter as máscaras
    edges, pieces_mask, initial_detection, board_mask = createPattern(img)
    
    # Detectar o tabuleiro e dividir em quadrantes
    warped_board, squares, transform_matrix, board_corners = detectBoardAndSquares(img, board_mask)
    
    if warped_board is None:
        print("❌ Falha ao processar o tabuleiro")
        return img, None, None
    
    # Criar cópias para anotação
    result_img = img.copy()
    warped_annotated = warped_board.copy()
    
    # Matriz 4x4 para armazenar o estado do tabuleiro
    board_state = [[None for _ in range(4)] for _ in range(4)]
    
    # Processar cada quadrante
    for square_data in squares:
        square_roi, (row, col), (x1, y1, square_size, square_size) = square_data
        
        # Analisar o quadrante
        has_piece, piece_color, piece_type, confidence = analyzeSquare(square_roi, templates)
        
        # Armazenar informações na matriz do tabuleiro
        if has_piece:
            board_state[row][col] = {
                'color': piece_color,
                'type': piece_type,
                'confidence': confidence
            }
            
            # Anotar no tabuleiro transformado
            label = f"{piece_color[0]}{piece_type[0]}"
            cv2.putText(warped_annotated, label, 
                       (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                       (0, 255, 255) if piece_color == "White" else (0, 0, 255), 
                       2)
            
            # Desenhar um círculo para marcar a peça
            center_x, center_y = x1 + square_size // 2, y1 + square_size // 2
            cv2.circle(warped_annotated, (center_x, center_y), square_size // 3, 
                      (0, 255, 0), 2)
            
            # Adicionar indicador de confiança
            conf_text = f"{confidence:.2f}"
            cv2.putText(warped_annotated, conf_text, 
                       (x1 + 5, y1 + square_size - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, 
                       (255, 255, 255), 
                       1)
    
    # Desenhar grid no tabuleiro transformado
    square_size = warped_board.shape[0] // 4
    for i in range(1, 4):
        # Linhas horizontais
        cv2.line(warped_annotated, (0, i * square_size), 
                (warped_board.shape[1], i * square_size), 
                (200, 200, 200), 1)
        # Linhas verticais
        cv2.line(warped_annotated, (i * square_size, 0), 
                (i * square_size, warped_board.shape[0]), 
                (200, 200, 200), 1)
    
    # Desenhar os cantos do tabuleiro na imagem original
    for i, corner in enumerate(board_corners):
        cv2.circle(result_img, (int(corner[0]), int(corner[1])), 10, (0, 255, 0), -1)
        cv2.putText(result_img, str(i), (int(corner[0])+15, int(corner[1])),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    # Estatísticas para adicionar à imagem original
    white_pieces = sum(1 for row in board_state for cell in row if cell and cell['color'] == 'White')
    black_pieces = sum(1 for row in board_state for cell in row if cell and cell['color'] == 'Black')
    
    # Adicionar estatísticas à imagem
    cv2.putText(result_img, f"White: {white_pieces}", (20, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(result_img, f"Black: {black_pieces}", (20, 60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return result_img, warped_annotated, board_state

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

def analyze_reference_pieces():
    """
    Analisa as imagens de referência das peças no diretório pieces-pictures
    para aprender as características de cada tipo de peça.
    """
    pieces_dir = "pieces-pictures"
    reference_pieces = {}
    
    # Verificar se o diretório existe
    if not os.path.exists(pieces_dir):
        print(f"❌ Diretório de peças não encontrado: {pieces_dir}")
        return None
    
    # Listar arquivos no diretório
    files = os.listdir(pieces_dir)
    
    for file in files:
        # Apenas arquivos de imagem
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            # Extrair informações do nome do arquivo
            parts = file.split('_')
            if len(parts) >= 3:
                # Obter cor da peça (BLACK/WHITE)
                piece_color = parts[0]
                
                # Carregar a imagem
                img_path = os.path.join(pieces_dir, file)
                img = cv2.imread(img_path)
                
                if img is None:
                    print(f"❌ Não foi possível carregar: {img_path}")
                    continue
                
                # Converter para HSV para análise
                hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                # Encontrar a peça na imagem (assumindo que é o objeto principal)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                
                # Encontrar contornos
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Obter o maior contorno (provavelmente a peça)
                if contours:
                    cnt = max(contours, key=cv2.contourArea)
                    
                    # Criar máscara para a peça
                    mask = np.zeros_like(gray)
                    cv2.drawContours(mask, [cnt], 0, 255, -1)
                    
                    # Extrair região da peça
                    piece_region = cv2.bitwise_and(img, img, mask=mask)
                    
                    # Coletar características
                    hsv_region = cv2.cvtColor(piece_region, cv2.COLOR_BGR2HSV)
                    masked_pixels = hsv_region[mask > 0]
                    
                    if len(masked_pixels) > 0:
                        # Calcular estatísticas da peça
                        avg_hue = np.mean(masked_pixels[:, 0])
                        avg_sat = np.mean(masked_pixels[:, 1])
                        avg_val = np.mean(masked_pixels[:, 2])
                        
                        # Salvar características
                        if piece_color not in reference_pieces:
                            reference_pieces[piece_color] = []
                        
                        reference_pieces[piece_color].append({
                            'file': file,
                            'avg_hue': avg_hue,
                            'avg_sat': avg_sat,
                            'avg_val': avg_val,
                            'contour': cnt
                        })
                        
                        print(f"✅ Analisada peça {piece_color} de {file}: H={avg_hue:.1f}, S={avg_sat:.1f}, V={avg_val:.1f}")
    
    # Calcular características médias para cada cor
    color_stats = {}
    for color, pieces in reference_pieces.items():
        avg_hue = np.mean([p['avg_hue'] for p in pieces])
        avg_sat = np.mean([p['avg_sat'] for p in pieces])
        avg_val = np.mean([p['avg_val'] for p in pieces])
        
        color_stats[color] = {
            'avg_hue': avg_hue,
            'avg_sat': avg_sat,
            'avg_val': avg_val,
            'count': len(pieces)
        }
        
        print(f"\n✅ Estatísticas para peças {color}:")
        print(f"  - Quantidade: {len(pieces)}")
        print(f"  - H média: {avg_hue:.1f}")
        print(f"  - S média: {avg_sat:.1f}")
        print(f"  - V média: {avg_val:.1f}")
    
    return color_stats

def identify_piece_color(roi, piece_mask):
    """
    Identifica a cor da peça com base nas estatísticas aprendidas das peças de referência.
    Utiliza características mais precisas extraídas das imagens de peças individuais.
    CORREÇÃO: As cores foram invertidas, corrigindo a classificação.
    """
    # Valores de referência para cada cor de peça (BLACK/WHITE)
    # Valores ajustados baseados nas imagens de peças de referência
    WHITE_REFERENCE_V = 180  # Peças brancas são geralmente muito claras
    BLACK_REFERENCE_V = 70   # Peças pretas são geralmente bem escuras
    
    # Obter apenas os pixels da peça usando a máscara
    masked_roi = cv2.bitwise_and(roi, roi, mask=piece_mask)
    
    # Converter para HSV para análise de cor
    hsv_roi = cv2.cvtColor(masked_roi, cv2.COLOR_BGR2HSV)
    
    # Obter apenas os pixels válidos (não pretos da máscara)
    valid_pixels = hsv_roi[piece_mask > 0]
    
    if len(valid_pixels) > 0:
        # Calcular valor médio (brilho)
        avg_value = np.mean(valid_pixels[:, 2])
        
        # Calcular percentis para análise mais robusta
        val_25th = np.percentile(valid_pixels[:, 2], 25)  # Quartil inferior
        val_75th = np.percentile(valid_pixels[:, 2], 75)  # Quartil superior
        
        # Calcular histograma para análise de distribuição
        hist = np.histogram(valid_pixels[:, 2], bins=8, range=(0, 256))[0]
        # Calcular porcentagem de pixels escuros (< 100)
        dark_percentage = np.sum(valid_pixels[:, 2] < 100) / len(valid_pixels)
        
        # CORREÇÃO: Invertendo a lógica de classificação de cores
        # Lógica para determinar a cor da peça usando vários critérios
        if avg_value > 160 or val_25th > 140:
            # Peça muito clara - com certeza é PRETA (inversão)
            piece_color = "Black"
            text_color = (255, 255, 255)  # Texto branco
            symbol_color = [0, 0, 255]  # Vermelho
        elif avg_value < 80 or val_75th < 100:
            # Peça muito escura - com certeza é BRANCA (inversão)
            piece_color = "White"
            text_color = (0, 0, 0)  # Texto preto
            symbol_color = [255, 0, 0]  # Azul
        elif dark_percentage < 0.3 and avg_value > 120:
            # Poucos pixels escuros e média clara - provavelmente PRETA (inversão)
            piece_color = "Black"
            text_color = (255, 255, 255)  # Texto branco
            symbol_color = [0, 0, 255]  # Vermelho
        elif dark_percentage > 0.7 and avg_value < 100:
            # Muitos pixels escuros e média escura - provavelmente BRANCA (inversão)
            piece_color = "White"
            text_color = (0, 0, 0)  # Texto preto
            symbol_color = [255, 0, 0]  # Azul
        else:
            # Caso ambíguo - usar a média como critério final (invertido)
            if avg_value > (WHITE_REFERENCE_V + BLACK_REFERENCE_V) / 2:
                piece_color = "Black"
                text_color = (255, 255, 255)  # Texto branco
                symbol_color = [0, 0, 255]  # Vermelho
            else:
                piece_color = "White"
                text_color = (0, 0, 0)  # Texto preto
                symbol_color = [255, 0, 0]  # Azul
            
        # Incluir informações adicionais para depuração
        debug_info = {
            'avg_value': avg_value,
            'val_25th': val_25th,
            'val_75th': val_75th,
            'dark_percentage': dark_percentage
        }
        
        return piece_color, text_color, symbol_color, avg_value, debug_info
    else:
        # Caso não haja pixels válidos
        return "Unknown", (255, 255, 255), [0, 255, 0], 0, {}

def identify_piece_type(roi, piece_color):
    """
    Identifica o tipo da peça (King, Queen, Tower, Pawn) usando análise geométrica.
    Esta função é usada como fallback quando o template matching falha.
    
    Args:
        roi: Região da imagem contendo a peça
        piece_color: Cor da peça ('Black' ou 'White')
    
    Returns:
        piece_type: Tipo da peça identificado
        confidence: Nível de confiança na identificação (0-1)
    """
    # Processar a região de interesse para destacar o símbolo
    symbol = enhanceSymbols(roi, piece_color)
    
    # Encontrar contornos do símbolo
    contours, _ = cv2.findContours(symbol, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Se não encontrou contornos, retornar tipo desconhecido
    if not contours:
        return "Unknown", 0.0
    
    # Obter o maior contorno (principal parte do símbolo)
    main_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(main_contour)
    
    # Se a área for muito pequena, pode não ser um símbolo válido
    if area < 10:
        return "Unknown", 0.0
    
    # Extrair características do símbolo detectado
    perimeter = cv2.arcLength(main_contour, True)
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    extent = float(area) / (w * h) if (w * h) > 0 else 0
    
    # Calcular solidez (solidity)
    hull = cv2.convexHull(main_contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0
    
    # Classificar peças com base em características geométricas
    # Valores baseados em observação empírica
    
    # KING: Geralmente tem uma cruz na parte superior
    # Características: Proporção próxima de 1 (quase quadrado), solidez média
    if 0.8 < aspect_ratio < 1.2 and 0.6 < solidity < 0.85:
        return "King", 0.7
    
    # QUEEN: Geralmente tem uma coroa com pontas na parte superior
    # Características: Proporção mais alta que o rei, solidez menor devido às pontas
    elif 0.9 < aspect_ratio < 1.4 and 0.5 < solidity < 0.75:
        return "Queen", 0.6
    
    # TOWER (Rook): Forma mais retangular e compacta
    # Características: Proporção próxima de 1 (mais quadrado), solidez alta (forma compacta)
    elif 0.7 < aspect_ratio < 1.1 and solidity > 0.8:
        return "Tower", 0.7
    
    # PAWN: Forma mais simples e geralmente menor
    # Características: Proporção variável, solidez alta
    elif solidity > 0.75:
        return "Pawn", 0.6
    
    # Se não conseguiu classificar com confiança
    return "Unknown", 0.4

def load_piece_templates():
    """
    Carrega as imagens de referência dos símbolos das peças do diretório assets
    e extrai características para comparação.
    
    Returns:
        Um dicionário de templates e características para cada tipo de peça
    """
    assets_dir = "assets"
    templates = {}
    
    # Verificar se o diretório existe
    if not os.path.exists(assets_dir):
        print(f"⚠️ Diretório de assets não encontrado: {assets_dir}")
        print(f"   Usando classificação baseada em geometria.")
        return None
    
    # Mapear nomes de arquivos para tipos de peças
    type_mapping = {
        "king": "King",
        "queen": "Queen",
        "rook": "Rook",
        "pawn": "Pawn"
    }
    
    # Carregar cada imagem de referência
    try:
        for color in ["white", "black"]:
            templates[color] = {}
            
            for piece_type in type_mapping.keys():
                filename = f"{color}-{piece_type}.png"
                filepath = os.path.join(assets_dir, filename)
                
                if os.path.exists(filepath):
                    # Carregar a imagem
                    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        continue
                    
                    # Limiarizar para garantir preto e branco puro
                    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
                    
                    # CORREÇÃO: Corrigir a forma como findContours é chamado
                    # Alterar de:
                    # contours, _ = cv2.findContours(binary, cv2.THRESH_BINARY_INV if color == "white" else cv2.THRESH_BINARY, 
                    #                              cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # Para:
                    if color == "white":
                        # Invertemos primeiro a imagem para branco em fundo preto
                        binary_inv = cv2.bitwise_not(binary)
                        contours, _ = cv2.findContours(binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    else:
                        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Extrair características se encontrar contornos
                    if contours:
                        main_contour = max(contours, key=cv2.contourArea)
                        area = cv2.contourArea(main_contour)
                        
                        if area > 0:
                            # Calcular características
                            perimeter = cv2.arcLength(main_contour, True)
                            x, y, w, h = cv2.boundingRect(main_contour)
                            aspect_ratio = float(w) / h if h > 0 else 0
                            extent = float(area) / (w * h) if (w * h) > 0 else 0
                            
                            # Invólucro convexo e solidez
                            hull = cv2.convexHull(main_contour)
                            hull_area = cv2.contourArea(hull)
                            solidity = float(area) / hull_area if hull_area > 0 else 0
                            
                            # Momento de Hu para análise de forma invariante
                            moments = cv2.moments(main_contour)
                            hu_moments = cv2.HuMoments(moments)
                            
                            # Armazenar características e imagem de referência
                            mapped_type = type_mapping[piece_type]
                            templates[color][mapped_type] = {
                                'binary': binary,
                                'contour': main_contour,
                                'area': area,
                                'perimeter': perimeter,
                                'aspect_ratio': aspect_ratio,
                                'extent': extent,
                                'solidity': solidity,
                                'hu_moments': hu_moments,
                                'w': w,
                                'h': h,
                                'original_image': img  # Guardar a imagem original para matching direto
                            }
                            
                            print(f"✅ Carregado template para {color} {mapped_type}")
                            print(f"   Proporção: {aspect_ratio:.2f}, Solidez: {solidity:.2f}")
        
        # Verificar se carregou todos os templates
        if templates['white'] and templates['black'] and len(templates['white']) > 0 and len(templates['black']) > 0:
            print(f"✅ Carregados {len(templates['white'])} templates brancos e {len(templates['black'])} templates pretos")
            return templates
        else:
            return None
    except Exception as e:
        print(f"⚠️ Erro ao carregar templates: {str(e)}")
        return None

def identify_piece_type_template_matching(roi, piece_color, piece_mask, templates):
    """
    Identifica o tipo de peça usando correspondência de templates e características.
    MELHORADO: Agora testa peças em múltiplas rotações para maior robustez.
    
    Args:
        roi: Região da imagem contendo a peça
        piece_color: Cor da peça ('Black' ou 'White')
        piece_mask: Máscara da peça
        templates: Dicionário de templates de referência
    
    Returns:
        piece_type: Tipo da peça identificado
        confidence: Nível de confiança na identificação (0-1)
    """
    if templates is None:
        # Fallback para o método baseado em geometria se não tiver templates
        return identify_piece_type(roi, piece_color)
    
    # Processar a região de interesse para destacar o símbolo
    symbol = enhanceSymbols(roi, piece_color)
    
    # Encontrar contornos do símbolo
    contours, _ = cv2.findContours(symbol, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Se não encontrou contornos, retornar tipo desconhecido
    if not contours:
        return "Unknown", 0.0
    
    # Obter o maior contorno (principal parte do símbolo)
    main_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(main_contour)
    
    # Se a área for muito pequena, pode não ser um símbolo válido
    if area < 10:
        return "Unknown", 0.0
    
    # Extrair características do símbolo detectado
    perimeter = cv2.arcLength(main_contour, True)
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    extent = float(area) / (w * h) if (w * h) > 0 else 0
    
    # Calcular solidez (solidity)
    hull = cv2.convexHull(main_contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0
    
    # Calcular momentos Hu para comparação de forma
    moments = cv2.moments(main_contour)
    hu_moments = cv2.HuMoments(moments)
    
    # Converter cor do formato "Black"/"White" para "black"/"white" para corresponder ao dicionário
    color_key = piece_color.lower()
    
    # MÉTODO APRIMORADO DE TEMPLATE MATCHING UTILIZANDO MÚLTIPLAS ABORDAGENS
    
    # 1. Método de correspondência direta com template
    # Redimensionar o símbolo para um tamanho padrão para facilitar a comparação
    standard_size = (64, 64)
    resized_symbol = cv2.resize(symbol, standard_size)
    
    # MELHORIA: Criar versões rotacionadas do símbolo para testar múltiplas orientações
    # Rotacionar o símbolo em 180 graus (como mencionado pelo usuário que a câmera está invertida)
    rotated_symbol = cv2.rotate(resized_symbol, cv2.ROTATE_180)
    
    # Dicionário para armazenar pontuações de similaridade
    scores = {}
    best_match = "Unknown"
    best_score = 0.0
    best_orientation = "normal"  # Para debug
    
    # Pesos para diferentes características
    weights = {
        'template_match': 0.5,  # Correspondência direta de template (aumentado o peso)
        'aspect_ratio': 0.15,   # Proporção largura/altura
        'solidity': 0.15,       # Solidez (área/área do invólucro convexo)
        'hu_moments': 0.2       # Momentos de Hu (invariantes a escala/rotação)
    }
    
    # Penalidades específicas para evitar falsos positivos de Torre
    tower_penalty = 0.2  # Penalidade quando o candidato é Torre para evitar superidentificação
    
    # Para testes/depuração - exibir informações
    debug_info = []
    
    # Comparar com cada template disponível
    for piece_type, template in templates[color_key].items():
        # Redimensionar o template para o mesmo tamanho padrão
        if 'original_image' in template:
            template_img = template['original_image']
            resized_template = cv2.resize(template_img, standard_size)
            
            # Inverter ou não dependendo da cor (para garantir que estamos comparando símbolos semelhantes)
            if (piece_color == "Black" and np.mean(resized_template) > 127) or \
               (piece_color == "White" and np.mean(resized_template) < 127):
                resized_template = 255 - resized_template
            
            # MELHORIA: Testar DUAS orientações (normal e rotacionada 180 graus)
            # Orientação 1: Normal
            result1 = cv2.matchTemplate(resized_symbol, resized_template, cv2.TM_CCOEFF_NORMED)
            _, template_score1, _, _ = cv2.minMaxLoc(result1)
            
            # Orientação 2: Rotacionada 180 graus
            result2 = cv2.matchTemplate(rotated_symbol, resized_template, cv2.TM_CCOEFF_NORMED)
            _, template_score2, _, _ = cv2.minMaxLoc(result2)
            
            # Usar a melhor orientação
            if template_score1 > template_score2:
                template_match_score = template_score1
                used_orientation = "normal"
            else:
                template_match_score = template_score2
                used_orientation = "rotated"
            
            # Normalizar para 0-1
            template_match_score = max(0, template_match_score)
        else:
            template_match_score = 0.5  # Valor neutro se não tiver imagem original
            used_orientation = "N/A"
        
        # 2. Similaridade de proporção (aspect ratio)
        aspect_diff = 1.0 - min(abs(aspect_ratio - template['aspect_ratio']) / max(template['aspect_ratio'], 0.01), 1.0)
        
        # 3. Similaridade de solidez (solidity)
        solidity_diff = 1.0 - min(abs(solidity - template['solidity']) / max(template['solidity'], 0.01), 1.0)
        
        # 4. Similaridade de momentos Hu (invariantes à escala, rotação e translação)
        hu_diff = 0.0
        for i in range(min(len(hu_moments), len(template['hu_moments']))):
            # Usar diferença logarítmica para momentos Hu
            if hu_moments[i][0] != 0 and template['hu_moments'][i][0] != 0:
                hu_diff += abs(np.log(abs(hu_moments[i][0])) - np.log(abs(template['hu_moments'][i][0])))
        
        # Normalizar e inverter a diferença Hu para obter similaridade (0-1)
        hu_similarity = max(0.0, 1.0 - min(hu_diff / 15.0, 1.0))  # Valor 15.0 é empírico
        
        # Combinação ponderada das similaridades
        score = (weights['template_match'] * template_match_score + 
                 weights['aspect_ratio'] * aspect_diff + 
                 weights['solidity'] * solidity_diff + 
                 weights['hu_moments'] * hu_similarity)
        
        # Aumentar a confiança das peças King e Queen pois são mais distintivas
        if piece_type == "King" or piece_type == "Queen":
            score *= 1.1  # Bônus de 10%
        
        # Aplicar penalidade para Tower/Rook para evitar falsos positivos
        if piece_type == "Rook" or piece_type == "Tower":
            score -= tower_penalty
        
        # Para depuração
        debug_info.append({
            'type': piece_type,
            'template_match': template_match_score,
            'orientation': used_orientation,
            'aspect': aspect_diff,
            'solidity': solidity_diff,
            'hu': hu_similarity,
            'final_score': score
        })
        
        # Armazenar pontuação
        scores[piece_type] = score
        
        # Atualizar melhor correspondência
        if score > best_score:
            best_score = score
            best_match = piece_type
            best_orientation = used_orientation
    
    # Exibir informações de depuração para ajudar a ajustar o algoritmo
    # print(f"DEBUG - Peça {piece_color} - Melhor: {best_match} ({best_score:.2f}) - Orientação: {best_orientation}")
    
    # Corrigir nomes (Rook -> Tower para manter compatibilidade)
    if best_match == "Rook":
        best_match = "Tower"
    
    # Converter pontuação para confiança (ajustar para dar valores mais realistas)
    confidence = min(1.0, max(0.0, best_score))
    
    # Se a confiança for muito baixa, usar o método de fallback
    if confidence < 0.4:
        fallback_type, fallback_conf = identify_piece_type(roi, piece_color)
        
        # Só usar o fallback se ele tiver uma confiança melhor
        if fallback_conf > confidence + 0.1:  # Adicionar margem para preferir o template matching
            return fallback_type, fallback_conf
    
    return best_match, confidence

def detectChessPieces(img, pieces_mask, contours=None, templates=None):
    """
    Detecta peças de xadrez e suas cores na imagem.
    
    Args:
        img: Imagem original
        pieces_mask: Máscara com as peças detectadas
        contours: Lista de contornos de peças pré-detectadas (opcional)
        templates: Dicionário de templates de referência (opcional)
    
    Returns:
        result_img: Imagem com as peças identificadas
        symbols_only: Visualização apenas dos símbolos
    """
    # Create a copy of the original image for drawing
    result_img = img.copy()
    # Create an all-black background for symbols-only visualization
    symbols_only = np.zeros_like(img)
    
    # Statistics counters for pieces
    white_pieces = 0
    black_pieces = 0
    piece_types = {'King': 0, 'Queen': 0, 'Tower': 0, 'Pawn': 0, 'Unknown': 0}
    
    # Find contours in the mask if not provided
    if contours is None:
        contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
    
    # Process each piece
    for i, cnt in enumerate(contours):
        # Get center and radius for the circular piece
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center = (int(x), int(y))
        radius = int(radius)
        
        # Get bounding rectangle (for ROI extraction)
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Ensure valid region
        if (x > 0 and y > 0 and x+w < img.shape[1] and y+h < img.shape[0]):
            # Get the region of interest (the chess piece)
            roi = img[y:y+h, x:x+w]
            
            # Skip if ROI is too small
            if roi.shape[0] < 20 or roi.shape[1] < 20:
                continue
            
            # Create a mask for the circular region only
            piece_circle_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(piece_circle_mask, (w//2, h//2), min(w, h)//2, 255, -1)
            
            # Identificar a cor da peça usando o método melhorado
            piece_color, text_color, symbol_color, avg_value, debug_info = identify_piece_color(roi, piece_circle_mask)
            
            # Identificar o tipo da peça
            piece_type, type_confidence = identify_piece_type_template_matching(roi, piece_color, piece_circle_mask, templates)
            
            # Incrementar o contador para este tipo de peça
            piece_types[piece_type] += 1
            
            # Atualizar contadores de cores
            if piece_color == "White":
                white_pieces += 1
            elif piece_color == "Black":
                black_pieces += 1
            
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
                
                # Create a visualization for the symbols-only image
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
            
            # Label the piece with more information
            brightness_text = f"{int(avg_value)}"
            dark_pct = debug_info['dark_percentage'] * 100 if 'dark_percentage' in debug_info else 0
            
            # Adicionar rótulo com ID, cor e tipo
            label = f"#{i+1} {piece_color} {piece_type}"
            cv2.putText(result_img, label, (x, y-10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
            cv2.putText(result_img, f"V:{brightness_text} D:{int(dark_pct)}%", (x, y+15), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
    
    # Add legend to the image
    legend_y = 30
    # Black piece legend with red symbol
    cv2.putText(result_img, "Black piece:", (10, legend_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(result_img, (120, legend_y-5), 10, (0, 0, 255), -1)
    
    # White piece legend with blue symbol
    cv2.putText(result_img, "White piece:", (10, legend_y+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.circle(result_img, (120, legend_y+25), 10, (255, 0, 0), -1)
    
    # Add stats text - color counts
    cv2.putText(result_img, f"White pieces: {white_pieces}", (10, legend_y+60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(result_img, f"Black pieces: {black_pieces}", (10, legend_y+80), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Add stats text - piece types
    piece_type_y = legend_y + 110
    for i, (type_name, count) in enumerate(piece_types.items()):
        if count > 0:  # Só mostrar tipos que foram detectados
            cv2.putText(result_img, f"{type_name}: {count}", (10, piece_type_y + i*20), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Add legend to symbols_only
    cv2.putText(symbols_only, "Black symbol (blue):", (10, legend_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(symbols_only, (160, legend_y-5), 10, (255, 0, 0), -1)
    
    cv2.putText(symbols_only, "White symbol (yellow):", (10, legend_y+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(symbols_only, (160, legend_y+25), 10, (0, 255, 255), -1)
    
    # Verificar se os contadores estão corretos
    if white_pieces + black_pieces != len(contours):
        print(f"⚠️ Atenção: Detectados {white_pieces} peças brancas e {black_pieces} peças pretas")
        print(f"   Total: {white_pieces + black_pieces} peças, mas há {len(contours)} contornos")
    
    # Exibir contagem de tipos de peças
    print("\n=== PEÇAS DETECTADAS POR TIPO ===")
    for type_name, count in piece_types.items():
        if count > 0:
            print(f"- {type_name}: {count}")
    
    return result_img, symbols_only

def analyze_hsv_colors(image, rect_size=30):
    """
    Ferramenta para analisar os valores HSV de diferentes regiões na imagem.
    Permite clicar na imagem para obter os valores HSV médios em uma área retangular.
    """
    img_copy = image.copy()
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Variável global para armazenar o estado do clique
    points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Calcular as coordenadas do retângulo
            x1 = max(0, x - rect_size // 2)
            y1 = max(0, y - rect_size // 2)
            x2 = min(image.shape[1], x + rect_size // 2)
            y2 = min(image.shape[0], y + rect_size // 2)
            
            # Extrair a região de interesse no espaço HSV
            roi_hsv = hsv_image[y1:y2, x1:x2]
            
            # Calcular os valores HSV médios
            avg_hsv = cv2.mean(roi_hsv)[:3]
            
            # Desenhar o retângulo na imagem
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Exibir os valores HSV médios
            text = f"HSV: {int(avg_hsv[0])},{int(avg_hsv[1])},{int(avg_hsv[2])}"
            cv2.putText(img_copy, text, (x2 + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Adicionar informações à lista de pontos
            points.append((x, y, avg_hsv))
            
            # Atualizar a exibição
            cv2.imshow("HSV Color Analyzer", img_copy)
            
            # Imprimir informações no console
            print(f"Região em ({x}, {y}): H={int(avg_hsv[0])}, S={int(avg_hsv[1])}, V={int(avg_hsv[2])}")
    
    # Configurar a janela e o callback do mouse
    cv2.namedWindow("HSV Color Analyzer")
    cv2.setMouseCallback("HSV Color Analyzer", mouse_callback)
    
    # Exibir instruções
    print("\n=== ANALISADOR DE CORES HSV ===")
    print("Clique em diferentes regiões da imagem para analisar os valores HSV.")
    print("Pressione 'q' para sair, 'r' para reiniciar, 's' para salvar.")
    
    # Exibir a imagem inicial
    cv2.imshow("HSV Color Analyzer", img_copy)
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            # Sair
            break
        elif key == ord('r'):
            # Reiniciar (limpar todos os pontos)
            img_copy = image.copy()
            points = []
            cv2.imshow("HSV Color Analyzer", img_copy)
        elif key == ord('s'):
            # Salvar a imagem com as anotações
            cv2.imwrite("hsv_analysis.jpg", img_copy)
            print("✅ Análise HSV salva como hsv_analysis.jpg")
            
            # Salvar os valores HSV em um arquivo de texto
            with open("hsv_values.txt", "w") as f:
                f.write("x,y,H,S,V\n")
                for p in points:
                    f.write(f"{p[0]},{p[1]},{int(p[2][0])},{int(p[2][1])},{int(p[2][2])}\n")
            print("✅ Valores HSV salvos em hsv_values.txt")
    
    cv2.destroyWindow("HSV Color Analyzer")
    return points

def visualize_detection(img, pieces_mask):
    """
    Cria uma visualização detalhada das peças detectadas.
    """
    # Criar uma cópia da imagem original para visualização
    visualization = img.copy()
    
    # Encontrar contornos na máscara das peças
    contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar contornos por área para eliminar ruído
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # Filtrar por área mínima
            valid_contours.append(cnt)
    
    # Desenhar contornos das peças com numeração
    for i, cnt in enumerate(valid_contours):
        # Obter área do contorno
        area = cv2.contourArea(cnt)
        # Obter centro e raio da peça
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center = (int(x), int(y))
        radius = int(radius)
        
        # Desenhar círculo em volta da peça
        cv2.circle(visualization, center, radius, (0, 255, 0), 2)
        
        # Adicionar número de identificação
        cv2.putText(visualization, f"#{i+1}", (center[0]-10, center[1]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    return visualization, valid_contours

def main():
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Análise de tabuleiro de xadrez 4x4')
    parser.add_argument('--image', type=str, default="chessboard_allpieces.png",
                        help='Caminho para a imagem do tabuleiro (padrão: chessboard_allpieces.png)')
    
    # Parâmetros para ajustar as faixas de cores HSV
    parser.add_argument('--yellow-lower', type=str, default="20,100,100",
                        help='Valor HSV inferior para a cor amarela (padrão: 20,100,100)')
    parser.add_argument('--yellow-upper', type=str, default="35,255,255",
                        help='Valor HSV superior para a cor amarela (padrão: 35,255,255)')
    parser.add_argument('--green-lower', type=str, default="35,50,50",
                        help='Valor HSV inferior para a cor verde (padrão: 35,50,50)')
    parser.add_argument('--green-upper', type=str, default="90,255,255",
                        help='Valor HSV superior para a cor verde (padrão: 90,255,255)')
    
    # Opção para salvar automaticamente as imagens intermediárias
    parser.add_argument('--save-all', action='store_true',
                        help='Salvar todas as imagens intermediárias para análise')
    parser.add_argument('--output-dir', type=str, default="output",
                        help='Diretório para salvar as imagens (padrão: output)')
    
    # Opção para analisar cores HSV
    parser.add_argument('--analyze-hsv', action='store_true',
                        help='Iniciar ferramenta para análise de cores HSV')
    
    # Opção para mostrar visualização de depuração detalhada
    parser.add_argument('--debug', action='store_true',
                        help='Mostrar visualizações de depuração detalhadas')
    
    # Opção para analisar as peças de referência
    parser.add_argument('--analyze-pieces', action='store_true',
                        help='Analisar as imagens de peças no diretório pieces-pictures')
    
    # Opção para usar Circle Hough Transform diretamente
    parser.add_argument('--use-hough', action='store_true',
                        help='Usar Hough Circle Transform para detecção de peças')
    
    args = parser.parse_args()
    
    # Se solicitado, analisar as peças de referência
    if args.analyze_pieces:
        print("\n=== ANALISANDO PEÇAS DE REFERÊNCIA ===")
        color_stats = analyze_reference_pieces()
        return
    
    # Carregar a imagem estática
    image_path = args.image
    
    # Verificar se o arquivo existe
    if not os.path.exists(image_path):
        print(f"❌ Arquivo não encontrado: {image_path}")
        return
        
    frame = cv2.imread(image_path)
    
    if frame is None:
        print(f"❌ Não foi possível carregar a imagem: {image_path}")
        return
    print(f"✅ Imagem carregada: {image_path}")
    
    # Se a opção de análise HSV estiver ativada, executar apenas essa ferramenta
    if args.analyze_hsv:
        analyze_hsv_colors(frame)
        return
    
    # Converter strings de argumentos HSV para arrays numpy
    yellow_lower = np.array([int(x) for x in args.yellow_lower.split(',')])
    yellow_upper = np.array([int(x) for x in args.yellow_upper.split(',')])
    green_lower = np.array([int(x) for x in args.green_lower.split(',')])
    green_upper = np.array([int(x) for x in args.green_upper.split(',')])
    
    # Definir faixas de cores
    yellow_range = (yellow_lower, yellow_upper)
    green_range = (green_lower, green_upper)
    
    # Criar diretório de saída se não existir
    if args.save_all and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"✅ Diretório de saída criado: {args.output_dir}")
    
    # Process frame with the customized parameters
    print("\n=== PROCESSANDO IMAGEM ===")
    edges, pieces_mask, initial_detection, board_mask = createPattern(frame, yellow_range, green_range)
    
    # Visualizar detecção de peças
    valid_contours = []
    contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar contornos válidos (área mínima e circularidade)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if circularity > 0.5:
                    valid_contours.append(cnt)
    
    # Criar visualização da detecção
    piece_detection_viz, _ = visualize_detection(frame, pieces_mask)
    
    # Contar quantas peças foram detectadas
    num_pieces = len(valid_contours)
    print(f"✅ Detectadas {num_pieces} peças no tabuleiro")
    
    # Verificar se encontramos o número correto de peças
    if num_pieces != 16:
        print(f"⚠️ Atenção: Esperadas 16 peças (8 brancas, 8 pretas), mas foram detectadas {num_pieces}.")
        
        # Se forçado a usar Hough Circle, tentar método adicional
        if args.use_hough or num_pieces < 10:
            print("Tentando método Hough Circle...")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
            
            # Método Hough Circle para detecção de peças
            circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                      param1=50, param2=30, minRadius=15, maxRadius=50)
            
            if circles is not None:
                circles = np.uint16(np.around(circles))
                print(f"✅ Método Hough Circle detectou {len(circles[0])} círculos")
                
                # Limpar a máscara anterior
                pieces_mask = np.zeros_like(gray)
                hough_viz = frame.copy()
                
                # Desenhar círculos na máscara e na visualização
                for circle in circles[0, :]:
                    center = (circle[0], circle[1])
                    radius = circle[2]
                    
                    # Desenhar círculo preenchido na máscara
                    cv2.circle(pieces_mask, center, radius, 255, -1)
                    
                    # Desenhar círculo na imagem de visualização
                    cv2.circle(hough_viz, center, radius, (0, 255, 0), 2)
                
                # Mostrar visualização Hough
                cv2.imshow("Hough Circle Detection", hough_viz)
                
                # Recalcular contornos
                contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                valid_contours = contours  # Usar todos os contornos gerados pelo Hough
                
                # Atualizar a visualização
                piece_detection_viz, _ = visualize_detection(frame, pieces_mask)
    
    # Carregar templates das peças de xadrez
    templates = load_piece_templates()
    
    # Detect chess pieces and their colors
    piece_detection, symbols_only = detectChessPieces(frame, pieces_mask, valid_contours, templates)
    
    # Create a 2x2 grid display (resize each to half size for better viewing)
    h, w = frame.shape[:2]
    h_half, w_half = h//2, w//2
    
    # Resize the images to fit the grid
    frame_small = cv2.resize(frame, (w_half, h_half))
    viz_small = cv2.resize(piece_detection_viz, (w_half, h_half))
    piece_detection_small = cv2.resize(piece_detection, (w_half, h_half))
    symbols_only_small = cv2.resize(symbols_only, (w_half, h_half))
    
    # Create the grid display
    top_row = np.hstack((frame_small, viz_small))
    bottom_row = np.hstack((piece_detection_small, symbols_only_small))
    combined = np.vstack((top_row, bottom_row))
    
    # Add labels to each quadrant
    cv2.putText(combined, "Original", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(combined, "Piece Detection", (w_half+10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(combined, "Color & Type", (10, h_half+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(combined, "Symbols Only", (w_half+10, h_half+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Salvar imagens intermediárias se solicitado
    if args.save_all:
        base_filename = os.path.basename(image_path).split('.')[0]
        
        # Salvar máscara
        mask_colored = cv2.cvtColor(pieces_mask, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(f"{args.output_dir}/{base_filename}_mask.jpg", mask_colored)
        
        # Salvar bordas
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(f"{args.output_dir}/{base_filename}_edges.jpg", edges_colored)
        
        # Salvar visualização de detecção de peças
        cv2.imwrite(f"{args.output_dir}/{base_filename}_detection.jpg", piece_detection_viz)
        
        # Salvar detecção de peças
        cv2.imwrite(f"{args.output_dir}/{base_filename}_pieces.jpg", piece_detection)
        
        # Salvar símbolos
        cv2.imwrite(f"{args.output_dir}/{base_filename}_symbols.jpg", symbols_only)
        
        # Salvar resultado combinado
        cv2.imwrite(f"{args.output_dir}/{base_filename}_combined.jpg", combined)
        
        print(f"✅ Imagens intermediárias salvas no diretório: {args.output_dir}")

    # Mostrar imagem em uma janela
    cv2.imshow("Chess Piece Detection", combined)
    print("Pressione qualquer tecla para sair ou 's' para salvar a imagem")
    
    # Criar visualização de depuração se solicitado
    if args.debug:
        # Extrair peças individuais para análise detalhada
        contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Encontrar peças válidas (circulares)
        valid_pieces = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:  # Filtrar por área mínima
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity > 0.5:
                        x, y, w, h = cv2.boundingRect(cnt)
                        if (x > 0 and y > 0 and x+w < frame.shape[1] and y+h < frame.shape[0]):
                            roi = frame[y:y+h, x:x+w]
                            if roi.shape[0] >= 20 and roi.shape[1] >= 20:
                                valid_pieces.append((cnt, roi, (x, y, w, h)))
        
        if valid_pieces:
            # Criar uma grade para mostrar peças individuais com histogramas
            piece_count = len(valid_pieces)
            cols = min(5, piece_count)
            rows = (piece_count + cols - 1) // cols
            
            # Tamanho para cada célula da grade (peça + histograma)
            cell_w, cell_h = 200, 200
            
            # Criar imagem de depuração
            debug_img = np.ones((rows * cell_h, cols * cell_w, 3), dtype=np.uint8) * 240
            
            for i, (cnt, roi, (x, y, w, h)) in enumerate(valid_pieces):
                row, col = i // cols, i % cols
                
                # Calcular posição na grade
                grid_x = col * cell_w
                grid_y = row * cell_h
                
                # Redimensionar ROI para exibição
                display_size = min(100, cell_w - 20)
                display_roi = cv2.resize(roi, (display_size, display_size))
                
                # Colocar ROI na célula
                y_offset = grid_y + 10
                x_offset = grid_x + (cell_w - display_size) // 2
                debug_img[y_offset:y_offset+display_size, x_offset:x_offset+display_size] = display_roi
                
                # Criar máscara circular para análise
                piece_circle_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(piece_circle_mask, (w//2, h//2), min(w, h)//2, 255, -1)
                
                # Extrair ROI mascarado
                masked_roi = cv2.bitwise_and(roi, roi, mask=piece_circle_mask)
                
                # Converter para HSV
                hsv_roi = cv2.cvtColor(masked_roi, cv2.COLOR_BGR2HSV)
                
                # Analisar cores dentro da máscara
                masked_pixels = hsv_roi[piece_circle_mask > 0]
                
                if len(masked_pixels) > 0:
                    # Identificar cor e tipo da peça
                    piece_color, _, _, avg_value, debug_info = identify_piece_color(roi, piece_circle_mask)
                    piece_type, type_confidence = identify_piece_type_template_matching(roi, piece_color, piece_circle_mask, templates)
                    
                    # Estatísticas
                    avg_value = np.mean(masked_pixels[:, 2])
                    dark_pixels = np.sum(masked_pixels[:, 2] < 90)
                    dark_percentage = dark_pixels / len(masked_pixels) if len(masked_pixels) > 0 else 0
                    
                    # Desenhar histograma de valor (V do HSV)
                    hist_height = 80
                    hist_y = y_offset + display_size + 10
                    hist_x = grid_x + 10
                    hist_width = cell_w - 20
                    
                    hist_img = np.ones((hist_height, hist_width, 3), dtype=np.uint8) * 240
                    v_values = masked_pixels[:, 2]
                    hist = np.histogram(v_values, bins=32, range=(0, 256))[0]
                    hist = hist * hist_height / (hist.max() if hist.max() > 0 else 1)
                    
                    for j in range(32):
                        bin_x = int(j * hist_width / 32)
                        bin_width = int(hist_width / 32)
                        bin_height = int(hist[j])
                        cv2.rectangle(hist_img, 
                                      (bin_x, hist_height - bin_height), 
                                      (bin_x + bin_width, hist_height),
                                      (100, 100, 255), -1)
                    
                    # Adicionar linha para o valor médio
                    avg_x = int(avg_value * hist_width / 256)
                    cv2.line(hist_img, (avg_x, 0), (avg_x, hist_height), (0, 0, 255), 2)
                    
                    # Adicionar linha para o limiar de pixels escuros (90)
                    thresh_x = int(90 * hist_width / 256)
                    cv2.line(hist_img, (thresh_x, 0), (thresh_x, hist_height), (0, 255, 0), 1)
                    
                    # Adicionar histograma à imagem de depuração
                    debug_img[hist_y:hist_y+hist_height, hist_x:hist_x+hist_width] = hist_img
                    
                    # Adicionar rótulos com cor e tipo
                    color_label = f"#{i+1} {piece_color} {piece_type}"
                    cv2.putText(debug_img, color_label, 
                               (grid_x + 10, y_offset + display_size + 8), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
                    
                    # Adicionar estatísticas
                    stats_text = f"V: {avg_value:.1f}, Dark: {dark_percentage:.2f}, Conf: {type_confidence:.2f}"
                    cv2.putText(debug_img, stats_text,
                               (grid_x + 10, hist_y + hist_height + 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            
            # Mostrar a imagem de depuração
            cv2.imshow("Chess Pieces Debug", debug_img)
            
            # Salvar a imagem de depuração se solicitado
            if args.save_all:
                cv2.imwrite(f"{args.output_dir}/pieces_debug.jpg", debug_img)
    
    # Aguardar pressionamento de tecla
    key = cv2.waitKey(0) & 0xFF
    if key == ord('s'):
        # Save result when 's' is pressed
        output_filename = f"chess_detection_{os.path.basename(image_path)}.jpg"
        cv2.imwrite(output_filename, combined)
        print(f"✅ Análise salva como {output_filename}")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
