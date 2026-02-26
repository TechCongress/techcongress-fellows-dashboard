import streamlit as st
from datetime import datetime, timedelta
from helpers import (
    fetch_fellows, create_fellow, update_fellow, update_fellow_checkin,
    fetch_checkins, add_checkin, delete_checkin,
    fetch_status_reports, add_status_report, update_status_report,
    get_required_report_months, calculate_report_streak,
    calculate_days_since, calculate_days_until, GOOGLE_SHEET_URL
)

def _cohort_sort_key(cohort_str: str) -> datetime:
    """Parse a cohort string into a datetime for correct chronological sorting.
    Handles 'January 2025' (month-year) and '2025' (year-only) formats."""
    if not cohort_str:
        return datetime.min
    for fmt in ("%B %Y", "%b %Y", "%Y"):
        try:
            return datetime.strptime(cohort_str.strip(), fmt)
        except ValueError:
            continue
    return datetime.min


def _parse_date_value(date_str):
    """Parse a date string from Google Sheets into a Python date object.
    Returns None if the string is empty or unparseable."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%m/%d/%y", "%-m/%-d/%y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    return None

# ============ AUTH GUARD ============
if not st.session_state.get("authenticated"):
    st.warning("Please log in first.")
    st.stop()

# ============ SESSION STATE ============
if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False
if "editing_fellow" not in st.session_state:
    st.session_state.editing_fellow = None
if "modal_fellow_id" not in st.session_state:
    st.session_state.modal_fellow_id = None
if "show_checkin_form" not in st.session_state:
    st.session_state.show_checkin_form = False
if "trigger_modal" not in st.session_state:
    st.session_state.trigger_modal = False

# ============ CUSTOM CSS ============
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }

    /* Force light mode styling */
    [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
    }

    [data-testid="stHeader"] {
        background-color: #f8fafc;
    }

    h1, h2, h3, p, span, label {
        color: #1f2937 !important;
    }
    .stat-card {
        background: white;
        padding: 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .stat-label {
        color: #6b7280;
        font-size: 0.875rem;
        margin: 0;
    }
    .fellow-card {
        background: white;
        padding: 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .fellow-card:hover {
        border-color: #93c5fd;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .status-on-track { background: #dcfce7; color: #166534; border-radius: 9999px; }
    .status-flagged { background: #fef9c3; color: #854d0e; border-radius: 9999px; }
    .status-ending-soon { background: #ffedd5; color: #9a3412; border-radius: 9999px; }
    .party-democrat { background: #dbeafe; color: #1d4ed8; }
    .party-republican { background: #fee2e2; color: #dc2626; }
    .party-independent { background: #f3e8ff; color: #7c3aed; }
    .fellow-type-senior { background: #e0e7ff; color: #4338ca; }
    .fellow-type-cif { background: #f1f5f9; color: #475569; }
    .needs-checkin { background: #fef9c3; color: #854d0e; }
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 1rem;
        border-radius: 0.75rem;
        border: 1px solid #e5e7eb;
    }

    div[data-testid="stMetric"] label {
        color: #6b7280 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #1f2937 !important;
    }

    /* Help icon (question mark) styling */
    [data-testid="stMetric"] svg {
        color: #6b7280 !important;
        stroke: #6b7280 !important;
    }

    /* Tooltip styling */
    [data-testid="stTooltipIcon"] {
        color: #6b7280 !important;
    }

    [data-testid="stTooltipIcon"] svg {
        color: #6b7280 !important;
        stroke: #6b7280 !important;
    }

    /* Tooltip popup content */
    div[data-baseweb="tooltip"] {
        background-color: #1f2937 !important;
        color: #ffffff !important;
    }

    div[data-baseweb="tooltip"] div {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
    }

    [data-testid="stSidebar"] * {
        color: #1f2937 !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] a {
        color: #1f2937 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #e5e7eb !important;
    }

    [data-testid="stSidebarContent"] {
        background-color: #ffffff !important;
    }

    .stButton button {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 0.5rem !important;
    }

    .stButton button:hover {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    .stSelectbox label, .stTextInput label {
        color: #1f2937 !important;
    }

    [data-testid="stExpander"] {
        background-color: white;
        border-radius: 0.75rem;
    }

    [data-testid="stExpander"] summary {
        color: #1f2937 !important;
    }

    [data-testid="stExpander"] summary span {
        color: #1f2937 !important;
    }

    [data-testid="stExpander"] div {
        color: #1f2937 !important;
    }

    [data-testid="stExpanderDetails"] {
        color: #1f2937 !important;
    }

    [data-testid="stExpanderDetails"] p {
        color: #1f2937 !important;
    }

    /* Modal styles */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        padding-top: 50px;
        overflow-y: auto;
    }

    .modal-container {
        background: white;
        border-radius: 1rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        width: 90%;
        max-width: 700px;
        max-height: calc(100vh - 100px);
        overflow-y: auto;
        margin-bottom: 50px;
    }

    .modal-header {
        padding: 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        position: sticky;
        top: 0;
        background: white;
        border-radius: 1rem 1rem 0 0;
        z-index: 10;
    }

    .modal-body {
        padding: 1.5rem;
    }

    .modal-close-btn {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: #f3f4f6;
        border: none;
        border-radius: 50%;
        width: 32px;
        height: 32px;
        cursor: pointer;
        font-size: 1.25rem;
        color: #6b7280;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .modal-close-btn:hover {
        background: #e5e7eb;
        color: #1f2937;
    }

    /* Force light mode for dialogs */
    [data-testid="stDialog"],
    [data-testid="stDialog"] > div,
    [data-testid="stDialog"] [data-testid="stVerticalBlock"],
    [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stDialog"] section,
    [data-testid="stDialog"] [role="dialog"],
    [role="dialog"],
    [role="dialog"] > div,
    div[data-modal-container="true"],
    .stDialog > div {
        background-color: white !important;
    }

    [data-testid="stDialog"] h1,
    [data-testid="stDialog"] h2,
    [data-testid="stDialog"] h3,
    [data-testid="stDialog"] h4,
    [data-testid="stDialog"] h5,
    [data-testid="stDialog"] p,
    [data-testid="stDialog"] span,
    [data-testid="stDialog"] label,
    [data-testid="stDialog"] div,
    [role="dialog"] h1,
    [role="dialog"] h2,
    [role="dialog"] h3,
    [role="dialog"] h4,
    [role="dialog"] p,
    [role="dialog"] span,
    [role="dialog"] div {
        color: #1f2937 !important;
    }

    /* Dialog header specifically */
    [data-testid="stDialogHeader"],
    [data-testid="stDialog"] header,
    [role="dialog"] header {
        background-color: white !important;
        color: #1f2937 !important;
    }

    [data-testid="stDialog"] a,
    [role="dialog"] a {
        color: #2563eb !important;
    }

    [data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {
        color: #1f2937 !important;
    }

    [data-testid="stDialog"] [data-testid="stCaptionContainer"],
    [role="dialog"] [data-testid="stCaptionContainer"] {
        color: #6b7280 !important;
    }

    [data-testid="stDialog"] hr,
    [role="dialog"] hr {
        border-color: #e5e7eb !important;
    }

    /* Form inputs in dialog */
    [data-testid="stDialog"] input,
    [data-testid="stDialog"] textarea,
    [data-testid="stDialog"] select,
    [role="dialog"] input,
    [role="dialog"] textarea,
    [role="dialog"] select {
        background-color: white !important;
        color: #1f2937 !important;
        border-color: #d1d5db !important;
    }

    /* Select boxes in dialog */
    [data-testid="stDialog"] [data-baseweb="select"],
    [data-testid="stDialog"] [data-baseweb="select"] > div,
    [role="dialog"] [data-baseweb="select"],
    [role="dialog"] [data-baseweb="select"] > div {
        background-color: white !important;
        color: #1f2937 !important;
    }

    /* Dialog close button (X) */
    [data-testid="stDialog"] button[aria-label="Close"],
    [role="dialog"] button[aria-label="Close"],
    [data-testid="stDialogCloseButton"],
    [data-testid="stDialog"] [data-testid="baseButton-header"],
    [role="dialog"] [data-testid="baseButton-header"] {
        color: #1f2937 !important;
        background-color: #f3f4f6 !important;
    }

    [data-testid="stDialog"] button[aria-label="Close"]:hover,
    [role="dialog"] button[aria-label="Close"]:hover {
        background-color: #e5e7eb !important;
        color: #1f2937 !important;
    }

    /* Close button icon/svg */
    [data-testid="stDialog"] button[aria-label="Close"] svg,
    [role="dialog"] button[aria-label="Close"] svg,
    [data-testid="stDialog"] [data-testid="baseButton-header"] svg {
        stroke: #1f2937 !important;
        color: #1f2937 !important;
    }

    /* Force light mode globally */
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"],
    .main,
    .block-container {
        background-color: #f8fafc !important;
        color: #1f2937 !important;
    }

    /* Expander / Filters section */
    [data-testid="stExpander"],
    [data-testid="stExpander"] > div,
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpanderDetails"] {
        background-color: white !important;
        color: #1f2937 !important;
    }

    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] p {
        color: #1f2937 !important;
    }

    /* All form inputs - light mode */
    input, textarea, select,
    [data-baseweb="input"],
    [data-baseweb="input"] input,
    [data-baseweb="textarea"],
    [data-baseweb="select"],
    [data-baseweb="select"] > div {
        background-color: white !important;
        color: #1f2937 !important;
    }

    /* Select dropdown text */
    [data-baseweb="select"] span,
    [data-baseweb="select"] div[class*="valueContainer"],
    [data-baseweb="select"] div[class*="singleValue"] {
        color: #1f2937 !important;
    }

    /* Dropdown menu */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"] ul,
    [role="listbox"],
    [role="listbox"] li,
    [role="option"] {
        background-color: white !important;
        color: #1f2937 !important;
    }

    [role="option"]:hover {
        background-color: #f3f4f6 !important;
    }

    /* Labels */
    .stSelectbox label,
    .stTextInput label,
    .stDateInput label,
    .stTextArea label,
    [data-testid="stWidgetLabel"] {
        color: #1f2937 !important;
    }

    /* Placeholder text */
    input::placeholder,
    textarea::placeholder {
        color: #9ca3af !important;
    }

    /* Streamlit header toolbar icons */
    [data-testid="stToolbar"],
    [data-testid="stToolbar"] button,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    header[data-testid="stHeader"] {
        background-color: #f8fafc !important;
        color: #1f2937 !important;
    }

    [data-testid="stToolbar"] svg,
    [data-testid="stToolbar"] button svg,
    header[data-testid="stHeader"] svg {
        color: #1f2937 !important;
        stroke: #1f2937 !important;
        fill: #1f2937 !important;
    }

    /* Main menu button */
    [data-testid="stMainMenu"],
    [data-testid="stMainMenu"] button {
        color: #1f2937 !important;
    }

    [data-testid="stMainMenu"] svg {
        color: #1f2937 !important;
        stroke: #1f2937 !important;
    }
</style>
""", unsafe_allow_html=True)


