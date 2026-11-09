import pandas as pd
from openpyxl import load_workbook
from pathlib import Path

base = Path("datasets/raw")
df = pd.read_csv("datasets/cleaned/nwmp_master_mapped_v2.csv")
missing = df[df["state"].isna()]

for (filename, sheet), group in missing.groupby(
    ["source_file", "source_sheet"]
):
    print(f"\n{'='*60}")
    print(filename, "-", sheet)

    wb = load_workbook(base / filename, data_only=True)
    ws = wb[sheet]

    for _, record in group.head(3).iterrows():
        station = str(record["station_code"]).replace(".0", "")
        print(f"\nStation: {station}")

        found = False
        for row in ws.iter_rows():
            values = [cell.value for cell in row]

            if str(values[0]).replace(".0", "").strip() == station:
                print("Excel row:", row[0].row)
                print("First 12 columns:", values[:12])
                found = True
                break

        if not found:
            print("Station not found in first column.")

    wb.close()