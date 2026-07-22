import serial # pyserial
import serial.tools.list_ports
import time
import sys

# Portas comuns a tentar caso a listagem automática não funcione
COMMON_CNC_PORTS = [
    "COM3", "COM4", "COM5", "COM6",
    "/dev/ttyUSB0", "/dev/ttyUSB1",
    "/dev/ttyACM0", "/dev/ttyACM1",
]


# Palavras que identificam a resposta do firmware customizado do projeto
CNC_FIRMWARE_SIGNATURES = [
    "Servo",
    "Eletroímã",
    "Electromagnet",
    "Arduino CNC",
]


def is_cnc_response(line):
    """Verifica se uma linha de resposta vem do firmware CNC do projeto."""
    upper = line.upper()
    return any(sig.upper() in upper for sig in CNC_FIRMWARE_SIGNATURES)


def find_cnc_port(baudrate=115200, timeout=1, probe_command="?"):
    """
    Tenta descobrir automaticamente a porta serial do Arduino/CNC.

    Estratégia:
    1. Lista todas as portas disponíveis via pyserial.
    2. Abre cada porta e aguarda a mensagem de boot do Arduino.
    3. Envia o comando '?' (status) e verifica se a resposta contém
       palavras-chave do firmware customizado (ex: 'Servo', 'Eletroímã').
    4. Se nenhuma porta detectada responder como CNC, tenta as portas
       mais comuns explicitamente.

    Parâmetros:
        baudrate (int): Taxa de transmissão
        timeout (float): Timeout de leitura em segundos
        probe_command (str): Comando usado para testar a conexão

    Retorna:
        str: Nome da porta encontrada, ou None se nenhuma funcionar
    """
    print("🔍 Procurando porta do Arduino/CNC automaticamente...")

    candidates = []

    # 1. Portas detectadas pelo sistema
    try:
        detected = [p.device for p in serial.tools.list_ports.comports()]
        candidates.extend(detected)
    except Exception as e:
        print(f"⚠️ Não foi possível listar portas detectadas: {e}")

    # 2. Portas comuns como fallback
    for fallback in COMMON_CNC_PORTS:
        if fallback not in candidates:
            candidates.append(fallback)

    for port in candidates:
        try:
            with serial.Serial(port, baudrate, timeout=timeout) as s:
                time.sleep(2)  # Aguarda inicialização do Arduino

                # Lê qualquer mensagem de boot que tenha chegado
                boot_lines = []
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if s.in_waiting > 0:
                        line = s.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            boot_lines.append(line)
                            print(f"   {port} -> {line}")
                            if is_cnc_response(line):
                                print(f"✅ CNC encontrada na porta {port}")
                                return port
                    else:
                        time.sleep(0.05)

                # Se não identificou pelo boot, envia comando de probe
                s.reset_input_buffer()
                s.reset_output_buffer()
                s.write(f"{probe_command}\n".encode())

                deadline = time.time() + timeout
                while time.time() < deadline:
                    if s.in_waiting > 0:
                        line = s.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            print(f"   {port} -> {line}")
                            if is_cnc_response(line):
                                print(f"✅ CNC encontrada na porta {port}")
                                return port
                    else:
                        time.sleep(0.05)

        except serial.SerialException as e:
            print(f"   {port} indisponível ({e})")
        except Exception as e:
            print(f"   {port} erro inesperado: {e}")

    print("❌ Não foi possível detectar a CNC automaticamente.")
    print("   Verifique se o Arduino do CNC está conectado e reconhecido pelo sistema.")
    return None


