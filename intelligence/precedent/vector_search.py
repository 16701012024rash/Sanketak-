import psycopg
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")


def report_to_text(report):
    text = []

    text.append(report.get("activity", ""))
    text.append(report.get("hazard", ""))

    text.extend(report.get("life_saving_rules", []))

    for failure in report.get("barrier_failures", []):
        text.append(failure.get("barrier", ""))
        text.append(failure.get("failure_mode", ""))

    return " ".join(text)


def vector_search(new_report, top_k=3):

    text = report_to_text(new_report)

    embedding = model.encode(text).tolist()

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