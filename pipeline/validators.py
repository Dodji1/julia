from collections import Counter

def validate_document(pages, articles):
    alerts = []
    if not pages:
        alerts.append("NO_PAGES")
    chars = sum(p.char_count for p in pages)
    if chars < 1000:
        alerts.append("VERY_LOW_EXTRACTED_TEXT")
    low_pages = [p.page_number for p in pages if p.char_count < 30]
    if len(low_pages) > max(3, len(pages)*0.30):
        alerts.append("DOCUMENT_MAY_BE_SCANNED_OR_IMAGE_BASED")

    ocr_pages = [p.page_number for p in pages if p.extraction_method == "ocr"]

    nums = [a.article_number for a in articles if a.article_number.isdigit()]
    duplicates = [n for n,c in Counter(nums).items() if c > 1]
    if duplicates:
        alerts.append(f"DUPLICATE_ARTICLE_NUMBERS:{','.join(duplicates[:20])}")

    return {
        "page_count": len(pages),
        "article_count": len(articles),
        "extracted_characters": chars,
        "ocr_page_count": len(ocr_pages),
        "ocr_pages": ocr_pages,
        "low_text_pages": low_pages[:100],
        "alerts": alerts,
        "status": "OK" if not alerts else "WARNING"
    }
