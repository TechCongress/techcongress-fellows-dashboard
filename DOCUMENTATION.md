# TechCongress Fellows Dashboard — Documentation

## Project Purpose

The TechCongress Fellows Dashboard is an internal staff tool for managing and monitoring TechCongress Congressional Innovation Fellows (CIF, Senior CIF, and AISF) throughout their fellowship placements. It replaces manual spreadsheet tracking by providing a centralized, interactive interface for viewing fellow profiles, logging check-ins, tracking monthly status reports, recording event attendance, and surfacing at-a-glance analytics on the current cohort and alumni.

The dashboard is built with Streamlit and reads/writes data from Google Sheets, making it lightweight to maintain without a traditional database.

---

## Key Features

### Current Fellows Page

- Summary stats bar showing total fellows, active count, fellows needing check-in, flagged fellows, and fellows ending soon
- Pie charts breaking down the cohort by party affiliation, chamber, and fellow type — displayed between the stats bar and the filters panel
- Filterable, searchable fellow cards with color-coded status badges
- Equal-height cards: all cards in a row share the same height regardless of data; footer fields (office, fellowship term, last check-in) are anchored to the card bottom via flexbox
- Fellow modal with six tabs: Contact, Placement, Background, Status Reports, Check-ins, and Events
- The Events tab inside the modal shows that fellow's quarterly compliance and full event history
- Inline editing of all fellow fields directly from the modal
- One-click check-in logging with automatic timestamp
- Status report tracking: staff can mark monthly reports as submitted and add notes

### Alumni Page

- Two-tab layout: **All Alumni** (existing roster view) and **On the Hill** (new focused view)
- Full alumni roster with filter/search controls
- Alumni modal with tabbed layout mirroring the current fellows modal
- Pie charts breaking down alumni by party affiliation, fellow type, and post-fellowship sector
- Alumni party chart handles fellows with multiple affiliations (e.g. "Democrat, Institutional Office") by counting each affiliation separately
- Equal-height cards: same flexbox approach as fellow cards; footer fields (office served, sector, location, LinkedIn) anchor to the bottom

### On the Hill View

- Dedicated tab on the Alumni page showing only alumni currently working in congressional roles
- Alumni are marked via a **"Currently on the Hill"** checkbox in the edit form
- Chamber (Senate vs. House) is **automatically inferred** from the `current_role` field using keyword matching: `"Sen."` or `"Senate"` → Senate; `"Rep."` or `"House"` → House. `"Sen."` is matched case-sensitively to avoid false matches on "Senior"
- Alumni whose chamber cannot be inferred appear in an "Other / Chamber Unknown" section below the two columns, with a note prompting staff to add the right keyword to their current role
- Stats bar at the top shows total on the Hill, Senate count, House count, and percentage of all alumni
- Filterable by name/role search, party, and cohort

### Events Page

- Event Management — add, edit, and view events with name, date, type, venue, quarter, and required status
- Three-tab layout: Overview, Events, and Fellows
- **Overview tab** — summary metrics including average attendance percentage across past events, at-risk fellow count, and per-quarter compliance breakdown
- **Events tab** — filterable list of all events; each card shows type/status badges, venue, and attendance rate; past events show an expandable attendance roster with present/absent indicators per fellow
- **Fellows tab** — per-fellow compliance cards showing quarterly met/not-met status, type and party badges, at-risk flagging (red border), and an expandable event history per fellow
- Attendance Recording — clicking "Record Attendance" opens a dialog with checkboxes for all eligible fellows; saving writes the entire cohort's attendance in a single batch operation (see API notes below)
- Quarter Compliance — each tracked fellow must attend at least one required event per quarter; compliance is computed per fellow per quarter
- Cohort Scoping — attendance tracking applies to Jan 2026 CIF/SCIF fellows and future cohorts only; earlier cohorts and AISF fellows are excluded from compliance tracking

### Add New Fellow

- Intake form pre-populated with all placement fields, accessible from the Current Fellows page
- Writes a new row directly to the Fellows Google Sheet on submission

### Authentication

- Simple username/password login gate on app load, configured via Streamlit secrets

### Dark Mode

