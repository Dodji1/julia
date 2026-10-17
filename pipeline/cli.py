import argparse
from pathlib import Path
from normalizer import slug
from pdf_extractor import extract_pages
from legal_parser import parse_pages
from procedure_parser import parse_procedural_pages
from validators import validate_document
from exporters import dump_json, dump_jsonl, dump_articles_csv
from dataclasses import asdict
from legal_chunk_builder import build_legal_chunks
from taxonomie_enricher import enrich_chunks

from manifest import load_manifest

manifest = load_manifest(
    Path("src/julia_ingestion/data/metadata/corpus_manifest.yaml")
)

manifest_by_filename = {}

for entry in manifest.entries.values():

    pdf_name = Path(
        manifest.file_path(entry)
    ).name.lower()

    manifest_by_filename[
        pdf_name
    ] = entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/input")
    ap.add_argument("--output", default="data/output")
    args = ap.parse_args()

    inp, out = Path(args.input), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(inp.glob("*.pdf"))
    all_docs, all_pages, all_articles, all_hierarchies, reports = [], [], [], {}, []
    all_procedure_sections = []
    all_chunks = []

    print("INPUT =", inp.resolve())
    print("EXISTS =", inp.exists())

    pdfs = sorted(inp.glob("*.pdf"))

    print("PDF FOUND =", len(pdfs))

    for pdf in pdfs:
        entry = manifest_by_filename.get(
            pdf.name.lower()
        )
        if entry is None:
            print(
                f"PDF absent du manifeste : {pdf.name}"
            )
            continue

        document_id = entry.id

        pages = extract_pages(pdf, document_id, use_ocr=True)

        chars = sum(p.char_count for p in pages)
        print(
            f"{pdf.name} | "
            f"pages={len(pages)} | "
            f"chars={chars}"
        )

        articles, hierarchy = parse_pages(
            pages,
            document_id
        )

        procedure_sections = []

        if len(articles) == 0:

            procedure_sections = (
                parse_procedural_pages(
                    pages=pages,
                    document_id=document_id,
                    source_filename=pdf.name
                )
            )

            print(
                f"{pdf.name} -> "
                f"{len(procedure_sections)} sections"
            )
        print(f"articles={len(articles)}")
        report = validate_document(pages, articles)

        metadata = {
            "document_id": entry.id,
            "document_title": entry.title,
            "document_type": entry.document_type,
            "country": entry.country,
            "status": entry.status.value,
            "source_level": entry.source_level,
            "version": entry.version_label,
            "is_ocr": any(
                p.extraction_method == "ocr"
                for p in pages
            )
        }

        chunks = build_legal_chunks(

        articles=articles,

        procedure_sections=procedure_sections,
        metadata=metadata

        )

        chunks = enrich_chunks(chunks)

        all_chunks.extend(chunk.model_dump() for chunk in chunks)


        doc = {
            "document_id": document_id,
            "filename": pdf.name,
            "source_path": str(pdf),
            "page_count": len(pages),
            "article_count": len(articles),
            "extracted_characters": sum(p.char_count for p in pages)
        }
        all_docs.append(doc)
        all_pages.extend(asdict(p) for p in pages)
        all_articles.extend(asdict(a) for a in articles)
        all_procedure_sections.extend(asdict(section) for section in procedure_sections)
        all_hierarchies[document_id] = hierarchy
        reports.append({**{"document_id": document_id, "filename": pdf.name}, **report})

    taxonomy_stats = {}

    for chunk in chunks:

        for tag in chunk.tags:

            taxonomy_stats[tag] = (
                taxonomy_stats.get(tag, 0) + 1
            )

    dump_json(out/"documents.json", all_docs)
    dump_jsonl(out/"pages.jsonl", all_pages)
    dump_jsonl(out/"articles.jsonl", all_articles)
    dump_jsonl(out / "procedure_sections.jsonl", all_procedure_sections)
    dump_json(out/"hierarchy.json", all_hierarchies)
    dump_json(out/"quality_report.json", reports)
    dump_jsonl(out / "legal_chunks.jsonl", all_chunks)
    dump_json(out / "taxonomy_report.json", taxonomy_stats)

    # CSV
    class Obj:
        def __init__(self,d): self.__dict__.update(d)
    dump_articles_csv(out/"articles.csv", [Obj(a) for a in all_articles])

    manifest = {
        "documents": len(all_docs),
        "pdfs_found": len(pdfs),
        "articles": len(all_articles),
        "procedure_sections": len(all_procedure_sections),
        "legal_chunks": len(all_chunks),
        "status": "OK" if all(not r["alerts"] for r in reports) else "WARNING"
    }
    dump_json(out/"manifest.json", manifest)
    print(f"{len(pdfs)} PDF(s) traités — {len(all_articles)} article(s) extrait(s).")
    print(f"Sorties : {out}")

if __name__ == "__main__":
    main()
