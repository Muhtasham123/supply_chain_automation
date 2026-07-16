"""Load the items table which is the master table that 
   is being referanced from almost all other store and
   imports related tables. Some items are also loaded from 
   purchases that are not in item database"""

import pandas as pd
from database.scripts.etl_common import (
    read_sheet, clean_text,
)
from pathlib import Path

EXCEL_FILE = Path.cwd() / "data" / "Item Database.xlsx"
PURCHASES_EXCEL_FILE = Path.cwd() / "data" / "Purchases List Report.xls"
STOCKS_EXCEL_FILE = Path.cwd() / "data" / "Stock Value Report.xls"
STORE_REQUISITIONS_EXCEL_FILE = Path.cwd() / "data" / "StoreRequisitionDetailExcel.xls"

#Order of columns matters here (must be same as order of columns in sheet)
ITEMS_COLUMNS = [
    "item_code", "item", "specs",  "group_name", "material_standard", "item_category","uom",
]

def load_items(conn):
    df = read_sheet("Sheet1", EXCEL_FILE)
    purchases_df = read_sheet("Sheet1", PURCHASES_EXCEL_FILE)
    stock_df = read_sheet("Sheet1", STOCKS_EXCEL_FILE)
    store_req_df = read_sheet("Sheet1", STORE_REQUISITIONS_EXCEL_FILE)

    item_codes_history = []
    items_rows = []

    with conn.cursor() as cur:
            cur.execute(
                "SELECT item_code from items" #--> getting already existing item codes
            )
            item_codes_history = [row[0] for row in cur.fetchall()]

    for _, row in df.iterrows():
        if clean_text(row.get("ItemCode")) not in item_codes_history:
            item_codes_history.append(clean_text(row.get("ItemCode")))
            items_rows.append((
                clean_text(row.get("ItemCode")),
                clean_text(row.get("Item")),
                clean_text(row.get("Specification")),
                clean_text(row.get("Group Name")),
                clean_text(row.get("Material Standard")),
                clean_text(row.get("Item Sub Group")),
                clean_text(row.get("Unit")),
            ))
    
    for _, row in purchases_df.iterrows():
        if clean_text(row.get("Item Code")) not in item_codes_history:
            item_codes_history.append(clean_text(row.get("Item Code")))
            items_rows.append((
                clean_text(row.get("Item Code")),
                clean_text(row.get("Item Name")),
                clean_text(row.get("Specificati")), #--> Not a typo.Actual column in purchases
                clean_text("-"),        #--> Group name not specified in purchases
                clean_text(row.get("Standard")),
                clean_text(row.get("Item Category")),  #--> material standard in items database
                clean_text(row.get("UOM")),
            ))
    
    for _, row in stock_df.iterrows():
        if clean_text(row.get("ItemCode")) not in item_codes_history:
            item_codes_history.append(clean_text(row.get("ItemCode")))
            items_rows.append((
                clean_text(row.get("ItemCode")),
                clean_text(row.get("Item")),
                clean_text("-"), #--> Specs not specified in stocks
                clean_text("-"),        #--> Group name not specified in stocks
                clean_text("-"),   #--> Standard not specified in stocks
                clean_text(row.get("Category")), 
                clean_text("-"),   #--> UOM not specified in stocks
            ))
    
    for _, row in store_req_df.iterrows():
        if clean_text(row.get("Item Code")) not in item_codes_history:
            item_codes_history.append(clean_text(row.get("Item Code")))
            items_rows.append((
                clean_text(row.get("Item Code")),
                clean_text(row.get("Item Name")),
                clean_text("-"), #--> Specs not specified in store req
                clean_text("-"),        #--> Group name not specified in store req
                clean_text("-"),   #--> Standard not specified in store req
                clean_text(row.get("ItemCategory")), 
                clean_text("-"),   #--> UOM not specified in store req
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
