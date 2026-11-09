import pandas as pd
import openpyxl
import json
import math
from pathlib import Path

# ==================================================
# PATHS
# ==================================================

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "datasets" / "raw"
REPORTS = BASE / "reports"

ISSUES = REPORTS / "measurement_anomaly_source_review.csv"
OUTPUT = REPORTS / "original_source_anomaly_verification.csv"
SUMMARY = REPORTS / "anomaly_verification_summary.txt"

# ==================================================
# LOAD ANOMALIES
# ==================================================

issues = pd.read_csv(ISSUES, low_memory=False)

print("\n========== SOURCE ANOMALY VERIFICATION ==========")

classification = issues["classification"].fillna("").astype(str)

review = issues[
    classification.isin([
        "Embedded line break",
        "Other text or formatting"
    ]) | classification.eq("")
].copy()

print("Selected anomalies:", len(review))
print("\nCategories:")
print(
    review["classification"]
    .fillna("Potential outlier")
    .value_counts()
    .to_string()
)

# ==================================================
# HELPERS
# ==================================================

def find_source_file(name):
    if pd.isna(name):
        return None

    filename = Path(str(name)).name
    exact = RAW / filename

    if exact.exists():
        return exact

    for path in RAW.iterdir():
        if path.name.lower() == filename.lower():
            return path

    return None


def normalize_code(value):
    if value is None:
        return ""

    text = str(value).strip()

    try:
        number = float(text)
        if number.is_integer():
            return str(int(number))
    except (ValueError, TypeError):
        pass

    return text


def normalize_value(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def values_match(a, b):
    if normalize_value(a) == normalize_value(b):
        return True

    try:
        x = float(str(a).replace(",", "").strip())
        y = float(str(b).replace(",", "").strip())

        return math.isclose(
            x, y,
            rel_tol=1e-9,
            abs_tol=1e-9
        )
    except (ValueError, TypeError):
        return False


# ==================================================
# INSPECT ORIGINAL EXCEL
# ==================================================

results = []
workbook_cache = {}
sheet_cache = {}

for number, (_, issue) in enumerate(review.iterrows(), start=1):

    source_file = issue["source_file"]
    source_sheet = issue["source_sheet"]
    station_code = issue["station_code"]
    original_value = issue["original_value"]

    target_code = normalize_code(station_code)

    result = {
        "anomaly_number": number,
        "station_code": station_code,
        "year": issue["year"],
        "parameter": issue["column"],
        "original_value": original_value,
        "classification": issue.get("classification", ""),
        "source_file": source_file,
        "source_sheet": source_sheet,
        "excel_row": "",
        "station_code_cell": "",
        "matching_value_cells": "",
        "original_excel_values": "",
        "verification_status": ""
    }

    path = find_source_file(source_file)

    if path is None:
        result["verification_status"] = "SOURCE FILE NOT FOUND"
        results.append(result)
        continue

    try:
        path_key = str(path)

        if path_key not in workbook_cache:
            workbook_cache[path_key] = openpyxl.load_workbook(
                path,
                read_only=True,
                data_only=True
            )

        workbook = workbook_cache[path_key]

        actual_sheet = next(
            (
                s for s in workbook.sheetnames
                if s.strip().casefold()
                == str(source_sheet).strip().casefold()
            ),
            None
        )

        if actual_sheet is None:
            result["verification_status"] = "SHEET NOT FOUND"
            results.append(result)
            continue

        cache_key = (path_key, actual_sheet)

        # Build a complete station-code index for this sheet ONCE.
        if cache_key not in sheet_cache:

            sheet = workbook[actual_sheet]
            station_index = {}

            for excel_row in sheet.iter_rows():

                for cell in excel_row[:8]:

                    code = normalize_code(cell.value)

                    if code:
                        station_index.setdefault(
                            code, []
                        ).append({
                            "excel_row": cell.row,
                            "station_code_cell": cell.coordinate,
                            "cells": [
                                {
                                    "coordinate": c.coordinate,
                                    "value": c.value
                                }
                                for c in excel_row
                                if c.value is not None
                            ]
                        })

                        break

            sheet_cache[cache_key] = station_index

        # IMPORTANT: retrieve only the CURRENT station's rows.
        matches = sheet_cache[cache_key].get(target_code, [])

        if not matches:
            result["verification_status"] = "STATION CODE NOT FOUND"
            results.append(result)
            continue

        evidence = []

        for row_match in matches:

            cells = row_match["cells"]

            value_cells = [
                item["coordinate"]
                for item in cells
                if values_match(item["value"], original_value)
            ]

            evidence.append({
                "excel_row": row_match["excel_row"],
                "station_code_cell": row_match["station_code_cell"],
                "matching_value_cells": value_cells,
                "cells": cells
            })

        result["excel_row"] = json.dumps(
            [e["excel_row"] for e in evidence],
            ensure_ascii=False
        )

        result["station_code_cell"] = json.dumps(
            [e["station_code_cell"] for e in evidence],
            ensure_ascii=False
        )

        result["matching_value_cells"] = json.dumps(
            [e["matching_value_cells"] for e in evidence],
            ensure_ascii=False
        )

        result["original_excel_values"] = json.dumps(
            evidence,
            ensure_ascii=False,
            default=str
        )

        if any(e["matching_value_cells"] for e in evidence):
            result["verification_status"] = (
                "STATION FOUND AND VALUE MATCHED"
            )
        else:
            result["verification_status"] = (
                "STATION FOUND - VALUE NOT MATCHED"
            )

    except Exception as error:
        result["verification_status"] = (
            f"INSPECTION ERROR: {error}"
        )

    results.append(result)

    if number % 10 == 0:
        print(f"Inspected {number}/{len(review)} anomalies")


# ==================================================
# SAVE RESULTS
# ==================================================

result_df = pd.DataFrame(results)

result_df.to_csv(OUTPUT, index=False)

# ==================================================
# SUMMARY
# ==================================================

with open(SUMMARY, "w", encoding="utf-8") as file:

    file.write("ORIGINAL SOURCE ANOMALY VERIFICATION\n")
    file.write("=" * 55 + "\n\n")

    file.write(f"Total inspected: {len(review)}\n\n")

    file.write("VERIFICATION RESULTS\n")
    file.write("-" * 55 + "\n")

    file.write(
        result_df["verification_status"]
        .value_counts()
        .to_string()
    )

    file.write("\n\nIMPORTANT NOTES\n")
    file.write("-" * 55 + "\n")

    file.write(
        "Station codes were indexed individually.\n"
        "Each anomaly was matched against its own station code.\n"
        "Original Excel rows and matching cell coordinates are recorded.\n"
        "No measurements were automatically corrected.\n"
        "Parameter column mapping still requires verification.\n"
        "Original source files remain unchanged.\n"
    )

# ==================================================
# FINAL OUTPUT
# ==================================================

print("\n========== VERIFICATION COMPLETE ==========")

print(
    result_df["verification_status"]
    .value_counts()
    .to_string()
)

print("\nGenerated:")
print(OUTPUT)
print(SUMMARY)

print("\nOriginal datasets remain unchanged.")
print("========== COMPLETE ==========")