- Full dark mode support via CSS custom properties (variables) in `styles.py`
- All badges, cards, charts, avatars, and roster rows respond to `prefers-color-scheme: dark`
- No separate dark-mode codebase — a single `@media (prefers-color-scheme: dark)` block in `styles.py` overrides all variables
- Plotly charts use transparent backgrounds (`rgba(0,0,0,0)`) so the CSS-controlled container color shows through

---

## Data Flow Overview

```
Google Sheets (source of truth)
        ↕
   helpers.py (gspread read/write)
        ↕
   styles.py (CSS injection)
        ↕
   Streamlit pages (UI layer)
```

All data lives in Google Sheets and is fetched fresh on each page load. There is no local database or caching layer. Writes (adding fellows, editing fields, logging check-ins, submitting status reports, recording event attendance) go back to Google Sheets immediately via the service account.

The dashboard connects to two separate Google Sheets:

- **Fellows Sheet** (`spreadsheet_id` in secrets) — contains the Fellows, Alumni, Check-ins, Status Reports, Events, and Event Attendance tabs
- **Form Responses Sheet** (`form_responses_url` in secrets) — the separate Google Form response sheet linked from the "View All Responses" button in the Status Reports tab

---

## Google Sheets Structure

**Fellows tab** — one row per current fellow, columns A–U:

| Col | Field |
|-----|-------|
| A | Fellow ID |
| B | Full Name |
| C | Email |
| D | Phone |
| E | Fellow Type (CIF / Senior CIF / AISF) |
| F | Party |
| G | State |
| H | Office |
| I | Chamber (Senate / House / Executive Branch) |
| J | Supervisor's Email |
| K | LinkedIn |
| L | Start Date |
| M | End Date |
| N | Status |
| O | Last Check-in |
| P | Prior Role |
| Q | Education |
| R | Notes |
| S | Requires Monthly Reports (TRUE/FALSE) |
| T | Report Start Date |
| U | Report End Month |

**Check-ins tab** — one row per check-in:

| Col | Field |
|-----|-------|
| A | Check-in ID |
| B | Fellow ID |
| C | Date |
| D | Check-in Type |
| E | Notes |
| F | Staff Member |

**Status Reports tab** — one row per report submission:

| Col | Field |
|-----|-------|
| A | Report ID |
| B | Fellow ID |
| C | Fellow Name |
| D | Month |
| E | Submitted (TRUE/FALSE) |
| F | Date Submitted |
| G | Notes |

**Alumni tab** — similar structure to Fellows with post-fellowship sector and `fellow_types` (plural, stored as comma-separated string) instead of `fellow_type`. Columns A–T:

| Col | Field |
|-----|-------|
| A | ID |
| B | Name |
| C | Email |
| D | Phone Number |
| E | Cohort |
| F | Fellow Type (comma-separated) |
| G | Party |
| H | Office Served |
| I | Chamber |
| J | Education |
| K | Prior Role |
| L | Current Role |
| M | Currently on Hill (TRUE/FALSE) |
| N | Sector |
| O | Location |
| P | Contact? (TRUE/FALSE) |
| Q | LinkedIn |
| R | Last Engaged |
| S | Engagement Notes |
| T | Notes |

> **Note:** Column M ("Currently on Hill") was added after the original build. If you have existing alumni rows in the spreadsheet, insert a new column M between Current Role and Sector and add the header "Currently on Hill". Leave existing rows blank (treated as FALSE) or set to TRUE where applicable. The update range in `update_alumni()` was expanded from `A:S` to `A:T` to accommodate this.

**Events tab** — one row per event:

| Col | Field |
|-----|-------|
| A | Event ID |
| B | Name |
| C | Date |
| D | Type |
| E | Venue |
| F | Quarter |
| G | Required? (TRUE/FALSE) |
| H | Notes |
| I | Location |
| J | Status |
| K | Cohort |

**Event Attendance tab** — one row per fellow per event:

| Col | Field |
|-----|-------|
| A | Record ID |
| B | Event ID |
| C | Fellow ID |
| D | Fellow Name |
| E | Attended? (TRUE/FALSE) |
| F | Notes |

> **Important:** Column A in every tab is the ID column. Records added through the app get a UUID auto-generated here. If you add rows directly in the spreadsheet, you must fill in the ID column yourself — any unique value works. Duplicate or missing IDs will cause update/delete errors. Column A can be hidden in Google Sheets to keep things tidy — the app reads and writes by column position, so hidden columns work fine.

---

