import os
import subprocess
import sys
from pathlib import Path


def run_startup() -> None:
    output_dir = Path("data/output")
    transactions = output_dir / "transactions.csv"
    model = Path("ml/models/saved/classifier.pkl")
    db = output_dir / "subscriptions.db"

    # Generate dataset if missing
    if not transactions.exists():
        print("Generating dataset...")
        subprocess.run([sys.executable, "-m", "data.generator.generate"], check=True)

    # Train model if missing
    if not model.exists():
        print("Training model...")
        subprocess.run([sys.executable, "-m", "ml.models.train"], check=True)

    # Initialise DB if missing
    if not db.exists():
        print("Initializing database...")
        subprocess.run([sys.executable, "-m", "api.init_db"], check=True)

    print("Startup complete.")


if __name__ == "__main__":
    run_startup()
