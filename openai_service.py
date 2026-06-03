import os
import random
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_lyrics_with_gpt4(occasion, giver, receiver, story, style):
    estilo_musical = style
    ocasiao = occasion
    nome_homenageado = receiver
    historia = story

    system_prompt = "Você é um compositor de músicas profissional especializado em criar letras em português brasileiro. Retorne apenas a letra da música, sem anotações ou explicações de seções."

    user_content = f"""Escreva uma música de {estilo_musical} em português brasileiro.
Esta música é uma {ocasiao} para {nome_homenageado}.
Use OBRIGATORIAMENTE o nome {nome_homenageado} na letra.
A história/contexto é: {historia}
NUNCA mencione cônjuge, esposo, esposa, casamento 
a menos que a ocasião seja casamento.
A letra deve refletir exatamente a ocasião informada."""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        title = f"Canção para {receiver}"
        return {"title": title, "lyrics": content}
        
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
    # Garante um termo carinhoso caso giver venha vazio
    giver_display = giver if (giver and giver.strip()) else "quem te quer bem"
    
    # Extrai fragmentos da história ou usa texto padrão
    story_hook = story.strip() if story else "todas as memórias e risadas que compartilhamos"
    if len(story_hook) > 80:
        story_hook = story_hook[:77] + "..."
        
    occasion_lower = occasion.lower() if occasion else ""
    
    # Mapeamento e normalização inteligente da ocasião
    mapped_occasion = "Outra ocasião"
    if "aniversário" in occasion_lower or "niver" in occasion_lower:
        mapped_occasion = "Aniversário"
    elif "casamento" in occasion_lower or "união" in occasion_lower:
        mapped_occasion = "Casamento"
    elif "mãe" in occasion_lower or "materno" in occasion_lower:
        mapped_occasion = "Dia das Mães"
    elif "pai" in occasion_lower or "paterno" in occasion_lower:
        mapped_occasion = "Dia das Pais"
    elif "namoro" in occasion_lower or "noivado" in occasion_lower:
        mapped_occasion = "Pedido de namoro"
    elif "homenagem" in occasion_lower or "agradecimento" in occasion_lower:
        mapped_occasion = "Homenagem"
    elif "amizade" in occasion_lower or "amigo" in occasion_lower:
        mapped_occasion = "Amizade"
        
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
    
    selected_title = random.choice(titles.get(mapped_occasion, titles["Outra ocasião"]))
    
    # Injeção dinâmica de termos baseados na ocasião para o fallback ser altamente contextualizado
    v1_prefix = "Olho no relógio e fico a pensar"
    ref_theme = "meu norte, minha direção"
    
    if "aniversário" in occasion_lower and ("mãe" in occasion_lower or "mãezinha" in occasion_lower):
        v1_prefix = "Mãe, no seu aniversário, vim te comemorar"
        ref_theme = "minha mãe amada, parabéns e gratidão"
    elif "aniversário" in occasion_lower:
        v1_prefix = "Hoje é o seu dia, vim comemorar"
        ref_theme = "parabéns pelo seu dia e celebração"
    elif "mãe" in occasion_lower or "mães" in occasion_lower:
        v1_prefix = "Mãe, minha rainha, vim te homenagear"
        ref_theme = "minha mãe, meu porto seguro e direção"
    elif "pai" in occasion_lower or "pais" in occasion_lower:
        v1_prefix = "Pai, meu grande herói, vim te homenagear"
        ref_theme = "meu pai, meu exemplo e direção"
    
    # Versos poéticos customizados baseados no gênero
    rhymes_style = {
        "Sertanejo": {
            "v1": f"{v1_prefix} / Em tudo o que a gente já viveu até aqui\nO peito aperta de tanto amar / E hoje com essa moda eu vim me declarar para ti.",
            "ref": f"[Refrão]\n{receiver}, {ref_theme}\nO amor de {giver_display} é todo seu, não tem jeito não\nGuardo cada abraço e toda nossa história\nVocê gravou seu nome na minha memória!",
            "v2": f"Com {story_hook}\nEscrevemos nossa história em versos de ouro e paixão\nE na viola que chora e no peito que sente\nEu te entrego inteiro o meu coração.",
            "ponte": "[Ponte]\nE se o tempo passar e o cabelo branquear\nA gente vai lembrar desse dia e sorrir\nPorque o que é verdadeiro nunca vai sumir."
        },
        "MPB": {
            "v1": f"No compasso sutil do teu caminhar / Encontro a poesia que eu quis compor\n{receiver}, teu riso é brisa que acalma o mar\nE traz de volta a primavera do amor.",
            "ref": f"[Refrão]\nCanto o afeto que {giver_display} quer te dar\nNuma bossa suave pra te ninar\nNossas memórias são joias raras no papel\nSeu brilho pinta o meu próprio céu.",
            "v2": f"Nessa estrada com {story_hook}\nDescobrimos que a vida é arte do encontro sim\nCada passo contigo é poema vivido\nUm jardim florido que não tem mais fim.",
            "ponte": "[Ponte]\nDeixa o som da MPB te abraçar bem devagar\nSentir a alma vibrar no violão\nNa melodia mais pura da nossa canção."
        },
        "Pop": {
            "v1": f"A vida corre rápida na velocidade do som / Mas quando estou contigo eu perco a gravidade\nCom {giver_display} e {receiver} tudo entra no tom\nVocê é minha música, minha metade.",
            "ref": f"[Refrão]\nHey! O som tá batendo forte no coração\nEssa é a nossa batida, a nossa canção\nGuardo na mente cada flash de nós\nNão há nada melhor do que ouvir sua voz!",
            "v2": f"Lembrando de tudo, de cada momento legal\nDe {story_hook}\nNosso amor é hit, é fora do normal\nO som que embala e nos faz flutuar.",
            "ponte": "[Ponte]\nNenhum algoritmo consegue explicar\nO tamanho do brilho que existe em você\nÉ pop, é chic, é ver pra crer!"
        },
        "Gospel": {
            "v1": f"Deus abençoou sua vida e o seu caminhar / {v1_prefix}\nSua graça nos guia, nos enche de paz\nCom fé no amanhã nós iremos trilhar\nO caminho do bem que o Pai nos traz.",
            "ref": f"[Refrão]\n{receiver}, você é bênção do Criador\nUm presente sagrado repleto de amor\n{giver_display} agradece ao Senhor por te ter\nSua vida me inspira a vencer e crescer!",
            "v2": f"Através de {story_hook}\nVemos a mão do Altíssimo nos abençoar\nSob Suas asas, no Seu santo abrigo\nNossa família sempre vai prosperar.",
            "ponte": "[Ponte]\nO amor de Deus é nossa rocha e fundação\nE nessa harmonia de oração e louvor\nEntregamos a nossa gratidão ao Senhor."
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
