import pandas as pd
from pathlib import Path

folder = Path("datasets/raw")
output = Path("reports/nwmp_all_sheets_preview.txt")

files = [
    "nwmp_major_2019.xlsx",
    "nwmp_major_2022.xlsx",
    "nwmp_major_2024.xlsx",
    "nwmp_medium_2019.xlsx",
    "nwmp_medium_2022.xlsx",
    "nwmp_medium_2024.xlsx"
]

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
                nrows=6
            )

            f.write(f"\nSHEET: {sheet} | Shape: {df.shape}\n")
            f.write(df.to_string(index=False, header=False))
            f.write("\n")

print("Audit completed!")
print(f"Saved to: {output}")