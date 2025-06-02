#include <Servo.h>

Servo myServo;
String inputString = "";
boolean stringComplete = false;

// Configurações do servo
const int SERVO_PIN = 11;
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;

// Relé conectado ao SpnDir (pino digital 13)
const int RELAY_PIN = 13;
bool electromagnetState = false;

// Posições do servo
int currentServoPosition = 0;
int targetServoPosition = 0;
const int SERVO_SPEED = 5;  // Reduzido para movimento mais suave
const int SERVO_DELAY = 15; // Aumentado para dar mais tempo entre passos

// Controle de estado do servo
bool servoAttached = false;
bool servoMoving = false;
unsigned long servoLastMoveTime = 0;
const unsigned long SERVO_DETACH_DELAY = 1000; // 1 segundo após parar de mover

// Configurações dos motores de passo
const int STEP_X = 3;
const int DIR_X = 6;
const int STEP_Y = 2;
const int DIR_Y = 5;
const int ENABLE = 8;

long currentX = 0;
long currentY = 0;

const float STEPS_PER_MM = 80.0;
int feedRate = 1500;

void setup() {
  Serial.begin(115200);
  
  // NÃO anexa o servo no início
  pinMode(SERVO_PIN, OUTPUT);
  digitalWrite(SERVO_PIN, LOW); // Garante que o pino está em LOW
  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Garante que o relé começa desligado

  pinMode(STEP_X, OUTPUT);
  pinMode(DIR_X, OUTPUT);
  pinMode(STEP_Y, OUTPUT);
  pinMode(DIR_Y, OUTPUT);
  pinMode(ENABLE, OUTPUT);
  digitalWrite(ENABLE, HIGH);
  
  Serial.println("Arduino CNC + Servo + Eletroímã Controller");
  Serial.println("Comandos suportados:");
  Serial.println("  G1 X<pos> Y<pos> F<feed> - Movimento linear");
  Serial.println("  G28 - Home (X0 Y0)");
  Serial.println("  G92 X<pos> Y<pos> - Define posição atual");
  Serial.println("  M3 S<valor> - Liga servo (S0-S1000) ou eletroímã (S1)");
  Serial.println("  M4 - Desliga eletroímã");
  Serial.println("  M5 - Desliga servo");
  Serial.println("  ? - Status");
  Serial.println("ok");
  
  inputString.reserve(200);
}

void loop() {
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }

  // Gerencia movimento do servo de forma otimizada
  manageServoMovement();
}

