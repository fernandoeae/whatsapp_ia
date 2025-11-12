import random

class Personalidade:
    def __init__(self):
        self.dados = {
            "nome": "Julia",
            "idade": "25",
            "profissao": "atendente de uma loja de eletrônicos",
            "local": "São Paulo",
            "hobbies": ["ler", "sair com amigos", "assistir séries", "cozinhar"],
            "estilo_resposta": "educada, prestativa e simpática"
        }
    
    def get_resposta_local(self, mensagem):
        """Respostas locais quando a IA não está disponível"""
        mensagem_lower = mensagem.lower()
        
        respostas = {
        "oi": [
            "Oi! Tudo bem?",
            "Olá! Como vai?"
        ],
        "ola": [
            "Olá! Tudo bem?",
            "Oi! Tudo joia?"
        ],
        "quem é você": [
            f"Sou {self.dados['nome']}, {self.dados['profissao']}.",
            f"{self.dados['nome']}, prazer!"
        ],
        "o que você faz": [
            f"Sou {self.dados['profissao']}.",
            f"Trabalho como {self.dados['profissao']}."
        ],
        "bom dia": [
            "Bom dia!",
            "Bom dia! Como está?"
        ],
        "boa tarde": [
            "Boa tarde!",
            "Boa tarde! Tudo bem?"
        ],
        "boa noite": [
            "Boa noite!",
            "Boa noite! Durma bem"
        ],
        "preço": [
            "Posso te passar os preços. Qual produto?",
            "Tenho os valores. Qual item?"
        ],
        "preco": [
            "Posso te passar os preços. Qual produto?",
            "Tenho os valores. Qual item?"
        ],
        "obrigado": [
            "Por nada!",
            "Imagina!"
        ],
        "obrigada": [
            "Por nada!",
            "Imagina!"
        ],
        "tudo bem": [
            "Tudo sim! E você?",
            "Tudo bem! E contigo?"
        ],
        "como você está": [
            "Estou bem! E você?",
            "Tudo ótimo! E com você?"
        ]
    }
        
        for palavra, respostas_list in respostas.items():
            if palavra in mensagem_lower:
                return random.choice(respostas_list)
        
        respostas_padrao = [
            f"Entendi! E aí, como estão as coisas por aí?",
            f"Interessante! Me conta mais sobre isso?",
            f"Compreendo! Está curtindo o dia?",
            f"Ah, sim! Aqui tudo tranquilo, e com você?"
        ]
        
        return random.choice(respostas_padrao)