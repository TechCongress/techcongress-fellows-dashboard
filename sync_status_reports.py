"""
sync_status_reports.py — Standalone monthly status report sync

Run this script on the 1st of each month to automatically log whether fellows
submitted their monthly status report on time, based on Google Form responses.

Grace period: submissions up to GRACE_DAYS into the following month are
attributed to the target month and flagged as late=TRUE. This prevents
double-counting when a fellow submits late (e.g. April 3rd for their March
report) and later submits their actual April report.

Usage:
    python sync_status_reports.py               # syncs previous month
    python sync_status_reports.py 2026 3        # syncs a specific year/month

Credentials are read from .streamlit/secrets.toml (same file the Streamlit app uses).
The script does NOT depend on Streamlit — it reads the secrets file directly.

Output: prints a summary to stdout and exits 0 on success, 1 on error.
"""

import sys
import calendar
import uuid
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

# The form responses live in a separate spreadsheet (linked from the Google Form).
# Extract the spreadsheet ID from the form_responses_url in secrets.
_form_url = secrets["gsheets"].get("form_responses_url", "")
if "/spreadsheets/d/" in _form_url:
    _form_id = _form_url.split("/spreadsheets/d/")[1].split("/")[0]
    form_spreadsheet = client.open_by_key(_form_id)
else:
    form_spreadsheet = spreadsheet

FELLOWS_SHEET        = "Fellows"
REPORTS_SHEET        = "Status Reports"
FORM_RESPONSES_SHEET = "Form Responses 1"

# Number of days into the next month that still count as a late submission
# for the current month. e.g. GRACE_DAYS=7 means April 1–7 submissions
# can be attributed to March as late.
GRACE_DAYS = 7


def _ws(name: str) -> gspread.Worksheet:
    return spreadsheet.worksheet(name)


def _form_ws(name: str) -> gspread.Worksheet:
    return form_spreadsheet.worksheet(name)


