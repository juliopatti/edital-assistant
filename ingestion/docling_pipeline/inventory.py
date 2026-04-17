from pathlib import Path
import json
import re


HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def detect_block_type(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "empty"

    pipe_lines = sum("|" in ln for ln in lines)
    if len(lines) >= 2 and pipe_lines / len(lines) >= 0.6:
        return "table"

    bullet_like = 0
    for ln in lines[: min(len(lines), 8)]:
        if ln.startswith(("-", "*", "+")) or re.match(r"^\d+[\.\)]\s+", ln):
            bullet_like += 1
    if bullet_like >= max(2, min(len(lines), 8) // 2):
        return "list"

    return "text"


def inventory_docling_markdown(md_text: str, source_pdf: str | None = None) -> list[dict]:
    lines = md_text.splitlines()

    items = []
    current_header = None
    current_content = []
    seq = 0

    def flush():
        nonlocal seq, current_content, current_header
        content = "\n".join(current_content).strip()

        if current_header is None and not content:
            current_content = []
            return

        items.append(
            {
                "item_id": f"item_{seq}",
                "source_pdf": source_pdf,
                "header_markdown_level": current_header["level"] if current_header else None,
                "header_text": current_header["text"] if current_header else None,
                "block_type": detect_block_type(content),
                "content_preview": content[:500],
                "raw_text": content,
            }
        )
        seq += 1
        current_content = []

    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            flush()
            current_header = {
                "level": len(m.group(1)),
                "text": m.group(2).strip(),
            }
        else:
            current_content.append(line)

    flush()
    return items


def build_inventory_from_markdown_file(md_path: str | Path, output_path: str | Path) -> str:
    md_path = Path(md_path)
    output_path = Path(output_path)

    md_text = md_path.read_text(encoding="utf-8")
    items = inventory_docling_markdown(md_text, source_pdf=md_path.stem)

    output_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(output_path)


if __name__ == "__main__":
    md_path = Path("out_test_docling/20240812EditalRetificadoFINALBNDES12agostoBNDES.md")
    output_path = Path("out_test_docling/docling_inventory.json")
    result = build_inventory_from_markdown_file(md_path, output_path)
    print(result)