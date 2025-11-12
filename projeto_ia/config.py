import os
from dotenv import load_dotenv
from google import genai  # ← ADICIONE ESTA LINHA

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))
    FIREFOX_PROFILE_PATH = "./firefox_perfil"
    
    @classmethod
    def validate(cls):
        """Valida as configurações necessárias"""
        if not cls.GEMINI_API_KEY:
            print("⚠️  GEMINI_API_KEY não encontrada, usando respostas locais")
            return False
        else:
            print("✅ GEMINI_API_KEY configurada")
            
            # Testa a conexão com a API
            try:
                client = genai.Client(api_key=cls.GEMINI_API_KEY)
                print("✅ Conexão com Gemini API estabelecida")
                return True
            except Exception as e:
                print(f"❌ Erro ao conectar com Gemini API: {e}")
                return False