# servidor_controle.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from datetime import datetime
import socket
import time

class ServidorControle:
    def __init__(self, bot, porta=8080):
        self.bot = bot
        self.porta = porta
        self.host = self._get_local_ip()
        self.server = None
        
    def _get_local_ip(self):
        """Obtém o IP local da máquina"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def iniciar(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Log simplificado para debugging
                print(f"🌐 Servidor: {self.path} - {args[0] if args else ''}")
            
            def _set_cors_headers(self):
                """Configura headers CORS para todas as respostas"""
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Max-Age', '86400')
                
            def do_OPTIONS(self):
                """Handle CORS preflight requests"""
                self.send_response(200)
                self._set_cors_headers()
                self.end_headers()
                
            def do_GET(self):
                try:
                    print(f"📥 GET recebido: {self.path}")
                    
                    if self.path == '/status':
                        status = "PAUSADO" if self.server.bot.pausar_bot else "RODANDO"
                        data = {
                            "status": status,
                            "mensagens_respondidas": len(self.server.bot.ultimas_mensagens),
                            "ultima_acao": self.server.bot.ultima_acao,
                            "proxima_verificacao": f"{self.server.bot.check_interval} segundos"
                        }
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(data).encode('utf-8'))
                        print(f"📤 Status enviado: {status}")
                        
                    elif self.path == '/limpar':
                        self.server.bot.ultimas_mensagens.clear()
                        self.server.bot.conversas_processadas.clear()
                        if hasattr(self.server.bot, 'historico_conversas'):
                            self.server.bot.historico_conversas.clear()
                        self.server.bot.ultima_acao = "Histórico limpo manualmente"
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "Histórico limpo"}).encode('utf-8'))
                        print("🧹 Histórico limpo via servidor")
                        
                    else:
                        self.send_response(404)
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Endpoint não encontrado"}).encode('utf-8'))
                        print(f"❌ Endpoint não encontrado: {self.path}")
                        
                except Exception as e:
                    print(f"❌ Erro no servidor GET: {e}")
                    self.send_response(500)
                    self._set_cors_headers()
                    self.end_headers()
            
            def do_POST(self):
                """Handle POST requests dos botões"""
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    print(f"📥 POST recebido: {self.path}")
                    
                    if self.path == '/pausar':
                        self.server.bot.pausar_bot = True
                        self.server.bot.ultima_acao = "Bot pausado manualmente"
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "Bot pausado"}).encode('utf-8'))
                        print("⏸️  Bot pausado via servidor")
                        
                    elif self.path == '/continuar':
                        self.server.bot.pausar_bot = False
                        self.server.bot.ultima_acao = "Bot continuado manualmente"
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "Bot continuando"}).encode('utf-8'))
                        print("▶️  Bot continuado via servidor")
                        
                    else:
                        self.send_response(404)
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Endpoint não encontrado"}).encode('utf-8'))
                        print(f"❌ Endpoint POST não encontrado: {self.path}")
                        
                except Exception as e:
                    print(f"❌ Erro no servidor POST: {e}")
                    self.send_response(500)
                    self._set_cors_headers()
                    self.end_headers()

        def start_server():
            try:
                # Tenta diferentes portas
                portas_tentativas = [self.porta, 8081, 8082, 8083]
                
                for porta in portas_tentativas:
                    try:
                        print(f"🔄 Tentando iniciar servidor na porta {porta}...")
                        self.server = HTTPServer(('0.0.0.0', porta), Handler)
                        self.server.bot = self.bot
                        self.porta = porta  # Atualiza a porta usada
                        
                        print(f"✅ Servidor de controle iniciado com sucesso!")
                        print(f"📍 URL: http://{self.host}:{porta}")
                        print(f"📍 Local: http://localhost:{porta}")
                        print("📡 Endpoints disponíveis:")
                        print("   • GET  /status    - Status do bot")
                        print("   • POST /pausar    - Pausar o bot") 
                        print("   • POST /continuar - Continuar o bot")
                        print("   • GET  /limpar    - Limpar histórico")
                        print("📡 Aguardando comandos...")
                        
                        self.server.serve_forever()
                        break
                        
                    except OSError as e:
                        if "Address already in use" in str(e):
                            print(f"❌ Porta {porta} já está em uso.")
                            continue
                        else:
                            raise e
                            
            except Exception as e:
                print(f"❌ Erro fatal no servidor: {e}")

        # Inicia o servidor em uma thread
        self.server_thread = threading.Thread(target=start_server, daemon=True)
        self.server_thread.start()
        
        # Aguarda um pouco e testa a conexão
        time.sleep(2)
        return self._testar_servidor()
    
    def _testar_servidor(self):
        """Testa se o servidor está respondendo"""
        import urllib.request
        import urllib.error
        
        print("🔍 Testando conexão com o servidor...")
        
        # Tenta conectar via IP local
        try:
            with urllib.request.urlopen(f'http://{self.host}:{self.porta}/status', timeout=5) as response:
                if response.getcode() == 200:
                    print(f"✅ Servidor respondendo em http://{self.host}:{self.porta}")
                    return True
        except Exception as e:
            print(f"❌ Falha ao conectar via IP {self.host}: {e}")
        
        # Tenta conectar via localhost
        try:
            with urllib.request.urlopen(f'http://localhost:{self.porta}/status', timeout=5) as response:
                if response.getcode() == 200:
                    print(f"✅ Servidor respondendo em http://localhost:{self.porta}")
                    return True
        except Exception as e:
            print(f"❌ Falha ao conectar via localhost: {e}")
        
        print("❌ Servidor não está respondendo em nenhuma URL")
        return False

    def parar(self):
        """Para o servidor"""
        if self.server:
            self.server.shutdown()
            print("🛑 Servidor parado")