class CNCArduinoController:
    def __init__(self, port=None, baudrate=115200, timeout=1):
        """
        Inicializa a conexão com o Arduino (CNC Shield)

        Parâmetros:
            port (str|None): Porta serial. Se None, tenta detectar automaticamente.
            baudrate (int): Taxa de transmissão
            timeout (float): Tempo limite para operações de leitura
        """
        if port is None:
            port = find_cnc_port(baudrate=baudrate, timeout=timeout)
            if port is None:
                print("❌ Falha ao detectar a porta do Arduino/CNC.")
                print("   Dica: conecte o Arduino e tente novamente,")
                print("   ou passe a porta manualmente, ex.: CNCArduinoController('COM3')")
                sys.exit(1)

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
            
            # Posições de morte na esquerda
            17: (-58.624, -13.596), # posição adicional 17
            18: (-46.624, -11.096), # posição adicional 18
            19: (-35.624, -8.096),  # posição adicional 19

            # Posições de morte na direita
            20: (28.260, -36.976),  # posição adicional 20
            21: (39.260, -33.976),  # posição adicional 21
            22: (52.260, -30.976)   # posição adicional 22
        }
        
        self.feed_rate = 1500  # Velocidade

        self.death_position_left = 17
        self.death_position_right = 20
        
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
        
        print("🔧 Enviando comandos iniciais...")
        for cmd in init_commands:
            self.send_command_and_wait(cmd)
        
        # Sequência de inicialização do servo e eletroimã
        print("🔄 Inicializando servo e eletroimã...")
        
        # 1. Ligar eletroimã
        print("🧲 Ligando eletroimã...")
        self.send_command_and_wait("M3")
        
        # 2. Levantar servo
        print("⬆️ Levantando servo...")
        self.send_command_and_wait("S0")
        
        # 3. Desligar eletroimã
        print("🔌 Desligando eletroimã...")
        self.send_command_and_wait("M4")
        
        print("✅ CNC inicializada com sucesso!")
    
    def send_command(self, command):
        """Envia um comando G-code para o Arduino (sem aguardar resposta)"""
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
    
    def send_command_and_wait(self, command, timeout=30):
        """
        Envia um comando G-code e aguarda a confirmação "ok" do GRBL
        
        Parâmetros:
            command (str): Comando G-code a ser enviado
            timeout (int): Tempo limite em segundos para aguardar resposta
            
        Retorna:
            bool: True se recebeu "ok", False se houve erro ou timeout
        """
        try:
            # Limpar buffer de entrada
            self.serial.flushInput()
            
            # Enviar comando
            full_command = f"{command}\n"
            self.serial.write(full_command.encode())
            print(f"Enviado: {command}")
            
            # Aguardar resposta com timeout
            start_time = time.time()
            response_buffer = ""
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    char = self.serial.read(1).decode('utf-8', errors='ignore')
                    response_buffer += char
                    
                    # Verificar se recebemos uma linha completa
                    if '\n' in response_buffer or '\r' in response_buffer:
                        lines = response_buffer.replace('\r', '\n').split('\n')
                        
                        for line in lines:
                            line = line.strip()
                            if line:
                                print(f"GRBL: {line}")
                                
                                # Verificar se é uma confirmação de sucesso
                                if line.lower() == "ok":
                                    return True
                                
                                # Verificar se é um erro
                                if line.lower().startswith("error"):
                                    print(f"❌ Erro GRBL: {line}")
                                    return False
                        
                        # Resetar buffer mantendo apenas a última parte incompleta
                        response_buffer = lines[-1] if not lines[-1].strip() else ""
                
                time.sleep(0.01)  # Pequeno delay para não sobrecarregar a CPU
            
            print(f"⚠️ Timeout aguardando resposta para comando: {command}")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao enviar comando e aguardar: {e}")
            return False
    
    def move_to_position(self, position_number, wait_for_completion=True):
        """
        Move para uma posição pré-definida
        
        Parâmetros:
            position_number (int): Número da posição (0-22)
            wait_for_completion (bool): Se deve aguardar a confirmação do GRBL
            
        Retorna:
            bool: True se o movimento foi bem-sucedido
        """
        if position_number not in self.positions:
            print(f"❌ Posição {position_number} não existe!")
            return False
        
        x, y = self.positions[position_number]
        command = f"G1 X{x:.3f} Y{y:.3f} F{self.feed_rate}"
        
        print(f"🎯 Movendo para POS{position_number}: X{x} Y{y}")
        
        if wait_for_completion:
            success = self.send_command_and_wait(command)
            if success:
                print(f"✅ Movimento para POS{position_number} concluído!")
            else:
                print(f"❌ Falha no movimento para POS{position_number}")
            return success
        else:
            # Modo compatível com código antigo
            self.send_command(command)
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
        success = self.send_command_and_wait("S25")
        if success:
            print("✅ Servo levantado!")
        else:
            print("❌ Falha ao levantar servo")
        return success
        
    def servo_down(self):
        """Abaixar o servo motor (S0)"""
        print("⬇️ Abaixando servo motor...")
        success = self.send_command_and_wait("S0")
        if success:
            print("✅ Servo abaixado!")
        else:
            print("❌ Falha ao abaixar servo")
        return success
        
    def electromagnet_on(self):
        """Ligar eletroimã (M3)"""
        print("🧲 Ligando eletroimã...")
        success = self.send_command_and_wait("M3")
        if success:
            print("✅ Eletroimã ligado!")
        else:
            print("❌ Falha ao ligar eletroimã")
        return success
        
    def electromagnet_off(self):
        """Desligar eletroimã (M4)"""
        print("🔌 Desligando eletroimã...")
        success = self.send_command_and_wait("M4")
        if success:
            print("✅ Eletroimã desligado!")
        else:
            print("❌ Falha ao desligar eletroimã")
        return success
    
    def pick_piece(self):
        """Sequência completa para pegar uma peça"""
        print("🤏 Iniciando sequência de captura...")
        
        if not self.servo_down():
            return False
        
        if not self.electromagnet_on():
            return False
        
        time.sleep(1)  # Delay para fixar a peça
        
        if not self.servo_up():
            return False
            
        print("✅ Peça capturada com sucesso!")
        return True
        
    def drop_piece(self):
        """Sequência completa para largar uma peça"""
        print("📤 Iniciando sequência de liberação...")
        
        if not self.servo_down():
            return False
        
        if not self.electromagnet_off():
            return False
        
        time.sleep(1)  # Delay para soltar a peça
        
        if not self.servo_up():
            return False
            
        print("✅ Peça liberada com sucesso!")
        return True
    
    def close(self):
        """Fecha a conexão serial"""
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial.close()
            print("🔌 Conexão fechada")

    def control_moves(self, move, captured):
        """
        Controla movimentos de xadrez com verificação de confirmação GRBL
        """
        try:
            pos_origem, pos_destino = calculate_position(move)
            self.servo_up()

            if captured == True:
                print("♟️ Captura detectada - removendo peça do destino")
                
                if not self.move_to_position(pos_destino):
                    print("❌ Falha ao mover para posição de captura")
                    return False
                
                if not self.pick_piece():
                    print("❌ Falha ao capturar peça")
                    return False

                # Move para a posição de morte
                death_pos = None
                if move[1][1] <= 1:  # Lado esquerdo do tabuleiro
                    death_pos = self.death_position_left
                    self.death_position_left += 1
                    if self.death_position_left > 19:
                        self.death_position_left = 17
                else:  # Lado direito do tabuleiro
                    death_pos = self.death_position_right
                    self.death_position_right += 1
                    if self.death_position_right > 22:
                        self.death_position_right = 20

                print(f"☠️ Movendo peça capturada para posição de morte {death_pos}")
                if not self.move_to_position(death_pos):
                    print("❌ Falha ao mover para posição de morte")
                    return False
                
                if not self.drop_piece():
                    print("❌ Falha ao soltar peça capturada")
                    return False

            # Movimento principal da peça
            print(f"♞ Executando movimento: POS{pos_origem} → POS{pos_destino}")
            
            if not self.move_to_position(pos_origem):
                print("❌ Falha ao mover para posição de origem")
                return False
            
            if not self.pick_piece():
                print("❌ Falha ao pegar peça de origem")
                return False

            if not self.move_to_position(pos_destino):
                print("❌ Falha ao mover para posição de destino")
                return False
            
            if not self.drop_piece():
                print("❌ Falha ao soltar peça no destino")
                return False

            # Retornar à origem
            print("🏠 Retornando à posição inicial")
            if not self.move_to_position(0):
                print("❌ Falha ao retornar à origem")
                return False
            
            self.servo_down()         # Deixar servo na posição baixa
            self.electromagnet_off()  # Garantir que eletroimã está desligado
            
            print("✅ Movimento executado com sucesso!")
            return True
                        
        except Exception as e:
            print(f"❌ Erro durante execução do movimento: {e}")
            return False

def calculate_position(move):
    try:
        (linha_origem, coluna_origem), (linha_destino, coluna_destino) = move
        
        pos_origem = 4 * linha_origem + coluna_origem + 1 
        pos_destino = 4 * linha_destino + coluna_destino + 1
    
    except:
        print("❌ Erro ao processar o movimento!")
        return None, None
        
    return pos_origem, pos_destino

def send_move(controller, pos):
    """Função auxiliar para compatibilidade"""
    return controller.move_to_position(pos)

def main():
    """Interface principal do terminal para controlar a CNC"""
    print("🤖 === CONTROLADOR CNC ARDUINO ===")
    print("Conectando ao Arduino...")

    try:
        # Inicializar o controlador (auto-detecta a porta)
        controller = CNCArduinoController()
        
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