# TechCongress Fellows Dashboard — Google Sheets Version

A Streamlit-based dashboard for managing TechCongress fellow placements and alumni,
connected to **Google Sheets** as the backend database.

> **Purpose:** This folder exists to compare building the same dashboard on Google Sheets
> vs. Airtable (see `techcongress-dashboards/`). The UI and business logic are identical;
> only the data layer (`helpers.py`) differs.

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
ID | Name | Email | Phone Number | Cohort | Fellow Type | Party | Office Served | Chamber | Education | Prior Role | Current Role | Current Organization | Sector | Location | LinkedIn | Last Engaged | Engagement Notes | Notes
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

### 5. Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Key differences from the Airtable version

| | Airtable (`techcongress-dashboards/`) | Google Sheets (`techcongress-dashboards-gsheets/`) |
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
techcongress-dashboards-gsheets/
├── app.py                          # Login page + multi-page navigation
├── helpers.py                      # Google Sheets config and CRUD functions (NEW)
├── pages/
│   ├── current-fellows-page.py     # Current fellows dashboard (unchanged from Airtable version)
│   └── alumni-page.py              # Alumni network dashboard (unchanged from Airtable version)
├── requirements.txt                # Updated: gspread + google-auth instead of requests
├── TechCongress Logo (black).png
├── .github/
│   └── workflows/
│       └── keep-alive.yml
├── .streamlit/
│   ├── secrets.toml                # Your credentials (not in repo)
│   └── secrets.toml.template       # Template to copy from
└── README.md
```
