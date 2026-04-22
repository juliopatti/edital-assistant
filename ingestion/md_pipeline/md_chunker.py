"""
Chunker estrutural para os markdowns gerados pelo md_pipeline.

Cada chunk é um pedaço de MARKDOWN VÁLIDO com a cadeia completa de headers
ancestrais reinjetada no topo. Assim:

    # ANEXO I – CONTEÚDO PROGRAMÁTICO
    ## CONHECIMENTOS ESPECÍFICOS: ANALISTA – Ciência de Dados – (Perfil 7)
    ### 2 - LINGUAGENS E BANCO DE DADOS

    Linguagem de programação Python. Sintaxe básica...

Isso dá ao embedding e ao leitor a estrutura hierárquica real — sem breadcrumb
inventado tipo "Contexto: X > Y > Z".

Quando um chunk agrega blocos irmãos, os headers intermediários ficam dentro
do chunk (não são perdidos), formando um MD ainda válido.

Parâmetros:
    CHUNK_MIN:   chunks menores tentam ser fundidos
    CHUNK_MAX:   chunks maiores são subdivididos
    CHUNK_ALVO:  alvo aproximado ao agregar parágrafos

Regras:
1. Corpo (cap_1..N não-anexo): unidade base = ## (seção). Headers H1 órfãos
   (sem conteúdo próprio) não viram chunk — viram contexto dos filhos.
2. Chunks pequenos são fundidos com irmão vizinho sob o mesmo H1, mantendo
   headers intermediários como parte do chunk.
3. Chunks grandes subdividem por ###, depois por parágrafo. Sub-chunks herdam
   h1..h4 do pai.
4. Cap_0 (preâmbulo): texto corrido, split por parágrafos até CHUNK_ALVO.
"""

import re
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Parâmetros (ajustáveis)
# ---------------------------------------------------------------------------
CHUNK_MIN  = 400
CHUNK_MAX  = 3500
CHUNK_ALVO = 1500


# Header markdown: 1..6 '#' seguido de espaço e texto
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")

# Numeração hierárquica tipo "9.6.1" no começo do header
_NUMERO_SECAO_RE = re.compile(r"^(\d+(?:\.\d+)+)\b")


def _tipo_capitulo(cap_num: int, cap_titulo: str) -> str:
    if cap_num == 0:
        return "preambulo"
    t = (cap_titulo or "").upper()
    if t.startswith("ANEXO"):
        return "anexo"
    if t.startswith(("APÊNDICE", "APENDICE")):
        return "apendice"
    return "corpo"


def _extrair_numero_secao(header_texto: str) -> str | None:
    m = _NUMERO_SECAO_RE.match(header_texto.strip())
    return m.group(1) if m else None


def _header_md(nivel: int, texto: str) -> str:
    return f"{'#' * nivel} {texto}"


# ---------------------------------------------------------------------------
# Parser: MD bruto -> lista de blocos com nivel/header/conteudo/h1..h4
# ---------------------------------------------------------------------------

def _parse_blocos(md_text: str) -> list[dict]:
    """Split do MD em blocos {nivel, header, conteudo, h1..h4}."""
    linhas = md_text.splitlines()
    stack: list[str | None] = [None, None, None, None]  # h1..h4

    blocos: list[dict] = []
    conteudo_atual: list[str] = []
    header_atual: dict | None = None

    def flush():
        if header_atual is None:
            return
        blocos.append({**header_atual, "conteudo": "\n".join(conteudo_atual).strip()})

    for linha in linhas:
        m = _HEADER_RE.match(linha)
        if m and len(m.group(1)) <= 4:
            flush()
            conteudo_atual = []

            nivel = len(m.group(1))
            header_txt = m.group(2).strip()

            stack[nivel - 1] = header_txt
            for i in range(nivel, 4):
                stack[i] = None

            header_atual = {
                "nivel":  nivel,
                "header": header_txt,
                "h1": stack[0], "h2": stack[1], "h3": stack[2], "h4": stack[3],
            }
        else:
            if header_atual is None:
                header_atual = {
                    "nivel":  0, "header": "",
                    "h1": None, "h2": None, "h3": None, "h4": None,
                }
            conteudo_atual.append(linha)

    flush()
    return blocos


# ---------------------------------------------------------------------------
# Renderização: bloco -> markdown válido com cadeia de ancestrais
# ---------------------------------------------------------------------------

