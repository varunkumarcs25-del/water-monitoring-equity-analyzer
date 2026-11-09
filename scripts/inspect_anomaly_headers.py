import pandas as pd
import openpyxl
import json
from pathlib import Path

# ==================================================
# PATHS
# ==================================================

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "datasets" / "raw"
REPORTS = BASE / "reports"

INPUT = REPORTS / "original_source_anomaly_verification.csv"
OUTPUT = REPORTS / "anomaly_header_evidence.csv"
SUMMARY = REPORTS / "anomaly_header_summary.txt"

# ==================================================
# LOAD VERIFICATION REPORT
# ==================================================

df = pd.read_csv(INPUT, low_memory=False)

print("\n========== ANOMALY HEADER INSPECTION ==========")
print("Anomalies loaded:", len(df))

# ==================================================
# HELPERS
# ==================================================

def find_file(name):
    filename = Path(str(name)).name

    exact = RAW / filename
    if exact.exists():
        return exact

    for p in RAW.iterdir():
        if p.name.lower() == filename.lower():
            return p

    return None


def read_row(sheet, row_number):
    return [
        {
            "cell": cell.coordinate,
            "value": cell.value
        }
        for cell in sheet[row_number]
        if cell.value is not None
    ]


# ==================================================
# INSPECT HEADERS AND ORIGINAL CELLS
# ==================================================

workbooks = {}
results = []

for i, record in df.iterrows():

    source_file = record["source_file"]
    source_sheet = record["source_sheet"]

    result = {
        "anomaly_number": record["anomaly_number"],
        "station_code": record["station_code"],
        "year": record["year"],
        "parameter": record["parameter"],
        "original_value": record["original_value"],
        "classification": record["classification"],
        "source_file": source_file,
        "source_sheet": source_sheet,
        "excel_row": record["excel_row"],
        "matching_value_cells": record["matching_value_cells"],
        "header_rows": "",
        "original_row_values": "",
        "previous_row_values": "",
        "next_row_values": "",
        "inspection_status": ""
    }

    path = find_file(source_file)

    if path is None:
        result["inspection_status"] = "SOURCE FILE NOT FOUND"
        results.append(result)
        continue

    try:
        key = str(path)

        if key not in workbooks:
            workbooks[key] = openpyxl.load_workbook(
                path,
                read_only=True,
                data_only=True
            )

        wb = workbooks[key]

        actual_sheet = next(
            (
                s for s in wb.sheetnames
                if s.strip().casefold()
                == str(source_sheet).strip().casefold()
            ),
            None
        )

        if actual_sheet is None:
            result["inspection_status"] = "SHEET NOT FOUND"
            results.append(result)
            continue

        sheet = wb[actual_sheet]

        row_numbers = json.loads(str(record["excel_row"]))

        # Capture the first 10 rows containing headers.
        headers = []

        for r in range(1, min(11, sheet.max_row + 1)):
            headers.append({
                "row": r,
                "values": read_row(sheet, r)
            })

        result["header_rows"] = json.dumps(
            headers, ensure_ascii=False, default=str
        )

        original_rows = []
        previous_rows = []
        next_rows = []

        for row_number in row_numbers:

            row_number = int(row_number)

            original_rows.append({
                "row": row_number,
                "values": read_row(sheet, row_number)
            })

            if row_number > 1:
                previous_rows.append({
                    "row": row_number - 1,
                    "values": read_row(sheet, row_number - 1)
                })

            if row_number < sheet.max_row:
                next_rows.append({
                    "row": row_number + 1,
                    "values": read_row(sheet, row_number + 1)
                })

        result["original_row_values"] = json.dumps(
            original_rows, ensure_ascii=False, default=str
        )

        result["previous_row_values"] = json.dumps(
            previous_rows, ensure_ascii=False, default=str
        )

        result["next_row_values"] = json.dumps(
            next_rows, ensure_ascii=False, default=str
        )

        result["inspection_status"] = "HEADER AND ROW EXTRACTED"

    except Exception as error:
        result["inspection_status"] = str(error)

    results.append(result)

    if (i + 1) % 10 == 0:
        print(f"Inspected {i + 1}/{len(df)} anomalies")

# ==================================================
# SAVE RESULTS
# ==================================================

result_df = pd.DataFrame(results)

result_df.to_csv(OUTPUT, index=False)

with open(SUMMARY, "w", encoding="utf-8") as f:

    f.write("ANOMALY HEADER INSPECTION REPORT\n")
    f.write("=" * 50 + "\n\n")

    f.write(f"Total anomalies: {len(result_df)}\n\n")

    f.write(
        result_df["inspection_status"]
        .value_counts()
        .to_string()
    )

    f.write(
        "\n\nOriginal Excel files were only inspected. "
        "No data was modified.\n"
    )

print("\n========== COMPLETE ==========")
print(result_df["inspection_status"].value_counts().to_string())

print("\nGenerated:")
print(OUTPUT)
print(SUMMARY)

print("\nOriginal datasets remain unchanged.")