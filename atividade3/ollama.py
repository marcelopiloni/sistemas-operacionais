import os
import json
import hashlib
import time
import base64
import requests
import paramiko
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import PyPDF2
import io

class FileSystemMapper:
    """Classe para mapear manualmente o sistema de arquivos"""
    
    def __init__(self):
        self.filesystem_map = {}
        self.pdf_files = {}
        self.last_scan = None
    
    def create_file_hash(self, file_path, size, modified_time):
        """Cria hash único para identificar arquivos"""
        hash_string = f"{file_path}_{size}_{modified_time}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def parse_find_output_linux(self, find_output):
        """Parseia saída do comando find (Linux) para encontrar PDFs"""
        files = {}
        lines = find_output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or 'Permission denied' in line or 'No such file' in line:
                continue
            
            # Saída do find com -ls: inode blocks permissions links user group size date time path
            if ' ' in line and line.count(' ') >= 8:
                parts = line.split()
                try:
                    if len(parts) >= 9:
                        permissions = parts[2]
                        size = int(parts[6]) if parts[6].isdigit() else 0
                        date_time = f"{parts[7]} {parts[8]} {parts[9] if len(parts) > 9 and ':' in parts[9] else '2024'}"
                        file_path = ' '.join(parts[10:]) if len(parts) > 10 else parts[-1]
                        
                        if not file_path.lower().endswith('.pdf'):
                            continue
                        
                        filename = os.path.basename(file_path)
                        
                        file_info = {
                            'name': filename,
                            'path': file_path,
                            'size': size,
                            'permissions': permissions,
                            'modified': date_time,
                            'is_directory': False,
                            'is_pdf': True,
                            'os_type': 'linux'
                        }
                        
                        file_hash = self.create_file_hash(file_path, size, date_time)
                        files[file_hash] = file_info
                        self.pdf_files[file_hash] = file_info
                        
                except (ValueError, IndexError) as e:
                    print(f"Erro ao parsear linha Linux: {line} - {e}")
                    continue
            else:
                # Formato simples - apenas o caminho do arquivo
                if line.lower().endswith('.pdf') and os.path.isabs(line):
                    filename = os.path.basename(line)
                    file_info = {
                        'name': filename,
                        'path': line,
                        'size': 0,
                        'permissions': 'unknown',
                        'modified': 'unknown',
                        'is_directory': False,
                        'is_pdf': True,
                        'os_type': 'linux'
                    }
                    
                    file_hash = self.create_file_hash(line, 0, 'unknown')
                    files[file_hash] = file_info
                    self.pdf_files[file_hash] = file_info
        
        return files
    
    def parse_powershell_output(self, ps_output):
        """Parseia saída do PowerShell para encontrar PDFs no Windows"""
        files = {}
        lines = ps_output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or 'Access denied' in line or 'Cannot find' in line:
                continue
            
            try:
                # Formato esperado do PowerShell: Nome|CaminhoCompleto|Tamanho|DataModificacao
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        filename = parts[0].strip()
                        full_path = parts[1].strip()
                        size_str = parts[2].strip()
                        modified_date = parts[3].strip()
                        
                        if not filename.lower().endswith('.pdf'):
                            continue
                        
                        try:
                            size = int(size_str) if size_str.isdigit() else 0
                        except:
                            size = 0
                        
                        file_info = {
                            'name': filename,
                            'path': full_path,
                            'size': size,
                            'permissions': 'unknown',  # Windows não tem permissões Unix
                            'modified': modified_date,
                            'is_directory': False,
                            'is_pdf': True,
                            'os_type': 'windows'
                        }
                        
                        file_hash = self.create_file_hash(full_path, size, modified_date)
                        files[file_hash] = file_info
                        self.pdf_files[file_hash] = file_info
                        
            except Exception as e:
                print(f"Erro ao parsear linha Windows: {line} - {e}")
                continue
        
        return files
    
    def map_linux_filesystem(self, ssh):
        """Mapeia sistema de arquivos Linux via SSH"""
        filesystem = {}
        
        # Diretórios comuns onde PDFs podem estar
        directories_to_scan = [
            '/home/*/Downloads',
            '/home/*/Documentos',
            '/home/*/Documents', 
            '/home/*/Desktop',
            '/tmp',
            '/var/tmp',
            '/opt',
            '/usr/share/doc'
        ]
        
        print("Iniciando busca por PDFs no Linux...")
        
        for directory_pattern in directories_to_scan:
            try:
                print(f"Buscando em: {directory_pattern}")
                
                cmd = f"find {directory_pattern} -type f -name '*.pdf' -ls 2>/dev/null"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode('utf-8', errors='ignore')
                
                if output.strip() and 'No such file' not in output:
                    files = self.parse_find_output_linux(output)
                    filesystem.update(files)
                    print(f"Encontrados {len(files)} PDFs em {directory_pattern}")
                    
            except Exception as e:
                print(f"Erro ao escanear {directory_pattern}: {e}")
                continue
        
        # Busca adicional mais ampla se não encontrou nada
        if not filesystem:
            print("Tentando busca mais ampla no Linux...")
            try:
                cmd = "find /home -name '*.pdf' -type f 2>/dev/null | head -20"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode('utf-8', errors='ignore')
                
                if output.strip():
                    files = self.parse_find_output_linux(output)
                    filesystem.update(files)
                    print(f"Busca ampla Linux encontrou {len(files)} PDFs")
                    
            except Exception as e:
                print(f"Erro na busca ampla Linux: {e}")
        
        return filesystem
    
    def map_windows_filesystem(self, ssh):
        """Mapeia sistema de arquivos Windows via SSH (usando PowerShell)"""
        filesystem = {}
        
        # Diretórios comuns do Windows onde PDFs podem estar
        directories_to_scan = [
            'C:\\Users\\*\\Downloads',
            'C:\\Users\\*\\Documents',
            'C:\\Users\\*\\Desktop',
            'C:\\Temp',
            'C:\\Users\\Public\\Downloads',
            'C:\\Users\\Public\\Documents'
        ]
        
        print("Iniciando busca por PDFs no Windows...")
        
        for directory_pattern in directories_to_scan:
            try:
                print(f"Buscando em: {directory_pattern}")
                
                # PowerShell command para buscar PDFs com detalhes
                powershell_cmd = f'''
                powershell -Command "
                Get-ChildItem -Path '{directory_pattern}' -Filter '*.pdf' -Recurse -ErrorAction SilentlyContinue | 
                ForEach-Object {{ 
                    Write-Output ('{0}|{1}|{2}|{3}' -f $_.Name, $_.FullName, $_.Length, $_.LastWriteTime)
                }}"
                '''
                
                stdin, stdout, stderr = ssh.exec_command(powershell_cmd)
                output = stdout.read().decode('utf-8', errors='ignore')
                error_output = stderr.read().decode('utf-8', errors='ignore')
                
                if error_output:
                    print(f"Erros PowerShell: {error_output}")
                
                if output.strip():
                    files = self.parse_powershell_output(output)
                    filesystem.update(files)
                    print(f"Encontrados {len(files)} PDFs em {directory_pattern}")
                else:
                    print(f"Nenhum PDF encontrado em {directory_pattern}")
                    
            except Exception as e:
                print(f"Erro ao escanear {directory_pattern}: {e}")
                continue
        
        # Busca alternativa mais simples se não encontrou nada
        if not filesystem:
            print("Tentando busca mais ampla no Windows...")
            try:
                simple_cmd = '''powershell -Command "Get-ChildItem -Path 'C:\\Users' -Filter '*.pdf' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { Write-Output ('{0}|{1}|{2}|{3}' -f $_.Name, $_.FullName, $_.Length, $_.LastWriteTime) }"'''
                
                stdin, stdout, stderr = ssh.exec_command(simple_cmd)
                output = stdout.read().decode('utf-8', errors='ignore')
                
                if output.strip():
                    files = self.parse_powershell_output(output)
                    filesystem.update(files)
                    print(f"Busca ampla Windows encontrou {len(files)} PDFs")
                    
            except Exception as e:
                print(f"Erro na busca ampla Windows: {e}")
        
        return filesystem

