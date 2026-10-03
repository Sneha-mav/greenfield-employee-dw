"""DataSynthesizer: scales the IBM HR Attrition snapshot to 100k+ employees."""
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

logger = logging.getLogger(__name__)

SNAPSHOT_DATE = pd.Timestamp("2025-12-31")  # the "current" state of every employee

# Numeric columns that get small random jitter when resampled
JITTER_COLS = {
    "age": (0.05, 18, 60),
    "monthly_income": (0.08, 1009, 19999),
    "daily_rate": (0.05, 102, 1499),
    "hourly_rate": (0.05, 30, 100),
    "monthly_rate": (0.05, 2094, 26999),
    "distance_from_home": (0.20, 1, 29),
    "total_working_years": (0.10, 0, 40),
}
DROP_COLS = ["employee_count", "over18", "standard_hours"]  # constant in IBM data


class DataSynthesizer:
    def __init__(self, raw_path, target_rows=100_000, seed=42):
        self._raw_path = Path(raw_path)
        self._target_rows = target_rows
        self._rng = np.random.default_rng(seed)
        self._fake = Faker("en_IN")
        Faker.seed(seed)
        self._base = None

    # ---------- load ----------
    def load_base(self):
        try:
            df = pd.read_csv(self._raw_path)
        except FileNotFoundError:
            logger.error("Raw file not found: %s", self._raw_path)
            raise
        df.columns = [self._snake(c) for c in df.columns]
        df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
        self._base = df
        logger.info("Loaded %d base rows", len(df))
        return df

    @staticmethod
    def _snake(name):
        out = ""
        for i, ch in enumerate(name):
            if ch.isupper() and i and not name[i - 1].isupper():
                out += "_"
            out += ch.lower()
        return out

    # ---------- scale ----------
    def scale(self):
        if self._base is None:
            self.load_base()
        start = time.time()
        base = self._base
        n_extra = self._target_rows - len(base)
        idx = self._rng.integers(0, len(base), size=max(n_extra, 0))
        extra = base.iloc[idx].copy().reset_index(drop=True)

        for col, (pct, lo, hi) in JITTER_COLS.items():
            noise = self._rng.normal(1.0, pct, size=len(extra))
            extra[col] = (extra[col] * noise).round().clip(lo, hi).astype(int)

        # keep tenure fields consistent: years_in_role/promotion/manager <= years_at_company
        extra["years_at_company"] = np.minimum(
            extra["years_at_company"] + self._rng.integers(-1, 2, len(extra)),
            extra["total_working_years"],
        ).clip(lower=0)
        for col in ["years_in_current_role", "years_since_last_promotion", "years_with_curr_manager"]:
            extra[col] = np.minimum(extra[col], extra["years_at_company"])

        start_id = int(base["employee_number"].max()) + 1
        extra["employee_number"] = np.arange(start_id, start_id + len(extra))
        df = pd.concat([base, extra], ignore_index=True)
        df = self._add_identity_columns(df)
        logger.info("Scaled to %d rows in %.1fs", len(df), time.time() - start)
        return df

    # ---------- identity: names, email, hire date ----------
    def _add_identity_columns(self, df):
        n = len(df)
        # Faker per-row is slow at 100k; build from a name pool, then combine
        firsts = np.array([self._fake.first_name() for _ in range(3000)])
        lasts = np.array([self._fake.last_name() for _ in range(3000)])
        df["first_name"] = firsts[self._rng.integers(0, len(firsts), n)]
        df["last_name"] = lasts[self._rng.integers(0, len(lasts), n)]
        df["email"] = (
            df["first_name"].str.lower() + "." + df["last_name"].str.lower()
            + df["employee_number"].astype(str) + "@company.com"
        )
        df["city"] = np.array([self._fake.city() for _ in range(300)])[self._rng.integers(0, 300, n)]
        days = (df["years_at_company"] * 365 + self._rng.integers(0, 300, n)).astype(int)
        df["hire_date"] = SNAPSHOT_DATE - pd.to_timedelta(days, unit="D")
        return df

    # ---------- dirty data for the CTE cleaning step (Assumption A5) ----------
    def inject_noise(self, df, dup_pct=0.015, null_pct=0.01):
        dupes = df.sample(frac=dup_pct, random_state=int(self._rng.integers(1e6)))
        out = pd.concat([df, dupes], ignore_index=True)
        for col in ["education_field", "marital_status", "distance_from_home"]:
            mask = self._rng.random(len(out)) < null_pct
            out.loc[mask, col] = None
        # messy casing/whitespace on a slice, so cleaning has real work to do
        mask = self._rng.random(len(out)) < 0.01
        out.loc[mask, "department"] = out.loc[mask, "department"].str.upper() + " "
        logger.info("Injected %d duplicates, nulls and casing noise", len(dupes))
        return out.sample(frac=1, random_state=1).reset_index(drop=True)