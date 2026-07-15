from database.scripts.logistics.load_01_exports import load_exports
from database.scripts.logistics.load_02_export_documentation import load_export_documenttion
from database.scripts.logistics.load_03_shipments import load_export_shipments
from database.scripts.logistics.load_04_packing import load_packing
from database.scripts.logistics.load_05_shifting import load_shifting
from database.scripts.stores.load_01_items import load_items
from database.scripts.stores.load_03_purchase_order import load_purchase_orders
from database.scripts.stores.load_02_purchases_data import load_purchases
from database.scripts.stores.load_04_issuance import load_issuances
from database.scripts.stores.load_06_store_requisitions import load_store_requisitions
from database.scripts.stores.load_05_stock import load_stock

from database.connection.database_connection import connection

def load_data(table_name, load_function):
    print("Populating " + table_name + "....")
    load_function(connection)
    print(table_name + " populated successfully....")


#--> Better not to change loading order

load_data("Exports", load_exports)
load_data("Exports Documentation", load_export_documenttion)
load_data("Shipments from logistics", load_export_shipments)
load_data("Packing", load_packing)
load_data("Shifting", load_shifting)
load_data("Items", load_items)
load_data("Purchase Orders", load_purchase_orders)
load_data("Purchases", load_purchases)
load_data("Issuances", load_issuances)
load_data("Stocks", load_stock)
load_data("Store Requisitions", load_store_requisitions)
