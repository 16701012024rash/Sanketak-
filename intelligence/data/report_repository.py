import json
from pathlib import Path


def load_historical_reports():
    file_path = Path(__file__).parent / "historical_reports.json"

    with open(file_path, "r") as file:
        return json.load(file)