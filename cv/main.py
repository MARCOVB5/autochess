"""
Módulo principal do sistema de visão computacional para detecção de peças de xadrez
"""
import cv2
import numpy as np
import argparse
import os
import platform
from modules.board_processing import process_board_image, visualize_board_and_pieces

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
    # Adicionar opção para usar matplotlib ao invés de OpenCV para visualização
    parser.add_argument('--use-matplotlib', action='store_true',
                        help='Usar matplotlib para visualização (recomendado para Linux)')
    
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
    
    # Salvar imagens se solicitado
    if args.save_all:
        base_filename = os.path.basename(image_path).split('.')[0]
        cv2.imwrite(f"{args.output_dir}/{base_filename}_board_detection.jpg", board_visualization)
    
    # Detectar automaticamente Linux ou usar opção explícita
    is_linux = platform.system() == 'Linux'
    use_matplotlib = args.use_matplotlib or (is_linux and not args.use_matplotlib)
    
    if use_matplotlib:
        print("Usando matplotlib para visualização...")
        try:
            show_with_matplotlib(board_viz_resized)
            # Salvar automaticamente ao usar matplotlib
            output_filename = f"chess_detection_{os.path.basename(image_path)}"
            cv2.imwrite(output_filename, board_viz_resized)
            print(f"✅ Resultado salvo como {output_filename}")
        except ImportError:
            print("❌ Matplotlib não encontrado. Instale com: pip install matplotlib")
            print("Tentando exibir com OpenCV...")
            # Fallback para OpenCV
            use_matplotlib = False
    
    if not use_matplotlib:
        # Configurações específicas para Linux
        if is_linux:
            # Definir propriedades da janela para GTK (Linux)
            cv2.namedWindow("Detecção de Tabuleiro e Peças", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_EXPANDED)
            # Garantir que a janela fique em primeiro plano
            cv2.setWindowProperty("Detecção de Tabuleiro e Peças", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.setWindowProperty("Detecção de Tabuleiro e Peças", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        
        # Mostrar as visualizações
        cv2.imshow("Detecção de Tabuleiro e Peças", board_viz_resized)
        
        # No Linux, forçar atualização da janela
        if is_linux:
            cv2.waitKey(1)  # Pequeno delay para garantir que a janela seja renderizada
        
        print("Pressione qualquer tecla para fechar a visualização...")
        print("Pressione 's' para salvar a imagem.")
        
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
