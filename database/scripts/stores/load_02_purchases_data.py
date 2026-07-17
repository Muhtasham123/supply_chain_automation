"""Load the Main Purchases table"""

import pandas as pd
pd.set_option("display.max_columns", None)
from database.scripts.etl_common import (
    read_sheet, clean_text, clean_int, clean_date
)
from pathlib import Path
directory = Path(r"C:\Users\hp\Desktop\internship\project\data\purchases")

files = list(directory.iterdir())

EXCEL_FILE = files[0]

#Order of columns matters here (must be same as order of ROWS list)
PURCHASES_COLUMNS = [
    "ref_no", "qty", "branch", "amount", "ppc_store", "required_d", "purchase", "mop", "dc_no"  ,"bill_no", "sourcing_o", "item_code ", "supplier", "po_number"
]

def load_purchases(conn):
    df = read_sheet("Sheet1", EXCEL_FILE)
    purchases_rows = []

    for _, row in df.iterrows():
        purchases_rows.append((
            clean_text(row.get("Ref No")),
            clean_int(row.get("Qty")),
            clean_text(row.get("Branch")),
            clean_text(row.get("Amount")),
            clean_date(row.get("PPC/Store")),
            clean_date(row.get("Required D")),
            clean_date(row.get("Purchase")),
            clean_text(row.get("MOP")),
            clean_text(row.get("DC No")),
            clean_text(row.get("Bill No")),
            clean_text(row.get("Sourcing O")),
            clean_text(row.get("Item Code")),
            clean_text(row.get("Supplier")),
            clean_text(row.get("PO Numbe")),
        ))
    
    with conn.cursor() as cur:
        for row in purchases_rows:
            cur.execute(
                f"INSERT INTO purchases_data ({', '.join(PURCHASES_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(PURCHASES_COLUMNS))}) "
                f"RETURNING ref_no",
                row
            )

    conn.commit()
    print(f"Purchases : inserted {len(purchases_rows)} rows")
