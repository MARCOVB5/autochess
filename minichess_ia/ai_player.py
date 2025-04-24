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
    
    def __init__(self, learning_rate=0.5, discount_factor=0.97, exploration_rate=0.4):
        self.learning_rate = learning_rate  # Taxa de aprendizado aumentada
        self.discount_factor = discount_factor  # Fator de desconto aumentado para valorizar mais recompensas futuras
        self.exploration_rate = exploration_rate  # Taxa de exploração
        
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
    
    def evaluate_board(self, game):
        """
        Avalia a posição do tabuleiro para o jogador atual (heurística).
        Retorna um valor positivo se for bom para as pretas (IA) e negativo se for bom para as brancas.
        """
        score = 0
        
        # Contagem de material
        for row in range(4):
            for col in range(4):
                piece = game.board[row][col]
                if piece != '.':
                    value = self.piece_values.get(piece, 0)
                    if game.get_piece_color(piece) == 'b':  # Peça preta (IA)
                        score += value
                    else:  # Peça branca (humano)
                        score -= value
        
        # Bônus para posições centrais (para peças pretas)
        for row in range(1, 3):
            for col in range(1, 3):
                piece = game.board[row][col]
                if piece != '.':
                    if game.get_piece_color(piece) == 'b':  # Peça preta (IA)
                        score += 0.8  # Bônus maior para peças no centro
                    else:  # Peça branca (humano)
                        score -= 0.8  # Penalidade para peças brancas no centro
        
        # Recompensa mobilidade - quanto mais movimentos possíveis, melhor
        valid_black_moves = len(game.get_all_valid_moves('b'))
        valid_white_moves = len(game.get_all_valid_moves('w'))
        score += 0.2 * (valid_black_moves - valid_white_moves)
        
        # Penalização para rei em xeque (para ambos os lados)
        if game.is_check('b'):
            score -= 5  # Penaliza mais a IA se estiver em xeque
        if game.is_check('w'):
            score += 5  # Bonifica mais a IA se o oponente estiver em xeque
        
        # Bônus para peões avançados (pretas avançam para linha 0)
        for col in range(4):
            for row in range(4):
                piece = game.board[row][col]
                if piece == 'p':  # Peão preto
                    # Quanto mais próximo da linha 0, melhor
                    score += (3 - row) * 0.7
                elif piece == 'P':  # Peão branco
                    # Quanto mais próximo da linha 3, melhor para as brancas
                    score -= row * 0.7
        
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
        Verifica se um movimento é seguro (não resulta na captura imediata de uma peça valiosa).
        """
        # Simula o movimento
        game_after_move = self.simulate_move(game, move)
        
        # Verifica todas as possíveis respostas do oponente
        for opponent_move in self.get_valid_actions(game_after_move):
            # Simula a resposta do oponente
            game_after_opponent = self.simulate_move(game_after_move, opponent_move)
            
            # Se o rei da IA for capturado ou estiver em xeque-mate após a resposta, o movimento não é seguro
            if game_after_opponent.is_king_captured() == 'b' or game_after_opponent.is_checkmate():
                return False
            
            # Se uma peça valiosa for capturada na resposta
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
        Usa a estratégia epsilon-greedy com preferência por movimentos seguros.
        """
        valid_actions = self.get_valid_actions(game)
        
        if not valid_actions:
            print("Nenhuma ação válida encontrada para a IA")
            return None
        
        # Filtra por movimentos seguros se possível
        safe_actions = [move for move in valid_actions if self.is_move_safe(game, move)]
        
        # Se houver movimentos seguros, prefere-os, mas mantém alguns movimentos não seguros para exploração
        if safe_actions and random.random() > 0.2:  # 80% de chance de escolher apenas entre movimentos seguros
            actions_to_consider = safe_actions
        else:
            actions_to_consider = valid_actions
        
        # Estado atual do jogo
        state_key = self.get_state_key(game.get_state_representation())
        
        # Inicializa os valores Q para este estado se não existirem
        if state_key not in self.q_values:
            self.q_values[state_key] = {}
        
        # Fase de exploração: escolhe ação aleatória com probabilidade epsilon
        if random.random() < self.exploration_rate:
            chosen_action = random.choice(actions_to_consider)
            print(f"IA explorando: Escolhendo ação {chosen_action}")
        else:
            # Fase de exploitação: escolhe a melhor ação conhecida
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
                
                # Bônus para capturas e movimentos que dão xeque
                origin, dest = action
                dest_row, dest_col = dest
                if game.board[dest_row][dest_col] != '.':  # É uma captura
                    captured_piece = game.board[dest_row][dest_col]
                    capture_value = self.piece_values.get(captured_piece, 0) * 0.1
                    value += capture_value  # Bônus para capturas proporcionais ao valor da peça
                
                # Verifica se o movimento dá xeque
                game_after_move = self.simulate_move(game, action)
                if game_after_move.is_check('w'):
                    value += 0.5  # Bônus para movimentos que dão xeque
                
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
        
        # Atualiza a taxa de exploração (diminui com o tempo)
        self.adjust_exploration_rate()
        
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
            
            # Amplifica recompensas nas primeiras partidas para acelerar o aprendizado
            if self.games_played < 5:
                move_reward *= 1.5  # Amplificação de 50% nas primeiras partidas
            
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
            # Amplifica a recompensa final nas primeiras partidas
            if self.games_played < 10:
                enhanced_rewards[-1] *= 1.5
        
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
            
            # Aprendizado acelerado nas primeiras partidas
            if self.games_played < 5:
                effective_learning_rate *= 1.3
            
            # Atualiza o valor Q
            self.q_values[state_key][action_key] = current_q + effective_learning_rate * (
                move_reward + self.discount_factor * next_max_q - current_q
            )
        
        # Limpa o histórico do jogo
        self.game_history = []
        
        # Salva o modelo após aprender
        self.save_model()
    
    def adjust_exploration_rate(self):
        """
        Reduz a taxa de exploração à medida que a IA joga mais jogos.
        Mantém um mínimo de exploração para continuar descobrindo novas estratégias.
        """
        min_exploration_rate = 0.03  # Mínimo mais baixo para explorar menos quando mais experiente
        decay_factor = 0.08  # Decaimento mais rápido
        self.exploration_rate = max(min_exploration_rate, 0.4 * np.exp(-decay_factor * self.games_played))
        print(f"Nova taxa de exploração: {self.exploration_rate:.3f}")
    
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
        self.exploration_rate = 0.4
        
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
        if self.games_played < 3:
            return "Iniciante (aprendendo)"
        elif self.games_played < 5:
            return "Básico"
        elif self.games_played < 8:
            return "Intermediário"
        elif self.games_played < 10:
            return "Avançado"
        else:
            return f"Mestre ({self.games_played} jogos)" 
