import numpy as np
import random
import pickle
import os
from copy import deepcopy
from minichess import MiniChess

class MiniChessAI:
    """
    IA para jogar MiniChess com capacidade de aprendizado de máquina.
    Utiliza um modelo de aprendizado por reforço avançado (Q-learning).
    """
    
    def __init__(self, learning_rate=0.3, discount_factor=0.9, exploration_rate=0.9):
        # Taxas mais altas para aprender mais rapidamente no início
        self.learning_rate = learning_rate  
        self.discount_factor = discount_factor  
        self.exploration_rate = exploration_rate  # Taxa de exploração inicial alta (90%)
        
        # Dicionário para armazenar valores Q: state -> {action -> value}
        self.q_values = {}
        
        # Histórico da partida atual
        self.game_history = []
        
        # Número de jogos jogados
        self.games_played = 0
        
        # Valores das peças para avaliação heurística
        self.piece_values = {
            'p': 1, 'P': 1,      # Peão
            'r': 5, 'R': 5,      # Torre
            'q': 9, 'Q': 9,      # Rainha
            'k': 100, 'K': 100   # Rei (valor alto para priorizar sua proteção)
        }
        
        # Fator de burrice aleatória (quanto maior, mais aleatória é a IA)
        self.random_mistake_factor = 0.8
        
        # Carregar modelo se existir
        self.load_model()
        
        # Ajustar exploration_rate e random_mistake_factor com base nos jogos jogados
        self.adjust_learning_parameters()
    
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
    
    def evaluate_board(self, game):
        """
        Avalia a posição do tabuleiro para o jogador atual (heurística).
        A sofisticação da avaliação aumenta com a experiência.
        """
        score = 0
        
        # Nível de sofisticação da avaliação com base na experiência
        sophistication = min(1.0, self.games_played / 50)
        
        # Contagem básica de material (sempre presente)
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.':
                    # Aplicamos um "erro de avaliação" proporcional à inexperiência
                    value = self.piece_values.get(piece, 0)
                    
                    # A IA iniciante às vezes não valoriza corretamente as peças
                    if random.random() < self.random_mistake_factor:
                        value = value * random.uniform(0.5, 1.5)
                    
                    if game.get_piece_color(piece) == 'b':  # Peça preta (IA)
                        score += value
                    else:  # Peça branca (humano)
                        score -= value
        
        # Avaliações mais sofisticadas surgem gradualmente com a experiência
        if sophistication > 0.2:
            # Bônus para posições centrais (para peças pretas)
            central_bonus = 0.5 * sophistication
            for row in range(1, 3):
                for col in range(1, 3):
                    piece = game.board[row][col]
                    if piece != '.' and game.get_piece_color(piece) == 'b':
                        score += central_bonus
        
        if sophistication > 0.5:
            # Penalização para rei em xeque (para ambos os lados)
            check_awareness = 3.0 * sophistication
            if game.is_check('b'):
                score -= check_awareness  # Penaliza a IA se estiver em xeque
            if game.is_check('w'):
                score += check_awareness  # Bonifica a IA se o oponente estiver em xeque
        
        # Normalização do score para evitar valores extremos
        return np.tanh(score * 0.1)
    
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
    
    def simulate_move(self, game, move):
        """
        Simula um movimento e retorna uma cópia do jogo após o movimento.
        """
        game_copy = deepcopy(game)
        game_copy.make_move(move)
        return game_copy
    
    def is_move_safe(self, game, move):
        """
        Verifica se um movimento é seguro, com análise proporcional à experiência.
        Uma IA inexperiente não consegue prever tão bem os perigos.
        """
        # A profundidade da análise de segurança depende da experiência
        safety_awareness = min(1.0, self.games_played / 40)
        
        # IAs inexperientes às vezes ignoram a segurança completamente
        if random.random() > safety_awareness:
            return True  # Falsa sensação de segurança
        
        # Simula o movimento
        game_after_move = self.simulate_move(game, move)
        
        # Verifica todas as possíveis respostas do oponente
        for opponent_move in self.get_valid_actions(game_after_move):
            # Simula a resposta do oponente
            game_after_opponent = self.simulate_move(game_after_move, opponent_move)
            
            # Se o rei da IA for capturado ou estiver em xeque-mate após a resposta, o movimento não é seguro
            if game_after_opponent.is_king_captured() == 'b' or game_after_opponent.is_checkmate():
                return False
            
            # IAs mais avançadas também se preocupam com a perda de peças valiosas
            if safety_awareness > 0.3:
                origin, dest = opponent_move
                dest_row, dest_col = dest
                captured_piece = game_after_move.board[dest_row][dest_col]
                
                if captured_piece != '.' and game_after_move.get_piece_color(captured_piece) == 'b':
                    piece_value = self.piece_values.get(captured_piece, 0)
                    if piece_value > 1:  # Se for mais valioso que um peão
                        return False
        
        return True
    
    def get_move(self, game):
        """
        Decide o próximo movimento com base no aprendizado atual e avaliação heurística.
        A qualidade da decisão aumenta com a experiência.
        """
        valid_actions = self.get_valid_actions(game)
        
        if not valid_actions:
            print("Nenhuma ação válida encontrada para a IA")
            return None
        
        # Chance de considerar a segurança aumenta com a experiência
        safety_consideration_chance = min(0.8, self.games_played / 50)
        
        # Filtrar por movimentos seguros conforme a experiência aumenta
        if random.random() < safety_consideration_chance:
            safe_actions = [move for move in valid_actions if self.is_move_safe(game, move)]
            if safe_actions:
                actions_to_consider = safe_actions
            else:
                actions_to_consider = valid_actions
        else:
            actions_to_consider = valid_actions
        
        # Estado atual do jogo
        state_key = self.get_state_key(game.get_state_representation())
        
        # Inicializa os valores Q para este estado se não existirem
        if state_key not in self.q_values:
            self.q_values[state_key] = {}
        
        # A IA inexperiente explora mais e comete mais erros aleatórios
        # Fase de exploração: escolhe ação aleatória com probabilidade exploration_rate
        if random.random() < self.exploration_rate:
            chosen_action = random.choice(actions_to_consider)
            print(f"IA explorando: Escolhendo ação {chosen_action}")
        else:
            # Fase de exploitação: escolhe a melhor ação conhecida, com potenciais erros
            best_value = float('-inf')
            best_actions = []
            
            for action in actions_to_consider:
                action_key = self.get_action_key(action)
                
                # Obtém o valor Q ou inicializa com heurística se não existir
                if action_key not in self.q_values[state_key]:
                    # Simula o movimento para avaliar a posição resultante
                    game_after_move = self.simulate_move(game, action)
                    # Inicializa com valor heurístico para guiar a aprendizagem inicial
                    self.q_values[state_key][action_key] = self.evaluate_board(game_after_move)
                
                value = self.q_values[state_key][action_key]
                
                # IAs mais experientes consideram fatores adicionais
                consideration_level = min(1.0, self.games_played / 50)
                
                if consideration_level > 0.3:
                    # Bônus para capturas e movimentos que dão xeque
                    origin, dest = action
                    dest_row, dest_col = dest
                    if game.board[dest_row][dest_col] != '.':  # É uma captura
                        captured_piece = game.board[dest_row][dest_col]
                        capture_value = self.piece_values.get(captured_piece, 0) * 0.1 * consideration_level
                        value += capture_value
                
                if consideration_level > 0.6:
                    # Verifica se o movimento dá xeque
                    game_after_move = self.simulate_move(game, action)
                    if game_after_move.is_check('w'):
                        value += 0.5 * consideration_level
                
                # IA inexperiente pode fazer erros na avaliação
                if random.random() < self.random_mistake_factor:
                    value = value * random.uniform(0.5, 1.5)
                
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
        Usa aprendizado por diferença temporal com recompensas intermediárias.
        """
        if not self.game_history:
            return
        
        # Incrementa o contador de jogos
        self.games_played += 1
        print(f"IA aprendendo do jogo {self.games_played} com recompensa final {reward}")
        
        # Atualiza os parâmetros de aprendizado (taxas de exploração, erro, etc.)
        self.adjust_learning_parameters()
        
        # Adiciona recompensas intermediárias baseadas em heurísticas
        enhanced_rewards = []
        
        # Reconstrói o jogo para avaliar cada estado
        sim_game = MiniChess()
        
        for i, (state_key, action_key) in enumerate(self.game_history):
            # Recria a ação a partir da chave
            origin = (action_key[0], action_key[1])
            destination = (action_key[2], action_key[3])
            action = (origin, destination)
            
            # Avalia o estado antes do movimento
            pre_move_score = self.evaluate_board(sim_game)
            
            # Executa o movimento
            sim_game.make_move(action)
            
            # Avalia o estado após o movimento
            post_move_score = self.evaluate_board(sim_game)
            
            # Calcula recompensa intermediária como a diferença de avaliação
            move_reward = post_move_score - pre_move_score
            
            # Recompensas ou penalidades específicas
            dest_row, dest_col = destination
            captured_piece = None
            
            # Verifica se foi uma captura
            if i > 0:  # Não há captura no primeiro movimento
                # Recupera a peça capturada do histórico do jogo
                prev_action = self.game_history[i-1][1]
                prev_dest = (prev_action[2], prev_action[3])
                if prev_dest == origin:  # Se o destino do movimento anterior é a origem deste, uma peça foi capturada
                    move_reward -= 2.0  # Penalidade por perder uma peça
            
            # Xeque ou xeque-mate são recompensados na função de recompensa final
            
            enhanced_rewards.append(move_reward)
        
        # Aplica a recompensa final para o último movimento
        if enhanced_rewards:
            enhanced_rewards[-1] = reward
        
        # Aplica o aprendizado para cada par estado-ação na história do jogo
        for i in range(len(self.game_history)):
            state_key, action_key = self.game_history[i]
            
            # Inicializa o valor Q se necessário
            if state_key not in self.q_values:
                self.q_values[state_key] = {}
            
            if action_key not in self.q_values[state_key]:
                self.q_values[state_key][action_key] = 0.0
            
            # Recompensa para este movimento
            move_reward = enhanced_rewards[i]
            
            # Próximo estado e melhor ação futura (para aprendizado TD)
            next_max_q = 0.0
            if i < len(self.game_history) - 1:
                next_state_key = self.game_history[i+1][0]
                
                if next_state_key in self.q_values and self.q_values[next_state_key]:
                    next_max_q = max(self.q_values[next_state_key].values())
            
            # Atualiza o valor Q para este par estado-ação usando a equação do Q-learning
            # Q(s,a) = Q(s,a) + alpha * [r + gamma * max(Q(s',a')) - Q(s,a)]
            current_q = self.q_values[state_key][action_key]
            
            # Taxa de aprendizado adaptativa: aprende mais rapidamente de erros
            effective_learning_rate = self.learning_rate
            if move_reward < 0:
                effective_learning_rate *= 1.5  # Aprende mais rápido de erros
            
            # Atualiza o valor Q
            self.q_values[state_key][action_key] = current_q + effective_learning_rate * (
                move_reward + self.discount_factor * next_max_q - current_q
            )
        
        # Limpa o histórico do jogo
        self.game_history = []
        
        # Salva o modelo após aprender
        self.save_model()
    
    def adjust_learning_parameters(self):
        """
        Ajusta todos os parâmetros de aprendizado de acordo com a experiência da IA.
        """
        # Ajusta a taxa de exploração (diminui com o tempo, mas não muito rápido)
        min_exploration_rate = 0.05  # Mínimo para continuar explorando um pouco
        decay_factor = 0.01  # Decaimento mais lento para uma progressão mais gradual
        self.exploration_rate = max(min_exploration_rate, 0.9 * np.exp(-decay_factor * self.games_played))
        
        # Ajusta o fator de "erro aleatório" (burrice)
        min_mistake_factor = 0.02  # Sempre haverá uma pequena chance de erro
        mistake_decay = 0.015  # Decaimento um pouco mais rápido que a exploração
        self.random_mistake_factor = max(min_mistake_factor, 0.8 * np.exp(-mistake_decay * self.games_played))
        
        # Ajusta a taxa de aprendizado (diminui gradualmente para estabilizar o aprendizado)
        min_learning_rate = 0.1
        lr_decay = 0.005  # Decaimento mais lento
        self.learning_rate = max(min_learning_rate, 0.3 * np.exp(-lr_decay * self.games_played))
        
        print(f"Parâmetros de aprendizado atualizados:")
        print(f"- Taxa de exploração: {self.exploration_rate:.3f}")
        print(f"- Fator de erro aleatório: {self.random_mistake_factor:.3f}")
        print(f"- Taxa de aprendizado: {self.learning_rate:.3f}")
    
    def save_model(self):
        """
        Salva o modelo Q-learning em um arquivo.
        """
        model_data = {
            'q_values': self.q_values,
            'games_played': self.games_played
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
        self.exploration_rate = 0.9
        self.random_mistake_factor = 0.8
        self.learning_rate = 0.3
        
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
        Agora com gradações mais suaves.
        """
        if self.games_played == 0:
            return "Completo iniciante (sem experiência)"
        elif self.games_played < 5:
            return "Muito iniciante"
        elif self.games_played < 10:
            return "Iniciante"
        elif self.games_played < 20:
            return "Básico (aprendendo)"
        elif self.games_played < 30:
            return "Básico (em evolução)"
        elif self.games_played < 45:
            return "Intermediário (iniciante)"
        elif self.games_played < 60:
            return "Intermediário"
        elif self.games_played < 80:
            return "Intermediário avançado"
        elif self.games_played < 100:
            return "Avançado"
        elif self.games_played < 130:
            return "Muito avançado"
        elif self.games_played < 170:
            return "Especialista"
        else:
            return f"Mestre ({self.games_played} jogos)" 