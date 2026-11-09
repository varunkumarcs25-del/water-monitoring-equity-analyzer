import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "reports/measurement_unit_audit.csv"
OUTPUT = ROOT / "reports/measurement_data_dictionary.csv"

audit = pd.read_csv(INPUT)

dictionary = [
    ["temperature", "°C", "Temperature", "All datasets"],
    ["dissolved_oxygen", "mg/L", "Dissolved Oxygen", "All datasets"],
    ["ph", "Unitless", "pH", "All datasets"],
    ["conductivity", "µS/cm", "Electrical Conductivity", "All datasets"],
    ["bod", "mg/L", "Biochemical Oxygen Demand", "All datasets"],
    ["nitrate", "mg/L", "Nitrate", "Major 2019 and 2022; Major 2024"],
    ["nitrate_n_nitrite_n", "mg/L", "Nitrate-N + Nitrite-N",
     "Medium 2019, 2022 and 2024"],
    ["fecal_coliform", "MPN/100 mL", "Fecal Coliform", "All datasets"],
    ["total_coliform", "MPN/100 mL", "Total Coliform", "All datasets"],
    ["fecal_streptococci", "MPN/100 mL", "Fecal Streptococci",
     "Where reported"]
]

result = pd.DataFrame(
    dictionary,
    columns=[
        "parameter_code",
        "unit",
        "parameter_name",
        "source_scope"
    ]
)

result["source_files_found"] = ""

for index, row in result.iterrows():

    keyword = row["parameter_name"].split()[0].lower()

    matches = audit[
        audit["header_evidence"].str.contains(
            keyword, case=False, na=False
        )
    ]

    result.at[index, "source_files_found"] = "; ".join(
        sorted(matches["source_file"].unique())
    )

result.to_csv(OUTPUT, index=False)

print("\nMEASUREMENT DATA DICTIONARY CREATED")
print(result.to_string(index=False))
print("\nSaved:", OUTPUT)