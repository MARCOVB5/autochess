"""
Módulo principal do sistema de visão computacional para detecção de peças de xadrez
"""
import cv2
import numpy as np
import argparse
import os
from modules.pattern_detection import process_board_image, visualize_board_and_pieces
from modules.visualization import analyze_hsv_colors
from modules.utils import analyze_reference_pieces

def main():
    # Configurar o parser de argumentos
    parser = argparse.ArgumentParser(description='Análise de tabuleiro de xadrez 4x4')
    parser.add_argument('--image', type=str, default="assets/chessboard_allpieces.jpg",
                        help='Caminho para a imagem do tabuleiro (padrão: chessboard_allpieces.png)')
    
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
    
    # Opção para segmentar o tabuleiro em quadrados
    parser.add_argument('--segment-squares', action='store_true',
                        help='Segmentar o tabuleiro em 16 quadrados (4x4)')
    
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
    
    # Se a opção de segmentação de quadrados estiver ativada, mostrar visualização detalhada
    if args.segment_squares:
        # Criar uma matriz 4x4 de recortes de peças para visualização
        grid_h, grid_w = 2 * warped_board.shape[0] // 3, 2 * warped_board.shape[1] // 3
        grid_img = np.ones((grid_h, grid_w, 3), dtype=np.uint8) * 240
        square_size = warped_board.shape[0] // 4
        display_size = grid_h // 4
        
        for square in squares:
            row, col = square['position']
            # Calcular posição na grade de visualização
            grid_x = col * display_size
            grid_y = row * display_size
            
            # Redimensionar a imagem do quadrado para exibição
            square_img = cv2.resize(square['image'], (display_size, display_size))
            
            # Inserir na grade
            grid_img[grid_y:grid_y+display_size, grid_x:grid_x+display_size] = square_img
            
            # Adicionar coordenada e indicação de peça
            board_coord = square['board_coords']
            contains_piece = square['contains_piece']
            piece_color = square['piece_color']
            square_color = "Y" if square['color'] == "yellow" else "G"
            
            # Desenhar retângulo de borda com cor conforme o tipo de quadrado
            border_color = (0, 255, 255) if square['color'] == "yellow" else (0, 255, 0)
            cv2.rectangle(grid_img, (grid_x, grid_y), 
                         (grid_x+display_size-1, grid_y+display_size-1), border_color, 2)
            
            # Adicionar informações de coordenada e cor do quadrado (preto com fundo branco para legibilidade)
            text_bg = np.ones((20, display_size, 3), dtype=np.uint8) * 255
            cv2.putText(text_bg, f"{board_coord} {square_color}", (5, 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Copiar texto para a grade
            grid_img[grid_y:grid_y+20, grid_x:grid_x+display_size] = text_bg
            
            # Se contém peça, adicionar indicação e cor da peça no rodapé
            if contains_piece:
                footer_bg = np.ones((20, display_size, 3), dtype=np.uint8) * 255
                
                if piece_color == 'white':
                    color_text = "BRANCA"
                    text_color = (0, 0, 0)
                elif piece_color == 'black':
                    color_text = "PRETA"
                    text_color = (0, 0, 255)
                else:
                    color_text = "PEÇA ?"
                    text_color = (0, 140, 255)
                
                # Verificar se usou template matching
                template_info = ""
                if 'template_match' in square and square['template_match']['color'] is not None:
                    template_color = square['template_match']['color']
                    template_conf = square['template_match']['confidence']
                    if template_conf > 0.5:
                        template_info = f" (T:{template_conf:.2f})"
                
                cv2.putText(footer_bg, color_text + template_info, (5, 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
                
                # Copiar rodapé para a grade
                grid_img[grid_y+display_size-20:grid_y+display_size, grid_x:grid_x+display_size] = footer_bg
    
    # Redimensionar para exibição
    scale_percent = 40  # Porcentagem do tamanho original
    width = int(board_visualization.shape[1] * scale_percent / 100)
    height = int(board_visualization.shape[0] * scale_percent / 100)
    
    board_viz_resized = cv2.resize(board_visualization, (width, height))
    
    # Mostrar as visualizações
    cv2.imshow("Detecção de Tabuleiro e Peças", board_viz_resized)
    
    if args.segment_squares:
        # Redimensionar grid para exibição
        grid_resized = cv2.resize(grid_img, 
                                (int(grid_img.shape[1] * scale_percent / 100),
                                 int(grid_img.shape[0] * scale_percent / 100)))
        cv2.imshow("Quadrados Individuais", grid_resized)
    
    # Salvar imagens se solicitado
    if args.save_all:
        base_filename = os.path.basename(image_path).split('.')[0]
        cv2.imwrite(f"{args.output_dir}/{base_filename}_board_detection.jpg", board_visualization)
        
        if args.segment_squares:
            cv2.imwrite(f"{args.output_dir}/{base_filename}_squares_grid.jpg", grid_img)
            
            # Salvar cada quadrado individualmente
            squares_dir = f"{args.output_dir}/squares"
            if not os.path.exists(squares_dir):
                os.makedirs(squares_dir)
            
            for square in squares:
                board_coord = square['board_coords']
                color = "yellow" if square['color'] == "yellow" else "green"
                has_piece = "piece" if square['contains_piece'] else "empty"
                piece_color = square['piece_color'] if square['piece_color'] else "unknown"
                
                if square['contains_piece']:
                    filename = f"{squares_dir}/{base_filename}_{board_coord}_{color}_{piece_color}.jpg"
                else:
                    filename = f"{squares_dir}/{base_filename}_{board_coord}_{color}_empty.jpg"
                    
                cv2.imwrite(filename, square['image'])
    
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
