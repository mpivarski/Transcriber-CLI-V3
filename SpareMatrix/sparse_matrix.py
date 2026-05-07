#!/usr/bin/env python3
"""
sparse_matrix.py  —  Pipeline Step 4
======================================
Compares two CSV files (an original first CSV and a modified second CSV)
and produces a sparse matrix CSV containing only the *changes* —
values that were added or modified in the second CSV relative to the first.

Workflow
--------
1.  Load the original CSV and the modified CSV.
2.  Auto-detect the join key (Catalog Number, Barcode, or otherCatalogNumbers).
3.  Match rows between the two files using the join key.
4.  For every matched row, compare each column:
      • If a cell in the second CSV differs from the first → keep the new value.
      • If a cell is identical or both are empty → leave it blank.
5.  For rows that exist only in the second CSV (new records), bring in all
    their values as additions.
6.  The output CSV has the same columns as the FIRST (original) CSV.
7.  Only rows that have a non-empty join key (Catalog Number / Barcode) AND
    at least one real changed value are included.

Usage
-----
    python sparse_matrix.py                      # interactive prompts
    python sparse_matrix.py --bryo bryo.csv \\
                             --riley rileytwoshot.csv \\
                             --out sparse_changes.csv

Requirements
------------
    pip install pandas
"""

import argparse
import sys
import os
import re
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("❌  pandas is not installed. Run:  pip install pandas")
    sys.exit(1)

# ── Column-name constants ──────────────────────────────────────────────────────

# Possible join key names (checked in order of preference)
JOIN_KEY_CANDIDATES = ["Catalog Number", "Barcode", "otherCatalogNumbers"]

# Known column aliases: second_csv_name → first_csv_name (for cols SHARED with original CSV)
# Per CSV_Instructions Metadata.csv field mapping requirements.
COLUMN_ALIASES = {
    # Use GlobalNames-verified scientific name (latestScientificName is excluded per instructions)
    "GlobalNamesVerifiedLatestScientificName": "Scientific Name",
    "collectedBy":            "Collector",
    "recordNumber":           "Collector Number",
    "secondaryCollectors":    "Associated Collectors",
    "minimumEventDate":       "Event Date",
    "verbatimEventDate":      "Verbatim Date",
    "identifiedBy":           "Identified By",
    "country":                "Country",
    "locality":               "Locality",
    "habitat":                "Habitat",
    "verbatimElevation":      "Elev. Min. (m)",
    "verbatimCoordinates":    "Verbatim Coordinates",
    "associatedTaxa":         "Associated Taxa",
}

# Portal fields NOT in the original bryo CSV but required for a complete skeletal upload.
# Per CSV_Instructions Metadata.csv: stateProvince, county, municipality, locationRemarks, typeStatus.
PORTAL_EXTRA_COLUMNS = {
    "firstPoliticalUnit":  "stateProvince",
    "secondPoliticalUnit": "county",
    "municipality":        "municipality",
    "verbatimLocality":    "locationRemarks",
    "typeStatus":          "typeStatus",
}

# Values that should be treated as "empty" / no data
EMPTY_VALUES = {"", "N/A", "n/a", "NA", "na", "none", "None"}

# ── Cleaning rules (CSV_Instructions / Fields removed for bryophyte import) ────
# Per-field: exact strings to blank out
FIELD_CLEANING_RULES: dict[str, list[str]] = {
    "Locality":         ["[precise locality unknown]", "Precise locality unknown",
                         "[Precise locality unknown]"],
    "locationRemarks":  ["[precise locality unknown]", "Precise locality unknown",
                         "[Precise locality unknown]"],
    "stateProvince":    ["[precise locality unknown]"],
    "county":           ["[precise locality unknown]"],
    "typeStatus":       ["no type status", "No type status", "No Type Status"],
    "Collector Number": ["s.n.", "S.N.", "S.n."],
    "recordNumber":     ["s.n.", "S.N.", "S.n."],
}

# Substrings to strip from ANY field
STRIP_ANYWHERE = ["unsure and check", "Unsure and check"]

# ── Helpers ────────────────────────────────────────────────────────────────────

DIVIDER = "─" * 60
THICK   = "═" * 60


def _hdr(title: str) -> None:
    print(f"\n{THICK}\n  {title}\n{THICK}")
def _sec(title: str) -> None:
    print(f"\n{DIVIDER}\n  {title}\n{DIVIDER}")
def _ok(msg: str)   -> None: print(f"  ✅  {msg}")
def _err(msg: str)  -> None: print(f"  ❌  {msg}")
def _info(msg: str) -> None: print(f"  ℹ️   {msg}")
def _warn(msg: str) -> None: print(f"  ⚠️   {msg}")
def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default
def _normalize(val) -> str:
    """Lower-case, strip whitespace, collapse inner spaces."""
    if pd.isna(val):
        return ""
    s = str(val).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s
