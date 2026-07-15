"""Load the items table which is the master table that 
   is being referanced from almost all other store and
   imports related tables"""

import pandas as pd
from database.scripts.etl_common import (
    read_sheet, clean_text,
)
from pathlib import Path

EXCEL_FILE = Path.cwd() / "data" / "Item Database.xlsx"

#Order of columns matters here (must be same as order of columns in sheet)
ITEMS_COLUMNS = [
    "item_code", "item", "specs",  "group_name", "material_standard", "item_category","uom",
]

def load_items(conn):
    df = read_sheet("Sheet1", EXCEL_FILE)
    items_rows = []

    for _, row in df.iterrows():
        items_rows.append((
            clean_text(row.get("ItemCode")),
            clean_text(row.get("Item")),
            clean_text(row.get("Specification")),
            clean_text(row.get("Group Name")),
            clean_text(row.get("Material Standard")),
            clean_text(row.get("Item Sub Group")),
            clean_text(row.get("Unit")),
        ))
    
    with conn.cursor() as cur:
        for row in items_rows:
            cur.execute(
                f"INSERT INTO items ({', '.join(ITEMS_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(ITEMS_COLUMNS))}) "
                f"RETURNING item_code",
                row
            )

    conn.commit()
    print(f"Items : inserted {len(items_rows)} rows")
