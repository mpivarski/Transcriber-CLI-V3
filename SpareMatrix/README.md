# 🌿 Sparse Matrix Builder — Pipeline Step 4

`sparse_matrix.py` compares two CSV files — an **original** specimen CSV and an **LLM-enriched** CSV — and produces a **sparse change matrix**: a new CSV containing only the rows and fields that were added or modified by the LLM.

This is designed for museum specimen digitization workflows where an LLM fills in missing fields (collector names, dates, geographic info, etc.) and a human curator must review and import only the changed data.

---

## Requirements

```bash
pip install pandas
```

Python 3.9+ recommended.

---

## How to Run

### Interactive mode (recommended for first-time use)

```bash
python sparse_matrix.py
```

You will be prompted for three things:

```
Path to original CSV (first file) [bryo.csv]: testData/no_countryThirdHundred.csv
Path to modified CSV (second file) [rileytwoshot.csv]: testData/4_30_300sMP_second_shot.csv
Output filename [sparse_changes.csv]: myOutput.csv
```

| Prompt | What to enter |
|---|---|
| **Original CSV** | The unmodified specimen export from the portal (the "before") |
| **Modified CSV** | The LLM-enriched CSV (the "after") |
| **Output filename** | Name of the sparse change matrix to write |

### Command-line flags (for scripting / batch runs)

```bash
python sparse_matrix.py \
  --bryo  testData/no_countryThirdHundred.csv \
  --riley testData/4_30_300sMP_second_shot.csv \
  --out   sparse_changes.csv
```

| Flag | Description |
|---|---|
| `--bryo FILE` | Path to the original CSV |
| `--riley FILE` | Path to the LLM-modified CSV |
| `--out FILE` | Output filename (default: `sparse_changes.csv`) |
| `--no-interactive` | Fail instead of prompting if paths are missing |

---

## What the Output Contains

The output CSV has the **same columns as the original CSV** plus a few portal-required fields and one metadata column:

| Column | Description |
|---|---|
| `Catalog Number` | Join key — always present |
| *(shared columns)* | Only non-empty if the LLM changed the value vs. the original |
| `stateProvince` | Added from LLM if present |
| `county` | Added from LLM if present |
| `municipality` | Added from LLM if present |
| `locationRemarks` | Verbatim locality from LLM |
| `typeStatus` | Added from LLM if present |
| **`dataGeneralizations`** | ⚠️ LLM provenance note (see below) |

### The `dataGeneralizations` Column

Every row in the output includes a `dataGeneralizations` note in the last column. This column:

- Flags the record as **LLM-generated and requiring human verification**
- Lists the **exact field names** that the LLM populated for that specific record

**Example value:**
```
LLM-generated data — requires human verification. Fields added by LLM: Collector, Event Date, Country, stateProvince, locationRemarks
```

> ⚠️ Only fields that survived data cleaning are listed. Fields that the LLM filled with placeholder values (e.g. `[precise locality unknown]`) are automatically removed and will NOT appear in this list.

---

## Data Cleaning Applied Automatically

Before writing the output, the script blanks out known bad values:

| Field | Values removed |
|---|---|
| `Locality`, `locationRemarks`, `stateProvince`, `county` | `[precise locality unknown]`, `Precise locality unknown` |
| `typeStatus` | `no type status`, `No type status` |
| `Collector Number` | `s.n.`, `S.N.`, `S.n.` |
| Any field | `unsure and check`, `Unsure and check` |

Rows that become completely empty after cleaning are dropped from the output.

---

## Column Mapping (Original CSV ↔ LLM CSV)

The two CSVs may use different column names. The script handles this automatically:

| LLM CSV column | Original CSV column |
|---|---|
| `collectedBy` | `Collector` |
| `recordNumber` | `Collector Number` |
| `secondaryCollectors` | `Associated Collectors` |
| `minimumEventDate` | `Event Date` |
| `verbatimEventDate` | `Verbatim Date` |
| `identifiedBy` | `Identified By` |
| `country` | `Country` |
| `locality` | `Locality` |
| `habitat` | `Habitat` |
| `verbatimElevation` | `Elev. Min. (m)` |
| `associatedTaxa` | `Associated Taxa` |
| `GlobalNamesVerifiedLatestScientificName` | `Scientific Name` |

---

## Join Key Detection

The script auto-detects the join key from these candidates (in order of preference):

1. `Catalog Number`
2. `Barcode`
3. `otherCatalogNumbers`

Both CSVs must share at least one of these columns.

---

## Example Workflow

```
testData/
  no_countryThirdHundred.csv   ← original portal export (100 rows)
  4_30_300sMP_second_shot.csv  ← LLM-enriched CSV (99 rows)

→ run sparse_matrix.py
→ output: sparse_changes.csv   ← 98 rows with changes only + dataGeneralizations
```

The output is ready to review and import into the Bryophyte Portal.

---

## File Structure

```
SpareMatrix/
├── sparse_matrix.py         # Main script (Pipeline Step 4)
├── README.md                # This file
├── CSV_Instructions/        # Field mapping rules and import instructions
│   └── FOR ROOSEVELT CLASS IMPORTED_Cleaned_batch37A_43 - Fields ADDED.csv
├── testData/                # Sample input CSVs for testing
│   ├── no_countryThirdHundred.csv
│   └── 4_30_300sMP_second_shot.csv
└── sparse_changes_300s.csv  # Example output
```
