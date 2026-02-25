"""
helpers.py — Google Sheets backend for TechCongress Fellows Dashboard

BACKEND: Google Sheets via gspread + service account authentication
Compare to helpers.py in techcongress-dashboards/ (Airtable backend)

Google Sheets structure — four tabs in one spreadsheet:
  Fellows       — ID | Name | Email | Phone Number | Cohort | Fellow Type | Party |
                  Office | Chamber | LinkedIn | Start Date | End Date | Status |
                  Last Check-in | Prior Role | Education | Notes |
                  Requires Monthly Reports | Report Start Date | Report End Month

  Check-ins     — ID | Fellow ID | Date | Check-in Type | Notes | Staff Member

  Status Reports — ID | Fellow ID | Month | Submitted | Date Submitted | Notes

  Alumni        — ID | Name | Email | Phone Number | Cohort | Fellow Type |
                  Party | Office Served | Chamber | Education | Prior Role |
                  Current Role | Current Organization | Sector | Location |
                  LinkedIn | Last Engaged | Engagement Notes | Notes

Key differences from Airtable version:
  - Auth: service account JSON in st.secrets["gcp_service_account"]
    instead of API key in st.secrets["airtable"]["api_key"]
  - IDs: UUID strings we generate ourselves (stored in column A of each sheet)
    instead of Airtable auto-generated record IDs ("recXXXXXXXXXXXXXX")
  - Linked records: stored as plain Fellow ID string
    instead of Airtable linked record arrays (["recXXX"])
  - Multi-select: comma-separated string in a single cell (e.g. "CIF,AISF")
    instead of Airtable's native multi-select array
  - No pagination: gspread fetches all rows at once
    instead of Airtable's 100-record page limit requiring offset loops
  - Booleans: "TRUE"/"FALSE" strings in cells
    instead of Airtable native checkbox booleans
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import uuid
from datetime import datetime, timedelta


# ============ GOOGLE SHEETS CONFIG ============

SPREADSHEET_ID = st.secrets["gsheets"]["spreadsheet_id"]
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Sheet (tab) names — must match the actual tab names in your spreadsheet
FELLOWS_SHEET      = "Fellows"
CHECKINS_SHEET     = "Check-ins"
REPORTS_SHEET      = "Status Reports"
ALUMNI_SHEET       = "Alumni"


# ============ CONNECTION HELPERS ============

@st.cache_resource
def _get_client():
    """
    Authenticate with Google using a service account and return a gspread client.
    Cached as a resource so the connection is reused across Streamlit reruns.

    Airtable equivalent: no explicit auth step — API key was just a header value.
    Here we need OAuth2 credentials from a service account JSON stored in secrets.

    secrets.toml entry:
        [gcp_service_account]
        type = "service_account"
        project_id = "..."
        private_key_id = "..."
        private_key = "..."
        client_email = "..."
        ...
    """
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def _worksheet(name: str) -> gspread.Worksheet:
    """Return a worksheet by tab name. Opens the spreadsheet each call (gspread caches internally)."""
    return _get_client().open_by_key(SPREADSHEET_ID).worksheet(name)


def _to_bool(val) -> bool:
    """Normalize a value from Google Sheets into a Python bool."""
    if isinstance(val, bool):
        return val
    return str(val).strip().upper() in ("TRUE", "1", "YES")


def _new_id() -> str:
    """Generate a unique record ID (UUID4). Replaces Airtable's auto-generated record IDs."""
    return str(uuid.uuid4())


# ============ FELLOWS CRUD ============

