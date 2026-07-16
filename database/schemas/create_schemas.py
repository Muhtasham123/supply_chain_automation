from database.connection.database_connection import connection, cursor
from database.schemas.logistics_schemas import logistics_schemas_queries
from database.schemas.logistics_views import logistics_views_queries
from database.schemas.imports_schemas import imports_schemas_queries
from database.schemas.stores_schemas import stores_schemas_queries

def execute_queries(queries_list, department_name, view_or_schema):
    print("Creating " + department_name + " " + view_or_schema + " ....")

    for query in queries_list:
        cursor.execute(query)
        print("Schema created")
        connection.commit()

    print(department_name + " " + view_or_schema + " created successfully....")



execute_queries(logistics_schemas_queries, "Logistics", "schemas")

execute_queries(logistics_views_queries, "Logistics", "views")


# imports MUST run before stores — it creates the shared masters (items, suppliers, purchase_order)
execute_queries(imports_schemas_queries, "Imports", "schemas")
execute_queries(stores_schemas_queries, "Stores", "schemas")