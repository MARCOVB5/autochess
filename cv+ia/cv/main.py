"""
Módulo principal do sistema de visão computacional para detecção de peças de xadrez
"""
import cv2
import numpy as np
import argparse
import os
import platform
import json
from cv.modules.board_processing import process_board_image, visualize_board_and_pieces

def show_with_matplotlib(image, title="Detecção de Tabuleiro e Peças"):
    """
    Exibe uma imagem usando matplotlib ao invés do OpenCV.
    Esta função é mais confiável no Linux.
    """
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    
    # Converter de BGR para RGB (OpenCV usa BGR, matplotlib usa RGB)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Criar figura e mostrar imagem
    plt.figure(figsize=(12, 10))
    plt.imshow(rgb_image)
    plt.title(title)
    plt.axis('off')  # Ocultar eixos
    plt.tight_layout()
    plt.show()

def generate_chess_notation_matrix(squares, rows=4, cols=4):
    """
    Gera uma matriz de notação de peças de xadrez (WP, WR, WQ, WK, BP, BR, BQ, BK) 
    a partir das informações dos quadrados detectados.
    
    Args:
        squares: Lista de informações dos quadrados 
        rows: Número de linhas do tabuleiro
        cols: Número de colunas do tabuleiro
        
    Returns:
        matriz: Matriz com notação das peças
        matriz_json: Representação JSON da matriz
    """
    # Inicializar matriz com espaços vazios
    matriz = [['' for _ in range(cols)] for _ in range(rows)]
    
    # Mapear cada quadrado para sua posição na matriz
    for square in squares:
        row, col = square['position']
        
        if square['contains_piece']:
            piece_color = square['piece_color']
            piece_type = "P"  # Default para peão (Pawn)
            
            # Verificar se temos informação do tipo da peça
            if 'piece_info' in square and 'type' in square['piece_info']:
                piece_type_val = square['piece_info']['type']
                if piece_type_val == 'pawn':
                    piece_type = "P"
                elif piece_type_val == 'rook':
                    piece_type = "R"
                elif piece_type_val == 'queen':
                    piece_type = "Q"
                elif piece_type_val == 'king':
                    piece_type = "K"
            
            # Prefixar com W para branco ou B para preto
            if piece_color == 'white':
                notation = f"{piece_type}"
            elif piece_color == 'black':
                notation = f"{piece_type.lower()}"
            else:
                notation = "??"  # Peça com cor indeterminada
                
            matriz[row][col] = notation
        else:
            # Quadrado vazio
            matriz[row][col] = "."
    
    # Criar representação JSON das posições
    matriz_json = []
    for r in range(rows):
        row_data = []
        for c in range(cols):
            square_data = {
                "position": f"{chr(65+c)}{rows-r}",  # A1, B2, etc.
                "piece": matriz[r][c] if matriz[r][c] != ".." else None
            }
            row_data.append(square_data)
        matriz_json.append(row_data)
    
    return matriz, matriz_json

def print_chess_matrix(matriz):
    """
    Imprime uma matriz de peças de xadrez em formato legível.
    
    Args:
        matriz: Matriz com notação das peças
    """
    rows = len(matriz)
    cols = len(matriz[0]) if matriz else 0
    
    # Imprimir cabeçalho de colunas (A, B, C, D)
    print("  ", end="")
    for c in range(cols):
        print(f"  {chr(65+c)} ", end="")
    print("\n")
    
    # Imprimir linhas com números
    for r in range(rows):
        print(f"{rows-r} ", end="")
        for c in range(cols):
            print(f"[{matriz[r][c]}]", end="")
        print(f" {rows-r}")  # Imprimir número da linha novamente
    
    # Imprimir cabeçalho de colunas novamente
    print("\n  ", end="")
    for c in range(cols):
        print(f"  {chr(65+c)} ", end="")
    print()