def _renderizar_chunk_md(
    conteudo: str,
    h1: str | None, h2: str | None, h3: str | None, h4: str | None,
    self_nivel: int | None = None,
) -> str:
    """
    Monta um markdown válido com os headers ancestrais preenchidos + conteúdo.

    Se self_nivel é passado, o header desse nível é o do próprio bloco (ele
    já vem no conteudo ou é o próprio `hN`). Headers de nível menor que
    self_nivel entram como ancestrais.
    """
    linhas: list[str] = []
    cadeia = [(1, h1), (2, h2), (3, h3), (4, h4)]
    for nivel, texto in cadeia:
        if texto:
            linhas.append(_header_md(nivel, texto))
    if linhas:
        linhas.append("")  # linha em branco antes do conteúdo
    if conteudo.strip():
        linhas.append(conteudo.strip())
    return "\n".join(linhas).strip()


def _bloco_para_md(bloco: dict) -> str:
    """Renderiza o bloco como MD com sua cadeia ancestral completa."""
    return _renderizar_chunk_md(
        bloco["conteudo"],
        bloco.get("h1"), bloco.get("h2"), bloco.get("h3"), bloco.get("h4"),
    )


# ---------------------------------------------------------------------------
# Descartar H1 órfão (H1 sem conteúdo, só serve de contexto pros filhos)
# ---------------------------------------------------------------------------

def _descartar_headers_orfaos(blocos: list[dict]) -> list[dict]:
    out = []
    for i, b in enumerate(blocos):
        if b["nivel"] == 1 and len(b["conteudo"]) < 10:
            if i + 1 < len(blocos) and blocos[i + 1]["nivel"] > 1:
                continue
        out.append(b)
    return out


# ---------------------------------------------------------------------------
# Split de blocos grandes
# ---------------------------------------------------------------------------

def _split_por_paragrafo(texto: str, alvo: int) -> list[str]:
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    out: list[str] = []
    buffer: list[str] = []
    tam = 0
    for p in paragrafos:
        if tam + len(p) > alvo and buffer:
            out.append("\n\n".join(buffer))
            buffer = [p]
            tam = len(p)
        else:
            buffer.append(p)
            tam += len(p) + 2
    if buffer:
        out.append("\n\n".join(buffer))
    return out


def _quebrar_bloco_grande(bloco: dict) -> list[dict]:
    """Se passa de CHUNK_MAX, subdivide preservando h1..h4 do pai."""
    texto = bloco["conteudo"]
    if len(texto) <= CHUNK_MAX:
        return [bloco]

    # Primeiro, tenta separar por sub-headers internos (nivel > self)
    partes: list[str] = []
    atual: list[str] = []
    for linha in texto.splitlines():
        m = _HEADER_RE.match(linha)
        if m and len(m.group(1)) > bloco["nivel"] and atual:
            partes.append("\n".join(atual))
            atual = [linha]
        else:
            atual.append(linha)
    if atual:
        partes.append("\n".join(atual))

    sub_blocos: list[dict] = []
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        if len(parte) <= CHUNK_MAX:
            sub_blocos.append({**bloco, "conteudo": parte})
        else:
            for pedaco in _split_por_paragrafo(parte, CHUNK_ALVO):
                sub_blocos.append({**bloco, "conteudo": pedaco})
    return sub_blocos


# ---------------------------------------------------------------------------
# Merge de blocos pequenos — preservando headers intermediários
# ---------------------------------------------------------------------------

def _fundir_blocos(a: dict, b: dict) -> dict:
    """
    Funde dois blocos em um. O conteúdo do `b` é prefixado com o header do `b`
    (no nível dele) — essa é a correção do bug anterior onde headers do segundo
    bloco eram perdidos na fusão.

    Os metadados do resultante ficam com o ancestral comum mais profundo:
    - h1 sempre igual (verificado antes de chamar)
    - h2..h4 viram o do `a` (primeiro bloco), que é o ancestral mais amplo
    """
    header_b_md = _header_md(b["nivel"], b["header"]) if b["header"] else ""
    conteudo_b  = b["conteudo"]
    pedaco_b = (header_b_md + "\n\n" + conteudo_b).strip() if header_b_md else conteudo_b
    conteudo_novo = (a["conteudo"] + "\n\n" + pedaco_b).strip()
    return {**a, "conteudo": conteudo_novo}


