#!/usr/bin/env python3
import subprocess
import os
import time
import signal
import sys
from threading import Thread

class VNCManager:
    def __init__(self):
        self.vnc_port = 5902
        self.web_port = 6081
        self.vnc_process = None
        self.websockify_process = None
        self.running = True
        
    def is_process_running(self, process_name):
        """Verifica se processo está rodando"""
        try:
            result = subprocess.run(
                ['pgrep', '-u', os.getenv('USER'), '-f', process_name],
                capture_output=True, text=True
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def _cleanup_processes(self):
        """Limpa processos existentes"""
        print("🧹 Limpando processos VNC existentes...")
        os.system("pkill -f x11vnc")
        os.system("pkill -f websockify")
        os.system("pkill -f novnc_proxy")
        time.sleep(2)

    def _start_xvfb(self):
        """Inicia Xvfb com resolução correta"""
        try:
            print("🔧 Criando Xvfb :1 com 1000x720x24...")
            subprocess.Popen(["Xvfb", ":1", "-screen", "0", "1920x1080x24", "-ac"])
            time.sleep(3)
            os.environ["DISPLAY"] = ":1"
            return True
        except Exception as e:
            print(f"❌ Erro ao iniciar Xvfb: {e}")
            return False

    def _start_x11vnc(self):
        """Inicia x11vnc no display configurado"""
        try:
            print("🔧 Iniciando x11vnc...")
            vnc_cmd = f"x11vnc -display :1 -forever -shared -nopw -listen 0.0.0.0 -rfbport {self.vnc_port} -noxdamage"
            self.vnc_process = subprocess.Popen(vnc_cmd, shell=True)
            time.sleep(5)
            return self.is_process_running("x11vnc")
        except Exception as e:
            print(f"❌ Erro ao iniciar x11vnc: {e}")
            return False

    def _start_novnc(self):
        """Inicia noVNC de forma robusta"""
        try:
            novnc_path = os.path.expanduser("~/noVNC")
            
            if not os.path.exists(novnc_path):
                print("❌ Diretório noVNC não encontrado")
                return False
            
            # Método 1: novnc_proxy
            print("🔄 Iniciando noVNC...")
            original_dir = os.getcwd()
            os.chdir(novnc_path)
            
            novnc_cmd = f"./utils/novnc_proxy --vnc localhost:{self.vnc_port} --listen {self.web_port}"
            self.websockify_process = subprocess.Popen(novnc_cmd, shell=True)
            
            os.chdir(original_dir)
            time.sleep(5)
            
            if self.is_process_running("novnc_proxy"):
                print("✅ noVNC iniciado")
                return True
            
            print("❌ noVNC não iniciou")
            return False
            
        except Exception as e:
            print(f"❌ Erro noVNC: {e}")
            return False
            
    def start(self):
        """Inicia sistema VNC completo"""
        try:
            print("🖥️  Iniciando VNC...")
            
            # Limpar processos
            self._cleanup_processes()
            
            # Iniciar componentes na ordem correta
            if not self._start_xvfb():
                return False
                
            if not self._start_x11vnc():
                return False
                
            if not self._start_novnc():
                print("⚠️  noVNC falhou, mas x11vnc está rodando na porta 5902")
                return False
            
            print(f"🎉 VNC COMPLETO! Acesse: http://31.97.251.184:{self.web_port}/vnc.html")
            return True
            
        except Exception as e:
            print(f"❌ Erro VNC: {e}")
            return False

    def start_vnc(self):
        """Método alternativo mantido para compatibilidade"""
        return self.start()
            
    def monitor_services(self):
        """Monitora e reinicia serviços se necessário"""
        while self.running:
            time.sleep(30)
            
            if not self.is_process_running("x11vnc"):
                print("🔄 VNC caiu, reiniciando...")
                self.start()
                
            if not self.is_process_running("novnc_proxy"):
                print("🔄 noVNC caiu, reiniciando...")
                self._start_novnc()
                
    def stop(self):
        """Para todos os serviços"""
        print("🛑 Parando serviços VNC...")
        self.running = False
        
        # Parar processos específicos
        if self.vnc_process:
            try:
                self.vnc_process.terminate()
            except:
                pass
                
        if self.websockify_process:
            try:
                self.websockify_process.terminate()
            except:
                pass
        
        # Limpeza geral
        self._cleanup_processes()
        print("✅ Serviços VNC parados")
        
    def run(self):
        """Executa o gerenciador"""
        print("🎯 Iniciando VNC Manager...")
        
        # Inicia serviços
        if self.start():
            print(f"\n🎉 VNC SISTEMA PRONTO!")
            print(f"📍 URL: http://31.97.251.184:{self.web_port}/vnc.html")
            print("📊 Monitorando serviços...")
            
            # Inicia monitoramento em thread
            monitor_thread = Thread(target=self.monitor_services)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Mantém principal rodando
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Parando VNC por solicitação do usuário")
                
        self.stop()

if __name__ == "__main__":
    manager = VNCManager()
    
    def signal_handler(sig, frame):
        manager.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    manager.run()