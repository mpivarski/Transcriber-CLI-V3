#!/usr/bin/env python3
"""
cli.py — Bryophyte Portal CLI
==============================
Interactive command-line tool for logging into the Bryophyte Portal
and optionally gathering specimen data with image URLs.

Usage
-----
    python cli.py
"""

import sys
import getpass

from htmltest import (
    DEFAULT_TABLE_URL,
    create_session,
    login,
    fetch_table,
    fetch_image_urls,
    save_csv,
)

# ── Formatting helpers ────────────────────────────────────────────────────────

DIVIDER  = "─" * 56
THICK    = "═" * 56

def _header():
    print(f"\n{THICK}")
    print("  🌿  Bryophyte Portal  — Data Gather CLI")
    print(THICK)

def _section(title: str):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)

def _success(msg: str): print(f"  ✅  {msg}")
def _error(msg: str):   print(f"  ❌  {msg}")
def _info(msg: str):    print(f"  ℹ️   {msg}")
def _warn(msg: str):    print(f"  ⚠️   {msg}")


# ── Prompt helpers ────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    """Prompt the user; return default if they press Enter with no input."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


def _ask_yes_no(prompt: str, default: str = "y") -> bool:
    """Ask a yes/no question, return True for 'y'."""
    indicator = "(Y/n)" if default.lower() == "y" else "(y/N)"
    try:
        ans = input(f"  {prompt} {indicator}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if not ans:
        ans = default.lower()
    return ans == "y"


# ── Login flow ────────────────────────────────────────────────────────────────

MAX_LOGIN_ATTEMPTS = 3

def _do_login(session) -> bool:
    """
    Prompt for credentials and attempt login, retrying up to MAX_LOGIN_ATTEMPTS.
    Returns True when logged in, False if all attempts exhausted.
    """
    _section("Step 1 — Login")

    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        if attempt > 1:
            _warn(f"Attempt {attempt} of {MAX_LOGIN_ATTEMPTS}")

        username = _ask("Username")
        if not username:
            _error("Username cannot be empty.")
            continue

        try:
            password = getpass.getpass("  Password: ")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not password:
            _error("Password cannot be empty.")
            continue

        print()
        _info("Logging in…")
        ok, msg = login(session, username, password)

        if ok:
            _success(msg)
            return True
        else:
            _error(msg)
            if attempt < MAX_LOGIN_ATTEMPTS:
                print()

    _error(f"Login failed after {MAX_LOGIN_ATTEMPTS} attempts. Exiting.")
    return False


# ── Data gather flow ──────────────────────────────────────────────────────────

def _do_data_gather(session) -> None:
    """Walk the user through table URL, limit, filename, then run the scrape."""
    _section("Step 2 — Data Gather Options")

    # ── URL ──────────────────────────────────────────────────────────────────
    print()
    _info("Table URL")
    print(f"    Default: {DEFAULT_TABLE_URL[:1000]}…")
    print()
    use_default_url = _ask_yes_no("Use the default query URL?", default="y")

    if use_default_url:
        table_url = DEFAULT_TABLE_URL
    else:
        print()
        table_url = _ask("Paste your custom table URL")
        if not table_url:
            _warn("No URL provided — using default.")
            table_url = DEFAULT_TABLE_URL

    # ── Row count ─────────────────────────────────────────────────────────────
    print()
    _info("Table entries")

    row_limit: int | None = None
    while True:
        raw = _ask("How many entries do you want from the table? (press Enter for all)", default="")
        if not raw:
            break  # None → all rows
        try:
            row_limit = int(raw)
            if row_limit < 1:
                raise ValueError
            break
        except ValueError:
            _error("Please enter a positive whole number, or press Enter to get all rows.")

    # ── Output filename ───────────────────────────────────────────────────────
    print()
    _info("Output file")
    output_file = _ask("Save CSV as", default="specimen_data.csv")
    if not output_file.endswith(".csv"):
        output_file += ".csv"

    # ── Confirmation ─────────────────────────────────────────────────────────
    print()
    _section("Step 3 — Confirm & Run")
    print(f"  URL     : {table_url[:70]}…")
    print(f"  Entries : {'All' if row_limit is None else row_limit}")
    print(f"  Output  : {output_file}")
    print()

    if not _ask_yes_no("Start scrape?", default="y"):
        _info("Scrape cancelled.")
        return

    # ── Fetch table ───────────────────────────────────────────────────────────
    print()
    _info("Fetching occurrence table…")
    df, msg = fetch_table(session, table_url)

    if df is None:
        _error(msg)
        return

    _success(msg)

    # ── Slice to requested row count ──────────────────────────────────────────
    if row_limit is not None:
        df = df.head(row_limit)
        _info(f"Trimmed to first {row_limit} entries.")

    # ── Fetch image URLs ──────────────────────────────────────────────────────
    print()
    _info("Fetching image URLs (this may take a while)…")
    df = fetch_image_urls(session, df, limit=None)

    # ── Save ──────────────────────────────────────────────────────────────────
    try:
        save_csv(df, output_file)
        print()
        _success(f"Saved CSV → {output_file}")
    except Exception as exc:
        _error(f"Could not save file: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _header()

    session = create_session()

    # Login
    if not _do_login(session):
        sys.exit(1)

    # Data gather loop
    while True:
        print()
        if not _ask_yes_no("Do you want to gather data?", default="y"):
            print()
            _info("Goodbye! 🌿")
            print()
            break

        _do_data_gather(session)

        # Ask to run again
        print()
        if not _ask_yes_no("Run another data gather with the same session?", default="n"):
            print()
            _info("Goodbye! 🌿")
            print()
            break


if __name__ == "__main__":
    main()
