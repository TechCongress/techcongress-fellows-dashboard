"""
sync_status_reports.py — Standalone monthly status report sync

Run this script on the 1st of each month to automatically log whether fellows
submitted their monthly status report on time, based on Google Form responses.

Usage:
    python sync_status_reports.py               # syncs previous month
    python sync_status_reports.py 2026 3        # syncs a specific year/month

Credentials are read from .streamlit/secrets.toml (same file the Streamlit app uses).
The script does NOT depend on Streamlit — it reads the secrets file directly.

Output: prints a summary to stdout and exits 0 on success, 1 on error.
"""

import sys
import calendar
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ── Load secrets from .streamlit/secrets.toml ────────────────────────────────

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"

try:
    import tomllib  # stdlib in Python 3.11+
    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli (for older Python)
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    except ImportError:
        print("ERROR: Python 3.11+ required (or install 'tomli' for older versions).")
        sys.exit(1)
except FileNotFoundError:
    print(f"ERROR: Secrets file not found at {SECRETS_PATH}")
    print("Make sure .streamlit/secrets.toml exists and is filled in.")
    sys.exit(1)


# ── Google Sheets connection (no Streamlit) ───────────────────────────────────

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

creds = Credentials.from_service_account_info(
    dict(secrets["gcp_service_account"]),
    scopes=SCOPES,
)
client      = gspread.authorize(creds)
spreadsheet = client.open_by_key(secrets["gsheets"]["spreadsheet_id"])

FELLOWS_SHEET        = "Fellows"
REPORTS_SHEET        = "Status Reports"
FORM_RESPONSES_SHEET = "Form Responses 1"


def _ws(name: str) -> gspread.Worksheet:
    return spreadsheet.worksheet(name)


def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().upper() in ("TRUE", "1", "YES")


# ── Timezone setup ────────────────────────────────────────────────────────────

try:
    import pytz
    EST = pytz.timezone("America/New_York")
    def _localize(dt):
        return EST.localize(dt)
    def _to_est(dt):
        return dt.astimezone(EST)
except ImportError:
    from datetime import timezone, timedelta
    print("WARNING: pytz not installed. Using fixed UTC-5 offset (no DST correction).")
    _EST_OFFSET = timezone(timedelta(hours=-5))
    def _localize(dt):
        return dt.replace(tzinfo=_EST_OFFSET)
    def _to_est(dt):
        return dt.astimezone(_EST_OFFSET)


# ── Core sync logic ───────────────────────────────────────────────────────────