void manageServoMovement() {
  if (currentServoPosition != targetServoPosition) {
    // Se o servo não estiver anexado, anexa agora
    if (!servoAttached) {
      myServo.attach(SERVO_PIN);
      servoAttached = true;
      delay(50); // Pequeno delay para estabilização
    }
    
    servoMoving = true;
    servoLastMoveTime = millis();
    
    // Movimento mais suave do servo
    int diff = abs(targetServoPosition - currentServoPosition);
    
    if (diff <= SERVO_SPEED) {
      currentServoPosition = targetServoPosition;
    } else {
      currentServoPosition += (currentServoPosition < targetServoPosition) ? SERVO_SPEED : -SERVO_SPEED;
    }
    
    myServo.write(currentServoPosition);
    delay(SERVO_DELAY);
    
  } else if (servoMoving) {
    // Servo chegou na posição final
    servoMoving = false;
    servoLastMoveTime = millis();
  }
  
  // Desanexa o servo após período de inatividade para economizar energia e evitar danos
  if (servoAttached && !servoMoving && 
      (millis() - servoLastMoveTime > SERVO_DETACH_DELAY)) {
    myServo.detach();
    servoAttached = false;
    pinMode(SERVO_PIN, OUTPUT);
    digitalWrite(SERVO_PIN, LOW); // Garante que o pino fica em LOW
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();

  Serial.print("Recebido: ");
  Serial.println(command);

  if (command.startsWith("G1")) {
    float targetX = currentX / STEPS_PER_MM;
    float targetY = currentY / STEPS_PER_MM;

    int xIndex = command.indexOf('X');
    int yIndex = command.indexOf('Y');
    int fIndex = command.indexOf('F');

    if (xIndex >= 0) targetX = extractFloatValue(command, xIndex + 1);
    if (yIndex >= 0) targetY = extractFloatValue(command, yIndex + 1);
    if (fIndex >= 0) feedRate = extractFloatValue(command, fIndex + 1);

    moveToPosition(targetX, targetY);
    Serial.println("ok");
  }

  else if (command.equals("G28")) {
    moveToPosition(0, 0);
    Serial.println("Home completed");
    Serial.println("ok");
  }

  else if (command.startsWith("G92")) {
    int xIndex = command.indexOf('X');
    int yIndex = command.indexOf('Y');
    if (xIndex >= 0) currentX = extractFloatValue(command, xIndex + 1) * STEPS_PER_MM;
    if (yIndex >= 0) currentY = extractFloatValue(command, yIndex + 1) * STEPS_PER_MM;
    Serial.println("Position set");
    Serial.println("ok");
  }

  else if (command.startsWith("M3")) {
    int sValue = extractSValue(command);

    if (sValue == 1) {
      digitalWrite(RELAY_PIN, HIGH);  // Liga eletroímã
      electromagnetState = true;
      Serial.println("Eletroímã ligado");
    } else if (sValue >= 0) {
      targetServoPosition = map(sValue, 0, 1000, SERVO_MIN, SERVO_MAX);
      targetServoPosition = constrain(targetServoPosition, SERVO_MIN, SERVO_MAX);
      Serial.print("Servo para: ");
      Serial.print(targetServoPosition);
      Serial.println(" graus");
    }
    Serial.println("ok");
  }

  else if (command.equals("M4")) {
    digitalWrite(RELAY_PIN, LOW);  // Desliga eletroímã
    electromagnetState = false;
    Serial.println("Eletroímã desligado");
    Serial.println("ok");
  }

  else if (command.equals("M5")) {
    targetServoPosition = SERVO_MIN;
    Serial.println("Servo desligando...");
    // Força o desanexo imediato do servo após chegar na posição
    servoLastMoveTime = millis() - SERVO_DETACH_DELAY - 1;
    Serial.println("ok");
  }

  else if (command.equals("?")) {
    Serial.print("X:");
    Serial.print(currentX / STEPS_PER_MM, 3);
    Serial.print(" Y:");
    Serial.print(currentY / STEPS_PER_MM, 3);
    Serial.print(" Servo:");
    Serial.print(currentServoPosition);
    Serial.print(" graus (");
    Serial.print(servoAttached ? "ATIVO" : "DESCANSO");
    Serial.print(") Eletroímã:");
    Serial.println(electromagnetState ? "LIGADO" : "DESLIGADO");
    Serial.println("ok");
  }

  else {
    Serial.println("ok");
  }
}

void moveToPosition(float targetXmm, float targetYmm) {
  digitalWrite(ENABLE, LOW);

  long targetXsteps = targetXmm * STEPS_PER_MM;
  long targetYsteps = targetYmm * STEPS_PER_MM;
  
  long deltaX = targetXsteps - currentX;
  long deltaY = targetYsteps - currentY;

  digitalWrite(DIR_X, deltaX >= 0 ? HIGH : LOW);
  digitalWrite(DIR_Y, deltaY >= 0 ? LOW : HIGH);

  deltaX = abs(deltaX);
  deltaY = abs(deltaY);

  int stepDelay = calculateStepDelay(feedRate);
  long maxSteps = max(deltaX, deltaY);

  for (long i = 0; i < maxSteps; i++) {
    if (i * deltaX < maxSteps * deltaX) {
      digitalWrite(STEP_X, HIGH); delayMicroseconds(1); digitalWrite(STEP_X, LOW);
    }

    if (i * deltaY < maxSteps * deltaY) {
      digitalWrite(STEP_Y, HIGH); delayMicroseconds(1); digitalWrite(STEP_Y, LOW);
    }

    delayMicroseconds(stepDelay);
  }

  currentX = targetXsteps;
  currentY = targetYsteps;

  Serial.print("Moved to X:");
  Serial.print(targetXmm, 3);
  Serial.print(" Y:");
  Serial.println(targetYmm, 3);
  
  delay(100);
  digitalWrite(ENABLE, HIGH);
}

int calculateStepDelay(int feedRateMMperMin) {
  float stepsPerSec = (feedRateMMperMin * STEPS_PER_MM) / 60.0;
  return (1000000.0 / stepsPerSec);
}

float extractFloatValue(String command, int startIndex) {
  String valueStr = "";
  for (int i = startIndex; i < command.length(); i++) {
    char c = command.charAt(i);
    if (isDigit(c) || c == '.' || c == '-') valueStr += c;
    else break;
  }
  return valueStr.toFloat();
}

int extractSValue(String command) {
  int sIndex = command.indexOf('S');
  if (sIndex >= 0) {
    String sString = command.substring(sIndex + 1);
    for (int i = 0; i < sString.length(); i++) {
      if (!isDigit(sString.charAt(i))) {
        sString = sString.substring(0, i);
        break;
      }
    }
    return sString.toInt();
  }
  return -1;
}