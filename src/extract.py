
from pathlib import Path
import logging
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_FILE = BASE_DIR / "data" / "raw" / "rbi_house_price_index.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def extract_data() -> pd.DataFrame:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"RBI dataset not found: {RAW_FILE}"
        )

    df = pd.read_csv(RAW_FILE)

    required_columns = {
        "base_per",
        "center_rn",
        "time_period",
        "obs_value",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    logger.info("Successfully extracted %s records", len(df))
    logger.info("Total columns: %s", len(df.columns))

    return df


if __name__ == "__main__":
    data = extract_data()

    print("\nDataset preview:")
    print(data.head())

    print("\nBase periods:")
    print(data["base_per"].value_counts())

    print("\nCities:")
    print(sorted(data["center_rn"].unique()))

    print("\nMissing values:")
    print(data.isna().sum())
