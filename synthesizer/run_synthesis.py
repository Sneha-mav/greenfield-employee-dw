"""Entry point: python -m synthesizer.run_synthesis"""
import logging
import time
from pathlib import Path

from synthesizer.data_synthesizer import DataSynthesizer
from synthesizer.history_generator import HistoryGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RAW = Path("data/raw/WA_Fn-UseC_-HR-Employee-Attrition.csv")
OUT = Path("data/synthesized")


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    synth = DataSynthesizer(RAW, target_rows=100_000)
    clean = synth.scale()

    history = HistoryGenerator(clean).generate()      # built from CLEAN data
    history.to_csv(OUT / "employee_history.csv", index=False)

    noisy = synth.inject_noise(clean)                  # dupes/nulls only in the staging file
    noisy.to_csv(OUT / "employees_synth.csv", index=False)
    print(f"employees_synth.csv: {len(noisy):,} rows | employee_history.csv: {len(history):,} rows | {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()