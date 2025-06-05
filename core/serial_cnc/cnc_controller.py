import serial # pyserial
import time
import sys

class CNCArduinoController:
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
            16: (15.260, -29.476),  # casa 16 → pos 4
            
            17: (-58.624, -13.596), # posição adicional 17
            18: (-46.624, -11.096), # posição adicional 18
            19: (-35.624, -8.096),  # posição adicional 19
            20: (28.260, -36.976),  # posição adicional 20
            21: (39.260, -33.976),  # posição adicional 21
            22: (52.260, -30.976)   # posição adicional 22
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
    
    def show_positions(self):
        """Mostra todas as posições disponíveis"""
        print("\n=== POSIÇÕES DISPONÍVEIS ===")
        for pos, (x, y) in self.positions.items():
            print(f"POS{pos:2d}: X{x:8.3f} Y{y:8.3f}")
        print("="*32)
    
    def servo_up(self):
        """Erguer o servo motor (S25)"""
        print("⬆️ Levantando servo motor...")
        self.send_command("S25")
        time.sleep(0.5)
        
    def servo_down(self):
        """Abaixar o servo motor (S0)"""
        print("⬇️ Abaixando servo motor...")
        self.send_command("S0")
        time.sleep(0.5)
        
    def electromagnet_on(self):
        """Ligar eletroimã (M3)"""
        print("🧲 Ligando eletroimã...")
        self.send_command("M3")
        time.sleep(0.2)
        
    def electromagnet_off(self):
        """Desligar eletroimã (M4)"""
        print("🔌 Desligando eletroimã...")
        self.send_command("M4")
        time.sleep(0.2)
    
    def pick_piece(self):
        """Sequência completa para pegar uma peça"""
        print("🤏 Iniciando sequência de captura...")
        self.servo_down()      # Abaixar servo
        self.electromagnet_on() # Ligar eletroimã
        time.sleep(1)          # Delay para fixar
        self.servo_up()        # Erguer servo
        print("✅ Peça capturada!")
        
    def drop_piece(self):
        """Sequência completa para largar uma peça"""
        print("📤 Iniciando sequência de liberação...")
        self.servo_down()       # Abaixar servo
        self.electromagnet_off() # Desligar eletroimã
        time.sleep(1)           # Delay para soltar
        self.servo_up()         # Erguer servo
        print("✅ Peça liberada!")
    
    def close(self):
        """Fecha a conexão serial"""
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial.close()
            print("Conexão fechada")

def control_moves(move, captured):
    '''
    - S25 : erguer o servo
    - S0 : abaixar o servo
    - M3 : ligar eletroimã
    - M4 : desligar eletroimã
    '''
    # Porta serial fixa como COM3
    port = "COM3"
    
    # Inicializar o controlador
    try:
        controller = CNCArduinoController(port)
        
        print("\n=== Controlador CNC Arduino ===")
        print("Posições disponíveis:")
        print(f"POS0: X0.000 Y0.000 (Origem)")
        for i in range(1, 17):
            x, y = controller.positions[i]
            print(f"POS{i}: X{x} Y{y}")

        pos_origem, pos_destino = calculate_position(move)

        # if(captured == True):
            # send_move(controller, pos_destino)

            # Pega a peça
            # S0, M3, delayzinho, S25

            # Calcula a posição para deixar a peça capturada
            # send_move(controller, POS_CALCULADA)

            # Deixa a peça
            # S0, M4, delayzinho, S25  

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
    """Interface principal do terminal para controlar a CNC"""
    print("🤖 === CONTROLADOR CNC ARDUINO ===")
    print("Conectando ao Arduino...")
    
    # Porta serial fixa como COM3
    port = "COM3"
    
    try:
        # Inicializar o controlador
        controller = CNCArduinoController(port)
        
        print("✅ CNC conectada e inicializada!")
        
        while True:
            print("\n" + "="*55)
            print("🤖 MENU DE CONTROLE CNC COMPLETO")
            print("="*55)
            print("📍 MOVIMENTAÇÃO:")
            print("  1. 📋 Mostrar todas as posições")
            print("  2. 🎯 Ir para uma posição")
            print("  3. 🏠 Ir para origem (POS0)")
            print("")
            print("🔧 CONTROLE SERVO/ELETROIMÃ:")
            print("  4. ⬆️ Erguer servo (S25)")
            print("  5. ⬇️ Abaixar servo (S0)")
            print("  6. 🧲 Ligar eletroimã (M3)")
            print("  7. 🔌 Desligar eletroimã (M4)")
            print("")
            print("🎮 SEQUÊNCIAS AUTOMÁTICAS:")
            print("  8. 🤏 Pegar peça (completo)")
            print("  9. 📤 Largar peça (completo)")
            print("")
            print("  0. ❌ Sair")
            print("="*55)
            
            opcao = input("👉 Escolha uma opção (0-9): ").strip()
            
            if opcao == "1":
                controller.show_positions()
                
            elif opcao == "2":
                controller.show_positions()
                try:
                    pos = input("\n🎯 Digite a posição desejada (0-22): ").strip()
                    pos_num = int(pos)
                    
                    if pos_num in controller.positions:
                        print(f"\n🚀 Movendo para posição {pos_num}...")
                        success = controller.move_to_position(pos_num)
                        if success:
                            x, y = controller.positions[pos_num]
                            print(f"✅ Movimento concluído! Posição atual: X{x} Y{y}")
                        else:
                            print("❌ Falha no movimento!")
                    else:
                        print(f"❌ Posição {pos_num} não existe! Use posições de 0 a 22.")
                        
                except ValueError:
                    print("❌ Por favor, digite um número válido!")
                except KeyboardInterrupt:
                    print("\n⚠️ Operação cancelada pelo usuário")
                    
            elif opcao == "3":
                print("\n🏠 Retornando à origem...")
                success = controller.move_to_position(0)
                if success:
                    print("✅ CNC na posição origem (0, 0)")
                else:
                    print("❌ Falha ao retornar à origem!")
                    
            elif opcao == "4":
                controller.servo_up()
                
            elif opcao == "5":
                controller.servo_down()
                
            elif opcao == "6":
                controller.electromagnet_on()
                
            elif opcao == "7":
                controller.electromagnet_off()
                
            elif opcao == "8":
                controller.pick_piece()
                
            elif opcao == "9":
                controller.drop_piece()
                    
            elif opcao == "0":
                print("\n👋 Encerrando programa...")
                break
                
            else:
                print("❌ Opção inválida! Por favor, escolha entre 0-9.")
                
    except KeyboardInterrupt:
        print("\n\n⚠️ Programa interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if 'controller' in locals():
            controller.close()
            print("🔌 Conexão com Arduino encerrada")
        print("👋 Programa finalizado!")

if __name__ == "__main__":
    main()