# db_manager.py

import sqlite3
import sys
import os 
from decimal import Decimal, InvalidOperation 
import pytz # برای کار با تایم زون ها
from datetime import datetime

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DATABASE_NAME = "trades.db"

DATABASE_SCHEMA_VERSION = 9 # افزایش ورژن برای اضافه کردن جدول تنظیمات و تغییرات تایم زون

def _get_db_version(cursor):
    cursor.execute("PRAGMA user_version;")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_version';")
    if not cursor.fetchone():
        return 0 
    try:
        cursor.execute("SELECT version FROM db_version WHERE id = 1")
        version = cursor.fetchone()
        return version[0] if version else 0
    except sqlite3.Error:
        return 0 

def _set_db_version(conn, cursor, version):
    cursor.execute("CREATE TABLE IF NOT EXISTS db_version (id INTEGER PRIMARY KEY, version INTEGER)")
    cursor.execute("INSERT OR REPLACE INTO db_version (id, version) VALUES (1, ?)", (version,))
    conn.commit()

def connect_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row 
    return conn, conn.cursor()

def migrate_database():
    conn, cursor = connect_db()
    current_db_version = _get_db_version(cursor)

    print(f"Current DB Schema Version: {current_db_version}")
    print(f"Expected DB Schema Version: {DATABASE_SCHEMA_VERSION}")

    try:
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
        
        if current_db_version < 3:
            print("Migrating to version 3: Adding 'size' column to 'trades' table.")
            cursor.execute("ALTER TABLE trades ADD COLUMN size REAL DEFAULT 0.0;")
            _set_db_version(conn, cursor, 3)
            current_db_version = 3
        
        if current_db_version < 4:
            print("Migrating to version 4: Adding 'position_id' column to 'trades' table.")
            cursor.execute("ALTER TABLE trades ADD COLUMN position_id TEXT;")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_position_id ON trades (position_id) WHERE position_id IS NOT NULL;")
            _set_db_version(conn, cursor, 4)
            current_db_version = 4

        if current_db_version < 5:
            print("Migrating to version 5: Adding 'type' column to 'trades' table.")
            cursor.execute("ALTER TABLE trades ADD COLUMN type TEXT DEFAULT '';")
            _set_db_version(conn, cursor, 5)
            current_db_version = 5

        if current_db_version < 6: 
            print("Migrating to version 6: Adding 'volume' column to 'trades' table (deprecated, will be removed in v7).")
            cursor.execute("PRAGMA table_info(trades);")
            columns = [col[1] for col in cursor.fetchall()]
            if 'volume' not in columns:
                cursor.execute("ALTER TABLE trades ADD COLUMN volume REAL DEFAULT 0.0;")
            _set_db_version(conn, cursor, 6)
            current_db_version = 6
        
        if current_db_version < 7:
            print("Migrating to version 7: Removing 'volume' column from 'trades' table.")
            cursor.execute("""
                CREATE TABLE trades_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry REAL,
                    exit REAL,
                    profit TEXT NOT NULL,
                    errors TEXT,
                    size REAL DEFAULT 0.0,
                    position_id TEXT,
                    type TEXT DEFAULT ''
                );
            """)
            cursor.execute("""
                INSERT INTO trades_new (id, date, time, symbol, entry, exit, profit, errors, size, position_id, type)
                SELECT id, date, time, symbol, entry, exit, profit, errors, size, position_id, type
                FROM trades;
            """)
            cursor.execute("DROP TABLE trades;")
            cursor.execute("ALTER TABLE trades_new RENAME TO trades;")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_position_id ON trades (position_id) WHERE position_id IS NOT NULL;")

            _set_db_version(conn, cursor, 7)
            current_db_version = 7
        
        if current_db_version < 8:
            print("Migrating to version 8: Changing 'entry', 'exit', 'size' columns to TEXT for Decimal support.")
            cursor.execute("""
                CREATE TABLE trades_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry TEXT, 
                    exit TEXT,  
                    profit TEXT NOT NULL,
                    errors TEXT,
                    size TEXT DEFAULT '0.0', 
                    position_id TEXT,
                    type TEXT DEFAULT ''
                );
            """)
            cursor.execute("""
                INSERT INTO trades_new (id, date, time, symbol, entry, exit, profit, errors, size, position_id, type)
                SELECT 
                    id, 
                    date, 
                    time, 
                    symbol, 
                    -- تبدیل مقادیر REAL قدیمی به TEXT (با هندل کردن NULL)
                    CASE WHEN entry IS NULL THEN NULL ELSE CAST(entry AS TEXT) END,
                    CASE WHEN exit IS NULL THEN NULL ELSE CAST(exit AS TEXT) END,
                    profit, 
                    errors, 
                    CASE WHEN size IS NULL THEN '0.0' ELSE CAST(size AS TEXT) END, 
                    position_id, 
                    type
                FROM trades;
            """)
            cursor.execute("DROP TABLE trades;")
            cursor.execute("ALTER TABLE trades_new RENAME TO trades;")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_position_id ON trades (position_id) WHERE position_id IS NOT NULL;")
            _set_db_version(conn, cursor, 8)
            current_db_version = 8

        # >>> بلاک مهاجرت جدید برای ورژن 9: اضافه کردن جدول settings
        if current_db_version < 9:
            print("Migrating to version 9: Creating 'settings' table and adding 'original_timezone' to trades.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # مقدار پیش‌فرض منطقه زمانی را بلافاصله پس از ایجاد جدول درج می‌کنیم
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('default_timezone', 'Asia/Tehran'))
            
            # اضافه کردن ستون original_timezone به جدول trades
            cursor.execute("ALTER TABLE trades ADD COLUMN original_timezone TEXT DEFAULT '';")
            
            # فرض می‌کنیم تریدهای قبلی بر اساس UTC+3:00 (زمان ایران) بودند و این مقدار را برای آن‌ها ست می‌کنیم.
            cursor.execute("UPDATE trades SET original_timezone = 'Etc/GMT-3' WHERE original_timezone = '';") # این باید معادل UTC+3:00 باشه


            _set_db_version(conn, cursor, 9)
            current_db_version = 9
        # <<< پایان بلاک مهاجرت جدید
            
        conn.commit()
        print("Database migration complete. DB is up to date.")
    except sqlite3.Error as e:
        print(f"Error during database migration: {e}")
        conn.rollback() 
    finally:
        conn.close()

