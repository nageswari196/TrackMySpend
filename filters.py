"""
Reusable search, filter, sort, and pagination controls for expense tables.
Kept separate from app.py so the same controls can be reused anywhere a
list of expenses is shown (currently: View Expenses page).
"""
import pandas as pd
import streamlit as st

SORT_OPTIONS = ["Newest first", "Oldest first", "Amount: High to Low", "Amount: Low to High"]

def filter_and_sort(df: pd.DataFrame, key_prefix: str = "flt") -> pd.DataFrame:
    """Renders search/filter/sort controls in a card and returns the filtered+sorted df."""
    if df.empty:
        return df

    working = df.copy()
    working["_date"] = pd.to_datetime(working["date"])

    with st.container(border=True):
        st.markdown("##### 🔍 Search & filter")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            search = st.text_input(
                "Search merchant or description",
                placeholder="e.g. starbucks, uber, groceries…",
                key=f"{key_prefix}_search",
                label_visibility="collapsed",
            )
        with c2:
            categories = st.multiselect(
                "Category",
                options=sorted(working["category"].dropna().unique().tolist()),
                key=f"{key_prefix}_cats",
                placeholder="All categories",
                label_visibility="collapsed",
            )
        with c3:
            sort_option = st.selectbox(
                "Sort by", SORT_OPTIONS, key=f"{key_prefix}_sort", label_visibility="collapsed"
            )

        c4, c5 = st.columns(2)
        min_date, max_date = working["_date"].min(), working["_date"].max()
        with c4:
            start_date = st.date_input("From", value=min_date, key=f"{key_prefix}_start")
        with c5:
            end_date = st.date_input("To", value=max_date, key=f"{key_prefix}_end")

    if search:
        mask = (
            working["merchant"].str.contains(search, case=False, na=False)
            | working["description"].str.contains(search, case=False, na=False)
        )
        working = working[mask]

    if categories:
        working = working[working["category"].isin(categories)]

    working = working[
        (working["_date"] >= pd.to_datetime(start_date)) & (working["_date"] <= pd.to_datetime(end_date))
    ]

    if sort_option == "Newest first":
        working = working.sort_values("_date", ascending=False)
    elif sort_option == "Oldest first":
        working = working.sort_values("_date", ascending=True)
    elif sort_option == "Amount: High to Low":
        working = working.sort_values("total", ascending=False)
    else:
        working = working.sort_values("total", ascending=True)

    return working.drop(columns=["_date"])

def paginate(df: pd.DataFrame, key_prefix: str = "pg", default_page_size: int = 10) -> pd.DataFrame:
    """Renders page-size + page controls and returns just the current page's rows."""
    if df.empty:
        st.info("No expenses match your filters.")
        return df

    total = len(df)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        page_size = st.selectbox("Rows per page", [10, 25, 50, 100],
                                  index=[10, 25, 50, 100].index(default_page_size),
                                  key=f"{key_prefix}_size")
    total_pages = max(1, (total - 1) // page_size + 1)
    with c2:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1,
                                key=f"{key_prefix}_page")
    with c3:
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        st.markdown(f"<div style='padding-top:1.8em; color:var(--tms-muted);'>Showing {start + 1}–{end} of {total}</div>",
                    unsafe_allow_html=True)

    start = (page - 1) * page_size
    return df.iloc[start:start + page_size]
