import pygame
import sys
import os
import time
import random

# Importação adaptativa dependendo de como o script é executado
try:
    from .minichess import MiniChess
    from .ai_player import MiniChessAI
except ImportError:
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
RED = (255, 100, 100)

# Configurações da tela
WIDTH, HEIGHT = 600, 600
BOARD_SIZE = 400
SQUARE_SIZE = BOARD_SIZE // 4
PIECE_SIZE = SQUARE_SIZE - 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini Chess com IA Q-Learning")

# Configurações de animação
ANIMATION_SPEED = 8
ANIMATION_FRAMES = 6

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
    """Carrega as imagens das peças."""
    # Lista de possíveis caminhos para as imagens
    possible_paths = [
        "assets"
    ]
    
    assets_dir = None
    # Tenta encontrar o diretório de assets
    for path in possible_paths:
        if os.path.exists(path):
            assets_dir = path
            break
    
    if not assets_dir:
        return
    
    # Carrega as imagens das peças
    for piece, filename in piece_filenames.items():
        try:
            filepath = os.path.join(assets_dir, filename)
            
            if os.path.exists(filepath):
                img = pygame.image.load(filepath)
                piece_images[piece] = pygame.transform.scale(img, (PIECE_SIZE, PIECE_SIZE))
        except Exception:
            pass

def draw_board(selected_square=None, valid_moves=None, king_in_check=None):
    """Desenha o tabuleiro com os quadrados destacados, se houver."""
    for row in range(4):
        for col in range(4):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            
            # Destaca a casa selecionada
            if selected_square and selected_square[0] == row and selected_square[1] == col:
                color = HIGHLIGHT
            
            # Destaca o rei em xeque
            elif king_in_check and king_in_check[0] == row and king_in_check[1] == col:
                color = RED  # Vermelho para xeque
            
            # Desenha o quadrado
            pygame.draw.rect(screen, color, (
                col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                SQUARE_SIZE, SQUARE_SIZE
            ))
            
            # Destaca movimentos válidos
            if valid_moves and (row, col) in valid_moves:
                # Círculo para indicar movimento válido
                pygame.draw.circle(screen, GREEN, (
                    col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + SQUARE_SIZE // 2, 
                    row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + SQUARE_SIZE // 2
                ), 10)

def draw_pieces(board):
    """Desenha todas as peças no tabuleiro."""
    for row in range(4):
        for col in range(4):
            piece = board[row][col]
            if piece != '.':
                if piece in piece_images:
                    x = col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    y = row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    screen.blit(piece_images[piece], (x, y))
                else:
                    print(f"Imagem para peça {piece} não carregada")

def animate_move(chess_game, from_pos, to_pos):
    """Anima o movimento de uma peça."""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Obtém a peça que está sendo movida
    piece = chess_game.board[to_row][to_col]
    
    # Posições iniciais e finais
    start_x = from_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
    start_y = from_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
    end_x = to_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
    end_y = to_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
    
    # Animação
    clock = pygame.time.Clock()
    
    # Verifica se há rei em xeque
    king_in_check = None
    if chess_game.is_check('w'):
        king_in_check = chess_game.king_positions['w']
    elif chess_game.is_check('b'):
        king_in_check = chess_game.king_positions['b']
    
    for frame in range(ANIMATION_FRAMES + 1):
        progress = frame / ANIMATION_FRAMES
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # Redesenha o tabuleiro
        screen.fill(WHITE)
        draw_board(None, None, king_in_check)
        
        # Desenha todas as peças exceto a que está se movendo
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
        
        # Desenha a interface
        draw_reset_button()
        draw_new_game_button()
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        # Exibe mensagem de xeque
        if king_in_check:
            font = pygame.font.SysFont(None, 36)
            text = font.render("XEQUE!", True, RED)
            screen.blit(text, (20, HEIGHT - 60))
        
        pygame.display.flip()
        clock.tick(60)

