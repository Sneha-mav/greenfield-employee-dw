"""EntityGenerator: projects, assignments and performance reviews, linked to employees by employee_number."""
import logging

import numpy as np
import pandas as pd
from faker import Faker

from synthesizer.data_synthesizer import SNAPSHOT_DATE

logger = logging.getLogger(__name__)

REVIEW_YEARS = range(2020, 2026)
PROJECT_PREFIX = ["Atlas", "Phoenix", "Orion", "Nimbus", "Vertex", "Helios", "Apex", "Zenith", "Aurora", "Pulse"]
PROJECT_TOPIC = ["Migration", "Onboarding Revamp", "Compliance Audit", "Analytics Platform", "Cost Optimisation",
                 "Customer Portal", "Talent Pipeline", "Process Automation", "Data Lake", "Quality Programme"]
ASSIGNMENT_ROLES = ["Contributor", "Lead", "Analyst", "Reviewer", "Coordinator"]


class EntityGenerator:
    def __init__(self, employees, n_projects=500, seed=11):
        self._emp = employees.drop_duplicates("employee_number").reset_index(drop=True)
        self._n_projects = n_projects
        self._rng = np.random.default_rng(seed)
        self._fake = Faker("en_IN")
        Faker.seed(seed)

    # ---------- projects ----------
    def generate_projects(self):
        n = self._n_projects
        depts = self._emp["department"].unique()
        start = SNAPSHOT_DATE - pd.to_timedelta(self._rng.integers(200, 365 * 8, n), unit="D")
        duration = self._rng.integers(300, 1800, n)
        end = start + pd.to_timedelta(duration, unit="D")
        status = np.where(end > SNAPSHOT_DATE, self._rng.choice(["Active", "On Hold"], n, p=[0.85, 0.15]), "Completed")
        names = [f"{PROJECT_PREFIX[i % 10]} {PROJECT_TOPIC[(i // 10) % 10]} {i + 1}" for i in range(n)]
        df = pd.DataFrame({
            "project_id": np.arange(1, n + 1), "project_name": names,
            "department": self._rng.choice(depts, n), "status": status,
            "start_date": start, "end_date": pd.Series(end).where(status == "Completed", pd.NaT),
        })
        self._projects = df
        return df

    # ---------- assignments ----------
    def generate_assignments(self):
        emp, proj, rng = self._emp, self._projects, self._rng
        rows = []
        for k, share in ((1, 0.85), (2, 0.20)):  # 85% get one project, 20% a second
            sel = emp[rng.random(len(emp)) < share][["employee_number", "department", "hire_date"]].copy()
            # pick a project, preferring the employee's own department (80%)
            sel["project_id"] = rng.choice(proj["project_id"], len(sel))
            same = rng.random(len(sel)) < 0.8
            for d, grp in sel[same].groupby("department"):
                pool = proj.loc[proj["department"] == d, "project_id"].to_numpy()
                if len(pool):
                    sel.loc[grp.index, "project_id"] = rng.choice(pool, len(grp))
            rows.append(sel)
        a = pd.concat(rows, ignore_index=True).drop_duplicates(["employee_number", "project_id"])
        a = a.merge(proj[["project_id", "start_date", "end_date"]].rename(
            columns={"start_date": "p_start", "end_date": "p_end"}), on="project_id")
        earliest = a[["hire_date", "p_start"]].max(axis=1)
        latest = a["p_end"].fillna(SNAPSHOT_DATE).clip(upper=SNAPSHOT_DATE)
        a = a[earliest < latest - pd.Timedelta(days=30)].copy()      # employee must overlap the project
        earliest, latest = earliest[a.index], latest[a.index]
        span = (latest - earliest).dt.days.to_numpy()
        a["start_date"] = earliest + pd.to_timedelta((rng.random(len(a)) * span * 0.4).astype(int), unit="D")
        ended = a["p_end"].notna()
        a["end_date"] = pd.Series(latest).where(ended, pd.NaT)
        a["role_on_project"] = rng.choice(ASSIGNMENT_ROLES, len(a), p=[0.55, 0.1, 0.2, 0.1, 0.05])
        a["allocation_pct"] = rng.choice([25, 50, 75, 100], len(a), p=[0.15, 0.35, 0.3, 0.2])
        a = a.reset_index(drop=True)
        a.insert(0, "assignment_id", np.arange(1, len(a) + 1))
        out = a[["assignment_id", "employee_number", "project_id", "role_on_project",
                 "allocation_pct", "start_date", "end_date"]]
        self._assignments = out
        return out

    # ---------- reviews ----------
    def generate_reviews(self):
        emp, rng = self._emp, self._rng
        years = pd.DataFrame({"review_year": list(REVIEW_YEARS)})
        r = emp[["employee_number", "hire_date", "performance_rating", "job_satisfaction",
                 "environment_satisfaction", "percent_salary_hike"]].merge(years, how="cross")
        offset = rng.integers(0, 15, len(r))
        r["review_date"] = pd.to_datetime(r["review_year"].astype(str) + "-12-15") + pd.to_timedelta(offset, unit="D")
        r = r[r["review_date"] > r["hire_date"] + pd.Timedelta(days=120)]   # only after ~4 months of service
        # ~3 reviews per employee, drawn at random from the eligible years so every year 2020-2025 has data (YoY trends)
        r["_k"] = rng.random(len(r))
        r = r.sort_values(["employee_number", "_k"]).groupby("employee_number").head(3).drop(columns="_k").copy()

        base = r["performance_rating"].to_numpy()                          # IBM 3/4 scale, widened to 1-5
        trend = (r["review_year"].to_numpy() - 2022) * 0.05
        rating = np.clip(np.rint(base + rng.normal(0.4 + trend, 0.7, len(r))), 1, 5).astype(int)
        r["performance_rating"] = rating
        r["review_score"] = np.clip(rating * 18 + rng.normal(5, 6, len(r)), 0, 100).round(1)
        for col in ("job_satisfaction", "environment_satisfaction"):
            r[col] = np.clip(r[col] + rng.integers(-1, 2, len(r)), 1, 4)
        r["salary_hike_pct"] = np.clip(r["percent_salary_hike"] + rng.integers(-3, 4, len(r)), 0, 30)

        # attach the project the employee was actually working on at review time (NULL if none)
        a = self._assignments[["employee_number", "project_id", "start_date", "end_date"]]
        m = r[["employee_number", "review_date"]].reset_index().merge(a, on="employee_number", how="left")
        ok = (m["start_date"] <= m["review_date"]) & (m["end_date"].isna() | (m["end_date"] >= m["review_date"]))
        m = m[ok].drop_duplicates("index").set_index("index")["project_id"]
        r["project_id"] = m.reindex(r.index)
        r = r.sort_values("review_date").reset_index(drop=True)
        r.insert(0, "review_id", np.arange(1, len(r) + 1))
        return r[["review_id", "employee_number", "project_id", "review_date", "performance_rating",
                  "review_score", "job_satisfaction", "environment_satisfaction", "salary_hike_pct"]]

    def generate_all(self):
        p = self.generate_projects()
        a = self.generate_assignments()
        r = self.generate_reviews()
        logger.info("Projects %d | Assignments %d | Reviews %d", len(p), len(a), len(r))
        return p, a, r