import serial # pyserial
import serial.tools.list_ports
import time
import sys
from pathlib import Path

try:
    import hardware_config as hardware
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import hardware_config as hardware


def is_cnc_response(line):
    """Verifica se uma linha de resposta vem do firmware CNC do projeto."""
    upper = line.upper()
    return any(sig.upper() in upper for sig in hardware.FIRMWARE_SIGNATURES)


def find_cnc_port(
    baudrate=hardware.SERIAL_BAUDRATE,
    timeout=hardware.SERIAL_TIMEOUT,
    probe_command=hardware.SERIAL_PROBE_COMMAND,
):
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
    print("Procurando porta do Arduino/CNC automaticamente...")

    candidates = []

    try:
        detected = [p.device for p in serial.tools.list_ports.comports()]
        candidates.extend(detected)
    except Exception as e:
        print(f"Não foi possível listar portas detectadas: {e}")

    for fallback in hardware.SERIAL_FALLBACK_PORTS:
        if fallback not in candidates:
            candidates.append(fallback)

    for port in candidates:
        try:
            with serial.Serial(port, baudrate, timeout=timeout) as s:
                time.sleep(hardware.SERIAL_STARTUP_DELAY)

                boot_lines = []
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if s.in_waiting > 0:
                        line = s.readline().decode("utf-8", errors="ignore").strip()
                        if line:
                            boot_lines.append(line)
                            print(f"   {port} -> {line}")
                            if is_cnc_response(line):
                                print(f"CNC encontrada na porta {port}")
                                return port
                    else:
                        time.sleep(hardware.SERIAL_PROBE_POLL_INTERVAL)

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
                                print(f"CNC encontrada na porta {port}")
                                return port
                    else:
                        time.sleep(hardware.SERIAL_PROBE_POLL_INTERVAL)

        except serial.SerialException as e:
            print(f"   {port} indisponível ({e})")
        except Exception as e:
            print(f"   {port} erro inesperado: {e}")

    print("Não foi possível detectar a CNC automaticamente.")
    print("   Verifique se o Arduino do CNC está conectado e reconhecido pelo sistema.")
    return None


