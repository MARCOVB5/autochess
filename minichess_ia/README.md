# Mini Chess 4x4 com IA de Aprendizado

Este projeto implementa um jogo de xadrez 4x4 (Mini Chess) com uma IA que aprende a jogar melhor conforme mais partidas são disputadas.

## Requisitos

- Python 3.7 ou superior
- Pygame
- Numpy

## Instalação

1. Clone este repositório:
```
git clone https://github.com/seu-usuario/minichess-learning-ai.git
cd minichess-learning-ai
```

2. Instale as dependências:
```
pip install -r requirements.txt
```

3. Para executar o jogo:
```
python main.py
```

## Como Jogar

- Use o mouse para selecionar e mover as peças brancas
- Primeiro clique na peça que deseja mover
- Os movimentos válidos serão destacados com círculos verdes
- Clique em um dos círculos verdes para mover a peça para aquela posição
- A IA (peças pretas) fará seu movimento automaticamente após o seu
- Após cada partida, a IA aprende e melhora para as próximas partidas
- Você pode resetar o aprendizado da IA clicando no botão "Resetar IA"

## Funcionamento da IA

A IA utiliza aprendizado por reforço (Q-learning) para melhorar suas jogadas:

1. No início, a IA faz movimentos aleatórios (exploração)
2. Conforme aprende quais movimentos levam a vitórias, começa a usar esse conhecimento (exploitação)
3. O modelo é salvo automaticamente após cada partida e carregado quando você reinicia o jogo
4. A força da IA é exibida na tela e evolui com o número de partidas jogadas

## Regras do Mini Chess 4x4

- O tabuleiro é de 4x4 casas
- Brancas jogam primeiro
- Configuração inicial:
  - Primeira fileira (pretas): torre, rainha, rei, torre
  - Segunda fileira (pretas): 4 peões
  - Terceira fileira (brancas): 4 peões
  - Quarta fileira (brancas): torre, rei, rainha, torre
- As peças se movem como no xadrez tradicional
- O objetivo é dar xeque-mate no rei adversário
- Não há promoção de peões ou movimento especial de roque

## Estrutura de Arquivos

- `main.py`: Interface gráfica e loop principal do jogo
- `minichess.py`: Implementação das regras do jogo
- `ai_player.py`: Implementação da IA com aprendizado de máquina
- `models/`: Diretório onde o modelo aprendido da IA é salvo
- `assets/`: Diretório para imagens das peças de xadrez

## Imagens das Peças

As imagens das peças devem ser nomeadas da seguinte forma:
- `white-pawn.png` - Peão branco
- `white-rook.png` - Torre branca
- `white-queen.png` - Rainha branca
- `white-king.png` - Rei branco
- `black-pawn.png` - Peão preto
- `black-rook.png` - Torre preta
- `black-queen.png` - Rainha preta
- `black-king.png` - Rei preto 