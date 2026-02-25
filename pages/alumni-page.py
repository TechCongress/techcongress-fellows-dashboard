import streamlit as st
from datetime import datetime
from helpers import (
    fetch_alumni, create_alumni, update_alumni,
    calculate_days_since
)

# ============ AUTH GUARD ============
if not st.session_state.get("authenticated"):
    st.warning("Please log in first.")
    st.stop()

# ============ SESSION STATE ============
if "alumni_show_add_form" not in st.session_state:
    st.session_state.alumni_show_add_form = False
if "alumni_editing" not in st.session_state:
    st.session_state.alumni_editing = None
if "alumni_modal_id" not in st.session_state:
    st.session_state.alumni_modal_id = None
if "alumni_trigger_modal" not in st.session_state:
    st.session_state.alumni_trigger_modal = False

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


# ============ HELPER FUNCTIONS ============

def get_fellow_type_badge(ft):
    """Return (label, bg_color, text_color) for a fellow type string."""
    ft_lower = ft.lower() if ft else ""
    if "senior" in ft_lower:
        return ("Senior CIF", "#6366f1", "#ffffff")
    elif "ai security" in ft_lower:
        return ("AISF", "#0891b2", "#ffffff")
    elif "congressional innovation scholar" in ft_lower:
        return ("CIS", "#059669", "#ffffff")
    elif "congressional digital service" in ft_lower:
        return ("CDSF", "#d97706", "#ffffff")
    else:
        return ("CIF", "#93c5fd", "#1e40af")


def get_sector_badge(sector):
    """Return (bg_color, text_color) for a sector."""
    sector_colors = {
        "Government": ("#dbeafe", "#1d4ed8"),
        "Nonprofit": ("#dcfce7", "#166534"),
        "Academia": ("#f3e8ff", "#7c3aed"),
        "Private": ("#ffedd5", "#9a3412"),
        "Policy/Think Tank": ("#fce7f3", "#9d174d"),
    }
    return sector_colors.get(sector, ("#f1f5f9", "#475569"))


def is_any_aisf(fellow_types):
    """Check if any of the fellow types is AI Security Fellow."""
    if not fellow_types:
        return False
    for ft in fellow_types:
        if "AI Security" in ft:
            return True
    return False


# ============ MAIN APP ============

