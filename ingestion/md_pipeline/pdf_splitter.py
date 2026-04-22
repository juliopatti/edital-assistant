"""
Fase 2: split físico do PDF em capítulos de nível 1 usando o TOC.

Lê o {stem}_toc.txt (gerado pela fase 1), filtra apenas linhas de nível 1
(headers markdown `# Título (p. X–Y)`), e grava um PDF por capítulo em
data/editais/splits/{stem}/cap_N.pdf.

O cap_0 cobre páginas 1..start_page_do_cap1 (preâmbulo do edital).
Os demais (cap_1..cap_N) cobrem exatamente start_page..end_page do TOC.

Porta da célula 5 do notebook toc_sonnet.ipynb (sem alterações de comportamento),
mas sem pandas — retorna list[dict] em vez de DataFrame.
"""

import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


# Match só cabeçalhos de nível 1:  # <titulo> (p. <ini>–<fim>)
# `^#\s` garante um único `#` (descarta `##`, `###`, ...). Aceita `–` e `-`.
LEVEL1_RE = re.compile(
    r'^#\s+(?P<title>.+?)\s+\(p\.\s*(?P<start>\d+)\s*[–\-]\s*(?P<end>\d+)\)\s*$'
)


def parse_toc_level1(toc_path: Path) -> list[dict]:
    """Lê o _toc.txt e retorna apenas as entradas de nível 1."""
    chapters = []
    for line in toc_path.read_text(encoding='utf-8').splitlines():
        m = LEVEL1_RE.match(line)
        if m:
            chapters.append({
                'title':      m.group('title').strip(),
                'start_page': int(m.group('start')),
                'end_page':   int(m.group('end')),
            })
    return chapters


def write_pages(reader: PdfReader, start_1b: int, end_1b: int, out_path: Path) -> None:
    """
    Grava um PDF contendo as páginas [start_1b..end_1b] (1-based, ambas inclusivas).
    """
    writer = PdfWriter()
    start_idx = max(0, start_1b - 1)
    end_idx   = min(len(reader.pages), end_1b)   # end_1b inclusivo ↔ range exclusivo
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        writer.write(f)


def split_edital(pdf_path: Path, toc_path: Path, out_dir: Path) -> list[dict]:
    """
    Divide o PDF em cap_0.pdf, cap_1.pdf, ..., cap_N.pdf.

    Retorna list[dict] com chaves:
        chapter_num, title, start_page, end_page, cap_path
    """
    pdf_path = Path(pdf_path)
    toc_path = Path(toc_path)
    out_dir  = Path(out_dir)

    chapters = parse_toc_level1(toc_path)
    if not chapters:
        raise ValueError(
            f"Nenhum capítulo de nível 1 encontrado em {toc_path}. "
            "Verifique se o TOC foi gerado corretamente."
        )

    reader = PdfReader(str(pdf_path))
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    # cap_0: páginas 1 até start_page do primeiro capítulo (inclusivas)
    first_start = chapters[0]['start_page']
    cap0_path = out_dir / 'cap_0.pdf'
    write_pages(reader, 1, first_start, cap0_path)
    rows.append({
        'chapter_num': 0,
        'title':       '(conteúdo antes do primeiro capítulo)',
        'start_page':  1,
        'end_page':    first_start,
        'cap_path':    str(cap0_path),
    })

    # cap_1, cap_2, ...
    for idx, chap in enumerate(chapters, start=1):
        out_path = out_dir / f'cap_{idx}.pdf'
        write_pages(reader, chap['start_page'], chap['end_page'], out_path)
        rows.append({
            'chapter_num': idx,
            'title':       chap['title'],
            'start_page':  chap['start_page'],
            'end_page':    chap['end_page'],
            'cap_path':    str(out_path),
        })

    return rows
