"""Load the Main Stocks table"""

import pandas as pd
from database.scripts.etl_common import (
    read_sheet, clean_text, clean_number
)

from pathlib import Path
current_dir = Path(__file__).resolve().parent
directory = Path(current_dir.parents[2] / "data" / "stocks")

files = list(directory.iterdir())

EXCEL_FILES = files

#Order of columns matters here (must be same as order of ROWS list)
STOCK_COLUMNS = ["item_code", "branch", "hold_qty", "stock_qty", "stock_qty_amount",  "available_qty", "available_amount"]

#--> Order must be same as columns order
STOCK_HEADERS = [
    ("ItemCode", clean_text),	("Branch", clean_text), ("Hold Qty", clean_number), ("StockQty", clean_number),	("Stock Qty Amou", clean_number), ("Available Qty", clean_number), ("Available Amoun",clean_number),
]

def load_stock(conn):
    dataframes = []
    stock_rows = []
    
    for file in EXCEL_FILES:
        dataframes.append(read_sheet("Sheet1", file))

    for df in dataframes:
        for _, row in df.iterrows():
            row_tuple = ()
            for header, cleaning_function in STOCK_HEADERS:
                row_tuple = row_tuple + (cleaning_function(row.get(header)), )
            stock_rows.append(row_tuple)
    
    with conn.cursor() as cur:
        for row in stock_rows:
            cur.execute(
                f"INSERT INTO stock ({', '.join(STOCK_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(STOCK_COLUMNS))}) "
                f"RETURNING stock_id",
                row
            )

    conn.commit()
    print(f"Stocks : inserted {len(stock_rows)} rows")
