import pandas as pd
import db_manager
import os
from datetime import datetime, timedelta
import re 

def _clean_numeric_value(value):
    """
    مقادیر رشته‌ای را پاکسازی کرده و به float تبدیل می‌کند.
    این تابع تنها مسئول تبدیل مقادیر عددی (حتی اگر شامل '/') به float است.
    """
    if pd.isna(value) or str(value).strip() == '':
        return 0.0
    
    s_value = str(value).strip().replace('\xa0', '').replace(',', '')

    # print(f"DEBUG_CLEAN: Input to _clean_numeric_value: '{value}' (type: {type(value)}) -> Cleaned string: '{s_value}'") 

    if '/' in s_value:
        parts = s_value.split('/')
        try:
            return float(parts[0].strip()) 
        except ValueError:
            # print(f"DEBUG_CLEAN: ValueError in split part: '{parts[0].strip()}' for original value: '{value}'")
            return 0.0
    
    try:
        return float(s_value)
    except ValueError:
        # print(f"DEBUG_CLEAN: ValueError for raw value: '{s_value}' for original value: '{value}'")
        return 0.0 

# تابع جدید برای پیش‌نمایش و پردازش اولیه گزارش MT5 بدون ذخیره در دیتابیس
def process_mt5_report_for_preview(file_path):
    """
    تریدهای اکسل (HTML) متاتریدر 5 را می‌خواند، داده‌های اولیه را پردازش کرده
    و یک لیست از تریدهای آماده برای ورود و آمار مربوطه را برمی‌گرداند،
    بدون اینکه آنها را به دیتابیس اضافه کند.
    """
    # print(f"--- شروع پردازش فایل برای پیش‌نمایش: {file_path} ---")

    prepared_trades_list = [] # لیست برای نگهداری تریدهای آماده برای ورود
    total_trades_in_file = 0
    duplicate_count = 0
    skipped_error_count = 0 # برای ردیف‌های نامعتبر یا فیلتر شده (مثل "canceled")

    try:
        # print("در حال خواندن تمام جداول از فایل HTML و جستجوی جدول 'Positions'...")
        
        encodings_to_try = ['utf-8', 'utf-16', 'utf-8-sig', 'cp1252']
        tables_raw_list = None
        detected_encoding = None

        for encoding in encodings_to_try:
            try:
                tables_raw_list = pd.read_html(file_path, header=None, encoding=encoding)
                detected_encoding = encoding
                break
            except Exception:
                tables_raw_list = None
            
        if tables_raw_list is None or not tables_raw_list:
            # print("خطا: هیچ جدولی در فایل HTML با کدگذاری‌های معمول پیدا نشد.")
            return [], 0, 0, 0

        # print(f"فایل با کدگذاری '{detected_encoding}' با موفقیت خوانده شد.")
        
        df_positions_table = None
        header_row_index_in_df_chunk = -1

        for df_chunk in tables_raw_list:
            for r_idx, row_data in df_chunk.iterrows():
                row_list = row_data.astype(str).tolist()
                if 'Position' in row_list and 'Time' in row_list and 'Symbol' in row_list and 'Profit' in row_list:
                    try:
                        pos_idx = row_list.index('Position')
                        _ = int(row_data[pos_idx]) 
                        continue 
                    except (ValueError, TypeError):
                        pass 

                    header_row_index_in_raw_df = r_idx
                    df_positions_table = df_chunk
                    break
            if df_positions_table is not None:
                break
        
        if df_positions_table is None:
            # print("خطا: جدول 'Positions' (بر اساس سربرگ‌های کلیدی) در فایل HTML یافت نشد.")
            return [], 0, 0, 0

        # print(f"جدول 'Positions' پیدا شد. ابعاد اولیه: {df_positions_table.shape}")
        # print(f"سطر سربرگ واقعی در ایندکس {header_row_index_in_raw_df} در جدول خام شناسایی شد.")
        
        actual_headers = df_positions_table.iloc[header_row_index_in_raw_df].astype(str).str.strip()
        
        processed_headers = []
        counts = {}
        for h in actual_headers:
            if h in counts:
                counts[h] += 1
                processed_headers.append(f"{h}.{counts[h]}")
            else:
                counts[h] = 0
                processed_headers.append(h)
        
        df_trades = df_positions_table.iloc[header_row_index_in_raw_df + 1:].copy()
        df_trades.columns = processed_headers 
        
        # print("سربرگ‌های جدول بعد از تنظیم دستی و تصحیح نام‌های تکراری (برای بررسی):")
        # print(df_trades.columns.tolist())

        column_map_to_final_names = {
            'Time': 'open_time_raw',
            'Position': 'position_id',
            'Symbol': 'symbol',
            'Type': 'trade_type',
            'Volume': 'size_raw', 
            'Price': 'entry_price_raw',
            'S / L': 'stop_loss_raw',
            'T / P': 'take_profit_raw',
            'Time.1': 'close_time_raw',
            'Price.1': 'exit_price_raw',
            'Commission': 'commission_raw',
            'Swap': 'swap_raw',
            'Profit.1': 'profit_amount_raw' 
        }
        
        cols_to_select_and_rename = {k: v for k, v in column_map_to_final_names.items() if k in df_trades.columns}
        
        df_processed = df_trades[list(cols_to_select_and_rename.keys())].copy()
        df_processed = df_processed.rename(columns=cols_to_select_and_rename)

        df_processed = df_processed.drop(columns=[
            'stop_loss_raw', 'take_profit_raw', 
            'close_time_raw',
            'commission_raw', 'swap_raw'
        ], errors='ignore')

        # print("سربرگ‌های جدول نهایی برای پردازش (برای بررسی):")
        # print(df_processed.columns.tolist())
        # print(f"ابعاد جدول نهایی پس از حذف ستون‌های نامربوط: {df_processed.shape}")
        
        initial_rows_count = len(df_processed)
        
        df_processed['position_id_temp'] = pd.to_numeric(df_processed['position_id'], errors='coerce')
        # ردیف‌های نامعتبر برای position_id حذف می‌شوند
        df_processed_valid_pos_id = df_processed.dropna(subset=['position_id_temp'])
        skipped_error_count += (initial_rows_count - len(df_processed_valid_pos_id))
        df_processed = df_processed_valid_pos_id.drop(columns=['position_id_temp'])


        initial_rows_count = len(df_processed)
        df_processed['open_time_temp'] = pd.to_datetime(df_processed['open_time_raw'], format='%Y.%m.%d %H:%M:%S', errors='coerce')
        # ردیف‌های نامعتبر برای open_time_raw حذف می‌شوند
        df_processed_valid_time = df_processed.dropna(subset=['open_time_temp'])
        skipped_error_count += (initial_rows_count - len(df_processed_valid_time))
        df_processed = df_processed_valid_time.drop(columns=['open_time_temp'])

        initial_rows_count = len(df_processed)
        df_processed['profit_amount_temp'] = pd.to_numeric(df_processed['profit_amount_raw'], errors='coerce')
        # ردیف‌های نامعتبر برای profit_amount_raw حذف می‌شوند
        df_processed_valid_profit = df_processed.dropna(subset=['profit_amount_temp'])
        skipped_error_count += (initial_rows_count - len(df_processed_valid_profit))
        df_processed = df_processed_valid_profit.drop(columns=['profit_amount_temp'])
        
        # print(f"ابعاد جدول نهایی پس از حذف ردیف‌های با مقادیر کلیدی نامعتبر: {df_processed.shape}")

        # **فیلتر کردن ردیف‌های مربوط به جداول "Orders" و "Deals" و همچنین ردیف‌های "canceled"**
        initial_rows_after_numeric_filter = len(df_processed)
        filter_keywords = ['filled', 'in', 'out', 'market', 'canceled'] 
        
        mask_to_remove = df_processed['trade_type'].astype(str).str.contains('|'.join(filter_keywords), case=False, na=False)
        
        df_processed_filtered = df_processed[~mask_to_remove].copy() 
        skipped_error_count += (initial_rows_after_numeric_filter - len(df_processed_filtered))
        df_processed = df_processed_filtered
        
        # print(f"ابعاد جدول نهایی پس از فیلتر کردن کلمات کلیدی: {df_processed.shape}")

        # **فیلتر کردن ردیف‌های تکراری Position ID در داخل فایل (اگر وجود داشته باشد)**
        pre_duplicate_filter_count_in_file = len(df_processed)
        df_processed.drop_duplicates(subset=['position_id'], keep='first', inplace=True)
        # تکراری‌های داخل فایل هم به عنوان skipped_error_count در نظر گرفته می‌شوند.
        skipped_error_count += (pre_duplicate_filter_count_in_file - len(df_processed))
        
        # print(f"ابعاد جدول نهایی پس از حذف Position IDهای تکراری در فایل: {df_processed.shape}")
        total_trades_in_file = pre_duplicate_filter_count_in_file # تعداد کل تریدهایی که در فایل داشتیم (قبل از حذف تکراری های داخلی)

        # حالا روی تریدهایی که باقی مانده‌اند حلقه می‌زنیم
        for index, row in df_processed.iterrows():
            try:
                position_id = str(row['position_id']).strip()

                # چک می‌کنیم که آیا ترید قبلاً در دیتابیس وجود دارد یا خیر
                if db_manager.check_duplicate_trade(position_id=position_id):
                    duplicate_count += 1
                    continue # اگر تکراری بود، به لیست تریدهای آماده اضافه نکن
                
                open_dt_obj = pd.to_datetime(row['open_time_raw'], format='%Y.%m.%d %H:%M:%S')
                open_dt_obj += timedelta(minutes=30) 
                trade_date = open_dt_obj.strftime('%Y-%m-%d')
                trade_time = open_dt_obj.strftime('%H:%M')

                symbol = str(row['symbol']).strip()
                trade_type = str(row['trade_type']).strip()

                size = _clean_numeric_value(row['size_raw']) 

                entry_price = _clean_numeric_value(row['entry_price_raw'])
                exit_price = _clean_numeric_value(row['exit_price_raw'])
                profit_amount = _clean_numeric_value(row['profit_amount_raw'])
                
                profit_type = "RF" 
                if profit_amount <= -10:
                    profit_type = "Loss" 
                elif profit_amount >= 10:
                    profit_type = "Profit" 
                
                errors_field = "" 

                # ترید را به صورت دیکشنری آماده می‌کنیم تا بعداً به دیتابیس اضافه شود
                prepared_trades_list.append({
                    'date': trade_date,
                    'time': trade_time,
                    'symbol': symbol,
                    'entry': entry_price,
                    'exit': exit_price,
                    'profit': profit_type,
                    'errors': errors_field,
                    'size': size,
                    'position_id': position_id,
                    'trade_type': trade_type
                })

            except KeyError as ke:
                # print(f"خطا در پیدا کردن ستون در ردیف (پیش‌نمایش): {ke}.")
                skipped_error_count += 1
            except ValueError as ve:
                # print(f"خطا در تبدیل داده در ردیف (پیش‌نمایش): {ve}.")
                skipped_error_count += 1
            except Exception as e:
                # print(f"خطای ناشناخته در ردیف (پیش‌نمایش): {e}.")
                skipped_error_count += 1

        # print("\n--- پردازش پیش‌نمایش به پایان رسید ---")
        return prepared_trades_list, total_trades_in_file, duplicate_count, skipped_error_count

    except FileNotFoundError:
        # print("خطا: فایل پیدا نشد.")
        return [], 0, 0, 0
    except pd.errors.EmptyDataError:
        # print("خطا: فایل خالی است یا فرمت آن صحیح نیست.")
        return [], 0, 0, 0
    except Exception as e:
        # print(f"خطایی در خواندن فایل رخ داد: {e}\nلطفاً فرمت فایل را بررسی کنید.")
        # print(f"Detailed error: {e}") 
        return [], 0, 0, 0

