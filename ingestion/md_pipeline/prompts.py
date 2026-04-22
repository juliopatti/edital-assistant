"""
Prompts e mapeamento de modelos usados pela pipeline de TOC/MD.

ATENÇÃO: os prompts abaixo são COPIADOS VERBATIM do notebook toc_sonnet.ipynb.
Qualquer alteração aqui altera o comportamento da extração e pode degradar a
qualidade do corpus markdown gerado. Se precisar mudar, valide com cuidado.
"""

# Token budget
MAX_TOKENS_TOC = 32000
MAX_TOKENS_CAP = 32000

# Mapa de apelidos -> model_id por provider
MODELOS = {
    "anthropic": {
        "sonnet": "claude-sonnet-4-5",
        "haiku":  "claude-haiku-4-5",
    },
    "google": {
        "flash":      "gemini-2.5-flash",
        "flash-lite": "gemini-3.1-flash-lite-preview",
    },
}


# ---------------------------------------------------------------------------
# PROMPT 1 — Extração de TOC (Table of Contents)
# Usado em: toc_extractor.get_toc_md
# Entrada: PDF completo (em base64) + este prompt
# Saída esperada: lista em formato
#   ▶ 1 - Título (p. X)
#       • 1.1 - Subtítulo (p. X)
# ---------------------------------------------------------------------------
PROMPT_TOC = (
    "Leia o documento COMPLETO, do início ao fim, analisando TODAS as páginas. "
    "Extraia somente a estrutura útil do documento, em ordem, com número de página.\n\n"

    "Inclua apenas itens que sejam cabeçalhos reais de seção.\n\n"

    "Podem ser incluídos:\n"
    "- nível 1 numerado: 1, 2, 3...\n"
    "- nível 2 numerado: 1.1, 1.2, 2.1...\n"
    "- nível 3 numerado: 1.1.1, 1.1.2...\n"
    "- nível 4 numerado: 1.1.1.1, 1.1.1.2...\n"
    "- ANEXOS e APÊNDICES\n"
    "- subtítulos internos de ANEXOS e APÊNDICES até 4 níveis, mesmo sem numeração, desde que sejam cabeçalhos curtos e estruturais\n\n"

    "Distinção entre cabeçalho e parágrafo numerado (CRÍTICO):\n"
    "- muitos documentos usam numeração hierárquica (1, 1.1, 1.1.1) em parágrafos de texto corrido, não em cabeçalhos\n"
    "- numeração NÃO é indício suficiente de cabeçalho\n"
    "- um item só é cabeçalho quando tem rótulo curto e estrutural, visualmente destacado, funcionando como título de seção\n"
    "- se após o número vier texto corrido, frase completa, ou conteúdo que continua parágrafo, NÃO é cabeçalho — OMITA\n"
    "- se houver qualquer dúvida entre cabeçalho e parágrafo, OMITA\n"
    "- a mesma regra vale em qualquer nível (1, 1.1, 1.1.1, 1.1.1.1) e também dentro de anexos e apêndices\n\n"

    "Regras obrigatórias:\n"
    "- inclua um item somente se houver título curto, claro e estrutural\n"
    "- não inclua itens apenas porque possuem numeração\n"
    "- não inclua itens quando o texto parecer continuação de parágrafo ou texto corrido\n"
    "- não inclua títulos longos, descritivos ou com aparência de frase completa\n"
    "- não invente título\n"
    "- não complete título truncado\n"
    "- ignore nível 5 ou superior\n"
    "- se houver dúvida, omita\n\n"

    "Regra especial para ANEXOS e APÊNDICES:\n"
    "- depois de identificar um ANEXO ou APÊNDICE, continue examinando cuidadosamente TODAS as páginas pertencentes a ele\n"
    "- procure subtítulos internos curtos, mesmo que não estejam numerados\n"
    "- dentro de ANEXOS e APÊNDICES, também podem existir subitens equivalentes a nível 2, nível 3 e nível 4\n"
    "- esses subitens devem ser incluídos se forem curtos e estruturais\n"
    "- não pare no título principal do anexo/apêndice\n"
    "- só omita subitens do anexo/apêndice quando forem longos, textuais ou duvidosos\n\n"

    "Regra sobre hiatos de páginas:\n"
    "- se qualquer item cobrir muitas páginas sem subtítulos intermediários identificados, examine essas páginas com atenção redobrada procurando cabeçalhos internos curtos\n"
    "- um intervalo grande de páginas sem estrutura detectada é forte indício de que existem subtítulos ainda não capturados\n"
    "- vale tanto para o corpo principal quanto para ANEXOS e APÊNDICES\n"
    "- ainda assim, só inclua se forem curtos, estruturais e funcionarem como rótulo de seção\n\n"

    "Critério para decidir:\n"
    "- o item deve funcionar como rótulo de seção\n"
    "- o item deve ser curto\n"
    "- o item deve parecer visualmente um cabeçalho, e não conteúdo textual\n"
    "- a mesma regra vale para itens numerados e para subitens internos de anexos/apêndices\n\n"

    "Formato da saída:\n"
    "▶ 1 - Título (p. X)\n"
    "    • 1.1 - Subtítulo (p. X)\n"
    "        ◦ 1.1.1 - Subtítulo curto (p. X)\n"
    "            ▪ 1.1.1.1 - Subtítulo curto (p. X)\n"
    "▶ ANEXO I - Título (p. X)\n"
    "    • Subtítulo interno curto do anexo (p. X)\n"
    "        ◦ Subitem curto do anexo (p. X)\n"
    "            ▪ Subitem curto do anexo (p. X)\n"
    "▶ APÊNDICE A - Título (p. X)\n"
    "    • Subtítulo interno curto do apêndice (p. X)\n"
    "        ◦ Subitem curto do apêndice (p. X)\n"
    "            ▪ Subitem curto do apêndice (p. X)\n\n"

    "Retorne somente a lista, sem comentários, sem explicações e sem texto fora do formato."
)


