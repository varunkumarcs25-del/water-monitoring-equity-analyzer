import pandas as pd
from pathlib import Path

# ==========================================
# PATHS
# ==========================================

BASE = Path(__file__).resolve().parent.parent

DATA = BASE / "datasets/cleaned/nwmp_master_dedup_candidate_v5.csv"
ISSUES = BASE / "reports/data_quality_issues_v6.csv"

OUTPUT = BASE / "reports/measurement_anomaly_source_review.csv"
SUMMARY = BASE / "reports/measurement_anomaly_summary.txt"

# ==========================================
# LOAD DATA
# ==========================================

df = pd.read_csv(DATA, low_memory=False)
issues = pd.read_csv(ISSUES, low_memory=False)

print("\n========== ANOMALY SOURCE INSPECTION ==========")

# ==========================================
# CLASSIFY NON-NUMERIC VALUES
# ==========================================

non_numeric = issues[
    issues["issue"] == "Non-numeric measurement"
].copy()

def classify(value):

    if pd.isna(value):
        return "Missing"

    value = str(value).strip()

    if value == "-":
        return "Hyphen missing marker"

    if value == "--":
        return "Double hyphen missing marker"

    if value.upper() == "BDL":
        return "Below Detection Limit"

    if value == "_":
        return "Underscore marker"

    if "\n" in value or "\r" in value:
        return "Embedded line break"

    return "Other text or formatting"

non_numeric["classification"] = (
    non_numeric["original_value"].apply(classify)
)

# ==========================================
# ADD ORIGINAL SOURCE INFORMATION
# ==========================================

metadata_columns = [
    "source_file",
    "source_sheet",
    "source_row",
    "category",
    "location",
    "state"
]

for col in metadata_columns:
    if col in df.columns:
        non_numeric[col] = non_numeric["row"].map(df[col])

# ==========================================
# INSPECT POTENTIAL OUTLIERS
# ==========================================

outliers = issues[
    issues["issue"].str.contains(
        "range violation",
        case=False,
        na=False
    )
].copy()

for col in metadata_columns:
    if col in df.columns:
        outliers[col] = outliers["row"].map(df[col])

# ==========================================
# COMBINE AND SAVE
# ==========================================

review = pd.concat(
    [non_numeric, outliers],
    ignore_index=True,
    sort=False
)

review.to_csv(OUTPUT, index=False)

# ==========================================
# GENERATE SUMMARY
# ==========================================

with open(SUMMARY, "w", encoding="utf-8") as f:

    f.write("MEASUREMENT ANOMALY REVIEW\n")
    f.write("=" * 50 + "\n\n")

    f.write("NON-NUMERIC VALUE CLASSIFICATION\n")
    f.write("-" * 50 + "\n")

    f.write(
        non_numeric["classification"]
        .value_counts()
        .to_string()
    )

    f.write("\n\nCOLUMN-WISE NON-NUMERIC COUNTS\n")
    f.write("-" * 50 + "\n")

    f.write(
        non_numeric["column"]
        .value_counts()
        .to_string()
    )

    f.write("\n\nPOTENTIAL OUTLIERS\n")
    f.write("-" * 50 + "\n")

    f.write(
        outliers[
            ["station_code", "year", "column", "original_value"]
        ].to_string(index=False)
    )

    f.write("\n\nAll observations retain their original source references.\n")

# ==========================================
# FINAL OUTPUT
# ==========================================

print("\nVALUE CLASSIFICATION:")
print(non_numeric["classification"].value_counts().to_string())

print("\nCOLUMN-WISE COUNTS:")
print(non_numeric["column"].value_counts().to_string())

print("\nPotential outliers:", len(outliers))

print("\nGenerated files:")
print(OUTPUT)
print(SUMMARY)

print("\nOriginal datasets remain unchanged.")
print("========== COMPLETE ==========")