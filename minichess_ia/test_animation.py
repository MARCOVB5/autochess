import pygame
import sys
import time
from minichess import MiniChess

# Inicialização do Pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)

# Configurações da tela
WIDTH, HEIGHT = 600, 600
BOARD_SIZE = 400
SQUARE_SIZE = BOARD_SIZE // 4
PIECE_SIZE = SQUARE_SIZE - 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Teste de Animação")

# Carregar e redimensionar imagens das peças
piece_images = {}
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

def draw_board():
    # Desenha o tabuleiro
    for row in range(4):
        for col in range(4):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                                          row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                                          SQUARE_SIZE, SQUARE_SIZE))

def draw_pieces(board):
    # Desenha as peças no tabuleiro
    for row in range(4):
        for col in range(4):
            piece = board[row][col]
            if piece != '.':
                if piece in piece_images:
                    x = col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    y = row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    screen.blit(piece_images[piece], (x, y))

def animate_move(chess_game, from_pos, to_pos, frames=10):
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Guarda a peça original antes de movê-la
    piece = chess_game.board[from_row][from_col]
    
    # Executa o movimento real (sem animação)
    chess_game.board[to_row][to_col] = piece
    chess_game.board[from_row][from_col] = '.'
    
    # Animação
    for frame in range(frames + 1):
        progress = frame / frames
        
        # Calcular posição da interpolação
        start_x = from_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        start_y = from_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_x = to_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_y = to_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # Desenha o tabuleiro
        screen.fill(WHITE)
        draw_board()
        
        # Desenha todas as peças, exceto a que está sendo animada
        for r in range(4):
            for c in range(4):
                p = chess_game.board[r][c]
                if p != '.' and not (r == to_row and c == to_col):
                    if p in piece_images:
                        x = c * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        y = r * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        screen.blit(piece_images[p], (x, y))
        
        # Desenha a peça animada
        if piece in piece_images:
            screen.blit(piece_images[piece], (current_x, current_y))
        
        pygame.display.flip()
        pygame.time.delay(30)  # 30ms de delay entre frames

def main():
    # Inicializar o jogo
    chess_game = MiniChess()
    
    # Carregar imagens das peças
    load_piece_images()
    
    # Loop principal
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Teste de animação: mover um peão branco
                    animate_move(chess_game, (2, 1), (1, 1))
                elif event.key == pygame.K_r:
                    # Reiniciar o jogo
                    chess_game = MiniChess()
        
        # Desenhar o jogo
        screen.fill(WHITE)
        draw_board()
        draw_pieces(chess_game.board)
        
        # Exibir instruções
        font = pygame.font.SysFont(None, 24)
        text = font.render("Pressione ESPAÇO para testar animação, R para reiniciar", True, BLACK)
        screen.blit(text, (40, HEIGHT - 40))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 