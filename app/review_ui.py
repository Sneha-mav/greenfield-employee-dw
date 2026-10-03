import streamlit as st
import datetime
from db_queries import (
    get_reviews, get_review_count, add_review, get_employees,
    reset_fallback_flag, show_fallback_warning,
)


def render_reviews():
    reset_fallback_flag()
    st.markdown("<h1>Performance Reviews</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#475569;font-size:1.05rem;margin-top:-12px;margin-bottom:28px;'>"
        "Submit and track employee performance evaluations.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("📝  Submit Performance Review", expanded=False):
        st.info(
            "✅ **Phase 2 — Database Write Enabled.** You can now safely submit performance reviews. "
            "Data will be written to MySQL and synced to OLAP dimensions."
        )
        with st.form("review_form", clear_on_submit=True):
            st.markdown("#### Review Details")
            st.markdown("<hr>", unsafe_allow_html=True)

            # Use first page of real employees for the picker
            df_emp    = get_employees(active_only=True, page=1)
            emp_names = (df_emp["ID"].astype(str) + "  —  " + df_emp["Name"]).tolist() if not df_emp.empty else []

            c1, c2 = st.columns(2)
            with c1:
                employee    = (st.selectbox("Select Employee", emp_names)
                               if emp_names else st.text_input("Employee Name"))
                review_date = st.date_input("Review Date", value=datetime.date.today())
            with c2:
                rating = st.slider("Performance Rating  (1 = Poor → 5 = Excellent)", 1, 5, 3)

            comments = st.text_area(
                "Manager Comments",
                placeholder="Describe key achievements, contributions and observations...",
            )
            goals = st.text_area(
                "Goals for Next Period",
                placeholder="Set specific, measurable goals for the next review cycle...",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✅  Submit Review"):
                if not employee or not str(employee).strip():
                    st.error("Please select or enter an employee name.")
                elif not (1 <= rating <= 5):
                    st.error("Rating must be between 1 and 5.")
                else:
                    try:
                        add_review({
                            "Employee":        employee,
                            "Review Date":     review_date,
                            "Performance Rating": rating,
                            "Manager Comments": comments,
                            "Goals": goals
                        })
                        st.success(f"✅ Performance Review for **{employee}** submitted successfully!")
                    except Exception as ex:
                        st.error(f"🚫 {ex}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⭐  Recent Performance Reviews")

    total_rev   = get_review_count()
    total_pages = max(1, -(-total_rev // 500))
    rev_page = st.number_input(
        f"Page (500 reviews/page — {total_rev:,} total reviews)",
        min_value=1, max_value=total_pages, value=1, step=1,
        key="rev_page",
    )
    df_rev = get_reviews(page=rev_page)
    show_fallback_warning()  # single banner after all fetches
    if not df_rev.empty:
        st.caption(
            f"Showing page {rev_page} of {total_pages} — {len(df_rev):,} reviews on this page."
        )
        st.dataframe(df_rev, width="stretch", hide_index=True)
    else:
        st.info("No performance reviews on record yet.")