# ============ MAIN APP ============

def main():
    # Header
    st.image("TechCongress Logo (black).png", width=200)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("TechCongress Fellows Dashboard")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

    st.caption("Monitor and manage current fellow placements")

    btn_col, _ = st.columns([1, 4])
    with btn_col:
        if st.button("Add Fellow", type="primary", use_container_width=True):
            st.session_state.show_add_form = True
            st.session_state.editing_fellow = None
            st.rerun()

    # Fetch data
    with st.spinner("Loading fellows..."):
        fellows = fetch_fellows()

    # Show modal if a fellow is selected AND trigger_modal is True
    if st.session_state.modal_fellow_id and st.session_state.trigger_modal:
        selected_fellow = next((f for f in fellows if f["id"] == st.session_state.modal_fellow_id), None)
        if selected_fellow:
            show_fellow_modal(selected_fellow)
        # Reset trigger after showing modal
        st.session_state.trigger_modal = False

    if not fellows:
        st.warning("No fellows found. Add your first fellow to get started!")
        if st.session_state.show_add_form:
            show_fellow_form()
        return

    # Calculate stats
    total = len(fellows)
    on_track = len([f for f in fellows if f["status"] in ["on-track", "Active"]])
    flagged = len([f for f in fellows if f["status"] in ["flagged", "Flagged"]])
    ending_soon = len([f for f in fellows if f["status"] in ["ending-soon", "Ending Soon"]])
    needs_checkin = len([f for f in fellows if calculate_days_since(f["last_check_in"]) > 210 and f["status"] in ["on-track", "Active"] and "AI Security" not in (f.get("fellow_type") or "")])

    # Stats row
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Fellows", total, help="Currently placed")
    with col2:
        st.metric("Active", on_track, help="No issues")
    with col3:
        st.metric("Needs Check-in", needs_checkin, help="7+ months since contact")
    with col4:
        st.metric("Flagged", flagged, help="Needs attention")
    with col5:
        st.metric("Ending Soon", ending_soon, help="Within 90 days")

    st.markdown("---")

    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            search = st.text_input("Search", placeholder="Name or office...")
        with col2:
            status_options = ["All Statuses", "Active", "Flagged", "Ending Soon"]
            status_filter = st.selectbox("Status", status_options)
        with col3:
            fellow_type_options = ["All Types", "Senior Congressional Innovation Fellow", "Congressional Innovation Fellow", "AI Security Fellow"]
            fellow_type_filter = st.selectbox("Fellow Type", fellow_type_options)
        with col4:
            party_options = ["All Parties", "Democrat", "Republican", "Independent", "Institutional Office"]
            party_filter = st.selectbox("Party", party_options)
        with col5:
            chamber_options = ["All Chambers", "Senate", "House"]
            chamber_filter = st.selectbox("Chamber", chamber_options)

        # Cohort filter
        col1, col2 = st.columns(2)
        with col1:
            cohorts = sorted(set([f["cohort"] for f in fellows if f["cohort"]]), key=_cohort_sort_key, reverse=True)
            cohort_options = ["All Cohorts"] + cohorts
            cohort_filter = st.selectbox("Cohort", cohort_options)
        with col2:
            sort_options = ["Priority (Flagged first)", "Name (A-Z)", "Name (Z-A)", "Last Check-in (oldest first)", "Last Check-in (newest first)", "End Date (soonest first)", "End Date (latest first)", "Cohort (newest first)", "Cohort (oldest first)"]
            sort_by = st.selectbox("Sort by", sort_options, index=sort_options.index("Cohort (newest first)"))

    # Apply filters
    filtered_fellows = fellows.copy()

    if search:
        search_lower = search.lower()
        filtered_fellows = [f for f in filtered_fellows if
            search_lower in f["name"].lower() or
            search_lower in f["office"].lower()]

    if status_filter != "All Statuses":
        filtered_fellows = [f for f in filtered_fellows if f["status"] == status_filter]

    if fellow_type_filter != "All Types":
        filtered_fellows = [f for f in filtered_fellows if f["fellow_type"] == fellow_type_filter]

    if party_filter != "All Parties":
        filtered_fellows = [f for f in filtered_fellows if f["party"] == party_filter]

    if chamber_filter != "All Chambers":
        filtered_fellows = [f for f in filtered_fellows if f["chamber"] == chamber_filter]

    if cohort_filter != "All Cohorts":
        filtered_fellows = [f for f in filtered_fellows if f["cohort"] == cohort_filter]

    # Sort based on selected option
    if sort_by == "Priority (Flagged first)":
        def sort_key(f):
            status_priority = {"flagged": 0, "Flagged": 0, "ending-soon": 1, "Ending Soon": 1, "on-track": 2, "Active": 2}.get(f["status"], 3)
            days_since = calculate_days_since(f["last_check_in"])
            return (status_priority, -days_since)
        filtered_fellows.sort(key=sort_key)
    elif sort_by == "Name (A-Z)":
        filtered_fellows.sort(key=lambda f: f["name"].lower())
    elif sort_by == "Name (Z-A)":
        filtered_fellows.sort(key=lambda f: f["name"].lower(), reverse=True)
    elif sort_by == "Last Check-in (oldest first)":
        filtered_fellows.sort(key=lambda f: f["last_check_in"] or "0000-00-00")
    elif sort_by == "Last Check-in (newest first)":
        filtered_fellows.sort(key=lambda f: f["last_check_in"] or "0000-00-00", reverse=True)
    elif sort_by == "End Date (soonest first)":
        filtered_fellows.sort(key=lambda f: f["end_date"] or "9999-99-99")
    elif sort_by == "End Date (latest first)":
        filtered_fellows.sort(key=lambda f: f["end_date"] or "0000-00-00", reverse=True)
    elif sort_by == "Cohort (newest first)":
        filtered_fellows.sort(key=lambda f: _cohort_sort_key(f.get("cohort") or ""), reverse=True)
    elif sort_by == "Cohort (oldest first)":
        filtered_fellows.sort(key=lambda f: _cohort_sort_key(f.get("cohort") or ""))

    # Show count
    st.caption(f"Showing {len(filtered_fellows)} of {total} fellows")

    # Show add/edit form if needed
    if st.session_state.show_add_form or st.session_state.editing_fellow:
        show_fellow_form()

    # Display fellows in cards
    cols = st.columns(3)
    for idx, fellow in enumerate(filtered_fellows):
        with cols[idx % 3]:
            show_fellow_card(fellow)


