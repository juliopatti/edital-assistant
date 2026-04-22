"""Busca semântica no texto dos editais com chunks estruturais."""

from langchain_core.tools import tool
from ingestion.rag import buscar_chunks


@tool
def buscar_no_edital(pergunta: str, edital_id: int = 0, n_results: int = 12) -> str:
    """Busca trechos relevantes no texto dos editais via similaridade semântica.

    Use para perguntas detalhadas não cobertas por dados estruturados:
    regras da prova, critérios de eliminação, o que pode levar no dia, etc.

    Args:
        pergunta: a pergunta do usuário (pode ser a pergunta crua).
        edital_id: ID do edital (via listar_editais). 0 = buscar em todos.
        n_results: quantos trechos retornar (default 12, suba pra 20 se precisar mais contexto).
    """

    # Primeiro: com filtro por edital. Se vier pouco, expande sem filtro.
    filtro_id = edital_id if edital_id > 0 else None
    chunks = buscar_chunks(pergunta, n_results=n_results, edital_id=filtro_id)

    if filtro_id is not None and len(chunks) < 3:
        sem_filtro = buscar_chunks(pergunta, n_results=n_results)
        if len(sem_filtro) > len(chunks):
            chunks = sem_filtro

    if not chunks:
        return (
            f"Nenhum trecho relevante encontrado para: '{pergunta}'.\n"
            "Sugestões: reformule a pergunta, tente consultar_edital para dados estruturados, "
            "ou ler_capitulo(edital_id, cap_num) se souber em qual capítulo procurar."
        )

    # Agrupar por (edital_id, cap_num), dentro do grupo ordenar por chunk_index
    # — o agente recebe trechos em ordem de leitura natural.
    from collections import defaultdict
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for c in chunks:
        m = c["metadata"]
        key = (m["edital_id"], m["cap_num"])
        grupos[key].append(c)

    # Ordena grupos por melhor distância (mais próximo primeiro)
    grupos_ordenados = sorted(
        grupos.items(),
        key=lambda kv: min(c.get("distancia") or 0 for c in kv[1]),
    )

    out: list[str] = [f"Encontrados {len(chunks)} trechos relevantes para '{pergunta}':"]
    for (eid, cap_num), lista in grupos_ordenados:
        lista.sort(key=lambda c: c["metadata"].get("chunk_index", 0))
        m0 = lista[0]["metadata"]
        cabecalho = (
            f"\n{'=' * 60}\n"
            f"Edital: {m0['orgao']} ({m0['numero_edital']}) — "
            f"cap_{cap_num}: {m0['cap_titulo']} "
            f"(pág {m0['pagina_inicio']}–{m0['pagina_fim']}) "
            f"[edital_id={eid}]\n"
            f"{'=' * 60}"
        )
        out.append(cabecalho)
        for c in lista:
            sec = c["metadata"].get("numero_secao") or ""
            tag = f"[seção {sec}] " if sec else ""
            out.append(f"\n{tag}")
            out.append(c["texto"])

    out.append(
        "\n\nDica: se vir uma seção específica (ex: 'tópico 2') e quiser a lista completa "
        "daquela seção, use ler_capitulo(edital_id, cap_num)."
    )
    return "\n".join(out)
