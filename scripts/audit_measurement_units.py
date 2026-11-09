import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
import re

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets" / "raw"
OUTPUT = ROOT / "reports" / "measurement_unit_audit.csv"

files = [
    "nwmp_major_2019.xlsx",
    "nwmp_major_2022.xlsx",
    "nwmp_major_2024.xlsx",
    "nwmp_medium_2019.xlsx",
    "nwmp_medium_2022.xlsx",
    "nwmp_medium_2024.xlsx"
]

keywords = re.compile(
    r"temperature|temp|dissolved oxygen|oxygen|conductivity|"
    r"\bec\b|\bph\b|\bbod\b|nitrate|coliform|streptococci|"
    r"mg/?l|µs|us/cm|mpn|cfu|degree|°c",
    re.IGNORECASE
)

results = []

for filename in files:
    path = RAW / filename

    print("Inspecting:", filename)

    wb = load_workbook(path, read_only=True, data_only=True)

    for ws in wb.worksheets:

        for row_number, row in enumerate(
            ws.iter_rows(min_row=1, max_row=20, values_only=True),
            start=1
        ):

            values = [
                f"{i+1}: {str(v).strip()}"
                for i, v in enumerate(row)
                if v is not None and str(v).strip()
            ]

            if not values:
                continue

            combined = " | ".join(values)

            if keywords.search(combined):
                results.append({
                    "source_file": filename,
                    "sheet": ws.title,
                    "excel_row": row_number,
                    "header_evidence": combined
                })

    wb.close()

pd.DataFrame(results).to_csv(OUTPUT, index=False)

print("\nUNIT AUDIT COMPLETE")
print("Header rows identified:", len(results))
print("Saved:", OUTPUT)