import streamlit as st
import pandas as pd
import datetime

def init_mock_data():
    if 'employees' not in st.session_state:
        st.session_state.employees = pd.DataFrame([
            {"ID": "EMP001", "Name": "Alice Smith", "Age": 30, "Gender": "Female", "Department": "Engineering", "Job Role": "Software Engineer", "Salary": 90000, "Joining Date": datetime.date(2021, 1, 15), "Experience": 5, "Is Active": True, "Effective Start Date": datetime.date(2021, 1, 15), "Effective End Date": datetime.date(9999, 12, 31)},
            {"ID": "EMP002", "Name": "Bob Johnson", "Age": 35, "Gender": "Male", "Department": "Sales", "Job Role": "Sales Manager", "Salary": 85000, "Joining Date": datetime.date(2019, 3, 10), "Experience": 8, "Is Active": True, "Effective Start Date": datetime.date(2019, 3, 10), "Effective End Date": datetime.date(9999, 12, 31)},
            {"ID": "EMP003", "Name": "Charlie Brown", "Age": 28, "Gender": "Male", "Department": "HR", "Job Role": "HR Specialist", "Salary": 60000, "Joining Date": datetime.date(2022, 6, 1), "Experience": 3, "Is Active": True, "Effective Start Date": datetime.date(2022, 6, 1), "Effective End Date": datetime.date(9999, 12, 31)},
            {"ID": "EMP004", "Name": "Diana Prince", "Age": 40, "Gender": "Female", "Department": "Engineering", "Job Role": "Engineering Manager", "Salary": 130000, "Joining Date": datetime.date(2018, 11, 20), "Experience": 12, "Is Active": True, "Effective Start Date": datetime.date(2018, 11, 20), "Effective End Date": datetime.date(9999, 12, 31)},
            {"ID": "EMP005", "Name": "Evan Wright", "Age": 25, "Gender": "Male", "Department": "Marketing", "Job Role": "Content Strategist", "Salary": 65000, "Joining Date": datetime.date(2023, 1, 10), "Experience": 2, "Is Active": True, "Effective Start Date": datetime.date(2023, 1, 10), "Effective End Date": datetime.date(9999, 12, 31)},
        ])

    if 'projects' not in st.session_state:
        st.session_state.projects = pd.DataFrame([
            {"Project Name": "Website Redesign", "Department": "Engineering", "Project Manager": "Diana Prince", "Start Date": datetime.date(2023, 1, 15), "End Date": datetime.date(2023, 6, 15), "Assigned Employees": "Alice Smith, Evan Wright"},
            {"Project Name": "Q3 Sales Campaign", "Department": "Sales", "Project Manager": "Bob Johnson", "Start Date": datetime.date(2023, 7, 1), "End Date": datetime.date(2023, 9, 30), "Assigned Employees": "Bob Johnson"},
        ])

    if 'reviews' not in st.session_state:
        st.session_state.reviews = pd.DataFrame([
            {"Employee": "Alice Smith", "Review Date": datetime.date(2023, 12, 1), "Rating": 4, "Manager Comments": "Great work on the backend APIs.", "Goals": "Lead a project next year"},
            {"Employee": "Bob Johnson", "Review Date": datetime.date(2023, 12, 5), "Rating": 5, "Manager Comments": "Exceeded sales targets.", "Goals": "Expand into new territories"},
        ])

def get_employees(active_only=False):
    df = st.session_state.employees
    if active_only:
        return df[df["Is Active"] == True]
    return df

def add_employee(data):
    data["Is Active"] = True
    data["Effective Start Date"] = datetime.date.today()
    data["Effective End Date"] = datetime.date(9999, 12, 31)
    st.session_state.employees = pd.concat([st.session_state.employees, pd.DataFrame([data])], ignore_index=True)

def update_employee_department(emp_id, new_department):
    '''Simulates SCD Type 2 logic for Department Update.'''
    df = st.session_state.employees
    # Find current active record
    active_idx = df[(df["ID"] == emp_id) & (df["Is Active"] == True)].index
    if not active_idx.empty:
        idx = active_idx[0]
        # Close old record
        df.at[idx, "Is Active"] = False
        df.at[idx, "Effective End Date"] = datetime.date.today()
        
        # Create new record
        new_record = df.loc[idx].copy()
        new_record["Department"] = new_department
        new_record["Is Active"] = True
        new_record["Effective Start Date"] = datetime.date.today()
        new_record["Effective End Date"] = datetime.date(9999, 12, 31)
        
        st.session_state.employees = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        return True
    return False

def get_projects():
    return st.session_state.projects

def add_project(data):
    st.session_state.projects = pd.concat([st.session_state.projects, pd.DataFrame([data])], ignore_index=True)

def get_reviews():
    return st.session_state.reviews

def add_review(data):
    st.session_state.reviews = pd.concat([st.session_state.reviews, pd.DataFrame([data])], ignore_index=True)

def get_dashboard_data():
    df_emp = get_employees(active_only=True)
    df_proj = st.session_state.projects
    df_rev = st.session_state.reviews

    total_employees = len(df_emp)
    total_departments = df_emp["Department"].nunique() if total_employees > 0 else 0
    total_projects = len(df_proj)
    avg_performance = df_rev["Rating"].mean() if len(df_rev) > 0 else 0

    return {
        "total_employees": total_employees,
        "total_departments": total_departments,
        "total_projects": total_projects,
        "avg_performance": round(avg_performance, 1)
    }
