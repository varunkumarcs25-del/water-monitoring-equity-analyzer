import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "datasets/cleaned/nwmp_master_verified_v8.csv"
OUTPUT = ROOT / "reports/v8_measurement_profile.csv"

df = pd.read_csv(INPUT)

parameters = [
    "temperature", "dissolved_oxygen", "ph",
    "conductivity", "bod", "nitrate",
    "fecal_coliform", "total_coliform",
    "fecal_streptococci"
]

results = []

for p in parameters:
    for suffix in ["min", "max"]:
        col = f"{p}_{suffix}"
        s = pd.to_numeric(df[col], errors="coerce")

        results.append({
            "parameter": col,
            "valid_values": s.count(),
            "missing_values": s.isna().sum(),
            "minimum": s.min(),
            "median": s.median(),
            "mean": s.mean(),
            "maximum": s.max()
        })

result = pd.DataFrame(results)
result.to_csv(OUTPUT, index=False)

print("\n========== MEASUREMENT PROFILE ==========")
print(result.to_string(index=False))
print("\nSaved:", OUTPUT)