# تابع اضافه کردن ترید به روز شده برای ذخیره زمان در UTC و original_timezone
def add_trade(date, time, symbol, entry, exit, profit, errors, size, position_id=None, trade_type=None, original_timezone_name=None): 
    conn, cursor = connect_db()
    try:
        entry_str = str(entry) if entry is not None else None
        exit_str = str(exit) if exit is not None else None
        size_str = str(size) if size is not None else '0.0' 

        # اینجا date و time باید زمان UTC باشند.
        # original_timezone_name باید تایم زون مبدا این date و time باشه.
        cursor.execute("""
            INSERT INTO trades (date, time, symbol, entry, exit, profit, errors, size, position_id, type, original_timezone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, time, symbol, entry_str, exit_str, profit, errors, size_str, position_id, trade_type, original_timezone_name)) 
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در افزودن ترید: {e}")
        return False
    finally:
        conn.close()

# تابع get_all_trades به روز شده برای هندل کردن original_timezone و تبدیل به تایم زون انتخابی کاربر
def get_all_trades(display_timezone_name):
    """
    تمام تریدها را از جدول trades بازیابی و زمان‌ها را به display_timezone_name تبدیل می‌کند.
    مقادیر عددی (entry, exit, size) که به صورت TEXT ذخیره شده‌اند، به Decimal تبدیل می‌شوند.
    """
    conn, cursor = connect_db()
    trades_list = []
    try:
        # دریافت تایم زون نمایش از pytz
        display_tz = pytz.timezone(display_timezone_name)

        cursor.execute("SELECT id, date, time, symbol, entry, exit, profit, errors, size, position_id, type, original_timezone FROM trades ORDER BY date ASC, time ASC") 
        rows = cursor.fetchall()
        for row in rows:
            processed_row = dict(row) 
            
            # تبدیل زمان UTC ذخیره شده در دیتابیس به تایم زون انتخابی کاربر
            # فرض می‌کنیم 'date' و 'time' در دیتابیس به صورت UTC ذخیره شده‌اند
            try:
                # ساخت یک datetime object بدون تایم زون (naive) از تاریخ و زمان UTC
                utc_naive_dt = datetime.strptime(f"{processed_row['date']} {processed_row['time']}", "%Y-%m-%d %H:%M")
                # تبدیل به datetime object آگاه به تایم زون (timezone-aware) با UTC
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                # تبدیل از UTC به تایم زون مورد نظر کاربر برای نمایش
                display_aware_dt = utc_aware_dt.astimezone(display_tz)
                processed_row['date'] = display_aware_dt.strftime('%Y-%m-%d')
                processed_row['time'] = display_aware_dt.strftime('%H:%M')
            except ValueError as ve:
                print(f"خطا در تبدیل زمان برای ترید {processed_row['id']}: {ve}. تاریخ و زمان اصلی نمایش داده می‌شوند.")
                # اگر تبدیل ناموفق بود، تاریخ و زمان اصلی دیتابیس (UTC) را نمایش بده.
                # نیازی به تغییر processed_row['date'] و processed_row['time'] نیست، همان مقادیر UTC استفاده می شوند.
                pass
            except Exception as e:
                 print(f"خطای غیرمنتظره در تبدیل زمان برای ترید {processed_row['id']}: {e}.")
                 pass

            entry_decimal = None
            if processed_row['entry'] is not None and processed_row['entry'] != '':
                try:
                    entry_decimal = Decimal(processed_row['entry'])
                except InvalidOperation:
                    pass
            processed_row['entry'] = entry_decimal

            exit_decimal = None
            if processed_row['exit'] is not None and processed_row['exit'] != '':
                try:
                    exit_decimal = Decimal(processed_row['exit'])
                except InvalidOperation:
                    pass
            processed_row['exit'] = exit_decimal

            size_decimal = Decimal('0.0') 
            if processed_row['size'] is not None and processed_row['size'] != '':
                try:
                    size_decimal = Decimal(processed_row['size'])
                except InvalidOperation:
                    size_decimal = Decimal('0.0') 
            processed_row['size'] = size_decimal

            trades_list.append(processed_row) 
            
        return trades_list 
    except InvalidOperation as e:
        print(f"DEBUG_DB_ERROR: خطای کلی InvalidOperation هنگام بازیابی تریدها: {e}")
        return []
    except sqlite3.Error as e:
        print(f"DEBUG_DB_ERROR: خطای SQLite در دریافت تریدها: {e}")
        return []
    finally:
        conn.close()

def delete_trade(trade_id):
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
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT errors FROM trades WHERE profit = 'Loss'")
        rows = cursor.fetchall()
        return [row[0] for row in rows] 
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای تریدهای زیان‌ده: {e}")
        return []
    finally:
        conn.close()

def get_total_trades_count():
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

def add_error_to_list(error_text):
    conn, cursor = connect_db()
    try:
        cursor.execute("INSERT OR IGNORE INTO error_list (error) VALUES (?)", (error_text,))
        conn.commit()
        return True 
    except sqlite3.Error as e:
        print(f"خطا در افزودن خطا به لیست: {e}")
        return False
    finally:
        conn.close()

def get_all_errors():
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
    conn, cursor = connect_db()
    error_counts = {}
    try:
        cursor.execute("SELECT errors FROM trades")
        for row in cursor.fetchall():
            if row['errors']: 
                for err in row['errors'].split(", "):
                    error_counts[err] = error_counts.get(err, 0) + 1
        return error_counts
    except sqlite3.Error as e:
        print(f"خطا در محاسبه تعداد استفاده از خطاها: {e}")
        return {}
    finally:
        conn.close()

def delete_error_from_list(error_id):
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
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM error_list WHERE error = ? AND id != ?", (new_name, error_id))
        if cursor.fetchone()[0] > 0:
            return "duplicate" 

        cursor.execute("UPDATE error_list SET error=? WHERE id=?", (new_name, error_id))

        cursor.execute("SELECT id, errors FROM trades")
        trades_to_update = []
        for trade_id, error_string in cursor.fetchall():
            if error_string and old_name in [e.strip() for e in error_string.split(',')]:
                errors_list = [e.strip() for e in error_string.split(',')]
                updated_errors_list = [new_name if e == old_name else e for e in errors_list]
                trades_to_update.append((", ".join(updated_errors_list), trade_id))
        
        for updated_error_string, trade_id in trades_to_update:
             cursor.execute("UPDATE trades SET errors=? WHERE id=?", (updated_error_string, trade_id))

        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        print(f"خطا (IntegrityError) در ویرایش عنوان: نام جدید تکراری است.")
        return "duplicate"
    except sqlite3.Error as e:
        print(f"خطا در ویرایش عنوان: {e}")
        return str(e) 
    finally:
        conn.close()

def get_profit_trades_count():
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

def check_duplicate_trade(date=None, time=None, position_id=None): 
    conn, cursor = connect_db()
    try:
        if position_id is not None: 
            cursor.execute("SELECT COUNT(*) FROM trades WHERE position_id = ?", (position_id,))
            return cursor.fetchone()[0] > 0
        elif date is not None and time is not None: 
            cursor.execute("SELECT COUNT(*) FROM trades WHERE date = ? AND time = ?", (date, time,))
            return cursor.fetchone()[0] > 0
        else:
            print("Error: check_duplicate_trade requires either position_id or both date and time.")
            return False
    except sqlite3.Error as e:
        print(f"خطا در بررسی ترید تکراری: {e}")
        return False
    finally:
        conn.close()

def update_trades_errors(trade_ids, errors_string):
    """
    فیلد 'errors' را برای لیستی از تریدهای مشخص به‌روزرسانی می‌کند.
    Args:
        trade_ids (list): لیستی از IDهای تریدها.
        errors_string (str): رشته‌ای شامل خطاهای جدید (جدا شده با کاما و فاصله).
    Returns:
        bool: True اگر عملیات موفقیت‌آمیز باشد، False در غیر این صورت.
    """
    if not trade_ids:
        return False

    conn, cursor = connect_db()
    try:
        placeholders = ','.join('?' * len(trade_ids))
        query = f"UPDATE trades SET errors = ? WHERE id IN ({placeholders})"
        
        cursor.execute(query, (errors_string, *trade_ids))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در به‌روزرسانی خطاهای تریدها: {e}")
        return False
    finally:
        conn.close()

def get_trade_errors_by_id(trade_id):
    """
    خطاهای یک ترید خاص را بر اساس ID آن برمی‌گرداند.
    Args:
        trade_id (int): ID ترید.
    Returns:
        str: رشته خطاهای مربوط به ترید، یا None اگر ترید پیدا نشود یا خطایی نداشته باشد.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT errors FROM trades WHERE id = ?", (trade_id,))
        result = cursor.fetchone()
        return result['errors'] if result else None
    finally:
        conn.close()

def get_errors_for_export():
    """
    position_id و errors را برای تمام تریدهایی که فیلد errors آنها خالی نیست، بازیابی می‌کند.
    مناسب برای خروجی گرفتن و بازیابی.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT position_id, errors FROM trades WHERE errors IS NOT NULL AND errors != ''")
        return cursor.fetchall() # برمی‌گرداند لیستی از تاپل‌ها: [(pos_id1, errors1), (pos_id2, errors2), ...]
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای تریدها برای خروجی: {e}")
        return []
    finally:
        conn.close()

def import_errors_by_position_id(error_data_list):
    """
    خطاهای تریدها را بر اساس position_id به‌روزرسانی می‌کند.
    اگر position_id وجود نداشته باشد، آن ردیف نادیده گرفته می‌شود.
    Args:
        error_data_list (list): لیستی از دیکشنری‌ها، هر دیکشنری شامل 'position_id' و 'errors'.
                                مثال: [{'position_id': '12345', 'errors': 'خطا1, خطا2'}]
    Returns:
        int: تعداد رکوردهایی که با موفقیت به‌روزرسانی شدند.
    """
    conn, cursor = connect_db()
    updated_count = 0
    try:
        for item in error_data_list:
            position_id = item.get('position_id')
            errors = item.get('errors')
            
            if position_id is None or errors is None:
                continue 
            
            cursor.execute("UPDATE trades SET errors = ? WHERE position_id = ?", (errors, position_id))
            if cursor.rowcount > 0:
                updated_count += 1
            
            if errors:
                for error_item in errors.split(','):
                    error_text = error_item.strip()
                    if error_text:
                        cursor.execute("INSERT OR IGNORE INTO error_list (error) VALUES (?)", (error_text,))

        conn.commit()
        return updated_count
    except sqlite3.Error as e:
        print(f"خطا در وارد کردن خطاهای تریدها بر اساس Position ID: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

# >>> توابع جدید برای مدیریت تنظیمات در دیتابیس
def get_setting(key, default_value=None):
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result['value'] if result else default_value
    except sqlite3.Error as e:
        print(f"خطا در دریافت تنظیمات '{key}': {e}")
        return default_value
    finally:
        conn.close()

def set_setting(key, value):
    conn, cursor = connect_db()
    try:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در ذخیره تنظیمات '{key}': {e}")
        return False
    finally:
        conn.close()

def get_default_timezone():
    return get_setting('default_timezone', 'Asia/Tehran') 

def set_default_timezone(timezone_name):
    return set_setting('default_timezone', timezone_name)
# <<< پایان توابع جدید

if __name__ == '__main__':
    migrate_database() 
    print("Database schema checked and migrated if necessary.")