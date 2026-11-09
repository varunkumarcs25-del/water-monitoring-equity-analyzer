import pandas as pd
import numpy as np
from pathlib import Path

# ==================================================
# 1. PATHS
# ==================================================

BASE = Path(__file__).resolve().parent.parent

RAW = BASE / "datasets" / "raw"
CLEANED = BASE / "datasets" / "cleaned"
REPORTS = BASE / "reports"

INPUT = CLEANED / "nwmp_master_dedup_candidate_v5.csv"
GADM = RAW / "gadm41_IND_2.geojson"

REPORT = REPORTS / "final_data_quality_audit.txt"
ISSUES = REPORTS / "final_data_quality_issues.csv"

REPORTS.mkdir(parents=True, exist_ok=True)

# ==================================================
# 2. LOAD DATA
# ==================================================

print("\n========== FINAL DATA QUALITY AUDIT ==========")

if not INPUT.exists():
    raise FileNotFoundError(f"Dataset not found: {INPUT}")

df = pd.read_csv(INPUT, low_memory=False)

checks = []
issues = []

def add_check(name, status, details):
    checks.append({
        "check": name,
        "status": status,
        "details": details
    })

def add_issue(category, description, count):
    if count > 0:
        issues.append({
            "category": category,
            "description": description,
            "count": int(count)
        })

print("Records loaded:", len(df))

# ==================================================
# 3. STRUCTURAL VALIDATION
# ==================================================

required_columns = [
    "year", "category", "station_code",
    "location", "state",
    "dissolved_oxygen_min", "dissolved_oxygen_max",
    "ph_min", "ph_max",
    "bod_min", "bod_max",
    "conductivity_min", "conductivity_max",
    "nitrate_min", "nitrate_max",
    "fecal_coliform_min", "fecal_coliform_max",
    "total_coliform_min", "total_coliform_max"
]

missing_columns = [
    c for c in required_columns if c not in df.columns
]

if not missing_columns:
    add_check(
        "Required columns",
        "PASS",
        "All required columns are present."
    )
else:
    add_check(
        "Required columns",
        "FAIL",
        f"Missing columns: {missing_columns}"
    )

# ==================================================
# 4. MISSING VALUE ANALYSIS
# ==================================================

missing = df.isna().sum()
missing_total = int(missing.sum())

add_check(
    "Missing value analysis",
    "WARNING" if missing_total > 0 else "PASS",
    f"{missing_total} missing cells found. Missingness is documented."
)

for col, count in missing.items():
    add_issue("Missing values", col, count)

# ==================================================
# 5. DUPLICATE VALIDATION
# ==================================================

station_duplicates = df.duplicated(
    subset=["year", "station_code"],
    keep=False
).sum()

exact_duplicates = df.duplicated(
    subset=[c for c in df.columns if c != "source_row"]
).sum()

add_check(
    "Exact duplicate records",
    "PASS" if exact_duplicates == 0 else "WARNING",
    f"{exact_duplicates} exact duplicates found."
)

add_check(
    "Station-year duplicates",
    "WARNING" if station_duplicates > 0 else "PASS",
    f"{station_duplicates} rows belong to repeated station-year groups. "
    "These require classification, not automatic deletion."
)

add_issue(
    "Duplicate records",
    "Repeated year and station_code combinations",
    station_duplicates
)

# ==================================================
# 6. DATA TYPE VALIDATION
# ==================================================

measurement_columns = [
    c for c in df.columns
    if c.endswith("_min") or c.endswith("_max")
]

non_numeric = []

for col in measurement_columns:
    converted = pd.to_numeric(df[col], errors="coerce")

    invalid = df[col].notna() & converted.isna()

    if invalid.any():
        non_numeric.append((col, int(invalid.sum())))

if non_numeric:
    add_check(
        "Measurement data types",
        "WARNING",
        f"Non-numeric measurement values: {non_numeric}"
    )
else:
    add_check(
        "Measurement data types",
        "PASS",
        "All populated measurement values are numeric."
    )

# ==================================================
# 7. MEASUREMENT RANGE VALIDATION
# ==================================================

ranges = {
    "dissolved_oxygen": (0, 25),
    "ph": (0, 14),
    "bod": (0, 100),
    "conductivity": (0, 100000),
    "nitrate": (0, 1000),
    "fecal_coliform": (0, 100000000),
    "total_coliform": (0, 100000000)
}

range_issues = []

for parameter, (low, high) in ranges.items():

    for suffix in ["_min", "_max"]:

        col = parameter + suffix

        if col not in df.columns:
            continue

        values = pd.to_numeric(df[col], errors="coerce")

        invalid = (
            values.notna()
            & ~values.between(low, high)
        )

        count = int(invalid.sum())

        if count:
            range_issues.append((col, count))
            add_issue(
                "Measurement range",
                col,
                count
            )

add_check(
    "Preliminary measurement ranges",
    "WARNING" if range_issues else "PASS",
    f"Potential range violations: {range_issues}. "
    "These are plausibility checks, not scientific unit validation."
)

# ==================================================
# 8. STATE VALIDATION
# ==================================================

missing_states = int(
    df["state"].isna().sum()
)

unique_states = int(
    df["state"].nunique()
)

