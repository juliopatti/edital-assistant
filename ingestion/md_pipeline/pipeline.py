"""
Orquestrador top-level do md_pipeline: executa as 4 fases para UM edital.

Idempotente: se os artefatos já existem no disco (_toc.txt + todos os cap_*.pdf
+ todos os cap_*.md), pula a geração e apenas devolve os metadados dos capítulos
reconstituídos a partir do TOC. Isso evita regenerar o corpus já validado e
comitado, e evita gasto de API em reingestões.

Uso:
    from ingestion.md_pipeline.pipeline import gerar_md_edital
    info = gerar_md_edital("data/editais/edital-cvm.pdf")

Fases:
    1. TOC        — toc_extractor.get_toc_md + salvar_toc_md
    2. Split      — pdf_splitter.split_edital
    3. Markdowns  — md_extractor.processar_edital
    4. Hierarquia — md_postprocess.atualizar_mds
"""

from pathlib import Path

from config import settings

from ingestion.md_pipeline.toc_extractor import get_toc_md, salvar_toc_md
from ingestion.md_pipeline.pdf_splitter import split_edital, parse_toc_level1
from ingestion.md_pipeline.md_extractor import processar_edital
from ingestion.md_pipeline.md_postprocess import atualizar_mds
from ingestion.md_pipeline.config import (
    PROVIDER_TOC,
    MODELO_TOC,
    PROVIDER_MD,
    MODELO_MD,
)


def _reconstituir_capitulos(
    toc_path: Path,
    splits_dir: Path,
) -> list[dict]:
    """
    Reconstrói a lista de capítulos quando os artefatos já existem.
    Mesmo formato que pdf_splitter.split_edital retorna.
    """
    chapters = parse_toc_level1(toc_path)
    rows: list[dict] = []

    first_start = chapters[0]["start_page"]
    rows.append({
        "chapter_num": 0,
        "title":       "(conteúdo antes do primeiro capítulo)",
        "start_page":  1,
        "end_page":    first_start,
        "cap_path":    str(splits_dir / "cap_0.pdf"),
    })
    for idx, chap in enumerate(chapters, start=1):
        rows.append({
            "chapter_num": idx,
            "title":       chap["title"],
            "start_page":  chap["start_page"],
            "end_page":    chap["end_page"],
            "cap_path":    str(splits_dir / f"cap_{idx}.pdf"),
        })
    return rows


def _artefatos_completos(toc_path: Path, splits_dir: Path) -> tuple[bool, list[dict]]:
    """
    Retorna (ok, capitulos): se ok=True, todos os artefatos já existem e capítulos
    foram reconstituídos. Se ok=False, algo falta e o pipeline deve rodar.
    """
    if not toc_path.exists() or not splits_dir.exists():
        return False, []

    capitulos = _reconstituir_capitulos(toc_path, splits_dir)
    for cap in capitulos:
        pdf_p = Path(cap["cap_path"])
        md_p  = pdf_p.with_suffix(".md")
        if not pdf_p.exists() or not md_p.exists():
            return False, capitulos
    return True, capitulos


def gerar_md_edital(pdf_path: str | Path) -> dict:
    """
    Executa o pipeline completo de MD para UM edital (idempotente).

    Retorna:
        toc_path:    caminho do {stem}_toc.txt
        splits_dir:  data/editais/splits/{stem}/
        n_capitulos: número de capítulos (inclui cap_0)
        capitulos:   list[dict] com chapter_num, title, start_page, end_page, cap_path
        ja_existia:  True se todos os artefatos já existiam e nada foi regenerado
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    toc_path   = pdf_path.with_name(f"{pdf_path.stem}_toc.txt")
    splits_dir = settings.editais_dir / "splits" / pdf_path.stem

    # --- Short-circuit: artefatos completos ---------------------------------
    ok, capitulos_existentes = _artefatos_completos(toc_path, splits_dir)
    if ok:
        print(f"[md_pipeline] Artefatos já presentes para {pdf_path.name} — "
              f"pulando regeneração ({len(capitulos_existentes)} capítulos).")
        return {
            "toc_path":    str(toc_path),
            "splits_dir":  str(splits_dir),
            "n_capitulos": len(capitulos_existentes),
            "capitulos":   capitulos_existentes,
            "ja_existia":  True,
        }

    # --- Fase 1: TOC --------------------------------------------------------
    if toc_path.exists():
        print(f"[md_pipeline] 1/4 TOC já existe ({toc_path.name}) — reaproveitando.")
    else:
        print(f"[md_pipeline] 1/4 Extraindo TOC de {pdf_path.name} "
              f"({PROVIDER_TOC}/{MODELO_TOC})...")
        toc_md = get_toc_md(str(pdf_path), provider=PROVIDER_TOC, modelo=MODELO_TOC)
        toc_path = salvar_toc_md(str(pdf_path), toc_md)
        print(f"[md_pipeline]     TOC salvo em {toc_path.name}")

    # --- Fase 2: split ------------------------------------------------------
    # Sempre recria os PDFs dos caps (baratos, determinísticos, usam o TOC atual)
    print(f"[md_pipeline] 2/4 Split em capítulos de nível 1...")
    capitulos = split_edital(pdf_path, toc_path, splits_dir)
    print(f"[md_pipeline]     {len(capitulos)} capítulos gerados em {splits_dir}")

    # --- Fase 3: PDF capítulo -> markdown (pula os .md que já existem) ------
    caps_a_processar: list[dict] = []
    for cap in capitulos:
        md_path = Path(cap["cap_path"]).with_suffix(".md")
        if md_path.exists():
            print(f"[md_pipeline]     cap_{cap['chapter_num']}.md já existe — mantendo.")
        else:
            caps_a_processar.append(cap)

    if caps_a_processar:
        print(f"[md_pipeline] 3/4 Extraindo markdown de {len(caps_a_processar)} "
              f"capítulo(s) ({PROVIDER_MD}/{MODELO_MD})...")
        processar_edital(caps_a_processar, provider=PROVIDER_MD, modelo=MODELO_MD)
    else:
        print(f"[md_pipeline] 3/4 Todos os .md já existem — pulando extração.")

    # --- Fase 4: pós-processamento da hierarquia markdown -------------------
    # Só aplica nos caps recém-gerados (os preexistentes já passaram por isso)
    if caps_a_processar:
        print(f"[md_pipeline] 4/4 Aplicando hierarquia markdown nos novos...")
        atualizar_mds(caps_a_processar)
    else:
        print(f"[md_pipeline] 4/4 Nada a pós-processar.")

    print(f"[md_pipeline] Concluído: {pdf_path.name}")
    return {
        "toc_path":    str(toc_path),
        "splits_dir":  str(splits_dir),
        "n_capitulos": len(capitulos),
        "capitulos":   capitulos,
        "ja_existia":  False,
    }
