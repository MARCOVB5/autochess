# MiniChess com IA de Aprendizado (Q-Learning)

Uma implementação de xadrez miniatura (4x4) com uma IA que aprende a jogar usando técnicas de aprendizado por reforço (Q-Learning).

## Sobre o Jogo

MiniChess é uma versão simplificada do xadrez tradicional, jogada em um tabuleiro 4x4. O jogo mantém as mesmas regras básicas do xadrez, mas com um espaço menor e apenas quatro tipos de peças:

- Rei (K): Move-se uma casa em qualquer direção
- Rainha (Q): Move-se em linha reta em qualquer direção
- Torre (R): Move-se em linha reta horizontal ou vertical
- Peão (P): Move-se uma casa para frente e captura na diagonal

## Sobre a IA

A IA utiliza um algoritmo de aprendizado por reforço chamado Q-Learning para melhorar progressivamente suas habilidades. Ela passa por três fases distintas de aprendizado:

1. **Fase 1 (Jogos 0-4)**: A IA é "super burra", propositalmente fazendo movimentos ruins para explorar o espaço de estados do jogo. Ela tenta sacrificar suas peças mais valiosas.

2. **Fase 2 (Jogos 5-9)**: A IA está em transição, gradualmente começando a fazer movimentos melhores a cada jogo.

3. **Fase 3 (Jogos 10+)**: A IA se torna "inteligente", utilizando o conhecimento que adquiriu para jogar de forma competitiva.

A cada jogo, a IA recebe recompensas com base no resultado da partida:
- Vitória: +1
- Empate: 0
- Derrota: -1

Esses valores são invertidos durante a fase 1 para incentivar o comportamento exploratório.

## Requisitos

- Python 3.6+
- Pygame
- NumPy

## Instalação

1. Clone o repositório:
```
git clone <repositório>
cd <repositório>
```

2. Instale as dependências:
```
pip install -r minichess_ia2/requirements.txt
```

## Como Jogar

Execute o script principal:
```
python minichess_ia2/run.py
```

### Controles:
- Clique em uma peça para selecioná-la
- Clique em um destino válido (destacado em verde) para mover
- Botão "Novo Jogo": Inicia uma nova partida
- Botão "Resetar IA": Reinicia a IA para a fase 1 (apaga todo o aprendizado)
- Botões "F1", "F2", "F3": Força a IA a entrar na fase específica

## Como Funciona a IA

A IA utiliza Q-Learning, armazenando valores para cada par estado-ação em uma tabela. A função Q representa a utilidade esperada de tomar uma ação específica em um determinado estado. A IA aprende atualizando esses valores com base nas recompensas recebidas.

Durante as primeiras partidas, a IA prioriza exploração (fazendo movimentos ruins de propósito) para conhecer melhor o espaço de estados. Conforme joga mais partidas, ela gradualmente equilibra exploração com exploração (escolhendo os melhores movimentos conhecidos).

## Implementação

O projeto está organizado em três módulos principais:

- `minichess.py`: Implementa as regras do jogo de xadrez miniatura
- `ai_player.py`: Implementa a IA com Q-Learning
- `main.py`: Implementa a interface gráfica e o loop principal do jogo

Os modelos aprendidos são salvos automaticamente em arquivos pickle no diretório `models/`. 