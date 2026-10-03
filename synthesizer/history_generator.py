"""HistoryGenerator: builds SCD Type 2 version history for a subset of employees."""
import logging

import numpy as np
import pandas as pd

from synthesizer.data_synthesizer import SNAPSHOT_DATE

logger = logging.getLogger(__name__)

TRACKED = ["department", "job_role", "job_level", "monthly_income"]


class HistoryGenerator:
    def __init__(self, employees, subset_pct=0.18, max_lookback_years=3, seed=7):
        self._emp = employees
        self._subset_pct = subset_pct
        self._lookback = max_lookback_years
        self._rng = np.random.default_rng(seed)
        # role -> department map learned from the data, keeps roles consistent
        self._roles_by_dept = employees.groupby("department")["job_role"].unique().to_dict()

    def generate(self):
        """Return one row per version. Every employee gets >=1 version; the
        latest version always equals the current snapshot."""
        eligible = self._emp[self._emp["years_at_company"] >= 1]
        frac = min(self._subset_pct * len(self._emp) / len(eligible), 1.0)
        chosen = set(eligible.sample(frac=frac, random_state=int(self._rng.integers(1e6)))["employee_number"])
        rows = []
        for r in self._emp.itertuples(index=False):
            current = {c: getattr(r, c) for c in TRACKED}
            if r.employee_number not in chosen:
                rows.append(self._row(r.employee_number, current, r.hire_date, None, "initial"))
                continue
            rows.extend(self._build_versions(r, current))
        df = pd.DataFrame(rows)
        logger.info("History: %d versions for %d employees (%d with changes)",
                    len(df), len(self._emp), len(chosen))
        return df

    def _build_versions(self, r, current):
        n_events = int(self._rng.integers(1, 4))
        earliest = max(r.hire_date + pd.Timedelta(days=60), SNAPSHOT_DATE - pd.Timedelta(days=365 * self._lookback))
        span = (SNAPSHOT_DATE - pd.Timedelta(days=30) - earliest).days
        if span < 60 * n_events:
            n_events = max(span // 60, 1) if span >= 60 else 0
        if n_events == 0:
            return [self._row(r.employee_number, current, r.hire_date, None, "initial")]
        offsets = np.sort(self._rng.choice(np.arange(0, span), size=n_events, replace=False))
        # enforce minimum spacing so versions never collapse onto one day
        offsets = np.array([o + 60 * i for i, o in enumerate(offsets)]) % max(span, 1)
        offsets = np.unique(np.sort(offsets))
        dates = [earliest + pd.Timedelta(days=int(o)) for o in offsets]
        types = [self._rng.choice(["department_change", "promotion", "salary_bump"], p=[0.25, 0.35, 0.40])
                 for _ in dates]

        # walk backwards from the current state, reversing each change
        states = [current]
        for i in range(len(types) - 1, -1, -1):
            # a promotion needs a lower level to come from; otherwise it is a salary bump
            if types[i] == "promotion" and int(states[-1]["job_level"]) <= 1:
                types[i] = "salary_bump"
            states.append(self._reverse(states[-1], types[i]))
        states = states[::-1]  # states[0] = oldest, states[-1] = current

        rows = [self._row(r.employee_number, states[0], r.hire_date, None, "initial")]
        for d, ctype, st in zip(dates, types, states[1:]):
            rows.append(self._row(r.employee_number, st, d, None, ctype))
        # close every version at the day before the next one starts
        for i in range(len(rows) - 1):
            rows[i]["effective_to"] = rows[i + 1]["effective_from"] - pd.Timedelta(days=1)
        return rows

    def _reverse(self, s, ctype):
        prev = dict(s)
        if ctype == "department_change":
            others = [d for d in self._roles_by_dept if d != s["department"]]
            prev["department"] = self._rng.choice(others)
            prev["job_role"] = self._rng.choice(self._roles_by_dept[prev["department"]])
        elif ctype == "promotion":
            prev["job_level"] = max(int(s["job_level"]) - 1, 1)
            prev["monthly_income"] = min(int(s["monthly_income"] * self._rng.uniform(0.80, 0.92)), int(s["monthly_income"]) - 1)
        else:  # salary_bump
            prev["monthly_income"] = min(int(s["monthly_income"] * self._rng.uniform(0.88, 0.96)), int(s["monthly_income"]) - 1)
        return prev

    @staticmethod
    def _row(emp_id, state, start, end, ctype):
        return {"employee_number": emp_id, **state,
                "effective_from": start, "effective_to": end, "change_type": ctype}