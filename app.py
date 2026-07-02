"""
TrackMySpend - main Streamlit app.

Changelog vs original app1.py:
  - Security: bcrypt password hashing w/ transparent migration (auth.py, db.py)
  - Portability: Tesseract path & secrets via config.py / .env, no hardcoded
    Windows paths
  - Bug fix: edit/delete now keyed by expense id, not merchant name
  - Feature: budgets now persist to the database (previously reset every rerun)
  - Feature: auto-categorization suggested from OCR text via a real trained
    model (categorize.py) -- the old category_model.pkl was unused dead weight
  - Reliability: currency conversion no longer depends on the defunct
    forex-python free API (currency.py)
  - Feature: CSV export of expenses
  - Feature: light/dark theme toggle (previously force-light only)
  - Feature: upgraded AI Assistant -- still works with zero setup (rule-based),
    but will use the real Claude API for natural-language answers if an
    ANTHROPIC_API_KEY is configured
"""
import streamlit as st
import pandas as pd
import re
from PIL import Image

import config
import db
from categorize import predict_category
from currency import convert_to_inr
from filters import filter_and_sort, paginate  # search / sort / pagination for View Expenses

# Optional OCR import - degrade gracefully if tesseract isn't installed
try:
    import pytesseract
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    OCR_AVAILABLE = config.TESSERACT_CMD is not None
except ImportError:
    OCR_AVAILABLE = False

import plotly.express as px

# -----------------------------
# Page config + theme
# -----------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "theme" not in st.session_state:
    st.session_state.theme = "light"

