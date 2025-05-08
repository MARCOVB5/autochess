"""
Módulo para análise de peças de xadrez e suas características
"""
import cv2
import numpy as np
import os

def identify_piece_color(roi, piece_mask):
    """
    Identifica a cor da peça com base nas estatísticas aprendidas das peças de referência.
    Utiliza características mais precisas extraídas das imagens de peças individuais.
    CORREÇÃO: As cores foram invertidas, corrigindo a classificação.
    """
    # Valores de referência para cada cor de peça (BLACK/WHITE)
    # Valores ajustados baseados nas imagens de peças de referência
    WHITE_REFERENCE_V = 180  # Peças brancas são geralmente muito claras
    BLACK_REFERENCE_V = 70   # Peças pretas são geralmente bem escuras
    
    # Obter apenas os pixels da peça usando a máscara
    masked_roi = cv2.bitwise_and(roi, roi, mask=piece_mask)
    
    # Converter para HSV para análise de cor
    hsv_roi = cv2.cvtColor(masked_roi, cv2.COLOR_BGR2HSV)
    
    # Obter apenas os pixels válidos (não pretos da máscara)
    valid_pixels = hsv_roi[piece_mask > 0]
    
    if len(valid_pixels) > 0:
        # Calcular valor médio (brilho)
        avg_value = np.mean(valid_pixels[:, 2])
        
        # Calcular percentis para análise mais robusta
        val_25th = np.percentile(valid_pixels[:, 2], 25)  # Quartil inferior
        val_75th = np.percentile(valid_pixels[:, 2], 75)  # Quartil superior
        
        # Calcular histograma para análise de distribuição
        hist = np.histogram(valid_pixels[:, 2], bins=8, range=(0, 256))[0]
        # Calcular porcentagem de pixels escuros (< 100)
        dark_percentage = np.sum(valid_pixels[:, 2] < 100) / len(valid_pixels)
        
        # CORREÇÃO: Invertendo a lógica de classificação de cores
        # Lógica para determinar a cor da peça usando vários critérios
        if avg_value > 160 or val_25th > 140:
            # Peça muito clara - com certeza é PRETA (inversão)
            piece_color = "Black"
            text_color = (255, 255, 255)  # Texto branco
            symbol_color = [0, 0, 255]  # Vermelho
        elif avg_value < 80 or val_75th < 100:
            # Peça muito escura - com certeza é BRANCA (inversão)
            piece_color = "White"
            text_color = (0, 0, 0)  # Texto preto
            symbol_color = [255, 0, 0]  # Azul
        elif dark_percentage < 0.3 and avg_value > 120:
            # Poucos pixels escuros e média clara - provavelmente PRETA (inversão)
            piece_color = "Black"
            text_color = (255, 255, 255)  # Texto branco
            symbol_color = [0, 0, 255]  # Vermelho
        elif dark_percentage > 0.7 and avg_value < 100:
            # Muitos pixels escuros e média escura - provavelmente BRANCA (inversão)
            piece_color = "White"
            text_color = (0, 0, 0)  # Texto preto
            symbol_color = [255, 0, 0]  # Azul
        else:
            # Caso ambíguo - usar a média como critério final (invertido)
            if avg_value > (WHITE_REFERENCE_V + BLACK_REFERENCE_V) / 2:
                piece_color = "Black"
                text_color = (255, 255, 255)  # Texto branco
                symbol_color = [0, 0, 255]  # Vermelho
            else:
                piece_color = "White"
                text_color = (0, 0, 0)  # Texto preto
                symbol_color = [255, 0, 0]  # Azul
            
        # Incluir informações adicionais para depuração
        debug_info = {
            'avg_value': avg_value,
            'val_25th': val_25th,
            'val_75th': val_75th,
            'dark_percentage': dark_percentage
        }
        
        return piece_color, text_color, symbol_color, avg_value, debug_info
    else:
        # Caso não haja pixels válidos
        return "Unknown", (255, 255, 255), [0, 255, 0], 0, {}


def load_piece_templates():
    """
    Carrega as imagens de referência dos símbolos das peças do diretório assets
    e extrai características para comparação.
    
    Returns:
        Um dicionário de templates e características para cada tipo de peça
    """
    assets_dir = "assets"
    templates = {}
    
    # Verificar se o diretório existe
    if not os.path.exists(assets_dir):
        print(f"⚠️ Diretório de assets não encontrado: {assets_dir}")
        print(f"   Usando classificação baseada em geometria.")
        return None
    
    # Mapear nomes de arquivos para tipos de peças
    type_mapping = {
        "king": "King",
        "queen": "Queen",
        "rook": "Rook",
        "pawn": "Pawn"
    }
    
    # Carregar cada imagem de referência
    try:
        for color in ["white", "black"]:
            templates[color] = {}
            
            for piece_type in type_mapping.keys():
                filename = f"{color}-{piece_type}.png"
                filepath = os.path.join(assets_dir, filename)
                
                if os.path.exists(filepath):
                    # Carregar a imagem
                    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        continue
                    
                    # Limiarizar para garantir preto e branco puro
                    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
                    
                    # CORREÇÃO: Corrigir a forma como findContours é chamado
                    if color == "white":
                        # Invertemos primeiro a imagem para branco em fundo preto
                        binary_inv = cv2.bitwise_not(binary)
                        contours, _ = cv2.findContours(binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    else:
                        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Extrair características se encontrar contornos
                    if contours:
                        main_contour = max(contours, key=cv2.contourArea)
                        area = cv2.contourArea(main_contour)
                        
                        if area > 0:
                            # Calcular características
                            perimeter = cv2.arcLength(main_contour, True)
                            x, y, w, h = cv2.boundingRect(main_contour)
                            aspect_ratio = float(w) / h if h > 0 else 0
                            extent = float(area) / (w * h) if (w * h) > 0 else 0
                            
                            # Invólucro convexo e solidez
                            hull = cv2.convexHull(main_contour)
                            hull_area = cv2.contourArea(hull)
                            solidity = float(area) / hull_area if hull_area > 0 else 0
                            
                            # Momento de Hu para análise de forma invariante
                            moments = cv2.moments(main_contour)
                            hu_moments = cv2.HuMoments(moments)
                            
                            # Armazenar características e imagem de referência
                            mapped_type = type_mapping[piece_type]
                            templates[color][mapped_type] = {
                                'binary': binary,
                                'contour': main_contour,
                                'area': area,
                                'perimeter': perimeter,
                                'aspect_ratio': aspect_ratio,
                                'extent': extent,
                                'solidity': solidity,
                                'hu_moments': hu_moments,
                                'w': w,
                                'h': h,
                                'original_image': img  # Guardar a imagem original para matching direto
                            }
                            
                            print(f"✅ Carregado template para {color} {mapped_type}")
                            print(f"   Proporção: {aspect_ratio:.2f}, Solidez: {solidity:.2f}")
        
        # Verificar se carregou todos os templates
        if templates['white'] and templates['black'] and len(templates['white']) > 0 and len(templates['black']) > 0:
            print(f"✅ Carregados {len(templates['white'])} templates brancos e {len(templates['black'])} templates pretos")
            return templates
        else:
            return None
    except Exception as e:
        print(f"⚠️ Erro ao carregar templates: {str(e)}")
        return None
