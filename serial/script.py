import serial
import time

# --- Configurações ---
PORTA_SERIAL = 'COM3'  # Altere para a porta correta do seu Arduino
BAUD_RATE = 115200          # Taxa de baud comum para GRBL
ARQUIVO_GCODE = 'program.gcode' # Arquivo com seus comandos G-code

def conectar_arduino(porta, baudrate):
    """Estabelece conexão serial com o Arduino."""
    try:
        ser = serial.Serial(porta, baudrate, timeout=1)
        print(f"Conectado a {porta} com baud rate {baudrate}")
        time.sleep(2)  # Aguarda a inicialização da conexão serial
        ser.flushInput() # Limpa o buffer de entrada
        return ser
    except serial.SerialException as e:
        print(f"Erro ao conectar: {e}")
        return None

def enviar_comando(serial_conn, comando):
    """Envia um comando G-code e aguarda a resposta 'ok'."""
    if serial_conn and serial_conn.isOpen():
        print(f"Enviando: {comando.strip()}")
        serial_conn.write(comando.encode('utf-8')) # Envia o comando
        resposta = ''
        while True:
            linha = serial_conn.readline().decode('utf-8').strip()
            if linha:
                print(f"Recebido: {linha}")
            if 'ok' in linha:
                break
            if 'error' in linha:
                print(f"Erro do GRBL: {linha}")
                break
            # Você pode adicionar mais verificações de resposta aqui
        return resposta
    else:
        print("Conexão serial não está aberta.")
        return None

def executar_gcode_de_arquivo(serial_conn, nome_arquivo):
    """Lê comandos G-code de um arquivo e os envia para o Arduino."""
    try:
        with open(nome_arquivo, 'r') as f:
            for linha_gcode in f:
                linha_gcode = linha_gcode.strip() # Remove espaços em branco e quebras de linha
                if not linha_gcode or linha_gcode.startswith(';'): # Ignora linhas vazias ou comentários
                    continue
                enviar_comando(serial_conn, linha_gcode + '\n') # Adiciona newline, pois o GRBL espera
    except FileNotFoundError:
        print(f"Erro: Arquivo G-code '{nome_arquivo}' não encontrado.")

# --- Programa Principal ---
if __name__ == "__main__":
    arduino = conectar_arduino(PORTA_SERIAL, BAUD_RATE)

    if arduino:
        # Exemplo 1: Enviar comandos G-code diretamente
        # Adicione mais comandos conforme necessário

        # Exemplo 2: Executar G-code de um arquivo
        # Certifique-se de que o arquivo 'meu_programa.gcode' existe no mesmo diretório
        # ou forneça o caminho completo.
        # print(f"\n--- Executando G-code do arquivo: {ARQUIVO_GCODE} ---")
        executar_gcode_de_arquivo(arduino, ARQUIVO_GCODE)

        print("\nComandos enviados.")
        arduino.close()
        print("Conexão fechada.")
    else:
        print("Não foi possível conectar ao Arduino.")