def _is_empty(val) -> bool:
    """Check if a value is considered empty / no data."""
    return str(val).strip() in EMPTY_VALUES
def clean_output_df(df: pd.DataFrame, join_col: str) -> pd.DataFrame:
    """
    Apply data cleaning rules from CSV_Instructions:
      • Remove '[precise locality unknown]' from Locality / locationRemarks / geo fields
      • Remove 'no type status' from typeStatus
      • Remove 's.n.' from Collector Number
      • Strip 'unsure and check' from any field
      • Blank out residual N/A-like values
      • Drop rows that become data-empty after cleaning
    """
    _sec("Applying Cleaning Rules (from CSV_Instructions)")
    cleaned_cells = 0

    for col in df.columns:
        if col == join_col:
            continue

        # Per-field exact-match blanking
        if col in FIELD_CLEANING_RULES:
            for bad_val in FIELD_CLEANING_RULES[col]:
                mask = df[col].str.strip().str.lower() == bad_val.lower()
                count = int(mask.sum())
                if count:
                    df.loc[mask, col] = ""
                    cleaned_cells += count
                    _info(f"Cleared '{bad_val}' from '{col}' ({count} cells)")

        # Substring strip from any field
        for bad_str in STRIP_ANYWHERE:
            mask = df[col].str.contains(bad_str, case=False, na=False)
            count = int(mask.sum())
            if count:
                df.loc[mask, col] = (
                    df.loc[mask, col]
                    .str.replace(bad_str, "", case=False, regex=False)
                    .str.strip()
                )
                cleaned_cells += count
                _info(f"Stripped '{bad_str}' from '{col}' ({count} cells)")

        # Blank residual N/A-like values
        mask = df[col].str.strip().isin(EMPTY_VALUES)
        df.loc[mask, col] = ""

    _ok(f"Cleaning complete — {cleaned_cells} cells cleared/modified")

    # Drop rows that are now all-empty (only the join key remains)
    data_cols = [c for c in df.columns if c != join_col]
    all_empty = df[data_cols].apply(
        lambda row: all(str(v).strip() == "" for v in row), axis=1
    )
    dropped = int(all_empty.sum())
    if dropped:
        df = df[~all_empty].reset_index(drop=True)
        _info(f"Dropped {dropped} rows that became empty after cleaning")

    return df


def add_data_generalizations(df: pd.DataFrame, join_col: str) -> pd.DataFrame:
    """
    Append a 'dataGeneralizations' column as the LAST column.

    Must be called AFTER clean_output_df so that the listed fields reflect
    only the values that actually survived cleaning.
    Each non-empty, non-join-key column in a row is listed as a field
    added by the LLM.
    """
    _sec("Adding dataGeneralizations Column")

    skip_cols = {join_col, "dataGeneralizations"}

    def _build_note(row: pd.Series) -> str:
        added = [
            col for col in df.columns
            if col not in skip_cols and str(row[col]).strip() != ""
        ]
        if not added:
            return ""
        return (
            "LLM-generated data — requires human verification. "
            f"Fields added by LLM: {', '.join(added)}"
        )

    df["dataGeneralizations"] = df.apply(_build_note, axis=1)
    filled = (df["dataGeneralizations"].str.strip() != "").sum()
    _ok(f"dataGeneralizations populated for {filled:,} rows")
    return df


# ── Core logic ─────────────────────────────────────────────────────────────────

def detect_join_key(df: pd.DataFrame, label: str) -> str:
    """Auto-detect which join key column exists in the DataFrame."""
    df.columns = [c.strip() for c in df.columns]
    for candidate in JOIN_KEY_CANDIDATES:
        if candidate in df.columns:
            return candidate
    _err(
        f"Could not find a join key in {label}.\n"
        f"  Expected one of: {JOIN_KEY_CANDIDATES}\n"
        f"  Found: {list(df.columns)}"
    )
    sys.exit(1)


