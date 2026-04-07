import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from styles import get_css
from helpers import (
    fetch_fellows, create_fellow, update_fellow, update_fellow_checkin,
    fetch_checkins, add_checkin, delete_checkin,
    fetch_status_reports, add_status_report, update_status_report,
    get_required_report_months, calculate_report_streak,
    calculate_days_since, calculate_days_until, GOOGLE_SHEET_URL,
    FORM_RESPONSES_URL,
    fetch_events, fetch_all_event_attendance, get_quarter_compliance,
    _date_to_quarter, _is_tracked_cohort,
    create_alumni,
)

EVENT_TYPE_COLORS = {
    "Happy Hour":        {"bg": "#dbeafe", "text": "#1d4ed8", "dot": "#3b82f6"},
    "Site Visit":        {"bg": "#dcfce7", "text": "#166534", "dot": "#22c55e"},
    "Social":            {"bg": "#ffedd5", "text": "#9a3412", "dot": "#f97316"},
    "Career Development":{"bg": "#f3e8ff", "text": "#7c3aed", "dot": "#8b5cf6"},
    "Speaker Series":    {"bg": "#fef9c3", "text": "#854d0e", "dot": "#eab308"},
    "Check-ins":         {"bg": "#f1f5f9", "text": "#475569", "dot": "#94a3b8"},
    "Conference":        {"bg": "#fee2e2", "text": "#991b1b", "dot": "#ef4444"},
    "Recruitment":       {"bg": "#f3f4f6", "text": "#374151", "dot": "#6b7280"},
}

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
if "trigger_alumni_dialog" not in st.session_state:
    st.session_state.trigger_alumni_dialog = False
if "alumni_source_fellow" not in st.session_state:
    st.session_state.alumni_source_fellow = None

