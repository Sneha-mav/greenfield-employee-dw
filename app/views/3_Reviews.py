"""Page 3 — Performance Reviews."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import inject_css, section_header
from app.components.forms import submit_review_form
from app.components.tables import employee_reviews_table
from src.db_manager import DatabaseError, ValidationError
from src.entities.review import Review
from src.managers import ProjectManager, ReviewManager

inject_css()

st.title("Performance Reviews")
st.caption("Submit reviews for employees and view review history.")

@st.cache_data(ttl=300)
def _load_projects() -> list:
    pm = ProjectManager()
    projects = pm.list_projects(status="Active", limit=500)
    return [{"project_id": p.project_id, "project_name": p.project_name}
            for p in projects]

try:
    projects = _load_projects()
except DatabaseError as exc:
    st.error(f"Could not connect to database: {exc}")
    st.stop()

tab_submit, tab_history = st.tabs(["Submit Review", "Review History"])

with tab_submit:
    section_header("New Performance Review")
    data = submit_review_form(projects)
    if data is not None:
        try:
            review = Review(
                employee_id=data["employee_id"],
                review_date=data["review_date"],
                performance_rating=data["performance_rating"],
                project_id=data["project_id"],
                review_score=data["review_score"],
                job_satisfaction=data["job_satisfaction"],
                environment_satisfaction=data["environment_satisfaction"],
                salary_hike_pct=data["salary_hike_pct"],
            )
            rm = ReviewManager()
            review = rm.create(review, refresh_warehouse=True)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Review ID",   str(review.review_id))
            col2.metric("Rating",      f"{review.performance_rating}/5")
            col3.metric("Score",       f"{review.review_score:.0f}/100")
            col4.metric("Performance", "High" if review.is_high_performer else "Standard")
            st.success(f"Review {review.review_id} submitted for employee {data['employee_id']}.")
        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
        except DatabaseError as exc:
            st.error(f"Database error: {exc}")

with tab_history:
    section_header("Employee Review History")
    col_a, _, col_b, _2 = st.columns([2, 0.1, 1, 1])
    emp_id   = col_a.number_input("Employee ID", min_value=1, step=1, key="hist_emp_id")
    with col_b:
        st.markdown('<div style="margin-top: 1.9rem;"></div>', unsafe_allow_html=True)
        load_btn = st.button("Load reviews", use_container_width=True, key="load_reviews")

    if load_btn:
        try:
            import pandas as pd
            rm      = ReviewManager()
            reviews = rm.list_for_employee(int(emp_id))
            if reviews:
                rows = [r.to_dict() for r in reviews]
                df   = pd.DataFrame(rows)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Reviews",   len(reviews))
                c2.metric("Avg Rating",      f"{df['performance_rating'].mean():.2f}")
                c3.metric("Avg Score",       f"{df['review_score'].mean():.1f}")
                c4.metric("High Performers", int((df["performance_rating"] >= 4).sum()))
                st.divider()
            employee_reviews_table(reviews)
        except DatabaseError as exc:
            st.error(str(exc))
