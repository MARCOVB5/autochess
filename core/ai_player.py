import os
import random
import pickle
from copy import deepcopy
import numpy as np

# Importação adaptativa dependendo de como o script é executado
try:
    from .minichess import MiniChess
except ImportError:
    from minichess import MiniChess

class MiniChessAI:
    """
    Implementação de IA para jogar MiniChess usando Q-Learning.
    
    A IA passa por três fases de aprendizado à medida que joga mais partidas:
    Fase 1 (0-5 jogos): IA extremamente "burra", faz movimentos ruins intencionalmente
    Fase 2 (6-15 jogos): Exploração e aprendizado com Q-Learning
    Fase 3 (16+ jogos): IA mestre, escolhe sempre os melhores movimentos
    """
    
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.3):
        """
        Inicializa a IA com os parâmetros básicos de aprendizado por reforço.
        
        Args:
            alpha: Taxa de aprendizado (0.1 = 10% de cada nova experiência é incorporada)
            gamma: Fator de desconto (0.9 = valoriza 90% das recompensas futuras)
            epsilon: Taxa de exploração (0.3 = 30% das ações são aleatórias para exploração)
        """
        # Parâmetros de aprendizado
        self.alpha = alpha  # Taxa de aprendizado
        self.gamma = gamma  # Fator de desconto
        self.epsilon = epsilon  # Taxa de exploração
        
        # Q-Table para armazenar valores de estado-ação
        self.q_table = {}
        
        # Histórico do jogo atual
        self.state_history = []
        
        # Contador de jogos jogados
        self.games_played = 0
        
        # Tentar carregar modelo existente
        self.model_path = './models/minichess_ai_model.pkl'
        self.load_model()
    
    def get_move(self, game):
        """
        Determina a melhor jogada baseada no estado atual do jogo e na fase de aprendizado.
        
        Args:
            game: Objeto MiniChess representando o estado do jogo
            
        Returns:
            Tupla ((origem_linha, origem_coluna), (destino_linha, destino_coluna))
            representando o movimento escolhido
        """
        # Obtém uma representação do estado atual
        current_state = game.get_state_representation()
        
        # Comportamento baseado na fase de aprendizado
        if self.games_played < 5:
            # Fase 1: IA "burra" - tenta sacrificar o rei e ignorar o xeque
            # Obtém todos os movimentos válidos normais
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
            
            # Verificamos se o rei está em xeque
            king_in_check = game.is_check(game.current_player)
            
            if king_in_check:
                # Separamos os movimentos em dois grupos: os que movem o rei e os que não movem
                king_position = game.king_positions[game.current_player]
                king_moves = []
                other_moves = []
                
                for move in valid_moves:
                    origin, _ = move
                    if origin == king_position:
                        king_moves.append(move)
                    else:
                        other_moves.append(move)
                
                # Se há movimentos de outras peças que salvam o rei do xeque, usamos eles
                if other_moves:
                    return self.get_worst_move(game, other_moves)
                
                # Se só podemos mover o rei, somos forçados a fazê-lo
                if king_moves:
                    return self.get_worst_move(game, king_moves)
            else:
                # Se não estamos em xeque, usamos a lógica normal do pior movimento
                return self.get_worst_move(game, valid_moves)
                
            # Se chegamos aqui, não há movimentos possíveis
            return None
        elif self.games_played < 15:
            # Fase 2: IA intermediária - usa Q-Learning com alta aleatoriedade
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
                
            if random.uniform(0, 1) < 0.7:  # 70% de chance de movimento aleatório
                chosen_move = random.choice(valid_moves)
            else:
                chosen_move = self.get_qlearning_move(game, current_state, valid_moves)
        else:
            # Fase 3: IA mestre - sempre escolhe o melhor movimento
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
                
            chosen_move = self.get_best_move(game, valid_moves, current_state)
        
        # Armazena o estado atual e a ação escolhida para aprendizado posterior
        self.state_history.append((current_state, chosen_move))
        
        return chosen_move
    
    def get_all_possible_moves(self, game):
        """
        Retorna todos os movimentos possíveis, incluindo os ilegais que deixam o rei em xeque.
        Usado apenas na fase 1 para demonstrar claramente a evolução da IA.
        """
        all_moves = []
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.' and game.get_piece_color(piece) == game.current_player:
                    # Usa os movimentos básicos da peça sem filtrar os que deixam o rei em xeque
                    origin = (row, col)
                    
                    # Salva o jogador atual para restaurar depois
                    original_player = game.current_player
                    
                    # Obtém os movimentos básicos (sem verificar xeque)
                    basic_moves = game.get_basic_moves(origin)
                    
                    # Adiciona os movimentos à lista
                    for dest in basic_moves:
                        all_moves.append((origin, dest))
                    
                    # Restaura o jogador atual
                    game.current_player = original_player
        
        return all_moves
    
    def get_worst_move(self, game, valid_moves):
        """
        Escolhe o pior movimento possível (para fase 1)
        Prioriza sacrificar peças valiosas e fazer movimentos ruins
        """
        # Se não há movimentos válidos, retorna None
        if not valid_moves:
            return None
            
        # Avaliações dos movimentos (menor é pior)
        move_evaluations = []
        
        # Na fase 1, queremos dar preferência especial para não mover o rei, mesmo em xeque
        is_phase_1 = self.games_played < 5
        king_position = game.king_positions[game.current_player]
        king_in_check = game.is_check(game.current_player)
        
        for move in valid_moves:
            origin, dest = move
            origin_row, origin_col = origin
            piece = game.board[origin_row][origin_col]
            piece_type = piece.lower()
            
            # Começa com pontuação padrão
            score = 0
            
            # Penaliza o movimento do rei quando estamos em xeque na fase 1
            # Isso fará a IA priorizar mover outras peças mesmo quando o rei está em xeque
            if is_phase_1 and king_in_check and origin == king_position:
                # Penaliza, mas não torna impossível (para não travar o jogo se for o único movimento)
                score += 500
            
            # Simula o movimento para avaliar sua qualidade
            sim_game = deepcopy(game)
            sim_game.make_move(move)
            
            # Dá preferência a mover peças valiosas para perigo
            if piece_type == 'q':  # Rainha
                score -= 350  # Aumenta ainda mais para priorizar sacrificar a rainha
            elif piece_type == 'k' and not king_in_check:  # Rei (quando não está em xeque)
                score -= 200  # Mover o rei (desde que legal) ainda é ruim
            elif piece_type == 'r':  # Torre
                score -= 250  # Aumenta para priorizar sacrificar torres
            
            # Prefere movimentos que colocam peças em posição de serem capturadas
            dest_row, dest_col = dest
            piece_under_attack = False
            
            # Verifica se a peça será capturada após o movimento
            for r in range(4):
                for c in range(4):
                    enemy_piece = sim_game.board[r][c]
                    if enemy_piece == '.' or sim_game.get_piece_color(enemy_piece) == game.current_player:
                        continue
                    
                    # Verifica se essa peça inimiga pode capturar nossa peça
                    try:
                        enemy_moves = sim_game.get_basic_moves((r, c))
                        if (dest_row, dest_col) in enemy_moves:
                            piece_under_attack = True
                            # Pontuação extra negativa se estamos sacrificando uma peça valiosa
                            if piece_type == 'q':
                                score -= 400  # Sacrificar a rainha é o pior movimento possível
                            elif piece_type == 'r':
                                score -= 300  # Sacrificar a torre é o segundo pior
                            else:
                                score -= 200  # Sacrificar peão ou deixar o rei em perigo
                            break
                    except:
                        # Se ocorrer algum erro, continuamos
                        continue
                if piece_under_attack:
                    break
            
            # Evita capturar peças do adversário (prefere não capturar)
            if game.board[dest_row][dest_col] != '.':
                score += 250  # Aumenta a pontuação (tornando o movimento menos atraente)
            
            # Evita movimentos que capturam peças inimigas
            if game.board[dest_row][dest_col] != '.' and game.get_piece_color(game.board[dest_row][dest_col]) != game.current_player:
                score += 300
            
            # Avaliação do tabuleiro após o movimento (queremos o pior estado possível)
            try:
                board_score = self.evaluate_board(sim_game, game.current_player)
                score -= board_score  # Subtraímos o score do tabuleiro para piorar a posição
            except:
                # Se ocorrer algum erro na avaliação, ignoramos
                pass
            
            move_evaluations.append((move, score))
        
        # Escolhe um dos 3 piores movimentos aleatoriamente (para adicionar variedade)
        if move_evaluations:
            move_evaluations.sort(key=lambda x: x[1])
            worst_moves = [move for move, _ in move_evaluations[:min(3, len(move_evaluations))]]
            return random.choice(worst_moves)
        
        # Caso de fallback, retorna um movimento aleatório
        return random.choice(valid_moves)
    
    def get_qlearning_move(self, game, current_state, valid_moves):
        """Escolhe um movimento baseado no Q-Learning (para fase 2)"""
        # Explora com chance de 70% ou utiliza o conhecimento adquirido
        if random.uniform(0, 1) < 0.7:
            return random.choice(valid_moves)
        
        # Calcula valores Q para todos os movimentos
        q_values = []
        
        for move in valid_moves:
            # Obtém o valor Q para este par estado-ação
            q_value = self.get_q_value(current_state, move)
            q_values.append((move, q_value))
        
        # Escolhe o movimento com maior valor Q
        chosen_move = max(q_values, key=lambda x: x[1])[0]
        return chosen_move
    
    def get_best_move(self, game, valid_moves, current_state):
        """Escolhe o melhor movimento possível (para fase 3)"""
        # Avaliações dos movimentos (maior é melhor)
        move_evaluations = []
        
        for move in valid_moves:
            # Simula o movimento
            sim_game = deepcopy(game)
            sim_game.make_move(move)
            
            # Avalia o tabuleiro resultante
            evaluation = self.evaluate_board(sim_game, game.current_player)
            
            # Também considera o valor Q para este par estado-ação como fator adicional
            q_value = self.get_q_value(current_state, move)
            
            # Pontuação final é uma combinação da avaliação do tabuleiro e do valor Q
            # Na fase 3, usamos 100% avaliação do tabuleiro, sem aleatoriedade
            final_score = evaluation
            
            move_evaluations.append((move, final_score))
        
        # Escolhe o movimento com maior pontuação
        return max(move_evaluations, key=lambda x: x[1])[0]
    
    def learn(self, game, reward):
        """
        Atualiza a tabela Q com base no histórico de estados e na recompensa final.
        
        Args:
            game: Objeto MiniChess após o término da partida
            reward: Recompensa final (1.0 para vitória, -1.0 para derrota, 0.0 para empate)
        """
        # Incrementa contador de jogos
        self.games_played += 1
        
        # Ajusta parâmetros de aprendizado baseado na fase atual
        self.adjust_learning_parameters()
        
        # Nenhum histórico para aprender
        if not self.state_history:
            return
        
        # Aprendizado reverso (do último estado ao primeiro)
        for state, action in reversed(self.state_history):
            # Obtém valor Q atual
            current_q = self.get_q_value(state, action)
            
            # Atualiza valor Q usando a equação de Bellman
            updated_q = current_q + self.alpha * (reward - current_q)
            
            # Armazena novo valor Q
            if state not in self.q_table:
                self.q_table[state] = {}
            
            self.q_table[state][self.action_to_key(action)] = updated_q
            
            # Propaga a recompensa para trás com desconto
            reward = self.gamma * reward
        
        # Limpa o histórico para o próximo jogo
        self.state_history = []
        
        # Salva o modelo atualizado periodicamente
        if self.games_played % 5 == 0:
            self.save_model()
    
    def get_exploration_rate(self):
        """
        Retorna a taxa de exploração atual com base no número de jogos jogados.
        A taxa diminui com o aumento da experiência.
        """
        # Fase 1: Taxa não importa pois usa estratégia própria
        if self.games_played < 5:
            return 0.0
        
        # Fase 2: Exploração alta
        elif self.games_played < 15:
            return 0.7
        
        # Fase 3: Sem exploração
        else:
            return 0.0
    
    def adjust_learning_parameters(self):
        """Ajusta os parâmetros de aprendizado com base na fase atual"""
        # Fase 1: Burra
        if self.games_played < 5:
            self.alpha = 0.01  # Aprendizado mínimo
            self.gamma = 0.5   # Desconto baixo
        
        # Fase 2: Aleatória com aprendizado
        elif self.games_played < 15:
            self.alpha = 0.2   # Aprendizado alto
            self.gamma = 0.8   # Desconto moderado
        
        # Fase 3: Mestre
        else:
            self.alpha = 0.05  # Aprendizado refinado
            self.gamma = 0.95  # Desconto alto
    
    def get_q_value(self, state, action):
        """Retorna o valor Q para um par estado-ação"""
        if state in self.q_table and self.action_to_key(action) in self.q_table[state]:
            return self.q_table[state][self.action_to_key(action)]
        return 0.0  # Valor padrão para novos pares estado-ação
    
    def action_to_key(self, action):
        """Converte uma ação para uma chave hashable para a tabela Q"""
        origin, destination = action
        return (origin[0], origin[1], destination[0], destination[1])
    
    def save_model(self):
        """Salva o modelo atual em um arquivo"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            with open(self.model_path, 'wb') as f:
                data = {
                    'q_table': self.q_table,
                    'games_played': self.games_played,
                    'alpha': self.alpha,
                    'gamma': self.gamma,
                    'epsilon': self.epsilon
                }
                pickle.dump(data, f)
        except Exception:
            pass
    
    def load_model(self):
        """Carrega o modelo de um arquivo, se existir"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.q_table = data['q_table']
                    self.games_played = data['games_played']
                    self.alpha = data['alpha']
                    self.gamma = data['gamma']
                    self.epsilon = data['epsilon']
                    return True
        except Exception:
            self.q_table = {}
            self.games_played = 0
            return False
        
        return False
    
    def reset_model(self):
        """Reseta o modelo para começar o aprendizado do zero"""
        self.q_table = {}
        self.games_played = 0
        self.alpha = 0.01
        self.gamma = 0.5
        self.epsilon = 0.0
        self.state_history = []
        
        # Remove o arquivo de modelo, se existir
        try:
            if os.path.exists(self.model_path):
                os.remove(self.model_path)
        except Exception:
            pass
    
    def force_phase(self, phase):
        """Força a IA a entrar em uma fase específica de aprendizado"""
        if phase == 1:
            self.games_played = 0
        elif phase == 2:
            self.games_played = 6
        elif phase == 3:
            self.games_played = 16
        
        self.adjust_learning_parameters()
    
    def get_strength_description(self):
        """Retorna uma descrição da força atual da IA"""
        if self.games_played < 5:
            return f"Fase 1: Iniciante ({self.games_played}/5)"
        elif self.games_played < 15:
            return f"Fase 2: Intermediária ({self.games_played - 5}/10)"
        else:
            return f"Fase 3: Mestre ({self.games_played} jogos)"
    
    def evaluate_board(self, game, player):
        """
        Avalia o estado do tabuleiro para o jogador especificado.
        Retorna um valor numérico onde valores maiores são melhores.
        """
        score = 0
        opponent = 'b' if player == 'w' else 'w'
        
        # Valores das peças
        piece_values = {
            'p': 1,   # Peão
            'r': 5,   # Torre
            'q': 9,   # Rainha
            'k': 100  # Rei
        }
        
        # Avalia material e posição
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece == '.':
                    continue
                    
                piece_type = piece.lower()
                piece_color = game.get_piece_color(piece)
                
                # Valor base da peça
                value = piece_values[piece_type]
                
                # Ajusta o valor baseado na cor
                if piece_color == player:
                    score += value
                else:
                    score -= value
        
        # Bônus para posições que atacam o rei adversário
        opponent_king_pos = game.king_positions[opponent]
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.' and game.get_piece_color(piece) == player:
                    # Verifica se a peça pode atacar o rei
                    moves = game.get_basic_moves((row, col))
                    if opponent_king_pos in moves:
                        # Bônus maior para peças que podem dar xeque-mate
                        if game.is_check(opponent):
                            score += 50  # Bônus muito alto para posições de xeque-mate
                        else:
                            score += 20  # Bônus para atacar o rei
        
        # Penalidade para deixar o próprio rei em xeque
        if game.is_check(player):
            score -= 30
        
        return score
    
    def get_valid_moves_on_board(self, board, position, player):
        """
        Retorna movimentos válidos para peça em posição específica em tabuleiro simulado
        """
        row, col = position
        piece = board[row][col]
        
        if piece == '.' or self.get_piece_color(piece, board) != player:
            return []
        
        valid_moves = []
        piece_type = piece.lower()
        
        # Movimentos do peão
        if piece_type == 'p':
            direction = -1 if player == 'w' else 1
            
            # Movimento para frente
            new_row = row + direction
            if 0 <= new_row < 4 and board[new_row][col] == '.':
                valid_moves.append((new_row, col))
            
            # Captura diagonal
            for new_col in [col-1, col+1]:
                if 0 <= new_row < 4 and 0 <= new_col < 4 and board[new_row][new_col] != '.':
                    if self.get_piece_color(board[new_row][new_col], board) != player:
                        valid_moves.append((new_row, new_col))
        
        # Movimentos da torre
        elif piece_type == 'r':
            # Direções: horizontal e vertical
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            
            for dr, dc in directions:
                for i in range(1, 4):
                    new_row, new_col = row + i * dr, col + i * dc
                    
                    if not (0 <= new_row < 4 and 0 <= new_col < 4):
                        break
                    
                    if board[new_row][new_col] == '.':
                        valid_moves.append((new_row, new_col))
                    else:
                        if self.get_piece_color(board[new_row][new_col], board) != player:
                            valid_moves.append((new_row, new_col))
                        break
        
        # Movimentos da rainha
        elif piece_type == 'q':
            # Todas as direções
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                for i in range(1, 4):
                    new_row, new_col = row + i * dr, col + i * dc
                    
                    if not (0 <= new_row < 4 and 0 <= new_col < 4):
                        break
                    
                    if board[new_row][new_col] == '.':
                        valid_moves.append((new_row, new_col))
                    else:
                        if self.get_piece_color(board[new_row][new_col], board) != player:
                            valid_moves.append((new_row, new_col))
                        break
        
        # Movimentos do rei
        elif piece_type == 'k':
            # Todas as direções, mas apenas uma casa
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                
                if 0 <= new_row < 4 and 0 <= new_col < 4:
                    if board[new_row][new_col] == '.' or self.get_piece_color(board[new_row][new_col], board) != player:
                        valid_moves.append((new_row, new_col))
        
        return valid_moves
    
    def get_piece_color(self, piece, board):
        """Retorna a cor da peça ('w' ou 'b')"""
        if piece == '.':
            return None
        return 'w' if piece.isupper() else 'b' 