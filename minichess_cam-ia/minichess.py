import numpy as np
from copy import deepcopy

class MiniChess:
    """
    Implementação de um jogo de MiniChess 4x4.
    """
    
    def __init__(self):
        # Inicializa um tabuleiro 4x4
        # Notação: maiúsculas para peças brancas, minúsculas para pretas
        # Peças: R=torre, Q=rainha, K=rei, P=peão
        # '.' representa uma casa vazia
        self.board = [
            ['r', 'q', 'k', 'r'], 
            ['p', 'p', 'p', 'p'],
            ['P', 'P', 'P', 'P'],
            ['R', 'K', 'Q', 'R']
        ]
        
        # O jogador branco começa
        self.current_player = 'w'
        
        # Histórico de movimentos para análise
        self.move_history = []
        
        # Posições dos reis para verificação de xeque-mate
        self.king_positions = {
            'w': (3, 1),  # Posição inicial do rei branco (linha, coluna)
            'b': (0, 2)   # Posição inicial do rei preto (linha, coluna)
        }
        
    def get_piece_color(self, piece):
        """Retorna a cor da peça ('w' para brancas, 'b' para pretas)"""
        if piece == '.':
            return None
        return 'w' if piece.isupper() else 'b'
    
    def is_valid_position(self, row, col):
        """Verifica se a posição está dentro do tabuleiro"""
        return 0 <= row < 4 and 0 <= col < 4
    
    def get_valid_moves(self, position):
        """
        Retorna todos os movimentos válidos para a peça na posição dada
        """
        row, col = position
        piece = self.board[row][col]
        
        # Se não há peça na posição ou se a peça não pertence ao jogador atual
        if piece == '.':
            return []
        if self.get_piece_color(piece) != self.current_player:
            return []
        
        valid_moves = []
        piece_type = piece.lower()
        
        # Movimentos do peão
        if piece_type == 'p':
            direction = -1 if self.current_player == 'w' else 1
            
            # Movimento para frente
            new_row = row + direction
            if self.is_valid_position(new_row, col) and self.board[new_row][col] == '.':
                valid_moves.append((new_row, col))
            
            # Captura diagonal
            for new_col in [col-1, col+1]:
                if self.is_valid_position(new_row, new_col) and self.board[new_row][new_col] != '.':
                    if self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                        valid_moves.append((new_row, new_col))
        
        # Movimentos da torre
        elif piece_type == 'r':
            # Direções: horizontal e vertical
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            
            for dr, dc in directions:
                for i in range(1, 4):  # No máximo 3 casas em um tabuleiro 4x4
                    new_row, new_col = row + i * dr, col + i * dc
                    
                    if not self.is_valid_position(new_row, new_col):
                        break
                    
                    if self.board[new_row][new_col] == '.':
                        valid_moves.append((new_row, new_col))
                    else:
                        if self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                            valid_moves.append((new_row, new_col))
                        break
        
        # Movimentos da rainha (combinação de torre e movimento diagonal)
        elif piece_type == 'q':
            # Todas as direções (horizontal, vertical e diagonal)
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                for i in range(1, 4):  # No máximo 3 casas em um tabuleiro 4x4
                    new_row, new_col = row + i * dr, col + i * dc
                    
                    if not self.is_valid_position(new_row, new_col):
                        break
                    
                    if self.board[new_row][new_col] == '.':
                        valid_moves.append((new_row, new_col))
                    else:
                        if self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                            valid_moves.append((new_row, new_col))
                        break
        
        # Movimentos do rei
        elif piece_type == 'k':
            # Todas as direções, mas apenas uma casa
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                
                if self.is_valid_position(new_row, new_col):
                    if self.board[new_row][new_col] == '.' or self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                        valid_moves.append((new_row, new_col))
        
        # Não mais filtrar os movimentos que deixariam o rei em xeque
        # Isso permite que o rei se mova para posições onde estaria em xeque
        return valid_moves
    
    def make_move(self, move):
        """
        Executa um movimento no formato ((origem_linha, origem_coluna), (destino_linha, destino_coluna))
        Retorna True se o movimento foi bem-sucedido, False caso contrário
        """
        origin, destination = move
        orig_row, orig_col = origin
        dest_row, dest_col = destination
        
        # Verifica se a origem e o destino são posições válidas
        if not (self.is_valid_position(orig_row, orig_col) and self.is_valid_position(dest_row, dest_col)):
            return False
        
        # Verifica se há uma peça na posição de origem
        piece = self.board[orig_row][orig_col]
        if piece == '.':
            return False
        
        # Verifica se a peça pertence ao jogador atual
        if self.get_piece_color(piece) != self.current_player:
            return False
        
        # Verifica se o movimento é válido
        valid_moves = self.get_valid_moves((orig_row, orig_col))
        if (dest_row, dest_col) not in valid_moves:
            print(f"Movimento inválido: ({orig_row},{orig_col}) -> ({dest_row},{dest_col})")
            print(f"Movimentos válidos para esta peça: {valid_moves}")
            return False
        
        # Captura a peça no destino, se houver
        captured_piece = self.board[dest_row][dest_col]
        
        # Executa o movimento
        self.board[dest_row][dest_col] = piece
        self.board[orig_row][orig_col] = '.'
        
        # Atualiza a posição do rei, se necessário
        if piece.lower() == 'k':
            self.king_positions[self.current_player] = (dest_row, dest_col)
        
        # Registra o movimento no histórico
        self.move_history.append((move, piece, captured_piece))
        
        # Troca o jogador atual
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        
        return True
    
    def make_move_without_validation(self, move):
        """
        Executa um movimento sem validações (usado internamente)
        """
        origin, destination = move
        orig_row, orig_col = origin
        dest_row, dest_col = destination
        
        piece = self.board[orig_row][orig_col]
        
        # Atualiza a posição do rei, se necessário
        if piece.lower() == 'k':
            self.king_positions[self.get_piece_color(piece)] = (dest_row, dest_col)
        
        # Executa o movimento
        self.board[dest_row][dest_col] = piece
        self.board[orig_row][orig_col] = '.'
        
        # Troca o jogador atual
        self.current_player = 'b' if self.current_player == 'w' else 'w'
    
    def is_check(self, player):
        """
        Verifica se o jogador está em xeque
        """
        king_row, king_col = self.king_positions[player]
        opponent = 'b' if player == 'w' else 'w'
        
        # Verifica se alguma peça do oponente pode atacar o rei
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == opponent:
                    # Peão
                    if piece.lower() == 'p':
                        direction = -1 if opponent == 'w' else 1
                        if row + direction == king_row and (col - 1 == king_col or col + 1 == king_col):
                            print(f"Xeque por peão! Peão em ({row},{col}) atacando rei em ({king_row},{king_col})")
                            return True
                    
                    # Torre
                    elif piece.lower() == 'r':
                        # Mesma linha
                        if row == king_row:
                            blocked = False
                            for c in range(min(col, king_col) + 1, max(col, king_col)):
                                if self.board[row][c] != '.':
                                    blocked = True
                                    break
                            if not blocked:
                                print(f"Xeque horizontal! Torre em ({row},{col}) atacando rei em ({king_row},{king_col})")
                                return True
                        
                        # Mesma coluna
                        elif col == king_col:
                            blocked = False
                            for r in range(min(row, king_row) + 1, max(row, king_row)):
                                if self.board[r][col] != '.':
                                    blocked = True
                                    break
                            if not blocked:
                                print(f"Xeque vertical! Torre em ({row},{col}) atacando rei em ({king_row},{king_col})")
                                return True
                    
                    # Rainha
                    elif piece.lower() == 'q':
                        # Movimentos horizontais/verticais (como torre)
                        if row == king_row:  # Mesma linha
                            blocked = False
                            for c in range(min(col, king_col) + 1, max(col, king_col)):
                                if self.board[row][c] != '.':
                                    blocked = True
                                    break
                            if not blocked:
                                print(f"Xeque horizontal! Rainha em ({row},{col}) atacando rei em ({king_row},{king_col})")
                                return True
                        
                        elif col == king_col:  # Mesma coluna
                            blocked = False
                            for r in range(min(row, king_row) + 1, max(row, king_row)):
                                if self.board[r][col] != '.':
                                    blocked = True
                                    break
                            if not blocked:
                                print(f"Xeque vertical! Rainha em ({row},{col}) atacando rei em ({king_row},{king_col})")
                                return True
                        
                        # Movimentos diagonais
                        elif abs(row - king_row) == abs(col - king_col):  # Está em diagonal
                            dr = 1 if king_row > row else -1
                            dc = 1 if king_col > col else -1
                            
                            blocked = False
                            r, c = row + dr, col + dc
                            
                            # Percorre a diagonal até atingir o rei
                            while r != king_row and c != king_col:
                                if not (0 <= r < 4 and 0 <= c < 4):
                                    blocked = True  # Fora dos limites
                                    break
                                    
                                if self.board[r][c] != '.':
                                    blocked = True  # Peça no caminho
                                    break
                                    
                                r += dr
                                c += dc
                            
                            # Se chegou até aqui sem bloqueios, é xeque
                            if not blocked:
                                print(f"Xeque diagonal! Rainha em ({row},{col}) atacando rei em ({king_row},{king_col})")
                                return True
                    
                    # Rei (adjacente)
                    elif piece.lower() == 'k':
                        if abs(row - king_row) <= 1 and abs(col - king_col) <= 1:
                            print(f"Xeque pelo rei! Rei em ({row},{col}) atacando rei em ({king_row},{king_col})")
                            return True
        
        return False
    
    def print_board(self):
        """
        Imprime o tabuleiro no console para depuração
        """
        print("\n  0 1 2 3")
        print(" +-+-+-+-+")
        for row in range(4):
            print(f"{row}|", end="")
            for col in range(4):
                print(f"{self.board[row][col]}|", end="")
            print("\n +-+-+-+-+")
        print(f"Jogador atual: {'Brancas' if self.current_player == 'w' else 'Pretas'}")
        print(f"Rei branco: {self.king_positions['w']}")
        print(f"Rei preto: {self.king_positions['b']}")
        print(f"Xeque para brancas: {self.is_check('w')}")
        print(f"Xeque para pretas: {self.is_check('b')}")
        print("\n")
    
    def is_checkmate(self):
        """
        Verifica se o jogador atual está em xeque-mate
        """
        player = self.current_player
        
        # Se não estiver em xeque, não pode ser xeque-mate
        if not self.is_check(player):
            return False
        
        print(f"Jogador {player} está em xeque, verificando xeque-mate...")
        self.print_board()
        
        # Verifica se há algum movimento válido para qualquer peça
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == player:
                    valid_moves = self.get_valid_moves((row, col))
                    if valid_moves:
                        print(f"Peça {piece} em ({row},{col}) tem os movimentos: {valid_moves} que evitam xeque-mate")
                        return False
        
        # Se nenhum movimento é possível enquanto estiver em xeque, é xeque-mate
        print(f"Xeque-mate confirmado para o jogador {player}")
        return True
    
    def is_king_captured(self):
        """
        Verifica se algum rei foi capturado
        """
        # Conta os reis no tabuleiro
        white_king_found = False
        black_king_found = False
        
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece == 'K':
                    white_king_found = True
                elif piece == 'k':
                    black_king_found = True
        
        # Se algum rei não foi encontrado, ele foi capturado
        if not white_king_found:
            print("O rei branco foi capturado! Vitória das pretas.")
            return 'b'  # Pretas venceram
        elif not black_king_found:
            print("O rei preto foi capturado! Vitória das brancas.")
            return 'w'  # Brancas venceram
        
        return None  # Nenhum rei capturado
    
    def is_stalemate(self):
        """
        Verifica se o jogador atual está em afogamento (stalemate)
        """
        # Se estiver em xeque, não é afogamento
        if self.is_check(self.current_player):
            return False
        
        # Verifica se há algum movimento válido
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == self.current_player:
                    moves = self.get_valid_moves((row, col))
                    if moves:
                        return False
        
        # Se não houver movimentos válidos, é afogamento
        return True
    
    def is_game_over(self):
        """
        Verifica se o jogo acabou (xeque-mate, empate ou rei capturado)
        """
        # Verifica se algum rei foi capturado
        captured = self.is_king_captured()
        if captured:
            return True
        
        # Verifica xeque-mate ou empate
        return self.is_checkmate() or self.is_stalemate()
    
    def get_result(self):
        """
        Retorna o resultado do jogo
        1 se as brancas venceram, -1 se as pretas venceram, 0 para empate, None se o jogo não acabou
        """
        # Verifica se algum rei foi capturado
        captured = self.is_king_captured()
        if captured == 'w':
            return 1  # Brancas venceram
        elif captured == 'b':
            return -1  # Pretas venceram
        
        if not self.is_game_over():
            return None
        
        if self.is_checkmate():
            return -1 if self.current_player == 'w' else 1  # O jogador que não está em movimento venceu
        
        return 0  # Empate
    
    def get_state_representation(self):
        """
        Retorna uma representação do estado atual do jogo para aprendizado da IA
        """
        # Tabuleiro linearizado com 1 para peças brancas, -1 para peças pretas, 0 para vazias
        state = []
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece == '.':
                    state.append(0)
                else:
                    value = 0
                    piece_type = piece.lower()
                    if piece_type == 'p':
                        value = 1
                    elif piece_type == 'r':
                        value = 2
                    elif piece_type == 'q':
                        value = 5
                    elif piece_type == 'k':
                        value = 6
                    
                    if self.get_piece_color(piece) == 'b':
                        value = -value
                    
                    state.append(value)
        
        # Adiciona o jogador atual (1 para brancas, -1 para pretas)
        state.append(1 if self.current_player == 'w' else -1)
        
        return np.array(state) 