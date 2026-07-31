from copy import deepcopy

class MiniChess:
    """
    Implementação de um jogo de MiniChess 4x4.
    """
    
    def __init__(self, ignore_check_rule=False):
        """
        Inicializa um tabuleiro 4x4
        Notação: maiúsculas para peças brancas, minúsculas para pretas
        Peças: R=torre, Q=rainha, K=rei, P=peão
        '.' representa uma casa vazia
        
        Args:
            ignore_check_rule: Se True, permite que ambos os jogadores deixem o próprio rei em xeque
        """
        self.board = [
            ['r', 'q', 'k', 'r'], 
            ['p', 'p', 'p', 'p'],
            ['P', 'P', 'P', 'P'],
            ['R', 'Q', 'K', 'R']
        ]
        
        self.board_size = 4
        
        self.current_player = 'w'
        
        self.move_history = []
        
        self.king_positions = {
            'w': (3, 2),  # Posição inicial do rei branco (linha, coluna)
            'b': (0, 2)   # Posição inicial do rei preto (linha, coluna)
        }
        
        # O simulador da IA desativa a regra de xeque nas primeiras partidas.
        self.ignore_check_rule = ignore_check_rule
        
    def get_piece_color(self, piece):
        """Retorna a cor da peça ('w' para brancas, 'b' para pretas)"""
        if piece == '.':
            return None
        return 'w' if piece.isupper() else 'b'
    
    def is_valid_position(self, row, col):
        """Verifica se a posição está dentro do tabuleiro"""
        return 0 <= row < 4 and 0 <= col < 4
    
    def get_basic_moves(self, position):
        """
        Retorna todos os movimentos básicos para a peça na posição dada,
        sem verificar se o movimento deixa o rei em xeque.
        Usado internamente para evitar recursão infinita.
        """
        row, col = position
        piece = self.board[row][col]
        
        if piece == '.':
            return []
        if self.get_piece_color(piece) != self.current_player:
            return []
        
        valid_moves = []
        piece_type = piece.lower()
        
        if piece_type == 'p':
            direction = -1 if self.current_player == 'w' else 1
            
            new_row = row + direction
            if self.is_valid_position(new_row, col) and self.board[new_row][col] == '.':
                valid_moves.append((new_row, col))
            
            for new_col in [col-1, col+1]:
                if self.is_valid_position(new_row, new_col) and self.board[new_row][new_col] != '.':
                    if self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                        valid_moves.append((new_row, new_col))
        
        elif piece_type == 'r':
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
        
        elif piece_type == 'q':
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
        
        elif piece_type == 'k':
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                
                if self.is_valid_position(new_row, new_col):
                    if self.board[new_row][new_col] == '.' or self.get_piece_color(self.board[new_row][new_col]) != self.current_player:
                        valid_moves.append((new_row, new_col))
        
        return valid_moves
    
    def get_valid_moves(self, position):
        """
        Retorna todos os movimentos válidos para a peça na posição dada
        """
        valid_moves = self.get_basic_moves(position)
        
        if self.ignore_check_rule:
            return valid_moves
        
        filtered_moves = []
        for move in valid_moves:
            temp_board = deepcopy(self)
            temp_board.make_move((position, move), check_validity=False)
            if not temp_board.is_king_attacked(self.current_player):
                filtered_moves.append(move)
        
        return filtered_moves
    
    def is_king_attacked(self, player):
        """
        Verifica se o rei do jogador está sob ataque direto.
        Esta função é usada para verificar xeque sem recursão infinita.
        """
        king_row, king_col = self.king_positions[player]
        opponent = 'b' if player == 'w' else 'w'
        
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == opponent:
                    original_player = self.current_player
                    self.current_player = opponent
                    
                    moves = self.get_basic_moves((row, col))
                    
                    self.current_player = original_player
                    
                    if (king_row, king_col) in moves:
                        return True
        
        return False
    
    def is_check(self, player):
        """
        Verifica se o jogador está em xeque
        """
        return self.is_king_attacked(player)
    
    def get_all_valid_moves(self, player):
        """
        Retorna todos os movimentos válidos para todas as peças do jogador
        """
        all_moves = []
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == player:
                    original_player = self.current_player
                    if player != self.current_player:
                        self.current_player = player
                    origin = (row, col)
                    moves = self.get_valid_moves(origin)
                    for dest in moves:
                        all_moves.append((origin, dest))
                    self.current_player = original_player
        return all_moves

    def make_move(self, move, check_validity=True):
        """
        Executa um movimento no formato ((origem_linha, origem_coluna), (destino_linha, destino_coluna))
        Retorna True se o movimento foi bem-sucedido, False caso contrário
        """
        origin, destination = move
        orig_row, orig_col = origin
        dest_row, dest_col = destination
        
        if not (self.is_valid_position(orig_row, orig_col) and self.is_valid_position(dest_row, dest_col)):
            return False
        
        piece = self.board[orig_row][orig_col]
        if piece == '.':
            return False
        
        if self.get_piece_color(piece) != self.current_player:
            return False
        
        if check_validity:
            valid_moves = self.get_valid_moves((orig_row, orig_col))
            if (dest_row, dest_col) not in valid_moves:
                return False
        
        captured_piece = self.board[dest_row][dest_col]
        
        self.board[dest_row][dest_col] = piece
        self.board[orig_row][orig_col] = '.'
        
        if piece.lower() == 'k':
            self.king_positions[self.current_player] = (dest_row, dest_col)
        
        self.move_history.append((move, piece, captured_piece))
        
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        
        return True

    def is_checkmate(self):
        """
        Verifica se o jogador atual está em xeque-mate
        """
        if self.ignore_check_rule:
            return False

        if not self.is_check(self.current_player):
            return False
        
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == self.current_player:
                    moves = self.get_valid_moves((row, col))
                    if moves:  # Se há pelo menos um movimento legal
                        return False
        
        return True
    
    def is_king_captured(self):
        """
        Verifica se algum rei foi capturado (o que encerra o jogo)
        Retorna a cor do jogador que perdeu ('w' ou 'b'), ou None se nenhum rei foi capturado
        """
        white_king_found = False
        for row in range(4):
            for col in range(4):
                if self.board[row][col] == 'K':
                    white_king_found = True
                    break
            if white_king_found:
                break
        
        black_king_found = False
        for row in range(4):
            for col in range(4):
                if self.board[row][col] == 'k':
                    black_king_found = True
                    break
            if black_king_found:
                break
        
        if not white_king_found:
            return 'w'  # Rei branco capturado
        if not black_king_found:
            return 'b'  # Rei preto capturado
            
        return None  # Nenhum rei capturado
    
    def is_draw(self):
        """
        Verifica se o jogo está empatado (sem movimentos legais, mas não em xeque)
        """
        if not self.ignore_check_rule and self.is_check(self.current_player):
            return False
        
        for row in range(4):
            for col in range(4):
                piece = self.board[row][col]
                if piece != '.' and self.get_piece_color(piece) == self.current_player:
                    moves = self.get_valid_moves((row, col))
                    if moves:  # Se há pelo menos um movimento legal
                        return False
        
        return True
    
    def is_game_over(self):
        """
        Verifica se o jogo acabou (rei capturado, xeque-mate ou empate)
        """
        return (self.is_king_captured() is not None or 
                self.is_checkmate() or 
                self.is_draw())
    
    def get_result(self):
        """
        Retorna o resultado do jogo:
        1 para vitória das brancas, -1 para vitória das pretas, 0 para empate,
        None se o jogo ainda não acabou
        """
        if not self.is_game_over():
            return None
            
        if self.is_king_captured() == 'b':
            return 1  # Vitória das brancas
        elif self.is_king_captured() == 'w':
            return -1  # Vitória das pretas
        elif self.is_checkmate():
            return 1 if self.current_player == 'b' else -1
        else:
            return 0  # Empate
    
    def get_state_representation(self):
        """
        Retorna uma representação do estado do jogo como uma tupla hashable
        """
        board_str = ''.join(''.join(row) for row in self.board)
        
        return (board_str, self.current_player)
