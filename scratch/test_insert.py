import sys
import os
import datetime

sys.path.insert(0, os.path.abspath('.'))

from app.db_queries import add_employee, get_employees

new_emp = {
    "ID": "EMP99999",
    "Name": "Test Employee",
    "Age": 30,
    "Gender": "Other",
    "Department": "Sales",
    "Job Role": "Sales Executive",
    "Salary": 60000,
    "Joining Date": datetime.date.today(),
    "Experience": 5
}

print("Adding employee...")
try:
    add_employee(new_emp)
    print("Employee added successfully!")
except Exception as e:
    print(f"Error adding employee: {e}")

print("Fetching employees...")
df = get_employees(active_only=True)
emp_rows = df[df["ID"] == 99999]
print("Employee in DataFrame:")
print(emp_rows)

if not emp_rows.empty:
    print("SUCCESS: Employee found.")
else:
    print("FAILURE: Employee NOT found in DataFrame.")
