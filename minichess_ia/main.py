import pygame
import sys
import numpy as np
import pickle
import os
import time
from minichess import MiniChess
from ai_player import MiniChessAI

# Inicialização do Pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (247, 247, 105)
GREEN = (0, 200, 0)

# Configurações da tela
WIDTH, HEIGHT = 600, 600
BOARD_SIZE = 400
SQUARE_SIZE = BOARD_SIZE // 4
PIECE_SIZE = SQUARE_SIZE - 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini Chess 4x4 com IA de Aprendizado")

# Configurações de animação
ANIMATION_SPEED = 10  # Quanto maior, mais rápida a animação
ANIMATION_FRAMES = 10  # Número de frames para animar o movimento

# Carregar e redimensionar imagens das peças
piece_images = {}
# Mapeamento de peças para nomes de arquivos
piece_filenames = {
    'p': 'black-pawn.png',
    'r': 'black-rook.png',
    'q': 'black-queen.png',
    'k': 'black-king.png',
    'P': 'white-pawn.png',
    'R': 'white-rook.png',
    'Q': 'white-queen.png',
    'K': 'white-king.png'
}

def load_piece_images():
    for piece, filename in piece_filenames.items():
        try:
            img = pygame.image.load(f"assets/{filename}")
            piece_images[piece] = pygame.transform.scale(img, (PIECE_SIZE, PIECE_SIZE))
        except FileNotFoundError:
            print(f"Erro: Imagem para a peça {piece} ({filename}) não encontrada")
            continue

def draw_board(selected_square=None, valid_moves=None, king_in_check=None):
    # Desenha o tabuleiro
    for row in range(4):
        for col in range(4):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            
            # Destaca a casa selecionada
            if selected_square and selected_square[0] == row and selected_square[1] == col:
                color = HIGHLIGHT
            # Destaca movimentos válidos
            elif valid_moves and (row, col) in valid_moves:
                pygame.draw.rect(screen, color, (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                                               row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                                               SQUARE_SIZE, SQUARE_SIZE))
                # Círculo para indicar movimento válido
                pygame.draw.circle(screen, GREEN, 
                                 (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + SQUARE_SIZE // 2, 
                                  row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + SQUARE_SIZE // 2), 
                                 10)
                continue
            # Destaca o rei em xeque
            elif king_in_check and king_in_check[0] == row and king_in_check[1] == col:
                # Fundo vermelho para o rei em xeque
                color = (255, 100, 100)  # Vermelho claro
                
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                                           row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                                           SQUARE_SIZE, SQUARE_SIZE))

def draw_pieces(board):
    """
    Desenha todas as peças no tabuleiro
    O parâmetro board deve ser a matriz de peças (não o objeto MiniChess)
    """
    for row in range(4):
        for col in range(4):
            piece = board[row][col]
            if piece != '.':
                if piece in piece_images:  # Verifica se a imagem existe
                    x = col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    y = row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    screen.blit(piece_images[piece], (x, y))
                else:
                    print(f"Imagem para peça {piece} não carregada")

def animate_move(chess_game, from_pos, to_pos):
    """Anima o movimento de uma peça de from_pos para to_pos"""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Obtém a peça que foi movida (já está na posição de destino)
    piece = chess_game.board[to_row][to_col]
    
    # Configuração da animação
    clock = pygame.time.Clock()
    
    # Verifica se há um rei em xeque após o movimento
    king_in_check = None
    if chess_game.is_check('w'):
        king_in_check = chess_game.king_positions['w']
    elif chess_game.is_check('b'):
        king_in_check = chess_game.king_positions['b']
    
    # Animação
    for frame in range(ANIMATION_FRAMES + 1):
        progress = frame / ANIMATION_FRAMES
        
        # Calcular a posição de interpolação
        start_x = from_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        start_y = from_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_x = to_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_y = to_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # Desenha o tabuleiro e as peças
        screen.fill(WHITE)
        draw_board(None, None, king_in_check)
        
        # Desenha todas as peças, exceto a que está sendo animada
        for r in range(4):
            for c in range(4):
                p = chess_game.board[r][c]
                if p != '.' and not (r == to_row and c == to_col):  # Não desenhar a peça que está sendo animada
                    if p in piece_images:
                        x = c * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        y = r * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        screen.blit(piece_images[p], (x, y))
        
        # Desenha a peça animada
        if piece in piece_images:
            screen.blit(piece_images[piece], (current_x, current_y))
        
        # Desenha os elementos da interface
        draw_reset_button()
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        # Exibe mensagem de xeque se aplicável
        if king_in_check:
            player_in_check = 'branco' if chess_game.is_check('w') else 'preto'
            font = pygame.font.SysFont(None, 36)
            text = font.render(f"XEQUE ao rei {player_in_check}!", True, (255, 0, 0))
            screen.blit(text, (20, HEIGHT - 120))
        
        pygame.display.flip()
        clock.tick(60)

