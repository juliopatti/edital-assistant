from pathlib import Path
import json

IN_PATH = Path("out_test_docling/docling_json_inventory.json")
OUT_PATH = Path("out_test_docling/docling_index.json")


def is_header(item: dict) -> bool:
    return item.get("kind") == "text" and item.get("label") == "section_header"


def is_content(item: dict) -> bool:
    if item.get("kind") == "table":
        return True
    if item.get("kind") == "text" and item.get("label") != "section_header":
        return bool((item.get("text") or "").strip())
    return False


def build_index(items: list[dict]) -> list[dict]:
    index = []
    current_page = None
    current_section = None
    recent_headers = []

    for item in items:
        page_no = item.get("page_no")

        if page_no != current_page:
            current_page = page_no
            recent_headers = []

        if is_header(item):
            header_text = (item.get("text") or "").strip()
            if header_text:
                current_section = header_text
                recent_headers.append(header_text)
                recent_headers = recent_headers[-3:]
            continue

        if is_content(item):
            text = (item.get("text") or "").strip()
            if not text:
                continue

            index.append(
                {
                    "item_id": item["item_id"],
                    "kind": item["kind"],
                    "label": item.get("label"),
                    "page_no": item.get("page_no"),
                    "bbox": item.get("bbox"),
                    "self_ref": item.get("self_ref"),
                    "parent_ref": item.get("parent_ref"),
                    "current_section": current_section,
                    "recent_headers": recent_headers[:],
                    "text": text,
                }
            )

    return index


def main():
    with open(IN_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    index = build_index(items)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Índice salvo em: {OUT_PATH}")
    print(f"Total de entradas: {len(index)}")

    print("\nPrimeiras 10 entradas:")
    for item in index[:10]:
        print("-" * 80)
        print("item_id:", item["item_id"])
        print("kind:", item["kind"])
        print("page_no:", item["page_no"])
        print("current_section:", item["current_section"])
        print("recent_headers:", item["recent_headers"])
        print("preview:", item["text"][:250].replace("\n", " "))


if __name__ == "__main__":
    main()