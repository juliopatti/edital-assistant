from pathlib import Path
import json

from docling.document_converter import DocumentConverter


def convert_pdf_with_docling(pdf_path: str | Path, output_dir: str | Path) -> dict:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    markdown = doc.export_to_markdown()
    markdown_path = output_dir / f"{pdf_path.stem}.md"
    markdown_path.write_text(markdown, encoding="utf-8")

    json_path = output_dir / f"{pdf_path.stem}.json"
    json_data = None

    export_methods = ["export_to_dict", "model_dump", "dict"]
    for method_name in export_methods:
        method = getattr(doc, method_name, None)
        if callable(method):
            try:
                json_data = method()
                break
            except Exception:
                pass

    if json_data is not None:
        json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        json_path = None

    return {
        "pdf_path": str(pdf_path),
        "output_dir": str(output_dir),
        "markdown_path": str(markdown_path),
        "json_path": str(json_path) if json_path else None,
    }


if __name__ == "__main__":
    pdf_path = "/home/julio/Documentos/tcc_GENAI/demo0/edital-assistant/data/editais/20240812EditalRetificadoFINALBNDES12agostoBNDES.pdf"
    output_dir = "out_test_docling"
    result = convert_pdf_with_docling(pdf_path, output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))