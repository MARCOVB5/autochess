import cv.main as cd

image_path = "assets/current_board.jpg"

result = cd.detect_chess_position(image_path)

for i in range(4):
    for j in range(4):
        print(result["matriz"][i][j], end=" ")
    print("")
