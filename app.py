import streamlit as st

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="TechCongress Fellows Dashboard",
    page_icon="🏛️",
    layout="wide"
)

# ============ LOGIN PAGE ============
def login_page():
    """Display login form."""
    st.markdown("""
    <style>
        .stApp {
            background-color: #f8fafc;
        }
        [data-testid="stAppViewContainer"] {
            background-color: #f8fafc;
        }
        [data-testid="stHeader"] {
            background-color: #f8fafc;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stApp"],
        .main,
        .block-container {
            background-color: #f8fafc !important;
            color: #1f2937 !important;
        }
        h1, h2, h3, p, span, label {
            color: #1f2937 !important;
        }
        input, textarea, select,
        [data-baseweb="input"],
        [data-baseweb="input"] input {
            background-color: white !important;
            color: #1f2937 !important;
        }
        .stSelectbox label, .stTextInput label {
            color: #1f2937 !important;
        }
        input::placeholder,
        textarea::placeholder {
            color: #9ca3af !important;
        }
        .stButton button,
        .stFormSubmitButton button,
        [data-testid="stFormSubmitButton"] button {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 0.5rem !important;
        }
        .stButton button:hover,
        .stFormSubmitButton button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            background-color: #2563eb !important;
            color: #ffffff !important;
        }
        .stFormSubmitButton button p,
        [data-testid="stFormSubmitButton"] button p,
        .stFormSubmitButton button span,
        [data-testid="stFormSubmitButton"] button span {
            color: #ffffff !important;
        }
        /* Password visibility toggle */
        [data-testid="stTextInput"] button,
        [data-testid="stTextInput"] button svg {
            color: #6b7280 !important;
            stroke: #6b7280 !important;
            background-color: transparent !important;
        }
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
        }
        [data-testid="stSidebar"] * {
            color: #1f2937 !important;
        }
        [data-testid="stSidebarContent"] {
            background-color: #ffffff !important;
        }
        [data-testid="stToolbar"],
        [data-testid="stToolbar"] button,
        header[data-testid="stHeader"] {
            background-color: #f8fafc !important;
            color: #1f2937 !important;
        }
        [data-testid="stToolbar"] svg,
        header[data-testid="stHeader"] svg {
            color: #1f2937 !important;
            stroke: #1f2937 !important;
            fill: #1f2937 !important;
        }
        [data-testid="stMainMenu"],
        [data-testid="stMainMenu"] button {
            color: #1f2937 !important;
        }
        [data-testid="stMainMenu"] svg {
            color: #1f2937 !important;
            stroke: #1f2937 !important;
        }
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 2rem;
            background: white;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([2, 1, 2])
    with col_b:
        st.image("TechCongress Logo (black).png", width="stretch")
    st.markdown("<h1 style='text-align: center; color: #1f2937;'>TechCongress Fellows Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Please log in to continue</p>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if username == st.secrets["auth"]["username"] and password == st.secrets["auth"]["password"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid username or password")

# ============ PAGE NAVIGATION ============
if st.session_state.get("authenticated"):
    current_fellows = st.Page("pages/current-fellows-page.py", title="Current Fellows", default=True)
    alumni = st.Page("pages/alumni-page.py", title="Alumni")
    pg = st.navigation([current_fellows, alumni])
else:
    pg = st.navigation([st.Page(login_page, title="Log in", default=True)])

pg.run()
