import json
import psycopg
from sentence_transformers import SentenceTransformer


# PostgreSQL connection
conn = psycopg.connect(
    "dbname=sanketak user=postgres password=1234 host=localhost"
)

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


# Load historical JSON
with open("intelligence/data/historical_reports.json", "r") as file:
    reports = json.load(file)


# Insert reports
with conn.cursor() as cur:

    for report in reports:

        text = report_to_text(report)

        embedding = model.encode(text).tolist()

        cur.execute(
            """
            INSERT INTO reports (
                report_id,
                activity,
                hazard,
                exposure,
                potential_consequence,
                life_saving_rules,
                barrier_failures,
                embedding
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (report_id) DO NOTHING
            """,
            (
                report["report_id"],
                report.get("activity"),
                report.get("hazard"),
                report.get("exposure"),
                report.get("potential_consequence"),
                json.dumps(report.get("life_saving_rules", [])),
                json.dumps(report.get("barrier_failures", [])),
                embedding
            )
        )


conn.commit()
conn.close()

print("Historical reports successfully loaded into PostgreSQL!")