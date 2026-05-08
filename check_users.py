import os
from db import get_db_connection
from werkzeug.security import check_password_hash

os.environ['DATABASE_URL'] = "mysql://root:QQBDFmEyhwObRPcedNNyjPBXDllHBcZL@switchback.proxy.rlwy.net:34184/railway"

conn, is_mysql = get_db_connection()
if conn:
    cursor = conn.cursor(dictionary=True) if is_mysql else conn.cursor()
    cursor.execute("SELECT username, password FROM users WHERE username = 'eliya'")
    user = cursor.fetchone()
    if user:
        stored_hash = user['password'] if is_mysql else user[1]
        test_password = "eliya@123"
        if check_password_hash(stored_hash, test_password):
            print("Password matches!")
        else:
            print("Password does not match.")
    else:
        print("User 'eliya' not found.")
    conn.close()
else:
    print("Failed to connect")