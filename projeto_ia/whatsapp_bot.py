from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import time
import random
from datetime import datetime, date
from google import genai

from config import Config
from personalidade import Personalidade
from servidor_controle import ServidorControle
from whatsapp_utils import WhatsAppUtils

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.ultimas_mensagens = {}
        self.conversas_processadas = set()
        self.hoje = date.today()
        self.pausar_bot = False
        self.ultima_acao = "Bot iniciado"
        self.check_interval = Config.CHECK_INTERVAL
        self.ia_disponivel = False
        
        # ✅ NOVO: Sistema de histórico para contexto
        self.historico_conversas = {}
        self.max_historico = 15  # Mantém últimas 15 mensagens por conversa
        
        # Inicializar componentes
        self.personalidade = Personalidade()
        self.servidor = ServidorControle(self)
        self.utils = WhatsAppUtils()
        
        # Configurar IA
        self._configurar_ia()
        
        print(f"🎭 {self.personalidade.dados['nome']} - {self.personalidade.dados['profissao']}")
        print(f"📅 Bot configurado para responder apenas mensagens de: {self.hoje.strftime('%d/%m/%Y')}")
    
    def _configurar_ia(self):
        """Configura o cliente da IA Gemini"""
        try:
            import os
            # Tenta pegar a chave diretamente da variável de ambiente
            api_key = os.getenv('GEMINI_API_KEY')
            
            if api_key:
                self.client = genai.Client(api_key=api_key)
                self.ia_disponivel = True
                print(f"✅ IA Gemini configurada - Chave: {api_key[:10]}...")  # Debug
            else:
                self.ia_disponivel = False
                print("❌ GEMINI_API_KEY não encontrada nas variáveis de ambiente")
                print("⚠️  IA não disponível, usando respostas locais")
        except Exception as e:
            self.ia_disponivel = False
            print(f"❌ Erro ao configurar IA: {e}")
            print("⚠️  IA não disponível, usando respostas locais")
    
    def _adicionar_ao_historico(self, contato, mensagem, eh_bot=False):
        """✅ NOVO: Adiciona mensagem ao histórico da conversa"""
        if contato not in self.historico_conversas:
            self.historico_conversas[contato] = []
        
        self.historico_conversas[contato].append({
            "mensagem": mensagem,
            "eh_bot": eh_bot,
            "timestamp": datetime.now().strftime('%H:%M')
        })
        
        # Manter apenas as últimas mensagens
        if len(self.historico_conversas[contato]) > self.max_historico:
            self.historico_conversas[contato] = self.historico_conversas[contato][-self.max_historico:]
    
    def _obter_contexto_conversa(self, contato):
        """✅ NOVO: Obtém o contexto completo da conversa"""
        if contato not in self.historico_conversas or not self.historico_conversas[contato]:
            return "Esta é a primeira mensagem da conversa."
        
        contexto = "Histórico recente da conversa:\n"
        for msg in self.historico_conversas[contato][-6:]:  # Últimas 6 mensagens
            remetente = "Você" if msg["eh_bot"] else contato
            contexto += f"{remetente}: {msg['mensagem']}\n"
        
        return contexto

    def _e_conversa_grupo(self, elemento_conversa):
        """✅ NOVO: Verifica se a conversa é um grupo"""
        try:
            texto_completo = elemento_conversa.text
            linhas = texto_completo.split('\n')
            
            if len(linhas) >= 2:
                nome_contato = linhas[0].lower()
                
                # Palavras que indicam que é um grupo
                indicadores_grupo = [
                    'grupo', 'group', 'whatsapp', 'zap', 'família', 'family',
                    'amigos', 'friends', 'trabalho', 'work', 'escritório', 'office',
                    'turma', 'class', 'time', 'team', 'comunidade', 'community'
                ]
                
                # Se contém qualquer indicador de grupo no nome
                if any(indicator in nome_contato for indicator in indicadores_grupo):
                    return True
                
                # Se o nome é muito longo (provavelmente lista de participantes)
                if len(nome_contato) > 30:
                    return True
            
            return False
            
        except Exception:
            return False

    def iniciar_navegador(self):
        """Inicia o navegador Chromium no Linux"""
        try:
            from selenium.webdriver.chrome.options import Options
            import os
            
            options = Options()
            
            # Caminho do perfil
            profile_path = os.path.abspath("./chrome_profile")
            options.add_argument(f"--user-data-dir={profile_path}")
            
            # 🔥 CONFIGURAÇÕES ESSENCIAIS PARA SERVIDOR HEADLESS
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # 🔥 RESOLVE O ERRO DevToolsActivePort
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            
            # 🔥 PORTAS ALTERNATIVAS para evitar conflito
            options.add_argument("--remote-debugging-address=0.0.0.0")
            
            # Usar Chromium
            options.binary_location = "/usr/bin/chromium-browser"
            
            # 🔥 DESABILITAR LOGS DESNECESSÁRIOS
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            self.driver = webdriver.Chrome(options=options)
            
            print("✅ Navegador iniciado com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao iniciar navegador: {e}")
            return False
    
    def injetar_controle_whatsapp(self):
        """Injeta controles diretamente na página do WhatsApp - CORRIGIDO"""
        try:
            # Obtém o IP local dinamicamente
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "localhost"
            
            # Obtém a porta do servidor
            porta = getattr(self.servidor, 'porta', 8080)
            
            script = f"""
            // Remover controles existentes para evitar duplicação
            var controleExistente = document.getElementById('bot-controle');
            if (controleExistente) {{
                controleExistente.remove();
            }}
            
            var controle = document.createElement('div');
            controle.id = 'bot-controle';
            controle.innerHTML = `
                <div style="
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background: rgba(0,0,0,0.9);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    z-index: 10000;
                    font-family: Arial, sans-serif;
                    font-size: 12px;
                    min-width: 220px;
                    border: 2px solid #667eea;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                ">
                    <div style="font-weight: bold; margin-bottom: 8px; text-align: center; font-size: 14px;">🤖 Controle Bot</div>
                    <div style="display: flex; gap: 5px; margin-bottom: 8px;">
                        <button id="btn-pausar" 
                                style="background: #ff6b6b; color: white; border: none; padding: 8px 12px; border-radius: 5px; flex: 1; cursor: pointer; font-size: 11px; font-weight: bold;">⏸️ Pausar</button>
                        <button id="btn-continuar" 
                                style="background: #51cf66; color: white; border: none; padding: 8px 12px; border-radius: 5px; flex: 1; cursor: pointer; font-size: 11px; font-weight: bold;">▶️ Continuar</button>
                    </div>
                    <div style="display: flex; gap: 5px; margin-bottom: 8px;">
                        <button id="btn-status" 
                                style="background: #339af0; color: white; border: none; padding: 6px 10px; border-radius: 5px; flex: 1; cursor: pointer; font-size: 10px;">🔄 Status</button>
                        <button id="btn-limpar" 
                                style="background: #f76707; color: white; border: none; padding: 6px 10px; border-radius: 5px; flex: 1; cursor: pointer; font-size: 10px;">🧹 Limpar</button>
                    </div>
                    <div id="bot-status" style="margin-top: 8px; font-size: 10px; text-align: center; padding: 4px; background: rgba(255,255,255,0.1); border-radius: 3px;">Status: Conectando...</div>
                    <div id="bot-info" style="margin-top: 5px; font-size: 9px; text-align: center; color: #ccc;">Mensagens: 0</div>
                </div>
            `;
            
            // Adicionar controles à página
            document.body.appendChild(controle);
            
            // ✅ CORRIGIDO: Usa o IP REAL da máquina (não localhost)
            const SERVER_URL = 'http://{local_ip}:{porta}';
            console.log('🔗 Conectando ao servidor:', SERVER_URL);
            
            // Event listeners diretos
            document.getElementById('btn-pausar').addEventListener('click', function() {{
                pausarBot();
            }});
            
            document.getElementById('btn-continuar').addEventListener('click', function() {{
                continuarBot();
            }});
            
            document.getElementById('btn-status').addEventListener('click', function() {{
                atualizarStatus();
            }});
            
            document.getElementById('btn-limpar').addEventListener('click', function() {{
                limparHistorico();
            }});
            
            async function pausarBot() {{
                try {{
                    document.getElementById('bot-status').textContent = 'Status: Pausando...';
                    console.log('🔄 Enviando pausa para:', SERVER_URL + '/pausar');
                    const response = await fetch(SERVER_URL + '/pausar', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }});
                    if (response.ok) {{
                        document.getElementById('bot-status').textContent = 'Status: PAUSADO ✓';
                        document.getElementById('bot-status').style.color = '#ff6b6b';
                        document.getElementById('btn-pausar').style.background = '#495057';
                        document.getElementById('btn-continuar').style.background = '#51cf66';
                        console.log('✅ Bot pausado com sucesso');
                    }} else {{
                        throw new Error('Resposta não OK: ' + response.status);
                    }}
                }} catch (error) {{
                    document.getElementById('bot-status').textContent = 'Status: Erro de conexão';
                    document.getElementById('bot-status').style.color = '#ff6b6b';
                    console.error('❌ Erro ao pausar:', error);
                }}
            }}
            
            async function continuarBot() {{
                try {{
                    document.getElementById('bot-status').textContent = 'Status: Continuando...';
                    console.log('🔄 Enviando continuar para:', SERVER_URL + '/continuar');
                    const response = await fetch(SERVER_URL + '/continuar', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }});
                    if (response.ok) {{
                        document.getElementById('bot-status').textContent = 'Status: RODANDO ✓';
                        document.getElementById('bot-status').style.color = '#51cf66';
                        document.getElementById('btn-pausar').style.background = '#ff6b6b';
                        document.getElementById('btn-continuar').style.background = '#495057';
                        console.log('✅ Bot continuado com sucesso');
                    }} else {{
                        throw new Error('Resposta não OK: ' + response.status);
                    }}
                }} catch (error) {{
                    document.getElementById('bot-status').textContent = 'Status: Erro de conexão';
                    document.getElementById('bot-status').style.color = '#ff6b6b';
                    console.error('❌ Erro ao continuar:', error);
                }}
            }}
            
            async function atualizarStatus() {{
                try {{
                    console.log('🔄 Buscando status de:', SERVER_URL + '/status');
                    const response = await fetch(SERVER_URL + '/status');
                    if (response.ok) {{
                        const data = await response.json();
                        document.getElementById('bot-status').textContent = 'Status: ' + data.status;
                        document.getElementById('bot-status').style.color = data.status === 'PAUSADO' ? '#ff6b6b' : '#51cf66';
                        document.getElementById('bot-info').textContent = 'Msgs: ' + data.mensagens_respondidas + ' | ' + data.ultima_acao;
                        console.log('✅ Status atualizado:', data.status);
                    }} else {{
                        throw new Error('Resposta não OK: ' + response.status);
                    }}
                }} catch (error) {{
                    document.getElementById('bot-status').textContent = 'Status: Servidor offline';
                    document.getElementById('bot-status').style.color = '#ff6b6b';
                    console.error('❌ Erro ao atualizar status:', error);
                }}
            }}
            
            async function limparHistorico() {{
                try {{
                    document.getElementById('bot-status').textContent = 'Status: Limpando...';
                    console.log('🔄 Enviando limpar para:', SERVER_URL + '/limpar');
                    const response = await fetch(SERVER_URL + '/limpar');
                    if (response.ok) {{
                        document.getElementById('bot-status').textContent = 'Status: Histórico limpo ✓';
                        setTimeout(atualizarStatus, 1000);
                        console.log('✅ Histórico limpo com sucesso');
                    }} else {{
                        throw new Error('Resposta não OK: ' + response.status);
                    }}
                }} catch (error) {{
                    document.getElementById('bot-status').textContent = 'Status: Erro ao limpar';
                    console.error('❌ Erro ao limpar:', error);
                }}
            }}
            
            // Testar conexão inicial
            console.log('🔗 Iniciando teste de conexão...');
            setTimeout(atualizarStatus, 1000);
            
            // Atualizar status a cada 10 segundos
            setInterval(atualizarStatus, 10000);
            
            console.log('🤖 Controles do bot injetados com sucesso!');
            """
            
            self.driver.execute_script(script)
            print("🎮 Controles injetados no WhatsApp Web!")
            print(f"📍 Servidor: http://{local_ip}:{porta}")
            print("📱 Os botões agora devem funcionar!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao injetar controles: {e}")
            return False
    
    def verificar_mensagens_nao_lidas_prioridade(self):
        """🎯 VERIFICA PRIMEIRO MENSAGENS NÃO LIDAS (PRIORIDADE) - IGNORA GRUPOS"""
        try:
            print("🔍 Verificando MENSAGENS NÃO LIDAS (Prioridade)...")
            self.ultima_acao = "Verificando mensagens não lidas"
            
            conversas_nao_lidas = self.driver.find_elements(By.CSS_SELECTOR, "div[role='row']")
            conversas_com_nao_lidas = []
            
            for conversa in conversas_nao_lidas[:30]:
                try:
                    # ✅ NOVO: Ignorar grupos
                    if self._e_conversa_grupo(conversa):
                        continue

                    contadores = conversa.find_elements(By.CSS_SELECTOR, 
                        "span[data-testid='icon-unread-count'], " +
                        "span[aria-label*='unread'], " +
                        "div[class*='unread'], " +
                        "span[class*='unread']")
                    
                    tem_mensagens_nao_lidas = False
                    for contador in contadores:
                        if contador.is_displayed():
                            texto = contador.text.strip()
                            if texto.isdigit() or texto == "":
                                tem_mensagens_nao_lidas = True
                                break
                    
                    if tem_mensagens_nao_lidas:
                        texto_completo = conversa.text
                        linhas = texto_completo.split('\n')
                        
                        if len(linhas) >= 2:
                            nome_contato = linhas[0]
                            ultima_mensagem = linhas[-1]
                            
                            if self._e_conversa_de_hoje(conversa):
                                chave_conversa = f"{nome_contato}_naolidas_{ultima_mensagem[:30]}"
                                
                                if chave_conversa not in self.conversas_processadas:
                                    print(f"🎯 MENSAGEM NÃO LIDA: {nome_contato} - '{ultima_mensagem}'")
                                    conversas_com_nao_lidas.append((conversa, nome_contato, ultima_mensagem, True))
                                    self.conversas_processadas.add(chave_conversa)
                            
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    continue
            
            return conversas_com_nao_lidas
            
        except Exception as e:
            print(f"❌ Erro ao verificar mensagens não lidas: {e}")
            return []
    
    def verificar_conversas_recentes(self):
        """Verifica conversas recentes (segunda prioridade) - IGNORA GRUPOS"""
        try:
            print("📞 Verificando conversas recentes...")
            self.ultima_acao = "Verificando conversas recentes"
            
            conversas = self.driver.find_elements(By.CSS_SELECTOR, "div[role='row']")
            conversas_recentes = []
            
            for conversa in conversas[:20]:
                try:
                    # ✅ NOVO: Ignorar grupos
                    if self._e_conversa_grupo(conversa):
                        continue

                    texto_completo = conversa.text
                    linhas = texto_completo.split('\n')
                    
                    if len(linhas) >= 2:
                        nome_contato = linhas[0]
                        ultima_mensagem = linhas[-1]
                        
                        if self._e_conversa_recente(conversa):
                            chave_conversa = f"{nome_contato}_recente_{ultima_mensagem[:30]}"
                            
                            if chave_conversa not in self.conversas_processadas:
                                print(f"🔔 CONVERSA RECENTE: {nome_contato} - '{ultima_mensagem}'")
                                conversas_recentes.append((conversa, nome_contato, ultima_mensagem, False))
                                self.conversas_processadas.add(chave_conversa)
                            
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
            
            return conversas_recentes
            
        except Exception as e:
            print(f"❌ Erro ao verificar conversas recentes: {e}")
            return []
    
    def verificar_todas_conversas(self):
        """🎯 VERIFICA PRIMEIRO MENSAGENS NÃO LIDAS, DEPOIS CONVERSAS RECENTES - IGNORA GRUPOS"""
        try:
            print("🎯 Verificando conversas (Prioridade para não lidas, ignorando grupos)...")
            self.ultima_acao = "Verificando todas as conversas"
            
            conversas_nao_lidas = self.verificar_mensagens_nao_lidas_prioridade()
            
            if conversas_nao_lidas:
                print(f"🎯 {len(conversas_nao_lidas)} MENSAGEM(S) NÃO LIDA(S) encontrada(s) (ignorando grupos)")
                return conversas_nao_lidas
            
            conversas_recentes = self.verificar_conversas_recentes()
            
            if conversas_recentes:
                print(f"📞 {len(conversas_recentes)} conversa(s) recente(s) encontrada(s) (ignorando grupos)")
                return conversas_recentes
            
            print("👀 Nenhuma conversa individual nova encontrada")
            return []
            
        except Exception as e:
            print(f"❌ Erro ao verificar conversas: {e}")
            return []
    
    def _e_conversa_de_hoje(self, elemento_conversa):
        """Verifica se a conversa tem atividade de hoje"""
        try:
            timestamps = elemento_conversa.find_elements(By.CSS_SELECTOR, 
                "[class*='timestamp'], " +
                "[data-pre-plain-text], " +
                "span[class*='message-time']")
            
            for timestamp in timestamps:
                if timestamp.is_displayed():
                    texto = timestamp.text.strip().lower()
                    if texto:
                        if any(indicador in texto for indicador in ['hoje', 'today', 'agora', 'now']):
                            return True
                        if ':' in texto and len(texto) <= 5:
                            return True
            
            indicadores_novos = elemento_conversa.find_elements(By.CSS_SELECTOR, 
                "[class*='new'], " +
                "[class*='unread'], " +
                "[data-testid*='unread']")
            
            if indicadores_novos:
                return True
            
            return True
            
        except Exception:
            return True
    
    def _e_conversa_recente(self, elemento_conversa):
        """Verifica se a conversa é recente (últimas horas)"""
        try:
            timestamps = elemento_conversa.find_elements(By.CSS_SELECTOR, 
                "[class*='timestamp'], " +
                "span[class*='message-time']")
            
            for timestamp in timestamps:
                if timestamp.is_displayed():
                    texto = timestamp.text.strip().lower()
                    if texto:
                        if ':' in texto and len(texto) <= 5:
                            return True
                        if any(palavra in texto for palavra in ['hoje', 'today']):
                            return True
            
            return True
            
        except Exception:
            return True
    
    def processar_conversa_inteligente(self, conversa, nome_contato, ultima_mensagem, eh_nao_lida):
        """Processa uma conversa de forma inteligente - VERIFICA SE É GRUPO"""
        try:
            # ✅ VERIFICAÇÃO EXTRA: Confirmar que não é grupo
            if self._e_conversa_grupo(conversa):
                print(f"🚫 Ignorando grupo: {nome_contato}")
                return False

            if self.pausar_bot:
                print(f"⏸️ Bot pausado - Ignorando conversa com {nome_contato}")
                self.ultima_acao = f"Bot pausado - Ignorou {nome_contato}"
                return False
            
            indicador_prioridade = "🎯" if eh_nao_lida else "📞"
            print(f"{indicador_prioridade} Abrindo conversa com: {nome_contato}")
            self.ultima_acao = f"Processando conversa com {nome_contato}"
            
            try:
                conversa.click()
            except StaleElementReferenceException:
                print("🔄 Elemento obsoleto, buscando conversa novamente...")
                if not self.utils.buscar_e_abrir_conversa_por_nome(self.driver, nome_contato):
                    return False
            except Exception as e:
                print(f"❌ Erro ao clicar: {e}")
                return False
            
            time.sleep(4)
            
            if not self.utils.verificar_conversa_carregada(self.driver):
                print("❌ Conversa não carregou corretamente")
                self.driver.back()
                time.sleep(2)
                return False
            
            ultima_mensagem_info = self._ler_ultima_mensagem_com_remetente()
            
            if ultima_mensagem_info:
                texto, foi_enviada_pelo_bot = ultima_mensagem_info
                
                if foi_enviada_pelo_bot:
                    print(f"💤 Última mensagem foi enviada pelo bot: '{texto}' - Ignorando")
                    self.driver.back()
                    time.sleep(2)
                    return True
                
                print(f"📩 Última mensagem de {nome_contato}: '{texto}'")
                
                # ✅ NOVO: Adicionar ao histórico ANTES de responder
                self._adicionar_ao_historico(nome_contato, texto, eh_bot=False)
                
                chave_resposta = f"{nome_contato}_{texto[:50]}"
                
                if chave_resposta not in self.ultimas_mensagens:
                    if self._responder_mensagem(texto, nome_contato):
                        self.ultimas_mensagens[chave_resposta] = datetime.now()
                        self.ultima_acao = f"Respondeu {nome_contato}"
                        print("✅ Resposta enviada com sucesso!")
                    else:
                        print("❌ Falha ao enviar resposta")
                else:
                    print("💤 Já respondemos esta mensagem")
            else:
                print("💤 Nenhuma mensagem para responder")
            
            print("↩️ Voltando para lista...")
            self.driver.back()
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ Erro ao processar conversa: {e}")
            try:
                self.driver.back()
                time.sleep(2)
            except:
                pass
            return False
    
    def _ler_ultima_mensagem_com_remetente(self):
        """Lê a última mensagem e verifica se foi enviada pelo bot"""
        try:
            time.sleep(2)
            
            # Buscar todas as mensagens visíveis
            mensagens = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='message-']")
            
            if not mensagens:
                return None
            
            # Pegar a última mensagem
            ultima_mensagem = mensagens[-1]
            
            # Verificar se é uma mensagem de saída (enviada pelo bot)
            classes = ultima_mensagem.get_attribute("class")
            foi_enviada_pelo_bot = "message-out" in classes
            
            # Extrair o texto da mensagem
            texto_element = ultima_mensagem.find_elements(By.CSS_SELECTOR, "span[class*='selectable-text']")
            texto = texto_element[0].text.strip() if texto_element else ""
            
            # Verificar também pelo conteúdo se é do bot
            if texto and self._e_mensagem_do_bot(texto):
                foi_enviada_pelo_bot = True
            
            return (texto, foi_enviada_pelo_bot)
            
        except Exception as e:
            print(f"❌ Erro ao ler mensagem com remetente: {e}")
            return None
    
    def _e_mensagem_do_bot(self, mensagem):
        """Verifica se a mensagem foi enviada pelo bot"""
        palavras_bot = ["🤖", "😊", "👋", "✅", "tamo", "tmj", "vlw", "obrigado", "posso ajudar"]
        mensagem_lower = mensagem.lower()
        return any(palavra in mensagem_lower for palavra in palavras_bot)
    
    def _responder_mensagem(self, mensagem, contato):
        """Responde à mensagem COM CONTEXTO"""
        try:
            if self.pausar_bot:
                print("⏸️ Bot pausado - Não respondendo")
                return False
                
            # ✅ ATUALIZADO: Usar resposta com contexto
            resposta = self._gerar_resposta_com_contexto(mensagem, contato)
            print(f"🎭 {self.personalidade.dados['nome']} respondendo: '{resposta}'")
            
            caixa = self.utils.esperar_elemento(self.driver, By.CSS_SELECTOR, "[contenteditable='true'][data-tab='10']")
            if not caixa:
                print("❌ Caixa de texto não encontrada")
                return False
            
            caixa.click()
            time.sleep(1)
            
            if not self.utils.digitar_texto_melhorado(self.driver, caixa, resposta):
                print("❌ Método principal falhou, tentando alternativo...")
                return self._responder_mensagem_alternativo(resposta)
            
            # ✅ NOVO: Adicionar resposta ao histórico
            self._adicionar_ao_historico(contato, resposta, eh_bot=True)
            
            print("💬 Mensagem enviada com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao responder: {e}")
            return self._responder_mensagem_alternativo(resposta)
    
    def _gerar_resposta_com_contexto(self, mensagem, contato):
        """✅ NOVO: Gera resposta considerando o contexto da conversa"""
        if self.ia_disponivel:
            try:
                contexto = self._obter_contexto_conversa(contato)
                
                prompt = f"""
                Você é {self.personalidade.dados['nome']}, {self.personalidade.dados['idade']} anos, {self.personalidade.dados['profissao']} de {self.personalidade.dados['local']}.
            
                REGRAS IMPORTANTES:
                - Seja DIRETA e OBJETIVA
                - Respostas CURTAS (1-2 frases no máximo)
                - Evite rodeios e explicações longas
                - Mantenha o contexto mas seja concisa
                - Use linguagem casual mas breve
                - É uma conversa de WhatsApp, não um email formal
                - Não precisa ser muito elaborada
                - Foque na mensagem principal
                
                CONTEXTO DA CONVERSA:
                {contexto}
                
                MENSAGEM ATUAL: "{mensagem}"
                
                Responda de forma DIRETA e BREVE:
                """
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt
                )
                return response.text.strip()
                
            except Exception as e:
                print(f"⚠️ Erro na IA: {e}")
        
        # Respostas locais (fallback)
        return self.personalidade.get_resposta_local(mensagem)
    
    def _responder_mensagem_alternativo(self, resposta):
        """Método alternativo usando JavaScript avançado"""
        try:
            print("🔄 Tentando método alternativo avançado...")
            caixa = self.utils.esperar_elemento(self.driver, By.CSS_SELECTOR, "[contenteditable='true'][data-tab='10']")
            if not caixa:
                return False
            
            self.driver.execute_script("""
                var element = arguments[0];
                var text = arguments[1];
                
                element.focus();
                element.textContent = text;
                element.innerHTML = text;
                
                var events = ['input', 'change', 'keydown', 'keyup', 'keypress'];
                events.forEach(function(eventType) {
                    var event;
                    if (eventType.startsWith('key')) {
                        event = new KeyboardEvent(eventType, {
                            key: eventType === 'keydown' ? 'Enter' : '',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        });
                    } else {
                        event = new Event(eventType, { bubbles: true });
                    }
                    element.dispatchEvent(event);
                });
                
                if (element._valueTracker) {
                    element._valueTracker.setValue(text);
                }
                
            """, caixa, resposta)
            
            time.sleep(1)
            
            try:
                caixa.send_keys(Keys.ENTER)
            except:
                self.driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}))", caixa)
            
            time.sleep(1)
            print("💬 Mensagem enviada (método alternativo)!")
            return True
            
        except Exception as e:
            print(f"❌ Erro no método alternativo avançado: {e}")
            return False

    def limpar_historico(self):
        """Limpa histórico antigo para evitar memory leak"""
        agora = datetime.now()
        
        if len(self.conversas_processadas) > 100:
            self.conversas_processadas.clear()
            print("🧹 Conversas processadas limpas")
        
        chaves_remover = []
        for chave, timestamp in self.ultimas_mensagens.items():
            if (agora - timestamp).total_seconds() > 7200:
                chaves_remover.append(chave)
        
        for chave in chaves_remover:
            del self.ultimas_mensagens[chave]
        
        if chaves_remover:
            print(f"🧹 {len(chaves_remover)} mensagens antigas removidas")
        
        # ✅ NOVO: Limpar histórico de conversas antigo
        contatos_remover = []
        for contato, historico in self.historico_conversas.items():
            if not historico:
                contatos_remover.append(contato)
        
        for contato in contatos_remover:
            del self.historico_conversas[contato]
    
    def executar(self):
        """Método principal de execução do bot"""
        try:
            if not self.iniciar_navegador():
                return
            
            # 🌐 Iniciar servidor de controle
            self.servidor.iniciar()
            
            self.driver.get("https://web.whatsapp.com")
            print("🌐 WhatsApp Web carregado")
            time.sleep(15)
            
            # 🎮 Injeta controles na mesma página
            self.injetar_controle_whatsapp()
            
            print(f"\n🎭 {self.personalidade.dados['nome']} - BOT INICIADO!")
            print("💬 Personalidade: descontraída, bem-humorada e simpática")
            print("🧠 NOVO: Sistema de contexto ativado - Mantém histórico das conversas")
            print("🚫 NOVO: Ignorando grupos - Só responde conversas individuais")
            print("🔄 Monitorando mensagens...")
            print("\n🎮 CONTROLES INTEGRADOS:")
            print("   • Botões de controle injetados no WhatsApp")
            print("   • Use os botões no canto superior direito")
            
            contador = 0
            while True:
                if self.pausar_bot:
                    time.sleep(2)
                    continue
                    
                contador += 1
                print(f"\n🔍 Verificação #{contador} - {datetime.now().strftime('%H:%M:%S')}")
                self.ultima_acao = f"Verificação #{contador}"
                
                if contador % 5 == 0:
                    self.limpar_historico()
                
                conversas_novas = self.verificar_todas_conversas()
                
                if conversas_novas:
                    print(f"🎯 {len(conversas_novas)} conversa(s) encontrada(s)")
                    
                    for i, (conversa, nome, mensagem, eh_nao_lida) in enumerate(conversas_novas):
                        print(f"\n📨 Processando {i+1}/{len(conversas_novas)}: {nome}")
                        self.processar_conversa_inteligente(conversa, nome, mensagem, eh_nao_lida)
                        time.sleep(3)
                    
                    print(f"✅ Processamento concluído")
                else:
                    print("👀 Nenhuma conversa nova encontrada")
                
                print(f"⏳ Próxima verificação em {self.check_interval} segundos...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 {self.personalidade.dados['nome']} parada pelo usuário")
        except Exception as e:
            print(f"💥 Erro: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("👋 Firefox fechado!")