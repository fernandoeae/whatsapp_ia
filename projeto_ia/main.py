from whatsapp_bot import WhatsAppBot
import time
import sys

def main():
    print("🚀 Iniciando WhatsApp Bot com IA...")
    print("=" * 50)
    
    try:
        # Inicializar o bot
        bot = WhatsAppBot()
        
        # Executar o bot
        bot.executar()
        
    except KeyboardInterrupt:
        print(f"\n\n🛑 Bot interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Erro crítico: {e}")
        print("🔧 Verifique sua configuração e tente novamente")
        sys.exit(1)

if __name__ == "__main__":
    main()