def main():
    # Header
    st.image("TechCongress Logo (black).png", width=200)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("Alumni Network")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

    st.caption("Track and manage TechCongress alumni")

    btn_col, _ = st.columns([1, 4])
    with btn_col:
        if st.button("Add Alumni", type="primary", use_container_width=True):
            st.session_state.alumni_show_add_form = True
            st.session_state.alumni_editing = None
            st.rerun()

    # Fetch data
    with st.spinner("Loading alumni..."):
        alumni_list = fetch_alumni()

    # Show modal if an alumni is selected AND trigger is True
    if st.session_state.alumni_modal_id and st.session_state.alumni_trigger_modal:
        selected_alumni = next((a for a in alumni_list if a["id"] == st.session_state.alumni_modal_id), None)
        if selected_alumni:
            show_alumni_modal(selected_alumni)
        st.session_state.alumni_trigger_modal = False

    if not alumni_list:
        st.warning("No alumni found. Add your first alumni to get started!")
        if st.session_state.alumni_show_add_form:
            show_alumni_form()
        return

    # Calculate stats
    total = len(alumni_list)
    govt = len([a for a in alumni_list if a.get("sector") == "Government"])
    private = len([a for a in alumni_list if a.get("sector") == "Private"])
    nonprofit_academia = len([a for a in alumni_list if a.get("sector") in ["Nonprofit", "Academia"]])
    policy = len([a for a in alumni_list if a.get("sector") == "Policy/Think Tank"])

    # Stats row
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Alumni", total)
    with col2:
        st.metric("Government", govt)
    with col3:
        st.metric("Private Sector", private)
    with col4:
        st.metric("Nonprofit / Academia", nonprofit_academia)
    with col5:
        st.metric("Policy / Think Tank", policy)

    st.markdown("---")

    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            search = st.text_input("Search", placeholder="Name, org, or office...")
        with col2:
            fellow_type_options = ["All Types", "Congressional Innovation Fellow", "Senior Congressional Innovation Fellow", "Congressional Innovation Scholar", "Congressional Digital Service Fellow", "AI Security Fellow"]
            fellow_type_filter = st.selectbox("Fellow Type", fellow_type_options)
        with col3:
            sector_options = ["All Sectors", "Government", "Nonprofit", "Academia", "Private", "Policy/Think Tank"]
            sector_filter = st.selectbox("Sector", sector_options)
        with col4:
            party_options = ["All Parties", "Democrat", "Republican", "Independent"]
            party_filter = st.selectbox("Party", party_options)
        with col5:
            chamber_options = ["All Chambers", "Senate", "House", "Executive Branch"]
            chamber_filter = st.selectbox("Chamber", chamber_options)

        # Cohort filter + Sort
        col1, col2 = st.columns(2)
        with col1:
            cohorts = sorted(set([a["cohort"] for a in alumni_list if a.get("cohort")]), reverse=True)
            cohort_options = ["All Cohorts"] + cohorts
            cohort_filter = st.selectbox("Cohort", cohort_options)
        with col2:
            sort_options = ["Cohort (newest first)", "Cohort (oldest first)", "Name (A-Z)", "Name (Z-A)", "Last Engaged (oldest first)", "Last Engaged (newest first)", "Organization (A-Z)", "Sector"]
            sort_by = st.selectbox("Sort by", sort_options, index=0)

    # Apply filters
    filtered = alumni_list.copy()

    if search:
        search_lower = search.lower()
        filtered = [a for a in filtered if
            search_lower in a["name"].lower() or
            search_lower in (a.get("current_org") or "").lower() or
            search_lower in (a.get("office_served") or "").lower() or
            search_lower in (a.get("current_role") or "").lower()]

    if fellow_type_filter != "All Types":
        filtered = [a for a in filtered if fellow_type_filter in (a.get("fellow_types") or [])]

    if sector_filter != "All Sectors":
        filtered = [a for a in filtered if a.get("sector") == sector_filter]

    if party_filter != "All Parties":
        filtered = [a for a in filtered if a.get("party") == party_filter]

    if chamber_filter != "All Chambers":
        filtered = [a for a in filtered if a.get("chamber") == chamber_filter]

    if cohort_filter != "All Cohorts":
        filtered = [a for a in filtered if a.get("cohort") == cohort_filter]

    # Sort
    if sort_by == "Cohort (newest first)":
        filtered.sort(key=lambda a: a.get("cohort") or "", reverse=True)
    elif sort_by == "Cohort (oldest first)":
        filtered.sort(key=lambda a: a.get("cohort") or "")
    elif sort_by == "Name (A-Z)":
        filtered.sort(key=lambda a: a["name"].lower())
    elif sort_by == "Name (Z-A)":
        filtered.sort(key=lambda a: a["name"].lower(), reverse=True)
    elif sort_by == "Last Engaged (oldest first)":
        filtered.sort(key=lambda a: a.get("last_engaged") or "0000-00-00")
    elif sort_by == "Last Engaged (newest first)":
        filtered.sort(key=lambda a: a.get("last_engaged") or "0000-00-00", reverse=True)
    elif sort_by == "Organization (A-Z)":
        filtered.sort(key=lambda a: (a.get("current_org") or "").lower())
    elif sort_by == "Sector":
        filtered.sort(key=lambda a: a.get("sector") or "")

    # Show count
    st.caption(f"Showing {len(filtered)} of {total} alumni")

    # Show add/edit form if needed
    if st.session_state.alumni_show_add_form or st.session_state.alumni_editing:
        show_alumni_form()

    # Display alumni in cards
    cols = st.columns(3)
    for idx, alumni in enumerate(filtered):
        with cols[idx % 3]:
            show_alumni_card(alumni)


