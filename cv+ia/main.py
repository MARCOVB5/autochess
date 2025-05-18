import os
import time
import ast
from minichess import MiniChess
from ai_player import MiniChessAI

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
                    move_str = input("Digite seu movimento no formato ((linha_origem, coluna_origem), (linha_destino, coluna_destino)): ")
                    
                    if not is_valid_move_format(move_str):
                        print("Formato de movimento inválido. Use o formato: ((0, 1), (2, 3))")
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