def apply_theme():
    """
    Modern-minimal design system for TrackMySpend.

    Palette rationale: a deep teal/emerald accent (#0F766E) reads as "money,
    growth, calm" without leaning on the generic AI-default terracotta/cream
    or neon-on-black looks. Background is a cool off-white (not cream) so
    numbers and charts stay the visual focus. Cards use soft shadows instead
    of hard borders for a lighter, more minimal feel.
    """
    if st.session_state.theme == "dark":
        bg = "#0B1120"; surface = "#131B2E"; border = "#1E293B"
        fg = "#E5E7EB"; muted = "#94A3B8"
        accent = "#2DD4BF"; accent_fg = "#04201C"
        shadow = "rgba(0, 0, 0, 0.35)"
    else:
        bg = "#F7F8FA"; surface = "#FFFFFF"; border = "#E7EAEE"
        fg = "#111827"; muted = "#6B7280"
        accent = "#0F766E"; accent_fg = "#FFFFFF"
        shadow = "rgba(15, 23, 42, 0.07)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@600;700&display=swap');

    :root {{
        --tms-bg: {bg}; --tms-surface: {surface}; --tms-border: {border};
        --tms-fg: {fg}; --tms-muted: {muted};
        --tms-accent: {accent}; --tms-accent-fg: {accent_fg};
        --tms-shadow: {shadow};
    }}

    html, body, .stApp {{
        background-color: var(--tms-bg) !important;
        color: var(--tms-fg) !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }}

    h1, h2, h3 {{
        font-family: 'Inter Tight', 'Inter', sans-serif !important;
        letter-spacing: -0.01em;
        color: var(--tms-fg) !important;
    }}
    h4, h5, h6, p, span, label {{ color: var(--tms-fg) !important; }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--tms-muted) !important; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: var(--tms-surface) !important;
        border-right: 1px solid var(--tms-border);
    }}
    [data-testid="stSidebar"] * {{ color: var(--tms-fg) !important; }}

    /* Bordered containers -> soft cards (used for filter panels, forms, chart groups) */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--tms-surface);
        border: 1px solid var(--tms-border) !important;
        border-radius: 14px !important;
        box-shadow: 0 1px 3px var(--tms-shadow);
        padding: 0.25rem 0.25rem;
    }}

    /* Metrics as cards */
    [data-testid="stMetric"] {{
        background: var(--tms-surface);
        border: 1px solid var(--tms-border);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px var(--tms-shadow);
    }}
    [data-testid="stMetricLabel"] {{ color: var(--tms-muted) !important; font-weight: 500; }}
    [data-testid="stMetricValue"] {{ color: var(--tms-fg) !important; font-family: 'Inter Tight', sans-serif; }}

    /* Inputs */
    input, textarea, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {{
        background-color: var(--tms-surface) !important;
        color: var(--tms-fg) !important;
        border-radius: 10px !important;
        border: 1px solid var(--tms-border) !important;
    }}
    input:focus, textarea:focus {{
        border-color: var(--tms-accent) !important;
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--tms-accent) 20%, transparent) !important;
    }}

    /* Buttons */
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {{
        background-color: var(--tms-accent) !important;
        color: var(--tms-accent-fg) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.5em 1.2em !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px var(--tms-shadow);
        transition: transform 0.06s ease, filter 0.15s ease;
    }}
    div.stButton > button:hover, div.stDownloadButton > button:hover, div.stFormSubmitButton > button:hover {{
        filter: brightness(1.1);
        transform: translateY(-1px);
    }}

    /* Radio nav in sidebar styled like a pill list */
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        border-radius: 10px;
        padding: 0.3rem 0.6rem;
        margin-bottom: 2px;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background-color: var(--tms-bg);
    }}

    /* Dataframe / table */
    [data-testid="stDataFrame"] {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--tms-border);
    }}

    hr {{ border-color: var(--tms-border) !important; }}
    </style>
    """, unsafe_allow_html=True)

apply_theme()

def style_fig(fig):
    """Applies the modern-minimal theme to a Plotly figure: transparent
    background so it sits flush on the card, Inter font, and a muted grid."""
    fg = "#E5E7EB" if st.session_state.theme == "dark" else "#111827"
    grid = "#1E293B" if st.session_state.theme == "dark" else "#E7EAEE"
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=fg),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid)
    return fig

# -----------------------------
# Session State
# -----------------------------
db.init_db()
if "user_id" not in st.session_state: st.session_state.user_id = None
if "page" not in st.session_state: st.session_state.page = "login"

def navigate_to(page_name: str):
    st.session_state.page = page_name
    st.rerun()

# -----------------------------
# Login Page
# -----------------------------
def login_page():
    st.markdown(f"<h1 style='text-align:center; color:var(--tms-accent);'>💰 {config.APP_NAME}</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:var(--tms-muted); font-weight:500;'>SPEND LESS, SAVE MORE</h3>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        action = st.radio("Action", ["Login", "Register"], horizontal=True)
        submitted = st.form_submit_button("Submit")
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            elif action == "Login":
                uid = db.login_user(username, password)
                if uid:
                    st.session_state.user_id = uid
                    navigate_to("dashboard")
                else:
                    st.error("❌ Invalid username or password")
            else:
                if len(password) < 6:
                    st.error("⚠️ Password should be at least 6 characters.")
                else:
                    ok = db.register_user(username, password)
                    if ok:
                        st.success("🎉 Account created. Please log in.")
                    else:
                        st.error("⚠️ Username already exists")

# -----------------------------
# OCR + receipt parsing (currency now via currency.py)
# -----------------------------
def parse_receipt_text(text: str):
    merchant = text.split("\n")[0] if text else "Unknown"
    date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})", text)
    date = date_match.group(1) if date_match else str(pd.Timestamp.today().date())
    amt_match = re.findall(r"\d+\.?\d*", text)
    total = float(amt_match[-1]) if amt_match else 0.0

    if "$" in text:
        total = convert_to_inr(total, "USD")
    elif "€" in text:
        total = convert_to_inr(total, "EUR")
    elif "£" in text:
        total = convert_to_inr(total, "GBP")

    suggested_category = predict_category(f"{merchant} {text}")
    return merchant, date, total, suggested_category

# -----------------------------
# Pages
# -----------------------------
def home_page():
    st.subheader("🏠 Dashboard Overview")
    df = db.load_expenses(st.session_state.user_id)

    if df.empty:
        st.warning("No expenses found yet. Add your first expense!")
        return

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    total_spent = df["total"].sum()

    days = st.number_input("Show data for last X days:", min_value=1, max_value=365, value=30)
    recent_df = df[df["date"] >= (pd.Timestamp.today() - pd.Timedelta(days=days))]
    recent_avg_daily = recent_df["total"].sum() / max(days, 1)
    top_cat_recent = recent_df.groupby("category")["total"].sum().idxmax() if not recent_df.empty else "—"

    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Total Spent (all time)", f"₹{total_spent:,.2f}")
    m2.metric(f"📆 Avg / day (last {days}d)", f"₹{recent_avg_daily:,.2f}")
    m3.metric("🏷️ Top category (recent)", top_cat_recent)

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            daily = recent_df.groupby("date")["total"].sum().reset_index()
            st.plotly_chart(style_fig(px.line(daily, x="date", y="total", title="Daily Expenses", markers=True)), use_container_width=True)
        with col2:
            cat_sum = recent_df.groupby("category")["total"].sum().reset_index()
            st.plotly_chart(style_fig(px.bar(cat_sum, x="total", y="category", orientation="h", title="Expenses per Category")), use_container_width=True)

    with st.container(border=True):
        col3, col4 = st.columns([1, 2])
        with col3:
            st.plotly_chart(style_fig(px.pie(cat_sum, values="total", names="category", hole=0.4, title="Spending Distribution")), use_container_width=True)
        with col4:
            monthly = recent_df.groupby(recent_df["date"].dt.to_period("M"))["total"].sum().reset_index()
            monthly["date"] = monthly["date"].astype(str)
            st.plotly_chart(style_fig(px.line(monthly, x="date", y="total", markers=True, title="Monthly Expenses")), use_container_width=True)

def add_expense_page():
    st.subheader("💳 Add Expense")

    if not OCR_AVAILABLE:
        st.caption("ℹ️ OCR is unavailable (Tesseract not found). You can still add expenses manually, or set TESSERACT_CMD in your .env file.")

    uploaded_file = st.file_uploader("📷 Upload Receipt (Image)", type=["png", "jpg", "jpeg"], disabled=not OCR_AVAILABLE)
    merchant, date, total = "", str(pd.Timestamp.today().date()), 0.0
    suggested_category = None

    if uploaded_file and OCR_AVAILABLE:
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)
        merchant, date, total, suggested_category = parse_receipt_text(text)
        st.text_area("📝 OCR Extracted Text", text, height=150)
        if suggested_category:
            st.info(f"🤖 Suggested category based on receipt text: **{suggested_category}**")

    categories = ["Travel", "Food", "Office", "Other"]
    default_idx = categories.index(suggested_category) if suggested_category in categories else 0

    with st.form("add_expense"):
        merchant_name = st.text_input("Merchant*", merchant)
        date_val = st.date_input("Date*", pd.to_datetime(date))
        total_val = st.number_input("Total*", min_value=0.0, step=0.01, value=float(total))
        category = st.selectbox("Category*", categories, index=default_idx)
        desc = st.text_area("Description")
        submitted = st.form_submit_button("💾 Save")
        if submitted:
            if not merchant_name.strip():
                st.error("Merchant is required.")
            else:
                db.save_expense(st.session_state.user_id, merchant_name, date_val, total_val, category, desc)
                st.success("✅ Expense added successfully!")

def view_expenses_page():
    st.subheader("📂 View Expenses")
    df = db.load_expenses(st.session_state.user_id)

    if df.empty:
        st.info("No expenses to show.")
        return

    # Search / filter / sort controls, then paginate the result
    filtered = filter_and_sort(df, key_prefix="view")
    st.caption(f"Matching {len(filtered)} of {len(df)} total expenses")

    page_df = paginate(filtered, key_prefix="view", default_page_size=10)
    st.dataframe(page_df, use_container_width=True, hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export filtered results as CSV", data=csv, file_name="expenses_filtered.csv", mime="text/csv")

    if not filtered.empty:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                cat_sum = filtered.groupby("category")["total"].sum().reset_index()
                st.plotly_chart(style_fig(px.pie(cat_sum, values="total", names="category", hole=0.3, title="Expense Breakdown by Category")), use_container_width=True)
            with col2:
                monthly = filtered.groupby(filtered["date"].str[:7])["total"].sum().reset_index()
                st.plotly_chart(style_fig(px.bar(monthly, x="date", y="total", title="Monthly Totals (filtered)")), use_container_width=True)

def edit_delete_expense_page():
    st.subheader("✏️ Edit / Delete Expense")
    df = db.load_expenses(st.session_state.user_id)
    if not df.empty:
        # Fixed: select by unique id (shown alongside merchant/date for clarity),
        # not by merchant name alone -- previously ambiguous if merchants repeated.
        df["label"] = df.apply(lambda r: f"#{r['id']} - {r['merchant']} - {r['date']} - ₹{r['total']:.2f}", axis=1)
        selected_label = st.selectbox("Select Expense", df["label"])
        row = df[df["label"] == selected_label].iloc[0]

        with st.form("edit_expense"):
            merchant = st.text_input("Merchant", row["merchant"])
            total = st.number_input("Total", value=float(row["total"]), step=0.01)
            category = st.selectbox("Category", ["Travel", "Food", "Office", "Other"],
                                     index=["Travel", "Food", "Office", "Other"].index(row["category"])
                                     if row["category"] in ["Travel", "Food", "Office", "Other"] else 0)
            update = st.form_submit_button("✅ Update")
            delete = st.form_submit_button("🗑️ Delete")
            if update:
                db.update_expense(int(row["id"]), merchant, total, category)
                st.success("Updated successfully!")
                st.rerun()
            if delete:
                db.delete_expense(int(row["id"]))
                st.warning("Deleted successfully!")
                st.rerun()
    else:
        st.info("No expenses to edit.")

def weekly_notifications_page():
    st.subheader("🔔 Weekly Notifications")
    df = db.load_expenses(st.session_state.user_id)

    if df.empty:
        st.info("Add expenses to receive notifications.")
        return

    today = pd.Timestamp.today()
    week_df = df[pd.to_datetime(df["date"]) >= (today - pd.Timedelta(days=7))]

    if week_df.empty:
        st.info("No expenses recorded this week.")
        return

    week_sum = week_df["total"].sum()
    avg_daily = week_sum / 7
    st.info(f"📅 This week you spent **₹{week_sum:.2f}** (avg ₹{avg_daily:.2f}/day).")

    top_cat = week_df.groupby("category")["total"].sum().idxmax()
    st.warning(f"⚡ Most of your money went into **{top_cat}** this week. Try to limit spending here!")

    prev_week_df = df[(pd.to_datetime(df["date"]) < (today - pd.Timedelta(days=7))) &
                      (pd.to_datetime(df["date"]) >= (today - pd.Timedelta(days=14)))]
    if not prev_week_df.empty:
        prev_sum = prev_week_df["total"].sum()
        if week_sum > prev_sum:
            st.error(f"⬆️ Spending increased by ₹{week_sum - prev_sum:.2f} compared to last week.")
        else:
            st.success(f"⬇️ Spending decreased by ₹{prev_sum - week_sum:.2f} compared to last week.")

def suggestions_page():
    st.subheader("💡 Suggestions")
    df = db.load_expenses(st.session_state.user_id)

    if df.empty:
        st.info("Add expenses to get suggestions.")
        return

    total_spent = df["total"].sum()
    top_category = df.groupby("category")["total"].sum().idxmax()

    if total_spent > 10000:
        st.warning("⚠️ Spending is very high. Reduce unnecessary purchases.")
    elif total_spent > 5000:
        st.info("📉 Spending is moderate. Keep an eye on frequent purchases.")
    else:
        st.success("✅ Spending is under control.")

    st.info(f"📊 You are spending the most on **{top_category}**. Consider setting a limit for this category.")
    st.success("💡 Try automating savings by allocating at least 10% of income to SIPs or FDs.")

def ai_assistant_page():
    st.subheader("🤖 AI Assistant")
    df = db.load_expenses(st.session_state.user_id)

    query = st.text_area("Ask about your spending & savings:")

    if st.button("💬 Get Insight"):
        if not query:
            st.info("Type a question to get insights.")
            return
        if df.empty:
            st.warning("No expense data found. Add expenses first.")
            return

        if config.ANTHROPIC_API_KEY:
            answer = _ask_claude(query, df)
            st.success(answer)
        else:
            answer = _rule_based_answer(query, df)
            st.success(answer)
            st.caption("ℹ️ Using rule-based answers. Set ANTHROPIC_API_KEY in .env for free-form natural-language answers.")

def _rule_based_answer(query: str, df: pd.DataFrame) -> str:
    q = query.lower()
    if "highest" in q or "biggest" in q:
        top = df.groupby("category")["total"].sum().idxmax()
        return f"📌 Your highest spending category is **{top}**."
    elif "monthly" in q:
        monthly = df.groupby(df["date"].str[:7])["total"].sum().reset_index()
        return "📅 Monthly spending:\n" + monthly.to_string(index=False)
    elif "average" in q:
        return f"📊 Your average expense is ₹{df['total'].mean():.2f}."
    elif "save" in q:
        return "💡 Try saving 20% of your monthly allowance/income."
    return "🤖 I recommend tracking your top 3 categories and setting budgets for them."

def _ask_claude(query: str, df: pd.DataFrame) -> str:
    """Optional real LLM-backed assistant, used only if ANTHROPIC_API_KEY is set."""
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    summary = df.groupby("category")["total"].sum().to_dict()
    prompt = (
        f"You are a personal finance assistant. Here is a user's expense summary by category (INR): {summary}. "
        f"Total records: {len(df)}. Answer this question concisely in 2-4 sentences: {query}"
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in resp.content if hasattr(block, "text"))
    except Exception as e:
        return f"⚠️ Couldn't reach the AI backend ({e}). Falling back to basic insight: " + _rule_based_answer(query, df)

def budget_management_page():
    st.subheader("💼 Budget Management")
    df = db.load_expenses(st.session_state.user_id)

    month = pd.Timestamp.today().strftime("%Y-%m")
    spent_this_month = df[df["date"].str.startswith(month)]["total"].sum() if not df.empty else 0.0

    # Budget now persists in the DB instead of resetting every rerun
    saved_budget = db.get_budget(st.session_state.user_id, month)
    budget = st.number_input("Set Monthly Budget (₹):", min_value=0.0, step=100.0, value=saved_budget)
    if st.button("💾 Save Budget"):
        db.set_budget(st.session_state.user_id, month, budget)
        st.success("Budget saved.")

    st.metric("💸 Spent This Month", f"₹{spent_this_month:.2f}")

    if budget > 0:
        remaining = budget - spent_this_month
        st.metric("💰 Remaining Budget", f"₹{remaining:.2f}")

        if spent_this_month > budget:
            st.error("⚠️ You have exceeded your budget. Cut down expenses immediately.")
        elif spent_this_month > 0.8 * budget:
            st.warning("⚠️ You have used more than 80% of your budget. Be cautious.")
        else:
            st.success("✅ You are within budget. Keep going!")

        if not df.empty:
            cat_sum = df[df["date"].str.startswith(month)].groupby("category")["total"].sum().reset_index()
            if not cat_sum.empty:
                top_cat = cat_sum.sort_values("total", ascending=False).iloc[0]
                st.info(f"📊 Most spending this month is on **{top_cat['category']}** (₹{top_cat['total']:.2f}).")

# -----------------------------
# Dashboard Navigation
# -----------------------------
def dashboard_page():
    with st.sidebar:
        st.image("logo.png", width=120)
        username = db.get_username(st.session_state.user_id)
        st.success(f"Logged in as: {username}")

        theme_choice = st.toggle("🌙 Dark mode", value=(st.session_state.theme == "dark"))
        new_theme = "dark" if theme_choice else "light"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()

        st.markdown("---")
        page_choice = st.radio("Navigation", [
            "🏠 Home",
            "💳 Add Expense",
            "📂 View Expenses",
            "✏️ Edit / Delete Expense",
            "🔔 Weekly Notifications",
            "💡 Suggestions",
            "🤖 AI Assistant",
            "💼 Budget Management"
        ])
        st.markdown("---")
        if st.button("🚪 Logout", key="logout"):
            st.session_state.user_id = None
            navigate_to("login")

    if page_choice == "🏠 Home": home_page()
    elif page_choice == "💳 Add Expense": add_expense_page()
    elif page_choice == "📂 View Expenses": view_expenses_page()
    elif page_choice == "✏️ Edit / Delete Expense": edit_delete_expense_page()
    elif page_choice == "🔔 Weekly Notifications": weekly_notifications_page()
    elif page_choice == "💡 Suggestions": suggestions_page()
    elif page_choice == "🤖 AI Assistant": ai_assistant_page()
    elif page_choice == "💼 Budget Management": budget_management_page()

# -----------------------------
# Render Pages
# -----------------------------
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "dashboard":
    dashboard_page()
