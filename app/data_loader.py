import sqlite3
import pandas as pd

CSV_PATH = "data/sales.csv"
DB_PATH = "data/sales.db"


def clean_data(csv_path: str = CSV_PATH):
    """Read the CSV, clean it, and return (dataframe, report)."""
    df = pd.read_csv(csv_path)
    report = {"rows_read": len(df)}

    # 1. Standardise column names and trim text values
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["transaction_id", "product", "category", "region",
                "sales_channel", "status"]:
        df[col] = df[col].astype(str).str.strip()

    # 2. Remove duplicates (same transaction id appearing twice)
    before = len(df)
    df = df.drop_duplicates(subset="transaction_id", keep="first")
    report["duplicates_removed"] = before - len(df)

    # 3. Parse dates explicitly: the file uses DD-MM-YYYY
    parsed = pd.to_datetime(df["order_date"], format="%d-%m-%Y", errors="coerce")
    df["order_date"] = parsed.dt.strftime("%Y-%m-%d")
    df["month"] = parsed.dt.strftime("%Y-%m")

    # 4. Force numeric types; bad values become NaN instead of crashing
    for col in ["quantity", "unit_price", "discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["discount_amount"] = df["discount_amount"].fillna(0)

    # 5. Calculate revenue (stays NaN if quantity or price is missing)
    df["revenue"] = df["quantity"] * df["unit_price"] - df["discount_amount"]

    # 6. Decide whether each row counts toward revenue, and why not
    def check_row(row):
        if pd.isna(row["order_date"]):
            return "invalid date"
        if pd.isna(row["quantity"]) or pd.isna(row["unit_price"]):
            return "missing quantity or price"
        if row["quantity"] <= 0 or row["unit_price"] < 0:
            return "non-positive quantity or negative price"
        if row["status"].lower() != "completed":
            return f"status is {row['status']}"
        return None

    df["exclusion_reason"] = df.apply(check_row, axis=1)
    df["counted"] = df["exclusion_reason"].isna().astype(int)

    report["rows_counted"] = int(df["counted"].sum())
    report["rows_excluded"] = int((df["counted"] == 0).sum())
    report["exclusions"] = df.loc[df["counted"] == 0,
                                  ["transaction_id", "exclusion_reason"]
                                  ].to_dict("records")
    return df, report


def load_to_db(csv_path: str = CSV_PATH, db_path: str = DB_PATH):
    """Clean the CSV and write it to a SQLite table called 'sales'."""
    df, report = clean_data(csv_path)
    with sqlite3.connect(db_path) as conn:
        df.to_sql("sales", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_month ON sales(month)")
    return report


if __name__ == "__main__":
    print(load_to_db())