import psycopg2

connection = psycopg2.connect(
    host="localhost",
    database="supply_chain",
    user="postgres",
    password="345waleed",
    port=5432
)

cursor = connection.cursor()
print("Database connected successfully")