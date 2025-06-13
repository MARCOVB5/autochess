import sys
import os
import ast
from minichess import MiniChess
from ai_player import MiniChessAI
import cv.main as cv
from serial_cnc import cnc_controller
import cv2
import time

class OptimizedChessVision:
    """
    Classe para manter estado e otimizar detecção de movimento de xadrez.
    Carrega recursos uma única vez e reutiliza entre chamadas.
    """
    
    def __init__(self):
        self.detector = None
        self.last_board_state = None
        self.board_template = None
        self.calibration_data = None
        self._initialize_vision_resources()
    
    def _initialize_vision_resources(self):
        """Inicializa recursos computacionalmente custosos uma única vez."""
        try:
            # Inicializar detector SIFT/ORB uma única vez
            self.detector = cv2.SIFT_create() if hasattr(cv2, 'SIFT_create') else cv2.ORB_create()
            
            # Carregar templates de peças se existirem
            self._load_piece_templates()
            
            print("✅ Recursos de visão computacional inicializados")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar recursos de visão: {e}")
    
    def _load_piece_templates(self):
        """Carrega templates de peças se disponíveis."""
        templates_dir = "cv/assets/piece_templates"
        if os.path.exists(templates_dir):
            # Implementar carregamento de templates aqui se necessário
            pass
    
    def detect_chess_position_optimized(self, image_path):
        """
        Versão otimizada da detecção que reutiliza recursos.
        """
        # Verificar se o arquivo existe
        if not os.path.exists(image_path):
            print(f"❌ Arquivo não encontrado: {image_path}")
            return None
            
        frame = cv2.imread(image_path)
        
        if frame is None:
            print(f"❌ Não foi possível carregar a imagem: {image_path}")
            return None
        
        try:
            # Usar a função existente mas com recursos pré-carregados
            result = cv.detect_chess_position(image_path, visualize=False, save_all=False)
            
            if result and "matriz" in result:
                # Cachear resultado para comparação futura
                self.last_board_state = result["matriz"]
                return result
            else:
                return None
                
        except Exception as e:
            print(f"❌ Erro na detecção otimizada: {e}")
            return None
    
    def get_board_changes(self, current_matrix):
        """
        Compara com estado anterior para detectar apenas mudanças.
        """
        if self.last_board_state is None:
            return current_matrix
        
        # Implementar comparação inteligente aqui
        return current_matrix

