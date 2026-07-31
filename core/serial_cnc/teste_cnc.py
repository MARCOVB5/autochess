"""
Script para testar GRBL modificado com controle de servo motor
Testa todas as funcionalidades: M3, M4, M5 e controle do servo via S
Porta: COM3
"""

import serial
import time
import sys

class GRBLServoTester:
    def __init__(self, port='COM3', baudrate=115200, timeout=2):
        """
        Inicializa conexão com GRBL
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        
    def connect(self):
        """
        Conecta à porta serial
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            print(f"Conectado na porta {self.port}")
            time.sleep(2)  # Aguarda inicialização do GRBL
            return True
        except serial.SerialException as e:
            print(f"Erro ao conectar na porta {self.port}: {e}")
            return False
    
    def disconnect(self):
        """
        Desconecta da porta serial
        """
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Desconectado")
    
    def send_command(self, command, wait_response=True, delay=0.5):
        """
        Envia comando G-code para GRBL
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("Conexão serial não estabelecida")
            return None
            
        try:
            command_with_newline = command + '\n'
            self.serial_conn.write(command_with_newline.encode('utf-8'))
            print(f"Enviado: {command}")
            
            if wait_response:
                time.sleep(delay)
                response = ""
                while self.serial_conn.in_waiting > 0:
                    response += self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8')
                
                if response:
                    print(f"Resposta: {response.strip()}")
                    return response.strip()
                else:
                    print("Sem resposta")
                    return None
            
            time.sleep(delay)
            return "ok"
            
        except Exception as e:
            print(f"Erro ao enviar comando '{command}': {e}")
            return None
    
    def wait_for_idle(self, max_wait=10):
        """
        Aguarda GRBL ficar em estado Idle
        """
        print("⏳ Aguardando GRBL ficar em estado Idle...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = self.send_command("?", wait_response=True, delay=0.1)
            if response and "Idle" in response:
                print("GRBL em estado Idle")
                return True
            time.sleep(0.5)
        
        print("Timeout aguardando estado Idle")
        return False
    
    def test_basic_connection(self):
        """
        Testa conexão básica com GRBL
        """
        print("\n" + "="*50)
        print("TESTE 1: Conexão Básica")
        print("="*50)
        
        response = self.send_command("?")
        if response:
            print("GRBL respondendo")
        else:
            print("GRBL não está respondendo")
            return False
        
        response = self.send_command("$I")
        print("Informações do sistema:")
        
        return True
    
    def test_relay_control(self):
        """
        Testa controle do relé (M3/M4)
        """
        print("\n" + "="*50)
        print("TESTE 2: Controle do Relé (M3/M4)")
        print("="*50)
        
        tests = [
            ("M3", "Liga relé (spindle CW)"),
            ("M4", "Desliga relé (spindle CCW)"),
            ("M5", "Para spindle")
        ]
        
        for command, description in tests:
            print(f"\nTestando: {command} - {description}")
            response = self.send_command(command)
            if response:
                print("Comando executado")
                time.sleep(2)  # Aguarda 2 segundos para observar
            else:
                print("Falha na execução")
        
        self.wait_for_idle()
    
    def test_servo_positions(self):
        """
        Testa posições do servo motor
        """
        print("\n" + "="*50)
        print("TESTE 3: Controle do Servo Motor")
        print("="*50)
        
        basic_tests = [
            ("M3 S0", "Servo em 0° (posição baixa)"),
            ("M3 S1", "Servo em 180° (posição alta)"),
            ("M3 S0", "Servo em 0° novamente"),
        ]
        
        for command, description in basic_tests:
            print(f"\nTestando: {command} - {description}")
            response = self.send_command(command)
            if response:
                print("Comando executado")
                time.sleep(3)  # 3 segundos para ver movimento do servo
            else:
                print("Falha na execução")
        
        self.send_command("M5")  # Para tudo
        self.wait_for_idle()
    
    def test_servo_intermediate_positions(self):
        """
        Testa posições intermediárias do servo
        """
        print("\n" + "="*50)
        print("TESTE 4: Posições Intermediárias do Servo")
        print("="*50)
        
        positions = [0, 45, 90, 135, 180, 90, 0]
        
        for pos in positions:
            command = f"M3 S{pos}"
            print(f"\nTestando: {command} - Servo em {pos}°")
            response = self.send_command(command)
            if response:
                print(f"Servo movido para {pos}°")
                time.sleep(2)  # 2 segundos para ver movimento
            else:
                print("Falha na execução")
        
        self.send_command("M5")  # Para tudo
        self.wait_for_idle()
    
    def test_sequence_automation(self):
        """
        Testa sequência automatizada completa
        """
        print("\n" + "="*50)
        print("TESTE 5: Sequência Automatizada")
        print("="*50)
        
        sequence = [
            ("M3", "Liga spindle"),
            ("G4 P0.5", "Aguarda 500ms"),
            ("M3 S0", "Servo para baixo (0°)"),
            ("G4 P1", "Aguarda 1s"),
            ("M4", "Muda direção do spindle"),
            ("G4 P0.5", "Aguarda 500ms"),
            ("M3 S180", "Servo para cima (180°)"),
            ("G4 P1", "Aguarda 1s"),
            ("M3 S90", "Servo no meio (90°)"),
            ("G4 P1", "Aguarda 1s"),
            ("M5", "Para tudo")
        ]
        
        print("Executando sequência completa...")
        
        for command, description in sequence:
            print(f"\n{description}: {command}")
            response = self.send_command(command, delay=0.2)
            if response:
                print("Executado")
            else:
                print("Falha")
                
            if "S" in command:
                time.sleep(1.5)
        
        self.wait_for_idle()
    
    def test_error_handling(self):
        """
        Testa tratamento de erros
        """
        print("\n" + "="*50)
        print("TESTE 6: Tratamento de Erros")
        print("="*50)
        
        error_tests = [
            ("M3 S300", "Valor S muito alto (deve limitar a 180)"),
            ("M3 S-10", "Valor S negativo"),
            ("INVALID", "Comando inválido")
        ]
        
        for command, description in error_tests:
            print(f"\nTestando: {command} - {description}")
            response = self.send_command(command)
            print(f"Resposta: {response}")
        
        self.send_command("M5")
        self.wait_for_idle()
    
    def interactive_mode(self):
        """
        Modo interativo para testes manuais
        """
        print("\n" + "="*50)
        print("MODO INTERATIVO")
        print("="*50)
        print("Digite comandos G-code ou 'quit' para sair")
        print("Exemplos: M3, M4, M5, M3 S0, M3 S90, M3 S180")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\nComando: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'sair']:
                    break
                
                if user_input:
                    response = self.send_command(user_input)
                    if not response:
                        print("Sem resposta do GRBL")
                        
            except KeyboardInterrupt:
                print("\n\nInterrompido pelo usuário")
                break
        
        self.send_command("M5")
    
    def run_all_tests(self):
        """
        Executa todos os testes
        """
        print("INICIANDO TESTES DO GRBL COM SERVO")
        print("=" * 60)
        
        if not self.connect():
            return False
        
        try:
            if not self.test_basic_connection():
                print("Falha no teste básico. Abortando.")
                return False
            
            input("\nPressione ENTER para continuar com teste do relé...")
            self.test_relay_control()
            
            input("\nPressione ENTER para continuar com teste do servo...")
            self.test_servo_positions()
            
            input("\nPressione ENTER para testar posições intermediárias...")
            self.test_servo_intermediate_positions()
            
            input("\nPressione ENTER para executar sequência automatizada...")
            self.test_sequence_automation()
            
            input("\nPressione ENTER para testar tratamento de erros...")
            self.test_error_handling()
            
            print("\nTODOS OS TESTES CONCLUÍDOS!")
            
            choice = input("\nDeseja entrar no modo interativo? (s/N): ")
            if choice.lower().startswith('s'):
                self.interactive_mode()
            
        except KeyboardInterrupt:
            print("\n\nTestes interrompidos pelo usuário")
        
        finally:
            self.send_command("M5")
            self.disconnect()
        
        return True


def main():
    """
    Função principal
    """
    print("GRBL Servo Tester v1.0")
    print("Porta: COM3 | Baudrate: 115200")
    
    tester = GRBLServoTester(port='COM3', baudrate=115200)
    
    while True:
        print("\n" + "="*40)
        print("MENU PRINCIPAL")
        print("="*40)
        print("1. Executar todos os testes")
        print("2. Teste de conexão apenas")
        print("3. Modo interativo")
        print("4. Sair")
        
        try:
            choice = input("\nEscolha uma opção (1-4): ").strip()
            
            if choice == '1':
                tester.run_all_tests()
                break
            elif choice == '2':
                if tester.connect():
                    tester.test_basic_connection()
                    tester.disconnect()
            elif choice == '3':
                if tester.connect():
                    tester.interactive_mode()
                    tester.disconnect()
            elif choice == '4':
                print("Até logo!")
                break
            else:
                print("Opção inválida!")
                
        except KeyboardInterrupt:
            print("\n\nPrograma interrompido")
            break


if __name__ == "__main__":
    main()
