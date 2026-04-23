"""
bryophyte_portal.py  (was htmltest.py)
--------------------------------------
Reusable helper functions for interacting with the Bryophyte Portal.
This module is NOT meant to be run directly — import it from cli.py.
"""

import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ── URLs ──────────────────────────────────────────────────────────────────────

LOGIN_URL = "https://bryophyteportal.org/portal/profile/index.php"

DEFAULT_TABLE_URL = (
    "https://bryophyteportal.org/portal/collections/editor/occurrencetabledisplay.php"
)

IMAGE_TAB_URL = (
    "https://bryophyteportal.org/portal/collections/editor/includes/"
    "imagetab.php?occid={occid}&occindex=1&csmode=0&collid=1"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Session ───────────────────────────────────────────────────────────────────

def create_session() -> requests.Session:
    """Return a requests.Session pre-configured with browser-like headers."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


# ── Login ─────────────────────────────────────────────────────────────────────

def login(session: requests.Session, username: str, password: str) -> tuple[bool, str]:
    """
    Attempt to log into the Bryophyte Portal.

    Returns
    -------
    (True,  success_message)  on success
    (False, error_message)    on failure
    """
    # 1) Fetch login page to pick up any hidden form fields / cookies
    try:
        r = session.get(LOGIN_URL, timeout=15)
        r.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Could not reach login page: {exc}"

    # 2) Parse the login form for hidden inputs
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form", {"id": "loginform"})

    payload = {
        "login":    username,
        "password": password,
        "remember": "1",
        "refurl":   "",
        "resetpwd": "",
        "action":   "login",
    }

    # Include any hidden inputs from the form
    if form:
        for inp in form.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                payload[name] = inp.get("value", "")

    # 3) POST credentials
    try:
        resp = session.post(LOGIN_URL, data=payload, allow_redirects=True, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Login POST failed: {exc}"

    # 4) Detect outcome from response text
    lower = resp.text.lower()
    if any(kw in lower for kw in ["invalid username", "incorrect password", "login failed"]):
        return False, "Invalid username or password."
    if any(kw in lower for kw in ["logout", "log out", "my profile"]):
        return True, "Login successful."
    # Ambiguous — treat as failure
    return False, "Could not confirm login. The site may have changed or require 2-FA."


# ── Table fetch ───────────────────────────────────────────────────────────────

def fetch_table(session: requests.Session, table_url: str) -> tuple[pd.DataFrame | None, str]:
    """
    Fetch the occurrence table page and parse it into a DataFrame.

    Returns
    -------
    (DataFrame, message)  on success
    (None,      message)  on failure
    """
    try:
        resp = session.get(table_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return None, f"Failed to fetch table page: {exc}"

    # Redirected back to login?
    if "profile/index.php" in resp.url and "refurl" in resp.url:
        return None, "Redirected to login — session may have expired."

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try multiple selectors — the portal uses different table identifiers
    # depending on the query / page variant.
    matched_by = ""

    # 1) Original editor table
    target = soup.find("table", {"id": "defaulttable"})
    if target:
        matched_by = "id='defaulttable'"

    # 2) Main occurrence table view (seen in browser devtools screenshot)
    if not target:
        target = soup.find("table", {"title": "Occurrence Table View"})
        if target:
            matched_by = "title='Occurrence Table View'"

    # 3) aria-describedby containing "dynamictable" (DataTables variant)
    if not target:
        for tbl in soup.find_all("table"):
            aria = tbl.get("aria-describedby", "")
            if "dynamictable" in aria:
                target = tbl
                matched_by = f"aria-describedby='{aria}'"
                break

    # 4) Any table that carries the DataTables CSS class
    if not target:
        target = soup.find("table", class_="dataTable")
        if target:
            matched_by = "class='dataTable'"

    if not target:
        all_tables = soup.find_all("table")
        table_info = ", ".join(
            f"id='{t.get('id', '')}' class='{' '.join(t.get('class', []))}'"
            for t in all_tables
        ) or "none"
        return None, (
            "Could not find the occurrence table. "
            f"Tables on page: [{table_info}]"
        )

    print(f"  📋 Table located via {matched_by}")

    # Headers
    headers = []
    thead = target.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
    if not headers:
        first_row = target.find("tr")
        if first_row:
            headers = [c.get_text(strip=True) for c in first_row.find_all(["th", "td"])]

    # Rows
    tbody = target.find("tbody")
    rows = tbody.find_all("tr") if tbody else target.find_all("tr")[1:]
    data_rows = [
        [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        for row in rows
        if row.find_all(["td", "th"])
    ]

    if not data_rows:
        return None, "Table found but contained no data rows."

    # Align headers / columns
    if len(headers) != len(data_rows[0]):
        headers = [f"Column_{i}" for i in range(len(data_rows[0]))]

    df = pd.DataFrame(data_rows, columns=headers)
    return df, f"Loaded {len(df)} rows × {len(df.columns)} columns."


# ── Image URL extraction ──────────────────────────────────────────────────────

def fetch_image_urls(
    session: requests.Session,
    df: pd.DataFrame,
    limit: int | None = None,
    progress_every: int = 50,
) -> pd.DataFrame:
    """
    Enrich *df* with an 'Image_URL' column by visiting each specimen's image tab.

    Parameters
    ----------
    limit          : max records to process (None = all)
    progress_every : print a progress line every N records
    """
    total = len(df) if limit is None else min(limit, len(df))
    df = df.copy()
    df["Image_URL"] = ""

    print(f"\n  Processing {total} specimen(s) for image URLs…")

    for idx, row in df.head(total).iterrows():
        occid = row.get("Symbiota ID", "")

        if not occid or pd.isna(occid):
            continue

        url = IMAGE_TAB_URL.format(occid=occid)

        try:
            img_resp = session.get(url, timeout=15)
            img_resp.raise_for_status()
            img_soup = BeautifulSoup(img_resp.text, "html.parser")

            web_url = ""

            # Method 1: anchor with fieldmuseum.org JPG
            for a_tag in img_soup.find_all("a", href=True):
                href = a_tag["href"]
                if "fm-digital-assets.fieldmuseum.org" in href and href.endswith(".jpg"):
                    web_url = href
                    break

            # Method 2: "Web URL:" label → next anchor
            if not web_url:
                for b_tag in img_soup.find_all("b"):
                    if "Web URL" in b_tag.get_text():
                        next_a = b_tag.find_next("a", href=True)
                        if next_a:
                            web_url = next_a.get("href", "")
                        break

            df.at[idx, "Image_URL"] = web_url

            if (idx + 1) % progress_every == 0:
                print(f"    → {idx + 1}/{total} processed")

            time.sleep(0.1)

        except Exception as exc:
            print(f"    ⚠  Error for occid {occid}: {exc}")

    found = df["Image_URL"].apply(lambda x: bool(x)).sum()
    print(f"  Found image URLs for {found}/{total} specimens.")
    return df


# ── CSV export ────────────────────────────────────────────────────────────────

def save_csv(df: pd.DataFrame, output_path: str) -> None:
    """Swap Image_URL into Symbiota ID column and write CSV."""
    df = df.copy()
    if "Image_URL" in df.columns:
        df["Symbiota ID"] = df["Image_URL"]
        df.drop(columns=["Image_URL"], inplace=True)
    df.to_csv(output_path, index=False)