import csv, json
from dataclasses import asdict
from pathlib import Path

def dump_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def dump_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def dump_articles_csv(path, articles):
    fields = ["article_id","document_id","article_number","article_title",
              "page_start","page_end","text","hierarchy"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for a in articles:
            d = asdict(a) if hasattr(a, "__dataclass_fields__") else dict(a.__dict__)
            d["hierarchy"] = json.dumps(d["hierarchy"], ensure_ascii=False)
            d.pop("text_lines", None)
            w.writerow({k:d.get(k) for k in fields})