## Dashboard Structure

```
techcongress-fellows-dashboard/
├── app.py                        # Entry point: login gate, sidebar nav
├── helpers.py                    # All Google Sheets read/write logic
├── styles.py                     # Centralized CSS: variables, badge classes, dark mode
├── pages/
│   ├── current-fellows-page.py   # Current fellows view, charts, modals
│   ├── alumni-page.py            # Alumni view, charts, modals
│   └── events-page.py            # Events planning + attendance tracking
├── runtime.txt                   # Pins Python to 3.11 for Streamlit Cloud
├── .streamlit/
│   └── secrets.toml              # Credentials (gitignored)
├── requirements.txt
├── README.md
└── DOCUMENTATION.md
```

### `helpers.py` — key functions

**Fellows:**
- `fetch_fellows()` — reads all rows from Fellows tab, returns list of dicts
- `create_fellow(data)` — appends a new row to Fellows tab
- `update_fellow(fellow_id, data)` — overwrites the fellow's entire row
- `update_fellow_checkin(fellow_id, timestamp)` — updates the Last Check-in column only

**Check-ins:**
- `fetch_checkins(fellow_id)` — reads Check-ins tab, filters by fellow ID
- `add_checkin(data)` — appends a row to Check-ins tab
- `delete_checkin(checkin_id)` — removes a check-in row by ID

**Status Reports:**
- `fetch_status_reports(fellow_id)` — reads Status Reports tab, filters by fellow ID
- `add_status_report(report_data)` — appends a row to Status Reports tab
- `update_status_report(report_id, submitted, date)` — marks a report as submitted

**Alumni:**
- `fetch_alumni()` — reads all rows from Alumni tab
- `create_alumni(data)` — appends a new alumni row
- `update_alumni(alumni_id, data)` — overwrites an alumni row

**Events:**
- `fetch_events()` — reads all rows from Events tab, returns list of dicts sorted by date
- `add_event(data)` — appends a new event row
- `update_event(event_id, data)` — overwrites an event row

**Event Attendance:**
- `fetch_all_event_attendance()` — reads entire Event Attendance tab, returns all records
- `save_event_attendance_batch(event_id, attendance_map)` — batch upsert for all fellows at one event; reads the sheet once, then writes all updates and inserts in at most two API calls (see API notes below)
- `get_quarter_compliance(fellows, events, attendance)` — computes per-fellow per-quarter met/not-met compliance

### `styles.py` — CSS system

All CSS is defined once in `styles.py` and injected at the top of each page via `st.markdown(get_css(), unsafe_allow_html=True)`. It uses CSS custom properties so a single `@media (prefers-color-scheme: dark)` block handles all dark mode overrides without touching Python code.

**Key CSS variable groups:**
- `--tc-bg`, `--tc-surface`, `--tc-surface2` — background layers
- `--tc-text`, `--tc-text2`, `--tc-text3`, `--tc-text4` — text hierarchy
- `--tc-border`, `--tc-shadow` — card borders and elevation
- `--tc-avatar-bg/text` — fellow initials avatars (Events page)
- `--tc-present-bg/text`, `--tc-absent-bg/text` — attendance roster row colors

**Badge classes:** instead of inline `background-color`/`color` on every badge, reusable `.tc-badge .tc-badge-{color}` classes are defined once in `styles.py`. Solid-color badges (indigo, cyan, emerald, amber) use white text and work in both modes without overrides. Pastel badges (blue, green, orange, purple, yellow, pink, gray, red) have explicit dark-mode overrides using saturated backgrounds and light text.

---

## Configuration and Local Setup

**Prerequisites:** Python 3.11, a Google Cloud service account with Sheets API enabled, and Editor access granted to the service account email on the Fellows spreadsheet.

### 1. Clone the repo and install dependencies

```bash
git clone <repo-url>
cd techcongress-fellows-dashboard
pip install -r requirements.txt
```

### 2. Create your secrets file

Copy the secrets template and fill in your values:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

The secrets file expects:

```toml
[gsheets]
spreadsheet_id = "your_spreadsheet_id_here"
form_responses_url = "https://docs.google.com/spreadsheets/d/..."

[gcp_service_account]
type = "service_account"
project_id = "your_project_id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[auth]
username = "your_username"
password = "your_password"
```

### 3. Run locally

```bash
streamlit run app.py
```

