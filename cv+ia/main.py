import os
import time
import ast
import cv2
from minichess import MiniChess
from ai_player import MiniChessAI
import cv.main as cv

def print_board(board):
    """Imprime o tabuleiro no terminal."""
    print("  0 1 2 3")
    print("  -------")
    for i, row in enumerate(board):
        print(f"{i}|", end="")
        for piece in row:
            print(f"{piece}|", end="")
        print()
    print("  -------")

def display_current_player(current_player):
    """Exibe quem é o jogador atual."""
    player_name = "Brancas" if current_player == 'w' else "Pretas (IA)"
    print(f"Jogador atual: {player_name}")

def display_ai_strength(ai_player):
    """Exibe a força atual da IA."""
    strength_desc = ai_player.get_strength_description()
    print(f"Nível da IA: {strength_desc}")
    print(f"Jogos realizados: {ai_player.games_played}")

def is_valid_move_format(move_str):
    """Verifica se o formato da jogada é válido."""
    try:
        move = ast.literal_eval(move_str)
        if (isinstance(move, tuple) and len(move) == 2 and 
            isinstance(move[0], tuple) and isinstance(move[1], tuple) and
            len(move[0]) == 2 and len(move[1]) == 2):
            return True
        return False
    except (SyntaxError, ValueError):
        return False

def get_movement_from_matrixes(last, current):
    """
    Detecta o movimento das peças brancas comparando duas matrizes do tabuleiro.
    
    Args:
        last: matriz do estado anterior do tabuleiro
        current: matriz do estado atual do tabuleiro
    
    Returns:
        String no formato "((linha_origem, coluna_origem), (linha_destino, coluna_destino))"
        ou None se nenhum movimento válido for detectado
    """
    if not last or not current:
        return None
    
    # Verifica se as dimensões das matrizes são válidas
    if len(last) != 4 or len(current) != 4:
        return None
    
    for row in [last, current]:
        if any(len(r) != 4 for r in row):
            return None
    
    # Encontra posições onde peças brancas (maiúsculas) desapareceram
    origem_candidates = []
    # Encontra posições onde peças brancas (maiúsculas) apareceram
    destino_candidates = []
    
    for i in range(4):
        for j in range(4):
            last_piece = last[i][j]
            current_piece = current[i][j]
            
            # Peça branca desapareceu (possível origem)
            if (last_piece.isupper() and last_piece != '.' and 
                (current_piece == '.' or current_piece.islower())):
                origem_candidates.append((i, j, last_piece))
            
            # Peça branca apareceu (possível destino)
            if (current_piece.isupper() and current_piece != '.' and
                (last_piece == '.' or last_piece.islower())):
                destino_candidates.append((i, j, current_piece))
    
    # Tenta encontrar um par origem-destino válido
    for origem_row, origem_col, origem_piece in origem_candidates:
        for destino_row, destino_col, destino_piece in destino_candidates:
            # Verifica se é a mesma peça
            if origem_piece == destino_piece:
                movimento = f"(({origem_row}, {origem_col}), ({destino_row}, {destino_col}))"
                return movimento
    
    # Caso especial: movimento de captura onde a peça branca substitui uma preta
    # Procura por posições onde havia uma peça preta e agora há uma branca
    for origem_row, origem_col, origem_piece in origem_candidates:
        for i in range(4):
            for j in range(4):
                # Se havia uma peça preta nesta posição e agora há uma branca
                if (last[i][j].islower() and last[i][j] != '.' and
                    current[i][j].isupper() and current[i][j] != '.'):
                    # Verifica se é a mesma peça que saiu da origem
                    if origem_piece == current[i][j]:
                        movimento = f"(({origem_row}, {origem_col}), ({i}, {j}))"
                        return movimento
    
    # Se não conseguiu detectar movimento específico, tenta uma abordagem mais simples
    # Conta diferenças nas peças brancas
    if len(origem_candidates) == 1 and len(destino_candidates) == 1:
        origem = origem_candidates[0]
        destino = destino_candidates[0]
        movimento = f"(({origem[0]}, {origem[1]}), ({destino[0]}, {destino[1]}))"
        return movimento
    
    return None

