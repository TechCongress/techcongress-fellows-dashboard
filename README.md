# TechCongress Fellows Dashboard — Google Sheets Version

A Streamlit-based dashboard for managing and monitoring TechCongress fellow placements, alumni, and events — connected to **Google Sheets** as the backend database.

---

## Features

### Current Fellows

- **Fellow Management** — Add, edit, and view fellow profiles with a modal popup interface
- **Status Tracking** — Monitor Active, Flagged, and Ending Soon fellows
- **Check-in History** — Log and track all fellow check-ins over time
- **Monthly Status Reports** — Track monthly report submissions with streak tracking and incentives; automatically synced from Google Form responses on the 1st of each month
- **Filtering & Sorting** — Filter by search term, status, fellow type, party, chamber, and cohort; sort by various criteria (default: Cohort, newest first)
- **Fellow Types** — Supports Congressional Innovation Fellows (CIF), Senior Congressional Innovation Fellows, and AI Security Fellows (AISF)
- **AI Security Fellow Handling** — AISF fellows display an "Executive Branch" tag instead of party affiliation and are excluded from check-in requirements
- **Equal-height cards** — All fellow cards in a row are the same height regardless of how much data they contain; variable fields (office, term, last check-in) are anchored to the card bottom via flexbox

### Alumni Network

- **Alumni Management** — Add, edit, and view alumni profiles with career and engagement tracking
- **Multi-Select Fellow Types** — Alumni can have multiple fellowship designations (CIF, Senior CIF, Congressional Innovation Scholar, Congressional Digital Service Fellow, AI Security Fellow)
- **Sector Tracking** — Track alumni across Government, Nonprofit, Academia, Private, and Policy/Think Tank sectors
- **Engagement Tracking** — Record last engaged date and engagement notes for each alum
- **Filtering & Sorting** — Filter by search term, fellow type, sector, party, chamber, and cohort; sort by cohort, name, last engaged, organization, or sector
- **Equal-height cards** — Same flexbox approach as fellow cards; footer fields (office served, sector, location, LinkedIn) anchor to the bottom

### Events Planning

- **Event Management** — Add, edit, and view events with name, date, type, venue, quarter, and required status
- **Attendance Recording** — Mark fellow attendance for each past event via a dialog with checkboxes; saves in batch (see API notes below)
- **Attendance Roster** — Expandable roster on each event card showing who attended vs. was absent
- **Quarter Compliance Tracking** — Each tracked fellow must attend at least one required event per quarter; compliance is computed per fellow per quarter and displayed as met/not-met pills
- **At-Risk Flagging** — Fellows who have missed all events in a quarter are flagged with a red border on their card
- **Fellows Tab** — Per-fellow view showing quarterly compliance, at-risk status, type/party badges, and an expandable full event history
- **Overview Tab** — Summary metrics: average attendance %, at-risk count, quarter compliance breakdown
- **Cohort Scoping** — Attendance tracking only applies to Jan 2026 CIF/SCIF fellows and future cohorts; earlier cohorts are excluded

### General

- **Multi-Page Navigation** — Toggle between Current Fellows, Alumni, and Events from the sidebar
- **Secure Access** — Password-protected login with TechCongress branding
- **Dark Mode** — Full dark mode support via CSS custom properties; all badges, cards, charts, and avatars respond to `prefers-color-scheme: dark`
- **Responsive Badges** — Reusable `tc-badge-*` CSS classes in `styles.py` replace inline hardcoded colors; both light and dark mode variants are defined centrally

---

## Fellow Types

### Current Fellows

- **Congressional Innovation Fellow (CIF)** — Standard fellows placed in congressional offices
- **Senior Congressional Innovation Fellow (Senior CIF)** — Senior fellows with extended placements
- **AI Security Fellow (AISF)** — Fellows placed in executive branch agencies; displayed with an "Executive Branch" tag instead of party affiliation and excluded from check-in and attendance tracking

### Alumni-Only Designations

- **Congressional Innovation Scholar (CIS)** — Historical designation
- **Congressional Digital Service Fellow (CDSF)** — Digital service fellowship designation

---

## UI Overview

- **Login Page** — Password-protected with centered TechCongress logo
- **Current Fellows Dashboard** — Card-based grid with status badges, check-in tracking, and monthly report management
- **Alumni Dashboard** — Card-based grid with sector tags, current role/organization, engagement tracking, and multi-select fellow type badges
- **Events Dashboard** — Three-tab layout: Overview (summary metrics), Events (filterable event list with attendance recording), Fellows (per-fellow compliance cards)
- **Modal Popups** — Click "View" on any card to open a tabbed detail view
- **Sidebar Navigation** — Toggle between all three pages

---

