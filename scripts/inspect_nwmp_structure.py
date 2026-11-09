import pandas as pd
from pathlib import Path

DATA_DIR = Path("datasets/raw")
OUTPUT_DIR = Path("reports")

files = [
    "nwmp_major_2019.xlsx",
    "nwmp_major_2022.xlsx",
    "nwmp_major_2024.xlsx",
    "nwmp_medium_2019.xlsx",
    "nwmp_medium_2022.xlsx",
    "nwmp_medium_2024.xlsx"
]

output = []

for filename in files:
    filepath = DATA_DIR / filename

    print(f"\n{'='*70}")
    print("FILE:", filename)

    excel = pd.ExcelFile(filepath)

    for sheet in excel.sheet_names:
        df = pd.read_excel(
            filepath,
            sheet_name=sheet,
            header=None
        )

        print(f"\nSHEET: {sheet}")
        print("Shape:", df.shape)
        print("\nFirst 8 rows:")

        preview = df.head(8).to_string(index=False)

        print(preview)

        output.append(
            f"\n\nFILE: {filename}\n"
            f"SHEET: {sheet}\n"
            f"SHAPE: {df.shape}\n"
            f"{preview}\n"
        )

OUTPUT_DIR.mkdir(exist_ok=True)

with open(
    OUTPUT_DIR / "nwmp_detailed_inspection.txt",
    "w",
    encoding="utf-8"
) as f:
    f.writelines(output)

print("\nInspection completed!")