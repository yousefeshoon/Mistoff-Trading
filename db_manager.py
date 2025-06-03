# db_manager.py

import sqlite3
import sys
import os
from decimal import Decimal, InvalidOperation
import pytz
from datetime import datetime

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DATABASE_NAME = "trades.db"

# از آنجایی که نرم افزار هنوز منتشر نشده و نگران مهاجرت از نسخه های قدیمی نیستیم،
# تمام بلاک های مهاجرتی قبلی را در یک شمای نهایی جمع بندی کرده ایم.
# برای هر تغییر ساختاری جدید در آینده، باید این ورژن را افزایش داده
# و یک بلاک مهاجرت جدید (با ALTER TABLE) اضافه کنیم.
DATABASE_SCHEMA_VERSION = 13

def _get_db_version(cursor):
    """
    نسخه فعلی اسکیمای دیتابیس را برمی گرداند.
    """
    cursor.execute("CREATE TABLE IF NOT EXISTS db_version (id INTEGER PRIMARY KEY, version INTEGER)")
    cursor.execute("INSERT OR IGNORE INTO db_version (id, version) VALUES (1, 0)")
    cursor.execute("SELECT version FROM db_version WHERE id = 1")
    version = cursor.fetchone()
    return version[0] if version else 0

def _set_db_version(conn, cursor, version):
    """
    نسخه اسکیمای دیتابیس را تنظیم می کند.
    """
    cursor.execute("INSERT OR REPLACE INTO db_version (id, version) VALUES (1, ?)", (version,))
    conn.commit()

