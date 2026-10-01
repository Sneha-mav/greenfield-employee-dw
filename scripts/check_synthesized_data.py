"""
checks whether the CSV files look consistent before loading in MySQL.

"""
import sys
from pathlib import Path

import pandas as pd

D = Path(sys.argv[1] if len(sys.argv) > 1 else "data/synthesized")
emp = pd.read_csv(D / "employees_synth.csv", parse_dates=["hire_date"])
his = pd.read_csv(D / "employee_history.csv", parse_dates=["effective_from", "effective_to"])
prj = pd.read_csv(D / "projects.csv")
asg = pd.read_csv(D / "assignments.csv")
rev = pd.read_csv(D / "reviews.csv", parse_dates=["review_date"])

problems = 0


def check(name, ok, detail=""):
    global problems
    problems += 0 if ok else 1
    print(f"[{'OK ' if ok else 'BAD'}] {name} {detail}")


ids = set(emp["employee_number"])
check("employees: 100k unique employee_number", len(ids) == 100_000, f"({len(ids)} unique, {len(emp)} rows)")
print(f"      duplicate employee rows: {len(emp) - len(ids)}")
print("      NULLs per column (only non-zero):", emp.isna().sum()[lambda s: s > 0].to_dict())
print("      department values:", sorted(emp["department"].dropna().unique())[:12])

check("history: all employees exist", set(his["employee_number"]) <= ids)
check("history: exactly 1 current row (effective_to NULL) per employee",
      his["effective_to"].isna().sum() == his["employee_number"].nunique(),
      f"({his['effective_to'].isna().sum()} current, {his['employee_number'].nunique()} employees)")
print("      change_type counts:", his["change_type"].value_counts().to_dict())

check("projects: unique project_id", prj["project_id"].is_unique)
check("assignments: employees exist", set(asg["employee_number"]) <= ids)
check("assignments: projects exist", set(asg["project_id"]) <= set(prj["project_id"]))

check("reviews: employees exist", set(rev["employee_number"]) <= ids)
check("reviews: projects exist (when not NULL)", set(rev["project_id"].dropna().astype(int)) <= set(prj["project_id"]))
hire = emp.drop_duplicates("employee_number").set_index("employee_number")["hire_date"]
before = (rev["review_date"] < rev["employee_number"].map(hire)).sum()
check("reviews: none dated before hire_date", before == 0, f"({before} violations)")
print("      reviews per year:", rev["review_date"].dt.year.value_counts().sort_index().to_dict())
print("      rating range:", rev["performance_rating"].min(), "-", rev["performance_rating"].max())
print("\nRESULT:", "all good" if problems == 0 else f"{problems} problem(s), tell the team before loading")
