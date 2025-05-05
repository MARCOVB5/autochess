import cv2
import numpy as np
import os
import argparse

# Importar funções do script principal
try:
    from main import enhanceSymbols, identify_piece_color, identify_piece_type_template_matching, load_piece_templates
except ImportError:
    print("⚠️ Não foi possível importar funções do arquivo main.py. Certifique-se de que o arquivo existe no mesmo diretório.")

def detectChessboardCorners(image):
    """
    Detecta os cantos do tabuleiro de xadrez usando a máscara de cores verde e amarela.
    """
    # Converter para HSV para detecção de cores
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Definir faixas de cor para verde e amarelo
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([90, 255, 255])
    
    # Criar máscaras para cores
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    
    # Combinar máscaras
    board_mask = cv2.bitwise_or(mask_yellow, mask_green)
    
    # Aplicar operações morfológicas para melhorar a máscara
    kernel = np.ones((5, 5), np.uint8)
    board_mask = cv2.morphologyEx(board_mask, cv2.MORPH_CLOSE, kernel)
    board_mask = cv2.morphologyEx(board_mask, cv2.MORPH_OPEN, kernel)
    
    # Encontrar contornos na máscara
    contours, _ = cv2.findContours(board_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Verificar se encontrou contornos
    if not contours:
        print("❌ Nenhum contorno de tabuleiro encontrado")
        return None, None
    
    # Pegar o maior contorno (presumivelmente o tabuleiro)
    board_contour = max(contours, key=cv2.contourArea)
    
    # Aproximar o contorno para um polígono
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
    corners = np.array([pt[1] for pt in ordered_points], dtype=np.float32)
    
    return corners, board_mask

def warpChessboardPerspective(image, corners):
    """
    Aplica transformação de perspectiva no tabuleiro.
    """
    # Definir as dimensões do tabuleiro transformado (um quadrado para manter a proporção)
    board_size = 400  # tamanho em pixels do tabuleiro transformado
    dst_points = np.array([
        [0, 0],
        [board_size, 0],
        [board_size, board_size],
        [0, board_size]
    ], dtype=np.float32)
    
    # Calcular a matriz de transformação de perspectiva
    M = cv2.getPerspectiveTransform(corners, dst_points)
    
    # Aplicar a transformação de perspectiva
    warped_board = cv2.warpPerspective(image, M, (board_size, board_size))
    
    return warped_board, M

def divideIntoSquares(warped_board):
    """
    Divide o tabuleiro em 16 quadrantes (4x4).
    """
    board_size = warped_board.shape[0]
    square_size = board_size // 4
    squares = []
    
    for row in range(4):
        for col in range(4):
            # Extrair o quadrante
            x1 = col * square_size
            y1 = row * square_size
            square_roi = warped_board[y1:y1 + square_size, x1:x1 + square_size]
            squares.append({
                'roi': square_roi,
                'position': (row, col),
                'coords': (x1, y1, square_size, square_size)
            })
    
    return squares

def detectPieceInSquare(square_roi):
    """
    Detecta se um quadrante contém uma peça.
    """
    # Converter para escala de cinza
    gray = cv2.cvtColor(square_roi, cv2.COLOR_BGR2GRAY)
    
    # Aplicar blur para reduzir ruído
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Criar uma máscara circular no centro do quadrante
    h, w = square_roi.shape[:2]
    center_x, center_y = w // 2, h // 2
    radius = min(w, h) // 3
    
    circle_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(circle_mask, (center_x, center_y), radius, 255, -1)
    
    # Aplicar limiarização adaptativa
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Aplicar a máscara
    masked = cv2.bitwise_and(thresh, thresh, mask=circle_mask)
    
    # Contar pixels não-zero na região central
    non_zero_pixels = cv2.countNonZero(masked)
    
    # Calcular porcentagem de área preenchida
    total_circle_pixels = np.sum(circle_mask > 0)
    fill_percentage = non_zero_pixels / total_circle_pixels if total_circle_pixels > 0 else 0
    
    # Definir um limiar para considerar que há uma peça
    piece_threshold = 0.25  # 25% da área do círculo preenchida
    has_piece = fill_percentage > piece_threshold
    
    return has_piece, circle_mask, fill_percentage

def analyzePieceInSquare(square_roi, piece_mask, templates):
    """
    Analisa uma peça dentro de um quadrante para determinar cor e tipo.
    """
    # Redimensionar para tamanho padrão
    standard_size = (64, 64)
    resized_roi = cv2.resize(square_roi, standard_size)
    resized_mask = cv2.resize(piece_mask, standard_size)
    
    # Identificar a cor da peça
    piece_color, text_color, symbol_color, avg_value, debug_info = identify_piece_color(
        resized_roi, resized_mask)
    
    # Identificar o tipo da peça
    piece_type, confidence = identify_piece_type_template_matching(
        resized_roi, piece_color, resized_mask, templates)
    
    return piece_color, piece_type, confidence

def drawChessboardAnnotations(image, squares, results):
    """
    Desenha anotações no tabuleiro warped com as peças identificadas.
    """
    annotated = image.copy()
    
    # Desenhar grid
    h, w = image.shape[:2]
    square_size = h // 4
    
    for i in range(1, 4):
        # Linhas horizontais
        cv2.line(annotated, (0, i * square_size), (w, i * square_size), (200, 200, 200), 1)
        # Linhas verticais
        cv2.line(annotated, (i * square_size, 0), (i * square_size, h), (200, 200, 200), 1)
    
    # Desenhar informações das peças
    for i, square in enumerate(squares):
        position = square['position']
        coords = square['coords']
        result = results[i]
        
        if result['has_piece']:
            # Extrair coordenadas
            x1, y1, size, _ = coords
            center_x = x1 + size // 2
            center_y = y1 + size // 2
            
            # Desenhar círculo ao redor da peça
            cv2.circle(annotated, (center_x, center_y), size // 3, 
                     (0, 255, 0), 2)
            
            # Adicionar etiqueta com tipo e cor
            color = result['color']
            piece_type = result['type']
            
            label = f"{color[0]}{piece_type[0]}"
            cv2.putText(annotated, label, (x1 + 5, y1 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                       (0, 255, 255) if color == "White" else (0, 0, 255), 2)
            
            # Adicionar confiança
            conf_text = f"{result['confidence']:.2f}"
            cv2.putText(annotated, conf_text, (x1 + 5, y1 + size - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    return annotated

def drawOriginalAnnotations(image, corners, board_state):
    """
    Desenha anotações na imagem original para mostrar o tabuleiro detectado.
    """
    result = image.copy()
    
    # Desenhar os cantos do tabuleiro
    for i, corner in enumerate(corners):
        cv2.circle(result, (int(corner[0]), int(corner[1])), 10, (0, 255, 0), -1)
        cv2.putText(result, str(i), (int(corner[0]) + 15, int(corner[1])),
                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    # Desenhar contorno do tabuleiro
    cv2.polylines(result, [np.int32(corners)], True, (0, 255, 0), 3)
    
    # Contar peças
    white_pieces = sum(1 for row in board_state for cell in row 
                     if cell and cell['has_piece'] and cell['color'] == 'White')
    black_pieces = sum(1 for row in board_state for cell in row 
                     if cell and cell['has_piece'] and cell['color'] == 'Black')
    
    # Adicionar estatísticas
    cv2.putText(result, f"White pieces: {white_pieces}", (20, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(result, f"Black pieces: {black_pieces}", (20, 60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return result

def main():
    """
    Função principal para processamento do tabuleiro de xadrez.
    """
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description='Análise de tabuleiro de xadrez 4x4 usando grade fixa')
    parser.add_argument('--image', type=str, default="chessboard_allpieces.png",
                      help='Caminho para a imagem do tabuleiro (padrão: chessboard_allpieces.png)')
    parser.add_argument('--debug', action='store_true',
                      help='Mostrar imagens intermediárias para depuração')
    parser.add_argument('--save', action='store_true',
                      help='Salvar resultados como imagens')
    
    args = parser.parse_args()
    
    # Carregar a imagem do tabuleiro
    image_path = args.image
    if not os.path.exists(image_path):
        print(f"❌ Arquivo não encontrado: {image_path}")
        return
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Não foi possível carregar a imagem: {image_path}")
        return
    
    print(f"✅ Imagem carregada: {image_path}")
    
    # Carregar templates das peças
    templates = load_piece_templates()
    if templates is None:
        print("❌ Falha ao carregar templates. Certifique-se de que o diretório 'assets' existe.")
        return
    
    # Detectar cantos do tabuleiro
    print("Detectando tabuleiro...")
    corners, board_mask = detectChessboardCorners(image)
    
    if corners is None:
        print("❌ Falha ao detectar os cantos do tabuleiro")
        return
    
    # Aplicar transformação de perspectiva
    print("Aplicando transformação de perspectiva...")
    warped_board, transformation_matrix = warpChessboardPerspective(image, corners)
    
    # Dividir em quadrantes
    print("Dividindo tabuleiro em quadrantes...")
    squares = divideIntoSquares(warped_board)
    
    # Mostrar tabuleiro com perspectiva corrigida
    if args.debug:
        cv2.imshow("Tabuleiro Transformado", warped_board)
    
    # Analisar cada quadrante
    print("Analisando peças em cada quadrante...")
    square_results = []
    board_state = [[None for _ in range(4)] for _ in range(4)]
    
    for square in squares:
        roi = square['roi']
        row, col = square['position']
        
        # Verificar se tem peça
        has_piece, piece_mask, fill_pct = detectPieceInSquare(roi)
        
        if has_piece:
            # Analisar a peça
            color, piece_type, confidence = analyzePieceInSquare(roi, piece_mask, templates)
            result = {
                'has_piece': True,
                'color': color,
                'type': piece_type,
                'confidence': confidence,
                'fill_percentage': fill_pct
            }
        else:
            result = {
                'has_piece': False,
                'fill_percentage': fill_pct
            }
        
        square_results.append(result)
        board_state[row][col] = result
        
        if args.debug:
            print(f"Quadrante ({row}, {col}): {'Peça ' + color + ' ' + piece_type if has_piece else 'Vazio'}")
    
    # Desenhar anotações no tabuleiro warped
    print("Gerando visualizações...")
    annotated_warped = drawChessboardAnnotations(warped_board, squares, square_results)
    
    # Desenhar anotações na imagem original
    annotated_original = drawOriginalAnnotations(image, corners, board_state)
    
    # Mostrar resultados
    cv2.imshow("Tabuleiro Original Anotado", annotated_original)
    cv2.imshow("Tabuleiro com Peças Identificadas", annotated_warped)
    
    # Contar peças por tipo e cor
    white_pieces = {
        'King': 0, 'Queen': 0, 'Tower': 0, 'Pawn': 0, 'Unknown': 0
    }
    black_pieces = {
        'King': 0, 'Queen': 0, 'Tower': 0, 'Pawn': 0, 'Unknown': 0
    }
    
    for result in square_results:
        if result['has_piece']:
            if result['color'] == 'White':
                white_pieces[result['type']] += 1
            else:
                black_pieces[result['type']] += 1
    
    # Exibir estatísticas
    print("\n=== PEÇAS DETECTADAS ===")
    print("BRANCAS:")
    for piece_type, count in white_pieces.items():
        if count > 0:
            print(f"  - {piece_type}: {count}")
    
    print("\nPRETAS:")
    for piece_type, count in black_pieces.items():
        if count > 0:
            print(f"  - {piece_type}: {count}")
    
    # Salvar resultados se solicitado
    if args.save:
        base_filename = os.path.basename(image_path).split('.')[0]
        
        # Criar diretório se não existir
        if not os.path.exists("output"):
            os.makedirs("output")
        
        # Salvar imagens
        cv2.imwrite(f"output/{base_filename}_original_annotated.jpg", annotated_original)
        cv2.imwrite(f"output/{base_filename}_warped_annotated.jpg", annotated_warped)
        
        if args.debug:
            # Salvar máscara do tabuleiro
            cv2.imwrite(f"output/{base_filename}_board_mask.jpg", board_mask)
            # Salvar tabuleiro warped sem anotações
            cv2.imwrite(f"output/{base_filename}_warped.jpg", warped_board)
        
        print(f"✅ Imagens salvas no diretório 'output'")
    
    print("\nPressione qualquer tecla para sair...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 