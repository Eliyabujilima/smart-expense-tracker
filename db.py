import mysql.connector

# ----------------------
# DATABASE CONNECTION
# ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",          # change if you have password
        database="expense_tracker"
    )