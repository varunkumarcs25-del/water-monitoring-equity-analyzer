import pandas as pd
import numpy as np
from pathlib import Path

# ==========================================
# PATHS
# ==========================================

BASE = Path(__file__).resolve().parent.parent

INPUT = BASE / "datasets/cleaned/nwmp_master_dedup_candidate_v5.csv"
OUTPUT = BASE / "datasets/cleaned/nwmp_quality_review_v6.csv"

REPORT = BASE / "reports/data_quality_correction_report.txt"
ISSUES = BASE / "reports/data_quality_issues_v6.csv"

# ==========================================
# LOAD DATA
# ==========================================

df = pd.read_csv(INPUT, low_memory=False)
original = df.copy()

print("\n========== DATA QUALITY CORRECTION ==========")
print("Records:", len(df))

# ==========================================
# NUMERIC CONVERSION
# ==========================================

measurement_columns = [
    c for c in df.columns
    if c.endswith("_min") or c.endswith("_max")
]

issues = []

for col in measurement_columns:

    original_values = df[col].copy()
    converted = pd.to_numeric(original_values, errors="coerce")

    invalid_mask = original_values.notna() & converted.isna()

    for idx in df.index[invalid_mask]:
        issues.append({
            "row": idx,
            "station_code": df.loc[idx, "station_code"],
            "year": df.loc[idx, "year"],
            "column": col,
            "original_value": original_values.loc[idx],
            "issue": "Non-numeric measurement"
        })

    df[col] = converted

# ==========================================
# PRELIMINARY OUTLIER DETECTION
# Do not delete potential outliers.
# ==========================================

ranges = {
    "dissolved_oxygen": (0, 25),
    "ph": (0, 14),
    "bod": (0, 100),
    "conductivity": (0, 100000),
    "nitrate": (0, 1000),
    "fecal_coliform": (0, 100000000),
    "total_coliform": (0, 100000000),
    "temperature": (-5, 60)
}

outlier_count = 0

for parameter, (low, high) in ranges.items():

    for suffix in ["_min", "_max"]:

        col = parameter + suffix

        if col not in df.columns:
            continue

        mask = (
            df[col].notna()
            & ~df[col].between(low, high)
        )

        for idx in df.index[mask]:

            issues.append({
                "row": idx,
                "station_code": df.loc[idx, "station_code"],
                "year": df.loc[idx, "year"],
                "column": col,
                "original_value": df.loc[idx, col],
                "issue": "Potential range violation - review required"
            })

            outlier_count += 1

# ==========================================
# DUPLICATE CLASSIFICATION
# ==========================================

duplicate_rows = df[
    df.duplicated(
        subset=["year", "station_code"],
        keep=False
    )
].copy()

duplicate_rows["duplicate_type"] = ""

for _, group in duplicate_rows.groupby(
    ["year", "station_code"],
    dropna=False
):

    categories = set(group["category"].dropna())
    sheets = set(group["source_sheet"].dropna())

    if len(categories) > 1:
        kind = "Major-Medium overlap"

    elif len(sheets) > 1:
        kind = "Multiple source sheets"

    else:
        kind = "Same-sheet repeated station"

    duplicate_rows.loc[group.index, "duplicate_type"] = kind

# ==========================================
# SAVE OUTPUTS
# ==========================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT, index=False)

issue_df = pd.DataFrame(issues)

issue_df.to_csv(ISSUES, index=False)

# ==========================================
# GENERATE REPORT
# ==========================================

with open(REPORT, "w", encoding="utf-8") as f:

    f.write("DATA QUALITY CORRECTION REPORT\n")
    f.write("=" * 50 + "\n\n")

    f.write(f"Original records: {len(original)}\n")
    f.write(f"Output records: {len(df)}\n")

    f.write(
        f"Non-numeric values converted to missing: "
        f"{sum(x['issue'] == 'Non-numeric measurement' for x in issues)}\n"
    )

    f.write(
        f"Potential range violations: {outlier_count}\n"
    )

    f.write(
        f"Rows participating in duplicate groups: "
        f"{len(duplicate_rows)}\n\n"
    )

    f.write("DUPLICATE CLASSIFICATION\n")
    f.write("-" * 50 + "\n")

    if not duplicate_rows.empty:
        f.write(
            duplicate_rows["duplicate_type"]
            .value_counts()
            .to_string()
        )
    else:
        f.write("No duplicate groups found.")

    f.write("\n\nIMPORTANT NOTES\n")
    f.write("-" * 50 + "\n")

    f.write(
        "Non-numeric entries were converted to missing values "
        "in the output dataset. Original source files remain unchanged.\n"
    )

    f.write(
        "Potential outliers were identified but NOT deleted.\n"
    )

    f.write(
        "Station-year duplicates were classified but NOT deleted.\n"
    )

    f.write(
        "Measurement units and source-to-output accuracy still "
        "require verification.\n"
    )

# ==========================================
# FINAL SUMMARY
# ==========================================

print("\n========== COMPLETE ==========")
print("Records:", len(df))
print("Non-numeric values:", sum(
    x["issue"] == "Non-numeric measurement" for x in issues
))
print("Potential outliers:", outlier_count)
print("Duplicate group rows:", len(duplicate_rows))

print("\nSaved files:")
print(OUTPUT)
print(REPORT)
print(ISSUES)

print("\nOriginal datasets remain unchanged.")