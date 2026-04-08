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
                  Contact? | LinkedIn | Last Engaged | Engagement Notes | Notes

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
import re
from datetime import datetime, timedelta


# ============ GOOGLE SHEETS CONFIG ============

SPREADSHEET_ID = st.secrets["gsheets"]["spreadsheet_id"]
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
try:
    FORM_RESPONSES_URL = st.secrets["gsheets"]["form_responses_url"]
except KeyError:
    FORM_RESPONSES_URL = GOOGLE_SHEET_URL

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Sheet (tab) names — must match the actual tab names in your spreadsheet
FELLOWS_SHEET          = "Fellows"
CHECKINS_SHEET         = "Check-ins"
REPORTS_SHEET          = "Status Reports"
ALUMNI_SHEET           = "Alumni"
EVENTS_SHEET           = "Events"
EVENT_ATTENDANCE_SHEET = "Event Attendance"
FORM_RESPONSES_SHEET   = "Form Responses 1"

EVENT_TYPES = [
    "Happy Hour", "Site Visit", "Social", "Career Development",
    "Speaker Series", "Check-ins", "Conference", "Recruitment",
]


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
            "congressional_email":     str(row.get("Congressional Email", "")),
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
            "supervisor_email":        str(row.get("Supervisor's Email", "")),
        })
    return fellows