class CNCArduinoController:
    def __init__(
        self,
        port=hardware.SERIAL_PORT,
        baudrate=hardware.SERIAL_BAUDRATE,
        timeout=hardware.SERIAL_TIMEOUT,
    ):
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
                raise RuntimeError(
                    "Falha ao detectar a porta do Arduino/CNC. "
                    "Conecte o Arduino ou configure SERIAL_PORT."
                )

        self.positions = dict(hardware.CNC_POSITIONS)
        
        self.feed_rate = hardware.CNC_FEED_RATE

        self.death_position_left = hardware.GRAVEYARD_LEFT_START
        self.death_position_right = hardware.GRAVEYARD_RIGHT_START
        
        try:
            self.serial = serial.Serial(port, baudrate, timeout=timeout)
            print(f"Conectado à porta {port}")
            time.sleep(hardware.SERIAL_STARTUP_DELAY)
            self.initialize_cnc()
        except serial.SerialException as e:
            raise RuntimeError(f"Erro ao conectar à porta {port}: {e}") from e
    
    def initialize_cnc(self):
        """Inicializa a CNC enviando comandos G-code iniciais"""
        init_commands = hardware.CNC_INITIALIZATION_COMMANDS
        
        print("Enviando comandos iniciais...")
        for cmd in init_commands:
            self.send_command_and_wait(cmd)
        
        print("Inicializando servo e eletroimã...")
        
        print("Ligando eletroimã...")
        self.send_command_and_wait(hardware.ELECTROMAGNET_ON_COMMAND)
        
        print("Abaixando servo...")
        self.send_command_and_wait(hardware.SERVO_DOWN_COMMAND)
        
        print("Desligando eletroimã...")
        self.send_command_and_wait(hardware.ELECTROMAGNET_OFF_COMMAND)
        
        print("CNC inicializada com sucesso!")
    
    def send_command(self, command):
        """Envia um comando G-code para o Arduino (sem aguardar resposta)"""
        try:
            full_command = f"{command}\n"
            self.serial.write(full_command.encode())
            
            time.sleep(hardware.SERIAL_RESPONSE_DELAY)
            response = self.serial.readline().decode().strip()
            
            if response:
                print(f"Resposta: {response}")
                
            return response
        except Exception as e:
            print(f"Erro ao enviar comando: {e}")
            return None
    
    def send_command_and_wait(
        self,
        command,
        timeout=hardware.SERIAL_COMMAND_TIMEOUT,
    ):
        """
        Envia um comando G-code e aguarda a confirmação "ok" do GRBL
        
        Parâmetros:
            command (str): Comando G-code a ser enviado
            timeout (int): Tempo limite em segundos para aguardar resposta
            
        Retorna:
            bool: True se recebeu "ok", False se houve erro ou timeout
        """
        try:
            self.serial.flushInput()
            
            full_command = f"{command}\n"
            self.serial.write(full_command.encode())
            print(f"Enviado: {command}")
            
            start_time = time.time()
            response_buffer = ""
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    char = self.serial.read(1).decode('utf-8', errors='ignore')
                    response_buffer += char
                    
                    if '\n' in response_buffer or '\r' in response_buffer:
                        lines = response_buffer.replace('\r', '\n').split('\n')
                        
                        for line in lines:
                            line = line.strip()
                            if line:
                                print(f"GRBL: {line}")
                                
                                if line.lower() == "ok":
                                    return True
                                
                                if line.lower().startswith("error"):
                                    print(f"Erro GRBL: {line}")
                                    return False
                        
                        response_buffer = lines[-1] if not lines[-1].strip() else ""
                
                time.sleep(hardware.SERIAL_POLL_INTERVAL)
            
            print(f"Timeout aguardando resposta para comando: {command}")
            return False
            
        except Exception as e:
            print(f"Erro ao enviar comando e aguardar: {e}")
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
            print(f"Posição {position_number} não existe!")
            return False
        
        x, y = self.positions[position_number]
        command = f"G1 X{x:.3f} Y{y:.3f} F{self.feed_rate}"
        
        print(f"Movendo para POS{position_number}: X{x} Y{y}")
        
        if wait_for_completion:
            success = self.send_command_and_wait(command)
            if success:
                print(f"Movimento para POS{position_number} concluído!")
            else:
                print(f"Falha no movimento para POS{position_number}")
            return success
        else:
            self.send_command(command)
            time.sleep(hardware.CNC_NONBLOCKING_MOVE_DELAY)
            return True
    
    def show_positions(self):
        """Mostra todas as posições disponíveis"""
        print("\n=== POSIÇÕES DISPONÍVEIS ===")
        for pos, (x, y) in self.positions.items():
            print(f"POS{pos:2d}: X{x:8.3f} Y{y:8.3f}")
        print("="*32)
    
    def servo_up(self):
        """Ergue o servo motor."""
        print("Levantando servo motor...")
        success = self.send_command_and_wait(hardware.SERVO_UP_COMMAND)
        if success:
            print("Servo levantado!")
        else:
            print("Falha ao levantar servo")
        return success
        
    def servo_down(self):
        """Abaixa o servo motor."""
        print("Abaixando servo motor...")
        success = self.send_command_and_wait(hardware.SERVO_DOWN_COMMAND)
        if success:
            print("Servo abaixado!")
        else:
            print("Falha ao abaixar servo")
        return success
        
    def electromagnet_on(self):
        """Liga o eletroímã."""
        print("Ligando eletroimã...")
        success = self.send_command_and_wait(hardware.ELECTROMAGNET_ON_COMMAND)
        if success:
            print("Eletroimã ligado!")
        else:
            print("Falha ao ligar eletroimã")
        return success
        
    def electromagnet_off(self):
        """Desliga o eletroímã."""
        print("Desligando eletroimã...")
        success = self.send_command_and_wait(hardware.ELECTROMAGNET_OFF_COMMAND)
        if success:
            print("Eletroimã desligado!")
        else:
            print("Falha ao desligar eletroimã")
        return success
    
    def pick_piece(self):
        """Sequência completa para pegar uma peça"""
        print("Iniciando sequência de captura...")
        
        if not self.servo_down():
            return False
        
        if not self.electromagnet_on():
            return False
        
        time.sleep(hardware.PIECE_HANDLING_DELAY)
        
        if not self.servo_up():
            return False
            
        print("Peça capturada com sucesso!")
        return True
        
    def drop_piece(self):
        """Sequência completa para largar uma peça"""
        print("Iniciando sequência de liberação...")
        
        if not self.servo_down():
            return False
        
        if not self.electromagnet_off():
            return False
        
        time.sleep(hardware.PIECE_HANDLING_DELAY)
        
        if not self.servo_up():
            return False
            
        print("Peça liberada com sucesso!")
        return True
    
    def close(self):
        """Fecha a conexão serial"""
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial.close()
            print("Conexão fechada")

    def control_moves(self, move, captured):
        """
        Controla movimentos de xadrez com verificação de confirmação GRBL
        """
        try:
            pos_origem, pos_destino = calculate_position(move)
            self.servo_up()

            if captured == True:
                print("Captura detectada - removendo peça do destino")
                
                if not self.move_to_position(pos_destino):
                    print("Falha ao mover para posição de captura")
                    return False
                
                if not self.pick_piece():
                    print("Falha ao capturar peça")
                    return False

                death_pos = None
                # Capturas das colunas A/B vão para a esquerda; C/D, direita.
                if move[1][1] <= 1:
                    death_pos = self.death_position_left
                    self.death_position_left += 1
                    if self.death_position_left > hardware.GRAVEYARD_LEFT_END:
                        self.death_position_left = hardware.GRAVEYARD_LEFT_START
                else:  # Lado direito do tabuleiro
                    death_pos = self.death_position_right
                    self.death_position_right += 1
                    if self.death_position_right > hardware.GRAVEYARD_RIGHT_END:
                        self.death_position_right = hardware.GRAVEYARD_RIGHT_START

                print(f"Movendo peça capturada para posição de morte {death_pos}")
                if not self.move_to_position(death_pos):
                    print("Falha ao mover para posição de morte")
                    return False
                
                if not self.drop_piece():
                    print("Falha ao soltar peça capturada")
                    return False

            print(f"Executando movimento: POS{pos_origem} → POS{pos_destino}")
            
            if not self.move_to_position(pos_origem):
                print("Falha ao mover para posição de origem")
                return False
            
            if not self.pick_piece():
                print("Falha ao pegar peça de origem")
                return False

            if not self.move_to_position(pos_destino):
                print("Falha ao mover para posição de destino")
                return False
            
            if not self.drop_piece():
                print("Falha ao soltar peça no destino")
                return False

            print("Retornando à posição inicial")
            if not self.move_to_position(hardware.CNC_HOME_POSITION):
                print("Falha ao retornar à origem")
                return False
            
            self.servo_down()         # Deixar servo na posição baixa
            self.electromagnet_off()  # Garantir que eletroimã está desligado
            
            print("Movimento executado com sucesso!")
            return True
                        
        except Exception as e:
            print(f"Erro durante execução do movimento: {e}")
            return False