def load_csv(path: str, label: str) -> tuple[pd.DataFrame, str]:
    """Load a CSV and detect its join key."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    join_col = detect_join_key(df, label)
    df[join_col] = df[join_col].str.strip()
    _ok(f"Loaded {label}  — {len(df):,} rows, {len(df.columns)} columns  (join on '{join_col}')")
    return df, join_col


def _build_column_map(first_cols: list[str], second_cols: list[str]) -> dict[str, str]:
    """
    Build a mapping from second CSV column names → first CSV column names.

    If both files share columns directly, those are mapped 1:1.
    Otherwise, known aliases are used as fallback.
    """
    first_set = set(first_cols)
    mapping = {}

    for scol in second_cols:
        # Direct match — same column name in both files
        if scol in first_set:
            mapping[scol] = scol
        # Alias match — different schema
        elif scol in COLUMN_ALIASES and COLUMN_ALIASES[scol] in first_set:
            mapping[scol] = COLUMN_ALIASES[scol]
        # Skip "Verified" prefixed columns
        elif scol.startswith("Verified"):
            continue

    return mapping


def build_sparse_matrix(
    first_df:    pd.DataFrame,
    first_join:  str,
    second_df:   pd.DataFrame,
    second_join: str,
) -> tuple[pd.DataFrame, dict]:
    """
    Compare the two DataFrames row-by-row using the join key.
    Produce a sparse DataFrame with the same columns as first_df,
    containing only the CHANGED or ADDED values from second_df.

    When both files have the same number of rows and the same join keys
    in the same order, rows are compared positionally (index-to-index).
    This correctly handles duplicate join keys.

    Only rows with a non-empty join key and at least one real change
    are included.
    """

    first_cols = list(first_df.columns)

    # Build column mapping:  second_col → first_col
    col_map = _build_column_map(first_cols, list(second_df.columns))

    # Also map the join keys to each other if they differ
    if second_join != first_join and second_join not in col_map:
        col_map[second_join] = first_join

    _info(f"Mapped {len(col_map)} columns between the two CSVs")

    # Determine comparison strategy:
    #   If both CSVs have the same row count, compare positionally (row by row).
    #   Otherwise, fall back to key-based matching.
    same_structure = (len(first_df) == len(second_df))
    if same_structure:
        _info("Same row count — using positional (row-by-row) comparison")
    else:
        _info("Different row counts — using key-based comparison")
        # Build index for key-based lookup
        first_indexed = first_df.set_index(first_join)
        first_indexed = first_indexed[~first_indexed.index.duplicated(keep="first")]

    # Statistics
    stats = {
        "matched_rows": 0,
        "new_rows": 0,
        "changed_cells": 0,
        "skipped_no_id": 0,
        "skipped_no_changes": 0,
    }

    # Extended output columns = original cols + portal extra cols
    # (dataGeneralizations is appended after cleaning — see add_data_generalizations)
    extra_portal_cols = [c for c in PORTAL_EXTRA_COLUMNS.values() if c not in first_cols]
    extended_cols = first_cols + extra_portal_cols

    sparse_rows = []

    for idx, second_row in second_df.iterrows():
        catalog_num = str(second_row.get(second_join, "")).strip()

        # Skip rows without a join key
        if not catalog_num or catalog_num in EMPTY_VALUES:
            stats["skipped_no_id"] += 1
            continue

        # Start with an empty row using ALL output columns (original + portal extras)
        sparse_row = {col: "" for col in extended_cols}
        sparse_row[first_join] = catalog_num

        change_count = 0
        first_row = None

        if same_structure and idx < len(first_df):
            # ── Positional match: compare same row index ───────────────────
            first_row = first_df.iloc[idx]
            stats["matched_rows"] += 1
        elif not same_structure:
            # ── Key-based match ────────────────────────────────────────────
            if catalog_num in first_indexed.index:
                first_row = first_indexed.loc[catalog_num]
                stats["matched_rows"] += 1

        if first_row is not None:
            # Compare cell by cell for shared columns
            for second_col, first_col in col_map.items():
                if second_col == second_join or first_col == first_join:
                    continue
                second_val = str(second_row.get(second_col, "")).strip()
                first_val  = str(first_row.get(first_col, "")).strip()
                if _is_empty(second_val):
                    continue
                if _normalize(second_val) != _normalize(first_val):
                    sparse_row[first_col] = second_val
                    change_count += 1
                    stats["changed_cells"] += 1

            # Always pull portal extra columns if non-empty (new fields for existing records)
            for second_col, portal_col in PORTAL_EXTRA_COLUMNS.items():
                if second_col == second_join:
                    continue
                second_val = str(second_row.get(second_col, "")).strip()
                if not _is_empty(second_val):
                    sparse_row[portal_col] = second_val
                    change_count += 1
                    stats["changed_cells"] += 1
        else:
            # ── New row (not in original): bring in all values ─────────────
            stats["new_rows"] += 1
            for second_col, first_col in col_map.items():
                if second_col == second_join or first_col == first_join:
                    continue
                second_val = str(second_row.get(second_col, "")).strip()
                if not _is_empty(second_val):
                    sparse_row[first_col] = second_val
                    change_count += 1
            for second_col, portal_col in PORTAL_EXTRA_COLUMNS.items():
                if second_col == second_join:
                    continue
                second_val = str(second_row.get(second_col, "")).strip()
                if not _is_empty(second_val):
                    sparse_row[portal_col] = second_val
                    change_count += 1

        # Only include the row if there is at least one actual change
        if change_count > 0:
            sparse_rows.append(sparse_row)
        else:
            stats["skipped_no_changes"] += 1

    # Build the sparse DataFrame with extended columns
    sparse_df = pd.DataFrame(sparse_rows, columns=extended_cols)

    # Final filter: only keep rows where the join key is non-empty
    sparse_df = sparse_df[sparse_df[first_join].str.strip() != ""]

    # Drop columns that are entirely empty
    non_empty_cols = [col for col in sparse_df.columns
                      if (sparse_df[col].str.strip() != "").any()]
    dropped = len(sparse_df.columns) - len(non_empty_cols)
    sparse_df = sparse_df[non_empty_cols]
    if dropped > 0:
        _info(f"Dropped {dropped} empty columns from output")

    return sparse_df, stats


def print_summary(sparse_df: pd.DataFrame, stats: dict, join_col: str) -> None:
    _sec("Summary")
    print(f"  Rows matched to original             : {stats['matched_rows']:,}")
    print(f"  New rows (not in original)            : {stats['new_rows']:,}")
    print(f"  Total changed/added cells             : {stats['changed_cells']:,}")
    print(f"  Rows skipped (no {join_col:17s})  : {stats['skipped_no_id']:,}")
    print(f"  Rows skipped (no changes)             : {stats['skipped_no_changes']:,}")
    print(f"  Rows in output sparse matrix          : {len(sparse_df):,}")

    if len(sparse_df) > 0:
        # Show how many non-empty cells per column
        _sec("Non-empty cells per column in output")
        for col in sparse_df.columns:
            count = (sparse_df[col].str.strip() != "").sum()
            if count > 0:
                print(f"    {col:40s} : {count:,}")
# ── CLI / interactive entry point ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Step 4 — Build sparse change-matrix from two CSVs",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--bryo",  metavar="FILE", help="Path to original CSV (first file)")
    p.add_argument("--riley", metavar="FILE", help="Path to modified CSV (second file)")
    p.add_argument("--out",   metavar="FILE", help="Output sparse matrix CSV filename",
                   default="sparse_changes.csv")
    p.add_argument("--no-interactive", action="store_true",
                   help="Fail instead of prompting if paths are missing")
    return p.parse_args()


def resolve_paths(args: argparse.Namespace) -> tuple[str, str, str]:
    """Return (first_path, second_path, out_path), prompting if needed."""
    bryo  = args.bryo
    riley = args.riley
    out   = args.out

    if args.no_interactive:
        missing = []
        if not bryo:  missing.append("--bryo")
        if not riley: missing.append("--riley")
        if missing:
            _err(f"Missing required arguments: {', '.join(missing)}")
            sys.exit(1)
    else:
        if not bryo:
            _sec("Input Files")
            bryo = _ask("Path to original CSV (first file)", default="bryo.csv")
        if not riley:
            riley = _ask("Path to modified CSV (second file)",
                         default="rileytwoshot.csv")
        if out == "sparse_changes.csv":
            out = _ask("Output filename", default="sparse_changes.csv")

    # Validate
    for label, path in [("original CSV", bryo), ("modified CSV", riley)]:
        if not os.path.isfile(path):
            _err(f"File not found: {path}  ({label})")
            sys.exit(1)

    return bryo, riley, out


def main() -> None:
    _hdr("🌿  Sparse Matrix Builder  —  Pipeline Step 4")

    args  = parse_args()
    first_path, second_path, out_path = resolve_paths(args)

    _sec("Loading Data")
    first_df,  first_join  = load_csv(first_path,  "original CSV (first file)")
    second_df, second_join = load_csv(second_path, "modified CSV (second file)")

    _sec("Building Sparse Change Matrix")
    sparse_df, stats = build_sparse_matrix(first_df, first_join, second_df, second_join)

    # Apply all cleaning rules from CSV_Instructions
    sparse_df = clean_output_df(sparse_df, first_join)

    # Add dataGeneralizations AFTER cleaning so only surviving fields are listed
    sparse_df = add_data_generalizations(sparse_df, first_join)

    print_summary(sparse_df, stats, first_join)

    _sec("Saving Output")
    sparse_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    _ok(f"Sparse matrix saved → {out_path}")
    _info(f"  Rows    : {len(sparse_df):,}")
    _info(f"  Columns : {len(sparse_df.columns):,}  (same as original CSV)")

    print(f"\n{THICK}")
    print("  Done! 🌿")
    print(THICK)


if __name__ == "__main__":
    main()
