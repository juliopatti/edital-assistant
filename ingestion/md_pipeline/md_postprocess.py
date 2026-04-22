"""
Fase 6: pós-processamento dos markdowns gerados.

Linhas que começam com numeração hierárquica do edital (2.1 Texto, 2.1.1 Texto,
2.1.1.1 Texto) são convertidas em headers markdown do nível correspondente
(##, ###, ####, ...). Isso é necessário porque o LLM às vezes devolve o conteúdo
com a numeração correta mas sem marcar como header — o que prejudicaria o
chunking estrutural do RAG por headers.

Regras:
- cap_0 não é pós-processado (é texto corrido, não tem hierarquia numerada).
- Capítulos cujo título começa com ANEXO/APÊNDICE também não são pós-processados,
  porque sua numeração interna não segue a hierarquia do corpo principal.

Porta da célula 15 do notebook toc_sonnet.ipynb (versão final).
"""

import re
from pathlib import Path


# Casa linhas como "2.1 Texto", "2.1.1 Texto", "2.1.1.1 Texto" (mas NÃO "1 Texto",
# que é o próprio título do capítulo e já vem como `# 1. Título`).
RE_NUMERO_HIER = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\.?\s+(.*)$")


def aplicar_hierarquia_md(txt: str) -> str:
    """
    Converte linhas `N.N.N Texto` em `### N.N.N. Texto` (headers markdown).
    Linhas que não casam o padrão ficam inalteradas.
    """
    linhas_out = []
    for linha in txt.splitlines():
        m = RE_NUMERO_HIER.match(linha.strip())
        if not m:
            linhas_out.append(linha)                 # não mexe
            continue
        numero, resto = m.group(1), m.group(2)
        nivel = min(numero.count(".") + 1, 6)        # 2.1→2, 2.1.1→3, ...
        linhas_out.append(f"{'#' * nivel} {numero}. {resto}")
    return "\n".join(linhas_out)


def atualizar_mds(capitulos: list[dict]) -> None:
    """
    Aplica aplicar_hierarquia_md em todos os .md do edital.
    Pula cap_0 (texto corrido) e capítulos de ANEXO/APÊNDICE.
    """
    for cap in capitulos:
        cap_num  = cap["chapter_num"]
        cap_path = cap.get("cap_path")
        titulo   = (cap.get("title") or "").upper()

        if cap_num == 0 or not isinstance(cap_path, str):
            continue
        if titulo.startswith(("ANEXO", "APÊNDICE", "APENDICE")):
            print(f"[skip anexo/apêndice] cap_{cap_num}: {cap.get('title')}")
            continue

        md_path = Path(cap_path).with_suffix(".md")
        if not md_path.exists():
            continue
        original = md_path.read_text(encoding="utf-8")
        md_path.write_text(aplicar_hierarquia_md(original), encoding="utf-8")
        print(f"[ok] {md_path.name}")
