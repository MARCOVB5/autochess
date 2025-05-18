"""
Exemplo de uso do detector de xadrez como módulo importado
"""
import main as cd

# Caminho para a imagem do tabuleiro
image_path = "assets/storage/testing-chessboards/5.jpg"

# Detectar posição sem visualização
result = cd.detect_chess_position(image_path, visualize=True)

print(result["matriz"])