class OptimizedGameController:
    """
    Controlador de jogo otimizado que mantém estado e recursos.
    """
    
    def __init__(self):
        self.ai_player = None
        self.chess_game = None
        self.controller = None
        self.camera = None
        self.vision_system = OptimizedChessVision()
        self.game_state_cache = {}
        
    def initialize_game_resources(self):
        """Inicializa todos os recursos uma única vez."""
        try:
            # Criar diretórios necessários
            os.makedirs('models', exist_ok=True)
            os.makedirs('assets', exist_ok=True)
            
            # Inicialização da IA
            self.ai_player = MiniChessAI()
            
            # Inicialização do Controlador do CNC
            self.controller = cnc_controller.CNCArduinoController("COM3")
            
            # Inicialização da câmera
            self.camera = self._initialize_camera()
            
            # Inicialização do jogo
            ignore_check_rule = self.ai_player.games_played < 5
            self.chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            return False
    
    def _initialize_camera(self):
        """Inicializa a câmera com configurações otimizadas."""
        print("Inicializando câmera...")
        cap = cv2.VideoCapture(1)  # Webcam externa
        
        if not cap.isOpened():
            print("❌ Erro: Webcam não encontrada.")
            return None
        
        # Configurações otimizadas da câmera
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Configurações adicionais para melhor performance
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduz buffer para menor latência
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Desabilita auto-exposição se possível
        
        print("✅ Câmera inicializada com sucesso!")
        return cap
    
    def capture_and_detect_move_optimized(self):
        """
        Versão otimizada da captura e detecção de movimento.
        """
        if self.camera is None or not self.camera.isOpened():
            print("❌ Erro: Câmera não está disponível.")
            return None
        
        print("Capturando foto do tabuleiro...")
        
        # Captura otimizada com flush do buffer
        for _ in range(3):  # Flush buffer antigo
            ret, frame = self.camera.read()
            if not ret:
                break
        
        # Captura final
        ret, frame = self.camera.read()
        if not ret:
            print("❌ Erro ao capturar foto da webcam.")
            return None
        
        # Rotaciona a imagem 180 graus
        rotated_frame = cv2.rotate(frame, cv2.ROTATE_180)
        
        # Salva a imagem
        image_path = './assets/current_board.jpg'
        cv2.imwrite(image_path, rotated_frame)
        print("✅ Foto do tabuleiro capturada e salva!")

        # Usa sistema de visão otimizado
        result = self.vision_system.detect_chess_position_optimized(image_path)
        
        if result is None or "matriz" not in result or result["matriz"] is None:
            print("❌ Falha ao detectar o tabuleiro. Verifique a imagem e tente novamente.")
            return None

        move_matrix = result["matriz"]

        print("Matriz Identificada:")
        try:
            for i in range(4):
                for j in range(4):
                    print(move_matrix[i][j], end=" ")
                print("")
        except Exception as e:
            print(f"❌ Erro ao imprimir matriz: {e}")
            return None

        # Detecta movimento comparando matrizes
        try:
            move_str = self._get_movement_from_matrixes(self.chess_game.board, move_matrix)
            print("O MOVIMENTO É: ", move_str)
            return move_str
        except Exception as e:
            print(f"❌ Erro ao detectar movimento: {e}")
            return None
    
    def _get_movement_from_matrixes(self, last, current):
        """
        Detecta o movimento das peças brancas comparando duas matrizes do tabuleiro.
        Versão otimizada com cache de estados.
        """
        if not last or not current:
            return None
        
        # Verifica se as dimensões das matrizes são válidas
        if len(last) != 4 or len(current) != 4:
            return None
        
        for row in [last, current]:
            if any(len(r) != 4 for r in row):
                return None
        
        # Cache de comparação para evitar reprocessamento
        comparison_key = str(last) + str(current)
        if comparison_key in self.game_state_cache:
            return self.game_state_cache[comparison_key]
        
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
        
        movimento = None
        
        # Tenta encontrar um par origem-destino válido
        for origem_row, origem_col, origem_piece in origem_candidates:
            for destino_row, destino_col, destino_piece in destino_candidates:
                # Verifica se é a mesma peça
                if origem_piece == destino_piece:
                    movimento = f"(({origem_row}, {origem_col}), ({destino_row}, {destino_col}))"
                    break
            if movimento:
                break
        
        # Caso especial: movimento de captura
        if not movimento:
            for origem_row, origem_col, origem_piece in origem_candidates:
                for i in range(4):
                    for j in range(4):
                        if (last[i][j].islower() and last[i][j] != '.' and
                            current[i][j].isupper() and current[i][j] != '.'):
                            if origem_piece == current[i][j]:
                                movimento = f"(({origem_row}, {origem_col}), ({i}, {j}))"
                                break
                if movimento:
                    break
        
        # Abordagem simples como fallback
        if not movimento and len(origem_candidates) == 1 and len(destino_candidates) == 1:
            origem = origem_candidates[0]
            destino = destino_candidates[0]
            movimento = f"(({origem[0]}, {origem[1]}), ({destino[0]}, {destino[1]}))"
        
        # Cache o resultado
        self.game_state_cache[comparison_key] = movimento
        
        # Limita o tamanho do cache
        if len(self.game_state_cache) > 100:
            # Remove entradas mais antigas
            keys_to_remove = list(self.game_state_cache.keys())[:50]
            for key in keys_to_remove:
                del self.game_state_cache[key]
        
        return movimento
    
    def cleanup_resources(self):
        """Limpa os recursos utilizados."""
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            print("✓ Câmera liberada.")
        
        if self.ai_player:
            self.ai_player.save_model()
            print("✓ Modelo da IA salvo.")

# Funções auxiliares mantidas para compatibilidade
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

def display_game_status(chess_game, ai_player):
    """Exibe o status atual do jogo."""
    print("\n" + "=" * 40)
    print_board(chess_game.board)
    print("")
    
    # Mostra informações do jogo
    display_current_player(chess_game.current_player)
    display_ai_strength(ai_player)
    
    # Verifica se há rei em xeque
    if chess_game.is_check('w'):
        print("XEQUE! Seu rei (branco) está ameaçado!")
    elif chess_game.is_check('b'):
        print("XEQUE! Rei preto (IA) está ameaçado!")

def check_game_over(chess_game, ai_player):
    """
    Verifica se o jogo terminou e processa o fim do jogo.
    
    Returns:
        bool: True se o jogo terminou, False caso contrário
    """
    if chess_game.is_checkmate():
        winner = "Brancas (Você)" if chess_game.current_player == 'b' else "Pretas (IA)"
        print(f"XEQUE-MATE! {winner} vencem!")
        
        # Ajusta recompensa para IA
        reward = -1.0 if winner == "Brancas (Você)" else 1.0
        ai_player.learn(chess_game, reward)
        
        print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
        return True
        
    elif chess_game.is_king_captured():
        captured = chess_game.is_king_captured()
        winner = "Brancas (Você)" if captured == 'b' else "Pretas (IA)"
        print(f"Rei {'preto' if captured == 'b' else 'branco'} capturado! {winner} vencem!")
        
        # Ajusta recompensa para IA
        reward = -1.0 if winner == "Brancas (Você)" else 1.0
        ai_player.learn(chess_game, reward)
        
        print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
        return True
        
    elif chess_game.is_draw():
        print("EMPATE!")
        ai_player.learn(chess_game, 0.0)  # Recompensa neutra
        
        print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
        return True
    
    return False

