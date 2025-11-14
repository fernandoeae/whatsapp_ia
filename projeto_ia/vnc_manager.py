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
            
    def start(self):
        """Inicia sistema VNC (método principal)"""
        try:
            print("🖥️  Iniciando VNC...")
            
            # Para processos existentes primeiro
            self._cleanup_processes()
            
            # ✅ CORREÇÃO: Usar COMANDO IDÊNTICO ao que funciona
            vnc_cmd = f"x11vnc -display :1 -forever -shared -nopw -listen 0.0.0.0 -rfbport {self.vnc_port} -noxdamage"
            self.vnc_process = subprocess.Popen(vnc_cmd, shell=True)  # ✅ shell=True
            time.sleep(5)
            
            # ✅ CORREÇÃO: Verificar se VNC está realmente rodando
            if not self.is_process_running("x11vnc"):
                print("❌ x11vnc não iniciou corretamente")
                return False
            
            # ✅ CORREÇÃO: Iniciar noVNC igual ao que funciona
            novnc_path = os.path.expanduser("~/noVNC")
            if os.path.exists(novnc_path):
                os.chdir(novnc_path)
                
                novnc_cmd = f"./utils/novnc_proxy --vnc localhost:{self.vnc_port} --listen {self.web_port}"
                self.websockify_process = subprocess.Popen(novnc_cmd, shell=True)  # ✅ shell=True
                time.sleep(3)
                
                if self.is_process_running("novnc_proxy"):
                    print(f"✅ noVNC iniciado com sucesso na porta {self.web_port}")
                else:
                    print("❌ noVNC não iniciou corretamente")
                    return False
            else:
                print("❌ Diretório noVNC não encontrado")
                return False
            
            print(f"✅ VNC rodando: http://31.97.251.184:{self.web_port}/vnc.html")
            return True
            
        except Exception as e:
            print(f"❌ Erro VNC: {e}")
            return False
    
    def start_vnc(self):
        """Inicia VNC server com resolução 1024x768"""
        try:
            print("🚀 Iniciando VNC server...")
            
            # Parar Xvfb existente
            os.system("pkill -f Xvfb")
            time.sleep(2)
            
            # ✅ RESOLUÇÃO 1024x768
            xvfb_cmd = ["Xvfb", ":1", "-screen", "0", "1000x720x24", "-ac"]
            subprocess.Popen(xvfb_cmd)
            time.sleep(3)
            
            os.environ["DISPLAY"] = ":1"
            
            vnc_cmd = f"x11vnc -display :1 -forever -shared -nopw -listen 0.0.0.0 -rfbport {self.vnc_port} -noxdamage"
            self.vnc_process = subprocess.Popen(vnc_cmd, shell=True)
            time.sleep(3)
            
            print("✅ VNC iniciado com resolução 1280x720x24")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao iniciar VNC: {e}")
            return False
            
    def start_websockify(self):
        """Método alternativo para iniciar WebSockify"""
        # Já é feito no método start()
        return True if self.websockify_process else False
            
    def monitor_services(self):
        """Monitora e reinicia serviços se necessário"""
        while self.running:
            time.sleep(30)
            
            if not self.is_process_running("x11vnc"):
                print("🔄 VNC caiu, reiniciando...")
                self.start_vnc()
                
            if not self.is_process_running("novnc_proxy"):
                print("🔄 noVNC caiu, reiniciando...")
                self.start_websockify()
                
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