## Monthly Status Reports

**Report Schedule:**
- Jan 2025 extended fellows: Reports start Feb 2026, due on the last day of each month
- Jan 2026 cohort: Reports start Mar 2026, due on the last day of each month
- Congressional Innovation Fellows (CIF): Reports through Sep 2026
- Senior Congressional Innovation Fellows: Reports through Nov 2026
- AI Security Fellows: Reports through Sep 2026 (default)
- Manual override available via "Report End Month" field

**Incentives & Consequences:**
- 🔥 Streak Tracking — Consecutive submissions are tracked
- 🎁 Gift Card — 3 reports in a row earns a $50 gift card
- ⚠️ At Risk — 1 missed report triggers a warning
- 🚫 Reimbursements Paused — 2+ missed reports pauses reimbursements

**Automated Sync:**

`sync_status_reports.py` runs on the 1st of each month via a scheduled task. It reads the previous month's Google Form responses ("Form Responses 1" tab) and automatically marks each fellow's status report as submitted in the Status Reports sheet. Matching is done by email first, with full name as a fallback. On-time is defined as submitted by 11:59 PM EST on the last day of the month. Late submissions are marked with a note. Duplicate submissions (same fellow, same month) are flagged for manual review. Unmatched submissions (no email or name match in the database) are printed in the summary output for manual entry.

To run manually for any month:
```bash
python sync_status_reports.py           # syncs previous month
python sync_status_reports.py 2026 3    # syncs a specific month
```

---

## Setup

### 1. Create the Google Spreadsheet

Create a new Google Spreadsheet with **six** tabs named exactly:

- `Fellows`
- `Check-ins`
- `Status Reports`
- `Alumni`
- `Events`
- `Event Attendance`

Add the following header rows (row 1) to each tab:

**Fellows:**
```
ID | Name | Email | Phone Number | Cohort | Fellow Type | Party | Office | Chamber | Supervisor's Email | LinkedIn | Start Date | End Date | Status | Last Check-in | Prior Role | Education | Notes | Requires Monthly Reports | Report Start Date | Report End Month
```

**Check-ins:**
```
ID | Fellow ID | Date | Check-in Type | Notes | Staff Member
```

**Status Reports:**
```
ID | Fellow ID | Month | Submitted | Date Submitted | Notes
```

**Alumni:**
```
ID | Name | Email | Phone Number | Cohort | Fellow Type | Party | Office Served | Chamber | Education | Prior Role | Current Role | Current Organization | Sector | Location | Contact? | LinkedIn | Last Engaged | Engagement Notes | Notes
```

**Events:**
```
Event ID | Name | Date | Type | Venue | Quarter | Required? | Notes | Location | Status | Cohort
```

**Event Attendance:**
```
Record ID | Event ID | Fellow ID | Fellow Name | Attended? | Notes
```

> **Note:** Column A in every tab is the ID column. Records added through the app get a UUID auto-generated here. If you add rows directly in the spreadsheet, you must fill in the ID column yourself — any unique value works (a number, short string, or UUID). Duplicate or missing IDs will cause update/delete errors.
>
> Column A can be hidden in Google Sheets to keep things tidy — the app reads and writes by column position, so hidden columns work fine.

### 2. Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Create a **Service Account** and download the JSON key file
5. Share your Google Spreadsheet with the service account email (`...@....iam.gserviceaccount.com`) — give it **Editor** access

