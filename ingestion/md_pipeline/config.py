"""
Escolha de provider/modelo para a pipeline de TOC/MD.

Por enquanto as opções ficam aqui no código (hardcoded).
No futuro podem migrar pra variáveis de ambiente via pydantic Settings.

Defaults (precaução de custo durante desenvolvimento):
    TOC e MD -> google / flash-lite (gemini-3.1-flash-lite-preview)

Cenário ideal (qualidade máxima):
    VAR_TOC = ("anthropic", "sonnet")   # claude-sonnet-4-5
    VAR_MD  = ("anthropic", "haiku")    # claude-haiku-4-5

Valores válidos para provider/modelo estão definidos em prompts.MODELOS.
"""

# (provider, modelo)
# VAR_TOC = ("google", "flash-lite")
# VAR_MD  = ("google", "flash-lite")

# Cenário ideal (qualidade máxima):
VAR_TOC = ("anthropic", "sonnet")   # claude-sonnet-4-5
VAR_MD  = ("anthropic", "haiku")    # claude-haiku-4-5

# Desempacotados como constantes individuais (usadas pelo pipeline)
PROVIDER_TOC, MODELO_TOC = VAR_TOC
PROVIDER_MD,  MODELO_MD  = VAR_MD
