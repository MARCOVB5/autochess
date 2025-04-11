import pygame
import sys
import numpy as np
import pickle
import os
import time
from minichess import MiniChess
from ai_player import MiniChessAI
import cv2
import serial
import threading

# Inicialização do Pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (247, 247, 105)
GREEN = (0, 200, 0)

# Configurações da tela
WIDTH, HEIGHT = 1200, 800
BOARD_SIZE = 500
SQUARE_SIZE = BOARD_SIZE // 4
PIECE_SIZE = SQUARE_SIZE - 10
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini Chess 4x4 com IA de Aprendizado")

# Configurações de animação
ANIMATION_SPEED = 10  # Quanto maior, mais rápida a animação
ANIMATION_FRAMES = 10  # Número de frames para animar o movimento

# Configurações do CNC
CNC_ENABLED = False  # Altere para True quando o hardware estiver conectado
CNC_PORT = '/dev/ttyACM0'  # Porta serial do Arduino (ajuste conforme necessário)
CNC_BAUDRATE = 9600
CNC_SQUARE_SIZE = 50  # Tamanho em mm de cada casa no tabuleiro físico
CNC_HOME_ON_START = True  # Se deve fazer homing ao iniciar
CNC_TIMEOUT = 60  # Timeout para operações do CNC (em segundos)

# Variáveis globais do CNC
cnc_arduino = None
cnc_lock = threading.Lock()  # Para operações thread-safe no Arduino
cnc_connected = False
cnc_calibrated = False

# Carregar e redimensionar imagens das peças
piece_images = {}
# Mapeamento de peças para nomes de arquivos
piece_filenames = {
    'p': 'black-pawn.png',
    'r': 'black-rook.png',
    'q': 'black-queen.png',
    'k': 'black-king.png',
    'P': 'white-pawn.png',
    'R': 'white-rook.png',
    'Q': 'white-queen.png',
    'K': 'white-king.png'
}

def load_piece_images():
    for piece, filename in piece_filenames.items():
        try:
            img = pygame.image.load(f"assets/{filename}")
            piece_images[piece] = pygame.transform.scale(img, (PIECE_SIZE, PIECE_SIZE))
        except FileNotFoundError:
            print(f"Erro: Imagem para a peça {piece} ({filename}) não encontrada")
            continue

def draw_board(selected_square=None, valid_moves=None):
    # Desenha o tabuleiro
    for row in range(4):
        for col in range(4):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            
            # Destaca a casa selecionada
            if selected_square and selected_square[0] == row and selected_square[1] == col:
                color = HIGHLIGHT
            # Destaca movimentos válidos
            elif valid_moves and (row, col) in valid_moves:
                pygame.draw.rect(screen, color, (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                                               row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                                               SQUARE_SIZE, SQUARE_SIZE))
                # Círculo para indicar movimento válido
                pygame.draw.circle(screen, GREEN, 
                                 (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + SQUARE_SIZE // 2, 
                                  row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + SQUARE_SIZE // 2), 
                                 10)
                continue
                
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2, 
                                           row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2, 
                                           SQUARE_SIZE, SQUARE_SIZE))

def draw_pieces(board):
    """
    Desenha todas as peças no tabuleiro
    O parâmetro board deve ser a matriz de peças (não o objeto MiniChess)
    """
    for row in range(4):
        for col in range(4):
            piece = board[row][col]
            if piece != '.':
                if piece in piece_images:  # Verifica se a imagem existe
                    x = col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    y = row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                    screen.blit(piece_images[piece], (x, y))
                else:
                    print(f"Imagem para peça {piece} não carregada")