def connect_db():
    """
    به دیتابیس متصل شده و اتصال و کِرسور را برمی گرداند.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def migrate_database():
    """
    دیتابیس را به آخرین نسخه اسکیمای مورد نیاز مهاجرت می دهد.
    اگر دیتابیس وجود نداشته باشد، با آخرین اسکیما ساخته می شود.
    """
    conn, cursor = connect_db()
    current_db_version = _get_db_version(cursor)

    print(f"Current DB Schema Version: {current_db_version}")
    print(f"Expected DB Schema Version: {DATABASE_SCHEMA_VERSION}")

    try:
        if current_db_version < 12:
            print("Migrating to version 12: Creating/Updating final schema.")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
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
                    type TEXT DEFAULT '',
                    original_timezone TEXT DEFAULT 'Asia/Tehran',
                    actual_profit_amount TEXT
                )
            """)
            
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_position_id ON trades (position_id) WHERE position_id IS NOT NULL;")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error TEXT UNIQUE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('default_timezone', 'Asia/Tehran'))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('rf_threshold', '1.5'))

            _set_db_version(conn, cursor, 12)
            current_db_version = 12

        if current_db_version < 13:
            print("Migrating to version 13: Adding 'error_frequency_threshold' setting.")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('error_frequency_threshold', '10.0'))
            _set_db_version(conn, cursor, 13)
            current_db_version = 13

        conn.commit()
        print("Database migration complete. DB is up to date.")
    except sqlite3.Error as e:
        print(f"Error during database migration: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_trade(date, time, symbol, entry, exit, profit, errors, size, position_id=None, trade_type=None, original_timezone_name=None, actual_profit_amount=None):
    conn, cursor = connect_db()
    try:
        entry_str = str(entry) if entry is not None else None
        exit_str = str(exit) if exit is not None else None
        size_str = str(size) if size is not None else '0.0'
        actual_profit_amount_str = str(actual_profit_amount) if actual_profit_amount is not None else None

        cursor.execute("""
            INSERT INTO trades (date, time, symbol, entry, exit, profit, errors, size, position_id, type, original_timezone, actual_profit_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, time, symbol, entry_str, exit_str, profit, errors, size_str, position_id, trade_type, original_timezone_name, actual_profit_amount_str))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"خطا در افزودن ترید: {e}")
        return False
    finally:
        conn.close()

def get_all_trades(display_timezone_name):
    conn, cursor = connect_db()
    trades_list = []
    try:
        display_tz = pytz.timezone(display_timezone_name)

        cursor.execute("SELECT id, date, time, symbol, entry, exit, profit, errors, size, position_id, type, original_timezone, actual_profit_amount FROM trades ORDER BY date ASC, time ASC")
        rows = cursor.fetchall()
        for row in rows:
            processed_row = dict(row)
            
            try:
                utc_naive_dt = datetime.strptime(f"{processed_row['date']} {processed_row['time']}", "%Y-%m-%d %H:%M")
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                display_aware_dt = utc_aware_dt.astimezone(display_tz)
                processed_row['date'] = display_aware_dt.strftime('%Y-%m-%d')
                processed_row['time'] = display_aware_dt.strftime('%H:%M')
            except ValueError as ve:
                print(f"خطا در تبدیل زمان برای ترید {processed_row['id']}: {ve}. تاریخ و زمان اصلی نمایش داده می‌شوند.")
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

            actual_profit_decimal = None
            if processed_row['actual_profit_amount'] is not None and processed_row['actual_profit_amount'] != '':
                try:
                    actual_profit_decimal = Decimal(processed_row['actual_profit_amount'])
                except InvalidOperation:
                    pass
            processed_row['actual_profit_amount'] = actual_profit_decimal

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

def get_profit_trades_errors():
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT errors FROM trades WHERE profit = 'Profit'")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای تریدهای سودده: {e}")
        return []
    finally:
        conn.close()

def get_all_trades_errors():
    """
    دریافت خطاهای تمام تریدها (چه سودده، چه زیان‌ده، چه ریسک‌فری) که فیلد errors آنها خالی نیست.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT errors FROM trades WHERE errors IS NOT NULL AND errors != ''")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای تمام تریدها: {e}")
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
        return cursor.fetchall()
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

def get_rf_threshold():
    threshold_str = get_setting('rf_threshold', '1.5')
    try:
        return Decimal(threshold_str)
    except InvalidOperation:
        print(f"Warning: Invalid rf_threshold '{threshold_str}' found in settings. Using default 1.5.")
        return Decimal('1.5')

def set_rf_threshold(threshold_value):
    return set_setting('rf_threshold', str(threshold_value))

def get_error_frequency_threshold():
    threshold_str = get_setting('error_frequency_threshold', '10.0')
    try:
        return Decimal(threshold_str)
    except InvalidOperation:
        print(f"Warning: Invalid error_frequency_threshold '{threshold_str}' found in settings. Using default 10.0.")
        return Decimal('10.0')

def set_error_frequency_threshold(threshold_value):
    return set_setting('error_frequency_threshold', str(threshold_value))

def calculate_profit_type(profit_amount_decimal, rf_threshold_decimal):
    if rf_threshold_decimal is not None:
        if profit_amount_decimal >= -rf_threshold_decimal and profit_amount_decimal <= rf_threshold_decimal:
            return "RF"
        elif profit_amount_decimal < 0:
            return "Loss"
        elif profit_amount_decimal > 0:
            return "Profit"
    else:
        if profit_amount_decimal < 0:
            return "Loss"
        elif profit_amount_decimal > 0:
            return "Profit"
    return "RF"

def recalculate_trade_profits():
    conn, cursor = connect_db()
    updated_count = 0
    rf_threshold = get_rf_threshold()

    try:
        cursor.execute("SELECT id, actual_profit_amount FROM trades WHERE actual_profit_amount IS NOT NULL")
        rows = cursor.fetchall()

        for row in rows:
            trade_id = row['id']
            actual_profit_str = row['actual_profit_amount']
            
            try:
                actual_profit_decimal = Decimal(actual_profit_str)
                new_profit_type = calculate_profit_type(actual_profit_decimal, rf_threshold)
                
                cursor.execute("SELECT profit FROM trades WHERE id = ?", (trade_id,))
                current_profit_type = cursor.fetchone()['profit']
                
                if current_profit_type != new_profit_type:
                    cursor.execute("UPDATE trades SET profit = ? WHERE id = ?", (new_profit_type, trade_id))
                    updated_count += 1
            except InvalidOperation:
                print(f"Warning: Could not convert actual_profit_amount '{actual_profit_str}' for trade ID {trade_id} to Decimal. Skipping recalculation for this trade.")
                continue
            except Exception as e:
                print(f"Error recalculating profit for trade ID {trade_id}: {e}. Skipping this trade.")
                continue

        conn.commit()
        return updated_count
    except sqlite3.Error as e:
        print(f"Error during recalculating trade profits: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
    print("Database schema checked and migrated if necessary.")