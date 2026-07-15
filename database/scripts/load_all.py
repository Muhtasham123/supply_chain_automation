from database.scripts.logistics.load_01_exports import load_exports
from database.scripts.logistics.load_02_export_documentation import load_export_documenttion
from database.scripts.logistics.load_03_shipments import load_export_shipments
from database.scripts.logistics.load_04_packing import load_packing
from database.scripts.logistics.load_05_shifting import load_shifting
from database.scripts.stores.load_01_items import load_items

from database.connection.database_connection import connection

def load_data(table_name, load_function):
    print("Populating " + table_name + "....")
    load_function(connection)
    print(table_name + " populated successfully....")


load_data("Exports", load_exports)
load_data("Exports Documentation", load_export_documenttion)
load_data("Shipments from logistics", load_export_shipments)
load_data("Packing", load_packing)
load_data("Shifting", load_shifting)
load_data("Items", load_items)
