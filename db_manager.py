# db_manager.py

import sqlite3
import sys
import os 

# تابع کمکی برای پیدا کردن مسیر فایل‌ها در حالت کامپایل‌شده
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'): # اگر برنامه با PyInstaller کامپایل شده باشد
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# حالا DATABASE_NAME را با استفاده از این تابع تعریف می‌کنیم
DATABASE_NAME = get_resource_path("trades.db")
DATABASE_NAME = "trades.db"

DATABASE_NAME = "trades.db"

# نسخه فعلی دیتابیس که انتظار داریم برنامه با آن کار کند
# هر زمان شمای دیتابیس را تغییر دادید، این عدد را زیاد کنید
DATABASE_SCHEMA_VERSION = 2 # مثلا: نسخه 1 برای جدول trades، نسخه 2 برای جدول error_list


def _get_db_version(cursor):
    """
    نسخه شمای دیتابیس را از جدول db_version دریافت می‌کند.
    اگر جدول وجود نداشت یا خالی بود، 0 را برمی‌گرداند.
    """
    cursor.execute("PRAGMA user_version;") # این پرگما برای مدیریت نسخه خودکار SQLite است
    # اما برای نسخه شمای خودمان بهتر است از یک جدول سفارشی استفاده کنیم.

    # ابتدا چک می‌کنیم که جدول db_version وجود دارد یا نه
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_version';")
    if not cursor.fetchone():
        return 0 # اگر جدول db_version وجود نداشت، یعنی دیتابیس خیلی قدیمی است یا تازه ساخته شده.

    try:
        cursor.execute("SELECT version FROM db_version WHERE id = 1")
        version = cursor.fetchone()
        return version[0] if version else 0
    except sqlite3.Error:
        return 0 # در صورت خطا در خواندن نسخه، 0 را برمی‌گرداند (یعنی نیاز به مهاجرت از ابتدا دارد)

def _set_db_version(conn, cursor, version):
    """
    نسخه شمای دیتابیس را در جدول db_version ذخیره می‌کند.
    """
    cursor.execute("CREATE TABLE IF NOT EXISTS db_version (id INTEGER PRIMARY KEY, version INTEGER)")
    cursor.execute("INSERT OR REPLACE INTO db_version (id, version) VALUES (1, ?)", (version,))
    conn.commit()

