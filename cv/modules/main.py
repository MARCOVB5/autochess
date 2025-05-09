"""
Módulo principal do sistema de visão computacional para detecção de peças de xadrez
"""
import cv2
import numpy as np
import argparse
import os
from cv.modules.board_processing import process_board_image, visualize_board_and_pieces

def main():
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Análise de tabuleiro de xadrez 4x4')
    parser.add_argument('--image', type=str, default="assets/testing-chessboards/chessboard_allpieces.jpg",
                        help='Caminho para a imagem do tabuleiro (padrão: chessboard_allpieces.png)')
    
    # Opção para salvar automaticamente as imagens intermediárias
    parser.add_argument('--save-all', action='store_true',
                        help='Salvar todas as imagens intermediárias para análise')
    parser.add_argument('--output-dir', type=str, default="output",
                        help='Diretório para salvar as imagens (padrão: output)')
    
    args = parser.parse_args()

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
    
    # Criar diretório de saída se não existir
    if args.save_all and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"✅ Diretório de saída criado: {args.output_dir}")
    
    # Processar a imagem usando a nova abordagem
    print("\n=== PROCESSANDO IMAGEM ===")
    print("🔍 Detectando tabuleiro e peças...")
    
    # Processar a imagem
    warped_board, squares, corners = process_board_image(frame)
    
    if warped_board is None:
        print("❌ Falha ao detectar o tabuleiro. Verifique a imagem e tente novamente.")
        return
    
    # Exibir informações sobre a detecção
    yellow_squares = sum(1 for s in squares if s['color'] == 'yellow')
    green_squares = sum(1 for s in squares if s['color'] == 'green')
    pieces_count = sum(1 for s in squares if s['contains_piece'])
    white_pieces = sum(1 for s in squares if s['piece_color'] == 'white')
    black_pieces = sum(1 for s in squares if s['piece_color'] == 'black')
    
    print(f"✅ Detecção concluída:")
    print(f"   - Tabuleiro 4x4 detectado com {len(squares)} quadrados")
    print(f"   - Quadrados: {yellow_squares} amarelos, {green_squares} verdes")
    print(f"   - Peças: {pieces_count} no total ({white_pieces} brancas, {black_pieces} pretas)")
    
    # Criar visualização do tabuleiro e peças
    board_visualization = visualize_board_and_pieces(frame, warped_board, squares, corners)
    
    # Redimensionar para exibição
    scale_percent = 40  # Porcentagem do tamanho original
    width = int(board_visualization.shape[1] * scale_percent / 100)
    height = int(board_visualization.shape[0] * scale_percent / 100)
    
    board_viz_resized = cv2.resize(board_visualization, (width, height))
    
    # Mostrar as visualizações
    cv2.imshow("Detecção de Tabuleiro e Peças", board_viz_resized)
    
    # Salvar imagens se solicitado
    if args.save_all:
        base_filename = os.path.basename(image_path).split('.')[0]
        cv2.imwrite(f"{args.output_dir}/{base_filename}_board_detection.jpg", board_visualization)
    
    # Aguardar pressionamento de tecla
    key = cv2.waitKey(0) & 0xFF
    if key == ord('s'):
        # Salvar resultado quando 's' for pressionado
        output_filename = f"chess_detection_{os.path.basename(image_path)}"
        cv2.imwrite(output_filename, board_viz_resized)
        print(f"✅ Resultado salvo como {output_filename}")
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
