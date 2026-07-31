"""Configuração da montagem física do robô.

Estes valores dependem da câmera, do firmware e da geometria da CNC.
Após qualquer alteração, teste os movimentos sem peças e com o eletroímã
desligado antes de executar uma partida completa.
"""

# Câmera
CAMERA_INDEX = 1
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 30
CAMERA_BUFFER_SIZE = 1
CAMERA_AUTO_EXPOSURE = 0.25
CAMERA_ROTATE_180 = True
CAMERA_BUFFER_FLUSH_FRAMES = 3
CAMERA_CAPTURE_PATH = "assets/current_board.jpg"

# Comunicação serial
SERIAL_PORT = None
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 1
SERIAL_STARTUP_DELAY = 2
SERIAL_COMMAND_TIMEOUT = 30
SERIAL_RESPONSE_DELAY = 0.1
SERIAL_POLL_INTERVAL = 0.01
SERIAL_PROBE_POLL_INTERVAL = 0.05
SERIAL_PROBE_COMMAND = "?"
SERIAL_FALLBACK_PORTS = (
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "/dev/ttyUSB0",
    "/dev/ttyUSB1",
    "/dev/ttyACM0",
    "/dev/ttyACM1",
)
FIRMWARE_SIGNATURES = (
    "Servo",
    "Eletroímã",
    "Electromagnet",
    "Arduino CNC",
)

# Arduino dos botões físicos
BUTTONS_SERIAL_PORT = None
BUTTONS_SERIAL_BAUDRATE = 9600
BUTTONS_SERIAL_TIMEOUT = 0.1
BUTTONS_STARTUP_DELAY = 2
BUTTONS_POLL_INTERVAL = 0.01
BUTTON_EVENT_PREFIX = "BUTTON_"

# Comandos aceitos pelo firmware instalado no robô
CNC_INITIALIZATION_COMMANDS = (
    "G21",
    "G90",
    "G92 X0 Y0",
)
SERVO_UP_COMMAND = "S25"
SERVO_DOWN_COMMAND = "S0"
ELECTROMAGNET_ON_COMMAND = "M3"
ELECTROMAGNET_OFF_COMMAND = "M4"

# Movimento e manipulação
CNC_FEED_RATE = 1500
PIECE_HANDLING_DELAY = 1
CNC_NONBLOCKING_MOVE_DELAY = 1
CNC_HOME_POSITION = 0

# Coordenadas absolutas da montagem atual
CNC_POSITIONS = {
    0: (0.000, 0.000),
    1: (16.564, -4.908),
    2: (31.964, -8.988),
    3: (47.500, -13.256),
    4: (63.824, -17.028),
    5: (1.172, -8.844),
    6: (16.332, -13.288),
    7: (30.960, -17.288),
    8: (47.328, -21.020),
    9: (-15.844, -13.008),
    10: (-0.752, -17.700),
    11: (15.984, -20.952),
    12: (31.528, -25.340),
    13: (-32.624, -16.596),
    14: (-15.764, -21.048),
    15: (-0.532, -25.076),
    16: (15.260, -29.476),
    17: (-58.624, -13.596),
    18: (-46.624, -11.096),
    19: (-35.624, -8.096),
    20: (28.260, -36.976),
    21: (39.260, -33.976),
    22: (52.260, -30.976),
}

# Casas 17–19 e 20–22 recebem as peças capturadas
GRAVEYARD_LEFT_START = 17
GRAVEYARD_LEFT_END = 19
GRAVEYARD_RIGHT_START = 20
GRAVEYARD_RIGHT_END = 22