### 3. Configure Secrets

Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml` and fill in:

```toml
[gsheets]
spreadsheet_id = "your_spreadsheet_id_from_the_url"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[auth]
username = "your_username"
password = "your_password"
```

> **Streamlit Cloud:** Paste these values directly into the app's Secrets settings (Settings → Secrets).

### 4. Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 5. Add the logo

Place the `TechCongress Logo (black).png` file in the project root. It appears on both the login page and the dashboard header.

---

## Deployment

Deployed on **Streamlit Community Cloud**.

- `runtime.txt` pins the Python version to `3.11` to prevent Streamlit Cloud from auto-upgrading to newer Python versions (which caused a deployment failure when they defaulted to Python 3.13).
- Push code to GitHub → Streamlit Cloud automatically redeploys. If the deployed app appears stale, pushing any file change (even `runtime.txt`) forces a clean redeployment.

---

## Architecture Notes

### CSS & Theming (`styles.py`)

All CSS lives in `styles.py` and is injected via `st.markdown(get_css(), unsafe_allow_html=True)` at the top of each page. It uses CSS custom properties (variables) so a single `@media (prefers-color-scheme: dark)` block handles all dark mode overrides without touching Python code.

Key variable groups:
- `--tc-bg`, `--tc-surface`, `--tc-surface2` — background layers
- `--tc-text`, `--tc-text2`, `--tc-text3`, `--tc-text4` — text hierarchy
- `--tc-border`, `--tc-shadow` — card borders and shadows
- `--tc-avatar-bg/text` — fellow initials avatars (Events page)
- `--tc-present-bg/text`, `--tc-absent-bg/text` — attendance roster row colors

**Badge classes** — instead of inline `background-color`/`color` on every badge, reusable `.tc-badge` + `.tc-badge-{color}` classes are defined once in `styles.py`:

- Solid badges (white text, work in both modes without overrides): `tc-badge-indigo`, `tc-badge-cyan`, `tc-badge-emerald`, `tc-badge-amber`
- Pastel badges (light mode pastels, dark mode gets saturated background + light text via `@media` override): `tc-badge-blue`, `tc-badge-green`, `tc-badge-orange`, `tc-badge-purple`, `tc-badge-yellow`, `tc-badge-pink`, `tc-badge-gray`, `tc-badge-red`
- Attendance badges: `tc-badge-met` (green), `tc-badge-not-met` (red)

### Equal-Height Cards

Fellow and alumni cards use `display:flex; flex-direction:column; min-height:Npx` on the card container. Variable-length footer fields (office, term dates, last check-in for fellows; office served, sector, location, LinkedIn for alumni) are wrapped in a `<div style="margin-top:auto">` so they always anchor to the card bottom. Short cards pad with whitespace; tall cards can still grow past the minimum.

### Google Sheets API — Batch Attendance Writing

The attendance save used to call `save_event_attendance()` once per fellow in a loop. Each call performed a full `ws.get_all_records()` (a read request). With ~40 fellows this fired 40 reads in rapid succession, hitting the Google Sheets 60-reads/minute quota and throwing `APIError: [429]`.

**Fix:** `save_event_attendance_batch()` in `helpers.py` reads the sheet **once**, builds an in-memory lookup of existing records, then writes all updates in a single `ws.batch_update()` call and all new rows in a single `ws.append_rows()` call — regardless of cohort size.

### Streamlit Element Key Conflicts

Streamlit requires unique keys for all interactive elements. The attendance button (`att_btn_{idx}_{event_id}`) and attendance checkbox (`att_chk_{event_id}_{fellow_id}`) previously used the same `att_` prefix, causing `StreamlitDuplicateElementKey` errors when numeric values aligned (e.g., `att_1_2` from both `idx=1, event_id=2` and `event_id=1, fellow_id=2`). Fixed by using distinct prefixes (`att_btn_` and `att_chk_`).

### Plotly Charts (Dark Mode)

Charts use `paper_bgcolor="rgba(0,0,0,0)"` and `plot_bgcolor="rgba(0,0,0,0)"` (transparent) so the CSS-controlled container background shows through. Text and legend colors are set to `#6b7280` (neutral gray) which is readable in both light and dark modes.

---

## File Structure

```
techcongress-fellows-dashboard/
├── app.py                          # Login page + multi-page navigation
├── helpers.py                      # Google Sheets config and all CRUD functions
├── styles.py                       # Centralized CSS (variables, badge classes, dark mode)
├── sync_status_reports.py          # Standalone monthly status report sync script
├── pages/
│   ├── current-fellows-page.py     # Current fellows dashboard
│   ├── alumni-page.py              # Alumni network dashboard
│   └── events-page.py              # Events planning + attendance tracking
├── runtime.txt                     # Pins Python to 3.11 for Streamlit Cloud
├── requirements.txt                # Python dependencies
├── TechCongress Logo (black).png   # Logo for login and header
├── .github/
│   └── workflows/
│       └── keep-alive.yml
├── .streamlit/
│   ├── secrets.toml                # Your credentials (not in repo)
│   └── secrets.toml.template       # Template to copy from
├── .gitignore
└── README.md
```

---

## Key Differences from the Airtable Version

| | Airtable (`techcongress-dashboards/`) | Google Sheets (`techcongress-fellows-dashboard/`) |
|---|---|---|
| **Auth** | API key in `st.secrets["airtable"]["api_key"]` | Service account JSON in `st.secrets["gcp_service_account"]` |
| **Record IDs** | Auto-generated (`recXXXXXXXXXXXXXX`) | UUID4 strings we generate |
| **Linked records** | Native linked record arrays (`["recXXX"]`) | Plain UUID string in a cell |
| **Multi-select** | Native array field | Comma-separated string (`"CIF,Senior CIF"`) |
| **Pagination** | 100-record limit, offset loop required | All rows in one call |
| **Filtering** | Server-side formula filter | Client-side filter after full fetch |
| **Dependencies** | `requests` | `gspread`, `google-auth` |