def show_alumni_card(alumni):
    """Display an alumni card."""
    fellow_types = alumni.get("fellow_types") or []
    aisf = is_any_aisf(fellow_types)

    # Build fellow type badges HTML
    type_badges_html = ""
    for ft in fellow_types:
        label, bg, text = get_fellow_type_badge(ft)
        type_badges_html += f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{bg};color:{text};margin-right:0.25rem;margin-bottom:0.25rem;">{label}</span>'

    # Party badge
    party_html = ""
    if alumni.get("party"):
        if alumni["party"] == "Republican":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#ef4444;color:#ffffff;">R</span>'
        elif alumni["party"] == "Democrat":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#3b82f6;color:#ffffff;">D</span>'
        elif alumni["party"] == "Independent":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#8b5cf6;color:#ffffff;">I</span>'
    elif aisf:
        party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#94a3b8;color:#ffffff;">Executive Branch</span>'

    # Sector badge
    sector_html = ""
    if alumni.get("sector"):
        s_bg, s_text = get_sector_badge(alumni["sector"])
        sector_html = f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{s_bg};color:{s_text};margin-top:0.25rem;">{alumni["sector"]}</span>'

    # Current role line
    role_html = ""
    if alumni.get("current_role") or alumni.get("current_org"):
        role_parts = []
        if alumni.get("current_role"):
            role_parts.append(alumni["current_role"])
        if alumni.get("current_org"):
            role_parts.append(alumni["current_org"])
        role_text = " @ ".join(role_parts) if len(role_parts) == 2 else role_parts[0]
        role_html = f'<div style="color:#374151;font-size:0.875rem;margin-bottom:0.25rem;font-weight:500;">{role_text}</div>'

    # Office served
    office_html = ""
    if alumni.get("office_served"):
        office_html = f'<div style="color:#6b7280;font-size:0.8rem;margin-bottom:0.25rem;">Served: {alumni["office_served"]}</div>'

    # Location
    location_html = ""
    if alumni.get("location"):
        location_html = f'<div style="color:#6b7280;font-size:0.8rem;">{alumni["location"]}</div>'

    # LinkedIn icon
    linkedin_html = ""
    if alumni.get("linkedin"):
        linkedin_html = f'<a href="{alumni["linkedin"]}" target="_blank" style="color:#0077b5;font-size:0.8rem;text-decoration:none;">LinkedIn</a>'

    # Do not contact indicator
    do_not_contact_html = ""
    if not alumni.get("contact", True):
        do_not_contact_html = '<div style="color:#dc2626;font-size:0.8rem;font-weight:600;margin-bottom:0.5rem;">⚠️ Do not contact</div>'

    card_html = f'<div style="background-color:white;padding:1.25rem;border-radius:0.75rem;border:1px solid #e5e7eb;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.1);"><div style="font-weight:600;font-size:1.1rem;margin-bottom:0.25rem;color:#1f2937;">{alumni["name"]}</div>{do_not_contact_html}<div style="color:#6b7280;font-size:0.875rem;margin-bottom:0.5rem;">Cohort: {alumni.get("cohort") or "N/A"}</div>{role_html}<div style="margin-bottom:0.5rem;">{type_badges_html}{party_html}</div>{office_html}<div style="margin-bottom:0.25rem;">{sector_html}</div>{location_html}{linkedin_html}</div>'

    st.markdown(card_html, unsafe_allow_html=True)

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View", key=f"alumni_view_{alumni['id']}", use_container_width=True):
            st.session_state.alumni_modal_id = alumni["id"]
            st.session_state.alumni_trigger_modal = True
            st.rerun()
    with col2:
        if st.button("Edit", key=f"alumni_edit_{alumni['id']}", use_container_width=True):
            st.session_state.alumni_editing = alumni
            st.session_state.alumni_show_add_form = False
            st.rerun()


