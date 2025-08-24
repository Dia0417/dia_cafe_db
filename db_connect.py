
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kashaf@1122",
        database="cafe_db"
    )
    if conn.is_connected():
        print("Connection successful!")
except mysql.connector.Error as err:
    print("Error:", err)
