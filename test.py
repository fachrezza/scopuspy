import mysql.connector
from mysql.connector import Error

try:
    # Mengatur koneksi
    connection = mysql.connector.connect(
        host='172.20.10.3',   # Ganti dengan IP komputer target
        port=3306,                  # Port default MySQL
        user='root',            # Ganti dengan username MySQL
        password='sa',        # Ganti dengan password MySQL
        database='db_scholar'    # Ganti dengan nama database yang ingin diakses
    )

    if connection.is_connected():
        print("Koneksi ke MySQL berhasil")
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE();")
        record = cursor.fetchone()
        print("Sedang terhubung ke database:", record)

except Error as e:
    print("Error saat menghubungkan ke MySQL", e)

finally:
    if connection.is_connected():
        cursor.close()
        connection.close()
        print("Koneksi ke MySQL ditutup")