# تابع جدید برای اضافه کردن تریدهای آماده به دیتابیس
def add_prepared_trades_to_db(trades_list):
    """
    لیستی از تریدهای آماده (که توسط process_mt5_report_for_preview برگردانده شده)
    را به دیتابیس اضافه می‌کند.
    """
    imported_count = 0
    for trade_data in trades_list:
        if db_manager.add_trade(
            date=trade_data['date'],
            time=trade_data['time'],
            symbol=trade_data['symbol'],
            entry=trade_data['entry'],
            exit=trade_data['exit'],
            profit=trade_data['profit'],
            errors=trade_data['errors'],
            size=trade_data['size'],
            position_id=trade_data['position_id'],
            trade_type=trade_data['trade_type']
        ):
            imported_count += 1
        else:
            # print(f"خطا در ذخیره ترید با Position ID: {trade_data.get('position_id', 'N/A')}")
            pass 
    return imported_count


# این بخش (if __name__ == "__main__":) برای تست مستقل ماژول است.
# حالا که این توابع به app.py منتقل شدند، این بخش را مطابق با توابع جدید به روز می‌کنیم.
if __name__ == "__main__":
    db_manager.migrate_database()
    
    test_file_path = "ReportHistory-303941.html"
    if os.path.exists(test_file_path):
        # اجرای تابع پیش‌نمایش و نمایش آمار در کنسول
        prepared_trades, total, dup, err = process_mt5_report_for_preview(test_file_path)
        # print(f"\n--- نتایج پیش‌نمایش ---")
        # print(f"کل تریدها در فایل: {total}")
        # print(f"آماده برای ورود: {len(prepared_trades)}")
        # print(f"تکراری در دیتابیس: {dup}")
        # print(f"رد شده (خطا/فیلتر): {err}")
        
        # اگر می‌خواهی واقعاً وارد کنی:
        # confirmed_import_count = add_prepared_trades_to_db(prepared_trades)
        # print(f"{confirmed_import_count} ترید با موفقیت وارد شد.")
    else:
        # print(f"فایل تستی '{test_file_path}' پیدا نشد. لطفاً آن را در کنار اسکریپت قرار دهید یا مسیر درست را وارد کنید.")
        pass