# ============ CUSTOM CSS ============
st.markdown(get_css(), unsafe_allow_html=True)


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

    # Show Move to Alumni dialog if triggered
    if st.session_state.trigger_alumni_dialog and st.session_state.alumni_source_fellow:
        show_move_to_alumni_dialog(st.session_state.alumni_source_fellow)
        st.session_state.trigger_alumni_dialog = False
        st.session_state.alumni_source_fellow = None

    if not fellows:
        st.warning("No fellows found. Add your first fellow to get started!")
        if st.session_state.show_add_form:
            show_fellow_form()
        return

    # Exclude withdrawn/alumni fellows from stats and default view
    INACTIVE_STATUSES = ["Withdrew", "Alumni"]
    active_fellows = [f for f in fellows if f["status"] not in INACTIVE_STATUSES]

    # Calculate stats (active fellows only)
    total = len(active_fellows)
    on_track = len([f for f in active_fellows if f["status"] in ["on-track", "Active"]])
    flagged = len([f for f in active_fellows if f["status"] in ["flagged", "Flagged"]])
    ending_soon = len([f for f in active_fellows if f["status"] in ["ending-soon", "Ending Soon"]])
    needs_checkin = len([f for f in active_fellows if calculate_days_since(f["last_check_in"]) > 210 and f["status"] in ["on-track", "Active"] and "AI Security" not in (f.get("fellow_type") or "")])

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

    # ── Fellow Breakdown Charts ──────────────────────────────────────────────
    def make_pie(title, labels, values, colors):
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
            textinfo="percent",
            textfont=dict(size=12, color="#ffffff"),
            hovertemplate="%{label}: %{value} fellow(s)<extra></extra>",
            hole=0,
            domain=dict(x=[0, 0.55]),
        ))
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=13, color="#6b7280", family="system-ui, -apple-system, sans-serif"),
                x=0, xanchor="left", pad=dict(l=14, t=6),
            ),
            margin=dict(t=40, b=20, l=16, r=16),
            height=260,
            showlegend=True,
            legend=dict(
                orientation="v",
                font=dict(size=12, color="#6b7280"),
                x=0.58, y=0.5, xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Build data from live fellows list
    party_counts = {}
    chamber_counts = {}
    type_counts = {}

    for f in active_fellows:
        p = f.get("party")
        if p:  # skip fellows with no party (e.g. AISF)
            party_counts[p] = party_counts.get(p, 0) + 1

        is_aisf_fellow = "AI Security" in (f.get("fellow_type") or "")
        c = "Executive Branch" if is_aisf_fellow else (f.get("chamber") or "Unknown")
        chamber_counts[c] = chamber_counts.get(c, 0) + 1

        ft = f.get("fellow_type") or "Unknown"
        if "Senior" in ft:
            ft = "Senior CIF"
        elif "AI Security" in ft:
            ft = "AISF"
        elif ft != "Unknown":
            ft = "CIF"
        type_counts[ft] = type_counts.get(ft, 0) + 1

    PARTY_COLORS = {
        "Democrat": "#3b82f6",
        "Republican": "#ef4444",
        "Independent": "#8b5cf6",
        "Institutional Office": "#64748b",
        "Unknown": "#d1d5db",
    }
    CHAMBER_COLORS = {"Senate": "#0891b2", "House": "#0d9488", "Executive Branch": "#94a3b8", "Unknown": "#d1d5db"}
    TYPE_COLORS = {"Senior CIF": "#6366f1", "CIF": "#93c5fd", "AISF": "#0891b2", "Unknown": "#d1d5db"}

    chart_col1, chart_col2, chart_col3 = st.columns(3)

    with chart_col1:
        st.plotly_chart(
            make_pie("By Party", list(party_counts.keys()), list(party_counts.values()),
                     [PARTY_COLORS.get(k, "#d1d5db") for k in party_counts]),
            use_container_width=True, config={"displayModeBar": False},
        )

    with chart_col2:
        st.plotly_chart(
            make_pie("By Chamber", list(chamber_counts.keys()), list(chamber_counts.values()),
                     [CHAMBER_COLORS.get(k, "#d1d5db") for k in chamber_counts]),
            use_container_width=True, config={"displayModeBar": False},
        )

    with chart_col3:
        st.plotly_chart(
            make_pie("By Fellow Type", list(type_counts.keys()), list(type_counts.values()),
                     [TYPE_COLORS.get(k, "#d1d5db") for k in type_counts]),
            use_container_width=True, config={"displayModeBar": False},
        )

    st.markdown("---")

    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            search = st.text_input("Search", placeholder="Name or office...")
        with col2:
            status_options = ["All Active", "Active", "Flagged", "Ending Soon", "Withdrew"]
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

    # Apply filters — base list depends on status filter
    if status_filter == "All Active":
        filtered_fellows = active_fellows.copy()
    elif status_filter == "Withdrew":
        filtered_fellows = [f for f in fellows if f["status"] == "Withdrew"]
    else:
        filtered_fellows = [f for f in active_fellows if f["status"] == status_filter]

    if search:
        search_lower = search.lower()
        filtered_fellows = [f for f in filtered_fellows if
            search_lower in f["name"].lower() or
            search_lower in f["office"].lower()]

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
            status_priority = {"flagged": 0, "Flagged": 0, "ending-soon": 1, "Ending Soon": 1, "on-track": 2, "Active": 2, "Withdrew": 4}.get(f["status"], 3)
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
    if status_filter == "Withdrew":
        st.caption(f"Showing {len(filtered_fellows)} withdrawn fellow(s)")
    else:
        st.caption(f"Showing {len(filtered_fellows)} of {total} active fellows")

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
        "Ending Soon": ("#f87171", "#991b1b"),
        "Withdrew": ("#e5e7eb", "#6b7280"),
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
        office_html = f'<div style="color:var(--tc-text4);font-size:0.875rem;margin-bottom:0.25rem;">{fellow["office"]}</div>'

    term_html = ""
    if fellow["start_date"] and fellow["end_date"]:
        term_html = f'<div style="color:var(--tc-text2);font-size:0.8rem;margin-bottom:0.25rem;">Fellowship Term: {fellow["start_date"]} - {fellow["end_date"]}</div>'

    checkin_html = ""
    if fellow["last_check_in"]:
        checkin_html = f'<div style="color:var(--tc-text2);font-size:0.8rem;">Last check-in: {fellow["last_check_in"]}</div>'

    card_html = f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;border:1px solid var(--tc-border);margin-bottom:1rem;box-shadow:0 1px 3px var(--tc-shadow);display:flex;flex-direction:column;min-height:240px;"><div style="font-weight:600;font-size:1.1rem;margin-bottom:0.25rem;color:var(--tc-text);">{fellow["name"]}</div><div style="color:var(--tc-text2);font-size:0.875rem;margin-bottom:0.75rem;">Cohort: {fellow["cohort"]}</div><div style="margin-bottom:0.5rem;"><span style="display:inline-block;padding:0.25rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:500;background-color:{bg_color};color:{text_color};">{status_label}</span>{checkin_badge}</div><div style="margin-bottom:0.5rem;">{type_html}{party_html}</div><div style="margin-top:auto;">{office_html}{term_html}{checkin_html}</div></div>'

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
        "Ending Soon": ("#f87171", "#991b1b"),
        "Withdrew": ("#e5e7eb", "#6b7280"),
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
     tab_reports, tab_checkins, tab_events) = st.tabs([
        "Contact",
        "Placement",
        "Background",
        "Status Reports",
        f"Check-ins ({checkin_count})",
        "Events",
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
            if fellow.get("supervisor_email"):
                st.markdown(f"**Supervisor's Email:** [{fellow['supervisor_email']}](mailto:{fellow['supervisor_email']})")
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
                f'<div style="background:var(--tc-note-bg);border:1px solid var(--tc-note-border);border-radius:0.5rem;'
                f'padding:0.75rem 1rem;font-size:0.9rem;color:var(--tc-text4);line-height:1.6;">'
                f'{fellow["notes"]}</div>',
                unsafe_allow_html=True
            )

    # ── Status Reports tab ───────────────────────────────────────────────────────
    with tab_reports:
        if not fellow.get("requires_monthly_reports"):
            st.caption("This fellow does not require monthly status reports.")
        else:
            # Link to the form responses sheet
            st.markdown(f"[📊 View All Responses in Google Sheet]({FORM_RESPONSES_URL})")

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
                    st.markdown(f'<div style="background:var(--tc-present-bg);padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #22c55e;"><span style="color:var(--tc-present-text);font-weight:600;">✅ {month}</span><span style="color:var(--tc-text4);"> — Submitted {report.get("date_submitted", "")}</span></div>', unsafe_allow_html=True)
                elif is_overdue:
                    st.markdown(f'<div style="background:var(--tc-absent-bg);padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #ef4444;"><span style="color:var(--tc-absent-text);font-weight:600;">❌ {month}</span><span style="color:var(--tc-text4);"> — OVERDUE (was due {last_day.strftime("%b %d")})</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:var(--tc-surface2);padding:0.5rem 0.75rem;border-radius:0.5rem;margin-bottom:0.5rem;border-left:3px solid #94a3b8;"><span style="color:var(--tc-text4);font-weight:600;">⬜ {month}</span><span style="color:var(--tc-text2);"> — Due {last_day.strftime("%b %d")}</span></div>', unsafe_allow_html=True)

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
                            "fellow_name": fellow["name"],
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
                st.markdown(
                    f'<div style="background:var(--tc-checkin-bg);padding:0.75rem;border-radius:0.5rem;margin-bottom:0.25rem;border-left:3px solid #3b82f6;">'
                    f'<div style="font-weight:600;color:var(--tc-text);font-size:0.9rem;">{checkin["date"]} • {checkin["check_in_type"]}</div>'
                    f'<div style="color:var(--tc-text4);font-size:0.85rem;margin-top:0.25rem;">{checkin["notes"]}</div>'
                    f'<div style="color:var(--tc-text2);font-size:0.75rem;margin-top:0.25rem;">— {checkin["staff_member"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Delete", key=f"delete_checkin_{checkin['id']}", use_container_width=True):
                    if delete_checkin(checkin["id"]):
                        st.success("Check-in deleted!")
                        import time
                        time.sleep(1)
                        st.rerun()
                st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
        else:
            st.caption("No check-ins recorded yet.")

    # ── Events tab ───────────────────────────────────────────────────────────
    with tab_events:
        if fellow.get("fellow_type") == "AISF" or not _is_tracked_cohort(fellow.get("cohort", "")):
            st.caption("Events attendance tracking applies to Jan 2026 CIF/SCIF fellows and future cohorts only.")
        else:
            all_events = fetch_events()
            all_attendance = fetch_all_event_attendance()
            all_fellows = fetch_fellows()

            compliance = get_quarter_compliance([fellow], all_events, all_attendance)
            qc = compliance.get(fellow["id"], {})
            quarters = sorted(qc.keys())

            # Quarterly compliance pills
            if quarters:
                pills_html = ""
                for q in quarters:
                    status = qc[q]
                    bg = "#dcfce7" if status == "met" else "#fee2e2"
                    text = "#166534" if status == "met" else "#991b1b"
                    icon = "✓" if status == "met" else "✗"
                    pills_html += (
                        f'<span style="display:inline-block;padding:0.25rem 0.7rem;'
                        f'border-radius:9999px;font-size:0.78rem;font-weight:600;'
                        f'background:{bg};color:{text};margin-right:0.35rem;">'
                        f'{icon} {q}</span>'
                    )
                st.markdown(
                    f'<div style="margin-bottom:1rem;">{pills_html}</div>',
                    unsafe_allow_html=True,
                )
                st.caption("Fellows must attend ≥1 required event per quarter.")
            else:
                st.caption("No past required events yet — check back after the first event.")

            st.markdown("<div style='margin:0.75rem 0;'></div>", unsafe_allow_html=True)

            # Event history
            fellow_att = {r["event_id"]: r["attended"] for r in all_attendance
                          if r["fellow_id"] == fellow["id"]}
            past_events = sorted(
                [e for e in all_events
                 if _parse_date_value(e["date"]) and _parse_date_value(e["date"]) < datetime.now().date()],
                key=lambda e: (_parse_date_value(e["date"]) or datetime.min.date()),
            )

            if not past_events:
                st.caption("No past events yet.")
            else:
                st.markdown("**Event History**")
                for e in past_events:
                    attended = fellow_att.get(e["id"])
                    if attended is None:
                        badge_bg, badge_color, badge_text = "#f3f4f6", "#6b7280", "— No record"
                    elif attended:
                        badge_bg, badge_color, badge_text = "#dcfce7", "#166534", "✓ Attended"
                    else:
                        badge_bg, badge_color, badge_text = "#fee2e2", "#991b1b", "✗ Absent"
                    dot = EVENT_TYPE_COLORS.get(e["type"], {}).get("dot", "#6366f1")
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:0.6rem;'
                        f'margin-bottom:0.4rem;">'
                        f'<div style="width:7px;height:7px;border-radius:50%;'
                        f'background:{dot};flex-shrink:0;"></div>'
                        f'<span style="font-size:0.85rem;color:var(--tc-text4);flex:1;">{e["name"]}</span>'
                        f'<span style="font-size:0.75rem;color:var(--tc-text3);">{e.get("quarter","")}</span>'
                        f'<span style="display:inline-block;padding:0.2rem 0.6rem;'
                        f'border-radius:9999px;font-size:0.75rem;font-weight:600;'
                        f'background:{badge_bg};color:{badge_color};">{badge_text}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("---")

    # Action buttons at bottom
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("Edit Fellow", key=f"edit_modal_{fellow['id']}", use_container_width=True, type="primary"):
            st.session_state.editing_fellow = fellow
            st.session_state.modal_fellow_id = None
            st.rerun()
    with btn_col2:
        if st.button("Move to Alumni", key=f"move_alumni_{fellow['id']}", use_container_width=True):
            st.session_state.trigger_alumni_dialog = True
            st.session_state.alumni_source_fellow = fellow
            st.session_state.modal_fellow_id = None
            st.rerun()
    with btn_col3:
        if st.button("Close", key=f"close_modal_{fellow['id']}", use_container_width=True):
            st.session_state.modal_fellow_id = None
            st.rerun()


@st.dialog("Move to Alumni", width="large")
def show_move_to_alumni_dialog(fellow):
    """Pre-filled alumni creation dialog triggered from fellow modal."""
    st.markdown(f"### Move {fellow['name']} to Alumni")
    st.caption("Confirm or fill in the details below. This will create an alumni record and mark this fellow as Alumni.")

    with st.form("move_to_alumni_form"):
        col1, col2 = st.columns(2)

        with col1:
            alumni_name = st.text_input("Name *", value=fellow.get("name", ""))
            alumni_email = st.text_input("Email", value=fellow.get("email", ""))
            alumni_phone = st.text_input("Phone", value=fellow.get("phone", ""))
            alumni_linkedin = st.text_input("LinkedIn URL", value=fellow.get("linkedin", ""))
            alumni_cohort = st.text_input("Cohort", value=fellow.get("cohort", ""))

        with col2:
            fellow_type_options = [
                "Congressional Innovation Fellow",
                "Senior Congressional Innovation Fellow",
                "AI Security Fellow",
            ]
            current_type = fellow.get("fellow_type", "")
            fellow_types_default = [current_type] if current_type in fellow_type_options else []
            fellow_types = st.multiselect("Fellow Type(s)", fellow_type_options, default=fellow_types_default)

            party_opts = ["", "Democrat", "Republican", "Independent", "Institutional Office"]
            alumni_party = st.selectbox(
                "Party",
                party_opts,
                index=party_opts.index(fellow.get("party", "")) if fellow.get("party", "") in party_opts else 0,
            )
            chamber_opts = ["", "Senate", "House", "Executive Branch"]
            alumni_chamber = st.selectbox(
                "Chamber",
                chamber_opts,
                index=chamber_opts.index(fellow.get("chamber", "")) if fellow.get("chamber", "") in chamber_opts else 0,
            )
            sector_opts = ["", "Government", "Nonprofit/Think Tank", "Academia", "Private Sector", "Other"]
            alumni_sector = st.selectbox("Current Sector", sector_opts)

        alumni_office_served = st.text_input("Office Served", value=fellow.get("office", ""))
        alumni_current_role = st.text_input("Current Role", placeholder="e.g., Policy Director at CSIS")
        alumni_location = st.text_input("Location", placeholder="e.g., Washington, DC")
        alumni_education = st.text_input("Education", value=fellow.get("education", ""))
        alumni_prior_role = st.text_input("Prior Role", value=fellow.get("prior_role", ""))

        chk_col1, chk_col2 = st.columns(2)
        with chk_col1:
            alumni_on_hill = st.checkbox("Currently on the Hill?", value=False)
        with chk_col2:
            alumni_contact = st.checkbox("Keep in contact?", value=True)

        alumni_notes = st.text_area("Notes", value=fellow.get("notes", ""))

        form_col1, form_col2 = st.columns(2)
        with form_col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with form_col2:
            confirm = st.form_submit_button("Move to Alumni", type="primary", use_container_width=True)

        if cancel:
            st.rerun()

        if confirm:
            if not alumni_name:
                st.error("Name is required.")
            else:
                alumni_data = {
                    "name": alumni_name,
                    "email": alumni_email,
                    "phone": alumni_phone,
                    "cohort": alumni_cohort,
                    "fellow_types": fellow_types,
                    "party": alumni_party,
                    "office_served": alumni_office_served,
                    "chamber": alumni_chamber,
                    "education": alumni_education,
                    "prior_role": alumni_prior_role,
                    "current_role": alumni_current_role,
                    "currently_on_hill": alumni_on_hill,
                    "sector": alumni_sector,
                    "location": alumni_location,
                    "contact": alumni_contact,
                    "linkedin": alumni_linkedin,
                    "last_engaged": "",
                    "engagement_notes": "",
                    "notes": alumni_notes,
                }
                alumni_created = create_alumni(alumni_data)
                if alumni_created:
                    fellow_update = dict(fellow)
                    fellow_update["status"] = "Alumni"
                    if update_fellow(fellow["id"], fellow_update):
                        st.success(f"{alumni_name} has been moved to alumni!")
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning("Alumni record created but failed to update fellow status. Please set status to Alumni manually.")
                else:
                    st.error("Failed to create alumni record. Please try again.")


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
            congressional_email = st.text_input("Congressional Email", value=fellow.get("congressional_email", ""), placeholder="e.g., firstname.lastname@mail.house.gov")
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
            status_form_opts = ["Active", "Flagged", "Ending Soon", "Withdrew"]
            status = st.selectbox(
                "Status",
                status_form_opts,
                index=status_form_opts.index(fellow.get("status", "Active")) if fellow.get("status", "Active") in status_form_opts else 0
            )

        office = st.text_input("Office", value=fellow.get("office", ""), placeholder="e.g., Sen. Maria Cantwell (D-WA)")
        supervisor_email = st.text_input("Supervisor's Email", value=fellow.get("supervisor_email", ""), placeholder="e.g., supervisor@mail.house.gov")
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
                    "congressional_email": congressional_email,
                    "phone": phone,
                    "fellow_type": fellow_type,
                    "party": party,
                    "office": office,
                    "supervisor_email": supervisor_email,
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
