from legal_chunk import LegalChunk


def _get_hierarchy_title(
    hierarchy: list,
    level_name: str
):

    for level in hierarchy:

        if level["level"] == level_name:

            return level.get("title")

    return None

def article_to_chunk(
    article,
    *,
    ordinal: int,
    document_id: str,
    document_title: str,
    document_type: str,
    source_level: int,
    country: str,
    status: str,
    version: str | None,
    is_ocr: bool,
):

    chunk = LegalChunk(

        chunk_id=(f"{document_id}:{ordinal:05d}"),

        document_id=document_id,

        ordinal=ordinal,

        content=article.text,

        source_level=source_level,

        country=country,

        document_type=document_type,

        document_title=document_title,

        status=status,

        version=version,

        title=article.article_title,

        chapter=_get_hierarchy_title(
            article.hierarchy,
            "chapitre"
        ),

        section=_get_hierarchy_title(
            article.hierarchy,
            "section"
        ),

        article=article.article_number,

        page_start=article.page_start,

        page_end=article.page_end,

        is_ocr=is_ocr,
    )

    return chunk

def procedure_to_chunk(
    section,
    *,
    ordinal: int,
    document_id: str,
    document_title: str,
    document_type: str,
    source_level: int,
    country: str,
    status: str,
    version: str | None,
    is_ocr: bool = False,
):

    chunk = LegalChunk(

        chunk_id=(f"{document_id}:{ordinal:05d}"),

        document_id=document_id,

        ordinal=ordinal,

        content=section.text,

        source_level=source_level,

        country=country,

        document_type=document_type,

        document_title=document_title,

        status=status,

        version=version,

        title=section.section_title,

        page_start=section.page_start,

        page_end=section.page_end,

        is_ocr=section.needs_human_review,
    )

    return chunk

def build_legal_chunks(
    *,
    articles=None,
    procedure_sections=None,
    metadata=None,
):

    chunks = []

    ordinal = 1

    if articles:

        for article in articles:

            chunks.append(

                article_to_chunk(
                    article,
                    ordinal=ordinal,
                    **metadata
                )

            )

            ordinal += 1

    if procedure_sections:

        for section in procedure_sections:

            chunks.append(

                procedure_to_chunk(
                    section,
                    ordinal=ordinal,
                    **metadata
                )

            )

            ordinal += 1

    return chunks