def fetch_fellows() -> list[dict]:
    """
    Fetch all fellows from the Fellows sheet.

    Airtable equivalent: GET https://api.airtable.com/v0/{base}/{table}
    Here: ws.get_all_records() returns a list of dicts keyed by header row values.
    """
    ws = _worksheet(FELLOWS_SHEET)
    rows = ws.get_all_records()
    fellows = []
    for row in rows:
        fellows.append({
            "id":                      str(row.get("ID", "")),
            "name":                    str(row.get("Name", "")),
            "email":                   str(row.get("Email", "")),
            "phone":                   str(row.get("Phone Number", "")),
            "fellow_type":             str(row.get("Fellow Type", "")),
            "party":                   str(row.get("Party", "")),
            "office":                  str(row.get("Office", "")),
            "chamber":                 str(row.get("Chamber", "")),
            "linkedin":                str(row.get("LinkedIn", "")),
            "start_date":              str(row.get("Start Date", "")),
            "end_date":                str(row.get("End Date", "")),
            "cohort":                  str(row.get("Cohort", "")),
            "status":                  str(row.get("Status", "Active")),
            "last_check_in":           str(row.get("Last Check-in", "")),
            "prior_role":              str(row.get("Prior Role", "")),
            "education":               str(row.get("Education", "")),
            "notes":                   str(row.get("Notes", "")),
            "requires_monthly_reports": _to_bool(row.get("Requires Monthly Reports", False)),
            "report_start_date":       str(row.get("Report Start Date", "")),
            "report_end_month":        str(row.get("Report End Month", "")),
        })
    return fellows


def _fellow_row_values(fellow_id: str, data: dict) -> list:
    """
    Build an ordered list of cell values for a fellow row.
    Column order must match the Fellows sheet header row exactly.
    """
    return [
        fellow_id,
        data.get("name", ""),
        data.get("email", ""),
        data.get("phone", ""),
        data.get("cohort", ""),
        data.get("fellow_type", ""),
        data.get("party", ""),
        data.get("office", ""),
        data.get("chamber", ""),
        data.get("linkedin", ""),
        data.get("start_date", ""),
        data.get("end_date", ""),
        data.get("status", "Active"),
        data.get("last_check_in", ""),
        data.get("prior_role", ""),
        data.get("education", ""),
        data.get("notes", ""),
        "TRUE" if data.get("requires_monthly_reports") else "FALSE",
        data.get("report_start_date", ""),
        data.get("report_end_month", ""),
    ]