def connect_db():
    """
    به دیتابیس متصل می‌شود و شیء اتصال و مکان‌نما را برمی‌گرداند.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # این خط باعث می‌شود نتایج کوئری‌ها به صورت دیکشنری قابل دسترسی باشند
    return conn, conn.cursor()

def migrate_database():
    """
    وظیفه این تابع، اعمال مهاجرت‌های دیتابیس بر اساس نسخه شمای آن است.
    """
    conn, cursor = connect_db()
    current_db_version = _get_db_version(cursor)

    print(f"Current DB Schema Version: {current_db_version}")
    print(f"Expected DB Schema Version: {DATABASE_SCHEMA_VERSION}")

    try:
        # مهاجرت از نسخه 0 به 1: ایجاد جدول trades (اگر وجود نداشت)
        if current_db_version < 1:
            print("Migrating to version 1: Creating 'trades' table.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry REAL,
                    exit REAL,
                    profit TEXT NOT NULL,
                    errors TEXT
                )
            """)
            _set_db_version(conn, cursor, 1)
            current_db_version = 1

        # مهاجرت از نسخه 1 به 2: ایجاد جدول error_list (اگر وجود نداشت)
        if current_db_version < 2:
            print("Migrating to version 2: Creating 'error_list' table.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error TEXT UNIQUE
                )
            """)
            _set_db_version(conn, cursor, 2)
            current_db_version = 2

        # اگر در آینده نیاز به مهاجرت‌های بیشتری بود:
        # if current_db_version < 3:
        #     print("Migrating to version 3: Add new column to trades table.")
        #     cursor.execute("ALTER TABLE trades ADD COLUMN new_column TEXT DEFAULT '';")
        #     _set_db_version(conn, cursor, 3)
        #     current_db_version = 3

        conn.commit()
        print("Database migration complete. DB is up to date.")

    except sqlite3.Error as e:
        print(f"Error during database migration: {e}")
        conn.rollback() # در صورت خطا، تغییرات را برگردان
    finally:
        conn.close()

def add_trade(date, time, symbol, entry, exit, profit, errors):
    """
    یک ترید جدید به جدول trades اضافه می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("""
            INSERT INTO trades (date, time, symbol, entry, exit, profit, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, time, symbol, entry, exit, profit, errors))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در افزودن ترید: {e}")
        return False
    finally:
        conn.close()

def get_all_trades():
    """
    تمام تریدها را از جدول trades بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT id, date, time, symbol, entry, exit, profit, errors FROM trades ORDER BY date ASC, time ASC")
        trades = cursor.fetchall()
        return trades
    except sqlite3.Error as e:
        print(f"خطا در دریافت تریدها: {e}")
        return []
    finally:
        conn.close()

def delete_trade(trade_id):
    """
    یک ترید مشخص را از جدول trades حذف می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در حذف ترید: {e}")
        return False
    finally:
        conn.close()

def get_loss_trades_errors():
    """
    خطاهای مربوط به تریدهای زیان‌ده را بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT errors FROM trades WHERE profit = 'Loss'")
        rows = cursor.fetchall()
        return [row[0] for row in rows] # فقط ستون errors را برمی‌گرداند
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای تریدهای زیان‌ده: {e}")
        return []
    finally:
        conn.close()

def get_total_trades_count():
    """
    تعداد کل تریدها را برمی‌گرداند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0] or 0
        return count
    except sqlite3.Error as e:
        print(f"خطا در دریافت تعداد کل تریدها: {e}")
        return 0
    finally:
        conn.close()

# این تابع برای اطمینان از وجود جدول در شروع برنامه استفاده می‌شود
if __name__ == '__main__':
    migrate_database() # حالا تابع migrate_database را صدا می‌زنیم
    print("Database schema checked and migrated if necessary.")

# db_manager.py (ادامه کد قبلی، اینا رو به انتهای فایل اضافه کن)

def add_error_to_list(error_text):
    """
    یک خطای جدید به جدول error_list اضافه می‌کند اگر وجود نداشته باشد.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("INSERT OR IGNORE INTO error_list (error) VALUES (?)", (error_text,))
        conn.commit()
        return True # اگر با موفقیت اضافه شد یا از قبل وجود داشت
    except sqlite3.Error as e:
        print(f"خطا در افزودن خطا به لیست: {e}")
        return False
    finally:
        conn.close()

def get_all_errors():
    """
    تمام خطاها را از جدول error_list بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT error FROM error_list ORDER BY error ASC")
        errors = cursor.fetchall()
        return [row[0] for row in errors]
    except sqlite3.Error as e:
        print(f"خطا در دریافت لیست خطاها: {e}")
        return []
    finally:
        conn.close()

def get_all_errors_with_id():
    """
    تمام خطاها را به همراه ID آن‌ها از جدول error_list بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT id, error FROM error_list ORDER BY error ASC")
        errors = cursor.fetchall()
        return errors
    except sqlite3.Error as e:
        print(f"خطا در دریافت لیست خطاها با ID: {e}")
        return []
    finally:
        conn.close()

def get_error_usage_counts():
    """
    تعداد دفعات استفاده از هر خطا را در جدول trades محاسبه می‌کند.
    """
    conn, cursor = connect_db()
    error_counts = {}
    try:
        cursor.execute("SELECT errors FROM trades")
        for row in cursor.fetchall():
            if row['errors']: # از row['errors'] استفاده می‌کنیم چون row_factory فعال است
                for err in row['errors'].split(", "):
                    error_counts[err] = error_counts.get(err, 0) + 1
        return error_counts
    except sqlite3.Error as e:
        print(f"خطا در محاسبه تعداد استفاده از خطاها: {e}")
        return {}
    finally:
        conn.close()

def delete_error_from_list(error_id):
    """
    یک خطا را از جدول error_list حذف می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("DELETE FROM error_list WHERE id=?", (error_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در حذف خطا از لیست: {e}")
        return False
    finally:
        conn.close()

def rename_error(error_id, old_name, new_name):
    """
    نام یک خطا را در جدول error_list تغییر می‌دهد و همچنین در جدول trades آن را به‌روزرسانی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        # 1. بررسی اینکه نام جدید در error_list وجود دارد یا نه
        cursor.execute("SELECT COUNT(*) FROM error_list WHERE error = ? AND id != ?", (new_name, error_id))
        if cursor.fetchone()[0] > 0:
            return "duplicate" # نام جدید تکراری است

        # 2. به‌روزرسانی نام خطا در جدول error_list
        cursor.execute("UPDATE error_list SET error=? WHERE id=?", (new_name, error_id))

        # 3. پیدا کردن تمام تریدهایی که این خطا توش هست و به‌روزرسانی آن‌ها
        # ابتدا تریدهایی که این خطا را دارند را پیدا می‌کنیم
        cursor.execute("SELECT id, errors FROM trades")
        trades_to_update = []
        for trade_id, error_string in cursor.fetchall():
            if error_string and old_name in [e.strip() for e in error_string.split(',')]:
                errors_list = [e.strip() for e in error_string.split(',')]
                updated_errors_list = [new_name if e == old_name else e for e in errors_list]
                trades_to_update.append((", ".join(updated_errors_list), trade_id))
        
        # حالا تریدها را به‌روزرسانی می‌کنیم
        for updated_error_string, trade_id in trades_to_update:
             cursor.execute("UPDATE trades SET errors=? WHERE id=?", (updated_error_string, trade_id))

        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        print(f"خطا (IntegrityError) در ویرایش عنوان: نام جدید تکراری است.")
        return "duplicate"
    except sqlite3.Error as e:
        print(f"خطا در ویرایش عنوان: {e}")
        return str(e) # برگرداندن پیغام خطا
    finally:
        conn.close()

def get_profit_trades_count():
    """
    تعداد تریدهای سودده را از جدول trades بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM trades WHERE profit = 'Profit'")
        count = cursor.fetchone()[0] or 0
        return count
    except sqlite3.Error as e:
        print(f"خطا در دریافت تعداد تریدهای سودده: {e}")
        return 0
    finally:
        conn.close()

def get_loss_trades_count():
    """
    تعداد تریدهای زیان‌ده را از جدول trades بازیابی می‌کند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM trades WHERE profit = 'Loss'")
        count = cursor.fetchone()[0] or 0
        return count
    except sqlite3.Error as e:
        print(f"خطا در دریافت تعداد تریدهای زیان‌ده: {e}")
        return 0
    finally:
        conn.close()

def check_duplicate_trade(date, time):
    """
    بررسی می‌کند که آیا تریدی با تاریخ و ساعت مشخص از قبل وجود دارد یا خیر.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM trades WHERE date = ? AND time = ?", (date, time))
        return cursor.fetchone()[0] > 0
    except sqlite3.Error as e:
        print(f"خطا در بررسی ترید تکراری: {e}")
        return False # در صورت خطا، فرض می‌کنیم تکراری نیست تا برنامه ادامه پیدا کند
    finally:
        conn.close()

# این تابع برای اطمینان از وجود جدول در شروع برنامه استفاده می‌شود
# این خط از قبل هم در db_manager.py بود
if __name__ == '__main__':
    migrate_database() # حالا تابع migrate_database را صدا می‌زنیم
    print("Database schema checked and migrated if necessary.")