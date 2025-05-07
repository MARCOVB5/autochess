"""
Módulo para detecção e identificação de peças de xadrez
"""
import cv2
import numpy as np
import os
from .piece_analysis import identify_piece_color, identify_piece_type_template_matching, enhanceSymbols

def detectChessPieces(img, pieces_mask, contours=None, templates=None):
    """
    Detecta peças de xadrez e suas cores na imagem.
    
    Args:
        img: Imagem original
        pieces_mask: Máscara com as peças detectadas
        contours: Lista de contornos de peças pré-detectadas (opcional)
        templates: Dicionário de templates de referência (opcional)
    
    Returns:
        result_img: Imagem com as peças identificadas
        symbols_only: Visualização apenas dos símbolos
    """
    # Create a copy of the original image for drawing
    result_img = img.copy()
    # Create an all-black background for symbols-only visualization
    symbols_only = np.zeros_like(img)
    
    # Statistics counters for pieces
    white_pieces = 0
    black_pieces = 0
    piece_types = {'King': 0, 'Queen': 0, 'Tower': 0, 'Pawn': 0, 'Unknown': 0}
    
    # Find contours in the mask if not provided
    if contours is None:
        contours, _ = cv2.findContours(pieces_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
    
    # Process each piece
    for i, cnt in enumerate(contours):
        # Get center and radius for the circular piece
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center = (int(x), int(y))
        radius = int(radius)
        
        # Get bounding rectangle (for ROI extraction)
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Ensure valid region
        if (x > 0 and y > 0 and x+w < img.shape[1] and y+h < img.shape[0]):
            # Get the region of interest (the chess piece)
            roi = img[y:y+h, x:x+w]
            
            # Skip if ROI is too small
            if roi.shape[0] < 20 or roi.shape[1] < 20:
                continue
            
            # Create a mask for the circular region only
            piece_circle_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(piece_circle_mask, (w//2, h//2), min(w, h)//2, 255, -1)
            
            # Identificar a cor da peça usando o método melhorado
            piece_color, text_color, symbol_color, avg_value, debug_info = identify_piece_color(roi, piece_circle_mask)
            
            # Identificar o tipo da peça
            piece_type, type_confidence = identify_piece_type_template_matching(roi, piece_color, piece_circle_mask, templates)
            
            # Incrementar o contador para este tipo de peça
            piece_types[piece_type] += 1
            
            # Atualizar contadores de cores
            if piece_color == "White":
                white_pieces += 1
            elif piece_color == "Black":
                black_pieces += 1
            
            # Enhance the symbols on the piece based on its color
            enhanced_roi = enhanceSymbols(roi, piece_color)
            
            # Create a mask for the piece based on its contour
            piece_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
            cv2.drawContours(piece_mask, [cnt], -1, 255, -1)
            
            # Place the enhanced ROI into the result image
            if enhanced_roi.shape[0] > 0 and enhanced_roi.shape[1] > 0:
                # Create a colored version of the enhanced ROI
                color_mask = np.zeros_like(roi)
                
                # Highlight the detected symbols with color
                color_mask[enhanced_roi > 50] = symbol_color
                
                # Create highlight mask with more visibility
                highlight_mask = np.zeros_like(roi)
                highlight_mask[enhanced_roi > 50] = [255, 255, 255]
                
                # Apply the highlight mask with higher contrast
                result_roi = result_img[y:y+h, x:x+w]
                result_roi = cv2.addWeighted(result_roi, 0.7, highlight_mask, 0.7, 0)
                
                # Then apply the colored symbols
                result_roi = cv2.addWeighted(result_roi, 0.7, color_mask, 0.9, 0)
                
                # Update the result image
                result_img[y:y+h, x:x+w] = result_roi
                
                # Create a visualization for the symbols-only image
                cv2.circle(symbols_only, center, radius+5, (50, 50, 50), -1)  # Dark circle background
                symbols_roi = symbols_only[y:y+h, x:x+w]
                symbol_highlight = np.zeros_like(roi)
                
                # Use bright colors for the symbols based on piece color
                if piece_color == "Black":
                    symbol_highlight[enhanced_roi > 50] = [255, 0, 0]  # Blue for black pieces
                else:
                    symbol_highlight[enhanced_roi > 50] = [0, 255, 255]  # Yellow for white pieces
                    
                # Apply to the symbols-only visualization
                symbols_roi = cv2.addWeighted(symbols_roi, 0.1, symbol_highlight, 0.9, 0)
                symbols_only[y:y+h, x:x+w] = symbols_roi
            
            # Label the piece with more information
            brightness_text = f"{int(avg_value)}"
            dark_pct = debug_info['dark_percentage'] * 100 if 'dark_percentage' in debug_info else 0
            
            # Adicionar rótulo com ID, cor e tipo
            label = f"#{i+1} {piece_color} {piece_type}"
            cv2.putText(result_img, label, (x, y-10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
            cv2.putText(result_img, f"V:{brightness_text} D:{int(dark_pct)}%", (x, y+15), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
    
    # Add legend to the image
    legend_y = 30
    # Black piece legend with red symbol
    cv2.putText(result_img, "Black piece:", (10, legend_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(result_img, (120, legend_y-5), 10, (0, 0, 255), -1)
    
    # White piece legend with blue symbol
    cv2.putText(result_img, "White piece:", (10, legend_y+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.circle(result_img, (120, legend_y+25), 10, (255, 0, 0), -1)
    
    # Add stats text - color counts
    cv2.putText(result_img, f"White pieces: {white_pieces}", (10, legend_y+60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(result_img, f"Black pieces: {black_pieces}", (10, legend_y+80), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Add stats text - piece types
    piece_type_y = legend_y + 110
    for i, (type_name, count) in enumerate(piece_types.items()):
        if count > 0:  # Só mostrar tipos que foram detectados
            cv2.putText(result_img, f"{type_name}: {count}", (10, piece_type_y + i*20), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Add legend to symbols_only
    cv2.putText(symbols_only, "Black symbol (blue):", (10, legend_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(symbols_only, (160, legend_y-5), 10, (255, 0, 0), -1)
    
    cv2.putText(symbols_only, "White symbol (yellow):", (10, legend_y+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(symbols_only, (160, legend_y+25), 10, (0, 255, 255), -1)
    
    # Verificar se os contadores estão corretos
    if white_pieces + black_pieces != len(contours):
        print(f"⚠️ Atenção: Detectados {white_pieces} peças brancas e {black_pieces} peças pretas")
        print(f"   Total: {white_pieces + black_pieces} peças, mas há {len(contours)} contornos")
    
    # Exibir contagem de tipos de peças
    print("\n=== PEÇAS DETECTADAS POR TIPO ===")
    for type_name, count in piece_types.items():
        if count > 0:
            print(f"- {type_name}: {count}")
    
    return result_img, symbols_only 