def show_fellow_card(fellow):
    """Display a fellow card (collapsed view only - modal handles expanded view)"""
    days_since_checkin = calculate_days_since(fellow["last_check_in"])
    is_aisf = "AI Security" in (fellow.get("fellow_type") or "")
    needs_checkin = days_since_checkin > 210 and fellow["status"] in ["on-track", "Active"] and not is_aisf

    # Status badge colors
    status_colors = {
        "on-track": ("#4ade80", "#166534"),
        "Active": ("#4ade80", "#166534"),
        "flagged": ("#fde047", "#854d0e"),
        "Flagged": ("#fde047", "#854d0e"),
        "ending-soon": ("#f87171", "#991b1b"),
        "Ending Soon": ("#f87171", "#991b1b")
    }
    status_label = {"on-track": "Active", "flagged": "Flagged", "ending-soon": "Ending Soon"}.get(fellow["status"], fellow["status"])
    bg_color, text_color = status_colors.get(fellow["status"], ("#4ade80", "#166534"))

    # Fellow type badge
    type_label = ""
    type_bg = ""
    type_text = "#ffffff"
    if fellow["fellow_type"]:
        if "Senior" in fellow["fellow_type"]:
            type_label = "Senior CIF"
            type_bg = "#6366f1"
            type_text = "#ffffff"
        elif "AI Security" in fellow["fellow_type"]:
            type_label = "AISF"
            type_bg = "#0891b2"
            type_text = "#ffffff"
        else:
            type_label = "CIF"
            type_bg = "#93c5fd"
            type_text = "#1e40af"

    # Build badge HTML
    checkin_badge = ""
    if needs_checkin:
        checkin_badge = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#eab308;color:#ffffff;margin-left:0.25rem;">Needs Check-in</span>'

    type_html = ""
    if type_label:
        type_html = f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{type_bg};color:{type_text};margin-right:0.25rem;">{type_label}</span>'

    party_html = ""
    if fellow["party"]:
        if fellow["party"] == "Republican":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#ef4444;color:#ffffff;">R</span>'
        elif fellow["party"] == "Democrat":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#3b82f6;color:#ffffff;">D</span>'
        elif fellow["party"] == "Independent":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#8b5cf6;color:#ffffff;">I</span>'
        elif fellow["party"] == "Institutional Office":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#64748b;color:#ffffff;">Institutional</span>'
    elif is_aisf:
        party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#94a3b8;color:#ffffff;">Executive Branch</span>'

    # CARD VIEW
    office_html = ""
    if fellow["office"]:
        office_html = f'<div style="color:#374151;font-size:0.875rem;margin-bottom:0.25rem;">{fellow["office"]}</div>'

    term_html = ""
    if fellow["start_date"] and fellow["end_date"]:
        term_html = f'<div style="color:#6b7280;font-size:0.8rem;margin-bottom:0.25rem;">Fellowship Term: {fellow["start_date"]} - {fellow["end_date"]}</div>'

    checkin_html = ""
    if fellow["last_check_in"]:
        checkin_html = f'<div style="color:#6b7280;font-size:0.8rem;">Last check-in: {fellow["last_check_in"]}</div>'

    card_html = f'<div style="background-color:white;padding:1.25rem;border-radius:0.75rem;border:1px solid #e5e7eb;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.1);"><div style="font-weight:600;font-size:1.1rem;margin-bottom:0.25rem;color:#1f2937;">{fellow["name"]}</div><div style="color:#6b7280;font-size:0.875rem;margin-bottom:0.75rem;">Cohort: {fellow["cohort"]}</div><div style="margin-bottom:0.5rem;"><span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{bg_color};color:{text_color};">{status_label}</span>{checkin_badge}</div><div style="margin-bottom:0.5rem;">{type_html}{party_html}</div>{office_html}{term_html}{checkin_html}</div>'

    st.markdown(card_html, unsafe_allow_html=True)

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View", key=f"view_{fellow['id']}", use_container_width=True):
            st.session_state.modal_fellow_id = fellow["id"]
            st.session_state.trigger_modal = True
            st.rerun()
    with col2:
        if st.button("Edit", key=f"edit_{fellow['id']}", use_container_width=True):
            st.session_state.editing_fellow = fellow
            st.session_state.show_add_form = False
            st.rerun()


