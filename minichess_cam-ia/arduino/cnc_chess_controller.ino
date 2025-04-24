#include <AccelStepper.h>
#include <MultiStepper.h>

// Definição dos pinos
#define X_STEP_PIN 2
#define X_DIR_PIN 5
#define Y_STEP_PIN 3
#define Y_DIR_PIN 6
#define Z_STEP_PIN 4
#define Z_DIR_PIN 7
#define ELECTROMAGNET_PIN 8

// Limites de fim de curso (opcional)
#define X_MIN_PIN 9
#define Y_MIN_PIN 10
#define Z_MIN_PIN 11

// Configurações
#define STEPS_PER_MM 80  // Ajuste baseado na sua mecânica
#define CHESS_SQUARE_SIZE 50  // Tamanho de cada casa em mm
#define Z_SAFE_HEIGHT 20      // Altura segura para movimento
#define Z_PICKUP_HEIGHT 0     // Altura para pegar/soltar peças

// Inicialização dos motores
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
MultiStepper steppers;

// Posição atual
int currentX = 0;
int currentY = 0;
int currentZ = 0;

// Controle de estado
bool systemReady = false;
bool emergencyStop = false;

void setup() {
  Serial.begin(9600);
  
  // Aguardar conexão serial (opcional, para debug via USB)
  delay(1000);

  // Configurar pinos de limite (opcional)
  pinMode(X_MIN_PIN, INPUT_PULLUP);
  pinMode(Y_MIN_PIN, INPUT_PULLUP);
  pinMode(Z_MIN_PIN, INPUT_PULLUP);

  // Configurar pino do eletroímã
  pinMode(ELECTROMAGNET_PIN, OUTPUT);
  digitalWrite(ELECTROMAGNET_PIN, LOW);
  
  // Configurar motores
  stepperX.setMaxSpeed(1000);
  stepperX.setAcceleration(500);
  stepperY.setMaxSpeed(1000);
  stepperY.setAcceleration(500);
  stepperZ.setMaxSpeed(500);
  stepperZ.setAcceleration(200);
  
  // Adicionar ao controle múltiplo
  steppers.addStepper(stepperX);
  steppers.addStepper(stepperY);
  
  Serial.println("Sistema CNC Xadrez inicializado");
  systemReady = true;
}

void loop() {
  // Verificar parada de emergência (opcional)
  if (emergencyStop) {
    return;
  }
  
  // Processar comandos recebidos
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();  // Remover espaços e quebras de linha
    processCommand(command);
  }
}

void processCommand(String command) {
  // Responder ao ping para verificação de conexão
  if (command == "PING") {
    Serial.println("PONG");
    return;
  }
  
  // Parada de emergência
  if (command == "STOP" || command == "EMERGENCY") {
    emergencyStop = true;
    stepperX.stop();
    stepperY.stop();
    stepperZ.stop();
    digitalWrite(ELECTROMAGNET_PIN, LOW);
    Serial.println("EMERGENCY STOP");
    return;
  }
  
  // Resetar após parada de emergência
  if (command == "RESET") {
    emergencyStop = false;
    stepperX.stop();
    stepperY.stop();
    stepperZ.stop();
    digitalWrite(ELECTROMAGNET_PIN, LOW);
    Serial.println("RESET OK");
    return;
  }
  
  // Se estiver em parada de emergência, não processa outros comandos
  if (emergencyStop) {
    Serial.println("ERROR: System in emergency stop");
    return;
  }
  
  // Formato: "MOVE x1 y1 x2 y2"
  if (command.startsWith("MOVE")) {
    int params[4];
    int paramIndex = 0;
    int cmdIndex = 5; // Após "MOVE "
    
    // Extrair parâmetros
    while (cmdIndex < command.length() && paramIndex < 4) {
      int spacePos = command.indexOf(' ', cmdIndex);
      if (spacePos == -1) spacePos = command.length();
      
      params[paramIndex++] = command.substring(cmdIndex, spacePos).toInt();
      cmdIndex = spacePos + 1;
    }
    
    if (paramIndex == 4) {
      movePiece(params[0], params[1], params[2], params[3]);
      Serial.println("OK");
    } else {
      Serial.println("ERROR: Invalid parameters");
    }
  } 
  else if (command == "HOME") {
    homeAxes();
    Serial.println("OK");
  }
  else if (command == "PARK") {
    // Mover para posição de estacionamento
    moveToPosition(0, 0, Z_SAFE_HEIGHT);
    Serial.println("OK");
  }
  else if (command.startsWith("GOTO")) {
    // Formato: "GOTO x y z"
    int params[3];
    int paramIndex = 0;
    int cmdIndex = 5; // Após "GOTO "
    
    // Extrair parâmetros
    while (cmdIndex < command.length() && paramIndex < 3) {
      int spacePos = command.indexOf(' ', cmdIndex);
      if (spacePos == -1) spacePos = command.length();
      
      params[paramIndex++] = command.substring(cmdIndex, spacePos).toInt();
      cmdIndex = spacePos + 1;
    }
    
    if (paramIndex == 3) {
      moveToPosition(params[0], params[1], params[2]);
      Serial.println("OK");
    } else {
      Serial.println("ERROR: Invalid parameters");
    }
  }
  else if (command == "MAGNET ON") {
    digitalWrite(ELECTROMAGNET_PIN, HIGH);
    Serial.println("OK");
  }
  else if (command == "MAGNET OFF") {
    digitalWrite(ELECTROMAGNET_PIN, LOW);
    Serial.println("OK");
  }
  else if (command == "STATUS") {
    // Enviar estado atual do sistema
    Serial.print("STATUS X:");
    Serial.print(currentX);
    Serial.print(" Y:");
    Serial.print(currentY);
    Serial.print(" Z:");
    Serial.print(currentZ);
    Serial.print(" MAGNET:");
    Serial.print(digitalRead(ELECTROMAGNET_PIN) ? "ON" : "OFF");
    Serial.print(" READY:");
    Serial.println(systemReady ? "YES" : "NO");
  }
  else {
    Serial.println("ERROR: Unknown command");
  }
}

