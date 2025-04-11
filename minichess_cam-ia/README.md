# Mini Chess com IA e Sistema CNC

Um jogo de xadrez 4x4 com Inteligência Artificial e sistema CNC para movimentação de peças físicas.

## Características

- Tabuleiro de xadrez 4x4 simplificado
- Interface gráfica com Pygame
- IA de aprendizado por reforço (Q-learning)
- Detecção de tabuleiro físico via câmera (OpenCV)
- Controle de sistema CNC para movimentação automatizada de peças físicas
- Modo interface gráfica e modo tabuleiro físico com câmera

## Requisitos

### Software
- Python 3.8+
- Pygame
- NumPy
- OpenCV
- PySerial (para comunicação com Arduino)

### Hardware
- Computador com câmera (para modo de detecção)
- Arduino (para controle do CNC)
- Sistema CNC para movimentação de peças (opcional)

## Instalação

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/mini-chess.git
cd mini-chess
```

2. Instale as dependências:
```bash
pip install pygame numpy opencv-python pyserial
```

3. [Opcional] Configure o Arduino:
   - Abra o arquivo `arduino/cnc_chess_controller.ino` no Arduino IDE
   - Carregue o firmware no Arduino 
   - Conecte o Arduino ao computador

## Uso

### Iniciar o jogo:
```bash
python main.py
```

### Modos de jogo

O sistema oferece dois modos de operação:

1. **Modo Interface**: Jogo pelo computador usando a interface gráfica
2. **Modo Câmera**: Jogo com tabuleiro físico utilizando detecção por câmera

Alterne entre os modos clicando no botão "Modo: Interface/Câmera" na interface.

### Controles

- **Clique do Mouse**: Seleciona e move peças (no modo interface)
- **Botão "Resetar IA"**: Reinicia o aprendizado da IA
- **Botão "Calibrar Câmera"**: Calibra a detecção por câmera
- **Botão "Visualizar Câmera"**: Mostra a visão da câmera em tempo real
- **Botão "Capturar Template"**: Captura modelos de peças para reconhecimento

## Componentes Principais

### Jogo de Xadrez
- `minichess.py`: Implementação das regras e lógica do jogo 4x4
- `main.py`: Interface gráfica e loop principal do jogo

### IA e Aprendizado
- `ai_player.py`: Implementação da IA com aprendizado por reforço (Q-learning)

### Detecção por Câmera
- Classe `ChessBoardDetector` em `main.py`: Detecção do tabuleiro físico e peças

### Sistema CNC (Opcional)
- `arduino/cnc_chess_controller.ino`: Firmware para controle do sistema CNC
- Funções de comunicação serial em `main.py`: Interação com o Arduino

## Sistema CNC para Movimentação Física

### Configuração

Para habilitar o sistema CNC, edite as seguintes configurações em `main.py`:

```python
# Configurações do CNC
CNC_ENABLED = True  # Altere para True quando o hardware estiver conectado
CNC_PORT = '/dev/ttyACM0'  # Porta serial do Arduino (ajuste conforme necessário)
```

### Montagem do Hardware

Consulte os seguintes recursos para montar o sistema CNC:

- `arduino/montagem_cnc_xadrez.md`: Guia detalhado de montagem
- `arduino/diagrama_conexoes.txt`: Diagrama de conexões elétricas

### Operação

Uma vez configurado, o sistema CNC irá:
1. Mover-se para a posição da peça de origem
2. Ativar o eletroímã para pegar a peça
3. Levantar e mover a peça para a posição de destino
4. Soltar a peça
5. Retornar para posição de espera

## Personalização

### Tamanho do Tabuleiro
O jogo atual utiliza um tabuleiro 4x4. Para alterar, modifique as constantes em `minichess.py`.

### Força da IA
Ajuste o aprendizado da IA modificando os parâmetros em `ai_player.py`:
- `learning_rate`: Taxa de aprendizado
- `discount_factor`: Fator de desconto para recompensas futuras
- `exploration_rate`: Taxa de exploração para novas jogadas

### Sistema CNC
Ajuste os parâmetros mecânicos no arquivo `arduino/cnc_chess_controller.ino`:
- `STEPS_PER_MM`: Passos por milímetro para seus motores
- `CHESS_SQUARE_SIZE`: Tamanho das casas do tabuleiro físico

## Solução de Problemas

### O jogo trava ou não responde
- Verifique se há erros no console
- Certifique-se de que todas as dependências estão instaladas

### A câmera não detecta o tabuleiro
- Verifique se a câmera está conectada e funcionando
- Execute a calibração em um ambiente bem iluminado
- Certifique-se de que o tabuleiro está completamente visível

### O sistema CNC não responde
- Verifique as conexões do Arduino
- Certifique-se de que a porta serial está correta em `CNC_PORT`
- Verifique a alimentação do sistema CNC
- Execute um reset no Arduino e reinicie o programa

## Contribuição

Contribuições são bem-vindas! Por favor, abra uma issue ou pull request.

## Licença

Este projeto está licenciado sob a Licença MIT.

## Agradecimentos

- OpenCV pela biblioteca de visão computacional
- Pygame pela biblioteca de jogos
- Comunidade de Xadrez e IA por referências e inspiração 