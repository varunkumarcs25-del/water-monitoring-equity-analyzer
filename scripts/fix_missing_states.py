import pandas as pd
from openpyxl import load_workbook
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "datasets" / "raw"
INPUT = BASE / "datasets" / "cleaned" / "nwmp_master_mapped_v2.csv"
OUTPUT = BASE / "datasets" / "cleaned" / "nwmp_master_mapped_v4.csv"

df = pd.read_csv(INPUT)

STATE_COLUMNS = {
    ("nwmp_major_2019.xlsx", "Table 20"): 2,
    ("nwmp_major_2022.xlsx", "Table 21"): 2,
    ("nwmp_major_2022.xlsx", "Table 32"): 3,
    ("nwmp_major_2022.xlsx", "Table 33"): 3,
    ("nwmp_major_2022.xlsx", "Table 34"): 3,
    ("nwmp_major_2022.xlsx", "Table 37"): 3,
    ("nwmp_major_2022.xlsx", "Table 40"): 3,
}

def clean_code(value):
    if value is None:
        return ""
    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        return str(value).strip()

missing = df[df["state"].isna()]
fixed = 0

for (filename, sheet), group in missing.groupby(
    ["source_file", "source_sheet"]
):
    workbook = load_workbook(
        RAW / filename, read_only=True, data_only=True
    )
    ws = workbook[sheet]

    state_col = STATE_COLUMNS[(filename, sheet)] + 1

    station_lookup = {}

    for row in ws.iter_rows(min_row=1):
        code = clean_code(row[0].value)
        state = ws.cell(row=row[0].row, column=state_col).value

        if code and state is not None and str(state).strip():
            station_lookup[code] = " ".join(str(state).split()).upper()

    for index, record in group.iterrows():
        code = clean_code(record["station_code"])

        if code in station_lookup:
            df.at[index, "state"] = station_lookup[code]
            fixed += 1

    workbook.close()

df.to_csv(OUTPUT, index=False)

print("\n========== CORRECTION COMPLETE ==========")
print("Original records:", len(df))
print("States recovered:", fixed)
print("Still missing:", df["state"].isna().sum())
print("Output:", OUTPUT)