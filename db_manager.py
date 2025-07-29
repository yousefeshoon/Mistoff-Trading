# db_manager.py

import sqlite3
import sys
import os
from decimal import Decimal, InvalidOperation
import pytz
from datetime import datetime
import json

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DATABASE_NAME = "trades.db"

# از آنجایی که نرم افزار هنوز منتشر نشده و نگران مهاجرت از نسخه های قدیمی نیستیم،
# تمام بلاک های مهاجرتی قبلی را در یک شمای نهایی جمع بندی کرده ایم.
# برای هر تغییر ساختاری جدید در آینده، باید این ورژن را افزایش داده
# و یک بلاک مهاجرت جدید (با ALTER TABLE) اضافه کنیم.
DATABASE_SCHEMA_VERSION = 16 # <--- افزایش ورژن دیتابیس (اینجا تغییری نکرد)

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
    اگر دیتابیس وجود نداشته باشد, با آخرین اسکیما ساخته می شود.
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
        
        if current_db_version < 14:
            print("Migrating to version 14: Adding 'working_days' setting.")
            # روزهای کاری پیش فرض: دوشنبه تا جمعه (0,1,2,3,4) (0=Monday, 6=Sunday در پایتون)
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('working_days', '0,1,2,3,4'))
            _set_db_version(conn, cursor, 14)
            current_db_version = 14
        
        if current_db_version < 15:
            print("Migrating to version 15: Adding default trading session times in UTC (adjusted for EDT display).")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('ny_session_start_utc', '13:30'))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('ny_session_end_utc', '20:00'))
            
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('sydney_session_start_utc', '00:00'))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('sydney_session_end_utc', '06:00'))
            
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('tokyo_session_start_utc', '00:00'))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('tokyo_session_end_utc', '06:00'))
            
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('london_session_start_utc', '07:00'))
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('london_session_end_utc', '15:30'))
            
            _set_db_version(conn, cursor, 15)
            current_db_version = 15

        if current_db_version < 16:
            print("Migrating to version 16: Creating 'report_templates' table.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    filters_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            _set_db_version(conn, cursor, 16)
            current_db_version = 16
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
    finally:
        conn.close()

def get_loss_trades_count():
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT COUNT(*) FROM trades WHERE profit = 'Loss'")
        count = cursor.fetchone()[0] or 0
        return count
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

def get_trades_for_hourly_analysis(start_date_str, end_date_str, trade_type_filter): # No change needed here for date removal from ReportSelectionWindow. This function might still be used by other parts of the application or for future features that do require date filtering.
    """
    تریدهای فیلتر شده را برای آنالیز ساعتی برمی‌گرداند.
    تاریخ‌ها را به صورت UTC و زمان‌ها را نیز به همان شکل ذخیره شده (UTC) برمی‌گرداند.
    این تابع فقط فیلتر تاریخ و نوع ترید را اعمال می‌کند.
    فیلتر خطاها در سطح بالاتر (hourly_analysis_report.py) انجام می‌شود.
    """
    conn, cursor = connect_db()
    trades_list = []
    try:
        query = "SELECT id, date, time, profit, errors, original_timezone FROM trades WHERE date BETWEEN ? AND ?"
        params = [start_date_str, end_date_str]

        if trade_type_filter != "همه":
            query += " AND profit = ?"
            params.append(trade_type_filter)
        
        cursor.execute(query + " ORDER BY date ASC, time ASC", params)
        rows = cursor.fetchall()
        for row in rows:
            processed_row = dict(row)
            
            for col in ['entry', 'exit', 'size', 'actual_profit_amount']:
                if col in processed_row and processed_row[col] is not None and processed_row[col] != '':
                    try:
                        processed_row[col] = Decimal(processed_row[col])
                    except InvalidOperation:
                        processed_row[col] = None 
            trades_list.append(processed_row)
            
        return trades_list
    except sqlite3.Error as e:
        print(f"خطا در دریافت تریدها برای آنالیز ساعتی: {e}")
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

def get_working_days():
    """
    روزهای کاری را به صورت لیستی از اعداد (0=دوشنبه تا 6=یکشنبه) از تنظیمات برمی‌گرداند.
    پیش‌فرض: 0,1,2,3,4 (دوشنبه تا جمعه)
    """
    working_days_str = get_setting('working_days', '0,1,2,3,4')
    try:
        return [int(day.strip()) for day in working_days_str.split(',') if day.strip()]
    except ValueError:
        print(f"Warning: Invalid working_days setting '{working_days_str}'. Using default 0,1,2,3,4.")
        return [0, 1, 2, 3, 4]

def set_working_days(days_list):
    """
    روزهای کاری را در دیتابیس ذخیره می‌کند (به صورت رشته‌ای از اعداد جدا شده با کاما).
    Args:
        days_list (list): لیستی از اعداد روزهای هفته (0=دوشنبه تا 6=یکشنبه) که روز کاری هستند.
    Returns:
        bool: True اگر عملیات موفقیت‌آمیز باشد، False در غیر این صورت.
    """
    working_days_str = ','.join(map(str, sorted(list(set(days_list)))))
    return set_setting('working_days', working_days_str)

def get_session_times_utc():
    """
    ساعت‌های شروع و پایان سشن‌های معاملاتی را به فرمت HH:MM (UTC) از تنظیمات برمی‌گرداند.
    """
    sessions = {
        'ny': {'start': get_setting('ny_session_start_utc', '13:30'), 'end': get_setting('ny_session_end_utc', '20:00')},
        'sydney': {'start': get_setting('sydney_session_start_utc', '00:00'), 'end': get_setting('sydney_session_end_utc', '06:00')},
        'tokyo': {'start': get_setting('tokyo_session_start_utc', '00:00'), 'end': get_setting('tokyo_session_end_utc', '06:00')},
        'london': {'start': get_setting('london_session_start_utc', '07:00'), 'end': get_setting('london_session_end_utc', '15:30')}
    }
    return sessions

def set_session_times_utc(session_data):
    """
    ساعت‌های شروع و پایان سشن‌های معاملاتی را (به فرمت HH:MM UTC) در تنظیمات ذخیره می‌کند.
    Args:
        session_data (dict): دیکشنری شامل ساعت‌های سشن‌ها.
                             مثال: {'ny': {'start': 'HH:MM', 'end': 'HH:MM'}, ...}
    Returns:
        bool: True اگر عملیات موفقیت‌آمیز باشد، False در غیر این صورت.
    """
    try:
        for session_key, times in session_data.items():
            if not set_setting(f'{session_key}_session_start_utc', times['start']) or \
               not set_setting(f'{session_key}_session_end_utc', times['end']):
                return False
        return True
    except Exception as e:
        print(f"Error setting session times: {e}")
        return False

def get_unique_symbols(): # start_date and end_date parameters removed
    """
    لیست نمادهای (symbols) یکتا را از تریدهای ذخیره شده در دیتابیس برمی‌گرداند.
    """
    conn, cursor = connect_db()
    try:
        query = "SELECT DISTINCT symbol FROM trades WHERE symbol IS NOT NULL AND symbol != ''"
        params = [] # params list is now empty as date filters are removed
        query += " ORDER BY symbol ASC"
        
        cursor.execute(query, params)
        symbols = cursor.fetchall()
        return [row[0] for row in symbols]
    except sqlite3.Error as e:
        print(f"خطا در دریافت لیست نمادهای یکتا: {e}")
        return []
    finally:
        conn.close()

def get_first_trade_date():
    """
    اولین تاریخ ترید ثبت شده در دیتابیس را برمی‌گرداند.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT MIN(date) FROM trades WHERE date IS NOT NULL AND date != ''")
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    except sqlite3.Error as e:
        print(f"خطا در دریافت اولین تاریخ ترید: {e}")
        return None
    finally:
        conn.close()

def get_session_times_with_display_utc(user_timezone_name):
    """
    ساعت‌های شروع و پایان سشن‌های معاملاتی را از تنظیمات برمی‌گرداند.
    هم نسخه UTC و هم نسخه تبدیل شده به منطقه زمانی کاربر را فراهم می‌کند.
    """
    current_session_times_utc = get_session_times_utc()
    user_tz = pytz.timezone(user_timezone_name)
    
    sessions_with_display = {}
    for key, times in current_session_times_utc.items():
        start_utc_str = times['start']
        end_utc_str = times['end']

        start_display_str = start_utc_str
        end_display_str = end_utc_str

        try:
            start_utc_time = datetime.strptime(start_utc_str, '%H:%M').time()
            end_utc_time = datetime.strptime(end_utc_str, '%H:%M').time()

            today_utc_date = datetime.utcnow().date() 

            start_dt_utc_naive = datetime.combine(today_utc_date, start_utc_time)
            start_dt_utc_aware = pytz.utc.localize(start_dt_utc_naive)
            start_display_aware = start_dt_utc_aware.astimezone(user_tz)
            start_display_str = start_display_aware.strftime('%H:%M')

            end_dt_utc_naive = datetime.combine(today_utc_date, end_utc_time)
            end_dt_utc_aware = pytz.utc.localize(end_dt_utc_naive)
            end_display_aware = end_dt_utc_aware.astimezone(user_tz)
            end_display_str = end_display_aware.strftime('%H:%M')
            
        except ValueError as e:
            print(f"Error converting session time for display ({key}): {e}")
            pass
        except Exception as e:
            print(f"General error converting session time for display ({key}): {e}")
            pass

        sessions_with_display[key] = {
            'start_utc': start_utc_str,
            'end_utc': end_utc_str,
            'start_display': start_display_str,
            'end_display': end_display_str
        }
    return sessions_with_display

def get_unique_errors_by_filters(trade_type_filter=None): # start_date and end_date parameters removed
    """
    خطاهای یکتا را بر اساس بازه تاریخی و نوع ترید برمی‌گرداند.
    """
    conn, cursor = connect_db()
    errors = set()
    try:
        query = "SELECT errors FROM trades WHERE errors IS NOT NULL AND errors != ''"
        params = []

        # if start_date and end_date: # This block is removed
        #     query += " AND date BETWEEN ? AND ?"
        #     params.extend([start_date, end_date])
        
        if trade_type_filter and trade_type_filter != "همه" and trade_type_filter != "همه انواع":
            query += " AND profit = ?"
            params.append(trade_type_filter)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            if row['errors']:
                for err in row['errors'].split(', '):
                    errors.add(err.strip())
        return sorted(list(errors))
    except sqlite3.Error as e:
        print(f"خطا در دریافت خطاهای یکتا بر اساس فیلتر: {e}")
        return []
    finally:
        conn.close()

def save_report_template(name, filters_data):
    """
    یک قالب گزارش جدید را ذخیره می‌کند.
    Args:
        name (str): نام یکتای قالب.
        filters_data (dict): دیکشنری حاوی تمام فیلترهای انتخاب شده.
    Returns:
        bool: True در صورت موفقیت، False در غیر این صورت (مثلاً نام تکراری).
    """
    conn, cursor = connect_db()
    try:
        filters_json = json.dumps(filters_data)
        cursor.execute("INSERT INTO report_templates (name, filters_json) VALUES (?, ?)", (name, filters_json))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Error: Report template with name '{name}' already exists.")
        return False
    except sqlite3.Error as e:
        print(f"Error saving report template: {e}")
        return False
    finally:
        conn.close()

def get_report_templates():
    """
    لیست همه قالب‌های گزارش ذخیره شده (ID و نام) را برمی‌گرداند.
    Returns:
        list: لیستی از دیکشنری‌ها، هر دیکشنری شامل 'id' و 'name'.
    """
    conn, cursor = connect_db()
    templates = []
    try:
        cursor.execute("SELECT id, name FROM report_templates ORDER BY name ASC")
        rows = cursor.fetchall()
        for row in rows:
            templates.append(dict(row))
        return templates
    except sqlite3.Error as e:
        print(f"Error getting report templates: {e}")
        return []
    finally:
        conn.close()

def get_report_template_by_id(template_id):
    """
    جزئیات یک قالب گزارش خاص را بر اساس ID آن برمی‌گرداند.
    Returns:
        dict: دیکشنری شامل 'id', 'name', 'filters_json' یا None.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("SELECT id, name, filters_json FROM report_templates WHERE id = ?", (template_id,))
        result = cursor.fetchone()
        if result:
            template_data = dict(result)
            template_data['filters_json'] = json.loads(template_data['filters_json'])
            return template_data
        return None
    except sqlite3.Error as e:
        print(f"Error getting report template by ID: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding filters_json for template ID {template_id}: {e}")
        return None
    finally:
        conn.close()

def update_report_template(template_id, new_name, new_filters_data):
    """
    یک قالب گزارش موجود را به‌روزرسانی می‌کند.
    Args:
        template_id (int): ID قالب برای به‌روزرسانی.
        new_name (str): نام جدید قالب.
        new_filters_data (dict): دیکشنری جدید حاوی فیلترها.
    Returns:
        bool: True در صورت موفقیت، False در غیر این صورت (مثلاً نام تکراری).
    """
    conn, cursor = connect_db()
    try:
        new_filters_json = json.dumps(new_filters_data)
        cursor.execute("SELECT COUNT(*) FROM report_templates WHERE name = ? AND id != ?", (new_name, template_id))
        if cursor.fetchone()[0] > 0:
            print(f"Error: Report template with name '{new_name}' already exists for another ID.")
            return False

        cursor.execute("""
            UPDATE report_templates
            SET name = ?, filters_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_name, new_filters_json, template_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Error (IntegrityError): Report template with name '{new_name}' already exists.")
        return False
    except sqlite3.Error as e:
        print(f"Error updating report template: {e}")
        return False
    finally:
        conn.close()

def delete_report_template(template_id):
    """
    یک قالب گزارش را حذف می‌کند.
    Args:
        template_id (int): ID قالب برای حذف.
    Returns:
        bool: True در صورت موفقیت، False در غیر این صورت.
    """
    conn, cursor = connect_db()
    try:
        cursor.execute("DELETE FROM report_templates WHERE id = ?", (template_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting report template: {e}")
        return False
    finally:
        conn.close()

# Helper function for time comparison (moved from hourly_filter or report)
def _time_to_minutes(time_str):
    """Converts 'HH:MM' string to total minutes from midnight."""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

# Helper function for checking if a trade's time is within an interval (moved from hourly_filter or report)
def _is_trade_in_time_interval(trade_datetime_obj, start_time_str, end_time_str):
    """
    Checks if a trade's time (HH:MM) falls within a given interval (HH:MM-HH:MM).
    Handles overnight intervals.
    Args:
        trade_datetime_obj (datetime): The datetime object of the trade (local timezone).
        start_time_str (str): Start time of the interval (e.g., "09:00").
        end_time_str (str): End time of the interval (e.g., "17:00" or "03:00" for overnight).
    Returns:
        bool: True if trade is within interval, False otherwise.
    """
    trade_time_minutes = trade_datetime_obj.hour * 60 + trade_datetime_obj.minute
    interval_start_minutes = _time_to_minutes(start_time_str)
    interval_end_minutes = _time_to_minutes(end_time_str)

    if interval_start_minutes <= interval_end_minutes:
        # Normal interval (e.g., 09:00 - 17:00)
        return interval_start_minutes <= trade_time_minutes < interval_end_minutes
    else:
        # Overnight interval (e.g., 22:00 - 04:00)
        # Trade is in interval if it's after start (on day 1) OR before end (on day 2)
        return trade_time_minutes >= interval_start_minutes or trade_time_minutes < interval_end_minutes

def get_trades_by_filters(filters=None):
    """
    تریدهای فیلتر شده را برمی‌گرداند.
    تاریخ‌ها را به صورت UTC و زمان‌ها را نیز به همان شکل ذخیره شده (UTC) برمی‌گرداند.
    فیلترها را از یک دیکشنری دریافت می‌کند.
    Args:
        filters (dict): دیکشنری حاوی فیلترها. مثال:
                        {'trade_type': 'Loss', 'symbol': ['US30', 'XAUUSD'], 'errors': ['اشتباه ۱', 'اشتباه ۲']}
                        'trade_type' می‌تواند 'Profit', 'Loss', 'RF' یا 'همه انواع' باشد.
                        'symbol' لیستی از نمادها یا 'همه' باشد.
                        'errors' لیستی از خطاها یا 'همه خطاها' یا 'فقط با خطا' باشد.
    Returns:
        list: لیستی از دیکشنری‌ها، هر دیکشنری یک ترید را نمایش می‌دهد.
    """
    conn, cursor = connect_db()
    trades_list = []
    
    # اطمینان حاصل کنید که filters یک دیکشنری است
    if filters is None:
        filters = {}

    try:
        query = "SELECT id, date, time, symbol, entry, exit, profit, errors, size, position_id, type, original_timezone, actual_profit_amount FROM trades WHERE 1=1"
        params = []

        # فیلتر بر اساس نوع ترید (Profit, Loss, RF, همه انواع)
        trade_type_filter = filters.get('trade_type')
        if trade_type_filter and trade_type_filter != "همه انواع":
            query += " AND profit = ?"
            params.append(trade_type_filter)

        # فیلتر بر اساس نماد (symbols)
        symbol_filter = filters.get('symbol')
        if symbol_filter and symbol_filter != "همه":
            if isinstance(symbol_filter, list) and symbol_filter:
                placeholders = ','.join('?' * len(symbol_filter))
                query += f" AND symbol IN ({placeholders})"
                params.extend(symbol_filter)
            elif isinstance(symbol_filter, str): # اگر یک نماد خاص ارسال شده باشد
                 query += " AND symbol = ?"
                 params.append(symbol_filter)

        # فیلتر بر اساس خطاها (errors)
        error_filter = filters.get('errors')
        if error_filter:
            if error_filter == "فقط با خطا": # برای انتخاب تریدهایی که هر خطایی دارند
                query += " AND errors IS NOT NULL AND errors != ''"
            elif error_filter != "همه خطاها": # برای فیلتر بر اساس خطاهای خاص
                if isinstance(error_filter, list) and error_filter:
                    error_clauses = []
                    for err in error_filter:
                        error_clauses.append("errors LIKE ?")
                        params.append(f"%{err}%") # استفاده از LIKE برای جستجوی زیررشته‌ها
                    query += " AND (" + " OR ".join(error_clauses) + ")"
                elif isinstance(error_filter, str): # اگر یک خطای خاص ارسال شده باشد
                    query += " AND errors LIKE ?"
                    params.append(f"%{error_filter}%")

        # اگر فیلترهای دیگر (مثل hourly, weekday) را هم بخواهیم اضافه کنیم، اینجا قرار می‌گیرند.
        # فعلاً فقط همین‌ها که در error_widget استفاده شده‌اند را پوشش می‌دهیم.

        query += " ORDER BY date ASC, time ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            processed_row = dict(row)
            
            # تبدیل مقادیر عددی به Decimal (مشابه get_all_trades)
            for col in ['entry', 'exit', 'size', 'actual_profit_amount']:
                if processed_row[col] is not None and processed_row[col] != '':
                    try:
                        processed_row[col] = Decimal(processed_row[col])
                    except InvalidOperation:
                        processed_row[col] = None 
            trades_list.append(processed_row)
            
        return trades_list
    except sqlite3.Error as e:
        print(f"خطا در دریافت تریدها با فیلتر: {e}")
        return []
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
    print("Database schema checked and migrated if necessary.")