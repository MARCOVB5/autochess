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
            0: (0.000, 0.000),  # Origem (não muda)
            
            1:  (16.564, -4.908),   # casa 1 → pos 13
            2:  (31.964, -8.988),   # casa 2 → pos 14
            3:  (47.500, -13.256),  # casa 3 → pos 15
            4:  (63.824, -17.028),  # casa 4 → pos 16

            5:  (1.172, -8.844),    # casa 5 → pos 9
            6:  (16.332, -13.288),  # casa 6 → pos 10
            7:  (30.960, -17.288),  # casa 7 → pos 11
            8:  (47.328, -21.020),  # casa 8 → pos 12

            9:  (-15.844, -13.008), # casa 9 → pos 5
            10: (-0.752, -17.700),  # casa 10 → pos 6
            11: (15.984, -20.952),  # casa 11 → pos 7
            12: (31.528, -25.340),  # casa 12 → pos 8

            13: (-32.624, -16.596), # casa 13 → pos 1
            14: (-15.764, -21.048), # casa 14 → pos 2
            15: (-0.532, -25.076),  # casa 15 → pos 3
            16: (15.260, -29.476)   # casa 16 → pos 4
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

def control_moves(move, captured):
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

        pos_origem, pos_destino = calculate_position(move)

        # if(captured == True):
            # send_move(controller, pos_destino)

            # Desce Eletroimã

            # Calcula a posição para deixar a peça capturada

            # Ergue

        send_move(controller, pos_origem)

        # Abaixar o eletroimã

        send_move(controller, pos_destino)

        # Erguer o eletroimã

        send_move(controller, 0)
                    
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'controller' in locals():
            controller.close()

def calculate_position(move):
    try:
        (linha_origem, linha_destino), (coluna_origem, coluna_destino) = move
        
        pos_origem = 4 * linha_origem + coluna_origem + 1 
        pos_destino = 4 * linha_destino + coluna_destino + 1
    
    except:
        print("Erro ao processar o movimento!")
        
    return pos_origem, pos_destino

def send_move(controller, pos):
    controller.move_to_position(pos)
    time.sleep(1)

def main():
   print("Main!!!")
   
if __name__ == "__main__":
    main()  
