"""
Teste isolado: captura foto da webcam e roda o pipeline de visão computacional.
Uso: python test_webcam_cv.py [device]
  device: índice da câmera (padrão: 0 = webcam integrada, 1 = externa)
"""
import sys
import cv2
import cv.main as cv

device = int(sys.argv[1]) if len(sys.argv) > 1 else 0

cap = cv2.VideoCapture(device)
if not cap.isOpened():
    print(f"Webcam {device} não encontrada")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

for _ in range(5):
    cap.read()

ret, frame = cap.read()
cap.release()

if not ret:
    print("Erro ao capturar frame")
    sys.exit(1)

frame = cv2.rotate(frame, cv2.ROTATE_180)
cv2.imwrite("assets/current_board.jpg", frame)
print("Foto salva em assets/current_board.jpg")

result = cv.detect_chess_position("assets/current_board.jpg", visualize=True)
if result and result.get("matriz"):
    print("\nMatriz detectada:")
    for row in result["matriz"]:
        print(" ".join(row))
    print(f"\nPeças: {result['pieces_count']} ({result['white_pieces']}B, {result['black_pieces']}P)")
else:
    print("Falha na detecção do tabuleiro")
