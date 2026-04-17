from pathlib import Path
import json


JSON_PATH = Path("out_test_docling/20240812EditalRetificadoFINALBNDES12agostoBNDES.json")
OUT_PATH = Path("out_test_docling/docling_json_inventory.json")


def extract_page_no(prov):
    if isinstance(prov, list) and prov:
        return prov[0].get("page_no")
    return None


def extract_bbox(prov):
    if isinstance(prov, list) and prov:
        return prov[0].get("bbox")
    return None


def normalize_text_block(item, idx):
    return {
        "item_id": f"text_{idx}",
        "kind": "text",
        "self_ref": item.get("self_ref"),
        "parent_ref": item.get("parent", {}).get("$ref") if isinstance(item.get("parent"), dict) else None,
        "label": item.get("label"),
        "level": item.get("level"),
        "page_no": extract_page_no(item.get("prov")),
        "bbox": extract_bbox(item.get("prov")),
        "text": item.get("text"),
    }


def table_to_text(table):
    data = table.get("data", {})
    grid = data.get("grid", [])

    rows = []
    for row in grid:
        values = []
        for cell in row:
            if isinstance(cell, dict):
                values.append((cell.get("text") or "").strip())
            else:
                values.append("")
        if any(values):
            rows.append(values)

    return "\n".join(" | ".join(row) for row in rows)


def normalize_table_block(item, idx):
    return {
        "item_id": f"table_{idx}",
        "kind": "table",
        "self_ref": item.get("self_ref"),
        "parent_ref": item.get("parent", {}).get("$ref") if isinstance(item.get("parent"), dict) else None,
        "label": item.get("label"),
        "level": None,
        "page_no": extract_page_no(item.get("prov")),
        "bbox": extract_bbox(item.get("prov")),
        "text": table_to_text(item),
    }


def build_inventory(docling_json):
    items = []

    for idx, text_item in enumerate(docling_json.get("texts", [])):
        items.append(normalize_text_block(text_item, idx))

    for idx, table_item in enumerate(docling_json.get("tables", [])):
        items.append(normalize_table_block(table_item, idx))

    def sort_key(x):
        page = x["page_no"] if x["page_no"] is not None else 10**9
        bbox = x.get("bbox") or {}
        top = bbox.get("t", 10**9)
        left = bbox.get("l", 10**9)
        return (page, top, left)

    items.sort(key=sort_key)
    return items


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    inventory = build_inventory(data)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

    print(f"Inventário salvo em: {OUT_PATH}")
    print(f"Total de blocos: {len(inventory)}")

    print("\nPrimeiros 10 blocos:")
    for item in inventory[:10]:
        print("-" * 80)
        print("item_id:", item["item_id"])
        print("kind:", item["kind"])
        print("label:", item["label"])
        print("level:", item["level"])
        print("page_no:", item["page_no"])
        preview = (item["text"] or "")[:250].replace("\n", " ")
        print("preview:", preview)


if __name__ == "__main__":
    main()