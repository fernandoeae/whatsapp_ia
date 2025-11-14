# main.py CORRIGIDO
from whatsapp_bot import WhatsAppBot
import time
import sys

def main():
    print("🚀 Iniciando Sistema WhatsApp Bot")
    
    try:
        print("🤖 Iniciando WhatsApp Bot...")
        bot = WhatsAppBot()
        
        print(f"\n🎯 SISTEMA COMPLETO PRONTO!")
        print(f"📍 Monitor VNC: http://31.97.251.184:6081/vnc.html")  # ✅ Porta 6081
        print(f"📱 WhatsApp Web: http://31.97.251.184:6081/vnc.html")  # ✅ Mesma URL
        print("⏳ Aguardando conexões...")
        
        bot.executar()
        
    except KeyboardInterrupt:
        print("\n🛑 Sistema interrompido pelo usuário")
    except Exception as e:
        print(f"💥 Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("👋 Sistema finalizado")

if __name__ == "__main__":
    main()