def sync(year: int, month: int) -> dict:
    """
    Sync status report submissions from the form responses sheet for the
    given year and month.

    Returns:
      synced             — list of {fellow_name, month, on_time, date_submitted}
      flagged_duplicates — list of {email, name, count}
      unmatched          — list of {email, first_name, last_name}
      errors             — list of error strings
    """
    result = {"synced": [], "flagged_duplicates": [], "unmatched": [], "errors": []}

    last_day    = calendar.monthrange(year, month)[1]
    deadline    = _localize(datetime(year, month, last_day, 23, 59, 59))
    month_label = datetime(year, month, 1).strftime("%b %Y")

    print(f"\nSyncing status reports for {month_label}")
    print(f"Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # 1. Read form responses
    try:
        rows = _ws(FORM_RESPONSES_SHEET).get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to read form responses: {e}")
        return result

    # 2. Parse timestamps, filter to target month
    def _parse_ts(ts_str: str):
        for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%-m/%-d/%Y %H:%M:%S"):
            try:
                return _localize(datetime.strptime(ts_str.strip(), fmt))
            except ValueError:
                continue
        return None

    month_responses = []
    for row in rows:
        ts = _parse_ts(str(row.get("Timestamp", "")))
        if ts and ts.year == year and ts.month == month:
            month_responses.append({
                "email":      str(row.get("Email Address", "")).strip().lower(),
                "first_name": str(row.get("First Name", "")).strip(),
                "last_name":  str(row.get("Last Name", "")).strip(),
                "timestamp":  ts,
                "on_time":    ts <= deadline,
            })

    print(f"Found {len(month_responses)} form response(s) for {month_label}")

    if not month_responses:
        result["errors"].append(f"No form responses found for {month_label}.")
        return result

    # 3. Detect duplicates; keep earliest submission per email
    by_email = defaultdict(list)
    for r in month_responses:
        by_email[r["email"]].append(r)

    for email, responses in by_email.items():
        if len(responses) > 1:
            r = responses[0]
            result["flagged_duplicates"].append({
                "email": email,
                "name":  f"{r['first_name']} {r['last_name']}",
                "count": len(responses),
            })

    deduped = {
        email: sorted(rs, key=lambda r: r["timestamp"])[0]
        for email, rs in by_email.items()
    }

    # 4. Build fellow lookup indexes
    try:
        fellows_rows = _ws(FELLOWS_SHEET).get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to fetch fellows: {e}")
        return result

    fellows = [
        {
            "id":    str(r.get("ID", "")),
            "name":  str(r.get("Name", "")),
            "email": str(r.get("Email", "")),
        }
        for r in fellows_rows
    ]
    email_to_fellow = {f["email"].strip().lower(): f for f in fellows if f.get("email")}
    name_to_fellow  = {f["name"].strip().lower():  f for f in fellows if f.get("name")}

    # 5. Load existing Status Report records
    try:
        all_reports = _ws(REPORTS_SHEET).get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to fetch status reports: {e}")
        return result

    # (fellow_id, month_label) → existing report ID
    existing = {
        (str(r.get("Fellow ID", "")), str(r.get("Month", ""))): str(r.get("ID", ""))
        for r in all_reports
    }

    # 6. Match each submission and upsert a Status Report record
    ws_reports = _ws(REPORTS_SHEET)

    for email, response in deduped.items():
        # Primary: email match
        fellow = email_to_fellow.get(email)

        # Fallback: full name match
        if not fellow:
            full_name = f"{response['first_name']} {response['last_name']}".strip().lower()
            fellow = name_to_fellow.get(full_name)

        if not fellow:
            result["unmatched"].append({
                "email":      response["email"],
                "first_name": response["first_name"],
                "last_name":  response["last_name"],
            })
            continue

        fellow_id      = fellow["id"]
        fellow_name    = fellow["name"]
        date_submitted = _to_est(response["timestamp"]).strftime("%Y-%m-%d")
        on_time        = response["on_time"]
        notes          = "" if on_time else "⚠️ Submitted after month-end deadline (11:59 PM EST)"

        key = (fellow_id, month_label)
        try:
            if key in existing:
                # Update existing record: find row by ID and update Submitted + Date Submitted
                report_id = existing[key]
                cell = ws_reports.find(report_id, in_column=1)
                if cell:
                    ws_reports.update_cell(cell.row, 5, "TRUE")           # E: Submitted
                    ws_reports.update_cell(cell.row, 6, date_submitted)   # F: Date Submitted
            else:
                # Append new record
                ws_reports.append_row([
                    _new_id(),      # A: ID
                    fellow_id,      # B: Fellow ID
                    fellow_name,    # C: Fellow Name
                    month_label,    # D: Month
                    "TRUE",         # E: Submitted
                    date_submitted, # F: Date Submitted
                    notes,          # G: Notes
                ], value_input_option="USER_ENTERED")
        except Exception as e:
            result["errors"].append(f"Failed to write record for {fellow_name}: {e}")
            continue

        result["synced"].append({
            "fellow_name":    fellow_name,
            "month":          month_label,
            "on_time":        on_time,
            "date_submitted": date_submitted,
        })

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Determine target year/month from args or default to previous month
    if len(sys.argv) == 3:
        try:
            year  = int(sys.argv[1])
            month = int(sys.argv[2])
        except ValueError:
            print("Usage: python sync_status_reports.py [year] [month]")
            print("  e.g. python sync_status_reports.py 2026 3")
            sys.exit(1)
    else:
        # Default: previous month
        today = datetime.now()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1

    result = sync(year, month)

    # Print summary
    month_label = datetime(year, month, 1).strftime("%b %Y")
    print(f"\n{'='*50}")
    print(f"SYNC SUMMARY — {month_label}")
    print(f"{'='*50}")

    print(f"\n✅ Synced ({len(result['synced'])}):")
    for r in result["synced"]:
        status = "on time" if r["on_time"] else "LATE"
        print(f"   {r['fellow_name']} — {r['date_submitted']} ({status})")

    if result["flagged_duplicates"]:
        print(f"\n⚠️  Duplicate submissions flagged ({len(result['flagged_duplicates'])}):")
        for d in result["flagged_duplicates"]:
            print(f"   {d['name']} ({d['email']}) submitted {d['count']} times — used earliest")

    if result["unmatched"]:
        print(f"\n❌ Unmatched submissions ({len(result['unmatched'])}) — no fellow found:")
        for u in result["unmatched"]:
            print(f"   {u['first_name']} {u['last_name']} ({u['email']})")

    if result["errors"]:
        print(f"\n🔴 Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"   {e}")
        sys.exit(1)

    print()
    sys.exit(0)