class OllamaAnalyzer:
    """Classe para análise de PDFs usando Ollama"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2:latest"
    
    def test_connection(self):
        """Testa conexão com Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"Modelos Ollama disponíveis: {[m['name'] for m in models]}")
                return True
            return False
        except Exception as e:
            print(f"Erro ao conectar com Ollama: {e}")
            return False
    
    def analyze_pdf_content(self, pdf_text, file_path):
        """Analisa conteúdo PDF usando Ollama"""
        if not pdf_text.strip():
            return "Arquivo PDF vazio ou não foi possível extrair texto"
        
        # Limita o texto para não sobrecarregar a IA
        text_sample = pdf_text[:1500] if len(pdf_text) > 1500 else pdf_text
        
        prompt = f"""Analise o seguinte conteúdo de um arquivo PDF e identifique o tema principal em português.

Arquivo: {os.path.basename(file_path)}

Conteúdo do PDF:
{text_sample}

Responda apenas com o tema principal deste documento em uma frase curta e objetiva em português."""

        try:
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Erro na resposta').strip()
            else:
                return f"Erro na análise: Status {response.status_code}"
                
        except Exception as e:
            return f"Erro ao analisar PDF: {str(e)}"

class PDFCollector:
    """Classe principal para coleta de PDFs"""
    
    def __init__(self):
        self.mapper = FileSystemMapper()
        self.analyzer = OllamaAnalyzer()
        self.vms = []
    
    def add_vm(self, host, usuario, senha, sistema):
        """Adiciona VM à lista de monitoramento"""
        self.vms.append({
            'host': host,
            'usuario': usuario,
            'senha': senha,
            'sistema': sistema.lower()
        })
    
    def connect_ssh(self, vm_info):
        """Conecta a VM via SSH (funciona para Linux e Windows com OpenSSH)"""
        try:
            print(f"Conectando a {vm_info['host']} via SSH...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=vm_info['host'],
                username=vm_info['usuario'],
                password=vm_info['senha'],
                timeout=15
            )
            print(f"Conectado com sucesso via SSH!")
            return ssh
        except Exception as e:
            raise Exception(f"Erro ao conectar via SSH: {e}")
    
    def download_pdf_linux(self, pdf_info, ssh):
        """Baixa PDF via SSH do Linux"""
        try:
            print(f"Baixando PDF do Linux: {pdf_info['path']}")
            
            # Verifica se arquivo existe
            cmd = f"test -f '{pdf_info['path']}' && echo 'EXISTS' || echo 'NOT_FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if 'NOT_FOUND' in output or not output.strip():
                print(f"Arquivo não encontrado: {pdf_info['path']}")
                return None
            
            # Usa base64 para transferir arquivo binário
            cmd = f"base64 -w 0 '{pdf_info['path']}'"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            base64_content = stdout.read().decode('utf-8', errors='ignore')
            
            if base64_content.strip():
                try:
                    base64_string = base64_content.strip().replace('\n', '').replace('\r', '')
                    pdf_bytes = base64.b64decode(base64_string)
                    print(f"PDF Linux baixado: {len(pdf_bytes)} bytes")
                    return pdf_bytes
                except Exception as e:
                    print(f"Erro ao decodificar base64: {e}")
            
        except Exception as e:
            print(f"Erro no download Linux: {e}")
        
        return None
    
    def download_pdf_windows(self, pdf_info, ssh):
        """Baixa PDF via SSH do Windows usando múltiplos métodos"""
        try:
            print(f"Baixando PDF do Windows: {pdf_info['path']}")
            
            # Escapa o caminho do arquivo para PowerShell
            escaped_path = pdf_info['path'].replace("'", "''").replace("\\", "\\\\")
            
            # Verifica se arquivo existe
            check_cmd = f'powershell -Command "Test-Path \\"{escaped_path}\\""'
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            
            if 'False' in output or not output.strip():
                print(f"Arquivo não encontrado: {pdf_info['path']}")
                return None
            
            print("Tentando método 1: PowerShell com ReadAllBytes...")
            # Método 1: PowerShell com ReadAllBytes
            base64_cmd = f'powershell -Command "$bytes = [System.IO.File]::ReadAllBytes(\\"{escaped_path}\\"); [System.Convert]::ToBase64String($bytes)"'
            
            stdin, stdout, stderr = ssh.exec_command(base64_cmd)
            base64_content = stdout.read().decode('utf-8', errors='ignore')
            error_output = stderr.read().decode('utf-8', errors='ignore')
            
            if error_output:
                print(f"Erro PowerShell método 1: {error_output}")
            
            if base64_content.strip() and len(base64_content.strip()) > 100:
                try:
                    base64_string = base64_content.strip().replace('\n', '').replace('\r', '')
                    pdf_bytes = base64.b64decode(base64_string)
                    print(f"PDF Windows baixado (método 1): {len(pdf_bytes)} bytes")
                    return pdf_bytes
                except Exception as e:
                    print(f"Erro ao decodificar base64 método 1: {e}")
            
            print("Tentando método 2: PowerShell com Get-Content...")
            # Método 2: PowerShell com Get-Content -Encoding Byte
            byte_cmd = f'powershell -Command "$content = Get-Content \\"{escaped_path}\\" -Encoding Byte; [System.Convert]::ToBase64String($content)"'
            
            stdin, stdout, stderr = ssh.exec_command(byte_cmd)
            base64_content = stdout.read().decode('utf-8', errors='ignore')
            error_output = stderr.read().decode('utf-8', errors='ignore')
            
            if error_output:
                print(f"Erro PowerShell método 2: {error_output}")
            
            if base64_content.strip() and len(base64_content.strip()) > 100:
                try:
                    base64_string = base64_content.strip().replace('\n', '').replace('\r', '')
                    pdf_bytes = base64.b64decode(base64_string)
                    print(f"PDF Windows baixado (método 2): {len(pdf_bytes)} bytes")
                    return pdf_bytes
                except Exception as e:
                    print(f"Erro ao decodificar base64 método 2: {e}")
            
            print("Tentando método 3: certutil...")
            # Método 3: usando certutil (nativo do Windows)
            temp_b64_file = f"C:\\temp_{int(time.time())}.b64"
            certutil_cmd = f'certutil -encode "{pdf_info["path"]}" "{temp_b64_file}" && type "{temp_b64_file}" && del "{temp_b64_file}"'
            
            stdin, stdout, stderr = ssh.exec_command(certutil_cmd)
            certutil_output = stdout.read().decode('utf-8', errors='ignore')
            error_output = stderr.read().decode('utf-8', errors='ignore')
            
            if error_output:
                print(f"Erro certutil: {error_output}")
            
            if certutil_output.strip():
                # Filtra apenas as linhas base64 (remove cabeçalho e rodapé do certutil)
                lines = certutil_output.strip().split('\n')
                base64_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-----') and 'certificate' not in line.lower():
                        base64_lines.append(line)
                
                if base64_lines:
                    try:
                        base64_string = ''.join(base64_lines)
                        pdf_bytes = base64.b64decode(base64_string)
                        print(f"PDF Windows baixado (método 3): {len(pdf_bytes)} bytes")
                        return pdf_bytes
                    except Exception as e:
                        print(f"Erro ao decodificar base64 método 3: {e}")
            
            print("Tentando método 4: via SFTP...")
            # Método 4: Tenta usar SFTP se disponível
            try:
                sftp = ssh.open_sftp()
                with sftp.file(pdf_info['path'], 'rb') as remote_file:
                    pdf_bytes = remote_file.read()
                    sftp.close()
                    print(f"PDF Windows baixado (método 4 - SFTP): {len(pdf_bytes)} bytes")
                    return pdf_bytes
            except Exception as e:
                print(f"SFTP não disponível: {e}")
            
        except Exception as e:
            print(f"Erro no download Windows: {e}")
        
        return None
    
    def extract_pdf_text(self, pdf_bytes):
        """Extrai texto do PDF"""
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"Página {page_num + 1}: {len(page_text)} caracteres extraídos")
            
            print(f"Total de texto extraído: {len(text)} caracteres")
            return text.strip()
            
        except Exception as e:
            print(f"Erro ao extrair texto do PDF: {e}")
            return ""
    
    def scan_vm(self, vm_info):
        """Escaneia uma VM em busca de PDFs"""
        print(f"\n=== Escaneando {vm_info['host']} ({vm_info['sistema']}) ===")
        
        try:
            # Conecta à VM via SSH
            connection = self.connect_ssh(vm_info)
            
            # Mapeia sistema de arquivos baseado no OS
            if vm_info['sistema'] == 'linux':
                filesystem = self.mapper.map_linux_filesystem(connection)
            elif vm_info['sistema'] == 'windows':
                filesystem = self.mapper.map_windows_filesystem(connection)
            else:
                print(f"Sistema operacional não suportado: {vm_info['sistema']}")
                return []
            
            print(f"Encontrados {len(self.mapper.pdf_files)} arquivos PDF")
            
            # Analisa cada PDF encontrado
            results = []
            for file_hash, pdf_info in self.mapper.pdf_files.items():
                # Filtra apenas os PDFs da VM atual
                if pdf_info.get('os_type') != vm_info['sistema']:
                    continue
                    
                print(f"\nProcessando: {pdf_info['path']}")
                
                # Baixa conteúdo do PDF baseado no OS
                if vm_info['sistema'] == 'linux':
                    pdf_bytes = self.download_pdf_linux(pdf_info, connection)
                elif vm_info['sistema'] == 'windows':
                    pdf_bytes = self.download_pdf_windows(pdf_info, connection)
                else:
                    pdf_bytes = None
                
                if pdf_bytes:
                    # Extrai texto
                    pdf_text = self.extract_pdf_text(pdf_bytes)
                    
                    # Analisa com Ollama se disponível
                    if self.analyzer.test_connection():
                        theme = self.analyzer.analyze_pdf_content(pdf_text, pdf_info['path'])
                    else:
                        theme = "Ollama não disponível - Análise baseada no nome do arquivo"
                        # Fallback simples baseado no nome
                        filename = pdf_info['name'].lower()
                        if 'relatorio' in filename or 'report' in filename:
                            theme += " - Provavelmente um relatório"
                        elif 'manual' in filename or 'guia' in filename:
                            theme += " - Provavelmente um manual ou guia"
                        else:
                            theme += " - Documento não categorizado"
                    
                    result = {
                        'vm': vm_info['host'],
                        'os_type': vm_info['sistema'],
                        'file_path': pdf_info['path'],
                        'file_name': pdf_info['name'],
                        'size': pdf_info['size'],
                        'modified': pdf_info['modified'],
                        'permissions': pdf_info['permissions'],
                        'theme': theme,
                        'scan_time': datetime.now().isoformat(),
                        'text_length': len(pdf_text)
                    }
                    
                    results.append(result)
                    print(f"  → Tema: {theme}")
                else:
                    print(f"  → Erro ao baixar arquivo")
            
            # Fecha conexão SSH  
            connection.close()
            
            # Limpa os PDFs processados para próxima VM
            self.mapper.pdf_files.clear()
            
            return results
            
        except Exception as e:
            print(f"Erro ao escanear VM {vm_info['host']}: {e}")
            return []
    
    def scan_all_vms(self):
        """Escaneia todas as VMs configuradas"""
        all_results = []
        
        print("Iniciando coleta de PDFs...")
        print(f"Ollama disponível: {self.analyzer.test_connection()}")
        
        for vm_info in self.vms:
            results = self.scan_vm(vm_info)
            all_results.extend(results)
        
        return all_results
    
    def save_results(self, results, filename="pdf_scan_results.json"):
        """Salva resultados em arquivo JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Resultados salvos em {filename}")
    
    def print_results(self, results):
        """Exibe resultados na tela"""
        print(f"\n=== RELATÓRIO FINAL - {len(results)} PDFs encontrados ===")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Arquivo: {result['file_name']}")
            print(f"   Localização: {result['file_path']}")
            print(f"   VM: {result['vm']} ({result['os_type']})")
            print(f"   Tamanho: {result['size']} bytes")
            print(f"   Modificado: {result['modified']}")
            if result['os_type'] == 'linux':
                print(f"   Permissões: {result['permissions']}")
            print(f"   Tema: {result['theme']}")
            print(f"   Texto extraído: {result['text_length']} caracteres")

def main():
    """Função principal"""
    collector = PDFCollector()
    
    # Configuração das VMs - Linux
    collector.add_vm("192.168.1.32", "user", "user", "linux")
    collector.add_vm("192.168.1.30", "user", "user", "linux")
    
    # Configuração da VM Windows (substitua pelos seus dados)
    # Certifique-se que o OpenSSH Server está instalado e rodando no Windows
    collector.add_vm("192.168.1.29", "user", "user", "windows")
    
    # Executa varredura
    results = collector.scan_all_vms()
    
    # Salva e exibe resultados
    if results:
        collector.save_results(results)
        collector.print_results(results)
    else:
        print("Nenhum PDF foi encontrado ou processado.")
    
    print(f"\nProcessamento concluído. {len(results)} PDFs analisados.")

if __name__ == "__main__":
    main()