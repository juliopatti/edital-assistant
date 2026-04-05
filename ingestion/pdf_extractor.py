"""Extrai texto de PDFs usando pdfplumber."""

import pdfplumber


def extrair_texto_pdf(caminho: str) -> str:
    """Retorna o texto completo do PDF, página a página."""
    partes = []
    with pdfplumber.open(caminho) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            texto = page.extract_text()
            if texto:
                partes.append(f"--- PÁGINA {i} ---\n{texto}")
    return "\n\n".join(partes)