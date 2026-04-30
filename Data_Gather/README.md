# 🌿 Bryophyte Portal — Data Gather CLI

A command-line tool that logs into the [Bryophyte Portal](https://bryophyteportal.org) and downloads specimen occurrence data (including image URLs) into a CSV file.

---

## Requirements

| Dependency | Install command |
|---|---|
| Python 3.11+ | (bundled with Anaconda) |
| `requests` | `pip install requests` |
| `beautifulsoup4` | `pip install beautifulsoup4` |
| `pandas` | `pip install pandas` |

> **Note:** You will also need a valid Bryophyte Portal account. Contact your collection manager if you don't have one.

---

## Files

| File | Purpose |
|---|---|
| `cli.py` | **Run this.** Interactive CLI entry point. |
| `htmltest.py` | Backend module — handles login, table parsing, image URL extraction. Do not run directly. |

---

## How to Run

Open a terminal, navigate to this folder, and run:

```bash
cd /path/to/Data_Gather
python cli.py
```

---

## Step-by-Step Walkthrough

### Step 1 — Login

The CLI will ask for your Bryophyte Portal username and password.  
Your password is **never shown on screen** (hidden as you type).

```
────────────────────────────────────────────
  Step 1 — Login
────────────────────────────────────────────
  Username: your_username
  Password:
  ✅  Login successful.
```

If your credentials are wrong, you get up to **3 attempts** before the program exits.

---

### Step 2 — Choose Your Data Options

You will be asked three questions:

#### 1. Table URL

```
  Use the default query URL? (Y/n):
```

- **Press Enter / type `Y`** — uses the built-in query (country field IS NULL)
- **Type `N`** — paste any custom URL from the Bryophyte Portal

**How to get a custom URL:**
1. Go to the portal and run your desired occurrence search
2. Copy the full URL from your browser's address bar
3. Paste it when prompted

#### 2. How Many Entries

```
  How many entries do you want from the table? (press Enter for all): 10
```

- Type a number (e.g. `10`) to get only the first N rows from the table
- Press **Enter** with no input to download all records

#### 3. Output Filename

```
  Save CSV as [specimen_data.csv]: my_results.csv
```

- Type a filename, or press **Enter** to use the default `specimen_data.csv`
- The `.csv` extension is added automatically if you forget it

---

### Step 3 — Confirm & Run

The CLI shows a summary before starting:

```
────────────────────────────────────────────
  Step 3 — Confirm & Run
────────────────────────────────────────────
  URL     : https://bryophyteportal.org/…
  Entries : 10
  Output  : my_results.csv

  Start scrape? (Y/n):
```

- Type `Y` to begin — the tool fetches the table, then visits each specimen's image tab to extract the image URL
- Type `N` to cancel without downloading anything

---

### Output

A CSV file is saved in the same folder as `cli.py`. It contains all occurrence table columns plus an **image URL** stored in the `Symbiota ID` column.

Example columns:

| Symbiota ID (Image URL) | Catalog Number | Scientific Name | Family | Country | … |
|---|---|---|---|---|---|
| https://fm-digital-assets… | C0020028F | Anastrophyllum minutum | Scapaniaceae | United States | … |

---

## Re-Running Without Logging In Again

After a successful data gather, the CLI asks:

```
  Run another data gather with the same session? (y/N):
```

Type `Y` to gather more data with a **different URL or limit** without having to log in again.

---

## Known Warnings

You may see this NumPy compatibility warning at startup — **it can be safely ignored**, the tool still runs correctly:

```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x…
```

To permanently silence it, you can downgrade NumPy:
```bash
pip install "numpy<2"
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Login failed` after 3 attempts | Double-check username/password on the portal website |
| `Could not find the occurrence table` | Make sure the URL is a valid occurrence table query — the error message lists all tables found on the page |
| `Redirected to login` | Your session expired; restart the CLI to log in again |
| Image URLs are empty | Some specimens may not have images uploaded to the portal |
| Output CSV has 0 rows | The query returned no results — try a broader search filter |