def detect_chess_position(image_path, visualize=False, save_all=False, save_matrix=False, output_dir="output"):
    """
    Detecta a posição das peças no tabuleiro de xadrez a partir de uma imagem.
    
    Args:
        image_path (str): Caminho para a imagem do tabuleiro
        visualize (bool): Se True, exibe a visualização do tabuleiro
        save_all (bool): Se True, salva todas as imagens intermediárias
        save_matrix (bool): Se True, salva a matriz de peças em JSON
        output_dir (str): Diretório para salvar os resultados
        
    Returns:
        dict: Dicionário contendo a matriz de peças, JSON correspondente e resultado da detecção
    """
    # Verificar se o arquivo existe
    if not os.path.exists(image_path):
        print(f"❌ Arquivo não encontrado: {image_path}")
        return None
        
    frame = cv2.imread(image_path)
    
    if frame is None:
        print(f"❌ Não foi possível carregar a imagem: {image_path}")
        return None
    
    # Criar diretório de saída se não existir
    if (save_all or save_matrix) and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Processar a imagem
    warped_board, squares, corners = process_board_image(frame)
    
    if warped_board is None:
        print("❌ Falha ao detectar o tabuleiro. Verifique a imagem e tente novamente.")
        return None
    
    # Gerar matriz de notação de xadrez
    matriz, matriz_json = generate_chess_notation_matrix(squares)
    
    # Salvar matriz em formato JSON se solicitado
    if save_matrix:
        base_filename = os.path.basename(image_path).split('.')[0]
        json_path = f"{output_dir}/{base_filename}_chess_matrix.json"
        
        with open(json_path, 'w') as json_file:
            json.dump(matriz_json, json_file, indent=2)
    
    # Preparar resultado para retorno
    result = {
        "matriz": matriz,
        "matriz_json": matriz_json,
        "total_squares": len(squares),
        "pieces_count": sum(1 for s in squares if s['contains_piece']),
        "white_pieces": sum(1 for s in squares if s['piece_color'] == 'white'),
        "black_pieces": sum(1 for s in squares if s['piece_color'] == 'black'),
    }
    
    # Visualização opcional
    if visualize:
        # Criar visualização do tabuleiro e peças
        board_visualization = visualize_board_and_pieces(frame, warped_board, squares, corners)
        
        # Redimensionar para exibição
        scale_percent = 40  # Porcentagem do tamanho original
        width = int(board_visualization.shape[1] * scale_percent / 100)
        height = int(board_visualization.shape[0] * scale_percent / 100)
        
        board_viz_resized = cv2.resize(board_visualization, (width, height))
        
        # Salvar imagens se solicitado
        if save_all:
            base_filename = os.path.basename(image_path).split('.')[0]
            output_path = f"{output_dir}/{base_filename}_board_detection.jpg"
            cv2.imwrite(output_path, board_visualization)
            result["detection_image_path"] = output_path
        
        # Detectar automaticamente Linux ou usar opção explícita
        is_linux = platform.system() == 'Linux'
        use_matplotlib = is_linux
        
        if use_matplotlib:
            try:
                show_with_matplotlib(board_viz_resized)
            except ImportError:
                # Fallback para OpenCV
                use_matplotlib = False
        
        if not use_matplotlib:
            # Exibir com OpenCV
            cv2.imshow("Detecção de Tabuleiro e Peças", board_viz_resized)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    
    return result

def main():
    """
    Função principal para uso via linha de comando.
    Analisa argumentos e chama a função de detecção.
    """
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Análise de tabuleiro de xadrez 4x4')
    parser.add_argument('--image', type=str, default="cv/assets/testing-chessboards/chessboard_allpieces.jpg",
                        help='Caminho para a imagem do tabuleiro (padrão: chessboard_allpieces.png)')
    
    # Opção para salvar automaticamente as imagens intermediárias
    parser.add_argument('--save-all', action='store_true',
                        help='Salvar todas as imagens intermediárias para análise')
    parser.add_argument('--output-dir', type=str, default="output",
                        help='Diretório para salvar as imagens (padrão: output)')
    # Adicionar opção para usar matplotlib ao invés de OpenCV para visualização
    parser.add_argument('--use-matplotlib', action='store_true',
                        help='Usar matplotlib para visualização (recomendado para Linux)')
    # Opção para salvar matriz de peças em JSON
    parser.add_argument('--save-matrix', action='store_true',
                        help='Salvar matriz de peças em formato JSON')
    # Opção para não visualizar (útil para processamento em lote)
    parser.add_argument('--no-viz', action='store_true',
                        help='Não exibir visualização (útil para processamento em lote)')
    
    args = parser.parse_args()

    # Carregar a imagem estática
    image_path = args.image
    print(f"✅ Processando imagem: {image_path}")
    
    # Chamar a função de detecção
    result = detect_chess_position(
        image_path=image_path,
        visualize=not args.no_viz,
        save_all=args.save_all,
        save_matrix=args.save_matrix,
        output_dir=args.output_dir
    )
    
    if result is not None:
        print("\n=== RESULTADO DA DETECÇÃO ===")
        print(f"Total de quadrados: {result['total_squares']}")
        print(f"Peças: {result['pieces_count']} ({result['white_pieces']} brancas, {result['black_pieces']} pretas)")
        
        print("\n=== MATRIZ DE PEÇAS ===")
        print_chess_matrix(result["matriz"])
        
        if args.save_matrix:
            base_filename = os.path.basename(image_path).split('.')[0]
            print(f"\n✅ Matriz de peças salva em: {args.output_dir}/{base_filename}_chess_matrix.json")
    
    return result

if __name__ == "__main__":
    main()
