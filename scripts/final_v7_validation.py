import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "datasets/cleaned/nwmp_master_verified_v7.csv"
EVIDENCE = ROOT / "reports/anomaly_header_evidence.csv"
LOG = ROOT / "reports/v7_correction_log.csv"
REVIEW = ROOT / "reports/v7_manual_review.csv"

REPORT = ROOT / "reports/final_v7_validation.txt"
UNMATCHED = ROOT / "reports/v7_unmatched_anomalies.csv"

df = pd.read_csv(DATA, dtype=str, keep_default_na=False)
ev = pd.read_csv(EVIDENCE, dtype=str, keep_default_na=False)
log = pd.read_csv(LOG)
review = pd.read_csv(REVIEW)

# Parameter naming differences between source evidence and dataset
aliases = {
    "dissolved_oxygen_min": "do_min",
    "dissolved_oxygen_max": "do_max"
}

ev["dataset_parameter"] = ev["parameter"].replace(aliases)

# Verify all 62 source anomalies against V7 raw-value columns
results = []

for _, item in ev.iterrows():

    parameter = item["dataset_parameter"]
    raw_col = parameter + "_raw"

    if raw_col not in df.columns:
        results.append({
            "anomaly_number": item["anomaly_number"],
            "station_code": item["station_code"],
            "year": item["year"],
            "parameter": parameter,
            "original_value": item["original_value"],
            "result": "PARAMETER COLUMN NOT FOUND"
        })
        continue

    mask = (
        (df["station_code"].astype(str) == item["station_code"]) &
        (df["year"].astype(str) == item["year"]) &
        (df[raw_col].astype(str) == item["original_value"])
    )

    results.append({
        "anomaly_number": item["anomaly_number"],
        "station_code": item["station_code"],
        "year": item["year"],
        "parameter": parameter,
        "original_value": item["original_value"],
        "result": "MATCHED" if mask.any() else "NOT MATCHED"
    })

results_df = pd.DataFrame(results)
results_df.to_csv(UNMATCHED, index=False)

# Measurement columns
measurement_columns = [
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

available = [
    c for c in measurement_columns
    if c in df.columns
]

missing = [
    c for c in measurement_columns
    if c not in df.columns
]

matched = (results_df["result"] == "MATCHED").sum()
unmatched = len(results_df) - matched

line_breaks = (ev["classification"] == "Embedded line break").sum()
outliers = (ev["classification"] == "").sum()
other_text = (ev["classification"] == "Other text or formatting").sum()

with open(REPORT, "w", encoding="utf-8") as f:

    f.write("FINAL V7 DATASET VALIDATION\n")
    f.write("=" * 50 + "\n\n")

    f.write(f"Dataset records: {len(df)}\n")
    f.write(f"Expected measurement columns: 18\n")
    f.write(f"Available measurement columns: {len(available)}\n")
    f.write(f"Missing measurement columns: {missing}\n\n")

    f.write(f"Source anomalies: {len(ev)}\n")
    f.write(f"Matched anomalies: {matched}\n")
    f.write(f"Unmatched anomalies: {unmatched}\n\n")

    f.write(f"Original line-break cases: {line_breaks}\n")
    f.write(f"Original potential outliers: {outliers}\n")
    f.write(f"Other formatting cases: {other_text}\n\n")

    f.write(f"Automatic corrections recorded: {len(log)}\n")
    f.write(f"Manual review rows: {len(review)}\n\n")

    f.write("DATASET PRESERVATION CHECK\n")
    f.write(f"Original raw-value columns available: "
            f"{sum(c.endswith('_raw') for c in df.columns)}\n")

    f.write("\nWQI STATUS: NOT YET APPROVED\n")
    f.write("Scientific units, parameter mapping and standards "
            "must be validated before WQI calculation.\n")

print("\nFINAL VALIDATION COMPLETE")
print("Records:", len(df))
print("Measurement columns:", len(available), "/ 18")
print("Matched source anomalies:", matched, "/ 62")
print("Unmatched source anomalies:", unmatched)
print("Report:", REPORT)
print("Unmatched details:", UNMATCHED)