# TechCongress Fellows Dashboard — Google Sheets Version

A Streamlit-based dashboard for managing and monitoring TechCongress fellow placements and alumni, connected to **Google Sheets** as the backend database.

> **Purpose:** This folder exists to compare building the same dashboard on Google Sheets
> vs. Airtable (see `techcongress-dashboards/`). The UI and business logic are identical;
> only the data layer (`helpers.py`) differs.

---

## Features

### Current Fellows

- **Fellow Management** — Add, edit, and view fellow profiles with a modal popup interface
- **Status Tracking** — Monitor Active, Flagged, and Ending Soon fellows
- **Check-in History** — Log and track all fellow check-ins over time
- **Monthly Status Reports** — Track monthly report submissions with streak tracking and incentives
- **Filtering & Sorting** — Filter by search term, status, fellow type, party, chamber, and cohort; sort by various criteria (default: Cohort, newest first)
- **Fellow Types** — Supports Congressional Innovation Fellows (CIF), Senior Congressional Innovation Fellows, and AI Security Fellows (AISF)
- **AI Security Fellow Handling** — AISF fellows display an "Executive Branch" tag instead of party affiliation and are excluded from check-in requirements

### Alumni Network

- **Alumni Management** — Add, edit, and view alumni profiles with career and engagement tracking
- **Multi-Select Fellow Types** — Alumni can have multiple fellowship designations (CIF, Senior CIF, Congressional Innovation Scholar, Congressional Digital Service Fellow, AI Security Fellow)
- **Sector Tracking** — Track alumni across Government, Nonprofit, Academia, Private, and Policy/Think Tank sectors
- **Engagement Tracking** — Record last engaged date and engagement notes for each alum
- **Filtering & Sorting** — Filter by search term, fellow type, sector, party, chamber, and cohort; sort by cohort, name, last engaged, organization, or sector

### General

- **Multi-Page Navigation** — Toggle between Current Fellows and Alumni from the sidebar
- **Secure Access** — Password-protected login with TechCongress branding and forced light mode styling

---

## Fellow Types

### Current Fellows

- **Congressional Innovation Fellow (CIF)** — Standard fellows placed in congressional offices
- **Senior Congressional Innovation Fellow (Senior CIF)** — Senior fellows with extended placements
- **AI Security Fellow (AISF)** — Fellows placed in executive branch agencies; displayed with an "Executive Branch" tag instead of party affiliation and excluded from periodic check-in requirements

### Alumni-Only Designations

- **Congressional Innovation Scholar (CIS)** — Historical designation for some earlier fellows
- **Congressional Digital Service Fellow (CDSF)** — Digital service fellowship designation

---

## UI Overview

- **Login Page** — Password-protected login with centered TechCongress logo and forced light mode
- **Current Fellows Dashboard** — Card-based grid showing all fellows with status badges, check-in tracking, and monthly report management
- **Alumni Dashboard** — Card-based grid showing alumni with sector tags, current role/organization, engagement tracking, and multi-select fellow type badges
- **Modal Popups** — Click "View" on any card to open detailed information with contact info, history, and notes
- **Sidebar Navigation** — Toggle between Current Fellows and Alumni pages

---

## Monthly Status Reports

The dashboard includes a monthly status report tracking system for fellows who require regular check-ins.

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

---

## Setup

### 1. Create the Google Spreadsheet

Create a new Google Spreadsheet with four tabs named exactly:

- `Fellows`
- `Check-ins`
- `Status Reports`
- `Alumni`

Add the following header rows (row 1) to each tab:

**Fellows:**
```
ID | Name | Email | Phone Number | Cohort | Fellow Type | Party | Office | Chamber | LinkedIn | Start Date | End Date | Status | Last Check-in | Prior Role | Education | Notes | Requires Monthly Reports | Report Start Date | Report End Month
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

### 4. Adding records directly in Google Sheets

Records added through the app get a UUID auto-generated in column A. But if you ever add a row directly in the spreadsheet, **you must fill in the ID column yourself** — otherwise the app won't be able to update or delete that record, and duplicate key errors can occur.

Any unique value works: a simple number (1, 2, 3...), a short string, or a generated UUID. The only requirement is that no two rows share the same ID within a tab.

> **Tip:** Column A can be hidden in Google Sheets to keep the spreadsheet tidy — the app reads and writes to it by column position, so hidden columns work fine.

### 5. Add the logo

Place the `TechCongress Logo (black).png` file in the project root directory. This logo appears on both the login page and the dashboard header.

### 6. Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Deployment

This app is deployed on **Streamlit Community Cloud**. To deploy your own instance:

1. Push code to GitHub
2. Connect your repo on Streamlit Cloud
3. Add secrets in the Streamlit Cloud settings

---

## Key differences from the Airtable version

| | Airtable (`techcongress-dashboards/`) | Google Sheets (`techcongress-fellows-dashboard/`) |
|---|---|---|
| **Auth** | API key in `st.secrets["airtable"]["api_key"]` | Service account JSON in `st.secrets["gcp_service_account"]` |
| **Record IDs** | Auto-generated (`recXXXXXXXXXXXXXX`) | UUID4 strings we generate |
| **Linked records** | Native linked record arrays (`["recXXX"]`) | Plain UUID string in a cell |
| **Multi-select** | Native array field | Comma-separated string (`"CIF,Senior CIF"`) |
| **Pagination** | 100-record limit, offset loop required | All rows in one call |
| **Filtering** | Server-side formula filter | Client-side filter after full fetch |
| **Dependencies** | `requests` | `gspread`, `google-auth` |

---

## File structure

```
techcongress-fellows-dashboard/
├── app.py                          # Login page + multi-page navigation
├── helpers.py                      # Google Sheets config and CRUD functions
├── pages/
│   ├── current-fellows-page.py     # Current fellows dashboard
│   └── alumni-page.py              # Alumni network dashboard
├── requirements.txt                # Python dependencies (gspread, google-auth, streamlit)
├── TechCongress Logo (black).png   # Logo displayed on login and dashboard
├── .github/
│   └── workflows/
│       └── keep-alive.yml
├── .streamlit/
│   ├── secrets.toml                # Your credentials (not in repo)
│   └── secrets.toml.template       # Template to copy from
├── .gitignore
└── README.md
```