# ---------------------------------------------------------------------------
# PROMPT 2 — Extração de markdown a partir do PDF de UM capítulo
# Usado em: md_extractor.extrair_md_capitulo
# Placeholders (via .format()):
#   - titulo_capitulo: título do capítulo atual
#   - trecho_proximo:  string adicional descrevendo o próximo título (pode ser "")
#   - trecho_parada:   string adicional descrevendo o ponto de parada (pode ser "")
# ---------------------------------------------------------------------------
PROMPT_EXTRACAO_CAP = """\
Você vai receber em PDF um trecho de um edital de concurso público brasileiro.
Esse trecho contém o capítulo "{titulo_capitulo}" e pode conter, na última página, o início do capítulo seguinte{trecho_proximo}.

Sua tarefa: extrair APENAS o conteúdo do capítulo "{titulo_capitulo}", formatado como markdown, aplicando o filtro descrito abaixo.

LIMITES DO CAPÍTULO:
- COMECE no título "{titulo_capitulo}" (ou na primeira linha relevante dele).
- PARE imediatamente ao encontrar o início do próximo capítulo{trecho_parada}. NÃO inclua o título do próximo capítulo nem qualquer linha dele.
- Ignore cabeçalhos/rodapés de página repetidos (nome do edital, paginação, etc.).

CONTEXTO DO LEITOR:
- O leitor é um candidato que vai prestar este concurso APENAS na ênfase "Ciência de Dados".
- Ele NÃO vai se inscrever em nenhuma outra ênfase.
- Conteúdo específico de OUTRAS ênfases é irrelevante e deve ser OMITIDO.
- Conteúdo comum (aplicável a qualquer candidato, independente da ênfase) é essencial e deve ser PRESERVADO.

REGRAS DE EXTRAÇÃO (sobre o texto que você mantiver):
1. Preserve o texto ORIGINAL, palavra por palavra. NÃO resuma, NÃO parafraseie, NÃO simplifique.
2. Mantenha a estrutura hierárquica (títulos, subtítulos, numeração 1., 1.1, 1.1.1, alíneas a), b), etc.).
3. Formate como markdown limpo: `#` para o título do capítulo, `##`/`###` para subseções, listas com `-` ou `1.`, negrito/itálico quando presentes no original.
4. Preserve a numeração exata dos itens (1.1, 1.2.3, I, II, a), b), etc.), exatamente como aparece.
5. Se houver tabelas, reproduza como tabelas markdown.

REGRAS DE FILTRAGEM:
MANTENHA integralmente:
- Toda seção cujo conteúdo se aplique a qualquer candidato (ex.: "Conhecimentos Básicos", regras gerais, Língua Portuguesa, Raciocínio Lógico, etc.).
- Toda seção específica da ênfase "Ciência de Dados" — inclua-a na ÍNTEGRA, sem cortar.

OMITA:
- Seções cujo conteúdo seja EXCLUSIVO de OUTRAS ênfases/cargos/áreas.
- Omita LIMPAMENTE: não deixe placeholder, não escreva "[seção omitida]", não comente o que foi removido, não liste as ênfases omitidas.

EM CASO DE DÚVIDA, PRESERVE.

SAÍDA:
- Retorne APENAS o markdown extraído e filtrado.
- Não adicione comentários, preâmbulos ou observações.
- Não envolva a saída em ```markdown ... ```.
- Comece direto pelo título do capítulo.
"""


# ---------------------------------------------------------------------------
# PROMPT 3 — Extração de texto corrido do cap_0 (preâmbulo do edital)
# Usado em: md_extractor.extrair_texto_cap0
# Placeholder (via .format()):
#   - trecho_parada: string descrevendo onde parar (pode ser "")
# ---------------------------------------------------------------------------
PROMPT_CAP0 = """\
Você vai receber em PDF a primeira página (ou páginas iniciais) de um edital de concurso público brasileiro.
Essa parte vem ANTES do primeiro capítulo numerado e normalmente contém: órgão/empresa responsável, título do edital, identificação do processo seletivo, data, e eventualmente um preâmbulo.

Sua tarefa: extrair o conteúdo como TEXTO CORRIDO ORGANIZADO.

LIMITES:
- PARE imediatamente ao encontrar o início do primeiro capítulo numerado{trecho_parada}. NÃO inclua o título nem qualquer linha dele.
- Ignore cabeçalhos/rodapés de página repetidos e paginação.

REGRAS:
1. Preserve o texto ORIGINAL, palavra por palavra. NÃO resuma, NÃO parafraseie.
2. NÃO use formatação markdown: nada de `#`, `##`, `**negrito**`, listas com `-` ou `1.`, etc.
3. Organize em parágrafos simples, separados por linha em branco, na ordem em que aparecem no documento.
4. Mantenha linha própria apenas para elementos que naturalmente ficam sozinhos (ex.: nome do órgão, título do edital, data) — sem marcadores.
5. Se houver numeração original no texto (ex.: "1.1", "I -"), preserve-a como parte do texto, mas sem transformar em lista markdown.

SAÍDA:
- Retorne APENAS o texto extraído.
- Não adicione comentários, preâmbulos ou observações.
- Não envolva em ```...```.
"""
