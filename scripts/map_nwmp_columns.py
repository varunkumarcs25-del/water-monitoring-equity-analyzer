import pandas as pd
from pathlib import Path
import re

folder = Path("datasets/raw")
output = Path("reports/nwmp_column_mapping.txt")

files = [
    "nwmp_major_2019.xlsx",
    "nwmp_major_2022.xlsx",
    "nwmp_major_2024.xlsx",
    "nwmp_medium_2019.xlsx",
    "nwmp_medium_2022.xlsx",
    "nwmp_medium_2024.xlsx"
]

def normalize(value):
    return re.sub(r"[^a-z]", "", str(value).lower())

with open(output, "w", encoding="utf-8") as f:

    for filename in files:
        path = folder / filename

        f.write("\n" + "=" * 100 + "\n")
        f.write(f"FILE: {filename}\n")
        f.write("=" * 100 + "\n")

        excel = pd.ExcelFile(path)

        for sheet in excel.sheet_names:

            df = pd.read_excel(
                path,
                sheet_name=sheet,
                header=None,
                nrows=10
            )

            header_row = None

            for i in range(len(df)):
                row_text = "".join(
                    normalize(x) for x in df.iloc[i].dropna()
                )

                if "stationcode" in row_text or "stncode" in row_text:
                    header_row = i
                    break

            if header_row is None:
                continue

            f.write(f"\nSHEET: {sheet}\n")
            f.write(f"HEADER ROW: {header_row}\n")

            for r in range(header_row, min(header_row + 3, len(df))):
                f.write(f"\nROW {r}:\n")

                for col, value in enumerate(df.iloc[r]):
                    if pd.notna(value):
                        f.write(f"  Column {col}: {value}\n")

            f.write("\n")

print("Column mapping audit completed!")
print(f"Saved to: {output}")