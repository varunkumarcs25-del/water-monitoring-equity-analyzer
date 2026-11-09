import pandas as pd
import numpy as np
import re
from pathlib import Path

# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "datasets" / "cleaned" / "nwmp_master_dedup_candidate_v5.csv"
EVIDENCE_FILE = ROOT / "reports" / "anomaly_header_evidence.csv"

OUTPUT_FILE = ROOT / "datasets" / "cleaned" / "nwmp_master_verified_v7.csv"
LOG_FILE = ROOT / "reports" / "v7_correction_log.csv"
REVIEW_FILE = ROOT / "reports" / "v7_manual_review.csv"
SUMMARY_FILE = ROOT / "reports" / "v7_validation_summary.txt"

MEASUREMENT_COLUMNS = [
    "temperature_min", "temperature_max",
    "do_min", "do_max",
    "ph_min", "ph_max",
    "conductivity_min", "conductivity_max",
    "bod_min", "bod_max",
    "nitrate_min", "nitrate_max",
    "fecal_coliform_min", "fecal_coliform_max",
    "total_coliform_min", "total_coliform_max",
    "fecal_streptococci_min", "fecal_streptococci_max"
]

# =========================================================
# LOAD DATA
# =========================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input dataset not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE, dtype=str, keep_default_na=False)

print("Input records:", len(df))

# Preserve original values in companion columns.
available_columns = [c for c in MEASUREMENT_COLUMNS if c in df.columns]

if not available_columns:
    raise ValueError("No expected measurement columns found. Check dataset headers.")

for col in available_columns:
    df[col + "_raw"] = df[col]

# =========================================================
# CLEAN AND CLASSIFY MEASUREMENTS
# =========================================================

correction_log = []
manual_review = []

for col in available_columns:

    raw_col = col + "_raw"
    status_col = col + "_status"

    numeric_values = []
    statuses = []

    for idx, raw_value in df[raw_col].items():

        original = str(raw_value).strip()
        cleaned = original

        if original == "" or original.lower() in ["nan", "none"]:
            numeric_values.append(np.nan)
            statuses.append("MISSING")
            continue

        # BDL is preserved as a qualifier, never converted to zero.
        if re.fullmatch(r"BDL", original, flags=re.IGNORECASE):
            numeric_values.append(np.nan)
            statuses.append("BDL")
            continue

        if original in ["-", "--", "_"]:
            numeric_values.append(np.nan)
            statuses.append("MISSING_MARKER")
            continue

        # Remove line breaks and surrounding whitespace.
        if "\n" in cleaned or "\r" in cleaned:
            candidate = re.sub(r"[\r\n\s]+", "", cleaned)

            # Correct only if the complete result is numeric.
            try:
                number = float(candidate)

                numeric_values.append(number)
                statuses.append("CORRECTED_LINE_BREAK")

                correction_log.append({
                    "dataframe_row": idx,
                    "column": col,
                    "original_value": original,
                    "corrected_value": candidate,
                    "correction": "Removed embedded line break",
                    "status": "AUTOMATICALLY_CORRECTED"
                })
                continue

            except ValueError:
                numeric_values.append(np.nan)
                statuses.append("MANUAL_REVIEW")

                manual_review.append({
                    "dataframe_row": idx,
                    "column": col,
                    "original_value": original,
                    "reason": "Line-break value remains non-numeric",
                    "action": "Requires original-source verification"
                })
                continue

        # Normal numeric value.
        try:
            number = float(cleaned)
            numeric_values.append(number)
            statuses.append("VALID_NUMERIC")

        except ValueError:
            numeric_values.append(np.nan)
            statuses.append("MANUAL_REVIEW")

            manual_review.append({
                "dataframe_row": idx,
                "column": col,
                "original_value": original,
                "reason": "Unrecognized non-numeric value",
                "action": "Preserved in raw column; manual review required"
            })

    df[col] = numeric_values
    df[status_col] = statuses

# =========================================================
# VERIFY THE 62 SOURCE-INSPECTED ANOMALIES
# =========================================================

verified_anomaly_count = 0

if EVIDENCE_FILE.exists():

    evidence = pd.read_csv(EVIDENCE_FILE, dtype=str, keep_default_na=False)

    for _, item in evidence.iterrows():

        parameter = item.get("parameter", "")
        station = item.get("station_code", "")
        year = item.get("year", "")
        original = item.get("original_value", "")

        if parameter not in available_columns:
            continue

        mask = (
            (df["station_code"].astype(str) == str(station)) &
            (df["year"].astype(str) == str(year)) &
            (df[parameter + "_raw"].astype(str) == str(original))
        )

        if mask.any():
            verified_anomaly_count += int(mask.sum())

else:
    print("WARNING: Evidence CSV not found. Dataset processing will continue.")

# =========================================================
# PRESERVE POTENTIAL OUTLIERS
# =========================================================

outlier_records = []

outlier_rules = {
    "do_max": 25,
    "bod_min": 100,
    "bod_max": 100,
}

for col, threshold in outlier_rules.items():

    if col not in available_columns:
        continue

    mask = pd.to_numeric(df[col], errors="coerce") > threshold

    for idx in df.index[mask]:

        outlier_records.append({
            "dataframe_row": idx,
            "column": col,
            "value": df.loc[idx, col],
            "action": "RETAINED_FOR_SCIENTIFIC_REVIEW"
        })

# =========================================================
# SAVE OUTPUTS
# =========================================================

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT_FILE, index=False)

pd.DataFrame(correction_log).to_csv(LOG_FILE, index=False)

review_df = pd.DataFrame(manual_review)

outlier_df = pd.DataFrame(outlier_records)

if not outlier_df.empty:
    review_df = pd.concat([review_df, outlier_df], ignore_index=True)

review_df.to_csv(REVIEW_FILE, index=False)

# =========================================================
# SUMMARY REPORT
# =========================================================

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:

    f.write("NWMP VERIFIED DATASET V7 - VALIDATION SUMMARY\n")
    f.write("=" * 55 + "\n\n")

    f.write(f"Input records: {len(df)}\n")
    f.write(f"Output records: {len(df)}\n")
    f.write(f"Measurement columns processed: {len(available_columns)}\n")
    f.write(f"Source-inspected anomaly matches: {verified_anomaly_count}\n")
    f.write(f"Automatic formatting corrections: {len(correction_log)}\n")
    f.write(f"Manual review entries: {len(manual_review)}\n")
    f.write(f"Potential outliers retained: {len(outlier_records)}\n\n")

    f.write("IMPORTANT DATA HANDLING RULES\n")
    f.write("- Original measurement values preserved in *_raw columns.\n")
    f.write("- BDL values preserved as BDL status, not zero.\n")
    f.write("- Missing values are not zero-filled.\n")
    f.write("- Ambiguous values are not automatically corrected.\n")
    f.write("- Potential outliers are retained.\n")
    f.write("- No original dataset was overwritten.\n")

print("\n========== V7 COMPLETE ==========")
print("Records:", len(df))
print("Measurements processed:", len(available_columns))
print("Automatic corrections:", len(correction_log))
print("Manual review entries:", len(manual_review))
print("Potential outliers retained:", len(outlier_records))
print("Source anomaly matches:", verified_anomaly_count)

print("\nOUTPUT FILES:")
print(OUTPUT_FILE)
print(LOG_FILE)
print(REVIEW_FILE)
print(SUMMARY_FILE)