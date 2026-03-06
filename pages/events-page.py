import streamlit as st
from datetime import datetime, date
from styles import get_css
from helpers import (
    fetch_fellows, fetch_events, add_event, update_event,
    fetch_all_event_attendance, save_event_attendance_batch,
    get_quarter_compliance, _date_to_quarter, _is_tracked_cohort,
    EVENT_TYPES, calculate_days_since,
)

# ============ AUTH GUARD ============
if not st.session_state.get("authenticated"):
    st.warning("Please log in first.")
    st.stop()

# ============ SESSION STATE ============
for key, default in {
    "events_editing": None,
    "events_show_form": False,
    "events_attendance_event_id": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============ CUSTOM CSS ============
st.markdown(get_css(), unsafe_allow_html=True)


# ============ CONSTANTS ============
TYPE_COLORS = {
    "Happy Hour":        {"badge": "tc-badge-blue",   "dot": "#3b82f6"},
    "Site Visit":        {"badge": "tc-badge-green",  "dot": "#22c55e"},
    "Social":            {"badge": "tc-badge-orange", "dot": "#f97316"},
    "Career Development":{"badge": "tc-badge-purple", "dot": "#8b5cf6"},
    "Speaker Series":    {"badge": "tc-badge-yellow", "dot": "#eab308"},
    "Check-ins":         {"badge": "tc-badge-gray",   "dot": "#94a3b8"},
    "Conference":        {"badge": "tc-badge-red",    "dot": "#ef4444"},
    "Recruitment":       {"badge": "tc-badge-gray",   "dot": "#6b7280"},
}


# ============ HELPERS ============

def _parse_date_value(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%m/%d/%y", "%-m/%-d/%y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _is_past(date_str: str) -> bool:
    d = _parse_date_value(date_str)
    return d is not None and d < date.today()


def _is_upcoming(date_str: str) -> bool:
    d = _parse_date_value(date_str)
    return d is not None and d >= date.today()


def _fmt_date(date_str: str) -> str:
    d = _parse_date_value(date_str)
    if not d:
        return date_str
    return d.strftime("%b %-d, %Y")


def _fmt_date_long(date_str: str) -> str:
    d = _parse_date_value(date_str)
    if not d:
        return date_str
    return d.strftime("%a, %B %-d, %Y")


def _event_status(date_str: str) -> str:
    d = _parse_date_value(date_str)
    if d is None:
        return "Upcoming"
    if d == date.today():
        return "Today"
    return "Past" if d < date.today() else "Upcoming"


def _type_badge(event_type: str) -> str:
    cls = TYPE_COLORS.get(event_type, {}).get("badge", "tc-badge-gray")
    return f'<span class="tc-badge {cls}">{event_type}</span>'


def _status_badge(status: str) -> str:
    cls_map = {"Past": "tc-badge-past", "Today": "tc-badge-today", "Upcoming": "tc-badge-upcoming"}
    cls = cls_map.get(status, "tc-badge-upcoming")
    return f'<span class="tc-badge {cls}">{status}</span>'


def _quarter_pill(status: str, label: str) -> str:
    icons = {"met": "✓", "not_met": "✗"}
    cls_map = {"met": "tc-badge-met", "not_met": "tc-badge-not-met"}
    icon = icons.get(status, "–")
    cls = cls_map.get(status, "tc-badge-gray")
    return f'<span class="tc-badge {cls}">{icon} {label}</span>'


def _att_bar(pct: int) -> str:
    color = "#22c55e" if pct >= 80 else "#f59e0b" if pct >= 60 else "#ef4444"
    return (f'<div style="display:flex;align-items:center;gap:0.5rem;">'
            f'<div style="flex:1;background:var(--tc-border);border-radius:9999px;height:6px;">'
            f'<div style="width:{pct}%;background:{color};border-radius:9999px;height:6px;"></div>'
            f'</div>'
            f'<span style="font-size:0.72rem;font-weight:600;color:var(--tc-text2);min-width:2.5rem;'
            f'text-align:right;">{pct}%</span></div>')


def _initials(name: str) -> str:
    return "".join(p[0] for p in name.split() if p)


# ============ ADD / EDIT EVENT DIALOG ============

@st.dialog("Add Event" if not st.session_state.get("events_editing") else "Edit Event", width="large")
def show_event_form(event: dict | None = None):
    is_editing = event is not None
    st.subheader("Edit Event" if is_editing else "Add New Event")

    with st.form("event_form"):
        name = st.text_input("Event Name", value=event.get("name", "") if is_editing else "")

        col1, col2 = st.columns(2)
        with col1:
            existing_date = _parse_date_value(event.get("date", "")) if is_editing else None
            event_date = st.date_input("Date", value=existing_date, format="YYYY-MM-DD")
        with col2:
            type_opts = EVENT_TYPES
            type_idx = type_opts.index(event["type"]) if is_editing and event.get("type") in type_opts else 0
            event_type = st.selectbox("Type", type_opts, index=type_idx)

        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("Location (City)", value=event.get("location", "") if is_editing else "",
                                     placeholder="e.g., Washington, DC")
        with col2:
            venue = st.text_input("Venue", value=event.get("venue", "") if is_editing else "",
                                  placeholder="e.g., Capitol Hill Club")

        col1, col2 = st.columns(2)
        with col1:
            cohort = st.text_input("Cohort", value=event.get("cohort", "Jan 2026 CIF/SCIF") if is_editing else "Jan 2026 CIF/SCIF")
        with col2:
            # Quarter is auto-computed from date but shown for confirmation
            auto_quarter = _date_to_quarter(str(event_date)) if event_date else ""
            st.text_input("Quarter (auto-computed)", value=auto_quarter, disabled=True)

        description = st.text_area("Description", value=event.get("description", "") if is_editing else "",
                                   placeholder="Brief description of the event")

        col1, col2 = st.columns(2)
        with col1:
            # Recruitment events are never required for fellows
            required_default = event.get("required", True) if is_editing else True
            required_disabled = event_type == "Recruitment"
            required = st.checkbox(
                "Required for Fellows?",
                value=False if event_type == "Recruitment" else required_default,
                disabled=required_disabled,
                help="Uncheck for optional or staff-only events. Recruitment events are never required.",
            )
        with col2:
            staffed_by = st.text_input(
                "Staffed By",
                value=event.get("staffed_by", "") if is_editing else "",
                placeholder="e.g., Grace, Mya",
            )
            st.caption("Enter staff first names in alphabetical order, separated by commas.")

        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with col2:
            submit = st.form_submit_button(
                "Save Changes" if is_editing else "Add Event",
                type="primary", use_container_width=True,
            )

    if cancel:
        st.session_state.events_editing = None
        st.session_state.events_show_form = False
        st.rerun()

    if submit:
        if not name:
            st.error("Event name is required.")
            return
        event_data = {
            "name":        name,
            "date":        str(event_date) if event_date else "",
            "type":        event_type,
            "location":    location,
            "venue":       venue,
            "cohort":      cohort,
            "quarter":     auto_quarter,
            "description": description,
            "required":    required and event_type != "Recruitment",
            "staffed_by":  staffed_by,
        }
        if is_editing:
            success = update_event(event["id"], event_data)
            if success:
                st.success("Event updated!")
                st.session_state.events_editing = None
                st.rerun()
        else:
            success = add_event(event_data)
            if success:
                st.success("Event added!")
                st.session_state.events_show_form = False
                st.rerun()


# ============ RECORD ATTENDANCE DIALOG ============

@st.dialog("Record Attendance", width="large")
def show_attendance_form(event: dict, fellows: list, attendance: list):
    st.subheader(f"{event['name']}")
    st.caption(f"{_fmt_date_long(event['date'])} · {event.get('venue') or event.get('location', '')}")
    st.divider()

    # Build existing attendance lookup for this event
    existing = {r["fellow_id"]: r["attended"] for r in attendance if r["event_id"] == event["id"]}

    eligible = [f for f in fellows if f.get("fellow_type") != "AISF" and _is_tracked_cohort(f.get("cohort", ""))]

    with st.form("attendance_form"):
        st.markdown("**Mark attendance for each fellow:**")
        checks = {}
        for fellow in eligible:
            default = existing.get(fellow["id"], False)
            checks[fellow["id"]] = st.checkbox(
                fellow["name"],
                value=default,
                key=f"att_chk_{event['id']}_{fellow['id']}",
            )

        col1, col2 = st.columns(2)
        with col1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with col2:
            submit = st.form_submit_button("Save Attendance", type="primary", use_container_width=True)

    if cancel:
        st.session_state.events_attendance_event_id = None
        st.rerun()

    if submit:
        # Build a single map and write everything in one batch (1 read + 1-2 writes)
        # instead of calling save_event_attendance() N times, which fires N get_all_records()
        # calls and hits the Google Sheets 60-reads/min quota.
        attendance_map = {
            fellow["id"]: (fellow["name"], checks[fellow["id"]], "")
            for fellow in eligible
        }
        ok = save_event_attendance_batch(event_id=event["id"], attendance_map=attendance_map)
        if ok:
            st.success("Attendance saved!")
            st.session_state.events_attendance_event_id = None
            st.rerun()


# ============ OVERVIEW TAB ============

def show_overview(fellows, events, attendance):
    past_events = [e for e in events if _is_past(e["date"])]

    # Compute avg attendance across past events
    att_by_event = {}
    for rec in attendance:
        att_by_event.setdefault(rec["event_id"], []).append(rec["attended"])

    pcts = []
    for e in past_events:
        vals = att_by_event.get(e["id"], [])
        if vals:
            pcts.append(int(round(sum(vals) / len(vals) * 100)))
    avg_pct = int(round(sum(pcts) / len(pcts))) if pcts else 0

    # Quarter compliance
    eligible = [f for f in fellows if f.get("fellow_type") != "AISF" and _is_tracked_cohort(f.get("cohort", ""))]
    compliance = get_quarter_compliance(eligible, events, attendance)
    at_risk = sum(1 for qc in compliance.values() if "not_met" in qc.values())

    # ── Metrics ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Events", len(events), delta=None)
        st.caption("All cohorts")
    with c2:
        st.metric("Events Completed", len(past_events))
        st.caption("Attendance recorded")
    with c3:
        st.metric("Avg. Attendance", f"{avg_pct}%")
        st.caption("Across past events")
    with c4:
        st.metric("At-Risk Fellows", at_risk)
        st.caption("Missing ≥1 quarterly event")

    st.markdown("---")

    col_left, col_right = st.columns([1.7, 1])

    # ── Left: Attendance by event ─────────────────────────────────────────────
    with col_left:
        st.markdown("**Attendance by Event**")
        if not past_events:
            st.caption("No past events yet.")
        else:
            rows_html = ""
            for e in past_events:
                vals = att_by_event.get(e["id"], [])
                attended = sum(vals)
                total = len(vals)
                pct = int(round(attended / total * 100)) if total else 0
                dot = TYPE_COLORS.get(e["type"], {}).get("dot", "#6366f1")
                bar = _att_bar(pct)
                rows_html += (
                    f'<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.6rem;">'
                    f'<div style="width:8px;height:8px;border-radius:50%;background:{dot};flex-shrink:0;"></div>'
                    f'<div style="width:10rem;flex-shrink:0;">'
                    f'<p style="font-size:0.83rem;font-weight:600;color:var(--tc-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0;">{e["name"]}</p>'
                    f'<p style="font-size:0.72rem;color:var(--tc-text3);margin:0;">{_fmt_date(e["date"])}</p>'
                    f'</div>'
                    f'<div style="flex:1;">{bar}</div>'
                    f'<span style="font-size:0.72rem;color:var(--tc-text3);min-width:2.5rem;text-align:right;">{attended}/{total}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;'
                f'border:1px solid var(--tc-border);box-shadow:0 1px 3px var(--tc-shadow);">'
                f'{rows_html}</div>',
                unsafe_allow_html=True,
            )

    # ── Right column ──────────────────────────────────────────────────────────
    with col_right:
        # Quarterly compliance grid
        quarters = sorted({q for qc in compliance.values() for q in qc.keys()})
        st.markdown("**Quarterly Compliance**")
        if not compliance:
            st.caption("No data yet.")
        else:
            rows_html = ""
            for fellow in eligible:
                fid = fellow["id"]
                qc = compliance.get(fid, {})
                pills = "".join(_quarter_pill(qc[q], q) for q in quarters if q in qc)
                at_risk_flag = (
                    '<span class="tc-badge tc-badge-not-met" style="margin-left:0.25rem;">⚠</span>'
                    if "not_met" in qc.values() else ""
                )
                rows_html += (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'margin-bottom:0.45rem;">'
                    f'<span style="font-size:0.83rem;color:var(--tc-text4);font-weight:500;">'
                    f'{fellow["name"]}{at_risk_flag}</span>'
                    f'<div style="display:flex;gap:0.25rem;flex-wrap:wrap;">{pills}</div></div>'
                )
            st.markdown(
                f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;'
                f'border:1px solid var(--tc-border);box-shadow:0 1px 3px var(--tc-shadow);">'
                f'{rows_html}'
                f'<p style="font-size:0.72rem;color:var(--tc-text3);margin-top:0.75rem;">'
                f'Fellows must attend ≥1 required event per quarter.</p></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

        # Upcoming events
        upcoming = [e for e in events if _is_upcoming(e["date"])][:5]
        st.markdown("**Upcoming Events**")
        if not upcoming:
            st.caption("No upcoming events scheduled.")
        else:
            rows_html = ""
            for e in upcoming:
                dot = TYPE_COLORS.get(e["type"], {}).get("dot", "#6366f1")
                rows_html += (
                    f'<div style="display:flex;gap:0.6rem;align-items:flex-start;margin-bottom:0.5rem;">'
                    f'<div style="width:8px;height:8px;border-radius:50%;background:{dot};'
                    f'flex-shrink:0;margin-top:0.3rem;"></div>'
                    f'<div><p style="font-size:0.83rem;font-weight:600;color:var(--tc-text);margin:0;">'
                    f'{e["name"]}</p>'
                    f'<p style="font-size:0.72rem;color:var(--tc-text3);margin:0;">'
                    f'{_fmt_date(e["date"])} · {e.get("location","")}</p></div></div>'
                )
            st.markdown(
                f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;'
                f'border:1px solid var(--tc-border);box-shadow:0 1px 3px var(--tc-shadow);">'
                f'{rows_html}</div>',
                unsafe_allow_html=True,
            )


# ============ EVENTS TAB ============

def show_events_tab(fellows, events, attendance):
    # ── Filters ───────────────────────────────────────────────────────────────
    col_search, col_type, col_quarter, col_btn = st.columns([3, 2, 2, 1.2])
    with col_search:
        search = st.text_input("Search", placeholder="Search events…", label_visibility="collapsed")
    with col_type:
        type_opts = ["All Types"] + EVENT_TYPES
        type_filter = st.selectbox("Type", type_opts, label_visibility="collapsed")
    with col_quarter:
        quarters = ["All Quarters"] + sorted({e["quarter"] for e in events if e.get("quarter")})
        quarter_filter = st.selectbox("Quarter", quarters, label_visibility="collapsed")
    with col_btn:
        if st.button("＋ Add Event", type="primary", use_container_width=True):
            st.session_state.events_editing = None
            st.session_state.events_show_form = True
            st.rerun()

    # ── Dialogs ───────────────────────────────────────────────────────────────
    if st.session_state.events_show_form and st.session_state.events_editing is None:
        show_event_form(event=None)

    if st.session_state.events_editing:
        editing_event = next((e for e in events if e["id"] == st.session_state.events_editing), None)
        if editing_event:
            show_event_form(event=editing_event)

    if st.session_state.events_attendance_event_id:
        target = next((e for e in events if e["id"] == st.session_state.events_attendance_event_id), None)
        if target:
            show_attendance_form(target, fellows, attendance)

    # ── Filter logic ──────────────────────────────────────────────────────────
    filtered = events
    if search:
        sl = search.lower()
        filtered = [e for e in filtered if sl in e["name"].lower()
                    or sl in e.get("description", "").lower()
                    or sl in e.get("location", "").lower()]
    if type_filter != "All Types":
        filtered = [e for e in filtered if e["type"] == type_filter]
    if quarter_filter != "All Quarters":
        filtered = [e for e in filtered if e.get("quarter") == quarter_filter]

    st.caption(f"Showing {len(filtered)} of {len(events)} events")

    # ── Event cards ───────────────────────────────────────────────────────────
    att_by_event = {}
    for rec in attendance:
        att_by_event.setdefault(rec["event_id"], {})[rec["fellow_id"]] = rec["attended"]

    eligible = [f for f in fellows if f.get("fellow_type") != "AISF" and _is_tracked_cohort(f.get("cohort", ""))]

    for idx, event in enumerate(filtered):
        status = _event_status(event["date"])
        ev_att = att_by_event.get(event["id"], {})
        total = len(ev_att)
        attended_count = sum(ev_att.values())
        pct = int(round(attended_count / total * 100)) if total else 0

        required_label = ""
        if not event.get("required"):
            required_label = '<span class="tc-badge tc-badge-gray">Not Required</span> '

        staffed_html = ""
        if event.get("staffed_by"):
            staffed_html = (f'<span style="font-size:0.78rem;color:var(--tc-text2);">👤 {event["staffed_by"]}</span>')

        location_parts = [p for p in [event.get("venue"), event.get("location")] if p]
        location_str = " · ".join(location_parts) if location_parts else ""

        location_span = f'<span>📍 {location_str}</span>' if location_str else ''
        quarter_span  = f'<span>🗓 {event.get("quarter","")}</span>' if event.get("quarter") else ''
        card_left = (
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;margin-bottom:0.3rem;">'
            f'<span style="font-weight:600;font-size:0.95rem;color:var(--tc-text);">{event["name"]}</span>'
            f'{_type_badge(event["type"])}{_status_badge(status)}{required_label}'
            f'</div>'
            f'<p style="font-size:0.82rem;color:var(--tc-text2);margin:0 0 0.4rem 0;">{event.get("description","")}</p>'
            f'<div style="display:flex;flex-wrap:wrap;gap:1rem;font-size:0.78rem;color:var(--tc-text3);">'
            f'<span>📅 {_fmt_date_long(event["date"])}</span>'
            f'{location_span}{quarter_span}{staffed_html}'
            f'</div></div>'
        )

        if status == "Past" and total > 0:
            card_right = (f'<div style="text-align:right;flex-shrink:0;margin-left:1rem;">'
                          f'<p style="font-size:1.5rem;font-weight:700;color:var(--tc-text);margin:0;">{pct}%</p>'
                          f'<p style="font-size:0.75rem;color:var(--tc-text3);margin:0 0 0.25rem 0;">'
                          f'{attended_count}/{total} attended</p>'
                          f'<div style="width:7rem;">{_att_bar(pct)}</div></div>')
        else:
            card_right = ""

        st.markdown(
            f'<div class="event-card">'
            f'<div style="display:flex;align-items:flex-start;">'
            f'{card_left}{card_right}</div></div>',
            unsafe_allow_html=True,
        )

        # Action buttons beneath each card
        btn_cols = st.columns([1, 1, 4])
        with btn_cols[0]:
            if st.button("✏️ Edit", key=f"edit_{idx}_{event['id']}", use_container_width=True):
                st.session_state.events_editing = event["id"]
                st.session_state.events_show_form = False
                st.rerun()
        with btn_cols[1]:
            if status == "Past":
                label = "📋 Update Attendance" if total > 0 else "📋 Record Attendance"
                if st.button(label, key=f"att_btn_{idx}_{event['id']}", use_container_width=True):
                    st.session_state.events_attendance_event_id = event["id"]
                    st.rerun()

        # Attendance roster (shown if attendance has been recorded)
        if status == "Past" and total > 0:
            with st.expander("View attendance roster", expanded=False):
                roster_cols = st.columns(3)
                for i, fellow in enumerate(eligible):
                    fid = fellow["id"]
                    was_present = ev_att.get(fid)
                    if was_present is None:
                        continue
                    row_bg = "var(--tc-present-bg)" if was_present else "var(--tc-absent-bg)"
                    dot_color = "#22c55e" if was_present else "#ef4444"
                    name_color = "var(--tc-present-text)" if was_present else "var(--tc-absent-text)"
                    with roster_cols[i % 3]:
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:0.4rem;'
                            f'padding:0.3rem 0.65rem;border-radius:0.4rem;background:{row_bg};'
                            f'margin-bottom:0.3rem;">'
                            f'<span style="width:7px;height:7px;border-radius:50%;'
                            f'background:{dot_color};flex-shrink:0;display:inline-block;"></span>'
                            f'<span style="font-size:0.82rem;color:{name_color};">'
                            f'{fellow["name"]}</span></div>',
                            unsafe_allow_html=True,
                        )

    if not filtered:
        st.info("No events match your filters.")


# ============ FELLOWS TAB ============

def show_fellows_tab(fellows, events, attendance):
    st.caption(
        "Tracking attendance for Jan 2026 CIF/SCIF fellows and future cohorts. "
        "Each fellow must attend at least one required event per quarter."
    )
    st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

    eligible = [f for f in fellows if f.get("fellow_type") != "AISF" and _is_tracked_cohort(f.get("cohort", ""))]
    compliance = get_quarter_compliance(eligible, events, attendance)
    quarters = sorted({q for qc in compliance.values() for q in qc.keys()})

    # Build attendance lookup: {fellow_id: {event_id: attended}}
    att_lookup = {}
    for rec in attendance:
        att_lookup.setdefault(rec["fellow_id"], {})[rec["event_id"]] = rec["attended"]

    past_events = [e for e in events if _is_past(e["date"])]

    col1, col2 = st.columns(2)
    for i, fellow in enumerate(eligible):
        fid = fellow["id"]
        qc = compliance.get(fid, {})
        at_risk = "not_met" in qc.values()

        f_att = att_lookup.get(fid, {})
        total = len([e for e in past_events if fid in att_lookup.get(fid, {}) or True])
        # Count only events where we have a record for this fellow
        fellow_past_records = [e for e in past_events if fid in att_lookup.get(fid, {})]
        attended_count = sum(1 for e in fellow_past_records if att_lookup[fid].get(e["id"], False))
        recorded_total = len(fellow_past_records)
        pct = int(round(attended_count / recorded_total * 100)) if recorded_total else 0

        border_color = "#fca5a5" if at_risk else "var(--tc-border)"

        pills_html = "".join(_quarter_pill(qc[q], q) for q in quarters if q in qc)
        if at_risk:
            pills_html += '<span class="tc-badge tc-badge-not-met" style="margin-left:0.25rem;">⚠ Needs attention</span>'

        initials_html = (
            f'<div style="width:2.5rem;height:2.5rem;border-radius:50%;'
            f'background:var(--tc-avatar-bg);color:var(--tc-avatar-text);display:flex;align-items:center;'
            f'justify-content:center;font-size:0.85rem;font-weight:700;flex-shrink:0;">'
            f'{_initials(fellow["name"])}</div>'
        )

        bar_html = _att_bar(pct)

        _type_cls = "tc-badge-blue" if fellow["fellow_type"] == "CIF" else "tc-badge-indigo"
        type_tag = f'<span class="tc-badge {_type_cls}">{fellow["fellow_type"]}</span>'

        pct_color = '#16a34a' if pct >= 80 else '#d97706' if pct >= 60 else '#dc2626'
        card_html = (
            f'<div style="background:var(--tc-surface);padding:1.25rem;border-radius:0.75rem;'
            f'border:1px solid {border_color};margin-bottom:0.75rem;'
            f'box-shadow:0 1px 3px var(--tc-shadow);">'
            f'<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.6rem;">'
            f'{initials_html}'
            f'<div style="flex:1;min-width:0;">'
            f'<p style="font-weight:600;font-size:1rem;color:var(--tc-text);margin:0;">{fellow["name"]}</p>'
            f'<p style="font-size:0.78rem;color:var(--tc-text2);margin:0;">'
            f'{type_tag}'
            f'<span style="margin-left:0.35rem;">{fellow.get("chamber","")} · {fellow.get("office","")}</span>'
            f'</p></div>'
            f'<div style="text-align:right;flex-shrink:0;">'
            f'<span style="font-size:1.4rem;font-weight:700;color:{pct_color};">{pct}%</span>'
            f'<p style="font-size:0.72rem;color:var(--tc-text3);margin:0;">{attended_count}/{recorded_total} events</p>'
            f'</div></div>'
            f'{bar_html}'
            f'<div style="display:flex;gap:0.35rem;flex-wrap:wrap;margin-top:0.65rem;">'
            f'{pills_html}'
            f'</div></div>'
        )

        target_col = col1 if i % 2 == 0 else col2
        with target_col:
            st.markdown(card_html, unsafe_allow_html=True)

            # Expandable event history
            with st.expander("View event history"):
                if not fellow_past_records:
                    st.caption("No attendance recorded yet.")
                else:
                    for e in fellow_past_records:
                        was_present = att_lookup[fid].get(e["id"], False)
                        dot = TYPE_COLORS.get(e["type"], {}).get("dot", "#6366f1")
                        badge_cls = "tc-badge-met" if was_present else "tc-badge-not-met"
                        badge_text = "✓ Attended" if was_present else "✗ Absent"
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:0.5rem;'
                            f'margin-bottom:0.3rem;">'
                            f'<div style="width:7px;height:7px;border-radius:50%;'
                            f'background:{dot};flex-shrink:0;"></div>'
                            f'<span style="font-size:0.82rem;color:var(--tc-text4);flex:1;">'
                            f'{e["name"]}</span>'
                            f'<span style="font-size:0.72rem;color:var(--tc-text2);">{e.get("quarter","")}</span>'
                            f'<span class="tc-badge {badge_cls}">{badge_text}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    if not eligible:
        st.info("No tracked fellows found. Fellows must be Jan 2026 CIF/SCIF or a later cohort.")


# ============ MAIN PAGE ============

st.markdown("## 📅 Events & Attendance")
st.caption("Jan 2026 CIF/SCIF cohort · Required: ≥1 event per quarter")
st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)

# Fetch data
fellows = fetch_fellows()
events = fetch_events()
attendance = fetch_all_event_attendance()

# Main tabs
tab_overview, tab_events, tab_fellows = st.tabs(["Overview", "Events", "Fellows"])

with tab_overview:
    show_overview(fellows, events, attendance)

with tab_events:
    show_events_tab(fellows, events, attendance)

with tab_fellows:
    show_fellows_tab(fellows, events, attendance)
