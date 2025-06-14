import serial
import time
import threading

# Tenta importar pynput (melhor para Linux)
try:
    from pynput.keyboard import Key, Controller
    USE_PYNPUT = True
    keyboard_controller = Controller()
    print("Usando pynput para simulação de teclado")
except ImportError:
    try:
        import keyboard
        USE_PYNPUT = False
        print("Usando keyboard para simulação de teclado")
    except ImportError:
        print("ERRO: Instale pynput ou keyboard:")
        print("pip install pynput")
        exit(1)

class ArduinoController:
    def __init__(self, port='COM3', baudrate=9600):
        """
        Inicializa a conexão serial com o Arduino
        
        Args:
            port (str): Porta serial (ex: 'COM3' no Windows, '/dev/ttyUSB0' no Linux)
            baudrate (int): Taxa de transmissão
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.running = False
        
    def connect(self):
        """Estabelece conexão com o Arduino"""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Aguarda o Arduino resetar
            print(f"Conectado ao Arduino na porta {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Encerra a conexão com o Arduino"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Conexão encerrada")
    
    def read_data(self):
        """Lê dados do Arduino"""
        if self.serial_connection and self.serial_connection.in_waiting > 0:
            try:
                data = self.serial_connection.readline().decode('utf-8').strip()
                return data
            except UnicodeDecodeError:
                return None
        return None
    
    def simulate_keypress(self, key_code):
        """Simula o pressionamento de tecla"""
        # Aceita qualquer tecla numérica que o Arduino enviar
        valid_keys = ['0', '1', '2']
        
        if key_code in valid_keys:
            if USE_PYNPUT:
                # Usando pynput (recomendado para Linux)
                key_to_press = key_code
                keyboard_controller.press(key_to_press)
                time.sleep(0.01)  # Pequeno delay
                keyboard_controller.release(key_to_press)
                print(f"✅ Tecla '{key_to_press}' pressionada (pynput)")
            else:
                # Usando keyboard (pode precisar de root no Linux)
                keyboard.press_and_release(key_code)
                print(f"✅ Tecla '{key_code}' pressionada (keyboard)")
        else:
            print(f"⚠️ Tecla '{key_code}' não reconhecida. Teclas válidas: {valid_keys}")
    
    def run(self):
        """Loop principal de monitoramento"""
        if not self.connect():
            return
        
        self.running = True
        print("Monitorando botões... Pressione Ctrl+C para sair")
        
        try:
            while self.running:
                data = self.read_data()
                if data:
                    print(f"Recebido do Arduino: {data}")
                    
                    # Processa os comandos recebidos
                    if data.startswith("BUTTON"):
                        try:
                            button_num = data.split("_")[1]
                            print(f"🔘 Recebido comando: {data}")
                            print(f"🎯 Simulando tecla '{button_num}'...")
                            self.simulate_keypress(button_num)
                            print("📝 Comando processado!")
                        except IndexError:
                            print(f"⚠️ Formato inválido: {data}")
                    else:
                        print(f"📟 Arduino: {data}")
                
                time.sleep(0.01)  # Pequeno delay para não sobrecarregar o CPU
                
        except KeyboardInterrupt:
            print("\nEncerrando programa...")
        finally:
            self.running = False
            self.disconnect()

def main():
    # Configuração da porta serial (ajuste conforme necessário)
    # Windows: geralmente COM3, COM4, etc.
    # Linux/Mac: geralmente /dev/ttyUSB0, /dev/ttyACM0, etc.
    
    print("Portas disponíveis:")
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"  {port.device} - {port.description}")
    except:
        print("  Não foi possível listar portas automaticamente")
    
    port = input("\nDigite a porta serial (ex: COM3 ou /dev/ttyUSB0): ").strip()
    if not port:
        port = "COM3"  # Porta padrão
    
    controller = ArduinoController(port=port)
    controller.run()

if __name__ == "__main__":
    print("=== Controlador Arduino com Botões KY-004 ===")
    print("Instale as dependências:")
    print("pip install pyserial pynput")
    print("(pynput é recomendado para Linux)")
    print()
    
    main()