def draw_reset_button():
    button_rect = pygame.Rect(WIDTH - 180, HEIGHT - 60, 150, 40)
    pygame.draw.rect(screen, (100, 100, 255), button_rect)
    pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
    
    font = pygame.font.SysFont(None, 28)
    text = font.render("Resetar IA", True, (0, 0, 0))
    screen.blit(text, (WIDTH - 160, HEIGHT - 50))
    
    return button_rect

def show_game_over(message):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    font = pygame.font.SysFont(None, 64)
    text = font.render(message, True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(text, text_rect)
    
    font_small = pygame.font.SysFont(None, 32)
    restart_text = font_small.render("Clique para jogar novamente", True, (255, 255, 255))
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(restart_text, restart_rect)
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False

def display_ai_strength(ai_player):
    font = pygame.font.SysFont(None, 24)
    text = font.render(f"Força da IA: {ai_player.get_strength_description()}", True, (0, 0, 0))
    screen.blit(text, (20, HEIGHT - 50))

def display_current_player(current_player):
    player_text = "Sua vez (brancas)" if current_player == 'w' else "Vez da IA (pretas)"
    font = pygame.font.SysFont(None, 24)
    text = font.render(player_text, True, (0, 0, 0))
    screen.blit(text, (20, HEIGHT - 80))

def screen_coords_to_board(x, y):
    board_x = (WIDTH - BOARD_SIZE) // 2
    board_y = (HEIGHT - BOARD_SIZE) // 2
    
    if (x < board_x or x >= board_x + BOARD_SIZE or 
        y < board_y or y >= board_y + BOARD_SIZE):
        return None
    
    col = (x - board_x) // SQUARE_SIZE
    row = (y - board_y) // SQUARE_SIZE
    
    return (row, col)

def main():
    # Criar diretório de assets se não existir
    os.makedirs("assets", exist_ok=True)
    
    # Verificar e criar diretório para modelos da IA
    os.makedirs("models", exist_ok=True)
    
    # Inicializar o jogo
    chess_game = MiniChess()
    global ai_player
    ai_player = MiniChessAI()
    
    # Carregar imagens das peças
    load_piece_images()
    
    selected_square = None
    valid_moves = []
    game_over = False
    reset_button = None
    
    # Loop principal
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Salvar o modelo da IA antes de sair
                ai_player.save_model()
                pygame.quit()
                sys.exit()
                
            if not game_over and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Botão esquerdo do mouse
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Verificar se o botão de reset foi clicado
                    if reset_button and reset_button.collidepoint(mouse_pos):
                        ai_player.reset_model()
                        print("IA resetada!")
                        continue
                    
                    # Se é a vez do jogador (peças brancas)
                    if chess_game.current_player == 'w':
                        clicked_square = screen_coords_to_board(*mouse_pos)
                        
                        if clicked_square:
                            row, col = clicked_square
                            
                            # Se já tiver uma peça selecionada
                            if selected_square:
                                # Tentar mover a peça
                                move = (selected_square, clicked_square)
                                
                                # Verificar se o destino é um movimento válido
                                if clicked_square in valid_moves:
                                    # Salvar a posição inicial para a animação
                                    from_pos = selected_square
                                    to_pos = clicked_square
                                    
                                    # Executar o movimento
                                    success = chess_game.make_move(move)
                                    if success:
                                        print(f"Movimento de {selected_square} para {clicked_square} realizado")
                                        # Animar o movimento
                                        animate_move(chess_game, from_pos, to_pos)
                                        # Verifica e imprime o tabuleiro após o movimento
                                        chess_game.print_board()
                                    else:
                                        print(f"Movimento inválido: {selected_square} -> {clicked_square}")
                                    
                                    selected_square = None
                                    valid_moves = []
                                    
                                    # Verificar se o jogo acabou após o movimento do jogador
                                    if chess_game.is_king_captured():
                                        game_over = True
                                        capturou = chess_game.is_king_captured()
                                        if capturou == 'w':
                                            ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                                            show_game_over("Você venceu!")
                                        else:
                                            ai_player.learn(chess_game, 0)  # IA aprende com a vitória
                                            show_game_over("IA venceu!")
                                        
                                        # Reiniciar o jogo
                                        chess_game = MiniChess()
                                        game_over = False
                                    elif chess_game.is_game_over():
                                        game_over = True
                                        
                                        if chess_game.is_checkmate():
                                            ai_player.learn(chess_game, 0)  # IA aprende com a derrota
                                            show_game_over("Você venceu!")
                                        else:
                                            ai_player.learn(chess_game, 0.5)  # Empate é neutro
                                            show_game_over("Empate!")
                                        
                                        # Reiniciar o jogo
                                        chess_game = MiniChess()
                                        game_over = False
                                    else:
                                        # Vez da IA
                                        print("Vez da IA...")
                                        ai_move = ai_player.get_move(chess_game)
                                        
                                        if ai_move:
                                            origin, dest = ai_move
                                            print(f"IA move: {origin} -> {dest}")
                                            
                                            # Salvar para animação
                                            ai_from_pos = origin
                                            ai_to_pos = dest
                                            
                                            success = chess_game.make_move(ai_move)
                                            
                                            # Animar o movimento da IA
                                            if success:
                                                print(f"IA moveu de {origin} para {dest}")
                                                animate_move(chess_game, ai_from_pos, ai_to_pos)
                                                chess_game.print_board()
                                            
                                            # Verificar se o jogo acabou após o movimento da IA
                                            if chess_game.is_king_captured():
                                                game_over = True
                                                capturou = chess_game.is_king_captured()
                                                if capturou == 'w':
                                                    ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                                                    show_game_over("Você venceu!")
                                                else:
                                                    ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                                                    show_game_over("IA venceu!")
                                                
                                                # Reiniciar o jogo
                                                chess_game = MiniChess()
                                                game_over = False
                                            elif chess_game.is_game_over():
                                                game_over = True
                                                
                                                if chess_game.is_checkmate():
                                                    # IA ganhou
                                                    ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                                                    show_game_over("IA venceu!")
                                                else:
                                                    # Empate
                                                    ai_player.learn(chess_game, 0.5)  # Empate é neutro
                                                    show_game_over("Empate!")
                                                
                                                # Reiniciar o jogo
                                                chess_game = MiniChess()
                                                game_over = False
                                        else:
                                            if chess_game.is_check('b'):
                                                ai_player.learn(chess_game, 0)  # IA aprende com a derrota
                                                show_game_over("Você venceu!")
                                                chess_game = MiniChess()
                                                game_over = False
                                else:
                                    # Cancelar seleção ou selecionar nova peça
                                    piece = chess_game.board[row][col]
                                    if piece != '.' and chess_game.get_piece_color(piece) == 'w':
                                        selected_square = (row, col)
                                        valid_moves = chess_game.get_valid_moves(selected_square)
                                        print(f"Nova peça {piece} selecionada em {selected_square}. Movimentos válidos: {valid_moves}")
                                    else:
                                        selected_square = None
                                        valid_moves = []
                            else:
                                # Selecionar peça
                                piece = chess_game.board[row][col]
                                if piece != '.' and chess_game.get_piece_color(piece) == 'w':
                                    selected_square = (row, col)
                                    valid_moves = chess_game.get_valid_moves(selected_square)
                                    print(f"Peça {piece} selecionada em {selected_square}. Movimentos válidos: {valid_moves}")
                
        # Renderização
        screen.fill(WHITE)
        
        # Verifica se há um rei em xeque
        king_in_check = None
        if chess_game.is_check('w'):
            king_in_check = chess_game.king_positions['w']
        elif chess_game.is_check('b'):
            king_in_check = chess_game.king_positions['b']
        
        # Desenha o tabuleiro com destaque para o rei em xeque, se houver
        draw_board(selected_square, valid_moves, king_in_check)
        
        # Desenha as peças
        draw_pieces(chess_game.board)
        
        # Desenha o botão de reset
        reset_button = draw_reset_button()
        
        # Mostra informações da IA
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        # Exibe mensagem de xeque se aplicável
        if king_in_check and not game_over:
            player_in_check = 'Brancas' if chess_game.is_check('w') else 'Pretas'
            font = pygame.font.SysFont(None, 36)
            text = font.render(f"XEQUE: {player_in_check} em perigo!", True, (255, 0, 0))
            screen.blit(text, (20, HEIGHT - 120))
        
        pygame.display.flip()
        clock.tick(30)  # 30 FPS

if __name__ == "__main__":
    main() 