def _new_id() -> str:
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
    given year and month (including a GRACE_DAYS grace period into the
    following month for late submissions).

    Conflict prevention: any form submission whose (fellow_id, date) is
    already recorded in the Status Reports sheet as a late submission for a
    DIFFERENT month is skipped. This means April 3rd submissions that were
    already attributed to March will not be double-counted as April reports.

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

    # Grace period: include submissions up to GRACE_DAYS into the next month
    if month == 12:
        grace_end = _localize(datetime(year + 1, 1, GRACE_DAYS, 23, 59, 59))
    else:
        grace_end = _localize(datetime(year, month + 1, GRACE_DAYS, 23, 59, 59))

    print(f"\nSyncing status reports for {month_label}")
    print(f"On-time deadline : {deadline.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Grace period ends: {grace_end.strftime('%Y-%m-%d %H:%M:%S %Z')} (submissions after deadline flagged as late)")

    # ── 1. Read form responses ────────────────────────────────────────────────
    try:
        rows = _form_ws(FORM_RESPONSES_SHEET).get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to read form responses: {e}")
        return result

    # ── 2. Parse timestamps; collect responses in the full window ─────────────
    def _parse_ts(ts_str: str):
        for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%-m/%-d/%Y %H:%M:%S"):
            try:
                return _localize(datetime.strptime(ts_str.strip(), fmt))
            except ValueError:
                continue
        return None

    all_responses = []
    for row in rows:
        ts = _parse_ts(str(row.get("Timestamp", "")))
        if ts:
            in_month = (ts.year == year and ts.month == month)
            in_grace = (deadline < ts <= grace_end)
            if in_month or in_grace:
                all_responses.append({
                    "email":      str(row.get("Email Address", "")).strip().lower(),
                    "first_name": str(row.get("First Name", "")).strip(),
                    "last_name":  str(row.get("Last Name", "")).strip(),
                    "timestamp":  ts,
                    "on_time":    ts <= deadline,
                    "late":       ts > deadline,
                })

    print(f"Found {len(all_responses)} form response(s) in window for {month_label}")

    if not all_responses:
        result["errors"].append(f"No form responses found for {month_label} (including {GRACE_DAYS}-day grace period).")
        return result

    # ── 3. Fetch fellows and build lookup indexes ─────────────────────────────
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

    # ── 4. Load existing Status Report records ────────────────────────────────
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

    # Build set of (fellow_id, date_submitted) pairs already consumed as late
    # submissions for a DIFFERENT month. These must be skipped to prevent
    # double-counting (e.g. an April 3rd submission already attributed to March).
    consumed_late = defaultdict(set)   # fellow_id -> {date_submitted_str, ...}
    for r in all_reports:
        if _to_bool(r.get("Late", "FALSE")):
            fid = str(r.get("Fellow ID", ""))
            ds  = str(r.get("Date Submitted", ""))
            if fid and ds:
                consumed_late[fid].add(ds)

    # ── 5. Preliminary fellow-matching (before dedup) ─────────────────────────
    # We match before deduplicating so that consumed-late filtering can use
    # fellow IDs, preventing the dup-detection from discarding the real
    # submission when an earlier one was already consumed by a prior month.
    for r in all_responses:
        email  = r["email"]
        fellow = email_to_fellow.get(email) if email else None
        if not fellow:
            full_name = f"{r['first_name']} {r['last_name']}".strip().lower()
            fellow = name_to_fellow.get(full_name)
        r["fellow_id"]   = fellow["id"]   if fellow else None
        r["fellow_name"] = fellow["name"] if fellow else None

    # ── 6. Filter consumed-late, then dedup ───────────────────────────────────
    by_fellow         = defaultdict(list)   # fellow_id -> [responses]
    unmatched_by_key  = defaultdict(list)   # email/placeholder -> [responses]

    for i, r in enumerate(all_responses):
        date_str = _to_est(r["timestamp"]).strftime("%Y-%m-%d")
        if r["fellow_id"]:
            # Skip if this exact submission date was already consumed as late
            # for a different month (e.g. April 3rd already used for March)
            if date_str in consumed_late.get(r["fellow_id"], set()):
                print(f"   ↩ Skipping {r['first_name']} {r['last_name']} ({date_str}) — already attributed to a prior month as late")
                continue
            by_fellow[r["fellow_id"]].append(r)
        else:
            key = r["email"] if r["email"] else f"__nomail_{i}__"
            unmatched_by_key[key].append(r)

    # Flag duplicates and keep earliest per fellow
    deduped_fellows = {}
    for fellow_id, responses in by_fellow.items():
        if len(responses) > 1:
            r = responses[0]
            result["flagged_duplicates"].append({
                "email": r["email"],
                "name":  f"{r['first_name']} {r['last_name']}",
                "count": len(responses),
            })
        deduped_fellows[fellow_id] = sorted(responses, key=lambda r: r["timestamp"])[0]

    # Flag duplicates and report unmatched
    for key, responses in unmatched_by_key.items():
        if len(responses) > 1 and not key.startswith("__nomail_"):
            r = responses[0]
            result["flagged_duplicates"].append({
                "email": key,
                "name":  f"{r['first_name']} {r['last_name']}",
                "count": len(responses),
            })
        r = sorted(responses, key=lambda r: r["timestamp"])[0]
        result["unmatched"].append({
            "email":      r["email"],
            "first_name": r["first_name"],
            "last_name":  r["last_name"],
        })

    # ── 7. Upsert Status Report records ───────────────────────────────────────
    ws_reports = _ws(REPORTS_SHEET)

    for fellow_id, response in deduped_fellows.items():
        fellow_name    = response["fellow_name"]
        date_submitted = _to_est(response["timestamp"]).strftime("%Y-%m-%d")
        is_late        = response["late"]
        notes          = "" if not is_late else "⚠️ Submitted after month-end deadline (11:59 PM EST)"

        report_key = (fellow_id, month_label)
        try:
            if report_key in existing:
                report_id = existing[report_key]
                cell = ws_reports.find(report_id, in_column=1)
                if cell:
                    ws_reports.update_cell(cell.row, 5, "TRUE")                              # E: Submitted
                    ws_reports.update_cell(cell.row, 6, date_submitted)                      # F: Date Submitted
                    ws_reports.update_cell(cell.row, 8, "TRUE" if is_late else "FALSE")      # H: Late
            else:
                ws_reports.append_row([
                    _new_id(),                              # A: ID
                    fellow_id,                              # B: Fellow ID
                    fellow_name,                            # C: Fellow Name
                    month_label,                            # D: Month
                    "TRUE",                                 # E: Submitted
                    date_submitted,                         # F: Date Submitted
                    notes,                                  # G: Notes
                    "TRUE" if is_late else "FALSE",         # H: Late
                ], value_input_option="USER_ENTERED")
        except Exception as e:
            result["errors"].append(f"Failed to write record for {fellow_name}: {e}")
            continue

        result["synced"].append({
            "fellow_name":    fellow_name,
            "month":          month_label,
            "on_time":        not is_late,
            "date_submitted": date_submitted,
            "late":           is_late,
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
        if r["late"]:
            status = "LATE"
        elif r["on_time"]:
            status = "on time"
        else:
            status = "unknown"
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