@st.dialog("Fellow Details", width="large")
def show_fellow_modal(fellow):
    """Display fellow details in a modal dialog with tab navigation"""
    days_since_checkin = calculate_days_since(fellow["last_check_in"])
    is_aisf = "AI Security" in (fellow.get("fellow_type") or "")
    needs_checkin = days_since_checkin > 210 and fellow["status"] in ["on-track", "Active"] and not is_aisf

    # Status badge colors
    status_colors = {
        "on-track": ("#4ade80", "#166534"),
        "Active": ("#4ade80", "#166534"),
        "flagged": ("#fde047", "#854d0e"),
        "Flagged": ("#fde047", "#854d0e"),
        "ending-soon": ("#f87171", "#991b1b"),
        "Ending Soon": ("#f87171", "#991b1b")
    }
    status_label = {"on-track": "Active", "flagged": "Flagged", "ending-soon": "Ending Soon"}.get(fellow["status"], fellow["status"])
    bg_color, text_color = status_colors.get(fellow["status"], ("#4ade80", "#166534"))

    # Fellow type badge
    type_label = ""
    type_bg = ""
    type_text = "#ffffff"
    if fellow["fellow_type"]:
        if "Senior" in fellow["fellow_type"]:
            type_label = "Senior CIF"
            type_bg = "#6366f1"
            type_text = "#ffffff"
        elif "AI Security" in fellow["fellow_type"]:
            type_label = "AISF"
            type_bg = "#0891b2"
            type_text = "#ffffff"
        else:
            type_label = "CIF"
            type_bg = "#93c5fd"
            type_text = "#1e40af"

    # Build badge HTML
    checkin_badge = ""
    if needs_checkin:
        checkin_badge = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#eab308;color:#ffffff;margin-left:0.25rem;">Needs Check-in</span>'

    type_html = ""
    if type_label:
        type_html = f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{type_bg};color:{type_text};margin-right:0.25rem;">{type_label}</span>'

    party_html = ""
    if fellow["party"]:
        if fellow["party"] == "Republican":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#ef4444;color:#ffffff;">R</span>'
        elif fellow["party"] == "Democrat":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#3b82f6;color:#ffffff;">D</span>'
        elif fellow["party"] == "Independent":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#8b5cf6;color:#ffffff;">I</span>'
        elif fellow["party"] == "Institutional Office":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#64748b;color:#ffffff;">Institutional</span>'
    elif is_aisf:
        party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#94a3b8;color:#ffffff;">Executive Branch</span>'

    # Modal header
    st.markdown(f"## {fellow['name']}")
    st.markdown(f"**{fellow['cohort']}** • {fellow['fellow_type'] or 'Fellow'}")

    badges_html = f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{bg_color};color:{text_color};">{status_label}</span>{checkin_badge}{type_html}{party_html}'
    st.markdown(f'<div style="margin-bottom:1rem;">{badges_html}</div>', unsafe_allow_html=True)

    # ── Tab navigation ──────────────────────────────────────────────────────────
    checkins = fetch_checkins(fellow["id"])
    checkin_count = len(checkins)

    (tab_contact, tab_placement, tab_background,
     tab_reports, tab_checkins) = st.tabs([
        "Contact",
        "Placement",
        "Background",
        f"Status Reports",
        f"Check-ins ({checkin_count})",
    ])

    # ── Contact tab ─────────────────────────────────────────────────────────────
    with tab_contact:
        if fellow["email"]:
            st.markdown(f"📧 **Email:** [{fellow['email']}](mailto:{fellow['email']})")
        if fellow["phone"]:
            st.markdown(f"📞 **Phone:** {fellow['phone']}")
        if fellow["linkedin"]:
            st.markdown(f"🔗 **LinkedIn:** [View profile]({fellow['linkedin']})")
        if not fellow["email"] and not fellow["phone"] and not fellow["linkedin"]:
            st.caption("No contact info on record.")

    # ── Placement tab ────────────────────────────────────────────────────────────
    with tab_placement:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Placement")
            if fellow["office"]:
                st.markdown(f"**Office:** {fellow['office']}")
            if fellow["chamber"]:
                st.markdown(f"**Chamber:** {fellow['chamber']}")
            if fellow["party"]:
                st.markdown(f"**Party:** {fellow['party']}")
            if not fellow["office"] and not fellow["chamber"]:
                st.caption("No placement info on record.")
        with col2:
            st.markdown("##### Fellowship Period")
            if fellow["start_date"]:
                st.markdown(f"**Start Date:** {fellow['start_date']}")
            if fellow["end_date"]:
                st.markdown(f"**End Date:** {fellow['end_date']}")
            if fellow["last_check_in"]:
                st.markdown(f"**Last Check-in:** {fellow['last_check_in']} ({days_since_checkin} days ago)")

    # ── Background tab ───────────────────────────────────────────────────────────
    with tab_background:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Prior Role")
            if fellow["prior_role"]:
                st.markdown(fellow["prior_role"])
            else:
                st.caption("No prior role on record.")
        with col2:
            st.markdown("##### Education")
            if fellow["education"]:
                st.markdown(fellow["education"])
            else:
                st.caption("No education info on record.")
        if fellow["notes"]:
            st.markdown("##### Notes")
            st.markdown(
                f'<div style="background-color:#fffbeb;border:1px solid #fde68a;border-radius:0.5rem;'
                f'padding:0.75rem 1rem;font-size:0.9rem;color:#374151;line-height:1.6;">'
                f'{fellow["notes"]}</div>',
                unsafe_allow_html=True
            )

    # ── Status Reports tab ───────────────────────────────────────────────────────
    with tab_reports:
        if not fellow.get("requires_monthly_reports"):
            st.caption("This fellow does not require monthly status reports.")
        else:
            # Link to Google Sheet
            st.markdown(f"[📊 View All Responses in Google Sheet]({GOOGLE_SHEET_URL})")

            required_months = get_required_report_months(fellow)
            status_reports = fetch_status_reports(fellow["id"])
            streak_info = calculate_report_streak(status_reports, required_months)

            # Streak / status badges
            report_badges_html = ""
            if streak_info["streak"] > 0:
                report_badges_html += f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#f97316;color:#ffffff;margin-right:0.5rem;">🔥 Streak: {streak_info["streak"]}</span>'
            if streak_info["gift_card_eligible"]:
                report_badges_html += '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#22c55e;color:#ffffff;margin-right:0.5rem;">🎁 Gift Card Earned!</span>'
            if streak_info["at_risk"]:
                report_badges_html += '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#eab308;color:#ffffff;margin-right:0.5rem;">⚠️ At Risk</span>'
            if streak_info["reimbursements_paused"]:
                report_badges_html += '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#ef4444;color:#ffffff;margin-right:0.5rem;">🚫 Reimbursements Paused</span>'
            if report_badges_html:
                st.markdown(f'<div style="margin-bottom:1rem;">{report_badges_html}</div>', unsafe_allow_html=True)

            # Report rows
            submitted_months = {r["month"]: r for r in status_reports if r.get("submitted")}
            today = datetime.now()
            for month in required_months:
                try:
                    month_date = datetime.strptime(month, "%b %Y")
                    if month_date.month == 12:
                        last_day = datetime(month_date.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        last_day = datetime(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
                except:
                    continue

                is_submitted = month in submitted_months
                is_overdue = not is_submitted and last_day < today

                if is_submitted:
                    report = submitted_months[month]
                    st.markdown(f'<div style="background-color:#dcfce7;padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #22c55e;"><span style="color:#166534;font-weight:600;">✅ {month}</span> — Submitted {report.get("date_submitted", "")}</div>', unsafe_allow_html=True)
                elif is_overdue:
                    st.markdown(f'<div style="background-color:#fee2e2;padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #ef4444;"><span style="color:#991b1b;font-weight:600;">❌ {month}</span> — OVERDUE (was due {last_day.strftime("%b %d")})</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background-color:#f8fafc;padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #94a3b8;"><span style="color:#475569;font-weight:600;">⬜ {month}</span> — Due {last_day.strftime("%b %d")}</div>', unsafe_allow_html=True)

            # Mark as submitted form
            st.markdown("##### Mark Report as Submitted")
            with st.form(f"status_report_form_{fellow['id']}"):
                month_to_mark = st.selectbox("Month", required_months)
                date_submitted = st.date_input("Date Submitted", value=datetime.now())

                if st.form_submit_button("Mark Submitted", use_container_width=True):
                    existing_report = None
                    for r in status_reports:
                        if r.get("month") == month_to_mark:
                            existing_report = r
                            break

                    if existing_report:
                        if update_status_report(existing_report["id"], True, date_submitted.strftime("%Y-%m-%d")):
                            st.success(f"Marked {month_to_mark} as submitted!")
                            import time
                            time.sleep(1)
                            st.rerun()
                    else:
                        report_data = {
                            "fellow_id": fellow["id"],
                            "month": month_to_mark,
                            "submitted": True,
                            "date_submitted": date_submitted.strftime("%Y-%m-%d")
                        }
                        if add_status_report(report_data):
                            st.success(f"Marked {month_to_mark} as submitted!")
                            import time
                            time.sleep(1)
                            st.rerun()

    # ── Check-ins tab ────────────────────────────────────────────────────────────
    with tab_checkins:
        if st.button("+ Log Check-in", key=f"log_checkin_{fellow['id']}", use_container_width=True):
            st.session_state.show_checkin_form = True
            st.rerun()

        if st.session_state.show_checkin_form:
            with st.form(f"checkin_form_{fellow['id']}"):
                checkin_date = st.date_input("Date", value=datetime.now())
                checkin_type = st.selectbox("Check-in Type", ["Email", "Phone", "Zoom", "In-person", "Slack", "Text"])
                checkin_notes = st.text_area("Notes")
                staff_member = st.text_input("Staff Member")

                form_col1, form_col2 = st.columns(2)
                with form_col1:
                    if st.form_submit_button("Save", use_container_width=True):
                        checkin_data = {
                            "fellow_id": fellow["id"],
                            "date": checkin_date.strftime("%Y-%m-%d"),
                            "check_in_type": checkin_type,
                            "notes": checkin_notes,
                            "staff_member": staff_member
                        }
                        if add_checkin(checkin_data):
                            if update_fellow_checkin(fellow["id"], checkin_date.strftime("%Y-%m-%d")):
                                st.success("Check-in logged!")
                            else:
                                st.warning("Check-in logged but failed to update Last Check-in date")
                            st.session_state.show_checkin_form = False
                            import time
                            time.sleep(2)
                            st.rerun()
                with form_col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_checkin_form = False
                        st.rerun()

        if checkins:
            for checkin in checkins:
                st.markdown(f"""
                <div style="background-color:#f8fafc;padding:0.75rem;border-radius:0.5rem;margin-bottom:0.25rem;border-left:3px solid #3b82f6;">
                    <div style="font-weight:600;color:#1f2937;font-size:0.9rem;">{checkin['date']} • {checkin['check_in_type']}</div>
                    <div style="color:#4b5563;font-size:0.85rem;margin-top:0.25rem;">{checkin['notes']}</div>
                    <div style="color:#6b7280;font-size:0.75rem;margin-top:0.25rem;">— {checkin['staff_member']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Delete", key=f"delete_checkin_{checkin['id']}", use_container_width=True):
                    if delete_checkin(checkin["id"]):
                        st.success("Check-in deleted!")
                        import time
                        time.sleep(1)
                        st.rerun()
                st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
        else:
            st.caption("No check-ins recorded yet.")

    st.markdown("---")

    # Action buttons at bottom
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Edit Fellow", key=f"edit_modal_{fellow['id']}", use_container_width=True, type="primary"):
            st.session_state.editing_fellow = fellow
            st.session_state.modal_fellow_id = None
            st.rerun()
    with btn_col2:
        if st.button("Close", key=f"close_modal_{fellow['id']}", use_container_width=True):
            st.session_state.modal_fellow_id = None
            st.rerun()


def show_fellow_form():
    """Show add/edit fellow form"""
    is_editing = st.session_state.editing_fellow is not None
    fellow = st.session_state.editing_fellow or {}

    with st.form("fellow_form"):
        st.markdown(f"### {'Edit' if is_editing else 'Add New'} Fellow")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", value=fellow.get("name", ""))
            email = st.text_input("Email", value=fellow.get("email", ""))
            phone = st.text_input("Phone", value=fellow.get("phone", ""))
            linkedin = st.text_input("LinkedIn URL", value=fellow.get("linkedin", ""))

        with col2:
            fellow_type_options_edit = ["", "Congressional Innovation Fellow", "Senior Congressional Innovation Fellow", "AI Security Fellow"]
            fellow_type = st.selectbox(
                "Fellow Type",
                fellow_type_options_edit,
                index=fellow_type_options_edit.index(fellow.get("fellow_type", "")) if fellow.get("fellow_type", "") in fellow_type_options_edit else 0
            )
            party = st.selectbox(
                "Party",
                ["", "Democrat", "Republican", "Independent", "Institutional Office"],
                index=["", "Democrat", "Republican", "Independent", "Institutional Office"].index(fellow.get("party", "")) if fellow.get("party", "") in ["", "Democrat", "Republican", "Independent", "Institutional Office"] else 0
            )
            chamber = st.selectbox(
                "Chamber",
                ["", "Senate", "House"],
                index=["", "Senate", "House"].index(fellow.get("chamber", "")) if fellow.get("chamber", "") in ["", "Senate", "House"] else 0
            )
            status = st.selectbox(
                "Status",
                ["Active", "Flagged", "Ending Soon"],
                index=["Active", "Flagged", "Ending Soon"].index(fellow.get("status", "Active")) if fellow.get("status", "Active") in ["Active", "Flagged", "Ending Soon"] else 0
            )

        office = st.text_input("Office", value=fellow.get("office", ""), placeholder="e.g., Sen. Maria Cantwell (D-WA)")
        cohort = st.text_input("Cohort", value=fellow.get("cohort", ""), placeholder="e.g., 2025")

        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=_parse_date_value(fellow.get("start_date")),
                format="YYYY-MM-DD"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=_parse_date_value(fellow.get("end_date")),
                format="YYYY-MM-DD"
            )
        with col3:
            last_check_in = st.date_input(
                "Last Check-in",
                value=_parse_date_value(fellow.get("last_check_in")),
                format="YYYY-MM-DD"
            )

        prior_role = st.text_input("Prior Role", value=fellow.get("prior_role", ""), placeholder="e.g., ML Engineer at Google")
        education = st.text_input("Education", value=fellow.get("education", ""), placeholder="e.g., PhD Computer Science, Stanford")
        notes = st.text_area("Notes", value=fellow.get("notes", ""))

        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with col2:
            submit = st.form_submit_button(
                "Save" if is_editing else "Add Fellow",
                type="primary",
                use_container_width=True
            )

        if cancel:
            st.session_state.show_add_form = False
            st.session_state.editing_fellow = None
            st.rerun()

        if submit:
            if not name:
                st.error("Name is required")
            else:
                fellow_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "fellow_type": fellow_type,
                    "party": party,
                    "office": office,
                    "chamber": chamber,
                    "linkedin": linkedin,
                    "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
                    "end_date": end_date.strftime("%Y-%m-%d") if end_date else "",
                    "cohort": cohort,
                    "status": status,
                    "last_check_in": last_check_in.strftime("%Y-%m-%d") if last_check_in else "",
                    "prior_role": prior_role,
                    "education": education,
                    "notes": notes
                }

                if is_editing:
                    success = update_fellow(fellow["id"], fellow_data)
                    if success:
                        st.success("Fellow updated successfully!")
                        st.session_state.editing_fellow = None
                        st.rerun()
                    else:
                        st.error("Failed to update fellow")
                else:
                    success = create_fellow(fellow_data)
                    if success:
                        st.success("Fellow added successfully!")
                        st.session_state.show_add_form = False
                        st.rerun()
                    else:
                        st.error("Failed to add fellow")


if __name__ == "__main__":
    main()
