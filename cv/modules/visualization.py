"""
Módulo para funções de visualização e análise visual
"""
import cv2
import numpy as np

def analyze_hsv_colors(image, rect_size=30):
    """
    Ferramenta para analisar os valores HSV de diferentes regiões na imagem.
    Permite clicar na imagem para obter os valores HSV médios em uma área retangular.
    """
    # Redimensionar a imagem original para 60% do tamanho para análise
    scale_factor = 0.6
    display_h, display_w = int(image.shape[0] * scale_factor), int(image.shape[1] * scale_factor)
    display_image = cv2.resize(image, (display_w, display_h))
    
    img_copy = display_image.copy()
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)  # Original HSV para precisão
    hsv_display = cv2.cvtColor(display_image, cv2.COLOR_BGR2HSV)  # HSV da imagem redimensionada
    
    # Variável global para armazenar o estado do clique
    points = []
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Converter coordenadas da imagem redimensionada para a original
            orig_x = int(x / scale_factor)
            orig_y = int(y / scale_factor)
            
            # Calcular as coordenadas do retângulo na imagem original
            x1_orig = max(0, orig_x - rect_size // 2)
            y1_orig = max(0, orig_y - rect_size // 2)
            x2_orig = min(image.shape[1], orig_x + rect_size // 2)
            y2_orig = min(image.shape[0], orig_y + rect_size // 2)
            
            # Calcular as coordenadas equivalentes na imagem redimensionada
            x1 = max(0, x - int(rect_size * scale_factor) // 2)
            y1 = max(0, y - int(rect_size * scale_factor) // 2)
            x2 = min(display_w, x + int(rect_size * scale_factor) // 2)
            y2 = min(display_h, y + int(rect_size * scale_factor) // 2)
            
            # Extrair a região de interesse no espaço HSV da imagem original
            roi_hsv = hsv_image[y1_orig:y2_orig, x1_orig:x2_orig]
            
            # Calcular os valores HSV médios
            avg_hsv = cv2.mean(roi_hsv)[:3]
            
            # Desenhar o retângulo na imagem redimensionada
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Exibir os valores HSV médios
            text = f"HSV: {int(avg_hsv[0])},{int(avg_hsv[1])},{int(avg_hsv[2])}"
            cv2.putText(img_copy, text, (x2 + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Adicionar informações à lista de pontos (coordenadas originais)
            points.append((orig_x, orig_y, avg_hsv))
            
            # Atualizar a exibição
            cv2.imshow("HSV Color Analyzer", img_copy)
            
            # Imprimir informações no console
            print(f"Região em ({orig_x}, {orig_y}): H={int(avg_hsv[0])}, S={int(avg_hsv[1])}, V={int(avg_hsv[2])}")
    
    # Configurar a janela e o callback do mouse
    cv2.namedWindow("HSV Color Analyzer")
    cv2.setMouseCallback("HSV Color Analyzer", mouse_callback)
    
    # Exibir instruções
    print("\n=== ANALISADOR DE CORES HSV ===")
    print("Clique em diferentes regiões da imagem para analisar os valores HSV.")
    print("Pressione 'q' para sair, 'r' para reiniciar, 's' para salvar.")
    
    # Exibir a imagem inicial
    cv2.imshow("HSV Color Analyzer", img_copy)
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            # Sair
            break
        elif key == ord('r'):
            # Reiniciar (limpar todos os pontos)
            img_copy = display_image.copy()
            points = []
            cv2.imshow("HSV Color Analyzer", img_copy)
        elif key == ord('s'):
            # Salvar a imagem com as anotações
            # Recriar as anotações na imagem original
            img_original_copy = image.copy()
            for p in points:
                orig_x, orig_y = p[0], p[1]
                # Calcular coordenadas do retângulo na imagem original
                x1 = max(0, orig_x - rect_size // 2)
                y1 = max(0, orig_y - rect_size // 2)
                x2 = min(image.shape[1], orig_x + rect_size // 2)
                y2 = min(image.shape[0], orig_y + rect_size // 2)
                # Desenhar retângulo
                cv2.rectangle(img_original_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Adicionar texto
                avg_hsv = p[2]
                text = f"HSV: {int(avg_hsv[0])},{int(avg_hsv[1])},{int(avg_hsv[2])}"
                cv2.putText(img_original_copy, text, (x2 + 5, orig_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            cv2.imwrite("hsv_analysis.jpg", img_original_copy)
            print("✅ Análise HSV salva como hsv_analysis.jpg")
            
            # Salvar os valores HSV em um arquivo de texto
            with open("hsv_values.txt", "w") as f:
                f.write("x,y,H,S,V\n")
                for p in points:
                    f.write(f"{p[0]},{p[1]},{int(p[2][0])},{int(p[2][1])},{int(p[2][2])}\n")
            print("✅ Valores HSV salvos em hsv_values.txt")
    
    cv2.destroyWindow("HSV Color Analyzer")
    return points

def visualize_detection(img, pieces_mask):
    """
    Cria uma visualização detalhada das peças detectadas.
    """
    # Criar uma cópia da imagem original para visualização
    visualization = img.copy()
    
    # Encontrar contornos na máscara das peças
    contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar contornos por área para eliminar ruído
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:  # Filtrar por área mínima
            valid_contours.append(cnt)
    
    # Desenhar contornos das peças com numeração
    for i, cnt in enumerate(valid_contours):
        # Obter área do contorno
        area = cv2.contourArea(cnt)
        # Obter centro e raio da peça
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center = (int(x), int(y))
        radius = int(radius)
        
        # Desenhar círculo em volta da peça
        cv2.circle(visualization, center, radius, (0, 255, 0), 2)
        
        # Adicionar número de identificação
        cv2.putText(visualization, f"#{i+1}", (center[0]-10, center[1]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    return visualization, valid_contours 