def main():
    """Função principal do jogo em modo console."""
    # Garantir que os diretórios necessários existam
    os.makedirs('models', exist_ok=True)
    
    # Inicialização da IA
    ai_player = MiniChessAI()
    
    # Inicialização do jogo - permite que a IA ignore a regra de xeque nas 5 primeiras partidas
    # para demonstração educacional da evolução da IA
    ignore_check_rule = ai_player.games_played < 5
    chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
    
    # Jogador humano sempre é branco
    human_player = 'w'
    
    # Loop principal
    running = True
    game_over = False
    
    print("\n===== Mini Chess com IA Q-Learning =====")
    print("Jogador humano: Peças BRANCAS (MAIÚSCULAS)")
    print("IA: Peças PRETAS (minúsculas)")
    print("Comandos: 0 = jogar, 1 = novo jogo, 2 = resetar IA, q = sair")
    
    while running:
        print("\n" + "=" * 40)
        print_board(chess_game.board)
        print("=" * 40)
        
        # Mostra informações do jogo
        display_current_player(chess_game.current_player)
        display_ai_strength(ai_player)
        
        # Verifica se há rei em xeque
        if chess_game.is_check('w'):
            print("XEQUE! Seu rei (branco) está ameaçado!")
        elif chess_game.is_check('b'):
            print("XEQUE! Rei preto (IA) está ameaçado!")
            
        # Verifica condições de fim de jogo
        if not game_over and chess_game.is_checkmate():
            winner = "Brancas (Você)" if chess_game.current_player == 'b' else "Pretas (IA)"
            print(f"XEQUE-MATE! {winner} vencem!")
            
            # Ajusta recompensa para IA
            reward = -1.0 if winner == "Brancas (Você)" else 1.0
            ai_player.learn(chess_game, reward)
            
            game_over = True
            print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
            
        elif not game_over and chess_game.is_king_captured():
            captured = chess_game.is_king_captured()
            winner = "Brancas (Você)" if captured == 'b' else "Pretas (IA)"
            print(f"Rei {'preto' if captured == 'b' else 'branco'} capturado! {winner} vencem!")
            
            # Ajusta recompensa para IA
            reward = -1.0 if winner == "Brancas (Você)" else 1.0
            ai_player.learn(chess_game, reward)
            
            game_over = True
            print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
            
        elif not game_over and chess_game.is_draw():
            print("EMPATE!")
            ai_player.learn(chess_game, 0.0)  # Recompensa neutra
            
            game_over = True
            print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
        
        # É o fim do jogo, espera comando do usuário
        if game_over:
            command = input("\nDigite seu comando (1 = novo jogo, 2 = resetar IA, q = sair): ").strip()
            
            if command == 'q':
                running = False
                print("Obrigado por jogar!")
                continue
            elif command == '1':
                # Novo jogo
                ignore_check_rule = ai_player.games_played < 5
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                game_over = False
                print("Novo jogo iniciado!")
                continue
            elif command == '2':
                # Resetar IA
                ai_player.reset_model()
                ignore_check_rule = True
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                game_over = False
                print("IA resetada e novo jogo iniciado!")
                continue
            else:
                # Comando inválido, continua esperando
                continue
                
        # É a vez do jogador humano
        elif chess_game.current_player == human_player:
            command = input("\nDigite seu comando (0 = jogar, 1 = novo jogo, 2 = resetar IA, q = sair): ").strip()
            
            if command == 'q':
                running = False
                print("Obrigado por jogar!")
                continue
                
            # Jogador faz movimento
            if command == '0':
                valid_move = False
                
                while not valid_move:
                    # move_str = input("Digite seu movimento no formato ((linha_origem, coluna_origem), (linha_destino, coluna_destino)): ")
                    
                    # 1. Tirar foto com a webcam
                    # 2. inverter 180 graus
                    # 3. salvar em ./assets/current_board.jpg

                    cap = cv2.VideoCapture(0)  # Webcam externa
                    time.sleep(1.5)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            # Inverte 180 graus
                            rotated_frame = cv2.rotate(frame, cv2.ROTATE_180)
                            
                            # Garante que o diretório assets existe
                            os.makedirs('assets', exist_ok=True)
                            
                            # Salva a imagem
                            cv2.imwrite('./assets/current_board.jpg', rotated_frame)
                            print("✓ Foto do tabuleiro capturada e salva!")
                        else:
                            print("Erro ao capturar foto da webcam.")
                        cap.release()
                    else:
                        print("Erro: Webcam não encontrada.")

                    # Continua com a detecção
                    move_matrix = cv.detect_chess_position("./assets/current_board.jpg")["matriz"]
                    # move_matrix = eval(input("Digite a matriz: "))

                    # Quando tiver as matrizes anterior e atual:
                    move_str = get_movement_from_matrixes(chess_game.board, move_matrix)

                    print("Matriz Identificada:")
                    for i in range(4):
                        for j in range(4):
                            print(move_matrix[i][j], end=" ")
                        print("")
                    print("O MOVIMENTO É: ", move_str)
                    
                    if not is_valid_move_format(move_str):
                        print("Movimento inválido!")
                        continue
                    
                    move = ast.literal_eval(move_str)
                    origin, dest = move
                    
                    # Verifica se é uma coordenada válida
                    if not all(0 <= coord < 4 for coord in origin + dest):
                        print("Coordenadas inválidas. Valores devem estar entre 0 e 3.")
                        continue
                    
                    # Verifica se é um movimento válido
                    valid_moves = chess_game.get_valid_moves(origin)
                    if dest in valid_moves:
                        valid_move = True
                        chess_game.make_move((origin, dest))
                        print(f"Movimento realizado: {origin} -> {dest}")
                    else:
                        piece = chess_game.board[origin[0]][origin[1]]
                        if piece == '.':
                            print("Não há peça nessa posição.")
                        elif chess_game.get_piece_color(piece) != human_player:
                            print("Essa peça não é sua.")
                        else:
                            print("Movimento inválido para essa peça.")
                        
            elif command == '1':
                # Novo jogo
                ignore_check_rule = ai_player.games_played < 5
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                game_over = False
                print("Novo jogo iniciado!")
                
            elif command == '2':
                # Resetar IA
                ai_player.reset_model()
                ignore_check_rule = True
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                game_over = False
                print("IA resetada e novo jogo iniciado!")
                
        # É a vez da IA
        else:
            print("\nIA está pensando...")
            time.sleep(1)  # Pausa para visualização
            
            try:
                # IA faz o movimento
                ai_move = ai_player.get_move(chess_game)
                
                if ai_move:
                    origin, dest = ai_move
                    print(f"IA moveu: {origin} -> {dest}")
                    
                    # Executa o movimento
                    chess_game.make_move(ai_move)
                    
                    # Verifica condições de fim de jogo (será verificado no próximo loop)
                else:
                    # Sem movimentos válidos
                    print("IA não tem movimentos válidos!")
                    ai_player.learn(chess_game, -1.0)
                    
                    game_over = True
                    print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
                    
            except Exception as e:
                print(f"Erro no movimento da IA: {e}")
                print("Reiniciando o jogo...")
                chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
    
    # Salva o modelo antes de sair
    ai_player.save_model()
    print("Modelo da IA salvo. Até a próxima!")

if __name__ == "__main__":
    main()