def _fundir_pequenos(blocos: list[dict]) -> list[dict]:
    """Funde blocos pequenos consecutivos que compartilhem h1."""
    if not blocos:
        return blocos

    # Loop progressivo: enquanto houver pequenos que couberem no vizinho, funde.
    mudou = True
    while mudou:
        mudou = False
        out: list[dict] = []
        i = 0
        while i < len(blocos):
            atual = blocos[i]
            if len(atual["conteudo"]) >= CHUNK_MIN:
                out.append(atual); i += 1; continue

            # Tentar fundir com próximo
            if (i + 1 < len(blocos)
                    and blocos[i + 1]["h1"] == atual["h1"]
                    and len(atual["conteudo"]) + len(blocos[i + 1]["conteudo"]) + 200 <= CHUNK_MAX):
                out.append(_fundir_blocos(atual, blocos[i + 1]))
                i += 2
                mudou = True
                continue

            # Tentar fundir com anterior já em `out`
            if out and out[-1]["h1"] == atual["h1"] \
                    and len(out[-1]["conteudo"]) + len(atual["conteudo"]) + 200 <= CHUNK_MAX:
                out[-1] = _fundir_blocos(out[-1], atual)
                i += 1
                mudou = True
                continue

            # Last resort: mantém pequeno
            out.append(atual); i += 1

        blocos = out

    return blocos


# ---------------------------------------------------------------------------
# Cap_0: texto corrido
# ---------------------------------------------------------------------------

def _chunks_cap0(texto: str) -> list[dict]:
    pedacos = _split_por_paragrafo(texto, CHUNK_ALVO)
    return [
        {"nivel": 0, "header": "", "h1": None, "h2": None, "h3": None, "h4": None,
         "conteudo": p}
        for p in pedacos
    ]


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def chunk_capitulo(
    md_text: str,
    *,
    edital_id: int,
    orgao: str,
    arquivo_origem: str,
    numero_edital: str,
    cap_num: int,
    cap_titulo: str,
    pagina_inicio: int,
    pagina_fim: int,
) -> list[dict]:
    """
    Chunka o markdown de um capítulo. Retorna list[dict] com:
        {"texto": str (MD válido), "metadata": dict}
    """
    tipo = _tipo_capitulo(cap_num, cap_titulo)

    if cap_num == 0:
        blocos = _chunks_cap0(md_text)
    else:
        blocos = _parse_blocos(md_text)
        blocos = _descartar_headers_orfaos(blocos)
        blocos = [b for b in blocos if b["conteudo"].strip()]

        grandes_resolvidos: list[dict] = []
        for b in blocos:
            grandes_resolvidos.extend(_quebrar_bloco_grande(b))
        blocos = grandes_resolvidos

        blocos = _fundir_pequenos(blocos)

    chunks: list[dict] = []
    for idx, b in enumerate(blocos):
        texto = _bloco_para_md(b)

        numero_secao = None
        for h in (b.get("h4"), b.get("h3"), b.get("h2"), b.get("h1")):
            if h:
                numero_secao = _extrair_numero_secao(h)
                if numero_secao:
                    break

        metadata = {
            "edital_id":      edital_id,
            "orgao":          orgao,
            "numero_edital":  numero_edital or "",
            "arquivo_origem": arquivo_origem,
            "cap_num":        cap_num,
            "cap_titulo":     cap_titulo or "",
            "tipo":           tipo,
            "h1":             b.get("h1") or "",
            "h2":             b.get("h2") or "",
            "h3":             b.get("h3") or "",
            "h4":             b.get("h4") or "",
            "numero_secao":   numero_secao or "",
            "pagina_inicio":  int(pagina_inicio),
            "pagina_fim":     int(pagina_fim),
            "chunk_index":    idx,
        }
        chunks.append({"texto": texto, "metadata": metadata})

    return chunks


def chunk_edital(
    capitulos: Iterable[dict],
    *,
    edital_id: int,
    orgao: str,
    arquivo_origem: str,
    numero_edital: str,
) -> list[dict]:
    todos: list[dict] = []
    for cap in capitulos:
        md_path = Path(cap["cap_path"]).with_suffix(".md")
        if not md_path.exists():
            continue
        texto_md = md_path.read_text(encoding="utf-8")
        todos.extend(chunk_capitulo(
            texto_md,
            edital_id=edital_id,
            orgao=orgao,
            arquivo_origem=arquivo_origem,
            numero_edital=numero_edital,
            cap_num=cap["chapter_num"],
            cap_titulo=cap["title"],
            pagina_inicio=cap["start_page"],
            pagina_fim=cap["end_page"],
        ))
    return todos
