import sqlite3

conn = sqlite3.connect('trades.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(trades)")
columns = cursor.fetchall()

for col in columns:
    print(col)
