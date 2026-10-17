from taxonomie_rules import (
    TAG_RULES,
    extract_country,
    extract_document_type,
    extract_version
)


def enrich_chunk(chunk):

    title = (
        chunk.document_title or ""
    )

    search_text = (
        f"{title} "
        f"{chunk.title or ''} "
        f"{chunk.content[:2000]}"
    ).lower()

    tags = []

    for tag, keywords in TAG_RULES.items():

        if any(
            keyword in search_text
            for keyword in keywords
        ):
            tags.append(tag)

    chunk.tags = sorted(
        set(tags)
    )

    if chunk.version is None:
        chunk.version = (
            extract_version(title)
        )

    if chunk.country == "BJ":
        chunk.country = (
            extract_country(title)
        )

    if chunk.document_type == "a_classifier":
        chunk.document_type = (
            extract_document_type(title)
        )

    return chunk


def enrich_chunks(chunks):

    return [
        enrich_chunk(chunk)
        for chunk in chunks
    ]