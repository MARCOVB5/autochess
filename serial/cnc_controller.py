import serial # pyserial
import time
import sys

class CNCArdunioController:
    def __init__(self, port='COM3', baudrate=115200, timeout=1):
        """
        Inicializa a conexão com o Arduino (CNC Shield)
        
        Parâmetros:
            port (str): Porta serial (ex: 'COM3' no Windows, '/dev/ttyUSB0' no Linux)
            baudrate (int): Taxa de transmissão
            timeout (float): Tempo limite para operações de leitura
        """
        self.positions = {
            0: (0.000, 0.000),  # Posição de origem X0 Y0
            1: (-32.624, -16.596),
            2: (-15.764, -21.048),
            3: (-0.532, -25.076),
            4: (15.260, -29.476),
            5: (-15.844, -13.008),
            6: (-0.752, -17.700),
            7: (15.984, -20.952),
            8: (31.528, -25.340),
            9: (1.172, -8.844),
            10: (16.332, -13.288),
            11: (30.960, -17.288),
            12: (47.328, -21.020),
            13: (16.564, -4.908),
            14: (31.964, -8.988),
            15: (47.500, -13.256),
            16: (63.824, -17.028)
        }
        
        self.feed_rate = 1500  # Velocidade
        
        try:
            self.serial = serial.Serial(port, baudrate, timeout=timeout)
            print(f"Conectado à porta {port}")
            time.sleep(2)  # Aguarda a inicialização do Arduino
            self.initialize_cnc()
        except serial.SerialException as e:
            print(f"Erro ao conectar à porta {port}: {e}")
            sys.exit(1)
    
    def initialize_cnc(self):
        """Inicializa a CNC enviando comandos G-code iniciais"""
        # Enviar comandos iniciais
        init_commands = [
            "G21",       # Definir unidades para milímetros
            "G90",       # Modo de posicionamento absoluto
            "G92 X0 Y0"  # Definir posição atual como origem
        ]
        
        for cmd in init_commands:
            self.send_command(cmd)
            time.sleep(0.1)
        
        print("CNC inicializada com sucesso!")
    
    def send_command(self, command):
        """Envia um comando G-code para o Arduino"""
        try:
            # Adicionar nova linha ao final do comando
            full_command = f"{command}\n"
            self.serial.write(full_command.encode())
            
            # Aguardar e ler a resposta (opcional, dependendo do firmware)
            time.sleep(0.1)
            response = self.serial.readline().decode().strip()
            
            if response:
                print(f"Resposta: {response}")
                
            return response
        except Exception as e:
            print(f"Erro ao enviar comando: {e}")
            return None
    
    def move_to_position(self, position_number):
        """Move para uma posição pré-definida"""
        if position_number not in self.positions:
            print(f"Posição {position_number} não existe!")
            return False
        
        x, y = self.positions[position_number]
        command = f"G1 X{x:.3f} Y{y:.3f} F{self.feed_rate}"
        
        print(f"Movendo para POS{position_number}: X{x} Y{y}")
        self.send_command(command)
        
        # Esperar o movimento ser concluído
        # Isso depende do firmware - alguns firmwares como GRBL responderam "ok" quando concluírem
        time.sleep(1)
        
        return True
    
    def close(self):
        """Fecha a conexão serial"""
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial.close()
            print("Conexão fechada")


def main():
    # Porta serial fixa como COM3
    port = "COM3"
    
    # Inicializar o controlador
    try:
        controller = CNCArdunioController(port)
        
        print("\n=== Controlador CNC Arduino ===")
        print("Posições disponíveis:")
        print(f"POS0: X0.000 Y0.000 (Origem)")
        for i in range(1, 17):
            x, y = controller.positions[i]
            print(f"POS{i}: X{x} Y{y}")
        
        print("\nDigite o número da posição desejada (0-16) ou 'q' para sair")
        
        while True:
            command = input("\nComando: ")
            
            if command.lower() == 'q':
                break
            
            try:
                position = int(command)
                controller.move_to_position(position)
            except ValueError:
                print("Comando inválido! Digite um número de posição (0-16) ou 'q' para sair.")
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'controller' in locals():
            controller.close()


if __name__ == "__main__":
    main()
