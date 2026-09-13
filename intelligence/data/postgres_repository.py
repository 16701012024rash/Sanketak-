import json
import psycopg


def load_historical_reports():

    conn = psycopg.connect(
        "dbname=sanketak user=postgres password=YOUR_PASSWARD host=localhost"
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT
                report_id,
                activity,
                hazard,
                exposure,
                potential_consequence,
                life_saving_rules,
                barrier_failures
            FROM reports
            """
        )

        rows = cur.fetchall()

    conn.close()

    reports = []

    for row in rows:

        reports.append({
            "report_id": row[0],
            "activity": row[1],
            "hazard": row[2],
            "exposure": row[3],
            "potential_consequence": row[4],
            "life_saving_rules": (
                row[5]
                if isinstance(row[5], list)
                else json.loads(row[5])
            ),
            "barrier_failures": (
                row[6]
                if isinstance(row[6], list)
                else json.loads(row[6])
            )
        })

    return reports