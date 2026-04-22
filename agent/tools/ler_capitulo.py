"""Leitura direta de capítulo(s) do edital a partir dos MDs gerados."""

from pathlib import Path
from langchain_core.tools import tool
from config import settings
from database.db import get_connection


def _splits_dir_de(edital_id: int) -> Path | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT arquivo_origem FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()
    if not row or not row["arquivo_origem"]:
        return None
    stem = Path(row["arquivo_origem"]).stem
    return settings.editais_dir / "splits" / stem


def _toc_path_de(edital_id: int) -> Path | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT arquivo_origem FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()
    if not row or not row["arquivo_origem"]:
        return None
    stem = Path(row["arquivo_origem"]).stem
    return settings.editais_dir / f"{stem}_toc.txt"


@tool
def listar_capitulos(edital_id: int) -> str:
    """Lista todos os capítulos/anexos de um edital com número e título.

    Útil pra decidir qual ler_capitulo() usar.
    Retorna o TOC completo do edital.

    Args:
        edital_id: ID numérico do edital (via listar_editais).
    """
    toc = _toc_path_de(edital_id)
    if not toc or not toc.exists():
        return f"TOC não disponível para edital_id={edital_id}."

    linhas = toc.read_text(encoding="utf-8").splitlines()
    # Só os nível 1 (# ...), com número
    splits = _splits_dir_de(edital_id)
    nivel1 = [l for l in linhas if l.startswith("# ")]

    out = [f"Capítulos do edital_id={edital_id}:"]
    out.append(f"cap_0: (preâmbulo do edital)")
    for i, linha in enumerate(nivel1, start=1):
        # linha tipo: "# 1 - Título (p. 1–1)"
        out.append(f"cap_{i}: {linha.removeprefix('# ').strip()}")
    out.append("\nUse ler_capitulo(edital_id, cap_num) para ler o conteúdo inteiro.")
    return "\n".join(out)


@tool
def ler_capitulo(edital_id: int, cap_num: int) -> str:
    """Lê o conteúdo INTEIRO de um capítulo do edital (em markdown).

    Use quando a pergunta cobre uma seção inteira do edital — por exemplo:
    conteúdo programático completo, cronograma, regras das provas, critérios
    de desempate. Também quando uma busca por similaridade retornou um
    tópico parcial e você quer o contexto completo (ex: viu 'tópico 2' e
    quer saber quais outros tópicos existem).

    Args:
        edital_id: ID numérico do edital (via listar_editais).
        cap_num:   número do capítulo (via listar_capitulos).
    """
    splits = _splits_dir_de(edital_id)
    if splits is None:
        return f"Edital_id={edital_id} não encontrado."

    md_path = splits / f"cap_{cap_num}.md"
    if not md_path.exists():
        return (
            f"cap_{cap_num} não existe para edital_id={edital_id}. "
            f"Use listar_capitulos({edital_id}) para ver os disponíveis."
        )

    conteudo = md_path.read_text(encoding="utf-8")
    if len(conteudo) > 30000:
        # Capítulos gigantes: avisa e corta; o agente pode pedir buscar_no_edital
        # com pergunta específica pra esse cap.
        conteudo = conteudo[:30000] + (
            "\n\n[... capítulo truncado — use buscar_no_edital(pergunta, edital_id) "
            "pra localizar trechos específicos]"
        )
    return f"=== cap_{cap_num} (edital_id={edital_id}) ===\n\n{conteudo}"
