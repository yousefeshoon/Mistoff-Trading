import sqlite3

conn = sqlite3.connect("trades.db")
cursor = conn.cursor()

# اضافه کردن ستون time فقط اگه وجود نداشته باشه
try:
    cursor.execute("ALTER TABLE trades ADD COLUMN time TEXT")
    print("Time column added successfully.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Time column already exists.")
    else:
        raise

conn.commit()
conn.close()