add_check(
    "State information",
    "PASS" if missing_states == 0 else "FAIL",
    f"Missing states: {missing_states}; unique state labels: {unique_states}. "
    "Labels still require geographic name harmonisation."
)

# ==================================================
# 9. YEAR-WISE VALIDATION
# ==================================================

year_summary = df.groupby(
    ["year", "category"]
).size().reset_index(name="records")

add_check(
    "Year-wise distribution",
    "PASS",
    f"Records distributed across {df['year'].nunique()} years."
)

# ==================================================
# 10. SOURCE TRACEABILITY
# ==================================================

trace_columns = [
    "source_file",
    "source_sheet",
    "source_row"
]

missing_trace_columns = [
    c for c in trace_columns if c not in df.columns
]

if not missing_trace_columns:

    trace_missing = int(
        df[trace_columns].isna().any(axis=1).sum()
    )

    add_check(
        "Source traceability",
        "PASS" if trace_missing == 0 else "FAIL",
        f"Records without complete source references: {trace_missing}"
    )

else:
    add_check(
        "Source traceability",
        "FAIL",
        f"Missing traceability columns: {missing_trace_columns}"
    )

# ==================================================
# 11. RAW SOURCE FILE VALIDATION
# ==================================================

raw_files = list(RAW.glob("*.xlsx"))

missing_sources = []

if "source_file" in df.columns:

    source_names = set(
        df["source_file"].dropna().astype(str)
    )

    raw_names = {f.name for f in raw_files}

    missing_sources = sorted(source_names - raw_names)

add_check(
    "Raw source availability",
    "PASS" if not missing_sources else "FAIL",
    f"Unmatched source files: {missing_sources}"
)

# ==================================================
# 12. GEOGRAPHIC READINESS
# ==================================================

if GADM.exists():

    try:
        import geopandas as gpd

        geo = gpd.read_file(GADM)

        add_check(
            "District boundary availability",
            "PASS",
            f"GADM boundary file loaded. Polygon records: {len(geo)}"
        )

        if "NAME_1" in geo.columns:
            district_column = (
                "NAME_2" if "NAME_2" in geo.columns else None
            )

            if district_column:
                add_check(
                    "District boundary attributes",
                    "PASS",
                    f"District attribute found: {district_column}"
                )
            else:
                add_check(
                    "District boundary attributes",
                    "WARNING",
                    "District-name attribute not identified."
                )

        add_check(
            "Station coordinate validation",
            "NOT VERIFIED",
            "NWMP station coordinates have not yet been "
            "geocoded and validated."
        )

    except Exception as e:

        add_check(
            "District boundary availability",
            "FAIL",
            str(e)
        )

else:

    add_check(
        "District boundary availability",
        "FAIL",
        "GADM GeoJSON file not found."
    )

# ==================================================
# 13. SCIENTIFIC VALIDATION STATUS
# ==================================================

add_check(
    "Measurement unit verification",
    "NOT VERIFIED",
    "Original measurement units must be checked against "
    "the source workbook headers and documentation."
)

add_check(
    "Source-to-output value verification",
    "NOT VERIFIED",
    "A row-level comparison against original Excel values "
    "is still required."
)

add_check(
    "WQI methodology",
    "NOT VERIFIED",
    "WQI standards, ideal values and parameter weights "
    "have not yet been finalized."
)

# ==================================================
# 14. SAVE REPORTS
# ==================================================

check_df = pd.DataFrame(checks)

issue_df = pd.DataFrame(
    issues,
    columns=["category", "description", "count"]
)

issue_df.to_csv(ISSUES, index=False)

with open(REPORT, "w", encoding="utf-8") as f:

    f.write("FINAL DATA QUALITY AUDIT REPORT\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"Total records: {len(df)}\n")
    f.write(f"Total columns: {len(df.columns)}\n")
    f.write(f"Unique states/UT labels: {unique_states}\n\n")

    f.write("VALIDATION RESULTS\n")
    f.write("-" * 60 + "\n")

    for _, row in check_df.iterrows():

        f.write(f"\n[{row['status']}] {row['check']}\n")
        f.write(f"    {row['details']}\n")

    f.write("\nYEAR-WISE DISTRIBUTION\n")
    f.write("-" * 60 + "\n")

    f.write(year_summary.to_string(index=False))

    f.write("\n\nOVERALL STATUS\n")
    f.write("-" * 60 + "\n")

    if "FAIL" in check_df["status"].values:
        f.write("FAIL: Critical validation issues need attention.\n")

    elif "NOT VERIFIED" in check_df["status"].values:
        f.write(
            "PARTIALLY VERIFIED: Some important checks remain pending.\n"
        )

    elif "WARNING" in check_df["status"].values:
        f.write("WARNING: Review outstanding data-quality warnings.\n")

    else:
        f.write("PASS: All implemented checks passed.\n")

# ==================================================
# 15. TERMINAL SUMMARY
# ==================================================

print("\n========== AUDIT RESULTS ==========")

print(check_df.to_string(index=False))

print("\nYear-wise distribution:")
print(year_summary.to_string(index=False))

print("\nTotal records:", len(df))
print("Missing cells:", missing_total)
print("Station-year duplicate rows:", station_duplicates)

print("\nReports generated:")
print(REPORT)
print(ISSUES)

print("\nOriginal datasets remain unchanged.")
print("========== AUDIT COMPLETE ==========")