@st.dialog("Alumni Details", width="large")
def show_alumni_modal(alumni):
    """Display alumni details in a modal dialog."""
    fellow_types = alumni.get("fellow_types") or []
    aisf = is_any_aisf(fellow_types)

    # Build fellow type badges
    type_badges_html = ""
    for ft in fellow_types:
        label, bg, text = get_fellow_type_badge(ft)
        type_badges_html += f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{bg};color:{text};margin-right:0.25rem;">{label}</span>'

    # Party badge
    party_html = ""
    if alumni.get("party"):
        if alumni["party"] == "Republican":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#ef4444;color:#ffffff;">R</span>'
        elif alumni["party"] == "Democrat":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#3b82f6;color:#ffffff;">D</span>'
        elif alumni["party"] == "Independent":
            party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#8b5cf6;color:#ffffff;">I</span>'
    elif aisf:
        party_html = '<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:#94a3b8;color:#ffffff;">Executive Branch</span>'

    # Sector badge
    sector_html = ""
    if alumni.get("sector"):
        s_bg, s_text = get_sector_badge(alumni["sector"])
        sector_html = f'<span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{s_bg};color:{s_text};">{alumni["sector"]}</span>'

    # Modal header
    fellow_type_display = ", ".join(fellow_types) if fellow_types else "Alumni"
    st.markdown(f"## {alumni['name']}")
    st.markdown(f"**Cohort {alumni.get('cohort') or 'N/A'}** • {fellow_type_display}")

    badges_html = f'{type_badges_html}{party_html} {sector_html}'
    st.markdown(f'<div style="margin-bottom:1rem;">{badges_html}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Two-column layout
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Contact")
        if alumni.get("email"):
            st.markdown(f"📧 [{alumni['email']}](mailto:{alumni['email']})")
        if alumni.get("phone"):
            st.markdown(f"📞 {alumni['phone']}")
        if alumni.get("linkedin"):
            st.markdown(f"🔗 [LinkedIn]({alumni['linkedin']})")
        if not alumni.get("email") and not alumni.get("phone") and not alumni.get("linkedin"):
            st.caption("No contact info")

        st.markdown("### Fellowship History")
        if fellow_types:
            st.markdown(f"**Fellow Type(s):** {', '.join(fellow_types)}")
        if alumni.get("office_served"):
            st.markdown(f"**Office Served:** {alumni['office_served']}")
        if alumni.get("chamber"):
            st.markdown(f"**Chamber:** {alumni['chamber']}")
        if alumni.get("party"):
            st.markdown(f"**Party:** {alumni['party']}")
        elif aisf:
            st.markdown("**Branch:** Executive Branch")

        st.markdown("### Background")
        if alumni.get("prior_role"):
            st.markdown(f"**Prior Role:** {alumni['prior_role']}")
        if alumni.get("education"):
            st.markdown(f"**Education:** {alumni['education']}")
        if not alumni.get("prior_role") and not alumni.get("education"):
            st.caption("No background info")

    with col2:
        st.markdown("### Current Info")
        if alumni.get("current_role"):
            st.markdown(f"**Role:** {alumni['current_role']}")
        if alumni.get("current_org"):
            st.markdown(f"**Organization:** {alumni['current_org']}")
        if alumni.get("sector"):
            st.markdown(f"**Sector:** {alumni['sector']}")
        if alumni.get("location"):
            st.markdown(f"**Location:** {alumni['location']}")
        if not alumni.get("current_role") and not alumni.get("current_org"):
            st.caption("No current info")

        st.markdown("### Engagement")
        if alumni.get("last_engaged"):
            days_ago = calculate_days_since(alumni["last_engaged"])
            st.markdown(f"**Last Engaged:** {alumni['last_engaged']} ({days_ago} days ago)")
        else:
            st.caption("No engagement date recorded")

    # Engagement Notes
    if alumni.get("engagement_notes"):
        st.markdown("#### Engagement Notes")
        st.markdown(alumni["engagement_notes"])

    # Notes
    if alumni.get("notes"):
        st.markdown("#### Notes")
        st.markdown(alumni["notes"])

    st.markdown("---")

    # Action buttons
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Edit Alumni", key=f"edit_modal_alumni_{alumni['id']}", use_container_width=True, type="primary"):
            st.session_state.alumni_editing = alumni
            st.session_state.alumni_modal_id = None
            st.rerun()
    with btn_col2:
        if st.button("Close", key=f"close_modal_alumni_{alumni['id']}", use_container_width=True):
            st.session_state.alumni_modal_id = None
            st.rerun()


def show_alumni_form():
    """Show add/edit alumni form."""
    is_editing = st.session_state.alumni_editing is not None
    alumni = st.session_state.alumni_editing or {}

    with st.form("alumni_form"):
        st.markdown(f"### {'Edit' if is_editing else 'Add New'} Alumni")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", value=alumni.get("name", ""))
            email = st.text_input("Email", value=alumni.get("email", ""))
            phone = st.text_input("Phone", value=alumni.get("phone", ""))
            linkedin = st.text_input("LinkedIn URL", value=alumni.get("linkedin", ""))

        with col2:
            fellow_type_all = [
                "Congressional Innovation Fellow",
                "Senior Congressional Innovation Fellow",
                "Congressional Innovation Scholar",
                "Congressional Digital Service Fellow",
                "AI Security Fellow"
            ]
            fellow_types = st.multiselect(
                "Fellow Type(s)",
                fellow_type_all,
                default=alumni.get("fellow_types", [])
            )
            party_options = ["", "Democrat", "Republican", "Independent"]
            party = st.selectbox(
                "Party",
                party_options,
                index=party_options.index(alumni.get("party", "")) if alumni.get("party", "") in party_options else 0
            )
            chamber_options = ["", "Senate", "House", "Executive Branch"]
            chamber = st.selectbox(
                "Chamber",
                chamber_options,
                index=chamber_options.index(alumni.get("chamber", "")) if alumni.get("chamber", "") in chamber_options else 0
            )

        col1, col2 = st.columns(2)
        with col1:
            cohort = st.text_input("Cohort", value=alumni.get("cohort", ""), placeholder="e.g., 2020")
            office_served = st.text_input("Office Served", value=alumni.get("office_served", ""), placeholder="e.g., Sen. Maria Cantwell (D-WA)")
        with col2:
            current_role = st.text_input("Current Role", value=alumni.get("current_role", ""))
            current_org = st.text_input("Current Organization", value=alumni.get("current_org", ""))

        prior_role = st.text_input("Prior Role", value=alumni.get("prior_role", ""), placeholder="Role before becoming a fellow")
        education = st.text_input("Education", value=alumni.get("education", ""), placeholder="e.g., PhD Computer Science, Stanford")

        col1, col2 = st.columns(2)
        with col1:
            sector_options = ["", "Government", "Nonprofit", "Academia", "Private", "Policy/Think Tank"]
            sector = st.selectbox(
                "Sector",
                sector_options,
                index=sector_options.index(alumni.get("sector", "")) if alumni.get("sector", "") in sector_options else 0
            )
        with col2:
            location = st.text_input("Location", value=alumni.get("location", ""), placeholder="e.g., Washington, DC")

        # Engagement
        last_engaged = st.date_input(
            "Last Engaged",
            value=datetime.strptime(alumni["last_engaged"], "%Y-%m-%d") if alumni.get("last_engaged") else None,
            format="YYYY-MM-DD"
        )
        engagement_notes = st.text_area("Engagement Notes", value=alumni.get("engagement_notes", ""))
        notes = st.text_area("Notes", value=alumni.get("notes", ""))

        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with col2:
            submit = st.form_submit_button(
                "Save" if is_editing else "Add Alumni",
                type="primary",
                use_container_width=True
            )

        if cancel:
            st.session_state.alumni_show_add_form = False
            st.session_state.alumni_editing = None
            st.rerun()

        if submit:
            if not name:
                st.error("Name is required")
            else:
                alumni_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "cohort": cohort,
                    "fellow_types": fellow_types,
                    "office_served": office_served,
                    "chamber": chamber,
                    "party": party,
                    "current_role": current_role,
                    "current_org": current_org,
                    "sector": sector,
                    "location": location,
                    "linkedin": linkedin,
                    "last_engaged": last_engaged.strftime("%Y-%m-%d") if last_engaged else "",
                    "engagement_notes": engagement_notes,
                    "notes": notes,
                    "prior_role": prior_role,
                    "education": education
                }

                if is_editing:
                    success = update_alumni(alumni["id"], alumni_data)
                    if success:
                        st.success("Alumni updated successfully!")
                        st.session_state.alumni_editing = None
                        st.rerun()
                    else:
                        st.error("Failed to update alumni")
                else:
                    success = create_alumni(alumni_data)
                    if success:
                        st.success("Alumni added successfully!")
                        st.session_state.alumni_show_add_form = False
                        st.rerun()
                    else:
                        st.error("Failed to add alumni")


if __name__ == "__main__":
    main()
