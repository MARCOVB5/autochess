import cv.main as cd

# Caminho para a imagem do tabuleiro
#image_path = "cv/assets/storage/testing-chessboards/21.png"
image_path = "assets/current_board.png"

# Detectar posição sem visualização
result = cd.detect_chess_position(image_path)

for i in range(4):
    for j in range(4):
        print(result["matriz"][i][j], end=" ")
    print("")
