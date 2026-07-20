"""Mock data for the prototype dashboard / inventory / purchase pages.

These pages currently use placeholder data. Swap these functions for real
queries against supply_chain_db when you're ready.
"""

import pandas as pd


def purchase_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Order": ["PO-1001", "PO-1002", "PO-1003", "PO-1004", "PO-1005", "PO-1006"],
            "Supplier": ["ABC Steel", "XYZ Metals", "ABC Steel", "Delta Alloys",
                         "XYZ Metals", "Delta Alloys"],
            "Qty": [120, 80, 200, 50, 90, 160],
            "Pending": [30, 0, 75, 10, 0, 40],
            "Status": ["Pending", "Completed", "Pending", "Pending",
                       "Completed", "Pending"],
        }
    )


def stock_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Item": ["Roll Shaft", "Bearing 6205", "Hydraulic Oil", "Gear Coupling",
                     "V-Belt", "Steel Plate"],
            "Qty": [12, 0, 45, 8, 0, 210],
            "Status": ["In Stock", "Out of Stock", "In Stock", "Low Stock",
                       "Out of Stock", "In Stock"],
        }
    )
