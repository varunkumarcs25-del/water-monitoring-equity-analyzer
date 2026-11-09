import pandas as pd
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
OUTPUT_DIR = BASE_DIR / "datasets" / "cleaned"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

all_records = []
summary = []

def clean(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def is_station_code(value):
    value = clean(value)
    return bool(re.fullmatch(r"\d+(?:\.0)?", value))

print("\n========== IMPROVED NWMP EXTRACTION ==========\n")

for file in sorted(RAW_DIR.glob("nwmp_*.xlsx")):

    year_match = re.search(r"2019|2022|2024", file.name)
    year = year_match.group() if year_match else "Unknown"
    category = "major" if "major" in file.name.lower() else "medium"

    print("Processing:", file.name)

    workbook = pd.ExcelFile(file)
    file_count = 0

    for sheet in workbook.sheet_names:

        df = pd.read_excel(file, sheet_name=sheet, header=None, dtype=object)

        if df.empty:
            continue

        # Locate the header row, allowing split words such as Statio n Code
        header_row = None

        for i in range(min(12, len(df))):
            row_text = " ".join(clean(v).lower() for v in df.iloc[i])
            compact = re.sub(r"[^a-z]", "", row_text)

            if (
                ("stationcode" in compact or "stncode" in compact)
                and ("location" in compact or "name" in compact)
            ):
                header_row = i
                break

        # Most NWMP sheets use the first three columns for code,
        # location and state. Medium 2024 has River as an extra column.
        if category == "medium" and year == "2024":
            code_col, location_col, river_col, state_col = 0, 1, 2, 3
            parameter_start = 4
        else:
            code_col, location_col, state_col = 0, 1, 2
            river_col = None
            parameter_start = 3

        # Start after header rows when present.
        # For sheets without headers, inspect all rows.
        start_row = header_row + 1 if header_row is not None else 0

        for row_index in range(start_row, len(df)):

            row = df.iloc[row_index]

            if len(row) <= state_col:
                continue

            station_code = clean(row.iloc[code_col])

            if not is_station_code(station_code):
                continue

            location = clean(row.iloc[location_col])
            state = clean(row.iloc[state_col])

            if not location or not state:
                continue

            record = {
                "year": year,
                "category": category,
                "source_file": file.name,
                "source_sheet": sheet,
                "station_code": station_code.replace(".0", ""),
                "location": location,
                "river": clean(row.iloc[river_col]) if river_col is not None else "",
                "state": state
            }

            for col in range(parameter_start, len(row)):
                record[f"raw_col_{col}"] = row.iloc[col]

            all_records.append(record)
            file_count += 1

    summary.append({
        "file": file.name,
        "year": year,
        "category": category,
        "records_extracted": file_count
    })

    print("Records extracted:", file_count)

if all_records:

    master = pd.DataFrame(all_records)

    master.to_csv(
        OUTPUT_DIR / "nwmp_master_raw.csv",
        index=False
    )

    pd.DataFrame(summary).to_csv(
        OUTPUT_DIR / "nwmp_extraction_summary_v2.csv",
        index=False
    )

    print("\n========== EXTRACTION COMPLETED ==========")
    print("Total records:", len(master))
    print(master.groupby(["year", "category"]).size())

else:
    print("No records extracted!")

print("\n==========================================")