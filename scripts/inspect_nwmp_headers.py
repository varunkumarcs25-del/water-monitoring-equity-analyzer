import pandas as pd
from pathlib import Path

files = [
    "nwmp_major_2019.xlsx",
    "nwmp_major_2022.xlsx",
    "nwmp_major_2024.xlsx",
    "nwmp_medium_2019.xlsx",
    "nwmp_medium_2022.xlsx",
    "nwmp_medium_2024.xlsx"
]

folder = Path("datasets/raw")

for filename in files:
    print("\n" + "=" * 90)
    print("FILE:", filename)
    print("=" * 90)

    excel = pd.ExcelFile(folder / filename)

    for sheet in excel.sheet_names[:3]:
        df = pd.read_excel(
            folder / filename,
            sheet_name=sheet,
            header=None,
            nrows=5
        )

        print(f"\nSHEET: {sheet}")
        print(df.to_string(index=False, header=False))