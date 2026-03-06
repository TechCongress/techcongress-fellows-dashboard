"""
styles.py — Shared CSS for TechCongress Fellows Dashboard

Provides a get_css() function that returns a <style> block using CSS custom
properties so the dashboard automatically adapts to the user's system dark/light
mode preference via @media (prefers-color-scheme: dark).

Usage in any page:
    from styles import get_css
    st.markdown(get_css(), unsafe_allow_html=True)

All custom HTML strings in the pages should reference these CSS variables
(e.g. style="background:var(--tc-surface);color:var(--tc-text)") so they
inherit the correct color in both modes.
"""


def get_css() -> str:
    return """<style>
/* ══════════════════════════════════════════════════════════
   THEME VARIABLES  — light defaults, dark overrides
══════════════════════════════════════════════════════════ */
:root {
  --tc-bg:           #f8fafc;   /* page / app background          */
  --tc-surface:      #ffffff;   /* cards, panels, dialogs         */
  --tc-surface2:     #f1f5f9;   /* subtle nested bg (checkins …)  */
  --tc-border:       #e5e7eb;   /* default border                 */
  --tc-border2:      #d1d5db;   /* slightly darker border         */
  --tc-text:         #1f2937;   /* primary text                   */
  --tc-text2:        #6b7280;   /* secondary / caption text       */
  --tc-text3:        #9ca3af;   /* muted / placeholder text       */
  --tc-text4:        #374151;   /* medium-weight body text        */
  --tc-shadow:       rgba(0,0,0,0.10);
  --tc-shadow-hover: rgba(0,0,0,0.10);
  --tc-note-bg:      #fffbeb;   /* yellow note / info block bg    */
  --tc-note-border:  #fde68a;   /* yellow note border             */
  --tc-hover:        #f9fafb;   /* hover state background         */
  --tc-btn-close:        #f3f4f6;
  --tc-btn-close-hover:  #e5e7eb;
  --tc-checkin-bg:   #f8fafc;   /* check-in / log row background  */
  --tc-avatar-bg:    #e0e7ff;   /* initials avatar background     */
  --tc-avatar-text:  #4338ca;   /* initials avatar text           */
  --tc-present-bg:   #f0fdf4;   /* attended / present row bg      */
  --tc-present-text: #166534;
  --tc-absent-bg:    #fef2f2;   /* absent row bg                  */
  --tc-absent-text:  #991b1b;
}

@media (prefers-color-scheme: dark) {
  :root {
    --tc-bg:           #0f172a;
    --tc-surface:      #1e293b;
    --tc-surface2:     #162032;
    --tc-border:       #334155;
    --tc-border2:      #475569;
    --tc-text:         #f1f5f9;
    --tc-text2:        #94a3b8;
    --tc-text3:        #64748b;
    --tc-text4:        #cbd5e1;
    --tc-shadow:       rgba(0,0,0,0.40);
    --tc-shadow-hover: rgba(0,0,0,0.30);
    --tc-note-bg:      #292524;
    --tc-note-border:  #78716c;
    --tc-hover:        #1e3050;
    --tc-btn-close:        #334155;
    --tc-btn-close-hover:  #475569;
    --tc-checkin-bg:   #162032;
    --tc-avatar-bg:    #312e81;
    --tc-avatar-text:  #a5b4fc;
    --tc-present-bg:   #052e16;
    --tc-present-text: #4ade80;
    --tc-absent-bg:    #450a0a;
    --tc-absent-text:  #fca5a5;
  }
}

/* ══════════════════════════════════════════════════════════
   APP SHELL
══════════════════════════════════════════════════════════ */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
.main,
.block-container {
  background-color: var(--tc-bg) !important;
  color: var(--tc-text) !important;
}

[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
header[data-testid="stHeader"] {
  background-color: var(--tc-bg) !important;
  color: var(--tc-text) !important;
}

[data-testid="stToolbar"] svg,
[data-testid="stToolbar"] button svg,
header[data-testid="stHeader"] svg {
  color: var(--tc-text) !important;
  stroke: var(--tc-text) !important;
  fill: var(--tc-text) !important;
}

[data-testid="stMainMenu"],
[data-testid="stMainMenu"] button {
  color: var(--tc-text) !important;
}
[data-testid="stMainMenu"] svg {
  color: var(--tc-text) !important;
  stroke: var(--tc-text) !important;
}

/* ══════════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
  background-color: var(--tc-surface) !important;
  border-right: 1px solid var(--tc-border) !important;
}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] a {
  color: var(--tc-text) !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--tc-border) !important;
}

/* ══════════════════════════════════════════════════════════
   TYPOGRAPHY
══════════════════════════════════════════════════════════ */
h1, h2, h3, p, span, label {
  color: var(--tc-text) !important;
}

/* ══════════════════════════════════════════════════════════
   METRIC WIDGETS
══════════════════════════════════════════════════════════ */
div[data-testid="stMetric"] {
  background-color: var(--tc-surface);
  padding: 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--tc-border);
}
div[data-testid="stMetric"] label {
  color: var(--tc-text2) !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
  color: var(--tc-text) !important;
}
[data-testid="stMetric"] svg {
  color: var(--tc-text2) !important;
  stroke: var(--tc-text2) !important;
}

/* ══════════════════════════════════════════════════════════
   TOOLTIPS
══════════════════════════════════════════════════════════ */
[data-testid="stTooltipIcon"],
[data-testid="stTooltipIcon"] svg {
  color: var(--tc-text2) !important;
  stroke: var(--tc-text2) !important;
}
div[data-baseweb="tooltip"] {
  background-color: #1f2937 !important;
  color: #ffffff !important;
}
div[data-baseweb="tooltip"] div {
  color: #ffffff !important;
}

/* ══════════════════════════════════════════════════════════
   CARD CLASSES  (used by pages via className in CSS)
══════════════════════════════════════════════════════════ */
.stat-card {
  background: var(--tc-surface);
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 1px solid var(--tc-border);
  box-shadow: 0 1px 3px var(--tc-shadow);
}
.stat-value { font-size: 2rem; font-weight: 700; margin: 0; }
.stat-label { color: var(--tc-text2); font-size: 0.875rem; margin: 0; }

.fellow-card {
  background: var(--tc-surface);
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 1px solid var(--tc-border);
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px var(--tc-shadow);
}
.fellow-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 6px var(--tc-shadow-hover);
}

.event-card {
  background: var(--tc-surface);
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 1px solid var(--tc-border);
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 3px var(--tc-shadow);
}
.event-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 6px var(--tc-shadow-hover);
}

/* Status badge classes */
.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}
.status-on-track    { background: #dcfce7; color: #166534; border-radius: 9999px; }
.status-flagged     { background: #fef9c3; color: #854d0e; border-radius: 9999px; }
.status-ending-soon { background: #ffedd5; color: #9a3412; border-radius: 9999px; }
.needs-checkin      { background: #fef9c3; color: #854d0e; }

/* ══════════════════════════════════════════════════════════
   EVENT / STATUS / COMPLIANCE BADGES  (theme-aware)
══════════════════════════════════════════════════════════ */
.tc-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.4;
  margin-right: 0.15rem;
}
/* Light-mode colors — pastel bg + dark text (need dark overrides) */
.tc-badge-blue     { background: #dbeafe; color: #1d4ed8; }
.tc-badge-green    { background: #dcfce7; color: #166534; }
.tc-badge-orange   { background: #ffedd5; color: #9a3412; }
.tc-badge-purple   { background: #f3e8ff; color: #7c3aed; }
.tc-badge-yellow   { background: #fef9c3; color: #854d0e; }
.tc-badge-pink     { background: #fce7f3; color: #9d174d; }
.tc-badge-gray     { background: #f3f4f6; color: #4b5563; }
.tc-badge-red      { background: #fee2e2; color: #991b1b; }
.tc-badge-upcoming { background: #eff6ff;  color: #2563eb; }
.tc-badge-today    { background: #dcfce7;  color: #166534; }
.tc-badge-past     { background: #f3f4f6;  color: #6b7280; }
.tc-badge-met      { background: #dcfce7;  color: #166534; }
.tc-badge-not-met  { background: #fee2e2;  color: #991b1b; }

/* Solid-color badges — saturated bg + white text (work in both modes as-is) */
.tc-badge-indigo  { background: #6366f1; color: #ffffff; }
.tc-badge-cyan    { background: #0891b2; color: #ffffff; }
.tc-badge-emerald { background: #059669; color: #ffffff; }
.tc-badge-amber   { background: #d97706; color: #ffffff; }

/* Dark-mode overrides for pastel badges */
@media (prefers-color-scheme: dark) {
  .tc-badge-blue     { background: #1e3a5f; color: #93c5fd; }
  .tc-badge-green    { background: #052e16; color: #4ade80; }
  .tc-badge-orange   { background: #431407; color: #fb923c; }
  .tc-badge-purple   { background: #2e1065; color: #c4b5fd; }
  .tc-badge-yellow   { background: #1c1917; color: #fde047; }
  .tc-badge-pink     { background: #500724; color: #fbcfe8; }
  .tc-badge-gray     { background: #334155; color: #94a3b8; }
  .tc-badge-red      { background: #450a0a; color: #fca5a5; }
  .tc-badge-upcoming { background: #1e3a5f; color: #93c5fd; }
  .tc-badge-today    { background: #052e16; color: #4ade80; }
  .tc-badge-past     { background: #334155; color: #94a3b8; }
  .tc-badge-met      { background: #052e16; color: #4ade80; }
  .tc-badge-not-met  { background: #450a0a; color: #fca5a5; }
}

/* ══════════════════════════════════════════════════════════
   CHARTS
══════════════════════════════════════════════════════════ */
[data-testid="stPlotlyChart"] {
  background-color: var(--tc-surface);
  border-radius: 0.75rem !important;
  border: 1px solid var(--tc-border);
  box-shadow: 0 1px 3px var(--tc-shadow);
  overflow: hidden;
  margin-top: 0.5rem;
}
[data-testid="stPlotlyChart"] > div {
  border-radius: 0.75rem !important;
}

/* ══════════════════════════════════════════════════════════
   EXPANDERS / FILTERS
══════════════════════════════════════════════════════════ */
[data-testid="stExpander"],
[data-testid="stExpander"] > div,
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpanderDetails"] {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
}
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] p,
[data-testid="stExpanderDetails"] p {
  color: var(--tc-text) !important;
}

/* ══════════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════════ */
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

/* ══════════════════════════════════════════════════════════
   FORM INPUTS
══════════════════════════════════════════════════════════ */
input, textarea, select,
[data-baseweb="input"],
[data-baseweb="input"] input,
[data-baseweb="textarea"],
[data-baseweb="select"],
[data-baseweb="select"] > div {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
  border-color: var(--tc-border2) !important;
}

[data-baseweb="select"] span,
[data-baseweb="select"] div[class*="valueContainer"],
[data-baseweb="select"] div[class*="singleValue"] {
  color: var(--tc-text) !important;
}

/* Dropdown menus */
[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="menu"] ul,
[role="listbox"],
[role="listbox"] li,
[role="option"] {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
}
[role="option"]:hover {
  background-color: var(--tc-hover) !important;
}

/* Labels */
.stSelectbox label, .stTextInput label,
.stDateInput label, .stTextArea label,
[data-testid="stWidgetLabel"] {
  color: var(--tc-text) !important;
}

/* Placeholders */
input::placeholder, textarea::placeholder {
  color: var(--tc-text3) !important;
}

/* ══════════════════════════════════════════════════════════
   DIALOGS / MODALS
══════════════════════════════════════════════════════════ */
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
  background-color: var(--tc-surface) !important;
}

[data-testid="stDialog"] h1, [data-testid="stDialog"] h2,
[data-testid="stDialog"] h3, [data-testid="stDialog"] h4,
[data-testid="stDialog"] h5, [data-testid="stDialog"] p,
[data-testid="stDialog"] span, [data-testid="stDialog"] label,
[data-testid="stDialog"] div,
[role="dialog"] h1, [role="dialog"] h2, [role="dialog"] h3,
[role="dialog"] h4, [role="dialog"] p, [role="dialog"] span,
[role="dialog"] div {
  color: var(--tc-text) !important;
}

[data-testid="stDialogHeader"],
[data-testid="stDialog"] header,
[role="dialog"] header {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
}

[data-testid="stDialog"] a, [role="dialog"] a {
  color: #2563eb !important;
}

[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {
  color: var(--tc-text) !important;
}

[data-testid="stDialog"] [data-testid="stCaptionContainer"],
[role="dialog"] [data-testid="stCaptionContainer"] {
  color: var(--tc-text2) !important;
}

[data-testid="stDialog"] hr, [role="dialog"] hr {
  border-color: var(--tc-border) !important;
}

[data-testid="stDialog"] input, [data-testid="stDialog"] textarea,
[data-testid="stDialog"] select,
[role="dialog"] input, [role="dialog"] textarea, [role="dialog"] select {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
  border-color: var(--tc-border2) !important;
}

[data-testid="stDialog"] [data-baseweb="select"],
[data-testid="stDialog"] [data-baseweb="select"] > div,
[role="dialog"] [data-baseweb="select"],
[role="dialog"] [data-baseweb="select"] > div {
  background-color: var(--tc-surface) !important;
  color: var(--tc-text) !important;
}

/* Dialog close button */
[data-testid="stDialog"] button[aria-label="Close"],
[role="dialog"] button[aria-label="Close"],
[data-testid="stDialogCloseButton"],
[data-testid="stDialog"] [data-testid="baseButton-header"],
[role="dialog"] [data-testid="baseButton-header"] {
  color: var(--tc-text) !important;
  background-color: var(--tc-btn-close) !important;
}
[data-testid="stDialog"] button[aria-label="Close"]:hover,
[role="dialog"] button[aria-label="Close"]:hover {
  background-color: var(--tc-btn-close-hover) !important;
  color: var(--tc-text) !important;
}
[data-testid="stDialog"] button[aria-label="Close"] svg,
[role="dialog"] button[aria-label="Close"] svg,
[data-testid="stDialog"] [data-testid="baseButton-header"] svg {
  stroke: var(--tc-text) !important;
  color: var(--tc-text) !important;
}

/* Modal class overrides */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background-color: rgba(0,0,0,0.6); z-index: 1000;
  display: flex; justify-content: center; align-items: flex-start;
  padding-top: 50px; overflow-y: auto;
}
.modal-container {
  background: var(--tc-surface);
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
  width: 90%; max-width: 700px;
  max-height: calc(100vh - 100px); overflow-y: auto; margin-bottom: 50px;
}
.modal-header {
  padding: 1.5rem; border-bottom: 1px solid var(--tc-border);
  position: sticky; top: 0;
  background: var(--tc-surface); border-radius: 1rem 1rem 0 0; z-index: 10;
}
.modal-body { padding: 1.5rem; }
.modal-close-btn {
  position: absolute; top: 1rem; right: 1rem;
  background: var(--tc-btn-close); border: none; border-radius: 50%;
  width: 32px; height: 32px; cursor: pointer; font-size: 1.25rem;
  color: var(--tc-text2); display: flex; align-items: center; justify-content: center;
}
.modal-close-btn:hover {
  background: var(--tc-btn-close-hover); color: var(--tc-text);
}
</style>"""
