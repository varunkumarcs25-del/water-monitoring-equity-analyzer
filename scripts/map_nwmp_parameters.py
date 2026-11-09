
import pandas as pd
from pathlib import Path
import re

RAW = Path("datasets/raw")
CLEANED = Path("datasets/cleaned")
REPORTS = Path("reports")

CLEANED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

FILES = {
    "nwmp_major_2019.xlsx": (2019, "major"),
    "nwmp_major_2022.xlsx": (2022, "major"),
    "nwmp_major_2024.xlsx": (2024, "major"),
    "nwmp_medium_2019.xlsx": (2019, "medium"),
    "nwmp_medium_2022.xlsx": (2022, "medium"),
    "nwmp_medium_2024.xlsx": (2024, "medium"),
}

PARAMETERS = [
    "temperature", "dissolved_oxygen", "ph", "conductivity",
    "bod", "nitrate", "fecal_coliform", "total_coliform",
    "fecal_streptococci"
]

STANDARD = [(3 + i * 2, 4 + i * 2) for i in range(9)]


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def extract_state(row, preferred_col):
    """
    Read State directly from its mapped source column.
    Preserve original State names, including '&' and line breaks.
    """

    value = (
        row.iloc[preferred_col]
        if preferred_col < len(row)
        else None
    )

    if pd.isna(value):
        return None

    text = re.sub(r"\s+", " ", str(value)).strip().upper()

    if not text or re.fullmatch(r"[\d.]+", text):
        return None

    return text


def find_header(df):
    for i in range(min(10, len(df))):
        row = "".join(normalize(v) for v in df.iloc[i].dropna())

        if "stationcode" in row or "stncode" in row:
            return i

    return None


def find_data_start(df, header):
    for r in range(header + 1, min(header + 7, len(df))):
        values = [normalize(v) for v in df.iloc[r].dropna()]

        if values.count("min") >= 5 and values.count("max") >= 5:
            return r + 1

    return header + 2


def get_layout(filename, sheet, df, header):

    layout = {
        "station": 0,
        "location": 1,
        "river": None,
        "state": 2,
        "pairs": dict(zip(PARAMETERS, STANDARD)),
    }

    # MEDIUM 2019
    if filename == "nwmp_medium_2019.xlsx":
        layout["pairs"] = dict(zip(PARAMETERS[:8], [
            (3, 4), (5, 6), (7, 8), (9, 10),
            (11, 12), (13, 14), (15, 16), (17, 18)
        ]))
        return layout

    # MEDIUM 2022
    if filename == "nwmp_medium_2022.xlsx":
        layout["pairs"] = dict(zip(PARAMETERS, STANDARD))
        return layout

    # MEDIUM 2024
    if filename == "nwmp_medium_2024.xlsx":
        layout["river"] = 2
        layout["state"] = 3

        layout["pairs"] = dict(zip(PARAMETERS, [
            (4, 5), (6, 7), (8, 9), (10, 11),
            (12, 13), (14, 15), (16, 17),
            (18, 19), (20, 21)
        ]))
        return layout

    # MAJOR 2019
    if filename == "nwmp_major_2019.xlsx":

        if sheet == "Table 20":
            layout["state"] = 3

            layout["pairs"] = dict(zip(PARAMETERS, [
                (6, 8), (10, 11), (13, 15),
                (16, 18), (20, 22), (23, 25),
                (26, 27), (29, 30), (32, 34)
            ]))

        elif sheet == "Table 21":
            layout["pairs"] = dict(zip(PARAMETERS, [
                (3, 4), (6, 7), (9, 10),
                (12, 13), (15, 16), (18, 19),
                (21, 22), (23, 24), (25, 27)
            ]))

        return layout

    # MAJOR 2022
    if filename == "nwmp_major_2022.xlsx":

        if sheet == "Table 21":
            layout["state"] = 3

            pairs = [
                (5, 7), (9, 11), (13, 15),
                (17, 19), (21, 23), (25, 27),
                (29, 31), (33, 35), (36, 37)
            ]

            layout["pairs"] = dict(zip(PARAMETERS, pairs))

        elif sheet in [
            "Table 32", "Table 33", "Table 34", "Table 40"
        ]:
            layout["state"] = 2

            pairs = [
                (4, 6), (8, 10), (12, 14),
                (16, 18), (20, 22), (24, 26),
                (28, 30), (32, 34), (36, 38)
            ]

            if sheet in ["Table 33", "Table 40"]:
                pairs[-1] = (36, 37)

            layout["pairs"] = dict(zip(PARAMETERS, pairs))

        elif sheet == "Table 37":
            layout["state"] = 2

            pairs = [
                (4, 6), (8, 10), (12, 14),
                (15, 16), (18, 20), (22, 24),
                (26, 28), (30, 32), (34, 36)
            ]

            layout["pairs"] = dict(zip(PARAMETERS, pairs))

        elif sheet == "Table 41":
            layout["state"] = 2

            pairs = [
                (3, 4), (5, 7), (9, 11),
                (13, 15), (17, 18), (20, 22),
                (24, 26), (28, 30), (32, 34)
            ]

            layout["pairs"] = dict(zip(PARAMETERS, pairs))

        return layout

    # MAJOR 2024
    # Table 28 has no header but uses standard column positions.
    return layout


