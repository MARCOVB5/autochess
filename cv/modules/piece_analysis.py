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

def identify_piece_type_template_matching(roi, piece_color, piece_mask, templates):
    """
    Identifica o tipo de peça usando correspondência de templates e características.
    MELHORADO: Agora testa peças em múltiplas rotações para maior robustez.
    
    Args:
        roi: Região da imagem contendo a peça
        piece_color: Cor da peça ('Black' ou 'White')
        piece_mask: Máscara da peça
        templates: Dicionário de templates de referência
    
    Returns:
        piece_type: Tipo da peça identificado
        confidence: Nível de confiança na identificação (0-1)
    """
    if templates is None:
        # Fallback para o método baseado em geometria se não tiver templates
        return identify_piece_type(roi, piece_color)
    
    # Processar a região de interesse para destacar o símbolo
    symbol = enhanceSymbols(roi, piece_color)
    
    # Encontrar contornos do símbolo
    contours, _ = cv2.findContours(symbol, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Se não encontrou contornos, retornar tipo desconhecido
    if not contours:
        return "Unknown", 0.0
    
    # Obter o maior contorno (principal parte do símbolo)
    main_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(main_contour)
    
    # Se a área for muito pequena, pode não ser um símbolo válido
    if area < 10:
        return "Unknown", 0.0
    
    # Extrair características do símbolo detectado
    perimeter = cv2.arcLength(main_contour, True)
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    extent = float(area) / (w * h) if (w * h) > 0 else 0
    
    # Calcular solidez (solidity)
    hull = cv2.convexHull(main_contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0
    
    # Calcular momentos Hu para comparação de forma
    moments = cv2.moments(main_contour)
    hu_moments = cv2.HuMoments(moments)
    
    # Converter cor do formato "Black"/"White" para "black"/"white" para corresponder ao dicionário
    color_key = piece_color.lower()
    
    # MÉTODO APRIMORADO DE TEMPLATE MATCHING UTILIZANDO MÚLTIPLAS ABORDAGENS
    
    # 1. Método de correspondência direta com template
    # Redimensionar o símbolo para um tamanho padrão para facilitar a comparação
    standard_size = (64, 64)
    resized_symbol = cv2.resize(symbol, standard_size)
    
    # MELHORIA: Criar versões rotacionadas do símbolo para testar múltiplas orientações
    # Rotacionar o símbolo em 180 graus (como mencionado pelo usuário que a câmera está invertida)
    rotated_symbol = cv2.rotate(resized_symbol, cv2.ROTATE_180)
    
    # Dicionário para armazenar pontuações de similaridade
    scores = {}
    best_match = "Unknown"
    best_score = 0.0
    best_orientation = "normal"  # Para debug
    
    # Pesos para diferentes características
    weights = {
        'template_match': 0.5,  # Correspondência direta de template (aumentado o peso)
        'aspect_ratio': 0.15,   # Proporção largura/altura
        'solidity': 0.15,       # Solidez (área/área do invólucro convexo)
        'hu_moments': 0.2       # Momentos de Hu (invariantes a escala/rotação)
    }
    
    # Penalidades específicas para evitar falsos positivos de Torre
    tower_penalty = 0.2  # Penalidade quando o candidato é Torre para evitar superidentificação
    
    # Para testes/depuração - exibir informações
    debug_info = []
    
    # Comparar com cada template disponível
    for piece_type, template in templates[color_key].items():
        # Redimensionar o template para o mesmo tamanho padrão
        if 'original_image' in template:
            template_img = template['original_image']
            resized_template = cv2.resize(template_img, standard_size)
            
            # Inverter ou não dependendo da cor (para garantir que estamos comparando símbolos semelhantes)
            if (piece_color == "Black" and np.mean(resized_template) > 127) or \
               (piece_color == "White" and np.mean(resized_template) < 127):
                resized_template = 255 - resized_template
            
            # MELHORIA: Testar DUAS orientações (normal e rotacionada 180 graus)
            # Orientação 1: Normal
            result1 = cv2.matchTemplate(resized_symbol, resized_template, cv2.TM_CCOEFF_NORMED)
            _, template_score1, _, _ = cv2.minMaxLoc(result1)
            
            # Orientação 2: Rotacionada 180 graus
            result2 = cv2.matchTemplate(rotated_symbol, resized_template, cv2.TM_CCOEFF_NORMED)
            _, template_score2, _, _ = cv2.minMaxLoc(result2)
            
            # Usar a melhor orientação
            if template_score1 > template_score2:
                template_match_score = template_score1
                used_orientation = "normal"
            else:
                template_match_score = template_score2
                used_orientation = "rotated"
            
            # Normalizar para 0-1
            template_match_score = max(0, template_match_score)
        else:
            template_match_score = 0.5  # Valor neutro se não tiver imagem original
            used_orientation = "N/A"
        
        # 2. Similaridade de proporção (aspect ratio)
        aspect_diff = 1.0 - min(abs(aspect_ratio - template['aspect_ratio']) / max(template['aspect_ratio'], 0.01), 1.0)
        
        # 3. Similaridade de solidez (solidity)
        solidity_diff = 1.0 - min(abs(solidity - template['solidity']) / max(template['solidity'], 0.01), 1.0)
        
        # 4. Similaridade de momentos Hu (invariantes à escala, rotação e translação)
        hu_diff = 0.0
        for i in range(min(len(hu_moments), len(template['hu_moments']))):
            # Usar diferença logarítmica para momentos Hu
            if hu_moments[i][0] != 0 and template['hu_moments'][i][0] != 0:
                hu_diff += abs(np.log(abs(hu_moments[i][0])) - np.log(abs(template['hu_moments'][i][0])))
        
        # Normalizar e inverter a diferença Hu para obter similaridade (0-1)
        hu_similarity = max(0.0, 1.0 - min(hu_diff / 15.0, 1.0))  # Valor 15.0 é empírico
        
        # Combinação ponderada das similaridades
        score = (weights['template_match'] * template_match_score + 
                 weights['aspect_ratio'] * aspect_diff + 
                 weights['solidity'] * solidity_diff + 
                 weights['hu_moments'] * hu_similarity)
        
        # Aumentar a confiança das peças King e Queen pois são mais distintivas
        if piece_type == "King" or piece_type == "Queen":
            score *= 1.1  # Bônus de 10%
        
        # Aplicar penalidade para Tower/Rook para evitar falsos positivos
        if piece_type == "Rook" or piece_type == "Tower":
            score -= tower_penalty
        
        # Para depuração
        debug_info.append({
            'type': piece_type,
            'template_match': template_match_score,
            'orientation': used_orientation,
            'aspect': aspect_diff,
            'solidity': solidity_diff,
            'hu': hu_similarity,
            'final_score': score
        })
        
        # Armazenar pontuação
        scores[piece_type] = score
        
        # Atualizar melhor correspondência
        if score > best_score:
            best_score = score
            best_match = piece_type
            best_orientation = used_orientation
    
    # Corrigir nomes (Rook -> Tower para manter compatibilidade)
    if best_match == "Rook":
        best_match = "Tower"
    
    # Converter pontuação para confiança (ajustar para dar valores mais realistas)
    confidence = min(1.0, max(0.0, best_score))
    
    # Se a confiança for muito baixa, usar o método de fallback
    if confidence < 0.4:
        fallback_type, fallback_conf = identify_piece_type(roi, piece_color)
        
        # Só usar o fallback se ele tiver uma confiança melhor
        if fallback_conf > confidence + 0.1:  # Adicionar margem para preferir o template matching
            return fallback_type, fallback_conf
    
    return best_match, confidence 