def create_fellow(fellow_data: dict) -> bool:
    """
    Append a new fellow row to the Fellows sheet.

    Airtable equivalent: POST https://api.airtable.com/v0/{base}/{table}
    Here: ws.append_row() — we generate the ID ourselves.
    """
    try:
        ws = _worksheet(FELLOWS_SHEET)
        fellow_id = _new_id()
        ws.append_row(_fellow_row_values(fellow_id, fellow_data), value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to create fellow: {e}")
        return False


def update_fellow(record_id: str, fellow_data: dict) -> bool:
    """
    Update an existing fellow row by ID.

    Airtable equivalent: PATCH https://api.airtable.com/v0/{base}/{table}/{record_id}
    Here: find the row by searching column A (ID), then overwrite the entire row.

    Note: gspread.find() does a full sheet scan — fine for small datasets.
    For large datasets, consider caching row indices locally.
    """
    try:
        ws = _worksheet(FELLOWS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error(f"Fellow {record_id} not found.")
            return False
        row_num = cell.row
        # Build the range string, e.g. "A5:T5" for 20 columns
        ws.update(f"A{row_num}:T{row_num}", [_fellow_row_values(record_id, fellow_data)], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to update fellow: {e}")
        return False


def update_fellow_checkin(record_id: str, checkin_date: str) -> bool:
    """
    Update only the 'Last Check-in' field for a fellow.

    Airtable equivalent: PATCH with just {"Last Check-in": date}
    Here: find the row, then update just column N (index 14, 1-based = column N).
    """
    try:
        ws = _worksheet(FELLOWS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            return False
        # "Last Check-in" is the 14th column (N)
        ws.update_cell(cell.row, 14, checkin_date)
        return True
    except Exception as e:
        st.error(f"Failed to update Last Check-in: {e}")
        return False


# ============ CHECK-INS CRUD ============

def fetch_checkins(fellow_id: str) -> list[dict]:
    """
    Fetch all check-ins for a specific fellow.

    Airtable equivalent: GET check-ins table filtered by linked Fellow record ID.
    Here: get all rows, filter by Fellow ID column (plain UUID string match).

    Note: We fetch ALL check-ins and filter client-side. For large datasets,
    Airtable's server-side filtering would be more efficient. With Google Sheets,
    consider a separate sheet per fellow or a database if scale becomes an issue.
    """
    ws = _worksheet(CHECKINS_SHEET)
    rows = ws.get_all_records()
    checkins = []
    for row in rows:
        if str(row.get("Fellow ID", "")) == fellow_id:
            checkins.append({
                "id":             str(row.get("ID", "")),
                "fellow":         [fellow_id],   # match Airtable structure: list of IDs
                "date":           str(row.get("Date", "")),
                "check_in_type":  str(row.get("Check-in Type", "")),
                "notes":          str(row.get("Notes", "")),
                "staff_member":   str(row.get("Staff Member", "")),
            })
    # Sort by date descending (most recent first)
    checkins.sort(key=lambda x: x["date"], reverse=True)
    return checkins


def add_checkin(checkin_data: dict) -> bool:
    """
    Append a new check-in row.

    Airtable equivalent: POST to Check-ins table with Fellow linked record.
    Here: append_row with Fellow ID stored as a plain UUID string.
    """
    try:
        ws = _worksheet(CHECKINS_SHEET)
        checkin_id = _new_id()
        ws.append_row([
            checkin_id,
            checkin_data.get("fellow_id", ""),
            checkin_data.get("date", ""),
            checkin_data.get("check_in_type", ""),
            checkin_data.get("notes", ""),
            checkin_data.get("staff_member", ""),
        ], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to add check-in: {e}")
        return False


def delete_checkin(record_id: str) -> bool:
    """
    Delete a check-in row by ID.

    Airtable equivalent: DELETE https://api.airtable.com/v0/{base}/Check-ins/{id}
    Here: find the row by ID, delete it with ws.delete_rows().

    Note: Airtable deletion is by record ID in the URL. Here we scan column A.
    """
    try:
        ws = _worksheet(CHECKINS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error("Check-in not found.")
            return False
        ws.delete_rows(cell.row)
        return True
    except Exception as e:
        st.error(f"Failed to delete check-in: {e}")
        return False


# ============ STATUS REPORTS CRUD ============

def fetch_status_reports(fellow_id: str) -> list[dict]:
    """
    Fetch all status reports for a specific fellow, sorted by month ascending.

    Airtable equivalent: GET Status Reports filtered by linked Fellow.
    Here: get all rows, filter client-side by Fellow ID column.
    """
    ws = _worksheet(REPORTS_SHEET)
    rows = ws.get_all_records()
    reports = []
    for row in rows:
        if str(row.get("Fellow ID", "")) == fellow_id:
            reports.append({
                "id":             str(row.get("ID", "")),
                "fellow":         [fellow_id],   # match Airtable structure
                "month":          str(row.get("Month", "")),
                "submitted":      _to_bool(row.get("Submitted", False)),
                "date_submitted": str(row.get("Date Submitted", "")),
                "notes":          str(row.get("Notes", "")),
            })
    # Sort by month ascending
    def _month_sort_key(r):
        try:
            return datetime.strptime(r["month"], "%b %Y")
        except Exception:
            return datetime.min
    reports.sort(key=_month_sort_key)
    return reports


def add_status_report(report_data: dict) -> bool:
    """
    Append a new status report row.

    Airtable equivalent: POST to Status Reports table with Fellow linked record.
    """
    try:
        ws = _worksheet(REPORTS_SHEET)
        report_id = _new_id()
        ws.append_row([
            report_id,
            report_data.get("fellow_id", ""),
            report_data.get("month", ""),
            "TRUE" if report_data.get("submitted", False) else "FALSE",
            report_data.get("date_submitted", ""),
            report_data.get("notes", ""),
        ], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to add status report: {e}")
        return False


def update_status_report(record_id: str, submitted: bool, date_submitted: str = None) -> bool:
    """
    Update a status report's submitted status (and optionally date).

    Airtable equivalent: PATCH with {"Submitted": bool, "Date Submitted": date}
    Here: find the row, update columns D (Submitted) and E (Date Submitted).
    """
    try:
        ws = _worksheet(REPORTS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error("Status report not found.")
            return False
        # "Submitted" is column 4, "Date Submitted" is column 5
        ws.update_cell(cell.row, 4, "TRUE" if submitted else "FALSE")
        if date_submitted:
            ws.update_cell(cell.row, 5, date_submitted)
        return True
    except Exception as e:
        st.error(f"Failed to update status report: {e}")
        return False


# ============ ALUMNI CRUD ============

def fetch_alumni() -> list[dict]:
    """
    Fetch all alumni from the Alumni sheet.

    Airtable equivalent: GET Alumni table with pagination (offset loop).
    Here: ws.get_all_records() returns everything in one call — no pagination needed.

    Multi-select Fellow Type is stored as a comma-separated string in Sheets
    ("CIF,Senior CIF") vs. Airtable's native array (["CIF", "Senior CIF"]).
    We parse it back into a list here so the rest of the app is unaffected.
    """
    ws = _worksheet(ALUMNI_SHEET)
    rows = ws.get_all_records()
    alumni = []
    for row in rows:
        raw_fellow_types = str(row.get("Fellow Type", ""))
        fellow_types = [t.strip() for t in raw_fellow_types.split(",") if t.strip()] if raw_fellow_types else []
        alumni.append({
            "id":               str(row.get("ID", "")),
            "name":             str(row.get("Name", "")),
            "email":            str(row.get("Email", "")),
            "phone":            str(row.get("Phone Number", "")),
            "cohort":           str(row.get("Cohort", "")),
            "fellow_types":     fellow_types,   # list, parsed from comma-separated string
            "office_served":    str(row.get("Office Served", "")),
            "chamber":          str(row.get("Chamber", "")),
            "party":            str(row.get("Party", "")),
            "current_role":     str(row.get("Current Role", "")),
            "current_org":      str(row.get("Current Organization", "")),
            "sector":           str(row.get("Sector", "")),
            "location":         str(row.get("Location", "")),
            "linkedin":         str(row.get("LinkedIn", "")),
            "last_engaged":     str(row.get("Last Engaged", "")),
            "engagement_notes": str(row.get("Engagement Notes", "")),
            "notes":            str(row.get("Notes", "")),
            "prior_role":       str(row.get("Prior Role", "")),
            "education":        str(row.get("Education", "")),
        })
    return alumni


def _alumni_row_values(alumni_id: str, data: dict) -> list:
    """
    Build an ordered list of cell values for an alumni row.

    Multi-select Fellow Type stored as comma-separated string.
    Airtable equivalent: native multi-select array field.
    """
    fellow_types = data.get("fellow_types", [])
    fellow_type_str = ",".join(fellow_types) if isinstance(fellow_types, list) else str(fellow_types)
    return [
        alumni_id,
        data.get("name", ""),
        data.get("email", ""),
        data.get("phone", ""),
        data.get("cohort", ""),
        fellow_type_str,        # comma-separated, e.g. "CIF,Senior CIF"
        data.get("party", ""),
        data.get("office_served", ""),
        data.get("chamber", ""),
        data.get("education", ""),
        data.get("prior_role", ""),
        data.get("current_role", ""),
        data.get("current_org", ""),
        data.get("sector", ""),
        data.get("location", ""),
        data.get("linkedin", ""),
        data.get("last_engaged", ""),
        data.get("engagement_notes", ""),
        data.get("notes", ""),
    ]


def create_alumni(alumni_data: dict) -> bool:
    """
    Append a new alumni row.

    Airtable equivalent: POST to Alumni table.
    """
    try:
        ws = _worksheet(ALUMNI_SHEET)
        alumni_id = _new_id()
        ws.append_row(_alumni_row_values(alumni_id, alumni_data), value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to create alumni record: {e}")
        return False


def update_alumni(record_id: str, alumni_data: dict) -> bool:
    """
    Update an existing alumni row by ID.

    Airtable equivalent: PATCH to Alumni table.
    Here: find the row by ID, overwrite the entire row (19 columns = A:S).
    """
    try:
        ws = _worksheet(ALUMNI_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error(f"Alumni {record_id} not found.")
            return False
        ws.update(f"A{cell.row}:S{cell.row}", [_alumni_row_values(record_id, alumni_data)], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to update alumni record: {e}")
        return False


# ============ CALCULATION HELPERS ============
# These functions are pure Python and identical to the Airtable version —
# they operate on data already fetched from the backend.

def _parse_date(date_str: str):
    """
    Try multiple date formats that Google Sheets may return.
    Airtable always returned YYYY-MM-DD; Google Sheets formatting
    depends on the cell's locale/format setting.
    """
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%m/%d/%y", "%-m/%-d/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def get_required_report_months(fellow: dict) -> list[str]:
    """Calculate which months a fellow needs to submit reports for."""
    if not fellow.get("requires_monthly_reports") or not fellow.get("report_start_date"):
        return []
    start_date = _parse_date(fellow["report_start_date"])
    if not start_date:
        return []

    if fellow.get("report_end_month"):
        end_month_str = fellow["report_end_month"]
    else:
        if "Senior" in (fellow.get("fellow_type") or ""):
            end_month_str = "Nov 2026"
        else:
            end_month_str = "Sep 2026"

    month_map = {
        "Feb 2026": (2026, 2), "Mar 2026": (2026, 3), "Apr 2026": (2026, 4),
        "May 2026": (2026, 5), "Jun 2026": (2026, 6), "Jul 2026": (2026, 7),
        "Aug 2026": (2026, 8), "Sep 2026": (2026, 9), "Oct 2026": (2026, 10),
        "Nov 2026": (2026, 11), "Dec 2026": (2026, 12),
    }
    if end_month_str not in month_map:
        return []

    end_year, end_month = month_map[end_month_str]
    required_months = []
    cur_year, cur_month = start_date.year, start_date.month
    while (cur_year < end_year) or (cur_year == end_year and cur_month <= end_month):
        required_months.append(datetime(cur_year, cur_month, 1).strftime("%b %Y"))
        cur_month += 1
        if cur_month > 12:
            cur_month = 1
            cur_year += 1
    return required_months


def calculate_report_streak(reports: list[dict], required_months: list[str]) -> dict:
    """Calculate current submission streak and incentive status."""
    if not required_months:
        return {
            "streak": 0,
            "gift_card_eligible": False,
            "at_risk": False,
            "reimbursements_paused": False,
            "missed_count": 0,
        }

    submitted_months = {r["month"] for r in reports if r.get("submitted")}
    today = datetime.now()

    past_months = []
    for month in required_months:
        try:
            month_date = datetime.strptime(month, "%b %Y")
            if month_date.month == 12:
                last_day = datetime(month_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
            if last_day < today:
                past_months.append(month)
        except Exception:
            continue

    streak = 0
    for month in reversed(past_months):
        if month in submitted_months:
            streak += 1
        else:
            break

    missed_count = 0
    for month in reversed(past_months):
        if month not in submitted_months:
            missed_count += 1
        else:
            break

    return {
        "streak": streak,
        "gift_card_eligible": streak >= 3,
        "at_risk": missed_count == 1,
        "reimbursements_paused": missed_count >= 2,
        "missed_count": missed_count,
    }


def calculate_days_since(date_str: str) -> int:
    """Return the number of days since a given date. Handles multiple date formats."""
    date = _parse_date(date_str)
    if not date:
        return 999
    return (datetime.now() - date).days


def calculate_days_until(date_str: str) -> int:
    """Return the number of days until a given date. Handles multiple date formats."""
    date = _parse_date(date_str)
    if not date:
        return 999
    return (date - datetime.now()).days