def is_station_code(value):
    if pd.isna(value):
        return False

    return bool(
        re.fullmatch(r"\d+(?:\.0)?", str(value).strip())
    )


def get_cell(row, col):
    if col is None or col >= len(row):
        return None

    return row.iloc[col]


records = []
issues = []

for filename, (year, category) in FILES.items():

    path = RAW / filename
    print(f"\nProcessing {filename}")

    excel = pd.ExcelFile(path)

    for sheet in excel.sheet_names:

        if filename == "nwmp_major_2022.xlsx" and sheet == "Table 1":
            continue

        df = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            dtype=object
        )

        if filename == "nwmp_major_2024.xlsx" and sheet == "Table 28":
            header = None
            data_start = 1

        else:
            header = find_header(df)

            if header is None:
                issues.append({
                    "file": filename,
                    "sheet": sheet,
                    "issue": "Header not detected"
                })
                continue

            data_start = find_data_start(df, header)

        layout = get_layout(filename, sheet, df, header)

        sheet_count = 0

        for row_index in range(data_start, len(df)):

            row = df.iloc[row_index]
            station = get_cell(row, layout["station"])

            if not is_station_code(station):
                continue

            record = {
                "year": year,
                "category": category,
                "source_file": filename,
                "source_sheet": sheet,
                "source_row": row_index,
                "station_code": str(station).replace(".0", ""),
                "location": get_cell(row, layout["location"]),
                "state": extract_state(row, layout["state"]),
                "river": get_cell(row, layout["river"]),
            }

            for parameter, (min_col, max_col) in layout["pairs"].items():
                record[f"{parameter}_min"] = get_cell(row, min_col)
                record[f"{parameter}_max"] = get_cell(row, max_col)

            records.append(record)
            sheet_count += 1

        print(f"  {sheet}: {sheet_count} records")


# CREATE MASTER DATASET
result = pd.DataFrame(records)

output_file = CLEANED / "nwmp_master_mapped_v2.csv"

result.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)


# SAVE EXTRACTION ISSUES
issues_file = REPORTS / "nwmp_mapping_issues_v2.csv"

pd.DataFrame(issues).to_csv(
    issues_file,
    index=False
)


# FINAL SUMMARY
print("\n========== EXTRACTION COMPLETED ==========")
print("Total records:", len(result))

print("\nRecords by year/category:")
print(result.groupby(["year", "category"]).size())

print("\nMissing State values:", result["state"].isna().sum())

print("\nOutput:", output_file)
print("Issues:", issues_file)
