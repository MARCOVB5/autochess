# Guia de Montagem do Sistema CNC para Xadrez

Este guia descreve como montar um sistema CNC simples para mover peças de xadrez em um tabuleiro físico.

## Lista de Materiais

### Componentes Eletrônicos
- 1 x Arduino Mega ou UNO
- 1 x CNC Shield V3 para Arduino
- 3 x Drivers de motor de passo A4988 ou DRV8825
- 3 x Motores de passo NEMA 17 (para eixos X, Y e Z)
- 1 x Fonte de alimentação 12V 5A
- 1 x Eletroímã 12V
- 1 x Transistor MOSFET ou Módulo Relé para controlar o eletroímã
- 3 x Chaves de fim de curso (opcional, mas recomendado)
- Cabos e conectores diversos

### Componentes Mecânicos
- Perfis de alumínio 2020 ou 2040 para a estrutura
- 2 x Correias GT2 e polias para os eixos X e Y
- 1 x Fuso trapezoidal ou barra roscada para o eixo Z
- Rolamentos lineares
- Suportes e acopladores para motores
- Placas de MDF ou acrílico para a base
- Parafusos, porcas e arruelas

### Ferramentas Necessárias
- Chaves de fenda e chaves Allen
- Alicate
- Ferro de solda e solda
- Multímetro
- Régua e esquadro
- Serra para cortar os perfis (se necessário)

## Montagem da Estrutura

### 1. Montagem do Quadro XY
1. Corte os perfis de alumínio nas seguintes dimensões:
   - 4 x 400mm para o quadro externo
   - 2 x 300mm para o eixo Y
   - 1 x 350mm para o eixo X

2. Monte o quadro externo formando um retângulo com os perfis de 400mm
3. Fixe os 2 perfis de 300mm em paralelo para formar os trilhos do eixo Y
4. Monte o perfil de 350mm perpendicular aos trilhos Y para formar o eixo X

### 2. Montagem do Eixo Z
1. Fixe o motor do eixo Z no carro do eixo X
2. Instale o fuso trapezoidal conectado ao motor Z
3. Monte uma plataforma pequena onde será fixado o eletroímã

### 3. Sistema de Movimento
1. Instale as correias GT2 nos eixos X e Y
2. Fixe as polias aos eixos dos motores
3. Instale os rolamentos lineares nas junções dos eixos
4. Ajuste a tensão das correias para evitar folgas

### 4. Montagem do Eletroímã
1. Fixe o eletroímã na extremidade do eixo Z
2. Passe os cabos do eletroímã de forma a não interferir no movimento
3. Opcionalmente, adicione um pequeno disco metálico na ponta do eletroímã para melhorar o contato com as peças

## Montagem Eletrônica

### 1. Preparação do Arduino e CNC Shield
1. Fixe o CNC Shield no Arduino
2. Configure os jumpers da CNC Shield para microstepping (geralmente 1/16 para mais precisão)
3. Insira os drivers A4988/DRV8825 nas posições X, Y e Z
4. Ajuste a corrente dos drivers com um multímetro (consulte especificações dos seus motores)

### 2. Conexão dos Motores
1. Conecte os 4 fios de cada motor de passo aos terminais correspondentes da CNC Shield
2. Verifique a polaridade correta - se o motor girar no sentido errado, inverta um par de fios

### 3. Instalação do Eletroímã
1. Conecte o eletroímã ao transistor MOSFET ou relé
2. Conecte o circuito de controle ao pino definido no código (pino 8)
3. Conecte a alimentação do eletroímã à fonte 12V (ATENÇÃO: não conecte diretamente ao Arduino!)

### 4. Instalação das Chaves de Fim de Curso (opcional)
1. Posicione as chaves no início dos eixos X, Y e Z
2. Conecte um terminal de cada chave ao GND
3. Conecte o outro terminal aos pinos definidos no código (9, 10 e 11)

### 5. Alimentação
1. Conecte a fonte 12V 5A à CNC Shield
2. Mantenha o Arduino alimentado via USB durante o desenvolvimento

## Calibração do Sistema

### 1. Upload do Firmware
1. Abra o arquivo `cnc_chess_controller.ino` no Arduino IDE
2. Conecte o Arduino ao computador via USB
3. Faça upload do firmware para o Arduino

### 2. Configuração do Firmware
1. Ajuste a variável `STEPS_PER_MM` de acordo com sua configuração mecânica
2. Defina o tamanho das casas do tabuleiro em `CHESS_SQUARE_SIZE`
3. Ajuste as velocidades e acelerações dos motores se necessário

### 3. Homing e Teste
1. Posicione o sistema no que será o ponto zero (canto inferior esquerdo do tabuleiro)
2. Execute o comando de homing pelo programa Python
3. Teste movimentos básicos para garantir que o sistema se move corretamente

## Integração com o Programa de Xadrez

1. No código Python, ative o sistema CNC alterando a variável `CNC_ENABLED` para `True`
2. Ajuste a porta serial em `CNC_PORT` de acordo com a porta do seu Arduino
3. Execute o programa e teste o movimento de peças com o sistema CNC

## Ajustes Finais

1. Marque a posição do tabuleiro para garantir que ele fique sempre no mesmo lugar
2. Faça pequenos ajustes nas coordenadas se necessário
3. Verifique se o eletroímã tem força suficiente para mover as peças
4. Teste o sistema completo com um jogo de xadrez

## Solução de Problemas

1. **Motores não movem**: Verifique alimentação, conexões e ajuste de corrente dos drivers
2. **Eletroímã não segura as peças**: Verifique a alimentação e certifique-se que as peças contêm metal
3. **Movimentos imprecisos**: Reajuste `STEPS_PER_MM` e verifique se as correias estão tensionadas
4. **Comunicação serial falha**: Verifique a porta serial e certifique-se que o Arduino está sendo reconhecido

## Notas
- Certifique-se que as peças de xadrez têm uma base metálica para interagir com o eletroímã
- Durante os testes, mantenha as mãos longe do sistema em movimento
- Considere adicionar um botão de emergência físico para paradas rápidas 