# servidor_controle.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from datetime import datetime
import socket
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class ServidorControle:
    def __init__(self, bot, porta=8080):
        self.bot = bot
        self.porta = porta
        self.host = self._get_local_ip()
        self.server = None
        self.server_running = True  # ⬅️ FLAG PARA CONTROLE DO SERVIDOR
        
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

    def setup_chrome(self):
        """Configura Chrome em tela cheia para VNC"""
        try:
            print("🔄 Iniciando Chrome em tela cheia...")
            
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            chrome_options = Options()
            
            # ✅ CONFIGURAÇÕES PARA TELA CHEIA
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1865,910')
            chrome_options.add_argument('--start-maximized')  # ✅ MAXIMIZADO
            chrome_options.add_argument('--kiosk')  # ✅ MODO QUASE TELA CHEIA

            # ✅ CONFIGURAÇÕES PARA REMOVER SCROLL
            chrome_options.add_argument('--hide-scrollbars')  # Esconde barras de scroll
            chrome_options.add_argument('--disable-overlay-scrollbar')  # Remove scroll overlay
            # ✅ BLOQUEAR CRIAÇÃO DE SCROLL
            chrome_options.add_argument('--disable-smooth-scrolling')
            chrome_options.add_argument('--force-device-scale-factor=1')
            
            # Configurações de performance
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--user-data-dir=/tmp/chrome_whatsapp')
            
            # ✅ REMOVER barras de interface
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-notifications')
            
            service = Service('/usr/local/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)

            print("✅ Chrome em tela cheia inicializado!")
            
            # ✅ FORÇAR TELA CHEIA VIA JAVASCRIPT
            driver.get('https://web.whatsapp.com')
            driver.execute_script("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
            
            return driver
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

    def testar_chrome(self):
        """Testa se o Chrome está funcionando corretamente"""
        print("🧪 Testando configuração do Chrome...")
        driver = self.setup_chrome()
        
        if driver:
            try:
                # Teste simples
                driver.get("https://www.google.com")
                print(f"✅ Chrome testado com sucesso! Título: {driver.title}")
                return True
            except Exception as e:
                print(f"❌ Erro durante teste do Chrome: {e}")
                return False
            finally:
                driver.quit()
        else:
            print("❌ Chrome não pôde ser inicializado")
            return False

    def iniciar(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                """Log simplificado - VERSÃO SUPER SEGURA"""
                try:
                    # Método ultra-conservador
                    path = 'unknown'
                    try:
                        path = self.path
                    except:
                        pass
                        
                    message = args[0] if args else ''
                    print(f"🌐 Servidor: {path} - {message}")
                except:
                    # Se tudo falhar, log mínimo
                    print("🌐 Servidor: request recebido")
            
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
                            "proxima_verificacao": f"{self.server.bot.check_interval} segundos",
                            "chrome_status": "Configurado" if hasattr(self.server.bot, 'driver') else "Não inicializado"
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
                    
                    elif self.path == '/chrome-test':
                        # Nova rota para testar o Chrome
                        resultado = self.server.bot.testar_chrome() if hasattr(self.server.bot, 'testar_chrome') else "Função não disponível"
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps({"chrome_test": str(resultado)}).encode('utf-8'))
                        print("🔧 Teste do Chrome solicitado")
                        
                    # ✅ NOVA ROTA: Página inicial
                    elif self.path == '/':
                        data = {
                            "status": "online", 
                            "bot": self.server.bot.personalidade.dados['nome'],
                            "mensagem": f"Bot {self.server.bot.personalidade.dados['nome']} está rodando!",
                            "endpoints": {
                                "/status": "GET - Status do bot",
                                "/pausar": "POST - Pausar o bot", 
                                "/continuar": "POST - Continuar o bot",
                                "/limpar": "GET - Limpar histórico",
                                "/chrome-test": "GET - Testar Chrome"
                            }
                        }
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json; charset=utf-8')
                        self._set_cors_headers()
                        self.end_headers()
                        self.wfile.write(json.dumps(data).encode('utf-8'))
                        print("📤 Página inicial enviada")
                        
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
                portas_tentativas = [8080, 8081, 8082, 8083, 8084, 8085, 8086]
                
                for porta in portas_tentativas:
                    try:
                        print(f"🔄 Tentando iniciar servidor na porta {porta}...")
                        self.server = HTTPServer(('0.0.0.0', porta), Handler)  # ✅ Use 0.0.0.0 para acesso externo
                        self.server.bot = self.bot
                        self.porta = porta
                        
                        print(f"✅ Servidor de controle iniciado com sucesso!")
                        print(f"📍 URL: http://{self.host}:{porta}")
                        print(f"📍 Local: http://localhost:{porta}")
                        print("📡 Endpoints disponíveis:")
                        print("   • GET  /status    - Status do bot")
                        print("   • POST /pausar    - Pausar o bot") 
                        print("   • POST /continuar - Continuar o bot")
                        print("   • GET  /limpar    - Limpar histórico")
                        print("   • GET  /chrome-test - Testar Chrome")
                        print("📡 Aguardando comandos...")
                        
                        # ✅ LOOP CORRIGIDO: Processa requisições sem bloquear
                        while self.server_running:
                            self.server.handle_request()
                            time.sleep(0.1)  # Pequena pausa para não sobrecarregar
                            
                        print("🛑 Loop do servidor finalizado")
                        break
                            
                    except OSError as e:
                        if "Address already in use" in str(e):
                            print(f"❌ Porta {porta} já está em uso.")
                            continue
                        else:
                            raise e
                            
            except Exception as e:
                print(f"❌ Erro fatal no servidor: {e}")
                print("📋 Stack trace completo:")
                import traceback
                traceback.print_exc()

        # Inicia o servidor em uma thread
        self.server_thread = threading.Thread(target=start_server, daemon=True)
        self.server_thread.start()
        
        # Aguarda um pouco e testa a conexão
        time.sleep(2)
        return self._testar_servidor()
    
    def _testar_servidor(self):
        """Testa se o servidor está respondendo (versão melhorada)"""
        try:
            import urllib.request
            import urllib.error
            print("🔍 Testando conexão com o servidor...")
            
            # Aguardar mais tempo para o servidor inicializar
            time.sleep(3)
            
            # Testar múltiplas URLs
            urls = [
                f'http://localhost:{self.porta}/status',
                f'http://127.0.0.1:{self.porta}/status',
                f'http://{self.host}:{self.porta}/status'
            ]
            
            for url in urls:
                try:
                    print(f"🔄 Testando {url}...")
                    with urllib.request.urlopen(url, timeout=10) as response:
                        if response.getcode() == 200:
                            print(f"✅ Servidor respondendo em {url}")
                            return True
                except urllib.error.URLError as e:
                    print(f"⚠️  Falha em {url}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️  Erro em {url}: {e}")
                    continue
            
            print("❌ Servidor não respondeu em nenhuma URL testada")
            return False
            
        except Exception as e:
            print(f"❌ Erro no teste do servidor: {e}")
            return False

    def parar(self):
        """Para o servidor de forma segura"""
        if self.server:
            print("🛑 Parando servidor...")
            self.server_running = False  # ✅ Para o loop principal
            
            # Força uma última requisição para desbloquear o handle_request()
            try:
                import urllib.request
                urllib.request.urlopen(f'http://localhost:{self.porta}/', timeout=1)
            except:
                pass
                
            if hasattr(self.server, 'shutdown'):
                self.server.shutdown()
            self.server.server_close()
            print("✅ Servidor parado com sucesso")
            
            # Aguarda a thread finalizar
            if hasattr(self, 'server_thread') and self.server_thread.is_alive():
                self.server_thread.join(timeout=2)
                print("✅ Thread do servidor finalizada")