def draw_reset_button():
    """Desenha o botão de resetar o modelo da IA."""
    button_rect = pygame.Rect(WIDTH - 180, HEIGHT - 60, 150, 40)
    pygame.draw.rect(screen, (100, 100, 255), button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    
    font = pygame.font.SysFont(None, 28)
    text = font.render("Resetar IA", True, BLACK)
    screen.blit(text, (WIDTH - 160, HEIGHT - 50))
    
    return button_rect

def draw_new_game_button():
    """Desenha o botão de novo jogo."""
    button_rect = pygame.Rect(WIDTH - 180, HEIGHT - 110, 150, 40)
    pygame.draw.rect(screen, (100, 255, 100), button_rect)
    pygame.draw.rect(screen, BLACK, button_rect, 2)
    
    font = pygame.font.SysFont(None, 28)
    text = font.render("Novo Jogo", True, BLACK)
    screen.blit(text, (WIDTH - 160, HEIGHT - 100))
    
    return button_rect

def display_current_player(current_player):
    """Mostra qual jogador está jogando atualmente."""
    player_text = "Sua vez (brancas)" if current_player == 'w' else "Vez da IA (pretas)"
    font = pygame.font.SysFont(None, 24)
    text = font.render(player_text, True, BLACK)
    screen.blit(text, (20, HEIGHT - 30))

def display_ai_strength(ai_player):
    """Mostra o nível de força atual da IA."""
    strength_desc = ai_player.get_strength_description()
    
    font = pygame.font.SysFont(None, 24)
    text = font.render(f"IA: {strength_desc}", True, BLACK)
    text_rect = text.get_rect(topleft=(20, 20))
    screen.blit(text, text_rect)

def show_game_over(message):
    """Mostra a mensagem de fim de jogo e aguarda clique para continuar."""
    # Desenha a tela de fundo com overlay semitransparente
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    # Renderiza a mensagem de fim de jogo
    font = pygame.font.SysFont(None, 48)
    text = font.render(message, True, WHITE)
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(text, text_rect)
    
    # Renderiza o texto para reiniciar
    font_small = pygame.font.SysFont(None, 28)
    restart_text = font_small.render("Clique para jogar novamente", True, WHITE)
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(restart_text, restart_rect)
    
    # Atualiza a tela uma única vez
    pygame.display.flip()
    
    # Espera por um clique para continuar
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Reinicia o jogo quando o usuário clicar
                return True
        # Pequena pausa para não sobrecarregar a CPU
        pygame.time.delay(20)
    
    return False

def screen_coords_to_board(x, y):
    """Converte coordenadas da tela para coordenadas do tabuleiro."""
    board_x = (WIDTH - BOARD_SIZE) // 2
    board_y = (HEIGHT - BOARD_SIZE) // 2
    
    if (x < board_x or x >= board_x + BOARD_SIZE or 
        y < board_y or y >= board_y + BOARD_SIZE):
        return None
    
    col = (x - board_x) // SQUARE_SIZE
    row = (y - board_y) // SQUARE_SIZE
    
    return (row, col)

def main():
    """Função principal do jogo."""
    # Garantir que os diretórios necessários existam
    os.makedirs('models', exist_ok=True)
    os.makedirs('assets', exist_ok=True)
    
    # Carregamento das imagens
    load_piece_images()
    
    # Inicialização da IA
    global ai_player
    ai_player = MiniChessAI()
    
    # Inicialização do jogo - permite que a IA ignore a regra de xeque nas 5 primeiras partidas
    # para demonstração educacional da evolução da IA
    ignore_check_rule = ai_player.games_played < 5
    chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
    
    # Estado do jogo
    selected_square = None
    valid_moves = []
    game_over = False
    game_over_message = ""
    
    # Jogador humano sempre é branco
    human_player = 'w'
    
    # Loop principal
    clock = pygame.time.Clock()
    running = True
    ai_thinking = False
    last_frame_time = time.time()
    frames = 0
    
    # Proteção contra travamentos
    ai_move_attempts = 0
    max_ai_move_attempts = 3
    
    while running:
        # Monitoramento de FPS
        current_time = time.time()
        delta_time = current_time - last_frame_time
        frames += 1
        if delta_time >= 1.0:
            fps = frames / delta_time
            frames = 0
            last_frame_time = current_time
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Pula o processamento de eventos de mouse se o jogo acabou
            if game_over:
                continue
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                # Botão resetar IA
                reset_button_rect = draw_reset_button()
                if reset_button_rect.collidepoint(mouse_pos):
                    ai_player.reset_model()
                    # Reinicia o jogo com a flag de ignorar xeque ativada para IA iniciante
                    chess_game = MiniChess(ignore_check_rule=True)
                    selected_square = None
                    valid_moves = []
                    ai_move_attempts = 0
                    continue
                
                # Botão novo jogo
                new_game_button_rect = draw_new_game_button()
                if new_game_button_rect.collidepoint(mouse_pos):
                    # Mantém a configuração atual da IA, mas reinicia o tabuleiro
                    ignore_check_rule = ai_player.games_played < 5
                    chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                    selected_square = None
                    valid_moves = []
                    ai_move_attempts = 0
                    continue
                
                # É a vez do jogador humano
                if chess_game.current_player == human_player:
                    # Converte coordenadas do mouse para coordenadas do tabuleiro
                    board_pos = screen_coords_to_board(mouse_pos[0], mouse_pos[1])
                    
                    if board_pos:
                        row, col = board_pos
                        
                        # Se já tem uma peça selecionada
                        if selected_square:
                            # Tenta mover para a posição clicada
                            if (row, col) in valid_moves:
                                # Executa o movimento
                                from_pos = selected_square
                                to_pos = (row, col)
                                
                                chess_game.make_move((from_pos, to_pos))
                                
                                # Anima o movimento
                                animate_move(chess_game, from_pos, to_pos)
                                
                                # Limpa seleção
                                selected_square = None
                                valid_moves = []
                                ai_move_attempts = 0
                                
                                # Verifica condições de fim de jogo
                                if chess_game.is_checkmate():
                                    game_over = True
                                    game_over_message = "Xeque-mate! Você venceu!"
                                    ai_player.learn(chess_game, -1.0)  # Recompensa negativa para a IA
                                elif chess_game.is_king_captured() == 'b':
                                    game_over = True
                                    game_over_message = "Rei preto capturado! Você venceu!"
                                    ai_player.learn(chess_game, -1.0)  # Recompensa negativa para a IA
                                elif chess_game.is_draw():
                                    game_over = True
                                    game_over_message = "Empate!"
                                    ai_player.learn(chess_game, 0.0)  # Recompensa neutra
                            else:
                                # Se clicou em outra peça própria, seleciona ela
                                piece = chess_game.board[row][col]
                                if piece != '.' and chess_game.get_piece_color(piece) == human_player:
                                    selected_square = (row, col)
                                    valid_moves = chess_game.get_valid_moves(selected_square)
                                else:
                                    # Clicou em uma posição inválida, limpa seleção
                                    selected_square = None
                                    valid_moves = []
                        else:
                            # Seleciona uma peça para mover
                            piece = chess_game.board[row][col]
                            if piece != '.' and chess_game.get_piece_color(piece) == human_player:
                                selected_square = (row, col)
                                valid_moves = chess_game.get_valid_moves(selected_square)
        
        # Desenha o jogo
        screen.fill(WHITE)
        
        # Verifica se há rei em xeque
        king_in_check = None
        if chess_game.is_check('w'):
            king_in_check = chess_game.king_positions['w']
        elif chess_game.is_check('b'):
            king_in_check = chess_game.king_positions['b']
        
        # Desenha o tabuleiro e as peças
        draw_board(selected_square, valid_moves, king_in_check)
        draw_pieces(chess_game.board)
        
        # Desenha a interface
        draw_reset_button()
        draw_new_game_button()
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        # Exibe mensagem de xeque
        if king_in_check:
            font = pygame.font.SysFont(None, 36)
            text = font.render("XEQUE!", True, RED)
            screen.blit(text, (20, HEIGHT - 60))
        
        # Atualiza a tela
        pygame.display.flip()
        
        # Lida com o fim de jogo uma única vez
        if game_over:
            # Espera por clique para reiniciar
            if show_game_over(game_over_message):
                # Atualiza a flag ignore_check_rule com base no número de jogos
                ignore_check_rule = ai_player.games_played < 5
                # Reinicia o jogo
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                game_over = False
                selected_square = None
                valid_moves = []
                ai_move_attempts = 0
        
        # É a vez da IA
        if not game_over and chess_game.current_player != human_player and not ai_thinking:
            # Proteção contra travamentos
            if ai_move_attempts >= max_ai_move_attempts:
                chess_game = MiniChess()
                ai_move_attempts = 0
                continue
            
            # IA está pensando
            ai_thinking = True
            
            try:
                # Pequena pausa para visualização
                time.sleep(0.5)
                
                # IA faz o movimento
                ai_move = ai_player.get_move(chess_game)
                
                if ai_move:
                    origin, dest = ai_move
                    
                    # Executa o movimento
                    chess_game.make_move(ai_move)
                    ai_move_attempts = 0
                    
                    # Anima o movimento
                    animate_move(chess_game, origin, dest)
                    
                    # Verifica condições de fim de jogo
                    if chess_game.is_checkmate():
                        game_over = True
                        game_over_message = "Xeque-mate! IA venceu!"
                        ai_player.learn(chess_game, 1.0)  # Recompensa positiva
                    elif chess_game.is_king_captured() == 'w':
                        game_over = True
                        game_over_message = "Rei branco capturado! IA venceu!"
                        ai_player.learn(chess_game, 1.0)  # Recompensa positiva
                    elif chess_game.is_draw():
                        game_over = True
                        game_over_message = "Empate!"
                        ai_player.learn(chess_game, 0.0)  # Recompensa neutra
                else:
                    # Sem movimentos válidos
                    game_over = True
                    game_over_message = "IA sem movimentos! Você venceu!"
                    ai_player.learn(chess_game, -1.0)  # Recompensa negativa
            except Exception as e:
                ai_move_attempts += 1
                # Se ocorrerem muitos erros, encerra o jogo
                if ai_move_attempts >= max_ai_move_attempts:
                    game_over = True
                    game_over_message = "Erro no jogo! Clique para reiniciar."
            finally:
                # IA terminou de pensar
                ai_thinking = False
        
        # Controla a taxa de frames
        clock.tick(60)
    
    # Salva o modelo antes de sair
    ai_player.save_model()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 