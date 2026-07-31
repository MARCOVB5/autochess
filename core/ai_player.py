import os
import random
import pickle
from copy import deepcopy
import numpy as np

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
        self.alpha = alpha  # Taxa de aprendizado
        self.gamma = gamma  # Fator de desconto
        self.epsilon = epsilon  # Taxa de exploração
        
        self.q_table = {}
        
        self.state_history = []
        
        self.games_played = 0
        
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
        current_state = game.get_state_representation()
        
        # Fase 1: escolhe deliberadamente jogadas ruins para demonstrar evolução.
        if self.games_played < 5:
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
            
            king_in_check = game.is_check(game.current_player)
            
            if king_in_check:
                king_position = game.king_positions[game.current_player]
                king_moves = []
                other_moves = []
                
                for move in valid_moves:
                    origin, _ = move
                    if origin == king_position:
                        king_moves.append(move)
                    else:
                        other_moves.append(move)
                
                if other_moves:
                    return self.get_worst_move(game, other_moves)
                
                if king_moves:
                    return self.get_worst_move(game, king_moves)
            else:
                return self.get_worst_move(game, valid_moves)
                
            return None
        # Fase 2: Q-learning com exploração alta.
        elif self.games_played < 15:
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
                
            if random.uniform(0, 1) < 0.7:  # 70% de chance de movimento aleatório
                chosen_move = random.choice(valid_moves)
            else:
                chosen_move = self.get_qlearning_move(game, current_state, valid_moves)
        # Fase 3: usa somente a melhor avaliação conhecida.
        else:
            valid_moves = game.get_all_valid_moves(game.current_player)
            
            if not valid_moves:
                return None
                
            chosen_move = self.get_best_move(game, valid_moves, current_state)
        
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
                    origin = (row, col)
                    
                    original_player = game.current_player
                    
                    basic_moves = game.get_basic_moves(origin)
                    
                    for dest in basic_moves:
                        all_moves.append((origin, dest))
                    
                    game.current_player = original_player
        
        return all_moves
    
    def get_worst_move(self, game, valid_moves):
        """
        Escolhe o pior movimento possível (para fase 1)
        Prioriza sacrificar peças valiosas e fazer movimentos ruins
        """
        if not valid_moves:
            return None
            
        move_evaluations = []
        
        is_phase_1 = self.games_played < 5
        king_position = game.king_positions[game.current_player]
        king_in_check = game.is_check(game.current_player)
        
        for move in valid_moves:
            origin, dest = move
            origin_row, origin_col = origin
            piece = game.board[origin_row][origin_col]
            piece_type = piece.lower()
            
            score = 0
            
            if is_phase_1 and king_in_check and origin == king_position:
                score += 500
            
            sim_game = deepcopy(game)
            sim_game.make_move(move)
            
            if piece_type == 'q':  # Rainha
                score -= 350  # Aumenta ainda mais para priorizar sacrificar a rainha
            elif piece_type == 'k' and not king_in_check:  # Rei (quando não está em xeque)
                score -= 200  # Mover o rei (desde que legal) ainda é ruim
            elif piece_type == 'r':  # Torre
                score -= 250  # Aumenta para priorizar sacrificar torres
            
            dest_row, dest_col = dest
            piece_under_attack = False
            
            for r in range(4):
                for c in range(4):
                    enemy_piece = sim_game.board[r][c]
                    if enemy_piece == '.' or sim_game.get_piece_color(enemy_piece) == game.current_player:
                        continue
                    
                    try:
                        enemy_moves = sim_game.get_basic_moves((r, c))
                        if (dest_row, dest_col) in enemy_moves:
                            piece_under_attack = True
                            if piece_type == 'q':
                                score -= 400  # Sacrificar a rainha é o pior movimento possível
                            elif piece_type == 'r':
                                score -= 300  # Sacrificar a torre é o segundo pior
                            else:
                                score -= 200  # Sacrificar peão ou deixar o rei em perigo
                            break
                    except:
                        continue
                if piece_under_attack:
                    break
            
            if game.board[dest_row][dest_col] != '.':
                score += 250  # Aumenta a pontuação (tornando o movimento menos atraente)
            
            if game.board[dest_row][dest_col] != '.' and game.get_piece_color(game.board[dest_row][dest_col]) != game.current_player:
                score += 300
            
            try:
                board_score = self.evaluate_board(sim_game, game.current_player)
                score -= board_score  # Subtraímos o score do tabuleiro para piorar a posição
            except:
                pass
            
            move_evaluations.append((move, score))
        
        if move_evaluations:
            move_evaluations.sort(key=lambda x: x[1])
            worst_moves = [move for move, _ in move_evaluations[:min(3, len(move_evaluations))]]
            return random.choice(worst_moves)
        
        return random.choice(valid_moves)
    
    def get_qlearning_move(self, game, current_state, valid_moves):
        """Escolhe um movimento baseado no Q-Learning (para fase 2)"""
        if random.uniform(0, 1) < 0.7:
            return random.choice(valid_moves)
        
        q_values = []
        
        for move in valid_moves:
            q_value = self.get_q_value(current_state, move)
            q_values.append((move, q_value))
        
        chosen_move = max(q_values, key=lambda x: x[1])[0]
        return chosen_move
    
    def get_best_move(self, game, valid_moves, current_state):
        """Escolhe o melhor movimento possível (para fase 3)"""
        move_evaluations = []
        
        for move in valid_moves:
            sim_game = deepcopy(game)
            sim_game.make_move(move)
            
            evaluation = self.evaluate_board(sim_game, game.current_player)
            
            q_value = self.get_q_value(current_state, move)
            
            final_score = evaluation
            
            move_evaluations.append((move, final_score))
        
        return max(move_evaluations, key=lambda x: x[1])[0]
    
    def learn(self, game, reward):
        """
        Atualiza a tabela Q com base no histórico de estados e na recompensa final.
        
        Args:
            game: Objeto MiniChess após o término da partida
            reward: Recompensa final (1.0 para vitória, -1.0 para derrota, 0.0 para empate)
        """
        self.games_played += 1
        
        self.adjust_learning_parameters()
        
        if not self.state_history:
            return
        
        # A recompensa final é propagada do último estado para o primeiro.
        for state, action in reversed(self.state_history):
            current_q = self.get_q_value(state, action)
            
            # Atualização temporal do valor estado-ação.
            updated_q = current_q + self.alpha * (reward - current_q)
            
            if state not in self.q_table:
                self.q_table[state] = {}
            
            self.q_table[state][self.action_to_key(action)] = updated_q
            
            reward = self.gamma * reward
        
        self.state_history = []
        
        if self.games_played % 5 == 0:
            self.save_model()
    
    def get_exploration_rate(self):
        """
        Retorna a taxa de exploração atual com base no número de jogos jogados.
        A taxa diminui com o aumento da experiência.
        """
        if self.games_played < 5:
            return 0.0
        
        elif self.games_played < 15:
            return 0.7
        
        else:
            return 0.0
    
    def adjust_learning_parameters(self):
        """Ajusta os parâmetros de aprendizado com base na fase atual"""
        if self.games_played < 5:
            self.alpha = 0.01  # Aprendizado mínimo
            self.gamma = 0.5   # Desconto baixo
        
        elif self.games_played < 15:
            self.alpha = 0.2   # Aprendizado alto
            self.gamma = 0.8   # Desconto moderado
        
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
        
        piece_values = {
            'p': 1,   # Peão
            'r': 5,   # Torre
            'q': 9,   # Rainha
            'k': 100  # Rei
        }
        
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece == '.':
                    continue
                    
                piece_type = piece.lower()
                piece_color = game.get_piece_color(piece)
                
                value = piece_values[piece_type]
                
                if piece_color == player:
                    score += value
                else:
                    score -= value
        
        opponent_king_pos = game.king_positions[opponent]
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.' and game.get_piece_color(piece) == player:
                    moves = game.get_basic_moves((row, col))
                    if opponent_king_pos in moves:
                        if game.is_check(opponent):
                            score += 50  # Bônus muito alto para posições de xeque-mate
                        else:
                            score += 20  # Bônus para atacar o rei
        
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
        
        if piece_type == 'p':
            direction = -1 if player == 'w' else 1
            
            new_row = row + direction
            if 0 <= new_row < 4 and board[new_row][col] == '.':
                valid_moves.append((new_row, col))
            
            for new_col in [col-1, col+1]:
                if 0 <= new_row < 4 and 0 <= new_col < 4 and board[new_row][new_col] != '.':
                    if self.get_piece_color(board[new_row][new_col], board) != player:
                        valid_moves.append((new_row, new_col))
        
        elif piece_type == 'r':
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
        
        elif piece_type == 'q':
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
        
        elif piece_type == 'k':
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
