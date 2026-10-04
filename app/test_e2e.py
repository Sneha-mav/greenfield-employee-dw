import sys
import os
import datetime

sys.path.insert(0, os.path.abspath('..'))

from src.db_manager import DatabaseConnection
from app.db_queries import add_employee, get_employees

db = DatabaseConnection()
test_id = 99998
raw_id = f"EMP{test_id}"

# 1. Cleanup any existing test data
with db.transaction() as cur:
    cur.execute("DELETE FROM assignments WHERE employee_id = %s", (test_id,))
    cur.execute("DELETE FROM employee_history WHERE employee_id = %s", (test_id,))
    cur.execute("DELETE FROM fact_performance_reviews WHERE employee_key = (SELECT employee_key FROM dim_employee WHERE employee_id = %s LIMIT 1)", (test_id,))
    cur.execute("DELETE FROM dim_employee WHERE employee_id = %s", (test_id,))
    cur.execute("DELETE FROM employees WHERE employee_id = %s", (test_id,))

# 2. Add employee
new_emp = {
    "ID": raw_id,
    "Name": "UI Test Employee",
    "Age": 25,
    "Gender": "Female",
    "Department": "IT",
    "Job Role": "Data Analyst",
    "Salary": 75000,
    "Joining Date": datetime.date.today(),
    "Experience": 2
}

print(f"Adding test employee {raw_id}...")
add_employee(new_emp)
print("Employee added successfully!")

# 3. Verify OLTP
oltp_emp = db.fetch_one("SELECT * FROM employees WHERE employee_id = %s", (test_id,))
if oltp_emp:
    print("OLTP: Employee found.")
else:
    print("OLTP: Employee NOT found.")

# 4. Verify OLAP
olap_emp = db.fetch_one("SELECT * FROM dim_employee WHERE employee_id = %s", (test_id,))
if olap_emp:
    print("OLAP: Employee found.")
else:
    print("OLAP: Employee NOT found.")

# 5. Verify UI (get_employees)
df = get_employees(active_only=True, page=1)
if not df.empty and df.iloc[0]["ID"] == test_id:
    print("UI: Employee is now visible at the top of the list!")
else:
    print("UI: Employee NOT at the top of the list.")
    print(df.head())

# 6. Cleanup
print("Cleaning up test data...")
with db.transaction() as cur:
    cur.execute("DELETE FROM employee_history WHERE employee_id = %s", (test_id,))
    cur.execute("DELETE FROM dim_employee WHERE employee_id = %s", (test_id,))
    cur.execute("DELETE FROM employees WHERE employee_id = %s", (test_id,))
print("Cleanup done.")
