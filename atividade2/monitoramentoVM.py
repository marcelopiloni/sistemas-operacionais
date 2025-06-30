import telnetlib
import paramiko
import time
import threading
import ftplib
import os
import json
from datetime import datetime
import subprocess
import base64

class MonitoramentoVMs:
    def __init__(self):
        self.vms = [
            {"host": "192.168.1.32", "usuario": "user", "senha": "user", "sistema": "linux", "nome": "Debian1"},
            {"host": "192.168.1.30", "usuario": "user", "senha": "user", "sistema": "linux", "nome": "Debian2"},
            {"host": "192.168.1.29", "usuario": "user", "senha": "user", "sistema": "windows", "nome": "Windows10"}
        ]
        self.resultado_monitoramento = {}
        self.lock = threading.Lock()

    def monitorar_linux_telnet(self, host, usuario, senha, nome):
        """Monitora sistema Linux via Telnet"""
        try:
            print(f"[{datetime.now()}] Conectando via Telnet a {host} ({nome})...")
            tn = telnetlib.Telnet(host, timeout=10)
            tn.read_until(b"login:", timeout=5)
            tn.write(usuario.encode("ascii") + b"\n")
            tn.read_until(b"Password:", timeout=5)
            tn.write(senha.encode("ascii") + b"\n")
            time.sleep(2)
            tn.read_very_eager()

            # Comandos para monitoramento detalhado
            comandos = {
                "Informações do Sistema": "uname -a",
                "Uptime": "uptime",
                "Memória Detalhada": "free -m && cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached'",
                "Uso de Disco": "df -h && du -sh /home /var /tmp 2>/dev/null",
                "CPU e Processos": "top -b -n1 | head -20",
                "Uso de Rede": "ifconfig && netstat -i",
                "Processos por CPU": "ps aux --sort=-%cpu | head -10",
                "Processos por Memória": "ps aux --sort=-%mem | head -10",
                "Temperatura": "sensors 2>/dev/null || echo 'sensors não disponível'",
                "Diretórios /tmp e /var": "ls -la /tmp && ls -la /var"
            }

            resultado = f"\n{'='*60}\n=== MONITORAMENTO DE {host} ({nome}) ===\n{'='*60}\n\n"
            
            for titulo, cmd in comandos.items():
                tn.write(cmd.encode("ascii") + b"\n")
                time.sleep(2)
                saida = tn.read_very_eager().decode("utf-8", errors="ignore").strip()
                resultado += f"--- {titulo} ---\n{saida}\n\n"

            # Injetar script de monitoramento contínuo
            self.injetar_script_linux(tn, host)
            
            tn.write(b"exit\n")
            time.sleep(1)
            tn.close()
            
            return resultado

        except Exception as e:
            return f"Erro ao conectar via Telnet a {host}: {e}"

    def monitorar_linux_ssh(self, host, usuario, senha, nome):
        """Monitora sistema Linux via SSH"""
        try:
            print(f"[{datetime.now()}] Conectando via SSH a {host} ({nome})...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=usuario, password=senha, timeout=10)

            # Comandos Linux via SSH
            comandos = {
                "Sistema": "uname -a",
                "Uptime": "uptime",
                "Memória": "free -h",
                "Disco": "df -h",
                "CPU": "top -b -n1 | head -10",
                "Rede": "ifconfig",
                "Processos CPU": "ps aux --sort=-%cpu | head -10",
                "Processos Memória": "ps aux --sort=-%mem | head -10",
                "Memória Detalhada": "cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached'",
                "Uso de Disco Detalhado": "du -sh /home /var /tmp 2>/dev/null",
                "Temperatura": "sensors 2>/dev/null || echo 'sensors não disponível'"
            }

            resultado = f"\n{'='*60}\n=== MONITORAMENTO DE {host} ({nome}) ===\n{'='*60}\n\n"
            
            for titulo, cmd in comandos.items():
                stdin, stdout, stderr = ssh.exec_command(cmd)
                saida = stdout.read().decode("utf-8", errors="ignore").strip()
                resultado += f"--- {titulo} ---\n{saida}\n\n"

            # Injetar script de monitoramento contínuo
            self.injetar_script_linux_ssh(ssh, host)

            ssh.close()
            return resultado

        except Exception as e:
            return f"Erro ao conectar via SSH a {host}: {e}"

    def monitorar_windows_ssh(self, host, usuario, senha, nome):
        """Monitora sistema Windows via SSH"""
        try:
            print(f"[{datetime.now()}] Conectando via SSH a {host} ({nome})...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=usuario, password=senha, timeout=10)

            # Comandos PowerShell para monitoramento detalhado
            comandos = {
                "Sistema": "Get-WmiObject -Class Win32_OperatingSystem | Select-Object Caption, Version, TotalVisibleMemorySize; Get-WmiObject -Class Win32_ComputerSystem | Select-Object Name, Manufacturer, Model",
                "Informações do Windows": "systeminfo | findstr /C:'OS Name' /C:'OS Version' /C:'System Type' /C:'Total Physical Memory'",
                "Memória": "Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory",
                "CPU": "Get-WmiObject -Class Win32_Processor | Select-Object Name, LoadPercentage, NumberOfCores, MaxClockSpeed",
                "Disco": "Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace, FileSystem",
                "Processos Top CPU": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name, CPU, WorkingSet, Id",
                "Processos Top Memória": "Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 Name, WorkingSet, CPU, Id",
                "Rede": "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, LinkSpeed, InterfaceDescription",
                "Serviços": "Get-Service | Where-Object Status -eq 'Running' | Select-Object -First 15 Name, Status, StartType",
                "Uptime": "Get-WmiObject -Class Win32_OperatingSystem | Select-Object @{Name='Uptime'; Expression={(Get-Date) - $_.ConvertToDateTime($_.LastBootUpTime)}}"
            }

            resultado = f"\n{'='*60}\n=== MONITORAMENTO DE {host} ({nome}) ===\n{'='*60}\n\n"
            
            for titulo, cmd in comandos.items():
                stdin, stdout, stderr = ssh.exec_command(f"powershell.exe -Command \"{cmd}\"")
                saida = stdout.read().decode("utf-8", errors="ignore").strip()
                erro = stderr.read().decode("utf-8", errors="ignore").strip()
                
                if saida:
                    resultado += f"--- {titulo} ---\n{saida}\n\n"
                elif erro:
                    resultado += f"--- {titulo} ---\nErro: {erro}\n\n"

            # Injetar script de monitoramento contínuo
            self.injetar_script_windows(ssh, host)
            
            ssh.close()
            return resultado

        except Exception as e:
            return f"Erro ao conectar via SSH a {host}: {e}"

    def injetar_script_linux(self, tn, host):
        """Injeta script de monitoramento contínuo no Linux via Telnet"""
        try:
            # Script que será executado em background
            script_content = '''#!/bin/bash
LOG_FILE="/tmp/monitor_log.json"
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    MEM_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    NETWORK_RX=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
    NETWORK_TX=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')
    
    echo "{\\"timestamp\\": \\"$TIMESTAMP\\", \\"memory\\": \\"$MEM_USAGE\\", \\"cpu\\": \\"$CPU_USAGE\\", \\"disk\\": \\"$DISK_USAGE\\", \\"network_rx\\": \\"$NETWORK_RX\\", \\"network_tx\\": \\"$NETWORK_TX\\"}" >> $LOG_FILE
    
    # Tira screenshot (se disponível)
    if command -v scrot &> /dev/null; then
        scrot "/tmp/screenshot_$(date +%Y%m%d_%H%M%S).png"
        # Manter apenas os 10 screenshots mais recentes
        ls -t /tmp/screenshot_*.png | tail -n +11 | xargs rm -f 2>/dev/null
    fi
    
    sleep 30
done &
'''
            
            # Escrever script no sistema remoto
            tn.write(b"cat > /tmp/monitor_script.sh << 'EOF'\n")
            time.sleep(0.5)
            tn.write(script_content.encode("ascii"))
            tn.write(b"EOF\n")
            time.sleep(1)
            
            # Dar permissão de execução e executar
            tn.write(b"chmod +x /tmp/monitor_script.sh\n")
            time.sleep(0.5)
            tn.write(b"nohup /tmp/monitor_script.sh &\n")
            time.sleep(1)
            # Adicionar ao crontab para iniciar no boot
            tn.write(b"(crontab -l 2>/dev/null; echo '@reboot /tmp/monitor_script.sh') | crontab -\n")
            time.sleep(1)
            
            print(f"Script de monitoramento injetado em {host}")
            
        except Exception as e:
            print(f"Erro ao injetar script no Linux {host}: {e}")

    def injetar_script_linux_ssh(self, ssh, host):
        """Injeta script de monitoramento contínuo no Linux via SSH"""
        try:
            # Script que será executado em background
            script_content = '''#!/bin/bash
LOG_FILE="/tmp/monitor_log.json"
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    MEM_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    NETWORK_RX=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
    NETWORK_TX=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')
    
    echo "{\\"timestamp\\": \\"$TIMESTAMP\\", \\"memory\\": \\"$MEM_USAGE\\", \\"cpu\\": \\"$CPU_USAGE\\", \\"disk\\": \\"$DISK_USAGE\\", \\"network_rx\\": \\"$NETWORK_RX\\", \\"network_tx\\": \\"$NETWORK_TX\\"}" >> $LOG_FILE
    
    # Tira screenshot (se disponível)
    if command -v scrot &> /dev/null; then
        scrot "/tmp/screenshot_$(date +%Y%m%d_%H%M%S).png"
        # Manter apenas os 10 screenshots mais recentes
        ls -t /tmp/screenshot_*.png | tail -n +11 | xargs rm -f 2>/dev/null
    fi
    
    sleep 30
done &
'''
            
            # Criar o script no sistema remoto
            stdin, stdout, stderr = ssh.exec_command(f"cat > /tmp/monitor_script.sh << 'EOF'\n{script_content}\nEOF")
            time.sleep(1)
            
            # Dar permissão de execução e executar
            ssh.exec_command("chmod +x /tmp/monitor_script.sh")
            time.sleep(0.5)
            ssh.exec_command("nohup /tmp/monitor_script.sh &")
            time.sleep(1)
            
            # Adicionar ao crontab para iniciar no boot
            ssh.exec_command("(crontab -l 2>/dev/null; echo '@reboot /tmp/monitor_script.sh') | crontab -")
            time.sleep(1)
            
            print(f"Script de monitoramento injetado em {host}")
            
        except Exception as e:
            print(f"Erro ao injetar script no Linux {host}: {e}")

    def injetar_script_windows(self, ssh, host):
        """Injeta script de monitoramento contínuo no Windows"""
        try:
            # Script PowerShell que será executado em background
            script_content = '''
$logFile = "C:\\temp\\monitor_log.json"
if (-not (Test-Path "C:\\temp")) { New-Item -ItemType Directory -Path "C:\\temp" }

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $memory = Get-WmiObject -Class Win32_OperatingSystem | ForEach-Object {[math]::Round((($_.TotalVisibleMemorySize - $_.FreePhysicalMemory) / $_.TotalVisibleMemorySize) * 100, 2)}
    $cpu = Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'" | ForEach-Object {[math]::Round((($_.Size - $_.FreeSpace) / $_.Size) * 100, 2)}
    
    $networkAdapter = Get-WmiObject -Class Win32_NetworkAdapter | Where-Object {$_.NetConnectionStatus -eq 2} | Select-Object -First 1
    $networkStats = Get-WmiObject -Class Win32_PerfRawData_Tcpip_NetworkInterface | Where-Object {$_.Name -like "*Ethernet*"} | Select-Object -First 1
    
    $logEntry = @{
        timestamp = $timestamp
        memory = $memory
        cpu = $cpu
        disk = $disk
        network_rx = if($networkStats) {$networkStats.BytesReceivedPerSec} else {0}
        network_tx = if($networkStats) {$networkStats.BytesSentPerSec} else {0}
    }
    
    $logEntry | ConvertTo-Json -Compress | Out-File -FilePath $logFile -Append -Encoding UTF8
    
    # Tira screenshot
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
    $timestamp_file = Get-Date -Format "yyyyMMdd_HHmmss"
    $bitmap.Save("C:\\temp\\screenshot_$timestamp_file.png")
    $graphics.Dispose()
    $bitmap.Dispose()
    
    # Manter apenas os 10 screenshots mais recentes
    Get-ChildItem "C:\\temp\\screenshot_*.png" | Sort-Object CreationTime -Descending | Select-Object -Skip 10 | Remove-Item -Force
    
    Start-Sleep -Seconds 30
}
'''
            
            # Criar o script no sistema remoto
            stdin, stdout, stderr = ssh.exec_command(f'powershell.exe -Command "Set-Content -Path \\"C:\\temp\\monitor_script.ps1\\" -Value @\\"\\n{script_content}\\n\\"@"')
            time.sleep(2)
            
            # Executar o script em background
            stdin, stdout, stderr = ssh.exec_command('powershell.exe -WindowStyle Hidden -Command "Start-Process powershell.exe -ArgumentList \\\"-WindowStyle Hidden -File C:\\temp\\monitor_script.ps1\\\" -WindowStyle Hidden"')
            
            # Adicionar ao startup do Windows
            stdin, stdout, stderr = ssh.exec_command('powershell.exe -Command "Copy-Item \\"C:\\temp\\monitor_script.ps1\\" \\"C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp\\monitor_script.ps1\\""')
            
            print(f"Script de monitoramento injetado em {host}")
            
        except Exception as e:
            print(f"Erro ao injetar script no Windows {host}: {e}")

    def coletar_logs_ftp(self, host, usuario, senha, sistema):
        """Coleta logs via FTP"""
        try:
            print(f"Coletando logs via FTP de {host}...")
            ftp = ftplib.FTP(host)
            ftp.login(usuario, senha)
            
            if sistema == "linux":
                log_file = "/tmp/monitor_log.json"
                local_file = f"logs_{host.replace('.', '_')}.json"
            else:
                log_file = "C:/temp/monitor_log.json"
                local_file = f"logs_{host.replace('.', '_')}.json"
            
            with open(local_file, 'wb') as f:
                ftp.retrbinary(f'RETR {log_file}', f.write)
            
            ftp.quit()
            print(f"Logs coletados de {host} -> {local_file}")
            return True
            
        except Exception as e:
            print(f"Erro ao coletar logs via FTP de {host}: {e}")
            return False

    def processar_thread(self, vm):
        """Processa monitoramento em thread separada"""
        try:
            if vm["sistema"] == "linux":
                # Você pode escolher entre SSH ou Telnet para Linux
                # Para usar SSH, descomente a linha abaixo:
                resultado = self.monitorar_linux_ssh(vm["host"], vm["usuario"], vm["senha"], vm["nome"])
                # Para usar Telnet, descomente a linha abaixo:
                # resultado = self.monitorar_linux_telnet(vm["host"], vm["usuario"], vm["senha"], vm["nome"])
            else:
                resultado = self.monitorar_windows_ssh(vm["host"], vm["usuario"], vm["senha"], vm["nome"])
            
            with self.lock:
                self.resultado_monitoramento[vm["host"]] = resultado
                
            # Salvar resultado individual
            nome_arquivo = f"monitoramento_{vm['host'].replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(nome_arquivo, "w", encoding="utf-8") as f:
                f.write(resultado)
            
            print(f"Monitoramento de {vm['host']} ({vm['nome']}) concluído!")
            
        except Exception as e:
            print(f"Erro no thread de {vm['host']}: {e}")

    def executar_monitoramento(self):
        """Executa monitoramento em todas as VMs usando threads"""
        print(f"Iniciando monitoramento de {len(self.vms)} VMs...")
        print(f"Timestamp: {datetime.now()}")
        print("-" * 80)
        
        threads = []
        
        # Criar e iniciar threads
        for vm in self.vms:
            thread = threading.Thread(target=self.processar_thread, args=(vm,))
            threads.append(thread)
            thread.start()
        
        # Aguardar conclusão de todas as threads
        for thread in threads:
            thread.join()
        
        # Gerar relatório consolidado
        self.gerar_relatorio_consolidado()
        
        print("\nMonitoramento concluído!")
        print(f"Resultados salvos em arquivos individuais e relatório consolidado.")

    def gerar_relatorio_consolidado(self):
        """Gera relatório consolidado de todas as VMs"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_relatorio = f"relatorio_consolidado_{timestamp}.txt"
        
        with open(nome_relatorio, "w", encoding="utf-8") as f:
            f.write("RELATÓRIO CONSOLIDADO DE MONITORAMENTO\n")
            f.write("=" * 80 + "\n")
            f.write(f"Gerado em: {datetime.now()}\n")
            f.write(f"Total de VMs monitoradas: {len(self.vms)}\n\n")
            
            for host, resultado in self.resultado_monitoramento.items():
                f.write(resultado)
                f.write("\n" + "=" * 80 + "\n")
        
        print(f"Relatório consolidado salvo: {nome_relatorio}")

    def limpar_logs_remotos(self):
        """Limpa logs antigos nos sistemas remotos"""
        for vm in self.vms:
            try:
                if vm["sistema"] == "linux":
                    # Usando SSH para limpar logs do Linux
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(hostname=vm["host"], username=vm["usuario"], password=vm["senha"], timeout=10)
                    ssh.exec_command("rm -f /tmp/monitor_log.json /tmp/screenshot_*.png")
                    ssh.close()
                else:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(hostname=vm["host"], username=vm["usuario"], password=vm["senha"], timeout=10)
                    ssh.exec_command('powershell.exe -Command "Remove-Item C:\\temp\\monitor_log.json, C:\\temp\\screenshot_*.png -Force"')
                    ssh.close()
                    
                print(f"Logs limpos em {vm['host']}")
                
            except Exception as e:
                print(f"Erro ao limpar logs em {vm['host']}: {e}")

def main():
    """Função principal"""
    monitor = MonitoramentoVMs()
    
    while True:
        print("\n" + "=" * 60)
        print("SISTEMA DE MONITORAMENTO DE VMs")
        print("=" * 60)
        print("1. Executar monitoramento completo")
        print("2. Coletar logs via FTP")
        print("3. Limpar logs remotos")
        print("4. Sair")
        print("-" * 60)
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            monitor.executar_monitoramento()
        elif opcao == "2":
            for vm in monitor.vms:
                monitor.coletar_logs_ftp(vm["host"], vm["usuario"], vm["senha"], vm["sistema"])
        elif opcao == "3":
            monitor.limpar_logs_remotos()
        elif opcao == "4":
            print("Encerrando sistema...")
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main()