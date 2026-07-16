"""
load_all.py — one-shot loader for the whole database (logistics + imports).

It performs a CLEAN reload: the transaction tables are truncated first, then
repopulated from the source workbooks in the `Project Files/` folder. The
master tables (items / suppliers / purchase_order) are upserted idempotently,
so they are not truncated.

Source paths are resolved here (from `Project Files/`) and injected into the
loader modules, so the modules keep their own placeholder paths untouched.

Usage:  python -m database.scripts.load_all
"""

from pathlib import Path

# Loader modules (imported as modules so we can point them at the real files).
import database.scripts.etl_common as etl_common
import database.scripts.etl_stores_imports as etl_si
import database.scripts.load_06_import_masters as load_06

from database.scripts.load_01_exports import load_exports
from database.scripts.load_02_export_documentation import load_export_documenttion
from database.scripts.load_03_shipments import load_export_shipments
from database.scripts.load_04_packing import load_packing
from database.scripts.load_05_shifting import load_shifting
# Imports module
from database.scripts.load_06_import_masters import load_import_masters
from database.scripts.load_07_import_details import load_import_details
from database.scripts.load_08_import_items import load_import_items
from database.scripts.load_09_shipment_details import load_shipment_details
from database.scripts.load_10_payment_history import load_payment_history
from database.connection.database_connection import connection

# ---------------------------------------------------------------------------
# Point every loader at the real source workbooks (kept in Project Files/).
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]          # D:/Work/QADBROS
PROJECT_FILES = ROOT / "Project Files"

etl_common.EXCEL_FILE = PROJECT_FILES / "Qadri-Group-Logistics-Master.xlsx"

_import_xlsx = str(PROJECT_FILES / "Import Status Sheet-2026-02 July.xlsx")
etl_si.IMPORT_FILE = _import_xlsx      # read_import_rows() reads this global
load_06.IMPORT_FILE = _import_xlsx     # load_06 reads its own module global


def truncate_transaction_tables():
    """Clean slate for a repeatable full load. CASCADE clears the child tables;
    masters are left intact (they are upserted idempotently)."""
    print("Truncating transaction tables for a clean reload....")
    with connection.cursor() as cur:
        cur.execute("TRUNCATE exports CASCADE")          # logistics + its children
        cur.execute("TRUNCATE import_details CASCADE")   # imports + its children
    connection.commit()


def load_data(table_name, load_function):
    print("Populating " + table_name + "....")
    try:
        load_function(connection)
        print(table_name + " populated successfully....")
    except Exception as exc:
        connection.rollback()
        print(f"!! {table_name} FAILED — {type(exc).__name__}: {exc}")


truncate_transaction_tables()

# --- Logistics ---
load_data("Exports", load_exports)
load_data("Exports Documentation", load_export_documenttion)
load_data("Shipments from logistics", load_export_shipments)
load_data("Packing", load_packing)
load_data("Shifting", load_shifting)

# --- Imports (masters first: items / suppliers / purchase_order) ---
load_data("Import Masters", load_import_masters)
load_data("Import Details", load_import_details)
load_data("Import Items", load_import_items)
load_data("Shipment Details", load_shipment_details)
load_data("Payment History", load_payment_history)

print("\nAll load steps complete.")
