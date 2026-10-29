import os
import sqlite3
from pathlib import Path
import pandas as pd

from app.config import DEFAULT_CSV_PATH, DEFAULT_DB_PATH

REQUIRED_COLUMNS = {
    "transaction_id",
    "order_date",
    "product",
    "category",
    "region",
    "sales_channel",
    "quantity",
    "unit_price",
    "discount_amount",
    "status",
}


def clean_data(csv_path: str = DEFAULT_CSV_PATH):
    """Read the CSV, validate structure, clean data, and return (dataframe, report)."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Sales CSV file not found at: {csv_path}")

    df = pd.read_csv(csv_path)
    report = {"rows_read": len(df)}

    # 1. Standardise column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Verify all required columns are present
    missing_cols = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_cols:
        raise ValueError(
            f"CSV file is missing required columns: {', '.join(missing_cols)}"
        )

    # Trim string columns
    for col in ["transaction_id", "product", "category", "region",
                "sales_channel", "status"]:
        df[col] = df[col].astype(str).str.strip()

    # 2. Remove duplicates (deterministic: keep first occurrence of transaction_id)
    before = len(df)
    df = df.drop_duplicates(subset="transaction_id", keep="first").copy()
    report["duplicates_removed"] = before - len(df)

    # 3. Parse dates explicitly: dataset uses DD-MM-YYYY
    parsed = pd.to_datetime(df["order_date"], format="%d-%m-%Y", errors="coerce")
    df["order_date"] = parsed.dt.strftime("%Y-%m-%d")
    df["month"] = parsed.dt.strftime("%Y-%m")

    # 4. Force numeric types; invalid non-numeric values become NaN
    for col in ["quantity", "unit_price", "discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Missing discount amounts default to zero
    df["discount_amount"] = df["discount_amount"].fillna(0)

    # 5. Calculate gross and net revenue:
    gross = df["quantity"] * df["unit_price"]
    df["revenue"] = gross - df["discount_amount"]

    # 6. Apply deterministic exclusion rules
    def check_row(row):
        if pd.isna(row["order_date"]):
            return "invalid date"
        if pd.isna(row["quantity"]) or pd.isna(row["unit_price"]):
            return "missing quantity or price"
        if row["quantity"] <= 0 or row["unit_price"] < 0:
            return "non-positive quantity or negative price"
        if str(row["status"]).strip().lower() != "completed":
            return f"status is {row['status']}"
        if row["discount_amount"] < 0:
            return "negative discount amount"
        row_gross = row["quantity"] * row["unit_price"]
        if row["discount_amount"] > row_gross:
            return "discount exceeds gross sales amount"
        return None

    df["exclusion_reason"] = df.apply(check_row, axis=1)
    df["counted"] = df["exclusion_reason"].isna().astype(int)

    report["rows_counted"] = int(df["counted"].sum())
    report["rows_excluded"] = int((df["counted"] == 0).sum())
    report["exclusions"] = df.loc[
        df["counted"] == 0, ["transaction_id", "exclusion_reason"]
    ].to_dict("records")

    return df, report


def load_to_db(csv_path: str = DEFAULT_CSV_PATH, db_path: str = DEFAULT_DB_PATH):
    """Clean the CSV and write it to a SQLite table called 'sales'."""
    df, report = clean_data(csv_path)

    # Ensure parent directory exists before creating the SQLite DB file
    Path(db_path).resolve().parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        df.to_sql("sales", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_month ON sales(month)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_counted ON sales(counted)")
    return report


if __name__ == "__main__":
    print(load_to_db())