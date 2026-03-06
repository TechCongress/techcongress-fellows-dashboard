import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from helpers import (
    fetch_alumni, create_alumni, update_alumni,
    calculate_days_since
)
from styles import get_css

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
st.markdown(get_css(), unsafe_allow_html=True)


# ============ HELPER FUNCTIONS ============

def get_fellow_type_badge(ft):
    """Return (label, css_class) for a fellow type string."""
    ft_lower = ft.lower() if ft else ""
    if "senior" in ft_lower:
        return ("Senior CIF", "tc-badge-indigo")
    elif "ai security" in ft_lower:
        return ("AISF", "tc-badge-cyan")
    elif "congressional innovation scholar" in ft_lower:
        return ("CIS", "tc-badge-emerald")
    elif "congressional digital service" in ft_lower:
        return ("CDSF", "tc-badge-amber")
    else:
        return ("CIF", "tc-badge-blue")


def get_sector_badge(sector):
    """Return a CSS class name for a sector."""
    sector_map = {
        "Government":           "tc-badge-blue",
        "Nonprofit/Think Tank": "tc-badge-green",
        "Academia":             "tc-badge-purple",
        "Private":              "tc-badge-orange",
        "Policy/Think Tank":    "tc-badge-pink",
    }
    return sector_map.get(sector, "tc-badge-gray")


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
    nonprofit_academia = len([a for a in alumni_list if a.get("sector") in ["Nonprofit/Think Tank", "Academia"]])
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
        st.metric("Nonprofit & Academia", nonprofit_academia)
    with col5:
        st.metric("Policy / Think Tank", policy)

    # ── Alumni Breakdown Charts ──────────────────────────────────────────────
    def make_pie(title, labels, values, colors, note=None):
        display_title = f"{title} ⓘ" if note else title
        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
            textinfo="percent",
            textfont=dict(size=12, color="#ffffff"),
            hovertemplate="%{label}: %{value} alumni<extra></extra>",
            hole=0,
            domain=dict(x=[0, 0.55]),
        ))
        fig.update_layout(
            title=dict(
                text=display_title,
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
        if note:
            fig.add_annotation(
                text=note,
                xref="paper", yref="paper",
                x=0, y=-0.02,
                showarrow=False,
                font=dict(size=10, color="#9ca3af"),
                xanchor="left",
            )
        return fig

    # Build data from live alumni list
    party_counts = {}
    type_counts = {}
    sector_counts = {}

    for a in alumni_list:
        raw_party = a.get("party") or ""
        for p in [x.strip() for x in raw_party.split(",") if x.strip()]:
            party_counts[p] = party_counts.get(p, 0) + 1

        for ft in (a.get("fellow_types") or []):
            ft = ft.strip()
            if "Senior" in ft:
                label = "Senior CIF"
            elif "AI Security" in ft:
                label = "AISF"
            elif "Scholar" in ft:
                label = "CIS"
            elif "Digital Service" in ft:
                label = "CDSF"
            else:
                label = "CIF"
            type_counts[label] = type_counts.get(label, 0) + 1

        s = a.get("sector") or "Unknown"
        sector_counts[s] = sector_counts.get(s, 0) + 1

    PARTY_COLORS = {
        "Democrat": "#3b82f6", "Republican": "#ef4444",
        "Independent": "#8b5cf6", "Institutional Office": "#64748b",
    }
    TYPE_COLORS = {
        "CIF": "#93c5fd", "Senior CIF": "#6366f1",
        "AISF": "#0891b2", "CIS": "#f59e0b", "CDSF": "#10b981",
    }
    SECTOR_COLORS = {
        "Government": "#3b82f6", "Private": "#8b5cf6",
        "Nonprofit/Think Tank": "#22c55e", "Academia": "#f59e0b",
        "Policy/Think Tank": "#0891b2", "Unknown": "#d1d5db",
    }

    chart_col1, chart_col2, chart_col3 = st.columns(3)

    with chart_col1:
        st.plotly_chart(
            make_pie("By Party", list(party_counts.keys()), list(party_counts.values()),
                     [PARTY_COLORS.get(k, "#d1d5db") for k in party_counts],
                     note="Alumni with multiple affiliations are counted in each category"),
            use_container_width=True, config={"displayModeBar": False},
        )

    with chart_col2:
        st.plotly_chart(
            make_pie("By Fellow Type", list(type_counts.keys()), list(type_counts.values()),
                     [TYPE_COLORS.get(k, "#d1d5db") for k in type_counts]),
            use_container_width=True, config={"displayModeBar": False},
        )

    with chart_col3:
        st.plotly_chart(
            make_pie("By Sector", list(sector_counts.keys()), list(sector_counts.values()),
                     [SECTOR_COLORS.get(k, "#d1d5db") for k in sector_counts]),
            use_container_width=True, config={"displayModeBar": False},
        )

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
            sector_options = ["All Sectors", "Government", "Nonprofit/Think Tank", "Academia", "Private", "Policy/Think Tank"]
            sector_filter = st.selectbox("Sector", sector_options)
        with col4:
            party_options = ["All Parties", "Democrat", "Republican", "Independent", "Institutional Office"]
            party_filter = st.selectbox("Party", party_options)
        with col5:
            chamber_options = ["All Chambers", "Senate", "House", "Executive Branch"]
            chamber_filter = st.selectbox("Chamber", chamber_options)

        # Cohort filter + Sort
        col1, col2 = st.columns(2)
        with col1:
            cohorts = sorted(set([a["cohort"] for a in alumni_list if a.get("cohort")]), key=_cohort_sort_key, reverse=True)
            cohort_options = ["All Cohorts"] + cohorts
            cohort_filter = st.selectbox("Cohort", cohort_options)
        with col2:
            sort_options = ["Cohort (newest first)", "Cohort (oldest first)", "Name (A-Z)", "Name (Z-A)", "Last Engaged (oldest first)", "Last Engaged (newest first)", "Current Role (A-Z)", "Sector"]
            sort_by = st.selectbox("Sort by", sort_options, index=0)

    # Apply filters
    filtered = alumni_list.copy()

    if search:
        search_lower = search.lower()
        filtered = [a for a in filtered if
            search_lower in a["name"].lower() or
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
        filtered.sort(key=lambda a: _cohort_sort_key(a.get("cohort") or ""), reverse=True)
    elif sort_by == "Cohort (oldest first)":
        filtered.sort(key=lambda a: _cohort_sort_key(a.get("cohort") or ""))
    elif sort_by == "Name (A-Z)":
        filtered.sort(key=lambda a: a["name"].lower())
    elif sort_by == "Name (Z-A)":
        filtered.sort(key=lambda a: a["name"].lower(), reverse=True)
    elif sort_by == "Last Engaged (oldest first)":
        filtered.sort(key=lambda a: a.get("last_engaged") or "0000-00-00")
    elif sort_by == "Last Engaged (newest first)":
        filtered.sort(key=lambda a: a.get("last_engaged") or "0000-00-00", reverse=True)
    elif sort_by == "Current Role (A-Z)":
        filtered.sort(key=lambda a: (a.get("current_role") or "").lower())
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
        label, cls = get_fellow_type_badge(ft)
        type_badges_html += f'<span class="tc-badge {cls}">{label}</span>'

    # Party badge
    party_html = ""
    if alumni.get("party"):
        if alumni["party"] == "Republican":
            party_html = '<span class="tc-badge" style="background:#ef4444;color:#fff;">R</span>'
        elif alumni["party"] == "Democrat":
            party_html = '<span class="tc-badge" style="background:#3b82f6;color:#fff;">D</span>'
        elif alumni["party"] == "Independent":
            party_html = '<span class="tc-badge" style="background:#8b5cf6;color:#fff;">I</span>'
        elif alumni["party"] == "Institutional Office":
            party_html = '<span class="tc-badge" style="background:#64748b;color:#fff;">Institutional</span>'
    elif aisf:
        party_html = '<span class="tc-badge" style="background:#64748b;color:#fff;">Executive Branch</span>'

    # Sector badge
    sector_html = ""
    if alumni.get("sector"):
        s_cls = get_sector_badge(alumni["sector"])
        sector_html = f'<span class="tc-badge {s_cls}">{alumni["sector"]}</span>'

    # Current role line
    role_html = ""
    if alumni.get("current_role"):
        role_html = f'<div style="color:var(--tc-text4);font-size:0.875rem;margin-bottom:0.25rem;font-weight:500;">{alumni["current_role"]}</div>'

    # Office served
    office_html = ""
    if alumni.get("office_served"):
        office_html = f'<div style="color:var(--tc-text2);font-size:0.8rem;margin-bottom:0.25rem;">Served: {alumni["office_served"]}</div>'

    # Location
    location_html = ""
    if alumni.get("location"):
        location_html = f'<div style="color:var(--tc-text2);font-size:0.8rem;">{alumni["location"]}</div>'

    # LinkedIn icon
    linkedin_html = ""
    if alumni.get("linkedin"):
        linkedin_html = f'<a href="{alumni["linkedin"]}" target="_blank" style="color:#0077b5;font-size:0.8rem;text-decoration:none;">LinkedIn</a>'

    # Do not contact indicator
    do_not_contact_html = ""
    if not alumni.get("contact", True):
        do_not_contact_html = '<div style="color:#dc2626;font-size:0.8rem;font-weight:600;margin-bottom:0.5rem;">⚠️ Do not contact</div>'

    card_html = f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;border:1px solid var(--tc-border);margin-bottom:1rem;box-shadow:0 1px 3px var(--tc-shadow);display:flex;flex-direction:column;min-height:260px;"><div style="font-weight:600;font-size:1.1rem;margin-bottom:0.25rem;color:var(--tc-text);">{alumni["name"]}</div>{do_not_contact_html}<div style="color:var(--tc-text2);font-size:0.875rem;margin-bottom:0.5rem;">Cohort: {alumni.get("cohort") or "N/A"}</div>{role_html}<div style="margin-bottom:0.5rem;">{type_badges_html}{party_html}</div><div style="margin-top:auto;">{office_html}<div style="margin-bottom:0.25rem;">{sector_html}</div>{location_html}{linkedin_html}</div></div>'

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
        label, cls = get_fellow_type_badge(ft)
        type_badges_html += f'<span class="tc-badge {cls}">{label}</span>'

    # Party badge
    party_html = ""
    if alumni.get("party"):
        if alumni["party"] == "Republican":
            party_html = '<span class="tc-badge" style="background:#ef4444;color:#fff;">R</span>'
        elif alumni["party"] == "Democrat":
            party_html = '<span class="tc-badge" style="background:#3b82f6;color:#fff;">D</span>'
        elif alumni["party"] == "Independent":
            party_html = '<span class="tc-badge" style="background:#8b5cf6;color:#fff;">I</span>'
        elif alumni["party"] == "Institutional Office":
            party_html = '<span class="tc-badge" style="background:#64748b;color:#fff;">Institutional</span>'
    elif aisf:
        party_html = '<span class="tc-badge" style="background:#64748b;color:#fff;">Executive Branch</span>'

    # Sector badge
    sector_html = ""
    if alumni.get("sector"):
        s_cls = get_sector_badge(alumni["sector"])
        sector_html = f'<span class="tc-badge {s_cls}">{alumni["sector"]}</span>'

    # Modal header
    fellow_type_display = ", ".join(fellow_types) if fellow_types else "Alumni"
    st.markdown(f"## {alumni['name']}")
    st.markdown(f"**Cohort {alumni.get('cohort') or 'N/A'}** • {fellow_type_display}")

    badges_html = f'{type_badges_html}{party_html} {sector_html}'
    st.markdown(f'<div style="margin-bottom:1rem;">{badges_html}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabbed layout ──────────────────────────────────────────────────────────
    (tab_contact, tab_fellowship, tab_background,
     tab_current, tab_engagement, tab_accomplishments) = st.tabs([
        "Contact", "Fellowship History", "Background",
        "Current Info", "Engagement", "Accomplishments"
    ])

    with tab_contact:
        if alumni.get("email"):
            st.markdown(f"📧 [{alumni['email']}](mailto:{alumni['email']})")
        if alumni.get("phone"):
            st.markdown(f"📞 {alumni['phone']}")
        if alumni.get("linkedin"):
            st.markdown(f"🔗 [LinkedIn]({alumni['linkedin']})")
        if not alumni.get("email") and not alumni.get("phone") and not alumni.get("linkedin"):
            st.caption("No contact info on record.")
        st.markdown("")
        if not alumni.get("contact", True):
            st.markdown('<p style="color:#dc2626;font-weight:600;margin:0;">⚠️ Do not contact</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#166534;margin:0;">✓ OK to contact</p>', unsafe_allow_html=True)

    with tab_fellowship:
        col1, col2 = st.columns(2)
        with col1:
            if fellow_types:
                st.markdown(f"**Fellow Type(s):** {', '.join(fellow_types)}")
            if alumni.get("cohort"):
                st.markdown(f"**Cohort:** {alumni['cohort']}")
            if alumni.get("chamber"):
                st.markdown(f"**Chamber:** {alumni['chamber']}")
            if alumni.get("party"):
                st.markdown(f"**Party:** {alumni['party']}")
            elif aisf:
                st.markdown("**Branch:** Executive Branch")
        with col2:
            if alumni.get("office_served"):
                st.markdown(f"**Office Served:** {alumni['office_served']}")

    with tab_background:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Prior Role**")
            st.markdown(alumni["prior_role"] if alumni.get("prior_role") else "_No prior role on record._")
        with col2:
            st.markdown("**Education**")
            st.markdown(alumni["education"] if alumni.get("education") else "_No education info on record._")

    with tab_current:
        col1, col2 = st.columns(2)
        with col1:
            if alumni.get("current_role"):
                st.markdown(f"**Current Role:** {alumni['current_role']}")
            if alumni.get("location"):
                st.markdown(f"**Location:** {alumni['location']}")
            if not alumni.get("current_role"):
                st.caption("No current info on record.")
        with col2:
            if alumni.get("sector"):
                s_cls = get_sector_badge(alumni["sector"])
                st.markdown("**Sector**")
                st.markdown(f'<span class="tc-badge {s_cls}">{alumni["sector"]}</span>', unsafe_allow_html=True)

    with tab_engagement:
        if alumni.get("last_engaged"):
            days_ago = calculate_days_since(alumni["last_engaged"])
            st.markdown(f"**Last Engaged:** {alumni['last_engaged']} _{days_ago} days ago_")
        else:
            st.caption("No engagement date recorded.")
        if alumni.get("engagement_notes"):
            st.markdown("**Engagement Notes**")
            st.markdown(alumni["engagement_notes"])
        if alumni.get("notes"):
            st.markdown("**Notes**")
            st.markdown(alumni["notes"])

    with tab_accomplishments:
        st.caption("Accomplishments tracking coming soon.")

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
            party_options = ["", "Democrat", "Republican", "Independent", "Institutional Office"]
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
            current_role = st.text_input("Current Role", value=alumni.get("current_role", ""), placeholder="e.g., Policy Analyst @ OSTP")

        prior_role = st.text_input("Prior Role", value=alumni.get("prior_role", ""), placeholder="Role before becoming a fellow")
        education = st.text_input("Education", value=alumni.get("education", ""), placeholder="e.g., PhD Computer Science, Stanford")

        col1, col2 = st.columns(2)
        with col1:
            sector_options = ["", "Government", "Nonprofit/Think Tank", "Academia", "Private", "Policy/Think Tank"]
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
