import numpy as np
import random
import pickle
import os
from copy import deepcopy

class MiniChessAI:
    """
    IA para jogar MiniChess com capacidade de aprendizado de máquina.
    Utiliza um modelo de aprendizado por reforço simples (Q-learning).
    """
    
    def __init__(self, learning_rate=0.3, discount_factor=0.95, exploration_rate=0.5):
        self.learning_rate = learning_rate  # Taxa de aprendizado (aumentada)
        self.discount_factor = discount_factor  # Fator de desconto para recompensas futuras (aumentado)
        self.exploration_rate = exploration_rate  # Taxa de exploração (vs. exploitação) (aumentada)
        
        # Dicionário para armazenar valores Q: state -> {action -> value}
        self.q_values = {}
        
        # Histórico da partida atual
        self.game_history = []
        
        # Número de jogos jogados
        self.games_played = 0
        
        # Carregar modelo se existir
        self.load_model()
    
    def get_state_key(self, game_state):
        """
        Converte o estado do jogo em uma chave hashable para o dicionário Q.
        """
        return tuple(game_state)
    
    def get_action_key(self, action):
        """
        Converte a ação em uma chave hashable.
        """
        return (
            action[0][0], action[0][1],  # Origem (linha, coluna)
            action[1][0], action[1][1]   # Destino (linha, coluna)
        )
    
    def get_valid_actions(self, game):
        """
        Retorna todas as ações válidas para o jogador atual.
        """
        valid_actions = []
        
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.' and game.get_piece_color(piece) == game.current_player:
                    origin = (row, col)
                    for dest_row, dest_col in game.get_valid_moves(origin):
                        valid_actions.append((origin, (dest_row, dest_col)))
        
        return valid_actions
    
    def evaluate_position(self, game):
        """
        Avalia uma posição de xadrez com base em heurísticas simples.
        Retorna um valor entre -1 e 1 (1 favorecendo o jogador atual).
        """
        # Valor das peças: peão=1, torre=5, rainha=9, rei=100
        piece_values = {'p': 1, 'r': 5, 'q': 9, 'k': 100}
        
        white_score = 0
        black_score = 0
        
        # Conta o valor material
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.':
                    value = piece_values[piece.lower()]
                    if piece.isupper():  # Peça branca
                        white_score += value
                    else:  # Peça preta
                        black_score += value
        
        # Posições do rei
        w_king_row, w_king_col = game.king_positions.get('w', (-1, -1))
        b_king_row, b_king_col = game.king_positions.get('b', (-1, -1))
        
        # Adiciona bônus para centralização dos reis na fase final
        if white_score + black_score < 30:  # Fase final do jogo
            # Centralização dos reis
            white_score += (0.1 * (1 - abs(w_king_row - 1.5) / 2))
            white_score += (0.1 * (1 - abs(w_king_col - 1.5) / 2))
            black_score += (0.1 * (1 - abs(b_king_row - 1.5) / 2))
            black_score += (0.1 * (1 - abs(b_king_col - 1.5) / 2))
        
        # Calcula a pontuação total relativa ao jogador atual
        if game.current_player == 'w':
            return (white_score - black_score) / max(white_score + black_score, 1)
        else:
            return (black_score - white_score) / max(white_score + black_score, 1)
    
    def get_move(self, game):
        """
        Decide o próximo movimento com base no aprendizado atual.
        Usa a estratégia epsilon-greedy: às vezes escolhe aleatoriamente para explorar.
        """
        valid_actions = self.get_valid_actions(game)
        
        if not valid_actions:
            print("Nenhuma ação válida encontrada para a IA")
            return None
        
        # Estado atual do jogo
        state_key = self.get_state_key(game.get_state_representation())
        
        # Inicializa os valores Q para este estado se não existirem
        if state_key not in self.q_values:
            self.q_values[state_key] = {}
        
        # Inicializa valores Q para ações não vistas antes com uma heurística
        for action in valid_actions:
            action_key = self.get_action_key(action)
            if action_key not in self.q_values[state_key]:
                # Simula a ação para avaliar
                temp_game = deepcopy(game)
                temp_game.make_move(action)
                
                # Avalia a nova posição
                evaluation = self.evaluate_position(temp_game)
                
                # Penaliza muito se a ação leva à captura do próprio rei
                if game.current_player == 'w' and temp_game.is_king_captured() == 'w':
                    evaluation = -1.0
                elif game.current_player == 'b' and temp_game.is_king_captured() == 'b':
                    evaluation = -1.0
                
                # Premia se captura o rei do oponente
                if game.current_player == 'w' and temp_game.is_king_captured() == 'b':
                    evaluation = 1.0
                elif game.current_player == 'b' and temp_game.is_king_captured() == 'w':
                    evaluation = 1.0
                
                self.q_values[state_key][action_key] = evaluation
        
        # Fase de exploração: escolhe ação aleatória com probabilidade epsilon
        if random.random() < self.exploration_rate:
            # Mesmo na exploração, evita movimentos suicidas
            non_suicidal_actions = []
            for action in valid_actions:
                temp_game = deepcopy(game)
                temp_game.make_move(action)
                if not (game.current_player == 'w' and temp_game.is_king_captured() == 'w') and \
                   not (game.current_player == 'b' and temp_game.is_king_captured() == 'b'):
                    non_suicidal_actions.append(action)
            
            if non_suicidal_actions:
                chosen_action = random.choice(non_suicidal_actions)
            else:
                chosen_action = random.choice(valid_actions)
            print(f"IA explorando: Escolhendo ação aleatória {chosen_action}")
        else:
            # Fase de exploitação: escolhe a melhor ação conhecida
            # Escolhe a ação com o maior valor Q conhecido
            best_value = float('-inf')
            best_actions = []
            
            for action in valid_actions:
                action_key = self.get_action_key(action)
                value = self.q_values[state_key].get(action_key, 0.0)
                
                if value > best_value:
                    best_value = value
                    best_actions = [action]
                elif value == best_value:
                    best_actions.append(action)
            
            chosen_action = random.choice(best_actions)  # Desempate aleatório
            print(f"IA aproveitando conhecimento: Escolhendo melhor ação {chosen_action} com valor Q {best_value}")
        
        # Registra o estado e a ação para aprendizado posterior
        self.game_history.append((state_key, self.get_action_key(chosen_action)))
        
        return chosen_action
    
    def learn(self, game, reward):
        """
        Atualiza os valores Q com base na recompensa recebida ao final do jogo.
        """
        if not self.game_history:
            return
        
        # Incrementa o contador de jogos
        self.games_played += 1
        print(f"IA aprendendo do jogo {self.games_played} com recompensa {reward}")
        
        # Atualiza a taxa de exploração (diminui com o tempo)
        self.adjust_exploration_rate()
        
        # Ajusta a taxa de aprendizado com base na experiência
        self.adjust_learning_rate()
        
        # Aplica o aprendizado para cada par estado-ação na história do jogo
        # Usa a técnica de Temporal Difference (TD) Learning com recompensa exponencialmente crescente
        for i in range(len(self.game_history) - 1, -1, -1):
            state_key, action_key = self.game_history[i]
            
            # Inicializa o valor Q se necessário
            if state_key not in self.q_values:
                self.q_values[state_key] = {}
            
            if action_key not in self.q_values[state_key]:
                self.q_values[state_key][action_key] = 0.0
            
            # Aplica uma recompensa mais forte para movimentos mais recentes
            # e mais fraca para movimentos mais antigos
            move_reward = reward * (self.discount_factor ** (len(self.game_history) - 1 - i))
            
            # Atualiza o valor Q para este par estado-ação
            # Q(s,a) = Q(s,a) + alpha * [reward + gamma * max(Q(s',a')) - Q(s,a)]
            # Simplificando para jogos terminais, onde não há próximo estado:
            # Q(s,a) = Q(s,a) + alpha * [reward - Q(s,a)]
            current_q = self.q_values[state_key][action_key]
            self.q_values[state_key][action_key] = current_q + self.learning_rate * (move_reward - current_q)
        
        # Limpa o histórico do jogo
        self.game_history = []
        
        # Salva o modelo após aprender
        self.save_model()
    
    def adjust_exploration_rate(self):
        """
        Reduz a taxa de exploração à medida que a IA joga mais jogos.
        """
        min_exploration_rate = 0.1  # Nunca deixa de explorar completamente
        # Decaimento mais lento para permitir mais exploração
        self.exploration_rate = max(min_exploration_rate, 0.5 * np.exp(-0.005 * self.games_played))
        print(f"Nova taxa de exploração: {self.exploration_rate:.3f}")
    
    def adjust_learning_rate(self):
        """
        Ajusta a taxa de aprendizado com base no número de jogos jogados.
        """
        min_learning_rate = 0.1
        self.learning_rate = max(min_learning_rate, 0.3 * np.exp(-0.01 * self.games_played))
    
    def save_model(self):
        """
        Salva o modelo Q-learning em um arquivo.
        """
        model_data = {
            'q_values': self.q_values,
            'games_played': self.games_played,
            'learning_rate': self.learning_rate,
            'exploration_rate': self.exploration_rate
        }
        
        try:
            with open('models/minichess_ai_model.pkl', 'wb') as f:
                pickle.dump(model_data, f)
            print(f"Modelo da IA salvo com sucesso! Jogos jogados: {self.games_played}")
        except Exception as e:
            print(f"Erro ao salvar o modelo: {e}")
    
    def load_model(self):
        """
        Carrega o modelo Q-learning de um arquivo.
        """
        try:
            if os.path.exists('models/minichess_ai_model.pkl'):
                with open('models/minichess_ai_model.pkl', 'rb') as f:
                    model_data = pickle.load(f)
                
                self.q_values = model_data['q_values']
                self.games_played = model_data['games_played']
                
                # Carrega taxas de aprendizado e exploração se disponíveis
                if 'learning_rate' in model_data:
                    self.learning_rate = model_data['learning_rate']
                if 'exploration_rate' in model_data:
                    self.exploration_rate = model_data['exploration_rate']
                else:
                    # Ajusta a taxa de exploração com base nos jogos jogados
                    self.adjust_exploration_rate()
                
                print(f"Modelo da IA carregado com sucesso! Jogos jogados: {self.games_played}")
            else:
                print("Nenhum modelo encontrado. Iniciando com um novo modelo.")
        except Exception as e:
            print(f"Erro ao carregar o modelo: {e}")
    
    def reset_model(self):
        """
        Reinicia o modelo da IA.
        """
        self.q_values = {}
        self.game_history = []
        self.games_played = 0
        self.learning_rate = 0.3
        self.exploration_rate = 0.5
        
        # Remove o arquivo do modelo antigo
        if os.path.exists('models/minichess_ai_model.pkl'):
            try:
                os.remove('models/minichess_ai_model.pkl')
                print("Modelo anterior removido.")
            except Exception as e:
                print(f"Erro ao remover o modelo anterior: {e}")
        
        print("Modelo da IA resetado. A IA começará a aprender do zero.")
    
    def get_strength_description(self):
        """
        Retorna uma descrição do nível de força da IA com base em quantos jogos ela já jogou.
        """
        if self.games_played < 10:
            return "Iniciante (aprendendo)"
        elif self.games_played < 50:
            return "Básico"
        elif self.games_played < 100:
            return "Intermediário"
        elif self.games_played < 200:
            return "Avançado"
        else:
            return f"Mestre ({self.games_played} jogos)" 