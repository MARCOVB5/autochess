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
                                return True
                        
                        # Mesma coluna
                        elif col == king_col:
                            blocked = False
                            for r in range(min(row, king_row) + 1, max(row, king_row)):
                                if self.board[r][col] != '.':
                                    blocked = True
                                    break
                            if not blocked:
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
                                return True
                        
                        elif col == king_col:  # Mesma coluna
                            blocked = False
                            for r in range(min(row, king_row) + 1, max(row, king_row)):
                                if self.board[r][col] != '.':
                                    blocked = True
                                    break
                            if not blocked:
                                return True
                        
                        # Movimentos diagonais
                        elif abs(row - king_row) == abs(col - king_col):  # Mesma diagonal
                            dr = 1 if king_row > row else -1
                            dc = 1 if king_col > col else -1
                            
                            r, c = row + dr, col + dc
                            blocked = False
                            
                            while r != king_row and c != king_col:
                                if self.board[r][c] != '.':
                                    blocked = True
                                    break
                                r += dr
                                c += dc
                            
                            if not blocked:
                                return True
                    
                    # Rei (pode capturar outro rei se estiver adjacente)
                    elif piece.lower() == 'k':
                        if abs(row - king_row) <= 1 and abs(col - king_col) <= 1:
                            return True
        
        return False
    
    def print_board(self):
        """
        Imprime o tabuleiro no console
        """
        print("  0 1 2 3")
        print(" +-+-+-+-+")
        for i, row in enumerate(self.board):
            print(f"{i}|{'|'.join(row)}|")
            print(" +-+-+-+-+")
        
        print(f"Jogador atual: {'Brancas' if self.current_player == 'w' else 'Pretas'}")
    
    def is_checkmate(self):
        """
        Verifica se o jogador atual está em xeque-mate
        """
        # Se o jogador não está em xeque, não pode estar em xeque-mate
        if not self.is_check(self.current_player):
            return False
        
        # Verifica se existe algum movimento que tire o jogador do xeque
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == self.current_player:
                    for dest_row, dest_col in self.get_valid_moves((row, col)):
                        # Simula o movimento
                        temp_board = deepcopy(self.board)
                        temp_king_pos = deepcopy(self.king_positions)
                        
                        # Atualiza a posição do rei, se necessário
                        if piece.lower() == 'k':
                            temp_king_pos[self.current_player] = (dest_row, dest_col)
                        
                        # Executa o movimento temporário
                        self.board[dest_row][dest_col] = piece
                        self.board[row][col] = '.'
                        self.king_positions = temp_king_pos
                        
                        # Verifica se o rei ainda está em xeque
                        still_in_check = self.is_check(self.current_player)
                        
                        # Desfaz o movimento temporário
                        self.board = temp_board
                        self.king_positions = temp_king_pos
                        
                        # Se encontrou um movimento que tira do xeque, não é xeque-mate
                        if not still_in_check:
                            return False
        
        # Se nenhum movimento tira do xeque, é xeque-mate
        return True
    
    def is_king_captured(self):
        """
        Verifica se algum rei foi capturado (condição alternativa de vitória)
        """
        king_w_found = False
        king_b_found = False
        
        for row in self.board:
            for piece in row:
                if piece == 'K':
                    king_w_found = True
                elif piece == 'k':
                    king_b_found = True
        
        if not king_w_found:
            return 'b'  # Pretas venceram (rei branco capturado)
        elif not king_b_found:
            return 'w'  # Brancas venceram (rei preto capturado)
        else:
            return None  # Nenhum rei foi capturado
    
    def is_stalemate(self):
        """
        Verifica se o jogo está em stalemate (empate por afogamento)
        """
        # Se o jogador está em xeque, não é stalemate
        if self.is_check(self.current_player):
            return False
        
        # Verifica se o jogador atual tem algum movimento válido
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == self.current_player:
                    if self.get_valid_moves((row, col)):
                        return False
        
        # Se não tem nenhum movimento válido e não está em xeque, é stalemate
        return True
    
    def is_game_over(self):
        """
        Verifica se o jogo terminou (xeque-mate, rei capturado ou stalemate)
        """
        # Verifica se algum rei foi capturado
        if self.is_king_captured():
            return True
        
        # Verifica se é xeque-mate
        if self.is_checkmate():
            return True
        
        # Verifica se é stalemate
        if self.is_stalemate():
            return True
        
        return False
    
    def get_result(self):
        """
        Retorna o resultado do jogo: 'w' se brancas venceram, 'b' se pretas venceram, 'draw' se empate
        """
        # Verifica se algum rei foi capturado
        king_captured = self.is_king_captured()
        if king_captured:
            return king_captured
        
        # Verifica se é xeque-mate
        if self.is_checkmate():
            # O jogador atual está em xeque-mate, então o oponente venceu
            return 'b' if self.current_player == 'w' else 'w'
        
        # Verifica se é stalemate
        if self.is_stalemate():
            return 'draw'
        
        # Jogo ainda não terminou
        return None
    
    def get_state_representation(self):
        """
        Retorna uma representação do estado atual do jogo como uma tupla de strings
        """
        # Concatena todas as linhas em uma única string
        board_str = ''
        for row in self.board:
            board_str += ''.join(row)
        
        # Adiciona o jogador atual
        return (board_str, self.current_player) 