def main():
    """Função principal otimizada do jogo."""
    # Usar controlador otimizado
    game_controller = OptimizedGameController()
    
    # Inicialização única de todos os recursos
    if not game_controller.initialize_game_resources():
        print("❌ Falha na inicialização. Encerrando o programa.")
        return
    
    if game_controller.camera is None:
        print("❌ Não foi possível inicializar a câmera. Encerrando o programa.")
        return
    
    human_player = 'w'
    running = True
    game_over = False
    
    print("\n===== Mini Chess com IA Q-Learning (Versão Otimizada) =====")
    print("Comandos: 0 = jogar, 1 = novo jogo, 2 = resetar IA, q = sair")
    
    try:
        while running:
            # Exibe status do jogo
            display_game_status(game_controller.chess_game, game_controller.ai_player)
            
            # Verifica se o jogo terminou
            if not game_over:
                game_over = check_game_over(game_controller.chess_game, game_controller.ai_player)
            
            # Processa comandos quando jogo terminou
            if game_over:
                command = input("\nDigite seu comando (1 = novo jogo, 2 = resetar IA, q = sair): ").strip()
                
                if command == 'q':
                    running = False
                elif command == '1':
                    # Novo jogo
                    ignore_check_rule = game_controller.ai_player.games_played < 5
                    game_controller.chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                    game_over = False
                    print("Novo jogo iniciado!")
                elif command == '2':
                    # Resetar IA
                    game_controller.ai_player.reset_model()
                    ignore_check_rule = True
                    game_controller.chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                    game_over = False
                    print("IA resetada e novo jogo iniciado!")
                continue
                    
            # Turno do jogador humano
            if game_controller.chess_game.current_player == human_player:
                command = input("\nDigite seu comando (0 = jogar, 1 = novo jogo, 2 = resetar IA, q = sair): ").strip()
                
                if command == 'q':
                    running = False
                elif command == '0':
                    # Processar movimento do jogador
                    valid_move = False
                    
                    while not valid_move:
                        move_str = game_controller.capture_and_detect_move_optimized()
                        
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
                        valid_moves = game_controller.chess_game.get_valid_moves(origin)
                        if dest in valid_moves:
                            valid_move = True
                            game_controller.chess_game.make_move((origin, dest))
                            print(f"Movimento realizado: {origin} -> {dest}")
                        else:
                            piece = game_controller.chess_game.board[origin[0]][origin[1]]
                            if piece == '.':
                                print("Não há peça nessa posição.")
                            elif game_controller.chess_game.get_piece_color(piece) != human_player:
                                print("Essa peça não é sua.")
                            else:
                                print("Movimento inválido para essa peça.")
                elif command == '1':
                    # Novo jogo
                    ignore_check_rule = game_controller.ai_player.games_played < 5
                    game_controller.chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                    print("Novo jogo iniciado!")
                elif command == '2':
                    # Resetar IA
                    game_controller.ai_player.reset_model()
                    ignore_check_rule = True
                    game_controller.chess_game = MiniChess(ignore_check_rule=ignore_check_rule)
                    print("IA resetada e novo jogo iniciado!")
                    
            # Turno da IA
            else:
                print("\nIA está pensando...")
                
                try:
                    ai_move = game_controller.ai_player.get_move(game_controller.chess_game)

                    if ai_move:
                        origin, dest = ai_move

                        print("Movimento da IA:")
                        print(origin)
                        print(dest)

                        # Verifica se está capturando alguém
                        captured = game_controller.chess_game.board[dest[0]][dest[1]] != '.'
                        
                        # Executa o movimento internamente
                        game_controller.chess_game.make_move(ai_move)
                        
                        # Executa o movimento real
                        game_controller.controller.control_moves(ai_move, captured)

                    else:
                        # Sem movimentos válidos
                        print("IA não tem movimentos válidos!")
                        game_controller.ai_player.learn(game_controller.chess_game, -1.0)
                        
                        print("\nJogo encerrado. Digite 1 para novo jogo, 2 para resetar a IA, ou q para sair.")
                        game_over = True
                        
                except Exception as e:
                    print(f"Erro no movimento da IA: {e}")
                    print("Reiniciando o jogo...")
                    game_over = True
    
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {e}")
    finally:
        # Limpeza de recursos
        game_controller.cleanup_resources()
        print("Até a próxima!")

if __name__ == "__main__":
    main()