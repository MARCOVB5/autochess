from minichess import MiniChess

def test_kings_draw():
    # Inicializa o jogo
    game = MiniChess()
    
    # Configura um tabuleiro com apenas dois reis
    game.board = [
        ['.', '.', 'k', '.'], 
        ['.', '.', '.', '.'],
        ['.', '.', '.', '.'],
        ['.', 'K', '.', '.']
    ]
    
    # Atualiza as posições dos reis
    game.king_positions = {
        'w': (3, 1),  # Rei branco
        'b': (0, 2)   # Rei preto
    }
    
    # Verifica se a função detecta apenas reis restantes
    is_only_kings = game.is_only_kings_remaining()
    print(f"Apenas reis restantes: {is_only_kings}")
    
    # Verifica se o jogo é considerado encerrado
    is_game_over = game.is_game_over()
    print(f"Jogo encerrado: {is_game_over}")
    
    # Verifica o resultado (deve ser 0 para empate)
    result = game.get_result()
    print(f"Resultado: {result} (0 = empate, 1 = brancas vencem, -1 = pretas vencem)")
    
    # Agora vamos adicionar uma peça para verificar que não é mais apenas reis
    game.board[1][1] = 'P'  # Adiciona um peão branco
    
    is_only_kings = game.is_only_kings_remaining()
    print(f"\nApós adicionar uma peça:")
    print(f"Apenas reis restantes: {is_only_kings}")
    print(f"Jogo encerrado: {game.is_game_over()}")
    print(f"Resultado: {game.get_result()}")

if __name__ == "__main__":
    test_kings_draw() 