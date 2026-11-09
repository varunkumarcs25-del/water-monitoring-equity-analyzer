import pandas as pd
import numpy as np
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "datasets/cleaned/nwmp_master_dedup_candidate_v5.csv"
OUTPUT = ROOT / "datasets/cleaned/nwmp_master_verified_v8.csv"

REPORT = ROOT / "reports/v8_correction_log.csv"
REVIEW = ROOT / "reports/v8_manual_review.csv"
SUMMARY = ROOT / "reports/v8_validation_summary.txt"

PARAMETERS = [
    "temperature", "dissolved_oxygen", "ph",
    "conductivity", "bod", "nitrate",
    "fecal_coliform", "total_coliform",
    "fecal_streptococci"
]

COLUMNS = [
    f"{parameter}_{suffix}"
    for parameter in PARAMETERS
    for suffix in ["min", "max"]
]

df = pd.read_csv(INPUT, dtype=str, keep_default_na=False)

missing = [c for c in COLUMNS if c not in df.columns]

if missing:
    raise ValueError(f"Missing measurement columns: {missing}")

corrections = []
manual = []

for col in COLUMNS:

    raw_col = col + "_raw"
    status_col = col + "_status"

    original_values = df[col].copy()
    numeric_values = []
    statuses = []

    for idx, value in original_values.items():

        original = str(value).strip()

        if original == "":
            numeric_values.append(np.nan)
            statuses.append("MISSING")

        elif original.upper() == "BDL":
            numeric_values.append(np.nan)
            statuses.append("BDL")

        elif original in ["-", "--", "_"]:
            numeric_values.append(np.nan)
            statuses.append("MISSING_MARKER")

        elif "\n" in original or "\r" in original:

            cleaned = re.sub(r"[\r\n\s]+", "", original)

            try:
                number = float(cleaned)

                numeric_values.append(number)
                statuses.append("CORRECTED_LINE_BREAK")

                corrections.append({
                    "row": idx,
                    "column": col,
                    "original": original,
                    "corrected": cleaned,
                    "status": "CORRECTED"
                })

            except ValueError:

                numeric_values.append(np.nan)
                statuses.append("MANUAL_REVIEW")

                manual.append({
                    "row": idx,
                    "column": col,
                    "original": original,
                    "reason": "Ambiguous line-break value"
                })

        else:

            try:
                numeric_values.append(float(original))
                statuses.append("VALID_NUMERIC")

            except ValueError:

                numeric_values.append(np.nan)
                statuses.append("MANUAL_REVIEW")

                manual.append({
                    "row": idx,
                    "column": col,
                    "original": original,
                    "reason": "Unrecognized measurement value"
                })

    df[raw_col] = original_values
    df[col] = numeric_values
    df[status_col] = statuses

# Preserve all numerical outliers.
# Do not automatically delete or modify them.

outliers = []

for col in COLUMNS:

    values = pd.to_numeric(df[col], errors="coerce")

    for idx in values[values.notna()].index:

        value = values.loc[idx]

        if col.startswith("bod_") and value > 100:
            outliers.append({
                "row": idx,
                "column": col,
                "value": value,
                "status": "RETAINED_FOR_REVIEW"
            })

        elif col.startswith("fecal_coliform_") and value > 100000:
            outliers.append({
                "row": idx,
                "column": col,
                "value": value,
                "status": "RETAINED_FOR_REVIEW"
            })

        elif col.startswith("total_coliform_") and value > 100000:
            outliers.append({
                "row": idx,
                "column": col,
                "value": value,
                "status": "RETAINED_FOR_REVIEW"
            })

pd.DataFrame(corrections).to_csv(REPORT, index=False)

review_df = pd.DataFrame(manual)
outlier_df = pd.DataFrame(outliers)

review_df.to_csv(REVIEW, index=False)

df.to_csv(OUTPUT, index=False)

with open(SUMMARY, "w", encoding="utf-8") as f:

    f.write("V8 DATASET VALIDATION\n")
    f.write("=" * 45 + "\n")
    f.write(f"Records: {len(df)}\n")
    f.write(f"Expected measurement columns: 18\n")
    f.write(f"Available measurement columns: {len(COLUMNS)}\n")
    f.write(f"Automatic corrections: {len(corrections)}\n")
    f.write(f"Manual review entries: {len(manual)}\n")
    f.write(f"Potential outliers retained: {len(outliers)}\n")
    f.write("Original v5 dataset preserved.\n")
    f.write("BDL values are not converted to zero.\n")
    f.write("Missing values are not zero-filled.\n")

print("\n========== V8 COMPLETE ==========")
print("Records:", len(df))
print("Measurement columns:", len(COLUMNS))
print("Automatic corrections:", len(corrections))
print("Manual review:", len(manual))
print("Potential outliers retained:", len(outliers))
print("\nSaved:", OUTPUT)
print("Correction log:", REPORT)
print("Review file:", REVIEW)
print("Summary:", SUMMARY)