def calculate_position(move):
    try:
        (linha_origem, coluna_origem), (linha_destino, coluna_destino) = move
        
        pos_origem = 4 * linha_origem + coluna_origem + 1 
        pos_destino = 4 * linha_destino + coluna_destino + 1
    
    except:
        print("Erro ao processar o movimento!")
        return None, None
        
    return pos_origem, pos_destino

def send_move(controller, pos):
    """Função auxiliar para compatibilidade"""
    return controller.move_to_position(pos)

def main():
    """Interface principal do terminal para controlar a CNC"""
    print("=== CONTROLADOR CNC ARDUINO ===")
    print("Conectando ao Arduino...")

    try:
        controller = CNCArduinoController()
        
        print("CNC conectada e inicializada!")
        
        while True:
            print("\n" + "="*55)
            print("MENU DE CONTROLE CNC COMPLETO")
            print("="*55)
            print("MOVIMENTAÇÃO:")
            print("  1. Mostrar todas as posições")
            print("  2. Ir para uma posição")
            print(f"  3. Ir para origem (POS{hardware.CNC_HOME_POSITION})")
            print("")
            print("CONTROLE SERVO/ELETROIMÃ:")
            print(f"  4. Erguer servo ({hardware.SERVO_UP_COMMAND})")
            print(f"  5. Abaixar servo ({hardware.SERVO_DOWN_COMMAND})")
            print(f"  6. Ligar eletroimã ({hardware.ELECTROMAGNET_ON_COMMAND})")
            print(f"  7. Desligar eletroimã ({hardware.ELECTROMAGNET_OFF_COMMAND})")
            print("")
            print("SEQUÊNCIAS AUTOMÁTICAS:")
            print("  8. Pegar peça (completo)")
            print("  9. Largar peça (completo)")
            print("")
            print("  0. Sair")
            print("="*55)
            
            opcao = input("Escolha uma opção (0-9): ").strip()
            
            if opcao == "1":
                controller.show_positions()
                
            elif opcao == "2":
                controller.show_positions()
                try:
                    pos = input("\nDigite a posição desejada (0-22): ").strip()
                    pos_num = int(pos)
                    
                    if pos_num in controller.positions:
                        print(f"\nMovendo para posição {pos_num}...")
                        success = controller.move_to_position(pos_num)
                        if success:
                            x, y = controller.positions[pos_num]
                            print(f"Movimento concluído! Posição atual: X{x} Y{y}")
                        else:
                            print("Falha no movimento!")
                    else:
                        print(f"Posição {pos_num} não existe! Use posições de 0 a 22.")
                        
                except ValueError:
                    print("Por favor, digite um número válido!")
                except KeyboardInterrupt:
                    print("\nOperação cancelada pelo usuário")
                    
            elif opcao == "3":
                print("\nRetornando à origem...")
                success = controller.move_to_position(hardware.CNC_HOME_POSITION)
                if success:
                    print("CNC na posição origem (0, 0)")
                else:
                    print("Falha ao retornar à origem!")
                    
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
                print("\nEncerrando programa...")
                break
                
            else:
                print("Opção inválida! Por favor, escolha entre 0-9.")
                
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'controller' in locals():
            controller.close()
            print("Conexão com Arduino encerrada")
        print("Programa finalizado!")

if __name__ == "__main__":
    main()