---

## Deployment (Streamlit Community Cloud)

The dashboard is deployed on Streamlit Community Cloud.

- `runtime.txt` (containing `3.11`) pins the Python version to prevent Streamlit Cloud from auto-upgrading. When Streamlit Cloud upgraded their default Python to 3.13, it caused a deployment failure (`ImportError` on a module that hadn't been recompiled). Pinning Python and pushing any file change forces a clean redeployment.
- To update: push changes to the `main` branch on GitHub — Streamlit Cloud redeploys automatically.
- If you're working on a new feature, create a branch (`git checkout -b feature-name`), push with `git push --set-upstream origin feature-name`, and open a pull request to merge into `main` when ready.
- Secrets are managed in the Streamlit Cloud dashboard under App settings → Secrets. Any changes to secrets require a manual app reboot from the dashboard to take effect.

---

## API and Performance Notes

### Google Sheets 429 Rate Limit (Read Quota)

Google Sheets enforces a limit of ~60 read requests per minute per user. The attendance save originally called a per-fellow function in a loop — each call did a full `ws.get_all_records()` (one read request). With ~40 fellows, this fired 40 reads in rapid succession and caused `APIError: [429] Quota exceeded`.

**Fix:** `save_event_attendance_batch()` reads the sheet **once**, builds an in-memory lookup of existing records, then performs all updates in a single `ws.batch_update()` call and all new inserts in a single `ws.append_rows()` call — regardless of cohort size. This reduces the operation from N reads + N writes to 1 read + 2 writes maximum.

### Streamlit Element Key Conflicts

Streamlit requires unique keys for all interactive elements. Two keys that previously shared the `att_` prefix could collide numerically (e.g. `att_1_2` from both `idx=1, event_id=2` and `event_id=1, fellow_id=2`), causing a `StreamlitDuplicateElementKey` error. Fixed by using distinct prefixes: `att_btn_` for attendance dialog trigger buttons and `att_chk_` for attendance checkboxes.

---

## Data Entry Conventions

These conventions ensure consistency across the dashboard and avoid display or filtering issues.

- **Education field** — Always enter the full, unabbreviated university or institution name. Write "Massachusetts Institute of Technology" not "MIT", "University of California, Berkeley" not "UC Berkeley". This keeps the alumni and fellow profiles consistent and searchable.
- **Cohort field** — Use "Month YYYY" format (e.g., "January 2026") for cohorts with a known start month, or "YYYY" for year-only cohorts. The dashboard sorts cohorts chronologically based on this format.
- **Dates** — Enter dates as YYYY-MM-DD. Google Sheets may store them differently internally, but the app's date parser handles the most common formats.
- **IDs** — Never edit column A (the ID column) in any tab. These are auto-generated UUIDs used to link records across sheets. Changing or duplicating them will break updates and deletes.
- **Fellow Type** — Use the exact values: `Congressional Innovation Fellow`, `Senior Congressional Innovation Fellow`, `AI Security Fellow`. Variations will cause filter and badge logic to fall back to defaults.

---

## Known Limitations

- **No real-time sync** — data is fetched on page load. If two staff members are editing simultaneously, the last write wins.
- **Empty rows in Google Sheets** — if a tab has many empty rows below the data, `append_row` will write past them rather than immediately after the last data row. Fix by selecting and deleting all empty rows below the last real entry.
- **Column position sensitivity** — write functions use column index, not header name. If columns are reordered in the sheet, the corresponding `helpers.py` functions must be updated to match.
- **Date format variability** — Google Sheets may return dates as `M/D/YYYY` rather than `YYYY-MM-DD`. The `_parse_date_value()` helper handles the most common formats, but unusual formats could still cause errors.
- **AISF party affiliation** — AISF fellows are placed in the executive branch and do not have a congressional party affiliation. They are intentionally excluded from the "By Party" pie chart and from event attendance compliance tracking.
- **Alumni `fellow_types` field** — alumni records use `fellow_types` (plural, stored as a comma-separated string parsed into a list) while current fellow records use `fellow_type` (singular string). Code that reads fellow type must account for this difference.
- **Events attendance scoping** — compliance tracking only applies to Jan 2026 CIF/SCIF fellows and future cohorts. Earlier cohorts appear in the fellows list but their attendance is not tracked for compliance purposes.
