"""Load the Main Issuances table"""

import pandas as pd
pd.set_option("display.max_columns", None)
from database.scripts.etl_common import (
    read_sheet, clean_text, clean_int, clean_date, clean_number
)
from pathlib import Path

EXCEL_FILE = Path.cwd() / "data" / "Issuance Detail Report.xls"

#Order of columns matters here (must be same as order of ROWS list)
ISSUANCE_COLUMNS = ["issuance_code", "item_code", "department", "branch", "issue_to_others",  "authorized_by", "issued_by", "received_by", "description", "ref_no", "demand_ref_no",       "quantity", "status", "from_date", "unit_price", "total_price", "job_number", ]

#--> Order must be same as columns order
ISSUANCE_HEADERS = [
    ("IssuanceCode", clean_text),	("ItemCode", clean_text), ("Department", clean_text), ("Branch", clean_text),	("IssueToOthers", clean_text), ("AuthorizedBy", clean_text), ("IssuedBy",clean_text),	("ReceivedBy", clean_text), ("Description", clean_text), ("RefNo", clean_text), ("Demand RefN", clean_text), ("Quantity", clean_int), ("Status", clean_text), ("FromDate", clean_date),	("UnitPrice", clean_number), ("TotalPric",clean_number), ("JobNumber", clean_text)
]

def load_issuances(conn):
    df = read_sheet("Sheet1", EXCEL_FILE)
    issuances_rows = []

    for _, row in df.iterrows():
        row_tuple = ()
        for header, cleaning_function in ISSUANCE_HEADERS:
            row_tuple = row_tuple + (cleaning_function(row.get(header)), )
        issuances_rows.append(row_tuple)
    
    with conn.cursor() as cur:
        for row in issuances_rows:
            cur.execute(
                f"INSERT INTO issuance ({', '.join(ISSUANCE_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(ISSUANCE_COLUMNS))}) "
                f"RETURNING issuance_code",
                row
            )

    conn.commit()
    print(f"Issuances : inserted {len(issuances_rows)} rows")
