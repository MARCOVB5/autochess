"""
Exemplo de uso do detector de xadrez como módulo importado
"""
import main as cd

# Caminho para a imagem do tabuleiro
image_path = "assets/storage/testing-chessboards/WIN_20250506_19_37_41_Pro.jpg"

# Detectar posição sem visualização
result = cd.detect_chess_position(image_path)

for i in range(0, 4):
    for j in range(0, 4):
        print(result["matriz"][i][j], end=" ")
    print("")