def animate_move(chess_game, from_pos, to_pos):
    """Anima o movimento de uma peça de from_pos para to_pos"""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Obtém a peça que foi movida (já está na posição de destino)
    piece = chess_game.board[to_row][to_col]
    
    # Configuração da animação
    clock = pygame.time.Clock()
    
    # Animação
    for frame in range(ANIMATION_FRAMES + 1):
        progress = frame / ANIMATION_FRAMES
        
        # Calcular a posição de interpolação
        start_x = from_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        start_y = from_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_x = to_col * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        end_y = to_row * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
        
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # Desenha o tabuleiro e as peças
        screen.fill(WHITE)
        draw_board()
        
        # Desenha todas as peças, exceto a que está sendo animada
        for r in range(4):
            for c in range(4):
                p = chess_game.board[r][c]
                if p != '.' and not (r == to_row and c == to_col):  # Não desenhar a peça que está sendo animada
                    if p in piece_images:
                        x = c * SQUARE_SIZE + (WIDTH - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        y = r * SQUARE_SIZE + (HEIGHT - BOARD_SIZE) // 2 + (SQUARE_SIZE - PIECE_SIZE) // 2
                        screen.blit(piece_images[p], (x, y))
        
        # Desenha a peça animada
        if piece in piece_images:
            screen.blit(piece_images[piece], (current_x, current_y))
        
        # Desenha os elementos da interface
        draw_reset_button()
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        pygame.display.flip()
        clock.tick(60)

def draw_reset_button():
    button_rect = pygame.Rect(WIDTH - 280, HEIGHT - 60, 250, 40)
    pygame.draw.rect(screen, (100, 100, 255), button_rect)
    pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
    
    font = pygame.font.SysFont(None, 36)
    text = font.render("Resetar IA", True, (0, 0, 0))
    screen.blit(text, (WIDTH - 230, HEIGHT - 50))
    
    return button_rect

def show_game_over(message):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    font = pygame.font.SysFont(None, 64)
    text = font.render(message, True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(text, text_rect)
    
    font_small = pygame.font.SysFont(None, 32)
    restart_text = font_small.render("Clique para jogar novamente", True, (255, 255, 255))
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(restart_text, restart_rect)
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False

def display_ai_strength(ai_player):
    font = pygame.font.SysFont(None, 36)
    text = font.render(f"Força da IA: {ai_player.get_strength_description()}", True, (0, 0, 0))
    screen.blit(text, (40, HEIGHT - 60))

def display_current_player(current_player):
    player_text = "Sua vez (brancas)" if current_player == 'w' else "Vez da IA (pretas)"
    font = pygame.font.SysFont(None, 36)
    text = font.render(player_text, True, (0, 0, 0))
    screen.blit(text, (40, HEIGHT - 100))

def screen_coords_to_board(x, y):
    board_x = (WIDTH - BOARD_SIZE) // 2
    board_y = (HEIGHT - BOARD_SIZE) // 2
    
    if (x < board_x or x >= board_x + BOARD_SIZE or 
        y < board_y or y >= board_y + BOARD_SIZE):
        return None
    
    col = (x - board_x) // SQUARE_SIZE
    row = (y - board_y) // SQUARE_SIZE
    
    return (row, col)

class ChessBoardDetector:
    def __init__(self, camera_index=0, calibration_file=None):
        self.camera = cv2.VideoCapture(camera_index)
        self.board_corners = None  # Cantos do tabuleiro
        self.square_colors = {}    # Cores médias de cada casa
        self.piece_templates = {}  # Templates para reconhecimento das peças
        self.last_frame = None     # Último frame capturado
        
        if calibration_file and os.path.exists(calibration_file):
            self.load_calibration(calibration_file)
    
    def calibrate(self):
        """Calibra o detector para encontrar o tabuleiro e definir suas características"""
        ret, frame = self.camera.read()
        if not ret:
            return False
            
        # Converter para escala de cinza para detecção de bordas
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detectar tabuleiro (assumindo que é o maior quadrado na imagem)
        # Usar detector de bordas e encontrar contornos
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Encontrar o maior contorno quadrado
        max_area = 0
        board_contour = None
        
        for contour in contours:
            # Aproximar o contorno para um polígono
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Se tem 4 vértices e área considerável
            if len(approx) == 4:
                area = cv2.contourArea(approx)
                if area > max_area:
                    max_area = area
                    board_contour = approx
        
        if board_contour is None:
            return False
            
        # Ordenar os cantos (topo-esquerdo, topo-direito, base-direito, base-esquerdo)
        self.board_corners = self._sort_corners(board_contour.reshape(4, 2))
        
        # Capturar cores das casas vazias
        self._calibrate_empty_squares(frame)
        
        return True
    
    def _sort_corners(self, corners):
        """Ordena os 4 pontos em: topo-esquerdo, topo-direito, base-direito, base-esquerdo"""
        # Soma das coordenadas x+y
        s = corners.sum(axis=1)
        # Diferença das coordenadas x-y
        diff = np.diff(corners, axis=1)
        
        return np.array([
            corners[np.argmin(s)],     # Topo-esquerdo (menor soma)
            corners[np.argmin(diff)],  # Topo-direito (menor diferença)
            corners[np.argmax(s)],     # Base-direito (maior soma)
            corners[np.argmax(diff)]   # Base-esquerdo (maior diferença)
        ])
    
    def _calibrate_empty_squares(self, frame):
        """Captura as cores médias de cada casa vazia do tabuleiro"""
        # Aplica transformação de perspectiva para obter visão de topo do tabuleiro
        warped = self._warp_perspective(frame)
        
        # Divide o tabuleiro em 4x4 células
        height, width = warped.shape[:2]
        cell_h, cell_w = height // 4, width // 4
        
        for row in range(4):
            for col in range(4):
                x, y = col * cell_w, row * cell_h
                # Região central da célula para evitar bordas
                cell = warped[y+10:y+cell_h-10, x+10:x+cell_w-10]
                # Cor média da célula
                avg_color = np.mean(cell, axis=(0, 1))
                self.square_colors[(row, col)] = avg_color
    
    def _warp_perspective(self, frame):
        """Aplica transformação de perspectiva para obter visão de topo do tabuleiro"""
        # Definir pontos de destino (tabuleiro de visão superior 400x400 pixels)
        dst_points = np.array([
            [0, 0],           # Topo-esquerdo
            [400, 0],         # Topo-direito
            [400, 400],       # Base-direito
            [0, 400]          # Base-esquerdo
        ], dtype=np.float32)
        
        # Calcular matriz de transformação
        M = cv2.getPerspectiveTransform(self.board_corners.astype(np.float32), dst_points)
        
        # Aplicar transformação
        warped = cv2.warpPerspective(frame, M, (400, 400))
        return warped
    
    def load_piece_templates(self, template_dir):
        """Carrega imagens de modelo para cada tipo de peça"""
        for piece in ['P', 'R', 'Q', 'K', 'p', 'r', 'q', 'k']:
            path = os.path.join(template_dir, f"{piece}_template.png")
            if os.path.exists(path):
                self.piece_templates[piece] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    
    def get_board_state(self):
        """Captura o estado atual do tabuleiro e retorna a representação interna"""
        ret, frame = self.camera.read()
        if not ret or self.board_corners is None:
            return None
        
        self.last_frame = frame.copy()  # Salvar o último frame capturado
            
        # Aplicar transformação de perspectiva
        warped = self._warp_perspective(frame)
        
        # Preparar matriz para o estado do tabuleiro
        board_state = [['.' for _ in range(4)] for _ in range(4)]
        
        # Dividir o tabuleiro em células 4x4
        height, width = warped.shape[:2]
        cell_h, cell_w = height // 4, width // 4
        
        for row in range(4):
            for col in range(4):
                x, y = col * cell_w, row * cell_h
                cell = warped[y:y+cell_h, x:x+cell_w]
                
                # Detectar se há peça nesta célula
                piece = self._detect_piece(cell, row, col)
                if piece:
                    board_state[row][col] = piece
        
        return board_state
    
    def _detect_piece(self, cell_img, row, col):
        """Detecta qual peça está presente na célula ou retorna None se vazia"""
        # Converter para HSV para melhor segmentação por cor
        cell_hsv = cv2.cvtColor(cell_img, cv2.COLOR_BGR2HSV)
        
        # Verificar se há objeto na célula comparando com a cor calibrada
        empty_color = self.square_colors.get((row, col))
        if empty_color is None:
            return None
            
        # Calcular diferença média de cor
        current_color = np.mean(cell_img, axis=(0, 1))
        color_diff = np.sum(np.abs(current_color - empty_color))
        
        # Se a diferença for pequena, a célula está vazia
        if color_diff < 30:  # Ajuste esse limiar conforme necessário
            return None
            
        # Determinar se é peça branca ou preta
        # (uma abordagem simples é usar o brilho médio)
        brightness = np.mean(cell_img)
        color = 'w' if brightness > 127 else 'b'
        
        # Identificar o tipo de peça usando template matching
        # Isso é uma simplificação - na prática você precisaria de um 
        # algoritmo mais robusto de reconhecimento de objetos
        
        cell_gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        best_match = None
        best_score = float('-inf')
        
        for piece, template in self.piece_templates.items():
            if (piece.isupper() and color == 'w') or (piece.islower() and color == 'b'):
                # Redimensionar o template para o tamanho da célula
                resized_template = cv2.resize(template, (cell_gray.shape[1], cell_gray.shape[0]))
                
                # Aplicar template matching
                res = cv2.matchTemplate(cell_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                score = np.max(res)
                
                if score > best_score:
                    best_score = score
                    best_match = piece
        
        # Se o score for muito baixo, não conseguimos identificar a peça com confiança
        if best_score < 0.4:  # Ajuste esse limiar conforme necessário
            return 'P' if color == 'w' else 'p'  # Assume peão como padrão
            
        return best_match
    
    def save_calibration(self, filename):
        """Salva dados de calibração para uso futuro"""
        data = {
            'board_corners': self.board_corners,
            'square_colors': self.square_colors
        }
        np.save(filename, data)
    
    def load_calibration(self, filename):
        """Carrega dados de calibração salvos anteriormente"""
        data = np.load(filename, allow_pickle=True).item()
        self.board_corners = data['board_corners']
        self.square_colors = data['square_colors']
    
    def release(self):
        """Libera a câmera"""
        self.camera.release()
    
    def capture_piece_template(self, piece_type):
        """Captura uma imagem para ser usada como template para uma peça específica"""
        if self.board_corners is None:
            print("Tabuleiro não calibrado. Calibre primeiro.")
            return False
        
        ret, frame = self.camera.read()
        if not ret:
            return False
        
        # Aplicar transformação de perspectiva
        warped = self._warp_perspective(frame)
        
        # Dividir o tabuleiro em células 4x4
        height, width = warped.shape[:2]
        cell_h, cell_w = height // 4, width // 4
        
        # Criar diretório para templates se não existir
        os.makedirs("assets/templates", exist_ok=True)
        
        # Salvar imagem para o usuário selecionar a região da peça manualmente
        timestamp = int(time.time())
        template_path = f"assets/templates/template_select_{timestamp}.png"
        cv2.imwrite(template_path, warped)
        
        print(f"Imagem para seleção de template salva em {template_path}")
        print(f"Por favor, abra esta imagem e recorte a região contendo apenas a peça {piece_type}")
        print(f"Em seguida, salve como assets/templates/{piece_type}_template.png")
        
        return True

def setup_cnc():
    """Configura a comunicação com o Arduino para controle do CNC"""
    global cnc_arduino, cnc_connected
    
    if not CNC_ENABLED:
        print("Sistema CNC desabilitado nas configurações")
        return False
    
    try:
        # Inicializar comunicação serial com o Arduino
        cnc_arduino = serial.Serial(CNC_PORT, CNC_BAUDRATE, timeout=CNC_TIMEOUT)
        time.sleep(2)  # Aguardar inicialização do Arduino
        
        # Testar comunicação
        cnc_arduino.write(b"PING\n")
        response = cnc_arduino.readline().decode().strip()
        
        if response == "PONG":
            print("Comunicação com CNC estabelecida")
            cnc_connected = True
            
            # Executar homing se necessário
            if CNC_HOME_ON_START:
                cnc_home()
                
            return True
        else:
            print(f"Erro na comunicação com CNC. Resposta: {response}")
            cnc_arduino.close()
            cnc_connected = False
            return False
            
    except Exception as e:
        print(f"Erro ao conectar ao Arduino CNC: {str(e)}")
        cnc_connected = False
        return False

def cnc_home():
    """Executa procedimento de homing do CNC"""
    global cnc_calibrated
    
    if not cnc_connected:
        print("CNC não conectado")
        return False
    
    try:
        with cnc_lock:
            cnc_arduino.write(b"HOME\n")
            response = cnc_arduino.readline().decode().strip()
            
            if response == "OK":
                print("Homing do CNC concluído com sucesso")
                cnc_calibrated = True
                return True
            else:
                print(f"Erro no homing do CNC: {response}")
                return False
    except Exception as e:
        print(f"Erro durante homing do CNC: {str(e)}")
        return False

def cnc_send_command(command):
    """Envia comando para o Arduino CNC e retorna a resposta"""
    if not cnc_connected:
        print("CNC não conectado")
        return "ERROR: Not connected"
    
    try:
        with cnc_lock:
            cnc_arduino.write(f"{command}\n".encode())
            response = cnc_arduino.readline().decode().strip()
            return response
    except Exception as e:
        print(f"Erro ao enviar comando ao CNC: {str(e)}")
        return f"ERROR: {str(e)}"

def move_physical_piece(from_pos, to_pos):
    """
    Função para controlar o braço CNC via Arduino para mover a peça no tabuleiro físico.
    """
    print(f"Movendo peça física de {from_pos} para {to_pos}")
    
    # Se o CNC não estiver habilitado, apenas simula o movimento
    if not CNC_ENABLED or not cnc_connected:
        print("Sistema CNC não disponível. Simulando movimento...")
        time.sleep(1)  # Simular tempo de movimento
        return True
    
    # Verificar se o CNC está calibrado
    if not cnc_calibrated:
        print("CNC não calibrado. Realizando homing...")
        if not cnc_home():
            print("Falha no homing. Não é possível mover a peça.")
            return False
    
    try:
        # Converter coordenadas do tabuleiro (0-3) para coordenadas físicas
        from_y, from_x = from_pos  # Atenção: no tabuleiro usamos (linha, coluna)
        to_y, to_x = to_pos
        
        # Enviar comando de movimento para o Arduino
        command = f"MOVE {from_x} {from_y} {to_x} {to_y}"
        response = cnc_send_command(command)
        
        if response == "OK":
            print("Movimento físico concluído com sucesso")
            return True
        else:
            print(f"Erro no movimento físico: {response}")
            return False
        
    except Exception as e:
        print(f"Erro na comunicação com o CNC: {str(e)}")
        return False

def cnc_reset():
    """Reseta o sistema CNC em caso de emergência"""
    if cnc_connected:
        try:
            with cnc_lock:
                cnc_arduino.write(b"RESET\n")
                time.sleep(1)
        except Exception as e:
            print(f"Erro ao resetar CNC: {str(e)}")

def cnc_shutdown():
    """Desativa o sistema CNC de forma segura"""
    global cnc_connected
    
    if cnc_connected:
        try:
            # Enviar comando para posição segura
            cnc_send_command("PARK")
            
            # Fechar comunicação
            with cnc_lock:
                cnc_arduino.close()
                cnc_connected = False
                print("Conexão com CNC encerrada")
        except Exception as e:
            print(f"Erro ao desativar CNC: {str(e)}")

def main():
    # Criar diretório de assets se não existir
    os.makedirs("assets", exist_ok=True)
    
    # Verificar e criar diretório para modelos da IA
    os.makedirs("models", exist_ok=True)
    
    # Inicializar o jogo
    chess_game = MiniChess()
    global ai_player
    ai_player = MiniChessAI()
    
    # Inicializar o detector de tabuleiro
    board_detector = ChessBoardDetector()
    camera_mode = True  # True para usar a câmera, False para jogar via interface gráfica
    calibration_done = False

    # Inicializar sistema CNC se habilitado
    if CNC_ENABLED:
        setup_cnc()
    
    # Inicializar o detector de tabuleiro
    try:
        # Verifica se a câmera está disponível
        board_detector = ChessBoardDetector()
        camera_available = board_detector.camera.isOpened()
        if not camera_available:
            print("Aviso: Câmera não disponível. Iniciando em modo interface.")
    except Exception as e:
        print(f"Erro ao inicializar câmera: {str(e)}")
        camera_available = False
    
    # Iniciar no modo interface por padrão
    camera_mode = False
    calibration_done = False
    
    # Carregar imagens das peças
    load_piece_images()
    
    selected_square = None
    valid_moves = []
    game_over = False
    reset_button = None
    last_physical_board_state = None
    
    # Botão para calibrar a câmera
    calibrate_button = pygame.Rect(WIDTH - 280, HEIGHT - 110, 250, 40)
    
    # Botão para alternar entre modo câmera e interface gráfica
    toggle_mode_button = pygame.Rect(WIDTH - 280, HEIGHT - 160, 250, 40)
    
    # Botão para visualizar a câmera
    view_camera_button = pygame.Rect(WIDTH - 280, HEIGHT - 210, 250, 40)
    show_camera_view = False
    
    # Botão para capturar template
    capture_template_button = pygame.Rect(WIDTH - 280, HEIGHT - 260, 250, 40)
    
    # Timer para atualização da visualização da câmera
    last_camera_update = 0
    camera_update_interval = 500  # milissegundos
    
    # Loop principal
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Salvar o modelo da IA antes de sair
                ai_player.save_model()
                if camera_mode:
                    board_detector.release()
                # Encerrar CNC de forma segura
                if CNC_ENABLED:
                    cnc_shutdown()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                
                # Verificar se o botão de calibrar foi clicado
                if calibrate_button.collidepoint(mouse_pos):
                    print("Calibrando câmera...")
                    if board_detector.calibrate():
                        calibration_done = True
                        print("Calibração concluída!")
                        board_detector.save_calibration("camera_calibration.npy")
                    else:
                        print("Falha na calibração. Tente novamente.")
                    continue
                
                # Verificar se o botão de reset foi clicado
                if reset_button and reset_button.collidepoint(mouse_pos):
                    ai_player.reset_model()
                    print("IA resetada!")
                    continue
                
                # Verificar se o botão de alternar modo foi clicado
                if toggle_mode_button.collidepoint(mouse_pos):
                    camera_mode = not camera_mode
                    print(f"Modo {'câmera' if camera_mode else 'interface'} ativado")
                    continue
                
                # Verificar se o botão de visualizar câmera foi clicado
                if view_camera_button.collidepoint(mouse_pos):
                    show_camera_view = not show_camera_view
                    print(f"Visualização da câmera {'ativada' if show_camera_view else 'desativada'}")
                    continue
                
                # Verificar se o botão de capturar template foi clicado
                if capture_template_button.collidepoint(mouse_pos):
                    if not camera_mode or not calibration_done:
                        print("Modo de câmera deve estar ativado e calibrado para capturar templates")
                    else:
                        # Solicitar ao usuário qual peça quer capturar
                        piece_types = ['P', 'R', 'Q', 'K', 'p', 'r', 'q', 'k']
                        piece_names = {
                            'P': 'Peão Branco', 'R': 'Torre Branca', 'Q': 'Rainha Branca', 'K': 'Rei Branco',
                            'p': 'Peão Preto', 'r': 'Torre Preta', 'q': 'Rainha Preta', 'k': 'Rei Preto'
                        }
                        
                        # Mostrar opções de peças na tela
                        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        overlay.fill((0, 0, 0, 180))
                        screen.blit(overlay, (0, 0))
                        
                        font_title = pygame.font.SysFont(None, 40)
                        text_title = font_title.render("Selecione a peça para capturar o template:", True, (255, 255, 255))
                        screen.blit(text_title, (WIDTH//2 - text_title.get_width()//2, 100))
                        
                        font = pygame.font.SysFont(None, 30)
                        buttons = []
                        
                        # Criar botões para cada tipo de peça
                        for i, piece in enumerate(piece_types):
                            y_pos = 180 + i * 50
                            button_rect = pygame.Rect(WIDTH//2 - 120, y_pos, 240, 40)
                            pygame.draw.rect(screen, (100, 100, 220), button_rect)
                            pygame.draw.rect(screen, (255, 255, 255), button_rect, 2)
                            
                            text = font.render(piece_names[piece], True, (255, 255, 255))
                            screen.blit(text, (WIDTH//2 - text.get_width()//2, y_pos + 8))
                            
                            buttons.append((button_rect, piece))
                        
                        # Botão de cancelar
                        cancel_rect = pygame.Rect(WIDTH//2 - 80, 180 + len(piece_types) * 50 + 20, 160, 40)
                        pygame.draw.rect(screen, (220, 100, 100), cancel_rect)
                        pygame.draw.rect(screen, (255, 255, 255), cancel_rect, 2)
                        
                        cancel_text = font.render("Cancelar", True, (255, 255, 255))
                        screen.blit(cancel_text, (WIDTH//2 - cancel_text.get_width()//2, 180 + len(piece_types) * 50 + 28))
                        
                        pygame.display.flip()
                        
                        # Aguardar seleção
                        waiting_selection = True
                        while waiting_selection:
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    pygame.quit()
                                    sys.exit()
                                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                    mouse_pos = pygame.mouse.get_pos()
                                    
                                    if cancel_rect.collidepoint(mouse_pos):
                                        waiting_selection = False
                                        break
                                    
                                    for button, piece in buttons:
                                        if button.collidepoint(mouse_pos):
                                            print(f"Capturando template para {piece_names[piece]}...")
                                            if board_detector.capture_piece_template(piece):
                                                print(f"Template para {piece_names[piece]} capturado com sucesso!")
                                            else:
                                                print(f"Falha ao capturar template para {piece_names[piece]}")
                                            waiting_selection = False
                                            break
                    continue
            
            # Se não estiver usando a câmera, processar jogadas via interface
            if not camera_mode and not game_over and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and chess_game.current_player == 'w':
                    clicked_square = screen_coords_to_board(*mouse_pos)
                    
                    if clicked_square:
                        row, col = clicked_square
                        
                        # Se já tiver uma peça selecionada
                        if selected_square:
                            # Tentar mover a peça
                            move = (selected_square, clicked_square)
                            
                            # Verificar se o destino é um movimento válido
                            if clicked_square in valid_moves:
                                # Salvar a posição inicial para a animação
                                from_pos = selected_square
                                to_pos = clicked_square
                                
                                # Executar o movimento
                                success = chess_game.make_move(move)
                                if success:
                                    print(f"Movimento de {selected_square} para {clicked_square} realizado")
                                    # Animar o movimento
                                    animate_move(chess_game, from_pos, to_pos)
                                    # Verifica e imprime o tabuleiro após o movimento
                                    chess_game.print_board()
                                else:
                                    print(f"Movimento inválido: {selected_square} -> {clicked_square}")
                                
                                selected_square = None
                                valid_moves = []
                                
                                # Verificar se o jogo acabou após o movimento do jogador
                                if chess_game.is_king_captured():
                                    game_over = True
                                    capturou = chess_game.is_king_captured()
                                    if capturou == 'w':
                                        print("O jogador capturou o rei da IA!")
                                        ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                                        show_game_over("Você venceu!")
                                    else:
                                        print("A IA capturou o rei do jogador!")
                                        ai_player.learn(chess_game, 0)  # IA aprende com a vitória
                                        show_game_over("IA venceu!")
                                    
                                    # Reiniciar o jogo
                                    chess_game = MiniChess()
                                    game_over = False
                                elif chess_game.is_game_over():
                                    game_over = True
                                    
                                    if chess_game.is_checkmate():
                                        print("O jogador deu xeque-mate na IA!")
                                        ai_player.learn(chess_game, 0)  # IA aprende com a derrota
                                        show_game_over("Você venceu!")
                                    else:
                                        print("Empate (afogamento)!")
                                        ai_player.learn(chess_game, 0.5)  # Empate é neutro
                                        show_game_over("Empate!")
                                    
                                    # Reiniciar o jogo
                                    chess_game = MiniChess()
                                    game_over = False
                                else:
                                    # Vez da IA
                                    print("Vez da IA...")
                                    ai_move = ai_player.get_move(chess_game)
                                    
                                    if ai_move:
                                        origin, dest = ai_move
                                        print(f"IA move: {origin} -> {dest}")
                                        
                                        # Salvar para animação
                                        ai_from_pos = origin
                                        ai_to_pos = dest
                                        
                                        success = chess_game.make_move(ai_move)
                                        
                                        # Animar o movimento da IA
                                        if success:
                                            print(f"IA moveu de {origin} para {dest}")
                                            animate_move(chess_game, ai_from_pos, ai_to_pos)
                                            chess_game.print_board()
                                        
                                        # Verificar se o jogo acabou após o movimento da IA
                                        if chess_game.is_king_captured():
                                            game_over = True
                                            capturou = chess_game.is_king_captured()
                                            if capturou == 'w':
                                                print("O jogador capturou o rei da IA!")
                                                ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                                                show_game_over("Você venceu!")
                                            else:
                                                print("A IA capturou o rei do jogador!")
                                                ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                                                show_game_over("IA venceu!")
                                            
                                            # Reiniciar o jogo
                                            chess_game = MiniChess()
                                            game_over = False
                                        elif chess_game.is_game_over():
                                            game_over = True
                                            
                                            if chess_game.is_checkmate():
                                                # IA ganhou
                                                print("A IA deu xeque-mate no jogador!")
                                                ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                                                show_game_over("IA venceu!")
                                            else:
                                                # Empate
                                                print("Empate (afogamento)!")
                                                ai_player.learn(chess_game, 0.5)  # Empate é neutro
                                                show_game_over("Empate!")
                                            
                                            # Reiniciar o jogo
                                            chess_game = MiniChess()
                                            game_over = False
                                    else:
                                        print("IA não encontrou movimento válido")
                                        if chess_game.is_check('b'):
                                            print("IA está em xeque-mate!")
                                            ai_player.learn(chess_game, 0)  # IA aprende com a derrota
                                            show_game_over("Você venceu!")
                                            chess_game = MiniChess()
                                            game_over = False
                            else:
                                # Cancelar seleção ou selecionar nova peça
                                piece = chess_game.board[row][col]
                                if piece != '.' and chess_game.get_piece_color(piece) == 'w':
                                    selected_square = (row, col)
                                    valid_moves = chess_game.get_valid_moves(selected_square)
                                    print(f"Nova peça {piece} selecionada em {selected_square}. Movimentos válidos: {valid_moves}")
                                else:
                                    selected_square = None
                                    valid_moves = []
                        else:
                            # Selecionar peça
                            piece = chess_game.board[row][col]
                            if piece != '.' and chess_game.get_piece_color(piece) == 'w':
                                selected_square = (row, col)
                                valid_moves = chess_game.get_valid_moves(selected_square)
                                print(f"Peça {piece} selecionada em {selected_square}. Movimentos válidos: {valid_moves}")
        
        # Modo câmera - verifica se houve movimento no tabuleiro físico
        if camera_mode and calibration_done and chess_game.current_player == 'w' and not game_over:
            current_time = pygame.time.get_ticks()
            
            # Atualizar visualização da câmera periodicamente
            if show_camera_view and current_time - last_camera_update > camera_update_interval:
                # Verificar se a câmera está disponível
                if board_detector.camera.isOpened():
                    # Capturar frame sem detectar estado
                    ret, frame = board_detector.camera.read()
                    if ret:
                        board_detector.last_frame = frame.copy()
                    last_camera_update = current_time
                else:
                    # Se a câmera não estiver disponível, mostrar mensagem e desativar visualização
                    print("Câmera não disponível para visualização")
                    show_camera_view = False

            # Verificar mudanças no tabuleiro apenas quando não estamos apenas atualizando a visualização
            if current_time - last_camera_update > camera_update_interval * 0.8:
                # Verificar se a câmera está disponível
                if board_detector.camera.isOpened():
                    current_board_state = board_detector.get_board_state()
                else:
                    # Se a câmera não estiver disponível, desativar modo câmera
                    print("Câmera não disponível. Alternando para modo interface.")
                    camera_mode = False
            
            if current_board_state and last_physical_board_state:
                # Encontrar a diferença entre os estados
                move = detect_move(last_physical_board_state, current_board_state)
                
                if move:
                    from_pos, to_pos = move
                    print(f"Movimento detectado: {from_pos} -> {to_pos}")
                    
                    # Verificar se o movimento é válido
                    valid_pieces = []
                    for r in range(4):
                        for c in range(4):
                            piece = chess_game.board[r][c]
                            if piece != '.' and chess_game.get_piece_color(piece) == 'w':
                                valid_pieces.append((r, c))
                    
                    if from_pos in valid_pieces and to_pos in chess_game.get_valid_moves(from_pos):
                        # Executar o movimento
                        success = chess_game.make_move((from_pos, to_pos))
                        
                        if success:
                            print(f"Movimento de {from_pos} para {to_pos} realizado")
                            last_physical_board_state = current_board_state
                            
                            # Verificar se o jogo acabou após o movimento do jogador
                            if chess_game.is_king_captured():
                                game_over = True
                                capturou = chess_game.is_king_captured()
                                if capturou == 'w':
                                    print("O jogador capturou o rei da IA!")
                                    ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                                    show_game_over("Você venceu!")
                                else:
                                    print("A IA capturou o rei do jogador!")
                                    ai_player.learn(chess_game, 0)  # IA aprende com a vitória
                                    show_game_over("IA venceu!")
                                
                                # Reiniciar o jogo
                                chess_game = MiniChess()
                                game_over = False
                                last_physical_board_state = None
                            elif chess_game.is_game_over():
                                game_over = True
                                
                                if chess_game.is_checkmate():
                                    print("O jogador deu xeque-mate na IA!")
                                    ai_player.learn(chess_game, 0)  # IA aprende com a derrota
                                    show_game_over("Você venceu!")
                                else:
                                    print("Empate (afogamento)!")
                                    ai_player.learn(chess_game, 0.5)  # Empate é neutro
                                    show_game_over("Empate!")
                                
                                # Reiniciar o jogo
                                chess_game = MiniChess()
                                game_over = False
                                last_physical_board_state = None
                            else:
                                # Vez da IA
                                new_game = handle_ai_turn(chess_game, ai_player)
                                if new_game != chess_game:
                                    chess_game = new_game
                                    game_over = False
                                    last_physical_board_state = None
                        else:
                            print(f"Movimento inválido: {from_pos} -> {to_pos}")
                    else:
                        print("Movimento inválido detectado na câmera")
            
            # Se for o primeiro frame, apenas salvar o estado
            if not last_physical_board_state:
                last_physical_board_state = current_board_state
        
        # Desenhar o jogo
        screen.fill(WHITE)
        draw_board(selected_square, valid_moves)
        draw_pieces(chess_game.board)
        reset_button = draw_reset_button()
        
        # Desenhar botão de calibração
        pygame.draw.rect(screen, (100, 255, 100), calibrate_button)
        pygame.draw.rect(screen, (0, 0, 0), calibrate_button, 2)
        font = pygame.font.SysFont(None, 32)
        text = font.render("Calibrar Câmera", True, (0, 0, 0))
        screen.blit(text, (WIDTH - 230, HEIGHT - 100))
        
        # Desenhar botão de alternar modo
        pygame.draw.rect(screen, (255, 180, 100), toggle_mode_button)
        pygame.draw.rect(screen, (0, 0, 0), toggle_mode_button, 2)
        mode_text = font.render("Modo: " + ("Câmera" if camera_mode else "Interface"), True, (0, 0, 0))
        screen.blit(mode_text, (WIDTH - 250, HEIGHT - 150))
        
        # Desenhar botão de visualizar câmera
        pygame.draw.rect(screen, (180, 180, 255), view_camera_button)
        pygame.draw.rect(screen, (0, 0, 0), view_camera_button, 2)
        view_text = font.render("Visualizar Câmera", True, (0, 0, 0))
        screen.blit(view_text, (WIDTH - 230, HEIGHT - 200))
        
        # Desenhar botão de capturar template
        pygame.draw.rect(screen, (200, 150, 250), capture_template_button)
        pygame.draw.rect(screen, (0, 0, 0), capture_template_button, 2)
        template_text = font.render("Capturar Template", True, (0, 0, 0))
        screen.blit(template_text, (WIDTH - 230, HEIGHT - 250))
        
        # Mostrar status da câmera
        if camera_mode:
            status = "Calibrada" if calibration_done else "Não Calibrada"
            text = font.render(f"Câmera: {status}", True, (0, 0, 0))
            screen.blit(text, (40, HEIGHT - 140))
        
        display_ai_strength(ai_player)
        display_current_player(chess_game.current_player)
        
        # Mostrar visualização da câmera se ativado
        if show_camera_view and camera_mode:
            if board_detector.last_frame is not None:
                # Converter frame da câmera para formato Pygame
                frame = cv2.cvtColor(board_detector.last_frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (200, 150))
                pygame_frame = pygame.image.frombuffer(frame.tostring(), (200, 150), "RGB")
                screen.blit(pygame_frame, (20, 20))
                
                # Se calibrado, mostrar também a imagem com a transformação de perspectiva
                if calibration_done and board_detector.board_corners is not None:
                    warped = board_detector._warp_perspective(board_detector.last_frame)
                    warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
                    warped = cv2.resize(warped, (200, 200))
                    pygame_warped = pygame.image.frombuffer(warped.tostring(), (200, 200), "RGB")
                    screen.blit(pygame_warped, (230, 20))
        
        pygame.display.flip()
        clock.tick(30)

def detect_move(old_state, new_state):
    """Detecta qual movimento foi feito comparando dois estados do tabuleiro"""
    from_pos = None
    to_pos = None
    
    for row in range(4):
        for col in range(4):
            # Peça removida (movimento de origem)
            if old_state[row][col] != '.' and new_state[row][col] == '.':
                from_pos = (row, col)
            
            # Peça adicionada ou substituída (movimento de destino)
            if old_state[row][col] != new_state[row][col] and new_state[row][col] != '.':
                to_pos = (row, col)
    
    if from_pos and to_pos:
        return (from_pos, to_pos)
    
    return None

def handle_ai_turn(chess_game, ai_player):
    """Processa o turno da IA"""
    print("Vez da IA...")
    ai_move = ai_player.get_move(chess_game)
    
    if ai_move:
        origin, dest = ai_move
        print(f"IA move: {origin} -> {dest}")
        
        # Salvar para animação
        ai_from_pos = origin
        ai_to_pos = dest
        
        success = chess_game.make_move(ai_move)
        
        # Animar o movimento da IA
        if success:
            print(f"IA moveu de {origin} para {dest}")
            animate_move(chess_game, ai_from_pos, ai_to_pos)
            chess_game.print_board()
            
            # Aqui você adicionaria o código para controlar o braço CNC ou eletroimãs
            # para mover a peça no tabuleiro físico
            move_physical_piece(ai_from_pos, ai_to_pos)
        
        # Verificar se o jogo acabou após o movimento da IA
        if chess_game.is_king_captured():
            game_over = True
            capturou = chess_game.is_king_captured()
            if capturou == 'w':
                print("O jogador capturou o rei da IA!")
                ai_player.learn(chess_game, 1)  # Recompensa máxima para o jogador
                show_game_over("Você venceu!")
            else:
                print("A IA capturou o rei do jogador!")
                ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                show_game_over("IA venceu!")
            
            # Reiniciar o jogo
            return MiniChess()
        elif chess_game.is_game_over():
            game_over = True
            
            if chess_game.is_checkmate():
                # IA ganhou
                print("A IA deu xeque-mate no jogador!")
                ai_player.learn(chess_game, 1)  # Recompensa máxima para a IA
                show_game_over("IA venceu!")
            else:
                # Empate
                print("Empate (afogamento)!")
                ai_player.learn(chess_game, 0.5)  # Empate é neutro
                show_game_over("Empate!")
            
            # Reiniciar o jogo
            return MiniChess()
    else:
        print("IA não encontrou movimento válido")
        if chess_game.is_check('b'):
            print("IA está em xeque-mate!")
            ai_player.learn(chess_game, 0)  # IA aprende com a derrota
            show_game_over("Você venceu!")
            return MiniChess()
    
    return chess_game

# Código para o firmware do Arduino (salvar em um arquivo separado)
ARDUINO_FIRMWARE = """
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

// Configurações
#define STEPS_PER_MM 80  // Ajuste baseado na sua mecânica
#define CHESS_SQUARE_SIZE 50  // Tamanho de cada casa em mm

// Inicialização dos motores
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
MultiStepper steppers;

// Posição atual
int currentX = 0;
int currentY = 0;
int currentZ = 0;

void setup() {
  Serial.begin(9600);

  // Configurar pinos
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
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\\n');
    processCommand(command);
  }
}

void processCommand(String command) {
  // Responder ao ping para verificação de conexão
  if (command == "PING") {
    Serial.println("PONG");
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
    moveToPosition(0, 0, 50);
    Serial.println("OK");
  }
  else if (command == "RESET") {
    // Parar todos os motores
    stepperX.stop();
    stepperY.stop();
    stepperZ.stop();
    digitalWrite(ELECTROMAGNET_PIN, LOW);
    Serial.println("RESET OK");
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
  
  // 1. Mover para a posição de origem (acima da peça)
  moveToPosition(x1, y1, 20);
  
  // 2. Descer para pegar a peça
  moveZ(0);
  
  // 3. Ativar eletroímã
  digitalWrite(ELECTROMAGNET_PIN, HIGH);
  delay(300); // Tempo para magnetização
  
  // 4. Levantar com a peça
  moveZ(20);
  
  // 5. Mover para a posição de destino
  moveToPosition(x2, y2, 20);
  
  // 6. Descer para soltar a peça
  moveZ(0);
  
  // 7. Desativar eletroímã
  digitalWrite(ELECTROMAGNET_PIN, LOW);
  delay(300);
  
  // 8. Levantar novamente
  moveZ(20);
  
  // 9. Mover para posição de repouso (opcional)
  // moveToPosition(0, 0, 20);
}

void moveToPosition(int x, int y, int z) {
  // Mover X e Y simultaneamente
  long positions[2];
  positions[0] = x * STEPS_PER_MM;
  positions[1] = y * STEPS_PER_MM;
  steppers.moveTo(positions);
  steppers.runSpeedToPosition();
  
  // Atualizar posição atual
  currentX = x;
  currentY = y;
  
  // Mover Z (altura) separadamente
  moveZ(z);
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
  // Esta função deveria implementar o retorno aos sensores fim-de-curso
  // Para simplicidade, estamos apenas zerando as coordenadas
  stepperX.setCurrentPosition(0);
  stepperY.setCurrentPosition(0);
  stepperZ.setCurrentPosition(0);
  currentX = 0;
  currentY = 0;
  currentZ = 0;
}
"""

if __name__ == "__main__":
    main() 