# whatsapp_utils.py
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
import time

class WhatsAppUtils:
    @staticmethod
    def esperar_elemento(driver, by, selector, timeout=10):
        """Espera um elemento ficar disponível"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                element = driver.find_element(by, selector)
                if element.is_displayed() and element.is_enabled():
                    return element
            except:
                pass
            time.sleep(0.5)
        return None
    
    @staticmethod
    def digitar_texto_melhorado(driver, caixa, texto):
        """Método melhorado para digitar texto no WhatsApp"""
        try:
            actions = ActionChains(driver)
            actions.click(caixa)
            
            for char in texto:
                actions.send_keys(char)
                actions.pause(0.01)
            
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"❌ Erro no ActionChains: {e}")
            return False
    
    @staticmethod 
    def verificar_conversa_carregada(driver):
        """Verifica se a conversa carregou corretamente"""
        try:
            caixa_texto = driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true'][data-tab='10']")
            return bool(caixa_texto)
        except:
            return False
    
    @staticmethod
    def buscar_e_abrir_conversa_por_nome(driver, nome_contato):
        """Busca e abre uma conversa pelo nome do contato"""
        try:
            print(f"🔍 Buscando conversa: {nome_contato}")
            
            conversas = driver.find_elements(By.CSS_SELECTOR, "div[role='row']")
            
            for conversa in conversas[:20]:
                try:
                    if nome_contato in conversa.text:
                        conversa.click()
                        time.sleep(3)
                        return True
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
            
            return False
        except Exception as e:
            print(f"❌ Erro ao buscar conversa: {e}")
            return False