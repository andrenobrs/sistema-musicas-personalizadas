import os
import random
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_lyrics_with_gpt4(occasion, giver, receiver, story, style):
    """Compoe uma letra de musica personalizada usando o GPT-4 da OpenAI."""
    prompt = f"""
    Escreva a letra de uma música personalizada em português com base nos seguintes dados:
    - Ocasião: {occasion}
    - Quem oferece a música: {giver}
    - Quem recebe a música: {receiver}
    - História / Memórias especiais: {story}
    - Estilo musical: {style}

    A música deve ser emocionante, poética e integrar a história fornecida de forma natural e profunda.
    Estruture a letra com tags claras em colchetes para guiar a IA de áudio (ex: [Verso 1], [Refrão], [Verso 2], [Ponte], [Refrão Final]).
    Assegure que as tags estejam em linhas separadas.

    Retorne o resultado estritamente no seguinte formato:
    TÍTULO: [Insira um título romântico ou emocionante aqui]
    LETRA:
    [Letra da música aqui com as tags de estrutura]
    """

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o",  # ou gpt-4
            messages=[
                {"role": "system", "content": "Você é um compositor de música profissional de elite, famoso por escrever letras tocantes e memoráveis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        return parse_openai_response(content)
        
    except Exception as e:
        print(f"OpenAI error: {e}. Using intelligent fallback poetics engine.")
        return generate_fallback_lyrics(occasion, giver, receiver, story, style)

def parse_openai_response(text):
    """Analisa a resposta do GPT-4 e separa o Título da Letra."""
    title = "Uma Canção Para Você"
    lyrics = text
    
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.upper().startswith("TÍTULO:") or line.upper().startswith("TITULO:"):
            title = line.split(":", 1)[1].strip().replace("[", "").replace("]", "")
        elif line.upper().startswith("LETRA:"):
            lyrics = "\n".join(lines[i+1:]).strip()
            break
            
    return {"title": title, "lyrics": lyrics}

def generate_fallback_lyrics(occasion, giver, receiver, story, style):
    """Gerador poético heurístico local para o modo demonstração."""
    # Extrai fragmentos da história ou usa texto padrão
    story_hook = story.strip() if story else "todas as memórias e risadas que compartilhamos"
    if len(story_hook) > 80:
        story_hook = story_hook[:77] + "..."
        
    titles = {
        "Aniversário": [f"O Dia de {receiver}", f"Mais Um Ano de Luz", f"Celebrando Você, {receiver}"],
        "Casamento": ["Nossa Eterna Promessa", "O Altar do Amor", "Dois Caminhos, Um Destino"],
        "Dia das Mães": ["Mãe, Meu Porto Seguro", "Amor Que Não Tem Fim", "Coração de Mãe"],
        "Dia das Pais": ["Pai, Meu Grande Exemplo", "Herói do Dia a Dia", "Laços de Sangue e Amor"],
        "Pedido de namoro": [f"Quer Namorar Comigo, {receiver}?", "Diga Que Sim", "Nosso Novo Começo"],
        "Homenagem": ["Gratidão em Melodia", "Uma Vida de Inspiração", "Seu Brilho no Mundo"],
        "Amizade": ["Irmãos de Coração", "Amizade Verdadeira", "Parceria Eterna"],
        "Outra ocasião": ["Melodia de Sentimentos", "Para Sempre em Mim", "Sintonia Pura"]
    }
    
    selected_title = random.choice(titles.get(occasion, titles["Outra ocasião"]))
    
    # Versos poéticos customizados baseados no gênero
    rhymes_style = {
        "Sertanejo": {
            "v1": f"Olho no relógio e fico a pensar / Em tudo o que a gente já viveu até aqui\nO peito aperta de tanto amar / E hoje com essa moda eu vim me declarar para ti.",
            "ref": f"[Refrão]\n{receiver}, meu norte, minha direção\nO amor de {giver} é todo seu, não tem jeito não\nGuardo cada abraço e toda nossa história\nVocê gravou seu nome na minha memória!",
            "v2": f"Com {story_hook}\nEscrevemos nossa história em versos de ouro e paixão\nE na viola que chora e no peito que sente\nEu te entrego inteiro o meu coração.",
            "ponte": "[Ponte]\nE se o tempo passar e o cabelo branquear\nA gente vai lembrar desse dia e sorrir\nPorque o que é verdadeiro nunca vai sumir."
        },
        "MPB": {
            "v1": f"No compasso sutil do teu caminhar / Encontro a poesia que eu quis compor\n{receiver}, teu riso é brisa que acalma o mar\nE traz de volta a primavera do amor.",
            "ref": f"[Refrão]\nCanto o afeto que {giver} quer te dar\nNuma bossa suave pra te ninar\nNossas memórias são joias raras no papel\nSeu brilho pinta o meu próprio céu.",
            "v2": f"Nessa estrada com {story_hook}\nDescobrimos que a vida é arte do encontro sim\nCada passo contigo é poema vivido\nUm jardim florido que não tem mais fim.",
            "ponte": "[Ponte]\nDeixa o som da MPB te abraçar bem devagar\nSentir a alma vibrar no violão\nNa melodia mais pura da nossa canção."
        },
        "Pop": {
            "v1": f"A vida corre rápida na velocidade do som / Mas quando estou contigo eu perco a gravidade\nCom {giver} e {receiver} tudo entra no tom\nVocê é minha música, minha metade.",
            "ref": f"[Refrão]\nHey! O som tá batendo forte no coração\nEssa é a nossa batida, a nossa canção\nGuardo na mente cada flash de nós\nNão há nada melhor do que ouvir sua voz!",
            "v2": f"Lembrando de tudo, de cada momento legal\nDe {story_hook}\nNosso amor é hit, é fora do normal\nO som que embala e nos faz flutuar.",
            "ponte": "[Ponte]\nNenhum algoritmo consegue explicar\nO tamanho do brilho que existe em você\nÉ pop, é chic, é ver pra crer!"
        },
        "Gospel": {
            "v1": f"Deus traçou o plano e uniu nossas vidas no altar\nSua graça nos guia, nos enche de paz\nCom fé no amanhã nós iremos trilhar\nO caminho do bem que o Pai nos traz.",
            "ref": f"[Refrão]\n{receiver}, você é bênção do Criador\nUm presente sagrado repleto de amor\n{giver} agradece ao Senhor por te ter\nSua vida me inspira a vencer e crescer!",
            "v2": f"Através de {story_hook}\nVemos a mão do Altíssimo nos abençoar\nSob Suas asas, no Seu santo abrigo\nNossa família sempre vai prosperar.",
            "ponte": "[Ponte]\nO amor de Deus é nossa rocha e fundação\nE nessa harmonia de oração e louvor\nEntregamos as nossas vidas ao Senhor."
        }
    }
    
    style_data = rhymes_style.get(style, rhymes_style["MPB"])
    
    lyrics = f"""[Verso 1]
{style_data['v1']}

{style_data['ref']}

[Verso 2]
{style_data['v2']}

{style_data['ref']}

{style_data['ponte']}

[Refrão Final]
{style_data['ref'].replace('[Refrão]', '')}
"""
    
    return {"title": selected_title, "lyrics": lyrics.strip()}
