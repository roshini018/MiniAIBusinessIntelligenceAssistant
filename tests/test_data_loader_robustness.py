import os
import sqlite3
import pytest
from pathlib import Path
from app.data_loader import clean_data, load_to_db


def test_missing_csv_file_raises_filenotfound(tmp_path):
    non_existent = str(tmp_path / "does_not_exist.csv")
    with pytest.raises(FileNotFoundError, match="Sales CSV file not found at"):
        clean_data(non_existent)


def test_missing_required_columns_raises_value_error(tmp_path):
    bad_csv = tmp_path / "missing_cols.csv"
    bad_csv.write_text("transaction_id,order_date,product\nT1,01-01-2026,Laptop\n")
    with pytest.raises(ValueError) as e:
        clean_data(str(bad_csv))
    msg = str(e.value)
    assert "missing required columns" in msg
    assert "quantity" in msg
    assert "unit_price" in msg
    assert "region" in msg


def test_column_names_trimmed_and_lowercased(tmp_path):
    """Headers with mixed case and extra spaces must be normalized without error."""
    spaced_csv = tmp_path / "spaced_cols.csv"
    spaced_csv.write_text(
        " Transaction_Id , ORDER_DATE , Product , Category , Region , Sales_Channel , Quantity , Unit_Price , Discount_Amount , Status \n"
        "T1,01-01-2026,Laptop,Electronics,North,Online,1,1000,0,Completed\n"
    )
    df, report = clean_data(str(spaced_csv))
    assert "transaction_id" in df.columns
    assert "order_date" in df.columns
    assert "unit_price" in df.columns
    assert report["rows_counted"] == 1


def test_empty_csv_with_headers_only(tmp_path):
    """Empty CSV with headers must produce a clean report with 0 rows."""
    empty_csv = tmp_path / "empty_headers.csv"
    empty_csv.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
    )
    df, report = clean_data(str(empty_csv))
    assert report["rows_read"] == 0
    assert report["duplicates_removed"] == 0
    assert report["rows_counted"] == 0
    assert report["rows_excluded"] == 0
    assert len(df) == 0


def test_duplicate_transaction_ids_kept_first(tmp_path):
    """First occurrence of duplicate transaction_id must be kept, subsequent dropped."""
    dup_csv = tmp_path / "dups.csv"
    dup_csv.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "D1,01-01-2026,FirstProduct,Electronics,North,Online,1,100,0,Completed\n"
        "D1,02-01-2026,SecondProduct,Electronics,South,Store,5,500,0,Completed\n"
    )
    df, report = clean_data(str(dup_csv))
    assert report["rows_read"] == 2
    assert report["duplicates_removed"] == 1
    assert len(df) == 1
    assert df.iloc[0]["product"] == "FirstProduct"


def test_invalid_date_formats_and_unparseable_strings(tmp_path):
    """Dates not matching DD-MM-YYYY or invalid calendar dates must be marked as invalid date."""
    date_csv = tmp_path / "dates.csv"
    date_csv.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "DT1,32-01-2026,Laptop,Electronics,North,Online,1,1000,0,Completed\n" # invalid day
        "DT2,15-13-2026,Laptop,Electronics,North,Online,1,1000,0,Completed\n" # invalid month
        "DT3,not-a-date,Laptop,Electronics,North,Online,1,1000,0,Completed\n"
        "DT4,15-05-2026,Laptop,Electronics,North,Online,1,1000,0,Completed\n" # valid
    )
    df, report = clean_data(str(date_csv))
    assert report["rows_counted"] == 1
    assert report["rows_excluded"] == 3
    reasons = {x["transaction_id"]: x["exclusion_reason"] for x in report["exclusions"]}
    assert reasons["DT1"] == "invalid date"
    assert reasons["DT2"] == "invalid date"
    assert reasons["DT3"] == "invalid date"


def test_invalid_numerics_coerce_to_nan_and_excluded(tmp_path):
    """Non-numeric values in quantity or price become NaN and get excluded."""
    num_csv = tmp_path / "numerics.csv"
    num_csv.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "N1,01-01-2026,Laptop,Electronics,North,Online,two,1000,0,Completed\n"
        "N2,02-01-2026,Laptop,Electronics,North,Online,1,thousand,0,Completed\n"
        "N3,03-01-2026,Laptop,Electronics,North,Online,1,1000,abc,Completed\n" # invalid discount coerced to 0!
    )
    df, report = clean_data(str(num_csv))
    reasons = {x["transaction_id"]: x["exclusion_reason"] for x in report["exclusions"]}
    assert reasons["N1"] == "missing quantity or price"
    assert reasons["N2"] == "missing quantity or price"
    # N3 has valid qty & price; discount coerced to NaN then fillna(0) -> valid!
    assert "N3" not in reasons


def test_database_directory_creation_and_indices(tmp_path):
    """load_to_db must automatically create non-existent parent directories and SQLite indices."""
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "T1,01-01-2026,Laptop,Electronics,North,Online,1,1000,0,Completed\n"
    )
    # Deep nested path that does not yet exist
    deep_db = str(tmp_path / "nested" / "deeply" / "sales.db")
    assert not Path(deep_db).parent.exists()

    report = load_to_db(str(csv_file), deep_db)
    assert report["rows_counted"] == 1
    assert Path(deep_db).exists()

    # Verify indices in SQLite
    with sqlite3.connect(deep_db) as conn:
        indices = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        ]
        assert "idx_month" in indices
        assert "idx_counted" in indices
