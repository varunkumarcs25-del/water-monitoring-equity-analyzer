import pandas as pd
import numpy as np
from pathlib import Path

# ==================================================
# 1. PROJECT PATHS
# ==================================================

BASE = Path(__file__).resolve().parent.parent

INPUT = BASE / "datasets" / "cleaned" / "nwmp_master_verified_v8.csv"

OUTPUT = BASE / "datasets" / "cleaned" / "nwmp_wqi_screening_v8.csv"

REPORT = BASE / "reports" / "wqi_validation_report_v8.txt"

# ==================================================
# 2. LOAD DATA
# ==================================================

print("\n========== WQI DATA VALIDATION ==========")

if not INPUT.exists():
    raise FileNotFoundError(f"Input dataset not found: {INPUT}")

df = pd.read_csv(INPUT, low_memory=False)

original_count = len(df)

print("Input records:", original_count)

# ==================================================
# 3. DEFINE PARAMETERS
# ==================================================

parameters = [
    "dissolved_oxygen",
    "ph",
    "bod",
    "conductivity",
    "nitrate",
    "total_coliform",
    "fecal_coliform"
]

# Six parameters used for screening eligibility.
required = [
    "dissolved_oxygen",
    "ph",
    "bod",
    "conductivity",
    "nitrate",
    "total_coliform"
]

# ==================================================
# 4. CONVERT MEASUREMENTS TO NUMERIC
# ==================================================

for parameter in parameters:

    minimum = parameter + "_min"
    maximum = parameter + "_max"

    for column in [minimum, maximum]:

        if column not in df.columns:
            raise ValueError(f"Required column missing: {column}")

        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # Representative value using available Min/Max values.
    df[parameter] = df[[minimum, maximum]].mean(
        axis=1,
        skipna=True
    )

# ==================================================
# 5. PLAUSIBILITY FLAGS (DO NOT DELETE VALUES)
# ==================================================

# These are broad screening limits, NOT regulatory standards.
# Values outside these limits are retained for manual review.

screening_ranges = {
    "dissolved_oxygen": (0, 25),
    "ph": (0, 14),
    "bod": (0, 100),
    "conductivity": (0, 100000),
    "nitrate": (0, 1000),
    "total_coliform": (0, 100000000),
    "fecal_coliform": (0, 100000000)
}

flagged_counts = {}

for parameter, (lower, upper) in screening_ranges.items():

    flag_column = parameter + "_review_flag"

    invalid_mask = (
        df[parameter].notna()
        & ~df[parameter].between(lower, upper)
    )

    df[flag_column] = np.where(
        invalid_mask,
        "Review required",
        "Within screening range"
    )

    flagged_counts[parameter] = int(invalid_mask.sum())

# ==================================================
# 6. CHECK PARAMETER COMPLETENESS
# ==================================================

df["valid_parameter_count"] = df[required].notna().sum(axis=1)

df["wqi_status"] = np.where(
    df["valid_parameter_count"] >= 4,
    "Eligible for WQI validation",
    "Insufficient measurements"
)

# Flag records containing at least one screening-range warning.
flag_columns = [
    parameter + "_review_flag"
    for parameter in parameters
]

df["measurement_review_required"] = (
    df[flag_columns] == "Review required"
).any(axis=1)

# ==================================================
# 7. PARAMETER AVAILABILITY
# ==================================================

available_counts = df[parameters].notna().sum()

missing_counts = df[parameters].isna().sum()

eligible_count = int(
    (df["valid_parameter_count"] >= 4).sum()
)

insufficient_count = int(
    (df["valid_parameter_count"] < 4).sum()
)

review_records = int(
    df["measurement_review_required"].sum()
)

# ==================================================
# 8. SAVE SCREENING DATASET
# ==================================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(OUTPUT, index=False)

# ==================================================
# 9. GENERATE VALIDATION REPORT
# ==================================================

with open(REPORT, "w", encoding="utf-8") as file:

    file.write("WQI DATA VALIDATION REPORT - V8\n")
    file.write("=" * 50 + "\n\n")

    file.write(f"Total records: {original_count}\n")
    file.write(f"Eligible records: {eligible_count}\n")
    file.write(f"Insufficient records: {insufficient_count}\n")
    file.write(f"Records requiring measurement review: {review_records}\n\n")

    file.write("PARAMETER AVAILABILITY\n")
    file.write("-" * 50 + "\n")

    for parameter in parameters:
        file.write(
            f"{parameter}: {available_counts[parameter]} available\n"
        )

    file.write("\nMISSING MEASUREMENTS\n")
    file.write("-" * 50 + "\n")

    for parameter in parameters:
        file.write(
            f"{parameter}: {missing_counts[parameter]} missing\n"
        )

    file.write("\nMEASUREMENTS FLAGGED FOR REVIEW\n")
    file.write("-" * 50 + "\n")

    for parameter, count in flagged_counts.items():
        file.write(f"{parameter}: {count} flagged values\n")

    file.write("\nIMPORTANT METHODOLOGICAL NOTES\n")
    file.write("-" * 50 + "\n")

    file.write(
        "This output is a WQI screening dataset, not a final WQI dataset.\n"
        "The Min/Max average is used as a representative value where "
        "one or both measurements are available.\n"
        "Broad plausibility limits are used only to flag values for review. "
        "No measurements are deleted because of these flags.\n"
        "Eligibility means at least four of six selected parameters "
        "are available. It does not establish that a valid WQI can "
        "be calculated.\n"
        "Nitrate measurements from different source definitions must "
        "be reconciled before final WQI calculation.\n"
        "Final WQI calculation requires verified units, an appropriate "
        "river-water quality standard, parameter-specific ideal values, "
        "quality ratings and justified weights.\n"
    )

# ==================================================
# 10. FINAL SUMMARY
# ==================================================

print("\n========== PROCESSING COMPLETE ==========")

print("Total records:", original_count)
print("Eligible for WQI validation:", eligible_count)
print("Insufficient measurements:", insufficient_count)
print("Records requiring review:", review_records)

print("\nParameter availability:")
print(available_counts.to_string())

print("\nMeasurements flagged for review:")
print(pd.Series(flagged_counts).to_string())

print("\nOUTPUT FILES")
print("Screening dataset:", OUTPUT)
print("Validation report:", REPORT)

print("\nOriginal V8 dataset remains unchanged.")
print("No measurements were deleted by range screening.")
print("==========================================")