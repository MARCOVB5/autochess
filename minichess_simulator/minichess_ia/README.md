# MiniChess com IA

Simulador 4×4 em que uma pessoa joga com as peças brancas contra a IA preta.

## Executar

A partir deste diretório:

```bash
pip install -r requirements.txt
python main.py
```

Clique em uma peça e depois em uma casa destacada. “Novo Jogo” preserva o
aprendizado; “Resetar IA” apaga o modelo. Os botões F1, F2 e F3 ajustam o
nível de exploração para fins de demonstração.

Por escolha pedagógica, ambos os jogadores podem deixar o próprio rei em
xeque. A partida continua até um rei ser capturado, permitindo observar se a
IA percebe uma ameaça, aproveita um rei exposto ou protege o próprio rei.

## Aprendizado

A IA combina duas fontes de decisão:

- uma avaliação imediata de material, xeque e captura do rei;
- uma tabela Q persistida em `models/minichess_ai_model.pkl`.

O comportamento foi desenhado para que uma criança perceba a evolução em
poucas partidas:

- partidas 1–5: **Iniciante** — escolhe deliberadamente entre as jogadas mais
  fracas;
- partidas 6–15: **Aprendendo** — alterna bastante entre exploração e boas
  jogadas;
- depois da partida 15: **Experiente** — usa a heurística e a tabela Q, mas
  mantém 8% de exploração para continuar cometendo erros ocasionais.

Essa progressão é um recurso pedagógico combinado ao Q-learning, não um
resultado produzido exclusivamente por ele. Ao final de cada partida, vitória,
empate ou derrota são propagados pelas decisões tomadas pela IA. O modelo é
salvo periodicamente e ao fechar o simulador.

O agente usado aqui é o mesmo de `core/ai_player.py`; este diretório mantém
apenas um adaptador para usar seu próprio arquivo de modelo.

## Treinar e avaliar sem interface

A partir de `core/`, é possível treinar contra um adversário branco aleatório:

```bash
python train_ai.py --games 1000
python evaluate_ai.py --games 200
```

Acrescente `--pedagogical` à avaliação para medir o comportamento visível do
nível atual. Sem essa opção, a avaliação mede a melhor política disponível sem
erros pedagógicos.

Use `--model /tmp/model.pkl` nos dois comandos para experimentar sem alterar o
modelo principal.
