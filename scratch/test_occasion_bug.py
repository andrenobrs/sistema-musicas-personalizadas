import os
import sys
from dotenv import load_dotenv

# Garante import do diretório correto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openai_service as ai

print("=========================================================================")
print("TESTANDO CORREÇÃO DO BUG DE OCASIÃO (OPENAI LYRICS GENERATION)")
print("=========================================================================")

occasion = "Homenagem para mãe"
giver = "Filho(a)"
receiver = "Maria"
story = "Ela sempre me apoiou"
style = "Gospel"

print(f"\nEnviando parâmetros para GPT-4o-mini:")
print(f"  - Ocasião: '{occasion}'")
print(f"  - Homenageado: '{receiver}'")
print(f"  - História: '{story}'")
print(f"  - Estilo: '{style}'")

result = ai.generate_lyrics_with_gpt4(
    occasion=occasion,
    giver=giver,
    receiver=receiver,
    story=story,
    style=style
)

print("\n=========================================================================")
print(f"LETRA GERADA:")
print("=========================================================================")
print(f"Título: {result['title']}")
print(f"Letra:\n{result['lyrics']}")
print("=========================================================================")

# Verificações básicas
lyrics_lower = result['lyrics'].lower()
has_mae = "mãe" in lyrics_lower or "mama" in lyrics_lower or "morta" in lyrics_lower or "minha coroa" in lyrics_lower or "mãezinha" in lyrics_lower
has_niver = "aniversário" in lyrics_lower or "parabéns" in lyrics_lower or "dia especial" in lyrics_lower or "celebrar" in lyrics_lower
has_maria = "maria" in lyrics_lower
has_apoio = "apoiou" in lyrics_lower or "apoio" in lyrics_lower or "segurou minha mão" in lyrics_lower or "cuidou" in lyrics_lower or "ajudou" in lyrics_lower or "estava lá" in lyrics_lower or "sempre" in lyrics_lower

print("\nVerificações de Segurança:")
print(f"  [VERIFICAÇÃO] Contém 'mãe' ou termos relacionados: {'SIM' if has_mae else 'NÃO'}")
print(f"  [VERIFICAÇÃO] Contém referências ao aniversário: {'SIM' if has_niver else 'NÃO'}")
print(f"  [VERIFICAÇÃO] Contém o nome 'Maria': {'SIM' if has_maria else 'NÃO'}")
print(f"  [VERIFICAÇÃO] Contém referências ao apoio/história: {'SIM' if has_apoio else 'NÃO'}")

if has_mae and has_maria:
    print("\n[RESULTADO] TESTE CONCLUÍDO COM SUCESSO! A ocasião foi totalmente respeitada.")
else:
    print("\n[RESULTADO] Falha nas verificações. A letra pode não ter focado nos parâmetros corretos.")
    sys.exit(1)