void movePiece(int fromX, int fromY, int toX, int toY) {
  // Converter coordenadas de tabuleiro para mm
  int x1 = fromX * CHESS_SQUARE_SIZE + CHESS_SQUARE_SIZE/2;
  int y1 = fromY * CHESS_SQUARE_SIZE + CHESS_SQUARE_SIZE/2;
  int x2 = toX * CHESS_SQUARE_SIZE + CHESS_SQUARE_SIZE/2;
  int y2 = toY * CHESS_SQUARE_SIZE + CHESS_SQUARE_SIZE/2;
  
  // Verificar se o destino é uma casa ocupada que precisa ser removida
  // (Implementar quando necessário - remover a peça capturada primeiro)
  
  // Sequência de movimentos para mover a peça
  // 1. Mover para a posição de origem (acima da peça)
  moveToPosition(x1, y1, Z_SAFE_HEIGHT);
  
  // 2. Descer para pegar a peça
  moveZ(Z_PICKUP_HEIGHT);
  
  // 3. Ativar eletroímã
  digitalWrite(ELECTROMAGNET_PIN, HIGH);
  delay(300); // Tempo para magnetização
  
  // 4. Levantar com a peça
  moveZ(Z_SAFE_HEIGHT);
  
  // 5. Mover para a posição de destino
  moveToPosition(x2, y2, Z_SAFE_HEIGHT);
  
  // 6. Descer para soltar a peça
  moveZ(Z_PICKUP_HEIGHT);
  
  // 7. Desativar eletroímã
  digitalWrite(ELECTROMAGNET_PIN, LOW);
  delay(300);
  
  // 8. Levantar novamente
  moveZ(Z_SAFE_HEIGHT);
}

void moveToPosition(int x, int y, int z) {
  // Verificar limites (adicionar verificação de limites se necessário)
  
  // Verificar se precisamos mover o Z primeiro para garantir altura segura
  if (z > currentZ) {
    moveZ(z);
  }
  
  // Mover X e Y simultaneamente
  long positions[2];
  positions[0] = x * STEPS_PER_MM;
  positions[1] = y * STEPS_PER_MM;
  steppers.moveTo(positions);
  steppers.runSpeedToPosition();
  
  // Atualizar posição atual
  currentX = x;
  currentY = y;
  
  // Mover Z para a altura final desejada (se ainda não moveu)
  if (z <= currentZ) {
    moveZ(z);
  }
}

void moveZ(int z) {
  long steps = z * STEPS_PER_MM;
  stepperZ.moveTo(steps);
  while (stepperZ.distanceToGo() != 0) {
    stepperZ.run();
  }
  currentZ = z;
}

void homeAxes() {
  // Esta função implementa o retorno aos sensores fim-de-curso
  
  // Se tiver sensores de fim de curso:
  // 1. Mover Z para cima primeiro por segurança
  moveZ(Z_SAFE_HEIGHT); 
  
  // 2. Home X
  while (digitalRead(X_MIN_PIN) == HIGH && !emergencyStop) {
    stepperX.moveTo(stepperX.currentPosition() - 10);
    stepperX.run();
  }
  
  // 3. Home Y
  while (digitalRead(Y_MIN_PIN) == HIGH && !emergencyStop) {
    stepperY.moveTo(stepperY.currentPosition() - 10);
    stepperY.run();
  }
  
  // 4. Home Z (opcional)
  while (digitalRead(Z_MIN_PIN) == HIGH && !emergencyStop) {
    stepperZ.moveTo(stepperZ.currentPosition() - 5);
    stepperZ.run();
  }
  
  // Reiniciar contagem de passos
  if (!emergencyStop) {
    stepperX.setCurrentPosition(0);
    stepperY.setCurrentPosition(0);
    stepperZ.setCurrentPosition(0);
    currentX = 0;
    currentY = 0;
    currentZ = 0;
  }
  
  // Mover para uma posição segura após homing
  moveZ(Z_SAFE_HEIGHT);
}

// Função alternativa de homing para sistemas sem sensores de fim de curso
void homeAxesManual() {
  // Para sistemas sem sensores, apenas redefinimos a posição atual como zero
  stepperX.setCurrentPosition(0);
  stepperY.setCurrentPosition(0);
  stepperZ.setCurrentPosition(0);
  currentX = 0;
  currentY = 0;
  currentZ = 0;
  
  // Mover Z para posição segura
  moveZ(Z_SAFE_HEIGHT);
} 