import sqlite3

# اتصال به دیتابیس (اگر وجود نداشته باشه ساخته میشه)
conn = sqlite3.connect('trades.db')
cursor = conn.cursor()

# ساخت جدول trades
cursor.execute('''
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    entry REAL,
    exit REAL,
    profit TEXT,
    errors TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database created successfully")
