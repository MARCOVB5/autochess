import pygame
import sys
import numpy as np
import os
from minichess import MiniChess

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
pygame.display.set_caption("Mini Chess 4x4 - Jogador vs Jogador")

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

def draw_board(selected_square=None, valid_moves=None):
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
        draw_board()
        
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
        draw_restart_button()
        display_current_player(chess_game.current_player)
        
        pygame.display.flip()
        clock.tick(60)

def draw_restart_button():
    button_rect = pygame.Rect(WIDTH - 180, HEIGHT - 60, 150, 40)
    pygame.draw.rect(screen, (100, 100, 255), button_rect)
    pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
    
    font = pygame.font.SysFont(None, 28)
    text = font.render("Nova Partida", True, (0, 0, 0))
    screen.blit(text, (WIDTH - 165, HEIGHT - 50))
    
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

def display_current_player(current_player):
    player_text = "Turno: Jogador Brancas" if current_player == 'w' else "Turno: Jogador Pretas"
    font = pygame.font.SysFont(None, 24)
    text = font.render(player_text, True, (0, 0, 0))
    screen.blit(text, (20, HEIGHT - 70))

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
    
    # Inicializar o jogo
    chess_game = MiniChess()
    
    # Carregar imagens das peças
    load_piece_images()
    
    selected_square = None
    valid_moves = []
    game_over = False
    restart_button = None
    
    # Loop principal
    clock = pygame.time.Clock()  # Para controlar o FPS
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if not game_over and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Botão esquerdo do mouse
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Verificar se o botão de restart foi clicado
                    if restart_button and restart_button.collidepoint(mouse_pos):
                        chess_game = MiniChess()
                        selected_square = None
                        valid_moves = []
                        game_over = False
                        continue
                    
                    # Converter coordenadas do mouse para coordenadas do tabuleiro
                    board_pos = screen_coords_to_board(*mouse_pos)
                    
                    if board_pos:
                        row, col = board_pos
                        # Se já tem uma peça selecionada, tenta mover para a nova posição
                        if selected_square:
                            if (row, col) in valid_moves:
                                # Realiza o movimento
                                move = (selected_square, (row, col))
                                if chess_game.make_move(move):
                                    # Anima o movimento
                                    animate_move(chess_game, selected_square, (row, col))
                                    
                                    # Verifica se o jogo terminou
                                    if chess_game.is_game_over():
                                        result = chess_game.get_result()
                                        if result == 'w':
                                            show_game_over("Brancas Venceram!")
                                        elif result == 'b':
                                            show_game_over("Pretas Venceram!")
                                        else:
                                            show_game_over("Empate!")
                                        
                                        chess_game = MiniChess()
                                        game_over = False
                            
                            # Independentemente do resultado, limpa a seleção
                            selected_square = None
                            valid_moves = []
                            
                        else:
                            # Verifica se há uma peça na posição clicada
                            if chess_game.board[row][col] != '.':
                                # Só permite selecionar peças do jogador atual
                                piece = chess_game.board[row][col]
                                if chess_game.get_piece_color(piece) == chess_game.current_player:
                                    selected_square = (row, col)
                                    valid_moves = chess_game.get_valid_moves(selected_square)
        
        # Renderização
        screen.fill(WHITE)
        
        # Desenha o tabuleiro
        draw_board(selected_square, valid_moves)
        
        # Desenha as peças
        draw_pieces(chess_game.board)
        
        # Desenha o botão de restart
        restart_button = draw_restart_button()
        
        # Mostra o jogador atual
        display_current_player(chess_game.current_player)
        
        # Verifica se está em xeque
        if not game_over and chess_game.is_check(chess_game.current_player):
            font = pygame.font.SysFont(None, 36)
            text = font.render("XEQUE!", True, (255, 0, 0))
            screen.blit(text, (20, HEIGHT - 120))
        
        pygame.display.flip()
        clock.tick(60)  # 60 FPS

if __name__ == "__main__":
    main() 