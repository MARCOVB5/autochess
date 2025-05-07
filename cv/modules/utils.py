"""
Módulo com funções utilitárias para o projeto
"""
import cv2
import numpy as np
import os

def analyze_reference_pieces():
    """
    Analisa as imagens de referência das peças no diretório pieces-pictures
    para aprender as características de cada tipo de peça.
    """
    pieces_dir = "pieces-pictures"
    reference_pieces = {}
    
    # Verificar se o diretório existe
    if not os.path.exists(pieces_dir):
        print(f"❌ Diretório de peças não encontrado: {pieces_dir}")
        return None
    
    # Listar arquivos no diretório
    files = os.listdir(pieces_dir)
    
    for file in files:
        # Apenas arquivos de imagem
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            # Extrair informações do nome do arquivo
            parts = file.split('_')
            if len(parts) >= 3:
                # Obter cor da peça (BLACK/WHITE)
                piece_color = parts[0]
                
                # Carregar a imagem
                img_path = os.path.join(pieces_dir, file)
                img = cv2.imread(img_path)
                
                if img is None:
                    print(f"❌ Não foi possível carregar: {img_path}")
                    continue
                
                # Converter para HSV para análise
                hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                # Encontrar a peça na imagem (assumindo que é o objeto principal)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                
                # Encontrar contornos
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Obter o maior contorno (provavelmente a peça)
                if contours:
                    cnt = max(contours, key=cv2.contourArea)
                    
                    # Criar máscara para a peça
                    mask = np.zeros_like(gray)
                    cv2.drawContours(mask, [cnt], 0, 255, -1)
                    
                    # Extrair região da peça
                    piece_region = cv2.bitwise_and(img, img, mask=mask)
                    
                    # Coletar características
                    hsv_region = cv2.cvtColor(piece_region, cv2.COLOR_BGR2HSV)
                    masked_pixels = hsv_region[mask > 0]
                    
                    if len(masked_pixels) > 0:
                        # Calcular estatísticas da peça
                        avg_hue = np.mean(masked_pixels[:, 0])
                        avg_sat = np.mean(masked_pixels[:, 1])
                        avg_val = np.mean(masked_pixels[:, 2])
                        
                        # Salvar características
                        if piece_color not in reference_pieces:
                            reference_pieces[piece_color] = []
                        
                        reference_pieces[piece_color].append({
                            'file': file,
                            'avg_hue': avg_hue,
                            'avg_sat': avg_sat,
                            'avg_val': avg_val,
                            'contour': cnt
                        })
                        
                        print(f"✅ Analisada peça {piece_color} de {file}: H={avg_hue:.1f}, S={avg_sat:.1f}, V={avg_val:.1f}")
    
    # Calcular características médias para cada cor
    color_stats = {}
    for color, pieces in reference_pieces.items():
        avg_hue = np.mean([p['avg_hue'] for p in pieces])
        avg_sat = np.mean([p['avg_sat'] for p in pieces])
        avg_val = np.mean([p['avg_val'] for p in pieces])
        
        color_stats[color] = {
            'avg_hue': avg_hue,
            'avg_sat': avg_sat,
            'avg_val': avg_val,
            'count': len(pieces)
        }
        
        print(f"\n✅ Estatísticas para peças {color}:")
        print(f"  - Quantidade: {len(pieces)}")
        print(f"  - H média: {avg_hue:.1f}")
        print(f"  - S média: {avg_sat:.1f}")
        print(f"  - V média: {avg_val:.1f}")
    
    return color_stats 