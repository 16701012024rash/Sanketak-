# psycopg and sentence_transformers are imported lazily, inside the function
# that needs them. At module scope they made the whole package unimportable
# without a database driver and a downloaded model — so barrier drift, emerging
# risk and the API seam, none of which touch Postgres, could not run or be
# tested either. Loading the embedding model at import cost several seconds on
# every `import intelligence` as well.
_model = None


def _get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def _text(value):
    """Coerce one field to a joinable string.

    `.get(field, "")` returns the default only when the key is MISSING. A
    fingerprint carries the key with a null value — "the narrative did not say"
    — so the default never fires and None reaches the join. Roughly a quarter
    of real extractions have a null activity, and every one of them crashed
    here with "sequence item 0: expected str instance, NoneType found".
    """
    return str(value) if value is not None else ""


def report_to_text(report):
    text = []

    text.append(_text(report.get("activity")))
    text.append(_text(report.get("hazard")))

    text.extend(_text(rule) for rule in report.get("life_saving_rules") or [])

    for failure in report.get("barrier_failures") or []:
        text.append(_text(failure.get("barrier")))
        text.append(_text(failure.get("failure_mode")))

    return " ".join(text)


def vector_search(new_report, top_k=3):

    import psycopg

    text = report_to_text(new_report)

    embedding = _get_model().encode(text).tolist()

    conn = psycopg.connect(
        "dbname=sanketak user=postgres password=YOUR_PASSWARD host=localhost"
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT
                report_id,
                1 - (embedding <=> %s::vector) AS similarity
            FROM reports
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, embedding, top_k)
        )

        rows = cur.fetchall()

    conn.close()

    results = []

    for report_id, similarity in rows:
        results.append({
            "report_id": report_id,
            "similarity": round(float(similarity), 3)
        })

    return results