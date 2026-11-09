import pandas as pd
from pathlib import Path

# --------------------------------
# PATHS
# --------------------------------
BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "datasets" / "cleaned" / "nwmp_master_mapped_v4.csv"
OUTPUT = BASE / "datasets" / "cleaned" / "nwmp_master_dedup_candidate_v5.csv"
DUPLICATES = BASE / "reports" / "duplicate_classification.csv"
SUMMARY = BASE / "reports" / "duplicate_summary.csv"
CLEANING_REPORT = BASE / "reports" / "nwmp_cleaning_report.txt"

# --------------------------------
# LOAD DATA
# --------------------------------
df = pd.read_csv(INPUT, low_memory=False)
original_count = len(df)

print("\n========== NWMP CLEANING ==========")
print("Original records:", original_count)

# --------------------------------
# IDENTIFY DUPLICATE GROUPS
# --------------------------------
group_cols = ["year", "station_code"]
duplicate_mask = df.duplicated(subset=group_cols, keep=False)

duplicates = df.loc[duplicate_mask].copy()
duplicates["duplicate_group_type"] = ""

for _, group in duplicates.groupby(group_cols, dropna=False):
    categories = set(group["category"].dropna().astype(str))
    sheets = set(group["source_sheet"].dropna().astype(str))

    if len(categories) > 1:
        group_type = "major_medium_overlap"
    elif len(sheets) > 1:
        group_type = "same_category_multiple_sheets"
    else:
        group_type = "same_sheet_repeat"

    duplicates.loc[group.index, "duplicate_group_type"] = group_type

# Save detailed duplicate review
DUPLICATES.parent.mkdir(parents=True, exist_ok=True)
duplicates.to_csv(DUPLICATES, index=False)

# Save duplicate summary
if not duplicates.empty:
    summary = (
        duplicates.groupby("duplicate_group_type")
        .agg(
            rows=("station_code", "size"),
            unique_station_years=("station_code", "count")
        )
        .reset_index()
    )
else:
    summary = pd.DataFrame(
        columns=["duplicate_group_type", "rows", "unique_station_years"]
    )

summary.to_csv(SUMMARY, index=False)

# --------------------------------
# REMOVE ONLY EXACT REPEATED ROWS
# Keep source sheet, category, location,
# state and all measurements in comparison.
# Ignore source_row because repeated copies
# may have different Excel row positions.
# --------------------------------
dedup_columns = [c for c in df.columns if c != "source_row"]

candidate = df.drop_duplicates(
    subset=dedup_columns,
    keep="first"
).copy()

removed = original_count - len(candidate)

# --------------------------------
# SAVE CANDIDATE DATASET
# --------------------------------
candidate.to_csv(OUTPUT, index=False)

# --------------------------------
# MISSING MEASUREMENT REPORT
# --------------------------------
measurement_columns = [
    c for c in candidate.columns
    if c.endswith("_min") or c.endswith("_max")
]

missing_report = candidate[measurement_columns].isna().sum()

# --------------------------------
# CLEANING REPORT
# --------------------------------
with open(CLEANING_REPORT, "w", encoding="utf-8") as f:
    f.write("NWMP DATA CLEANING REPORT\n")
    f.write("=========================\n\n")
    f.write(f"Original records: {original_count}\n")
    f.write(f"Exact repeated rows removed: {removed}\n")
    f.write(f"Candidate records: {len(candidate)}\n")
    f.write(f"Remaining duplicate station-year rows: ")
    f.write(
        f"{candidate.duplicated(subset=group_cols, keep=False).sum()}\n\n"
    )

    f.write("DUPLICATE CLASSIFICATION\n")
    f.write("------------------------\n")
    f.write(summary.to_string(index=False))
    f.write("\n\nMISSING MEASUREMENTS\n")
    f.write("--------------------\n")
    f.write(missing_report.to_string())

# --------------------------------
# FINAL OUTPUT
# --------------------------------
print("\nDuplicate classification:")
print(summary.to_string(index=False))

print("\nExact repeated rows removed:", removed)
print("Candidate records:", len(candidate))

print("\nMissing measurements:")
print(missing_report.to_string())

print("\n========== COMPLETE ==========")
print("Candidate CSV:", OUTPUT)
print("Duplicate review:", DUPLICATES)
print("Summary:", SUMMARY)
print("Cleaning report:", CLEANING_REPORT)
print("\nOriginal v4 file remains unchanged.")