def _fellow_row_values(fellow_id: str, data: dict) -> list:
    """
    Build an ordered list of cell values for a fellow row.
    Column order must match the Fellows sheet header row exactly.
    """
    return [
        fellow_id,                                                       # A
        data.get("name", ""),                                            # B
        data.get("email", ""),                                           # C
        data.get("congressional_email", ""),                             # D
        data.get("phone", ""),                                           # E
        data.get("cohort", ""),                                          # F
        data.get("fellow_type", ""),                                     # G
        data.get("party", ""),                                           # H
        data.get("office", ""),                                          # I
        data.get("chamber", ""),                                         # J
        data.get("supervisor_email", ""),                                # K
        data.get("linkedin", ""),                                        # L
        data.get("start_date", ""),                                      # M
        data.get("end_date", ""),                                        # N
        data.get("status", "Active"),                                    # O
        data.get("last_check_in", ""),                                   # P
        data.get("prior_role", ""),                                      # Q
        data.get("education", ""),                                       # R
        data.get("notes", ""),                                           # S
        "TRUE" if data.get("requires_monthly_reports") else "FALSE",    # T
        data.get("report_start_date", ""),                               # U
        data.get("report_end_month", ""),                                # V
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
        ws.update(f"A{row_num}:V{row_num}", [_fellow_row_values(record_id, fellow_data)], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to update fellow: {e}")
        return False


def update_fellow_checkin(record_id: str, checkin_date: str) -> bool:
    """
    Update only the 'Last Check-in' field for a fellow.

    Airtable equivalent: PATCH with just {"Last Check-in": date}
    Here: find the row, then update just column O (index 15, 1-based = column O).
    """
    try:
        ws = _worksheet(FELLOWS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            return False
        # "Last Check-in" is column P (16) after Congressional Email was added at D
        ws.update_cell(cell.row, 16, checkin_date)
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
                "late":           _to_bool(row.get("Late", False)),
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
            report_id,                                                    # A
            report_data.get("fellow_id", ""),                             # B
            report_data.get("fellow_name", ""),                           # C
            report_data.get("month", ""),                                 # D
            "TRUE" if report_data.get("submitted", False) else "FALSE",   # E
            report_data.get("date_submitted", ""),                        # F
            report_data.get("notes", ""),                                 # G
            "TRUE" if report_data.get("late", False) else "FALSE",        # H
        ], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to add status report: {e}")
        return False


def update_status_report(record_id: str, submitted: bool, date_submitted: str = None, late: bool = None) -> bool:
    """
    Update a status report's submitted status (and optionally date/late flag).

    Sheet columns: A=ID, B=Fellow ID, C=Fellow Name, D=Month,
                   E=Submitted, F=Date Submitted, G=Notes, H=Late
    """
    try:
        ws = _worksheet(REPORTS_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error("Status report not found.")
            return False
        ws.update_cell(cell.row, 5, "TRUE" if submitted else "FALSE")   # E: Submitted
        if date_submitted:
            ws.update_cell(cell.row, 6, date_submitted)                  # F: Date Submitted
        if late is not None:
            ws.update_cell(cell.row, 8, "TRUE" if late else "FALSE")     # H: Late
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
            "sector":           str(row.get("Sector", "")),
            "location":         str(row.get("Location", "")),
            "contact":          _to_bool(row.get("Contact?", True)),
            "linkedin":         str(row.get("LinkedIn", "")),
            "last_engaged":     str(row.get("Last Engaged", "")),
            "engagement_notes": str(row.get("Engagement Notes", "")),
            "notes":            str(row.get("Notes", "")),
            "prior_role":       str(row.get("Prior Role", "")),
            "education":        str(row.get("Education", "")),
            "currently_on_hill": _to_bool(row.get("Currently on the Hill?", False)),
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
        "TRUE" if data.get("currently_on_hill", False) else "FALSE",
        data.get("sector", ""),
        data.get("location", ""),
        "TRUE" if data.get("contact", True) else "FALSE",
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
    Here: find the row by ID, overwrite the entire row (20 columns = A:T).
    """
    try:
        ws = _worksheet(ALUMNI_SHEET)
        cell = ws.find(record_id, in_column=1)
        if not cell:
            st.error(f"Alumni {record_id} not found.")
            return False
        ws.update(f"A{cell.row}:T{cell.row}", [_alumni_row_values(record_id, alumni_data)], value_input_option="USER_ENTERED")
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

    # Only on-time submissions count toward streaks; late ones are excluded
    submitted_months = {r["month"] for r in reports if r.get("submitted") and not r.get("late")}
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


# ============ EVENTS CRUD ============

def _date_to_quarter(date_str: str) -> str:
    """Convert a date string to a quarter label like 'Q1 2026'."""
    d = _parse_date(date_str)
    if not d:
        return ""
    q = (d.month - 1) // 3 + 1
    return f"Q{q} {d.year}"


def _is_tracked_cohort(cohort_str: str) -> bool:
    """
    Return True if a cohort is January 2026 or later.

    Fellows in earlier cohorts (pre-Jan 2026) are not required to attend events.
    Handles formats like 'Jan 2026 CIF/SCIF', 'January 2026', 'Jan 2026'.
    """
    if not cohort_str:
        return False
    cutoff = datetime(2026, 1, 1)
    # Try to extract a "Month Year" pattern (e.g. "Jan 2026" from "Jan 2026 CIF/SCIF")
    match = re.search(r'([A-Za-z]+ \d{4})', str(cohort_str))
    if match:
        for fmt in ("%b %Y", "%B %Y"):
            try:
                return datetime.strptime(match.group(1), fmt) >= cutoff
            except ValueError:
                continue
    # Fallback: year-only pattern (e.g. "2026")
    match = re.search(r'\b(\d{4})\b', str(cohort_str))
    if match:
        try:
            return datetime(int(match.group(1)), 1, 1) >= cutoff
        except (ValueError, OverflowError):
            pass
    return False


def fetch_events() -> list[dict]:
    """Fetch all events from the Events sheet, sorted by date ascending."""
    ws = _worksheet(EVENTS_SHEET)
    rows = ws.get_all_records()
    events = []
    for row in rows:
        if not str(row.get("Event ID", "")).strip():
            continue  # skip blank rows
        events.append({
            "id":          str(row.get("Event ID", "")),
            "name":        str(row.get("Event Name", "")),
            "date":        str(row.get("Date", "")),
            "type":        str(row.get("Type", "")),
            "location":    str(row.get("Location", "")),
            "venue":       str(row.get("Venue", "")),
            "cohort":      str(row.get("Cohort", "")),
            "quarter":     str(row.get("Quarter", "")),
            "description": str(row.get("Description", "")),
            "required":    _to_bool(row.get("Required for Fellows?", True)),
            "staffed_by":  str(row.get("Staffed By", "")),
        })
    events.sort(key=lambda e: _parse_date(e["date"]) or datetime.min)
    return events


def _event_row_values(event_id: str, data: dict) -> list:
    """Build ordered list of cell values for an event row (columns A–K)."""
    return [
        event_id,                                               # A: Event ID
        data.get("name", ""),                                   # B: Event Name
        data.get("date", ""),                                   # C: Date
        data.get("type", ""),                                   # D: Type
        data.get("location", ""),                               # E: Location
        data.get("venue", ""),                                  # F: Venue
        data.get("cohort", ""),                                 # G: Cohort
        data.get("quarter", ""),                                # H: Quarter
        data.get("description", ""),                            # I: Description
        "TRUE" if data.get("required", True) else "FALSE",     # J: Required for Fellows?
        data.get("staffed_by", ""),                             # K: Staffed By
    ]


def add_event(event_data: dict) -> bool:
    """Append a new event row to the Events sheet."""
    try:
        ws = _worksheet(EVENTS_SHEET)
        event_id = _new_id()
        ws.append_row(_event_row_values(event_id, event_data), value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to add event: {e}")
        return False


def update_event(event_id: str, event_data: dict) -> bool:
    """Update an existing event row by Event ID."""
    try:
        ws = _worksheet(EVENTS_SHEET)
        cell = ws.find(event_id, in_column=1)
        if not cell:
            st.error(f"Event {event_id} not found.")
            return False
        ws.update(f"A{cell.row}:K{cell.row}", [_event_row_values(event_id, event_data)], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to update event: {e}")
        return False


def fetch_all_event_attendance() -> list[dict]:
    """Fetch all rows from the Event Attendance sheet."""
    ws = _worksheet(EVENT_ATTENDANCE_SHEET)
    rows = ws.get_all_records()
    records = []
    for row in rows:
        records.append({
            "id":          str(row.get("Record ID", "")),
            "event_id":    str(row.get("Event ID", "")),
            "fellow_id":   str(row.get("Fellow ID", "")),
            "fellow_name": str(row.get("Fellow Name", "")),
            "attended":    _to_bool(row.get("Attended?", False)),
            "notes":       str(row.get("Notes", "")),
        })
    return records


def save_event_attendance(event_id: str, fellow_id: str, fellow_name: str,
                          attended: bool, notes: str = "") -> bool:
    """
    Upsert an attendance record for one fellow at one event.
    Updates column E (Attended?) if a record already exists; appends a new row otherwise.
    """
    try:
        ws = _worksheet(EVENT_ATTENDANCE_SHEET)
        rows = ws.get_all_records()
        for i, row in enumerate(rows, start=2):  # row 1 is the header
            if (str(row.get("Event ID", "")) == event_id and
                    str(row.get("Fellow ID", "")) == fellow_id):
                ws.update_cell(i, 5, "TRUE" if attended else "FALSE")
                ws.update_cell(i, 6, notes)
                return True
        # No existing record — append a new row
        record_id = _new_id()
        ws.append_row([
            record_id,                          # A: Record ID
            event_id,                           # B: Event ID
            fellow_id,                          # C: Fellow ID
            fellow_name,                        # D: Fellow Name
            "TRUE" if attended else "FALSE",    # E: Attended?
            notes,                              # F: Notes
        ], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Failed to save attendance: {e}")
        return False


def save_event_attendance_batch(event_id: str, attendance_map: dict) -> bool:
    """
    Batch upsert attendance for all fellows at one event in a single API round-trip.

    attendance_map: {fellow_id: (fellow_name, attended, notes)}

    Strategy:
      1. Read the attendance sheet ONCE.
      2. Build a lookup of existing (event_id, fellow_id) → row number.
      3. Collect updates (existing rows) and new rows (inserts) in memory.
      4. Write all updates via one batch_update call and all inserts via one append_rows call.

    This replaces the old per-fellow loop that called get_all_records() N times,
    which caused 429 quota errors when saving attendance for large cohorts.
    """
    try:
        ws = _worksheet(EVENT_ATTENDANCE_SHEET)
        rows = ws.get_all_records()  # single read

        # Build lookup: (event_id, fellow_id) → sheet row number (1-indexed, row 1 = header)
        existing: dict[tuple, int] = {}
        for i, row in enumerate(rows, start=2):
            key = (str(row.get("Event ID", "")), str(row.get("Fellow ID", "")))
            existing[key] = i

        batch_updates = []  # for ws.batch_update()
        new_rows = []       # for ws.append_rows()

        for fellow_id, (fellow_name, attended, notes) in attendance_map.items():
            key = (event_id, fellow_id)
            attended_str = "TRUE" if attended else "FALSE"
            if key in existing:
                row_num = existing[key]
                batch_updates.append({
                    "range": f"E{row_num}:F{row_num}",
                    "values": [[attended_str, notes]],
                })
            else:
                new_rows.append([
                    _new_id(),    # A: Record ID
                    event_id,     # B: Event ID
                    fellow_id,    # C: Fellow ID
                    fellow_name,  # D: Fellow Name
                    attended_str, # E: Attended?
                    notes,        # F: Notes
                ])

        if batch_updates:
            ws.batch_update(batch_updates, value_input_option="USER_ENTERED")
        if new_rows:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")

        return True
    except Exception as e:
        st.error(f"Failed to save attendance: {e}")
        return False


# ============ STATUS REPORT SYNC FROM FORM ============

def sync_status_reports_from_form(year: int, month: int) -> dict:
    """
    Read Google Form responses for the given year/month, match each submission
    to a fellow in the database, and create or update a Status Report record.

    Matching order:
      1. Email (primary) — case-insensitive match against fellows["email"]
      2. Full name fallback — "First Name" + "Last Name" from form matched against fellows["name"]

    On-time rule: submitted by 11:59:59 PM EST on the last calendar day of the month.
    Duplicates (same email, same month): flag them and use the earliest submission.

    Returns a dict with four keys:
      synced             — list of {fellow_name, month, on_time, date_submitted}
      flagged_duplicates — list of {email, name, count}
      unmatched          — list of {email, first_name, last_name}
      errors             — list of error strings (non-fatal issues are logged here, not raised)
    """
    import calendar
    from collections import defaultdict

    try:
        import pytz
        EST = pytz.timezone("America/New_York")
        def _localize(dt):
            return EST.localize(dt)
        def _to_est(dt):
            return dt.astimezone(EST)
    except ImportError:
        from datetime import timezone, timedelta
        EST = timezone(timedelta(hours=-5))  # fallback: fixed UTC-5 (no DST)
        def _localize(dt):
            return dt.replace(tzinfo=EST)
        def _to_est(dt):
            return dt.astimezone(EST)

    result = {"synced": [], "flagged_duplicates": [], "unmatched": [], "errors": []}

    # Deadline: last day of the target month at 23:59:59 EST
    last_day = calendar.monthrange(year, month)[1]
    deadline = _localize(datetime(year, month, last_day, 23, 59, 59))
    month_label = datetime(year, month, 1).strftime("%b %Y")

    # ── 1. Read form responses ────────────────────────────────────────────────
    try:
        ws = _worksheet(FORM_RESPONSES_SHEET)
        rows = ws.get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to read form responses: {e}")
        return result

    # ── 2. Parse timestamps, filter to target month ───────────────────────────
    def _parse_form_ts(ts_str: str):
        """Parse a Google Forms timestamp string into a timezone-aware datetime."""
        for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%-m/%-d/%Y %H:%M:%S"):
            try:
                return _localize(datetime.strptime(ts_str.strip(), fmt))
            except ValueError:
                continue
        return None

    month_responses = []
    for row in rows:
        ts = _parse_form_ts(str(row.get("Timestamp", "")))
        if ts and ts.year == year and ts.month == month:
            month_responses.append({
                "email":      str(row.get("Email Address", "")).strip().lower(),
                "first_name": str(row.get("First Name", "")).strip(),
                "last_name":  str(row.get("Last Name", "")).strip(),
                "timestamp":  ts,
                "on_time":    ts <= deadline,
            })

    if not month_responses:
        result["errors"].append(f"No form responses found for {month_label}.")
        return result

    # ── 3. Detect duplicates; keep earliest submission per email ──────────────
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

    # ── 4. Build fellow lookup indexes ────────────────────────────────────────
    try:
        fellows = fetch_fellows()
    except Exception as e:
        result["errors"].append(f"Failed to fetch fellows: {e}")
        return result

    email_to_fellow = {f["email"].strip().lower(): f for f in fellows if f.get("email")}
    name_to_fellow  = {f["name"].strip().lower(): f  for f in fellows if f.get("name")}

    # ── 5. Load existing Status Report records for this month ─────────────────
    try:
        all_reports = _worksheet(REPORTS_SHEET).get_all_records()
    except Exception as e:
        result["errors"].append(f"Failed to fetch status reports: {e}")
        return result

    # (fellow_id, month_label) → existing report ID
    existing_reports = {
        (str(r.get("Fellow ID", "")), str(r.get("Month", ""))): str(r.get("ID", ""))
        for r in all_reports
    }

    # ── 6. Match each submission and upsert a Status Report record ────────────
    for email, response in deduped.items():
        # Primary match: email
        fellow = email_to_fellow.get(email)

        # Fallback match: full name (case-insensitive)
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
        if key in existing_reports:
            update_status_report(existing_reports[key], submitted=True, date_submitted=date_submitted)
        else:
            add_status_report({
                "fellow_id":      fellow_id,
                "fellow_name":    fellow_name,
                "month":          month_label,
                "submitted":      True,
                "date_submitted": date_submitted,
                "notes":          notes,
            })

        result["synced"].append({
            "fellow_name":    fellow_name,
            "month":          month_label,
            "on_time":        on_time,
            "date_submitted": date_submitted,
        })

    return result


def get_quarter_compliance(fellows: list, events: list, attendance: list) -> dict:
    """
    Compute quarterly attendance compliance for each CIF/SCIF fellow.

    Returns: {fellow_id: {quarter_label: "met" | "not_met"}}

    A quarter appears in a fellow's result only if at least one past required
    event falls in that quarter. AISF fellows are excluded entirely.
    """
    today = datetime.now().date()

    # Build lookup: {event_id: {fellow_id: attended_bool}}
    att_lookup: dict = {}
    for rec in attendance:
        att_lookup.setdefault(rec["event_id"], {})[rec["fellow_id"]] = rec["attended"]

    # Past required events grouped by quarter
    quarter_events: dict = {}
    for event in events:
        if not event.get("required"):
            continue
        d = _parse_date(event["date"])
        if not d or d.date() >= today:
            continue
        q = event.get("quarter") or _date_to_quarter(event["date"])
        if q:
            quarter_events.setdefault(q, []).append(event["id"])

    result: dict = {}
    for fellow in fellows:
        if fellow.get("fellow_type") == "AISF":
            continue
        fid = fellow["id"]
        result[fid] = {}
        for quarter, event_ids in quarter_events.items():
            attended_any = any(
                att_lookup.get(eid, {}).get(fid, False) for eid in event_ids
            )
            result[fid][quarter] = "met" if attended_any else "not_met"
    return result
