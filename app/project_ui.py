import streamlit as st
import datetime
from db_queries import (
    get_projects, add_project, get_employees,
    reset_fallback_flag, show_fallback_warning,
)


def render_projects():
    reset_fallback_flag()
    st.markdown("<h1>Project Management</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#475569;font-size:1.05rem;margin-top:-12px;margin-bottom:12px;'>"
        "Track active projects, assign teams and monitor delivery timelines.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    with st.expander("➕  Create New Project", expanded=False):
        st.info(
            "✅ **Phase 2 — Database Write Enabled.** You can now safely create projects. "
            "Data will be written to MySQL and synced to OLAP dimensions."
        )
        with st.form("project_form", clear_on_submit=True):
            st.markdown("#### Project Details")
            st.markdown("<hr>", unsafe_allow_html=True)

            # Use first page of real employees for the picker
            df_emp    = get_employees(active_only=True, page=1)
            emp_names = (df_emp["ID"].astype(str) + "  —  " + df_emp["Name"]).tolist() if not df_emp.empty else []

            c1, c2 = st.columns(2)
            with c1:
                name       = st.text_input("Project Name", placeholder="e.g. Q4 Data Migration")
                manager    = (st.selectbox("Project Manager", emp_names)
                              if emp_names else st.text_input("Project Manager"))
                start_date = st.date_input("Start Date")
            with c2:
                dept          = st.text_input("Department", placeholder="e.g. Engineering")
                assigned_emps = st.multiselect("Assign Employees", emp_names) if emp_names else []
                end_date      = st.date_input("End Date")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀  Create Project"):
                if not name.strip():
                    st.error("Project Name is required.")
                elif not dept.strip():
                    st.error("Department is required.")
                elif end_date < start_date:
                    st.error("End Date cannot be before Start Date.")
                else:
                    try:
                        add_project({
                            "Project Name":      name,
                            "Department":        dept,
                            "Project Manager":   manager,
                            "Start Date":        start_date,
                            "End Date":          end_date,
                            "Assigned Employees": assigned_emps,  # pass list directly
                        })
                        st.success(f"✅ Project **{name}** created successfully!")
                    except Exception as ex:
                        st.error(f"🚫 {ex}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋  Active Projects")

    df_proj = get_projects()
    show_fallback_warning()  # single banner after all fetches
    if not df_proj.empty:
        st.caption(f"{len(df_proj):,} projects loaded from database.")
        st.dataframe(df_proj, width="stretch", hide_index=True)
    else:
        st.info("No projects found in the database.")
